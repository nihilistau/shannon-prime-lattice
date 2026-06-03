# CONTRACTS C4 / C5 / C6 — decisions captured (stubs; detailed design DEFERRED)

**Parent:** RFC-001. **Status:** decision-capture stubs, NOT full contracts. **Deliberate scope limit:** detailed L1-ABI/daemon state machines are **deferred until C1/C2 prove the substrate** (the project's failure mode is architecting unbuilt pillars ahead of the measured base). This file exists so the *decisions* below are not lost (anti-amnesia), not to design the machines now.

Source: critique of a Gemini synthesis directive, 2026-06-02. Where Gemini over-reached, it's corrected here.

---

## C4 — MTP as a transactional rollback protocol

**Approved frame:** draft → verify → **byte-exact integer accept** (not a probability spread) → lossless rollback on reject. NextN block (or `-Draft` model) is the draft head; one batched target forward verifies.

**THE SEAM DECISION (answers "Spinor ABI vs daemon host-memory?"):** *layered, copy-free.*
- **Spinor block = the commit unit + integrity boundary.** The 0xA5-sentinel cache-line is already canonical + checkable; "known-good state" = the committed Spinor blocks. The ABI provides the addressable boundary, not the protocol.
- **Daemon owns the transaction as an epoch/watermark over the Spinor ring**, NOT a host-memory snapshot. Speculative blocks are written *past the committed watermark*; **commit advances the watermark; abort resets the watermark pointer — no copy, no restore.** A full host snapshot/restore would defeat the compression + pay the bandwidth tax the architecture exists to avoid.
- Composes with Ring-2: committed blocks may spill (Optane); speculative blocks stay Ring-1 until commit.

**Corrections to the Gemini draft:** "draft in a q₁ sub-ring" is a `[SPECULATIVE]` optimization (cheaper single-prime draft), not load-bearing — do not bake it in. "Speculative polynomial evaluation" is metaphor; the mechanism is draft/verify/commit/rollback.

**[DESIGN]** (protocol) / **[PROVEN]** (Spinor ABI + transactional-rewind primitive). **Gate (future):** 100-step decode with speculation produces bit-identical output to non-speculative decode (proves rollback is lossless), at K=4 draft depth.

**[MEASURED 2026-06-04, engine `b602ddf`]** — `tests/sp_toks.c SP_MTP=1` on Qwen3-0.6B-f16. Prompt-lookup draft (NG=2) → ONE batched `qwen3_forward` verify → byte-exact greedy argmax accept → corrected token → O(1) advance. N=48 decode steps, draft depth K=8:
- `greedy_forwards=48  mtp_forwards=18` → **2.67× fewer forward passes**
- `mean_accept=1.78/8` per verify
- `bit_identical_to_greedy=1` — **the rollback-lossless gate is met** (ran at K=8, exceeding the K=4 future-gate spec)

**Batched-forward ceiling** (`SP_MTP_CEIL`): K=8 in one pass ≈ 19.83 ms/token vs 33.97 ms/token at K=1-per-token → **1.71× weight-read amortization** ceiling.

**[REALIZED 2026-06-04, engine `145bf43`]** — `qwen3_mtp_forward` (persistent-KV batched append-forward) + `qwen3_mtp_decode` (prompt-lookup draft → KV-reuse verify → byte-exact accept → O(1) watermark advance). Run on the **production swivel path**: `qwen3_rt.sp-model` loaded via `sp_model_load` → `sp_model_to_qwen3` (OK_Q8 packed arena, `gguf==NULL`, **zero quant inflation**). 96-token decode, K=8 / NG=2, vs K=0 incremental-KV greedy on the *same* arena substrate:
- greedy(K=0): 96 tok / 4.240 s = **22.64 tok/s** (96 forwards)
- MTP(K=8):   96 tok / 2.407 s = **39.88 tok/s** (34 forwards, mean_accept 1.94/8)
- **1.76× wall-clock speedup**, `bit_identical_to_greedy=1`, forwards 96→34 (2.82× fewer)

The KV-reuse verify is realized — the forward-count reduction now turns into wall-clock because each verify reuses the cached prefix K/V instead of re-prefilling. Gate (`tests/sp_toks.c SP_MTP_KV=1 SP_TOKS_SP=qwen3_rt.sp-model`).

**OPEN (production-daemon integration):** this is the engine CPU *reference* path with a self-contained dense cache. The daemon's transactional speculation should compose this with the frozen `sp_session_clone` / `sp_session_rewind` primitives (`lib/shannon-prime-system/core/session/sp_session.c`) — the epoch/watermark-over-Spinor-ring design above — so rollback is the watermark reset, not a buffer free. MTP × Ring-2/recall/fuse also compose later (the reference path is plain f32 only).

**OPEN:** byte-exact accept under temperature>0 (needs a discretized-sampling contract); watermark granularity (per-block vs per-layer-block).

---

## C5 — MeMo as a commutative Z_q receipt ledger

**Approved frame:** base frozen Z_q weights never change; learning/context = **commutative, associative additive Spinor receipts** (order-independent); a memory profile = a file of receipts, **algebraically fused at Frobenius-lift load** into the arena; peer-shareable byte-exactly over the mesh (a Ring-2 tenant). Portable without shipping weights.

**Load-bearing caveat (keep `[SPECULATIVE]`):** "useful learning = commutative additive low-rank Z_q delta" is unproven. If real continual-learning signal needs non-commutative/ordered composition, the elegant load-time-fusion story weakens. **Gate before believing:** a concrete task measurably improves via fused receipts, reproduced bit-exactly, before C5 promotes past `[SPECULATIVE]`.

**OPEN:** receipt format (rank/scale/provenance hash) as a frozen field; load-time fusion vs runtime overlay (cf. KSTE-KV overlay); relation to agent-level two-tier memory (same mechanism or analogue?).

---

## C6 — The cyclotomic ring paper (honest)

**Approved frame:** R_q = Z_q[X]/(X^N+1) is the bounded, composable computational universe — the reason an H100, an M4, and a Hexagon DSP produce the same bits. Continuous LLM probabilities map to discrete polynomial coefficients; fp is non-compute plumbing only.

**MUST carry these `[PROVEN]` constraints or it re-hypes:**
- **N ≤ 512** with the frozen primes (2N | q−1; both primes v₂(q−1)=10). N≥1024 is a Phase-5 third-prime cascade, not a flag. Long ctx ⇒ tiled N=512 or Bluestein (≤512).
- **NTT is NOT faster than fp32 dot at HD ≤ 256** (measured 0.15–0.72×). The win is over HD (poly length), not ctx. Speed comes from compression + bandwidth-bypass + integer pipes + multi-device, not NTT-per-op.
- Per-backend NTT-vs-Barrett-direct crossover differs (HVX vrmpy / AVX VNNI / CUDA dp4a) — the paper must state where each wins.

---

## φ-fabric correction (applies to C2/C4 routing)

Gemini's "route CPU/GPU/NPU via Beatty" **over-reaches.** A Beatty/Rayleigh partition cleanly cleaves the integers into **exactly two** sequences (φ, φ²). **k-way (3+) Beatty partition is a hard open problem (Fraenkel).** Honest scope: **Beatty for 2-way island splits (and 2-way KV/expert sharding); k-way islands route via CRT-residue (mod k) or another construction — NOT Beatty.** Use the right tool per arity.

---

## Disposition

These three contracts are **parked at decision-level** until C1 (`.sp-model` reducing container) and C2 (Spinor-KV two-ring, where the ~120× and the regime split get *measured*) are built. Detailed L1-ABI surfaces + the daemon state machine are drafted **after** the substrate they orchestrate is proven, not before. The decisions above are the durable part; the machines wait.

**Update 2026-06-03 — the substrate is now proven.** **C1 is CLOSED** (reducing `.sp-model`, output-lossless top-1) and **C2.1 is wired live + measured** (two-ring memory: 910× resident KV @32k, needle off physical Optane @7.57 µs/read, 8×@+0.69% PPL, fusion). So **C4 (MTP) unparks as the P2 lead** — its Spinor-journal watermark/epoch protocol can now be designed against a measured base, composing with P1 SPEED. C5 (MeMo) and C6 (cyclotomic paper) stay decision-level until their own gates ([SPECULATIVE] continual-learning signal for C5; the NTT crossover paper for C6). The decisions above remain the durable part.
