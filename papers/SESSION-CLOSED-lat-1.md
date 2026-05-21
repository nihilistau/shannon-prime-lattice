# SESSION-STATE-lat-1

**Phase:** 1 — Math core foundations (`shannon-prime-system`).
**Session date:** 2026-05-21.
**Status:** **Phase 1 CLOSED at Tier-1 + Tier-2.** All six subphases (1A–1F) green under Windows MinGW-gcc (Tier-1); integrated root `ctest` = **6/6** (T_OK, T_NTT, T_PR, T_VHT, T_FRO, T_KSTE), whole-build UBSan sweep clean. Linux gcc CI green (Tier-2, run 26235084222). Tag `lat-phase-1-closed` cut on both repos. Tier-3 (MSVC) is a separately-tracked follow-up wave, not a close blocker (§3.7).

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

1. **Tier-2 (Linux CI)** — not yet confirmed. Push all repos to trigger `.github/workflows/ci.yml`; verify the run is green before declaring Phase 1 fully closed.
2. **Scaffold: add a `DEPENDS` arg to `sp_add_module`** (1C feedback). Currently a dependent module appends `target_link_libraries(sp_<m> PUBLIC sp_<dep>)` after the call and only the root build links. A `DEPENDS sp_ntt_crt` arg (helper does the link, optionally find-or-add_subdirectory the dep) would make dependent modules uniform and standalone-buildable. Phase 2 will have many inter-module deps — worth doing before then.
3. **Tier-3 (MSVC)** — deferred wave: T_NTT_3, and MSVC runs of T_VHT_5 / T_KSTE_4. Plan: configure each module in a second build dir via `vcvarsall x64`; the `__int128` oracle can't compile on MSVC, so generate a checked-in reference fixture from the gcc build. Note: `.gitignore` blocks `*.bin` — use a `.h` fixture (C array) or add a `.gitattributes` negation + `binary` attr.
4. **T_FRO_4** — runs in Phase 2 alongside E_CPU_3.
5. **Minor:** add `.gitattributes` (`*.bin binary`, settle CRLF) for the MSVC fixture wave; CRLF↔LF warnings on commit are cosmetic.

---

## Next session — pick up first

Phase 1 close is done (6/6 Tier-1, Tier-2 CI green, tagged `lat-phase-1-closed`, this file renamed to `SESSION-CLOSED-lat-1.md`). The fork:

1. **MSVC parity wave (Tier-3)** — close the deferred T_NTT_3 + MSVC runs of T_VHT_5 / T_KSTE_4. Configure each module via `vcvarsall x64` in a second build dir; the `__int128` oracle won't compile under MSVC, so generate a checked-in reference fixture from the gcc build (`.h` C array, not `.bin` — gitignored). Add `.gitattributes` (`*.bin binary`) while there. Then tag the full `lat-phase-1-closed` (all three tiers).
2. **Phase 2-CPU (engine)** — GGUF loader → Qwen3-0.6B Q8 forward pass, the reference anchor all other backends verify against (E_CPU_1..6). This is the project's centre of mass; the math core is now ready to consume.
3. **Scaffold polish** — add `sp_add_module(... DEPENDS ...)` before Phase 2 multiplies inter-module links.

Recommend 2 (Phase 2-CPU) as the higher-leverage path; the MSVC wave can run opportunistically since nothing downstream needs MSVC yet.
