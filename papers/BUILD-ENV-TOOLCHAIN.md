---
type: runbook
title: "BUILD-ENV-TOOLCHAIN — the canonical from-clean build of the wire-cuda daemon (and why it kept breaking)"
description: "The authoritative, receipts-backed procedure to build shannon-prime-system-engine from a CLEAN tree on the dev box, plus the toolchain map and the exact gotchas that have repeatedly broken clean-build and fed the restart cycle. Root cause (2026-06-28): env-cpu.bat had drifted to MSVC cl.exe, which cannot compile the math-core's __int128 (exact_islands.c). Fix: CPU/math-core builds with clang-cl (MSVC-ABI). Verified GREEN end-to-end, engine commit a69fac7."
tags: [runbook, build, toolchain, clang-cl, cuda, msvc, mingw, clean-build, anti-drift, foundational]
timestamp: 2026-06-28T00:00:00Z
resource: shannon-prime-repos/shannon-prime-system-engine/scripts/env/env-cpu.bat
sp_status: GREEN
sp_gate: G-CLEAN-BUILD
sp_commit: a69fac7
sp_repro: "see §3 (the three stages); each must end without error and produce its artifact"
---

# BUILD-ENV-TOOLCHAIN

> **Read this before touching any build script or concluding the engine is rotted.** Driving the rebuild on 2026-06-28 exposed that the engine did not build from a clean tree — not because of rot, but because `env-cpu.bat` had drifted to the wrong compiler. This doc is the anti-drift fix.

## 0. The one rule that ends the restart cycle

**The CPU / math-core build uses `clang-cl`, NOT `cl.exe`.** The math-core uses `__int128` (`core/exact_islands/exact_islands.c`), C11 `<stdatomic.h>`, and other GCC/Clang constructs. **PROVEN 2026-06-28:** `clang-cl -fsyntax-only exact_islands.c` → OK; `cl.exe` → `error C4235: '__int128' keyword not supported`. `clang-cl` supports them AND emits **MSVC-ABI** `.lib` archives that the `x86_64-pc-windows-msvc` cargo daemon links. A prior session flipped `env-cpu.bat` to `cl.exe` ("MSVC + Ninja") — that single drift makes clean-build RED and is a prime cause of the 23 restarts. **Do not revert it.**

## 1. Toolchain map (all present on the dev box — nothing is missing)

| Role | Toolchain | Where | Notes |
|---|---|---|---|
| **CPU / math-core (engine `build-cpu`, MSVC-ABI `.lib`)** | **clang-cl** | `C:\Program Files\LLVM\bin` | uses VS2019 headers/libs via `vcvars64`; supports `__int128`/stdatomic |
| CUDA host (engine `build-host-cuda-backend`) | VS2019 BT + CUDA 13.2 (nvcc) | `SP_PIN_VS_BUILDTOOLS` / `SP_PIN_CUDA_ROOT` | the byte-exact CUDA avoids `__int128` (dual-prime, fits u64) |
| Daemon (cargo) | `stable-x86_64-pc-windows-msvc` | rustup | links the clang-cl `.lib` (MSVC ABI) + the CUDA `.lib` |
| math-core dev/test (system repo `build/`) | MinGW-gcc-15.2 | `C:\ProgramData\mingw64\mingw64\bin` | the `T_KSTE`/`T_NTT`/`T_ARM` gates run here (GNU ABI; separate from the daemon's `build-cpu`) |
| Tier-3 MSVC-parity only | VS2022 (VS18) | `D:\Program Files (x86)\Microsoft Visual Studio\18` | never for CPU/CUDA production |

env pins live in `engine/scripts/env/env-common.bat`. `env-cpu.bat` now sets `CC=CXX=clang-cl` + LLVM on PATH after `vcvars64`.

## 2. The two separate math-core builds (do not confuse them)
- **system repo `shannon-prime-system/build/`** = MinGW-gcc, GNU ABI, for the math-core's own ctest gates (T_KSTE etc.). Green.
- **engine `shannon-prime-system-engine/build-cpu/`** = clang-cl, MSVC ABI, the archives the *daemon* links. This is the one that was broken.

## 3. The from-clean build (the canonical chain)

For the served wire-cuda 12B daemon (`--features wire_cuda_backend`):

1. **Math-core (clang-cl, AVX512 off for the CUDA daemon, tests off):**
   ```
   call scripts\env\env-cpu.bat   (sets clang-cl)
   cmake -S . -B build-cpu -G Ninja -DCMAKE_BUILD_TYPE=Release ^
         -DSP_ENGINE_WITH_AVX512=OFF -DSP_ENGINE_BUILD_TESTS=OFF -DSP_SYSTEM_BUILD_TESTS=OFF
   cmake --build build-cpu --config Release -j
   ```
   → 22 `.lib` under `build-cpu/lib/shannon-prime-system/core/`.
2. **CUDA backend (nvcc + VS2019 host):** `call tools\sp_daemon\build-host-cuda-backend.bat` → `build-host-cuda-backend\sp_cuda_daemon_backend.lib` (contains `cuda_forward.cu`).
3. **Daemon link (cargo, MSVC):**
   ```
   call scripts\env\env-cuda.bat
   set "CARGO_TARGET_DIR=<engine>\tools\sp_daemon\target-wirecuda"
   cd tools\sp_daemon
   cargo build --release --features wire_cuda_backend
   ```
   → `target-wirecuda\release\sp-daemon.exe`. **Verified GREEN 2026-06-28 (`Finished release in 27.84s`; daemon serves "7 times 8 is 56.").**

A clean runner is `engine/_build_kvfound.bat` (stages 1–3 with rc logging). Gate **G-CLEAN-BUILD** = all three stages succeed + the daemon binds :3000 and answers a smoke prompt.

## 4. Gotchas that have bitten (each cost a debugging cycle)
- **`cl.exe` can't do `__int128`** → use clang-cl (the rule, §0).
- **AVX512 under clang-cl:** `cl.exe`-style `/arch:AVX512` doesn't enable VNNI → "Cannot select VPDPBUSD". For the CUDA daemon, build `-DSP_ENGINE_WITH_AVX512=OFF` (it runs on GPU; CPU AVX512 kernels aren't needed). If CPU-AVX512 is ever required, pass clang `-mavx512vnni -mavx512bw …` per-TU.
- **`-DSP_ENGINE_BUILD_TESTS=OFF`** for the daemon build — `tests/bench_avx512.c` uses POSIX `clock_gettime`/`CLOCK_MONOTONIC` (not on MSVC/clang-cl).
- **`build-host-cuda-backend.bat` lacks a final `exit /b 0`** → returns a spurious non-zero even on success; a wrapping `if errorlevel 1` will false-FAIL. (Fixed: add `exit /b 0`.)
- **cmd `set VAR=val && cmd`** captures a trailing space into VAR — always quote: `set "VAR=val"`.
- **Stale build dir:** changing the compiler requires deleting `build-cpu` so cmake reconfigures (the compiler is cached on first configure).

## 5. Anti-drift
- `env-cpu.bat` carries a loud "DO NOT revert to cl.exe" comment.
- `okf_mem` fact: "clean-build FIXED — CPU=clang-cl" (supersedes the earlier RED finding).
- This runbook is the single source for the build; `engine/CLAUDE.md` + `lattice/CLAUDE.md` point here.
- Suggested gate to add to the Stage-0 battery once a cheap clean-build smoke exists: `G-CLEAN-BUILD`.
