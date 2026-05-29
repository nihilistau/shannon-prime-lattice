# SESSION PLAN — lat-3-hx-mode-k (K v0.alpha — dispatch-parallelism premise)
**Date:** 2026-05-30
**Goal:** Empirically verify whether two ARM threads concurrently invoking the EXISTING Sprint J FFN diag method on the cDSP achieve wall-clock parallelism via FastRPC + cDSP's dual-vector-context capability. **No kernel changes, no Halide generator changes, no second prime.** ~150 LOC; pcycle overlap is the decision gate for whether K v0.beta (Barrett-reduction CRT kernel) dispatches or K.2 (NPU/Mode B/D) takes priority.

---

## 1. Reference summary

| Source | Citation | Relevance |
|---|---|---|
| `reference-v69-hvx-expert-practices` (operator memory) | "V69 has 4 scalar threads, 2 vector contexts; SSR:XA={4,5} attach 2 threads to vector contexts 0 and 1 → true SIMT parallelism on chip" | Architectural premise being tested. |
| `reference-mode-d-bridge-architecture` (operator memory) | Sprint A–G marshalling primitives | Reused as-is; no new shape. |
| Sprint H closure `lat-phase-3-hx-mode-d-h-closed` | q_bits ≤ 15 operating range; matmul-2 codegen at q=16 still open | Sprint K stays at q=14. |
| Sprint J closure `lat-phase-4-sprint-j-closed` | `DspModel<'sess>` + `KvCache<'sess>` resident in cDSP DmaBuffers; layer 14 W_gate bitwise via Sprint H diag method 9 | The kernel + data K v0.alpha exercises. |
| Engine `dsp_rpc.rs:257` | `pub fn invoke(&self, scalars: u32, args: &mut [RemoteArg]) -> Result<(), SpErr>` — `&self`, synchronous | Critical detail: invoke is sync, takes `&self` not `&mut self`. |

---

## 2. Architectural decision: Arc<FastRpcSession>, NOT Mutex<FastRpcSession>

The Sprint K mandate specced `Mutex<FastRpcSession>` for thread sharing. Empirical re-check: `FastRpcSession::invoke` is a **synchronous** call (does not return until cdsp work completes — standard FastRPC semantic). Holding a `Mutex` lock across `invoke()` therefore serializes the test at the ARM lock-hold level **by construction** — thread B blocks at `Mutex::lock()` until thread A's full cdsp work completes.

K v0.alpha needs to discriminate "FastRPC + cdsp can parallelize concurrent invokes on one handle" from "they cannot." A Mutex-wrapped session forces a serial outcome regardless of cdsp behavior, which would falsely indict the cdsp/FastRPC layer.

Correct design: `Arc<FastRpcSession>`. `invoke(&self, …)` takes `&self`, and `FastRpcSession`'s fields (`Library` from libloading 0.8 + bare fn pointers + `u64` handle) are auto-`Send + Sync`. Two threads each call `sess.invoke(...)` concurrently on the same handle. If the compile-time Send/Sync check fails for any reason, fall back to `Mutex<FastRpcSession>` and report the resulting overlap with the design caveat in the closure.

This decision is operator-approved in spirit by the original pushback acknowledgment: *"verify Mutex doesn't serialize the actual cDSP work."* Since invoke is sync, the Mutex DOES serialize cdsp work — the correct check is `Arc` (concurrent invokes on one handle).

The mandate's `Mutex<FastRpcSession>` spec is preserved as the **fallback path** if `Arc` doesn't compile, with explicit note that any Mutex-bound overlap-fraction measurement is by-construction serial and tells us nothing about cdsp parallelism.

---

## 3. Bench design

Two measurements; both required for the parallelism verdict:

### Bench A — Single-thread sequential baseline

One ARM thread, invokes `sp_compute_ffn_2stage_diag_halide` (method 9) **twice** back-to-back on the same inputs. Records:
- Per-invoke wall time (`std::time::Instant`)
- Per-invoke kernel pcycles (returned from skel)
- Sum wall time

This is the "no parallelism possible" lower bound.

### Bench C — Arc<FastRpcSession>, two threads concurrent

Two ARM threads, each calls `sess.invoke(...)` on the same shared `Arc<FastRpcSession>`. Each thread:
- Captures `start_arm = Instant::now()` immediately before invoke
- Calls `sp_compute_ffn_2stage_diag_halide` with the same inputs Sprint J validated
- Captures `end_arm = Instant::now()` immediately after invoke returns
- Returns (start_arm, end_arm, kernel_pcyc) to the dispatcher

Dispatcher then computes:
```
T0          = min(start_a, start_b)        // earliest start
T1          = max(end_a,   end_b)          // latest end
wall_total  = T1 - T0                       // total wall window
overlap     = max(0, min(end_a, end_b) - max(start_a, start_b))   // intersection
overlap_fraction = overlap / wall_total     // ∈ [0, 1]
```

**Decision rule (per operator's K v0.alpha mandate):**
| overlap_fraction | Action |
|---|---|
| ≥ 0.5 | K v0.beta dispatch authorized — proceed to Barrett-reduction kernel rewrite |
| < 0.5 | K v0.beta NOT dispatched; pivot to K.2 (NPU/Mode B/D); closure documents which dispatch link serialized |

Speedup check (secondary, informative):
```
speedup = sequential_wall / dual_wall
```
- If `speedup ≥ 1.5`: strong parallelism (≈ true 2× minus overhead)
- If `1.0 ≤ speedup < 1.5`: partial parallelism
- If `speedup < 1.0`: regression (dual-thread is slower than sequential — contention dominates)

### Note on `Mutex<FastRpcSession>` as fallback

If the Arc compile-time check fails, Bench C is implemented with `Arc<Mutex<FastRpcSession>>`. The closure note flags this and the resulting overlap fraction is read as "the floor a Mutex'd design gives" — a useful baseline but NOT the test of the cdsp-parallelism premise.

---

## 4. Gates

| Gate | Definition |
|---|---|
| `M_K_alpha_FUNCTIONAL` | Both threads complete without errors. Each thread's `hidden` output bitwise-equal to the single-thread baseline's `hidden` output. Proves the concurrent dispatch doesn't corrupt data via DMA/marshalling race. NOT a performance claim. |
| `M_K_alpha_PCYCLE_OVERLAP` | `overlap_fraction` computed per §3 reported verbatim. Decision rule applied per §3 (≥ 0.5 vs < 0.5). Closure documents the value, the speedup ratio, and which dispatch path was used (Arc vs Mutex fallback). |
| `M_K_alpha_LEAK_FREE` | 100-iter cycle of Bench-C dispatch + drop; verify FastRpcSession is still usable post-100-iter and there are no fastrpc_shell zombies. (Per Sprint J pattern.) |

Umbrella `lat-phase-13-6-k-alpha-closed` fires when all 3 gates close.

---

## 5. Module structure

| File | Purpose | LOC est |
|---|---|---|
| `tools/sp_dsp_smoke/src/sp_dual_dispatch.rs` | NEW. `DualDispatch` struct holding `Arc<FastRpcSession>`. Methods: `single_invoke`, `dual_invoke`. ARM-side timestamp capture; overlap_fraction computation. | ~120 |
| `tools/sp_dsp_smoke/src/sp_dual_dispatch_smoke.rs` | NEW. Bin: loads Sprint J's DspModel; runs Bench A + Bench C; reports gate verdicts. | ~120 |
| `tools/sp_dsp_smoke/Cargo.toml` | EDIT. +`[[bin]]` for `sp_dual_dispatch_smoke`. | +6 |

Skel handler unchanged. The existing `sp_compute_ffn_2stage_diag_halide` returns `kernel_pcycles_lo/hi` already — Bench C uses ARM-side timestamps for the overlap math, with kernel_pcyc as the work-done secondary metric.

---

## 6. Commit plan

| # | Content | Repo |
|---|---|---|
| 1 | This plan | lattice |
| 2 | `sp_dual_dispatch.rs` + `sp_dual_dispatch_smoke.rs` + Cargo.toml (bundled because dispatcher only used by this one bin — separation would split into orphan modules) | engine |
| 3 | Verbatim on-device run output as `sprint_k_alpha_run_output.txt` | engine |
| 4 | Closure note + tags | lattice |

Per `feedback-bundled-changeset-root-cause-ambiguity`: the dispatcher module's only consumer is its sibling bin. Splitting them into two commits gains nothing diagnostically (no other code path could break the dispatcher alone). Bundling matches the operator's hard scope limit of "~150 LOC, ~2 hours."

---

## 7. Sub-tags

- `lat-phase-13-6-k-alpha-functional` — Bench-C output matches Bench-A; data integrity proven.
- `lat-phase-13-6-k-alpha-pcycle-measured` — overlap_fraction recorded with verbatim numbers; decision rule applied.
- `lat-phase-13-6-k-alpha-closed` — umbrella (after the 2 substantive sub-tags + leak gate).

If `M_K_alpha_PCYCLE_OVERLAP` ≥ 0.5, the closure files Sprint K v0.beta with the Barrett-reduction kernel scope (math identity gate per operator's corrected conditional formulation: Sprint J bitwise-equal AND `|acc| < INT32_MAX` for all test data).

If `M_K_alpha_PCYCLE_OVERLAP` < 0.5, the closure files Sprint K.2 (NPU integration via Mode B/D bridge unification) and documents which dispatch link serialized — FastRPC marshalling, cdsp scheduler, or Halide-emitted shared-resource contention — using the FastRPC shell logs + wall-clock vs summed-pcyc comparison.

---

## 8. Out of scope (hard limits per operator)

- ❌ Barrett reduction (K v0.beta if authorized)
- ❌ Halide generator changes (K v0.beta)
- ❌ Compute skel handler changes beyond what's already there (kernel_pcyc is already returned)
- ❌ Second prime constant — K v0.alpha uses identical Sprint J kernel on both threads
- ❌ NPU dispatch (K.2)
- ❌ Channel-pair allocation (Sprint M)
- ❌ Full FFN composition (Sprint K.3 or later)
- ❌ Touching sp_daemon (Sprint J.5 owns it)
- ❌ q_bits > 15 (Sprint H constraint)
- ❌ Touching Sprint J's loader (read-only consumer)

---

## 9. Risk register

**R1: `FastRpcSession` doesn't compile as `Sync` for `Arc` sharing.** Fallback to `Mutex<FastRpcSession>` immediately at compile-error time. Closure flags the fallback and notes any overlap measurement is by-construction serial.

**R2: Arc-shared concurrent invoke segfaults at runtime.** Some FastRPC client libs aren't thread-safe at the handle level even if the Rust wrapper compiles. Fallback to per-thread separate FastRpcSession instances (two skel handles per process; Sprint A precedent). LOC budget grows by ~30. Closure documents.

**R3: Both threads see identical wall-clock (full serialization).** This is the < 0.5 outcome the decision rule already anticipates. Closure files K.2 + documents which layer serialized:
- If `sum(kernel_pcyc)` ≈ `cdsp_clock × wall_total` ⇒ cdsp scheduler serializing on shared HVX context.
- If `sum(kernel_pcyc)` << `cdsp_clock × wall_total` ⇒ FastRPC marshalling/transport serializing (cdsp work was fast but ARM side waited).

**R4: Bench-C output diverges from Bench-A baseline.** Concurrent invokes corrupting each other's DmaBuffer state. M_K_alpha_FUNCTIONAL fails. Surface immediately; this is a real bug, not a scope issue.

**R5: 100-iter leak gate fails.** Some FastRPC client state leaks per concurrent invoke. Investigate; not unique to Sprint K.
