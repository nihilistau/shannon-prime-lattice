#!/usr/bin/env python3
"""
M.0-real dataset generator — builds the JSONL the SFT script consumes.

The Memory model is the factual-response component of the M.2 dialogue
protocol (Grounding → Entity ID → Synthesis). Executive sends a grounding
query; Memory responds with the factual content; Executive synthesizes
the user-facing answer. Memory must handle ANY question the Executive
can probe with — it's the general world-knowledge engine, not a
domain-specific classifier.

This generator pulls from public Hugging Face datasets, filters for
factual/instruction-following quality, and reformats into the
Memory-role chat template the SFT script expects. Default sources are
balanced for coverage:

    trivia_qa            — 950k trivia Q&A pairs; broad topic coverage
    nq_open              — Natural Questions (real Google search queries
                           with Wikipedia answers)
    databricks-dolly-15k — instruction-tuning examples across 8 categories
    squad_v2             — reading-comprehension Q&A
    sciq                 — science Q&A

You can override the source list, per-source limits, system prompt, or
add your own JSONL of in-domain Q&A. The output is a single shuffled
JSONL ready for `run_train.sh`.

Usage on RunPod:

    # Default: pulls all 5 sources, ~80k examples mixed:
    python generate_dataset.py --out /workspace/data/m0_real.jsonl

    # Restrict to factual Q&A only (skip instruction-following):
    python generate_dataset.py --out ... \\
        --sources trivia_qa,nq_open,squad_v2,sciq

    # Add your own custom Q&A on top of the defaults:
    python generate_dataset.py --out ... \\
        --custom_jsonl /workspace/data/my_custom_qa.jsonl

    # Fewer examples for a fast first pass:
    python generate_dataset.py --out ... --per_source 2000

Custom JSONL format (each line one of these):

    {"question": "...", "answer": "..."}
    {"prompt": "...", "completion": "..."}
    {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}
"""

import argparse
import json
import random
import sys
from pathlib import Path

# ── Memory-role system prompt (matches M.2 dialogue protocol) ─────────

MEMORY_SYSTEM = (
    "You are the Memory module of the Shannon-Prime dialogue protocol. "
    "The Executive module sends you a grounding query — a question or "
    "probe drawn from a user conversation. Your job is to respond with "
    "concise, accurate factual content: the relevant names, dates, "
    "definitions, facts, or knowledge that answers the query. Be direct "
    "and informative. The Executive will synthesize your response into "
    "the final user-facing answer."
)

# ── Source loaders. Each returns an iterator of (user_query, factual_response) tuples.

def _load_trivia_qa(n: int, seed: int):
    """TriviaQA — 950k trivia Q&A pairs."""
    from datasets import load_dataset
    ds = load_dataset("trivia_qa", "rc.nocontext", split="train", streaming=True)
    rng = random.Random(seed)
    yielded = 0
    for ex in ds:
        if yielded >= n:
            return
        q = ex.get("question", "").strip()
        ans_struct = ex.get("answer") or {}
        a = ans_struct.get("value", "").strip() if isinstance(ans_struct, dict) else ""
        if not q or not a:
            continue
        # Skip examples where answer is suspiciously short (likely a token, not a fact)
        if len(a) < 2:
            continue
        yield q, a
        yielded += 1


def _load_nq_open(n: int, seed: int):
    """Natural Questions Open — real Google queries with Wikipedia answers."""
    from datasets import load_dataset
    ds = load_dataset("nq_open", split="train", streaming=True)
    yielded = 0
    for ex in ds:
        if yielded >= n:
            return
        q = ex.get("question", "").strip()
        answers = ex.get("answer", [])
        if not q or not answers:
            continue
        a = answers[0].strip() if isinstance(answers, list) else str(answers).strip()
        if len(a) < 2:
            continue
        # NQ questions are often lowercase + no question mark; normalize lightly.
        if not q.endswith("?"):
            q = q[0].upper() + q[1:] + "?"
        yield q, a
        yielded += 1


def _load_dolly_15k(n: int, seed: int):
    """Databricks Dolly 15k — instruction-following across 8 categories.
    We keep open_qa, closed_qa, classification, information_extraction,
    summarization. Skip 'brainstorming' and 'creative_writing' (not the
    factual mode Memory model targets)."""
    from datasets import load_dataset
    ds = load_dataset("databricks/databricks-dolly-15k", split="train")
    keep = {"open_qa", "closed_qa", "classification",
            "information_extraction", "summarization", "general_qa"}
    rng = random.Random(seed + 1)
    rows = [r for r in ds if r.get("category") in keep]
    rng.shuffle(rows)
    for r in rows[:n]:
        instr = (r.get("instruction") or "").strip()
        ctx = (r.get("context") or "").strip()
        resp = (r.get("response") or "").strip()
        if not instr or not resp:
            continue
        # Fold context into the user message if present.
        q = f"{instr}\n\nContext: {ctx}" if ctx else instr
        yield q, resp


def _load_squad_v2(n: int, seed: int):
    """SQuAD v2 reading comprehension. Folds passage into the question."""
    from datasets import load_dataset
    ds = load_dataset("squad_v2", split="train", streaming=True)
    yielded = 0
    for ex in ds:
        if yielded >= n:
            return
        q = ex.get("question", "").strip()
        ctx = (ex.get("context") or "").strip()
        answers = ex.get("answers", {}).get("text", [])
        if not q or not ctx or not answers:
            continue
        a = answers[0].strip()
        if len(a) < 2:
            continue
        prompt = f"Based on the passage, {q}\n\nPassage: {ctx}"
        yield prompt, a
        yielded += 1


def _load_sciq(n: int, seed: int):
    """SciQ — science Q&A with multiple-choice + correct answer."""
    from datasets import load_dataset
    ds = load_dataset("sciq", split="train")
    rng = random.Random(seed + 2)
    rows = list(ds)
    rng.shuffle(rows)
    for r in rows[:n]:
        q = (r.get("question") or "").strip()
        a = (r.get("correct_answer") or "").strip()
        support = (r.get("support") or "").strip()
        if not q or not a:
            continue
        if support and len(support) < 800:
            # Synthesize a richer factual response from the support text.
            yield q, f"{a}. {support}"
        else:
            yield q, a


SOURCE_LOADERS = {
    "trivia_qa":  _load_trivia_qa,
    "nq_open":    _load_nq_open,
    "dolly_15k":  _load_dolly_15k,
    "squad_v2":   _load_squad_v2,
    "sciq":       _load_sciq,
}


def _load_custom(path: str):
    """Load user-supplied JSONL. Accept three shapes:
       {question, answer}, {prompt, completion}, {messages: [...]}.
    """
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "messages" in ex:
                msgs = ex["messages"]
                user_msg = next((m for m in msgs if m["role"] == "user"), None)
                asst_msg = next((m for m in reversed(msgs) if m["role"] == "assistant"), None)
                if user_msg and asst_msg:
                    yield user_msg["content"], asst_msg["content"]
            elif "question" in ex and "answer" in ex:
                yield ex["question"], ex["answer"]
            elif "prompt" in ex and "completion" in ex:
                yield ex["prompt"], ex["completion"]


def _format_row(q: str, a: str, system: str) -> dict:
    """Wrap a (query, answer) pair into the Memory chat-template."""
    return {
        "messages": [
            {"role": "system",    "content": system},
            {"role": "user",      "content": q.strip()},
            {"role": "assistant", "content": a.strip()},
        ]
    }


def main():
    p = argparse.ArgumentParser(
        description="M.0-real dataset generator (public HF Q&A → Memory chat-template)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--out", required=True, help="Output JSONL path")
    p.add_argument("--sources", default="trivia_qa,nq_open,dolly_15k,squad_v2,sciq",
                   help=f"Comma-separated source list. Available: {','.join(SOURCE_LOADERS.keys())}")
    p.add_argument("--per_source", type=int, default=20000,
                   help="Cap examples drawn from each source (default 20000 → ~80-100k total)")
    p.add_argument("--custom_jsonl", default=None,
                   help="Optional path to your own Q&A JSONL (appended to the mix)")
    p.add_argument("--system_prompt", default=MEMORY_SYSTEM,
                   help="System prompt for the Memory role (default: M.2-protocol-aligned)")
    p.add_argument("--max_query_len", type=int, default=4000,
                   help="Drop examples whose user message exceeds this char length")
    p.add_argument("--max_answer_len", type=int, default=2000,
                   help="Drop examples whose answer exceeds this char length")
    p.add_argument("--min_answer_len", type=int, default=2,
                   help="Drop examples whose answer is shorter than this")
    p.add_argument("--shuffle", action="store_true", default=True)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in sources if s not in SOURCE_LOADERS]
    if unknown:
        sys.exit(f"unknown source(s): {unknown}. Available: {list(SOURCE_LOADERS)}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[gen] sources={sources}  per_source={args.per_source}")
    print(f"[gen] system_prompt={args.system_prompt[:80]}...")

    rng = random.Random(args.seed)
    all_pairs = []

    for src in sources:
        print(f"[gen] loading {src} (cap {args.per_source})...")
        try:
            loader = SOURCE_LOADERS[src]
            kept = 0
            for q, a in loader(args.per_source, args.seed):
                if not q or not a:
                    continue
                if len(q) > args.max_query_len or len(a) > args.max_answer_len:
                    continue
                if len(a) < args.min_answer_len:
                    continue
                all_pairs.append((q, a))
                kept += 1
            print(f"[gen]   {src}: {kept} examples kept")
        except Exception as e:
            print(f"[gen]   {src}: FAILED ({type(e).__name__}: {e}) — skipping this source")
            print(f"[gen]   continuing with other sources; this source contributes 0 examples")

    if args.custom_jsonl:
        print(f"[gen] loading custom JSONL: {args.custom_jsonl}")
        kept = 0
        for q, a in _load_custom(args.custom_jsonl):
            if not q or not a:
                continue
            if len(q) > args.max_query_len or len(a) > args.max_answer_len:
                continue
            if len(a) < args.min_answer_len:
                continue
            all_pairs.append((q, a))
            kept += 1
        print(f"[gen]   custom: {kept} examples kept")

    if not all_pairs:
        sys.exit("[gen] no examples produced — check network / HF cache / source names")

    if args.shuffle:
        rng.shuffle(all_pairs)

    with open(out_path, "w", encoding="utf-8") as f:
        for q, a in all_pairs:
            row = _format_row(q, a, args.system_prompt)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[gen] wrote {len(all_pairs)} examples to {out_path}")
    print(f"[gen] next: bash run_train.sh   (will pick up DATASET={out_path})")


if __name__ == "__main__":
    main()
