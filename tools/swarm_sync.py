"""swarm_sync.py — SP-SWARM L1+L2 core: content-addressed have/want replication of the
MEM-OKF store, transport-agnostic (no crypto, no network yet).

This is the FIRST brick of the SP-SWARM memory mesh (design: papers/PPT-LAT-DESIGN-SWARM-
MEMORY-MESH.md). It proves the two gates that doc §8 requires BEFORE any transport:
  L1 — content-address round-trip byte-identity (every object re-hashes to its address).
  L2 — replication convergence (have/want → both peers hold the union; verify-on-arrival).

It reuses okf_mem's EXACT addressing (norm + addr_of + parse_fm) so a "node" here is just a
MEM-OKF root dir. Transport is abstracted: `pull` copies bytes between two local roots; a
libp2p/Noise transport (L0) later swaps in behind the same manifest/have/want/pull seam
WITHOUT changing this reconciliation logic.

Object = full/<addr>.md (Tier-2) + sum/<addr>.md (Tier-1) + a LUT.md row. addr =
sha256(norm(body_without_frontmatter))[:16]. Integrity = re-hash the stored body == addr.
"""
import os, sys, shutil
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import okf_mem  # noqa: E402  (reuse norm/addr_of/parse_fm/read/write/lut_rows/write_lut)

FULL, SUM = okf_mem.FULL_DIR, okf_mem.SUM_DIR

def object_addr_from_file(path):
    """Re-derive the content address of a stored full/<addr>.md by re-hashing its body."""
    _fm, body = okf_mem.parse_fm(okf_mem.read(path))
    return okf_mem.addr_of(body)

# MEM-OKF has TWO address classes (grounded finding, G-SWARM-REPLICATE-CONVERGE):
#   - CONTENT-ADDRESSED (agent facts): addr = sha256(norm(body))[:16] -> re-hash MUST match
#     the filename. This is the strong, tamper-evident guarantee.
#   - C2-ADDRESSED (XBAR/NIGHTSHIFT episodes, added with --addr = their 256-bit C2 SimHash):
#     body does NOT re-hash to addr; the address is externally assigned. Integrity here is
#     self-consistency (frontmatter mem_addr == filename) NOW; cryptographic authenticity is
#     L3's Ed25519 provenance signature (not yet built). NOT tamper-evident on body alone.
def classify(path, addr):
    """-> ('content', True) strong re-hash match; ('c2', True) self-consistent episode;
       (_, False) INVALID (tampered content object, or malformed)."""
    text = okf_mem.read(path)
    fm, body = okf_mem.parse_fm(text)
    if okf_mem.addr_of(body) == addr:
        return ("content", True)
    if fm.get("mem_addr") == addr and fm.get("mem_kind") == "episode":
        return ("c2", True)
    return ("bad", False)

def manifest(root):
    """{addr: (class, valid)} for every object the node HOLDS (from full/)."""
    d = os.path.join(root, FULL)
    out = {}
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.endswith(".md"):
                addr = fn[:-3]
                out[addr] = classify(os.path.join(d, fn), addr)
    return out

def have(root):
    return set(manifest(root).keys())

def verify_object(root, addr):
    """Valid iff content-addressed re-hash matches OR it is a self-consistent C2 episode.
    A tampered content-addressed object (body changed) fails (re-hash != addr, kind != episode)."""
    p = os.path.join(root, FULL, addr + ".md")
    if not os.path.exists(p):
        return False
    return classify(p, addr)[1]

def _lut_row_for(root, addr):
    for r in okf_mem.lut_rows(root):
        if r and r[0] == addr:
            return r
    return None

def pull(remote_root, local_root, addrs, verifier=None):
    """Fetch `addrs` from remote into local, VERIFYING each on arrival (git/IPFS pattern)
    BEFORE writing. L2 check always: content objects must re-hash to addr, C2 episodes must be
    self-consistent. If `verifier` is given (L3 Ed25519, a callable (full_path, addr)->(ok,
    reason)), the object must ALSO pass provenance — this is what makes C2 episodes tamper-
    evident cross-node. Anything failing either check is REJECTED, never written.
    Returns (pulled:list, rejected:list of (addr, reason))."""
    okf_mem.ensure_root(local_root)
    pulled, rejected = [], []
    local_rows = {r[0]: r for r in okf_mem.lut_rows(local_root) if r}
    for addr in addrs:
        rfull = os.path.join(remote_root, FULL, addr + ".md")
        if not os.path.exists(rfull):
            rejected.append((addr, "missing-on-remote")); continue
        cls, ok = classify(rfull, addr)
        if not ok:
            rejected.append((addr, "integrity-fail")); continue
        if verifier is not None:
            vok, reason = verifier(rfull, addr)
            if not vok:
                rejected.append((addr, reason)); continue
        okf_mem.write(os.path.join(local_root, FULL, addr + ".md"), okf_mem.read(rfull))
        rsum = os.path.join(remote_root, SUM, addr + ".md")
        if os.path.exists(rsum):
            okf_mem.write(os.path.join(local_root, SUM, addr + ".md"), okf_mem.read(rsum))
        row = _lut_row_for(remote_root, addr)
        if row:
            local_rows[addr] = row
        pulled.append(addr)
    if pulled:
        okf_mem.write_lut(local_root, list(local_rows.values()))
    return pulled, rejected

def sync(a_root, b_root, verifier=None):
    """Bidirectional content-addressed convergence. Each side pulls what it's missing +
    verifies on arrival (L2 always; L3 provenance when `verifier` given). Idempotent."""
    a, b = have(a_root), have(b_root)
    a_want, b_want = b - a, a - b
    a_pulled, a_rej = pull(b_root, a_root, sorted(a_want), verifier=verifier)
    b_pulled, b_rej = pull(a_root, b_root, sorted(b_want), verifier=verifier)
    a2, b2 = have(a_root), have(b_root)
    return {
        "a_before": len(a), "b_before": len(b),
        "a_pulled": len(a_pulled), "b_pulled": len(b_pulled),
        "a_rejected": a_rej, "b_rejected": b_rej,
        "a_after": len(a2), "b_after": len(b2),
        "converged": a2 == b2, "union": len(a | b),
    }

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["manifest", "sync", "verify"])
    ap.add_argument("root")
    ap.add_argument("peer", nargs="?")
    x = ap.parse_args()
    if x.cmd in ("manifest", "verify"):
        m = manifest(x.root)
        content = sum(1 for c, ok in m.values() if c == "content")
        c2 = sum(1 for c, ok in m.values() if c == "c2")
        bad = [a for a, (c, ok) in m.items() if not ok]
        print(f"{x.root}: {len(m)} objects | content-addressed={content} c2-episode={c2} invalid={len(bad)}")
        if x.cmd == "verify":
            print("VERDICT:", "GREEN" if not bad else f"RED ({len(bad)} invalid: {bad[:10]})")
    elif x.cmd == "sync":
        print(sync(x.root, x.peer))
