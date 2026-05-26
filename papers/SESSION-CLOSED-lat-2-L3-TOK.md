# SESSION CLOSED — Phase 2-L3.TOK

**Tag:** `lat-phase-2-l3-tok-closed`
**Date:** 2026-05-26
**Host:** Windows 11 Pro, x86_64, MSVC toolchain (Rust stable-x86_64-pc-windows-msvc 1.92.0)
**Model fixture:** `build-cpu/tests/qwen3_rt.sp-model` + `.sp-tokenizer` (~754 MB, Qwen3-0.6B Q4)

## Scope

Phase 2-L3.TOK — SPTB tokenizer integration into sp-daemon: text input encoding,
chat template application, UTF-8 detokenization, stop-string buffering.
Engine commit `9aa442d`.

## Changes from SSE baseline (`2db6f9b`)

| File | Change |
|---|---|
| `src/tokenizer.rs` (new) | SPTB parser, GPT2 byte-level decode table, `SptbTokenizer` (BPE/GPT2 via `tokenizers` crate, `ByteLevel` pre-tokenizer), `chatml_template` / `gemma3_template`, `TokenDecodeBuffer` (UTF-8 boundary + stop-string buffering) |
| `src/routes.rs` | `ChatRequest`: `prompt/messages/prompt_tokens/stop` (HTTP 400 if >1 or 0); `v1_chat` returns `Response`; tokenize → prefill → decode loop with EOS check + `TokenDecodeBuffer` + flush on cancel/done; phase string updated |
| `src/session.rs` | `SpModel::tokenizer_blob()` via `sp_model_tokenizer_blob` L1 ABI |
| `src/state.rs` | `AppState.tokenizer: Arc<SptbTokenizer>` |
| `src/daemon.rs` | `SptbTokenizer::build` after `arch_info`; logs arch_id + eos_ids |
| `src/main.rs` | `mod tokenizer;` |
| `Cargo.toml` | `tokenizers = "0.21"`, `ahash = "0.8"` (AHashMap for BpeBuilder::vocab_and_merges) |

## Gate results (Qwen3-0.6B Q4, Windows MSVC x86_64)

| Gate | Result | Note |
|---|---|---|
| E_L3_TOK_1 — `{"prompt":"..."}` sane completion | ✓ | "The meaning of life is a question that has long been debated by philosophers..." |
| E_L3_TOK_2 — `{"messages":[...]}` sane chat response | ✓ | Qwen3 `<think>` chain-of-thought triggered; ChatML template applied correctly |
| E_L3_TOK_3 — stop string halts generation | ✓ | stop=[" seven"] on counting sequence: " five, six," emitted, clean [DONE] |
| E_L3_TOK_4 — detokenized text valid UTF-8 | ✓ | All deltas valid UTF-8 across 20-token Chinese-prompt completion |

## Chat template vetting (Option 1 — hardcode per arch_id)

Vetted by review against the template patterns in the engine's
`lib/shannon-prime-system/include/sp/sp_l1.h` comments and the `llm_chat_template.hpp`
reference in the engine codebase. Empirical llama-cli diff was NOT used (per spec).

**Qwen3 / Qwen2.5 (arch_id 2, 6) — ChatML:**
```
<|im_start|>system\n{content}<|im_end|>\n   ← added if first message is not system
<|im_start|>{role}\n{content}<|im_end|>\n   ← each message
<|im_start|>assistant\n                      ← assistant turn prompt
```
EOS tokens: `<|im_end|>` (151645), `<|endoftext|>` (151643)

**Gemma3 (arch_id 3):**
```
<start_of_turn>{role}\n{content}<end_of_turn>\n   ← "assistant" → "model"
<start_of_turn>model\n                             ← model turn prompt
```
EOS tokens: `<eos>`, `<end_of_turn>`

## TokenDecodeBuffer architecture

```
decode loop → token_id → decode_token(id) → raw bytes
    │
    └── TokenDecodeBuffer::push(bytes)
          hold = max_stop_len - 1 (bytes held back for stop detection)
          → scan full buffer for stop strings (memmem)
          → emit valid_utf8_up_to(buf[..len-hold]) bytes per push
          → Emit(bytes) or Stopped(bytes_before_stop)
    │
    └── flush() on loop exit — emits held-back bytes before [DONE]/cancelled
```

## SPTB format parsed (BPE_GPT2 type_id=2, Qwen3 fixture)

```
u32 magic=0x42545053 | u32 type_id=2 | u32 vocab_size=151936 | u32 n_merges
vocab: 151936 × (u32 len + UTF-8 bytes)
merges: N × (u32 len + "left right" UTF-8, split on first ASCII space)
```

EOS IDs logged at startup: `[151643, 151645]` (endoftext + im_end) ✓

## Follow-on: Phase 2-FMT.template

Templates are hardcoded per arch_id (Fix A — stopgap). Fix B (end-state) is
Phase 2-FMT.template: extend `sp_tok_header` to carry a template blob so the
daemon reads the template from the model file rather than from hardcoded Rust.
Same Fix-A-stopgap / Fix-B-end-state pattern as §9.0 (sp_model_release_source).

Tracking: Phase 2-FMT.template, scope: extend `sp_tok_header` + C encoder +
Rust reader in `tokenizer.rs::apply_template`.

## Not fired

`lat-phase-2-l3-closed` — fires after FG / AUTH all close.
