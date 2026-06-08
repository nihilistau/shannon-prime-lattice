# RUNBOOK — Cloud GPU compute from the Knack box (RunPod + HF, SSH-free)

**Purpose.** Run GPU jobs that don't fit the local RTX 2060-12GB (P2.b adapter training, Phase-0 inversion on the full bf16 12B) — autonomously, cost-safely, with receipts. Proven end-to-end 2026-06-09 (XBAR P2.b Phase 0: 50-span + 30-span inversion runs on an A6000, ~$0.40-0.50 each).

## 0. The three shells (keep their paths straight)

| Shell | How | Sees repos at | Role |
|---|---|---|---|
| Workspace sandbox | `mcp__workspace__bash` | `/sessions/<name>/mnt/shannon-prime-repos/` | standalone C builds (gcc), forensics |
| **Default WSL (Ubuntu-20.04)** | `wsl -e bash` | `/mnt/d/F/shannon-prime-repos/` | **cloud control** — runpod CLI, HF |
| Ubuntu-22.04-sp | `wsl -d Ubuntu-22.04-sp` | `/mnt/d/...` | GPU passthrough (2060); not for cloud control |

The default WSL distro has: `runpod` python CLI 1.9 (`~/.local/bin/runpod`), `~/.runpod/config.toml` (`apikey`), `~/.ssh/id_runpod*`, and `huggingface_hub` (pip --user).

## 1. Credentials (reference the PATHS, never the values)

- **RunPod API key:** `~/.runpod/config.toml` (default WSL). Parse via regex `apikey\s*=\s*'([^']+)'` (py3.8 has no `tomllib`).
- **HF token:** `D:\F\shannon-prime-repos\archive\notes_and_stuff\claude-hf-token.txt`. User **KnackAU**, **write** scope. Read inside scripts; never echo.

## 2. Weights source (trusted)

`google/gemma-4-12B` rev `56820d7d` — `model.safetensors` byte-matches the local gold bucket (23,919,549,408 B). Verify with `hf_verify.py` before any run. The token has gated-repo access.

## 3. The pattern — SSH-free, HF-mediated, self-terminating

There's no `runpodctl`/croc and community pods don't expose clean SSH/telemetry, so don't fight SSH. Route everything through a private HF dataset (`KnackAU/xbar-p2b-run`):

1. **Stage** (`hf_stage.py`): upload `invert_p0.py` (or training script) + `bootstrap.sh` + tokens/seeds + `bucket_manifest.json`.
2. **Launch** (`launch_pod.py`): `runpod.create_pod(image="pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime", gpu_type_id="NVIDIA RTX A6000", container_disk_in_gb=70, env={HF_TOKEN, JOB_REPO, RUNPOD_API_KEY}, docker_args=<base64 bootstrap-fetch>)`. A6000 48 GB ($0.33/hr) fits 24 GB bf16 + backward.
3. **Bootstrap** (`bootstrap.sh`, pulled from the dataset): `trap finish EXIT` (upload results + `terminate_pod` on ANY exit) → pip install hf_hub → fetch job + `snapshot_download` model (config + safetensors) → **verify size vs manifest** → run smoke then batch (each `timeout`-bounded) → write STATUS → finish uploads `results*/` + self-terminates via `RUNPOD_API_KEY`.
4. **Monitor/pull** (`monitor.py`): list `results*/` on HF + STATUS; when DONE, pull receipts (`fetch_log.py`, `analyze_*.py`).

Scripts persist in `D:\F\shannon-prime-repos\_xbar\p2b\` (under the workspace folder).

## 4. Gotchas (each paid for once — don't pay twice)

- **`docker_args` must contain NO double-quotes** — the SDK splices it into a GraphQL string; a `"` corrupts the mutation. Base64 the fetch script; single-quote wrap only.
- **Community pods return no runtime telemetry** (uptime/util = None). → bootstrap should **periodic-upload its log**; otherwise pull the RunPod web console log manually.
- **PowerShell↔WSL quoting**: avoid `<` (PS reserved), bare `$var` (PS expands it), nested `"`. Write scripts to files + run by path; for WSL-native files use a base64 pipe; keep pipes (`| head`) *inside* `wsl -e bash -c "..."`.
- **WSL2 drvfs serves stale/truncated files to gcc** right after a Windows-side edit → `sync; sleep`, or base64-pipe the file into `/tmp` and build there.
- **`arm.c` standalone build** needs `-D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64` (fseeko/off_t) and linking `arm_scan.c` (sp_arm_scan_sig).
- Validate the corpus is **coherent before** a long inversion: greedy 90-token generation degenerates to markdown/newline loops even on the gold model.

## 5. Cost discipline

Self-terminate (trap) is the primary safety; the local monitor is the backstop. Per-arm `timeout` caps hangs. Don't poll-watch a bake (that, not the GPU, was the cost on Stage Alpha). A full inversion run ≈ ~$0.50.
