"""g_swarm_provenance.py — GATE G-SWARM-PROVENANCE-ED25519 (SP-SWARM L3).

Proves Ed25519 provenance (libsodium/PyNaCl) makes replication cryptographically tamper-evident
BEFORE commit — closing the C2-episode hole L1 left open. All local, no network.

Positive: signed objects (content + C2 episode) from a rostered node pull + verify + commit.
Kill-tests (each MUST be rejected on pull and NOT written):
  (a) tampered C2 episode body   -> sig-invalid   [the headline: L1 could not catch this]
  (b) stripped signature         -> unsigned
  (c) forged signature           -> sig-invalid
  (d) signer not in roster       -> untrusted-signer
  (e) tampered content body       -> sig-invalid (also fails L1 re-hash)

Usage: python g_swarm_provenance.py <memory-okf-root>
"""
import os, sys, shutil
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import okf_mem, swarm_sync as sw, swarm_provenance as prov

def seed_one(dst_root, src_root, addr):
    okf_mem.ensure_root(dst_root)
    okf_mem.write(os.path.join(dst_root, sw.FULL, addr + ".md"),
                  okf_mem.read(os.path.join(src_root, sw.FULL, addr + ".md")))
    ss = os.path.join(src_root, sw.SUM, addr + ".md")
    if os.path.exists(ss):
        okf_mem.write(os.path.join(dst_root, sw.SUM, addr + ".md"), okf_mem.read(ss))

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "memory-okf"
    tmp = os.path.join(_HERE, "_tmp_prov")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    fails = []

    # identities: B originates+signs, A pulls; U is an UNTRUSTED (unrostered) key
    b_sk, b_vk = prov.keypair(); B = "node-B"
    a_sk, a_vk = prov.keypair(); A = "node-A"
    u_sk, u_vk = prov.keypair(); U = "node-UNKNOWN"
    roster = {B: prov.vk_hex(b_vk), A: prov.vk_hex(a_vk)}   # U deliberately absent
    verifier = lambda path, addr: prov.verify_object(path, addr, roster)

    m = sw.manifest(src)
    content_addrs = [a for a, (c, ok) in sorted(m.items()) if c == "content"]
    c2_addrs = [a for a, (c, ok) in sorted(m.items()) if c == "c2"]
    if not content_addrs or not c2_addrs:
        print(f"RED: need both classes (content={len(content_addrs)} c2={len(c2_addrs)})"); sys.exit(1)
    ca, ep = content_addrs[0], c2_addrs[0]   # one content object, one C2 episode
    print(f"[setup] roster={list(roster)}; content-obj={ca} c2-episode={ep}")

    def fresh_origin(addr, sign_key=b_sk, signer=B):
        """a scratch origin holding one signed object."""
        o = os.path.join(tmp, "orig_" + addr[:6] + "_" + os.urandom(2).hex())
        seed_one(o, src, addr)
        prov.sign_object(os.path.join(o, sw.FULL, addr + ".md"), addr, sign_key, signer)
        return o

    def pull_fresh(origin, addr):
        p = os.path.join(tmp, "pull_" + os.urandom(3).hex())
        pulled, rejected = sw.pull(origin, p, [addr], verifier=verifier)
        present = os.path.exists(os.path.join(p, sw.FULL, addr + ".md"))
        return pulled, rejected, present

    # (POSITIVE) both a signed content object and a signed C2 episode verify + commit
    for label, addr in (("content", ca), ("c2-episode", ep)):
        o = fresh_origin(addr)
        pulled, rejected, present = pull_fresh(o, addr)
        okp = (addr in pulled) and present and not rejected
        print(f"[+] signed {label} {addr}: pulled={bool(pulled)} present={present} rejected={rejected} -> {'ACCEPT (good)' if okp else 'FAIL'}")
        if not okp:
            fails.append(f"positive-{label} not accepted")

    # (a) tampered C2 episode body -> sig no longer matches -> sig-invalid  [L1 could not catch]
    o = fresh_origin(ep); f = os.path.join(o, sw.FULL, ep + ".md")
    fm, body = okf_mem.parse_fm(okf_mem.read(f))
    okf_mem.write(f, okf_mem.fm_block(fm) + "\n" + okf_mem.norm(body + "\nTAMPER-EPISODE\n"))
    pulled, rejected, present = pull_fresh(o, ep)
    ok = (not pulled) and (not present) and any(r[1] == "sig-invalid" for r in rejected)
    print(f"[a] tampered C2 episode: rejected={rejected} present={present} -> {'REJECT sig-invalid (good)' if ok else 'BAD'}")
    if not ok: fails.append("tampered-c2 not rejected")

    # (b) stripped signature -> unsigned
    o = fresh_origin(ca); f = os.path.join(o, sw.FULL, ca + ".md")
    fm, body = okf_mem.parse_fm(okf_mem.read(f)); fm.pop("mem_sig", None); fm.pop("mem_signer", None)
    okf_mem.write(f, okf_mem.fm_block(fm) + "\n" + okf_mem.norm(body))
    pulled, rejected, present = pull_fresh(o, ca)
    ok = (not pulled) and (not present) and any(r[1] == "unsigned" for r in rejected)
    print(f"[b] stripped signature: rejected={rejected} -> {'REJECT unsigned (good)' if ok else 'BAD'}")
    if not ok: fails.append("stripped-sig not rejected")

    # (c) forged signature -> sig-invalid
    o = fresh_origin(ca); f = os.path.join(o, sw.FULL, ca + ".md")
    fm, body = okf_mem.parse_fm(okf_mem.read(f)); fm["mem_sig"] = os.urandom(64).hex()
    okf_mem.write(f, okf_mem.fm_block(fm) + "\n" + okf_mem.norm(body))
    pulled, rejected, present = pull_fresh(o, ca)
    ok = (not pulled) and (not present) and any(r[1] == "sig-invalid" for r in rejected)
    print(f"[c] forged signature: rejected={rejected} -> {'REJECT sig-invalid (good)' if ok else 'BAD'}")
    if not ok: fails.append("forged-sig not rejected")

    # (d) valid signature from an UNROSTERED key -> untrusted-signer
    o = fresh_origin(ca, sign_key=u_sk, signer=U)
    pulled, rejected, present = pull_fresh(o, ca)
    ok = (not pulled) and (not present) and any(r[1] == "untrusted-signer" for r in rejected)
    print(f"[d] unrostered signer: rejected={rejected} -> {'REJECT untrusted-signer (good)' if ok else 'BAD'}")
    if not ok: fails.append("untrusted-signer not rejected")

    # (e) tampered content body -> sig-invalid (also L1 re-hash fails -> integrity-fail is fine too)
    o = fresh_origin(ca); f = os.path.join(o, sw.FULL, ca + ".md")
    fm, body = okf_mem.parse_fm(okf_mem.read(f))
    okf_mem.write(f, okf_mem.fm_block(fm) + "\n" + okf_mem.norm(body + "\nTAMPER-CONTENT\n"))
    pulled, rejected, present = pull_fresh(o, ca)
    ok = (not pulled) and (not present) and any(r[1] in ("sig-invalid", "integrity-fail") for r in rejected)
    print(f"[e] tampered content: rejected={rejected} -> {'REJECT (good)' if ok else 'BAD'}")
    if not ok: fails.append("tampered-content not rejected")

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("==== G-SWARM-PROVENANCE-ED25519 ====")
    if fails:
        print("VERDICT: RED"); [print("  FAIL:", x) for x in fails]; sys.exit(1)
    print("VERDICT: GREEN — Ed25519 (libsodium) sign-on-write + verify-on-pull: signed content "
          "AND C2 episodes commit; tampered-episode / stripped / forged / unrostered / tampered-"
          "content ALL rejected before write. C2 episodes are now tamper-evident cross-node.")

if __name__ == "__main__":
    main()
