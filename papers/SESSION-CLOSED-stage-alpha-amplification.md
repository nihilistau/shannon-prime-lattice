# SESSION-CLOSED — Stage Alpha: the amplification arc + C2 envelope close (2026-06-04→06)

**Scope:** the CPU/RAM/Optane tier (Stage Alpha). Closes the C2 ARM-memory
envelope in parts and disposes the composed 32k finale. Companion: CONTRACT-C2
§C2.2/C2.3/C2.4, CONTRACT-SPEED, PPT-LAT-STATE §5.06/§5.08.

## What shipped + gated (each on its own metric)

| Item | Result | Evidence |
|---|---|---|
| Canonical two-ring in math-core (C2.2) | decode is single-source; engine duplicate incinerated; 22.62 tok/s in-engine | math-core `9c26475→54ee28b`; T_ARM_GENKV |
| Dual-prime NTT keystore fusion | 18.35 tok/s (84% f32), bit-identical sequences | T_PR_KSTORE/_BLUE/_RESDOT |
| q-transform SoA head-batch | fusion 18.35→22.3 tok/s; gap 16%→7%; **NTT compute arc CLOSED** | math-core `f7b9b6d`, engine `144d445`; T_PR_BATCH |
| Optane dual-size + QUIC peer + 2-process showpiece | 20.16 MB raw residues over loopback, sequence identical | engine `a0d4e8e`/`2aad7db`/`57c9a53`; M_NET_RING2 |
| Bit-packed popcount router (C2.3) | NIAH 6/6 + PPL −0.97%/−0.12% @≤4×; FAILS 8× (+6.08% vs f32 +0.69%) | math-core `92c07fe`, engine `3d2d2c3`; T_ARM_SIG |
| KVSEL group-centroid kv-head selection | NIAH 3/3 @4× incl d90; PPL −0.92% (beats per-Q-head) | math-core `2441e0b` |
| Split-device Optane (K→F: / V→E:) + read_batch2 overlap | serial split 4u/S WORSE than single 3u/S; overlapped 2u/S | engine `200c0ec`/`2484650` |
| Bounded LRU temporal staging cache | T_CACHE_EXACT bit-identical; absorbs 86%→42% by depth | engine `16e15e3` |

## The novel finding — temporal locality of attention routing

At 32k ingest the composed run pulled **~9.46 TB of Optane reads to serve
~3 GB of unique blocks**: adjacent decode steps' recall sets DRIFT slowly, so
the router re-fetches the same hot blocks every token. A bounded 2 GB LRU cache
absorbs 86% early and tapers to ~42% as the reuse-window union outgrows the
slab with depth (full curve mapped, not extrapolated). The router's working
set glides across the cold store; the cache surfs the live edge. This reframed
the cache from "optimization" to a mandatory O(1)-context component.

## C2.4 composed 32k finale — DISPOSITION: terminated, gate PENDING, not claimed

Four versions chased four real, sequentially-revealed walls: **v2** the O(N²)
scalar routing scan (fixed: AVX512-VPOPCNTDQ); **v3** GQA Q-head divergence
(fixed: KVSEL) — but serial-split-on-asymmetric-silicon was *worse* than one
device; **v4** the device-overlap serialization tax (fixed: read_batch2
concurrent queues); **v5** the temporal re-fetch monster (fixed: LRU cache,
240× less I/O at matched depth). Each lever shipped + gated. **But the single
composed 32k log was never banked** — every run found the next lever and
restarted, and v5 was terminated at 65.5% by operator economic call.

**DECISION (operator):** v5 is the terminal finale; the 4 GB-slab scaling is
DOCUMENTED-NOT-RUN (the absorption curve is measured at 2 GB; scaling the slab
widens the horizon predictably); NO more finale relaunches. The partial run
proved indestructibility (8.6 h saturated dual-store IOCP, RAM flat, zero
leak). The composed gate closes when re-run cheaply post-amplification — it is
NOT load-bearing for the rest of the project.

## Lessons pinned (memory)

- ETA estimates missed 4× same-direction: model READ AMPLIFICATION (union ×
  block × layers) + re-fetch volume, not just op counts. The counters outrank
  the arithmetic.
- Multi-hour bakes are OWNED BY THE OS (schtasks ONCE), never the agent
  process tree (a host restart killed a run living in the shell tree).
- The agent poll-watching a deterministic bake is the real cost, not the
  machine; the machine runs free.
