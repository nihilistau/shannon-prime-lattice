#!/usr/bin/env python3
"""
G-FOUNDATION-ROUTING — architectural invariant gate (the anti-drift guardrail).

WHY THIS EXISTS: the project's recurring failure is a backend shipping its OWN copy of a
primitive (KV cache, forward, recall) that BYPASSES the L1 ABI / the foundation, then being
called "the system". This gate makes that drift a tracked RED instead of an invisible regression.

INVARIANT CHECKED: the served CUDA decode must route KV through the foundation KV contract
(the L1 ABI codec sp/spinor_block.h + the kv_flags / SP_KV_SPINOR seam) — NOT a private raw
float buffer in cuda_forward.cu.

  RED  = the CUDA decode allocates raw float K/V and the CUDA decode path contains no
         SP_KV_SPINOR / spinor_block handling  -> KV bypasses the foundation (current regression).
  GREEN= the CUDA decode honors the ABI KV codec (SP_KV_SPINOR / spinor_block present in the
         decode/attention KV path)  -> KV is routed through the foundation.

Run:  python g_foundation_routing.py [engine_repo_root]
Exit 0 iff GREEN. Intended to run in the Stage-0 battery and pre-commit.
"""
import os, re, sys

DEFAULT_ENG = r"D:\F\shannon-prime-repos\shannon-prime-system-engine"

# (file, marker-of-bypass, marker-of-foundation-routing)
CHECKS = [
    {
        "name": "CUDA decode KV storage",
        "files": [r"src\backends\cuda\cuda_forward.cu"],
        "bypass": [r"cudaMalloc\(\s*&?K(st)?\b.*sizeof\(float\)", r"cudaMalloc\(\s*&?V(st)?\b.*sizeof\(float\)"],
        "foundation": [r"SP_KV_SPINOR", r"spinor_block", r"sp_spinor_decode", r"kv_flags"],
    },
    {
        "name": "CUDA kvdecode dispatch honors ABI kv_flags",
        "files": [r"tools\sp_daemon\src\cuda_kvdecode_dispatch.rs"],
        "bypass": [],
        "foundation": [r"SP_KV_SPINOR", r"kv_flags", r"spinor"],
    },
]


def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def scan(eng):
    rows, red = [], False
    for c in CHECKS:
        text = "".join(read(os.path.join(eng, f)) for f in c["files"])
        has_bypass = any(re.search(p, text) for p in c["bypass"]) if c["bypass"] else False
        has_found = any(re.search(p, text) for p in c["foundation"])
        # A check is RED if it bypasses without foundation routing, OR (no bypass markers) it
        # simply lacks any foundation-routing marker where one is required.
        if c["bypass"]:
            ok = (not has_bypass) or has_found
        else:
            ok = has_found
        if not ok:
            red = True
        rows.append((c["name"], has_bypass, has_found, ok))
    return rows, red


def main():
    eng = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENG
    print(f"G-FOUNDATION-ROUTING  (engine = {eng})")
    print("invariant: served CUDA decode routes KV through the L1 ABI foundation codec, not a private float buffer\n")
    rows, red = scan(eng)
    for name, byp, fnd, ok in rows:
        print(f"  [{'GREEN' if ok else 'RED  '}] {name:42}  bypass={byp!s:5}  foundation_routed={fnd!s}")
    print("\n" + "=" * 60)
    if red:
        print("VERDICT: RED — KV bypasses the foundation (cuda_forward.cu stores raw float K/V,")
        print("         CUDA decode does not honor SP_KV_SPINOR). This is the tracked regression.")
        print("         Fix: CONTRACT-CUDA-KV-FOUNDATION. Gate goes GREEN when the CUDA backend")
        print("         implements the ABI KV codec (exact default + SP_KV_SPINOR compressed mode).")
        return 1
    print("VERDICT: GREEN — served CUDA decode routes KV through the foundation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
