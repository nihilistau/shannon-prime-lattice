#!/usr/bin/env python3
"""G-OKF-ASK (block half) — gate for A5 upsert-block (co-edit markers).

PASS (CONTRACT §3, A5): upsert-block edits ONLY the region between SP_GENERATED:<key>
markers; human text outside is preserved byte-for-byte; re-running with the same content
is idempotent; a second key does not disturb the first.

Self-contained, no deps. Repro: python tools/tests/test_okf_upsert.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import okf_mem as M

fails = []
def check(n, c, d=""):
    if not c: fails.append((n, d))

human = "# My hand-written doc\n\nImportant human note. DO NOT TOUCH.\n"

t1 = M.upsert_block(human, "summary", "Generated summary v1.")
check("human-preserved-1", t1.startswith(human), repr(t1[:60]))
s, e = M._markers("summary")
check("markers-present", s in t1 and e in t1)
check("content-v1", "Generated summary v1." in t1)

t2 = M.upsert_block(t1, "summary", "Generated summary v2 UPDATED.")
check("human-preserved-2", t2.startswith(human))
check("old-content-gone", "v1." not in t2)
check("new-content", "v2 UPDATED" in t2)
check("single-block", t2.count(s) == 1 and t2.count(e) == 1, "marker count")

t3 = M.upsert_block(t2, "summary", "Generated summary v2 UPDATED.")
check("idempotent", t3 == t2)

t4 = M.upsert_block(t2, "notes", "Some agent notes.")
s2, _ = M._markers("notes")
check("second-key-independent", "v2 UPDATED" in t4 and "Some agent notes" in t4)
check("two-blocks", t4.count("SP_GENERATED") == 4)  # 2 keys x (START+END)
check("human-still-there", t4.startswith(human))

print("=== G-OKF-ASK (upsert-block half) ===")
print(t4)
for f in fails: print("  FAIL:", f[0], "->", f[1])
print("---- %d checks | %d failed | VERDICT: %s ----" % (10, len(fails), "GREEN" if not fails else "RED"))
sys.exit(0 if not fails else 1)
