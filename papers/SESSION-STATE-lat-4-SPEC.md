# SESSION-STATE: Phase 4-SPEC (lat-phase-4-spec-math-closed)

**Phase:** 4-SPEC  
**Branch:** main  
**Started:** 2026-05-26  
**Status:** IN PROGRESS — plan written, implementation pending

## Fixture

- **Target:** Qwen2.5-Coder-3B.i1-Q4_K_M.gguf (36 layers, 2048 hidden, vocab 151936)
- **Draft:**  Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf (24 layers, 896 hidden, vocab 151936)
- **Fixture gap:** Qwen2.5-Coder-14B NOT on disk. M_SPEC_3 deferred.
- **Arch:** both `qwen2`, `rope_freq_base=1e6`, 3 F32 QKV biases/layer, no QK norms ✓
- **Transcode tool:** `build-cpu/tools/sp_transcode/sp_transcode.exe <in.gguf> <out.sp-model> <out.sp-tokenizer> [--verify]`

## Theorem T8 Framing

T8 (§11.5 PPT-LAT-Theory) is about MTP auxiliary heads.  
**Corollary T8.1** (the SPEC load-bearing claim): state at position t+j after  
`sp_session_rewind(K-j)` from t+K is byte-identical to state at t+j having  
never visited t+K. This is validated via logit identity in the `spec_validate` binary.

## Accept/Reject Protocol

Binary integer comparison: `argmax(target_logits[k]) == draft_tokens[k]`.  
No softmax. No temperature. No threshold. No probabilistic mixing.  
The Lattice operates over Z_q; accept/reject is integer equality.

## Key L1 Primitives Used

- `sp_session_clone` — fork target/draft sessions for per-chat isolation
- `sp_session_rewind(n)` — O(1) ring-pointer decrement on draft session after rejection
- `sp_session_position` — gate verification (M_SPEC_2)
- `sp_prefill_chunk` / `sp_decode_step` — draft generation + target verify
- `sp_session_config.deterministic = 1` — required for bit-exact M_SPEC_1

## Implementation Plan

`docs/superpowers/plans/2026-05-26-phase-4-spec.md`

Tasks:
1. Transcode both GGUFs via sp_transcode
2. Add `SpSession::rewind()` to session.rs
3. Dual-model AppState (state.rs + daemon.rs + main.rs)
4. spec.rs discrete loop module
5. spec_validate binary (M_SPEC_1 + M_SPEC_2)
6. Run gates
7. Memory entries
8. Closure

## Gate Results

| Gate | Status | Notes |
|------|--------|-------|
| M_SPEC_1 | PENDING | T8.1 rewind identity + planted acceptance rates |
| M_SPEC_2 | PENDING | position(target) == position(draft) throughout |
| M_SPEC_3 | DEFERRED | Awaits 14B fixture (≥1.5× throughput gate) |
| M_SPEC_4 | DEFERRED | Weight aliasing / peak RSS check |

## Closure Criteria

- [ ] M_SPEC_1: bit-identical output + T8.1 rewind identity at all planted rates
- [ ] M_SPEC_2: position(target) == position(draft) throughout 500-token soak
- [ ] Tag `lat-phase-4-spec-math-closed` on engine + lattice repos
- [ ] Rename to SESSION-CLOSED-lat-4-SPEC.md

## Anti-Contamination Notes

- Do NOT modify sp_l1.h or any math-core C files (L1 ABI is frozen)
- Do NOT read shannon-prime/ or shannon-prime-engine/ directories (legacy)
- If M_SPEC_1 fails on T8.1: escalate to math-core, do not work around in Rust
- If you find yourself writing softmax/temperature/probability ratio code: STOP
