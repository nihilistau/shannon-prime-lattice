#!/usr/bin/env python3
"""
G-FOUNDATION-ROUTING — architectural invariant gate (the anti-drift guardrail).

WHY THIS EXISTS: the project's recurring failure is a backend shipping its OWN copy of a
primitive (KV cache, forward, recall) that BYPASSES the L1 ABI / the foundation, then being
called "the system". This gate makes that drift a tracked RED instead of an invisible regression.

INVARIANT: the served CUDA decode must route KV through the foundation KV codec (the O_K Spinor
carrier via the L1 ABI kv_flags / SP_KV_SPINOR seam), NOT a private raw-float buffer.

IMPORTANT (integrity, 2026-06-28): an earlier version of this gate matched on the mere PRESENCE
of the strings "kv_flags" / "SP_KV_SPINOR". That FALSE-GREENED the moment the (inert) kv_flags
ABI surface was added, even though the KV was still raw float. A gate you can satisfy by writing
a comment is worthless. So this gate now keys on a REAL CARRIER SENTINEL that is added to
cuda_forward.cu ONLY when the O_K Spinor KV store + inline-decode is actually implemented AND its
runtime gates pass (G-WIRE-CUDA-DECODE-GEMMA4 bit-exact + G-CUDA-KV-RATIO). Do not add the
sentinel to pass the gate; add it because the carrier is real.

The static gate is a TRIPWIRE; the REAL proof is the runtime gates (bit-exact decode == oracle on
the O_K Spinor KV + measured compression). This file just refuses to let the seam be mistaken for
the carrier.

Run:  python g_foundation_routing.py [engine_repo_root]
Exit 0 iff GREEN (carrier sentinel present). RED otherwise.
"""
import os, re, sys

DEFAULT_ENG = r"D:\F\shannon-prime-repos\shannon-prime-system-engine"
CU = r"src\backends\cuda\cuda_forward.cu"
DISPATCH = r"tools\sp_daemon\src\cuda_kvdecode_dispatch.rs"

# The carrier sentinel — a single, unambiguous marker. Add this EXACT token to cuda_forward.cu
# only when the live-KV O_K Spinor store+inline-decode is implemented and its runtime gates pass.
CARRIER_SENTINEL = "SP_KV_FOUNDATION_CARRIER_IMPL"


def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def main():
    eng = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENG
    cu = read(os.path.join(eng, CU))
    disp = read(os.path.join(eng, DISPATCH))

    seam = ("set_kv_flags" in disp) and ("kv_flags" in disp)              # the ABI seam (done)
    carrier = CARRIER_SENTINEL in cu                                       # the real carrier (sentinel)
    # honesty check: if the live-decode KV is still a raw-float alloc AND no sentinel, it's a bypass.
    raw_float_kv = bool(re.search(r"cudaMalloc\(\s*&?(K|V)st\[[^\]]*\][^;]*sizeof\(float\)", cu))

    print(f"G-FOUNDATION-ROUTING  (engine = {eng})")
    print("invariant: served CUDA decode routes KV through the O_K Spinor foundation carrier (not a private float buffer)\n")
    print(f"  [{'GREEN' if seam else 'RED  '}] ABI seam present (kv_flags / set_kv_flags in cuda_kvdecode_dispatch.rs)")
    print(f"  [{'GREEN' if carrier else 'RED  '}] CARRIER implemented (sentinel {CARRIER_SENTINEL} in cuda_forward.cu)")
    print(f"  [{'note ' }] live-decode raw-float KV alloc still present: {raw_float_kv}")
    green = seam and carrier
    print("\n" + "=" * 64)
    if green:
        print("VERDICT: GREEN — served CUDA decode routes KV through the foundation carrier.")
        print("  (Confirm the runtime gates too: G-WIRE-CUDA-DECODE-GEMMA4 + G-CUDA-KV-RATIO.)")
        return 0
    print("VERDICT: RED — KV not yet routed through the foundation.")
    print(f"  seam={'ok' if seam else 'missing'}; carrier={'IN' if carrier else 'NOT IMPLEMENTED'}"
          + ("; live KV is still raw float (the bypass)." if raw_float_kv else "."))
    print("  Fix: CONTRACT-CUDA-KV-FOUNDATION (implement the O_K Spinor store+inline-decode in the")
    print("  CUDA decode, reusing the XBAR store pattern; add the sentinel only when its runtime gates pass).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
