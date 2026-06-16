# RELEASE — KAIROS Latent Interrupt (KAI-2) + Audio-Port Bridge (KAI-3)

**Release date:** 2026-06-16
**Repos:** `shannon-prime-system-engine` (impl) · `shannon-prime-lattice` (contracts/docs)
**Model context:** the **12B is gemma-4-12B "Unified"** (no AltUp, no PLE), **OK_Q4B `-b1`**, on the **RTX 2060 (12 GB, sm_75)**.

---

## 0. Framing (load-bearing — two distinct-but-related programs)

This release closes one step of **KAIROS** and opens the **GNA "EAR" line**. They are **separate but related**, and they share one proven primitive — the `gemma4_kv_inject` residual-entry seam. Do not conflate them.

- **KAIROS** = the **latent interrupt / agency-time axis** = the **BASIS OF THE XBAR latent-space memory** (the token-free, receipted memory crossbar). Lineage: **KAI-1 / 1b / 1c** (resident heartbeat NO_OP discipline; O(1) bit-exact KV rewind; wrap-aware journaled SWA ring) + **KAI-2** (the latent interrupt, this release).
- **GNA "EAR" line** = a **separate-but-related sibling program**: real **AUDIO in/out** via the Intel NUC "Beast Canyon" **GNA 2.0 always-on hardware** — an always-on *ear* that gives the frozen model a real-world audio sense. **KAI-3 (the audio-port frame projector) is the BRIDGE into the GNA line.** It reuses KAIROS's frozen `gemma4_kv_inject` seam but is **not** a replacement for KAIROS latent memory.
- The audio/GNA work is a **deliberate near-term pivot**; after the EAR lands, the project **pivots back to XBAR (KAIROS latent memory)**.

---

## 1. Executive summary

A resident daemon must be **interruptible**: an environment event should be deliverable mid-idle as a latent payload, not a verbose text frame (which costs the **44 text-delivery steps** measured in CONTRACT-KAIROS §6.2).

- **KAI-2 (latent interrupt) is CLOSED — BOUNDED.** Phase 1 proved the latent-delivery seam `gemma4_kv_inject` GREEN as a frozen asset (a real-token embedding **sequence** pivots the model: salient→ACTION, idle→NO_OP). Phase 2 then showed that a learned **single static compressed packet** (`KAI2Codec`) **cannot** carry the pivot — the wall is **sequence-positional** (a fixed-width packet compresses out the per-position directional variance attention routes on), not manifold-distance and not capacity. No more codec-compression cycles.
- **KAI-3 (audio-port frame projector) is CLOSED GREEN** — the **inverse** of KAI-2: inject a **sequence of N projected frames, 1:1 with positions, no compression**, via the new `gemma4_kv_inject_seq` ABI. On the resident 12B the metal gate hits **8/8 semantic pivots**. KAI-3 is the bridge into the GNA "EAR" line.
- **Next milestone: GNA Stage 2 (#154)** — replace the synthetic anchor matrix with the real GNA/CNN audio front-end.

---

## 2. KAI-2 — latent interrupt (CLOSED, BOUNDED)

**Engine commit `c5628e4` · lattice contract CONTRACT-KAIROS-K0-K1 §6.6 commit `2675c79`.**

| Leg | What | Result | Verdict |
|---|---|---|---|
| Phase 1 — delivery seam | `gemma4_kv_inject` residual-entry seam; EMB control (a real-token embedding **sequence**) | A salient event sequence pivots → `<ACTION>`; an idle event → `NO_OP`. **EMB control 2/2** on the 12B OK_Q4B / RTX 2060 | **GREEN — frozen verified asset** (the seam KAI-3 + the GNA EAR line build on) |
| Phase 2 — compressed codec | learned single-event codec `KAI2Codec`; maximally-constrained `t10` packet: **k=16**, on-manifold **cos 0.9913**, sharp **τ=0.2**, held-out **`val_KL` plateau 0.9157** | The static packet **MISSED** the salient pivot (**PACKET 1/2**) | **BOUNDED** |

**Root cause (kept on the record):** the wall is **SEQUENCE-POSITIONAL** — a fixed-width *static* packet compresses out the per-position directional variance attention routes on. It is **NOT** manifold-distance (the packet is on-manifold, cos 0.9913) and **NOT** capacity. **Decision: no more codec-compression cycles.** This honest negative is exactly what motivated KAI-3 (deliver a *sequence*, not a packet).

---

## 3. KAI-3 — audio-port frame projector (CLOSED GREEN; the GNA "EAR" bridge)

**Engine commit `e35a227` · lattice contract CONTRACT-KAIROS-K0-K1 §7.3 commit `e826950`.**

The inverse of KAI-2: inject a **SEQUENCE of N projected frames (1:1 with positions, no compression)** so the per-position directional variance survives.

| Gate / metric | Setup | Result |
|---|---|---|
| **G-KAIROS-3-NULL** (seam equivalence) | `gemma4_kv_inject_seq` = strict loop over the frozen inject+prefill primitives, vs the inline EMB loop | **2/2 byte-identical** |
| Synthetic ladder (held-out) | per-position MLP 640→V_sub + on-manifold binder; `noise_rel=0.1` (2.5× noise:signal) | per-position **top-1 1.000**, manifold **cos 0.9998** (binder noise-independent) |
| Real-token train | `V_sub=60` | **top-1 0.931**, **cos 0.9937** |
| **G-KAIROS-3 metal gate** (`SP_G4_KAI3` manifest) | resident 12B; salient + idle events | **8/8 SEMANTIC pivots** — salient → event-specific ACTION ("Restart the build process", "Check disk status and run SMART"); idle → `NO_OP`; `KAI3_GATE_EXIT=0` |

**The projector** (`tools/audio_port/{gen_synth_frames,frame_projector,emit_corpus}.py`): per-position MLP `640→V_sub` + on-manifold binder `softmax(logits/τ)·W_sub` (with `W_sub` = real embed rows × √H), trained with **DENSE PER-POSITION cross-entropy** — the fix for the KAI-2 `t10` sparse-gradient plateau; **the pivot is a consequence, never the train signal.**

**Done LOCAL / NO CLOUD.** The engine now owns the gemma tokenizer (new `SP_G4_TOK_DUMP` mode), so a cloud G4 for a tiny MLP would be over-provisioning.

**Receipts:** `_xbar/p2b/kai3_gate.log`, `tools/audio_port/KAI3-LADDER-RESULTS.md` (engine repo).

---

## 4. Frozen assets (the load-bearing primitives this release establishes)

| Asset | Where | Role |
|---|---|---|
| `gemma4_kv_inject` | engine `cuda_forward.cu` | the residual-entry seam — latent delivery into the frozen 12B; **GREEN frozen asset (EMB 2/2)**. Shared by KAIROS (KAI-2) and the GNA EAR line (KAI-3) |
| `gemma4_kv_inject_seq` | engine `cuda_forward.cu` | new ABI — inject a **sequence** of N frames 1:1 with positions (no compression); strict loop over the frozen inject+prefill primitives (G-KAIROS-3-NULL byte-identical to the inline EMB loop) |
| `frame_projector.py` (+ `gen_synth_frames.py`, `emit_corpus.py`) | engine `tools/audio_port/` | per-position MLP 640→V_sub + on-manifold binder, trained with dense per-position cross-entropy |
| `sp_tok_dump` / `SP_G4_TOK_DUMP` | engine (gemma tokenizer) | engine-owned tokenizer dump — lets the projector train + gate **locally**, no cloud |

---

## 5. Next milestone — GNA Stage 2 (task #154)

Replace the synthetic anchor matrix **A** with the **real GNA/CNN audio front-end**:

- live audio / telemetry → **40 ms / 640-float / 16 kHz frames**
- `audio_token_id = 258881`
- the KAI-3 **delivery + projection architecture is LOCKED** — Stage 2 swaps only the front-end (synthetic → real GNA hardware).

This is the GNA "EAR" line proper (real-world audio sense via the always-on NUC GNA 2.0). After it lands, the project **pivots back to XBAR (KAIROS latent memory)**.

---

*Pointers: `CONTRACT-KAIROS-K0-K1.md` (§6.6 KAI-2, §7.3 KAI-3) · `PPT-LAT-STATE.md` (KAIROS section) · `RFC-XBAR-auditable-latent-crossbar.md` (scope note: XBAR=KAIROS latent memory vs the GNA EAR sibling) · `CURRENT-STATE-OF-PROJECT.md` §4.4–4.6.*
