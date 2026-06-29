---
type: reference
title: "PPT-LAT-FRAMEWORK-INDEX — keywords, SHAs, flags, gates, cross-links"
description: "Fast-lookup companion to PPT-LAT-FRAMEWORK-API.md. Pure index: keyword -> location, the exhaustive SP_* env-flag table (flag/file:line/effect/default), the G-* gate registry, the MTP-campaign commit SHAs, and the alias cross-links (terms that resolve to the SAME endpoint/concept, e.g. feature == dnx == gemma4_kv_capture_feat == gemma4_forward_feat; stop == eos_ids == <turn|>=106 == turn_stop_ids). Grep this first."
tags: [reference, index, keywords, sha, flags, gates, cross-links, aliases, lut]
timestamp: 2026-06-29T00:00:00Z
resource: shannon-prime-repos
sp_status: ACTIVE
sp_gate: G-OKF-CONFORM
sp_commit: 5689e3f
sp_repro: "synthesized with PPT-LAT-FRAMEWORK-API.md from the same 6-agent survey; flag/gate/commit tables are direct extractions at this commit"
---

# PPT-LAT-FRAMEWORK-INDEX

> Companion to **`PPT-LAT-FRAMEWORK-API.md`** (the breadth reference). This file is the *grep target*: keyword → where, every flag, every gate, the SHAs, and the aliases that point at one concept. `§N` refs are sections of the API doc.

## §K — Keyword → location

| Keyword | Location (file:line / fn) | API § |
|---|---|---|
| apply_template_ids | daemon tokenizer.rs:612 | §6.2 |
| arch_id enum | core sp/sp_model.h (GEMMA4=7, GEMMA4_ASSISTANT=10) | §3.1 |
| byte-exact forward | cuda_forward.cu (`SP_BYTEEXACT`, d_bx_flag); CONTRACT-BYTEEXACT-forward.md | §4,§6.3 |
| C2 signature | recall.rs:21-85 (Projection::signature) | §5.1 |
| capture_feat (EAGLE feature) | cuda_forward.cu:4567 | §4.2 |
| chat endpoint | routes.rs `/v1/chat` (run_kvdecode_chat) | §6.1,§6.4 |
| draft (MTP/EAGLE) | gemma4_draft_open/step/close cuda_forward.cu:4624/4677/4658 | §4.3 |
| draft forward (oracle/CPU/CUDA) | eagle/sp_eagle_ref.py / sp_eagle_fwd.c / sp_eagle_fwd_cuda.cu | §8.2 |
| dtype ids | core sp/sp_model.h (OK_Q4=11, OK_Q8=10, OK_Q4B=13) | §3.1 |
| eos_ids / stop | tokenizer.rs:296 (find_eos_ids :270; <eos>=1, <turn|>=106) | §6.2 |
| feature tap (CPU) | gemma4_forward_feat core/forward/gemma4.c:308 | §3.3 |
| feature tap (served) | gemma4_kv_capture_feat cuda_forward.cu:4567 | §4.2 |
| Frobenius episode codec | curator/frob_episode.py; core/vht2/spinor_block.c | §5.1 |
| inject seam (residual memory) | gemma4_kv_inject/_seq/_tokens cuda_forward.cu:4744/4776/4882 | §5.4 |
| KV tap | gemma4_forward_kvtap core/forward/gemma4.c:315 (g4_kv_tap) | §3.3 |
| KAIROS tick | kairos.rs / kairos_runner.rs (SP_KERNEL/SP_KAIROS_ALPHA) | §5.3 |
| kvdecode backend reg | sp_session_register_kvdecode_backend sp_session.c:909 | §3.2 |
| MEM-OKF store | lattice tools/okf_mem.py + memory-okf/ | §5.5 |
| model load | sp_model_load io_format/sp_model_load.c:119 | §3.2 |
| nightshift curator | nightshift_curator.rs (extract_secret, admit) | §5.3 |
| rewind / commit | gemma4_kv_rewind/_commit cuda_forward.cu:4465/4495 | §4.2 |
| ring (Ring-1/2/3) | core/arm/arm.c; sp_g4_kv dKc/dVc; RFC-XBAR | §5.1 |
| sampler / suppress | sampler.rs:123 (with_suppress), :171 (mask) | §6.3 |
| session create | sp_session_create sp_session.c:78 | §3.2 |
| sp_arch_info | core sp/sp_l1.h (256-B arch_struct payload) | §3.1 |
| sp_g4_kv struct | cuda_forward.cu:3865 | §4.1 |
| suppress_token_ids | tokenizer.rs:559 (config_suppress 258882/258883) | §6.2 |
| transcode | engine tools/sp_transcode/sp_transcode.c | §8.2 |
| W_c recall head | recall.rs:534 (WcHead), :557 (wc_score) | §5.2 |

## §F — SP_* env flags (exhaustive)

| Flag | Read at | Effect | Default |
|---|---|---|---|
| SP_MODEL_PATH / SP_TOKENIZER_PATH | main.rs:102/104 | target model + tokenizer | "" |
| SP_DRAFT_MODEL_PATH / _TOKENIZER_PATH | main.rs:108/111 | spec-decode draft | "" |
| SP_MEMO_MODEL_PATH / _TOKENIZER_PATH | main.rs:115/119 | /v1/dialogue memory model | "" |
| SP_POUW_LEDGER_PATH | main.rs:126 | append PoUW receipts | "" |
| SP_HTTP_PORT / SP_QUIC_PORT | main.rs:132/129 | HTTP / QUIC mesh port | 8080 / 0 |
| SP_PEERS / SP_RING2_SERVE / SP_RING2_PEER | main.rs:138/216/231 | QUIC peers / Ring-2 peer store | "" |
| SP_DAEMON_BACKEND | daemon.rs:359… | cpu\|cuda\|hex\|vulkan | unset |
| SP_DAEMON_KVDECODE | daemon.rs:585 | resident KV decode (12B chat) | unset |
| SP_DAEMON_KVDECODE_PMAX/_RING_W/_JMAX | daemon.rs:597/607/614 | resident budget / SWA ring / journal | arch |
| SP_CUDA_DECODE_INT8 | cuda_forward.cu:2444 / sp_eagle_accept.rs | tied-head INT8 decode (required for kv_open) | "1" |
| SP_BYTEEXACT | cuda_forward.cu:595/2433 | exact-integer islands + CRT-NTT attn | off |
| SP_ENGINE_NTT_ATTN / SP_ENGINE_FP16 | cuda_forward.cu:7279/7291 | NTT exact attn (prefill) / f16 acts | off |
| SP_G4_KV_GRAPH / _RING_W / _JMAX | cuda_forward.cu:4043/4311/4312 | CUDA-graph decode / ring / journal | off/0/64 |
| SP_XBAR_SWA_W / _RING | cuda_forward.cu:2331/2334 | SWA window / ring mode | model |
| SP_ARM_SHADOW/_GATHER/_ORACLE/_SLAB | cuda_forward.cu:2349… | P3 router shadow / recall-set / oracle | off |
| SP_REPLAY_MTARGET / _ALPHA | cuda_forward.cu:4848 / routes.rs | episode replay target / K·V scale | off |
| SP_DRAFT_ASCALE | cuda_forward.cu:4689 | draft attn scale: one\|rsqrt | rsqrt |
| SP_RECALL_REGISTRY | daemon.rs:650 / routes.rs:937 | episode registry JSONL path | unset |
| SP_AUTO_RECALL_DEFAULT | routes.rs:424 | default auto_recall | unset |
| SP_PERSIST_KV | routes.rs:767 | O(1) conversation KV reuse (LCP) | off |
| SP_DECIDE / SP_FORGET | routes.rs:769/770 | memory agency decide / forget | off |
| SP_B4_NIGHTSHIFT | routes.rs:771 | between-turn consolidation (capture turn) | off |
| SP_B3_JUDGE | routes.rs:772 | generative memory-injection judge | off |
| SP_B3_DISPOSER / _TAU | routes.rs:773/1811 | ablation oracle (ΣΔLL) / threshold | off / ∞ |
| SP_B3_WC | recall.rs / routes.rs | learned W_c recall selector | off |
| SP_B3_QK_TOPM / SP_B3_TAU_QK | routes.rs:977/982 | q·K top-m / relevance threshold | 8 / ∞ |
| SP_B3_QK_COSINE / SP_B3_QDUMP | recall.rs:140 / routes.rs:994 | cosine q·K / dump queries | off |
| SP_INT2 / _W / _K / _TAU | routes.rs:774/1024/1026/1077 | Stage-2 cull / window / budget / threshold | off/20/20/−8 |
| SP_EOT_BIAS / SP_EOT_DEBUG | routes.rs:1986/1968 | end-of-turn logit bias / rank log | 0 / off |
| SP_NIGHTSHIFT_OFFLINE / _LIVE / _PERSIST | main.rs:157/160 / routes.rs:649 | offline curator / live dir / persist registry | off/_nightshift_live/off |
| SP_KERNEL | (kairos) | enable KAIROS heartbeat | off |
| SP_KAIROS_ALPHA/_MODEL/_TOK/_TAPE/_REPORT | main.rs:171… | KAI-1 alpha runner | unset |
| SP_KAIROS_NOTHINK/_CHATML/_PRUNE/_SALIENCE_POLICY | kairos_runner.rs:170… | think-suppress / template / idle-prune / policy | off |
| SP_OKF_MEM / _ROOT / _PY | nightshift_curator.rs:147 | OKF model / root / python | "" / memory-okf / python |
| SP_DG_WCACHE / _PREFIXKV / _TRACE | cuda_forward.cu:6182… | diffusion weight cache / prefix-KV / trace | off |
| SP_CURRENT_CONVO / SP_B4_DIAG | routes.rs:320 / daemon.rs:735 | consolidation hook / B4 diag | unset |

## §G — Gate registry (G-*)

- **EAGLE/MTP:** G-EAGLE-DRAFT-FWD-C (`73314ac`), G-EAGLE-DRIVE-C (`fab177a`), G-EAGLE-DRAFT-FWD-CUDA (`726733c`), G-EAGLE-ACCEPT (live, `5689e3f`).
- **Byte-exact:** G-BYTEEXACT-FORWARD-12B, G-BYTEEXACT-ISLANDS-CUDA, G-BYTEEXACT-ATTN-NTT, G-BYTEEXACT-ATTN-12B, G-ISLANDS-Q-REF.
- **Chat full-stack:** G-CHAT-A1, A2, A2-POLISH (`cc4e26c`), B1 (`66e30bc`), B2-RING-DEBUG, S1 (`58b6c2d`), B3-WC-{DEPLOY,DIV2}, B3, B4, FULLSTACK.
- **Wire-CUDA:** G-WIRE-CUDA-DECODE-GEMMA4 (32/32==oracle, the null-floor), G-WIRE-CUDA, G-WIRE-CUDA-GEMMA4.
- **Ring-3 / integer:** G-R3-BIND, -BIND-OK, -DUALROUTE, -MOBIUS, -NIGHTSHIFT, -LOSS, -VSA, -PROV; G-NORM-INTEGER, G-ISLANDS-INTEGER; G-XBAR-ORGANISM(-FULL); G-R2-FROB(-AB/-ENTROPY/-PARITY).
- **Spec-decode (C4):** G-SPEC-WIRE(-NULLFLOOR/-PARITY), G-SPEC-ACCEPT-12B, G-SPEC-BASELINE-12B, G-SPEC-ISLAND, G-SPEC-SCHED; G-PONCELET-CORR (oracle killed).
- **Memory/curator:** G-NIGHTSHIFT-CURATOR, G-MEMO-{LOOP,CUE,NULL}, G-CHAT-B3-WC-DIV2 (360/361 + 50/50).
- **Persist/perf:** G-PERSIST-KV-REWIND (`b566c2a`), G-CTX-SCALE, G-P3-{SHARED,PPL,R2,GEOM,VLESS,WIN}.
- **DG / diffusion:** G-DG-N0..N6, G-DG-PREFIXKV(-PARITY/-PROD), G-DUALGPU-RESIDUE, G-DIFFJUDGE-OOD-H2H, G-DIFFJUDGE-NATIVE.
- **KAIROS:** G-KAIROS-0..6, G-KAIROS-SOAK, G-KAIROS-3-{GNA-HW,AUDIO}.
- **Harness:** G-HARNESS-{AGENCY,CONVMEM,DAEMON,MEMTOOLS,TOOLCALL,HOOK,KAIROS-TICK}-E2E.
- **Build/format:** G-CLEAN-BUILD, G-OKF-CONFORM, G-MEM-OKF-CONFORM, G-CROSS-COMPILE.
- **Transcode/MTP-new (this campaign):** G-MTP-TRANSCODE (`d6ee0f7`), G-EAGLE-DRAFT-FWD-C/-CUDA, G-EAGLE-DRIVE-C, G-EAGLE-ACCEPT-LIVE.

## §S — MTP-campaign commit SHAs (engine)

`d6ee0f7` transcode gemma4-assistant→sp-Q4 · `ed28fe6` numpy oracle (G-EAGLE-DRAFT-REF) · `73314ac` C draft forward (G-EAGLE-DRAFT-FWD-C) · `fab177a` K-step drive (G-EAGLE-DRIVE-C) · submodule `98b0032`→parent `af858e1` feature tap (gemma4_forward_feat) · submodule `3ccd1f1`→parent `19e1cb8` KV tap (gemma4_forward_kvtap) · `beebac6` served feature tap (gemma4_kv_capture_feat) · `726733c` CUDA draft forward (G-EAGLE-DRAFT-FWD-CUDA) · `6092a97` draft loader (gemma4_draft_open) · `933715b` draft step (gemma4_draft_step) · `5689e3f` live probe (sp_eagle_accept). Pre-campaign anchors: `a69fac7` clang-cl build fix + G-BYTEEXACT/G-WIRE-CUDA-DECODE-GEMMA4 · `58b6c2d` G-CHAT-S1 (coherent gemma4 chat, byte-exact default) · `b566c2a` G-PERSIST-KV-REWIND · `cc4e26c` G-CHAT-A2-POLISH (control-token suppression).

## §X — Cross-links / aliases (terms that resolve to ONE concept)

- **"feature" / "the hidden" / "inp_h seed"** == post-`output_norm` hidden == `dnx` (cuda_forward.cu:4249) == captured by `gemma4_kv_capture_feat` (served) == emitted by `gemma4_forward_feat` (CPU ref) == `embedding_length_out`=3840.
- **"stop" / "turn terminator" / "EOS"** == `eos_ids` == `<eos>`=1 + `<turn|>`=106 == `turn_stop_ids()` (105/106) == `find_eos_ids` + `load_generation_config eos_token_id`.
- **"suppress" / "soft tokens" / "placeholders"** == `suppress_token_ids()` == `generation_config.json suppress_tokens` (258882/258883) + pipe-controls `<*|>` + named specials == masked −∞ in `Sampler::sample` (sampler.rs:171).
- **"frame" / "chat template" / "turn structure"** == `apply_template_ids` == `<|turn>`=105 (start) / `<turn|>`=106 (end) — NOT `<start_of_turn>`/`<end_of_turn>` (the gemma3-on-gemma4 bug).
- **"draft" / "MTP" / "EAGLE" / "gemma4-assistant" / "arch 10"** == `SP_ARCH_ID_GEMMA4_ASSISTANT`=10 == `gemma4_draft_*` (CUDA) == `sp_eagle_*` (tools) == nextn.pre/post_projection + 4 Q-only layers reading target KV.
- **"the served decode" / "resident KV" / "the ring"** == `sp_g4_kv` == `gemma4_kv_*` == `dKc/dVc` == `run_kvdecode_chat` == `SP_DAEMON_KVDECODE`.
- **"recall" / "autonomous memory" / "W_c"** == `recall.rs wc_score` == `SP_B3_WC` == q·K relevance == C2-sig registry (`SP_RECALL_REGISTRY`).
- **"inject" / "memory as residual" / "the seam"** == `gemma4_kv_inject`/`_seq`/`_tokens` == `inject_frames`/`single_entry` == the post-embed residual override (NOT tokens).
- **"O_K" / "dual-prime" / "byte-exact carrier"** == Q(√−163) == q1=1073738753 q2=1073732609 == CRT-NTT (`core/ntt_crt`) == `SP_BYTEEXACT` == G-R3-BIND / G-BYTEEXACT-*.
- **"anti-rebuild" / "don't rebuild" / "lookup first"** == MEM-OKF == `okf_mem.py lookup` == LUT→summary→full == binding pre-flight (prompt.md §0/§8).
- **"served model"** == `gemma4-12b-b1.sp-model` (8.79 GB) + `gemma4-12b-b1.sp-tokenizer` (the daemon `--model`).
- **"the build"** == clang-cl (CPU, env-cpu.bat) + nvcc sm_75 (CUDA, env-cuda.bat) + cargo `--features wire_cuda_backend --target-dir target-wirecuda`.
