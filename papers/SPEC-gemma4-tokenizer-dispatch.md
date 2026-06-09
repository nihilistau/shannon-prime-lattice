# SPEC — gemma4 tokenizer dispatch (the 514k-merge BPE)

Status: **IMPLEMENTED — GATES GREEN (2026-06-10).** Engine `3457a41..3253a82` +
core `9d3cc72` (SP_TOK_GEMMA4_BPE=4 + a vocab-only-GGUF open fix found en route).
**T_G4_TOK_PARITY 5432/5432 exact on BOTH lanes** (GGUF-direct AND
`--tok-only`-transcoded GEMMA4_BPE blob), **T_G4_TOK_ROUNDTRIP 60/60** (incl.
emoji/CJK/control-byte/invalid-UTF-8 `<0xNN>` fallback). Fixture provenance
reconstructed: first 24576 B of `archive/eval/wikitext-103-raw/wiki.test.raw`,
re-verified fresh vs HF tokenizers 0.22.2 (official bucket tokenizer.json).
No-regression: qwen3 `.sp-tokenizer` SHA-identical through the new dispatch;
GPT2 lane 45/45 vs stock-llama oracle ids; E_FMT_4_QWEN3 green. Stage-0
normalizer point: llama-vocab.cpp:3144-3151 (b8861); regex `"[^\n]+|[\n]+"`,
byte_encode=false. REMAINING (deliberate): the shipped gold-campaign
`models/gemma4-12b*.sp-tokenizer` blobs are legacy type_id=2 (old loud
encode-(-1) behavior) until regenerated with `--tok-only` and re-paired via
`tokenizer_hash` — the gold artifacts were NOT mutated. 12B text-in (daemon,
NIAH-on-12B, Stage-Eta prompting) is now unblocked behind that regeneration.

*(Original status, for history: DESIGN SKETCH 2026-06-08; every PPL number
rode the verified token fixture.)*

## Ground truth (established 2026-06-07, receipts in session record)

`tokenizer.ggml.model = "gemma4"` is a NEW vocab variant: BPE with **514k
merges** over **unicode-space (▁) pieces** + **byte_fallback** + a **Split
pre-tokenizer**, vocab 262144. It is NOT the GPT2-byte-space BPE (our
existing path returns encode −1 on its pieces: ▁-pieces are not byte-mapped)
and NOT classic SentencePiece-Viterbi (it has BPE merge ranks, not just
scores). T1 proved llama.cpp's implementation == HF tokenizer.json exactly
(5431/5431 token IDs on the wikitext head). The transcoder already extracts
everything needed: `build_tok_blob` writes tokens + scores + the 514k merges
into the `.sp-tokenizer` blob; the 12B blob ships in
`models/gemma4-12b-st.sp-tokenizer` (10.6 MB).

## Stage 0 (MANDATORY, lead-with-the-reference)

Read llama.cpp's actual gemma4 tokenize path BEFORE writing code, with
file:line citations in the plan commit: the `LLAMA_VOCAB_PRE_TYPE_*` case
for gemma4 in `src/llama-vocab.cpp` (exact Split regex, space→▁ rules,
special-token handling, BOS/EOS defaults) and the merge-application loop.
Two prior theory-first failures are on the record; the regex especially is
NOT guessable — copy it verbatim and cite it.

## Pipeline (encode)

1. **Specials pass** — match registered special tokens (BOS=2 family, etc.,
   from GGUF kv) as atomic segments; never run BPE across them.
2. **Pre-tokenize** — apply the gemma4 Split regex (from Stage 0) to cut
   the text into pre-tokens. NO byte-mapping (that is the GPT2 path's move).
3. **▁-normalize** — replace U+0020 with ▁ (U+2581) per the reference's
   rule (leading-space conventions exactly as llama does them; verify the
   add-prefix-space flag in the GGUF kv).
4. **Greedy rank-BPE** — within each pre-token: start from UTF-8 bytes
   grouped into initial pieces present in the vocab; repeatedly merge the
   adjacent pair with the LOWEST merge rank until no pair is mergeable.
   514k merges ⇒ pair→rank lookup MUST be a hash (u64 key = (left_id<<32)
   | right_id → rank; ~8 MB, built once at load), never a linear scan.
5. **byte_fallback** — any unmatched byte emits its `<0xNN>` token.

Decode: piece concat with ▁→space, byte tokens reassembled, specials
stripped per flags — round-trip exercised by the gate.

## Dispatch wiring

The `.sp-tokenizer` blob grows a `family` tag (GPT2_BPE | SPM | GEMMA4_BPE),
written by sp_transcode from `tokenizer.ggml.model` + pre-tokenizer kv, read
at `sp_model_load`. Unknown family = hard error naming the family string —
NOT a silent fallback to GPT2 (the encode−1 failure mode was at least loud;
a wrong-dispatch SILENT mis-tokenization would be the tokenizer twin of the
GGUF weight corruption: every id valid, every id wrong).

## Gates

1. `T_G4_TOK_PARITY` — encode the wikitext head; diff vs the verified
   fixture `_g4_12b_wiki_tokens.txt` (5432 ids, llama-dumped == HF):
   **5432/5432 exact**, no tolerance.
2. `T_G4_TOK_ROUNDTRIP` — decode(encode(x)) == x over the fixture corpus +
   adversarial set (emoji, CJK, control bytes → byte_fallback coverage).
3. Perf telemetry only: encode MB/s with the hashed rank table (no gate;
   tokenization is not on any hot path yet).

## Non-goals

No claim about other gemma4-family models' tokenizers (E-series uses the
same family; verify per-model kv). No streaming/incremental encode until the
daemon needs it.
