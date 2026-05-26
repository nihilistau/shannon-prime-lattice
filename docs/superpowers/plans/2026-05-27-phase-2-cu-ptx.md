# Phase 2-CU.PTX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal.** Replace generic `nvcc`-compiled CUDA C++ on the CUDA backend's lattice-specific kernels with hand-written PTX inline assembly. The Lattice is a discrete algebraic substrate in Z_q — PTX is the silicon-direct wedge that wields its 63-byte Spinor block geometry, GF(p) modular arithmetic, and INT8-coded Q8 arena as the GPU actually executes them.

**WARNING.** You are NOT writing generic FP16 GEMM kernels. Do not add softmax, temperature, top-p, or probability ratios anywhere. PTX is for speed; the math is already correct in the C scalar math-core. PTX must be FASTER, not different. Any divergence from math-core scalar output is a bug.

**Scope boundary (binding):**
- PTX REPLACES generic CUDA C++ for: Spinor block loads, GF(p) NTT butterflies, KSTE/sieve hash primitives, INT8 tensor-core Q8 matmul on the Frobenius arena.
- PTX does NOT replace cuBLAS HGEMM. cuBLAS owns the fp16-weight path.

**Repository:** `shannon-prime-system-engine` ONLY. Branch: `lat-2-cu-ptx`.

**Platform:** RTX 2060 (WDDM, sm_75 Turing, CUDA 13.2, Driver 596.21). Target sm_75 minimum through sm_90.

**Anti-contamination:** Do NOT copy CUDA code from `D:\F\shannon-prime-repos\shannon-prime-engine\` (legacy, contaminated). Re-derive from math-core scalar reference + PTX ISA docs.

**Sub-phase execution order (dependency chain):** NTT → HASH → SPINOR → MMA → PERSIST(optional)

---

## Closure Gates

- **M_PTX_1 (math gate):** Every PTX kernel produces bit-identical output vs math-core C scalar reference. Integer kernels (NTT, HASH): byte-exact equality. Float-adjacent (SPINOR, MMA): within fp16 ULP floor. Any drift = STOP.
- **M_PTX_2 (throughput):** ≥85% SOL DRAM on SPINOR; ≥8× NTT butterfly vs nvcc baseline; ≥3× MMA vs k_dequant_arena+cuBLAS SGEMM.
- **M_PTX_3 (memory honesty):** zero `cudaMalloc` on hot path. PTX operates on `sp_session` + Fix B mmap pointers only.
- **M_PTX_4 (session isolation):** PTX kernels run on the per-`sp_session` CUDA stream. No `cudaDeviceSynchronize`. Two concurrent sessions interleave without corruption.

Commit prefix: `[lat-2-cu-ptx]`. Sub-tags: `lat-phase-2-cu-ptx-ntt-closed`, `...-hash-closed`, `...-spinor-closed`, `...-mma-closed`, `...-persist-closed`. Umbrella: `lat-phase-2-cu-ptx-closed`.

---

## File Map

### Files to create
- `src/backends/cuda/ptx_ntt.cuh` — PTX Barrett butterfly for q1/q2 (§17.2)
- `src/backends/cuda/ptx_hash.cuh` — lop3.b32 + prmt.b32 primitives (§17.4)
- `src/backends/cuda/ptx_spinor.cuh` — 63-byte warp-load with hot/cold cache dispatch (§17.1)
- `src/backends/cuda/ptx_mma.cuh` — INT8 tensor-core Q8 matmul, sm_75/sm_80+ dispatch (§17.3)
- `src/backends/cuda/ptx_persist.cuh` — persistent kernel for spec-decode (§17.5, optional)
- `src/backends/cuda/ptx_validate.cu` — standalone validation binary: M_PTX_1 bit-identity for all sub-phases
- `src/backends/cuda/ptx_bench.cu` — throughput benchmark binary: M_PTX_2 Nsight Compute target
- `papers/SESSION-CLOSED-lat-2-CU-PTX.md` (lattice repo) — closure note with SASS + Nsight numbers

### Files to modify
- `src/backends/cuda/cuda_forward.cu` — wire PTX spinor loads + MMA matmul into forward path
- `CMakeLists.txt` — add `ptx_validate` + `ptx_bench` as optional CUDA executables

### Files NOT touched
- `src/backends/cuda/cuda_backend.cu` — C-ABI surface only; no kernel changes needed
- `include/sp_engine/cuda_backend.h` — L1 ABI surface; PTX is internal, not exposed
- Anything under `lib/shannon-prime-system/` (math-core is ground truth, never modified here)
- Legacy path `D:\F\shannon-prime-repos\shannon-prime-engine\` (anti-contamination)

---

## Dispatch Architecture (upfront, before any sub-phase)

**Problem:** CI has no GPU. ptx_validate + ptx_bench must compile on CI and run on dev host.

**Solution:** Compile-time dispatch via `#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750`. On the host side (CI), the PTX `.cuh` headers are included but the kernel bodies are never instantiated. The `ptx_validate` / `ptx_bench` binaries check `sp_cuda_device_count() == 0` at runtime and skip GPU tests gracefully with `SKIP (no GPU device)` output.

Each `.cuh` header follows this pattern:

```c
// In ptx_ntt.cuh — example dispatch guard:
#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750
__device__ __forceinline__ uint32_t ptx_barrett_mul_q1(uint32_t a, uint32_t b) {
    // ... PTX asm blocks ...
}
#else
// sm_70- or host-side stub: C++ fallback (slower, same math)
__host__ __device__ __forceinline__ uint32_t ptx_barrett_mul_q1(uint32_t a, uint32_t b) {
    uint64_t x = (uint64_t)a * (uint64_t)b;
    // Barrett in C — matches ntt_crt.c reference exactly
    return (uint32_t)barrett_reduce_c(x, SP_NTT_Q1, MU_Q1);
}
#endif
```

This means `ptx_validate.cu` on CI (no GPU) links and runs the C++ fallback path, which trivially matches the scalar reference. Real PTX coverage requires a GPU device.

---

## Task 0: CMake integration and ptx_validate skeleton

**Files:**
- Modify: `CMakeLists.txt` (add two optional CUDA executables)
- Create: `src/backends/cuda/ptx_validate.cu` (skeleton that compiles clean, prints SKIP on no-GPU)
- Create: `src/backends/cuda/ptx_bench.cu` (skeleton)

### Step 0.1: Add ptx_validate + ptx_bench to CMakeLists.txt

In `CMakeLists.txt`, after the existing `SP_ENGINE_WITH_CUDA` block, add:

```cmake
if(SP_ENGINE_WITH_CUDA)
    # ptx_validate — M_PTX_1 bit-identity test for all PTX sub-phases
    add_executable(ptx_validate src/backends/cuda/ptx_validate.cu)
    target_link_libraries(ptx_validate PRIVATE shannon-prime-engine ${CUDA_LIBRARIES})
    target_include_directories(ptx_validate PRIVATE
        include
        lib/shannon-prime-system/include
        src/backends/cuda
    )
    set_target_properties(ptx_validate PROPERTIES
        CUDA_ARCHITECTURES "75;80;86;90"
    )

    # ptx_bench — M_PTX_2 throughput target (Nsight Compute)
    add_executable(ptx_bench src/backends/cuda/ptx_bench.cu)
    target_link_libraries(ptx_bench PRIVATE shannon-prime-engine ${CUDA_LIBRARIES})
    target_include_directories(ptx_bench PRIVATE
        include
        lib/shannon-prime-system/include
        src/backends/cuda
    )
    set_target_properties(ptx_bench PROPERTIES
        CUDA_ARCHITECTURES "75;80;86;90"
    )
endif()
```

### Step 0.2: Write ptx_validate.cu skeleton

Create `src/backends/cuda/ptx_validate.cu`:

```cuda
/*
 * ptx_validate.cu — M_PTX_1 bit-identity validation for Phase 2-CU.PTX sub-phases.
 * Compares PTX kernel output vs math-core C scalar reference.
 * Usage: ./ptx_validate [ntt|hash|spinor|mma|all]
 * On no-GPU host: prints SKIP for each GPU gate.
 */
#include <cstdio>
#include <cstdint>
#include <cassert>
#include "sp_engine/cuda_backend.h"

/* sub-phase headers — added progressively per task */
/* #include "ptx_ntt.cuh"    */
/* #include "ptx_hash.cuh"   */
/* #include "ptx_spinor.cuh" */
/* #include "ptx_mma.cuh"    */

static int g_dev = -1;

static bool gpu_available() {
    int n = 0;
    cudaGetDeviceCount(&n);
    if (n == 0) return false;
    cudaDeviceProp p;
    cudaGetDeviceProperties(&p, 0);
    if (p.major < 7 || (p.major == 7 && p.minor < 5)) {
        fprintf(stderr, "ptx_validate: sm_%d%d < sm_75, PTX gates require sm_75+\n",
                p.major, p.minor);
        return false;
    }
    g_dev = 0;
    return true;
}

int main(int argc, char **argv) {
    const char *filter = (argc > 1) ? argv[1] : "all";
    bool gpu = gpu_available();

    printf("ptx_validate: GPU=%s filter=%s\n", gpu ? "YES" : "NO (SKIP)", filter);

    /* NTT gate — Task 1 */
    if (!strcmp(filter,"ntt") || !strcmp(filter,"all")) {
        if (!gpu) { printf("M_PTX_1 NTT: SKIP\n"); }
        else       { printf("M_PTX_1 NTT: [not yet implemented]\n"); }
    }

    /* HASH gate — Task 2 */
    if (!strcmp(filter,"hash") || !strcmp(filter,"all")) {
        if (!gpu) { printf("M_PTX_1 HASH: SKIP\n"); }
        else       { printf("M_PTX_1 HASH: [not yet implemented]\n"); }
    }

    /* SPINOR gate — Task 3 */
    if (!strcmp(filter,"spinor") || !strcmp(filter,"all")) {
        if (!gpu) { printf("M_PTX_1 SPINOR: SKIP\n"); }
        else       { printf("M_PTX_1 SPINOR: [not yet implemented]\n"); }
    }

    /* MMA gate — Task 4 */
    if (!strcmp(filter,"mma") || !strcmp(filter,"all")) {
        if (!gpu) { printf("M_PTX_1 MMA: SKIP\n"); }
        else       { printf("M_PTX_1 MMA: [not yet implemented]\n"); }
    }

    printf("ptx_validate: done\n");
    return 0;
}
```

### Step 0.3: Write ptx_bench.cu skeleton

Create `src/backends/cuda/ptx_bench.cu` with same structure as ptx_validate.cu but printing throughput numbers. Fill in per task.

### Step 0.4: Build skeleton

```bash
cd D:\F\shannon-prime-repos\shannon-prime-system-engine
cmake -B build-ptx -G Ninja -DSP_ENGINE_WITH_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-ptx --target ptx_validate ptx_bench 2>&1
```

Expected: compiles clean. Run:
```bash
./build-ptx/ptx_validate.exe all
```
Expected: `GPU=YES filter=all` (on dev host with RTX 2060) then SKIP/not-yet-implemented for each gate.

### Step 0.5: Commit

```bash
git add CMakeLists.txt src/backends/cuda/ptx_validate.cu src/backends/cuda/ptx_bench.cu
git commit -m "[lat-2-cu-ptx] Task 0: CMake integration + ptx_validate/ptx_bench skeletons"
```

---

## Task 1: NTT PTX — GF(p) Barrett butterfly (§17.2)

**Math-core reference:** `lib/shannon-prime-system/core/ntt_crt/ntt_crt.c`

Critical Barrett implementation to match **byte-for-byte** on integer kernels:

```c
/* Q_BITS = 30 */
static inline uint64_t barrett_reduce(uint64_t x, uint64_t q, uint64_t mu) {
    uint64_t qhat = ((x >> (Q_BITS - 1u)) * mu) >> (Q_BITS + 1u);
    uint64_t r = x - qhat * q;
    if (r >= q) r -= q;
    if (r >= q) r -= q;
    return r;
}
static inline uint32_t modmul(uint32_t a, uint32_t b, uint32_t q, uint64_t mu) {
    uint64_t x = (uint64_t)a * (uint64_t)b;  /* < 2^60 */
    return (uint32_t)barrett_reduce(x, (uint64_t)q, mu);
}
```

Frozen primes and mu constants (from ntt_crt.h + math):

```c
#define SP_NTT_Q1   1073738753u  /* 30-bit Proth: 2^20 * 1023 + 1 */
#define SP_NTT_Q2   1073732609u  /* 30-bit Proth: 2^20 * 1023 - ... */
/* mu = floor(2^60 / q) — precomputed at compile time */
#define MU_Q1 ((uint64_t)1073753089ULL)   /* floor(2^60 / 1073738753) */
#define MU_Q2 ((uint64_t)1073759233ULL)   /* floor(2^60 / 1073732609) */
```

**PTX translation strategy:**

`mad.wide.u32 %rd_prod, %r_a, %r_b, 0` → exact 64-bit product in one instruction.
`shf.r.wrap.b32` + carry manipulation → Barrett shift `>> Q_BITS+1` on the high 32 bits.

**Target:** ~4 cycle butterfly vs ~40 cycle nvcc `%` operator.

**Files to create:** `src/backends/cuda/ptx_ntt.cuh`

### Step 1.1: Write ptx_ntt.cuh

Create `src/backends/cuda/ptx_ntt.cuh`:

```cuda
/*
 * ptx_ntt.cuh — PTX GF(p) Barrett butterfly for Shannon-Prime NTT.
 *
 * Frozen primes: q1=1073738753, q2=1073732609 (30-bit Proth primes).
 * Each must bit-match lib/shannon-prime-system/core/ntt_crt/ntt_crt.c::modmul().
 *
 * PTX strategy:
 *   1. mad.wide.u32: exact 64-bit product a*b in one cycle (no implicit upcast overhead)
 *   2. Barrett: qhat = ((x >> 29) * mu) >> 31, all uint64 (two 32-bit halves via shf.r)
 *   3. r = x - qhat*q; two conditional subtractions (at most 2, per Barrett bound)
 *
 * No 128-bit types. No __int128. No division. Pure Z_q.
 */
#pragma once
#include <cstdint>

/* mu = floor(2^60 / q) — matches ntt_crt.c Q_BITS=30 Barrett */
#define PTX_NTT_Q1  1073738753u
#define PTX_NTT_Q2  1073732609u
#define PTX_MU_Q1   1073753089ULL
#define PTX_MU_Q2   1073759233ULL

/* ── C reference (scalar fallback + host-side) ─────────────────────────── */

__host__ __device__ __forceinline__
uint32_t barrett_reduce32_ref(uint64_t x, uint32_t q, uint64_t mu) {
    uint64_t qhat = ((x >> 29u) * mu) >> 31u;
    uint64_t r    = x - qhat * (uint64_t)q;
    if (r >= q) r -= q;
    if (r >= q) r -= q;
    return (uint32_t)r;
}

__host__ __device__ __forceinline__
uint32_t modmul_ref_q1(uint32_t a, uint32_t b) {
    return barrett_reduce32_ref((uint64_t)a * (uint64_t)b, PTX_NTT_Q1, PTX_MU_Q1);
}
__host__ __device__ __forceinline__
uint32_t modmul_ref_q2(uint32_t a, uint32_t b) {
    return barrett_reduce32_ref((uint64_t)a * (uint64_t)b, PTX_NTT_Q2, PTX_MU_Q2);
}

/* ── PTX Barrett (device, sm_75+) ────────────────────────────────────────── */

#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750

/*
 * ptx_modmul_q1: a * b mod q1 via PTX inline asm.
 *
 * PTX registers used:
 *   lo, hi = 64-bit product of a,b (mad.wide.u32 packs into two 32-bit regs)
 *   mu_lo, mu_hi = compile-time immediate split of MU_Q1
 *
 * Barrett step-by-step:
 *   x       = a*b                  (< 2^60, fits 64-bit)
 *   x_shr29 = x >> 29              (x_shr29 < 2^31 after the shift)
 *   q_hat   = x_shr29 * mu >> 31  (q_hat approximates floor(x/q))
 *   r       = x - q_hat * q       (r < 2q)
 *   if r >= q: r -= q             (at most twice)
 */
__device__ __forceinline__
uint32_t ptx_modmul_q1(uint32_t a, uint32_t b) {
    uint32_t lo, hi;   /* 64-bit product split into two 32-bit halves */
    uint32_t sh_lo, sh_hi;  /* x >> 29 (64-bit right shift) */
    uint32_t mlo, mhi;  /* x_shr29 * mu_q1 (64-bit product) */
    uint32_t qhat;
    uint32_t rlo, rhi;
    uint32_t qlo, qhi;
    uint32_t res;

    asm volatile (
        /* Step 1: 64-bit product x = a*b via mad.wide.u32 */
        "mul.wide.u32  %0, %8, %9;\n\t"  /* lo:hi = a*b (64-bit, lo is bits[31:0]) */
        /* NOTE: PTX mad.wide packs result into two adjacent u32 regs.
         * We use mul.wide.u32 then extract hi via shf.r */
        : "=r"(lo)
        : "r"(a), "r"(b)
    );
    /* Extract high 32 bits via funnel-shift */
    asm volatile (
        "mul.hi.u32  %0, %1, %2;\n\t"
        : "=r"(hi) : "r"(a), "r"(b)
    );

    /* Step 2: x >> 29 — 64-bit right shift of (hi:lo) by 29 */
    asm volatile (
        "shf.r.wrap.b32  %0, %1, %2, 29;\n\t"   /* sh_lo = bits [60:29] of x */
        "shr.u32         %3, %2, 29;\n\t"         /* sh_hi = hi >> 29 (bits [63:61], should be ~0) */
        : "=r"(sh_lo), "=r"(sh_hi)
        : "r"(lo), "r"(hi)
    );

    /* Step 3: sh * mu_q1 (64-bit). sh < 2^31, mu < 2^31 => product < 2^62 */
    asm volatile (
        "mul.lo.u32   %0, %4, %5;\n\t"    /* mlo = sh_lo * mu_q1_lo */
        "mul.hi.u32   %1, %4, %5;\n\t"    /* mhi = mulhi(sh_lo, mu_q1_lo) */
        "mad.lo.cc.u32 %0, %4, 0, %0;\n\t" /* placeholder — actual mul.wide below */
        : "=r"(mlo), "=r"(mhi)
        : "r"(sh_lo), "r"((uint32_t)(PTX_MU_Q1 & 0xFFFFFFFFu))
    );
    /* Use mul.wide for exact 64-bit: sh_lo * mu_q1 */
    asm volatile (
        "mul.wide.u32   %0, %2, %3;\n\t"
        : "=r"(mlo), "=r"(mhi)
        : "r"(sh_lo), "r"((uint32_t)PTX_MU_Q1)
    );
    /* Hmm: mul.wide.u32 expands to 64-bit but PTX doesn't natively give two-reg output
     * in a single instruction without paired registers. Use .f2h trick or just do:
     *   qhat = (mlo:mhi >> 31)  i.e. extract bits [62:31] */
    asm volatile (
        "shf.r.wrap.b32  %0, %1, %2, 31;\n\t"
        : "=r"(qhat) : "r"(mlo), "r"(mhi)
    );

    /* Step 4: r = x - qhat * q1 */
    asm volatile (
        "mul.lo.u32  %0, %2, %3;\n\t"      /* qlo = qhat * q1 (lo) */
        "mul.hi.u32  %1, %2, %3;\n\t"      /* qhi = mulhi(qhat,q1) — should be 0 */
        : "=r"(qlo), "=r"(qhi) : "r"(qhat), "r"(PTX_NTT_Q1)
    );
    asm volatile (
        "sub.u32  %0, %2, %3;\n\t"
        : "=r"(rlo) : "r"(lo), "r"(qlo)
    );
    /* rhi = hi - qhi - borrow: since x < 2^60 and qhat*q <= x + q, rlo suffices */

    /* Step 5: two conditional subtractions (Barrett bound) */
    asm volatile (
        "setp.ge.u32  %%p1, %1, %2;\n\t"
        "@%%p1 sub.u32 %0, %1, %2;\n\t"
        "setp.ge.u32  %%p2, %0, %2;\n\t"
        "@%%p2 sub.u32 %0, %0, %2;\n\t"
        : "=r"(res) : "r"(rlo), "r"(PTX_NTT_Q1)
    );

    return res;
}

/*
 * ptx_modmul_q2: same as above for q2=1073732609.
 * Identical structure — separate function to keep mu constant inlined.
 */
__device__ __forceinline__
uint32_t ptx_modmul_q2(uint32_t a, uint32_t b) {
    uint32_t lo, hi, sh_lo, sh_hi, mlo, mhi, qhat, qlo, rlo, res;

    asm volatile ("mul.lo.u32  %0, %2, %3;\n\t" "mul.hi.u32  %1, %2, %3;\n\t"
        : "=r"(lo), "=r"(hi) : "r"(a), "r"(b));
    asm volatile ("shf.r.wrap.b32  %0, %1, %2, 29;\n\t" "shr.u32  %3, %2, 29;\n\t"
        : "=r"(sh_lo), "=r"(sh_hi) : "r"(lo), "r"(hi));
    asm volatile ("mul.wide.u32  %0, %2, %3;\n\t" /* 64-bit sh*mu */
        : "=r"(mlo), "=r"(mhi)
        : "r"(sh_lo), "r"((uint32_t)PTX_MU_Q2));
    asm volatile ("shf.r.wrap.b32  %0, %1, %2, 31;\n\t"
        : "=r"(qhat) : "r"(mlo), "r"(mhi));
    asm volatile ("mul.lo.u32  %0, %1, %2;\n\t" : "=r"(qlo) : "r"(qhat), "r"(PTX_NTT_Q2));
    asm volatile ("sub.u32  %0, %1, %2;\n\t" : "=r"(rlo) : "r"(lo), "r"(qlo));
    asm volatile (
        "setp.ge.u32  %%p1, %1, %2;\n\t"
        "@%%p1 sub.u32 %0, %1, %2;\n\t"
        "setp.ge.u32  %%p2, %0, %2;\n\t"
        "@%%p2 sub.u32 %0, %0, %2;\n\t"
        : "=r"(res) : "r"(rlo), "r"(PTX_NTT_Q2));
    return res;
}

/* NTT Cooley-Tukey butterfly: (a, b) -> (a + w*b, a - w*b) mod q */
__device__ __forceinline__
void ptx_butterfly_q1(uint32_t *a, uint32_t *b, uint32_t w) {
    uint32_t wb = ptx_modmul_q1(*b, w);
    uint32_t t  = *a + wb;
    if (t >= PTX_NTT_Q1) t -= PTX_NTT_Q1;
    uint32_t u  = *a + PTX_NTT_Q1 - wb;
    if (u >= PTX_NTT_Q1) u -= PTX_NTT_Q1;
    *a = t; *b = u;
}

__device__ __forceinline__
void ptx_butterfly_q2(uint32_t *a, uint32_t *b, uint32_t w) {
    uint32_t wb = ptx_modmul_q2(*b, w);
    uint32_t t  = *a + wb;
    if (t >= PTX_NTT_Q2) t -= PTX_NTT_Q2;
    uint32_t u  = *a + PTX_NTT_Q2 - wb;
    if (u >= PTX_NTT_Q2) u -= PTX_NTT_Q2;
    *a = t; *b = u;
}

#else  /* sm_70- or host: C++ fallback — same math, no PTX */

__host__ __device__ __forceinline__ uint32_t ptx_modmul_q1(uint32_t a, uint32_t b) {
    return modmul_ref_q1(a, b);
}
__host__ __device__ __forceinline__ uint32_t ptx_modmul_q2(uint32_t a, uint32_t b) {
    return modmul_ref_q2(a, b);
}
__host__ __device__ __forceinline__
void ptx_butterfly_q1(uint32_t *a, uint32_t *b, uint32_t w) {
    uint32_t wb = modmul_ref_q1(*b, w); uint32_t t = *a + wb;
    if (t >= PTX_NTT_Q1) t -= PTX_NTT_Q1;
    uint32_t u = *a + PTX_NTT_Q1 - wb;
    if (u >= PTX_NTT_Q1) u -= PTX_NTT_Q1;
    *a = t; *b = u;
}
__host__ __device__ __forceinline__
void ptx_butterfly_q2(uint32_t *a, uint32_t *b, uint32_t w) {
    uint32_t wb = modmul_ref_q2(*b, w); uint32_t t = *a + wb;
    if (t >= PTX_NTT_Q2) t -= PTX_NTT_Q2;
    uint32_t u = *a + PTX_NTT_Q2 - wb;
    if (u >= PTX_NTT_Q2) u -= PTX_NTT_Q2;
    *a = t; *b = u;
}

#endif  /* __CUDA_ARCH__ >= 750 */
```

**IMPORTANT implementation note:** The PTX mul.wide.u32 instruction expands to a 64-bit result packed into two adjacent 32-bit registers. In PTX inline asm with nvcc, you must use separate `"=r"` output constraints for lo and hi. The pattern is:
```
asm("mul.wide.u32 {%0,%1}, %2, %3;" : "=r"(lo), "=r"(hi) : "r"(a), "r"(b));
```
This is a **paired register** output. If PTX inline asm in nvcc doesn't support the `{%0,%1}` brace syntax, fall back to `mul.lo.u32` + `mul.hi.u32` as two separate instructions — same cycle count on Turing.

The implementer **must** verify the PTX syntax compiles against nvcc's inline asm rules for sm_75. If the mul.wide paired register syntax fails, rewrite using mul.lo.u32 + mul.hi.u32 + shf.r.wrap.b32.

### Step 1.2: Add NTT gate to ptx_validate.cu

Implement `validate_ntt()` in `ptx_validate.cu`:

- Allocate two arrays `a[]` and `b[]` of uint32_t values in [0, q1).
- Run `modmul_ref_q1(a[i], b[i])` on CPU for each pair — this is the ground truth.
- Launch a GPU kernel that runs `ptx_modmul_q1(a[i], b[i])` via the PTX path.
- Compare output arrays bit-for-bit (uint32_t equality).
- Also test `ptx_butterfly_q1` against the scalar butterfly from ntt_crt.c.
- Test set: 1024 random pairs at several corner values (0, 1, q1-1, q1/2, random).
- Print `M_PTX_1 NTT Q1: PASS` / `FAIL (idx=N ref=X got=Y)`.
- Repeat for q2.

### Step 1.3: Add NTT bench to ptx_bench.cu

Implement `bench_ntt()`:
- Launch 1M butterfly operations in a CUDA kernel.
- Time with CUDA events.
- Print: `NTT: PTX butterflies/s = X, nvcc_baseline = Y, speedup = Z.Zx`.
- For nvcc baseline: compile a separate kernel with `__noinline__` and a `%` operator.
- Target: ≥8× speedup (M_PTX_2).

### Step 1.4: Build and run

```bash
cd D:\F\shannon-prime-repos\shannon-prime-system-engine
cmake --build build-ptx --target ptx_validate ptx_bench 2>&1
./build-ptx/ptx_validate.exe ntt
./build-ptx/ptx_bench.exe ntt
```

Expected for ptx_validate: `M_PTX_1 NTT Q1: PASS`, `M_PTX_1 NTT Q2: PASS`.
Expected for ptx_bench: `speedup = N.Nx` where N >= 8.

**If PTX inline asm syntax fails to compile:** Rewrite the Barrett using only `mul.lo.u32` + `mul.hi.u32` + `shf.r.wrap.b32` + `mad.lo.u32` — no paired register syntax. This is a known nvcc limitation with the `{}` brace form for wide output; the two-instruction form is always safe.

### Step 1.5: Capture SASS via cuobjdump

```bash
cuobjdump --dump-sass ./build-ptx/ptx_validate.exe 2>&1 | grep -A 20 "ptx_modmul_q1"
```

Save the output to `papers/SESSION-CLOSED-lat-2-CU-PTX.md` §NTT.SASS. Verify IMAD/IMUL instructions are present (not FMUL or generic integer division).

### Step 1.6: Commit

```bash
git add src/backends/cuda/ptx_ntt.cuh src/backends/cuda/ptx_validate.cu src/backends/cuda/ptx_bench.cu
git commit -m "[lat-2-cu-ptx] Task 1: ptx_ntt.cuh — PTX Barrett butterfly q1/q2, M_PTX_1 NTT gates green"
git tag lat-phase-2-cu-ptx-ntt-closed
```

---

## Task 2: HASH PTX — lop3.b32 + prmt.b32 primitives (§17.4)

**Math-core reference:** `lib/shannon-prime-system/include/sp/sp_hash.h` + the XXH3 mixing and KSTE tier-0 logic. The specific targets are the inner mixing rounds of XXH3 (XOR + multiply + rotate) and byte-extraction sequences for KSTE tree-index from Spinor blocks.

**Key PTX instructions:**
- `lop3.b32 dst, a, b, c, immLut` — any 3-input boolean in 1 cycle. Lookup table `immLut` encodes the truth table. Example: XOR(a,b) = `lop3.b32 dst, a, b, 0, 0x96` (LUT for a^b^0).
- `prmt.b32 dst, a, b, selector` — byte permute across 8 source bytes. 4-bit selector per output byte. Used for KSTE block index extraction.

**Files to create:** `src/backends/cuda/ptx_hash.cuh`

### Step 2.1: Read the scalar reference

Read `lib/shannon-prime-system/core/` for XXH3 mixing rounds and KSTE tier-0 subtract-with-borrow signature. Identify the XOR/multiply/rotate sequences that lop3 can collapse.

A typical XXH3 avalanche step:
```c
uint64_t x = acc;
x ^= (x >> 37);         // XOR with shifted self
x *= 0x165667919E3779F9ULL; // multiply
x ^= (x >> 32);
```

The XOR-with-shift step on 32-bit lanes: `(x ^ (x >> N))` is two instructions in C but maps to a single `lop3` if combined with another XOR. For the mixing round `a ^= b ^ (c >> N)`:
```
prmt: extract shifted bytes of c
lop3.b32 dst, a, b, prmt_out, 0x96  /* XOR(XOR(a,b),c) in one cycle */
```

### Step 2.2: Write ptx_hash.cuh

Create `src/backends/cuda/ptx_hash.cuh`:

```cuda
/*
 * ptx_hash.cuh — PTX lop3.b32 + prmt.b32 primitives for KSTE/XXH3.
 *
 * These are PTX-exclusive — no CUDA C++ equivalent emits lop3 directly.
 * Scalar C fallback: separate function per primitive, C equivalent.
 * Full sieve integration is Phase 5; this lands the PTX-native primitives only.
 */
#pragma once
#include <cstdint>

/* ── lop3 LUT constants for common boolean functions ─────────────────────── */
/* LUT truth table for f(a,b,c): bit i of immLut is f evaluated at (a[i],b[i],c[i]) */
#define LUT_XOR_AB_XOR_C  0x96u  /* a^b^c */
#define LUT_AND_AB_OR_C   0xE8u  /* (a&b)|c */
#define LUT_XOR_AB        0x96u  /* a^b (with c=0 source) */
#define LUT_MEDIAN3       0xE8u  /* majority(a,b,c) */

#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750

/* Three-input XOR: a ^ b ^ c in 1 cycle (replaces 2 XOR instructions) */
__device__ __forceinline__
uint32_t ptx_xor3(uint32_t a, uint32_t b, uint32_t c) {
    uint32_t r;
    asm volatile ("lop3.b32 %0, %1, %2, %3, 0x96;" : "=r"(r) : "r"(a), "r"(b), "r"(c));
    return r;
}

/* Byte permute: 4-byte selector selects bytes from {b,a} into output */
__device__ __forceinline__
uint32_t ptx_prmt(uint32_t a, uint32_t b, uint32_t selector) {
    uint32_t r;
    asm volatile ("prmt.b32 %0, %1, %2, %3;" : "=r"(r) : "r"(a), "r"(b), "r"(selector));
    return r;
}

/* KSTE tier-0 block-index extraction from packed 32-bit Spinor word.
 * Extracts 3 non-contiguous byte lanes and packs them into one 32-bit word.
 * selector = 0x03020100u extracts bytes [0,1,2,3] from a — adjust per KSTE spec. */
__device__ __forceinline__
uint32_t ptx_kste_extract(uint32_t packed_word, uint32_t selector) {
    return ptx_prmt(packed_word, 0u, selector);
}

/* XXH3 avalanche round (32-bit lane): r = (x ^ (x >> shift)) using lop3.
 * For shift=16: xor_part = x ^ (x >> 16); lop3 can't do this alone,
 * but it DOES collapse (a ^ b ^ c) into one cycle for mixing three words. */
__device__ __forceinline__
uint32_t ptx_xxh3_mix3(uint32_t a, uint32_t b, uint32_t c) {
    return ptx_xor3(a, b, c);  /* (a^b^c) in one cycle */
}

/* lop3 general: evaluates any 3-input boolean at compile-time immLut */
__device__ __forceinline__
uint32_t ptx_lop3(uint32_t a, uint32_t b, uint32_t c, uint8_t lut) {
    uint32_t r;
    /* nvcc allows 'lop3.b32' only with compile-time immediate LUT.
     * Use template specialization or inline-asm with literal constant.
     * For a runtime LUT: this would require a branch table — don't do that.
     * All call sites must use a compile-time constant for lut. */
    switch (lut) {
        case 0x96: { asm volatile ("lop3.b32 %0, %1, %2, %3, 0x96;" : "=r"(r) : "r"(a),"r"(b),"r"(c)); break; }
        case 0xE8: { asm volatile ("lop3.b32 %0, %1, %2, %3, 0xe8;" : "=r"(r) : "r"(a),"r"(b),"r"(c)); break; }
        /* Add more as needed. Unrecognized LUTs fall to C. */
        default:   {
            /* C fallback for unrecognized LUT — construct truth table manually */
            r = 0u;
            for (int i = 0; i < 32; i++) {
                int ai = (a>>i)&1, bi = (b>>i)&1, ci = (c>>i)&1;
                int bit = (lut >> (ai*4 + bi*2 + ci)) & 1;
                r |= (uint32_t)bit << i;
            }
        }
    }
    return r;
}

#else  /* host / sm_70- fallback */

__host__ __device__ __forceinline__ uint32_t ptx_xor3(uint32_t a, uint32_t b, uint32_t c) { return a^b^c; }
__host__ __device__ __forceinline__ uint32_t ptx_prmt(uint32_t a, uint32_t b, uint32_t sel) {
    /* Byte permute: C emulation */
    const uint8_t *src = (const uint8_t *)&a;
    const uint8_t *src2 = (const uint8_t *)&b;
    uint8_t out[4];
    for (int i = 0; i < 4; i++) {
        uint8_t s = (sel >> (4*i)) & 0xF;
        out[i] = (s < 4) ? src[s] : src2[s-4];
    }
    uint32_t r; __builtin_memcpy(&r, out, 4); return r;
}
__host__ __device__ __forceinline__ uint32_t ptx_kste_extract(uint32_t w, uint32_t sel) { return ptx_prmt(w, 0u, sel); }
__host__ __device__ __forceinline__ uint32_t ptx_xxh3_mix3(uint32_t a, uint32_t b, uint32_t c) { return a^b^c; }

#endif /* __CUDA_ARCH__ >= 750 */
```

### Step 2.3: Add HASH gate to ptx_validate.cu

Implement `validate_hash()`:
- For `ptx_xor3`: compare `ptx_xor3(a,b,c)` vs `a^b^c` on 1024 random triples. Byte-exact.
- For `ptx_prmt`: compare `ptx_prmt(a,b,sel)` vs the C emulation on 256 combinations. Byte-exact.
- For `ptx_kste_extract`: compare against the KSTE tier-0 C scalar on representative Spinor block words.
- Print `M_PTX_1 HASH: PASS` / `FAIL`.

### Step 2.4: Add HASH bench to ptx_bench.cu

Implement `bench_hash()`:
- 10M `ptx_xor3` vs 2x XOR: measure latency. Expect ~1 cycle vs ~2 cycles.
- Print cycles-per-op comparison.

### Step 2.5: Build, run, commit

```bash
cmake --build build-ptx --target ptx_validate 2>&1
./build-ptx/ptx_validate.exe hash
```
Expected: `M_PTX_1 HASH: PASS`.

```bash
git add src/backends/cuda/ptx_hash.cuh src/backends/cuda/ptx_validate.cu src/backends/cuda/ptx_bench.cu
git commit -m "[lat-2-cu-ptx] Task 2: ptx_hash.cuh — lop3.b32/prmt.b32 primitives, M_PTX_1 HASH green"
git tag lat-phase-2-cu-ptx-hash-closed
```

---

## Task 3: SPINOR PTX — 63-byte warp-load (§17.1)

**Geometry (frozen — never change sp_spinor_block_t):**
```c
typedef struct {
    uint8_t vht2_header[7];   /* norm + exponent + VHT2 basis selector */
    uint8_t mobius_body[55];  /* Mobius-reordered, packed anchor coefficients */
    uint8_t checksum;         /* CRC-8 of vht2_header || mobius_body */
} sp_spinor_block_t;          /* 63 bytes total, packed (byte 63 = SP_SPINOR_SENTINEL on-disk) */
```

**Warp packing:** 32 threads × 4 bytes = 128 bytes = 2 Spinor blocks (126 bytes) + 2 sentinel slack bytes. Two Spinors fit in one warp transaction. Cross-block bytes use `shfl.sync`.

**Cache policy dispatch (runtime, not compile-time):**
- Hot window (position > current_pos - swa_window): `ld.global.cg` (L2-cached, L1-bypassed)
- Cold tail (older history): `ld.global.cs` or `ld.global.nc` (L1+L2 bypass)
- Boundary check at kernel entry via position comparison.

**Files to create:** `src/backends/cuda/ptx_spinor.cuh`

### Step 3.1: Write ptx_spinor.cuh

Create `src/backends/cuda/ptx_spinor.cuh`:

```cuda
/*
 * ptx_spinor.cuh — PTX 63-byte Spinor warp-load with hot/cold cache dispatch.
 *
 * sp_spinor_block_t geometry: 63 bytes = 7 header + 55 body + 1 CRC.
 * 32 threads × 4 bytes = 128 bytes per warp = 2 Spinors + 2 sentinel slack.
 *
 * Cache policy:
 *   hot  (pos > cur - swa_window): ld.global.cg  (L2-cached, L1-bypassed)
 *   cold (older):                  ld.global.cs  (L1+L2 bypass, streaming)
 *
 * Usage: sp_spinor_warpload(base_ptr, block_idx, lane_id, is_hot) -> uint32_t
 * Returns the 4-byte word assigned to this lane.
 * Caller uses shfl.sync to assemble full 63-byte block.
 */
#pragma once
#include <cstdint>

#ifdef __CUDACC__

#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750

/* Hot load: ld.global.cg (L2-cached, L1-bypassed) */
__device__ __forceinline__
uint32_t ptx_ld_global_cg_u32(const void *addr) {
    uint32_t v;
    asm volatile ("ld.global.cg.u32 %0, [%1];" : "=r"(v) : "l"(addr));
    return v;
}

/* Cold load: ld.global.cs (streaming, L1+L2 bypass) */
__device__ __forceinline__
uint32_t ptx_ld_global_cs_u32(const void *addr) {
    uint32_t v;
    asm volatile ("ld.global.cs.u32 %0, [%1];" : "=r"(v) : "l"(addr));
    return v;
}

/* Cold load via non-coherent (nc) path — fallback to cs if nc not available */
__device__ __forceinline__
uint32_t ptx_ld_global_nc_u32(const void *addr) {
    uint32_t v;
    asm volatile ("ld.global.nc.u32 %0, [%1];" : "=r"(v) : "l"(addr));
    return v;
}

/*
 * sp_spinor_warpload: load one 4-byte word per lane from a packed array of
 * 63-byte Spinor blocks. Two Spinors fit per 128-byte warp transaction.
 *
 * @param base: base address of Spinor array (must be 64-byte aligned)
 * @param block_idx: which Spinor block this warp is loading
 * @param lane: threadIdx.x & 31 (lane within warp, 0..31)
 * @param is_hot: 1=hot window (cg), 0=cold (cs)
 *
 * Returns: 4-byte word for this lane. Cross-Spinor bytes at positions 63-127
 * use shfl.sync in the caller to exchange between even/odd lane pairs.
 *
 * Layout: block_idx=0 occupies bytes [0..62], block_idx=1 occupies [63..125],
 * two sentinel bytes [126..127] are discarded. Each lane gets 4 contiguous bytes
 * starting at offset = (block_idx * 63 / 4) * 4 + lane * 4, approximately.
 * The exact lane-to-byte mapping requires the caller to handle cross-block splits.
 */
__device__ __forceinline__
uint32_t sp_spinor_warpload(const uint32_t *base, uint32_t block_idx,
                             int lane, int is_hot) {
    /* Each 63-byte block, when aligned to 4-byte boundary, takes 16 words (64 bytes).
     * block_idx=0: words [0..15], bytes [0..63] — bytes 63 is sentinel slack.
     * block_idx=1: words [16..31], bytes [64..127] — byte 63+1 = real data, etc.
     *
     * For simplicity: pack two Spinors into a 128-byte warp-stride window.
     * Each lane loads its word; caller handles the 4 "overflow" bytes at boundary.
     */
    const uint32_t *ptr = base + ((size_t)block_idx * 16) + lane;

    if (is_hot) {
        return ptx_ld_global_cg_u32(ptr);
    } else {
        return ptx_ld_global_cs_u32(ptr);
    }
}

/* v4.u32 load: loads 4 contiguous uint32_t words using vector PTX instruction.
 * More efficient than 4 scalar ld.global when stride allows coalescing. */
__device__ __forceinline__
void ptx_ld4_cg(const uint32_t *addr, uint32_t *v0, uint32_t *v1, uint32_t *v2, uint32_t *v3) {
    asm volatile (
        "ld.global.cg.v4.u32 {%0,%1,%2,%3}, [%4];"
        : "=r"(*v0), "=r"(*v1), "=r"(*v2), "=r"(*v3)
        : "l"(addr)
    );
}

__device__ __forceinline__
void ptx_ld4_cs(const uint32_t *addr, uint32_t *v0, uint32_t *v1, uint32_t *v2, uint32_t *v3) {
    asm volatile (
        "ld.global.cs.v4.u32 {%0,%1,%2,%3}, [%4];"
        : "=r"(*v0), "=r"(*v1), "=r"(*v2), "=r"(*v3)
        : "l"(addr)
    );
}

#else  /* sm_70- or host fallback */

__host__ __device__ __forceinline__
uint32_t ptx_ld_global_cg_u32(const void *addr) {
    uint32_t v; __builtin_memcpy(&v, addr, 4); return v;
}
__host__ __device__ __forceinline__
uint32_t ptx_ld_global_cs_u32(const void *addr) {
    uint32_t v; __builtin_memcpy(&v, addr, 4); return v;
}
__host__ __device__ __forceinline__
uint32_t ptx_ld_global_nc_u32(const void *addr) {
    uint32_t v; __builtin_memcpy(&v, addr, 4); return v;
}
__device__ __forceinline__
uint32_t sp_spinor_warpload(const uint32_t *base, uint32_t block_idx, int lane, int is_hot) {
    return *(base + (size_t)block_idx * 16 + lane);
}

#endif /* __CUDA_ARCH__ >= 750 */
#endif /* __CUDACC__ */
```

### Step 3.2: Wire into cuda_forward.cu

In `cuda_forward.cu`, the attention kernel (`k_attn` or `k_attn_ntt`) currently reads KV cache data. Replace the raw `float *` or `uint8_t *` loads for Spinor KV blocks with `sp_spinor_warpload` + a position-vs-swa_window check:

```cuda
// Before (generic load):
float kv_val = kv_cache[offset];

// After (PTX dispatch):
int is_hot = (kv_block_pos > (int)current_pos - SWA_WINDOW);
uint32_t raw = sp_spinor_warpload(
    (const uint32_t *)spinor_base,
    kv_block_idx, lane, is_hot
);
// decode raw uint32_t to float via Frobenius scale (unchanged math)
```

The SWA window constant comes from `sp_arch_info.swa_window` (set per arch, 0 if full attention).

### Step 3.3: Add SPINOR gate to ptx_validate.cu

- Allocate a Spinor array on device (packed 63-byte blocks, aligned to 64 bytes).
- Load each block with `sp_spinor_warpload` PTX path.
- Load with C++ `memcpy` scalar path on same data.
- Compare all bytes. Byte-exact (SPINOR carries integers, no float rounding).
- Print `M_PTX_1 SPINOR: PASS` / `FAIL`.

### Step 3.4: Add SPINOR bench to ptx_bench.cu

- Benchmark 10K Spinor loads (hot path) vs 10K cold (cs).
- Compute effective DRAM bandwidth.
- Target: ≥85% SOL DRAM (M_PTX_2).
- Use Nsight Compute `ncu --metrics l1tex__t_bytes_pipe_lsu_mem_global_op_ld.sum.per_second` to verify.

### Step 3.5: Build, run, commit

```bash
cmake --build build-ptx --target ptx_validate 2>&1
./build-ptx/ptx_validate.exe spinor
```
Expected: `M_PTX_1 SPINOR: PASS` + bandwidth number.

```bash
git add src/backends/cuda/ptx_spinor.cuh src/backends/cuda/cuda_forward.cu src/backends/cuda/ptx_validate.cu src/backends/cuda/ptx_bench.cu
git commit -m "[lat-2-cu-ptx] Task 3: ptx_spinor.cuh — 63-byte warp-load hot/cold dispatch, M_PTX_1+M_PTX_2 SPINOR green"
git tag lat-phase-2-cu-ptx-spinor-closed
```

---

## Task 4: MMA PTX — INT8 tensor-core Q8 matmul (§17.3)

**The core deliverable.** RTX 2060 (sm_75 Turing) has INT8 tensor cores accessible via `mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32`. nvcc won't emit these for Q8-packed data.

**Existing baseline (what MMA replaces):**
In `cuda_forward.cu`, the current path is:
1. `k_dequant_arena`: decode Q8 codes (int8) to f32 scratch buffer
2. cuBLAS SGEMM on the f32 scratch

New path `sp_frob_matmul_q8_mma`:
1. Load Q8 codes directly from mmap'd arena into shared memory tiles (no decode to f32)
2. `mma.sync` accumulates int8×int8→int32 in 1/4 the cycles
3. Post-multiply: apply per-row Frobenius scale `(s32_acc * fp32_scale)` → fp16 output
4. No intermediate f32 scratch buffer (M_PTX_3 satisfied)

**sm_75 vs sm_80+ dispatch:**
- sm_80+ (Ampere): `cp.async.cg.shared.global` for async shared memory prefetch
- sm_75 (Turing): `ld.global.cg` + synchronous copy to shared

**MMA instruction format:**
```
mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32
    {d0,d1,d2,d3},     // D: 4 s32 accumulators (m8n8)
    {a0,a1},           // A: 2 s32 packing 8 s8 values (m8k16, row-major)
    {b0,b1},           // B: 2 s32 packing 8 s8 values (k16n8, col-major)
    {c0,c1,c2,c3}      // C: 4 s32 accumulate-in
```

Each warp computes an 8×8 tile. For an M×K × K×N matmul with K=head_dim (64):
- Tile the output into 8×8 blocks.
- Each warp handles one 8×8 output tile.
- Loop over K in steps of 16 (one mma.sync per 16 elements of K).

**Files to create:** `src/backends/cuda/ptx_mma.cuh`

### Step 4.1: Write ptx_mma.cuh

Create `src/backends/cuda/ptx_mma.cuh`:

```cuda
/*
 * ptx_mma.cuh — INT8 tensor-core Q8 matmul for Shannon-Prime Frobenius arena.
 *
 * Replaces: k_dequant_arena (int8→f32 decode) + cuBLAS SGEMM (f32 matmul).
 * New path:  mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 (direct int8 TC)
 *            + per-row Frobenius scale applied post-accumulation.
 *
 * M_PTX_3: No cudaMalloc on hot path. Shared memory tiles are stack-allocated
 *           (__shared__ arrays inside the kernel). Input from Fix-B mmap pointers.
 * M_PTX_4: All kernels must be launched on the per-sp_session CUDA stream.
 *
 * Tile size: m8n8k16 warp tile. Grid/block tiling wraps around it.
 *
 * sm_75 (RTX 2060): use ld.global.cg + synchronous smem copy.
 * sm_80+ (A100/etc): use cp.async.cg.shared.global for async prefetch.
 */
#pragma once
#include <cstdint>

#ifdef __CUDACC__

/* ── Shared memory tile dimensions ─────────────────────────────────────── */
/* Warp tile: 8×8 output, 8×16 A tile, 16×8 B tile */
#define MMA_M  8
#define MMA_N  8
#define MMA_K  16

#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750

/* Load 8×16 A tile (int8) from global memory into shared memory — sm_75 path */
__device__ __forceinline__
void ptx_load_a_tile_sm75(const int8_t *src, int8_t *smem,
                            int m_off, int k_off, int M, int K) {
    /* 8×16 = 128 bytes; warp has 32 lanes; 4 lanes per row */
    int lane = threadIdx.x & 31;
    int row  = lane / 4;   /* 0..7 */
    int col  = (lane % 4) * 4; /* 0,4,8,12 */
    if (m_off + row < M && k_off + col < K) {
        /* ld.global.cg.u32: 4 int8 packed as uint32 */
        uint32_t v;
        asm volatile ("ld.global.cg.u32 %0, [%1];"
            : "=r"(v) : "l"(src + (m_off + row)*K + k_off + col));
        *(uint32_t *)(smem + row*16 + col) = v;
    }
}

/* Load 16×8 B tile (int8) — col-major layout expected by mma */
__device__ __forceinline__
void ptx_load_b_tile_sm75(const int8_t *src, int8_t *smem,
                            int k_off, int n_off, int K, int N) {
    int lane = threadIdx.x & 31;
    int row  = lane / 4;
    int col  = (lane % 4) * 4;
    if (k_off + row < K && n_off + col < N) {
        uint32_t v;
        asm volatile ("ld.global.cg.u32 %0, [%1];"
            : "=r"(v) : "l"(src + (k_off + row)*N + n_off + col));
        *(uint32_t *)(smem + row*8 + col) = v;
    }
}

#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 800
/* sm_80+: async load via cp.async */
__device__ __forceinline__
void ptx_async_copy_u32(void *smem_dst, const void *gmem_src) {
    asm volatile (
        "cp.async.cg.shared.global [%0], [%1], 4;"
        : : "r"(__cvta_generic_to_shared(smem_dst)), "l"(gmem_src)
    );
}
__device__ __forceinline__
void ptx_async_commit() { asm volatile ("cp.async.commit_group;"); }
__device__ __forceinline__
void ptx_async_wait_all() { asm volatile ("cp.async.wait_all;"); }
#endif /* sm_80+ */

/*
 * ptx_mma_m8n8k16_s8s8s32:
 * Computes D += A * B where A is 8×16 s8, B is 16×8 s8, D is 8×8 s32.
 * All values in registers (called with tiles already loaded to smem).
 *
 * PTX register layout:
 *   A fragment: 2 uint32 (8 int8 packed per reg, 16 total = 8×16 matrix)
 *   B fragment: 2 uint32 (16 int8 packed, 16×8 col-major)
 *   C/D:        4 int32 (8×8 output, each thread holds 2×2 sub-tile)
 */
__device__ __forceinline__
void ptx_mma_m8n8k16_s8s8s32(
    uint32_t a0, uint32_t a1,   /* A fragment: 2×4 int8 → 8 values */
    uint32_t b0, uint32_t b1,   /* B fragment: 2×4 int8 → 8 values */
    int32_t &d0, int32_t &d1, int32_t &d2, int32_t &d3  /* D accumulator */
) {
    asm volatile (
        "mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 "
        "{%0,%1,%2,%3}, {%4,%5}, {%6,%7}, {%0,%1,%2,%3};"
        : "+r"(d0), "+r"(d1), "+r"(d2), "+r"(d3)
        : "r"(a0), "r"(a1), "r"(b0), "r"(b1)
    );
}

/*
 * sp_frob_matmul_q8_mma_kernel:
 * Full Q8 Frobenius matmul with INT8 tensor cores.
 *
 * A: (M × K) int8 codes from mmap arena (row-major)
 * B: (K × N) int8 codes from mmap arena (col-major for mma)
 * scale_a: (M,) fp32 per-row Frobenius scale for A
 * scale_b: (N,) fp32 per-row Frobenius scale for B (applied per output col)
 * C: (M × N) fp16 output (activations)
 *
 * Each warp block handles one 8×8 output tile.
 * Grid: (N/8, M/8), Block: (32, 1) — one warp per tile.
 *
 * M_PTX_3: smem tiles are __shared__ arrays, no cudaMalloc.
 * M_PTX_4: caller must launch on per-sp_session stream.
 */
__global__
void sp_frob_matmul_q8_mma_kernel(
    const int8_t *A, const int8_t *B,
    const float  *scale_a, const float *scale_b,
    __half       *C,
    int M, int K, int N
) {
    const int warp_m = blockIdx.y;  /* which 8-row tile */
    const int warp_n = blockIdx.x;  /* which 8-col tile */
    const int lane   = threadIdx.x & 31;

    /* D accumulator: 4 int32, one warp covers 8×8 output */
    int32_t d0=0, d1=0, d2=0, d3=0;

    /* Shared memory tiles — no cudaMalloc (M_PTX_3) */
    __shared__ int8_t smem_a[MMA_M * MMA_K];  /* 128 bytes */
    __shared__ int8_t smem_b[MMA_K * MMA_N];  /* 128 bytes */

    /* Loop over K tiles of size 16 */
    for (int k = 0; k < K; k += MMA_K) {
        /* Load A tile (8×16) and B tile (16×8) into smem */
        ptx_load_a_tile_sm75(A, smem_a, warp_m*MMA_M, k, M, K);
        ptx_load_b_tile_sm75(B, smem_b, k, warp_n*MMA_N, K, N);
        __syncwarp();

        /* Pack A and B fragments into registers (2 uint32 each) */
        /* Each lane loads its 8-byte portion of the 8×16 A tile */
        uint32_t a0_frag, a1_frag, b0_frag, b1_frag;
        /* Fragment packing: per PTX mma.m8n8k16 register layout, */
        /* each lane holds 2 elements of A (row offset: lane/4) and B. */
        /* This requires precise lane-to-matrix-element mapping per PTX spec. */
        /* See: https://docs.nvidia.com/cuda/parallel-thread-execution/#warp-level-matrix-fragment-mma-m8n8k16 */
        int a_row = lane / 4;
        int a_col = (lane % 4) * 4;
        __builtin_memcpy(&a0_frag, smem_a + a_row*MMA_K + a_col, 4);
        __builtin_memcpy(&a1_frag, smem_a + a_row*MMA_K + a_col + 8, 4);

        int b_col = (lane % 4) * 2;
        int b_row = (lane / 4) * 2;
        __builtin_memcpy(&b0_frag, smem_b + b_row*MMA_N + b_col, 4);
        __builtin_memcpy(&b1_frag, smem_b + (b_row+8)*MMA_N + b_col, 4);

        ptx_mma_m8n8k16_s8s8s32(a0_frag, a1_frag, b0_frag, b1_frag,
                                  d0, d1, d2, d3);
        __syncwarp();
    }

    /* Post-accumulation: apply Frobenius scales and write fp16 output */
    /* Each thread writes 2×2 output tile elements */
    int out_row0 = warp_m*MMA_M + (lane / 4);
    int out_row1 = warp_m*MMA_M + (lane / 4) + 4;
    int out_col0 = warp_n*MMA_N + (lane % 4) * 2;
    int out_col1 = warp_n*MMA_N + (lane % 4) * 2 + 1;

    if (out_row0 < M && out_col0 < N) {
        float v = (float)d0 * scale_a[out_row0] * scale_b[out_col0];
        C[out_row0 * N + out_col0] = __float2half(v);
    }
    if (out_row0 < M && out_col1 < N) {
        float v = (float)d1 * scale_a[out_row0] * scale_b[out_col1];
        C[out_row0 * N + out_col1] = __float2half(v);
    }
    if (out_row1 < M && out_col0 < N) {
        float v = (float)d2 * scale_a[out_row1] * scale_b[out_col0];
        C[out_row1 * N + out_col0] = __float2half(v);
    }
    if (out_row1 < M && out_col1 < N) {
        float v = (float)d3 * scale_a[out_row1] * scale_b[out_col1];
        C[out_row1 * N + out_col1] = __float2half(v);
    }
}

/* Launcher: sp_frob_matmul_q8_mma
 * Replaces: k_dequant_arena + cuBLAS SGEMM Q8 path.
 * M_PTX_4: caller provides stream.
 */
inline void sp_frob_matmul_q8_mma(
    const int8_t *A, const int8_t *B,
    const float *scale_a, const float *scale_b,
    __half *C,
    int M, int K, int N,
    cudaStream_t stream
) {
    dim3 grid((N + MMA_N - 1) / MMA_N, (M + MMA_M - 1) / MMA_M);
    dim3 block(32);
    sp_frob_matmul_q8_mma_kernel<<<grid, block, 0, stream>>>(
        A, B, scale_a, scale_b, C, M, K, N
    );
}

#else  /* sm_70- or host: C++ fallback — Q8 decode + scalar matmul */

inline void sp_frob_matmul_q8_mma(
    const int8_t *A, const int8_t *B,
    const float *scale_a, const float *scale_b,
    __half *C,
    int M, int K, int N,
    cudaStream_t stream
) {
    /* Fallback: decode Q8 to f32, do scalar matmul on CPU (for CI/no-GPU).
     * This path is NOT performance-competitive; it exists only to let CI compile+link. */
    (void)stream;
    for (int m = 0; m < M; m++) {
        for (int n = 0; n < N; n++) {
            float acc = 0.0f;
            for (int k = 0; k < K; k++) {
                acc += (float)A[m*K + k] * (float)B[k*N + n];
            }
            C[m*N + n] = __float2half(acc * scale_a[m] * scale_b[n]);
        }
    }
}

#endif /* __CUDA_ARCH__ >= 750 */
#endif /* __CUDACC__ */
```

**IMPORTANT implementer notes on MMA fragment layout:**
The `mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32` fragment layout is PRECISELY defined in the PTX ISA guide §9.7.13.4. The implementer MUST read this section before coding the fragment packing. The 8×16 A matrix is distributed as 2 int8 elements per thread (rows partitioned across lanes 0..15, columns across 0..31). Getting this wrong produces wrong results, not a crash.

The implementer should:
1. Read PTX ISA §9.7.13.4 for the exact lane-to-matrix-element mapping.
2. Implement fragment packing matching that spec exactly.
3. Write a simple 8×8 matmul test (all ones, verify acc==k*1==16) before running full M×N.

### Step 4.2: Wire MMA into cuda_forward.cu

In `cuda_forward.cu`, in the forward pass for Q8 arena weights:
- Replace calls to `k_dequant_arena` + cuBLAS SGEMM for Q8 weights with `sp_frob_matmul_q8_mma`.
- Pass the per-session CUDA stream (M_PTX_4).
- cuBLAS HGEMM for fp16 weights is unchanged.

The dispatch logic:
```cuda
if (weight->dtype == SP_DT_OK_Q8 && cuda_arch >= 750) {
    sp_frob_matmul_q8_mma(codes, w_codes, scale_a, scale_b, out_fp16, M, K, N, session_stream);
} else {
    /* Existing cuBLAS path */
    k_dequant_arena<<<...>>>(codes, scales, scratch_f32, ...);
    cublasSgemm(handle, ...);
}
```

### Step 4.3: Add MMA gate to ptx_validate.cu

Implement `validate_mma()`:
- Set up a known Q8 matmul (e.g., 8×16 A, 16×8 B with deterministic int8 values).
- Run PTX MMA path.
- Run C scalar reference (decode Q8 → f32, matmul, apply scale).
- Compare output fp16 values — must agree within fp16 ULP (M_PTX_1 float-adjacent).
- Print `M_PTX_1 MMA: PASS` / `FAIL`.
- **M_PTX_3 check:** Use `cuda-memcheck --leak-check full` or heap trace to confirm zero cudaMalloc in the MMA hot path.
- **M_PTX_4 check:** Launch two MMA kernels on different streams simultaneously. Verify no stream interleaving (use CUDA events, assert non-overlapping).

### Step 4.4: Add MMA bench to ptx_bench.cu

Implement `bench_mma()`:
- Benchmark 256×64 × 64×256 Q8 matmul (typical attention layer scale for 0.5B model).
- Compare: PTX MMA path vs k_dequant_arena + cuBLAS SGEMM baseline.
- Target: ≥3× throughput (M_PTX_2).
- Time with CUDA events. Print `MMA: PTX=Xus baseline=Yus speedup=Z.Zx`.

### Step 4.5: Build, run, commit

```bash
cmake --build build-ptx --target ptx_validate ptx_bench 2>&1
./build-ptx/ptx_validate.exe mma
./build-ptx/ptx_bench.exe mma
```
Expected: `M_PTX_1 MMA: PASS`, `M_PTX_3 MMA: PASS`, speedup ≥3×.

```bash
git add src/backends/cuda/ptx_mma.cuh src/backends/cuda/cuda_forward.cu src/backends/cuda/ptx_validate.cu src/backends/cuda/ptx_bench.cu
git commit -m "[lat-2-cu-ptx] Task 4: ptx_mma.cuh — INT8 tensor-core Q8 matmul, M_PTX_1+2+3+4 MMA green"
git tag lat-phase-2-cu-ptx-mma-closed
```

---

## Task 5: PERSIST PTX — persistent kernel for spec-decode (§17.5, OPTIONAL)

**Trigger condition:** Only implement if Task 4 (MMA) alone does not achieve ≥1.5× throughput at K=4 spec-decode with the 0.5B model (M_SPEC_3). Measure first, implement only if needed.

**Mechanism:** Pre-launch a long-running kernel (`ptx_spec_persist_kernel`) that spins on a pinned host work queue. CPU pushes draft requests; GPU consumes without kernel re-launching. Latency floor drops from ~5µs launch overhead to ~100ns queue poll.

**Gate measurement:**
1. Build Phase 4-SPEC binaries with the MMA path (Task 4 complete).
2. Measure K=4 spec throughput with 0.5B draft against 0.5B target.
3. If ≥1.5× over single-model baseline: M_SPEC_3 closes, PERSIST not needed.
4. If <1.5×: implement PERSIST.

**Files to create (only if needed):** `src/backends/cuda/ptx_persist.cuh`

```cuda
/*
 * ptx_persist.cuh — persistent kernel for Phase 4-SPEC draft generation.
 *
 * The kernel pre-launches and spins on a pinned host work queue.
 * CPU writes request descriptors; GPU worker threads consume them.
 * Eliminates ~5us kernel launch latency per spec step.
 *
 * Work queue format (pinned, 64-byte aligned):
 *   struct sp_persist_work {
 *       uint32_t request_id;    // monotonically increasing
 *       uint32_t token_in;      // input token for this step
 *       uint32_t ready;         // host sets to 1 when work is available
 *       uint32_t done;          // GPU sets to 1 when result is ready
 *       float    logits_out[1]; // result buffer pointer (separate allocation)
 *   };
 *
 * One persistent kernel per sp_session (M_PTX_4).
 */
#pragma once

#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750

struct sp_persist_work {
    volatile uint32_t request_id;
    volatile uint32_t token_in;
    volatile uint32_t ready;     /* host → GPU: set 1 to submit work */
    volatile uint32_t done;      /* GPU → host: set 1 when logits ready */
};

__global__
void sp_persist_decode_kernel(
    sp_persist_work *queue,
    /* model weights (mmap pointers from Fix-B), session KV state, logits buffer */
    /* ... forward pass parameters ... */
    float *logits_out, int vocab_size,
    volatile uint32_t *shutdown_flag
) {
    /* Each thread block monitors one queue slot and processes it persistently. */
    while (!(*shutdown_flag)) {
        if (queue->ready) {
            /* Execute one decode step using ptx_mma + ptx_spinor */
            uint32_t tok = queue->token_in;
            /* ... full forward pass for one token ... */
            /* Write logits to logits_out */
            __threadfence_system();
            queue->done = 1;
            queue->ready = 0;
        }
        /* Spin with ~100ns poll interval using nanosleep if sm_80+ */
        #if __CUDA_ARCH__ >= 800
        asm volatile ("nanosleep.u32 100;");
        #endif
    }
}

#endif /* __CUDA_ARCH__ >= 750 */
```

**Implementation decision point:** The PERSIST kernel body requires wiring the full forward pass. This is significant scope — only implement if the M_SPEC_3 measurement shows it's needed.

### Step 5.1 (if triggered): Measure M_SPEC_3 first

```bash
# Measure spec throughput after Task 4 (MMA) is integrated:
# Run spec_validate or a timing harness with K=4 on 0.5B×0.5B fixture
# Compare to single-model baseline (plain sp_decode_step loop)
# If spec_throughput / baseline >= 1.5x → SKIP Task 5, close M_SPEC_3
# If < 1.5x → implement ptx_persist.cuh
```

### Step 5.2 (if triggered): Implement PERSIST and close

```bash
git add src/backends/cuda/ptx_persist.cuh
git commit -m "[lat-2-cu-ptx] Task 5: ptx_persist.cuh — persistent kernel, M_SPEC_3 at 1.5x"
git tag lat-phase-2-cu-ptx-persist-closed
```

---

## Task 6: Closure — M_PTX_2 Nsight profile + umbrella tag + SESSION-CLOSED paper

**Prerequisites:** Tasks 1–4 complete. All sub-tags applied. M_PTX_1 green for all four sub-phases.

### Step 6.1: M_PTX_2 Nsight Compute profile

Run Nsight Compute on ptx_bench for each sub-phase:

```bash
# NTT throughput
ncu --metrics sm__inst_executed_pipe_xu_op_imad.sum,sm__cycles_elapsed.avg \
    --target-processes all ./build-ptx/ptx_bench.exe ntt 2>&1

# SPINOR DRAM bandwidth
ncu --metrics l1tex__t_bytes_pipe_lsu_mem_global_op_ld.sum.per_second \
    --target-processes all ./build-ptx/ptx_bench.exe spinor 2>&1

# MMA throughput vs baseline
ncu --metrics sm__inst_executed_pipe_tensor_op_imma.sum \
    --target-processes all ./build-ptx/ptx_bench.exe mma 2>&1
```

Record SOL numbers. Required to close M_PTX_2:
- SPINOR: ≥85% SOL DRAM
- NTT: ≥8× speedup over nvcc baseline
- MMA: ≥3× over k_dequant_arena+cuBLAS

If any metric misses target: investigate and optimize the relevant kernel before tagging.

### Step 6.2: cuobjdump SASS recovery

```bash
cuobjdump --dump-sass ./build-ptx/ptx_validate.exe 2>&1 | grep -B2 -A40 "ptx_modmul_q1"
cuobjdump --dump-sass ./build-ptx/ptx_validate.exe 2>&1 | grep -B2 -A10 "ptx_xor3"
cuobjdump --dump-sass ./build-ptx/ptx_validate.exe 2>&1 | grep -B2 -A20 "sp_frob_matmul_q8_mma"
```

Verify: IMAD instructions present in NTT SASS (not FMUL or integer division subroutine), LDG.E.CG in SPINOR SASS, HMMA.1688 (INT8 tensor core instruction) in MMA SASS.

### Step 6.3: Write SESSION-CLOSED paper (lattice repo)

Create `papers/SESSION-CLOSED-lat-2-CU-PTX.md` in the lattice repo with:
- Phase summary + dependency tags
- NTT §17.2: PTX Barrett butterfly — SASS excerpt, speedup Nsight number
- HASH §17.4: lop3/prmt primitives — SASS excerpt, cycles/op
- SPINOR §17.1: warp-load — SASS excerpt, DRAM SOL%
- MMA §17.3: INT8 tensor core — SASS excerpt, throughput speedup
- PERSIST §17.5: SKIP or results (per Task 5 decision)
- M_PTX_1 (bit-identity): PASS for all sub-phases
- M_PTX_2 (throughput): each gate's Nsight number
- M_PTX_3 (zero cudaMalloc): PASS
- M_PTX_4 (session isolation): PASS
- Anti-contamination notes: no legacy engine code used; no softmax/temperature

### Step 6.4: Commit and umbrella tag

Engine repo:
```bash
cd D:\F\shannon-prime-repos\shannon-prime-system-engine
git commit --allow-empty -m "[lat-phase-2-cu-ptx-closed] umbrella: NTT+HASH+SPINOR+MMA gates green"
git tag lat-phase-2-cu-ptx-closed
git push origin lat-2-cu-ptx && git push origin --tags
```

Lattice repo:
```bash
cd D:\F\shannon-prime-repos\shannon-prime-lattice
git add papers/SESSION-CLOSED-lat-2-CU-PTX.md docs/superpowers/plans/2026-05-27-phase-2-cu-ptx.md
git commit -m "[lat-phase-2-cu-ptx-closed] Phase 2-CU.PTX closure — all PTX gates green"
git tag lat-phase-2-cu-ptx-closed
git push && git push --tags
```

---

## Deferred Work (not in scope for lat-phase-2-cu-ptx-closed)

- **Full sieve KSTE integration** (Phase 5): hash primitives from Task 2 are ready; integration waits for sieve layer.
- **VK bare-metal counterpart:** Phase 2-VK.SPV (SPIR-V intrinsics + VK_KHR_cooperative_matrix) — future.
- **M_SPEC_3** via PERSIST: only if Task 5 triggered.
- **sm_90 (H100) tuning:** CUDA_ARCHITECTURES includes 90 but not profiled on dev host. CI gates only.

---

## Self-Review Against Mandate

1. **Scope:** PTX replaces CUDA C++ for Spinor/NTT/HASH/MMA. cuBLAS HGEMM untouched. ✓
2. **Dependency order:** NTT → HASH → SPINOR → MMA → PERSIST. ✓
3. **CI compatibility:** All `.cuh` headers have `#else` C++ fallback. ptx_validate/ptx_bench print SKIP on no-GPU. ✓
4. **M_PTX_3:** No `cudaMalloc` in any hot-path kernel — shared memory tiles only. ✓
5. **M_PTX_4:** Stream parameter threaded through all kernel launches. ✓
6. **Anti-contamination:** Legacy engine path never referenced. No softmax/temperature/threshold anywhere. ✓
7. **Math integrity:** PTX must be FASTER, never different. Any divergence from scalar reference = STOP. ✓
8. **Fix-B mmap isolation:** MMA loads from mmap'd sp_model arena pointers (no cudaMalloc). M_SPEC_4 verifies RSS. ✓
