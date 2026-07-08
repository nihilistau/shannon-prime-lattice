#!/usr/bin/env python3
"""mem_consolidate.py — A3: deterministic MDL/AIC consolidation gate.

Complements (does NOT replace) the 12B DECIDE/MERGE model-call in the daemon
(routes.rs). A cheap, zero-inference first pass decides the common cases and
reserves the model-call for the genuinely ambiguous ones — the same "deterministic
gate beats the model-call" shape as the Jaccard judge that retired the 26B.

Description-length proxy: L(x) = |content tokens(x)|. Merging A,B counts shared
tokens once, so the DL *saved* by merging is |toks(A) ∩ toks(B)| − overhead(λ).

Routing for a NEW fact N vs its best existing candidate C:
  * near-identical (one subsumes the other)      -> SUPERSEDE-OR-DUP  (model / A4 dedup)
  * enough shared tokens that merging saves DL    -> MERGE            (deterministic)
  * some overlap but inconclusive                 -> MODEL            (fall through to 12B)
  * little overlap                                -> KEEP-BOTH

Safety invariant (pre-registered, G-MEM-MDL): a proposed MERGE text that drops any
key-term present in A∪B is ALWAYS rejected (0 fact-loss). Source: arXiv 2606.01444
(MDL/AIC accept gate + audit contract) and OpenSelfRevise gates.py.

Reference logic here (Python); the Rust port into routes.rs Stage-2 rides the
existing DECIDE/MERGE seam (build-wave item, alongside A1/A2). No third-party deps.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import okf_mem as M


def keyterms(text):
    """Key-terms = the content token set (frontmatter-agnostic; caller passes body text)."""
    return M.toks(text)


def mdl_merge_gain(a, b, lam=3):
    """Description-length saved by merging A and B (shared tokens counted once) minus overhead."""
    ta, tb = M.toks(a), M.toks(b)
    return len(ta & tb) - lam


def merge_is_lossless(a, b, merged):
    """True iff the proposed merged text retains EVERY key-term of A and of B (0 fact-loss)."""
    need = M.toks(a) | M.toks(b)
    return need.issubset(M.toks(merged))


def consolidate_decision(a, b, merged_proposal=None, theta=1, lam=3, subsume_cov=0.9):
    """Deterministic route for (existing C=a, new N=b).
    Returns dict: {route, gain, cov_min, lossless}.
      route ∈ {SUPERSEDE-OR-DUP, MERGE, REJECT-LOSSY-MERGE, MODEL, KEEP-BOTH}."""
    ta, tb = M.toks(a), M.toks(b)
    shared = len(ta & tb)
    cov_min = shared / min(len(ta), len(tb)) if (ta and tb) else 0.0
    gain = shared - lam
    if cov_min >= subsume_cov:
        route, lossless = "SUPERSEDE-OR-DUP", None            # one subsumes the other -> model/supersede/dedup
    elif gain > theta:
        if merged_proposal is not None:
            lossless = merge_is_lossless(a, b, merged_proposal)
            route = "MERGE" if lossless else "REJECT-LOSSY-MERGE"
        else:
            route, lossless = "MERGE", True                   # deterministic union merge is lossless by construction
    elif gain <= 0:
        route, lossless = "KEEP-BOTH", None
    else:
        route, lossless = "MODEL", None                       # inconclusive -> 12B DECIDE/MERGE
    return {"route": route, "gain": gain, "cov_min": round(cov_min, 3), "lossless": lossless}


if __name__ == "__main__":
    # tiny CLI: two files (existing, new) [+ optional proposed merge]
    if len(sys.argv) < 3:
        print("usage: mem_consolidate.py <existing.txt> <new.txt> [merged.txt]", file=sys.stderr)
        sys.exit(2)
    a = M.read(sys.argv[1]); b = M.read(sys.argv[2])
    m = M.read(sys.argv[3]) if len(sys.argv) > 3 else None
    print(consolidate_decision(a, b, m))
