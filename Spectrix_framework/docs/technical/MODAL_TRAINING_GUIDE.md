# BioQL Foundational Model - Modal Training Guide

## Setup Complete! ✅

You have Modal configured and ready to use GPUs in the cloud.

## Quick Start

### 1. Train Model on Modal GPU (A100)

```bash
# Train with default settings (10K examples, TinyLlama, 3 epochs)
modal run modal_train.py

# Train with more examples
modal run modal_train.py --num-examples 50000

# Train with larger model (requires more GPU memory/time)
modal run modal_train.py --model mistralai/Mistral-7B-v0.1 --epochs 5

# Train with LLaMA-2 (requires HuggingFace token)
modal run modal_train.py --model meta-llama/Llama-2-7b-hf
```

### 2. Test Trained Model

```bash
# Test the model
modal run modal_train.py --test-only
```

### 3. Deploy Model as API

```bash
# Deploy the model as REST API
modal deploy modal_serve.py

# Test the deployed API
modal run modal_serve.py --prompt "Create a Bell state"
```

## What Happens During Training

```
[1/4] Generating training dataset
  → Creates 10,000 (prompt → BioQL code) pairs
  → Saves to Modal volume

[2/4] Configuring training
  → Loads base model (TinyLlama/Mistral/LLaMA)
  → Adds LoRA adapters (efficient fine-tuning)
  → Configures QLoRA (4-bit quantization)

[3/4] Training model
  → Fine-tunes on BioQL dataset
  → Takes 1-4 hours on A100 GPU
  → Saves checkpoints to Modal volume

[4/4] Testing model
  → Generates test code
  → Validates model works
```

## GPU Options

### TinyLlama-1.1B (Default - Fast & Cheap)
- **Time**: ~30-60 minutes
- **Cost**: ~$0.50-1.00
- **Quality**: Good for testing
```bash
modal run modal_train.py
```

### Mistral-7B (Better Quality)
- **Time**: ~2-3 hours
- **Cost**: ~$2-4
- **Quality**: Production-ready
```bash
modal run modal_train.py --model mistralai/Mistral-7B-v0.1 --num-examples 50000
```

### LLaMA-2-7B (Best Quality)
- **Time**: ~2-4 hours
- **Cost**: ~$2-5
- **Quality**: Best
- **Requires**: HuggingFace token
```bash
# Set HF token first
export HF_TOKEN=your_token_here

modal run modal_train.py --model meta-llama/Llama-2-7b-hf --num-examples 100000
```

## Cost Estimates

Modal pricing (approximate):
- **A100 GPU**: ~$1.10/hour
- **T4 GPU**: ~$0.20/hour (for inference)

Training costs:
- **10K examples, TinyLlama**: ~$0.50-1.00
- **50K examples, Mistral-7B**: ~$3-5
- **100K examples, LLaMA-2-7B**: ~$5-8

## After Training

### Option 1: Use via Modal API

```bash
# Deploy as API
modal deploy modal_serve.py

# Get API endpoint
modal app list

# Use the API
curl -X POST https://your-modal-url/api_generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a Bell state"}'
```

### Option 2: Download Model to Local

```bash
# Download from Modal volume
modal volume get bioql-training-data bioql_model_output ./local_model

# Use locally (slow without GPU)
python
>>> from bioql.llm.models.inference import quick_inference
>>> code = quick_inference(
...     prompt="Create a Bell state",
...     model_path="./local_model"
... )
```

### Option 3: Keep on Modal, Call Remotely

```python
import modal

# Connect to deployed model
BioQLAPI = modal.Cls.lookup("bioql-model-api", "BioQLModelAPI")

# Generate code
result = BioQLAPI().generate.remote("Create a Bell state")
print(result["code"])
```

## Monitoring Training

Modal provides a web dashboard:
```
https://modal.com/apps
```

You'll see:
- Real-time logs
- GPU usage
- Training progress
- Costs

## Troubleshooting

### Out of Memory
```bash
# Use smaller batch size
modal run modal_train.py --num-examples 5000
```

### Training Too Slow
```bash
# Use smaller model
modal run modal_train.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### Model Not Generating Good Code
```bash
# Train with more examples and epochs
modal run modal_train.py --num-examples 100000 --epochs 10
```

## Next Steps

1. **Start with small test**: `modal run modal_train.py` (10K examples)
2. **Validate quality**: `modal run modal_train.py --test-only`
3. **Scale up**: `modal run modal_train.py --num-examples 100000 --model mistralai/Mistral-7B-v0.1`
4. **Deploy API**: `modal deploy modal_serve.py`

## Files Created

- `modal_train.py` - Training script for Modal
- `modal_serve.py` - API serving script for Modal
- `MODAL_TRAINING_GUIDE.md` - This guide

## Ready to Start?

```bash
# Start training now!
modal run modal_train.py
```

This will:
1. Spin up an A100 GPU on Modal
2. Generate 10,000 training examples
3. Fine-tune TinyLlama on BioQL
4. Test the model
5. Save to Modal volume

Total time: ~30-60 minutes
Total cost: ~$0.50-1.00

---

**Questions?** Check Modal logs at: https://modal.com/apps
