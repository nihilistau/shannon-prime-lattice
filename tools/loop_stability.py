#!/usr/bin/env python3
"""loop_stability.py — B3: the rho<1 stability monitor for any iterative latent loop.

Guard rail for B1 (Coconut continuous-thought) and B6 (looped Gemma). Parcae (arXiv
2604.12946) frames a weight-shared / recurrent loop as an LTI system over the residual
stream: it is stable iff the effective update's spectral radius rho(A) < 1. We cannot cheaply
get rho(A) at inference, so we monitor the OBSERVABLE proxy: the sequence of hidden-state
L2 norms ||h_t|| across loop iterations. A non-expansive loop keeps successive ratios
||h_{t+1}||/||h_t|| at or below 1 and never blows the norm up; a divergent loop shows a
sustained ratio > 1 (Parcae Fig. 3: divergent runs learn rho>=1).

rho_hat = geometric mean of consecutive norm ratios (the average per-step gain). Verdict:
  STABLE    — rho_hat <= 1+eps AND peak norm not blown up (Parcae: residual bounded).
  DIVERGENT — sustained expansion; recommend the Parcae fixes (Prelude-Norm on the injected
              signal; negative-diagonal state parameterization A:=Diag(-exp(.)) to force rho<1).

Offline analyzer over dumped ||h_t|| (the daemon will emit these once B1's loop exists). No deps.
Repro of the gate: python tools/tests/test_loop_stability.py
"""
import math


def analyze(norms, eps=0.02, hard_ratio=1.5, blowup=10.0):
    """norms: [||h_0||, ||h_1||, ..., ||h_T||] across loop iterations. Returns a verdict dict."""
    pos = [n for n in norms if n > 0]
    if len(pos) < 2:
        return {"verdict": "UNKNOWN", "reason": "need >=2 positive norms", "n": len(norms)}
    ratios = [norms[i + 1] / norms[i] for i in range(len(norms) - 1) if norms[i] > 0]
    rho_hat = math.exp(sum(math.log(r) for r in ratios) / len(ratios))  # geometric mean gain/step
    max_ratio = max(ratios)
    peak = max(norms)
    blew_up = peak > norms[0] * blowup
    expansive = rho_hat > 1 + eps or max_ratio > hard_ratio
    divergent = blew_up or expansive
    return {"verdict": "DIVERGENT" if divergent else "STABLE",
            "rho_hat": round(rho_hat, 4), "max_ratio": round(max_ratio, 4),
            "peak": round(peak, 4), "n0": round(norms[0], 4), "n": len(norms),
            "fix": None if not divergent else
            "Parcae: add Prelude-Norm (LayerNorm on the injected signal e) and/or parameterize "
            "the state matrix A := Diag(-exp(log_A)) with learned delta (ZOH) to force rho(A)<1."}


if __name__ == "__main__":
    import json, sys
    # read whitespace/CSV/JSON list of norms from stdin or a file arg
    raw = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    raw = raw.strip()
    nums = json.loads(raw) if raw.startswith("[") else [float(x) for x in raw.replace(",", " ").split()]
    print(json.dumps(analyze(nums), indent=2))
