#!/usr/bin/env python3
"""
M.0-real dataset generator — produces the JSONL the SFT script consumes.

Two modes:

  --mode teacher   Load a teacher LLM on the GPU and generate synthetic
                   3-turn dialogues (Grounding -> Entity ID -> Synthesis).
                   Default teacher: Qwen2.5-7B-Instruct (fits 24 GB VRAM bf16;
                   8 GB at 4-bit). For each seed prompt, generates N variations.

  --mode template  No GPU required. Generates programmatic examples by
                   filling templates against a seed entity table. Fast,
                   deterministic, useful for bootstrap + smoke testing the
                   train pipeline before spending teacher compute.

The Memory model handles Turn 2 (entity-ID lookup). By default each output
row is a single-shot Memory-focused training example (system + user fact +
canonical ID assistant turn). Use --multi_turn to include all three turns
per example.

Usage on RunPod:

  # No-GPU bootstrap (~1k examples in 10 seconds):
  python generate_dataset.py --mode template \\
      --seeds seed_topics.txt \\
      --n_per_seed 20 \\
      --out /workspace/data/m0_real_bootstrap.jsonl

  # Teacher-LLM generation (~10k examples in 1-3 hr on A40):
  python generate_dataset.py --mode teacher \\
      --teacher Qwen/Qwen2.5-7B-Instruct \\
      --seeds seed_topics.txt \\
      --n_per_seed 50 \\
      --out /workspace/data/m0_real.jsonl

Output JSONL format (per line):

  {"messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Fact: ..."},
    {"role": "assistant", "content": "ENTITY:..."}
  ]}
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path

# --- Memory-model system prompt (3-turn protocol per sp_daemon dialogue) ---

MEMORY_SYSTEM = (
    "You are the Memory module of the Shannon-Prime dialogue protocol. "
    "Given a grounded fact, return its canonical entity ID in the form "
    "ENTITY:<DOMAIN>/<SLUG>. Domains are uppercase, slugs are uppercase "
    "snake_case. Return ONLY the entity ID, nothing else."
)

# Domain → seed entity table used in --mode template. Edit to suit your
# project. Each entry is (domain, slug, descriptive_phrase).
SEED_ENTITIES = [
    ("CHIP", "SNAPDRAGON_8GEN1",  "Snapdragon 8 Gen 1 with Hexagon V69 NPU"),
    ("CHIP", "SNAPDRAGON_8GEN3",  "Snapdragon 8 Gen 3 with Hexagon V73 NPU"),
    ("CHIP", "APPLE_M3",          "Apple M3 SoC with unified memory"),
    ("CHIP", "RTX_4090",          "NVIDIA RTX 4090 with 24 GB GDDR6X"),
    ("CHIP", "A100_80GB",         "NVIDIA A100 80 GB HBM2e datacenter GPU"),
    ("PHONE", "SAMSUNG_S22U",     "Samsung Galaxy S22 Ultra (Snapdragon 8 Gen 1)"),
    ("PHONE", "PIXEL_8_PRO",      "Google Pixel 8 Pro (Tensor G3)"),
    ("MODEL", "QWEN3_06B",        "Qwen3 0.6B parameter language model"),
    ("MODEL", "GEMMA3_1B",        "Gemma 3 1B parameter language model"),
    ("MODEL", "QWEN25_05B",       "Qwen 2.5 0.5B parameter language model"),
    ("PROJECT", "SHANNON_PRIME",  "Shannon-Prime PPT ARM Lattice"),
    ("CONCEPT", "CRT",            "Chinese Remainder Theorem"),
    ("CONCEPT", "FROBENIUS_LIFT", "Frobenius lift Q8 quantization"),
    ("CONCEPT", "NTT",            "Number Theoretic Transform"),
    ("LIB", "PYTORCH",            "PyTorch deep learning framework"),
    ("LIB", "TRANSFORMERS",       "Hugging Face Transformers library"),
    ("ORG", "QUALCOMM",           "Qualcomm Technologies Inc."),
    ("ORG", "ANTHROPIC",          "Anthropic AI safety company"),
    ("ORG", "NVIDIA",             "NVIDIA Corporation"),
    ("CITY", "SYDNEY",            "Sydney, Australia"),
    ("CITY", "SAN_FRANCISCO",     "San Francisco, California, USA"),
    # Add your own here — the more domain-specific, the more useful the
    # Memory model becomes for your dialogue use case.
]

# Templated phrasings for --mode template. Each is a (context, fact) pair
# where {phrase} is the descriptive phrase of the entity.
TEMPLATES = [
    ("Tell me about the {phrase}.",                          "Fact: the {phrase}."),
    ("What is the {phrase}?",                                "Fact: the {phrase} is a known entity."),
    ("I'm reading about the {phrase}.",                      "Fact: subject is the {phrase}."),
    ("Has anything been published on the {phrase}?",         "Fact: the {phrase} appears in the literature."),
    ("Can you summarize the {phrase}?",                      "Fact: focus entity is the {phrase}."),
    ("The {phrase} was mentioned in my notes.",              "Fact: the user references the {phrase}."),
    ("Background context: the {phrase}.",                    "Fact: context anchored on the {phrase}."),
    ("Show me details about the {phrase}.",                  "Fact: the {phrase} is the subject."),
]


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").upper()
    return s


def _format_example(domain: str, slug: str, phrase: str, context: str,
                    fact: str, multi_turn: bool) -> dict:
    """Produce one JSONL row (HF chat-template format)."""
    if multi_turn:
        # Full 3-turn protocol. Memory model role is Turn 2 — the assistant
        # message gives the entity ID. Turns 1 + 3 are framing.
        messages = [
            {"role": "system",    "content": MEMORY_SYSTEM},
            {"role": "user",      "content": f"Context: {context}"},
            {"role": "assistant", "content": f"Grounded fact: {fact}"},
            {"role": "user",      "content": fact},
            {"role": "assistant", "content": f"ENTITY:{domain}/{slug}"},
        ]
    else:
        # Single-turn Memory-focused example (most efficient for SFT). The
        # context is folded into the user message so the model still learns
        # to ignore distractors before emitting the ID.
        messages = [
            {"role": "system",    "content": MEMORY_SYSTEM},
            {"role": "user",      "content": fact},
            {"role": "assistant", "content": f"ENTITY:{domain}/{slug}"},
        ]
    return {"messages": messages}


# ── Mode 1: template generation (no GPU) ────────────────────────────────

def gen_template(args):
    rng = random.Random(args.seed)
    # Load seed entities. Use SEED_ENTITIES default unless a custom JSON is
    # passed via --entities.
    if args.entities:
        with open(args.entities) as f:
            ents = [(e["domain"], e["slug"], e["phrase"]) for e in json.load(f)]
    else:
        ents = SEED_ENTITIES

    # Optional extra seed phrases — used as additional "context" wrappers.
    extra_contexts = []
    if args.seeds and os.path.exists(args.seeds):
        with open(args.seeds) as f:
            extra_contexts = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen_hashes = set()  # dedupe by hash of fact
    n_written = 0

    with open(out_path, "w") as fout:
        for ent in ents:
            domain, slug, phrase = ent
            for _ in range(args.n_per_seed):
                ctx_template, fact_template = rng.choice(TEMPLATES)
                # Maybe wrap with extra context text from --seeds file.
                if extra_contexts and rng.random() < 0.4:
                    extra = rng.choice(extra_contexts)
                    context = f"{extra} {ctx_template.format(phrase=phrase)}"
                else:
                    context = ctx_template.format(phrase=phrase)
                fact = fact_template.format(phrase=phrase)
                h = hashlib.sha256((domain + slug + fact).encode()).hexdigest()[:16]
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                row = _format_example(domain, slug, phrase, context, fact, args.multi_turn)
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_written += 1
    print(f"[template] wrote {n_written} examples to {out_path}")
    print(f"[template] entities={len(ents)}  contexts={len(extra_contexts)}  multi_turn={args.multi_turn}")


# ── Mode 2: teacher-LLM generation (needs GPU) ──────────────────────────

def gen_teacher(args):
    """Use a teacher LLM to generate richer synthetic examples.

    Strategy: ask the teacher to produce a JSON array of {context, fact,
    entity_id} triples for each seed phrase. Parse strictly; skip malformed.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        sys.exit("teacher mode needs torch + transformers; pip install -r requirements.txt")

    print(f"[teacher] loading {args.teacher} (this takes 1-3 min)")
    tok = AutoTokenizer.from_pretrained(args.teacher, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dtype = torch.bfloat16 if args.bf16 else torch.float16
    qcfg = None
    if args.load_4bit:
        from transformers import BitsAndBytesConfig
        qcfg = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        args.teacher, torch_dtype=dtype, device_map="auto",
        quantization_config=qcfg, trust_remote_code=True,
    )
    model.eval()

    # Load seed entities
    if args.entities:
        with open(args.entities) as f:
            ents = [(e["domain"], e["slug"], e["phrase"]) for e in json.load(f)]
    else:
        ents = SEED_ENTITIES

    instruction = (
        "Generate {n} diverse short fact-and-context pairs about the entity "
        "described below. Each pair must be ONE conversational context "
        "sentence (what a user might say) followed by ONE 'Fact: ...' line "
        "that grounds the subject. Vary phrasing widely. Output ONLY a JSON "
        "array of objects with keys 'context' and 'fact', nothing else.\n\n"
        "Entity: {phrase}\n"
        "Canonical ID: ENTITY:{domain}/{slug}\n\n"
        "Output:"
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen_hashes = set()
    n_written = 0

    with open(out_path, "w") as fout:
        for i, (domain, slug, phrase) in enumerate(ents):
            prompt = instruction.format(n=args.n_per_seed, phrase=phrase,
                                         domain=domain, slug=slug)
            messages = [{"role": "user", "content": prompt}]
            text = tok.apply_chat_template(messages, tokenize=False,
                                            add_generation_prompt=True)
            inputs = tok(text, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=args.n_per_seed * 60,
                    do_sample=True,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    pad_token_id=tok.pad_token_id,
                )
            gen = tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

            # Parse: find the first '[' ... ']' span and json.loads it.
            try:
                start = gen.find("[")
                end = gen.rfind("]")
                if start < 0 or end < 0:
                    raise ValueError("no JSON array in output")
                arr = json.loads(gen[start:end+1])
            except Exception as e:
                print(f"[teacher] entity {domain}/{slug}: parse fail ({e}); skipping batch")
                continue

            n_kept = 0
            for item in arr:
                if not isinstance(item, dict):
                    continue
                ctx = str(item.get("context", "")).strip()
                fact = str(item.get("fact", "")).strip()
                if not ctx or not fact:
                    continue
                if not fact.lower().startswith("fact:"):
                    fact = "Fact: " + fact
                h = hashlib.sha256((domain + slug + fact).encode()).hexdigest()[:16]
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                row = _format_example(domain, slug, phrase, ctx, fact, args.multi_turn)
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_written += 1
                n_kept += 1
            print(f"[teacher] {i+1}/{len(ents)} {domain}/{slug}: kept {n_kept}/{len(arr)}")

    print(f"[teacher] wrote {n_written} examples to {out_path}")


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="M.0-real dataset generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--mode", choices=["template", "teacher"], default="template")
    p.add_argument("--out", required=True, help="Output JSONL path")
    p.add_argument("--seeds", default=None,
                   help="Optional seed_topics.txt — extra context phrases (one per line)")
    p.add_argument("--entities", default=None,
                   help="Optional JSON file overriding the default SEED_ENTITIES table. "
                        "Format: [{\"domain\": ..., \"slug\": ..., \"phrase\": ...}, ...]")
    p.add_argument("--n_per_seed", type=int, default=20,
                   help="Examples per entity (template) or generated triples per entity (teacher)")
    p.add_argument("--multi_turn", action="store_true",
                   help="Emit full 3-turn dialogues instead of single-turn Memory examples")
    p.add_argument("--seed", type=int, default=42)
    # Teacher-only
    p.add_argument("--teacher", default="Qwen/Qwen2.5-7B-Instruct",
                   help="Teacher LLM (HF repo or local path). Default fits 24 GB bf16 / 8 GB 4-bit.")
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--top_p", type=float, default=0.95)
    p.add_argument("--bf16", action="store_true", default=True)
    p.add_argument("--load_4bit", action="store_true",
                   help="QLoRA-style 4-bit teacher load — needed for 8 GB VRAM pods")
    args = p.parse_args()

    if args.mode == "template":
        gen_template(args)
    else:
        gen_teacher(args)


if __name__ == "__main__":
    main()
