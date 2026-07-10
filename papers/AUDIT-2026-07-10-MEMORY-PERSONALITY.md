---
type: audit
title: "AUDIT 2026-07-10 — memory persistence + personality systems, five-repo review"
description: "Root-cause + fix of 'memory does not persist across sessions'; personality system audit (PF-B1..B5); flag plumbing audit; OKFS store conformance repair; live verification on the reason-model serve."
tags: [audit, memory, persistence, personality, launcher, okfs, flags]
sp_status: GREEN
sp_gate: "persist-after-restart probe 4/5 + foreign clean (inline path); h_personality_* 5/5; G-PK2-* offline 5/5; G-OKF-CONFORM 394/412"
sp_commit: "working trees 2026-07-10 (engine + harness + lattice)"
sp_repro: "run_console_reason.bat; python tools/memory_doctor.py audit; persist probe; python tests/h_personality_*.py; python tools/okf_validate.py memory-okf"
---

# AUDIT 2026-07-10 — memory + personality, five-repo review

Scope: `Position_Is_Arithmetic`, `shannon-prime-system`, `shannon-prime-system-engine`,
`shannon-prime-lattice`, `shannon-prime-harness`. Focus: the live memory system, the
personality system, flag plumbing, cross-session persistence, OKFS conformance.
OKFS entries: `1264a8623b7c6c0e` (memory), `dd122e50e2a82fea` (personality/OKFS).

## 1. The persistence failure — three stacked root causes (all fixed)

The report "memory does not persist across sessions" was real and had three
independent causes that compounded:

**1a. `run_console_reason.bat` was memory-broken** (the launcher last edited 2026-07-10
10:09, i.e. the one in daily use). Line 33 read `set "SP_NIGHTSHIFT_PERSIST"` — with no
`=1` this is a **no-op in batch** (it queries rather than sets), so persistence was
never armed. There was also no `SP_RECALL_REGISTRY` (the daemon then loads `None` and
disables auto-recall for the whole serve), plus `SP_RECALL_L5=0` and
`SP_AUTO_RECALL_DEFAULT=0`. Net behavior: `SP_B4_NIGHTSHIFT=1` still *captured* every
qualifying turn into `_nightshift_live/` — as orphans that no restart would ever see.
**Binding lesson: in batch, `set "VAR"` does not set VAR.**

**1b. Registry rot, silently tolerated.** 13 of 17 rows in
`_memory_live\registry.jsonl` pointed at episode dirs that no longer exist.
`recall::load_registry` rehydrates missing sidecars with `unwrap_or_default()`
(recall.rs ~555–557) and the L5 selector silently skips any episode with
`l5key.len() != 512` (routes.rs ~2186) — **no warning is ever logged**. Dead memories
are invisible: the registry says they exist, recall never finds them. Capture is
gated and logged; reload failure is silent — an asymmetry worth closing in code.

**1c. Orphan blindness.** The daemon never rescans `_nightshift_live/` at startup; the
in-memory nightshift Vec starts empty every boot. 43 orphaned episode dirs were found
on disk (a mix of real user facts from sessions run under the broken launcher, and
test-corpus junk leaked from gate runs).

## 2. Fixes shipped

- **`run_console_reason.bat` rewritten** — full memory stack on the production
  registry: registry bootstrap, `SP_NIGHTSHIFT_PERSIST=1`, `SP_RECALL_L5=1`,
  `SP_AUTO_RECALL_DEFAULT=1`, `SP_QKEY_MINT=1` (question-space keys — the landed
  condition quiet-memory mode was waiting on), `SP_MEM_CLASSIFY=1` + `SP_MEM_POLICY=1`
  (per-entry policy dispatch, OKFS 171c675e), global `SP_RECALL_L5_PROMPT=plain`
  (Hodor binding), SPECTEST veto head. `SP_SPINE` **removed** — see §4.
- **`run_console_everything_reason.bat`** — gains `SP_QKEY_MINT`/`SP_MEM_CLASSIFY`/
  `SP_MEM_POLICY`; its quiet-memory default is preserved (operator verdict; the
  console checkbox overrides per-request).
- **New `tools/memory_doctor.py`** (engine) — `audit` (LIVE/DEAD rows + orphans),
  `prune-dead` (backs up, drops dead rows, dumps re-mint candidates), `adopt`
  (re-index orphan dirs into the registry; dummy `sig_bits` is safe — the L5 path
  never reads it, precedent `build_sne_registry.py`), `remint` (replay facts through
  the live store verb so they re-capture under the current mint config).
- **Registry repaired**: 13 dead rows pruned (backups kept), the two real personal
  facts re-minted live ("My name is Knack.", "My cat's name is Tuffy."), 5 gate-test
  facts removed from the production registry after gating (test-corpus leakage into
  the production registry is a repeat hazard — `run_console_faithful.bat` remains
  GATE-ONLY).
- **RUNBOOK-ONE-CONFIG.md §6 launcher map updated** in the same change-set
  (doc-update law).
- **Harness `agent.py`**: PF-B4 `@personality` pack wired into `all_tools()` gated on
  `SP_PERSONALITY=1` (verified: 4 tools appear when set, absent when unset — null
  floor preserved; smoke suite 10/10).

## 3. Live verification (reason model, fixed launcher)

- Boot: `B3 AUTONOMOUS RECALL: loaded N episode(s)` banner confirms flags landed.
- Re-mint 2/2 → live recall: "what is my cat's name?" → **"Tuffy."**
- `G-B4-GROW-RECALL-L5 grow` leg: growth + persist worked (registry rows appended with
  `mem_class`); R-leg 2/5 on the adversarial same-template bank — the OKFS-documented
  structural L5 collapse ("what is the name of my X" is one L5 neighborhood,
  6d191b79), amplified by a non-empty registry. Not a persistence defect.
- **Full daemon restart → persist probe 4/5** (cat ✓ name/door/sister ✓ before
  cleanup; after test-fact cleanup: cat ✓ name ✓ foreign clean ✓). Facts that exist
  in memory survive restarts and are recalled. **Cross-session persistence: WORKING.**

## 4. New finding — SP_SPINE live leak (one-variable A/B)

With `SP_SPINE=1` and a small personal registry, the foreign probe "What is the
capital of Spain?" answered **"Knack."** — the persona record delivered off-topic,
past attr-gate/veto. Same serve with `SP_SPINE=0` (inline path): **"Madrid."** clean.
The proven serve composition (G-B4-GROW-RECALL-L5, run_console_everything*) is the
inline path; the spine serve composition is ungated. **Keep `SP_SPINE` off in daily
drivers until it earns a live gate.**

## 5. Personality system (PF-B1..B5)

All five offline gates PASS (persona/ownership/tags/decorators/curate). Architecture
facts: the daemon at :3000 is personality-blind by design — persona injection and tag
persistence exist only in the harness gateway (:8800). Persona state itself
(persona.md, memory-okf-self, memory-okf-personality) is on disk and does persist.
Open defects (documented, not yet fixed): `PersonalityStateInterceptor` is registered
under `SP_PERSONALITY=1` but the live serve path never invokes the interceptor
pipeline (the ADR-006 spine `run_post_turn` does the real write-back, gated on
`typed`, not `SP_PERSONALITY`); duplicate interceptor definitions; PF-B5 auto-curation
only arms when `run_agency.py` runs with `SP_CURRENT_CONVO` + `SP_PERSONALITY=1`, so
persona.md trait drift is otherwise unbounded; nothing outside tests sets
`SP_PERSONALITY=1`. To *use* personality live: run the gateway (`harness serve`,
:8800) with `SP_PERSONALITY=1` in front of the daemon.

## 6. Flag plumbing audit

All memory/recall flags are consumed in Rust (`std::env::var`) — no C-side visibility
issue for them. Only `SP_G4_KV_RING_W`/`SP_G4_KV_JMAX` are `_putenv_s`-bridged
(daemon.rs ~663–687); the C glue reads `SP_XBAR_*`/`SP_BYTEEXACT` from the shell —
fine for .bat launchers, a trap for any future Rust `set_var`. Known asymmetries:
`SP_RECALL_L5_PROMPT` default differs by path (spine `systemecho` vs inline `plain`);
persistence requires BOTH `SP_NIGHTSHIFT_PERSIST=1` AND `SP_RECALL_REGISTRY`; capture
requires `messages` (the console's template-fallback retry sends `prompt` and silently
bypasses capture); `npos` is written as full `ntok` while the C2 sig uses clamped
`npos_sig` (latent mismatch, benign while the C2 scan is dead at TAU=+inf).

## 7. OKFS store conformance

`G-OKF-CONFORM` was RED with 50 errors. 32 `sp_status` enum-case violations
(`green`/`PROVEN`/`PARTIAL`) normalized to `GREEN`/`GREEN`/`ACTIVE` across `full/` +
`sum/` — address-safe (addr = sha256(body), frontmatter excluded). Now 394/412
conformant. Remaining, needing owner decision: 18 root `_*.md` legacy notes with no
frontmatter (conform or move to scratch/), and 6 slug-named agent entries
(`echo-47-*`, `noexact-*`, `pf-b4/b5-*`) that fail `okf_mem.py verify` because
filename ≠ sha256(body) — a design tension between `add --addr <slug>` and the
sha-verify rule.

## 8. Recommended follow-ups (priority order)

1. Log a WARN in `load_registry` when a row's dir/`ep.l5` is missing (make rot
   visible); optionally auto-mark `lifecycle` on dead rows.
2. Startup orphan scan (or a `memory_doctor audit` call in the launchers) so orphaned
   captures are at least reported.
3. Gate the spine serve composition (the §4 leak repro is a ready-made gate case).
4. Same-template relevance head (the R-leg residual; OKFS 6d191b79's one unconvicted
   lever).
5. Decide the 18 legacy notes + 6 slug-addr entries in memory-okf.
6. Fix the console template-fallback retry to send `messages` so capture still fires.
