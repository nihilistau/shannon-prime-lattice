---
type: memory
title: MEM-OKF v2 + ADR-004 built: per-entry policy dispatch DEMONSTRATED; E8 two-stage REFUTED; delivery is perfect given selection (G-MEMPOLICY-V3)
description: Designed+built MEM-OKF v2 (per-entry policy block: mem_class/retrieval/delivery/decline) + ADR-004 (memory as a governing layer co-equal with the Decide->Execute spine). okf_mem.py v2 adds policy add/verify (secret with leaky delivery = RED, safety monotone). G-MEMPOLICY-V3: ONE store, per-entry dispatch - counterfact->systemecho 30/30 @ 0 leak (delivery is PERFECT given the right entry => the 22/30 live ceiling is PURELY selection, the representation limit, NOT delivery); secret->recall 5/5 + 0 confab; secret-decline via proven attr-gate. E8 two-stage REFUTED (22/3 <= systemecho: discrete select = selection ceiling + leak on off-topic mis-select; E1's +3 was generation-integration not selection). same-template default corrected two-stage->systemecho. WHOLE SYSTEM AS ONE: MEM-OKF v2 is the single format engine-spine(EXECUTE)+harness-Nexus(INGEST)+agency-loop=NIGHTSHIFT(CURATE)+L5/Nexus-vector/qmd(RETRIEVE) all speak. Follow-on: wire mem_policy into served routes.rs behind SP_MEM_POLICY. DO NOT rebuild the harness Nexus (ingest/embed/query-router/agency exist).
timestamp: 2026-07-03T08:44:05Z
resource: engine 1317718
sp_status: GREEN
sp_gate: G-MEMPOLICY-V3
sp_commit: engine 1317718
sp_repro: python _v3_corpus/mempolicy_run.py + e8_twostage.py; okf_mem.py verify --root memory-okf; docs PPT-LAT-ADR-004 + PPT-LAT-MEM-OKF-V2-SPEC
mem_kind: agent
mem_addr: cada52f5ebc9a242
mem_class: fact
mem_delivery: recite
mem_authority: supplements
mem_confidence: 0.9
tags: [mem-okf-v2, adr-004, policy, memory-governance, systemecho, two-stage-refuted, e8, composition, karpathy-wiki, nexus, nightshift, agent, tier-2]
mem_tier: full
---

ï»¿G-MEMPOLICY-V3 â€” the ADR-004 composition proof: ONE store, per-entry policy dispatch, each
class hits its proven behavior. Plus E8 (two-stage) REFUTED. (2026-07-03)
=========================================================================================
Tests ADR-004 (memory as a governing layer) + the MEM-OKF v2 policy block: a single store
holding two classes (V3 counterfacts + synthetic private-secrets), each dispatched by its own
mem_class to its proven tool. Harness _v3_corpus/mempolicy_run.py; systemecho daemon (engine
933ea88), custom auto_recall:false prompts per entry policy.

===== E8 (two-stage delivery) â€” REFUTED (_v3_e8.out) =====
Two-stage = stage-1 SELECT the fact index from full numbered context, stage-2 GENERATE that
single fact with systemecho authority. Hypothesis (from G-E1-E2-DELIVERY): capture E1's +3
obey AND keep systemecho's 0 leak.
  RESULT: SELECT 22/30  OBEY 22/30 (73.3%)  LEAK 3   (baseline systemecho 22/0; E1 25/4)
  VERDICT: REFUTED. (1) The discrete "pick a number" select is NO better than L5-cosine (both
  22) â€” the same-template selection ceiling reasserts the moment selection is made discrete.
  (2) It is LEAKIER than systemecho: on a mis-select to a TOTALLY off-topic fact (iron_symbol
  ->idx0 longest_river; dynamite->idx17; rainforest->idx0) single-fact systemecho cannot
  suppress the prior â‡’ 3 leaks. L5-cosine at least stays in the template FAMILY (topically
  adjacent), which preserves 0-leak. (3) E1's +3 obey was GENERATION INTEGRATION (the model
  answering while reading all facts), NOT cleaner selection â€” it does not harvest into a
  select-then-deliver pipeline. CONSEQUENCE for the design: the `same-template` class default
  is corrected two-stage -> systemecho (best available: 22/0) + a low-confidence/decline option;
  two-stage is a kept honest-negative.

===== G-MEMPOLICY-V3 (per-entry policy composition) â€” DEMONSTRATED (_v3_mempolicy.out) =====
counterfact class (mem_delivery=systemecho), each query delivered its OWN correct fact:
  OBEY 30/30  LEAK 0.  => ISOLATES delivery from selection: GIVEN the correct entry, systemecho
  is perfect (30/30 @ 0 leak). The 22/30 ceiling in the live gates is PURELY selection (the
  representation limit, G-WCHEAD-SAMETEMPLATE), never delivery. The policy routes the class to
  the right tool and the tool delivers.
private-secret class (mem_delivery=attr-gate-strict, zero-inference decline):
  present-attribute queries -> recall 5/5 (systemecho recites the stated attribute: door=4471,
    wifi=copperfield, locker=27, cat=Mochi, flight=BA0992).
  absent-attribute queries  -> confab 0 / leak 0 (the model naturally declined the absent
    detail under single-fact systemecho). HONEST GAP: the harness's deterministic decline
    detector (a crude salient-word-absence ratio) did NOT fire (0/5 explicit zero-inference
    declines) â€” it is weaker than the real attr-gate. The HARD zero-inference guarantee (fixed
    string, NO forward â‡’ leak mathematically impossible) is proven SEPARATELY and remains the
    backstop: G-SNE-ATTRGATE-ZEROINF (confab 80â†’0, leak 5â†’0). Here the soft path held anyway.
  => a private-secret is NEVER systemecho'd/full-context-dumped (the format + verify forbid the
     downgrade: a secret with a leaky delivery is a G-MEM-OKF-CONFORM RED â€” proven in the
     okf_mem v2 smoke test).

NET â€” the composition works: ONE content-addressed store, each entry dispatched by its own
mem_class/mem_delivery/mem_decline, each class hitting its proven number (counterfact 30/30Â·0
via systemecho; secret 5/5 recall + 0 confab; secret-decline via the proven attr-gate). This
is ADR-004 realized at the harness level. WHAT'S NOT YET WIRED (honest): the SERVED spine
(routes.rs) still uses the global env path; reading mem_policy per entry in-daemon behind
SP_MEM_POLICY is the follow-on build (the harness proves the composition; the daemon wiring
carries it to the metal).

REPRO: run_v3_gate_se.bat nohead (serve) + python _v3_corpus/{e8_twostage,mempolicy_run}.py.
Store tooling: tools/okf_mem.py (v2 policy add/verify) in shannon-prime-lattice. Docs:
papers/PPT-LAT-ADR-004-MEMORY-GOVERNANCE.md + PPT-LAT-MEM-OKF-V2-SPEC.md. ENV: engine 933ea88.
