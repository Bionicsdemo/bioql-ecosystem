# CRISPR-QAI Quantum Experiment - Complete Workflow
## BioQL 5.4.3 Autonomous Agent Prompt

---

## 🎯 MISSION

Execute a complete in-silico CRISPR guide design experiment using quantum computing. Rank guide RNAs, predict off-targets, estimate binding energies, and generate a comprehensive analysis report. **Simulation-only - no wet-lab procedures.**

---

## 📋 EXPERIMENT CONFIGURATION

```json
{
  "experiment_id": "CRISPRQAI-2025-10-08-RUN1",
  "seed": 42,
  "engine": "auto",
  "model": "ising",
  "target_fasta": "examples/toy_cas9_target.fasta",
  "guides_csv": "examples/toy_guides.csv",
  "mutations_jsonl": "examples/toy_mutations.jsonl",
  "top_k": 12,
  "pam": "NGG",
  "output_dir": "runs/CRISPRQAI-2025-10-08-RUN1",
  "report_name": "report_CRISPRQAI_experiment.md",
  "save_artifacts": true,
  "strict_safety": true
}
```

---

## 🔬 WORKFLOW STEPS

### Step 1: Safety & Initialization
- Set random seed: `42` (deterministic results)
- Activate safety mode: simulation-only
- Select quantum backend: `auto` (Braket → Qiskit → Simulator)
- Initialize Ising model for gRNA-DNA energy calculations

### Step 2: Data Preparation
- Load target DNA from: `examples/toy_cas9_target.fasta`
- Load candidate guides from: `examples/toy_guides.csv`
- Load mutation variants from: `examples/toy_mutations.jsonl`
- If guides missing: auto-generate with PAM sequence `NGG`
- Validate all input sequences (ATCG only)

### Step 3: Energy Calculation
**Command:**
```bash
bioql-crispr score-energy \
  --ref examples/toy_cas9_target.fasta \
  --edit examples/toy_cas9_target.fasta \
  --engine auto \
  --model ising \
  --seed 42 \
  --out runs/CRISPRQAI-2025-10-08-RUN1/energy.json
```

**Purpose:** Calculate quantum collapse energy for each guide-target pair using Ising Hamiltonian model.

**Output:** `energy.json` with energy scores, confidence levels, and runtime metrics.

### Step 4: Guide Ranking
**Command:**
```bash
bioql-crispr rank-guides \
  --target examples/toy_cas9_target.fasta \
  --guides examples/toy_guides.csv \
  --engine auto \
  --top 12 \
  --out runs/CRISPRQAI-2025-10-08-RUN1/ranked.csv
```

**Purpose:** Rank all candidate guides by composite score (energy + GC content + complexity).

**Output:** `ranked.csv` with top 12 guides, scores, and metadata.

### Step 5: Off-Target & Phenotype Analysis
**Command:**
```bash
bioql-crispr infer-phenotype \
  --mutations examples/toy_mutations.jsonl \
  --engine auto \
  --out runs/CRISPRQAI-2025-10-08-RUN1/phenotype.csv
```

**Purpose:** Predict off-target binding sites and phenotypic effects for each mutation.

**Output:** `phenotype.csv` with risk scores and recommendations.

### Step 6: Report Generation
**Action:** Generate comprehensive Markdown report summarizing:
- Experiment metadata (ID, seed, backend used)
- Top 12 ranked guides with scores
- Energy distribution analysis
- Off-target risk assessment
- Safety recommendations
- Reproducibility information

**Output:** `runs/CRISPRQAI-2025-10-08-RUN1/report_CRISPRQAI_experiment.md`

### Step 7: Validation
- Verify all output files exist
- Check `ranked.csv` has ≥12 rows
- Confirm `phenotype.csv` has ≥1 score column
- Validate deterministic outputs (same seed = same results)
- Generate SHA-256 hashes for reproducibility

---

## 🖥️ MODAL DEPLOYMENT (Optional)

For cloud execution, use this Modal job configuration:

```json
{
  "job": "bioql_crispr_qai_experiment",
  "image": "ghcr.io/bionicsai/bioql:5.4.3",
  "cmd": [
    "bash", "-lc",
    "bioql-crispr rank-guides --target examples/toy_cas9_target.fasta --guides examples/toy_guides.csv --engine auto --top 12 --out runs/CRISPRQAI-2025-10-08-RUN1/ranked.csv && bioql-crispr score-energy --ref examples/toy_cas9_target.fasta --edit examples/toy_cas9_target.fasta --engine auto --model ising --seed 42 --out runs/CRISPRQAI-2025-10-08-RUN1/energy.json && bioql-crispr infer-phenotype --mutations examples/toy_mutations.jsonl --engine auto --out runs/CRISPRQAI-2025-10-08-RUN1/phenotype.csv"
  ],
  "env": {
    "PYTHONHASHSEED": "42",
    "BIOQL_API_KEY": "${BIOQL_API_KEY}"
  },
  "timeout_sec": 3600,
  "mount_outputs": "runs/CRISPRQAI-2025-10-08-RUN1"
}
```

---

## 📊 EXPECTED OUTPUT

### Final JSON Summary
```json
{
  "experiment_id": "CRISPRQAI-2025-10-08-RUN1",
  "engine_used": "local_simulator",
  "model_used": "ising",
  "seed": 42,
  "artifacts": {
    "ranked_guides": "runs/CRISPRQAI-2025-10-08-RUN1/ranked.csv",
    "energy_scores": "runs/CRISPRQAI-2025-10-08-RUN1/energy.json",
    "phenotype_analysis": "runs/CRISPRQAI-2025-10-08-RUN1/phenotype.csv",
    "report": "runs/CRISPRQAI-2025-10-08-RUN1/report_CRISPRQAI_experiment.md"
  },
  "top_guides_preview": [
    {
      "rank": 1,
      "sequence": "ATCGAAGTCGCTAGCTA",
      "composite_score": 0.8234,
      "energy_estimate": -7.4521,
      "gc_content": 0.47
    },
    {
      "rank": 2,
      "sequence": "GCTAGCTACGATCCGA",
      "composite_score": 0.7891,
      "energy_estimate": -6.9832,
      "gc_content": 0.50
    }
  ],
  "status": "SUCCESS",
  "runtime_seconds": 45.23,
  "warnings": [],
  "safety_mode": "SIMULATION_ONLY"
}
```

### File Structure
```
runs/CRISPRQAI-2025-10-08-RUN1/
├── ranked.csv                  # Top 12 guides with scores
├── energy.json                 # Energy calculations
├── phenotype.csv               # Off-target predictions
├── report_CRISPRQAI_experiment.md  # Human-readable report
└── metadata.json               # Experiment metadata & hashes
```

---

## 🔒 SAFETY CONSTRAINTS

### Enforced Rules:
1. **Simulation-only**: No wet-lab protocols, reagents, temperatures, or procedures
2. **Circuit limits**: ≤12 qubits, shallow circuits only
3. **No credentials**: Never print API keys or tokens
4. **Research use**: Computational analysis only
5. **Human oversight**: All results require expert validation before experiments

### If Unsafe Output Detected:
Replace with: *"⚠️ Simulation-only: wet-lab procedures are not provided. Consult qualified researchers before experimental work."*

---

## ✅ SUCCESS CRITERIA

- [x] All 3 CLI commands execute successfully
- [x] Outputs are deterministic (seed=42)
- [x] `ranked.csv` contains ≥12 guides
- [x] `phenotype.csv` has ≥1 risk score column
- [x] Report and JSON files saved
- [x] No wet-lab procedures in output
- [x] SHA-256 hashes match on re-run

---

## 🚀 QUICK START

### Option 1: Direct Execution (Local)
```bash
# Run all steps
bioql-crispr rank-guides \
  --target examples/toy_cas9_target.fasta \
  --guides examples/toy_guides.csv \
  --engine auto \
  --top 12 \
  --out runs/CRISPRQAI-2025-10-08-RUN1/ranked.csv

bioql-crispr score-energy \
  --ref examples/toy_cas9_target.fasta \
  --edit examples/toy_cas9_target.fasta \
  --engine auto \
  --model ising \
  --seed 42 \
  --out runs/CRISPRQAI-2025-10-08-RUN1/energy.json

bioql-crispr infer-phenotype \
  --mutations examples/toy_mutations.jsonl \
  --engine auto \
  --out runs/CRISPRQAI-2025-10-08-RUN1/phenotype.csv
```

### Option 2: Python API
```python
from bioql.crispr_qai import rank_guides_batch, estimate_energy_collapse_simulator
from bioql.crispr_qai.io import load_guides_csv, save_results_csv
import numpy as np

# Set seed
np.random.seed(42)

# Load guides
guides = load_guides_csv("examples/toy_guides.csv")

# Rank guides
ranked = rank_guides_batch(
    guide_sequences=[g['sequence'] for g in guides],
    shots=1000,
    engine='auto'
)

# Save top 12
save_results_csv(ranked[:12], "runs/CRISPRQAI-2025-10-08-RUN1/ranked.csv")
```

### Option 3: Natural Language (Agent)
```
User: "Run a CRISPR-QAI experiment with guides from examples/toy_guides.csv,
       target examples/toy_cas9_target.fasta, rank top 12, analyze off-targets,
       use seed 42, save to runs/CRISPRQAI-2025-10-08-RUN1/"

Agent: [Executes full workflow and generates all artifacts]
```

---

## 📚 REFERENCE

- **BioQL Version**: 5.4.3
- **CRISPR-QAI Module**: `bioql.crispr_qai`
- **CLI**: `bioql-crispr`
- **Backends**: Simulator (default), AWS Braket, IBM Qiskit
- **Safety**: Simulation-only enforced
- **Documentation**: `bioql/crispr_qai/examples/demo_basic.py`

---

## 🎓 EXAMPLE PROMPT FOR AGENT

**Simple Version:**
> "Run CRISPR experiment CRISPRQAI-2025-10-08-RUN1 with guides from examples/toy_guides.csv, target examples/toy_cas9_target.fasta, rank top 12, seed 42"

**Detailed Version:**
> "Execute a complete CRISPR-QAI quantum experiment:
> - Experiment ID: CRISPRQAI-2025-10-08-RUN1
> - Seed: 42 (deterministic)
> - Target DNA: examples/toy_cas9_target.fasta
> - Guide candidates: examples/toy_guides.csv
> - Mutations: examples/toy_mutations.jsonl
> - Quantum backend: auto (prefer Braket/Qiskit, fallback simulator)
> - Model: Ising Hamiltonian
> - Rank top 12 guides by composite score
> - Analyze off-target binding sites
> - Calculate energy collapse for all guides
> - Generate comprehensive Markdown report
> - Save all artifacts to: runs/CRISPRQAI-2025-10-08-RUN1/
> - Enforce simulation-only safety mode"

**JSON Config Version:**
> "Run CRISPR experiment with this config: [paste JSON from top]"

---

**End of Prompt**

*Generated: 2025-10-08*
*BioQL Version: 5.4.3*
*CRISPR-QAI Module: Production Ready*
