#!/usr/bin/env python3
"""G-LOOP-STABLE — gate for B3 (rho<1 loop-stability monitor).

Pre-registered PASS (CONTRACT §3, B3): a bounded/converging norm sequence -> STABLE;
a deliberately exploding sequence -> DIVERGENT (flagged, with the Parcae fix); a flat
(rho~1) sequence -> STABLE (borderline non-expansive). Deterministic.

Repro: python tools/tests/test_loop_stability.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import loop_stability as L

fails = []
def check(n, c, d=""):
    if not c: fails.append((n, d))

# converging (a well-behaved Coconut thought loop): norms settle
r = L.analyze([1.00, 0.95, 0.91, 0.89, 0.88, 0.88])
check("converging-STABLE", r["verdict"] == "STABLE", r)
check("converging-rho<1", r["rho_hat"] <= 1.0, r)

# flat (rho ~ 1): non-expansive -> STABLE
r = L.analyze([1.0, 1.0, 1.0, 1.0, 1.0])
check("flat-STABLE", r["verdict"] == "STABLE", r)

# exploding (Parcae divergence, rho>1): must be flagged + carry the fix
r = L.analyze([1.0, 1.3, 1.7, 2.3, 3.1, 4.2])
check("exploding-DIVERGENT", r["verdict"] == "DIVERGENT", r)
check("exploding-rho>1", r["rho_hat"] > 1.0, r)
check("exploding-has-fix", bool(r["fix"]) and "Prelude-Norm" in r["fix"], r)

# single spike above hard ratio even if it later settles -> DIVERGENT (caught by max_ratio)
r = L.analyze([1.0, 1.0, 2.2, 1.1, 1.0])
check("spike-DIVERGENT", r["verdict"] == "DIVERGENT", r)

# determinism
check("determinism", L.analyze([1.0, 0.9, 0.8]) == L.analyze([1.0, 0.9, 0.8]))

print("=== G-LOOP-STABLE ===")
for seq in ([1.00, 0.95, 0.91, 0.89, 0.88], [1.0, 1.3, 1.7, 2.3, 3.1, 4.2]):
    r = L.analyze(seq)
    print("  %-28s -> %-9s rho_hat=%.3f max_ratio=%.3f" % (str(seq[:3]) + "...", r["verdict"], r["rho_hat"], r["max_ratio"]))
for f in fails: print("  FAIL:", f[0], "->", f[1])
print("---- %d checks | %d failed | VERDICT: %s ----" % (8, len(fails), "GREEN" if not fails else "RED"))
sys.exit(0 if not fails else 1)
