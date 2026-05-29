# SESSION PLAN — lat-3-hx-mode-d-i (Sprint I — single-layer smoke)
**Date:** 2026-05-30
**Goal:** Load ONE FFN layer's `W_gate` tile from a real Qwen3-0.6B `.sp-model`, push through the existing Sprint G dual-VTCM Halide matmul kernel via `FastRpcSession` + `DmaBuffer`, verify bit-identity against the inline scalar reference at q_bits ≤ 15. Single matmul, single tile, single layer. No new memory entries; no Phase 4 scope.

---

## 0. Pre-flight (Stage 0 results)

### A. `.sp-model` location

| Path | Size | sha256 |
|---|---|---|
| `D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tests\qwen3_rt.sp-model` | 754,551,808 B (720 MB) | `30717fbd…f122376` |
| `D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cuda\tests\qwen3_rt.sp-model` | 754,551,808 B | `c3ce79af…dcaa77f` |

Both are 720 MB but the sha256 differs — content is not identical between the build-cpu and build-cuda copies (likely transcoded with different settings: arena tile size, fp16 vs bf16 norms, etc.). **Sprint I uses `build-cpu/tests/qwen3_rt.sp-model`** because that file came from the CPU-tier transcode path that the inline scalar reference at `test_hvx.rs:471-503` matches (Sprint G's bit-identity gate validated against this transcode lineage).

The upstream GGUF (for transcribe-from auditing): `D:\Files\Models\Qwen\Qwen3-0.6B-GGUF\Qwen3-0.6B-Q8_0.gguf`.

### B. Bridge regression check

Sprint G's production gates ran on-device at engine HEAD `b5a642b`. All PASS:

```
T_HALIDE_FFN_VTCM_ZEROS   PASS  (all-zero output)
T_HALIDE_FFN_VTCM_B4      PASS  via VTCM  pcyc=7,866,928
T_HALIDE_FFN_VTCM_B8      PASS  via VTCM  pcyc=15,725,256
T_HALIDE_FFN_VTCM_B16     PASS  via VTCM  pcyc=31,449,737
T_HALIDE_FFN_VTCM_B64     PASS  via VTCM  pcyc=125,803,205
```

**State note:** the test_hvx binary on-device is currently running against a `libsp_compute_skel.so` build that includes my unshipped Sprint H.PATCH (`cast<int32_t>(q_bits)` in the diag generator only — see Sprint H closure for the empirical brief). Engine HEAD `b5a642b` source files do not include this patch. Sprint I uses q_bits = 14 (well within the Sprint H validated range either way), so the patched/unpatched device state does not affect Sprint I correctness. The patched device .so is a leftover from an interactive session; the source tree is the canonical record.

**Action before Sprint I starts:** rebuild `libsp_compute_skel.so` from source HEAD and push to the device to bring the device state into alignment with the source-tree intent. The skel only changes if a future H.PATCH ships explicitly.

### C. Sprint H tags

```
lat-phase-3-hx-mode-d-h-diag-instrument
lat-phase-3-hx-mode-d-h-bisect-qbits
lat-phase-3-hx-mode-d-h-bisect-dim
lat-phase-3-hx-mode-d-h-closed
```

All four present on engine.

### D. Layer + tile + matmul method selection

- **Layer 0** of Qwen3-0.6B's FFN block. Smallest activation fan-in (no residual sum needed; matches the simplest possible matmul shape).
- **W_gate** projection (Qwen3 SwiGLU's `gate_proj`). Single matmul; no composition with W_up / W_down. Tensor name convention follows Qwen3's GGUF naming: `blk.0.ffn_gate.weight` + scale companion `blk.0.ffn_gate.weight.scale`.
- **Tile 128 × 128 i16**. Sprint G's PASS envelope is `d_in = d_out = 128` and `h_dim` arbitrary (Sprint H bisect_dim shows H ∈ {128, 160, 192, 224, 256} all PASS at q=14). Picking 128×128 hits the smallest validated configuration.
- **q_bits = 14**. b_term = 0. Inside the Sprint H ≤ 15 envelope with margin.
- **Kernel method:** `sp_compute_ffn_2stage_diag_halide` (Sprint H IDL method = 9). The method exposes `hidden_out = clamp((X @ W1 + b) >> q, 0, 32767)` as a separate Output buffer — i.e., the result of matmul-1 alone, which is exactly the W_gate projection math. W2 is set to all-zeros (unused; Y output ignored). batch = 4 (multiple of 4 required).

This route deliberately reuses the kernel that Sprint H already validated end-to-end; no production skel changes.

---

## 1. Architectural decisions

- **No new compute skel methods.** Sprint I drives the existing `sp_compute_ffn_2stage_diag_halide` (the Sprint H diag method) with W2 zeroed and `hidden_out` as the matmul result. Production correctness has already been proven for `d_in = h_dim = d_out = 128` at q ≤ 15.
- **No `sp_daemon` integration.** Sprint J productionizes the loader into the daemon. Sprint I is a standalone `[[bin]] sp_model_layer_smoke` in `tools/sp_dsp_smoke/` (matches the Sprint C `dsp_axum_server` precedent for standalone-on-device binaries).
- **No Fix B aliasing.** The smoke loads the W_gate tile by reading bytes into a DmaBuffer slice. Zero-copy aliasing of `.sp-model` mmap into FastRPC SMMU is Sprint J scope.
- **No multi-layer / no KV cache.** Single-layer single-matmul gate only.
- **Synthetic activations, not prefill output.** Three deterministic patterns (sentinel, pseudorandom, all-ones) drive bit-identity. Real prefill activations are Sprint J+.

---

## 2. File deliverables

### `tools/sp_dsp_smoke/src/sp_model_layer.rs` (parser library, commit 2)

Minimal `.sp-model` reader per `include/sp/sp_model.h`:

- `SpModelHeader` struct (512 bytes, `#[repr(C, packed)]`) mirroring `sp_model_header`. Fields exposed: `magic`, `version_major/minor`, `arch_id`, `vocab_size`, `tensor_count`, `tensor_table_offset`, `tensor_data_offset`.
- `SpTensorEntry` struct (256 bytes, `#[repr(C, packed)]`) mirroring `sp_tensor_entry`. Fields: `name[80]`, `dtype_id`, `n_dims`, `dims[8]`, `offset_in_data`, `size_bytes`, `block_size`, `block_count`.
- `read_header(file) -> io::Result<SpModelHeader>` — reads + magic + version check; SP_MODEL_MAGIC = 0x444D5053 ("SPMD"), version_major = 0.
- `read_tensor_table(file, header) -> io::Result<Vec<SpTensorEntry>>` — reads `tensor_count` entries from `tensor_table_offset`.
- `find_tensor(table, name) -> Option<&SpTensorEntry>` — linear search by name prefix (small N).
- `dequantize_q8_row(q8: &[i8], scale: f32, fixed_point_scale: f32) -> Vec<i16>` — multiplies each i8 by its row scale, applies the activation-scale conversion, clamps to i16.
- `read_layer_w_gate_tile(file, w_gate_entry, scale_entry, header, tile_offset, tile_dim, fp_scale) -> io::Result<Vec<i16>>` — seeks to `tensor_data_offset + w_gate_entry.offset_in_data + tile_offset_bytes`, reads `tile_dim.0 * tile_dim.1` Q8 bytes + per-row scales, dequantizes row-by-row to `Vec<i16>`.

DO NOT:
- Implement Fix B aliasing.
- Cache headers across calls.
- Add unnecessary error variants.

~80 LOC.

### `tools/sp_dsp_smoke/src/sp_model_layer_smoke.rs` (driver, commit 3)

Mirrors the `dsp_axum_server.rs` / `test_hvx.rs` shape:

```rust
#[cfg(not(target_os = "android"))]
fn main() {
    eprintln!("sp_model_layer_smoke: host build skipped");
}

#[cfg(target_os = "android")]
mod dsp_rpc;
#[cfg(target_os = "android")]
mod sp_model_layer;

#[cfg(target_os = "android")]
fn main() {
    // 1. Open FastRpcSession against the Sprint G compute skel.
    // 2. Open .sp-model file (path on /data/local/tmp/ after adb push).
    // 3. Parse header + tensor table; find blk.0.ffn_gate.weight + .scale.
    // 4. Load 128×128 W_gate tile into Vec<i16> via dequant + fixed-point scale.
    // 5. For each of 3 activation patterns:
    //    a. Materialize X (4 × 128 i16).
    //    b. Build W2 = zeros (4 × 128).
    //    c. Invoke ffn_2stage_diag_halide (method 9 — Sprint H IDL).
    //    d. Compute scalar ref via ffn_2stage_ref_with_hidden (same code as
    //       test_hvx.rs:471-503).
    //    e. assert_eq!(halide_hidden, scalar_ref_hidden) for the full 4×128.
    // 6. 100-iter leak test: same call in a loop; verify no growing FD on the
    //    fastrpc_shell process.
}
```

Inputs from `dsp_rpc.rs`: `FastRpcSession`, `RemoteArg`, `RemoteBuf`, `make_scalars`, `SpErr`. The invocation marshalling matches `test_hvx.rs::invoke_ffn_diag` (already proven for method 9 in Sprint H). The scalar reference is the existing `ffn_2stage_ref_with_hidden` (lines 471-503 of `test_hvx.rs`); for Sprint I we copy it locally or expose it via `mod` — both acceptable since the original lives in a bin file not a library. **Copy-paste with line-range citation** is the lower-risk choice (no cross-bin module gymnastics).

~100 LOC.

### `tools/sp_dsp_smoke/Cargo.toml` (commit 2)

Add `[[bin]]` for `sp_model_layer_smoke` pointing at `src/sp_model_layer_smoke.rs`. No new dependencies (uses libloading + std::fs + std::io — all already in scope).

---

## 3. Test gates

| Gate | Definition |
|---|---|
| `T_MODEL_HEADER_PARSE` | Parser returns `SpModelHeader` with `magic = 0x444D5053`, `version_major = 0`, `tensor_count > 0`. Validates header bytes against the C struct layout via roundtrip read+compare on a small known fixture. |
| `T_DMA_TILE_LOAD` | After `read_layer_w_gate_tile`, the i16 tile contents match a side-channel readback: bytes at `file_offset = tensor_data_offset + w_gate_entry.offset_in_data` dequantized by the same in-Rust path yield identical Vec<i16>. (Defensive — catches off-by-one in the byte-range math before we hand bytes to the kernel.) |
| `T_LAYER_MATMUL_BITWISE` | Halide kernel's `hidden_out` (single 4×128 batch of matmul-1 results) equals the scalar-reference `ffn_2stage_ref_with_hidden` output byte-for-byte. Verified across **3 distinct activation patterns**: (a) sentinel `0x1234` repeated; (b) pseudorandom `((i * 37 + 11) & 0x7FFF) - 16384` (matches Sprint G's X pattern); (c) all-ones `1i16`. **All three must PASS.** |
| `T_LAYER_NO_HEAP_LEAK` | 100-iter loop of `invoke_ffn_diag` with the same loaded tile; `adb shell "ps -A | grep fastrpc"` count stays at 1 across iterations. Wall-time growth bounded (no progressive slowdown that would imply per-iter heap fragmentation). |

The `M_I_SINGLE_LAYER` umbrella gate is PASS iff all four sub-gates are PASS.

---

## 4. Sub-tag taxonomy

- `lat-phase-3-hx-mode-d-i-parser-correct` — Stage 2 (parser) lands; T_MODEL_HEADER_PARSE + T_DMA_TILE_LOAD PASS.
- `lat-phase-3-hx-mode-d-i-bridge-bitwise` — Stage 3 (driver) lands; T_LAYER_MATMUL_BITWISE PASS across 3 activation patterns.
- `lat-phase-3-hx-mode-d-i-leak-free` — T_LAYER_NO_HEAP_LEAK PASS.
- `lat-phase-3-hx-mode-d-i-closed` — umbrella.

---

## 5. Commit plan

| # | Content | Repo |
|---|---|---|
| 1 | This plan | lattice |
| 2 | Parser (`sp_model_layer.rs`) + Cargo.toml bin entry; `T_MODEL_HEADER_PARSE` + `T_DMA_TILE_LOAD` as inline unit tests | engine |
| 3 | Driver (`sp_model_layer_smoke.rs`) with the three activation patterns; `T_LAYER_MATMUL_BITWISE` | engine |
| 4 | On-device run + leak gate `T_LAYER_NO_HEAP_LEAK`; verbatim output committed in the closure | engine |
| 5 | Closure with verbatim gate output + pcycles + Sprint J unblock note | lattice |

Per-commit isolation per the mandate's "DO NOT bundle parser + driver in one commit". Diagnostic value: if Stage 3 fails the bit-identity gate, we know the parser worked (Stage 2 closure stands) and the bug is in the marshalling / dequant.

---

## 6. Out of scope (explicit)

- Multi-layer load → Sprint J.
- KV cache allocation → Sprint J.
- Fix B zero-copy aliasing of `.sp-model` mmap into FastRPC SMMU → Sprint J.
- Full FFN (gate × up × down → SiLU) → Sprint J. Sprint I tests gate matmul only.
- Real activation tensor from prefill → Sprint J+. Sprint I uses synthetic patterns.
- Sprints K / L / M / N (depend on Sprint J landing first per the roadmap §13.6).
- `sp_daemon` integration → Sprint J. Sprint I is a standalone `sp-dsp-smoke` bin.
- Touching the production compute skel. Sprint I drives the existing Sprint H diag method as-is.
- `q_bits > 15` testing. Locked at q=14 per Sprint H constraint.

---

## 7. Risks + responses

**R1: Tensor-name mismatch (`blk.0.ffn_gate.weight` may not be the .sp-model's name for that tensor).** Sprint I parser scans the tensor table linearly anyway; if the name isn't found, the test fails fast with a clear "tensor X not found in .sp-model" error. Fix: dump tensor names from the file on first failure, pick the right one.

**R2: Q8 dequant scale doesn't fit the kernel's expected i16 range.** Sprint G's test data used scaled i16 weights in [-64, 63]. Real Qwen3 weights after dequant may be in [-127, 127] or wider. The fixed-point conversion scale needs tuning; if the Halide kernel hits saturation due to weight magnitude, the bit-identity gate still holds (both Halide and scalar ref saturate identically per Sprint H findings), but values will be near 0 after the q=14 shift. The bit-identity is the gate, not the magnitude.

**R3: 100-iter leak test catches a real leak.** Drop ordering for `DmaBuffer` was Sprint B's gate; if Sprint I sees FD growth, the bug is in the new driver's allocation pattern, not in `DmaBuffer` itself. Diagnostic: comment out the file-read step and re-run — if no leak, the leak is in the file IO; if still a leak, it's in the invoke path.

**R4: Sprint G's device skel state mismatch (per §0.B).** Source HEAD is `b5a642b` (unpatched); device has my interactive H.PATCH .so. Sprint I uses q=14 which works on both. Mitigation: rebuild + push the unpatched skel before starting Sprint I work, document the alignment in the closure.

---

## 8. What this sprint does NOT prove

- That dequantized weights match the upstream GGUF byte-for-byte. The .sp-model transcoder did the GGUF → .sp-model conversion at some prior point; Sprint I trusts that transcode and only proves the matmul pipeline works on the .sp-model bytes as-is.
- That the kernel handles all real-model shapes (Qwen3-0.6B has `hidden_size` and `intermediate_size` that don't match 128 — those are full-matrix shapes, not the 128×128 tile slice Sprint I validates). Sprint J tests at full shapes.
- That the activation scale is correct for end-to-end inference. Sprint I's synthetic activations exercise the matmul mechanics; activation pipeline correctness is a Sprint K-or-later validation.
