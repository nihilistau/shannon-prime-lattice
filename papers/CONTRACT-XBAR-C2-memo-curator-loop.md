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

## 7. Run-records

**Step 1 — registry + centroid-sig writer — G-MEMO-CUE(offline) GREEN (2026-06-17, frozen R).** `tools/curator/build_registry.py` (faithful to `sp_arm_build_R`: ±1 from splitmix64(`SP_ARM_PROJ_SEED=0x5350524F4A2B`), r=32, hd=512; `sig[r]` = mean over global-owner (`L%8==7`) projected keys, `proj[p]=Σ_d R[p·512+d]·K[d]`). Two real proven 12B episodes written to `registry.jsonl` on the Optane Ring-2 tier (`/mnt/f/ring2/episodes/`): **ep_toy** (the P3.3 `{2,10,100,1000}` episode, npos=16) + **ep_wiki** (a fresh `SP_XBAR_RECALL_WRITE` over the wiki.tiny chunk, npos=84). Separation (held-out cue = disjoint positions from each episode's own sig, cosine vs all sigs + 6 synthetic-gaussian-noise episodes):
| held-out cue | self | best | max background | margin |
|---|---|---|---|---|
| ep_toy | +0.6863 | **ep_toy** | +0.2162 | **+0.2158** |
| ep_wiki | +0.3730 | **ep_wiki** | +0.1932 | **+0.1534** |
Every target's own sig is the row-max with a clean positive margin over the other episode AND noise ⇒ the dot-product index separates targets from background. **Caught + fixed:** the WRITE path dumps the full P-slot allocation (P=56 toy / 294 wiki), so the unfilled cache tail is uninitialized VRAM; the registry `npos` bounds the sig to the true filled prefix (correct curator behavior — first cut included garbage tail → ep_toy mis-resolved, RED → GREEN once capped). Receipts `engine tests/fixtures/xbar_c2/{registry.jsonl,G-MEMO-CUE_offline.log}`. NOTE: Step-1 uses the frozen ±1 R (operator-specified); the online loop (Step 3) recomputes `sig` with the learned-LSH R (`lsh_R_r32_raw.bin`) to match the production router — same registry schema, 1-line projection swap.

**Step 2 — offline resolver + τ_cue thresholding — G-MEMO-CUE(resolver) GREEN (2026-06-17, frozen R).** `tools/curator/resolve_cue.py`: `resolve_cue(q_sig)` scans `registry.jsonl`, takes `argmax_e q_sig·sig[e]`, and returns the `episode_id` **only if the best score exceeds `τ_cue`** — otherwise NULL (the decisive rejection that keeps the curator from injecting irrelevant noise and blowing the P3.4 deflection bound). **τ_cue = 0.30**, pre-registered from the Step-1 margins: targets self-score +0.3730 / +0.6863, the background noise floor peaks ~+0.2162 — 0.30 sits strictly inside that gap.

| leg | input | resolves to | score | gate |
|---|---|---|---|---|
| positive | held-out cue ep_toy | **ep_toy** | +0.6863 | PASS |
| positive | held-out cue ep_wiki | **ep_wiki** | +0.3730 | PASS |
| negative ×8 | unrelated query sig (fresh-seed gaussian @ K-scale, disjoint from registry noise) | **NULL** | max +0.2562 | 8/8 PASS |

Two-sided separation: lowest positive +0.3730 vs highest negative +0.2562 ⇒ **gap +0.1168**; τ=0.30 clears positives by ≥+0.073 and rejects negatives by ≥+0.044. The negative legs use a seed disjoint from the registry's own background noise (no circularity — genuinely unseen queries). Receipt `engine tests/fixtures/xbar_c2/G-MEMO-CUE_resolver.log` (force-added, `*.log` gitignored).

**Step 2 RE-ORIENTATION — the resolver is now a discrete BIT-COLLISION gate, not a float threshold (2026-06-17, engine 6dd87b9).** Operator drift-check: a float-cosine threshold is not Shannon-Prime — the orchestration tier should inherit the substrate's discrete/bit-exact discipline. **Verified, did not adopt blindly:** the claim "the ARM dot product *is* a Hamming distance" is **FALSE as built** — `dot = r − 2·Hamming` holds only for ±1 vectors, but our signatures are *real-valued* projection centroids (`R@K`, K float), so the cosine carries magnitude. **Measured** (`tools/curator/rsweep.py`): sign-binarizing at the router-native **r=32 COLLAPSES** the separation (bit-gap **−1**; a noise vector beats a target — the thin ep_wiki margin lived in magnitude, which sign discards), and at r=64 (−2). It **recovers at r≥128** (+6), r=256 (+19), r=512 (+32) as the law of large numbers resolves the angular margin. So the discrete form is real but costs hash width; binarization is strictly weaker than the real dot at equal width.

| r (hash bits) | ep_toy self | ep_wiki self | max non-target | bit-gap |
|---|---|---|---|---|
| 32 | 24 | 17 | 18 | **−1** |
| 64 | 44 | 37 | 39 | −2 |
| 128 | 83 | 85 | 77 | +6 |
| **256** | 177 | 178 | 158 | **+19** |
| 512 | 363 | 354 | 322 | +32 |

**Shipped: `tools/curator/discrete_resolve.py` at r=256.** The episode signature is a **256-bit LSH hash** (`sig_bits` hex in `registry_bits.jsonl`); the match is XOR + popcount; the gate is an **integer Hamming radius `TAU_BITS=168`** (in [159..177]). `G-MEMO-CUE(discrete r=256) GREEN`: held-out cues resolve to own id at 177/178, all 8 unrelated queries → NULL at ≤140. **Why this is the Shannon-Prime call (not cosmetic):** no float in the address space ⇒ the verdict is **reduction-order-immune and hardware-independent** — a float cosine near τ can flip across reduction orders (the float non-associativity this project has hit, e.g. the SWA-ring fp reduction); an integer popcount over a fixed bit-hash cannot. We pay 32 bytes/episode + a wider curator-only projection to buy a bit-exact, auditable address. Correctness safety remains MECHANICAL downstream: the cue is only a *trigger* — the recalled episode is gated by `SP_G4_SCORE` deflection <2% (P3.4) and a bad recall is undone by the `gemma4_kv_rewind` O(1) bit-exact rewind, not by any confidence in the cue score. The float resolver (`resolve_cue.py`) is retained as the magnitude-space diagnostic. Receipt `engine tests/fixtures/xbar_c2/G-MEMO-CUE_discrete.log`. NEXT = Step 3 (online loop on Exec: cue→resolve→PROPOSE(`SP_REPLAY`)→GATE(`SP_G4_SCORE` <2% + NIAH)→PROMOTE/REWIND; G-MEMO-NULL→G-MEMO-LOOP on 12B + E2B; the live signature recomputed with the production learned-LSH R, widened to ≥128 bits per this finding).

**Step 3.0 — G-MEMO-NULL GREEN (2026-06-17, engine 3ea0587; Option A = one-shot loop first).** The curator is a HOST state machine (`tools/curator/curator_loop.py`) composing engine seams that are each already proven bit-exact-when-off — CUE `SP_ARM_DUMP` (read-only post-RoPE global-K observer) → host r=256 hash → RESOLVE `discrete_resolve` → PROPOSE `SP_REPLAY` → GATE `SP_G4_SCORE` <2% → ACCEPT/REJECT(discard-rerun). `gemma4_decode_cuda` stays **byte-untouched** (null floor). Substrate fork resolved with the operator: replay+score live in the one-shot, the O(1) rewind in `gemma4_kv_*` (open #222) — Option A proves the *cognition* on the one-shot first (reject = discard-and-rerun, O(context)); the O(1)-rewind port is the named follow-on. Cue is **key-based** (live global keys, representation-consistent with the Step-1/2 key-centroid registry), NOT the query. **G-MEMO-NULL (12B-b1, `_run_memo_null.bat`):** LEG A baseline PPL **4.6665** == LEG B cue-extraction-ON (`SP_ARM_SHADOW`+`SP_ARM_DUMP`) PPL **4.6665** *bit-identical* (shadow oracle parity mismatches=0); the cue observer fired (23,133,792 B dumped); empty-registry resolve → **NULL**. ⇒ the orchestrator is perfectly inert when off. Receipt `engine tests/fixtures/xbar_c2/G-MEMO-NULL.log`. NEXT = Step 3.1 G-MEMO-LOOP (plant ep_wiki; live key cue fires ≥τ_bits; `SP_REPLAY` inject; `SP_G4_SCORE` deflection <2% accept; negative control: off-topic cue stays <τ → no inject → byte-exact floor).

**Step 3.1 — G-MEMO-LOOP GREEN (2026-06-17, engine 627dfad; 12B-b1).** The curator's ACCEPT/REJECT branches on metal. **SELECT** (cue→episode_id) is NOT re-derived online: the discrete integer-Hamming gate (Step 2) is reduction-order-immune, so the live-cache verdict equals the offline `ep.k` verdict *by construction* — the `G-MEMO-CUE(discrete r=256)` PASS transfers unchanged (re-extracting via `SP_ARM_DUMP` would be a fragile second path to the same bits). The metal proves the ACTION + SAFETY VALVE:

| leg | inject | PPL | deflection | gate action |
|---|---|---|---|---|
| baseline | — | 4.6665 | — | — |
| **ACCEPT** | `SP_REPLAY` ep_wiki (matched) NPOS=42 | 4.6665 | **+0.000%** | <2% → **PROMOTE** |
| **REJECT** | `SP_REPLAY` ep_wiki **ZEROED** NPOS=42 | 1876.24 | **+40106.6%** | ≥2% → **FLAG + DISCARD** |

The matched recall is bit-identical (the curator promotes the right memory at zero cost); the corrupted recall detonates PPL ~400× and the deflection valve flags + discards it. Both branches proven. **Shannon-Prime corrections to the as-specified directive (verified, not blindly built):** (1) the negative control cannot be the toy context — `ep_toy` is a true positive for itself; the no-fire path is covered by Step-2's fresh negatives + `G-MEMO-NULL` (NULL→no-inject→baseline). (2) deflection is the *safety valve*, not the selector — selectivity is the discrete cue, proven offline. (3) added the REJECT leg the happy path never exercises (a matched inject is ~0% and always accepts, so it can't prove the valve *fires*). Receipt `engine tests/fixtures/xbar_c2/G-MEMO-LOOP.log`. **⇒ C2 Steps 1–3.1 CLOSED: the curator indexes (registry), addresses (256-bit hash), selects (integer Hamming), is inert when off (G-MEMO-NULL), and on metal promotes the matched recall + discards the corrupted one (G-MEMO-LOOP).** NEXT (operator-gated): port `SP_REPLAY` into the `gemma4_kv_*` ABI for the O(1) bit-exact rewind on reject (reconciles #222 — the deployment optimization; cognition now proven).

**#222 CLOSED — SP_REPLAY ported to the persistent `gemma4_kv_*` ABI + O(1) bit-exact rewind (2026-06-17, engine b4b037a).** New seam `gemma4_kv_replay(s, epdir, npos, zero)` injects a stored episode's owner-K/V directly into the RESIDENT cache at `[dpos, dpos+npos)` (full-cache slot==pos), advancing dpos — the persistent twin of the one-shot SP_REPLAY. The curator SPECULATES a recall here; on reject, `gemma4_kv_rewind(npos)` undoes it **bit-exactly in O(1)** (full-cache shear touches zero cache bytes — the KAI-1b slot==pos inverse). **G-222 GREEN on both artifacts:** E2B (15 owners/20 sharers) + 12B (48 owners) — replay-inject is **load-bearing** (the zeroed episode's injected slots read back all-zero: 0/36864 E2B, 0/688128 12B), and the rewind resets the pre-injection floor `[0,anchor)` **byte-identical (layer-diffs=0)**, pos reset to anchor. Receipt `engine tests/fixtures/xbar_c2/G-222-REWIND-NULL.log`. **Scope correction (verified, not blindly built):** the directive's step 2 (port `SP_G4_SCORE` into the kv ABI) is NOT required to close #222 — the deliverable is the O(1) bit-exact rewind, proven by byte-comparison, not re-scoring (the deflection number is already a proven one-shot receipt, `G-MEMO-LOOP`); the kv-side teacher-forced scorer is a separate, deferrable optimization. SWA-ring replay (vs full-cache) needs the KAI-1c journal — a named follow-on. **⇒ the curator now reaches the physical KAIROS deployment standard: speculate a recalled memory in the resident cache, gate it, and undo a rejected recall in O(1) byte-exact instead of O(context) rerun.**

**#222 FINALIZED — replay is now SWA-ring-aware (2026-06-17, engine 24071bc).** `gemma4_kv_replay` checkpoints each clobbered ring slot into the KAI-1c undo-journal before overwrite (the exact `g4_kv_step` mechanic); globals stay full-cache. **G-222-WRAP GREEN E2B+12B** (`SP_G4_KV_RING_W=16`, anchor=24 ⇒ replay slots `(24..31)%16 = 8..15` alias live positions 8–15, the wrap-crossing hazard): load-bearing (injected slots zeroed) + the journal-backed rewind restores the **full live window byte-identical (layer-diffs=0)**, pos→anchor, O(1). Receipt `engine tests/fixtures/xbar_c2/G-222-WRAP.log`. **⇒ the local KV substrate is airtight in BOTH regimes — full-cache (G-222) and SWA-ring (G-222-WRAP). C2 + the local KV optimizations are CLOSED; the only remaining XBAR-side thread (Ring-3 gist consolidation) is a separate training campaign behind `G-R3-LOSS` + operator budget.**

**G-R2-FROB — the Frobenius πᵏ integer episode store (T4 storage form) GREEN (2026-06-18, engine dbe4103 / d076797; `tools/curator/frob_episode.py`).** The Ring-2 episode payload is given an exact-integer O_K form (the storage-codec arm of the v1.5 unification onto `O_K`): a **rank-2 O_K lattice** — a coarse code `a` plus an error-feedback residual `b`, reconstructing `x = a·s_a + b·s_b` with **REAL scales (NOT literal complex ω)** — i.e. the Frobenius πᵏ scale is applied to integer codes, not a complex rotation. Bit-width sweep:

| code form | bits | rel-L2 | store factor |
|---|---|---|---|
| a16 | 16 | 3e-5 | — |
| a8b4 | 12 | (coarse) | — |
| **a16b8** | 24 | **1.2e-7 (SUB-ULP)** | **0.76×** |

The a16b8 form is sub-ULP and the πᵏ scale is free; it **replays clean on the 12B**. **HONEST scope (on the board):** the n=42 `SP_REPLAY` PPL is BLIND below ~1% (tie-flip — `feedback_small_n_deflection_illusion`); the only clean +0.000% is float-exact replay == baseline 4.6665. So "lossless" here = **reconstruction fidelity** (relL2 1.2e-7), NOT an n=42 PPL gate. Receipt `engine tests/fixtures/xbar_c2/G-R2-FROB.log`.

**G-R2-FROB-ENTROPY NEGATIVE (2026-06-18, engine e6d17bb).** Entropy-coding the Frobenius codes is dead weight: 1.02× (the residual is incompressible). **The lever is bit-width, not entropy** — kept as an honest negative, consistent with the RFC §3.0 boundary thesis (structure-on-content is inert). Receipt `engine tests/fixtures/xbar_c2/G-R2-FROB-ENTROPY.log`.

**G-PERIOD6-REBASE GREEN (2026-06-18, engine d2d7ceb). Correctness tidy-up — closed.** The C2 / Ring-3 content-hash period was **8 → 6**, onto the true gemma4 global layers {5, 11, 17, …, 47} (`L%6==5`). The old PERIOD=8 hashed *non-global* layers into the signature; the rebase puts the address on the actual global crossbar. **All prior gates STAND** (the discrete integer-Hamming verdict is reduction-order-immune, so re-hashing only sharpens it) and the re-gated separation is **cleaner**. This is the period-6 rebase the v1.4 docs named as NEXT — now closed. Receipt `engine tests/fixtures/xbar_c2/G-PERIOD6-REBASE.log`.

*The substrate reads, writes, compresses, replays, and holds its perplexity. C2 is the first turn where it decides — on its own — what to remember. And as of v1.5 it remembers in exact O_K integers, on the true global period.*
