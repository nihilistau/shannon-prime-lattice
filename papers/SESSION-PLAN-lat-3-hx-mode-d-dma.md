# SESSION PLAN — lat-3-hx-mode-d-dma (Sprint B)
**Date:** 2026-05-29  
**Goal:** `DmaBuffer` zero-copy via `rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, RPCMEM_TRY_MAP_STATIC, size)`. Eliminate the ARM↔DSP marshalling copy that Sprint A pays for plain `Vec<u8>` buffers.

---

## 1. Reference Summary (Stage 0)

### `rpcmem.h` API (Hexagon SDK 5.5.6.0, `ipc/fastrpc/rpcmem/inc/rpcmem.h`)

```c
void *rpcmem_alloc(int heapid, uint32 flags, int size);   // line 186
void  rpcmem_free(void *po);                              // line 216
int   rpcmem_to_fd(void *po);                             // line 223
void  rpcmem_init(void);                                  // line 127 — optional on Lahaina+ when linked to libcdsprpc.so
void  rpcmem_deinit(void);                                // line 141
```

Constants used:
- `RPCMEM_HEAP_ID_SYSTEM = 25` (line 89) — V69 cDSP via SMMU
- `RPCMEM_HEAP_ID_CONTIG = 22` (line 83) — legacy; deprecated for V73+; not used
- `RPCMEM_DEFAULT_FLAGS = 1` (line 52) — ION_FLAG_CACHED
- `RPCMEM_TRY_MAP_STATIC = 0x04000000` (line 62) — pre-map at alloc; recommended for latency-critical hot path

### Critical contract (per `reference-hexagon-working-setup` §"Exact rpcmem size MATCH"):

The `size` passed to `rpcmem_alloc` MUST EXACTLY equal the `Len` parameter in the IDL signature at invoke time. Off-by-one (e.g. allocating extra "safety pad") → `AEE_EUNSUPPORTED` (0x80000414) silent failure that masquerades as DSP crash.

### Symbol location

All `rpcmem_*` exports are in **`libcdsprpc.so`** (the same .so we already dynamic-link for `remote_handle64_*`). No new .so to load — just 4 more `Library::get` calls in `FastRpcSession::new`.

### Prior cohort pattern (`shannon_prime_hexagon.c:174-185`)

```c
ctx->scratch_bytes = SP_HEXAGON_HEAD_DIM_MAX * sizeof(float);
int alloc_flags = RPCMEM_DEFAULT_FLAGS | RPCMEM_TRY_MAP_STATIC;
ctx->scratch_in_f32[b]  = rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, alloc_flags, scratch_bytes);
ctx->scratch_out_f32[b] = rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, alloc_flags, scratch_bytes);
```

Two-deep ping-pong scratch sized for the largest expected `head_dim`. Allocated ONCE at session create per Phase 2-L3.FG ABI rule (no allocation on hot path).

---

## 2. API Decision

Add to `dsp_rpc.rs` (mirrored across sp_daemon + sp_dsp_smoke per existing convention):

```rust
/// RPC-memory backed buffer. Backing memory is an ION dma-buf allocated by
/// libcdsprpc.so's rpcmem_alloc — zero-copy across the ARM/DSP boundary
/// (FastRPC sees these as ION fd and skips the marshal copy).
///
/// Drop calls rpcmem_free. The owning FastRpcSession's libloading::Library
/// MUST outlive any DmaBuffer it issued — DmaBuffer holds a borrowed alloc/
/// free fn ptr pair, not its own Library handle.
pub struct DmaBuffer<'sess> {
    ptr:       *mut u8,
    len:       usize,
    fn_free:   FnRpcMemFree,
    _phantom:  std::marker::PhantomData<&'sess FastRpcSession>,
}

impl<'sess> DmaBuffer<'sess> {
    pub fn as_ptr(&self) -> *const u8 { self.ptr }
    pub fn as_mut_ptr(&mut self) -> *mut u8 { self.ptr }
    pub fn len(&self) -> usize { self.len }
    /// Borrow as a byte slice. Safe because we control the allocation +
    /// alignment and the size is invariant for the buffer's lifetime.
    pub fn as_slice(&self) -> &[u8] { unsafe { std::slice::from_raw_parts(self.ptr, self.len) } }
    pub fn as_mut_slice(&mut self) -> &mut [u8] { unsafe { std::slice::from_raw_parts_mut(self.ptr, self.len) } }
}

impl<'sess> Drop for DmaBuffer<'sess> { fn drop(&mut self) { (self.fn_free)(self.ptr as *mut c_void); } }

impl FastRpcSession {
    /// Allocate a zero-copy buffer of `size` bytes from heap 25 (cDSP SMMU).
    /// Flags = RPCMEM_DEFAULT_FLAGS | RPCMEM_TRY_MAP_STATIC (cached + pre-mapped).
    /// Returns SpErr::RpcMemAlloc on failure.
    pub fn alloc_dma(&self, size: usize) -> Result<DmaBuffer<'_>, SpErr>;
}
```

### Error variants (extension)

Add to `SpErr`:
- `Symbol("rpcmem_alloc")` / `Symbol("rpcmem_free")` — extension of existing variant
- `RpcMemAlloc(usize)` — `rpcmem_alloc` returned NULL for requested size

---

## 3. Tests

Append to `sp_dsp_smoke/src/main.rs`:

- **T_DMA_ALLOC_FREE** — single alloc(1 MB) → drop → no crash, no leak
- **T_DMA_PING_BITWISE** — invoke `sp_echo_ping` using a `DmaBuffer` as the in_buf AND a `DmaBuffer` as out_buf; verify bitwise correctness across 16 B / 4 KB / 1 MB
- **T_DMA_VS_HEAP** — comparison bench: 1000 iter of 1 MB ping with `Vec<u8>` (marshal copy) vs 1000 iter of 1 MB ping with `DmaBuffer` (zero-copy). Print P50 wall and ratio. **Expected**: rpcmem path is faster by some factor; no specific gate (this is a finding, not a binary pass/fail). If rpcmem path is NOT faster, surface as finding.
- **T_DMA_LEAK_1** — 1000-cycle alloc/use/drop; no leak

Tests live in `sp_dsp_smoke/src/main.rs` after the existing T_RPC_LEAK_1 block.

---

## 4. Exact-Size Discipline (no off-by-one)

When backing `sp_echo_ping`'s `in_buf` / `out_buf` with DmaBuffer:
- Caller picks payload size N
- `DmaBuffer::alloc_dma(N)` — exactly N bytes
- `primIn[0] = N as u32; primIn[1] = N as u32` — same N
- `RemoteArg { pv = buf.as_mut_ptr(), nlen = N }` — same N

Any divergence → AEE_EUNSUPPORTED on invoke (per `reference-hexagon-working-setup`).

---

## 5. Sub-tag Taxonomy

- `lat-phase-3-hx-mode-d-dma-alloc-correctness` (T_DMA_ALLOC_FREE + T_DMA_PING_BITWISE pass)
- `lat-phase-3-hx-mode-d-dma-zero-copy-verified` (T_DMA_VS_HEAP shows rpcmem ≤ heap on 1 MB transfer)
- `lat-phase-3-hx-mode-d-dma-leak-free` (T_DMA_LEAK_1 1000 cycles)
- Umbrella `lat-phase-3-hx-mode-d-dma-closed` after all 3.

---

## 6. Commit Plan

| # | Content |
|---|---|
| 1 | Plan (this file) — lattice |
| 2 | dsp_rpc.rs: rpcmem symbol resolution + `DmaBuffer` + `alloc_dma` — engine |
| 3 | sp_dsp_smoke: T_DMA_* tests + run on device — engine |
| 4 | Closure note + sub-tags + umbrella — lattice |

Existing engine `tools/sp_echo_skel/` from Sprint A is unchanged — same skel handles both Vec-backed and DmaBuffer-backed invokes because FastRPC negotiates the marshalling automatically based on whether the input pointer is an rpcmem fd or a regular heap pointer.

---

## 7. Out of Scope (Sprint C)

- Axum HTTP integration (Sprint C)
- Wiring DmaBuffer into the daemon's inference path (Sprint C / Phase 2-L3.FG)
- Real Halide AOT kernel invocation (Mode D Sprint D when relevant)
