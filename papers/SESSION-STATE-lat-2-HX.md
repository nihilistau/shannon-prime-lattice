# SESSION-STATE-lat-2-HX

**Phase:** 2-HX — engine, Hexagon V69 HTP backend (`shannon-prime-system-engine`).
**Session date:** 2026-05-23.
**Status:** IN PROGRESS — HX.0/HX.1/HX.2-prep + **HX.2 (FastRPC round-trip) GREEN**; HX.3a (scalar-DSP forward) next.
**Worktree:** `D:\F\shannon-prime-repos\shannon-prime-system-engine\.claude\worktrees\agent-ad9c9f2f466528372`
**Branch:** `worktree-agent-ad9c9f2f466528372` (off `main` @ cc1aafd, the 2-CU close).
**Device:** adb serial `R5CT22445JA`, SM-S908E (Galaxy S22 Ultra), board `taro` = SM8450, Hexagon V69.

---

## Ground truth established this session (host probe)

- **Hexagon SDK is 5.5.6.0** at `C:\Qualcomm\Hexagon_SDK\5.5.6.0` (brief said 5.4.0.x; env-common.bat
  said 5.4.0.x — WRONG, fixed to 5.5.6.0). `HEXAGON_Tools` = `8.7.06`, `toolv87`. NDK `android-ndk-r25c`.
- **qaic.exe** at `ipc\fastrpc\qaic\WinNT\qaic.exe` — runs ("No input files given." on no-arg).
- **`build\cmake\hexagon_fun.cmake` line ~287 already patched** to `${proj-qaic_src}/WinNT/qaic.exe`
  (the `C:\Qualcomm` Controlled-Folder-Access workaround). DO NOT redo. Persists across builds.
- **ADB**: `D:\Files\Android\pt-latest\platform-tools\adb.exe` (newer than the disabled old ones).
  Device responds; `/data/local/tmp/sp22u` writable. Unsigned PD on domain 3 works (no signing).

## Inherited memories used (toolchain/protocol facts, NOT contaminated forward-pass code)

`reference_hexagon_build_recipe.md` + `reference_hexagon_working_setup.md` +
`project_hexagon_silent_fallback.md` (under AppData\Roaming\Claude\local-agent-mode-sessions\...\memory\).
These are SDK incantations + V69 HVX hardware facts the project itself recorded; the working-setup
explicitly says "fork the S22U project layout". Anti-contamination = no forward-pass CODE from
shannon-prime\, shannon-prime-engine\, shannon-prime-llama\backends\hexagon\. Fresh kernel cohort.

### V69 HVX gotchas (verified 2026-04-29, DO NOT rediscover)
1. Macro is `__HVX__` (not `__HEXAGON_HVX__`).
2. `-mhvx` NOT default for v69 — pass explicitly.
3. `-mhvx-ieee-fp` required for `Q6_Vsf_*` codegen — BUT see (7).
4. `qurt_hvx_lock(QURT_HVX_MODE_128B)` is thread-local; FastRPC dispatchers run methods on different
   worker threads — lock PER-METHOD inside each HVX-using function, not in open.
5. Stack arrays to HVX kernels need `__attribute__((aligned(128)))` (clang emits strict `vmem`).
6. DSP-side `malloc()` unreliable on unsigned PD — use stack arrays / rpcmem.
7. **`Q6_Vsf_*` IEEE single-float HVX family is STRUCTURALLY BROKEN on V69** (off 4-20 absolute,
   not rounding). FIX: do intermediate arithmetic in qf32 (`Q6_Vqf32_*`), convert sf->qf32 at
   input, qf32->sf only at final store (`Q6_Vsf_equals_Vqf32`). Bit-equiv to scalar within ~3.8e-6.
8. `Q6_Vw_equals_Vsf` (fp32->int32 vector) is V73+ only — V69 has no vector fp32->int8 past amax.

## ARCHITECTURE DECISION (load-bearing — settled before kernel code)

FastRPC is INTRA-DEVICE IPC (Android-arm -> cDSP) ON THE PHONE. A Windows host CANNOT FastRPC to the
phone's DSP. So unlike CUDA (which compiles device+host in one in-tree nvcc TU and runs on the dev box),
the Hexagon PPL gate REQUIRES sp_engine to cross-compile to **Android aarch64** and RUN ON THE PHONE.

The brief's "mirror the CUDA CMake block" is at the SHAPE level (a separate static lib + a ppl.c
`SP_BACKEND=hexagon` dispatch branch), NOT the literal build mechanics. Three artifacts per HX build:
  1. `sp_engine` + tests cross-compiled to **aarch64-android** (NDK r25c), with a new
     `sp_engine_hexagon` static lib = the FastRPC HOST STUB (host = phone's ARM side).
  2. `libsp_engine_hex_skel.so` — the DSP-side HVX skel, built SEPARATELY by the SDK's
     `build_cmake hexagon DSP_ARCH=v69` (hexagon-clang), NOT the engine MSVC/NDK toolchain.
  3. An Android-aarch64 test runner (mirror of test_ppl) that drives `sp_perplexity` with
     `SP_BACKEND=hexagon`, pushed + run via adb; results adb-pulled.

The existing `build-hexagon.bat` aims `CMAKE_TOOLCHAIN_FILE=toolchain-hexagon.cmake` at
`SYSTEM_NAME Generic / hexagonv69` — WRONG (cross-compiles the whole engine to the DSP, which can't
run a PPL test). Must be rebuilt as the aarch64-android host build + a separate SDK skel build.

KSTE = HOST `sp_kste_encode` (D->H copy of post-norm/post-RoPE K), same as 2-CU — NOT ported to HVX.
NTT-attn = int64 exact dot (== sp_pr_inner), NOT a CRT-NTT port.

## FASTRPC EXACT-ALLOC TRAP (suspect FIRST if PPL is gibberish)
rpcmem registration size MUST EQUAL the IDL length parameter EXACTLY. Over-alloc -> AEE_EUNSUPPORTED
(rc=0x4e=78) -> bridge silently zero-fills -> model RUNS but PPL is garbage. Plan every IDL length to
equal its allocation; per-call scratch sized exactly, never a slice of a max-sized buffer.

## Plan (dependency-ordered, mirrors HX.0..HX.7 ~ CU.0..CU.7)

- **HX.0** — env fixes (SDK 5.5.6.0, SP_ENGINE worktree local-hack, env-hexagon.bat goto-rewrite) +
  HARD GATE: build SDK `examples/calculator` end-to-end (DSP skel + android exe) and run on phone.
  Proves qaic + hexagon-clang + NDK + FastRPC + unsigned-PD all work. NO engine code until green.
- **HX.1** — aarch64-android sp_engine build (NDK toolchain) + on-phone test_ppl runner; CPU-on-phone
  PPL sanity (no DSP yet) to prove the runner + model load + tokenizer work on the device.
- **HX.2** — IDL + host stub + DSP skel scaffold (matmul first), FastRPC round-trip smoke.
- **HX.3** — HVX kernels: matmul, rmsnorm + QK-rmsnorm, NEOX RoPE, GQA windowed softmax attn,
  GeGLU/SwiGLU, embed-scale, residual; Frobenius arena decode (Q8 code*scale/127, Q4 nibble *scale/7).
  qf32 intermediate per gotcha (7).
- **HX.4** — hexagon_forward (gemma3) wired through ppl.c SP_BACKEND=hexagon.
- **HX.5** — NTT-attn int64 dot (E_HX_5), KL gate.
- **HX.6** — KSTE host-encode 3-part gate (E_HX_6).
- **HX.7** — T_FRO_4_HX: (a) hexagon-f32 PPL vs f16 oracle 32.86939 <=0.05% OR document an HVX
  precision floor; (b) per-row Q8 drift <=2%. Gemma3-1B f16.

## Progress log

### 2026-05-23 — orientation complete, architecture settled
Read CU session-state (full mirror reference), cuda_forward.cu structure, ppl.c dispatch,
src/CMakeLists.txt CUDA block, the 3 Hexagon memories, roadmap §8.5/§8.6.1. Device + SDK + qaic verified.
Architecture decision above recorded. Starting HX.0 env fixes + calculator hard-gate.

### 2026-05-23 — HX.0 env fixes done + HARD GATE (calculator) GREEN
- env-common.bat: SDK 5.4.0.x -> 5.5.6.0 (committable); SP_ENGINE worktree override (LOCAL HACK,
  not committed). env-hexagon.bat rewritten ASCII/goto (was box-drawing + parenthesised if-blocks
  that break on the SDK/VS "(x86)" paths); sources setup_sdk_env, prepends Git sh.exe, sets NDK r25c,
  ADB pt-latest, device serial/dir. Runs clean: build_cmake.exe + gow make + cmake all on PATH.
  (qaic NOT needed on PATH — hexagon_fun.cmake already calls WinNT\qaic.exe directly.)
- **HARD GATE PASSED.** Built SDK examples/calculator (copied to D:\F\hx-gate to dodge C:\Qualcomm CFA):
  `build_cmake hexagon DSP_ARCH=v69 BUILD=Release` -> libcalculator_skel.so (qaic ran:
  "Generating calculator_skel.c/_stub.c/.h"; hexagon-clang V69 compiled+linked).
  `build_cmake android HLOS_ARCH=64 BUILD=Release` -> calculator (ARM exe) + libcalculator.so (stub),
  NDK r25c clang 14.0.7. Pushed all 3 to /data/local/tmp/sp22u, ran:
  "Attempting to run on unsigned PD on domain 3 ... Call calculator_sum on the DSP ... Success".
  Proves qaic + hexagon-clang V69 + NDK + FastRPC + unsigned-PD-domain-3 all work on THIS host.
  Toolchain is NOT the problem from here. Next: HX.1 cross-compile sp_engine to aarch64-android.

### 2026-05-23 — HX.1 GREEN: sp_engine cross-compiles to aarch64-android + CPU-on-phone PPL PASS
- Verified the whole stack is portable: math-core has NO x86 intrinsics + STATIC libs; engine AVX2
  is guarded behind SP_ENGINE_AVX2 (set OFF for aarch64); gguf loader has a POSIX mmap path
  (MAP_PRIVATE/PROT_READ) beside the Win32 CreateFileMapping; no aligned_alloc/posix_memalign.
- CMakeLists.txt: added `option(SP_ENGINE_TARGET_ANDROID)` + `option(SP_ENGINE_WITH_HEXAGON)`.
  tests/CMakeLists.txt: gated the full suite behind `if(NOT SP_ENGINE_TARGET_ANDROID)` so the
  android build compiles ONLY test_ppl (the rest needs the Qwen3 model); test_ppl gets relative
  corpus/oracle defaults on android (resolved from CWD = the on-phone run dir).
- build-hexagon.bat REWRITTEN: was aiming a Generic/hexagonv69 toolchain at the WHOLE engine (would
  never run a PPL test). Now: `android` target cross-compiles via NDK r25c android.toolchain.cmake
  (ANDROID_ABI=arm64-v8a, PLATFORM=android-31, AVX/CUDA off) + a `dsp` target placeholder for the
  SDK skel (HX.2+). Cross-compile + link of sp_engine + math-core + test_ppl SUCCEEDS clean
  (only pre-existing -Wshadow tokenizer warnings).
- Build-script gotchas fixed: (1) caret line-continuations inside a parenthesised cmd if-block
  break on this host -> cmake configure is a single logical line. (2) env-hexagon's setup_sdk_env
  PATH-cleanup loop splits inherited spaced PATH entries ("Microsoft Visual Studio") into bare
  tokens it tries to run -> benign "'M' is not recognized" noise + nonzero residual errorlevel;
  fixed with `ver >nul` after the call + suppressing the call. (3) a multiply-edited .bat picked up
  a parse corruption; rewrote it fresh (UTF-8). Clean from-scratch rebuild via the script: GREEN.
- Pushed test_ppl (372 KB aarch64) + wiki.tiny.raw + wiki.tiny.oracle_ppl.txt to a CLEAN
  /data/local/tmp/sp22u/lat-hx/ (kept SEPARATE from prior contaminated-session artifacts in the
  parent dir). Pushed the 2.0 GB Gemma3-1B f16 GGUF to the parent (shared, push-once).
- **CPU-ON-PHONE PPL (aarch64, pure scalar f32) — T_FRO_4 PASS, checks=9 fails=0:**
  - f32 PPL = **32.86464** vs oracle f16 32.86939 -> **-0.0144%** (gate 0.05%). Matches desktop
    CPU/CUDA (-0.0146%) to 5 sig figs -> the cross-compile is FAITHFUL.
  - Q8 arena drift = **-0.7354%** (gate 2%), IDENTICAL to desktop CPU/CUDA.
  This is the HX discriminator the advisor flagged: ARM-vs-x86 honest f32 agree. The engine runs
  correctly on the phone. A correct HVX backend now only has to match THIS f32 baseline.
- env-common.bat SP_ENGINE worktree override confirmed working (SP_BUILD_DIR lands in the worktree).

### 2026-05-23 — HX.2-prep: rpcmem capacity probe GREEN (weight-upload architecture de-risked)
- src/backends/hexagon/rpcmem_probe.c (standalone aarch64 binary, pure rpcmem+cdsprpc, no DSP/IDL).
  On R5CT22445JA: single SYSTEM-heap rpcmem alloc OK at 64..2000 MB (all sizes probed).
  **Q8 arena (574.5 MB) single-buffer upload = FEASIBLE.** Device has 11.4 GB RAM / 6.3 GB avail.
- DECISION: HX.2 weight-upload mirrors CUDA build_weights — upload the Q8 arena into ONE
  DSP-visible rpcmem buffer (RPCMEM_HEAP_ID_SYSTEM=25 + RPCMEM_TRY_MAP_STATIC) at model load;
  matmul IDL takes a handle/offset, NOT a per-call weight tile. No partition-on-load needed.
- Wiring: src/backends/hexagon/CMakeLists.txt (early-return unless SP_ENGINE_TARGET_ANDROID; exact
  SDK 5.5.6.0 paths: rpcmem.a + libcdsprpc android_aarch64 + incs/stddef AEEStdDef + incs mmdefs +
  log/dl) + src/CMakeLists.txt add_subdirectory (mirrors CUDA block). build-hexagon.bat android
  builds test_ppl + rpcmem_probe. Verified clean rebuild + identical on-device re-run.
- Confirmed the Android test guard does NOT break the desktop build: CPU configure (Android OFF,
  AVX2=ON) green with the FULL test suite intact (test_avx/arena/forward/frob/gemma3/kste/etc.).
  Regression invariant holds.

## DURABLE HANDOFF FACTS (so the next session does NOT rediscover)

### env-common.bat LOCAL HACK (reapply, do NOT commit)
After `set SP_ENGINE=%SP_REPO_ROOT%\shannon-prime-system-engine`, the worktree build needs:
```
set SP_ENGINE=%SP_REPO_ROOT%\shannon-prime-system-engine\.claude\worktrees\agent-ad9c9f2f466528372
```
This line is UNSTAGED on purpose (committed env-common has only the SDK 5.4.0.x->5.5.6.0 bump).
If you take a fresh worktree, re-add this line pointing at YOUR worktree root.

### Working build incantations (verified)
- Toolchain hard gate (off-tree calculator): copy examples/calculator to a writable D: dir (C:\Qualcomm
  has Controlled Folder Access), then in the env-hexagon shell:
  `build_cmake hexagon DSP_ARCH=v69 BUILD=Release -gMake` and
  `build_cmake android HLOS_ARCH=64 BUILD=Release -gMake`. Push the 3 ship/ artifacts
  (libX_skel.so + libX.so + X exe), run `LD_LIBRARY_PATH=. ADSP_LIBRARY_PATH=. ./X` -> unsigned PD
  domain 3 -> Success.
- On-phone engine: `scripts\build\build-hexagon.bat android` (NDK aarch64, builds test_ppl +
  rpcmem_probe). Run dir convention: `/data/local/tmp/sp22u/lat-hx/` (CLEAN, separate from the
  parent dir's PRIOR-CONTAMINATED-SESSION artifacts: sp-engine, sp_hex, libsp_hex_skel.so, various
  ggufs — DO NOT use/link those). GGUF at parent `/data/local/tmp/sp22u/gemma-3-1b-it-f16.gguf`
  (pushed, 2.0 GB). adb = `D:\Files\Android\pt-latest\platform-tools\adb.exe`, serial R5CT22445JA.
  Run: `cd /data/local/tmp/sp22u/lat-hx && LD_LIBRARY_PATH=/vendor/lib64:. ADSP_LIBRARY_PATH=. ./test_ppl`.

### Batch-file parse traps resolved (don't relive the debugging loop)
1. Caret `^` line-continuations inside a parenthesised cmd `if (...)` block break on this host's
   spaced paths -> "'M' is not recognized". Put cmake invocations on a SINGLE logical line.
2. A multiply-Edit'd .bat picked up a parse corruption (same 'M' symptom even after fixing #1).
   Fix: rewrite the whole .bat fresh with Write (clean UTF-8). build-hexagon.bat is now clean.
3. setup_sdk_env.cmd's PATH-cleanup `for %%a in (%PATH%)` loop splits the inherited spaced
   "Microsoft Visual Studio" PATH entry into bare tokens it tries to run (cosmetic 'M' noise) AND
   leaves a nonzero residual errorlevel. Fixed in env-hexagon.bat with `ver >nul` after the call;
   callers should `call env-hexagon.bat 1>nul 2>nul` to suppress the noise.
4. hexagon_fun.cmake line ~287 is ALREADY patched to WinNT\qaic.exe — do NOT redo.

## NEXT (HX.2+): DSP/HVX backend — concrete action list
The on-phone CPU f32 PPL 32.86464 (-0.0144%) is the REFERENCE a correct HVX backend must match.
1. **IDL minimal-noop FIRST** (mirror calculator): `interface sp_hex : remote_handle64 { ... }` with
   one trivial method; build skel (build_cmake hexagon under src/backends/hexagon/dsp/) + host stub
   (NDK), FastRPC round-trip on device. Proves YOUR IDL/CMake wiring before any matmul logic. The
   build-hexagon.bat `dsp` target is stubbed for this (looks for src/backends/hexagon/dsp/CMakeLists.txt).
2. **Exact-alloc wrapper from day 1**: sp_hex_rpcalloc(n) that registers EXACTLY n bytes + logs
   (call_site,size). Every IDL `length` param == its buffer size. Over-alloc -> AEE_EUNSUPPORTED
   (rc=0x4e) -> silent zero-fill -> plausible-but-WRONG PPL. If HX.7 f32 PPL is structurally OK but
   numerically off, suspect THIS first (grep the alloc log vs IDL lengths).
3. **Weight upload (proven feasible)**: one SYSTEM-heap rpcmem buffer for the 574.5 MB Q8 arena at
   model load (RPCMEM_TRY_MAP_STATIC); matmul IDL takes handle/offset. Mirror cuda build_weights cache.
4. **HVX kernels — qf32 from line 1** (V69 gotcha 7: Q6_Vsf_* IEEE family is BROKEN, off 4-20 abs).
   Pattern: sf->qf32 at input, Q6_Vqf32_* in middle, Q6_Vsf_equals_Vqf32 at final store. Per-method
   `qurt_hvx_lock(QURT_HVX_MODE_128B)` (thread-local; FastRPC uses different worker threads). 128-byte
   aligned stack arrays. DSP malloc unreliable on unsigned PD -> stack/rpcmem. Kernel set mirrors
   cuda_forward.cu: matmul, rmsnorm + per-head QK-rmsnorm, NEOX RoPE, GQA windowed softmax attn,
   GeGLU/SwiGLU, embed-scale, residual + Frobenius arena decode (Q8 code*scale/127, Q4 nibble*scale/7).
5. **HX.4** hexagon_forward (gemma3) + ppl.c SP_BACKEND=hexagon dispatch branch (mirror the
   #ifdef SP_ENGINE_WITH_CUDA / SP_BACKEND=cuda branch; add #ifdef SP_ENGINE_WITH_HEXAGON). Do NOT
   add the dispatch until gemma3_forward_hexagon exists (won't compile otherwise).
6. **HX.5** NTT-attn = int64 exact dot (== sp_pr_inner), NOT CRT-NTT. Gate KL(f32||ntt)<=1e-7, KL_max>0.
7. **HX.6** KSTE = HOST sp_kste_encode (D->H copy of post-norm/post-RoPE K), NOT on HVX. 3-part gate:
   encoder determinism + signatures deterministic & wire-valid + Tier-0 label drift <=4 LSB vs CPU.
8. **HX.7** T_FRO_4_HX gate: (a) hexagon-f32 PPL vs f16 oracle 32.86939 <=0.05% OR document an HVX
   precision floor (analog of §8.6.1); (b) per-row Q8 drift <=2%.

### 2026-05-23 — HX.2 GREEN: sp_hex FastRPC IDL round-trip on device (main, post-integration)
Picked up on engine `main` (the 3-agent integration merged the HX foundation; worktree retired —
SP_ENGINE now points at the real repo, no local hack). Used `C:\Qualcomm\Hexagon_IDE\S22U` as
STRUCTURAL REFERENCE ONLY (IDL/skel/stub/host-split/CMake patterns) — no code copied; recreated fresh.
- Fresh `sp_hex` interface: `inc/sp_hex.idl` (`ping(in long, rout long)` smoke; whole-forward-on-DSP
  upload+forward methods land in HX.3a). `dsp/sp_hex_imp.c` + `dsp/CMakeLists.txt` → `build_cmake
  hexagon` builds `libsp_hex_skel.so` (qaic generates skel/stub/header; hexagon-clang V69). Host:
  `sp_hex_rt.c` + a qaic `add_custom_command` in `src/backends/hexagon/CMakeLists.txt` (qaic flags
  from the SDK `build_idl`: `-mdll -o <dir> -I<sdk>/incs -I<sdk>/incs/stddef`) → `test_hex_rt` (NDK
  aarch64) links the stub + rpcmem.a + libcdsprpc.so. `build-hexagon.bat android` builds it.
- **ON DEVICE (R5CT22445JA, unsigned PD domain 3): `sp_hex_ping(41) -> 42 (rc=0x0)` → HX.2 ROUND-TRIP OK.**
  OUR qaic/skel/stub/FastRPC/unsigned-PD wiring proven end-to-end before any HVX. Engine `4c5f6a2`.
- qaic-generated files NOT committed (build artifacts); only `inc/sp_hex.idl` is. `.gitignore`: SDK
  `build_cmake` output trees (`hexagon_*_toolv*/`, `android_*_aarch64/`).

## STATUS SUMMARY
- HX.0 GREEN (c99f613): env + qaic/hexagon-clang/NDK/FastRPC hard gate.
- HX.1 GREEN (da77dba): aarch64-android cross-compile + on-phone CPU PPL T_FRO_4 -0.0144%.
- HX.2-prep GREEN (e6bc5b2): rpcmem capacity probe, 574 MB Q8 single-buffer FEASIBLE.
- **HX.2 GREEN (4c5f6a2): sp_hex FastRPC IDL round-trip on device (ping 41->42).**
- HX.3..HX.7 NOT STARTED. **NEXT: HX.3a — scalar-f32 `sp_hex_forward` on the cDSP, gated to match the
  on-phone CPU PPL baseline (-0.0144%) BEFORE any HVX** (advisor discipline: this validates the
  per-tensor rpcmem upload + forward orchestration + exact-alloc with zero HVX risk; the silent-fallback
  trap lives here). Then HX.3b matmul→HVX qf32, then op-by-op, each PPL-gated. T_FRO_4_HX NOT reached.
- Math-core submodule at eca1bdc (NOT bumped).

### IDL design (settled for HX.3a)
Whole-forward-on-DSP. `sp_hex_upload_tensor(layer, slot, dtype, in buf, in len)` — per-tensor rpcmem
buffer (exact-alloc: len == bytes; ~28 buffers for Gemma3-1B, all < the 2000 MB probed ceiling; same
table for f32 gate (a) and Q8 gate (b)). `sp_hex_forward(in tokens[], n_tok, rout logits[])` — one
FastRPC call per chunk; the DSP runs the full gemma3 forward, returns logits. Single
`qurt_hvx_lock(QURT_HVX_MODE_128B)` at the top of `sp_hex_forward` (one method, one worker thread).
