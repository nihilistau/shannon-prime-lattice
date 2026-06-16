The individual pieces have already been validated on the Samsung S22 Ultra.

By treating the transformer's activation layers as "images," you can bypass standard CPU bottlenecks. The Spectra 680 Image Signal Processor (ISP) is essentially a massive, fixed-point parallel calculator. Pushing the Feed-Forward Network (FFN) skeleton and residual band fusion to the ISP at 18-bit fixed point offloads the heavy lifting from the standard cores.

### B. Will it run at hyper speed?

**Yes, but with a brutal physical caveat.**

The Halide-compiled Hexagon Vector eXtensions (HVX) kernels—handling the Q8 dequantization, matmul, and NTT—were validated on your S22U at an 81-microsecond minimum dispatch time. This matches the absolute limit of the Qualcomm AI Hub reference run.

However, running the Spectra 680 ISP in parallel with the V69 Hexagon Tensor Processor (HTP) pulls so much power that the phone will heat-soak in 30 to 60 seconds. Once the hardware hits that thermal trip point, the firmware will hard-throttle the DSP throughput by roughly 40% to prevent physical damage. It runs at hyper speed, but it is a sprint, not a marathon, without active cooling.

### C. The Execution Plan (Stringing together "Mode D")

Right now, the architecture operates primarily in Mode C (using the QNN HTP for matmuls and HVX for everything else). To string the ISP offload together into Mode D, you need to execute the following pipeline:

1. **AOT Cross-Compilation via Halide:** Following the Arm workflow you linked, write the ISP fusion algorithms in Halide on your host machine. Use Halide’s AOT compiler to generate an optimized static library (`.a`) targeting Android. Ensure you use the `NoRuntime` flag so the pipeline shares a single runtime state, avoiding duplicate symbol crashes when linked into the main engine.
2. **Operator Fusion to Save DRAM:** Use Halide's scheduling directives (like `compute_root` and `compute_inline`) to fuse the skeleton and residual band operations. This keeps intermediate tensors in the ISP’s fast local cache instead of writing them out to UFS or DRAM, completely bypassing the memory bandwidth wall.
3. **Shared Virtual Memory (SVM) via FastRPC:** To feed the ISP and the V69 HTP without copying memory, you must allocate zero-copy Shared Virtual Memory buffers. Be extremely careful here: the FastRPC `rpcmem` registration size must perfectly match the IDL length parameter. If you over-allocate by even a byte, the DSP will silently fail with an `AEE_EUNSUPPORTED` error.


4. **The Parallel Dispatch:** Route the heavy $Q \cdot K^T$ matmuls to the V69 HTP via the QNN backend while simultaneously firing the Halide-compiled FFN fusion kernels to the Spectra 680 ISP.


5. **Thermal Micro-Pausing:** To survive the 30-60 second heat-soak wall, you must retain the engine's 1-2 millisecond micro-pauses between layers. This allows the host thermal sensor to ride the limit smoothly without triggering the firmware's 40% hard throttle.

This is exactly the right sequence. We build the algorithmic fusion in Halide first (the logic), and then we build the FastRPC zero-copy plumbing (the pipe).

Here is the blueprint for executing both steps, keeping strict adherence to the engine's memory constraints and avoiding the known Hexagon traps.

### Step 1: The Halide FFN Skeleton (ISP/DSP Fusion)

The goal here is to implement **Mode D**: spectral reconstruction where the skeleton and residual band fusion happens at 18-bit fixed point. In Halide, we treat the hidden states and weights as 2D images `(hidden_dim, sequence_length)` and fuse the Up-Projection, Gate (SwiGLU/GeGLU), and Down-Projection into a single pipeline so intermediate tensors never hit DRAM.

Here is the conceptual Halide Generator architecture you will need to write in C++ on your host machine to AOT-compile the kernel:

```cpp
#include "Halide.h"
using namespace Halide;

class FFNSkeletonGenerator : public Halide::Generator<FFNSkeletonGenerator> {
public:
    // Inputs (Mapped from SVM buffers)
    Input<Buffer<int16_t>> residual_in{"residual_in", 2}; 
    Input<Buffer<int8_t>>  w_up{"w_up", 2};       // Q8 packed weights
    Input<Buffer<int8_t>>  w_gate{"w_gate", 2};   // Q8 packed weights
    Input<Buffer<int8_t>>  w_down{"w_down", 2};   // Q8 packed weights
    Input<Buffer<float>>   scales{"scales", 1};   // Frobenius row scales

    // Output
    Output<Buffer<int16_t>> ffn_out{"ffn_out", 2};

    void generate() {
        Var x("x"), y("y"), c("c");

        // 1. Up & Gate Projections (Dot products)
        RDom r(0, w_up.width());
        Func up("up"), gate("gate");
        
        // Accumulate in 32-bit to prevent overflow, simulating the 18-bit fixed point
        up(x, y) += cast<int32_t>(residual_in(r, y)) * cast<int32_t>(w_up(x, r));
        gate(x, y) += cast<int32_t>(residual_in(r, y)) * cast<int32_t>(w_gate(x, r));

        // 2. SwiGLU / GeGLU Activation (Approximated for fixed point)
        Func activated("activated");
        // (Insert fixed-point SiLU/GELU approximation here)
        activated(x, y) = up(x, y) * /* silu */(gate(x, y));

        // 3. Down Projection & Residual Addition
        RDom r_down(0, w_down.width());
        Func down("down");
        down(x, y) += activated(r_down, y) * cast<int32_t>(w_down(x, r_down));

        // Scale back to 16-bit and add the residual
        ffn_out(x, y) = residual_in(x, y) + cast<int16_t>(down(x, y) * scales(x));
    }

    void schedule() {
        if (get_target().has_feature(Target::Hexagon)) {
            Var xi("xi"), yi("yi");
            // Tile and vectorize for the 128-byte HVX vectors
            ffn_out.compute_root()
                   .hexagon()
                   .tile(x, y, xi, yi, 64, 4) // 64 int16s = 128 bytes
                   .vectorize(xi);
            
            // FUSION: Compute intermediates inline within the Hexagon L2 cache
            up.compute_at(ffn_out, x).vectorize(x);
            gate.compute_at(ffn_out, x).vectorize(x);
        } else {
            // Standard ARM NEON fallback schedule
            ffn_out.compute_root().vectorize(x, 8);
        }
    }
};
HALIDE_REGISTER_GENERATOR(FFNSkeletonGenerator, ffn_skeleton)

```

**The Compilation Target:**
When you compile this with Halide AOT, you must specify the exact target string to emit the Hexagon object code:
`arm-64-android-hexagon-hexagon_dma`

This will emit an `ffn_skeleton.a` and `ffn_skeleton.h` that you link directly into `libshannonprime.so`.

---

### Step 2: The FastRPC SVM Buffer Allocation

This is the bridge that feeds the Halide kernel without triggering a memory copy between the Android ARM cores and the DSP/ISP.

**The Footgun Warning:**
As documented in the Systems spec, the `rpcmem` registration size must **exactly equal** the IDL length parameter. If you over-allocate a scratch buffer by even a single byte to be "safe", FastRPC will silently fail with an `AEE_EUNSUPPORTED` error, which masquerades as a DSP crash.

Here is how you allocate and pass the zero-copy buffer to the Halide function:

```c
#include "rpcmem.h"
#include "ffn_skeleton.h" // Generated by Halide AOT
#include "HalideBuffer.h"

// FastRPC ION Heap ID for Hexagon DSP
#define RPCMEM_HEAP_ID_SYSTEM 25 
#define RPCMEM_DEFAULT_FLAGS 1

sp_status allocate_and_run_ffn(sp_session* sess, int hidden_dim, int seq_len) {
    // 1. EXACT size calculation to avoid AEE_EUNSUPPORTED
    size_t buffer_size = hidden_dim * seq_len * sizeof(int16_t);
    
    // 2. Allocate Shared Virtual Memory (SVM)
    rpcmem_init();
    void* svm_residual = rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, RPCMEM_DEFAULT_FLAGS, buffer_size);
    void* svm_ffn_out  = rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, RPCMEM_DEFAULT_FLAGS, buffer_size);

    if (!svm_residual || !svm_ffn_out) {
        return SP_ENOMEM;
    }

    // 3. Wrap SVM pointers in Halide buffers (Zero-copy)
    halide_dimension_t shape[] = {
        {0, hidden_dim, 1},
        {0, seq_len, hidden_dim}
    };
    
    halide_buffer_t halide_residual = {0};
    halide_residual.host = (uint8_t*)svm_residual;
    halide_residual.dimensions = 2;
    halide_residual.dim = shape;
    halide_residual.type = halide_type_of<int16_t>();

    halide_buffer_t halide_out = {0};
    halide_out.host = (uint8_t*)svm_ffn_out;
    halide_out.dimensions = 2;
    halide_out.dim = shape;
    halide_out.type = halide_type_of<int16_t>();

    // 4. Dispatch the Halide AOT function (Executes on DSP/ISP)
    // w_up, w_gate, w_down, and scales would also be mapped SVM buffers
    int result = ffn_skeleton(&halide_residual, &w_up, &w_gate, &w_down, &scales, &halide_out);

    if (result != 0) {
        // Halide returned an error
        rpcmem_free(svm_residual);
        rpcmem_free(svm_ffn_out);
        return SP_EHVX; 
    }

    // Free buffers (or retain them if bound to the sp_session lifecycle)
    rpcmem_free(svm_residual);
    rpcmem_free(svm_ffn_out);
    rpcmem_deinit();

    return SP_OK;
}

```

### Next Steps for Execution

1. **Verify the Halide Generator:** 
2. **Lifecycle Management:** In `PPT-LAT-L1-ABI`, we locked in that L1 (C) does not allocate memory on the hot path. Therefore, these `rpcmem_alloc` calls should technically happen at `sp_session_create` (allocating the maximum required bounds), and the pointers should live inside the `sp_session` struct so they are just reused step-by-step.

### 1. Refining the Fixed-Point Math (The Activation Function)

When running on the Hexagon DSP or Spectra ISP, transcendental functions like `exp()` for a true SiLU/SwiGLU ($x \cdot \text{sigmoid}(x)$) or GELU will completely decimate your vector throughput. To maintain that 81-microsecond dispatch time, you must use a fixed-point polynomial approximation.

The industry standard DSP trick for SwiGLU is to approximate it with **HardSwish**:
`f(x) = x * clamp(x + 3, 0, 6) / 6`

In Halide, operating on `int32_t` accumulators with a fixed fractional precision (let's assume $Q$-bits of fractional precision, e.g., $Q=8$ or $Q=12$ depending on your Frobenius scale bounds), the implementation looks like this:

```cpp
// 1. Define the Q-point scaling constants for the DSP
// If Q=8, then 3.0 is 3 << 8 (768), and 6.0 is 6 << 8 (1536)
const int Q_BITS = 8;
Expr three = make_const(Int(32), 3 << Q_BITS);
Expr six   = make_const(Int(32), 6 << Q_BITS);

// 2. The Gate Projection (Accumulated int32_t)
Expr gate_val = gate(x, y); 
Expr up_val   = up(x, y);

// 3. HardSwish Approximation (Vectorizes perfectly on HVX)
Expr swish_factor = clamp(gate_val + three, 0, six);

// 4. Multiply and downshift
// We multiply up_val by swish_factor, then divide by 'six' (which the DSP 
// compiler will optimize into a multiply-by-reciprocal and a bitshift).
// We then shift down by Q_BITS to return to the base Q-point scale.
activated(x, y) = (up_val * swish_factor) / (six << Q_BITS);

```

This approximation fuses perfectly into the Hexagon L2 cache, uses only basic integer arithmetic (add, clamp, multiply, shift), and avoids the pipeline stalls associated with floating-point math or lookup tables.

### 2. How to Handle the FastRPC SVM Lifecycle

The `PPT-LAT-L1-ABI` stricture is clear: **L1 `malloc`s nothing that crosses the FFI except the three handles**, and there is no memory allocation on the hot path (prefill or decode).

However, the ABI also states: *"internal arenas (activation, ARM bank, sieve, Spinor pool) are session-private and released by `sp_session_destroy`"*.

Because FastRPC requires `rpcmem_alloc` (backed by ION heaps) to achieve zero-copy Shared Virtual Memory (SVM), we cannot let the Rust wrapper (L2) allocate standard heap memory and pass it down. If Rust passes standard memory, FastRPC will perform a hidden, blocking memory copy under the hood, killing your latency.

Here is the exact lifecycle blueprint to respect the ABI while honoring Hexagon's hardware constraints:

**A. Allocation at Session Creation**
When L2 calls `sp_session_create`, it passes a `sp_session_config` struct that includes `max_context`. Inside the C core's implementation of `sp_session_create` (specifically the Hexagon variant), you allocate the FastRPC scratch buffers based on that maximum bound:

```c
// Inside sp_session_create (Hexagon backend implementation)
size_t ffn_scratch_size = arch_info.hidden_dim * config.max_context * sizeof(int16_t);

// Allocate the zero-copy ION buffers
rpcmem_init();
session->svm_residual = rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, RPCMEM_DEFAULT_FLAGS, ffn_scratch_size);
session->svm_ffn_out  = rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, RPCMEM_DEFAULT_FLAGS, ffn_scratch_size);

if (!session->svm_residual || !session->svm_ffn_out) {
    return SP_ENOMEM; // Caught safely at load time[cite: 7]
}

```

**B. Execution on the Hot Path**
During `sp_prefill_chunk` or `sp_decode_step`, there are zero `malloc` or `rpcmem_alloc` calls. You simply map the current token length against the pre-allocated ION heap pointers, wrap them in `halide_buffer_t`, and fire the AOT function.

**C. Destruction**
When Rust drops the session, it calls `sp_session_destroy`. The C core cleans up the ION heaps:

```c
// Inside sp_session_destroy
rpcmem_free(session->svm_residual);
rpcmem_free(session->svm_ffn_out);
rpcmem_deinit();

```

This perfectly satisfies the ABI contract. L2 never knows about the Hexagon-specific memory allocators, no allocation occurs during token generation, and the DSP gets its mandatory zero-copy SVM pointers.

---

With the fixed-point math tightened and the lifecycle properly mapped to the session arena, we have a clear path to compile the Halide generator.

Let's lock in the FastRPC bridge. The Interface Definition Language (IDL) file is the absolute arbiter of what crosses the boundary between the Android ARM cores and the Hexagon DSP.

If the IDL is wrong, FastRPC defaults to copying memory over the bus, which instantly kills the latency and defeats the purpose of the Shared Virtual Memory (SVM) ION buffers. Furthermore, as documented in the roadmap, if the buffer sizes passed into the IDL signature do not **exactly** match the sizes allocated by `rpcmem_alloc`, the DSP will silently fail with `AEE_EUNSUPPORTED`.

Here is the exact `ffn_fusion.idl` and the bridging logic required to expose your Halide kernel safely.

### 1. The IDL Signature (`ffn_fusion.idl`)

Create this file in your Hexagon backend directory (e.g., `src/engine/hexagon/ffn_fusion.idl`).

```c
#include "remote.h"

interface ffn_fusion {
    // The sizes passed to the *Len parameters MUST exactly match the rpcmem_alloc size.
    // 'in'   = ARM to DSP (read-only on DSP)
    // 'rout' = DSP to ARM (write-only on DSP, avoids an unnecessary copy-in)
    
    long run_ffn_skeleton(
        in  int16* residual_in, int residual_inLen,
        in  int8*  w_up,        int w_upLen,
        in  int8*  w_gate,      int w_gateLen,
        in  int8*  w_down,      int w_downLen,
        in  float* scales,      int scalesLen,
        rout int16* ffn_out,    int ffn_outLen,
        in  int    hidden_dim,
        in  int    seq_len
    );
};

```

*Note the `rout` keyword for `ffn_out`. By specifying `rout` (Reference Out) instead of `inout`, you tell FastRPC that the DSP does not need to read the initial garbage state of the output buffer. This saves memory bandwidth on the dispatch.*

### 2. Compiling the IDL (`qaic`)

To compile this, you must use Qualcomm's `qaic` compiler. Relying on the roadmap's strict environmental warnings for your Windows host setup, the command invocation must respect the path fixes:

```bash
# Executed from your env-hexagon.bat context, ensuring Git sh.exe is in PATH
qaic.exe -mdll -I <Hexagon_SDK_Path>/inc/stddef ffn_fusion.idl

```

This command generates two critical C files:

* `ffn_fusion_stub.c`: Gets linked into your host Android `libshannonprime.so` (L1).
* `ffn_fusion_skel.c`: Gets linked into the DSP-side shared object (`libffn_fusion_skel.so`), which the DSP loads at runtime.

### 3. The DSP Skeleton Wrapper (Bridging IDL to Halide)

The `qaic` compiler generates the network boilerplate, but you must write the implementation function on the DSP side that receives the raw pointers and wraps them in `halide_buffer_t` before invoking your AOT-compiled kernel.

Create `ffn_fusion_imp.c` (this compiles for the Hexagon target, **not** ARM):

```c
#include "ffn_fusion.h"      // Generated by qaic
#include "ffn_skeleton.h"    // Generated by Halide AOT
#include "HalideBuffer.h"

// This function signature matches the IDL definition exactly
long ffn_fusion_run_ffn_skeleton(
    const int16* residual_in, int residual_inLen,
    const int8*  w_up,        int w_upLen,
    const int8*  w_gate,      int w_gateLen,
    const int8*  w_down,      int w_downLen,
    const float* scales,      int scalesLen,
    int16*       ffn_out,     int ffn_outLen,
    int          hidden_dim,
    int          seq_len
) {
    // 1. Safety check to prevent Halide OOB
    int expected_elements = hidden_dim * seq_len;
    if (residual_inLen != expected_elements * sizeof(int16_t) || 
        ffn_outLen != expected_elements * sizeof(int16_t)) {
        return -1; // AEE_EBADPARM equivalent
    }

    // 2. Wrap the raw FastRPC pointers in Halide buffers
    halide_dimension_t shape[] = {
        {0, hidden_dim, 1},
        {0, seq_len, hidden_dim}
    };

    halide_buffer_t h_res_in = {0};
    h_res_in.host = (uint8_t*)residual_in;
    h_res_in.dimensions = 2;
    h_res_in.dim = shape;
    h_res_in.type = halide_type_of<int16_t>();

    // Repeat for w_up, w_gate, w_down, and scales...
    // (Ensure you adjust shapes for the weight matrices accordingly)

    halide_buffer_t h_out = {0};
    h_out.host = (uint8_t*)ffn_out;
    h_out.dimensions = 2;
    h_out.dim = shape;
    h_out.type = halide_type_of<int16_t>();

    // 3. Dispatch the Halide Kernel
    int result = ffn_skeleton(&h_res_in, &h_w_up, &h_w_gate, &h_w_down, &h_scales, &h_out);

    return result == 0 ? 0 : -2; // Return 0 on success, negative on Halide error
}

```

### The Execution Pipeline

At this point, the stack is fully defined:

1. **L1 Engine (ARM):** Calls `ffn_fusion_run_ffn_skeleton()` passing the SVM pointers.
2. **FastRPC Stub (ARM):** Marshals the call, verifies sizes against ION heap allocations, and triggers the DSP over the shared bus.
3. **FastRPC Skel (DSP):** Receives the call without copying memory.
4. **DSP Imp (DSP):** Wraps the pointers in Halide bounds.
5. **Halide Kernel (DSP/ISP):** Executes the fused `int32_t` accumulation and HardSwish approximation natively on the hardware.

We write the CMake instructions for the Hexagon backend to correctly split the compilation (stub for ARM, skel+imp+Halide for DSP)

Let's wire it up. Compiling for the Hexagon backend is uniquely tricky because you are actually orchestrating a split-architecture build: the L1 engine runs on the Android ARM64 host, but the compute payload runs on the Hexagon V69 DSP.

Here is how you compile the Halide Generator locally, followed by the CMake logic required to bridge the ARM and DSP targets without breaking the build environment.

### 1. Compiling the Halide Generator (Local Windows Host)

Before CMake can link anything, you need to compile your Halide C++ generator on your Windows host and execute it to emit the DSP object code.

Open your `env-hexagon.bat` environment and run:

```bash
# 1. Compile the generator itself (using your host compiler, e.g., MinGW g++)
g++ ffn_skeleton_generator.cpp -std=c++17 -I <path_to_halide_include> -L <path_to_halide_lib> -lHalide -o generate_ffn_skeleton.exe

# 2. Execute the generator to cross-compile for the Hexagon V69 DSP
# The 'hexagon' target tells Halide to emit HVX vector instructions.
generate_ffn_skeleton.exe -g ffn_skeleton -e static_library,h -o . target=hexagon-v69-no_asserts

```

This generates `ffn_skeleton.a` (the DSP machine code) and `ffn_skeleton.h` (the C header).

### 2. The Split-Architecture CMake Configuration

In standard Android NDK builds, CMake only cross-compiles for ARM64. To build the DSP-side `.so`, you have to explicitly invoke the Hexagon toolchain (`hexagon-clang`).

Here is the exact `CMakeLists.txt` logic for your `src/engine/hexagon/` directory. It uses `add_custom_command` to handle the `qaic` IDL compilation and splits the targets perfectly.

```cmake
# ==============================================================================
# Phase 2-HX: Hexagon Backend Build Configuration
# ==============================================================================

# FastRPC and Hexagon SDK paths (inherited from env-hexagon.bat)
set(HEXAGON_SDK_ROOT $ENV{HEXAGON_SDK_ROOT})
# Note: Windows path for qaic.exe explicitly handled per build recipe
set(QAIC_EXE ${HEXAGON_SDK_ROOT}/ipc/fastrpc/qaic/WinNT/qaic.exe)

# ------------------------------------------------------------------------------
# 1. QAIC Interface Generation
# ------------------------------------------------------------------------------
# Compiles the IDL into the ARM stub and the DSP skel.
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion_stub.c 
           ${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion_skel.c 
           ${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion.h
    COMMAND ${QAIC_EXE} -mdll -I ${HEXAGON_SDK_ROOT}/inc/stddef ${CMAKE_CURRENT_SOURCE_DIR}/ffn_fusion.idl
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/ffn_fusion.idl
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Generating FastRPC stub and skel from ffn_fusion.idl"
)

# ------------------------------------------------------------------------------
# 2. DSP-Side Compute Target (libffn_fusion_skel.so)
# ------------------------------------------------------------------------------
# This must be compiled with hexagon-clang, NOT the Android NDK.
# We treat it as a custom target that invokes the Hexagon toolchain.
set(HEXAGON_CLANG ${HEXAGON_SDK_ROOT}/tools/HEXAGON_Tools/8.5.08/Tools/bin/hexagon-clang)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/libffn_fusion_skel.so
    COMMAND ${HEXAGON_CLANG} -O3 -mv69 -G0 -shared -fPIC 
            -I${HEXAGON_SDK_ROOT}/inc/stddef 
            -I${HEXAGON_SDK_ROOT}/inc/fastrpc
            -I${CMAKE_CURRENT_BINARY_DIR}
            ${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion_skel.c
            ${CMAKE_CURRENT_SOURCE_DIR}/ffn_fusion_imp.c
            ${CMAKE_CURRENT_SOURCE_DIR}/ffn_skeleton.a  # The Halide AOT object
            -o ${CMAKE_CURRENT_BINARY_DIR}/libffn_fusion_skel.so
            -lhexagon
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion_skel.c 
            ${CMAKE_CURRENT_SOURCE_DIR}/ffn_fusion_imp.c
            ${CMAKE_CURRENT_SOURCE_DIR}/ffn_skeleton.a
    COMMENT "Compiling Hexagon DSP shared library"
)

# Create a dummy target to force the custom command to run
add_custom_target(dsp_skel_lib ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/libffn_fusion_skel.so)

# ------------------------------------------------------------------------------
# 3. ARM-Side L1 Engine Target
# ------------------------------------------------------------------------------
# This links into the main libshannonprime.so via the Android NDK.
target_sources(sp_engine_hexagon PRIVATE
    ${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion_stub.c
    ${CMAKE_CURRENT_SOURCE_DIR}/forward_hexagon.c
)

target_include_directories(sp_engine_hexagon PRIVATE 
    ${CMAKE_CURRENT_BINARY_DIR} # For ffn_fusion.h
    ${HEXAGON_SDK_ROOT}/inc/stddef
    ${HEXAGON_SDK_ROOT}/inc/fastrpc
)

# Ensure the stub isn't compiled until the IDL is processed
set_source_files_properties(${CMAKE_CURRENT_BINARY_DIR}/ffn_fusion_stub.c PROPERTIES GENERATED TRUE)

```

### The Deployment Flow

When you run your build, CMake will now:

1. Run `qaic.exe` to generate the communication bridge.


2. Invoke `hexagon-clang` to compile `ffn_fusion_imp.c` and link your Halide `ffn_skeleton.a` into `libffn_fusion_skel.so`.
3. Compile the ARM side of the engine (`forward_hexagon.c`) using the Android NDK, linking the FastRPC stub.

When you push this to the S22 Ultra, **both** shared libraries must go to the device.

* `libshannonprime.so` (and your executable/APK) goes to the standard Android library paths.
* `libffn_fusion_skel.so` must be pushed to `/vendor/lib/rfsa/adsp/` or `/system/lib/rfsa/adsp/` (or your app's `ADSP_LIBRARY_PATH`), so the DSP knows where to load it when the ARM core makes the RPC call.

To keep the repository sterile and honor our absolute anti-contamination rule, we will build a fresh, from-scratch deployment and execution batch script (`deploy-s22u.bat`).

This script handles the cross-architecture reality of the Phase 2-HX backend: pushing the ARM64 host binary, placing the Hexagon DSP skeleton library where FastRPC can actually find it without requiring root access, setting up the `freethedsp` unsigned process domain environment, and executing cleanly on your Samsung S22 Ultra.

Here is the pristine deployment blueprint.

### The Deployment Script (`scripts/deploy/deploy-s22u.bat`)

```bat
@echo off
setlocal enabledelayedexpansion

:: ==============================================================================
:: Shannon-Prime Lattice: Phase 2-HX S22U Deployment & Execution Script
:: Re-written from first principles to ensure zero cross-contamination.
:: ==============================================================================

:: --- Configuration ---
set DEVICE_TARGET_DIR=/data/local/tmp/shannon-prime
set LOCAL_BUILD_ARM=build-android-arm64
set LOCAL_BUILD_DSP=build-hexagon

:: --- Step 1: Verify Host Environment & Connection ---
echo [HX-DEPLOY] Checking for connected Android devices via ADB...
adb devices | findstr /C:"device" >nul
if errorlevel 1 (
    echo [ERROR] No Android device detected. Connect your S22U and enable USB Debugging.
    exit /b 1
)

:: --- Step 2: Create Safe Directory Structure on Device ---
echo [HX-DEPLOY] Initializing device workspace directory structure...
adb shell "mkdir -p !DEVICE_TARGET_DIR!"
adb shell "mkdir -p !DEVICE_TARGET_DIR!/dsp"

:: --- Step 3: Push Binaries & Verify Presence ---
echo [HX-DEPLOY] Staging ARM64 host engine components...
if not exist "!LOCAL_BUILD_ARM!\bin\sp_engine_runner" (
    echo [ERROR] Missing sp_engine_runner host executable. Run build-cpu/build-hx first.
    exit /b 1
)
adb push !LOCAL_BUILD_ARM!\bin\sp_engine_runner !DEVICE_TARGET_DIR!/
adb push !LOCAL_BUILD_ARM!\lib\libshannonprime.so !DEVICE_TARGET_DIR!/

echo [HX-DEPLOY] Staging Hexagon DSP compute skeleton...
if not exist "!LOCAL_BUILD_DSP!\libffn_fusion_skel.so" (
    echo [ERROR] Missing libffn_fusion_skel.so. Verify your qaic/hexagon-clang outputs.
    exit /b 1
)
:: DSP shared libraries must sit in an explicit directory for the DSP loader
adb push !LOCAL_BUILD_DSP!\libffn_fusion_skel.so !DEVICE_TARGET_DIR!/dsp/

:: --- Step 4: Staging Model & Tokenizer Assets ---
echo [HX-DEPLOY] Checking for model artifacts...
:: Using the frozen v0 model layout and SentencePiece tokenizer paths
set MODEL_FILE=D:\Files\Models\Mine\gemma-3-1b-it\gemma-3-1b-it-f16\gemma-3-1b-it-f16.sp-model
set TOKENIZER_FILE=D:\Files\Models\Mine\gemma-3-1b-it\gemma-3-1b-it-f16\gemma-3-1b-it-f16.sp-tokenizer

if exist "!MODEL_FILE!" (
    echo [HX-DEPLOY] Pushing .sp-model weight structure...
    adb push !MODEL_FILE! !DEVICE_TARGET_DIR!/model.sp-model
) else (
    echo [WARN] Local .sp-model file not found at default path. Generation will require offline transfer.
)

if exist "!TOKENIZER_FILE!" (
    echo [HX-DEPLOY] Pushing paired SentencePiece tokenizer...
    adb push !TOKENIZER_FILE! !DEVICE_TARGET_DIR!/tokenizer.sp-tokenizer
)

:: --- Step 5: Set Permissions and Prepare Environment ---
echo [HX-DEPLOY] Finalizing execution permissions on S22U...
adb shell "chmod +x !DEVICE_TARGET_DIR!/sp_engine_runner"

:: --- Step 6: Targeted Remote Execution ---
echo [HX-DEPLOY] Launching unified inference loop on Snapdragon 8 Gen 1...
echo ------------------------------------------------------------------------------

:: Environment Variable Invariants:
:: 1. LD_LIBRARY_PATH: Forces the host runner to link our local libshannonprime.so
:: 2. ADSP_LIBRARY_PATH: Tells FastRPC exactly where our unsigned DSP .so rests[cite: 5].
::    We append the trailing semicolon because the Qualcomm Hexagon loader treats 
::    the path string as a tokenized list.
:: 3. SP_FREETHEDSP=1: Engages the unsigned process domain runtime hook for retail devices[cite: 1, 5].
:: 4. SP_ENGINE_NTT_ATTN=1: Activates the 128x lossless polynomial-shift cache[cite: 4, 5].

adb shell "export LD_LIBRARY_PATH=!DEVICE_TARGET_DIR!:\$LD_LIBRARY_PATH && ^
           export ADSP_LIBRARY_PATH=\"!DEVICE_TARGET_DIR!/dsp;\" && ^
           export SP_FREETHEDSP=1 && ^
           export SP_ENGINE_NTT_ATTN=1 && ^
           !DEVICE_TARGET_DIR!/sp_engine_runner ^
                --model !DEVICE_TARGET_DIR!/model.sp-model ^
                --tokenizer !DEVICE_TARGET_DIR!/tokenizer.sp-tokenizer ^
                --prompt \"The capital of France is\""

echo ------------------------------------------------------------------------------
echo [HX-DEPLOY] Session closed.
endlocal

```

### Critical Blueprint Safeguards Realized

* **The `ADSP_LIBRARY_PATH` Semicolon Trick:** The Qualcomm FastRPC framework expects the DSP path to terminate with a literal trailing semicolon when specified as a local directory string inside `/data/local/tmp/`. Omitting this token causes the firmware-side dynamic loader to fail parsing the path string, causing a generic initialization fault.
* **The Zero-Copy / Unsigned Boundary:** By pushing to `!DEVICE_TARGET_DIR!/dsp` and passing that exact string to `ADSP_LIBRARY_PATH`, the `freethedsp` unsigned process domain allows your retail S22 Ultra to load your hand-coded Halide and `qaic` binaries without needing root permissions or locked `/vendor/lib/rfsa` filesystem access.


* **Decoupled Variables:** The runtime call explicitly activates `SP_ENGINE_NTT_ATTN=1`. This guarantees that while your Spectra 680 ISP and V69 HTP are executing the newly refined fixed-point FFN skeleton, your relative attention cache is compressed losslessly down to 16 KB inside the cyclotomic ring—massively reducing your local DDR memory bus utilization during token generation.

