#!/usr/bin/env python3
<<<<<<< HEAD
"""
OpsGate GRPO Training — Unsloth + TRL on A100.

Trains Llama-3.1-8B-Instruct with GRPO using OpsGate's deterministic
reward function. Each generation is scored by the verifier (no LLM judge).

Usage:
    python training/train_grpo.py
    python training/train_grpo.py --wandb_run hackathon-v1
"""

import sys
import os
import json
import argparse
import re

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from hyperparameters import *
from tasks import TASKS
from models import ToolCall
=======
"""OpsGate GRPO Training - pure PEFT + TRL, no Unsloth"""
import sys, os, json, argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from hyperparameters import *
from tasks import TASKS
>>>>>>> bff4d20 (v2: 25 tasks + GRPO pipeline + trained adapter)
from server.tools.crm import CRMTool
from server.tools.billing import BillingTool
from server.tools.calendar import CalendarTool
from server.tools.email import EmailTool
from server.verifier import verify_episode

SYSTEM_PROMPT = """You are an enterprise operations agent with access to 4 tools: crm, billing, calendar, email.
For each tool call, respond with exactly one JSON object per line:
{"tool": "<tool_name>", "action": "<action_name>", "parameters": {<params>}}
Available actions:
- crm: get_user, update_user, add_note, log_interaction
- billing: get_invoice, issue_refund
- calendar: list_events, create_event, reschedule_event, cancel_event
- email: send
Business rules:
- Refund policy limit: $500 max. Cap at $500 if exceeded.
- Never double-refund an already-refunded invoice.
- Always notify stakeholders via email.
When done: {"tool": "system", "action": "submit", "parameters": {}}"""

<<<<<<< HEAD
# ═══════════════════════════════════════════════════════════════
#  Dataset: Convert tasks to GRPO prompts
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an enterprise operations agent with access to 4 tools: crm, billing, calendar, email.

For each tool call, respond with exactly one JSON object per line:
{"tool": "<tool_name>", "action": "<action_name>", "parameters": {<params>}}

Available actions:
- crm: get_user, update_user, add_note, log_interaction
- billing: get_invoice, issue_refund
- calendar: list_events, create_event, reschedule_event, cancel_event
- email: send

Business rules:
- Refund policy limit: $500 max per refund. Cap at $500 if requested amount exceeds this.
- Never double-refund an already-refunded invoice.
- Always notify relevant stakeholders via email after completing actions.

When done, output: {"tool": "system", "action": "submit", "parameters": {}}
"""


def build_dataset():
    """Convert TASKS into a list of prompt dicts for GRPO."""
    dataset = []
    for task in TASKS:
        prompt = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task["description"]},
        ]
        dataset.append({
            "task_id": task["id"],
            "prompt": prompt,
            "task": task,  # Keep full task for reward computation
        })
    return dataset


# ═══════════════════════════════════════════════════════════════
#  Reward Function: Run completions through OpsGate verifier
# ═══════════════════════════════════════════════════════════════

def parse_tool_calls(completion_text: str) -> list[dict]:
    """Extract JSON tool calls from model completion."""
    calls = []
    for line in completion_text.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            if "tool" in obj and "action" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            continue
    return calls


def compute_reward(completion_text: str, task: dict) -> float:
    """
    Execute parsed tool calls against fresh tool instances,
    then score with the verifier. Pure Python, no LLM judge.
    """
    calls = parse_tool_calls(completion_text)

    if not calls:
        return REWARD_BLOCK  # No valid tool calls = block

    # Fresh tool instances
    crm = CRMTool()
    billing = BillingTool()
    calendar = CalendarTool()
    email_tool = EmailTool()

    # Seed
    seed = task["seed"]
    if seed.get("users"):
        crm.seed(seed["users"])
    if seed.get("invoices"):
        billing.seed(seed["invoices"])
    if seed.get("events"):
        calendar.seed(seed["events"])

    tool_map = {
        "crm": crm, "billing": billing,
        "calendar": calendar, "email": email_tool,
    }

    invalid_calls = 0
    policy_violations = 0
    tool_calls_made = 0

    for call in calls:
        tool_name = call.get("tool", "")
        action = call.get("action", "")
        params = call.get("parameters", {})

        if tool_name == "system" and action == "submit":
            break

        tool = tool_map.get(tool_name)
        if not tool:
            invalid_calls += 1
            continue

        tool_calls_made += 1
        result = tool.execute(action, params)

        if "error" in result:
            if result.get("policy_violated"):
                policy_violations += 1
            else:
                invalid_calls += 1

    # Snapshot and verify
    snapshots = {
        "crm": crm.snapshot(),
        "billing": billing.snapshot(),
        "calendar": calendar.snapshot(),
        "email": email_tool.snapshot(),
    }

    reward, violations, verdict = verify_episode(
        target=task["target"],
        snapshots=snapshots,
        policy_violations=policy_violations,
        invalid_calls=invalid_calls,
        tool_calls_made=max(tool_calls_made, 1),
    )

    return reward


def reward_fn(completions: list[list[dict]], prompts: list[list[dict]] = None, **kwargs) -> list[float]:
    """
    GRPO reward function. Called by TRL's GRPOTrainer.

    Args:
        completions: List of completions, each is a list of message dicts
                     with 'role' and 'content' keys.
        prompts: The original prompts (not used directly here).
    Returns:
        List of float rewards, one per completion.
    """
    rewards = []
    for i, completion_messages in enumerate(completions):
        # Extract text from the assistant's completion
        if isinstance(completion_messages, list):
            text = " ".join(
                m.get("content", "") for m in completion_messages
                if isinstance(m, dict) and m.get("role") == "assistant"
            )
            if not text:
                # Might be a single string or the content directly
                text = str(completion_messages)
        else:
            text = str(completion_messages)

        # Determine which task this belongs to
        task_idx = (i // NUM_GENERATIONS) % len(TASKS)
        task = TASKS[task_idx]

        reward = compute_reward(text, task)
        rewards.append(float(reward))

    return rewards


# ═══════════════════════════════════════════════════════════════
#  Training Loop
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="OpsGate GRPO Training")
    parser.add_argument("--wandb_run", type=str, default="opsgate-grpo-v1")
    parser.add_argument("--no_wandb", action="store_true")
    args = parser.parse_args()

    print("═" * 60)
    print("  OpsGate GRPO Training")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Tasks: {len(TASKS)} ({sum(1 for t in TASKS if t['id'].startswith('trap_'))} adversarial)")
    print(f"  LoRA: rank={LORA_RANK}, alpha={LORA_ALPHA}")
    print(f"  Batch: {BATCH_SIZE} × {GRADIENT_ACCUMULATION_STEPS} accum × {NUM_GENERATIONS} gens")
    print(f"  LR: {LEARNING_RATE}, Epochs: {NUM_TRAIN_EPOCHS}")
    print("═" * 60)

    # ── W&B ──
    if not args.no_wandb:
        import wandb
        wandb.init(project=WANDB_PROJECT, name=args.wandb_run)

    # ── Load model with Unsloth ──
    print("\n→ Loading model with Unsloth...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,  # Auto-detect (bf16 on A100)
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=LORA_TARGETS,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # ── Build dataset ──
    print("→ Building dataset from tasks...")
    raw_data = build_dataset()

    # Convert to HF Dataset format
    from datasets import Dataset

    hf_data = Dataset.from_list([
        {"prompt": item["prompt"]} for item in raw_data
    ])

    print(f"  Dataset: {len(hf_data)} examples")

    # ── Configure GRPO Trainer ──
    print("→ Configuring GRPO trainer...")
    from trl import GRPOConfig, GRPOTrainer

    training_config = GRPOConfig(
        output_dir=CHECKPOINT_DIR,
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        num_generations=NUM_GENERATIONS,
        num_train_epochs=NUM_TRAIN_EPOCHS,
        max_completion_length=MAX_COMPLETION_LENGTH,
        save_steps=SAVE_STEPS,
        logging_steps=LOGGING_STEPS,
        temperature=TEMPERATURE,
        bf16=True,
        report_to="wandb" if not args.no_wandb else "none",
        remove_unused_columns=False,
        log_on_each_node=False,
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        config=training_config,
        train_dataset=hf_data,
        reward_funcs=reward_fn,
    )

    # ── Train ──
    print("\n→ Starting GRPO training...")
    print("  (Each generation is scored by OpsGate verifier — no LLM judge)")
    print("")

    trainer.train()

    # ── Save ──
    print(f"\n→ Saving final model to {FINAL_MODEL_DIR}...")
    model.save_pretrained(FINAL_MODEL_DIR)
    tokenizer.save_pretrained(FINAL_MODEL_DIR)

    # ── Quick eval ──
    print("\n→ Running quick eval on adversarial tasks...")
    FastLanguageModel.for_inference(model)

    trap_tasks = [t for t in TASKS if t["id"].startswith("trap_")]
    pass_count = 0

    for task in trap_tasks:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task["description"]},
        ]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to(model.device)

        import torch
        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs,
                max_new_tokens=EVAL_MAX_TOKENS,
                temperature=EVAL_TEMPERATURE,
                do_sample=True,
            )

        completion = tokenizer.decode(outputs[0][inputs.shape[-1]:], skip_special_tokens=True)
        reward = compute_reward(completion, task)

        verdict = "PASS" if reward >= REWARD_PASS else "HOLD" if reward >= REWARD_HOLD else "BLOCK"
        icon = "✅" if verdict == "PASS" else "⚠️" if verdict == "HOLD" else "❌"
        print(f"  {icon} {task['id']}: reward={reward:.2f} ({verdict})")

        if verdict == "PASS":
            pass_count += 1

    print(f"\n  Adversarial PASS rate: {pass_count}/{len(trap_tasks)}")

    if not args.no_wandb:
        wandb.log({"adversarial_pass_rate": pass_count / len(trap_tasks)})
        wandb.finish()

    print("\n═" * 60)
    print("  ✅ Training complete.")
    print(f"  Model saved to: {FINAL_MODEL_DIR}")
    print("═" * 60)
=======
def build_dataset():
    return [{"prompt": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": t["description"]}], "task": t} for t in TASKS]

def parse_tool_calls(text):
    calls = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"): continue
        try:
            obj = json.loads(line)
            if "tool" in obj and "action" in obj: calls.append(obj)
        except json.JSONDecodeError: continue
    return calls

def compute_reward(text, task):
    calls = parse_tool_calls(text)
    if not calls: return REWARD_BLOCK
    crm, billing, calendar, email_tool = CRMTool(), BillingTool(), CalendarTool(), EmailTool()
    seed = task["seed"]
    if seed.get("users"): crm.seed(seed["users"])
    if seed.get("invoices"): billing.seed(seed["invoices"])
    if seed.get("events"): calendar.seed(seed["events"])
    tool_map = {"crm": crm, "billing": billing, "calendar": calendar, "email": email_tool}
    invalid_calls = policy_violations = tool_calls_made = 0
    for call in calls:
        tn, act, params = call.get("tool",""), call.get("action",""), call.get("parameters",{})
        if tn == "system" and act == "submit": break
        tool = tool_map.get(tn)
        if not tool: invalid_calls += 1; continue
        tool_calls_made += 1
        result = tool.execute(act, params)
        if "error" in result:
            if result.get("policy_violated"): policy_violations += 1
            else: invalid_calls += 1
    snapshots = {"crm": crm.snapshot(), "billing": billing.snapshot(), "calendar": calendar.snapshot(), "email": email_tool.snapshot()}
    reward, _, _ = verify_episode(target=task["target"], snapshots=snapshots, policy_violations=policy_violations, invalid_calls=invalid_calls, tool_calls_made=max(tool_calls_made,1))
    return reward

def reward_fn(completions, **kwargs):
    rewards = []
    for i, msgs in enumerate(completions):
        text = " ".join(m.get("content","") for m in msgs if isinstance(m,dict) and m.get("role")=="assistant") if isinstance(msgs,list) else str(msgs)
        if not text: text = str(msgs)
        rewards.append(float(compute_reward(text, TASKS[(i // NUM_GENERATIONS) % len(TASKS)])))
    return rewards

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wandb_run", default="opsgate-grpo-v1")
    parser.add_argument("--no_wandb", action="store_true")
    args = parser.parse_args()
    print("="*60)
    print(f"  OpsGate GRPO | {MODEL_NAME} | {len(TASKS)} tasks")
    print("="*60)
    if not args.no_wandb:
        import wandb; wandb.init(project=WANDB_PROJECT, name=args.wandb_run)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model

    print("\n-> Loading model with bitsandbytes 4-bit...")
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, quantization_config=bnb_config, device_map="auto", torch_dtype=torch.bfloat16)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    print("-> Applying LoRA...")
    lora_config = LoraConfig(r=LORA_RANK, lora_alpha=LORA_ALPHA, target_modules=LORA_TARGETS, lora_dropout=0, bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    model.enable_input_require_grads()

    from datasets import Dataset
    hf_data = Dataset.from_list([{"prompt": d["prompt"]} for d in build_dataset()])
    print(f"  Dataset: {len(hf_data)} examples")

    from trl import GRPOConfig, GRPOTrainer
    config = GRPOConfig(output_dir=CHECKPOINT_DIR, learning_rate=LEARNING_RATE, per_device_train_batch_size=BATCH_SIZE, gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS, num_generations=NUM_GENERATIONS, num_train_epochs=NUM_TRAIN_EPOCHS, max_completion_length=512, save_steps=SAVE_STEPS, logging_steps=LOGGING_STEPS, temperature=TEMPERATURE, bf16=True, report_to="wandb" if not args.no_wandb else "none", remove_unused_columns=False, log_on_each_node=False, gradient_checkpointing=True)
    trainer = GRPOTrainer(model=model, processing_class=tokenizer, args=config, train_dataset=hf_data, reward_funcs=reward_fn)
    print("\n-> Training...")
    trainer.train()
    print(f"\n-> Saving to {FINAL_MODEL_DIR}")
    model.save_pretrained(FINAL_MODEL_DIR); tokenizer.save_pretrained(FINAL_MODEL_DIR)
>>>>>>> bff4d20 (v2: 25 tasks + GRPO pipeline + trained adapter)

    print("\n-> Eval adversarial tasks...")
    model.eval()
    pc = 0
    for t in [t for t in TASKS if t["id"].startswith("trap_")]:
        msgs = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":t["description"]}]
        inp = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(model.device)
        with torch.no_grad(): out = model.generate(input_ids=inp, max_new_tokens=EVAL_MAX_TOKENS, temperature=EVAL_TEMPERATURE, do_sample=True)
        r = compute_reward(tokenizer.decode(out[0][inp.shape[-1]:], skip_special_tokens=True), t)
        v = "PASS" if r >= REWARD_PASS else "HOLD" if r >= REWARD_HOLD else "BLOCK"
        print(f"  {t['id']}: {r:.2f} ({v})"); pc += (v=="PASS")
    print(f"\n  Pass rate: {pc}/{len([t for t in TASKS if t['id'].startswith('trap_')])}\n" + "="*60)

if __name__ == "__main__":
    main()

# #!/usr/bin/env python3
# """
# OpsGate GRPO Training Script

# Post-trains a base LLM to improve enterprise tool orchestration
# using OpenEnv environment + TRL GRPOTrainer + Unsloth.

# Run on GCP A100:
#     gcloud compute ssh apex-train --zone=us-west1-b
#     cd opsgate
#     python training/train_grpo.py

# Tracks scores over episodes, saves checkpoints, generates plots.
# Modeled after MADDPG training loop: rolling average, early stopping,
# periodic checkpointing, score evolution chart.
# """

# import json
# import os
# import sys
# import time
# from collections import deque

# import numpy as np
# import torch

# # Add project root to path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# from hyperparameters import (
#     MODEL_NAME, MAX_SEQ_LENGTH, LORA_RANK, LORA_ALPHA, LORA_TARGETS,
#     LEARNING_RATE, BATCH_SIZE, GRADIENT_ACCUMULATION_STEPS,
#     NUM_GENERATIONS, NUM_TRAIN_EPOCHS, SAVE_STEPS, LOGGING_STEPS,
#     MAX_COMPLETION_LENGTH, TEMPERATURE, EVAL_TEMPERATURE,
#     CHECKPOINT_DIR, FINAL_MODEL_DIR, WANDB_PROJECT,
#     MAX_STEPS_PER_EPISODE,
# )
# from tasks import TASKS


# # ═══════════════════════════════════════════════════════════════
# #  System Prompt (what the agent sees every episode)
# # ═══════════════════════════════════════════════════════════════

# SYSTEM_PROMPT = """You are an enterprise operations agent. You have access to 4 tools:

# 1. CRM: get_user, update_user, add_note, log_interaction, list_users
# 2. Billing: get_invoice, list_invoices, issue_refund, cancel_subscription
# 3. Calendar: list_events, create_event, cancel_event, reschedule_event
# 4. Email: send, list_sent

# IMPORTANT POLICIES:
# - Refunds over $500 require manager approval. Issue partial refund of $500 max.
# - Always update CRM status when a user churns or is offboarded.
# - Always notify account managers of cancellations and escalations.
# - Always add a CRM note explaining significant account changes.

# Respond with a JSON tool call:
# {"tool": "crm", "action": "get_user", "parameters": {"user_id": 101}}

# When you have completed all steps, respond with:
# {"tool": "system", "action": "submit", "parameters": {}}
# """


# # ═══════════════════════════════════════════════════════════════
# #  Tool Call Parser
# # ═══════════════════════════════════════════════════════════════

# def parse_tool_call(response: str) -> dict:
#     """Extract JSON tool call from model response.

#     Returns dict with tool, action, parameters keys.
#     Raises ValueError if no valid JSON found.
#     """
#     # Find JSON in response
#     start = response.find("{")
#     end = response.rfind("}") + 1
#     if start == -1 or end == 0:
#         raise ValueError("No JSON found in response")
#     data = json.loads(response[start:end])
#     if "tool" not in data or "action" not in data:
#         raise ValueError("JSON missing 'tool' or 'action' key")
#     return data


# # ═══════════════════════════════════════════════════════════════
# #  Environment Runner (one episode)
# # ═══════════════════════════════════════════════════════════════

# def run_episode(model, tokenizer, task: dict, env_tools: dict) -> dict:
#     """Run one episode: agent interacts with tools until done.

#     Returns dict with: reward, score, grade, verdict, steps, conversation.
#     """
#     from server.tools.crm import CRMTool
#     from server.tools.billing import BillingTool
#     from server.tools.calendar import CalendarTool
#     from server.tools.email import EmailTool
#     from server.verifier import verify_episode

#     # Initialize fresh tools
#     crm = CRMTool()
#     billing = BillingTool()
#     calendar = CalendarTool()
#     email = EmailTool()

#     # Seed data
#     seed = task["seed"]
#     if seed.get("users"):
#         crm.seed(seed["users"])
#     if seed.get("invoices"):
#         billing.seed(seed["invoices"])
#     if seed.get("events"):
#         calendar.seed(seed["events"])

#     tool_map = {"crm": crm, "billing": billing, "calendar": calendar, "email": email}

#     # Build conversation
#     messages = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": task["description"]},
#     ]

#     total_step_reward = 0.0
#     steps = 0
#     invalid_calls = 0
#     policy_violations = 0
#     done = False

#     for step in range(MAX_STEPS_PER_EPISODE):
#         # Generate model response
#         input_text = tokenizer.apply_chat_template(
#             messages, tokenize=False, add_generation_prompt=True
#         )
#         inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

#         with torch.no_grad():
#             outputs = model.generate(
#                 **inputs,
#                 max_new_tokens=MAX_COMPLETION_LENGTH,
#                 do_sample=True,
#                 temperature=TEMPERATURE,
#             )

#         response = tokenizer.decode(
#             outputs[0][inputs["input_ids"].shape[1]:],
#             skip_special_tokens=True
#         )

#         steps += 1

#         # Parse tool call
#         try:
#             tool_call = parse_tool_call(response)
#         except (ValueError, json.JSONDecodeError):
#             invalid_calls += 1
#             total_step_reward -= 0.1
#             messages.append({"role": "assistant", "content": response})
#             messages.append({"role": "user", "content": '{"error": "Invalid JSON. Respond with valid tool call JSON."}'})
#             continue

#         # Check for submit
#         if tool_call.get("action") == "submit":
#             done = True
#             break

#         # Execute tool call
#         tool = tool_map.get(tool_call.get("tool"))
#         if not tool:
#             invalid_calls += 1
#             total_step_reward -= 0.1
#             result = {"error": f"Unknown tool: {tool_call.get('tool')}"}
#         else:
#             result = tool.execute(tool_call["action"], tool_call.get("parameters", {}))
#             total_step_reward -= 0.05  # per-call penalty
#             if result.get("policy_violated"):
#                 policy_violations += 1

#         messages.append({"role": "assistant", "content": response})
#         messages.append({"role": "user", "content": json.dumps(result)})

#     # Verify final state
#     snapshots = {
#         "crm": crm.snapshot(),
#         "billing": billing.snapshot(),
#         "calendar": calendar.snapshot(),
#         "email": email.snapshot(),
#     }

#     reward, violations, verdict = verify_episode(
#         target=task["target"],
#         snapshots=snapshots,
#         policy_violations=policy_violations,
#         invalid_calls=invalid_calls,
#         tool_calls_made=steps,
#     )

#     return {
#         "reward": reward,
#         "score": verdict.get("score", 0),
#         "grade": verdict.get("grade", "F"),
#         "verdict": verdict.get("decision", "BLOCK"),
#         "steps": steps,
#         "invalid_calls": invalid_calls,
#         "policy_violations": policy_violations,
#         "violations": violations,
#     }


# # ═══════════════════════════════════════════════════════════════
# #  Baseline Evaluation
# # ═══════════════════════════════════════════════════════════════

# def evaluate(model, tokenizer, tasks: list, label: str = "Eval") -> dict:
#     """Run all tasks and compute aggregate metrics."""
#     results = []
#     for task in tasks:
#         result = run_episode(model, tokenizer, task, {})
#         results.append(result)

#     scores = [r["score"] for r in results]
#     rewards = [r["reward"] for r in results]
#     pass_count = sum(1 for r in results if r["verdict"] == "PASS")
#     hold_count = sum(1 for r in results if r["verdict"] == "HOLD")
#     block_count = sum(1 for r in results if r["verdict"] == "BLOCK")

#     avg_score = np.mean(scores)
#     avg_reward = np.mean(rewards)
#     pass_rate = pass_count / len(results) * 100

#     print(f"\n{'='*60}")
#     print(f"  {label} Results")
#     print(f"{'='*60}")
#     print(f"  Avg Score:  {avg_score:.1f}/100")
#     print(f"  Avg Reward: {avg_reward:.3f}")
#     print(f"  Pass Rate:  {pass_rate:.1f}% ({pass_count}/{len(results)})")
#     print(f"  Verdicts:   {pass_count} PASS | {hold_count} HOLD | {block_count} BLOCK")
#     print(f"{'='*60}")

#     for r, t in zip(results, tasks):
#         icon = "✅" if r["verdict"] == "PASS" else "⚠️" if r["verdict"] == "HOLD" else "❌"
#         print(f"  {icon} {t['id']}: {r['verdict']} | Score: {r['score']} | Steps: {r['steps']}")

#     return {
#         "avg_score": avg_score,
#         "avg_reward": avg_reward,
#         "pass_rate": pass_rate,
#         "pass_count": pass_count,
#         "results": results,
#     }


# # ═══════════════════════════════════════════════════════════════
# #  Score Plot (like MADDPG model_01.png)
# # ═══════════════════════════════════════════════════════════════

# def plot_training(scores: list, filename: str = "training_scores.png"):
#     """Save score evolution chart."""
#     try:
#         import matplotlib
#         matplotlib.use("Agg")
#         import matplotlib.pyplot as plt

#         fig, ax = plt.subplots(figsize=(10, 6))
#         ax.plot(range(1, len(scores) + 1), scores, color="darkblue", alpha=0.6, label="Episode Score")

#         # Rolling average
#         window = min(20, len(scores))
#         if len(scores) >= window:
#             rolling = [np.mean(scores[max(0, i - window):i + 1]) for i in range(len(scores))]
#             ax.plot(range(1, len(rolling) + 1), rolling, color="red", linewidth=2, label=f"Rolling Avg ({window})")

#         ax.set_xlabel("Episode", fontsize=14)
#         ax.set_ylabel("Safety Score (0-100)", fontsize=14)
#         ax.set_title("OpsGate — Training Score Evolution", fontsize=16)
#         ax.legend()
#         ax.grid(True, alpha=0.3)
#         fig.tight_layout()
#         fig.savefig(filename, dpi=150)
#         plt.close(fig)
#         print(f"  📊 Training plot saved: {filename}")
#     except ImportError:
#         print("  ⚠️  matplotlib not available, skipping plot")


# # ═══════════════════════════════════════════════════════════════
# #  Main Training Loop
# # ═══════════════════════════════════════════════════════════════

# def main():
#     from unsloth import FastLanguageModel

#     print("=" * 60)
#     print("  OpsGate — GRPO Post-Training")
#     print(f"  Model: {MODEL_NAME}")
#     print(f"  Tasks: {len(TASKS)}")
#     print("=" * 60)

#     # ── Load model via Unsloth ──
#     print("\n  Loading model...")
#     model, tokenizer = FastLanguageModel.from_pretrained(
#         model_name=MODEL_NAME,
#         max_seq_length=MAX_SEQ_LENGTH,
#         load_in_4bit=False,
#     )

#     model = FastLanguageModel.get_peft_model(
#         model,
#         r=LORA_RANK,
#         target_modules=LORA_TARGETS,
#         lora_alpha=LORA_ALPHA,
#         use_gradient_checkpointing="unsloth",
#     )
#     print("  ✅ Model loaded")

#     # ── Create checkpoint dir ──
#     os.makedirs(CHECKPOINT_DIR, exist_ok=True)

#     # ── Baseline evaluation ──
#     print("\n  Running baseline evaluation...")
#     baseline = evaluate(model, tokenizer, TASKS, label="BASELINE")

#     # ── Training loop ──
#     # (Modeled after MADDPG: rolling window, periodic save, early stop)
#     NB_EPISODES = len(TASKS) * NUM_TRAIN_EPOCHS * NUM_GENERATIONS
#     EARLY_STOP_SCORE = 85.0  # Stop if avg score reaches this
#     CHECKPOINT_EVERY = 50    # Save every N episodes

#     scores_deque = deque(maxlen=100)
#     all_scores = []
#     all_rewards = []

#     print(f"\n  Starting training ({NB_EPISODES} episodes)...")
#     start_time = time.time()

#     for i_episode in range(1, NB_EPISODES + 1):
#         # Pick task (round-robin)
#         task = TASKS[(i_episode - 1) % len(TASKS)]

#         # Run episode
#         result = run_episode(model, tokenizer, task, {})

#         # Track scores
#         episode_score = result["score"]
#         all_scores.append(episode_score)
#         all_rewards.append(result["reward"])
#         scores_deque.append(episode_score)
#         avg_score = np.mean(scores_deque)

#         # Display progress
#         print(f"\rEpisode {i_episode}\tAvg Score: {avg_score:.1f}\t"
#               f"Episode: {episode_score:.0f} ({result['verdict']})\t"
#               f"Steps: {result['steps']}",
#               end="")

#         if i_episode % 100 == 0:
#             elapsed = time.time() - start_time
#             print(f"\rEpisode {i_episode}\tAvg Score: {avg_score:.1f}\t"
#                   f"Time: {elapsed:.0f}s\t"
#                   f"Pass rate: {sum(1 for s in scores_deque if s >= 90) / len(scores_deque) * 100:.0f}%")

#         # Periodic checkpoint
#         if i_episode % CHECKPOINT_EVERY == 0:
#             ckpt_path = os.path.join(CHECKPOINT_DIR, f"checkpoint_{i_episode}")
#             model.save_pretrained(ckpt_path)
#             tokenizer.save_pretrained(ckpt_path)
#             print(f"  💾 Checkpoint saved: {ckpt_path}")

#         # Early stopping
#         if i_episode > 100 and avg_score >= EARLY_STOP_SCORE:
#             print(f"\n  🎯 Early stop: avg score {avg_score:.1f} >= {EARLY_STOP_SCORE}")
#             break

#     # ── Save final model ──
#     print(f"\n  Saving final model to {FINAL_MODEL_DIR}...")
#     os.makedirs(FINAL_MODEL_DIR, exist_ok=True)
#     model.save_pretrained(FINAL_MODEL_DIR)
#     tokenizer.save_pretrained(FINAL_MODEL_DIR)

#     # ── Post-training evaluation ──
#     print("\n  Running post-training evaluation...")
#     post_train = evaluate(model, tokenizer, TASKS, label="POST-TRAINING")

#     # ── Generate plot ──
#     plot_training(all_scores)

#     # ── Save scores to file ──
#     with open("training_scores.txt", "w") as f:
#         f.write(json.dumps({"scores": all_scores, "rewards": all_rewards}))
#     print("  📄 Scores saved: training_scores.txt")

#     # ── Print delta ──
#     print("\n" + "=" * 60)
#     print("  THE DELTA (your winning slide)")
#     print("=" * 60)
#     print(f"  Baseline avg score:     {baseline['avg_score']:.1f}/100")
#     print(f"  Post-trained avg score: {post_train['avg_score']:.1f}/100")
#     print(f"  Improvement:            +{post_train['avg_score'] - baseline['avg_score']:.1f} points")
#     print(f"  Baseline pass rate:     {baseline['pass_rate']:.1f}%")
#     print(f"  Post-trained pass rate: {post_train['pass_rate']:.1f}%")
#     print("=" * 60)


# if __name__ == "__main__":
#     main()
