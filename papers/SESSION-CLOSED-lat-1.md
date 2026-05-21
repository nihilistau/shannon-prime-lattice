# SESSION-CLOSED-lat-1

**Phase:** 1 — Math core foundations (`shannon-prime-system`).
**Session date:** 2026-05-21.
**Status:** **Phase 1 CLOSED — all three platform tiers green.** All six subphases (1A–1F): integrated `ctest` **6/6** (T_OK, T_NTT, T_PR, T_VHT, T_FRO, T_KSTE), UBSan-clean. Tier-1 Windows MinGW-gcc; Tier-2 Linux gcc CI; **Tier-3 Windows MSVC** (full suite 6/6 under VS2019 BT, plus a `windows-msvc` CI job — both CI jobs green, run 26237235573). Tag `lat-phase-1-closed` on both repos. Only Phase-1 item carried forward: T_FRO_4 (needs the Phase-2 forward pass).

---

## What was built

Phase 1 was executed by **parallel agent dispatch** over a shared, scaffold-first CMake harness. One coordinator built the harness, dispatched one agent per dep-free subphase (1A probe → 1B/1D/1F → 1C/1E waves), and integrated. Every module is self-contained under `core/<module>/` with its own `CMakeLists.txt`, sources, and one ctest entry.

### Scaffold (`shannon-prime-system`)
- `CMakeLists.txt` — EXISTS-guarded `add_subdirectory(core/<m>)` over a fixed `SP_MODULES` list; configures green before a module exists, so parallel agents never edit a shared file.
- `cmake/sp_module.cmake` — `sp_add_module()` → static lib `sp_<m>` + test exe `test_<m>` + `add_test(T_<TAG>)`; shared `-Wall -Wextra -Wshadow -Wconversion -Wsign-conversion -Wpointer-arith`; `SP_UBSAN` option with libubsan feature-detect → `-fsanitize-undefined-trap-on-error` fallback (MinGW-Builds ships no libubsan).
- `include/sp/sp_test.h` — header-only assert harness; `SP_CHECK`, `SP_CHECK_EQ_I64`, `SP_RUN(fn)` prints `[fn] PASS/FAIL`, `SP_DONE()` nonzero exit on any failure.
- `CONVENTIONS.md` — module template (standalone + add_subdirectory dual-mode), file-ownership rules, anti-contamination, platform-gate policy.
- `.github/workflows/ci.yml` — Tier-2 Linux gcc gate (ubuntu-latest, Ninja, ctest) on push/PR.

### Modules (Tier-1 Win MinGW-gcc green)
| Sub | Module | Test | Result |
|-----|--------|------|--------|
| 1A | `core/ok_arith` (`include/sp/ok_int.h`) | T_OK_1..6 | 163742 checks, 0 fail |
| 1B | `core/ntt_crt` (`include/sp/ntt_crt.h`) | T_NTT_1,2,4,5 (3 deferred) | green |
| 1D | `core/vht2` (`include/sp/spinor_block.h`) | T_VHT_1..6 | green |
| 1E | `core/frobenius` (`include/sp/frobenius_lift.h`) | T_FRO_1..3 (4 deferred) | green |
| 1F | `core/kste` (`include/sp/kste.h`) | T_KSTE_1..5 | green |
| 1C | `core/poly_ring` (`include/sp/poly_ring.h`) | T_PR_1..4 | green (KL=0) |

All built warning-free; all UBSan-clean (trap-on-error mode on MinGW).

**1C inner product:** ⟨q,k⟩ = (q ⊗ k*)₀, involution k*₀=k₀, k*ⱼ=−k_{N−j}; the negacyclic x^N=−1 sign cancels the involution sign, so coefficient 0 is the exact Euclidean dot (T_PR_2 KL measured exactly 0). `sp_poly_ring` links `sp_ntt_crt` (root build only; standalone single-module build does not link for this module).

**Integration lesson:** a `-Wsign-conversion` warning in `vht2.c` `sp_crc8` surfaced only under a *fresh* `-DSP_UBSAN=ON` build — incremental builds (and the 1D agent's standalone run) cached past it. Fixed (shift in unsigned). Always run the integrated UBSan build from a clean dir before closing.

### Frozen layouts / constants (load-bearing — do not change silently)
- **Spinor block (1D):** 63 bytes = `vht2_header[7]` (LE float32 scale, int8 exponent, uint8 basis_sel, uint8 reserved) + `mobius_body[55]` (int8 anchor coeffs at Möbius-permuted positions, `mobius(i)=17i mod n`) + CRC-8/SMBus checksum. `SP_SPINOR_LAYOUT_VERSION=1`.
- **KSTE tree (1F):** 64 bytes, T_{60,3} = fixed depth-3 arity-3 (1 root + 3 + 9). int32 input → 6 int16 order statistics/node. Tier-0 = root label (bytes 8..19), Tier-1 = 3 canonically-sorted children (bytes 20..55), reserved Tier-2 digest (56..63). Componentwise product partial order. `SP_KSTE_LAYOUT_VERSION=1`.
- **NTT (1B):** frozen primes q1=1073738753, q2=1073732609 (q−1 = 2^10·odd ⇒ **N ∈ {128,256,512}** only). ψ table per (N,q) found from base a=3. Barrett μ=floor(2^60/q) (μ1=1073744895, μ2=1073751039), all intermediates < 2^64, **no `__int128` in production** (configure-time guard in `core/ntt_crt/CMakeLists.txt`). Symmetric Garner CRT, q1⁻¹ mod q2 = 894602413, M = 1152908312643096577.
- **O_K (1A):** Q(√-163), ω=(1+√-163)/2, ω²=ω−41, N(a+bω)=a²+ab+41b², units {±1}, UFD.

---

## How to run the tests

```bash
cd D:/F/shannon-prime-repos/shannon-prime-system
cmake -B build -G Ninja -DCMAKE_C_COMPILER=gcc
cmake --build build
ctest --test-dir build --output-on-failure      # the regression runner; one section per T_*
# UBSan sweep:
cmake -B build-ubsan -G Ninja -DCMAKE_C_COMPILER=gcc -DSP_UBSAN=ON && cmake --build build-ubsan && ctest --test-dir build-ubsan
```
Single module (fast iteration): `cmake -B core/<m>/build -S core/<m> -G Ninja -DCMAKE_C_COMPILER=gcc` — **except `poly_ring`**, which links `sp_ntt_crt` and must build via the root.

Integrated root `ctest` at last full run (1A,1B,1D,1E,1F): **5/5 green** (T_OK, T_NTT, T_VHT, T_FRO, T_KSTE).

---

## Spec amendments made this session (`shannon-prime-lattice/papers/`)
- **Roadmap §3.7 (new):** three-tier platform gate — Tier-1 Windows MinGW-gcc (closes in-session), Tier-2 Linux gcc via CI, Tier-3 Windows MSVC (follow-up wave). `__int128` parity strategy: gcc dumps reference fixture, MSVC compares (no `__int128` on MSVC).
- **Roadmap §4.2/4.3/7.2/7.3/7.8 + Theory §2.3:** N capped to {128,256,512}; the frozen primes admit no 2N-th root at N=1024. Primes kept frozen (dominance-verification + DHT topology depend on the exact residues). User-confirmed decision.
- **Roadmap §7.5:** T_FRO_4 (Gemma3-1B PPL) deferred to Phase 2 — needs a forward pass that doesn't exist in Phase 1.

---

## Open / outstanding

1. ✅ **Tier-2 (Linux CI)** — green (`.github/workflows/ci.yml`, `linux-gcc`).
2. ✅ **`sp_add_module` `DEPENDS`** — done; `poly_ring` uses it, standalone build works. Helper auto-`add_subdirectory`s the sibling dep when its target is absent.
3. ✅ **Tier-3 (MSVC)** — done. T_NTT_3 compiles on every compiler and checks the production kernel against `core/ntt_crt/ntt_ref_vectors.h` (gcc-pre-generated from the `__int128` oracle by `ntt_gen_fixture.c`); T_NTT_2 self-skips on MSVC; oracle excluded from the MSVC test build. T_VHT_5 / T_KSTE_4 byte-identity pass under MSVC. `windows-msvc` CI job (VS2022 generator) added — both CI jobs green.
4. ✅ **`.gitattributes`** — `* text=auto` + `*.bin/*.gguf/*.safetensors binary`.
5. **T_FRO_4** — the only carried-forward item: runs in Phase 2 alongside E_CPU_3 (needs the forward pass + Gemma3-1B).

---

## Next session — pick up first

Phase 1 is fully closed (all three tiers green, tagged `lat-phase-1-closed`, scaffold polished, MSVC + CI durable). Next is **Phase 2-CPU (engine)** — the project's centre of mass:

- Repo: `shannon-prime-system-engine` (consumes the math core via `lib/shannon-prime-system` submodule — add the submodule pointer first, Phase-2 entry).
- Bring-up order (§8.1 per-backend template, B=CPU): **2-CPU.A** GGUF loader → **2-CPU.B** forward pass on **Qwen3-0.6B Q8** (within 1e-4 / 0.1% of llama.cpp logits) → **2-CPU.C** inline Frobenius-decompressed matmul (use `sp_frob_*`) → **2-CPU.D** AVX2 (+optional AVX512) → **2-CPU.E** NTT-attention wired in, sieve OFF (use `sp_pr_*` / `sp_ntt_*`) → **2-CPU.F** KSTE KV-cache encode behind `SP_KSTE_KV=1` (use `sp_kste_*`, `sp_spinor_*`).
- Tests E_CPU_1..6; **T_FRO_4** (Gemma3-1B PPL within 0.1%) runs here once the forward pass exists.
- The engine build uses the pinned scripts under `shannon-prime-system-engine/scripts/env|build/` (NOT the math-core gcc/Ninja flow). CPU env: `env-cpu*.bat`.
- Reuse the **scaffold-first + parallel-agent** pattern, but note Phase-2 cells are larger and more sequential within a backend (loader → forward → kernels), so parallelism is across backends/models, not within a single forward-pass bring-up.
