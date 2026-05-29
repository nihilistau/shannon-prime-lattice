# SESSION CLOSED — lat-3-hx-mode-d-dma (Sprint B)
**Date:** 2026-05-29  
**Plan:** `papers/SESSION-PLAN-lat-3-hx-mode-d-dma.md` (`db90a43`)  
**Engine commit:** `f73db35`  

**Tags issued at engine `f73db35`:**
- `lat-phase-3-hx-mode-d-dma-alloc-correctness` ✓
- `lat-phase-3-hx-mode-d-dma-zero-copy-verified` ✓
- `lat-phase-3-hx-mode-d-dma-leak-free` ✓
- **Umbrella: `lat-phase-3-hx-mode-d-dma-closed` ✓**

---

## 1. Status

**CLOSED.** All three sub-tags + umbrella issued. Zero-copy DmaBuffer working on Knack's S22U; bitwise correctness across 16 B / 4 KB / 1 MB; 1000-cycle leak-free.

---

## 2. Deliverables (`f73db35`)

### `dsp_rpc.rs` additions

| Symbol | Source |
|---|---|
| `pub const RPCMEM_HEAP_ID_SYSTEM: c_int = 25` | rpcmem.h:89 — V69 cDSP via SMMU |
| `pub const RPCMEM_DEFAULT_FLAGS: u32 = 1` | rpcmem.h:52 — ION_FLAG_CACHED |
| `pub const RPCMEM_TRY_MAP_STATIC: u32 = 0x04000000` | rpcmem.h:62 — pre-map for latency-critical calls |
| `type FnRpcMemAlloc / FnRpcMemFree` | rpcmem.h:186,216 — from libcdsprpc.so |
| `FastRpcSession::alloc_dma(size) -> Result<DmaBuffer<'_>, SpErr>` | new |
| `struct DmaBuffer<'sess>` | lifetime-tied via `PhantomData<&FastRpcSession>`; Drop → `rpcmem_free` |
| `SpErr::RpcMemAlloc(usize)` | new variant for null alloc |

Per rpcmem.h:127, `rpcmem_init`/`rpcmem_deinit` are NOT required when linked to `libcdsprpc.so` (which we already are). Saved two more symbol resolutions.

### Sprint B tests in `sp_dsp_smoke/main.rs`

- `T_DMA_ALLOC_FREE` — 1 MB alloc + Drop
- `T_DMA_PING_{16B,4KB,1MB}` — `sp_echo_ping` invoke with DmaBuffer-backed `in_buf`/`out_buf` + bitwise verify
- `T_DMA_VS_HEAP` — 1000-iter 1 MB ping wall comparison (heap `Vec<u8>` vs DmaBuffer)
- `T_DMA_LEAK_1` — 1000 alloc/invoke/drop cycles

---

## 3. On-Device Results (S22U R5CT22445JA, ~50 sec total wall)

```
[sp-dsp-smoke] ═══ Sprint B: DmaBuffer tests ═══
[sp-dsp-smoke] T_DMA_ALLOC_FREE (1 MB) PASS — ptr=0x7c0e74d000
[sp-dsp-smoke] T_DMA_PING_16B  (16 B)        PASS
[sp-dsp-smoke] T_DMA_PING_4KB  (4096 B)      PASS
[sp-dsp-smoke] T_DMA_PING_1MB  (1048576 B)   PASS
[sp-dsp-smoke] T_DMA_VS_HEAP   (1 MB × 1000): heap 22.999s, dma 22.030s, ratio 0.958×
[sp-dsp-smoke] T_DMA_LEAK_1    (1000 alloc/invoke/drop) PASS
[sp-dsp-smoke] ALL GATES PASS
```

Sprint A regression baseline preserved — `T_RPC_ECHO_{1,2,3}` and `T_RPC_LEAK_1` all still PASS in the same binary.

---

## 4. Findings

### F1 — Zero-copy speedup modest on 1 MB (~4.2%) but real

Heap path: 22.999s / 1000 iter ≈ 23.0 ms/iter.  
DMA path:  22.030s / 1000 iter ≈ 22.0 ms/iter. **Ratio 0.958×; DMA is 4.2% faster.**

Most of the per-iter wall (~22 ms) is DSP wakeup + invoke overhead, not the marshal copy itself. The marshal copy at 1 MB on the ARM↔DSP fabric is somewhere in the sub-ms range, so eliminating it saves ~1 ms which is the observed delta.

**Where DmaBuffer's bigger payoff appears:**
- Sub-ms inference hot path (token decode, ~64-512 KB KV reads per layer) where the per-call marshal copy is a larger fraction of total wall
- Spinor-block KV cache where rpcmem buffers can be **reused across many invokes** (no per-call alloc/free cost; FastRPC's `RPCMEM_TRY_MAP_STATIC` keeps them pre-mapped on the cDSP side)
- Halide AOT kernels (Sprint D / Mode D FFN fusion) that read large weight chunks via FastRPC — there the marshal copy dominates

### F2 — Exact-size discipline trivially honored

The `DmaBuffer` API forces this by design: `alloc_dma(N)` returns a buffer of exactly N bytes; `buf.len()` always returns N; the smoke uses the same N when constructing `RemoteArg::nlen` and `primIn[i]`. No off-by-one possible without contortion. Per `reference-hexagon-working-setup` §"Exact rpcmem size MATCH" this avoids the `AEE_EUNSUPPORTED` silent-fail footgun.

### F3 — `rpcmem_init`/`rpcmem_deinit` not needed

Per rpcmem.h:127,141, those calls are only mandatory on **pre-Lahaina targets when linked to `rpcmem.a` (static)**. When the host dynamic-links libcdsprpc.so (which we do), the .so initializes internally on first call. Two fewer symbols to resolve, slightly simpler error handling.

---

## 5. Open Work

| Item | Phase | Trigger |
|---|---|---|
| Sprint C: Axum integration loop binding FastRpcSession + DmaBuffer into daemon HTTP path | §3-HX Sprint C | UNBLOCKED by this umbrella |
| Sprint D / Mode D FFN: Halide AOT FFN skeleton + DmaBuffer-backed weight bank | post-Sprint C | Gated on C + lattice §16.5 KSTE patterns |
| `rpcmem_alloc2` wrapper for >2 GB buffers | extension | Out of scope; current SP_HEXAGON_HEAD_DIM_MAX × f32 = 4 KB so single rpcmem_alloc(int size) suffices |
| Consolidate dsp_rpc.rs duplication (sp_daemon vs sp_dsp_smoke) into shared workspace member | post-Sprint A | When sp-daemon's android target build is sorted (Phase 2-L3.FG) |
