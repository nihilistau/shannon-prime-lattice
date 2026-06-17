# CONTRACT-XBAR-C2 — the Memo curator: the autonomous Ring-2 recall loop

**Status:** SPEC (opened 2026-06-17, the turn after P3 closed end-to-end). Forward spec, not yet built.
**One line:** P3 made the latent crossbar *read / write / compress / replay / recall-quality-bounded*. C2 is the **policy that drives it** — a resident loop that, on its own, decides *when* to search memory, *which* episode to pull, and hands that episode to the proven `SP_REPLAY` inject seam, all under the same bit-exact-when-off + bounded-deflection discipline the substrate is built on.

**Reads first (do not re-derive — all proven/in-tree):**
- `CONTRACT-XBAR-C1-lite-curator.md` — the **control flow is already proven** on the qwen3 CPU two-ring: PROPOSE→GATE→PROMOTE/REWIND (G-C1L-1), recall-hit telemetry `sp_arm_hits_*` (G-C1L-2 step 1), cold-evict mask (G-C1L-2 step 2), and the `SP_REPLAY` replay-decode null (G-C1L-0b). **C2 is C1-lite's loop, moved online and onto Exec.**
- `CONTRACT-XBAR-P3-ring-on-exec.md` — P3.0 manifest (`sp_xbar_block_off`), P3.2 spill/page/ring, P3.2-b-2b learned-LSH router, Phase C O(1) slab, C-c NIAH, **P3.3 `SP_REPLAY` replay-write (G-P3-SHARED, 12B+E2B)**, **P3.4 `G-P3-PPL` recall-quality (+1.38% < 2%)**.
- `RFC-XBAR-…md §3.1` — the Ring-1/2/3 hierarchy and the "recall-cue → episode-id → `SP_REPLAY`" line this contract makes concrete.

---

## 1. What's already built (the substrate this drives)

| Primitive | Surface | Proven by |
|---|---|---|
| Recall router (rank positions by projected-query affinity) | `sp_arm_select` / `sp_arm_select_geom` (core/arm/arm.h) | §P3.2-b-2b G2, C-c NIAH |
| Recall-hit / coldness telemetry (LRU signal) | `sp_arm_hits_attach/detach` | G-C1L-2 step 1 |
| Cold-evict (drop dead positions, lossless) | `sp_arm_evict_attach` (mask in `sp_arm_select`) | G-C1L-2 step 2 |
| Episode store on disk (verbatim K/V, owner-indirect) | `sp_xbar_manifest_*` + `sp_xbar_block_off`; Ring-2 backend `sp_arm_ring2_stdio_open[_ro]` / `_register` | P3.0, P3.1b, P3.2-a |
| **Inject a recalled episode into the live decode** | **`SP_REPLAY` / `SP_REPLAY_NPOS`** seam in `gemma4_decode_cuda` (graph + velocity prefill stores) | **P3.3 G-P3-SHARED** |
| Recall is perplexity-bounded | `SP_G4_SCORE` deflection ≤ the locked 2% | **P3.4 G-P3-PPL (+1.38%)** |
| Resident decode + O(1) rewind/commit (the loop's substrate) | `gemma4_kv_open/prefill/decode/rewind/commit/close`, `gemma4_kv_inject[_seq]` | KAI-1b/1c, KAI-2/3 |
| Resident daemon heartbeat (the tick clock) | `sp_daemon` KAIROS runner, deterministic event-tape loop | G-KAIROS-1 (6h soak) |

**The substrate is complete. It is inert until a policy fires it. That policy is the Memo curator. The three things that do not yet exist — and are this contract's whole job — are the CUE, the INDEX, and the RESOLVER.**

---

## 2. The three missing pieces (the design)

### 2.1 The episode INDEX (how memories are named and made addressable)
A flat, append-only, auditable **episode registry** on Optane Ring-2 (`episodes/registry.jsonl`, one line per episode — the receipts-first convention):
```
{ episode_id, ring2_path, manifest_path, npos, sig[r], created_tick, last_recall_tick, recall_count, sha256 }
```
- `episode_id` = monotonic `u64` (or content-hash; monotonic is cheaper and ordering = recency).
- **`sig[r]` = the episode's recall KEY: the r-dim mean (centroid) of its global-owner projected keys** — `mean_pos sp_arm_project(R, K_global[pos])` over the episode, computed ONCE at write time with the *same frozen R / learned-LSH M* the live router uses. This is the load-bearing design choice: **the episode's address lives in the exact projection space the router already ranks in**, so resolving a cue is one r-dim dot per episode, not a model call.
- Owner-indirection + the byte law are inherited unchanged from the P3.0 manifest (`sp_xbar_block_off`). No new on-disk K/V format — episodes ARE the P3.1b serialized stores.

### 2.2 The CUE (when to search memory)
Computed at each curator tick from the **live query** — no extra forward, reuse the projection already minted in the decode path:
- **Cue vector** `q_sig[r] = sp_arm_project(R, q_global)` of the current step's global query head(s) (mean over heads), the same projection `sp_arm_select` computes internally.
- **Trigger** = `max_e ( q_sig · registry[e].sig ) ≥ τ_cue` AND a rate-limit (no recall within `W_cool` ticks of the last, to bound churn). τ_cue is **pre-registered** (set from the NIAH-style separation between a planted-relevant episode's score and the background-episode scores), never tuned post-hoc.
- Rationale: the trigger is the recall router *applied to the index instead of to in-window positions* — same math, same frozen geometry, so a cue that fires is a cue the downstream gather would also act on. Cheap (r·|registry| flops), deterministic, auditable.
- Tick source = the existing KAIROS heartbeat (`sp_daemon`); the curator is a feature-gated module on that loop, NOT a new daemon.

### 2.3 The RESOLVER (cue → episode_id → payload)
On a fired cue: `episode_id = argmax_e q_sig·sig[e]` (top-1; top-k optional for dual-candidate), `ring2_path` + `npos` from the registry row → that IS the `SP_REPLAY` dir + `SP_REPLAY_NPOS`. The handoff is literally setting the seam's inputs. Bump `last_recall_tick` / `recall_count` (feeds the C1-lite cold-evict LRU signal).

---

## 3. The round-trip loop (the autonomous Ring-2 recall)

Resident Exec on `gemma4_kv_*`, curator on the heartbeat:
```
loop each tick:
  1. Exec decodes the live step (gemma4_kv_decode / prefill).
  2. CUE  : q_sig = project(current global query);  fired = (max_e q_sig·sig[e] ≥ τ_cue) && cooled.
  3. if !fired: continue (the silent-by-default majority — the KAIROS discipline).
  4. RESOLVE: e* = argmax_e q_sig·sig[e];  (dir, npos) = registry[e*].
  5. PROPOSE (shadow): snapshot the cache (gemma4_kv_snapshot / a commit boundary);
     inject e* via SP_REPLAY (dir, npos) as a recalled-history prefix at the recall slot.
  6. GATE  : SP_G4_SCORE deflection of the continuation under the injected episode.
            PASS iff deflection < 2.0% (the P3.4 bound) AND the recalled fact is present
            (NIAH-style readback when the episode carries a fact).
  7. PROMOTE: gate PASS -> keep the injection, gemma4_kv_commit (the recall is retained,
            recall_count++);  REWIND: gate FAIL -> gemma4_kv_rewind to the snapshot
            (the recalled episode is discarded, byte-exact — the C1-lite transactional law).
```
**This is C1-lite's propose→gate→promote/rewind, run online, with the gate = P3.4's deflection bound and the rewind = KAI-1b's O(1) shear.** Every closed primitive snaps in at a named boundary — the same composition that let `SP_REPLAY` ∘ `SP_G4_SCORE` need zero new engine code in P3.4.

---

## 4. Pre-registered gates (thresholds fixed BEFORE code)

- **G-MEMO-NULL (null floor).** Curator feature OFF ⇒ Exec decode is byte-identical to the P3-closed baseline. The whole loop is bit-exact-when-off. *Falsify:* any drift with the curator disabled.
- **G-MEMO-CUE (the trigger is selective, not trigger-happy).** Plant one relevant episode + K background episodes in the registry; run a context the relevant one answers. The cue must **fire on the relevant episode and stay below τ_cue for the background** (a separation, reported as a margin — the NIAH/selectivity discipline). *Falsify:* fires on background, or misses the relevant.
- **G-MEMO-LOOP (the round trip works AND is bounded).** Full loop on a planted fact: (a) the recalled fact is reproduced in the continuation (NIAH-style HIT); (b) deflection < 2.0% (P3.4); (c) **negative control** — an irrelevant cue either does not fire or is REWOUND by the gate, leaving the cache byte-exact. *Falsify:* fact lost, deflection ≥ 2%, or a bad recall sticks.
- Artifacts: 12B-b1 (capacity) + E2B (owner-indirection), mirroring P3.3. Receipts → `tests/fixtures/xbar_c2/`.

---

## 5. Scope fence (what is DEFERRED, budget-gated)

- **Ring-3 consolidation / the P2.b gist adapter / NIGHTSHIFT are OUT OF SCOPE here.** C2 is **Ring-2 verbatim autonomous recall only**. Ring-3 (n→k gist compaction) stays behind `G-R3-LOSS` (the irreversible recoverable-information gate, RFC §3.1) and the operator's training-budget green; it is a downstream tier, not part of this loop.
- **No learned cue.** The cue is the frozen/LSH projection dot — no new training. (A learned cue head is a possible later refinement, explicitly not in C2.)
- **Single-episode recall first.** Dual-candidate / dual-ring (Ring-2 + Ring-3) recall (`G-R3-DUALROUTE`) is deferred to after C2 closes.

## 6. Build order (smallest falsifiable steps)
1. **Registry + sig writer** — extend the P3.1b WRITE path to also append a registry row with `sig[r]` (centroid of projected global-owner keys). Standalone gate: registry round-trips, `sig` reproducible (cf. G-C1L-0a re-projection determinism).
2. **Resolver (offline)** — `cue → argmax episode_id` over a synthetic registry; G-MEMO-CUE selectivity on planted vs background episodes (no Exec yet).
3. **Online loop on Exec** — wire steps 1-7 onto `gemma4_kv_*` + `SP_REPLAY`; G-MEMO-NULL then G-MEMO-LOOP on 12B + E2B.
4. Land receipts + contract run-record + STATE/handoff; then (operator-gated) open Ring-3.

*The substrate reads, writes, compresses, replays, and holds its perplexity. C2 is the first turn where it decides — on its own — what to remember.*
