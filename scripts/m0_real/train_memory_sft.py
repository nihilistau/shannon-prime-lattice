#!/usr/bin/env python3
"""
M.0-real — SFT Memory artifact training script.

Targets RunPod (or any host with a CUDA GPU + PyTorch + HF stack). Fine-tunes
a small base model (Qwen2.5-0.5B by default) on the 3-turn dialogue protocol
used by sp_daemon's /v1/dialogue endpoint:

    Turn 1 — Grounding:   context  -> grounded fact
    Turn 2 — Entity ID:   fact     -> canonical entity ID  (Memory role focus)
    Turn 3 — Synthesis:   ID + ctx -> final answer

The Memory model handles the Entity-ID step. Training data is JSONL with HF
chat-template messages. Default mode is LoRA (cheap, runs on a single 24 GB
GPU in 1-3 hours for 10k examples). Full-SFT mode also supported.

Output: a HF checkpoint at `--output_dir` containing the merged LoRA weights
(if --merge_lora) or the adapter alone. Run `export_to_sp_model.py` next to
convert to GGUF -> .sp-model via the engine's sp_transcode tool.

Usage (RunPod default container, /workspace mount):

    python train_memory_sft.py \\
        --base_model Qwen/Qwen2.5-0.5B \\
        --dataset /workspace/data/m0_real.jsonl \\
        --output_dir /workspace/output/memory-sft-v0 \\
        --epochs 3 \\
        --batch_size 16 \\
        --lr 2e-4 \\
        --merge_lora

For full SFT (no LoRA):

    python train_memory_sft.py ... --no_lora

For distributed (multi-GPU on one node):

    accelerate launch --num_processes 4 train_memory_sft.py ...
"""

import argparse
import json
import os
import sys
from pathlib import Path

# --- Imports kept lazy so --help works without the full stack installed ---

def _parse_args():
    p = argparse.ArgumentParser(
        description="M.0-real Memory model SFT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Model + data
    p.add_argument("--base_model", default="Qwen/Qwen2.5-0.5B",
                   help="HF model repo or local path (default: Qwen/Qwen2.5-0.5B)")
    p.add_argument("--dataset", required=True,
                   help="Path to JSONL training dataset (HF chat-template format)")
    p.add_argument("--eval_dataset", default=None,
                   help="Optional eval JSONL (10%% holdout if unset)")
    p.add_argument("--output_dir", required=True,
                   help="Where to write checkpoints + final model")
    p.add_argument("--max_seq_len", type=int, default=2048)

    # Training schedule
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch_size", type=int, default=16,
                   help="Per-device batch size")
    p.add_argument("--grad_accum", type=int, default=2,
                   help="Gradient accumulation steps")
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--warmup_ratio", type=float, default=0.03)
    p.add_argument("--weight_decay", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)

    # LoRA
    p.add_argument("--no_lora", action="store_true", help="Disable LoRA (full SFT)")
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--lora_alpha", type=int, default=32)
    p.add_argument("--lora_dropout", type=float, default=0.05)
    p.add_argument("--lora_targets", default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj",
                   help="Comma-separated target module names for LoRA")
    p.add_argument("--merge_lora", action="store_true",
                   help="Merge LoRA into base weights at end (single combined checkpoint)")

    # Precision / quantization
    p.add_argument("--bf16", action="store_true", default=True)
    p.add_argument("--fp16", action="store_true")
    p.add_argument("--load_4bit", action="store_true",
                   help="QLoRA: load base in 4-bit (saves VRAM, ~5%% acc drop)")
    p.add_argument("--gradient_checkpointing", action="store_true", default=True)

    # Logging
    p.add_argument("--log_steps", type=int, default=10)
    p.add_argument("--save_steps", type=int, default=500)
    p.add_argument("--eval_steps", type=int, default=500)
    p.add_argument("--save_total_limit", type=int, default=3)
    p.add_argument("--report_to", default="none",
                   help="HF report target: 'none', 'wandb', 'tensorboard'")
    p.add_argument("--run_name", default=None)

    return p.parse_args()


def _import_stack():
    """Lazy import so --help works without the dependency tree installed."""
    import torch
    import datasets
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        set_seed,
    )
    try:
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel
    except ImportError:
        LoraConfig = get_peft_model = prepare_model_for_kbit_training = PeftModel = None
    try:
        from transformers import BitsAndBytesConfig
    except ImportError:
        BitsAndBytesConfig = None
    return {
        "torch": torch,
        "datasets": datasets,
        "AutoTokenizer": AutoTokenizer,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "TrainingArguments": TrainingArguments,
        "Trainer": Trainer,
        "DataCollatorForLanguageModeling": DataCollatorForLanguageModeling,
        "set_seed": set_seed,
        "LoraConfig": LoraConfig,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "PeftModel": PeftModel,
        "BitsAndBytesConfig": BitsAndBytesConfig,
    }


def _load_dataset(stack, args):
    """Load JSONL; apply HF chat template; tokenize."""
    datasets = stack["datasets"]
    AutoTokenizer = stack["AutoTokenizer"]

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        # Use EOS as pad if no pad-token is set (common for Qwen / Llama families).
        tokenizer.pad_token = tokenizer.eos_token
    if tokenizer.chat_template is None:
        # Fall back to a minimal ChatML template if the base model didn't ship one.
        tokenizer.chat_template = (
            "{% for m in messages %}"
            "<|im_start|>{{ m['role'] }}\n{{ m['content'] }}<|im_end|>\n"
            "{% endfor %}"
            "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
        )

    raw = datasets.load_dataset("json", data_files=args.dataset, split="train")

    if args.eval_dataset:
        raw_eval = datasets.load_dataset("json", data_files=args.eval_dataset, split="train")
    else:
        split = raw.train_test_split(test_size=0.1, seed=args.seed)
        raw, raw_eval = split["train"], split["test"]

    def fmt(ex):
        msgs = ex["messages"]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    def tok(ex):
        out = tokenizer(
            ex["text"],
            max_length=args.max_seq_len,
            truncation=True,
            padding=False,
        )
        out["labels"] = out["input_ids"].copy()
        return out

    raw = raw.map(fmt, remove_columns=raw.column_names)
    raw_eval = raw_eval.map(fmt, remove_columns=raw_eval.column_names)
    raw = raw.map(tok, remove_columns=["text"], batched=False)
    raw_eval = raw_eval.map(tok, remove_columns=["text"], batched=False)

    print(f"[data] train={len(raw)}  eval={len(raw_eval)}  max_seq_len={args.max_seq_len}")
    return tokenizer, raw, raw_eval


def _load_model(stack, args, tokenizer):
    torch = stack["torch"]
    AutoModelForCausalLM = stack["AutoModelForCausalLM"]

    dtype = torch.bfloat16 if args.bf16 and not args.fp16 else (torch.float16 if args.fp16 else torch.float32)

    quant_config = None
    if args.load_4bit:
        if stack["BitsAndBytesConfig"] is None:
            sys.exit("--load_4bit requires bitsandbytes; install it first.")
        quant_config = stack["BitsAndBytesConfig"](
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=True,
        )

    print(f"[model] loading {args.base_model} dtype={dtype} 4bit={bool(quant_config)}")
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=dtype,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False  # required when gradient_checkpointing is on

    if quant_config is not None and stack["prepare_model_for_kbit_training"] is not None:
        model = stack["prepare_model_for_kbit_training"](model)

    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    if not args.no_lora:
        if stack["LoraConfig"] is None:
            sys.exit("LoRA requested but peft is not installed; pip install peft")
        targets = [t.strip() for t in args.lora_targets.split(",") if t.strip()]
        lora_cfg = stack["LoraConfig"](
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=targets,
        )
        model = stack["get_peft_model"](model, lora_cfg)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters())
        print(f"[lora] trainable={trainable:,} ({100*trainable/total:.2f}% of {total:,})")

    return model


def _collator(tokenizer):
    def _pad(batch):
        keys = ["input_ids", "labels", "attention_mask"]
        # max length in batch
        L = max(len(b["input_ids"]) for b in batch)
        pad_id = tokenizer.pad_token_id
        out = {k: [] for k in keys}
        for b in batch:
            n = len(b["input_ids"])
            pad = L - n
            out["input_ids"].append(b["input_ids"] + [pad_id] * pad)
            # labels: -100 in pad positions so loss ignores them
            out["labels"].append(b["labels"] + [-100] * pad)
            am = b.get("attention_mask", [1] * n)
            out["attention_mask"].append(am + [0] * pad)
        import torch
        return {k: torch.tensor(v) for k, v in out.items()}
    return _pad


def main():
    args = _parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    stack = _import_stack()
    stack["set_seed"](args.seed)

    tokenizer, train_ds, eval_ds = _load_dataset(stack, args)
    model = _load_model(stack, args, tokenizer)

    training_args = stack["TrainingArguments"](
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        bf16=args.bf16 and not args.fp16,
        fp16=args.fp16,
        gradient_checkpointing=args.gradient_checkpointing,
        logging_steps=args.log_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        eval_strategy="steps",
        save_total_limit=args.save_total_limit,
        load_best_model_at_end=False,
        report_to=args.report_to,
        run_name=args.run_name or f"m0-real-{Path(args.base_model).name}",
        seed=args.seed,
        dataloader_num_workers=2,
        remove_unused_columns=False,
    )

    trainer = stack["Trainer"](
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=_collator(tokenizer),
        tokenizer=tokenizer,
    )

    print("[train] starting")
    trainer.train()
    print("[train] done")

    # --- Save ---
    final_dir = os.path.join(args.output_dir, "final")
    Path(final_dir).mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(final_dir)

    if not args.no_lora and args.merge_lora:
        print("[save] merging LoRA into base weights")
        model = model.merge_and_unload()
        model.save_pretrained(final_dir, safe_serialization=True)
    else:
        model.save_pretrained(final_dir, safe_serialization=True)

    # Write a small manifest the export-to-sp-model script reads.
    manifest = {
        "base_model": args.base_model,
        "trained_on": str(Path(args.dataset).resolve()),
        "epochs": args.epochs,
        "lora": (not args.no_lora),
        "merged": (not args.no_lora and args.merge_lora),
        "max_seq_len": args.max_seq_len,
    }
    with open(os.path.join(final_dir, "m0_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[save] final checkpoint at {final_dir}")
    print(f"[next] convert HF -> GGUF then sp_transcode -> .sp-model:")
    print(f"       python convert_hf_to_gguf.py {final_dir} --outfile {final_dir}.gguf")
    print(f"       sp_transcode {final_dir}.gguf {final_dir}.sp-model")


if __name__ == "__main__":
    main()
