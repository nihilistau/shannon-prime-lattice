#!/usr/bin/env python3
"""G-MEM-MDL — gate for A3 (deterministic MDL consolidation gate).

Pre-registered PASS criteria (CONTRACT-EXTERNAL-ADOPTION.md §3, A3):
 * correct routing on labelled {merge / keep-both / supersede-or-dup / model} cases;
 * SAFETY INVARIANT: a proposed MERGE that drops any key-term present in A∪B is ALWAYS
   rejected (0 fact-loss);
 * report the model-call reduction (fraction resolved deterministically, no 12B call);
 * determinism.

Self-contained, no deps. Repro: python tools/tests/test_mem_mdl.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mem_consolidate as MC

fails = []


def check(name, cond, detail=""):
    if not cond:
        fails.append((name, detail))


# --- MERGE: complementary facts, same subject, moderate-high overlap (not subsuming) ---
C_m = "Alice joined Acme in the Sydney office working on the backend payments platform team."
N_m = "Alice at Acme now leads the backend payments platform team in the Sydney office."
merged_lossless = C_m + " " + N_m                      # concatenation -> covers every key-term
merged_lossy = "Alice at Acme leads the Sydney backend platform team."   # drops 'payments','now','joined','working'

r = MC.consolidate_decision(C_m, N_m, merged_lossless)
check("merge/lossless-route", r["route"] == "MERGE", r)
check("merge/lossless-flag", r["lossless"] is True, r)

r = MC.consolidate_decision(C_m, N_m, merged_lossy)
check("merge/lossy-rejected", r["route"] == "REJECT-LOSSY-MERGE" and r["lossless"] is False, r)

# explicit 0-fact-loss invariant on the primitive
check("invariant/lossy-not-lossless", MC.merge_is_lossless(C_m, N_m, merged_lossy) is False)
check("invariant/full-is-lossless", MC.merge_is_lossless(C_m, N_m, merged_lossless) is True)

# --- KEEP-BOTH: unrelated facts, ~no overlap ---
C_k = "The capital of France is Paris."
N_k = "Photosynthesis converts sunlight into chemical energy inside chloroplasts."
r = MC.consolidate_decision(C_k, N_k)
check("keep-both/route", r["route"] == "KEEP-BOTH", r)

# --- SUPERSEDE-OR-DUP: new fact subsumes the old one entirely ---
C_s = "Alice is a backend engineer."
N_s = "Alice is a backend engineer at Acme in Sydney working on payments."
r = MC.consolidate_decision(C_s, N_s)
check("subsume/route", r["route"] == "SUPERSEDE-OR-DUP", r)

# --- MODEL: inconclusive overlap (defer to 12B DECIDE/MERGE) ---
C_x = "The report covers revenue growth margin and churn."
N_x = "The report covers revenue growth for the new region."
r = MC.consolidate_decision(C_x, N_x)
check("model/route", r["route"] == "MODEL", r)

# --- determinism ---
check("determinism", MC.consolidate_decision(C_m, N_m, merged_lossless)
      == MC.consolidate_decision(C_m, N_m, merged_lossless))

# --- model-call reduction: how many labelled cases resolved without a 12B call ---
labelled = [("merge", C_m, N_m, merged_lossless), ("keep", C_k, N_k, None),
            ("subsume", C_s, N_s, None), ("model", C_x, N_x, None)]
DET = {"MERGE", "KEEP-BOTH", "REJECT-LOSSY-MERGE"}
det = sum(1 for _, a, b, m in labelled if MC.consolidate_decision(a, b, m)["route"] in DET)

print("=== G-MEM-MDL ===")
for nm, a, b, m in labelled:
    r = MC.consolidate_decision(a, b, m)
    print("  %-8s -> %-18s gain=%d cov_min=%.2f lossless=%s"
          % (nm, r["route"], r["gain"], r["cov_min"], r["lossless"]))
print("  model-call reduction: %d/%d resolved deterministically (no 12B call)" % (det, len(labelled)))
for f in fails:
    print("  FAIL:", f[0], "->", f[1])
verdict = "GREEN" if not fails else "RED"
print("---- %d checks | %d failed | VERDICT: %s ----" % (9, len(fails), verdict))
sys.exit(0 if not fails else 1)
