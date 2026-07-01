# Friedman-sieve application numbers — re-derived fresh (split verdict)

The archived Paper III §11.6 sieve numbers (720× speedup / 93.86% eviction / ~307 plateau / 17× discrimination) were PROVEN in the anti-contaminate-gated OLD shannon-prime repos (must not be copied). Re-derived fresh against the CURRENT in-tree core (harness `shannon-prime-system/tests/sieve_measure.c`, receipt `tests/fixtures/G-SIEVE-MEASURE-2026-07-01.log`, @ 15698b0):

- **Termination = CONFIRMED** (Dickson wqo: frontier saturates) — but plateau = **2 slots**, not ~307.
- **Speed = CONFIRMED + exceeded**: raw tier0+tier1 dominance **16.77 ns/pair**; per-candidate sieve p99 **0.063 µs**; 50 µs wall-time gate CLEAR by ~800×.
- **Discrimination = HONEST-NEGATIVE on the current v1 encoder**: intra/inter "would-dedup" ratio only **1.0–1.3×** (paper claimed 17×). The in-tree KSTE v1 (fixed 13-node T_{60,3} shape, 6 order-statistic labels, componentwise dominance) is magnitude-dominated → most pairs comparable (inter-dedup ~0.73–0.91) → weak semantic separation, and it over-collapses i.i.d. input to a 2-element antichain.

**Why:** the current core is an explicitly-labeled "Phase 1" simplified encoder. The paper's rich discrimination/plateau belong to the fuller 60-node magnitude-as-depth encoder that lives ONLY in the anti-contaminate-gated old repos. To get the paper's numbers in the new tree, the fuller encoder must be RE-DERIVED natively (a real build task) — NOT copied. Do not claim the 17×/307 numbers for the in-tree core; they are not reproduced there.
