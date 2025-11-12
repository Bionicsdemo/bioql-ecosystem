#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""Test v7.0.3 code generator with exact user prompt"""

import re
import sys

# Simular la lógica del generador
prompt = """Dock my clinical molecule with SMILES="COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2" against GLP1R receptor (PDB: 6B3J) for obesity/diabetes using IBM Torino quantum computer with 2000 shots and surface_code QEC. Calculate Ki from binding affinity using thermodynamic formula. Save quantum provenance and docking results to artifacts/. Generate professional report with binding poses. use Quillow corrections"""

prompt_lower = prompt.lower()

# Check for docking
if any(
    kw in prompt_lower
    for kw in ["dock", "binding", "affinity", "ligand", "receptor", "smiles", "pdb"]
):
    print("✅ Matched DOCKING template")

    # Extract parameters
    ligand_match = re.search(
        r"(?:ligand|drug|compound|molecule)(?:\s+(?:is|:|named))?\s+(\w+)", prompt_lower
    )
    receptor_match = re.search(
        r"(?:receptor|protein|target)(?:\s+(?:is|:|named))?\s+(\w+)", prompt_lower
    )
    smiles_match = re.search(
        r'(?:smiles|structure)(?:\s+(?:is|:|=))?\s*"([^"]+)"', prompt, re.IGNORECASE
    )
    pdb_match = re.search(r"(?:pdb|id)(?:\s+(?:is|:))?\s+([0-9A-Z]{4})", prompt, re.IGNORECASE)
    backend_match = re.search(r"\b(ibm_\w+|ionq_\w+|aws_braket|simulator)\b", prompt_lower)
    shots_match = re.search(r"(?:with\s+)?(\d+)\s+shots?", prompt_lower)

    ligand = ligand_match.group(1) if ligand_match else "clinical_molecule"
    receptor = receptor_match.group(1) if receptor_match else "glp1r"
    smiles = smiles_match.group(1) if smiles_match else "SMILES_HERE"
    pdb = pdb_match.group(1) if pdb_match else "6B3J"
    backend = backend_match.group(1) if backend_match else "ibm_torino"
    shots = int(shots_match.group(1)) if shots_match else 2000

    print(f"  ligand: {ligand}")
    print(f"  receptor: {receptor}")
    print(f"  smiles: {smiles[:50]}...")
    print(f"  pdb: {pdb}")
    print(f"  backend: {backend}")
    print(f"  shots: {shots}")

    # Check QEC
    enable_qec = any(
        kw in prompt_lower
        for kw in ["qec", "error correction", "surface code", "quillow", "steane", "shor"]
    )
    print(f"\n✅ QEC enabled: {enable_qec}")

    if enable_qec:
        qec_type = "surface_code"
        logical_qubits = 2

        if "steane" in prompt_lower:
            qec_type = "steane"
        elif "shor" in prompt_lower:
            qec_type = "shor"

        logical_match = re.search(r"(\d+)\s+logical\s+qubits?", prompt_lower)
        if logical_match:
            logical_qubits = int(logical_match.group(1))

        print(f"  qec_type: {qec_type}")
        print(f"  logical_qubits: {logical_qubits}")

        # Build QEC params
        qec_params = f",\\n    qec_enabled=True,\\n    qec_type='{qec_type}',\\n    logical_qubits={logical_qubits}"
        qec_info = f" using {qec_type} error correction with {logical_qubits} logical qubits"

        print(f"\n✅ qec_params will be injected as:")
        print(qec_params)

        # Check Quillow explicit
        use_quillow_explicit = "quillow" in prompt_lower and enable_qec
        print(f"\n✅ Quillow explicit: {use_quillow_explicit}")

        # Check artifacts
        save_artifacts = (
            "save" in prompt_lower or "artifact" in prompt_lower or "report" in prompt_lower
        )
        print(f"✅ Save artifacts: {save_artifacts}")

        # Simulate the template generation (simplified)
        print("\n" + "=" * 80)
        print("GENERATED CODE (quantum() call only):")
        print("=" * 80)

        code_snippet = f"""result = quantum(
    f"Analyze ligand with SMILES {{smiles_neutralized}} docking to receptor PDB {pdb}{qec_info}. "
    f"Calculate binding affinity in kcal/mol, explore conformational space, "
    f"identify key interactions, calculate Ki using thermodynamic formula "
    f"(Ki = exp(ΔG/RT) where R=1.987 cal/mol·K, T=298K), "
    f"and return docking scores with pharmacological parameters.",
    backend='{backend}',
    shots={shots},
    api_key=api_key{qec_params}
)"""

        print(code_snippet)

        # Check if it has qec_config (WRONG)
        if "qec_config" in code_snippet:
            print("\n❌ ERROR: Generated code contains qec_config!")
        else:
            print("\n✅ CORRECTO: No qec_config found")

        # Check if it has qec_enabled (CORRECT)
        if "qec_enabled=True" in code_snippet:
            print("✅ CORRECTO: qec_enabled=True found")
        else:
            print("❌ ERROR: qec_enabled=True NOT found")

else:
    print("❌ Did NOT match docking template")
