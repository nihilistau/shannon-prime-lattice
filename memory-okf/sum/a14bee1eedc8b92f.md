---
type: memory
title: f16-KV storage flip = 116-site refactor through rewind/replay/recall (NOT a free win); foundation committed, flip = careful-per-subsystem or defer
description: 3.2b __half storage flip touches 116 dKc/dVc/jK/jV sites across k_kv_store + rewind journal + XBAR replay + ARM recall + spill + NaN-poison + a forward path -- not atomic. Why f16-KV keeps being abandoned. 3.1+3.2a templating foundation DONE+COMMITTED (feat/kv-f16, compiling, bit-identical). Recommend per-subsystem-gated or DEFER (modest ~225MB payoff; MTP resurfaces KV).
timestamp: 2026-06-28T07:23:49Z
resource: 0bcaeff
sp_status: DESIGN
sp_gate: scope-mapped
sp_commit: 0bcaeff
sp_repro: none
mem_kind: agent
mem_addr: a14bee1eedc8b92f
tags: [f16-KV 3.2b scope, 116 sites, not atomic, pervasive, rewind journal, XBAR replay, ARM recall, NaN poison, do not one-shot, defer or per-subsystem gated, templating foundation done feat/kv-f16, agent, tier-1]
mem_tier: summary
mem_full: a14bee1eedc8b92f
---

# f16-KV storage flip = 116-site refactor through rewind/replay/recall (NOT a free win); foundation committed, flip = careful-per-subsystem or defer

3.2b __half storage flip touches 116 dKc/dVc/jK/jV sites across k_kv_store + rewind journal + XBAR replay + ARM recall + spill + NaN-poison + a forward path -- not atomic. Why f16-KV keeps being abandoned. 3.1+3.2a templating foundation DONE+COMMITTED (feat/kv-f16, compiling, bit-identical). Recommend per-subsystem-gated or DEFER (modest ~225MB payoff; MTP resurfaces KV).

Full context: [full/a14bee1eedc8b92f.md](../full/a14bee1eedc8b92f.md)
