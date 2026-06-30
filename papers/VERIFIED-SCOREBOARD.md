---
type: project-state
title: "Verified Scoreboard — what is built, what is open (receipts-checked)"
description: "The proven-capability scoreboard, re-verified 2026-07-01 against actual commits + gate fixtures by the Phase 0 ground-truth fleet (not transcribed from prior docs). 9 VERIFIED, 1 PARTIAL, 0 false-greens. Plus the open frontier, the honest negatives kept attached, and the contradictions reconciled."
tags: [project-state, scoreboard, receipts, verification]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/VERIFIED-SCOREBOARD.md
sp_status: GREEN
sp_gate: "each row names its gate"
sp_commit: "see rows"
sp_repro: "Phase 0 fleet audit 2026-07-01: every commit confirmed an ancestor of engine HEAD; every gate fixture read, not just stat'd"
---

# Verified Scoreboard (2026-07-01)

Method: a read-only fleet checked each claim against (a) a commit that resolves and is an ancestor of engine HEAD, and (b) a gate fixture/receipt file that exists and contains a GREEN verdict. A claim with no commit+gate was to be downgraded. Result: **9 VERIFIED · 1 PARTIAL · 0 UNVERIFIED · 0 false-greens.**

## Built + verified

| Capability | Status | Commit | Gate / receipt | Verdict |
|---|---|---|---|---|
| Byte-exact 12B forward (`SP_BYTEEXACT`) | gated-GREEN, default-off | `69c0588` | `tests/fixtures/xbar_r3/G-BYTEEXACT-FORWARD-12B.log` | VERIFIED — off 4.6665 null-floor / on 4.6569 / run-to-run bit-identical |
| O(1) persistent conversation KV (`SP_PERSIST_KV`) | PROVEN, default-ON | `d211fd2` | `tests/perf/G-PERSIST-KV-PARITY.log` | VERIFIED — 6-turn SHA-256 ON==OFF byte-identical |
| SWA ring (sliding-window KV shrink) | GREEN | in `0019b86→d2d7ceb` | `tests/fixtures/xbar_p3_replay/` | VERIFIED |
| Global-eviction slab + learned-LSH + NIAH | CLOSED GREEN | `222463a`,`33ac632`,`8e35877`,`3218d73` | `tests/fixtures/lsh/lsh_R_r32_raw.bin`+`lsh_M_r32.bin`; NIAH/ladder logs | VERIFIED — needle HIT at depth 10/50/90%; FROZEN±1 = MISS (neg control) |
| B3-WC autonomous episodic recall | CLOSED GREEN-LIVE | `edc8079` | `tests/fixtures/chat_fullstack/G-CHAT-B3-WC-{DEPLOY,DIV2}.log` | VERIFIED — live on the 12B; foreign-reject clean |
| Diffusion Judge OOD | PROVEN | lattice `dda7ffa` | `tests/fixtures/chat_fullstack/G-DIFFJUDGE-OOD-H2H.log` | VERIFIED — recall 94.4% / reject 98.0% |
| CHAT-FULLSTACK (served 12B chat) | GREEN-LIVE | chat_fullstack arc | `CONTRACT-CHAT-FULLSTACK.md` + `G-CHAT-*.log` | VERIFIED — coherent + byte-exact + O(1) + single-entry |
| Memory agency: forget / decide / merge | GREEN | chat arc | `G-FORGET.log`,`G-DECIDE.log`,`G-MERGE.log` | VERIFIED — all three GREEN, null-floor when off |
| Telepathy TELE-1..15 (bridge + route + two-stage + native delegate + LIVE delegate) | PROVEN (1-3) / WIRED (4) / native CPU delegate / **LIVE two-stage delegate** | `2f57520` (TELE chain) + `c3c4b22`,`ef6c282` (TELE-15) | `tests/fixtures/telepathy/G-TELEPATHY-LIVE.log` + receipts in `tools/telepathy/*` | VERIFIED — TELE-15 `G-TELEPATHY-LIVE` GREEN: `decide_route(latent)` → `delegate_execute` runs the qwen coder on CLEAN TEXT (CPU L1, ~0.8 tok/s), coherent answer; never-fuse honored. Honest scope = gist/intent routing + clean-text execution, NOT latent verbatim |
| MEM-OKF anti-rebuild store | ACTIVE | tooling | `tools/okf_mem.py` + `memory-okf/` (verify GREEN, 83 objects) | VERIFIED |
| NIGHTSHIFT offline curator | **PARTIAL** | `6107f3e`,`9ad7ede`,`9ee4668` | `tests/fixtures/chat_fullstack/G-NIGHTSHIFT-CURATOR.log` | PARTIAL — synthetic gate GREEN; **criterion 5 (live B4 in-distribution) PENDING** |

## The open frontier (what we actually skipped)

Grouped by the 4 roadmap axes:

**Axis 1 — Sovereign Telepathy.** v1 **DONE** (TELE-15 `G-TELEPATHY-LIVE` + TELE-16 `G-TELEPATHY-CHAT-LIVE`, both GREEN): the cemented two-stage delegate runs live AND is wired into the served `/v1/chat` SSE path (`SP_TELEPATHY_CHAT=1`, default-off null floor) — a routed turn streams the qwen coder's clean-text answer into the live `{delta}` stream with `⟦delegate⟧` markers, never fusing (TELE-12). Engine `c3c4b22`/`50200eb`; tag `telepathy-v1`. Remaining: (a) **autonomous feat-route on the served path** — currently route is `SP_ROUTE_FORCE`-driven; the TELE-7 head needs a NON-COMMITTING `capture_feat` dispatch verb (the existing `gemma4_kv_capture_feat` is async-armed and would commit the cache) + d_model plumbing; (b) GPU-speed transmit, blocked by the arch gap (CUDA `qwen3_decode_cuda` is `SP_ARCH_QWEN3`-only; `qwen3_generate_kv` segfaults on the CUDA session) → coder runs CPU-only (~0.8 tok/s) by design. NOTE: a latent-prefix `inputs_embeds` seam is deliberately NOT built — fusing latent+text is the TELE-12 0.000 negative. Licensing/attestation = SPEC (fail-closed).

**Axis 2 — CRT residue split / multi-device.** Garner 2-prime constants PROVEN; residue-exchange multi-device is `[DESIGN]`; QUIC residue transport proven on **loopback only**. The 2-physical-GPU byte-exact bit-identical check is the one remaining external byte-exact item.

**Axis 3 — Absolute faithfulness. SOLVED (2026-07-01, `184994b`).** Recall-path fact obedience = **100%** (G-FAITHFUL-RECALL-JACCARD 15/15) on a strong-prior conflict set. The chain: in-context obedience was already 100% (F1); pure-KV replay recall = 0% (F1b.1 — W_c mis-selects natural facts + attenuated K/V can't override a prior); the fix (F2b, `SP_RECALL_JACCARD`, default-off) = select the episode by token-overlap/Jaccard (`recall::token_overlap`, not the geometric W_c) + deliver text-in-context with the faithfulness system prompt. Rule: natural facts → Jaccard+text; novel high-entropy needles → keep W_c+replay. Receipts `tests/fixtures/faithful/`.

**Axis 4 — Native consolidation.** Port host-Python XBAR tooling (C2 signatures, Frobenius episode codec) to C/Rust; T4 Frobenius of model **weights** (validated lever, unbuilt); single-binary deployment. Wire the proven P3 eviction slab from the test-bin into the live daemon (PORT, not rebuild — `lsh_R_r32_raw.bin` is already trained).

**Also open:** WIRE-CPU integer-pipe speed (~23× behind llama.cpp on 0.6B CPU — the RFC north-star P1); NIGHTSHIFT live B4 (criterion 5); P3.4 larger-N multi-chunk PPL hardening.

## Honest negatives (kept attached, by policy)

- **P2.b generation channel** at k=2: latent generation refuted; recognition sub-usable (32-way top-1 0.462). Adopted fallback = two-stage retrieve-then-verify.
- **Telepathy precise-symbolic channel**: latent carries gist/intent only; fused latent+text = 0.000 (corrupts downstream). Architecture is strictly two-stage: decide via latent, execute via clean text. Never fuse.
- **C2.4 32k/64× Optane finale**: needle not retrieved at 64× selection — closed as a miss.
- **KSTE as a recall router**: falsified (histogram, permutation-invariant); router is the ±1 Rademacher projection.
- **ETA.5b 34.2 tok/s**: retired (quant artifact failed PPL gate); real number 26.1 tok/s @ PPL 5.12.

## Contradictions reconciled (2026-07-01)

These were drifting across dated docs; the authoritative resolution:

1. **Diffusion judge** — the 26B cascade is **retired**; production recall gate is the deterministic **Jaccard verifier @0.6**. The native diffusion judge plateaus ~50% recall (won the OOD kill-test as a *proxy*, but is not the production path). The 06-21 docs claiming "N5b justified / native judge is production" are **superseded** (`STATUS-MAP-2026-06-21.md`, `RFC-ORGANISM-unified.md` → marked stale on this point).
2. **MTP / spec-decode** — `G-EAGLE-ACCEPT` live probe **shipped** (`5689e3f`); the EAGLE/MTP draft pipeline is wired. STATE's older "parked, needs draft source" framing is stale; FRAMEWORK-INDEX §G/§S is current.
3. **Gate registry** — single source is `PPT-LAT-FRAMEWORK-INDEX.md §G`; `gate-receipts.md` is archived (superseded).
4. **API reference** — single source is `PPT-LAT-FRAMEWORK-API.md`; `PPT-LAT-KEYSTONE-API.md` is superseded.
5. **Systems narrative** — `PPT-LAT-Systems-v1.md` is current; `PPT-LAT-Systems.md` (v0) archived.
