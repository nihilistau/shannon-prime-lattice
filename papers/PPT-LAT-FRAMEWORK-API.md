---
type: reference
title: "PPT-LAT-FRAMEWORK-API — the whole Shannon-Prime framework, API-style"
description: "Single-file API reference for every part of the Shannon-Prime / PPT-ARM-Lattice framework: the 5 repos + rust crates + build, the SP model loader + L1 ABI + .sp-model format, the engine forward entries, the CUDA backend (sp_g4_kv + gemma4_kv_* + the EAGLE/MTP draft), the XBAR/memory/KAIROS/nightshift/recall/MEM-OKF stack, the daemon endpoints + the token-management contract (frame/suppress/stop) + sampler, the exhaustive SP_* flag table, and the harness/tools/gates. GIST + LUT + full sections, intralinked. Companion fast-lookup index: PPT-LAT-FRAMEWORK-INDEX.md."
tags: [reference, api, framework, l1-abi, sp-model, cuda, gemma4, xbar, kairos, memory, daemon, tokenizer, flags, gates, lut]
timestamp: 2026-06-29T00:00:00Z
resource: shannon-prime-repos
sp_status: ACTIVE
sp_gate: G-OKF-CONFORM
sp_commit: 5689e3f
sp_repro: "synthesized from a 6-agent survey of the 5 repos (repos/crates/build, loader/L1/format, CUDA backend, memory/XBAR/KAIROS, daemon/endpoints/flags/tokenizer, harness/tools/gates); anchors are file:line at this commit"
---

# PPT-LAT-FRAMEWORK-API

> Companion: **`PPT-LAT-FRAMEWORK-INDEX.md`** (keywords + SHAs + flags + gates + cross-links, the fast lookup). Canonical state map: `PPT-LAT-KEYSTONE.md` / `PPT-LAT-KEYSTONE-API.md`. This doc is the *breadth* reference — every moving part, where it lives, how it is called.
> Anchors are `file:line` relative to each repo root at `sp_commit`. Repo roots: `engine` = shannon-prime-system-engine, `core` = its `lib/shannon-prime-system` submodule, `lattice` = shannon-prime-lattice.

## §0 GIST (the whole machine in one screen)

Shannon-Prime serves a **Gemma-4-12B** on an **exact-integer O_K substrate** (Q(√−163) dual-prime CRT-NTT, q1=1073738753 q2=1073732609) with a **receipted memory organism** hanging off the live KV cache. The data path, top to bottom:

1. **Harness** (Python) — agent runtime: OpenAI-compatible gateway → tool calling → memory tiers → agency loop. Translates to the daemon's native `ChatRequest`.
2. **Daemon** (Rust, `sp-daemon`) — HTTP/SSE server. `/v1/chat` frames the prompt (`apply_template_ids`), suppresses control tokens (`Sampler::with_suppress`), drives the resident KV decode, stops on `eos_ids`, and fires XBAR recall / nightshift on the same loop.
3. **L1 ABI** (C) — `sp_model_load` → `sp_session_create` → `sp_session_qwen3_model`; the per-step verbs `sp_prefill_chunk` / `sp_decode_step` (+ `clone`/`rewind`); pluggable backends via `sp_session_register_{compute,forward,kvdecode}_backend`.
4. **Engine forward** (C, `core/forward/`) — the reference forwards (`gemma4_forward` + `_feat`/`_kvtap`, qwen3/qwen25/qwen36, diffusion) and the persistent-KV decode (`decode.c`).
5. **CUDA backend** (`engine/src/backends/cuda/cuda_forward.cu`) — the *served* 12B: the `sp_g4_kv` resident ring + the `gemma4_kv_*` API (decode_logits, rewind/commit, capture/inject, **capture_feat**) + the **EAGLE/MTP draft** (`gemma4_draft_open/step/close`).
6. **Memory** — XBAR (auditable latent crossbar: Ring-1 resident / Ring-2 disk / Ring-3 gist, C2 256-bit signatures, Frobenius episode codec), RECALL (`recall.rs`: episode registry + the learned W_c head), KAIROS (heartbeat/tick loop), NIGHTSHIFT (between-turn consolidation + ablation oracle), MEM-OKF (content-addressed LUT→summary→full anti-rebuild store).
7. **Tooling** — `sp_transcode` (GGUF→.sp-model), `eagle` (the MTP draft pipeline), `curator`/`ring3`/`xbar_lsh`, and ~200 `G-*` gates (receipts-first; no number without a reproducing command).

**The token-management contract (critical, non-obvious):** the served artifact's turn tokens are **`<|turn>`=105 (start) / `<turn|>`=106 (terminator)** — NOT the literal `<start_of_turn>`/`<end_of_turn>` strings (which don't exist in its 514k vocab; using them is "the gemma3-template-on-gemma4 bug"). The model **must** (1) be framed with `apply_template_ids`, (2) have soft/placeholder tokens **suppressed** to −∞ before argmax (`258882/258883` image/audio + the `<*|>` pipe-controls), and (3) **stop** on `eos_ids` (`<eos>`=1 + `<turn|>`=106). Skip any of the three and the model emits a suppressed soft token off a malformed frame (the `258882`-repeat failure). See [§7.2](#72-token-management-contract).

---

## §1 LUT — master lookup (concept → location → one line)

| Concept | Where | One line |
|---|---|---|
| Load a model | `sp_model_load` (core io_format/sp_model_load.c:119) | path → `sp_model*` |
| Make a session | `sp_session_create` (core session/sp_session.c:78) | model → runnable session |
| Get runnable model | `sp_session_qwen3_model` (sp_session.c:931) | session → `qwen3_model*` (for backends) |
| One decode step | `sp_decode_step` (sp_session.c:725) / CUDA `gemma4_kv_decode_logits` (cuda_forward.cu:4385) | token → logits |
| Served 12B decode | `sp_g4_kv` + `gemma4_kv_*` (cuda_forward.cu:3865) | resident-ring CUDA decode |
| Spec-decode rewind | `gemma4_kv_rewind`/`commit` (cuda_forward.cu:4465/4495) | O(1) evict + journal |
| EAGLE feature tap | `gemma4_kv_capture_feat` (cuda_forward.cu:4567) | post-output_norm hidden → host |
| EAGLE draft | `gemma4_draft_open/step/close` (cuda_forward.cu:4624/4677/4658) | gemma4-assistant draft on the live ring |
| Frame a prompt | `SptbTokenizer::apply_template_ids` (daemon tokenizer.rs:612) | messages → token ids (`<|turn>`/`<turn|>`) |
| Suppress soft tokens | `suppress_token_ids()` + `Sampler::with_suppress` (tokenizer.rs:559 / sampler.rs:123) | mask `258882/258883`+pipe-controls to −∞ |
| Stop tokens | `eos_ids` (tokenizer.rs:296; `find_eos_ids` :270) | `<eos>`=1, `<turn|>`=106 |
| Memory recall | `recall.rs` (Episode :88, `wc_score` :557, `load_registry`) | C2-sig registry + W_c selector |
| Memory inject (residual) | `gemma4_kv_inject`/`_seq`/`_tokens` (cuda_forward.cu:4744/4776/4882) | episode K/V enters as residual, not tokens |
| Between-turn curate | `nightshift_curator.rs` (`extract_secret`,`admit`) | distill + ablation oracle + PoUW |
| Anti-rebuild store | `lattice/tools/okf_mem.py` (lookup/add/expand/verify) | LUT→summary→full content-addressed |
| Transcode a model | `engine/tools/sp_transcode/sp_transcode.c` | GGUF → .sp-model (--st/--q4/--q4b) |
| Build CPU | `scripts/env/env-cpu.bat` (clang-cl) + `build-cpu` | math core + engine |
| Build CUDA backend | `tools/sp_daemon/build-host-cuda-backend.bat` (nvcc, sm_75) | `sp_cuda_daemon_backend.lib` |
| Build daemon | `cargo build --release --features wire_cuda_backend --target-dir target-wirecuda` | sp-daemon + bins |
| Serve | `sp-daemon start --model …b1.sp-model --tokenizer … --port 3000` | the live chat |

---

## §2 Repos, crates, build

### 2.1 Repos
| Repo | Role | Key dirs |
|---|---|---|
| **shannon-prime-lattice** | umbrella: roadmap, papers, gates, MEM-OKF | `papers/ demos/ tests/ tools/ memory-okf/ staging/` |
| **shannon-prime-system** | math core (Phase-1 primitives) | `core/ include/ tests/` |
| **shannon-prime-system-engine** | inference engine (forward + KV decode + 4 backends) | `src/ lib/shannon-prime-system(submodule) tools/ scripts/` |
| **shannon-prime-harness** | Python agent runtime (tools, memory, agency) | `harness/{agent,inference,mcp,skills,server} memory-okf/` |
| **Position_Is_Arithmetic** | public-facing papers (receipts-first) | `papers/ posts/` |

### 2.2 Rust crates
- **sp-daemon** (`engine/tools/sp_daemon/Cargo.toml`) — the L3 HTTP/SSE daemon over the L1 C ABI. Features: `wire_cpu_backend`, `wire_cuda_backend`, `wire_hex_backend`, `wire_vulkan_backend`, `kairos`. Bins: `sp-daemon`, `sp-console`, `sp_wire_cuda_decode_gate`, `sp_eagle_accept`, `sp_chat_*`, `sp_memo_m{1,2,4,5}_*`, `sp_ntt_*`, `sp_ring2_showpiece`, `spec_validate`.
- **sp-dsp-smoke** (`tools/sp_dsp_smoke`) — FastRPC/aarch64-android bridge + 19 test bins (NTT bit-exact).
- **sp-npu-spike**, **sp-trick1** — NPU dispatch smoke / two-process decode showpiece.

### 2.3 Build system
- **Math core CMake** (`core/CMakeLists.txt`): 23 ordered `sp_*` static modules — `forward_kernels, exact_islands, io_hash, io_format, weight_dtype, gguf, ok_arith, ntt_crt, poly_ring, ring3, vht2, frobenius, kste, arena, model, forward_dispatch, arm, forward, session, sp_channel, dominance, sieve, xbar`.
- **Engine CMake** (`engine/CMakeLists.txt`): options `SP_ENGINE_BACKEND={cpu,cuda,vulkan,hexagon}`, AVX2 ON / AVX512 OFF; adds `tools/sp_transcode`, `tools/sp_tok_dump`, `tools/eagle`, `tests`.
- **Env scripts** (`engine/scripts/env/`): `env-common.bat` (pins: CUDA **13.2**, VS2019 BT, MinGW gcc 15.2, sm **75**); `env-cpu.bat` → **clang-cl** (MSVC-ABI; `cl.exe` can't compile `__int128` in `exact_islands.c` → C4235); `env-cuda.bat` → vcvars64 + nvcc + `--use-local-env`.
- **Canonical builds:** CPU `cmake --build build-cpu` (clang-cl); CUDA backend `tools/sp_daemon/build-host-cuda-backend.bat` (cmake+Ninja+nvcc → `sp_cuda_daemon_backend.lib`, ~40s incremental); daemon `cargo build --release --features wire_cuda_backend --target-dir target-wirecuda`. Full from-clean runbook: `lattice/papers/BUILD-ENV-TOOLCHAIN.md` (gate `G-CLEAN-BUILD`).
- **build.rs CUDA linkage** (`tools/sp_daemon/build.rs:423`): MSVC links `cudart`/`cudadevrt`/`cublas`/`cublasLt` via **absolute-path `rustc-link-arg`** (plain `rustc-link-lib` does NOT propagate to standalone `[[bin]]` on MSVC — that left `cudadevrt __cudaRegister*` unresolved for the probe bins).

---

## §3 SP loader, L1 ABI, .sp-model format

### 3.1 .sp-model format (headers: `core/include/sp/sp_model.h`, `sp/sp_l1.h`, `sp/model.h`)
- `sp_model_header` (512 B): magic `SPMD`, `arch_id`, `arch_struct[256]` (the `sp_arch_info` image), `tokenizer_hash[32]`, `vocab_size`, `tensor_count`, table/data offsets, `header_crc32` (over [0,360)).
- `sp_tensor_entry` (256 B): `name[80]`, `dtype_id`, `n_dims`, `dims[8]`, `offset_in_data`, `size_bytes`, `block_size/count`, `blake3[32]`, `name_hash` (xxh64; table sorted).
- `sp_dtype_id`: F32=1, F16=2, BF16=3, **OK_Q8=10**, **OK_Q4=11**, FROBENIUS_SCALE_FP32=12, OK_Q4B=13, BLOCK_SCALE_FP16=14, SPINOR63=20, RING_RESIDUE_CRT_30_30=30, OK_INTEGER=31.
- `sp_arch_id`: LLAMA3=1, QWEN3=2, GEMMA3=3, DEEPSEEK_V4=4, QWEN25=6, **GEMMA4=7**, QWEN36=8, DIFFUSION_GEMMA=9, **GEMMA4_ASSISTANT=10**.
- `sp_arch_info` (the 256-B payload): base geometry (arch_id, vocab, hidden, n_layers, n_heads, n_kv_heads, head_dim, max_context, swa_window, rope_freq_base, ffn_variant 0=SwiGLU/1=GeGLU, norm_variant 0=pre/1=sandwich, tied_embeddings, has_qk_norm, n_ff, rms_eps) + **g4_*** (g4_hd_swa, g4_nh_swa, g4_nkv_swa, g4_rope_base_swa, g4_n_kv_from_start, g4_logit_softcap, g4_swa_period) + **q36_*** (MoE/GDN + `q36_nextn_predict_layers`) + **dg_*** (diffusion).

### 3.2 Loader + session (L1 ABI)
- `sp_model_load(model_path, tok_path, **out)` (io_format/sp_model_load.c:119); `sp_model_unload`; `sp_model_get_header`; `sp_model_find_tensor`; `sp_model_arch(m, sp_arch_info*)` (sp_model_arch.c:22 — generic projection of `arch_struct`, no arch_id gate → arch 10 loads as-is).
- Adapters: `sp_model_to_{qwen3,gemma3,qwen25,gemma4,qwen36,diffusion_gemma}` + `sp_model_store_qm`/`borrow_qm`.
- Session: `sp_session_create(m,cfg,cancel,**out)` (sp_session.c:78), `_destroy`, `_position`, **`sp_prefill_chunk`** (:154), **`sp_decode_step`** (:725), **`sp_session_clone`** (:773, spec-decode), **`sp_session_rewind`** (:818), `sp_session_qwen3_model` (:931).
- Backend registration: `sp_session_register_compute_backend` (NTT), `_register_forward_backend` (full forward), **`_register_kvdecode_backend`** (:909) with the `sp_kvdecode_dispatch_fn` table {open, prefill, decode_step, rewind, position, close} — this is how the CUDA `gemma4_kv_*` plugs into `sp_decode_step`.

### 3.3 Engine forward entries (`core/forward/`, header `sp/model.h`)
- `gemma4_forward(m,tokens,n,logits)` (gemma4.c:298) — SWA/global per-layer geometry, AltUp, softcap. **`gemma4_forward_feat(…,feat_out)`** (:308) — also emits the post-output_norm hidden (EAGLE feature). **`gemma4_forward_kvtap(…,feat_out,g4_kv_tap*)`** (:315) — also copies the target KV for layers n-1 (full)/n-2 (SWA).
- `qwen3_forward`/`_ex`/`_ex2` (forward.c), `gemma3_forward`/`_ex2`, `qwen25_forward`, `qwen36_forward` (GDN+MoE).
- Persistent-KV: `qwen3_generate_kv` (decode.c:909), `qwen3_ppl_decode` (decode.c:920, teacher-forced PPL).
- Kernels (`sp/forward_kernels.h`): `sp_dot_f32`, `sp_rmsnorm`, `sp_rmsnorm_head`, `sp_rope_neox`/`_freqs`, `sp_attn_head`. Dispatch (`sp/forward_dispatch.h`): `sp_matmul`, `sp_embed_row`, `sp_weight_row`, `sp_as_f32`, `sp_dequant_row`, `sp_kernels_read_env`.

---

## §4 CUDA backend — the served 12B (`engine/src/backends/cuda/cuda_forward.cu`)

### 4.1 `sp_g4_kv` (the resident decode handle, :3865)
Fields, grouped: geometry `E,NL,V,SW,period,kvfs,PL,Pmax`; per-type head geom **`g_nh/g_nkv/g_hd`** (global) + **`s_nh/s_nkv/s_hd`** (SWA); rope bases `g_base/s_base`; `eps,embscale,softcap`; **ring** `dKc/dVc` (per-layer K/V) + `jK/jV` + `ring_W/Jmax/commit_pos/jcur`; residual scratch `dx,dnx,dq,…,dlog`; seq `dseq,dpos,dpos_host`; **capture/inject** `cap_host/cap_active` (post-embed), **`feat_host/feat_active`** (post-output_norm EAGLE feature), `qcap_*` (query capture for recall); graph `gcap/gexec/graph_mode`; `bx_on` (byte-exact).

### 4.2 `gemma4_kv_*` API (extern "C")
| Fn | Line | Semantics |
|---|---|---|
| `gemma4_kv_open(m,Pmax)` | 4273 | allocate resident ring |
| `gemma4_kv_prefill(s,toks,n)` | 4336 | ingest n; head on last |
| `gemma4_kv_decode(s,n_gen,out)` | 4351 | greedy argmax n_gen |
| **`gemma4_kv_decode_logits(s,token,logits)`** | 4385 | one step → full-vocab logits (daemon samples) |
| `gemma4_kv_pos` / `_seq_peek` | 4502/4451 | position / dseq peek |
| **`gemma4_kv_rewind(s,delta)`** / `_commit` | 4465/4495 | O(1) evict (journal restore) / clear baseline |
| `gemma4_kv_reset` / `_reset_cold` | 4508/4532 | soft / full reset |
| `gemma4_kv_capture(s,emb)` | 4558 | arm post-embed residual D2H |
| **`gemma4_kv_capture_feat(s,feat)`** | 4567 | arm post-output_norm hidden D2H (EAGLE seed) |
| `gemma4_kv_inject(s,emb)` / `_seq` / `_tokens` | 4744/4776/4882 | residual-seam injection (memory enters as residual) |
| `gemma4_kv_replay(s,epdir,npos,zero)` | 4910 | inject stored episode K/V |
| `gemma4_kv_byteexact_set` / `_set_kv_flags` | 4425/4437 | toggle exact-integer / KV codec |
| `gemma4_forward_cuda` / `gemma4_decode_cuda` / `gemma4_cuda_probe` | 2035/2314/1711 | stateless forward / decode / truncatable probe |

### 4.3 EAGLE/MTP draft (the spec-decode draft, served-path)
- **`gemma4_draft_open(gguf_path)`** (:4624) — load the gemma4-assistant draft GGUF to GPU (`DraftWeights g_draft`; 4 layers, hd 256/256/256/512, Vd 262144, BBt 3840).
- **`gemma4_draft_step(s,feat_host,token,*out_token,out_hnext)`** (:4677) — one draft step on the **live** target ring: `x = target_embd[token]·√BBt` (`k_embed_scale_one` or `k_embed_packed_one`) ⧺ feature → `nextn.pre_projection` → 4 sandwich blocks (Q-only attn over `dKc[NL-1]` full / `dKc[NL-2]` SWA via `k_attn_decode_ring`, GQA group=16/nkv) → output_norm → draft tied head → argmax. Attention scale env-tunable `SP_DRAFT_ASCALE=one|rsqrt`.
- `gemma4_draft_close` (:4658).
- Proven offline: `G-EAGLE-DRAFT-FWD-CUDA` GREEN (matches the numpy oracle to ~2e-5).

### 4.4 Key kernels
attention `k_attn_decode_ring`(:606)/`_ring_bx`(:652)/`_win`/`_gather`/`_decode`; `k_rmsnorm`(:338)/`_head`(:358); rope `k_rope_at`(:999)/`k_rope_freqs_at`(:477); embed `k_embed_scale_one`(:98)/`k_embed_packed_one`(:107); `k_argmax`(:977)/`_at`; `k_gelu_mul`(:1047)/`k_silu_mul`; `k_softcap`(:852); `k_matmul_draft`(:4594); dp4a GEMVs `k_gemv_q{8,4,4b}_dp4a_v2`. Weight upload `upload_weight`(:1381)/`upload_packed`/`draft_up`(:4601). Structs `DevTensor`, `CudaWeights g_w`, `DraftWeights g_draft`.

---

## §5 Memory: XBAR / RECALL / KAIROS / NIGHTSHIFT / MEM-OKF

### 5.1 XBAR (auditable latent crossbar)
Token-free cross-session memory: episodes are latent KV state, content-addressed by a **C2 256-bit signature** (sign of ±1 Rademacher rank-256 projection of global-layer K; `recall.rs:21-85`). Rings: **Ring-1** resident hot cache (`core/arm/arm.c`, Spinor-compressed), **Ring-2** disk offload (`sp_arm_ring2_stdio_open_ro`, byte-exact f32 K/V), **Ring-3** gist/VSA (deferred, OFF by `G-R3-LOSS`). Episode codec = **Frobenius rank-2 O_K** (`curator/frob_episode.py`, schemes a16/a8b4/a16b8) + the 63-byte **Spinor** block (`core/vht2/spinor_block.c`). The O_K dual-prime CRT-NTT is the exact-integer carrier (`G-R3-BIND`). Contracts: `CONTRACT-XBAR-*`, `CONTRACT-C2-ARM-spinor-kv-two-ring`, `RFC-XBAR-auditable-latent-crossbar`.

### 5.2 RECALL (`daemon/src/recall.rs`)
`Episode {name,dir,npos,topic,text,sig[u64;4],global_k}` (:88). `load_registry` / `load_episode_global_k` / `load_wc`. **W_c head** (`WcHead {hd,r,s0,sscale,w}` :534; `wc_score` :557) = the learned autonomous selector: logsumexp-over-positions, mean-over-global-layers relevance; `score>s0` admits, else foreign-reject. Live recall via `SP_B3_WC` / q·K relevance; gate `G-CHAT-B3-WC-DIV2` (360/361 recall + 50/50 reject). `strip_special_tokens` (:427) cleans `<…|>` markers.

### 5.3 KAIROS + NIGHTSHIFT
KAIROS (`kairos.rs`/`kairos_runner.rs`): the heartbeat/idle tick loop over an `EventTape` of `TapeEvent`s; one persistent `SpSession`, per-tick frame (`frame_prompt_gemma`/`_chatml`) + `decode_decision`; activated by `SP_KERNEL=1` / `SP_KAIROS_ALPHA`. NIGHTSHIFT (`nightshift_curator.rs`, `SP_NIGHTSHIFT_OFFLINE=1`): between-turn consolidation — `extract_secret` (model-call distiller) → `admit` (teacher-forced causal-ablation oracle, the `SP_B3_DISPOSER` ΣΔLL gate, TAU=−8) → PoUW receipt + MEM-OKF emit. Gate `G-NIGHTSHIFT-CURATOR`.

### 5.4 Inject seam (memory enters as RESIDUAL, not tokens)
`gemma4_kv_inject`/`_seq`/`_tokens` (CUDA) + `inject_frames`/`single_entry`/`auto_recall` (`routes.rs`): cue (W_c or `SP_REPLAY_MTARGET`) → resolve Ring-2 path → snapshot (O(1) `commit`/`rewind`) → load f32 K/V → inject at the recall slot → gate PPL deflection (<2%) → commit/rewind. Token-free: the model's attention consumes the loaded K/V directly.

### 5.5 MEM-OKF (anti-rebuild store, `lattice/tools/okf_mem.py` + `memory-okf/`)
Three tiers: **Tier-0 LUT** (`memory-okf/LUT.md`, one row/object: addr|kind|keys|summary|status), **Tier-1 summary** (`sum/<addr>.md`), **Tier-2 full** (`full/<addr>.md`). Address = `sha256(body)[:16]` (agent) or C2 sig (episode). CLI: `add`/`lookup`/`expand`/`verify`. Gate `G-MEM-OKF-CONFORM`. **Pre-flight (binding): `okf_mem.py lookup` before building any subsystem.** Profile: `papers/MEMORY-OKF-PROFILE.md`, `papers/SP-OKF-PROFILE.md` (frontmatter: type + sp_status/sp_gate/sp_commit/sp_repro).

---

## §6 Daemon, endpoints, token contract, sampler

### 6.1 Endpoints (`server.rs`/`routes.rs`)
`/v1/chat` (POST → SSE), `/v1/dialogue` (MeMo 3-turn), `/v1/metrics`, `/v1/abort/:id`, `/v1/capture`, `/v1/receipts`, `/v1/events` (SSE), `/v1/pouw/ledger`, `/v1/mesh/peers`, `/v1/node/telemetry`, `/v1/debug/backend_counts`, `/v1/dsp/*`. Launch: `sp-daemon start --model --tokenizer [--draft-model --memo-model --pouw-ledger-path --quic-port] --port`.

### 6.2 Token-management contract
**Frame** — `SptbTokenizer::apply_template_ids(&[Message{role,content}])` (tokenizer.rs:612) emits the real control ids: **`<|turn>`=105 (start), `<turn|>`=106 (terminator)**; literal `<start_of_turn>`/`<end_of_turn>` strings shatter (not in vocab). BOS auto-prepended (gemma4 add_bos=1). **Suppress** — `suppress_token_ids()` (:559) = pipe-controls (`<*|>`/`<|*>`) + named specials + `generation_config.json` `suppress_tokens` (**258882/258883** image/audio softs); `Sampler::with_suppress` forces them to −∞ before argmax (sampler.rs:171). **Stop** — `eos_ids` (:296; `find_eos_ids` :270 = `<eos>`,`<end_of_turn>`→ here `<eos>`=1 + `<turn|>`=106; `turn_stop_ids` covers 105/106). Key ids: BOS=2, EOS=1, turn-start=105, turn-end=106, audio=258881, image-softs=258882/258883. The served loop checks eos/turn-stop *before emit* so markers never reach the stream.

### 6.3 Sampler (`sampler.rs`)
`SamplingParams {temperature=0.7, top_p=0.95, top_k=40, repetition_penalty=1.1, frequency_penalty=0, seed}`. `Sampler::with_suppress(params, suppress)`; `sample(&mut logits)`: suppress→ (temp==0 ? argmax : penalties→temp→top-k→softmax→top-p→draw). `raw_logits=true` ⇒ empty suppress ⇒ byte-identical old argmax (determinism leg). Default served greedy = suppressed + clean. `byteexact` defaults ON (exact-integer islands + CRT-NTT attention; run-to-run bit-identical).

### 6.4 Served decode loop (`run_kvdecode_chat`)
byteexact guard → (optional `SP_PERSIST_KV` LCP reuse) → reset/rewind → prefill (or `single_entry` inject_tokens) → inject_frames → auto-recall (C2 query sig → q·K rank → fire if ≥ `SP_B3_TAU_QK`) → first logits → sample loop {eos/turn-stop check → `sample` → emit → `decode_step` → eot_bias} → flush. Resident-cache path (kvdecode, CUDA) vs session-clone path (prefill_chunk+decode_step fallback).

---

## §7 SP_* flags (exhaustive — see INDEX doc for the full table)

Model/launch: `SP_MODEL_PATH`, `SP_TOKENIZER_PATH`, `SP_DRAFT_MODEL_PATH`, `SP_MEMO_MODEL_PATH`, `SP_POUW_LEDGER_PATH`, `SP_HTTP_PORT`(8080), `SP_QUIC_PORT`, `SP_PEERS`. Backend: `SP_DAEMON_BACKEND={cpu,cuda,hex,vulkan}`, `SP_DAEMON_KVDECODE(_PMAX/_RING_W/_JMAX)`, `SP_CUDA_DECODE_INT8`, `SP_BYTEEXACT`, `SP_ENGINE_NTT_ATTN`, `SP_ENGINE_FP16`. Memory/agency: `SP_RECALL_REGISTRY`, `SP_AUTO_RECALL_DEFAULT`, `SP_PERSIST_KV`, `SP_DECIDE`, `SP_FORGET`, `SP_B4_NIGHTSHIFT`, `SP_B3_JUDGE`, `SP_B3_DISPOSER(_TAU)`, `SP_B3_WC`, `SP_B3_QK_TOPM`, `SP_B3_TAU_QK`(∞), `SP_INT2(_W/_K/_TAU)`, `SP_REPLAY_MTARGET`/`_ALPHA`, `SP_NIGHTSHIFT_OFFLINE`/`_LIVE`/`_PERSIST`, `SP_EOT_BIAS`. KAIROS: `SP_KERNEL`, `SP_KAIROS_{ALPHA,MODEL,TOK,TAPE,REPORT,NOTHINK,CHATML,PRUNE,SALIENCE_POLICY}`. EAGLE: `SP_DRAFT_ASCALE`. DG: `SP_DG_WCACHE`, `SP_DG_PREFIXKV`, `SP_DG_TRACE`. The full table (flag · file:line · effect · default) is in `PPT-LAT-FRAMEWORK-INDEX.md §Flags`.

---

## §8 Harness, tools, gates

### 8.1 Harness (`shannon-prime-harness`)
Python agent runtime: `harness/agent.py` (`run_with_tools`, persona), `harness/inference/client.py` (`SPDaemonClient` → daemon `ChatRequest` via `InferenceConfig.to_sp_chat()`), `harness/mcp/` (tools + `@skill`), `harness/skills/` (memory primitives remember/forget/list/recall), `harness/server/` (OpenAI gateway, SSE). Run: `run_agency.py` / gateway :3000. Gates `G-HARNESS-*`.

### 8.2 Tools (`engine/tools/`)
`sp_transcode` (GGUF→.sp-model; `--st` safetensors / `--q4`/`--q4b`; gemma4-assistant arch support); `eagle` (`sp_eagle_ref.py` numpy oracle + `sp_eagle_fwd.c` CPU + `sp_eagle_fwd_cuda.cu` CUDA + `sp_eagle_accept.rs` live probe); `sp_tok_dump`; `sp_dsp_smoke`; `curator/frob_episode.py`; `ring3/*` (exact-integer gates); `xbar_lsh/*` (B3 dataset/train/judge).

### 8.3 Gates (receipts-first; ~200 `G-*`, full list in INDEX §Gates)
Families: **EAGLE/MTP** `G-EAGLE-{DRAFT-FWD-C,DRAFT-FWD-CUDA,DRIVE-C,ACCEPT}`; **byte-exact** `G-BYTEEXACT-{FORWARD-12B,ISLANDS-CUDA,ATTN-NTT}`; **chat** `G-CHAT-{A1,A2,A2-POLISH,B1,S1,B3-WC-*}`; **ring3** `G-R3-{BIND,DUALROUTE,MOBIUS,NIGHTSHIFT,LOSS}`; **wire** `G-WIRE-CUDA-DECODE-GEMMA4`; **curator** `G-NIGHTSHIFT-CURATOR`; **build** `G-CLEAN-BUILD`; **OKF** `G-OKF-CONFORM`/`G-MEM-OKF-CONFORM`; **persist** `G-PERSIST-KV-REWIND`; **DG** `G-DG-N{0..6}`/`G-DG-PREFIXKV`; **diffjudge** `G-DIFFJUDGE-OOD-H2H`.

### 8.4 MTP campaign commits (engine)
`d6ee0f7` transcode gemma4-assistant→Q4 · `ed28fe6` numpy oracle · `73314ac` C draft fwd (G-EAGLE-DRAFT-FWD-C) · `fab177a` drive loop (G-EAGLE-DRIVE-C) · `98b0032`/`af858e1` feature tap (gemma4_forward_feat) · `3ccd1f1`/`19e1cb8` KV tap (gemma4_forward_kvtap) · `beebac6` served feature tap (gemma4_kv_capture_feat) · `726733c` CUDA draft fwd (G-EAGLE-DRAFT-FWD-CUDA) · `6092a97` draft loader (gemma4_draft_open) · `933715b` draft step (gemma4_draft_step) · `5689e3f` live probe (sp_eagle_accept).

---

*Maintenance: this is a breadth reference; depth lives in the per-domain CONTRACT-*/PPT-LAT-* docs it cites. Re-run the 6-agent survey (sp_repro) after large refactors. Validate with `python tools/okf_validate.py papers/PPT-LAT-FRAMEWORK-API.md`.*
