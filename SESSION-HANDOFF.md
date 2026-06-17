# SESSION-HANDOFF.md — where things stand

**Updated:** 2026-06-17 (**C2 Memo curator CLOSED** Steps 1–3.1 + #222 + G-XBAR-ORGANISM step 1 GREEN; **Ring-3 Path A CLOSED end-to-end** R3.1→R3.4 GREEN; **XBAR P3 CLOSED end-to-end** P3.0→P3.4; **GNA EAR CLOSED on physical silicon**; **nothing baking**; **pivoted back to XBAR**).

---

## 0. State in one paragraph

The whole XBAR memory stack is proven end-to-end on the 12B within a 12 GB footprint. **Ring-2 verbatim** (C2 curator + #222): curator indexes (registry + 256-bit discrete hash), addresses (integer Hamming TAU_BITS=168), is inert when off (G-MEMO-NULL bit-identical), and on metal promotes matched recall at +0.000% deflection + discards corrupted recall at +40106.6% (G-MEMO-LOOP). #222 ports SP_REPLAY into the persistent kv ABI with O(1) bit-exact rewind in both full-cache (G-222) and SWA-ring (G-222-WRAP) regimes. **Ring-3 gist** (Path A, parameter-free): VSA/HRR superposition seeded from C2 256-bit sigs; R3.1 BIND (recall@1=1.0 to N=32), R3.2 LOSS (hit +0.000%, miss +8.04% gate-caught), R3.3 DUALROUTE (clean hit + decoy scan + null parity), R3.4 NIGHTSHIFT (40 episodes → 349.8 MB KV demoted to Optane → 16.3 KB Ring-3 index; D=128 gate-driven seal proves seal is the math). **EAR→Ring-2 bridge** (G-XBAR-ORGANISM step 1): ep_audio [48,114,512] uniform-512, signature separates self 211/256 margin +79, SP_REPLAY loads+injects clean (+1989% is foreign-by-design, ~0% is matched-context only). **Substrate basis** (P3 closed, GNA closed, KAIROS closed) unchanged.

**No runs in flight. No pods. No schtasks. RunPod balance: $0.**

---
## 1. IN FLIGHT right now (nothing; all clean)

- No active GPU runs. No pods. No schtasks. GPU clocks at default.
Previous closed items (all on record, nothing in flight):
- ✓ **C2 Memo curator CLOSED** Steps 1–3.1 + #222 + G-XBAR-ORGANISM step 1 GREEN (2026-06-17). Contracts: `CONTRACT-XBAR-C2-memo-curator-loop.md`.
- ✓ **Ring-3 Path A CLOSED** R3.1→R3.4 GREEN, parameter-free (2026-06-17). Contract: `CONTRACT-XBAR-R3-consolidation.md`.
- ✓ **XBAR P3 CLOSED** P3.0→P3.4 GREEN (2026-06-17). Contract: `CONTRACT-XBAR-P3-ring-on-exec.md`.
- ✓ **GNA EAR CLOSED** on physical silicon (2026-06-17). Contract: `CONTRACT-KAIROS-K0-K1.md §7.4–7.6`.
- ✓ **G-KAIROS-1 6h soak GREEN** (2026-06-16); KAI-1/1b/1c CLOSED; KAI-2 CLOSED-BOUNDED; KAI-3 CLOSED GREEN. Contract: `CONTRACT-KAIROS-K0-K1.md §5.5–5.9, §6.6, §7.3`.
- ✓ **Phase C alloc-shrink + C-c NIAH CLOSED** (2026-06-14). §P3.2-b-2b LSH 8× +0.47% CLOSED (2026-06-13). Contracts: `CONTRACT-XBAR-P3-ring-on-exec.md`.

## 2. The decision queue (locked order — do not reshuffle without the operator)

1. **▶▶ Period-6 rebase (2026-06-17).** C2/Ring-3 sig pipeline uses `PERIOD=8` (L%8==7) as the content-hash layer subset; the 12B's true SWA period is **6** (L%6==5). All prior C2/R3 gates STAND (separation is robust). This is a correctness tidy-up: update `build_registry.py`, `discrete_resolve.py`, `g_r3_bind.py` and any other tool that selects the content-hash subset to use L%6==5. Re-run the offline gates to confirm separation holds. No new contracts needed — record the rebase in the existing C2/R3 contracts as a correctness note. No budget.

2. **▶ Full G-XBAR-ORGANISM loop (2026-06-17+).** Step 1 (EAR→Ring-2 write seam) is GREEN. The full loop: drive a raw audio cue through the live curator → Ring-3 unbind shortlist → #222 verify scan (inject each candidate via `gemma4_kv_replay`, score via `SP_G4_SCORE`, ACCEPT +0% / REJECT +8% → `gemma4_kv_rewind`) → autonomously land ep_audio in the resident cache. Gate: clean hit + null parity (no audio episode = baseline byte-exact). Pre-register the deflection bound before code (audio context ≠ wiki context so the cue threshold must be recalibrated from the organism data, not transplanted from G-MEMO-LOOP). Contract: extend `CONTRACT-XBAR-C2-memo-curator-loop.md` §organism or open a new `CONTRACT-XBAR-ORGANISM.md`. No budget.

3. **Hygiene queue (non-blocking; pick up when convenient).**
   - #220 cudaEvent journal-tax (exact per-tick overhead; wall-clock floor on 2060 makes it noise otherwise).
   - `gemma4_kv_decode` first-token boundary reconcile (the #222 OPEN from 2026-06-14; kv-path seam alignment with the one-shot `SP_XBAR_EMB` path).
   - Compact-slab globals wrap-rewind (slab + SWA-ring journal = the joint regime; not exercised yet).
   - P3.4 larger-N multi-chunk hardening run (the named pre-public lever; deterministic, not noise-flippable, just a wider corpus run).
   - R3.x Z_q/NTT engine port of host-numpy VSA bind/unbind (deployment, exact integer; deferred from Ring-3 Path A close).

## 3. Open threads (persistent small items)

- HF model bucket `KnackAU/sp-diffusion-stage` — staged for diffusion/spec-decode prototypes; no active run.
- WSL gcloud unauthed (fine; Windows is canonical).
- HF-token path: `_xbar/p2b` scripts read `archive/notes_and_stuff/claude-hf-token.txt`; `creds/claude-hf-token.txt` is the authoritative path — keep in sync or repoint scripts.

## 4. Standing watch procedure

No pods, no RunPod balance to check. Before any new cloud run: `check_pods.py` (any pods?) → verify `papers/RUNBOOK-cloud-compute.md` pattern → per-unit upload in the loop → verify-then-terminate. ⬢
