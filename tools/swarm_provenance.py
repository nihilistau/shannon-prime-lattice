"""swarm_provenance.py — SP-SWARM L3: Ed25519 provenance over MEM-OKF objects.

Audited crypto only (libsodium via PyNaCl; NEVER a rolled/pure-python signer — that would
violate the exact law this brick exists to uphold, SWARM doc §2). Mirrors the production
Rust path (libp2p/ed25519-dalek).

WHY L3: L1 re-hash makes CONTENT-addressed objects tamper-evident, but C2-addressed episodes
(addr = external 256-bit SimHash) are NOT body-re-hashable — a tampered episode would pass L1.
An Ed25519 signature over (addr || body) binds the payload to a trusted identity, so a tampered
episode, a stripped signature, a forged signature, or a signature from an unrostered key all
FAIL verification BEFORE the object is committed to the local store.

Signature travels in the object's frontmatter (mem_signer, mem_sig) — it does NOT change the
content address (addr = sha256(norm(body)) is over the BODY, frontmatter is metadata).
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import okf_mem  # noqa: E402
from nacl.signing import SigningKey, VerifyKey  # audited: libsodium
from nacl.exceptions import BadSignatureError
import nacl.encoding

def keypair():
    sk = SigningKey.generate()
    return sk, sk.verify_key

def vk_hex(vk):
    return vk.encode(encoder=nacl.encoding.HexEncoder).decode()

def signing_payload(addr, body):
    """Bind the signature to BOTH the address and the normalized body (prevents body-swap AND
    address-swap). Deterministic across nodes because norm() is canonical."""
    return (addr + "\n").encode("utf-8") + okf_mem.norm(body).encode("utf-8")

def sign_object(full_path, addr, signing_key, node_id):
    """Sign-on-write: sign (addr||body), store mem_signer/mem_sig in the object frontmatter,
    body (=> content address) unchanged."""
    fm, body = okf_mem.parse_fm(okf_mem.read(full_path))
    sig = signing_key.sign(signing_payload(addr, body)).signature.hex()
    fm["mem_signer"] = node_id
    fm["mem_sig"] = sig
    okf_mem.write(full_path, okf_mem.fm_block(fm) + "\n" + okf_mem.norm(body))
    return sig

def verify_object(full_path, addr, roster):
    """Verify-on-pull. roster = {node_id: verify_key_hex}. Returns (ok, reason).
    Rejects: unsigned, untrusted-signer, sig-invalid (tampered body / forged sig)."""
    fm, body = okf_mem.parse_fm(okf_mem.read(full_path))
    signer = fm.get("mem_signer"); sig = fm.get("mem_sig")
    if not signer or not sig:
        return (False, "unsigned")
    if signer not in roster:
        return (False, "untrusted-signer")
    try:
        vk = VerifyKey(roster[signer], encoder=nacl.encoding.HexEncoder)
        vk.verify(signing_payload(addr, body), bytes.fromhex(sig))
        return (True, "ok")
    except (BadSignatureError, ValueError):
        return (False, "sig-invalid")
