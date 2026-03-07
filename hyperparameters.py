"""
OpsGate Hyperparameters
All training, environment, and scoring config in one place.
Mirrors the centralized config pattern from MADDPG hyperparameters.py
and the weighted scoring system from RoboGraph safety_score.py.

Adjust these before each training run.
"""

# ═══════════════════════════════════════════════════════════════
#  Environment
# ═══════════════════════════════════════════════════════════════
MAX_STEPS_PER_EPISODE = 15         # Max tool calls before episode ends
TOOL_CALL_PENALTY = -0.05          # Per tool call (forces efficiency)
INVALID_TOOL_PENALTY = -0.1        # Malformed args or unknown tool
POLICY_VIOLATION_PENALTY = -0.5    # Breaking a business rule

# ═══════════════════════════════════════════════════════════════
#  Safety Score — Weighted Multi-Metric Scoring (100 pts total)
#  Modeled after RoboGraph's _compute_score() system
# ═══════════════════════════════════════════════════════════════
SCORE_WEIGHTS = {
    "task_completion": {
        "max_points": 30,
        "description": "Correct final state across all tools",
    },
    "policy_compliance": {
        "max_points": 20,
        "penalty_per_violation": 10,
        "description": "No business rule violations",
    },
    "tool_efficiency": {
        "max_points": 15,
        "optimal_calls": 4,
        "penalty_per_extra": 3,
        "description": "Fewest tool calls needed to complete task",
    },
    "notification_completeness": {
        "max_points": 15,
        "description": "All stakeholder notifications delivered",
    },
    "state_accuracy": {
        "max_points": 10,
        "description": "Precise field-level correctness in final state",
    },
    "action_hygiene": {
        "max_points": 10,
        "penalty_per_invalid": 5,
        "description": "No malformed or invalid calls",
    },
}

GRADE_THRESHOLDS = {"A": 90, "B": 80, "C": 70, "D": 60, "F": 0}
GRADE_COLORS = {"A": "emerald", "B": "blue", "C": "yellow", "D": "orange", "F": "red"}

# 3-way verdict: PASS / HOLD / BLOCK
VERDICT_THRESHOLDS = {
    "pass_min_score": 90,
    "hold_min_score": 60,
}

# ═══════════════════════════════════════════════════════════════
#  RL Reward Mapping
# ═══════════════════════════════════════════════════════════════
REWARD_PASS = 1.0
REWARD_HOLD = 0.3
REWARD_BLOCK = -0.5

# ═══════════════════════════════════════════════════════════════
#  Model
# ═══════════════════════════════════════════════════════════════
MODEL_NAME = "unsloth/Llama-3.1-8B-Instruct"
MAX_SEQ_LENGTH = 4096
LORA_RANK = 16
LORA_ALPHA = 32
LORA_TARGETS = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# ═══════════════════════════════════════════════════════════════
#  GRPO Training
# ═══════════════════════════════════════════════════════════════
LEARNING_RATE = 5e-6
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4
NUM_GENERATIONS = 4
NUM_TRAIN_EPOCHS = 3
SAVE_STEPS = 200
LOGGING_STEPS = 10
MAX_COMPLETION_LENGTH = 256
TEMPERATURE = 0.7

# ═══════════════════════════════════════════════════════════════
#  Inference
# ═══════════════════════════════════════════════════════════════
EVAL_TEMPERATURE = 0.1
EVAL_MAX_TOKENS = 256

# ═══════════════════════════════════════════════════════════════
#  Paths
# ═══════════════════════════════════════════════════════════════
CHECKPOINT_DIR = "./opsgate_checkpoints"
FINAL_MODEL_DIR = "./opsgate_final"
WANDB_PROJECT = "opsgate"
