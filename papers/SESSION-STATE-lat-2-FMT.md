# SESSION-STATE — lat-2-FMT (`.sp-model` on-disk format)

Worktree: `D:\F\shannon-prime-repos\shannon-prime-system-engine\.claude\worktrees\agent-ae9cd42cdb37e9a1c`
Branch:   `worktree-agent-ae9cd42cdb37e9a1c`
Phase:    2-FMT (parallel to 2-CU/VK/HX). Contract: PPT-LAT-SP-MODEL-v0 Appendix B, PPT-LAT-L1-ABI-v0, Roadmap §10.

## Scope (exit = E_FMT_1..4 green)
- E_FMT_1: `src/io/sp_model_load.c` — mmap + header parse + tensor-table pointer setup; magic/version/CRC-32/tokenizer SHA-256 verify.
- E_FMT_2: `tools/sp_transcode/` — GGUF→.sp-model; dequant→OK_Q8 (dtype 10) + FROBENIUS_SCALE_FP32 (dtype 12) sibling; sorted-by-xxh3 table; 65536-aligned data region, 64-aligned tensors; §9 sibling-adjacency.
- E_FMT_3: `.sp-tokenizer` extraction (SPTK header §7) + tokenizer_hash = SHA-256 of produced file.
- E_FMT_4: `tests/test_sp_model_roundtrip.c` — Gemma3-1B GGUF→.sp-model→load, gemma3_forward bit-identical (deterministic) vs GGUF path.

## Design decisions
- OK_Q8 on-disk == `sp_frob_pack_tensor(precision=8)` bytes: per-row int8 codes (the OK_Q8 tensor) + per-row fp32 scale (the .scale sibling, dtype 12). Re-quant REUSES `sp_frob_*` via the GGUF-row→f32 reader (mirrors arena.c build_tensor).
- E_FMT_4 equivalence: `sp_model_load` reconstructs a `qwen3_model` whose matmul weights live in an `sp_arena` rebuilt from the .sp-model OK_Q8 codes+scales (row_prec=8), norms/embedding owned f32. GGUF side loaded with the SAME Q8 quant (SP_ARENA=q8 + embed). Identical f32 dequant → identical Q8 codes → bit-identical logits.
- Hashes: minimal public-domain CRC-32 (IEEE), SHA-256, xxh3_64 implemented fresh in src/io/. BLAKE3 per-tensor verify opt-in (SP_VERIFY_TENSORS); header CRC + tokenizer SHA are the default-load checks.

## Build hack (DO NOT COMMIT)
- env-common.bat SP_ENGINE redirected to this worktree. Revert/unstage before commit.

## Status — CLOSED, all gates GREEN
Build: scripts\build\build-cpu.bat (after SP_ENGINE redirect) -> BUILD_EXIT=0, no warnings.
Tests: `ctest --test-dir build-cpu -R E_FMT --output-on-failure` -> 6/6 pass.
- E_FMT_0 (hash primitives: CRC-32/SHA-256/XXH64 vs published vectors + struct sizeof) PASS
- E_FMT_1 (sp_model_load: header CRC, magic/version/alignment, tokenizer SHA-256 verify + mismatch->SP_ETOKENIZER_HASH, O(logN) lookup) PASS
- E_FMT_2 (on-disk OK_Q8 codes + .scale BYTE-IDENTICAL to sp_frob_pack_tensor(prec=8); §9 sibling-adjacency) PASS
- E_FMT_3 (.sp-tokenizer SPTK magic + header CRC[0,52) + vocab==model) PASS
- E_FMT_4 (CLOSURE: Gemma3-1B transcode->load->gemma3_forward bit-identical vs GGUF arena-q8): bit_exact=YES, worst_abs=0, L2-drift=0.000000%, argmax 8/8 PASS
- E_FMT_4_QWEN3 (cross-arch: Qwen3-0.6B same gate): bit_exact=YES, drift 0%, argmax 8/8 PASS

Artifacts: gemma3 .sp-model 1003371008 B / 523 tensors (from 2.0GB F16 GGUF); qwen3 .sp-model 754551808 B / 509 tensors. .sp-tokenizer gemma3 4412662 B.
Full prior CPU regression (20 tests incl. E_CPU_10 release path, E_CPU_9 arena byte-identity, GEN_KV, COMPOSE, M_GEMMA3_CPU): 100% pass — additive changes broke nothing.

Build hack reverted (env-common.bat clean). Files: include/sp_engine/sp_model.h, src/io/{sp_hash.[ch],sp_model_load.c,sp_model_adapter.c}, tools/sp_transcode/, tests/{test_sp_hash.c,test_sp_model_roundtrip.c}; additive edits to arena.[ch], model.[ch], CMakeLists.
