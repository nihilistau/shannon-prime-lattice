# "Lost stuff" triage — Friedman Stack + DHT/chain/tokenomics (do NOT treat as lost)

When the big "Friedman Stack" (Papers III/IV: KSTE / sieve / Dickson / ultraproduct / choice operator) or the "DHT / token-economy / blockchain / Fibonacci-prime address space" design comes back as "lost work we should resurrect" — it is NOT lost. It triages into four buckets (grounded 2026-07-01 via two repo sweeps + PPT-LAT-STATE + memory-okf):

## Bucket A — PROVEN and in-tree (kept, not lost)
- **KSTE encoder** itself: implemented + gated (E_CPU_6 / math-core; PPT-LAT-STATE §2, ~21/21). It is a signature encoder.
- **Dickson dominance ⪯_d + Tier-0/Tier-1 signatures**: real exact arithmetic (PPT-LAT-Theory §5).
- **Garner recombination + M.4 PoUW receipt-ledger + mesh canonical Garner order**: [PROVEN-per-record] (STATE §3 line 89; CLOSURE-MESH-CANONICAL-ORDER.md). This "two devices holding the same receipt set in canonical order" IS the honest kernel of the whole blockchain section — an append-only AUDIT ledger, already cited as SP-SWARM's L2 trust model. Tokens/consensus/AMM are NOT part of it.

## Bucket B — RESOLVED honest-negatives (killed on purpose; reviving = the rebuild sin)
- **KSTE as a recall ROUTER**: FALSIFIED (memory 59af46dc, core commit 186aadb) — signature-only, can't generate; replaced by ±1 Rademacher projection router (C2, gated GREEN).
- **Fibonacci-φ as a recall router**: measured-negative (φ is for eviction COVERAGE, not peaked-mass recall). Rademacher replaced it.
- **CRT multi-device / expert-sharding**: RESOLVED-negative (memory dff07b41; SESSION-PERF-SYNTHESIS-2026-06-23; STATE 121/300) — CRT shards numbers not experts, per-device mem saved = 0.

## Bucket C — PAPER-ONLY, never built, superseded (Papers III/IV are ARCHIVED in Position_Is_Arithmetic/Archived/, superseded by PPT-LAT-Theory.md)
- **Ultraproduct attention** (ultrafilter/Łoś): never implemented; non-differentiable; not in served system.
- **Choice operator F / Extended-Domain Reduction**: never implemented; displaced by the learned W_c recall head (empirically superior).

## Bucket D — the ONE genuinely-parked real thing (parked for a good, operator-endorsed reason)
- **Friedman sieve as a KV-eviction/dedup policy**: real code (core/sieve), with STRONG numbers CLAIMED in archived Paper III §11.6 (AUC 0.500 strict→ 17× ratio + 720× speedup + 93.86% eviction + cache plateau ~307/512 under Dickson). BUT: the T2.x / T4_RES_PROBE receipt LOGS were NOT found on disk — the numbers are paper-claimed, not re-verifiable gate logs. AND it is the KV-EVICTION rabbit hole the operator explicitly EXITED this session ("stepping entirely away from the OKV eviction rabbit hole"); STATE re-ranked KV-eviction as NOT the load-bearing differentiator (Ring-2 effective-context is). → Do NOT re-enter unless KV-eviction is deliberately reprioritized, and only after re-gating the paper-claimed numbers.

## DHT / token-economy / blockchain
- **NOT-FOUND in code, and the paper itself says "this section is scaffolding, not specification."** It is UNBUILT design, not lost work. The honest, sound 10% (private mesh + content-addressing + provenance) already lives in `papers/PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md` (SP-SWARM), and the useful accounting kernel is the M.4 receipt-ledger (Bucket A). Tokens/AMM/validators/slashing/Golden-Ratio-consensus/PoUW-as-crypto-economy = speculative, on top of a single-node research system.

**Bottom line: the project already CONVERGED. Reusable kernels survive (M.4 ledger; C2/Rademacher addressing). Everything else is proven-kept, killed-on-purpose, superseded, or in an abandoned lane. "Resurrect it all" is not the move.**
