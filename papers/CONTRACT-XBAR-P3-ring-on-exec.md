# CONTRACT XBAR-P3 — ring-on-Exec: the two-ring + recall router + episode replay on the gemma4 CUDA decode

**Parent:** RFC-XBAR v1 §3/§3.1 (ring hierarchy + design rules) + §5 (P3 row); CONTRACT-XBAR-C1-lite §3b (the P3 pre-flight audit; gates G-P3-GEOM / G-P3-SHARED / G-P3-WIN named there) + its run-record (geom substrate landed, core `64b698c`, T_ARM_GEOM 26/26); CONTRACT-C2 §C2.1 (the gate vocabulary: parity-when-off, NIAH G1, PPL-deflection G2). **Status:** **RATIFIED (operator, 2026-06-11)** — the staged plan, the five gates, the host-side-router-v0 decision, the 12B/E2B gate split, the prefix-sum episode law, and the named deferrals (G-P3-WIN / CUDA-graph ring exec / device router / Spinor-coded spill) are the agreed law. Build-ready when sequenced (queue #5, behind horizon → Fork-3 → InfoNCE). Contract-before-code — code may now ship per-stage against these gates; any need discovered outside this spec amends the contract first.
**One line:** port the proven qwen3-CPU two-ring (Ring 1 sink+window, Ring 2 spill/recall through the registered-backend ABI, the ±1 Rademacher recall router, the `SP_REPLAY` episode seam) onto the **Exec** — `gemma4_decode_cuda` — per-layer-class geometry-aware (G-P3-GEOM) and shared-KV owner-indirect (G-P3-SHARED), null-first, bit-exact-when-off.

---

## 1. Scope & non-goals

**P3 is the ring WIRING on the Exec, nothing else.** The Exec path is `gemma4_decode_cuda` (`shannon-prime-system-engine/src/backends/cuda/cuda_forward.cu:1634`), the ETA.5a/5b decode with the jagged per-owner KV cache. The reference being ported is the qwen3 CPU wiring in `core/forward/decode.c` (projk sidecar build at decode.c:470-480, `sp_arm_select` sites at decode.c:608-623, Ring-2 spill setup at decode.c:339-391, `SP_REPLAY` injection at decode.c:457-468) — that path is the PATTERN and stays UNMODIFIED. The geom substrate is already landed and gated (core `64b698c`: `sp_arm_geom` descriptor + `sp_arm_geom_layout` + `sp_arm_project{,_sig}_geom` / `sp_arm_select{,_sig}_geom`, `include/sp/arm.h:129-192`; legacy entry points delegate, uniform-null bit-exact, T_ARM_GEOM 26/26). P3 consumes that API; it does not extend it.

**Substrate precondition.** Development runs against the **12B B1 artifact** (OK_Q4B per-32, the 06-R10 gold instrument: 24/24 gates, PPL 5.12, 26.1 tok/s on the 2060-12GB) as the Exec, and the **E2B** artifact for cheap gates wherever a stage doesn't need 12B-class capacity. The two artifacts split the gate load by construction:

- **12B** (NL=48, period 6 → 8 global / 40 SWA; CONTRACT-XBAR-P1 §1): every layer owns its K/V (the dense artifact carries no shared-KV; P1's CAPTURE of all 48 per-layer rows is the receipt). The 12B exercises **G-P3-GEOM** (jagged classes, V-less globals) at real capacity.
- **E2B** (NL=35, period 5, **kvfs=15** → 15 owners / 20 sharers; SESSION-CLOSED-stage-eta-phase1 finding 3-4): the only artifact in hand with real sharer layers. The E2B exercises **G-P3-SHARED** (owner-indirection, owner-map manifest) cheaply.

Every run banner echoes its geometry from the loaded config (`kvfs`/`period`/per-class dims), never from prose — the banner-echoes-getenv rule extends to geometry.

**Non-goals (each owned elsewhere):**
- NOT the trained Memo / learned curator — that is C2 (the P2.b adapter lane), currently adapter-limited per the k-sweep verdict.
- NOT NIGHTSHIFT (N1) — the offline schtasks loop composes on P3's persisted episodes but is its own contract.
- NOT multi-writer permissions on Ring 2/2′ — the RFC §8 named gap stays open; Exec is the sole writer here.
- NOT Spinor-lossy KV on the Exec — v0 rings carry the f32 cache bytes (the CUDA cache is f32; the Spinor overlay is a later, separately-gated knob, as it was on qwen3).
- NOT G-P3-WIN (ring-window × model-SWA interaction, global-vs-SWA recall policy) — explicitly DEFERRED to a follow-on stage after P3.4; v0 recall treats the budget uniformly per layer and the SWA window stays the model's own (audit row #4 stands as an open, lower-risk item).
- NOT CUDA-graph-path ring execution — see §4 risk 1; v0 ring work lives on the per-step path only.

## 2. Staged plan — one gate per stage, null first

| Stage | What | Gate (its own metric) | Falsification (pre-stated) |
|---|---|---|---|
| **P3.0 — episode/owner-map manifest** | The G-P3-SHARED data structure, spec'd before any decode wiring: per-layer-class geometry descriptor + own-vs-shared skiplist + owner indirection + per-owner episode offsets (schema below). Implemented as a header + serializer gated standalone (the curator_replay.c discipline — no model, no decode). | **G-P3-0 (manifest null + determinism):** round-trip byte-exact; on UNIFORM geometry (qwen3 dims) the manifest-driven offsets reproduce the legacy `((L*P)+pos)*KVD*4` layout exactly (the T_ARM_GEOM uniform-null pattern); on E2B dims the offsets match a brute-force prefix-sum oracle. | Any manifest-driven offset differing from the legacy layout on uniform geometry, or from the oracle on jagged. |
| **P3.1 — recall router on the CUDA decode** (the G-P3-GEOM wiring half) | **a) shadow router:** mint the geom projk sidecar HOST-side from D2H-copied post-RoPE owner K (mint site cuda_forward.cu:2147-2155); run `sp_arm_select_geom` host-side per query head; LOG the recall sets, gate NOTHING into attention yet. **b) gated attention:** apply the recall set via an index-list attention kernel (`k_attn_decode_gather`, the `k_attn_decode_win` variant taking H2D'd `ri[m]`). Knobs `SP_ARM_B/W/SINK/R` in the SP_XBAR_* seam style (env-gated, additive, banner-echoed — cuda_forward.cu:1712-1788 is the precedent). | **G-P3-GEOM.a:** shadow-router selections IDENTICAL to the CPU `sp_arm_select_geom` oracle fed the same D2H'd K (same floats ⇒ same sets; the arm.h:117-127 exactness-contract discipline), AND knobs-unset decode bit-identical (both per-step and graph paths). **G-P3-GEOM.b:** knobs-off bit-exact floor re-proven; then NIAH-style needle on the **12B** at modest N (N=2k, depth-sweep per C2.1 G1) with B ≪ N: retrieval parity with full attention. #115 closed ⇒ real-prompt needles, not fixtures. | a: any selection mismatch vs the CPU oracle, or any off-path divergence. b: needle MISS at a B where full attention HITs (router loses information), or parity break when off. |
| **P3.2 — Ring 2 spill/recall, owner-indirect** | **a) shadow spill:** every step, D2H the minted owner K/V row and spill via the **registered-backend ABI** (`sp_arm_ring2_backend`, arm.h:211-256 — Optane engine backend or stdio reference, unchanged); jagged cache stays full (no behavior change). Sharer layers spill NOTHING (skiplist). **b) recall + Ring-1 shrink:** evicted positions served from Ring 2 through owner-indirect reads (`own[L]` from the P3.0 manifest); device cache shrinks toward sink+W per owner. | **G-P3-R2.a (byte identity):** every spilled block byte-identical to a post-run D2H of the corresponding `dKc/dVc[own[L]]` row, on 12B AND E2B (sharer rows must never appear in the store). **G-P3-R2.b:** needle HIT served off disk (the C2.1 Optane pattern) + knobs-off parity. | a: any spilled byte differing from the device cache, or any sharer-layer block present. b: needle MISS off disk where P3.1b HIT from RAM. |
| **P3.3 — `SP_REPLAY` on the Exec** (the G-P3-SHARED replay half) | The decode.c:457-468 injection ported to the cache-store seam: for `pos < SP_REPLAY_NPOS`, H2D the episode block (L,pos) over the freshly minted row before `cudaMemcpyAsync`/`k_kv_store` lands it (cuda_forward.cu:2154-2155 / 1959), owner layers only; sharers follow by construction (`Kuse = dKc[src]`, cuda_forward.cu:2157-2160). Episode loaded read-only (`sp_arm_ring2_stdio_open_ro`, arm.h:243). | **G-P3-SHARED (replay null on a shared-layer episode, E2B):** intact replay ⇒ generated sequence **bit-identical** to baseline (the f32 store is lossless — the T_GENKV_REPLAY_NULL standard); zeroed episode ⇒ DIVERGES; `SP_REPLAY` unset ⇒ bit-exact floor. The E2B arm proves owner-indirection end to end: replay touches 15 owner rows, all 35 layers' attention reproduces. | Intact-replay divergence (injection corrupts), zeroed-replay identity (injection is a no-op), or any off-path drift. |
| **P3.4 — PPL deflection gate** | The C2.1 G2 instrument on the Exec: teacher-forced NLL via the existing `SP_G4_SCORE` path (cuda_forward.cu:1705-1711, 2230-2274 — forces per-step, which is where the ring lives anyway), gold-instrument 12B artifact. `deflection(N,B) = PPL[ring+recall@B] / PPL[ring-off] − 1` at pinned ratios (B=N full-recall floor first, then B≪N). | **G-P3-PPL:** deflection **< 2%** at the pinned ratios (the C2.1 G2 bound). Möbius sinks admitted as a lever if the bare router misses the bound (they are part of the proven C2.1 recipe, not a silent gate revision). | Deflection ≥ 2% with sinks already applied ⇒ surface UPSTREAM (per the no-silent-gate-revisions rule), do not tune fixtures. |

**Deliberately deferred beyond P3.4:** G-P3-WIN (window-interaction recall policy per class), CUDA-graph re-capture with ring knobs on (perf), device-side router minting (below), Spinor-coding the spilled blocks, int8/int4 router quant (the C2.1 projk-RAM item — moot at v0 sizes, see §4).

### P3.0 manifest schema (normative)

Episode = `{K store, V store, manifest}` (the C1-lite/N1 format, extended). Manifest fields:

- header: magic/version, artifact sha, projection seed version (`SP_ARM_PROJ_SEED`, arm.h:47-49), `NL`, `P`, `period`, `kvfs`, `r`;
- per-layer record `[NL]`: `class` (GLOBAL/SWA), `nh`, `nkv`, `hd`, `kvd = nkv*hd`, `rope_base`, `has_freq_factors`, `window` (−1 global / SW), `owns_kv = (L < kvfs)`, `own[L]` (= `L` for owners; `kvfs−1` global / `kvfs−2` SWA for sharers — gemma4.c:198-202, bounds-guarded core `c608b2f`), `vless` (attn_v absent ⇒ V = weightless-normed raw K proj — gemma4.c:179-187), `off[L]` (per-owner episode byte offset, prefix-sum law in §3).

projk is NOT serialized — rebuilt by re-projection from the stored K (the C1L.0a proven property), now via `sp_arm_project_geom` per class.

### Host-vs-device router: the v0 decision (recommended: HOST)

Post-RoPE K exists only on DEVICE: the per-step path mints `dk` → `k_rmsnorm_head` → `k_rope_*` → `cudaMemcpyAsync` into `dKc[L]` (cuda_forward.cu:2147-2155); the graph path uses `k_kv_store` with device `dpos` (cuda_forward.cu:1959). Two ways to get a router:

- **HOST v0 (chosen):** D2H the minted K (and the roped q) per step, project + select with the SAME `core/arm` code the CPU gates already proved (T_ARM_GEOM 26/26) — zero new router math, the CPU oracle is the parity twin for free. Cost: K = 48·512·4 B ≈ 96 KiB + q ≈ 48·2048·4 B ≈ 384 KiB ⇒ ~480 KiB/step D2H + per-step syncs ≈ low-ms; against the 12B's 38.3 ms/step (26.1 tok/s, 06-R10) that is a single-digit-% v0 tax on a gate lane. Per-step path only.
- **DEVICE (deferred):** a `k_arm_project` kernel + device top-k. New CUDA math ⇒ needs its own exactness gate (identical cand arrays, the `sp_arm_scan_sig` override contract, arm.h:117-127). This is the perf pass, not the correctness pass; do it only after G-P3-PPL is green host-side.

## 3. Geometry law (the §3b audit table, normative form)

Ground truth, line-cited: per-layer class `global = (L % period == period−1)` (gemma4.c:148, cuda_forward.cu:2130); 12B GLOBAL = nh 4 / **nkv 1 / hd 512**, RoPE 1e6 + proportional freqs, full attention; SWA = nh 8 / **nkv 2 / hd 256**, RoPE 1e4, sliding window (gemma4.c:70-71,149-157; CONTRACT-XBAR-P1 §1). Owners `[0,kvfs)`; sharers reuse `kvfs−1` (global) / `kvfs−2` (SWA) and mint nothing (gemma4.c:174,197-204; cuda_forward.cu:2146-2160).

| Transfers **as-is** (12B) | Is **per-class** (manifest-carried) | Is **owner-indirect** (sharer layers) |
|---|---|---|
| Episode block layout `((L*P)+pos)*KVD*4` with **KVD = 512 constant** (global 1×512 = SWA 2×256; gemma4.c:16,79 — audit finding #1). The `SP_REPLAY` injection discipline (overwrite minted K/V pre-store, post-RoPE, query untouched). The Rademacher R built once at `hd_max = 512` (the arm.h:139-145 R-sizing contract). | projk strides + offsets (`sp_arm_geom_layout`, heterogeneous per-layer blocks `P*nkv*r`); select NKV/HD per class (`sp_arm_select_geom` descriptor); RoPE base + freq-factors and the attention window (capture metadata — needed to interpret an episode, not to address it). | **Spill**: sharers write nothing (skiplist). **Recall**: reads address `own[L]`'s store/projk block. **Replay**: injects owner rows only; sharer attention follows because `Kuse/Vuse` alias the owner buffer by construction. |

**The E2B caveat (new in this contract — the constant-KVD layout does NOT transfer there):** the jagged cache is genuinely jagged on the E2B — global owners write 512-wide rows, SWA owners 256-wide (cuda_forward.cu:1615-1617, alloc at 1817-1822 computes `kvd` per class). The normative episode addressing is therefore the **prefix-sum law**:

```
off[L]            = Σ_{L' < L, owns_kv(L')} P · kvd_{L'} · 4      (owners only)
block(L, pos) at    off[own[L]] + pos · kvd_{own[L]} · 4
```

On the 12B (all owners, kvd ≡ 512) this degenerates exactly to `((L*P)+pos)*512*4` — the C1-lite layout, byte for byte. P3.0's gate holds the degeneration as the uniform-null.

### projk sidecar sizing (computed from the real 12B dims)

Per-layer f32 projk block = `P·nkv·r` floats (arm.h:147-154). 12B: Σ_L nkv = 8 global·1 + 40 SWA·2 = **88** kv-head streams ⇒ total = `88·P·r` floats = `352·P·r` bytes:

| P | r=32 | r=64 |
|---|---|---|
| 2048 | 352·2048·32 = 23,068,672 B ≈ **22.0 MiB** | 44.0 MiB |
| 4096 | 46,137,344 B ≈ **44.0 MiB** | 88.0 MiB |
| 8192 | 92,274,688 B ≈ **88.0 MiB** | 176.0 MiB |

Sig (bit-packed) sidecar = `88·P·8` B = 704·P: 1.4 / 2.8 / 5.5 MiB at the same P — the gated lossier overlay, same admission rule as ever (re-pass NIAH + deflection per regime). v0 keeps projk HOST-side (router decision above), so this is RAM, not VRAM; if the device router lands later the same bytes move on-card and remain negligible against the cache (next).

## 4. Risks

1. **CUDA-graph capture vs per-step ring branches.** The ring needs host work (or at minimum data-dependent indices) inside the step — incompatible with the captured graph. Precedent: the X-R1/XBAR seam already declines the graph when knobs are set (`use_graph = … && !xbar_on`, cuda_forward.cu:1840). **Accepted for v0:** `SP_ARM_*` set ⇒ per-step path, graph declines, banner says so; knobs-off must re-green BOTH paths bit-exact. Graph re-capture with ring on (e.g. fixed-budget gather kernels with device-resident indices) is the deferred perf stage.
2. **VRAM budget on the 2060-12GB.** Weights ≈ 6.4 GB (OK_Q4B per-32) ⇒ ~5 GB headroom. Jagged K+V cache = `2·48·512·4·P` = 196,608·P B: **384 MiB @ P=2k, 768 MiB @ 4k, 1.5 GiB @ 8k** — fits with room at every gate point; P=32k (6 GiB) is out of v0 scope and is exactly what P3.2b's Ring-1 shrink is for. projk stays host-side (≤ 176 MiB RAM, table above) — VRAM-neutral in v0.
3. **Host-device sync per step.** ~480 KiB/step D2H + syncs on the router lane, ~192 KiB/step on the spill lane (owner K+V) — low-ms against 38.3 ms/step; single-digit-% tax, diagnostic-lane precedent (the XBAR ranks telemetry already syncs per step, cuda_forward.cu:2293-2296). If measured worse than ~10%, batch the D2H per step (one staging buffer, one copy), don't redesign.
4. **#115-closed dependency (enabling, not blocking).** Tokenizer parity 5432/5432 both lanes + ROUNDTRIP 60/60 means P3.1b/P3.2b needles run on REAL prompts, not fixtures. Run-prep: 12B text-in needs the gold-blob `--tok-only` regen first (night-shift 06-10 note).
5. **V-less globals on the 12B (corrects §3b finding #5's resolution).** The audit declared "no V=K aliasing — SP projects V via attn_v for both classes"; that holds for the E2B-class artifact but NOT the 12B: dense gemma-4 globals ship no `attn_v`, and both forwards implement the V-less fallback — V = raw K projection, weightless-normed, never roped (gemma4.c:179-187; cuda_forward.cu:2148-2149, also 1878-1879/1953-1954; CONTRACT-XBAR-P1 §1 table). **Episode format is unaffected** (V blocks store the minted V bytes whatever their provenance, and replay injects K+V as a pair), but the manifest carries `vless` per layer and any future re-mint/re-rope tooling must NOT re-derive V from post-norm K on globals. No new gate; a law line so nobody re-trips the eta-5b confusion.
6. **Mixed-artifact gate drift.** G-P3-SHARED greens on the E2B; the 12B never exercises owner-indirection (all owners). Stated plainly: a 12B-only green is NOT shared-KV-ready, and an E2B-only green is NOT 12B-capacity-ready. Closure requires the per-stage artifact assignments in §2 as written.

## 5. Run-record

*(receipts land here as stages close; format: gate name, artifact, commits, counts, verdict)*

| Date | Stage / gate | Artifact | Receipts |
|---|---|---|---|
| 2026-06-11 | **P3.0 — G-P3-0** (manifest null + determinism) | qwen3-uniform + 12B + E2B fixtures (no model) | **PASS**. New module: `include/sp/xbar_episode.h` + `core/xbar/xbar_episode.c` + standalone gate `tools/curator/xbar_manifest_gate.c` (system `9a2b0a9`, MinGW gcc 15.2 `-Wall -Wextra` clean). Three checks all green: (1) round-trip serialize→deserialize→serialize **byte-exact** + record-field-identical on all 3 fixtures; (2) uniform-null — qwen3 (NL=28, all owners, KVD=1024) reproduces `((L*P)+pos)*1024*4` and the 12B (NL=48, all owners, KVD const 512 = global 1×512 == SWA 2×256) reproduces `((L*P)+pos)*512*4`, **exactly**; (3) jagged — E2B (NL=35, period 5, kvfs=15 → 15 owners/20 sharers, global 512 / SWA 256 owner rows) every `block(L,pos)` matches an INDEPENDENT brute-force prefix-sum + owner-indirection oracle (own[L], owns_kv, off[L], store_bytes all agree). Falsification (offset ≠ legacy on uniform, or ≠ oracle on jagged) not triggered. projk NOT serialized (re-projected from stored K, C1L.0a). Standalone (curator_replay discipline) — no decode wiring; P3.1 consumes this manifest. |
