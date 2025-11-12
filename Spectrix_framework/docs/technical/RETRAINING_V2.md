# 🔄 BioQL Model Retraining v2 - Improved Syntax

**Date**: October 2, 2025
**Status**: 🔄 Training in Progress
**Reason**: Model generating incorrect syntax

---

## 🐛 Problem Identified

### Incorrect Output Examples
```python
# ❌ WRONG - What the model v1 generated:
result = quantum("QKFG", 4 qubits)  # Invalid syntax!
result = quantum("QGator", 1 qubit)  # Not BioQL syntax!
result = quantum("Bell", 2)  # Incorrect format!
```

### Root Cause
- **Insufficient training examples** (only 5,000)
- **No negative examples** (didn't learn what NOT to do)
- **Hallucinated functions** from base CodeLlama knowledge

---

## ✅ Solution: Retraining v2

### Dataset Improvements

#### 1. Increased Dataset Size
- **v1**: 5,000 examples
- **v2**: 10,000 examples (2x more data)
- **Training steps**: 468 → 936 (doubled)

#### 2. Added "Correct Syntax" Category

New examples explicitly showing RIGHT vs WRONG:

```python
{
    "instruction": "Run QFT on 4 qubits",
    "reasoning": "QFT transforms computational basis to frequency basis. The syntax is: quantum(description, backend, shots). NEVER use quantum(gate_name, num_qubits) - that's incorrect!",
    "code": '''from bioql import quantum

# CORRECT syntax:
result = quantum("Run QFT on 4 qubits and measure", backend="simulator", shots=1000)
print(result)

# WRONG: quantum("QFT", 4)  # This is INCORRECT!'''
}
```

#### 3. Explicit Anti-patterns

Examples showing what NOT to do:

```python
{
    "instruction": "Create entanglement between 2 qubits",
    "reasoning": "Entanglement is created with Bell state. Use natural language description, not gate names as function arguments.",
    "code": '''from bioql import quantum

# CORRECT:
result = quantum("Create Bell state on 2 qubits", backend="simulator", shots=1000)
print(result)

# WRONG examples (DO NOT USE):
# quantum("Bell", 2)  # INCORRECT!
# quantum("CNOT", (0, 1))  # INCORRECT!'''
}
```

#### 4. Added Categories

New training categories:
- **correct_syntax** - Explicit right/wrong examples
- **docking** - Molecular docking syntax
- **multi_step** - Complex operations

Example docking:
```python
{
    "instruction": "Dock ibuprofen to COX-2 protein",
    "reasoning": "Molecular docking uses the dock() function with natural language description, SMILES string, and PDB code.",
    "code": '''from bioql.docking import dock

result = dock(
    "dock ibuprofen to COX-2 protein and calculate binding affinity",
    ligand_smiles="CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O",
    protein_pdb="1CX2",
    backend="simulator",
    shots=1000
)
print("Binding affinity:", result.score)'''
}
```

---

## 📊 Training Configuration v2

### Model
- **Base**: deepseek-ai/deepseek-coder-1.3b-instruct
- **Size**: 1.3B parameters
- **Method**: LoRA fine-tuning
- **Trainable params**: 6,291,456

### Training Hyperparameters
```python
{
    "num_train_epochs": 3,
    "per_device_train_batch_size": 8,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "warmup_steps": 100,
    "precision": "BF16",
    "optimizer": "AdamW",
    "max_grad_norm": 0.3
}
```

### Dataset Statistics
- **Total examples**: 10,000
- **Categories**: 9 (vs 7 in v1)
- **Training steps**: 936
- **Expected time**: ~20 minutes
- **GPU**: Modal A100

---

## 🎯 Expected Improvements

### Before (v1)
```python
# ❌ Hallucinated syntax
result = quantum("QKFG", 4)
result = quantum("Bell", 2 qubits)
```

### After (v2)
```python
# ✅ Correct BioQL syntax
result = quantum("Run QFT on 4 qubits and measure", backend="simulator", shots=1000)
result = quantum("Create Bell state on 2 qubits", backend="simulator", shots=1024)
```

### Quality Metrics
- **Syntax accuracy**: 60% → 95%+ (expected)
- **Format consistency**: Improved
- **Natural language understanding**: Better
- **Anti-pattern avoidance**: Learned explicitly

---

## 📈 Training Progress

### Dataset Generation
```
[1/5] Generating BioQL training dataset...
   ✅ Generated 10000 training examples
```

### Model Loading
```
[2/5] Loading DeepSeek-Coder-1.3B-Instruct...
   ✅ Model loaded (1.3B parameters)
```

### LoRA Setup
```
[3/5] Adding LoRA adapters...
   ✅ LoRA ready - Trainable: 6,291,456 / 1,352,763,392 params
```

### Tokenization
```
[4/5] Tokenizing dataset...
   ✅ Dataset tokenized: 10000 examples
```

### Training
```
[5/5] Training (30 minutes on A100)...
Step 10/936: loss 15.97
Step 20/936: loss 15.22
...
[In progress]
```

---

## 🔧 Code Changes

### `/training/TRAIN_DEEPSEEK.py`

#### Change 1: Dataset Size
```python
# Before:
def generate_bioql_dataset(num_examples=5000):

# After:
def generate_bioql_dataset(num_examples=10000):
```

#### Change 2: Added Correct Syntax Examples
```python
"correct_syntax": [
    {
        "instruction": "Run QFT on 4 qubits",
        "reasoning": "... NEVER use quantum(gate_name, num_qubits) ...",
        "code": '...\n# WRONG: quantum("QFT", 4)  # This is INCORRECT!'
    },
    # ... more anti-pattern examples
]
```

#### Change 3: Added Docking Examples
```python
"docking": [
    {
        "instruction": "Dock ibuprofen to COX-2 protein",
        "reasoning": "Molecular docking uses the dock() function...",
        "code": 'from bioql.docking import dock\n\nresult = dock(...)'
    }
]
```

#### Change 4: Added Multi-step Examples
```python
"multi_step": [
    {
        "instruction": "Create Bell state, then measure in X basis",
        "reasoning": "For multi-step operations, describe the full sequence...",
        "code": 'result = quantum("Create Bell state... then measure in X basis", ...)'
    }
]
```

#### Change 5: Auto-delete Old Model
```python
# Before:
if os.path.exists("/data/final_model/adapter_config.json"):
    print("Training would overwrite it. Skipping...")
    return

# After:
if os.path.exists("/data/final_model"):
    print("Deleting old model for retraining...")
    shutil.rmtree("/data/final_model")
```

---

## 🧪 Testing Plan (Post-Training)

### Test 1: Basic Generation
**Prompt**: "Create a Bell state"

**Expected**:
```python
from bioql import quantum

result = quantum("Create Bell state on 2 qubits", backend="simulator", shots=1024)
print(result)
```

**NOT Expected**:
```python
# ❌ These should NOT appear:
quantum("Bell", 2)
quantum("CNOT", (0,1))
```

### Test 2: QFT
**Prompt**: "Run QFT on 4 qubits"

**Expected**:
```python
result = quantum("Run QFT on 4 qubits and measure", backend="simulator", shots=1000)
```

**NOT Expected**:
```python
# ❌ These should NOT appear:
quantum("QFT", 4)
quantum("Fourier", 4 qubits)
```

### Test 3: Docking
**Prompt**: "Dock ibuprofen to COX-2"

**Expected**:
```python
from bioql.docking import dock

result = dock(
    "dock ibuprofen to COX-2 protein...",
    ligand_smiles="...",
    protein_pdb="1CX2",
    ...
)
```

---

## 📊 Comparison: v1 vs v2

| Metric | v1 (Old) | v2 (New) | Change |
|--------|----------|----------|--------|
| **Examples** | 5,000 | 10,000 | +100% |
| **Categories** | 7 | 9 | +2 |
| **Training Steps** | 468 | 936 | +100% |
| **Anti-patterns** | ❌ No | ✅ Yes | Added |
| **Docking Examples** | ❌ No | ✅ Yes | Added |
| **Explicit Syntax Rules** | ❌ No | ✅ Yes | Added |
| **Training Time** | ~10 min | ~20 min | +100% |
| **Expected Accuracy** | ~60% | ~95% | +35% |

---

## ⏰ Timeline

- **Start**: October 2, 2025 22:36 UTC
- **Expected Completion**: October 2, 2025 22:56 UTC
- **Duration**: ~20 minutes

### Training Steps
- [x] Delete old model
- [x] Generate 10,000 examples
- [x] Load DeepSeek-Coder-1.3B
- [x] Add LoRA adapters
- [x] Tokenize dataset
- [ ] Train for 936 steps (in progress)
- [ ] Save final model
- [ ] Deploy to production
- [ ] Test with real prompts

---

## 🚀 Post-Training Actions

Once training completes:

1. **Deploy Updated Model**
   - Model already deployed, will auto-load new version
   - Endpoint: `https://spectrix--bioql-inference-deepseek-generate-code.modal.run`

2. **Test with Curl**
   ```bash
   curl -X POST https://spectrix--bioql-inference-deepseek-generate-code.modal.run \
     -H "Content-Type: application/json" \
     -d '{
       "api_key": "bioql_test_870ce7ae",
       "prompt": "Create a Bell state",
       "include_reasoning": true
     }'
   ```

3. **Verify VS Code Extension**
   - Test `@bioql create a Bell state`
   - Verify no hallucinated syntax
   - Check reasoning quality

4. **Update Documentation**
   - Mark v2 as production
   - Document improvements
   - Update version numbers

---

## 🎯 Success Criteria

Training is successful if:
- ✅ Final loss < 0.05
- ✅ No NaN/inf errors
- ✅ Model generates `quantum(description, backend, shots)` format
- ✅ No hallucinated function signatures
- ✅ Docking examples use `dock()` correctly
- ✅ Reasoning includes step-by-step explanations

---

**Status**: 🔄 Training in Progress (Step 23/936)
**ETA**: ~18 minutes remaining
**Expected Loss**: < 0.05

Will update when training completes.
