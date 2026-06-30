---
type: reference
title: "Shannon-Prime — KEYSTONE API reference"
description: "The integration surface of the KEYSTONE system: the daemon HTTP endpoints, the L1 ABI decode verbs, the harness Python modules/functions, the env knobs, and the launchers. Pair with PPT-LAT-KEYSTONE.md (the map). This is the 'how do I call it' tier."
tags: [keystone, api, reference, daemon, harness, l1-abi, knobs, okf]
timestamp: 2026-06-25T00:00:00Z
resource: shannon-prime-lattice
sp_status: SUPERSEDED
sp_gate: KEYSTONE-1
sp_commit: keystone-1
sp_repro: "see the gate names per surface; live: _e2e_seed_serve.bat + run_agency.bat"
---

# KEYSTONE — API reference

The map is [PPT-LAT-KEYSTONE.md](PPT-LAT-KEYSTONE.md); this is the call surface. Three layers:
**(A)** the daemon HTTP API (what the console + harness call), **(B)** the L1 ABI (how the engine
plugs into the math core), **(C)** the harness Python API (tool calling + memory + agency).
All `SP_*` env flags are **default-off = byte-identical null floor**.

---

## A. Daemon HTTP API — `sp-daemon` on `http://127.0.0.1:3000`

### `POST /v1/chat` → SSE
Body (`ChatRequest`, JSON). Exactly one input of `prompt` | `messages` | `prompt_tokens`:

| field | type | notes |
|---|---|---|
| `messages` | `[{role, content}]` | full conversation; daemon templates with gemma4 control tokens; **server carries the thread** |
| `prompt` / `prompt_tokens` | string / int[] | raw alternatives (no chat template) |
| `max_tokens` | int | default 512 |
| `temperature`,`top_p`,`top_k`,`repetition_penalty`,`frequency_penalty`,`seed` | sampler | `temperature:0` = argmax (byte-exact-friendly) |
| `eot_bias` | float | logit bias on stop tokens; ≈4 = clean stop |
| `auto_recall` | bool | autonomous episodic recall (W_c head → judge → recite/abstain) |
| `byteexact` | bool | exact-integer islands (auditable) |
| `replay` / `replay_npos` | string/int | force-replay an episode dir |
| `single_entry` | bool | route text through the one residual seam |

Response: `text/event-stream`, one `data: {"delta": "...", "chat_id": N}` per token, terminated by
`data: [DONE]`. Side effects (per turn, env-gated): writes `SP_CURRENT_CONVO`; NIGHTSHIFT capture;
LAYER-2/3 forget/decide/merge. Gate: G-CHAT-FULLSTACK / G-JUDGE-SERVED.

### Other endpoints
- `POST /v1/abort/{chat_id}` → 204. Cancel an in-flight generation.
- `POST /v1/capture` `{text, out_dir}` → `{ok, npos}`. Mint an episode (ep.k/ep.v/ep.mf) for the
  registry — used by the seed/curator/capabilities scripts and the harness `remember()`.
- `GET /v1/metrics` → `{tokens_per_sec, ram_svm_bytes, peers, phase, session_pos}`.
- `GET /v1/mesh/peers`, `GET /v1/debug/backend_counts`, `GET /v1/pouw/ledger` (SSE).

---

## B. L1 ABI — `include/sp/sp_l1.h` (the engine↔core seam)

The frozen, append-only ABI. The engine registers backends; the daemon drives the 12B through them.

- **`sp_session_register_forward_backend(...)`** — §6: the prefill / full-forward hook
  (engine `gemma4` forward registers here). G-WIRE-CUDA-GEMMA4.
- **`sp_session_register_kvdecode_backend(...)`** — §6b: the **stateful persistent-KV decode** verb
  (`open / prefill / decode_step / rewind / position / close`). The engine's
  `gemma4_kv_decode_logits` registers here so the daemon decodes token-by-token at flat O(1) VRAM.
  G-WIRE-CUDA-DECODE-GEMMA4 (32/32 == oracle).

Exact-integer anchor: `core/exact_islands/` (the 4 nonlinear islands, gate `T_EXACT_ISLANDS`);
two-ring memory: `core/arm/`; the only decode in the tree: `core/forward/decode.c`.

---

## C. Harness Python API — `shannon-prime-harness/`

Import root is the repo dir (`sys.path` it, or run from there). Core is stdlib-only; the live
transport needs `httpx` (the gateway extra).

### Inference seam — `harness.inference`
- `SPDaemonClient(base_url="http://127.0.0.1:3000")`
  - `.chat(messages=|prompt=, config=InferenceConfig) -> InferenceResponse(text, chat_id, …)`
  - `.chat_stream(...) -> generator[str]` (yields deltas, returns the response)
  - `.metrics() / .health() / .abort(chat_id)`
- `InferenceConfig(temperature, top_p, top_k, repetition_penalty, max_tokens, byteexact,
  auto_recall, replay, single_entry, …)` → `.to_sp_chat(prompt=|messages=|prompt_tokens=)` builds the
  `/v1/chat` body. The single translation point — never add a second client.

### Ephemeral tool calling — `harness.mcp.tools`
- `ToolSpec.from_callable(fn)` — derive a tool from a typed Python callable (schema from the signature).
- `ToolRegistry().register(fn)` / `.load_from_skills(pack=|names=)` (bridges `@skill`).
- `run_with_tools(messages, tools, *, client=, config=, max_rounds=6, on_tool=) -> str` — the ReAct
  loop: the model emits `<tool name="X">{json}</tool>`, the harness parses + executes + feeds the
  observation back, looping until it stops emitting tool calls. No native tool channel required.
  Gates: G-HARNESS-DAEMON-E2E (H1), G-HARNESS-TOOLCALL-E2E (H2).

### Memory tools — `harness.skills.memory` (operate on `SP_RECALL_REGISTRY`)
- `list_memories() -> str` (introspect) · `remember(fact) -> str` (idempotent; mints via /v1/capture
  when reachable) · `forget(fact) -> str` (token-overlap match → remove). `MEMORY_TOOLS` = the trio.
  Gate: G-HARNESS-MEMTOOLS-E2E (H3).

### Tiered conversation memory + capabilities — `harness.skills.conversation_memory`
Built on `tools/okf_mem.py` (sha256 addr; LUT→`sum/`→`full/`). Roots: `SP_CONV_OKF_ROOT`,
`SP_CAPS_OKF_ROOT`.
- `summarize_conversation(messages) -> gist` · `store_conversation(messages) -> addr` (full+summary,
  sha-linked) · `recall_conversations(query) -> gist lines` · `read_conversation(addr) -> full`
- `extract_facts(messages) -> [fact]` · `consolidate_conversation(messages) -> {facts, conversation_addr}`
  (the short→mid+long extraction pass)
- `seed_capabilities() -> [addr]` · `recall_capability(query)` · `init_primer() -> str` (the
  "how do I use myself" priming). Gates: G-HARNESS-CONVMEM-E2E (H6).

### The agency loop — `harness.control.agency`
- `agency_round(*, client=, config=, on_tool=) -> str` — one model-driven memory-maintenance round
  (the model reviews its memory + curation tools and decides what to forget/consolidate).
- `consolidate_current(convo_path, client=) -> {facts, conversation_addr} | None` — consolidate the
  current-conversation document.
- `run_agency_scheduler(*, interval=30, rounds=None, idle_gate=True, convo_path=None, on_round=,
  on_tool=) -> int` — the KAIROS tick: each beat (idle-gated) consolidate `convo_path` then run a
  maintenance round. Gates: G-HARNESS-AGENCY-E2E (H4), G-HARNESS-KAIROS-TICK-E2E (H5),
  G-HARNESS-LIVE + G-HARNESS-HOOK-E2E (H7).
- Launcher: `run_agency.py` / engine `run_agency.bat`.

### MEM-OKF tool — `tools/okf_mem.py` (CLI)
`add --keys --summary [--full-file|--blob-ref] [--addr]` · `lookup <kw>` · `expand <addr> [--full]`
· `verify --root <root>` (gate G-MEM-OKF-CONFORM). Address = sha256(body)[:16] or a passed C2 sig.

---

## Knobs index → see [PPT-LAT-KEYSTONE.md §7](PPT-LAT-KEYSTONE.md). Run it → §10. Gates → §9.
