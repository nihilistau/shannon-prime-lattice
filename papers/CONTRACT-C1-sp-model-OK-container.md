---
type: contract
title: CONTRACT C1 — `.sp-model` v1 + the O_K container (the REDUCING artifact)
description: "Parent: RFC-001. Status: ✅ CLOSED 2026-06-03 — all C1 gates green on 2 archs (gemma4 OK_Q8 + qwen35moe OK_Q4)."
tags: [contract]
timestamp: 2026-06-03T10:13:47Z
resource: shannon-prime-lattice/papers/CONTRACT-C1-sp-model-OK-container.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# CONTRACT C1 — `.sp-model` v1 + the O_K container (the REDUCING artifact)

**Parent:** RFC-001. **Status:** ✅ **CLOSED 2026-06-03** — all C1 gates green on 2 archs (gemma4 OK_Q8 + qwen35moe OK_Q4). The reducing loader is now public as **Position Is Arithmetic paper 02** (repro green, 6/6 E_FMT gates).
**One line:** the offline converter produces a discrete model artifact that is **≤ the source quant on disk**, carries **one canonical object (O_K)** every backend reads identically, and defines the **runtime-expansion contract** by which the loader lifts that min-entropy body into Ring-1's ALU-adapted compute container.

> Anchor (RFC-001 §3, STATE §5): the converter **REDUCES** size. Inflating a Q4_K source to OK_Q8 (1 byte/weight, ~35 GB) is the wrong-direction artifact that disk-blocked qwen35moe. C1 makes "reducing" a *gated invariant*, not an aspiration.

> **CLOSED 2026-06-03 — gate results.** **C1_REDUCTION:** qwen35moe 16.33 GB ≤ 19.7 GB Q4_K source (~17% smaller); gemma4 OK_Q8 ≤ source; Qwen3-0.6B-f16 1,439 → 720 MB (50%). **C1_ROUNDTRIP_TOP1:** top-1 bit-exact to GGUF-direct on both archs (qwen35moe `5444`). **C1_ARENA_EXPERT + C1_ZERO_INFLATION:** green. Engine `66ccab9`; gates `qwen36_spmodel_top1` / `E_PARITY_2` + the engine `E_FMT_4`/`E_FMT_4_QWEN3` closure gates (Position paper 02 `EXPECTED.md`). **Open follow-up (not a gate):** true sub-Q4 via shared-scale / Spinor structure — the headline ratio question, carried into C2/§5.

---

## C1.0 Invariants (violating one fails the contract)

- **I1 — Reduction.** `sizeof(.sp-model) ≤ sizeof(source GGUF)` for the same weights. Target: meaningfully smaller (sub-source via shared scales / Spinor structure), never larger.
- **I2 — O_K one object.** Exactly one canonical discrete representation per tensor. No backend holds a different numerical truth (zero-inflation invariant).
- **I3 — Round-trip correctness.** `transcode → sp_model_load → forward` is **top-1 bit-exact** to the GGUF-direct forward (which is itself oracle-gated). This is the closure gate, not a size number.
- **I4 — Min-entropy on disk; expansion in cache.** Disk holds the object near its source entropy. Any 8-bit/ALU-adapted container is built **at load, in RAM/VTCM**, and any spare bits carry **distinct compute-useful info** (never a redundant copy of the same weight). Spare-bit schemes ship only if their per-element mask cost is *measured* to net-win.

---

## C1.1 Default codec by source quant (decision)

| Source GGUF quant | `.sp-model` body codec | Rationale |
|---|---|---|
| Q8_0 (e.g. gemma4-E2B) | **OK_Q8** (Frobenius Q8 + per-row scale) | ≤ source; already proven (M_GEMMA4) |
| Q4_K / Q4_K_M (e.g. qwen35moe) | **OK_Q4** (Frobenius Q4 + per-row scale) | ≤ source; OK_Q8 here INFLATES — banned by I1 |
| F16 | OK_Q8 or OK_Q4 (operator-chosen) | reduces from 16-bit |

**Rule of thumb:** codec bit-width ≤ source bit-width. The current transcoder hardcodes Q8 packing (`sp_frob_pack_tensor(..., 8, ...)`); C1 makes the bit-width a function of the source (or an explicit flag), defaulting to **match-or-reduce**.

---

## C1.2 On-disk format (extends the existing `.sp-model` v0)

Already in place (reuse): header + magic + `file_size`; `sp_tensor_entry` (name, dtype_id, n_dims, dims[8], offset, size); `sp_arch_info` 256-byte `arch_struct` (q36 tail + `SP_ARCH_ID_QWEN36=8` already landed, core `d0d4269`); `.sp-tokenizer` + SHA. **Per-row Frobenius `.scale` sibling** stored adjacent (existing add_q8 pattern).

New for C1:
- **Codec tag per tensor** = `SP_DT_OK_Q4` | `SP_DT_OK_Q8` (so the loader knows the body width without guessing).
- **Rank-3 expert tensors** `[cols, rows, n_expert]` packed as `(rows*n_expert)` contiguous Frobenius rows (already implemented in the engine transcoder `add_q8`, engine `3c5f370`); the bridge slices expert `e` = rows `[e*rows, (e+1)*rows)`.
- **(DESIGN) runtime-expansion descriptor** — a small per-tensor field declaring the cache-side container + spare-bit schema (interleaved block-scale / MoE routing / island residue). Off by default; only populated when a measured net-win scheme exists. Not required for I3.

---

## C1.3 The work (implementation tasks)

1. **Transcoder codec-by-source** — pick OK_Q4 for Q4_K/Q6_K sources (default), OK_Q8 for Q8_0. (Engine `sp_transcode`; k-quant `row_bytes` + rank-3 `add_q8` already done.) Emit the per-tensor codec tag.
2. **`sp_model_to_qwen36` bridge** (core `sp_model_bridge.c`, mirror `sp_model_to_gemma4`): const sp_model* → q36 qwen3_model with synth tensors for GDN/full-attn + rank-3 expert tensors (n_dims=3 preserved); set cfg from `sp_arch_info` q36 tail; `q36_is_recurrent` per `(i+1)%interval`.
3. **Arena-aware expert path** (`qwen36.c::expert_mm`): on the `.sp-model` path there is **no GGUF** (`m->gguf == NULL`) — `expert_mm` must read the packed **arena** expert-slice, not `gguf_tensor_data`. (GDN/attn matmuls already route through the arena-aware `sp_matmul`.) This is the catch from RFC-001 — do it before the bridge ships.
4. **End-to-end:** transcode (OK_Q4) → `sp_model_load` → `sp_model_to_qwen36` → forward → top-1 == GGUF-direct (`5444 8 198`).

---

## C1.4 Gates

- **C1_REDUCTION** — `.sp-model` byte size ≤ source GGUF byte size. Report the ratio. (For qwen35moe: OK_Q4 ≈ 20 GB ≤ 19.7 GB source? — *measure; if OK_Q4 still exceeds source, the converter must achieve sub-Q4 via shared scales, or document why ≤ is not yet met.*)
- **C1_ROUNDTRIP_TOP1** — `.sp-model` forward top-1 bit-exact to GGUF-direct (gemma4 + qwen35moe). The closure gate.
- **C1_ZERO_INFLATION** — assert no tensor's on-disk body exceeds its source row bytes (I1/I2 mechanically).
- **C1_ARENA_EXPERT** — MoE experts produce identical output via the arena path as via the GGUF path (isolates task 3).

> Disk note: OK_Q4 of qwen35moe (~20 GB) fits the current free space; OK_Q8 (~35 GB) never should have been attempted. If C1_REDUCTION shows OK_Q4 ≈ source rather than below, that is honest — record it and open the sub-Q4 (shared-scale / Spinor-structured) line as follow-up; do NOT inflate to pass any other gate.

---

## C1.5 What this unblocks

The qwen35moe `.sp-model` production path (task #29) becomes runnable on local disk; the bridge + arena-expert path land tested (against the oracle, per discipline); and the **measurement substrate for C2** (Spinor KV ratio, tok/s envelope) exists — you can't measure the envelope until the on-disk object is the right, reducing one.

**Then → C2** (the ARM Spinor-KV two-ring memory contract) where the ~120× compression and the System-1/System-2 regime get *measured*, which is where the project's value thesis is proven or broken.
