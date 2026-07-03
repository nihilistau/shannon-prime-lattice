---
type: design
title: "ADR-004 — Memory as a Governing Layer: MEM-OKF policy drives the Decide→Execute spine"
description: "Elevates MEM-OKF to a governing layer CO-EQUAL with ADR-002's Decide→Execute spine. The empirical result of the whole faithfulness campaign is that NO single global delivery/decline tool is correct — each proven tool (zero-inference decline, systemecho, two-stage, recite, pass) is right for a DIFFERENT class of memory. Therefore the retrieved memory entry's OWN declared policy (carried in its MEM-OKF frontmatter, per the MEM-OKF v2 spec) must drive the spine's LatentDecision, rather than a hard-coded global rule. Deciders stop hard-coding delivery; they consult mem_policy. This makes the memory FORMAT a first-class control surface: a secret can never be systemecho'd, a counterfact is always authoritatively delivered, a same-template-ambiguous fact is two-staged — by construction, per entry."
tags: [design, adr, memory, mem-okf, governance, decide-execute, spine, delivery, decline, faithfulness, okf, karpathy-llm-wiki]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-004-MEMORY-GOVERNANCE.md
sp_status: GREEN
sp_gate: "G-MEMPOLICY-V3 (harness) + G-MEMPOLICY-SERVED (metal, GREEN): served A/B — global SP_RECALL_L5_PROMPT=plain, SP_MEM_POLICY=0 gives OBEY 11/30·17-leak; SP_MEM_POLICY=1 gives 21/30·0-leak (the entry's counterfact policy overrode plain->systemecho on the served spine)"
sp_commit: "opens after engine 88b0280 + the E1/E2/E8 delivery receipts; builds on ADR-002 (PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE) + MEM-OKF v1 (MEMORY-OKF-PROFILE)"
sp_repro: "per MEM-OKF-V2-SPEC + the policy harness (pending)"
---

# ADR-004 — Memory as a Governing Layer

**Status: DESIGN (proposed).** Builds on and is CO-EQUAL with **ADR-002** (the Decide→Execute
spine). Depends on **[MEM-OKF v2 spec](PPT-LAT-MEM-OKF-V2-SPEC.md)** for the policy schema.

## 1. Context — the empirical result that forces this

The faithfulness campaign convicted every *global* selection lever and, in doing so, produced
a sharper truth: the proven **delivery / decline tools are each correct for a DIFFERENT class
of memory**, and no single one is globally right. The receipts (this session + prior):

| tool (proven) | behavior | leak | what it's RIGHT for | what it's WRONG for | receipt |
|---|---|---|---|---|---|
| **zero-inference decline** (attr-gate) | streams a fixed string, NO forward | leak *mathematically impossible* | private / zero-prior secrets (SNE) | general knowledge (over-declines) | `G-SNE-ATTRGATE-ZEROINF` |
| **systemecho** | single-fact authoritative override | **0** | general counterfacts / overrides | same-template cross-picks (can't fix selection) | `G-QKEYS-SYSTEMECHO` (22/30·0) |
| **two-stage** (select→single) | full-ctx select, single-fact generate | **3/30 (REFUTED)** | — | discrete select = the selection ceiling, +leak on off-topic mis-select | `G-MEMPOLICY-V3` (22/3, ≤ systemecho) |
| **full-context** | all facts in one context | **4/30** | recovering buried selection | dilutes authority ⇒ leaks | `G-E1-E2-DELIVERY` (25/30·4) |
| **recite** | plain in-context fact | low | unique-subject high-confidence | strong-prior overrides | RUNBOOK §11 |
| **pass / QONLY** | no recall, clean model | n/a | non-interrogative turns | — | `G-RECALL-QONLY` |
| **learned relevance head** | W_c metric | — | unique-subject (360/361) | same-template novel (0% holdout) | `G-WCHEAD-SAMETEMPLATE` |

The spine today (ADR-002) hard-codes ONE global path (`SP_RECALL_L5_PROMPT=systemecho`,
`SP_RECALL_ATTR_GATE`, …) chosen by env flags at serve time. That is a *config*, not a
*per-memory* decision — so a private secret and a general counterfact get the SAME treatment,
which is provably wrong for one of them. **The lever the campaign leaves standing is not a
better selector — it is letting each memory carry its own policy.**

## 2. Decision

**The retrieved memory entry's declared policy drives the spine's `LatentDecision`.** MEM-OKF
is promoted from a passive store to a **governing layer co-equal with the Decide→Execute
spine**: the DECIDE tier READS the entry's `mem_*` policy (MEM-OKF v2 frontmatter) and
dispatches to the matching executor, instead of applying one hard-coded global rule.

Concretely, the spine gains a policy-driven decider:

```
retrieve(query)            -> [Entry]                      (MEM-OKF v2 retrieval policy: key/selector/tau/guard)
RecallPolicyDecider.refine(view, current):
    e = best entry for view                                (per its OWN mem_retrieval)
    match e.policy.delivery:
        attr-gate-strict / zero-inference -> Decline{ e.decline.message }   (if e.decline.when fires)
        systemecho                        -> Deliver{ e, SystemEcho }
        two-stage                         -> Deliver{ e, SelectThenSingle }
        recite                            -> Deliver{ e, Recite }
        route:<target>                    -> Route{ target }
        pass                              -> Pass
execute(decision)          -> stream                       (executor honors delivery; decline at the ZERO-decode seam)
```

### The five laws of ADR-004 (governing, like ADR-002's four)

1. **Every recallable entry declares its policy.** `mem_class` + `mem_retrieval` +
   `mem_delivery` + (`mem_decline` when it can refuse). No policy ⇒ the **class default**
   (§3 table); no class ⇒ the global safe default (`recite`, non-authoritative).
2. **The decider consults policy; it never hard-codes delivery.** Adding a delivery tool =
   adding an executor arm + a `mem_delivery` value. No spine rewrite, no new seam (ADR-002 §8.2).
3. **Decline is honored at the ZERO-decode seam.** A `zero-inference` decline streams a fixed
   string with NO gemma4 forward ⇒ confabulation/leak stays *mathematically impossible*
   (`G-SNE-ATTRGATE-ZEROINF`). Policy cannot weaken this; it can only *select* it per entry.
4. **Safety is monotone in class.** A `private-secret` entry can NEVER be `systemecho`'d or
   full-context-dumped (the format forbids the downgrade); the strictest applicable policy wins
   on conflict. A secret's worst case is an over-decline, never a leak.
5. **Default-off / null-floor preserved.** `SP_MEM_POLICY` unset ⇒ the ADR-002 global path,
   byte-identical. The policy layer is additive; an un-tagged store degrades to today's behavior.

## 3. Class → default-policy (grounded in the receipts)

The memory *class* sets the default policy; per-entry fields override. (Full schema in the
[MEM-OKF v2 spec](PPT-LAT-MEM-OKF-V2-SPEC.md) §3.)

| `mem_class` | retrieval | delivery | decline | authority | why (receipt) |
|---|---|---|---|---|---|
| `private-secret` | exact-token + entity_guard | attr-gate-strict | zero-inference on attribute-absent | private | SNE 0-confab/0-leak (`G-SNE-ATTRGATE-ZEROINF`) |
| `counterfact` | l5-question cosine (τ0.30) | systemecho | — | overrides-prior | 22/30·0 leak (`G-QKEYS-SYSTEMECHO`) |
| `same-template` | family-scoped | systemecho (two-stage REFUTED by E8) | low-confidence flag / clarify | overrides-prior | delivery is perfect given selection (30/30·0, `G-MEMPOLICY-V3`); the residual is the selection ceiling (`G-WCHEAD-SAMETEMPLATE`), not delivery |
| `fact` (unique) | l5-cosine | recite | — | supplements | ~100% needle regime |
| `preference`/`persona` | l5-cosine | system | — | supplements | persona turns |
| `episodic-event` | c2-sig / l5 | recite-or-summary | — | supplements | XBAR organism |

## 4. Why this is co-equal with ADR-002 (not subordinate)

ADR-002 defines *how* a latent decision becomes clean-text execution (the compiler-enforced
boundary). ADR-004 defines *what* decides — and the answer is **the memory itself**. The spine
is the mechanism; MEM-OKF is the policy. Neither dominates: a decision needs both a governing
policy (which memory, delivered how) and a governed executor (the spine's clean seam). Hence
"ADR includes the MEM-OKFs": the memory format is now a control structure, validated by a gate
(`G-MEM-OKF-CONFORM` extended to the policy fields), not just a data store.

This also completes the **Karpathy LLM-wiki** picture for our substrate: the wiki is the
compounding, cross-linked, self-describing store; the *schema* (CLAUDE.md-like) that tells the
agent how to operate it is exactly this per-entry policy + the class defaults. Ingest writes
policy-tagged entries and cross-links (contradiction/supersedes/same-template edges); Query is
the policy-driven recall; Lint (NIGHTSHIFT) health-checks policy conformance + contradiction
edges. See MEM-OKF v2 §5.

## 5. Consequences

* **Per-entry safety by construction.** The `private-secret`↔`counterfact` confusion that a
  global config cannot resolve is resolved by the format: the secret carries `zero-inference`,
  the counterfact carries `systemecho`. Wrong-tool-for-the-class becomes structurally impossible.
* **Extensibility.** New tools slot in as `(executor arm, mem_delivery value)` pairs — the
  E8 two-stage executor is the first one added under this ADR.
* **Auditability.** `verify` gains policy conformance; a mis-classed secret is a gate failure,
  not a latent leak waiting to happen.
* **Cost.** Policy read is O(1) frontmatter; two-stage costs a second forward *only for entries
  that opt in* (same-template) — the common `counterfact`/`fact` paths are unchanged.

## 6. Integration surface (the "surface area")

- **Spine (`spine.rs`)**: a `RecallPolicyDecider` (LatentHead-adjacent) that reads `Entry.policy`
  and emits `LatentDecision`; a `SelectThenSingle` `Delivery` executor arm (E8). Gated `SP_MEM_POLICY=1`.
- **Retrieval (`routes.rs` L5 block / `recall.rs`)**: honor `mem_retrieval` per entry (key type,
  selector, tau, entity_guard) instead of the single global L5 path.
- **Latent Interceptor / GEODESIC / TELEPATHY**: all are executors OR deciders under ADR-002;
  they become *delivery/route targets a policy can name* (`mem_delivery: route:telepathy`,
  a future `mem_delivery: geodesic-steer`). ADR-004 gives them a declarative entry point.
- **Store (`okf_mem.py` + `memory-okf/`)**: `add --class/--delivery/--decline …` writes the
  policy block; `verify` validates it (G-MEM-OKF-CONFORM v2).

## 7. Status / honesty
GREEN — realized ON THE METAL (`G-MEMPOLICY-SERVED`): the served spine (`routes.rs` L5 block)
reads each recalled entry's `recall::MemPolicy` (loaded per registry row: `mem_class`/
`mem_delivery`/`mem_decline_*`) and resolves an effective `delivery_mode` + `attr_gate` from
it, OVERRIDING the global env flags, behind `SP_MEM_POLICY=1`. Served A/B (same daemon, global
`SP_RECALL_L5_PROMPT=plain`, registry tagged `counterfact`): SP_MEM_POLICY=0 → OBEY 11/30·17-leak
(plain); SP_MEM_POLICY=1 → **21/30·0-leak** (the entry's policy forced systemecho per-entry).
Default-off = the ADR-002 env path, byte-identical. Follow-on: NIGHTSHIFT assigns `mem_class`
at capture (live episodes currently load `policy=None`→env); a served private-secret episode to
re-prove the decline arm on the metal; point the served registry at the `memory-okf/` store.

Composition also DEMONSTRATED at the harness level (`G-MEMPOLICY-V3`): one store, per-entry
dispatch — counterfact→systemecho **30/30 @ 0 leak** (delivery is perfect given the right
entry), private-secret→recall **5/5** + 0 confab, secret-decline via the proven attr-gate, and
the `okf_mem.py` v2 verify REDs a secret with a leaky delivery (safety monotone enforced). E8
two-stage was REFUTED in the same run (22/3 ≤ systemecho), so `same-template` delivery is
systemecho + a low-confidence flag, not two-stage. What remains: wiring `mem_policy` into the
SERVED spine (`routes.rs` behind `SP_MEM_POLICY`) — the harness proves the composition, the
daemon wiring carries it to the metal. No frozen-ABI change; default-off = the ADR-002 global
path, byte-identical.
