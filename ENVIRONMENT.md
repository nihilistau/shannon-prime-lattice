# ENVIRONMENT.md — the operational environment (tools, lanes, credentials, gotchas)

**Role:** the single source of truth for HOW this project's compute, cloud, and credential
plumbing works. `prompt.md` says what the project IS; this says what the *toolbox* is and how
not to cut yourself on it. Every gotcha below was paid for once — don't pay twice.
**Maintained by:** Claude, operator-delegated. Last full update: 2026-06-11.
**Companion (SECRETS — never committed, never echoed):**
`D:\F\shannon-prime-repos\archive\notes_and_stuff\creds\claude-credentials.txt`

---

## 1. The credentials registry (read this before touching any cloud)

`archive\notes_and_stuff\creds\claude-credentials.txt` — per-service blocks: accounts
(primary first), token values, interfaces/CLIs, **renewal procedures**, last-verified stamps.

Rules: (a) token VALUES live only there (plus service-native caches it names) — memory, chat,
commits, logs reference the PATH, never values; (b) `archive/` is outside every git repo by
design — verify before ever moving it; (c) on any auth failure, check the registry's renewal
block FIRST; (d) new service/account/token → update the registry + its Last-verified stamp.
The HF token is ALSO at `archive\notes_and_stuff\claude-hf-token.txt` (the path the `_xbar/p2b`
scripts read) — keep the two in sync.

**Account map (the part that bites):** `knack112358@gmail.com` = HF (KnackAU, PRO) + RunPod +
primary Google (Drive 5TB / Cloud / Workspace) + primary GitHub. `nihilistcod@gmail.com` =
the Colab CU account, operator-nicknamed **"nihilistau"** (also his public GitHub handle --
do not "correct" Colab auth to knack112358).

## 2. Compute lanes

| Lane | What | When |
|---|---|---|
| **Local** | Beast Canyon: i9-11900KB, 32 GB RAM, RTX 2060-12GB (sm_75), Optane E:(16G)/F:(32G) | all gates/deploys; builds per `shannon-prime-system-engine/docs/BUILD-ENV.md` (MinGW gcc 15.2 `build/` = canonical CPU; VS2019+CUDA `build-cuda/`). **XBAR host-lane native math (2026-06-18):** the exact-integer O_K bind/store (`core/ntt_crt`+`core/poly_ring`: `sp_pr_mul`/`ntt_forward`/`sp_pr_inner`/`sp_pr_score_kstore`) is reachable from the host Ring-3/curator python via **ctypes against the engine lib** — already linked into `sp_engine_cuda`, **no new linkage** (the `gemma4_kv_*` cache is pure f32; the only int8 path is the weight gemv). If a standalone shared lib is needed for ctypes, build it from the math core (`build/` MinGW). Frozen primes q1=1073738753, q2=1073732609, M=1152908312643096577. **BYTE-EXACT / wire-CUDA build (2026-06-18):** the CUDA backend for the byte-exact-forward + daemon-driven 12B builds under **VS18 BuildTools** (`D:\Program Files (x86)\Microsoft Visual Studio\2022\18\BuildTools`, cl 14.50) + **CUDA 13.2** (`build-cuda-vs22/`); the daemon's CUDA path is the cargo feature **`wire_cuda_backend`** (off = null floor; gate `T_WIRE_CUDA_RUNTIME_ACTIVE`), `build.rs` links `sp_cuda_daemon_backend.lib` + cudart/cublas. The universal crate's HOST bins (the byte-exact scalar references + comparators — `sp_islands_q_ref_test`, `bx_islands_compare`, `sp_matmul_q_ref` gates) run via `cargo run --bin <name>` in `tools/sp_dsp_smoke`, **host x86, NO GPU/DSP** (the L2 reference lane). The 12B byte-exact gate itself (`test_gemma4_ppl_cuda` under `SP_BYTEEXACT`) needs the warm CUDA build + the `gemma4-12b-b1.sp-model`/`.sp-tokenizer` pair **CHAT / AUTONOMOUS RECALL (2026-06-20):** `run_console.bat` (engine root) launches the served coherent byte-exact O(1)-context 12B chat at http://127.0.0.1:3000/; `run_console_recall.bat` is the same launcher + the B3-WC autonomous librarian armed (3 env vars: `SP_RECALL_REGISTRY=_needle_corpus_div\registry.jsonl`, `SP_B3_WC=_b3_wc\wc_deploy.bin`, `SP_REPLAY_MTARGET=42`; PMAX 4096 for the 12 GB card). Deploy blob rebuilt via `python tools\xbar_lsh\export_wc_deploy.py`. |
| **RunPod (BAKE)** | multi-hour/multi-seed training runs; HF-mediated SSH-free pattern: `papers/RUNBOOK-cloud-compute.md` + scripts in `D:\F\shannon-prime-repos\_xbar\p2b\` | batch=1 => cheapest-card-that-fits (A6000 first; ladder {A6000,L40S,L40,A40,RTX6000Ada}); per-UNIT upload inside the loop; verify-then-terminate; **after any launch error, reconcile `get_pods` TWICE with delay -- a client timeout does not mean no pod was created (duplicate-pod incident 2026-06-10)**; `kill_pod.py` for surgical termination |
| **Colab (PROTOTYPE)** | `colab` CLI in WSL (`~/.local/bin`); smokes on T4 (~2 CU/hr), first real runs on A100 40GB (~12 CU/hr); 100 CU ~= 8.5 A100-h -- does NOT hold a 20h seed | `colab run --gpu T4 script.py` = new+exec+stop one-shot w/ exit codes; kernel state persists across `exec`; secrets piped into the kernel (`echo "import os; os.environ['HF_TOKEN']='...'" | colab exec`); ALWAYS `colab stop`; never run repl/console/auth/drivemount interactively from an agent; full notes: memory `reference-colab-cli-lane` + source `C:\Projects\google-colab-cli-main` |
| **Google (gws)** | `C:\Projects\google-workspace-cli-x86_64-pc-windows-msvc\gws.exe` -- Discovery-dynamic Drive/Gmail/Calendar/Sheets/etc., project `sp-ppt-arm-lat`, 9 scopes, smoked green 2026-06-11 | API params via `--params '<JSON>'` (NOT flags); `--format table|json|yaml|csv`; `--page-all`; renewal `gws auth login`; consent screen is Testing-mode -- account must be on the test-user list (Cloud Console -> Auth Platform -> Audience). **Linux gws needs glibc >=2.39 -> does NOT run on Ubuntu 20.04 WSL; the Windows exe is canonical.** gcloud 572: Windows `C:\Projects\google-cloud-sdk` (authed), WSL `~/google-cloud-sdk` (not authed) |
| **HF (RECEIPTS+WEIGHTS)** | PRO. Private dataset `KnackAU/xbar-p2b-run` = run receipts + job staging; gold weights bucket verified per RUNBOOK §2 | every cloud run exports receipts here; fetch scripts in `_xbar/p2b/` |
| **GNA (EAR -- SW emu + physical HW)** | Intel GNA 2.0 on the local Beast Canyon (i9-11900KB, driver `gna_03.05.00.2116`). Toolchain = **OpenVINO 2023.3 _archive_ runtime via `setupvars` + system py3.8** (the pip wheel LACKS the GNA plugin -- mixing pip+archive ABI-fails both ways; the archive is a single self-consistent ABI island). | `GNA_SW_EXACT` i16 emulation runs in WSL (no driver needed); **`GNA_HW` on the real silicon is native-Windows only** (WSL2 has no GNA MMIO passthrough). Conv constraints: no padding (VALID-only) + filters multiple-of-4. POT GNA-native i16 PTQ = full FP32 recovery (0.877). Full recipe: memory `reference_gna_openvino_toolchain`; tooling `engine/tools/audio_port/{ov_gna_score,pot_gna_quantize}.py` + `run_gna_hw.bat` + `GNA_HW_BRINGUP.md` |

## 3. The three shells (paths + each one's trap)

| Shell | Sees repos at | Trap |
|---|---|---|
| PowerShell MCP (Windows -- builds, git, gates, gws, launches) | `D:\F\shannon-prime-repos\` | **kills foreground at ~40s** -> targeted ninja/ctest -R, `Start-Process` + log-tail for long work; **quoting eats `$var`/`<`/nested quotes -> write a script FILE and run by path**; PS 5.1 parses scripts as ANSI -> **ASCII-only in .ps1** (em-dashes break parsing); detached scripts: redirect stderr to a file or failures are invisible; cmd.exe `.cmd` files dodge PS parsing entirely |
| WSL Ubuntu-20.04 (cloud control: runpod/colab/HF/gcloud) | `/mnt/d/F/shannon-prime-repos/` | drvfs serves stale/truncated files to gcc right after Windows-side edits; background `nohup` children can die with the session -> detach via Windows `Start-Process wsl ...`; stdout is BUFFERED when piped (`PYTHONUNBUFFERED=1` or URLs/progress never appear); OAuth listeners: kill stale ports first (`fuser -k 8200/tcp`) |
| Linux sandbox (`mcp__workspace__bash` -- standalone gcc, forensics, python) | `/sessions/<name>/mnt/shannon-prime-repos/` | **mount pins stale PARTIALS of just-edited files** -> stage authoritative content into `/tmp` (heredoc) and build there; git status here shows phantom CRLF churn -- Windows-side git is authoritative |

Interactive TUIs (gws auth setup/login, anything crossterm): **never launch hidden** -- terminals
are type-blocked for desktop control; relaunch with `-WindowStyle Normal` and the operator
drives Enter/arrows. Browser OAuth flows: localhost redirects forward from the Windows browser
into WSL listeners (proven :8200, :8085).

## 4. Storage law

D: = working SSD (repos, models -- watch free space; transcodes need ~40 GB peak). E:/F: =
Optane, RESERVED for Ring-2 spill. **G: = Google Drive stream: writes MUST go under
`G:\My Drive\` -- root-level dirs are silently discarded by the client** (paid for 2026-06-10).
H: = bulk cold models (the suite's reference GGUFs/ref.bins were restored FROM here -- check H:
before re-downloading anything). `D:\Files\Models\` pinned paths feed the engine test suite.
Engine `models\`: `.sp-model` headers are SHA-paired to their `.sp-tokenizer` -- **never move a
non-`.pre115` file out of `models\`** (pairing breaks 12B text-in; restored 2026-06-10).

## 5. Why it's set up this way (the reasoning, once)

Bake-vs-prototype split: RunPod bills cash but holds 20h+ runs; Colab CU are pre-paid but cap
at ~8.5 A100-h -- so seeds bake on RunPod, mechanism smokes and first-runs prototype on Colab.
HF as the receipts bus: community pods have no telemetry and terminate-skips-traps, so receipts
must stream OUT per-unit (30-min salvage uploads on long runs); a private HF dataset is the
only channel all lanes share. Per-account separation: CU entitlements (nihilistcod) vs paid
subscriptions (knack112358) don't mix; the registry exists because four services × two accounts
× rotating tokens exceeded what chat memory should carry. gws over the G: mount for anything
that matters: the API reports errors, the mount discards silently.

## 6. Session docs map

- `prompt.md` -- WHO/WHAT/HOW (canonical bootstrap; read first)
- `ENVIRONMENT.md` -- this file (toolbox + lanes + creds + gotchas)
- `SESSION-HANDOFF.md` -- WHERE THINGS STAND right now (in-flight runs, queue, last session's
  landings; updated at every session end / major handoff)
- `papers/PPT-LAT-STATE.md` -- the PROVEN record; contracts = forward specs; memory = the
  operational lessons index
