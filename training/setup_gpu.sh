#!/bin/bash
# OpsGate — GCP A100 setup script
# Run on your GCP instance after SSH-ing in
# Usage: bash setup_gpu.sh
set -e

echo "=== Verifying GPU ==="
nvidia-smi

echo "=== Installing Python packages ==="
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install unsloth trl vllm wandb
pip install openenv-core fastapi uvicorn[standard]
pip install openpipe-art

echo "=== Pre-downloading model ==="
python3 -c "
from unsloth import FastLanguageModel
model, tok = FastLanguageModel.from_pretrained(
    'unsloth/Llama-3.1-8B-Instruct',
    max_seq_length=4096,
    load_in_4bit=False
)
print('Model downloaded successfully!')
del model, tok
"

echo "=== Login to services ==="
echo "Run these manually:"
echo "  wandb login"
echo "  huggingface-cli login"
echo ""
echo "=== Setup complete! ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo "VRAM: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader)"
