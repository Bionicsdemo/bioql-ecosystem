# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL VS Code Model Server - Modal Deployment
Sirve el checkpoint-2000 entrenado para VS Code extension
"""
import modal
import os

# Create Modal app
app = modal.App("bioql-inference-deepseek")

# GPU image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.0",
        "transformers==4.37.0",
        "peft==0.7.1",
        "accelerate==0.25.0",
        "bitsandbytes==0.41.3",
        "fastapi==0.108.0",
        "pydantic==2.5.0"
    )
)

# Create volume for checkpoint
checkpoint_volume = modal.Volume.from_name("bioql-checkpoint", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A10G",  # Smaller GPU, más barato
    volumes={"/checkpoint": checkpoint_volume},
    timeout=600,
    scaledown_window=300
)
@modal.concurrent(max_inputs=10)
class BioQLVSCodeServer:
    """Server para VS Code extension"""

    @modal.enter()
    def load_model(self):
        """Load model on container startup"""
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel

        print("🔄 Loading base model...")
        base_model = "Qwen/Qwen2.5-7B-Instruct"

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model,
            trust_remote_code=True
        )

        # Base model with 4-bit quantization
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True
        )

        print("🔄 Loading LoRA checkpoint-2000...")
        self.model = PeftModel.from_pretrained(
            model,
            "/checkpoint",
            torch_dtype=torch.float16
        )

        self.model.eval()
        print("✅ Model loaded and ready!")

    @modal.method()
    def generate(self, prompt: str, max_length: int = 300, temperature: float = 0.7) -> dict:
        """Generate BioQL code from prompt"""
        import torch
        import re

        # Detect drug discovery tasks and generate correct code directly
        prompt_lower = prompt.lower()

        # Check for DE NOVO drug design tasks (BioQL 5.4.1 - DrugDesigner V2)
        if any(kw in prompt_lower for kw in ['design', 'generate', 'create', 'discover']) and \
           any(kw in prompt_lower for kw in ['drug', 'molecule', 'compound', 'ligand', 'new', 'novel', 'de novo']):
            # Extract disease/target if possible
            disease_match = re.search(r'(?:for|targeting|treat)\s+(\w+)', prompt_lower)
            pdb_match = re.search(r'(?:pdb|id|receptor)(?:\s+(?:is|:))?\s+([0-9A-Z]{4})', prompt, re.IGNORECASE)

            # Extract backend (full name like ibm_torino, ionq_aria)
            backend_match = re.search(r'\b(ibm_\w+|ionq_\w+|aws_braket|simulator)\b', prompt_lower)
            backend = backend_match.group(1) if backend_match else "ibm_torino"

            # Extract shots number
            shots_match = re.search(r'(?:with\s+)?(\d+)\s+shots?', prompt_lower)
            shots = int(shots_match.group(1)) if shots_match else 5000

            disease = disease_match.group(1) if disease_match else "unspecified disease"
            pdb = pdb_match.group(1) if pdb_match else "unspecified"

            # Generate DE NOVO drug design code (BioQL 5.6.2 API)
            code = f'''from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("="*80)
print("🧬 DE NOVO Drug Design V2 for {disease.capitalize()}")
print("⚛️  VALIDATED Molecules + REAL AutoDock Vina")
print("✅ RDKit Sanitization + PAINS Filters + ADME/Tox")
print("="*80)

# Execute de novo design on IBM Quantum hardware
result = quantum(
    "Design a new drug for {disease} targeting receptor PDB {pdb}",
    backend='{backend}',  # Quantum backend from user request
    shots={shots},        # Quantum measurements from user request
    api_key=api_key
)

print(f"\\n✅ De Novo Design Complete!")
print(f"Backend: {{result.backend if hasattr(result, 'backend') else 'ibm_torino'}}")

# Access bio_interpretation for all data
bio = getattr(result, 'bio_interpretation', {{}})

# Molecule info
if bio.get('designed_molecule'):
    print(f"\\n🧬 Best Molecule:")
    print(f"   SMILES: {{bio['designed_molecule']}}")
    print(f"   Name: {{bio.get('molecule_name', 'N/A')}}")

# Binding data
if bio.get('binding_affinity'):
    print(f"\\n📊 Binding Analysis:")
    print(f"   Affinity: {{bio['binding_affinity']:.2f}} kcal/mol")
    if bio.get('ki'):
        print(f"   Ki: {{bio['ki']:.2f}} nM")
    if bio.get('ic50'):
        print(f"   IC50: {{bio['ic50']:.2f}} nM")

# Drug-likeness
if bio.get('qed_score') is not None:
    print(f"\\n💊 Drug-Likeness:")
    print(f"   QED Score: {{bio['qed_score']:.2f}}")
    print(f"   SA Score: {{bio.get('sa_score', 'N/A')}}/10")
    print(f"   Lipinski: {{'✅ Pass' if bio.get('lipinski_pass') else '❌ Fail'}} ({{bio.get('lipinski_violations', 0)}} violations)")

# ADME properties
if bio.get('molecular_weight'):
    print(f"\\n🔬 ADME Properties:")
    print(f"   MW: {{bio['molecular_weight']:.1f}} Da")
    print(f"   LogP: {{bio.get('logP', 'N/A')}}")
    print(f"   TPSA: {{bio.get('tpsa', 'N/A')}} Ų")
    print(f"   Oral Bioavailability: {{bio.get('oral_bioavailability', 'N/A')}}")
    print(f"   BBB Permeability: {{bio.get('bbb_permeability', 'N/A')}}")

# Toxicity
if bio.get('toxicity_class'):
    print(f"\\n☢️  Toxicity Prediction:")
    print(f"   Class: {{bio['toxicity_class']}}")
    print(f"   Ames Test: {{bio.get('ames_test', 'N/A')}}")
    print(f"   Hepatotoxicity: {{bio.get('hepatotoxicity', 'N/A')}}")
    print(f"   Cardiotoxicity: {{bio.get('cardiotoxicity', 'N/A')}}")

# All candidates
if bio.get('all_candidates'):
    print(f"\\n🧪 All Candidates ({{len(bio['all_candidates'])}}):")
    for i, cand in enumerate(bio['all_candidates'][:5], 1):
        print(f"   {{i}}. {{cand.get('smiles', 'N/A')[:50]}}...")

print("\\n" + "="*80)
'''
            return {{
                "code": code,
                "success": True
            }}

        # Check for docking/binding tasks
        elif any(kw in prompt_lower for kw in ['dock', 'binding', 'affinity', 'ligand', 'receptor', 'smiles', 'pdb']):
            # Extract ligand and receptor if possible
            ligand_match = re.search(r'(?:ligand|drug|compound)(?:\s+(?:is|:|named))?\s+(\w+)', prompt_lower)
            receptor_match = re.search(r'(?:receptor|protein|target)(?:\s+(?:is|:|named))?\s+(\w+)', prompt_lower)
            smiles_match = re.search(r'(?:smiles|structure)(?:\s+(?:is|:))?\s+([A-Z0-9\(\)=\[\]@\+\-#]+)', prompt, re.IGNORECASE)
            pdb_match = re.search(r'(?:pdb|id)(?:\s+(?:is|:))?\s+([0-9A-Z]{4})', prompt, re.IGNORECASE)

            # Extract backend (full name like ibm_torino, ionq_aria)
            backend_match = re.search(r'\b(ibm_\w+|ionq_\w+|aws_braket|simulator)\b', prompt_lower)
            backend = backend_match.group(1) if backend_match else "ibm_torino"

            # Extract shots number
            shots_match = re.search(r'(?:with\s+)?(\d+)\s+shots?', prompt_lower)
            shots = int(shots_match.group(1)) if shots_match else 2000

            ligand = ligand_match.group(1) if ligand_match else "ligand"
            receptor = receptor_match.group(1) if receptor_match else "receptor"
            smiles = smiles_match.group(1) if smiles_match else "SMILES_HERE"
            pdb = pdb_match.group(1) if pdb_match else "PDB_ID_HERE"

            # Generate clean QUANTUM docking code (BioQL 5.6.2 API)
            code = f'''from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("="*80)
print("🧬 QUANTUM Molecular Docking: {ligand.capitalize()} → {receptor.upper()}")
print("⚛️  Executing VQE on IBM Quantum Hardware")
print("="*80)

# Execute VQE on REAL quantum hardware (IBM Quantum)
result = quantum(
    "Analyze ligand with SMILES {smiles} docking to receptor PDB {pdb}. "
    "Calculate binding affinity using VQE quantum computation. "
    "Identify key molecular interactions from quantum states. "
    "Calculate Ki and IC50 from quantum binding energies.",
    backend='{backend}',  # Quantum backend from user request
    shots={shots},        # Quantum measurements from user request
    api_key=api_key
)

print(f"\\n✅ QUANTUM Docking Complete!")
print(f"Backend: {{result.backend if hasattr(result, 'backend') else 'ibm_torino'}}")
print(f"Success: {{result.success}}")

# Access bio_interpretation for comprehensive data
bio = getattr(result, 'bio_interpretation', {{}})

if bio.get('binding_affinity'):
    print(f"\\n⚛️  Binding Affinity (from VQE): {{bio['binding_affinity']:.2f}} kcal/mol")
if bio.get('ki'):
    print(f"   Ki: {{bio['ki']:.2f}} nM")
if bio.get('ic50'):
    print(f"   IC50: {{bio['ic50']:.2f}} nM")

# Molecular interactions
if bio.get('h_bonds'):
    print(f"\\n🔗 Molecular Interactions (from quantum states):")
    print(f"   H-bonds: {{bio.get('h_bonds', 'N/A')}}")
    print(f"   Hydrophobic: {{bio.get('hydrophobic_contacts', 'N/A')}}")
    print(f"   π-stacking: {{bio.get('pi_stacking', 'N/A')}}")
    print(f"   Salt bridges: {{bio.get('salt_bridges', 'N/A')}}")

# Drug-likeness if available
if bio.get('qed_score') is not None:
    print(f"\\n💊 Drug-Likeness:")
    print(f"   QED: {{bio['qed_score']:.2f}}")
    print(f"   Lipinski: {{'✅' if bio.get('lipinski_pass') else '❌'}}")

print("\\n" + "="*80)
'''
            return {
                "code": code,
                "success": True
            }

        # Check for Quillow Quantum Error Correction tasks
        elif any(kw in prompt_lower for kw in ['quillow', 'qec', 'quantum error correction', 'surface code',
                                                 'error correction', 'logical qubit', 'syndrome',
                                                 'distance', 'stabilizer', 'decoder', 'mwpm']):
            # Extract code distance (d=3, 5, 7, 9, etc.)
            distance_match = re.search(r'(?:distance|d)\s*=?\s*(\d+)', prompt_lower)
            distance = int(distance_match.group(1)) if distance_match else 5

            # Extract backend (stim, bioql, modal, simulator)
            backend_match = re.search(r'\b(stim|bioql|modal|simulator|qiskit)\b', prompt_lower)
            backend = backend_match.group(1) if backend_match else "stim"

            # Extract shots number
            shots_match = re.search(r'(?:with\s+)?(\d+)\s+shots?', prompt_lower)
            shots = int(shots_match.group(1)) if shots_match else 10000

            # Extract error rate
            error_rate_match = re.search(r'(?:error\s+rate|physical\s+error)(?:\s+(?:is|=|:))?\s+([\d.]+(?:e-?\d+)?)', prompt_lower)
            error_rate = float(error_rate_match.group(1)) if error_rate_match else 0.001

            # Extract decoder type
            decoder_match = re.search(r'\b(pymatching|mwpm|union-find|belief-propagation|neural)\b', prompt_lower)
            decoder = decoder_match.group(1) if decoder_match else "pymatching"

            # Extract number of rounds
            rounds_match = re.search(r'(?:rounds?|cycles?)\s*=?\s*(\d+)', prompt_lower)
            rounds = int(rounds_match.group(1)) if rounds_match else 10

            # Generate Quillow QEC code template
            code = f'''from quillow import SurfaceCodeSimulator, BioQLOptimizer
import os
import numpy as np

# Quillow QEC Configuration
api_key = os.getenv('BIOQL_API_KEY', '__BIOQL_REDACTED__')

print("="*80)
print("⚛️  Quillow Quantum Error Correction")
print("🛡️  Google Willow-Style Surface Codes")
print(f"📊 Code Distance: d={distance}, Error Rate: {error_rate:.4f}")
print("="*80)

# Initialize Surface Code Simulator
# Surface codes are the gold standard for fault-tolerant quantum computing
# Distance 'd' determines the number of errors that can be corrected: (d-1)/2
sim = SurfaceCodeSimulator(
    distance={distance},              # Code distance (larger = more error correction)
    physical_error_rate={error_rate},  # Physical qubit error rate
    rounds={rounds},                   # Number of QEC cycles to simulate
    decoder='{decoder}',              # Error correction decoder algorithm
    backend='{backend}'               # Simulation backend
)

print(f"\\n🔧 Simulation Parameters:")
print(f"   Distance: {distance} (corrects up to {{({distance}-1)//2}} errors)")
print(f"   Physical qubits: {{sim.num_physical_qubits}}")
print(f"   Data qubits: {{sim.num_data_qubits}}")
print(f"   Syndrome qubits: {{sim.num_syndrome_qubits}}")
print(f"   Physical error rate: {error_rate:.4f}")
print(f"   Decoder: {decoder}")
print(f"   Backend: {backend}")

# Run surface code simulation
print(f"\\n🚀 Running QEC simulation with {shots} shots...")
result = sim.run(
    shots={shots},
    measure_logical=True,
    track_syndromes=True
)

# Display results
print(f"\\n✅ Simulation Complete!")
print(f"\\n📊 Error Correction Performance:")
print(f"   Logical error rate: {{result.logical_error_rate:.6f}}")
print(f"   Physical error rate: {{result.physical_error_rate:.6f}}")
print(f"   Error suppression: {{result.physical_error_rate / result.logical_error_rate:.2f}}x")
print(f"   Below threshold: {{'✅ Yes' if result.is_below_threshold else '❌ No'}}")

# Syndrome detection statistics
if hasattr(result, 'syndrome_stats'):
    print(f"\\n🔍 Syndrome Detection:")
    print(f"   Total syndromes detected: {{result.syndrome_stats.get('total_syndromes', 0)}}")
    print(f"   X-type errors: {{result.syndrome_stats.get('x_errors', 0)}}")
    print(f"   Z-type errors: {{result.syndrome_stats.get('z_errors', 0)}}")
    print(f"   Decoder success rate: {{result.syndrome_stats.get('decoder_success_rate', 0):.2%}}")

# Logical qubit fidelity
if hasattr(result, 'logical_fidelity'):
    print(f"\\n🎯 Logical Qubit Performance:")
    print(f"   Logical fidelity: {{result.logical_fidelity:.6f}}")
    print(f"   Logical lifetime: {{result.logical_lifetime:.2f}} rounds")
    print(f"   Effective T1: {{result.effective_t1:.2f}} µs")

# Comparison with threshold
if hasattr(result, 'threshold_comparison'):
    print(f"\\n📈 Threshold Analysis:")
    print(f"   Surface code threshold: {{result.threshold_comparison.get('threshold', 0.01):.4f}}")
    print(f"   Current error rate: {{result.physical_error_rate:.4f}}")
    print(f"   Margin: {{(result.threshold_comparison.get('threshold', 0.01) - result.physical_error_rate) * 100:.2f}}%")

# Visualization of error patterns (if available)
if hasattr(result, 'error_patterns'):
    print(f"\\n🎨 Error Pattern Summary:")
    print(f"   Most common error type: {{result.error_patterns.get('most_common', 'N/A')}}")
    print(f"   Error clustering: {{result.error_patterns.get('clustering_coefficient', 0):.3f}}")

# Performance metrics
if hasattr(result, 'performance'):
    print(f"\\n⚡ Performance Metrics:")
    print(f"   Simulation time: {{result.performance.get('sim_time', 0):.2f}} seconds")
    print(f"   Shots per second: {{result.performance.get('shots_per_second', 0):.0f}}")
    print(f"   Memory usage: {{result.performance.get('memory_mb', 0):.1f}} MB")

# Scalability prediction (Willow-style exponential suppression)
if {distance} >= 3:
    print(f"\\n🚀 Scalability Prediction (Willow-Style):")
    print(f"   Current d={distance}: {{result.logical_error_rate:.6f}}")
    # Exponential suppression: each distance increase should reduce error rate
    predicted_d_next = result.logical_error_rate * (result.physical_error_rate / 0.01)
    print(f"   Predicted d={{{distance}+2}}: {{predicted_d_next:.6f}} (estimate)")
    print(f"   Expected improvement: {{result.logical_error_rate / predicted_d_next:.2f}}x")

print("\\n" + "="*80)
print("💡 Tip: Increase distance for better error correction")
print("💡 Tip: Lower physical error rate improves logical performance")
print("="*80)
'''
            return {{
                "code": code,
                "success": True
            }}

        # For non-drug-discovery tasks, use the model
        formatted_prompt = f"""You are a BioQL 6.0.0 code generator - 100% QUANTUM computing platform with:

✅ DE NOVO Drug Design V2 + ADME/Tox prediction
✅ Quillow Quantum Error Correction (Google Willow-style surface codes)
✅ Multi-Omics Integration (Proteomics, Metabolomics, Genomics)
✅ Real Quantum Hardware (IBM Quantum, IonQ, AWS Braket)

QUANTUM ERROR CORRECTION (Quillow):
- Surface codes with d=3, 5, 7, 9 (higher distance = more protection)
- Below-threshold operation: logical errors decrease exponentially with distance
- Real-time syndrome extraction and MWPM decoding
- Automatic protection for quantum chemistry calculations
- Backends: Stim (fast simulator), BioQL API (hardware), Modal (GPU)

Quillow Usage:
1. Basic QEC: from quillow import SurfaceCodeSimulator; sim = SurfaceCodeSimulator(distance=5); result = sim.run(shots=10000)
2. Protected Chemistry: from quillow import BioQLOptimizer; optimizer = BioQLOptimizer(api_key="...", qec_distance=5)
3. Threshold Analysis: Run multiple distances (3,5,7) to demonstrate below-threshold
4. Hardware Integration: Use backend='ibm_torino' for real quantum processors

IMPORTANT RULES:
- BioQL is 100% QUANTUM - all computations run on real quantum processors
- Quillow adds fault-tolerant error correction to quantum circuits
- For critical calculations: use d=5 or d=7 for QEC protection
- For testing/development: use d=3 or simulator backend
- QEC overhead: d=5 = 1.5x cost, d=7 = 2.0x cost
- NEVER create undefined variables
- ALWAYS extract from result.bio_interpretation dictionary using .get()
- Use VQE for drug discovery and binding affinity calculations
- DE NOVO Drug Design V2: VALIDATED molecules with RDKit sanitization + PAINS filters + ADME/Tox
- Access data via: bio = result.bio_interpretation
- Available fields: designed_molecule, binding_affinity, ki, ic50, qed_score, sa_score, molecular_weight, logP, toxicity_class, adme properties, interactions
- No unstable groups (peroxides, azides) - all molecules pre-validated
- Default to real hardware backends: ibm_torino, ibm_brisbane, ionq_aria
- For drug design: use quantum("Design a new drug for DISEASE targeting PDB_ID")

When user mentions "quillow", "qec", "error correction", "surface code":
→ Generate Quillow quantum error correction code

User request: {prompt}

BioQL code:
```python
"""

        # Tokenize
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.model.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=temperature,
                do_sample=True,
                top_p=0.95,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract code after the prompt
        code = generated.split("```python")[-1].split("```")[0].strip()

        return {
            "code": code,
            "success": True
        }


@app.function(image=image)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def generate_code():
    """FastAPI endpoint"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    web_app = FastAPI(title="BioQL VS Code Server")

    class GenerateRequest(BaseModel):
        prompt: str = None
        request: str = None  # Agent format uses "request" instead of "prompt"
        max_length: int = 300
        temperature: float = 0.7
        api_key: str = None  # Optional, for compatibility
        include_reasoning: bool = False  # Optional

    class GenerateResponse(BaseModel):
        code: str
        success: bool
        action: str = "code_generation"  # For agent compatibility
        cost: dict = None  # For agent compatibility

    @web_app.get("/health")
    async def health():
        return {"status": "healthy"}

    @web_app.post("/generate", response_model=GenerateResponse)
    async def generate_endpoint(request: GenerateRequest):
        try:
            # Support both "prompt" and "request" fields
            user_prompt = request.prompt or request.request
            if not user_prompt:
                raise HTTPException(status_code=400, detail="Missing prompt or request field")

            server = BioQLVSCodeServer()
            result = server.generate.remote(
                user_prompt,
                request.max_length,
                request.temperature
            )

            # Add agent-compatible fields
            result["action"] = "code_generation"
            result["cost"] = {
                "user_cost_usd": 0.0,
                "total_seconds": 0.0
            }

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @web_app.post("/", response_model=GenerateResponse)
    async def root_endpoint(request: GenerateRequest):
        """Root endpoint for agent compatibility"""
        return await generate_endpoint(request)

    return web_app


# For local testing
@app.local_entrypoint()
def test():
    """Test the model locally"""
    server = BioQLVSCodeServer()

    test_prompts = [
        "Create a Bell state",
        "Generate a 3-qubit GHZ state",
        "Apply Hadamard to qubit 0"
    ]

    print("\n" + "="*60)
    print("Testing BioQL VS Code Server")
    print("="*60 + "\n")

    for prompt in test_prompts:
        print(f"📝 Prompt: {prompt}")
        result = server.generate.remote(prompt)
        print(f"✅ Code:\n{result['code']}\n")
        print("-"*60 + "\n")
