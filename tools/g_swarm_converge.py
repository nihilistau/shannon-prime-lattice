"""g_swarm_converge.py — GATE G-SWARM-REPLICATE-CONVERGE (SP-SWARM L1+L2 core).

Proves, on ONE machine with two store dirs (zero crypto, zero network), that the MEM-OKF
content-addressed have/want replication is CORRECT:
  1. L1 integrity: every object in the REAL memory-okf store re-hashes to its address.
  2. Divergence: two "nodes" seeded with disjoint+overlapping splits of the store.
  3. L2 convergence: after bidirectional sync both nodes hold the UNION, byte-identical.
  4. Integrity-on-arrival: every pulled object re-hashes to its address.
  5. Idempotence: a second sync pulls 0 (no churn).
  6. Negative control: a TAMPERED object (flipped byte) is REJECTED on pull (hash-mismatch),
     never written — so corruption/forgery cannot propagate.
  7. No duplicate LUT rows after convergence.

Usage: python g_swarm_converge.py <memory-okf-root>
"""
import os, sys, shutil, filecmp
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import okf_mem, swarm_sync as sw

def seed(dst, src_root, addrs):
    okf_mem.ensure_root(dst)
    rows = {r[0]: r for r in okf_mem.lut_rows(src_root) if r}
    keep = []
    for a in addrs:
        sf = os.path.join(src_root, sw.FULL, a + ".md")
        if not os.path.exists(sf):
            continue
        okf_mem.write(os.path.join(dst, sw.FULL, a + ".md"), okf_mem.read(sf))
        ss = os.path.join(src_root, sw.SUM, a + ".md")
        if os.path.exists(ss):
            okf_mem.write(os.path.join(dst, sw.SUM, a + ".md"), okf_mem.read(ss))
        if a in rows:
            keep.append(rows[a])
    okf_mem.write_lut(dst, keep)

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "memory-okf"
    tmp = os.path.join(_HERE, "_tmp_swarm")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    A, B = os.path.join(tmp, "node_a"), os.path.join(tmp, "node_b")
    fails = []

    # (1) L1 integrity of the real store
    m = sw.manifest(src)
    content = sum(1 for c, ok in m.values() if c == "content")
    c2 = sum(1 for c, ok in m.values() if c == "c2")
    bad = sorted(a for a, (c, ok) in m.items() if not ok)
    print(f"[1] real store: {len(m)} objects | content-addressed={content} c2-episode={c2} invalid={len(bad)}")
    if bad:
        fails.append(f"real-store invalid {len(bad)}: {bad[:5]}")
    allad = sorted(m.keys())
    if len(allad) < 6:
        print("RED: need >=6 objects to split"); sys.exit(1)

    # (2) divergent split: even-index -> A, odd-index -> B, plus a shared overlap of 3
    overlap = allad[:3]
    A_only = allad[3::2]
    B_only = allad[4::2]
    seed(A, src, overlap + A_only)
    seed(B, src, overlap + B_only)
    ha, hb = sw.have(A), sw.have(B)
    union = ha | hb
    print(f"[2] node_a={len(ha)} node_b={len(hb)} overlap={len(ha & hb)} union={len(union)} (divergent={ha != hb})")
    if ha == hb:
        fails.append("nodes not divergent")

    # (3)+(4) bidirectional sync + verify-on-arrival
    rep = sw.sync(A, B)
    print(f"[3] sync: a_pulled={rep['a_pulled']} b_pulled={rep['b_pulled']} "
          f"a_after={rep['a_after']} b_after={rep['b_after']} converged={rep['converged']} "
          f"rejected(a={len(rep['a_rejected'])},b={len(rep['b_rejected'])})")
    if not rep["converged"]:
        fails.append("did not converge")
    if sw.have(A) != union or sw.have(B) != union:
        fails.append("post-sync != union")
    # every object re-hashes on both nodes
    ia = [a for a, (c, ok) in sw.manifest(A).items() if not ok]
    ib = [a for a, (c, ok) in sw.manifest(B).items() if not ok]
    print(f"[4] post-sync integrity: node_a fail={len(ia)} node_b fail={len(ib)}")
    if ia or ib:
        fails.append("post-sync integrity")
    # byte-identical full/ objects across the two converged nodes
    diffs = [a for a in union
             if not filecmp.cmp(os.path.join(A, sw.FULL, a + ".md"),
                                os.path.join(B, sw.FULL, a + ".md"), shallow=False)]
    print(f"[4b] byte-identical across nodes: {len(union)-len(diffs)}/{len(union)} (diffs={len(diffs)})")
    if diffs:
        fails.append(f"non-byte-identical {len(diffs)}")

    # (5) idempotence
    rep2 = sw.sync(A, B)
    print(f"[5] idempotent re-sync: a_pulled={rep2['a_pulled']} b_pulled={rep2['b_pulled']} (want 0/0)")
    if rep2["a_pulled"] or rep2["b_pulled"]:
        fails.append("not idempotent")

    # (6) NEGATIVE CONTROL: tamper an object on B, drop it from A, confirm pull REJECTS it
    victim = next((a for a, (c, ok) in sorted(sw.manifest(A).items()) if c == "content"), sorted(union)[0])
    os.remove(os.path.join(A, sw.FULL, victim + ".md"))   # A now "wants" victim
    vb = os.path.join(B, sw.FULL, victim + ".md")
    body = okf_mem.read(vb)
    okf_mem.write(vb, body + "\nTAMPERED-PAYLOAD\n")       # B's copy no longer hashes to addr
    pulled, rejected = sw.pull(B, A, [victim])
    rej_ok = (not pulled) and any(r[0] == victim and r[1] == "integrity-fail" for r in rejected)
    print(f"[6] tamper-reject: pulled={pulled} rejected={rejected} -> {'REJECTED (good)' if rej_ok else 'ACCEPTED (BAD)'}")
    if not rej_ok:
        fails.append("tampered object not rejected")

    # (7) no duplicate LUT rows
    dupa = len([r[0] for r in okf_mem.lut_rows(A)]) - len(set(r[0] for r in okf_mem.lut_rows(A)))
    print(f"[7] node_a LUT duplicate addrs={dupa}")
    if dupa:
        fails.append("dup LUT rows")

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("==== G-SWARM-REPLICATE-CONVERGE ====")
    if fails:
        print("VERDICT: RED"); [print("  FAIL:", f) for f in fails]; sys.exit(1)
    print(f"VERDICT: GREEN — L1 content-address round-trip + L2 have/want convergence + "
          f"verify-on-arrival + idempotence + tamper-reject, over {len(union)} real MEM-OKF objects")

if __name__ == "__main__":
    main()
