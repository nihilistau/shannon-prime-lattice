---
type: memory
title: FP-profile foundation landed (engine e58150d, default GREEN)
description: FP-profile foundation landed (engine e58150d, default GREEN): exact feature default-on, build.rs ring gating, ntt_ffi gated. Remaining: quic_shard NTT-recombine cfg-gating for FP link-green.
timestamp: 2026-07-04T04:08:18Z
resource: TBD
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
mem_kind: agent
mem_addr: noexact-profile-foundation
tags: [no-exact profile, FP profile foundation, exact cargo feature, G-NOEXACT-BUILD, quic_shard gating, ring modules gated, build.rs exact, agent, tier-2]
mem_tier: full
---

ï»¿FP-PROFILE FOUNDATION (--no-exact) landed engine e58150d, default build GREEN. Cargo xact feature DEFAULT-ON; build.rs skips 4 ring archives (ntt_crt/poly_ring/ok_arith/frobenius) under !exact; lib.rs gates ntt_ffi. FP profile = cargo build --no-default-features --features wire_cuda_backend. REMAINING for FP link-green (G-NOEXACT-BUILD): cfg-gate network/quic_shard.rs 3 NTT-recombine sites (QUIC garner mesh, ring-dependent) then --no-default-features build; separately remove exact_islands.c from build-cpu for cl.exe. CUDA byteexact NOT gated (no __int128, interwoven, zero cost off) - DON'T attempt CUDA #ifndef. Doc papers/DESIGN-NO-EXACT-PROFILE.md 4b/4c. Value = portability hygiene only (A/B proved FP ties faithfulness); deprioritized.
