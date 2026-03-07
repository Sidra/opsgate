#!/usr/bin/env python3
"""
OpsGate Baseline Evaluation

Run a model (base or post-trained) against all 15 tasks.
Outputs scores, verdicts, and saves results for the delta slide.

Usage:
    python training/eval_baseline.py                          # base model
    python training/eval_baseline.py ./opsgate_final          # post-trained
    python training/eval_baseline.py unsloth/Qwen2.5-7B-Instruct  # alternative model
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from training.train_grpo import evaluate, TASKS


def main():
    from unsloth import FastLanguageModel
    from hyperparameters import MODEL_NAME, MAX_SEQ_LENGTH

    model_path = sys.argv[1] if len(sys.argv) > 1 else MODEL_NAME
    label = "POST-TRAINED" if "final" in model_path or "checkpoint" in model_path else "BASELINE"

    print(f"  Loading model: {model_path}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=False,
    )
    print(f"  ✅ Model loaded")

    results = evaluate(model, tokenizer, TASKS, label=label)

    # Save results
    outfile = f"eval_{label.lower()}.json"
    with open(outfile, "w") as f:
        json.dump({
            "model": model_path,
            "label": label,
            "avg_score": results["avg_score"],
            "avg_reward": results["avg_reward"],
            "pass_rate": results["pass_rate"],
            "pass_count": results["pass_count"],
        }, f, indent=2)
    print(f"\n  📄 Results saved: {outfile}")


if __name__ == "__main__":
    main()
