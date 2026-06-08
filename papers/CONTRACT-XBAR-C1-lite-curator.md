# CONTRACT XBAR-C1-lite — Memo v0, the heuristic curator loop on the qwen3 CPU two-ring

**Parent:** RFC-XBAR v1 §5 (C1-lite) + §7 (NIGHTSHIFT). **Status:** SPEC + seam analysis (2026-06-09). The parallel track to P2.b — needs no cloud, no 12B, no training; runs on the proven qwen3 CPU two-ring (C2.2, `T_ARM_GENKV` green).
**One line:** stand up the full **propose → gate → promote/rewind** control flow of the curator on the existing two-ring, with a heuristic Memo v0 (cold-evict / merge) and the gate = PPL delta on the consolidated episode — before any learned curator (P2.b adapter = C2) or CUDA-ring port (P3).

---

## 1. Seam analysis — three findings from the 2026-06-09 survey (read before coding)

The survey of `core/forward/decode.c` + `core/arm/arm.c` + `include/sp/arm.h` surfaced three architecture facts that reshape C1-lite's first slice. None were obvious; all are load-bearing.

1. **The two-ring is per-decode-EPHEMERAL.** `qwen3_generate_kv` / `qwen3_ppl_decode` build the recall index `projk` (`[NL × P × NKV × r]` f32) and the Ring-2 store *fresh inside the call* and `free()` them at `done:`. There is **no persisted episode object** for a curator to sit between. The curator's whole premise — operate on stored state between sessions — has no seam yet. *This is exactly RFC §7's "episode persistence" item, now confirmed as a prerequisite, not an add-on.*

2. **`projk` is RECOMPUTABLE from the persisted K store.** The router index is just the frozen ±1 Rademacher projection of each position's post-RoPE K (`sp_arm_project`). The Ring-2 K stream (the stdio backend's `sp_arm_ring2_k.bin`) already persists that K. So episode persistence does **not** need to serialize `projk` — it can be rebuilt by re-projecting the stored K on load. Persisted episode = {K store, V store, manifest} + a re-projection pass.

3. **Eviction is DOUBLY entangled, and the stdio store TRUNCATES on open.** (a) Dropping a block from the Ring-2 store alone does not change recall — the router selects by `projk` score over all positions independently; a curator that evicts must prune *both* the store and the `projk` index (or the rebuilt-from-store index, which makes #2 the clean path). (b) `sp_arm_ring2_stdio_open` uses `fopen(..., "w+b")` — "fresh store per open" — so the current decode **cannot load a pre-curated store**; replaying a curated episode needs a non-truncating load path or a registered backend that serves curated data.

**Net:** C1-lite's enabling capability is an **episode replay decode mode** (load persisted K/V + rebuild `projk` + score a window against it). The curator + gate compose on top of that. The cleverness (which heuristic) is downstream of the plumbing (can we replay a foreign episode at all).

## 2. Staged plan (each stage its own gate; null control first, per P1 discipline)

| Stage | What | Gate (its own metric) |
|---|---|---|
| **C1L.0 — episode persistence + replay** | A decode mode that LOADS a persisted episode ({`sp_arm_ring2_k/v.bin`, manifest}), rebuilds `projk` by re-projecting the stored K, and runs `qwen3_ppl_decode`-style scoring of a query window against it. Either a non-truncating stdio "load" backend or a registered in-RAM replay backend. | **G-C1L-0 (replay null):** replaying an un-curated episode reproduces the same-window PPL of the original in-line streaming run within the Spinor-KV lossy bound (the run that produced it) — proves replay is faithful before any curation |
| **C1L.1 — the loop, identity curator** | propose→gate→promote/rewind harness with a NO-OP curator (proposes the episode unchanged to a shadow dir). | **G-C1L-1 (loop null):** identity propose → gate PASS → promote → replayed episode byte-identical to source; a forced reject → rewind leaves the canonical episode untouched. The control-flow null. |
| **C1L.2 — cold-evict heuristic** | instrument `sp_arm_select` to count per-position recall hits (the access/association signal — RFC §7 = the LRU telemetry); curator evicts the coldest K% of positions from {K store, V store} and rebuilds `projk` over survivors. | **G-C1L-2 (consolidation):** ≥1 promotion that SHRINKS the episode (fewer stored positions) while PPL delta on a held-out window stays within tolerance vs the un-curated replay; a too-aggressive evict that blows the PPL budget is correctly REWOUND |
| C1L.3 (stretch) | merge-adjacent-similar instead of pure evict (Spinor-block average of near-duplicate positions) | recall@budget ≥ cold-evict at equal episode size |

## 3. Gate currency & receipts

PPL via `qwen3_ppl_decode` (teacher-forced, the C2.1 instrument). Episode size = stored position count × per-position bytes. Every promotion logs a receipt: positions evicted/merged, before/after PPL + size, accept/reject reason — the auditable-dream record (RFC §6). Model: the proven `qwen3_rt.sp-model` (OK_Q8 swivel). Honest bound carried from C2: Spinor-KV recall is a ~6.5%-argmax-flip lossy overlay, so the replay null gate is bounded-divergence, not bit-exact (the weight path + recall-off remains the bit-exact floor).

## 4. Scope discipline

C1-lite proves the curator's **control flow + a working heuristic on real KV**, nothing about learned compression (that is C2 = the P2.b adapter applied to ring state). It runs entirely on the qwen3 CPU path; the gemma4-CUDA ring is P3. NIGHTSHIFT (N1) = C1-lite's loop run offline under schtasks over a persisted episode — so C1L.0's persistence format is also NIGHTSHIFT's episode format. No silent gate revisions; surface upstream.
