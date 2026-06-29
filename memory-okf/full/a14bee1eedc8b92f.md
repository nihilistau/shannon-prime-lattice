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
tags: [f16-KV 3.2b scope, 116 sites, not atomic, pervasive, rewind journal, XBAR replay, ARM recall, NaN poison, do not one-shot, defer or per-subsystem gated, templating foundation done feat/kv-f16, agent, tier-2]
mem_tier: full
---

ï»¿f16-KV 3.2b SCOPE (measured 2026-06-28): the __half STORAGE flip is NOT a bounded atomic change -- dKc/dVc/jK/jV occur at 116 sites in cuda_forward.cu, threaded through: k_kv_store (write), the rewind journal jK/jV save/restore (G-PERSIST-KV-REWIND), XBAR replay/inject, ARM recall (k_qk_scores + slab + spill/recall + host float staging), NaN-poison (cudaMemset 0xFF = f32 NaN, not f16), a separate prefill forward path, and dozens of cudaMemcpy(...*sizeof(float)) assuming 4-byte elems. THIS is why f16-KV keeps being rediscovered-as-free then abandoned: the value is f16 but the cost is re-threading the whole resident-KV substrate through the proven rewind/replay/recall/spill gates. DONE+COMMITTED (feat/kv-f16): 3.1+3.2a = the two resident-decode ring kernels templated on KV elem type (sp_kvld), <float> instantiated, compiling, bit-identical -- the SAFE foundation, ready. RECOMMENDATION: do NOT one-shot the 116-site flip blind. Either (a) careful per-subsystem conversion, each individually gated (decode-store -> rewind -> replay -> recall -> spill), or (b) DEFER -- payoff is modest (~225MB / 2x on a 12GB card dominated by the 9.4GB model) and MTP/DeepSpec will resurface the entire KV anyway (operator's point). Templating foundation stays as the committed groundwork.
