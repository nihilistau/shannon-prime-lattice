# iGPU / CRT multi-device sharding — RESOLVED honest-negative (do NOT re-offer)

**Verdict: do NOT offer to build, wire, or "prove" CRT multi-device residue-sharing, and do NOT wire the iGPU as a "second CRT island." This was investigated end-to-end and killed on physics.**

Receipt: `shannon-prime-system-engine/tests/perf/SESSION-PERF-SYNTHESIS-2026-06-23.md` (engine `1d0e414`, committed), §1.2 "Why CRT does NOT shard experts across the two GPUs" + §2 tiering.

## Why the pitch is dead
- **CRT shards NUMBERS, not experts.** Dual-prime CRT represents each number by residues; a GEMM is computed IN FULL in each prime channel, then Garner-combined. Assigning p1,p2→2060 and p3→iGPU means each device computes the ENTIRE network in its modulus and needs ALL the weights. Per-device memory saved = **zero**.
- **Real device-sharding needs full ACTIVATION exchange** between devices, not "tiny residue arrays." CRT does not remove activation traffic.
- **CRT's genuine gift to a heterogeneous split is BIT-EXACTNESS** (no cross-device float drift) — the *enabler* of a clean split, NOT the split mechanism.
- **"Ship residues, not tensors" is FALSIFIED physics.**

## The iGPU on this box specifically
Intel UHD Graphics (Tiger Lake Xe-LP, 32 EU, **no XMX**), ~0.75 TFLOPS fp32, dp4a int8 only, **shares system DRAM** (no separate VRAM pool). At best a phase-3-MAYBE cold-tail expert offload from DRAM via Level Zero (needs ACTIVATION exchange, bounded hard by 0.75 TFLOPS + DRAM contention). It is **never a CRT island**. Also: the 2060 is PCIe **gen3 x8** (~6.2 GB/s), not x16/Gen5; the Optanes are M10 block SSDs (~1 GB/s), not app-direct PMEM — both prior pitch assumptions were wrong on physics too.

## What (if anything) is actually left
The only residual sliver is a literal **2-*discrete*-GPU bit-identity diff** for auditability (out-of-band, low priority) — NOT a perf or VRAM lever, and not achievable with the iGPU.

## Doc reconciliation done 2026-06-30
`papers/PPT-LAT-STATE.md` line 121 (§4 target table) and line 300 (P3 roadmap) were both corrected from `[TARGET]`/"the proof" to point here. Prior drift cause: this synthesis lived in `engine/tests/perf/` unlinked from STATE, so fresh reads kept re-offering the dead pitch (this was ~the 8th re-offer).
