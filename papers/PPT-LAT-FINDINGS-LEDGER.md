---
type: findings-ledger
title: "Findings Ledger — the measured constants, layers, levers, boundaries, and test outcomes"
description: "The single lookup table for everything the campaign has MEASURED on the metal: which layer carries the fact signal, what every threshold/tau/K/alpha is and where it came from, the architectural boundaries (what works vs what is measured-inert), the substrate constants, and a per-test ledger (corpus + config + outcome + receipt + commit). Read this when you need 'which layer / what tau / what K / where the lever is' without re-deriving. Receipts-first: every number names a gate log + commit."
tags: [findings-ledger, constants, layers, levers, boundaries, thresholds, receipts, decide-execute]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-FINDINGS-LEDGER.md
sp_status: GREEN
sp_gate: "each row names its gate"
sp_commit: "engine fc2e846 (attr-gate zero-inference HEAD of this arc); see per-row commits"
sp_repro: "each finding cites the launcher + harness + fixture that reproduces it"
---

# Findings Ledger

**Gist.** The fact signal is layer-localized (global layer 5). Recall = *decide in latent, execute in clean text, never fuse*. The cheap levers win: L5 cosine (τ=0.30) selects at 86.89%; a Jaccard/attribute check grounds delivery; the model's own robustness rejects general-knowledge foreign; a deterministic attribute-gate closes the zero-prior hole at zero inference. The heavy generative judge is parked (it earned nothing the cheap levers didn't). This doc is the flat lookup table of the constants and boundaries behind those sentences.

## Keyword LUT (jump table)
`L5` `global-layer-5` → §1. `tau` `τ=0.30` `Jaccard-0.6` `attr_tau-0.5` `K=2` `TAU=-8` `M_target=42` `EOT_BIAS=4.0` → §2. `never-fuse` `deciders-dont-execute` `native-robustness-boundary` `judge-needs-2` `query-token-guard` → §3. `dual-prime` `period-6` `HD=512` `Ring-3` `C2-256` → §4. `test-ledger` `receipts` → §5. `honest-negatives` `measured-inert` → §6.

---

## 1. Layer / representation localization

| what | value | how measured | receipt / commit |
|---|---|---|---|
| **The fact signal lives in global layer 5** | L5 exact→paraphrase recall@1 = **85.2%**; all-8-global-layer average = **11.5%** (averaging *dilutes* the signal ~7×) | per-layer sweep of the global-Q representation vs a Jaccard oracle | `G-REP-LAYER-L5` |
| L5-cosine query-key recall (offline) | **100% exact / 88.5% paraphrase** (vs Jaccard 100% / 8.2%) | cosine of L5 query-embed vs stored L5 key | `G-REP-LAYER-L5` |
| **L5-cosine recall LIVE (served 12B)** | ~~86.89% (07-01, unreproducible — `G-L5-OBEY-REPRO`)~~ → **88.52% OBEY / 0 LEAK (2026-07-02, `systemecho` delivery)**. 54/61 == selector top-1: every correctly-selected episode obeyed; misses = selection cross-picks. Delivery solved; obey ceiling = selector. Law: obey receipts carry build SHA + canary + full env dump | live `/v1/chat`, `SP_RECALL_L5` + `SP_RECALL_L5_PROMPT=systemecho` | `G-DELIVERY-SWEEP` + `G-ONECONFIG-LIVE`, engine `8ae343b` |
| `SP_RECALL_L5_PROMPT` | **`systemecho`** (fact as SYSTEM authority + verbatim-echo priming; multi-turn preserved) | delivery wording is a MEASURED lever: plain 40.98 < scaled 63.93 < sandwich < factecho/system < systemecho 88.52 (0 leak) | `G-DELIVERY-SWEEP` |
| `SP_RECALL_QONLY` | **1** (canonical config) | non-interrogative turns skip the L5 stage (in-registry cos background ≥0.9 otherwise injects an irrelevant fact) | `G-RECALL-QONLY-LEXICAL` 188/188 + `G-ONECONFIG-LIVE` Q-phase |
| gemma4 global layers | period **6** → global layers `{5, 11, 17, 23, 29, 35, 41, 47}`; `n_global = NL/PERIOD = 8` | arch (content-hash period rebased 8→6 to the true global layers at G-PERIOD6-REBASE) | `d2d7ceb` |
| L5 query-embed construction | mean over `G_NH=16` heads of global layer 5 (last token), L2-normalized → **512-d** (`HD=512`) | `recall::l5_query_embed`; `L5_LAYER=5` | engine `recall.rs` |
| observed L5 cosine range (private entities) | exact-match query ≈ **1.000**; same-entity *different-attribute* query ≈ **0.93–0.95** (the shared entity token dominates the embedding) | SNE serve log | `G-SNE-CRUCIBLE-L5DIRECT` |

**Takeaway:** select on L5 alone; never average the global layers. The entity/subject dominates the L5 embedding — which is why a same-entity mismatched-attribute query still scores ~0.95 (see §3 boundary).

## 2. Thresholds / levers (every knob, its default, and what it does)

| lever (env / const) | value | role | receipt |
|---|---|---|---|
| `SP_RECALL_L5_TAU` | **0.30** | L5-cosine recall gate; below-τ = no recall (silently rejects genuine out-of-corpus foreign) | `G-L5-RECALL-LIVE`, `G-HARDFOREIGN-L5DIRECT` |
| `recall::OVERLAP_THR` (Jaccard) | **0.6** | the production faithfulness verifier — token-overlap of the cited span vs the fact | `G-FAITHFUL-RECALL-JACCARD` (15/15) |
| `SP_RECALL_ATTR_TAU` | **0.5** | attribute-gate: if ≥50% of the query's salient words are ABSENT from the fact → decline | `G-SNE-ATTRGATE` |
| `query_has_entity_token` guard | token `len≥4` AND contains a digit | fires the attribute-gate ONLY for private-entity queries (paraphrase-safe) | `G-ATTRGATE-GUARD-PARA` |
| `SP_B3_JUDGE_K` | **2** (minimum working) | judge candidate count. **K=1 breaks the reject** (single candidate → always-PICK, NULLs=0); **K=2 = 83% clean-reject** (== K=8, cheaper) | `G-JUDGE-KSWEEP-K2` |
| causal-ablation admit oracle `TAU` | **−8** | W_c admission: novel needle ΣΔLL ≈ **−33.56** vs parametric ≈ **−0.15** → clean separation | B3-v13 `15738c1` |
| `SP_REPLAY_MTARGET` | **42** | KV-replay injection-mass clamp (recall replay winner) | `G-CHAT-B3-WC-DEPLOY` |
| `SP_EOT_BIAS` | **4.0** | end-of-turn logit bias (clean turn-stop on the served chat) | chat_fullstack |
| Diffusion Judge (OOD proxy) | recall **94.4%** / reject **98.0%** | won the OOD kill-test as a *proxy*; **NOT** the production path (native judge plateaus ~50%) | `G-DIFFJUDGE-OOD-H2H` |
| C2 SimHash bit-count (similarity overlay) | **256** (frozen C2) → recall@1 0.607 / recall@5 0.885; 512/1024/2048 → @1 0.72/0.82/0.87 | wider sigs recover top-1 toward L5-cosine (0.885); 256 = the shortlist-hint default | `G-SWARM-C2-SEMANTIC` |

## 3. The boundary map (what works vs what is structurally impossible)

The governing law (ADR-002): **DECIDE in latent, EXECUTE in clean symbol/text, NEVER fuse latent content into generation, and a decider must not execute.** The measured boundaries:

| boundary | finding | evidence |
|---|---|---|
| **Never fuse** | fused latent+text transmit = **0.000**; sequential decide→execute is the win | TELE-12/13 |
| **Deciders don't execute** | when the judge *delivered* its own pick it lost context-authority (right pick, parametric answer); routing delivery through the judge session costs recall (50% vs 86.89%) | `G-JUDGE-KSWEEP-K2`, authority fix `4ff75d1` |
| **Judge needs ≥2 candidates** | at K=1 the generative judge degenerates to always-PICK (no reject) | `G-JUDGE-KSWEEP-K2` |
| **Native robustness protects GENERAL knowledge, not PRIVATE data** | general-knowledge hard-foreign (Athens/silver/…) = **0/18 spurious** even when a mismatched fact is delivered (the model has priors); zero-prior novel entities = **80% confabulation + 5% leak** (no priors to fall back on) | `G-HARDFOREIGN-L5DIRECT`, `G-SNE-CRUCIBLE-L5DIRECT` |
| **tau + robustness ≥ the generative judge on reject** | judge = 0 benefit over L5-direct+τ (0/18 == 0/18) AND PASSed 15/18 hard-foreign (failed its own reject job) → PARKED | `G-HARDFOREIGN-JUDGE` |
| **Attribute grounding is a query property, not a query∩fact property** | gate on whether the QUERY carries a private-entity token (a wrong retrieval must NOT lower the shield); a shared-token guard broke SNE decline to 2/6 when L5 delivered a wrong same-structure entity | `G-SNE-ATTRGATE-GUARD` |
| **Zero-inference decline** | on attribute-absence the reject streams a fixed string with NO gemma4 forward → confabulation/leak *mathematically impossible* + microsecond latency | `G-SNE-ATTRGATE-ZEROINF` (16/16 "no gemma4 decode") |
| **Byte-exact ENVELOPE GAP on the served path (2026-07-02)** | served chat already runs byte-exact islands+decode-attention per request (`byteexact` default-true → `gemma4_kv_byteexact_set`); `SP_BYTEEXACT` env = no-op there (61/61 byte-identical A/B). The residual float surface = **prefill cuBLAS GEMMs** — the un-pinned surface behind the para-obey receipt divergence. Name the envelope in every byte-exact claim. | `G-BX-OBEY-AB` |
| **Blunt closed-book prompt over-declines** | `SP_RECALL_STRICT` made the model refuse even valid matches (0/4) — dead lever | `G-SNE-STRICT-OVERDECLINE` |
| **A speed ladder lives in COMPILE FLAGS, not just code (2026-07-02)** | the engine's standard `build-cpu` math-core libs compile WITHOUT `/openmp /arch:AVX2` → any binary linking them silently loses the brick-4/5/6 qwen36 ladder (served 35B ran 3×-slow; CPU-only A/B = 0.17 tok/s = exactly the pre-OMP rung). Perf-critical exes must link `build-cpu-perf` (+ LLVM `libomp.lib` — MSVC 14.29's lacks `__kmpc_dispatch_deinit`). Two enums trap in the same campaign: L1 wire `arch_id` (QWEN36=**8**) ≠ internal `sp_arch_t` (QWEN36=4). | `G-QWEN36-SERVE` |

## 4. Substrate constants (the exact-integer container)

| constant | value |
|---|---|
| dual-prime CRT-NTT primes | `q1 = 1073738753`, `q2 = 1073732609` |
| CRT modulus | `M = 1152908312643096577` (≈2⁶⁰, fits u64 ⇒ no `__int128` in the ring) |
| O_K | `Z[(1+√−163)/2]` (class number 1) |
| content-hash period (C2/Ring-3 ↔ global layers) | **6** |
| C2 signature | **256-bit** (Rademacher ±1 projection router) |
| Ring-3 VSA dimension | `D = 1024` (two 512-blocks); superposition CAP = **32** |
| byte-exact forward | `SP_BYTEEXACT` (default-off = byte-identical null floor); 4 nonlinear islands (RMSNorm/softmax/GELU/RoPE) on the same CRT-NTT | `G-BYTEEXACT-FORWARD-12B`, `69c0588` |
| MEM-OKF address classes | **content-addressed** = sha256(norm(body))[:16] (agent facts, tamper-evident by re-hash); **C2-addressed** = 256-bit C2 SimHash via `--addr` (episodes, not body-re-hashable; L3 Ed25519 for cross-node authenticity). Store split: 87 content / 26 c2 | `G-SWARM-REPLICATE-CONVERGE` |
| CRLF cross-platform interop | Python-on-Windows WRITES MEM-OKF as CRLF but computes addr over the LF-normalized body (text-mode read translates CRLF→LF). A Rust/other node MUST normalize line endings on read (`parse_fm` normalizes first) or every cross-node address mismatches. | `G-SWARM-RUST-PARITY` |

## 5. Test ledger (this campaign — corpus · config · outcome · receipt)

All receipts under `shannon-prime-system-engine/tests/fixtures/chat_fullstack/` unless noted; served 12B (OK_Q4B) on the RTX 2060, `wire_cuda_backend`.

| gate / test | corpus + config | outcome | commit |
|---|---|---|---|
| `G-L5-RECALL-LIVE` | 61 faithful facts, paraphrase queries, `SP_RECALL_L5` τ=0.30 | **86.89%** paraphrase obey (default-off) | `d9099cd` |
| `G-JUDGE-KSWEEP-K2` | 12 in-mem para + 12 foreign-v2, `SP_B3_JUDGE_L5` | K=1 reject broken; **K=2 = 50% recall / 17% spurious (83% clean-reject)**; recall-thru-judge is the cost, not K | `4ff75d1`, `5d336c7` |
| `G-JUDGE-REORDER-K2` | same 12/12, reorder (judge veto → L5-#1 deliver) | 50% recall / 17% spurious — preserves L5 recall, doesn't beat L5-direct+τ | `61160e9` |
| `G-L5-DIRECT-SAME12` | same hard-12 baseline | **50% recall / 8% spurious** (the hard-12 is a hard slice of the 86.89% full-61) | `61160e9` |
| `G-HARDFOREIGN-L5DIRECT` | 18 same-domain high-cosine UNANSWERABLE (general knowledge) | **0/18 spurious** — native robustness absolute | `8dbbcdc` |
| `G-HARDFOREIGN-JUDGE` | same 18, judge@K=2 | 0/18 spurious BUT judge PASSed 15/18 → judge PARKED | `8dbbcdc` |
| `G-SNE-CRUCIBLE-L5DIRECT` | **20 synthetic novel entities** (uuid ids, high-entropy override codes, 0 parametric prior; audited) | MATCH recall **20/20=100%**; MISMATCH **confab 80% / leak 5% / decline 15%** — the vulnerability | `45149a1` |
| `G-SNE-STRICT-OVERDECLINE` | SNE + `SP_RECALL_STRICT` | 0/4 match (over-declines) — STRICT rejected | `f161a27` |
| `G-SNE-ATTRGATE` | SNE + `SP_RECALL_ATTR_GATE` τ=0.5 | **100% recall + 100% decline, confab 80→0, leak 5→0** | `f161a27` |
| `G-ATTRGATE-PARA-REGRESSION` | fct paraphrase + attr-gate (no guard) | 0/12 — lexical gate over-declines paraphrase (needs guard) | `f161a27` |
| `G-SNE-ATTRGATE-GUARD` / `G-ATTRGATE-GUARD-PARA` | SNE + fct, attr-gate + query-token guard | SNE 100%/decline preserved; **paraphrase 6/12 = baseline, 0 over-decline** (globally safe) | `a4ebe3d` |
| `G-SNE-ATTRGATE-ZEROINF` | SNE + zero-inference symbolic decline | 16/16 match+decline; **all declines "no gemma4 decode"** (hallucination-immune reject) | `fc2e846` |
| `G-KSTE-MD` / `G-KSTE-MD-REALDATA` | magnitude-depth encoder + Dickson σ0⊕σ1 | 37.6× synthetic discrimination but **INPUT-GATED** (directional signal → magnitude-shape-blind on real global-Q) → honest negative | `104-109` (this session) |
| `G-SWARM-REPLICATE-CONVERGE` | 2 divergent store-dir "nodes" over the real 113-object MEM-OKF | content-address round-trip + have/want convergence (113/113 byte-identical) + verify-on-arrival + idempotence + tamper-reject; SP-SWARM L1+L2 core, transport-agnostic | lattice (this session) |
| `G-SWARM-PROVENANCE-ED25519` | Ed25519 (libsodium/PyNaCl) sign-on-write + verify-on-pull vs invite-only roster, over real MEM-OKF objects | signed content+episode commit; tampered-episode→sig-invalid, stripped→unsigned, forged→sig-invalid, unrostered→untrusted-signer, tampered-content→integrity-fail (all rejected pre-commit); C2 episodes now tamper-evident cross-node; SP-SWARM L3 | lattice (this session) |
| `G-SWARM-RUST-PARITY` | Rust `tools/sp_swarm` (sha2 + ed25519-dalek) vs pynacl-signed fixture + real store | 6/6: Rust reproduces Python addresses (89 content), ed25519-dalek verifies the pynacl signature over addr‖body, tamper+roster reject; cross-lang byte-parity | engine (this session) |
| `G-SWARM-TRANSPORT-QUIC` | 2-node localhost over quinn/rustls; Ed25519 mutual roster auth | A↔B bidirectional convergence (pull 3 / pull 2), tampered object rejected on arrival (integrity-fail), off-roster peer dropped (0 objects); SP-SWARM L0 (reused engine QUIC, not rust-libp2p) | engine (this session) |
| `G-SWARM-NODE` | 2-node localhost, `run_node` autonomous periodic sync | converge 5/5 both directions; persistent identity stable across reloads; roster file parsed; SP-SWARM integration orchestration | engine (this session) |
| `G-SWARM-DAEMON-WIRE` | `cargo build --features wire_cuda_backend,swarm` | sp-daemon builds+links with the mesh wired (19.33s); `SP_SWARM=1` spawns run_node, unset=no-op null floor; SP-SWARM daemon integration | engine (this session) |
| `G-SWARM-C2-INDEX` | synthetic near/far 256-bit sigs | C2Index find_similar top-k Hamming: near>far, exact=0, monotone, hex round-trip; L4 index mechanics | engine (this session) |
| `G-SWARM-C2-SEMANTIC` | 61 paraphrase L5 embeds → nearest episode; SimHash vs L5-cosine | C2-256 recall@1 **0.607** vs cosine 0.885 (retains 69% — weak top-1) BUT recall@5 **0.885** = cosine's top-1 (strong shortlist); bit-count lever (512/1024/2048 → 0.72/0.82/0.87 @1). L4 = hint/shortlist, not top-1 | engine (this session) |
| `G-SWARM-GOSSIP-DISCOVERY` | 2-node localhost QUIC; SIM shortlist gossip + exact-fetch verify | A discovers a B-only object via C2 shortlist → exact-fetch (accept L1+L2+L3) → converge; decoys A holds skipped; off-roster rejected; k≥5. SP-SWARM L4 network discovery | engine (this session) |

## 6. Honest negatives (levers measured inert — kept attached by policy)

- **KSTE-MD / Friedman magnitude-depth router**: 37.6× synthetic discrimination collapses on real global-Q (input-gated, directional-blind). Parked as a dedup/eviction primitive, OFF the recall path.
- **C2-256 SimHash as a TOP-1 retriever**: 0.607 recall@1 (retains only 69% of L5-cosine 0.885) — honest-negative for standalone discovery. VIABLE only as a top-k shortlist→exact-fetch hint (recall@5 0.885, its designed §6 role). Boundary thesis again: the quantized structure-on-content signal is a hint, not the answer.
- **Query-side foreign reject** (L5 / Jaccard / margin thresholds): ~90% false-accept on clean-v2 foreign — cheap query-side signals cannot reject; the model's robustness + τ do.
- **Generative judge** (SP_B3_JUDGE): 0 benefit over L5-direct+τ on hard-foreign, PASSes 15/18 → PARKED.
- **STRICT closed-book prompt**: over-declines valid matches (0/4) — dead lever.
- **Shared-token attribute guard** (query∩fact): broke SNE decline (2/6) on wrong-entity delivery → replaced by the query-token guard.
- **Fused latent+text** (Telepathy precise channel): 0.000. **CRT multi-device**: loopback-only (resolved-negative pending 2-GPU). **Möbius/entropy-coding on M / T2-Möbius embedding**: measured-inert (see STATE boundary thesis).
- **T4 Frobenius π^k of the model WEIGHTS as a compression lever** (`G-T4-WEIGHTS`, 2026-07-01): REDUNDANT vs OK_Q4B. On 3/3 real 12B tensors, OK_Q4B (per-32-block int4+f16, **4.5 eff bits/w**) = relL2 0.10–0.12; the Frobenius "free" per-tensor scale at 4 b/w = 0.40 (**~3.3–4× worse to save 0.5 bits**), per-row 0.21–0.28; matching fidelity needs the scale back at per-block (== OK_Q4B). The free-scale property that holds on Ring-2 EPISODES (`G-R2-FROB`, sub-ULP@24b) does **not** transfer to trained weight tensors (per-block outliers). Refutes T4-as-weight-compression, NOT the T4 exact-*cancellation* property (needs Q8, buys auditability). Scope+receipt: `PPT-LAT-T4-WEIGHTS-SCOPE.md`, engine `tests/fixtures/t4_weights/G-T4-WEIGHTS.log`. Boundary thesis extended to the weights (as T2 was).

## Cross-links
- Law + architecture: [PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md](PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md)
- What is built + open: [VERIFIED-SCOREBOARD.md](VERIFIED-SCOREBOARD.md)
- Proven ledger (full detail): [PPT-LAT-STATE.md](PPT-LAT-STATE.md)
- Swarm/DHT primary axis: [PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md](PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md)
- MEM-OKF banked findings (hashed, gisted): `memory-okf/` (`python tools/okf_mem.py lookup --root memory-okf "<keyword>"`)

*Banking discipline: durable findings here are also banked to MEM-OKF (content-addressed, SHA-hashed, gist+full tiers) so they are anti-rebuild-searchable. This doc is the human-readable flat index; MEM-OKF is the hashed store.*
