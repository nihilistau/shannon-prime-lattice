#!/usr/bin/env python3
"""G-MEM-LIFECYCLE (Python half) — A1 trust x freshness state machine in okf_mem.py.

The full A1 gate (supersede marks-not-drops + SP_MEM_ROLLBACK + null-floor) is the daemon
receipt; this half proves the MEM-OKF curated-store state machine:
 * capture defaults mem_verified=unverified, mem_lifecycle=active;
 * verified='verified' cannot be set at capture (rejected);
 * legal_transition enforces the audit-preserving state machine;
 * verify() flags a superseded/contradicted row missing its audit link.

Self-contained, no deps. Repro: python tools/tests/test_mem_lifecycle_py.py
"""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import okf_mem as M

fails = []
def check(n, c, d=""):
    if not c: fails.append((n, d))

class A: pass
def mkargs(root, **kw):
    a = A()
    d = dict(root=root, kind="agent", keys="alpha,beta", summary="a test fact for lifecycle",
             title=None, detail=None, detail_file=None, full_file=None, blob_ref=None, addr=None,
             status="ACTIVE", gate="none", commit=None, repro=None, mem_class=None, delivery=None,
             authority=None, retrieval_key=None, decline_when=None, decline_message=None,
             confidence=None, verified=None, lifecycle=None, supersedes=None, superseded_by=None,
             contradicted_by=None, revises=None)
    d.update(kw)
    for k, v in d.items(): setattr(a, k, v)
    return a

root = tempfile.mkdtemp(prefix="okflife_")
try:
    body = "The recall selector reads the layer-5 global query and cosine-matches episode keys.\n"
    bf = os.path.join(root, "_body.txt"); M.write(bf, body)

    # (1) default capture -> unverified / active
    rc = M.cmd_add(mkargs(root, full_file=bf))
    check("add-rc0", rc == 0, rc)
    addr = M.addr_of(body)
    fm, _ = M.parse_fm(M.read(os.path.join(root, M.FULL_DIR, addr + ".md")))
    check("default-unverified", fm.get("mem_verified") == "unverified", fm.get("mem_verified"))
    check("default-active", fm.get("mem_lifecycle") == "active", fm.get("mem_lifecycle"))

    # (2) cannot set verified at capture
    bf2 = os.path.join(root, "_body2.txt"); M.write(bf2, "Another distinct fact about tau thresholds.\n")
    rc = M.cmd_add(mkargs(root, full_file=bf2, verified="verified"))
    check("verified-at-capture-rejected", rc == 2, rc)

    # (3) transition state machine
    check("t-unverified->verified", M.legal_transition("unverified", "verified") is True)
    check("t-verified->rolled_back", M.legal_transition("verified", "rolled_back") is True)
    check("t-contradicted->verified-ILLEGAL", M.legal_transition("contradicted", "verified") is False)
    check("t-rolled_back->verified-ILLEGAL", M.legal_transition("rolled_back", "verified") is False)

    # (4a) clean store verifies GREEN
    rc = M.cmd_verify(mkargs(root))
    check("clean-verify-green", rc == 0, rc)

    # (4b) a superseded+contradicted row missing its audit links -> RED
    bad = "badf0000badf0000"
    M.write(os.path.join(root, M.FULL_DIR, bad + ".md"),
            M.fm_block({"type": "memory", "mem_addr": bad, "mem_kind": "episode",
                        "mem_verified": "contradicted", "mem_lifecycle": "superseded"}) + "\nblob\n")
    rc = M.cmd_verify(mkargs(root))
    check("tainted-row-rejected", rc == 1, rc)

    print("=== G-MEM-LIFECYCLE (python half) ===")
    for f in fails: print("  FAIL:", f[0], "->", f[1])
    print("---- %d checks | %d failed | VERDICT: %s ----" % (11, len(fails), "GREEN" if not fails else "RED"))
    sys.exit(0 if not fails else 1)
finally:
    shutil.rmtree(root, ignore_errors=True)
