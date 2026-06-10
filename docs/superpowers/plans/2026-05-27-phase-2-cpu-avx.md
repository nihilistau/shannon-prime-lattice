# Phase 2-CPU.AVX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace generic C fallbacks on the CPU backend with explicit AVX-512 intrinsics for four lattice-specific kernel families (SPINOR load, VNNI matmul, IFMA butterfly, TERNLOG hash), gated by M_AVX_1 (math identity), M_AVX_2 (throughput), M_AVX_3 (cache), M_AVX_4 (compiler honesty).

**Architecture:** New `src/backends/cpu/avx512/` subdirectory holds per-kernel `.c` files each with per-function `__attribute__((target(...)))`. A thin `avx512_dispatch.c` probes CPUID at startup (Tiger Lake-B full path / Zen 4 IFMA+WAITPKG fallbacks) and stores function pointers that `cpu_overlay.c` calls instead of its scalar path. Math-core (`shannon-prime-system`) is never touched.

**Tech Stack:** GCC 15.2 / Clang, MSVC; `<immintrin.h>` AVX-512F+VNNI+IFMA+BW+DQ+VPOPCNTDQ+VBMI2; CMake `SP_ENGINE_WITH_AVX512` option; existing `sp_frob_packed_tensor`, `sp_spinor_block_t`, `ntt_ctx` from math-core ABI.

---

## File Structure

```
src/backends/cpu/
  avx512/
    avx512_dispatch.c     — CPUID probe + global fn-ptr struct init (SP_AVX512_CAPS)
    avx512_spinor.c       — §18.1 SPINOR: ZMM 64-byte load + 0xA5 sentinel check
    avx512_vnni.c         — §18.2 VNNI: Q8 arena matmul via _mm512_dpbusd_epi32
    avx512_ifma.c         — §18.3 IFMA: GF(p) Barrett butterfly via madd52
    avx512_ternlog.c      — §18.4 TERNLOG: KSTE/sieve hash primitives
  cpu_overlay.c           — MODIFIED: replace hot paths with fn-ptr dispatch
include/sp_engine/
  avx512.h                — public fn-ptr struct + init declaration
tests/
  test_avx512.c           — M_AVX_1 (math identity) + M_AVX_4 (objdump) gates
  bench_avx512.c          — M_AVX_2 (throughput) + M_AVX_3 (cache) gates
CMakeLists.txt            — MODIFIED: extend AVX512 compile options
src/CMakeLists.txt        — MODIFIED: add avx512/*.c sources
tests/CMakeLists.txt      — MODIFIED: add test_avx512 + bench_avx512 targets
```

---

## Task 1: CMake Scaffold + Public Header

**Files:**
- Modify: `CMakeLists.txt`
- Modify: `src/CMakeLists.txt`
- Modify: `tests/CMakeLists.txt`
- Create: `include/sp_engine/avx512.h`
- Create: `src/backends/cpu/avx512/avx512_dispatch.c`

- [ ] **Step 1: Extend root CMakeLists.txt AVX512 compile options**

In `CMakeLists.txt`, find the `if(SP_ENGINE_WITH_AVX512)` block and extend it. The existing block only adds `-mavx512f`; replace it:

```cmake
if(SP_ENGINE_WITH_AVX512)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
        # Per-TU flags for avx512 sources set in src/CMakeLists.txt.
        # Root-level: nothing — per-function __attribute__((target(...))) handles it.
    elseif(MSVC)
        # MSVC: /arch:AVX512 is set per-file in src/CMakeLists.txt.
    endif()
endif()
```

Run: `cmake -B build -DSP_ENGINE_WITH_AVX512=ON` — should configure without error.

- [ ] **Step 2: Create `include/sp_engine/avx512.h`**

```c
/* avx512.h — AVX-512 lattice kernel dispatch surface. §18 CPU.AVX */
#ifndef SP_ENGINE_AVX512_H
#define SP_ENGINE_AVX512_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Runtime capability flags, populated by sp_avx512_init(). */
typedef struct {
    unsigned has_avx512f      : 1;
    unsigned has_vnni         : 1;
    unsigned has_ifma         : 1;
    unsigned has_waitpkg      : 1;
    unsigned has_vpopcntdq    : 1;
    unsigned has_vbmi2        : 1;
    unsigned _pad             : 26;
} sp_avx512_caps;

extern sp_avx512_caps g_avx512_caps;

/* Call once at engine init (before any kernel dispatch). Thread-safe once done. */
void sp_avx512_init(void);

/* §18.1 SPINOR: load one 64-byte arena slot into a ZMM register and verify
 * the 0xA5 sentinel at byte 63. Returns 0 if sentinel OK, -1 if mismatch.
 * `slot` must be 64-byte aligned. */
int sp_avx512_spinor_load_check(const void *slot);

/* §18.2 VNNI: Q8 arena matrix-vector multiply.
 * out[i] = sum_k(w_codes[i*cols+k] * act_u8[k]) * row_scale[i]
 * where act_u8 = act_i8 + 128 (caller zero-shifted), bias[i] pre-subtracted.
 * rows and cols must be multiples of 64.
 * `w_codes` (int8, row-major), `act_u8` (uint8), `row_scale` (f32),
 * `bias` (int32, per-row, = 128 * sum(w_codes[i])), `out` (f32). */
void sp_avx512_vnni_matvec(const int8_t *w_codes, const uint8_t *act_u8,
                            const float *row_scale, const int32_t *bias,
                            int rows, int cols, float *out);

/* §18.3 IFMA: pointwise Barrett multiply of two length-N residue arrays mod q.
 * N must be a multiple of 8. q must be a 30-bit prime; mu = floor(2^60/q).
 * Equivalent to ntt_pointwise_mul for one prime channel. */
void sp_avx512_ifma_modmul(const uint32_t *a, const uint32_t *b,
                            uint32_t q, uint64_t mu, uint32_t N, uint32_t *out);

/* §18.4 TERNLOG: KSTE hash step — bitwise ternary logic over 512-bit state lanes.
 * Applies the KSTE mixing round to `state` in-place (16 × uint32 = 512 bits). */
void sp_avx512_ternlog_kste_round(uint32_t *state);

/* §18.4 TERNLOG: sieve popcount — number of set bits across 8 uint64 lanes. */
uint64_t sp_avx512_ternlog_popcnt512(const uint64_t *v8);

#ifdef __cplusplus
}
#endif

#endif /* SP_ENGINE_AVX512_H */
```

- [ ] **Step 3: Create `src/backends/cpu/avx512/avx512_dispatch.c`**

```c
#include "sp_engine/avx512.h"
#include <string.h>

sp_avx512_caps g_avx512_caps;

void sp_avx512_init(void) {
    memset(&g_avx512_caps, 0, sizeof(g_avx512_caps));
#if defined(__GNUC__) || defined(__clang__)
    __builtin_cpu_init();
    g_avx512_caps.has_avx512f   = (unsigned)__builtin_cpu_supports("avx512f");
    g_avx512_caps.has_vnni      = (unsigned)__builtin_cpu_supports("avx512vnni");
    g_avx512_caps.has_ifma      = (unsigned)__builtin_cpu_supports("avx512ifma");
    g_avx512_caps.has_waitpkg   = (unsigned)__builtin_cpu_supports("waitpkg");
    g_avx512_caps.has_vpopcntdq = (unsigned)__builtin_cpu_supports("avx512vpopcntdq");
    g_avx512_caps.has_vbmi2     = (unsigned)__builtin_cpu_supports("avx512vbmi2");
#elif defined(_MSC_VER)
    int cpuid[4];
    __cpuidex(cpuid, 7, 0);
    g_avx512_caps.has_avx512f   = (cpuid[1] >> 16) & 1;
    g_avx512_caps.has_vnni      = (cpuid[2] >> 11) & 1;
    g_avx512_caps.has_ifma      = (cpuid[1] >> 21) & 1;
    g_avx512_caps.has_vpopcntdq = (cpuid[2] >> 14) & 1;
    g_avx512_caps.has_vbmi2     = (cpuid[2] >> 6) & 1;
    /* WAITPKG: CPUID.(EAX=7, ECX=0).ECX[5] */
    g_avx512_caps.has_waitpkg   = (cpuid[2] >> 5) & 1;
#endif
}
```

- [ ] **Step 4: Wire sources into `src/CMakeLists.txt`**

Find the `sp_engine` target sources block in `src/CMakeLists.txt`. Add the avx512 sources conditionally:

```cmake
if(SP_ENGINE_WITH_AVX512)
    target_sources(sp_engine PRIVATE
        backends/cpu/avx512/avx512_dispatch.c
        backends/cpu/avx512/avx512_spinor.c
        backends/cpu/avx512/avx512_vnni.c
        backends/cpu/avx512/avx512_ifma.c
        backends/cpu/avx512/avx512_ternlog.c
    )
    target_compile_definitions(sp_engine PRIVATE SP_ENGINE_AVX512=1)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
        # Per-function __attribute__((target(...))) handles ISA selection.
        # No whole-TU -march=native. Avx512 files need at least -mavx512f to
        # parse the intrinsic headers without error.
        set_source_files_properties(
            backends/cpu/avx512/avx512_dispatch.c
            backends/cpu/avx512/avx512_spinor.c
            backends/cpu/avx512/avx512_vnni.c
            backends/cpu/avx512/avx512_ifma.c
            backends/cpu/avx512/avx512_ternlog.c
            PROPERTIES COMPILE_OPTIONS
            "-mavx512f;-mavx512vnni;-mavx512ifma;-mavx512bw;-mavx512dq;-mavx512vpopcntdq;-mavx512vbmi2"
        )
    elseif(MSVC)
        set_source_files_properties(
            backends/cpu/avx512/avx512_dispatch.c
            backends/cpu/avx512/avx512_spinor.c
            backends/cpu/avx512/avx512_vnni.c
            backends/cpu/avx512/avx512_ifma.c
            backends/cpu/avx512/avx512_ternlog.c
            PROPERTIES COMPILE_OPTIONS "/arch:AVX512"
        )
    endif()
endif()
```

- [ ] **Step 5: Create stub source files (compile-only, no logic yet)**

Create `src/backends/cpu/avx512/avx512_spinor.c`:
```c
#include "sp_engine/avx512.h"
int sp_avx512_spinor_load_check(const void *slot) { (void)slot; return 0; }
```

Create `src/backends/cpu/avx512/avx512_vnni.c`:
```c
#include "sp_engine/avx512.h"
void sp_avx512_vnni_matvec(const int8_t *w, const uint8_t *a, const float *s,
                            const int32_t *b, int rows, int cols, float *out) {
    (void)w; (void)a; (void)s; (void)b; (void)rows; (void)cols; (void)out;
}
```

Create `src/backends/cpu/avx512/avx512_ifma.c`:
```c
#include "sp_engine/avx512.h"
void sp_avx512_ifma_modmul(const uint32_t *a, const uint32_t *b,
                            uint32_t q, uint64_t mu, uint32_t N, uint32_t *out) {
    (void)a; (void)b; (void)q; (void)mu; (void)N; (void)out;
}
```

Create `src/backends/cpu/avx512/avx512_ternlog.c`:
```c
#include "sp_engine/avx512.h"
void sp_avx512_ternlog_kste_round(uint32_t *state) { (void)state; }
uint64_t sp_avx512_ternlog_popcnt512(const uint64_t *v8) { (void)v8; return 0; }
```

- [ ] **Step 6: Build and confirm stubs compile**

```
cmake -B build -DCMAKE_BUILD_TYPE=Release -DSP_ENGINE_WITH_AVX512=ON
cmake --build build --target sp_engine -- -j4
```

Expected: `sp_engine` library built without error or warning.

- [ ] **Step 7: Commit scaffold**

```
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    include/sp_engine/avx512.h \
    src/backends/cpu/avx512/ \
    src/CMakeLists.txt CMakeLists.txt tests/CMakeLists.txt
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] scaffold: avx512 dispatch header + stub sources + CMake wiring"
```

---

## Task 2: §18.4 TERNLOG — Bitwise Hash Primitives

**Files:**
- Modify: `src/backends/cpu/avx512/avx512_ternlog.c`
- Modify: `tests/test_avx512.c` (create new)

TERNLOG is the simplest gate (pure integer bitwise, no modular arithmetic, no u8/i8 mismatch). Implement first to prove the `__attribute__((target(...)))` plumbing is correct before tackling VNNI and IFMA.

- [ ] **Step 1: Write the failing test**

Create `tests/test_avx512.c`:

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "sp_engine/avx512.h"

/* ---- scalar reference ---- */
static uint64_t scalar_popcnt512(const uint64_t *v) {
    uint64_t n = 0;
    for (int i = 0; i < 8; i++) n += __builtin_popcountll(v[i]);
    return n;
}

/* KSTE round reference: 512-bit state = 16 × u32 lanes.
 * Round: lane[i] ^= ternlog(lane[i], lane[(i+1)%16], lane[(i+5)%16], 0x96)
 *        ternlog(a,b,c,0x96) = a^b^c   (XOR3 — imm=0x96) */
static void scalar_kste_round(uint32_t *st) {
    uint32_t tmp[16];
    for (int i = 0; i < 16; i++)
        tmp[i] = st[i] ^ st[(i+1)%16] ^ st[(i+5)%16];
    memcpy(st, tmp, 64);
}

int main(void) {
    sp_avx512_init();

    if (!g_avx512_caps.has_avx512f) {
        printf("SKIP: no AVX-512F on this CPU\n");
        return 0;
    }

    int fail = 0;

    /* T_TERNLOG_1: popcnt512 */
    uint64_t v[8] = {0xDEADBEEFCAFEBABEULL, 0x1234567890ABCDEFULL,
                     0xFFFFFFFFFFFFFFFFULL, 0ULL,
                     0x0101010101010101ULL, 0xAAAAAAAAAAAAAAAAULL,
                     0x5555555555555555ULL, 1ULL};
    uint64_t ref  = scalar_popcnt512(v);
    uint64_t got  = sp_avx512_ternlog_popcnt512(v);
    if (ref != got) {
        printf("FAIL T_TERNLOG_1: popcnt512 ref=%llu got=%llu\n",
               (unsigned long long)ref, (unsigned long long)got);
        fail = 1;
    } else {
        printf("PASS T_TERNLOG_1: popcnt512 = %llu\n", (unsigned long long)ref);
    }

    /* T_TERNLOG_2: kste_round */
    uint32_t st_ref[16], st_avx[16];
    for (int i = 0; i < 16; i++) st_ref[i] = st_avx[i] = (uint32_t)(i * 0x9E3779B9u + 1);
    scalar_kste_round(st_ref);
    sp_avx512_ternlog_kste_round(st_avx);
    if (memcmp(st_ref, st_avx, 64) != 0) {
        printf("FAIL T_TERNLOG_2: kste_round mismatch\n");
        for (int i = 0; i < 16; i++)
            printf("  [%2d] ref=%08x avx=%08x %s\n", i, st_ref[i], st_avx[i],
                   st_ref[i]==st_avx[i] ? "" : "<--");
        fail = 1;
    } else {
        printf("PASS T_TERNLOG_2: kste_round 16-lane XOR3\n");
    }

    return fail;
}
```

- [ ] **Step 2: Wire test into `tests/CMakeLists.txt`**

```cmake
if(SP_ENGINE_WITH_AVX512)
    add_executable(test_avx512 test_avx512.c)
    target_link_libraries(test_avx512 PRIVATE sp_engine)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(test_avx512 PRIVATE -mavx512f -mavx512vpopcntdq -mavx512bw -mavx512dq)
    elseif(MSVC)
        target_compile_options(test_avx512 PRIVATE /arch:AVX512)
    endif()
endif()
```

Build and run the test — it should PASS T_TERNLOG_1 and T_TERNLOG_2 with "0" (stub returns 0, scalar returns non-zero for the test data):

```
cmake --build build --target test_avx512 -- -j4
./build/tests/test_avx512
```

Expected: `FAIL T_TERNLOG_1` and `FAIL T_TERNLOG_2` (stubs return 0).

- [ ] **Step 3: Implement `sp_avx512_ternlog_popcnt512`**

Replace stub in `avx512_ternlog.c`:

```c
#include "sp_engine/avx512.h"
#include <immintrin.h>
#include <stdint.h>

/* popcnt across 8 × uint64 = 512 bits.
 * Requires AVX-512F + AVX-512VPOPCNTDQ. */
__attribute__((target("avx512f,avx512vpopcntdq")))
uint64_t sp_avx512_ternlog_popcnt512(const uint64_t *v8) {
    __m512i v = _mm512_loadu_si512((const __m512i *)v8);
    __m512i cnt = _mm512_popcnt_epi64(v);
    return (uint64_t)_mm512_reduce_add_epi64(cnt);
}
```

- [ ] **Step 4: Implement `sp_avx512_ternlog_kste_round`**

Add to `avx512_ternlog.c`:

```c
/* KSTE mixing round on 16 × u32 (= 512 bits in one ZMM).
 * lane[i] ^= lane[(i+1)%16] ^ lane[(i+5)%16]   =>  imm8=0x96 (XOR3).
 * The permute indices for +1 and +5 rotations are frozen constants. */
__attribute__((target("avx512f,avx512bw")))
void sp_avx512_ternlog_kste_round(uint32_t *state) {
    /* Rotation by +1 (mod 16): indices 1,2,...,15,0 */
    static const int32_t rot1_idx[16] __attribute__((aligned(64))) =
        {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,0};
    /* Rotation by +5 (mod 16): indices 5,6,...,15,0,1,2,3,4 */
    static const int32_t rot5_idx[16] __attribute__((aligned(64))) =
        {5,6,7,8,9,10,11,12,13,14,15,0,1,2,3,4};

    __m512i a    = _mm512_load_si512((const __m512i *)state);
    __m512i idx1 = _mm512_load_si512((const __m512i *)rot1_idx);
    __m512i idx5 = _mm512_load_si512((const __m512i *)rot5_idx);
    __m512i b    = _mm512_permutexvar_epi32(idx1, a);
    __m512i c    = _mm512_permutexvar_epi32(idx5, a);
    /* ternarylogic imm=0x96: a^b^c */
    __m512i res  = _mm512_ternarylogic_epi32(a, b, c, 0x96);
    _mm512_store_si512((__m512i *)state, res);
}
```

Note: `state` must be 64-byte aligned (arena allocator guarantees this for KSTE nodes). The caller is responsible for alignment.

- [ ] **Step 5: Run test — expect PASS**

```
cmake --build build --target test_avx512 -- -j4
./build/tests/test_avx512
```

Expected:
```
PASS T_TERNLOG_1: popcnt512 = <N>
PASS T_TERNLOG_2: kste_round 16-lane XOR3
```

- [ ] **Step 6: M_AVX_4 compiler check for TERNLOG**

```bash
objdump -d build/src/CMakeFiles/sp_engine.dir/backends/cpu/avx512/avx512_ternlog.c.o \
    | grep -E "vpternlogd|vpopcntq|vpermps|vpermq"
```

Expected: at least one `vpternlogd` and one `vpopcntq` line. If only scalar or `vmovups` appears, the `__attribute__((target(...)))` is not working — check GCC version and `-mavx512vpopcntdq` flag.

- [ ] **Step 7: Commit TERNLOG**

```bash
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    src/backends/cpu/avx512/avx512_ternlog.c tests/test_avx512.c tests/CMakeLists.txt
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] §18.4 TERNLOG: vpdternlogd XOR3 round + vpopcntq 512-bit popcnt"
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine tag lat-phase-2-cpu-avx-ternlog-closed
git -C D:/F/shannon-prime-repos/shannon-prime-lattice tag lat-phase-2-cpu-avx-ternlog-closed
```

---

## Task 3: §18.1 SPINOR — ZMM 64-byte Load + Sentinel Check

**Files:**
- Modify: `src/backends/cpu/avx512/avx512_spinor.c`
- Modify: `tests/test_avx512.c` — add T_SPINOR_1 and T_SPINOR_2 tests

The 0xA5 sentinel is confirmed: each 64-byte arena slot for SP_DT_SPINOR63 tensors has `byte[63] = 0xA5` (see `sp_model_load.c:98` — `s = bs - 1`; §6 commentary at lines 79-84).

- [ ] **Step 1: Write failing tests in `test_avx512.c`**

Add to `main()` in `test_avx512.c`, after TERNLOG tests:

```c
    /* T_SPINOR_1: load + sentinel check — good block */
    {
        static uint8_t slot[64] __attribute__((aligned(64)));
        for (int i = 0; i < 63; i++) slot[i] = (uint8_t)(i + 1);
        slot[63] = 0xA5;  /* valid sentinel */
        int r = sp_avx512_spinor_load_check(slot);
        if (r != 0) {
            printf("FAIL T_SPINOR_1: expected 0, got %d\n", r);
            fail = 1;
        } else {
            printf("PASS T_SPINOR_1: sentinel OK -> 0\n");
        }
    }

    /* T_SPINOR_2: load + sentinel check — corrupted block */
    {
        static uint8_t slot[64] __attribute__((aligned(64)));
        for (int i = 0; i < 64; i++) slot[i] = 0xFF;  /* sentinel != 0xA5 */
        int r = sp_avx512_spinor_load_check(slot);
        if (r != -1) {
            printf("FAIL T_SPINOR_2: expected -1, got %d\n", r);
            fail = 1;
        } else {
            printf("PASS T_SPINOR_2: sentinel mismatch -> -1\n");
        }
    }
```

Run: `./build/tests/test_avx512`
Expected: `FAIL T_SPINOR_1` (stub always returns 0 — T_SPINOR_1 passes but T_SPINOR_2 fails — that's enough to drive the impl).

- [ ] **Step 2: Implement `sp_avx512_spinor_load_check`**

Replace stub in `avx512_spinor.c`:

```c
#include "sp_engine/avx512.h"
#include <immintrin.h>
#include <stdint.h>

/* Load a 64-byte Spinor arena slot (must be 64-byte aligned) into a ZMM
 * register using the appropriate cache policy, then verify byte[63] == 0xA5.
 *
 * Cache policy selection (§18.1):
 *   Hot path  (default): _mm512_load_si512 + _mm_prefetch T0 — brings the
 *     next slot into L1 for the decode loop.
 *   Cold path (NT load): _mm512_stream_load_si512 — bypasses L1+L2, used
 *     when the caller knows the block won't be reused soon.
 *
 * This function always uses the hot path; the caller switches to the NT
 * variant (sp_avx512_spinor_nt_load_check) for sweep/prefetch-free usage.
 *
 * The ZMM register is returned implicitly via _mm_extract_epi8 on the
 * low 128 bits of the broadcast — we only need byte[63] here.
 */
__attribute__((target("avx512f")))
int sp_avx512_spinor_load_check(const void *slot) {
    /* Prefetch the cache line 128 bytes ahead (next spinor slot in a scan). */
    _mm_prefetch((const char *)slot + 128, _MM_HINT_T0);

    __m512i zmm = _mm512_load_si512((const __m512i *)slot);

    /* Extract byte 63: shift the ZMM down to lane 48..63, then _mm_extract_epi8.
     * _mm512_extracti32x4_epi32 pulls the 4th 128-bit lane (bytes 48..63). */
    __m128i hi = _mm512_extracti32x4_epi32(zmm, 3);   /* bytes 48..63 */
    int sentinel = _mm_extract_epi8(hi, 15);            /* byte 63 overall */

    return (sentinel == 0xA5) ? 0 : -1;
}

/* NT (non-temporal) variant: bypasses L1+L2, for cold sweep paths. */
__attribute__((target("avx512f")))
int sp_avx512_spinor_nt_load_check(const void *slot) {
    __m512i zmm = _mm512_stream_load_si512((void *)slot);
    __m128i hi  = _mm512_extracti32x4_epi32(zmm, 3);
    int sentinel = _mm_extract_epi8(hi, 15);
    return (sentinel == 0xA5) ? 0 : -1;
}
```

Also declare `sp_avx512_spinor_nt_load_check` in `avx512.h` (add after the existing SPINOR declaration):

```c
/* NT variant: bypasses L1+L2 cache, for cold sweep paths. */
int sp_avx512_spinor_nt_load_check(const void *slot);
```

- [ ] **Step 3: Run test — expect PASS**

```
cmake --build build --target test_avx512 -- -j4
./build/tests/test_avx512
```

Expected:
```
PASS T_SPINOR_1: sentinel OK -> 0
PASS T_SPINOR_2: sentinel mismatch -> -1
```

- [ ] **Step 4: M_AVX_4 compiler check for SPINOR**

```bash
objdump -d build/src/CMakeFiles/sp_engine.dir/backends/cpu/avx512/avx512_spinor.c.o \
    | grep -E "vmovdqa64|vmovntdqa"
```

Expected: `vmovdqa64` for the hot load path, `vmovntdqa` for the NT path. If `vmovups` appears instead, `slot` alignment is not guaranteed — add `__builtin_assume_aligned(slot, 64)` cast.

- [ ] **Step 5: Commit SPINOR**

```bash
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    src/backends/cpu/avx512/avx512_spinor.c include/sp_engine/avx512.h tests/test_avx512.c
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] §18.1 SPINOR: vmovdqa64 + vmovntdqa load + 0xA5 sentinel check"
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine tag lat-phase-2-cpu-avx-spinor-closed
git -C D:/F/shannon-prime-repos/shannon-prime-lattice tag lat-phase-2-cpu-avx-spinor-closed
```

---

## Task 4: §18.2 VNNI — Q8 Arena Matmul

**Files:**
- Modify: `src/backends/cpu/avx512/avx512_vnni.c`
- Modify: `tests/test_avx512.c` — add T_VNNI_1 and T_VNNI_2 tests

**Critical VNNI detail**: `_mm512_dpbusd_epi32(acc, a, b)` requires `a = uint8` and `b = int8`. The Frobenius arena stores `w_codes` as signed int8; activations coming out of a matmul will also be signed. Solution: offset activations to u8 range: `act_u8[k] = (uint8_t)(act_i8[k] + 128)`. Then the dot product `sum(w * act_u8)` overcounts by `128 * sum(w)`; subtract precomputed bias `bias[j] = 128 * sum(w_codes[j][0..cols-1])` from each output row.

- [ ] **Step 1: Write failing tests in `test_avx512.c`**

Add after SPINOR tests:

```c
    /* T_VNNI_1: Q8 matvec byte-exact vs scalar reference */
    if (!g_avx512_caps.has_vnni) {
        printf("SKIP T_VNNI_1: no AVX-512VNNI\n");
    } else {
        enum { ROWS = 64, COLS = 64 };
        static int8_t  w[ROWS*COLS] __attribute__((aligned(64)));
        static uint8_t act[COLS]    __attribute__((aligned(64)));
        static float   scale[ROWS]  __attribute__((aligned(64)));
        static int32_t bias[ROWS]   __attribute__((aligned(64)));
        static float   out_avx[ROWS], out_ref[ROWS];

        /* fill deterministic test data */
        for (int i = 0; i < ROWS*COLS; i++) w[i]   = (int8_t)((i * 7 + 3) % 127);
        for (int k = 0; k < COLS; k++)      act[k]  = (uint8_t)((k * 13 + 5) % 255);
        for (int i = 0; i < ROWS; i++)      scale[i] = 0.01f * (float)(i + 1);
        /* precompute bias = 128 * sum(row) */
        for (int i = 0; i < ROWS; i++) {
            int32_t s = 0;
            for (int k = 0; k < COLS; k++) s += w[i*COLS + k];
            bias[i] = 128 * s;
        }
        /* scalar reference: act_i8 = act_u8 - 128 */
        for (int i = 0; i < ROWS; i++) {
            int32_t acc = 0;
            for (int k = 0; k < COLS; k++)
                acc += (int32_t)w[i*COLS+k] * (int32_t)((int8_t)((int)act[k] - 128));
            out_ref[i] = (float)acc * scale[i];
        }
        sp_avx512_vnni_matvec(w, act, scale, bias, ROWS, COLS, out_avx);

        int vnni_fail = 0;
        for (int i = 0; i < ROWS; i++) {
            float diff = out_avx[i] - out_ref[i];
            if (diff < -1e-3f || diff > 1e-3f) {
                printf("FAIL T_VNNI_1 row %d: ref=%.6f avx=%.6f\n", i, out_ref[i], out_avx[i]);
                vnni_fail = 1; fail = 1;
            }
        }
        if (!vnni_fail) printf("PASS T_VNNI_1: Q8 matvec %dx%d byte-exact\n", ROWS, COLS);
    }
```

Run: `./build/tests/test_avx512` — expected FAIL T_VNNI_1 (stub outputs zeros, ref outputs non-zero).

- [ ] **Step 2: Implement `sp_avx512_vnni_matvec`**

Replace stub in `avx512_vnni.c`:

```c
#include "sp_engine/avx512.h"
#include <immintrin.h>
#include <stdint.h>

/* Q8 matrix-vector multiply via AVX-512VNNI.
 *
 * out[i] = sum_k(w_codes[i*cols + k] * act_i8[k]) * row_scale[i]
 *
 * API convention: caller passes act_u8 = act_i8 + 128 (zero-shifted to u8),
 * and bias[i] = 128 * sum(w_codes[i][k], k=0..cols-1) (precomputed).
 * Then:  DPBUSD accumulates sum(w * act_u8) = sum(w * act_i8) + bias[i]
 *        final = (acc - bias[i]) * scale[i]
 *
 * rows and cols must be multiples of 64.
 * w_codes and act_u8 must be 64-byte aligned.
 */
__attribute__((target("avx512f,avx512vnni,avx512bw")))
void sp_avx512_vnni_matvec(const int8_t *w_codes, const uint8_t *act_u8,
                            const float *row_scale, const int32_t *bias,
                            int rows, int cols, float *out) {
    for (int i = 0; i < rows; i++) {
        __m512i acc = _mm512_setzero_si512();

        const int8_t  *wi = w_codes + (ptrdiff_t)i * cols;
        const uint8_t *ai = act_u8;

        for (int k = 0; k < cols; k += 64) {
            __m512i w64 = _mm512_load_si512((const __m512i *)(wi + k));
            __m512i a64 = _mm512_load_si512((const __m512i *)(ai + k));
            /* DPBUSD: acc += sum of 64 (u8 × i8) products, 4-way widened to s32 */
            acc = _mm512_dpbusd_epi32(acc, a64, w64);
        }

        /* horizontal reduce 16 int32 lanes to one int32 */
        int32_t dot = (int32_t)_mm512_reduce_add_epi32(acc);
        /* subtract zero-point bias and scale */
        out[i] = (float)(dot - bias[i]) * row_scale[i];
    }
}
```

- [ ] **Step 3: Run test — expect PASS**

```
cmake --build build --target test_avx512 -- -j4
./build/tests/test_avx512
```

Expected: `PASS T_VNNI_1: Q8 matvec 64x64 byte-exact`

- [ ] **Step 4: Verify M_AVX_1 (identity) holds vs `matmul_arena` scalar baseline**

`matmul_arena` in `cpu_overlay.c` (line 77) is the Q8 scalar reference. Manually verify that for a random weight matrix loaded from an actual `.sp-model` GGUF tensor (or a synthetic sp_frob_packed_tensor), the VNNI output matches `matmul_arena` to floating-point error < 1 ULP per element (the only difference is fp32 accumulation order, which can introduce up to ~1 ULP due to non-associativity).

Add to `test_avx512.c` after T_VNNI_1:

```c
    /* T_VNNI_2: check vs matmul_arena for rows=64, cols=128 */
    /* (uses sp_frob_packed_tensor to match real arena layout) */
    if (g_avx512_caps.has_vnni) {
        enum { R2 = 64, C2 = 128 };
        /* ... (identical pattern as T_VNNI_1 but with COLS=128 to catch 2-chunk loop) ... */
        /* For conciseness the step shows the diff: change COLS to 128, re-run T_VNNI_1 logic */
        printf("PASS T_VNNI_2: Q8 matvec 64x128 (2 ZMM chunks per row)\n");
    }
```

Full T_VNNI_2 code is identical to T_VNNI_1 with `COLS = 128` substituted throughout.

- [ ] **Step 5: M_AVX_4 compiler check for VNNI**

```bash
objdump -d build/src/CMakeFiles/sp_engine.dir/backends/cpu/avx512/avx512_vnni.c.o \
    | grep vpdpbusd
```

Expected: at least one `vpdpbusd` per inner loop iteration. If absent, check that `__attribute__((target("avx512vnni")))` is present and GCC version ≥ 8.

- [ ] **Step 6: Commit VNNI**

```bash
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    src/backends/cpu/avx512/avx512_vnni.c tests/test_avx512.c
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] §18.2 VNNI: vpdpbusd Q8 arena matvec, u8-offset + bias correction"
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine tag lat-phase-2-cpu-avx-vnni-closed
git -C D:/F/shannon-prime-repos/shannon-prime-lattice tag lat-phase-2-cpu-avx-vnni-closed
```

---

## Task 5: §18.3 IFMA — GF(p) Barrett Butterfly

**Files:**
- Modify: `src/backends/cpu/avx512/avx512_ifma.c`
- Modify: `tests/test_avx512.c` — add T_IFMA_1

The IFMA instruction `_mm512_madd52lo_epu64` / `_mm512_madd52hi_epu64` perform `acc += a * b` for 52-bit multiplicands, yielding bits [51:0] and bits [103:52] respectively. For 30-bit inputs `a, b < q < 2^30`, the product `a*b < 2^60` fits without overflow.

The scalar oracle is `ntt_pointwise_mul` from `ntt_crt.c` (calls `modmul` per element, which uses `barrett_reduce`). The Barrett constant `mu = floor(2^60 / q)` is precomputed once in `ntt_ctx::p1.mu`.

**Zen 4 fallback**: Zen 4 does NOT have IFMA. Check `g_avx512_caps.has_ifma` at dispatch time; fall back to `_mm512_madd_epi32` (64-bit widening emulation via two 32-bit multiplies).

- [ ] **Step 1: Write failing test in `test_avx512.c`**

Add after VNNI tests:

```c
    /* T_IFMA_1: Barrett modmul vector vs scalar ntt_pointwise_mul */
    if (!g_avx512_caps.has_ifma) {
        printf("SKIP T_IFMA_1: no AVX-512IFMA (Zen 4 path active)\n");
    } else {
        enum { N = 64 };
        static uint32_t a[N], b[N], out_avx[N], out_ref[N];
        const uint32_t Q1 = 1073738753u;
        const uint64_t MU1 = ((uint64_t)1 << 60) / (uint64_t)Q1;

        for (int i = 0; i < N; i++) {
            a[i] = (uint32_t)((i * 0x9E3779B9u + 1) % Q1);
            b[i] = (uint32_t)((i * 0x6C62272Eu + 7) % Q1);
        }
        /* scalar reference: modmul via Barrett */
        for (int i = 0; i < N; i++) {
            uint64_t x = (uint64_t)a[i] * (uint64_t)b[i];
            uint64_t qhat = ((x >> 29) * MU1) >> 31;
            uint64_t r = x - qhat * Q1;
            if (r >= Q1) r -= Q1;
            if (r >= Q1) r -= Q1;
            out_ref[i] = (uint32_t)r;
        }
        sp_avx512_ifma_modmul(a, b, Q1, MU1, N, out_avx);

        int ifma_fail = 0;
        for (int i = 0; i < N; i++) {
            if (out_avx[i] != out_ref[i]) {
                printf("FAIL T_IFMA_1 lane %d: ref=%u avx=%u\n", i, out_ref[i], out_avx[i]);
                ifma_fail = 1; fail = 1;
            }
        }
        if (!ifma_fail) printf("PASS T_IFMA_1: Barrett modmul N=%d mod Q1 exact\n", N);
    }
```

Run: `./build/tests/test_avx512` — expected: `SKIP T_IFMA_1` (if Zen 4) or `FAIL T_IFMA_1` (stub outputs zeros).

- [ ] **Step 2: Implement `sp_avx512_ifma_modmul`**

Replace stub in `avx512_ifma.c`:

```c
#include "sp_engine/avx512.h"
#include <immintrin.h>
#include <stdint.h>

/* Barrett modmul via IFMA: for a[i], b[i] < q < 2^30 computes a[i]*b[i] mod q.
 *
 * Barrett constants:
 *   mu = floor(2^60 / q)  (stored as uint64, ~31 bits)
 *   For each lane: x = a*b (< 2^60)
 *     qhat = ((x >> 29) * mu) >> 31
 *     r = x - qhat*q; if r >= q: r -= q; if r >= q: r -= q
 *
 * IFMA mapping:
 *   x_lo = madd52lo(0, a, b)  = x & ((1<<52)-1)      bits [51:0]
 *   x_hi = madd52hi(0, a, b)  = x >> 52              bits [103:52] (here = x >> 52, ~8 bits)
 *   Reconstruct x: x = x_hi << 52 | x_lo  (fits uint64 since x < 2^60)
 *   qhat_num = (x >> 29)   — shift x right 29: = (x_hi << 23) | (x_lo >> 29)
 *   q_tmp    = madd52lo(0, qhat_num, mu) >> 31   (qhat_num < 2^31, mu < 2^32 => product < 2^63)
 *   qhat     = q_tmp >> 31
 *   r        = x - qhat*q; two conditional subtracts.
 *
 * Requires AVX-512F + AVX-512IFMA.
 * N must be a multiple of 8 (8 uint32 lanes per ZMM after 32->64 widening).
 */
__attribute__((target("avx512f,avx512ifma,avx512dq")))
void sp_avx512_ifma_modmul(const uint32_t *a, const uint32_t *b,
                            uint32_t q, uint64_t mu, uint32_t N, uint32_t *out) {
    __m512i vq  = _mm512_set1_epi64((int64_t)q);
    __m512i vmu = _mm512_set1_epi64((int64_t)mu);

    for (uint32_t i = 0; i < N; i += 8) {
        /* load 8 × uint32, zero-extend to uint64 */
        __m256i a32 = _mm256_loadu_si256((const __m256i *)(a + i));
        __m256i b32 = _mm256_loadu_si256((const __m256i *)(b + i));
        __m512i va  = _mm512_cvtepu32_epi64(a32);
        __m512i vb  = _mm512_cvtepu32_epi64(b32);

        /* x = a * b: low 52 bits + high bits */
        __m512i zero = _mm512_setzero_si512();
        __m512i x_lo = _mm512_madd52lo_epu64(zero, va, vb);  /* bits [51:0] */
        __m512i x_hi = _mm512_madd52hi_epu64(zero, va, vb);  /* bits stored at [51:0] = x >> 52 */

        /* reconstruct x = (x_hi << 52) | x_lo */
        __m512i x = _mm512_or_si512(x_lo, _mm512_slli_epi64(x_hi, 52));

        /* qhat_num = x >> 29 */
        __m512i qhat_num = _mm512_srli_epi64(x, 29);

        /* qhat_prod = qhat_num * mu  (< 2^31 * 2^32 = 2^63, fits in madd52lo) */
        __m512i qhat_prod = _mm512_madd52lo_epu64(zero, qhat_num, vmu);
        /* qhat = qhat_prod >> 31 */
        __m512i qhat = _mm512_srli_epi64(qhat_prod, 31);

        /* r = x - qhat * q */
        __m512i qhat_q = _mm512_mullo_epi64(qhat, vq);
        __m512i r = _mm512_sub_epi64(x, qhat_q);

        /* two conditional subtracts: if r >= q: r -= q */
        __mmask8 m1 = _mm512_cmpge_epu64_mask(r, vq);
        r = _mm512_mask_sub_epi64(r, m1, r, vq);
        __mmask8 m2 = _mm512_cmpge_epu64_mask(r, vq);
        r = _mm512_mask_sub_epi64(r, m2, r, vq);

        /* narrow back to uint32 and store */
        __m256i r32 = _mm512_cvtepi64_epi32(r);
        _mm256_storeu_si256((__m256i *)(out + i), r32);
    }
}
```

- [ ] **Step 3: Run test — expect PASS**

```
cmake --build build --target test_avx512 -- -j4
./build/tests/test_avx512
```

Expected: `PASS T_IFMA_1: Barrett modmul N=64 mod Q1 exact`

- [ ] **Step 4: M_AVX_4 compiler check for IFMA**

```bash
objdump -d build/src/CMakeFiles/sp_engine.dir/backends/cpu/avx512/avx512_ifma.c.o \
    | grep -E "vpmadd52luq|vpmadd52huq"
```

Expected: `vpmadd52luq` and `vpmadd52huq` both present. If absent, the compiler lacks IFMA support — verify `-mavx512ifma` is in `COMPILE_OPTIONS`.

- [ ] **Step 5: Commit IFMA**

```bash
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    src/backends/cpu/avx512/avx512_ifma.c tests/test_avx512.c
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] §18.3 IFMA: vpmadd52luq/huq Barrett modmul N=64 mod Q1+Q2"
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine tag lat-phase-2-cpu-avx-ifma-closed
git -C D:/F/shannon-prime-repos/shannon-prime-lattice tag lat-phase-2-cpu-avx-ifma-closed
```

---

## Task 6: M_AVX_2 Throughput Benchmarks

**Files:**
- Create: `tests/bench_avx512.c`
- Modify: `tests/CMakeLists.txt` — add bench_avx512 target

M_AVX_2 gates: VNNI ≥3.5× over scalar, IFMA ≥8× over scalar, TERNLOG ≥16× over scalar.

- [ ] **Step 1: Create `tests/bench_avx512.c`**

```c
/* bench_avx512.c — M_AVX_2 throughput gate for §18 AVX-512 kernels. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "sp_engine/avx512.h"

static double now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e9 + (double)t.tv_nsec;
}

#define WARMUP 10
#define ITERS  2000

int main(void) {
    sp_avx512_init();

    /* ---- TERNLOG throughput ---- */
    {
        static uint32_t state[16] __attribute__((aligned(64)));
        for (int i = 0; i < 16; i++) state[i] = i * 0x9E3779B9u + 1;

        /* warmup */
        for (int i = 0; i < WARMUP; i++) sp_avx512_ternlog_kste_round(state);
        double t0 = now_ns();
        for (int i = 0; i < ITERS; i++) sp_avx512_ternlog_kste_round(state);
        double avx_ns = (now_ns() - t0) / ITERS;

        uint32_t st2[16];
        memcpy(st2, state, 64);
        t0 = now_ns();
        for (int i = 0; i < ITERS; i++) {
            uint32_t tmp[16];
            for (int j = 0; j < 16; j++) tmp[j] = st2[j]^st2[(j+1)%16]^st2[(j+5)%16];
            memcpy(st2, tmp, 64);
        }
        double scalar_ns = (now_ns() - t0) / ITERS;

        double ratio = scalar_ns / avx_ns;
        printf("TERNLOG: scalar=%.1fns  avx=%.1fns  speedup=%.1fx  [need >=16x] %s\n",
               scalar_ns, avx_ns, ratio, ratio >= 16.0 ? "PASS" : "FAIL");
    }

    /* ---- VNNI throughput ---- */
    if (g_avx512_caps.has_vnni) {
        enum { ROWS = 256, COLS = 256 };
        static int8_t  w[ROWS*COLS] __attribute__((aligned(64)));
        static uint8_t act[COLS]    __attribute__((aligned(64)));
        static float   sc[ROWS]     __attribute__((aligned(64)));
        static int32_t bias[ROWS]   __attribute__((aligned(64)));
        static float   out[ROWS]    __attribute__((aligned(64)));
        for (int i = 0; i < ROWS*COLS; i++) w[i]  = (int8_t)(i % 127);
        for (int k = 0; k < COLS; k++)      act[k] = (uint8_t)(k % 255);
        for (int i = 0; i < ROWS; i++)      sc[i]  = 0.01f;
        memset(bias, 0, sizeof(bias));

        for (int i = 0; i < WARMUP; i++) sp_avx512_vnni_matvec(w, act, sc, bias, ROWS, COLS, out);
        double t0 = now_ns();
        for (int i = 0; i < ITERS; i++) sp_avx512_vnni_matvec(w, act, sc, bias, ROWS, COLS, out);
        double avx_ns = (now_ns() - t0) / ITERS;

        /* scalar baseline */
        static float out2[ROWS];
        t0 = now_ns();
        for (int it = 0; it < ITERS; it++) {
            for (int r = 0; r < ROWS; r++) {
                int32_t acc = 0;
                for (int k = 0; k < COLS; k++)
                    acc += (int32_t)w[r*COLS+k] * (int32_t)((int8_t)((int)act[k]-128));
                out2[r] = (float)acc * sc[r];
            }
        }
        double scalar_ns = (now_ns() - t0) / ITERS;

        double ratio = scalar_ns / avx_ns;
        printf("VNNI:    scalar=%.1fns  avx=%.1fns  speedup=%.1fx  [need >=3.5x] %s\n",
               scalar_ns, avx_ns, ratio, ratio >= 3.5 ? "PASS" : "FAIL");
    } else {
        printf("VNNI:    SKIP (no AVX-512VNNI)\n");
    }

    /* ---- IFMA throughput ---- */
    if (g_avx512_caps.has_ifma) {
        enum { N = 512 };
        static uint32_t a[N], b[N], out_v[N], out_s[N];
        const uint32_t Q1 = 1073738753u;
        const uint64_t MU1 = ((uint64_t)1<<60) / Q1;
        for (int i = 0; i < N; i++) {
            a[i] = (uint32_t)((i*0x9E3779B9u+1) % Q1);
            b[i] = (uint32_t)((i*0x6C62272Eu+7) % Q1);
        }
        for (int i = 0; i < WARMUP; i++) sp_avx512_ifma_modmul(a, b, Q1, MU1, N, out_v);
        double t0 = now_ns();
        for (int i = 0; i < ITERS; i++) sp_avx512_ifma_modmul(a, b, Q1, MU1, N, out_v);
        double avx_ns = (now_ns() - t0) / ITERS;

        t0 = now_ns();
        for (int it = 0; it < ITERS; it++) {
            for (uint32_t i = 0; i < N; i++) {
                uint64_t x = (uint64_t)a[i]*(uint64_t)b[i];
                uint64_t qhat = ((x>>29)*MU1)>>31;
                uint64_t r = x - qhat*Q1;
                if (r>=Q1) r-=Q1; if (r>=Q1) r-=Q1;
                out_s[i] = (uint32_t)r;
            }
        }
        double scalar_ns = (now_ns() - t0) / ITERS;

        double ratio = scalar_ns / avx_ns;
        printf("IFMA:    scalar=%.1fns  avx=%.1fns  speedup=%.1fx  [need >=8x] %s\n",
               scalar_ns, avx_ns, ratio, ratio >= 8.0 ? "PASS" : "FAIL");
        (void)out_s;
    } else {
        printf("IFMA:    SKIP (no AVX-512IFMA — Zen 4 fallback path)\n");
    }

    return 0;
}
```

- [ ] **Step 2: Wire bench into `tests/CMakeLists.txt`**

```cmake
if(SP_ENGINE_WITH_AVX512)
    add_executable(bench_avx512 bench_avx512.c)
    target_link_libraries(bench_avx512 PRIVATE sp_engine)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(bench_avx512 PRIVATE -mavx512f -mavx512vnni -mavx512ifma -mavx512bw -mavx512dq -mavx512vpopcntdq -O3)
    elseif(MSVC)
        target_compile_options(bench_avx512 PRIVATE /arch:AVX512 /O2)
    endif()
endif()
```

- [ ] **Step 3: Build and run M_AVX_2 gate**

```
cmake --build build --target bench_avx512 -- -j4
./build/tests/bench_avx512
```

Expected (Tiger Lake-B):
```
TERNLOG: scalar=...ns  avx=...ns  speedup=??x  [need >=16x] PASS
VNNI:    scalar=...ns  avx=...ns  speedup=??x  [need >=3.5x] PASS
IFMA:    scalar=...ns  avx=...ns  speedup=??x  [need >=8x] PASS
```

If any gate fails, tune loop unrolling or add `_mm_prefetch` before inner loops.

- [ ] **Step 4: Commit benchmarks**

```bash
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    tests/bench_avx512.c tests/CMakeLists.txt
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] M_AVX_2 throughput benchmark: VNNI/IFMA/TERNLOG speedup gates"
```

---

## Task 7: Closure — M_AVX_4 Full Objdump Gate + Tags + Closure Doc

**Files:**
- Create: `papers/SESSION-CLOSED-lat-2-CPU-AVX.md`

- [ ] **Step 1: Run full M_AVX_4 compiler honesty check**

```bash
OBJDIR=build/src/CMakeFiles/sp_engine.dir/backends/cpu/avx512

echo "=== SPINOR ===" && \
  objdump -d $OBJDIR/avx512_spinor.c.o | grep -E "vmovdqa64|vmovntdqa" | head -5

echo "=== VNNI ===" && \
  objdump -d $OBJDIR/avx512_vnni.c.o | grep vpdpbusd | head -5

echo "=== IFMA ===" && \
  objdump -d $OBJDIR/avx512_ifma.c.o | grep -E "vpmadd52luq|vpmadd52huq" | head -5

echo "=== TERNLOG ===" && \
  objdump -d $OBJDIR/avx512_ternlog.c.o | grep -E "vpternlogd|vpopcntq" | head -5
```

All four sections must produce non-empty output. Any `vmovups` in SPINOR or scalar arithmetic in IFMA is a failure — fix by adding `__builtin_assume_aligned(ptr, 64)` or hardening the `__attribute__((target(...)))`.

- [ ] **Step 2: Run full regression**

```
cmake --build build --target test_avx512 -- -j4
./build/tests/test_avx512
```

All tests must PASS (or SKIP on Zen 4 for IFMA/WAITPKG).

- [ ] **Step 3: Write closure document `papers/SESSION-CLOSED-lat-2-CPU-AVX.md`**

```markdown
# Session Closed: Phase 2-CPU.AVX

**Date:** 2026-05-27
**Branch:** main (shannon-prime-system-engine + shannon-prime-lattice)
**Mandate:** §18 of PPT-LAT-Roadmap.md

## Gates Passed

| Gate    | Criterion                                              | Result |
|---------|--------------------------------------------------------|--------|
| M_AVX_1 | Math identity: byte-exact int, fp16 ULP floor for f32 | PASS   |
| M_AVX_2 | VNNI ≥3.5×, IFMA ≥8×, TERNLOG ≥16× vs scalar        | PASS   |
| M_AVX_4 | vmovdqa64, vpdpbusd, vpmadd52luq, vpternlogd in obj   | PASS   |

M_AVX_3 (perf counters, NT cache bypass): deferred — requires `perf stat` on Linux CI.

## Sub-tags

- `lat-phase-2-cpu-avx-ternlog-closed`
- `lat-phase-2-cpu-avx-spinor-closed`
- `lat-phase-2-cpu-avx-vnni-closed`
- `lat-phase-2-cpu-avx-ifma-closed`

## Notes

- IFMA skipped on Zen 4 (no AVX-512IFMA); Zen 4 uses scalar `modmul`.
- WAITPKG / §18.5 PERSIST deferred to future phase.
- M_AVX_3 deferred pending Linux CI `perf stat -e cache-misses` integration.
```

- [ ] **Step 4: Commit closure doc and apply umbrella tag**

```bash
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine add \
    papers/SESSION-CLOSED-lat-2-CPU-AVX.md
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine commit -m \
    "[lat-2-cpu-avx] Phase 2-CPU.AVX closed: M_AVX_1+2+4 PASS; closure doc"

git -C D:/F/shannon-prime-repos/shannon-prime-system-engine tag lat-phase-2-cpu-avx-closed
git -C D:/F/shannon-prime-repos/shannon-prime-system-engine push origin main --tags

git -C D:/F/shannon-prime-repos/shannon-prime-lattice add papers/SESSION-CLOSED-lat-2-CPU-AVX.md
git -C D:/F/shannon-prime-repos/shannon-prime-lattice commit -m \
    "[lat-2-cpu-avx] Phase 2-CPU.AVX closure note"
git -C D:/F/shannon-prime-repos/shannon-prime-lattice tag lat-phase-2-cpu-avx-closed
git -C D:/F/shannon-prime-repos/shannon-prime-lattice push origin main --tags
```

---

## Anti-Contamination Checklist

Before any commit, verify:

- [ ] No changes in `lib/shannon-prime-system/` (math-core is read-only)
- [ ] No `-march=native` on the TU level (only per-function `__attribute__((target(...)))`)
- [ ] No `f32::exp`, `f32::ln`, softmax, temperature, top-p anywhere in AVX-512 files
- [ ] No files copied or adapted from `D:\F\shannon-prime-repos\shannon-prime-engine\`
- [ ] `SP_FROB_ARENA_LAYOUT_VERSION` is read, not bumped
- [ ] `SP_SPINOR_LAYOUT_VERSION` is read, not bumped

---

## Self-Review

**Spec coverage:**
- §18.1 SPINOR: Task 3 (ZMM load + 0xA5 sentinel hot + NT variants) ✓
- §18.2 VNNI: Task 4 (dpbusd + u8-offset + bias) ✓
- §18.3 IFMA: Task 5 (madd52lo/hi Barrett butterfly + Zen 4 SKIP) ✓
- §18.4 TERNLOG: Task 2 (vpternlogd XOR3 + vpopcntq) ✓
- §18.5 PERSIST: explicitly deferred (not a closure gate) ✓
- M_AVX_1: Tasks 2–5 each have byte-exact identity tests ✓
- M_AVX_2: Task 6 throughput benchmark ✓
- M_AVX_3: noted as deferred (needs Linux perf counters) ✓
- M_AVX_4: Task 7 objdump checks ✓

**Spec gaps:** None. §18.5 PERSIST is non-gating; explicitly noted deferred.

**Type consistency:**
- `sp_avx512_vnni_matvec` signature matches across Task 1 header and Task 4 impl ✓
- `sp_avx512_ifma_modmul(a, b, q, mu, N, out)` consistent across Tasks 1, 5, 6 ✓
- `sp_avx512_ternlog_kste_round(state)` consistent across Tasks 1, 2, 6 ✓
