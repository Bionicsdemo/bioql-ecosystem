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

            # Check if QEC is mentioned
            enable_qec = any(kw in prompt_lower for kw in ['qec', 'error correction', 'surface code', 'quillow', 'steane', 'shor'])

            # Extract QEC parameters if present
            qec_type = 'surface_code'  # default
            logical_qubits = 2  # default

            if enable_qec:
                if 'steane' in prompt_lower:
                    qec_type = 'steane'
                elif 'shor' in prompt_lower:
                    qec_type = 'shor'

                # Extract logical qubits
                logical_match = re.search(r'(\d+)\s+logical\s+qubits?', prompt_lower)
                if logical_match:
                    logical_qubits = int(logical_match.group(1))

            disease = disease_match.group(1) if disease_match else "unspecified disease"
            pdb = pdb_match.group(1) if pdb_match else "unspecified"

            # Build QEC parameters string if enabled
            qec_params = ""
            qec_info = ""
            if enable_qec:
                qec_params = f",\n    qec_enabled=True,\n    qec_type='{qec_type}',\n    logical_qubits={logical_qubits}"
                qec_info = f" using {qec_type} error correction with {logical_qubits} logical qubits"

            # Generate DE NOVO drug design code (BioQL 5.6.2 API)
            code = f'''from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("="*80)
print("🧬 DE NOVO Drug Design V2 for {disease.capitalize()}")
print("⚛️  VALIDATED Molecules + REAL AutoDock Vina")
print("✅ RDKit Sanitization + PAINS Filters + ADME/Tox")
{f'print("🛡️  QEC: {qec_type} with {logical_qubits} logical qubits")' if enable_qec else ''}
print("="*80)

# Execute de novo design on IBM Quantum hardware
result = quantum(
    "Design a new drug for {disease} targeting receptor PDB {pdb}{qec_info}",
    backend='{backend}',  # Quantum backend from user request
    shots={shots},        # Quantum measurements from user request
    api_key=api_key{qec_params}
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

        # ============================================================================
        # QPHAROS DETECTION (NEW IN v7.0.4)
        # ============================================================================
        # Check if user wants QPHAROS instead of BioQL
        if 'qpharos' in prompt_lower:
            # Determine which QPHAROS schema to use
            # Schema 1: Simple API (keywords: simple, quick, beginner, easy)
            # Schema 2: Functional API (keywords: functional, research, custom) - DEFAULT
            # Schema 3: OOP API (keywords: oop, class, pipeline, batch, session)
            # Schema 4: Layer API (keywords: layer, quantum, expert, circuit, vqe, qaoa)

            qpharos_schema = 2  # Default to Schema 2 (Functional)

            if any(kw in prompt_lower for kw in ['simple', 'quick', 'beginner', 'easy', 'esquema 1', 'schema 1']):
                qpharos_schema = 1
            elif any(kw in prompt_lower for kw in ['oop', 'class', 'pipeline', 'batch', 'session', 'analyzer', 'esquema 3', 'schema 3']):
                qpharos_schema = 3
            elif any(kw in prompt_lower for kw in ['layer', 'quantum', 'expert', 'circuit', 'vqe', 'qaoa', 'esquema 4', 'schema 4']):
                qpharos_schema = 4

            # Extract parameters
            smiles_match = re.search(r'(?:smiles|structure)(?:\s+(?:is|:))?\s+(["\']?)([A-Z0-9\(\)=\[\]@\+\-#]+)\1', prompt, re.IGNORECASE)
            pdb_match = re.search(r'(?:pdb|id|receptor)(?:\s+(?:is|:))?\s+([0-9A-Z]{4})', prompt, re.IGNORECASE)
            backend_match = re.search(r'\b(ibm_\w+|ionq_\w+|aws_braket|simulator)\b', prompt_lower)
            shots_match = re.search(r'(?:with\s+)?(\d+)\s+shots?', prompt_lower)

            smiles = smiles_match.group(2) if smiles_match else "CCO"
            pdb = pdb_match.group(1) if pdb_match else "6B3J"
            backend = backend_match.group(1) if backend_match else "ibm_torino"
            shots = int(shots_match.group(1)) if shots_match else 2000

            # Generate code based on schema
            if qpharos_schema == 1:
                # Schema 1: Simple API
                code = f'''# QPHAROS Schema 1: Simple API (Beginner-friendly)
# Install: pip install qpharos
# Set env: export BIOQL_API_KEY=\'your_key_here\'

from qpharos.simple import quick_dock, is_drug_like, test_molecule

print("="*80)
print("🔶 QPHAROS - Simple API (Schema 1)")
print("="*80)

# Quick docking (1 line!)
affinity = quick_dock(\'{smiles}\', \'{pdb}\')
print(f"\\n⚛️  Binding Affinity: {{affinity:.2f}} kcal/mol")

# Check drug-likeness
drug_like = is_drug_like(\'{smiles}\')
print(f"💊 Drug-like: {{drug_like}}")

# Complete test (docking + ADMET)
print("\\n📊 Running complete analysis...")
result = test_molecule(\'{smiles}\', \'{pdb}\')

print("\\n🔬 Complete Results:")
print(f"   Affinity: {{result[\'affinity\']}} kcal/mol")
print(f"   Ki: {{result[\'ki_nM\']}} nM")
print(f"   Drug-like: {{result[\'drug_like\']}}")
print(f"   QED Score: {{result[\'qed_score\']}}")
print(f"   ✅ {{result[\'recommendation\']}}")
print(f"\\n🔗 IBM Job: https://quantum.ibm.com/jobs/{{result[\'job_id\']}}")

print("\\n" + "="*80)
print("✅ QPHAROS Simple API Complete!")
print("="*80)
'''

            elif qpharos_schema == 3:
                # Schema 3: OOP API
                code = f'''# QPHAROS Schema 3: OOP API (Object-Oriented for Pipelines)
# Install: pip install qpharos
# Set env: export BIOQL_API_KEY=\'your_key_here\'

from qpharos import QPHAROSAnalyzer, QPHAROSConfig
import os

print("="*80)
print("🔶 QPHAROS - OOP API (Schema 3)")
print("="*80)

# Configure analyzer
config = QPHAROSConfig(
    backend=\'{backend}\',
    shots={shots},
    api_key=os.getenv(\'BIOQL_API_KEY\'),
    qec_enabled=True
)

# Create analyzer instance (with session tracking)
analyzer = QPHAROSAnalyzer(config)

print("\\n📊 Running analysis with session management...")

# Run docking
result = analyzer.dock(\'{smiles}\', \'{pdb}\')

print(f"\\n⚛️  Binding Affinity: {{result.binding_affinity:.2f}} kcal/mol")
print(f"💊 Ki: {{result.ki:.2f}} nM")

# Run ADMET prediction
admet = analyzer.predict_admet(\'{smiles}\')
print(f"\\n💊 Drug-Likeness:")
print(f"   Lipinski Pass: {{admet.lipinski_pass}}")
print(f"   QED Score: {{admet.qed_score:.2f}}")

# Get session summary
summary = analyzer.get_session_summary()
print(f"\\n📈 Session Summary:")
print(f"   Session ID: {{summary[\'session_id\']}}")
print(f"   Total Analyses: {{summary[\'total_analyses\']}}")

# Save reports
analyzer.save_report(\'qpharos_results.json\', format=\'json\')
analyzer.save_report(\'qpharos_results.txt\', format=\'text\')

print(f"\\n💾 Reports saved!")
print("\\n" + "="*80)
print("✅ QPHAROS OOP API Complete!")
print("="*80)
'''

            elif qpharos_schema == 4:
                # Schema 4: Layer-by-Layer API (Quantum Expert)
                code = f'''# QPHAROS Schema 4: Layer-by-Layer API (Quantum Expert)
# Install: pip install qpharos
# Set env: export BIOQL_API_KEY=\'your_key_here\'

from qpharos.layers import (
    QuantumFeatureEncoder,
    QuantumEntanglementMapper,
    QuantumConformationalSearch,
    QuantumScoringFunction,
    QuantumErrorCorrection
)
from qpharos.core import quantum_backend
import os

print("="*80)
print("🔶 QPHAROS - Layer-by-Layer API (Schema 4 - Quantum Expert)")
print("="*80)

# Initialize quantum backend
backend = quantum_backend.QuantumBackend(
    backend_name=\'{backend}\',
    shots={shots},
    api_key=os.getenv(\'BIOQL_API_KEY\')
)

print("\\n⚛️  Running 5-Layer QPHAROS Architecture...")

# Layer 1: Quantum Feature Encoding
print("\\n🔷 Layer 1: Quantum Feature Encoding")
encoder = QuantumFeatureEncoder(backend)
ligand_encoded = encoder.encode_molecule(\'{smiles}\')
receptor_encoded = encoder.encode_protein(\'{pdb}\')
print(f"   Ligand qubits: {{ligand_encoded.n_qubits}}")
print(f"   Receptor qubits: {{receptor_encoded.n_qubits}}")

# Layer 2: Quantum Entanglement Mapping
print("\\n🔷 Layer 2: Quantum Entanglement Mapping")
mapper = QuantumEntanglementMapper(backend)
entangled_state = mapper.create_entanglement(ligand_encoded, receptor_encoded)
print(f"   Entanglement depth: {{entangled_state.circuit_depth}}")
print(f"   Total qubits: {{entangled_state.n_qubits}}")

# Layer 3: Quantum Conformational Search (QAOA)
print("\\n🔷 Layer 3: Quantum Conformational Search (QAOA)")
search = QuantumConformationalSearch(backend)
conformers = search.find_conformers(entangled_state, n_conformers=5)
print(f"   Conformers found: {{len(conformers)}}")

# Layer 4: Quantum Scoring Function (VQE)
print("\\n🔷 Layer 4: Quantum Scoring Function (VQE)")
scorer = QuantumScoringFunction(backend)
affinity = scorer.calculate_binding_affinity(conformers[0])
print(f"   Binding Affinity: {{affinity:.2f}} kcal/mol")

# Layer 5: Quantum Error Correction
print("\\n🔷 Layer 5: Quantum Error Correction (Surface Code)")
qec = QuantumErrorCorrection(backend, code_type=\'surface_code\')
corrected_affinity = qec.correct_measurement(affinity)
print(f"   QEC Corrected Affinity: {{corrected_affinity:.2f}} kcal/mol")
print(f"   Error Margin: {{abs(corrected_affinity - affinity):.4f}} kcal/mol")

print("\\n" + "="*80)
print("✅ QPHAROS 5-Layer Architecture Complete!")
print("🎯 All quantum layers executed successfully")
print("="*80)
'''

            else:
                # Schema 2: Functional API (DEFAULT)
                code = f'''# QPHAROS Schema 2: Functional API (Research-grade)
# Install: pip install qpharos
# Set env: export BIOQL_API_KEY=\'your_key_here\'

from qpharos import dock, predict_admet
import os

api_key = os.getenv(\'BIOQL_API_KEY\', \'your_api_key_here\')

print("="*80)
print("🔶 QPHAROS - Functional API (Schema 2)")
print(f"Ligand SMILES: {smiles}")
print(f"Receptor PDB: {pdb}")
print(f"Backend: {backend}")
print(f"Shots: {shots}")
print("="*80)

# Molecular docking with full parameter control
print("\\n⚛️  Running quantum molecular docking...")
result = dock(
    ligand=\'{smiles}\',
    receptor=\'{pdb}\',
    api_key=api_key,
    backend=\'{backend}\',
    shots={shots},
    qec=True
)

print(f"\\n✅ Docking Complete!")
print(f"\\n📊 Results:")
print(f"   Binding Affinity: {{result.binding_affinity:.2f}} kcal/mol")
print(f"   Ki: {{result.ki:.2f}} nM")
print(f"   IC50: {{result.ic50:.2f}} nM")

# Interactions
if result.interactions:
    print(f"\\n🔗 Molecular Interactions:")
    print(f"   H-bonds: {{result.interactions.get(\'h_bonds\', \'N/A\')}}")
    print(f"   Hydrophobic: {{result.interactions.get(\'hydrophobic\', \'N/A\')}}")
    print(f"   π-stacking: {{result.interactions.get(\'pi_stacking\', \'N/A\')}}")

# ADMET prediction
print("\\n💊 Running ADMET prediction...")
admet = predict_admet(
    smiles=\'{smiles}\',
    api_key=api_key,
    backend=\'{backend}\',
    shots=1500
)

print(f"\\n🔬 ADMET Properties:")
print(f"   Lipinski Pass: {{admet.lipinski_pass}}")
print(f"   QED Score: {{admet.qed_score:.2f}}")
print(f"   LogP: {{admet.logp:.2f}}")
print(f"   Solubility: {{admet.solubility}}")
print(f"   BBB Permeability: {{admet.bbb_permeability}}")

print(f"\\n🔗 IBM Job: https://quantum.ibm.com/jobs/{{result.job_id}}")

print("\\n" + "="*80)
print("✅ QPHAROS Functional API Complete!")
print("="*80)
'''

            return {
                "code": code,
                "success": True,
                "schema": f"QPHAROS Schema {qpharos_schema}"
            }


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

            # Check if QEC is mentioned
            enable_qec = any(kw in prompt_lower for kw in ['qec', 'error correction', 'surface code', 'quillow', 'steane', 'shor'])

            # Extract QEC parameters if present
            qec_type = 'surface_code'  # default
            logical_qubits = 2  # default

            if enable_qec:
                if 'steane' in prompt_lower:
                    qec_type = 'steane'
                elif 'shor' in prompt_lower:
                    qec_type = 'shor'

                # Extract logical qubits
                logical_match = re.search(r'(\d+)\s+logical\s+qubits?', prompt_lower)
                if logical_match:
                    logical_qubits = int(logical_match.group(1))

            ligand = ligand_match.group(1) if ligand_match else "ligand"
            receptor = receptor_match.group(1) if receptor_match else "receptor"
            smiles = smiles_match.group(1) if smiles_match else "SMILES_HERE"
            pdb = pdb_match.group(1) if pdb_match else "PDB_ID_HERE"

            # Build QEC parameters string if enabled
            qec_params = ""
            qec_info = ""
            if enable_qec:
                qec_params = f",\n    qec_enabled=True,\n    qec_type='{qec_type}',\n    logical_qubits={logical_qubits}"
                qec_info = f" using {qec_type} error correction with {logical_qubits} logical qubits"

            # Check if user wants Quillow explicit setup
            use_quillow_explicit = 'quillow' in prompt_lower and enable_qec

            # Check if user wants to save artifacts
            save_artifacts = 'save' in prompt_lower or 'artifact' in prompt_lower or 'report' in prompt_lower

            # Generate comprehensive QUANTUM docking code (BioQL 5.6.2 API)
            code = f'''from bioql import quantum
import os
from pathlib import Path
import json
from datetime import datetime

# Import Quillow for real quantum error correction
{"try:" if use_quillow_explicit else "# Quillow QEC will be handled by BioQL backend"}
{"    import importlib" if use_quillow_explicit else ""}
{"    quillow = importlib.import_module('quillow')" if use_quillow_explicit else ""}
{"    SurfaceCodeSimulator = getattr(quillow, 'SurfaceCodeSimulator', None)" if use_quillow_explicit else ""}
{"    MWPMDecoder = getattr(quillow, 'MWPMDecoder', None)" if use_quillow_explicit else ""}
{"    if SurfaceCodeSimulator is None or MWPMDecoder is None:" if use_quillow_explicit else ""}
{"        raise ImportError('quillow installed but missing expected classes')" if use_quillow_explicit else ""}
{"    QUILLOW_AVAILABLE = True" if use_quillow_explicit else ""}
{"    print('✅ Quillow QEC engine loaded')" if use_quillow_explicit else ""}
{"except Exception:" if use_quillow_explicit else ""}
{"    QUILLOW_AVAILABLE = False" if use_quillow_explicit else ""}
{"    SurfaceCodeSimulator = None" if use_quillow_explicit else ""}
{"    MWPMDecoder = None" if use_quillow_explicit else ""}
{"    print('⚠️  Quillow not available - using BioQL native QEC')" if use_quillow_explicit else ""}

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("="*80)
print("🧬 QUANTUM Molecular Docking: {ligand.capitalize()} → {receptor.upper()}")
print(f"Ligand: {ligand}")
print(f"SMILES: {smiles}")
print(f"Receptor: {receptor}")
print(f"PDB ID: {pdb}")
{f'print("QEC Type: {qec_type}")' if enable_qec else ''}
{f'print("Logical Qubits: {logical_qubits}")' if enable_qec else ''}
print(f"Backend: {backend}")
print(f"Shots: {shots}")
print("="*80)

# Neutralize charged atoms in SMILES (AutoDock Vina compatibility)
try:
    from rdkit import Chem
    from rdkit.Chem.MolStandardize import rdMolStandardize
    mol = Chem.MolFromSmiles("{smiles}")
    if mol:
        uncharger = rdMolStandardize.Uncharger()
        mol_neutral = uncharger.uncharge(mol)
        smiles_neutralized = Chem.MolToSmiles(mol_neutral)
        if smiles_neutralized != "{smiles}":
            print(f"\\n⚠️  Neutralized SMILES: {{smiles_neutralized}}")
        else:
            smiles_neutralized = "{smiles}"
    else:
        smiles_neutralized = "{smiles}"
except Exception as e:
    print(f"\\n⚠️  Could not neutralize SMILES: {{e}}")
    smiles_neutralized = "{smiles}"

{"# ============================================================================" if use_quillow_explicit else ""}
{"# QUILLOW QUANTUM ERROR CORRECTION SETUP" if use_quillow_explicit else ""}
{"# ============================================================================" if use_quillow_explicit else ""}
{f"qec_distance = 3  # Surface code distance" if use_quillow_explicit else ""}
{f"qec_physical_qubits = (2 * qec_distance - 1) ** 2" if use_quillow_explicit else ""}
{f"qec_logical_qubits = {logical_qubits}" if use_quillow_explicit else ""}
{"" if use_quillow_explicit else ""}
{"if QUILLOW_AVAILABLE:" if use_quillow_explicit else ""}
{"    print(f'\\n🛡️  Initializing Quillow QEC Protection')" if use_quillow_explicit else ""}
{"    print(f'   Surface Code Distance: d={{qec_distance}}')" if use_quillow_explicit else ""}
{"    print(f'   Physical Qubits: {{qec_physical_qubits}} per logical qubit')" if use_quillow_explicit else ""}
{"    print(f'   Total Physical Qubits: {{qec_physical_qubits * qec_logical_qubits}}')" if use_quillow_explicit else ""}
{"    print(f'   Decoder: Minimum Weight Perfect Matching (MWPM)')" if use_quillow_explicit else ""}
{"    qec_simulator = SurfaceCodeSimulator(distance=qec_distance)" if use_quillow_explicit else ""}
{"    decoder = MWPMDecoder()" if use_quillow_explicit else ""}
{"    print(f'   ✅ Quillow QEC initialized - ready for fault-tolerant computation')" if use_quillow_explicit else ""}
{"    print('-' * 60)" if use_quillow_explicit else ""}

# Execute VQE on REAL quantum hardware (IBM Quantum)
print(f"\\n⚛️  Executing quantum docking{' with QEC protection' if enable_qec else ''}...")
result = quantum(
    f"Analyze ligand with SMILES {{smiles_neutralized}} docking to receptor PDB {pdb}{qec_info}. "
    f"Calculate binding affinity in kcal/mol, explore conformational space, "
    f"identify key interactions, calculate Ki using thermodynamic formula "
    f"(Ki = exp(ΔG/RT) where R=1.987 cal/mol·K, T=298K), "
    f"and return docking scores with pharmacological parameters.",
    backend='{backend}',
    shots={shots},
    api_key=api_key{qec_params}
)

print(f"\\n✅ QUANTUM Docking Complete!")
print(f"Backend: {{result.backend if hasattr(result, 'backend') else '{backend}'}}")
print(f"Success: {{result.success}}")

# Access bio_interpretation for comprehensive data
bio = getattr(result, 'bio_interpretation', {{}})

# Binding affinity and thermodynamics
if bio.get('binding_affinity'):
    affinity = bio['binding_affinity']
    print(f"\\n⚛️  Binding Affinity (from VQE): {{affinity:.2f}} kcal/mol")

    # Calculate Ki from thermodynamic formula if not provided
    if not bio.get('ki') and affinity:
        import math
        R = 1.987e-3  # kcal/mol·K
        T = 298.15    # K (25°C)
        Ki_M = math.exp(affinity / (R * T))  # Molar
        Ki_nM = Ki_M * 1e9  # Convert to nM
        print(f"   Ki (calculated): {{Ki_nM:.2f}} nM")
        bio['ki'] = Ki_nM
    elif bio.get('ki'):
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

# Drug-likeness
if bio.get('qed_score') is not None:
    print(f"\\n💊 Drug-Likeness:")
    print(f"   QED: {{bio['qed_score']:.2f}}")
    print(f"   Lipinski: {{'✅ Pass' if bio.get('lipinski_pass') else '❌ Fail'}}")

{"# ============================================================================" if save_artifacts else ""}
{"# SAVE RESULTS TO ARTIFACTS" if save_artifacts else ""}
{"# ============================================================================" if save_artifacts else ""}
{"artifacts_dir = Path('artifacts')" if save_artifacts else ""}
{"artifacts_dir.mkdir(exist_ok=True)" if save_artifacts else ""}
{"" if save_artifacts else ""}
{"# Save quantum provenance" if save_artifacts else ""}
{"provenance = {{" if save_artifacts else ""}
{"    'timestamp': datetime.now().isoformat()," if save_artifacts else ""}
{"    'ligand': '{ligand}'," if save_artifacts else ""}
{"    'smiles': smiles_neutralized," if save_artifacts else ""}
{"    'receptor': '{receptor}'," if save_artifacts else ""}
{"    'pdb': '{pdb}'," if save_artifacts else ""}
{"    'backend': '{backend}'," if save_artifacts else ""}
{"    'shots': {shots}," if save_artifacts else ""}
{f"    'qec_enabled': True," if save_artifacts and enable_qec else ""}
{f"    'qec_type': '{qec_type}'," if save_artifacts and enable_qec else ""}
{f"    'logical_qubits': {logical_qubits}," if save_artifacts and enable_qec else ""}
{"    'results': bio" if save_artifacts else ""}
{"}}" if save_artifacts else ""}
{"" if save_artifacts else ""}
{"provenance_file = artifacts_dir / f'docking_provenance_{{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}}.json'" if save_artifacts else ""}
{"with open(provenance_file, 'w') as f:" if save_artifacts else ""}
{"    json.dump(provenance, f, indent=2)" if save_artifacts else ""}
{"print(f'\\n💾 Quantum provenance saved: {{provenance_file}}')" if save_artifacts else ""}
{"" if save_artifacts else ""}
{"# Generate professional report" if save_artifacts else ""}
{"report_file = artifacts_dir / f'docking_report_{{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}}.txt'" if save_artifacts else ""}
{"with open(report_file, 'w') as f:" if save_artifacts else ""}
{"    f.write('='*80 + '\\n')" if save_artifacts else ""}
{"    f.write('QUANTUM MOLECULAR DOCKING REPORT\\n')" if save_artifacts else ""}
{"    f.write('='*80 + '\\n\\n')" if save_artifacts else ""}
{"    f.write(f'Date: {{datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}}\\n')" if save_artifacts else ""}
{"    f.write(f'Ligand: {ligand}\\n')" if save_artifacts else ""}
{"    f.write(f'SMILES: {{smiles_neutralized}}\\n')" if save_artifacts else ""}
{"    f.write(f'Receptor: {receptor} (PDB: {pdb})\\n')" if save_artifacts else ""}
{"    f.write(f'Backend: {backend}\\n')" if save_artifacts else ""}
{"    f.write(f'Shots: {shots}\\n')" if save_artifacts else ""}
{f"    f.write(f'QEC: {qec_type} with {logical_qubits} logical qubits\\n')" if save_artifacts and enable_qec else ""}
{"    f.write('\\n' + '='*80 + '\\n')" if save_artifacts else ""}
{"    f.write('RESULTS\\n')" if save_artifacts else ""}
{"    f.write('='*80 + '\\n\\n')" if save_artifacts else ""}
{"    if bio.get('binding_affinity'):" if save_artifacts else ""}
{"        f.write(f'Binding Affinity: {{bio[\"binding_affinity\"]:.2f}} kcal/mol\\n')" if save_artifacts else ""}
{"    if bio.get('ki'):" if save_artifacts else ""}
{"        f.write(f'Ki: {{bio[\"ki\"]:.2f}} nM\\n')" if save_artifacts else ""}
{"    if bio.get('ic50'):" if save_artifacts else ""}
{"        f.write(f'IC50: {{bio[\"ic50\"]:.2f}} nM\\n')" if save_artifacts else ""}
{"    f.write('\\n')" if save_artifacts else ""}
{"    if bio.get('h_bonds'):" if save_artifacts else ""}
{"        f.write('Molecular Interactions:\\n')" if save_artifacts else ""}
{"        f.write(f'  H-bonds: {{bio.get(\"h_bonds\", \"N/A\")}}\\n')" if save_artifacts else ""}
{"        f.write(f'  Hydrophobic: {{bio.get(\"hydrophobic_contacts\", \"N/A\")}}\\n')" if save_artifacts else ""}
{"        f.write(f'  π-stacking: {{bio.get(\"pi_stacking\", \"N/A\")}}\\n')" if save_artifacts else ""}
{"        f.write(f'  Salt bridges: {{bio.get(\"salt_bridges\", \"N/A\")}}\\n')" if save_artifacts else ""}
{"print(f'\\n📄 Professional report saved: {{report_file}}')" if save_artifacts else ""}

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

QUANTUM ERROR CORRECTION (QEC) - CORRECT USAGE:
- Surface codes with d=3, 5, 7, 9 (higher distance = more protection)
- Below-threshold operation: logical errors decrease exponentially with distance
- Real-time syndrome extraction and MWPM decoding
- Automatic protection for quantum chemistry calculations
- Backends: Stim (fast simulator), BioQL API (hardware), Modal (GPU)

✅ CORRECT QEC Parameters for quantum() function:
result = quantum(
    "Your prompt here",
    backend='ibm_torino',
    shots=2000,
    api_key=api_key,
    qec_enabled=True,              # ✅ Use this
    qec_type='surface_code',       # ✅ Use this: 'surface_code', 'steane', or 'shor'
    logical_qubits=2               # ✅ Use this
)

❌ NEVER use qec_config={} - This parameter does NOT exist!

QEC Examples:
1. Docking with QEC: quantum("Analyze SMILES ... with surface_code QEC", qec_enabled=True, qec_type='surface_code', logical_qubits=2)
2. Drug design with QEC: quantum("Design drug for diabetes", backend='ibm_torino', qec_enabled=True, qec_type='surface_code', logical_qubits=3)
3. Without QEC: quantum("Create Bell state", backend='simulator', shots=1000)

Quillow Direct Usage (for advanced QEC):
1. Basic: from quillow import SurfaceCodeSimulator; sim = SurfaceCodeSimulator(distance=5); result = sim.run(shots=10000)
2. Protected Chemistry: from quillow import BioQLOptimizer; optimizer = BioQLOptimizer(api_key="...", qec_distance=5)
3. Threshold Analysis: Run multiple distances (3,5,7) to demonstrate below-threshold

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
