---
type: design
title: "O(1) Conversation KV — scoping the persistent resident cache (the agentic-loop scaling fix)"
description: "Grounded scope for making a follow-up turn O(1) on the served Gemma-3-12B: the per-position KV cost + token ceiling on the 12GB RTX 2060, the L1 kvdecode verb readiness vs the serving loop, and Gemma-GPU/coder-CPU session isolation. KEY FINDING: the cross-turn O(1) append is ALREADY IMPLEMENTED (SP_PERSIST_KV, default-off, LCP-reuse + suffix-only prefill + bounded-tail rewind) — the pillar is gate+enable+long-session-capacity, not build."
tags: [design, okv, persistent-kv, o1-context, kvdecode, scaling, scope, gemma4]
timestamp: 2026-06-30T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-OKV-Persistent-KV-SCOPE.md
sp_status: DRAFT
sp_gate: "scoping doc (no code this pass); the gate G-PERSIST-KV is defined in §4"
sp_commit: TBD
sp_repro: "grounded from engine src: cuda_forward.cu sp_g4_kv/gemma4_kv_open; tools/sp_daemon/src/{daemon.rs,routes.rs,cuda_kvdecode_dispatch.rs}; gemma4.c head geometry"
---

# O(1) Conversation KV — scope (the agentic-loop scaling fix)

**Why:** the autonomous loop (Latent Interceptor + XBAR tiers + KAIROS tick) wakes repeatedly to think. If each wake re-prefills the whole conversation (O(n)), the loop throttles itself to death as context grows (measured: tok/s 30→1 on long chats). To run indefinitely, appending a thought/observation must be O(1).

**Headline finding (anti-rebuild):** the O(1) append already exists in the engine, default-off. The work is **gate → enable → extend the capacity envelope**, not a from-scratch build.

## 1. KV ring capacity on the 12GB RTX 2060 (S1 — grounded)

Per-position KV is **flat 4 KB per owner-layer**, by the real Gemma-3-12B geometry (`gemma4.c`, `arm_geom_test.c`):

- GLOBAL layers: `n_kv=1 × head_dim=512` = 512 floats K + 512 V.
- SWA layers: `n_kv=2 × head_dim=256` = 512 floats K + 512 V.
- Both ⇒ 1024 floats = **4096 B / position / owner-layer**.

Owners: `g4_n_kv_from_start = n_layers = 48` (gemma-3 has no cross-layer KV sharing — the loader sets kvfs=NL). Period 6 ⇒ **8 GLOBAL** owner layers (L%6==5) + **40 SWA** owner layers.

Two regimes (`gemma4_kv_open`, the jagged per-layer cache):

| Mode | Globals (8) | SWA (40) | Per-position | Notes |
|---|---|---|---|---|
| **Full-cache** (default, `ring_W=0`) | full `Pmax` | full `Pmax` | **192 KB/pos** | every layer grows O(n) |
| **SWA-ring** (`SP_DAEMON_KVDECODE_RING_W=W`) | full `Pmax` (32 KB/pos) | fixed `W` slots (160 KB·W total) | globals 32 KB/pos + const | only the 8 globals grow |

VRAM budget: 12 GB − ~9.4 GB Q4 weights − ~0.6–1 GB CUDA ctx/scratch ≈ **~1.5–2.0 GB for KV**.

- **Full-cache ceiling ≈ ~8–10K tokens** (2.0 GB ÷ 192 KB). Current `Pmax` default = **4096** ⇒ 786 MB resident (comfortable).
- **SWA-ring ceiling**: SWA fixed (e.g. W=4096 ⇒ 640 MB), globals 32 KB/pos ⇒ remaining ~1.3 GB ÷ 32 KB ≈ **~40K global positions**. The **8 global layers are the hard O(n) floor**; everything else is already O(1) under the ring.
- **Truly unbounded** ⇒ evict/page the global layers. That tier already exists: the **XBAR Ring-2 → Optane demotion** (KAI/C2 curator; 349.8 MB→Optane proven). Globals are exactly what must survive, so global-eviction-to-Optane is the infinite-context path, not new math.

## 2. L1 kvdecode verb readiness vs the serving loop (S2 — the key finding)

**The persistent-decode verb is built + gated.** `sp_session_register_kvdecode_backend` is registered in `daemon.rs` (open/prefill/decode_step/rewind/position/close → `gemma4_kv_*`); **G-WIRE-CUDA-DECODE-GEMMA4** proved 32/32 tokens bit-identical to the oracle with **VRAM flat (O(1) cache)**. Decode *within* a generation is already O(1).

**The cross-turn O(1) append is ALSO already built — `SP_PERSIST_KV` (default-off)** in `routes.rs::run_kvdecode_chat`:

- Tracks the committed token sequence in a global `KV_COMMITTED: Vec<i32>` (cache holds exactly `committed`, `pos == committed.len()`).
- On a new prompt: **longest-common-prefix reuse** — reuse the shared prefix, **rewind only the small diverging committed tail** (`REWIND_BOUND=32`, inside the SWA undo-journal `Jmax=64`), **prefill only the new suffix**. `drop==0` is the pure strict-prefix append (no rewind).
- **Byte-exact rationale documented**: reused-prefix K/V is the same deterministic compute; the suffix is prefilled fresh. `prefill_from=0` ⇒ identical to the reset+full-prefill **null floor**.
- **Correctly excluded** (paths that mutate the cache in ways a token-sequence can't mirror): operator replay / `single_entry` / `inject_frames`; memory-agency writers (`SP_DECIDE`/`SP_FORGET`/`SP_B4_NIGHTSHIFT`); speculative recall (`SP_B3_JUDGE`/`SP_B3_DISPOSER`/`SP_INT2`). `auto_recall` is **allowed** (W_c/q·K scoring reads global K/Q non-committingly, rolling the cache back).

**So: no C-level refactor is needed for the basic append.** Remaining engineering:

1. **Gate it** — no `G-PERSIST-KV` exists yet (grep found none). This is the one real deliverable (see §4).
2. **Capacity envelope** — bump `Pmax` (`SP_DAEMON_KVDECODE_PMAX`, 4096→larger) + enable the **SWA ring** (`SP_DAEMON_KVDECODE_RING_W`) for long sessions; gate the **persist × ring** interaction (the ring's wrap-rewind is proven in isolation by G-1b-WRAP-NULL; persist+ring is the new combination).
3. **Diverging-tail policy** — `drop_n > 32` falls back to a full reset (correct, O(n) that one turn). Fine as a safety valve; revisit only if real conversations trip it often.
4. **API-shape constraint** — `KV_COMMITTED` is a SINGLE global sequence ⇒ **one active conversation at a time**; switching `chat_id` LCP-misses → full reset. Acceptable for the single-organism loop; multi-conversation co-residency is a separate (unscoped) extension.

## 3. Session isolation: Gemma GPU vs coder CPU (S3 — confirmed safe)

- **Gemma resident cache** = the single global `sp_g4_kv` on GPU (CUDA `g_w` weights, **Mutex-serialized**); all state-mgmt (`position`/`rewind`/`reset`) goes through the `cuda_kvdecode_handle`. `KV_COMMITTED` tracks *this* cache only.
- **Native coder delegate** (TELE-14 `run_telepathy_native`) = its **own** `SpModel`/`SpSession`, **CPU L1** — no CUDA backend registered on it ⇒ it never touches `g_w`; host memory only.
- **Isolation is structural**: separate handles, separate memory spaces (GPU vs host), separate forward paths (`gemma4_kv` CUDA vs `qwen3` CPU). A `rewind`/`reset` on the Gemma handle cannot reach the coder session, and vice-versa. `g_w` stays keyed to the 12B because the coder is CPU and never rebuilds it.
- **Forward note**: the coder is currently a standalone verb, not yet invoked from the live chat loop. When wired in, it must run off-thread without taking the Gemma cache Mutex — trivially safe since it shares zero state. No new isolation risk for `SP_PERSIST_KV` itself (the coder isn't involved in a persist turn).

## 4. The gate (kill-test) — G-PERSIST-KV

**Claim:** persist-ON (suffix-append) is byte-identical to persist-OFF (fresh full re-prefill) across a multi-turn conversation, with a tok/s win on long context.

- **Correctness:** run a scripted N-turn conversation twice — `SP_PERSIST_KV=1` vs unset — and assert **identical output tokens AND bit-identical per-turn logits** at every turn. *Kill: any divergence.* (Bit-exact-when-off is automatic: `prefill_from=0` is the null floor.)
- **Performance:** on a long conversation (e.g. ≥2K committed tokens), persist-ON holds ~steady tok/s while persist-OFF decays (reverse the measured 30→1). Report both with the turn count + committed length (scope travels with the figure).
- **Ring combo (P2):** repeat the correctness assert with `SP_DAEMON_KVDECODE_RING_W` set + a larger `Pmax`, exercising at least one wrap; persist×ring must stay byte-identical to full-cache persist within the SWA window.

## 5. Phased plan (no build this pass)

- **P1 — Gate + enable (small).** Author `G-PERSIST-KV` (multi-turn byte-identity + tok/s), full-cache, `Pmax=4096`. If green, `SP_PERSIST_KV` becomes the default for the plain decode path. *This is the whole O(1)-append win for normal-length sessions.*
- **P2 — Long-session capacity.** Enable the SWA ring + raise `Pmax`; gate persist×ring byte-identity + wrap. Lands ~40K-token sessions on the 2060.
- **P3 — Unbounded.** Wire the global-layer eviction to the existing XBAR Ring-2/Optane demotion (the 8 globals are the O(n) floor). Only this step is genuinely new engineering, and it reuses a closed tier.

**Bottom line:** the scaling fix is mostly *already in the tree*. P1 is a gate + a flag flip; the real new work is the long-session capacity path (P2/P3), which leans on the SWA ring and the XBAR demotion tier that are themselves already built.
