---
type: contract
title: "CONTRACT — qwen36 (35B-A3B) served chat: wire the 337x hybrid ladder into sp-daemon"
description: "The productization contract for SPEED_NORTHSTAR: serve the qwen36 hybrid decode (state decode + GPU dense/experts/streaming, G-MOE-GPU4-PINNED 6.073 tok/s) through sp-daemon /v1/chat. S1 (the one-call C boot, sp_q36gpu_boot) is BUILT and compiled into the CUDA backend lib; S2 (Rust lane) and S3 (launcher+gate) are specced here to file/line so a fresh session starts cold and ships."
tags: [contract, qwen36, northstar, serve, daemon, gpu-residency]
timestamp: 2026-07-02T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-QWEN36-SERVE.md
sp_status: ACTIVE
sp_gate: "G-QWEN36-SERVE (spec §4, pending)"
sp_commit: "engine (S1 in the post-d9c4417 backend lib); submodule branch qwen36-gen-coherence"
sp_repro: "S1: sp_q36gpu_boot in src/backends/cuda/cuda_forward.cu; ladder receipts G-MOE-* in engine tests/fixtures/chat_fullstack/"
---

# CONTRACT — qwen36 served chat

**Why.** The 35B-A3B ladder is closed at **6.073 tok/s / 337×** (`G-MOE-GPU4-PINNED`) but lives
in a test harness. The deliverable is a served `/v1/chat` — the daemon runs the 35B the same
way the operator runs the 12B today.

## S1 — DONE (this session): the one-call C boot
`sp_q36gpu_boot(const qwen3_model *m, double moe_gb, int stream_on) -> void*` in
`src/backends/cuda/cuda_forward.cu`: uploads the dense set (852.5MB), uploads experts under
`moe_gb` (26/40 layers at 9.9GB), builds the per-layer streaming table, registers the INTERNAL
matmul + moe hooks (resident → streamed → CPU). Compiled into `sp_cuda_daemon_backend.lib`.
The daemon needs exactly ONE call after `sp_model_to_qwen36`.

## S2 — the Rust lane (fresh session, ~half day)
1. **FFI** (`tools/sp_daemon/src/ffi.rs`): `sp_model_to_qwen36(*const sp_model) -> *mut qwen3_model`
   (opaque), `qwen36_state_new/free/step`, `sp_q36gpu_boot`. LINK CHECK FIRST: the daemon's
   build.rs core-lib list must resolve `sp_model_to_qwen36` (core/session/sp_model_bridge.c —
   the perf-harness builds needed it as an extra TU; if the daemon link lacks it, add the
   bridge to the session module's CMake sources — do NOT duplicate the TU).
2. **Daemon boot branch** (`daemon.rs:~135`, after `arch_info()`): if `arch.arch_id == 8`
   (SP_ARCH_QWEN36): skip `SpSession::create` + kvdecode boot; `qm = sp_model_to_qwen36`;
   if `SP_Q36_GPU=1`: `sp_q36gpu_boot(qm, SP_Q36_GPU_MOE_GB|9.9, SP_Q36_GPU_STREAM|1)`.
   Stash `qm` (+boot handle) in AppState.
3. **Tokenizer** (`tokenizer.rs`): add `ARCH_QWEN36: u32 = 8` to `find_eos_ids`
   (`<|im_end|>`, `<|endoftext|>` — same names as ARCH_QWEN3) and to the chat-template arm
   (Qwen im_start/im_end format; verify against the model's own behavior — brick-2 showed the
   bare model quiz-drifts without its template, and llama-cli renders `<|im_start|>user…`).
4. **Chat lane** (`routes.rs` or a new `qwen36_chat.rs`): in `v1_chat`, when the qwen36 lane is
   active: `apply_template_ids(messages)` → `qwen36_state_new(m, SP_Q36_PMAX|4096)` → step over
   prompt ids (prefill; NOTE 0.16s/token — long conversations pay; batch-prefill is a known
   follow-up) → decode loop: `qwen36_step` → existing `sampler` over the logits row → SSE
   `{delta}` via the existing stream machinery, stop on eos/turn_stop/max_tokens →
   `qwen36_state_free`. Greedy first; sampler knobs after the gate.
5. **VRAM note**: the 2060 cannot host the 12B resident cache AND the 35B experts — the qwen36
   daemon instance is EXCLUSIVE (own port, own launcher). Do not try to co-serve.

## S3 — launcher + gate
`run_console_qwen36.bat`: env-cuda + **LLVM bin on PATH (libomp — 0xC0000135 silent death
otherwise, receipted 2x)** + `SP_MODEL_PATH=models/qwen36-35b-a3b.sp-model` +
`SP_Q36_GPU=1 SP_Q36_GPU_MOE_GB=9.9 SP_Q36_GPU_STREAM=1` + port 3001.
**G-QWEN36-SERVE**: (1) `/v1/chat` "What is the capital of France?" → coherent reply
containing "Paris"; (2) 3-turn conversation coherent; (3) measured serve tok/s ≥ 5 (the
harness ladder number minus template overhead); (4) rerun same prompt → identical stream
(greedy); (5) env dump in the receipt (re-baseline law).

## Phase-2 backlog (operator-ordered, RUNBOOK §15, tasks #35-38)
expert-count dial (SP_MOE_TOPK) · concurrent GPU/CPU expert lanes · re-do 26B diffusion GPU
with the 36B patterns · re-do gemma4-12B serve speed (INVESTIGATE the 1-vs-26 tok/s
discrepancy first — suspect: served byteexact default-ON).
