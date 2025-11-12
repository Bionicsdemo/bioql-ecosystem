# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS High-Level API
Simple functions that use BioQL under the hood
"""

import os
from typing import Any, Dict, List, Optional

from bioql import quantum

from .models import ADMETResult, DockingResult, DrugDesignResult


def dock(
    ligand: str,
    receptor: str,
    binding_site: Optional[str] = None,
    api_key: Optional[str] = None,
    backend: str = "ibm_torino",
    shots: int = 2000,
    qec: bool = True,
) -> DockingResult:
    """
    Perform QPHAROS 5-layer quantum molecular docking.

    Args:
        ligand: SMILES string of ligand molecule
        receptor: PDB ID or structure of receptor protein
        binding_site: Optional binding site specification
        api_key: BioQL API key (or set BIOQL_API_KEY environment variable)
        backend: Quantum backend ('ibm_torino', 'ibm_kyoto', 'simulator')
        shots: Number of quantum shots (default: 2000)
        qec: Enable Quantum Error Correction (default: True)

    Returns:
        DockingResult with binding affinity, Ki, IC50, interactions, etc.

    Example:
        >>> from qpharos import dock
        >>> result = dock(
        ...     ligand='COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2',
        ...     receptor='6B3J',
        ...     api_key='bioql_xxx'
        ... )
        >>> print(f"Binding Affinity: {result.binding_affinity} kcal/mol")
        >>> print(f"Ki: {result.ki} nM")
    """

    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv("BIOQL_API_KEY")
        if not api_key:
            raise ValueError(
                "API key required. Provide api_key parameter or set BIOQL_API_KEY environment variable.\\n"
                "Get your key at: https://bioql.bio/signup"
            )

    # Build QPHAROS prompt
    prompt = f"""QPHAROS 5-Layer Quantum Drug Discovery:

Molecular Docking Analysis:
Ligand SMILES: {ligand}
Receptor: {receptor}
"""

    if binding_site:
        prompt += f"Binding Site: {binding_site}\\n"

    prompt += """
QPHAROS Quantum Layers:
1. Quantum Feature Encoding: Encode molecular properties into quantum states
2. Quantum Entanglement Mapping: Map protein-ligand interactions via entanglement
3. Quantum Conformational Search: Use QAOA to explore conformational space
4. Quantum Scoring Function: Calculate binding affinity using VQE
"""

    if qec:
        prompt += "5. Quantum Error Correction: Apply Surface Code QEC for validation\\n"

    prompt += """
Calculate using VQE quantum computation:
- Binding affinity (kcal/mol) from quantum energy states
- Inhibition constant Ki (nM) using: Ki = exp(ΔG/RT) where R=1.987 cal/(mol·K), T=298K
- IC50 (nM) from Ki approximation
- Key molecular interactions: H-bonds, hydrophobic contacts, π-π stacking
- Docking score with confidence level
"""

    # Execute via BioQL
    result = quantum(prompt, backend=backend, shots=shots, api_key=api_key)

    # Parse results into DockingResult
    return DockingResult.from_bioql_result(result)


def predict_admet(
    smiles: str, api_key: Optional[str] = None, backend: str = "ibm_torino", shots: int = 1500
) -> ADMETResult:
    """
    Predict ADMET properties using QPHAROS quantum algorithms.

    Args:
        smiles: SMILES string of molecule
        api_key: BioQL API key
        backend: Quantum backend
        shots: Number of quantum shots

    Returns:
        ADMETResult with absorption, distribution, metabolism, excretion, toxicity

    Example:
        >>> from qpharos import predict_admet
        >>> result = predict_admet('COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2')
        >>> print(f"Lipinski Pass: {result.lipinski_pass}")
        >>> print(f"QED Score: {result.qed_score}")
    """

    if api_key is None:
        api_key = os.getenv("BIOQL_API_KEY")

    prompt = f"""QPHAROS Quantum ADMET Prediction:

Molecule SMILES: {smiles}

Calculate using quantum feature encoding and VQE:

ADMET Properties:
- Absorption: Caco-2 permeability, Human Intestinal Absorption (HIA)
- Distribution: Volume of distribution (VDss), Plasma protein binding (PPB)
- Metabolism: CYP450 enzyme interactions (CYP3A4, CYP2D6, CYP2C9)
- Excretion: Clearance (CL), Half-life (t1/2)
- Toxicity: hERG inhibition, AMES mutagenicity, LD50

Drug-likeness:
- Lipinski Rule of 5 compliance
- QED (Quantitative Estimate of Drug-likeness) score
- Synthetic Accessibility (SA Score)
- PAINS alerts
"""

    result = quantum(prompt, backend=backend, shots=shots, api_key=api_key)
    return ADMETResult.from_bioql_result(result)


def design_drug(
    target_protein: str,
    scaffold: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    backend: str = "ibm_torino",
    shots: int = 3000,
) -> DrugDesignResult:
    """
    Design novel drug candidates using QPHAROS QGAN.

    Args:
        target_protein: PDB ID of target protein
        scaffold: Optional molecular scaffold (SMILES) to constrain generation
        constraints: Optional constraints (MW, logP, etc.)
        api_key: BioQL API key
        backend: Quantum backend
        shots: Number of quantum shots

    Returns:
        DrugDesignResult with generated molecules, scores, properties

    Example:
        >>> from qpharos import design_drug
        >>> result = design_drug(
        ...     target_protein='6B3J',
        ...     constraints={'MW': (300, 500), 'logP': (0, 5)}
        ... )
        >>> for mol in result.molecules[:5]:
        ...     print(f"{mol.smiles}: Score {mol.score}")
    """

    if api_key is None:
        api_key = os.getenv("BIOQL_API_KEY")

    prompt = f"""QPHAROS Quantum Drug Design (QGAN):

Target Protein: {target_protein}
"""

    if scaffold:
        prompt += f"Scaffold: {scaffold}\\n"

    prompt += """
Use Quantum Generative Adversarial Network (QGAN) to design novel drug candidates:

1. Generator: 8-layer quantum circuit to generate molecular graphs
2. Discriminator: 6-layer quantum circuit to evaluate drug-likeness
3. Quantum Feature Encoding of training molecules
4. Adversarial training loop for 100 iterations

Generate 10 novel molecules optimized for:
- Binding affinity to target
- Drug-likeness (QED score)
- Synthetic accessibility
- Lipinski Rule of 5 compliance
"""

    if constraints:
        prompt += f"\\nConstraints: {constraints}\\n"

    result = quantum(prompt, backend=backend, shots=shots, api_key=api_key)
    return DrugDesignResult.from_bioql_result(result)


def screen_library(
    ligands: List[str],
    receptor: str,
    api_key: Optional[str] = None,
    backend: str = "ibm_torino",
    shots_per_ligand: int = 1000,
) -> List[DockingResult]:
    """
    Screen a library of ligands against a receptor (batch docking).

    Args:
        ligands: List of SMILES strings
        receptor: PDB ID of receptor
        api_key: BioQL API key
        backend: Quantum backend
        shots_per_ligand: Shots per ligand (default: 1000)

    Returns:
        List of DockingResult objects, sorted by binding affinity

    Example:
        >>> from qpharos import screen_library
        >>> ligands = ['CCO', 'CC(C)O', 'CCCO']  # Example library
        >>> results = screen_library(ligands, '6B3J')
        >>> best = results[0]
        >>> print(f"Best ligand: {best.ligand_smiles}")
    """

    if api_key is None:
        api_key = os.getenv("BIOQL_API_KEY")

    results = []

    for ligand in ligands:
        result = dock(
            ligand=ligand,
            receptor=receptor,
            api_key=api_key,
            backend=backend,
            shots=shots_per_ligand,
            qec=False,  # Disable QEC for faster screening
        )
        results.append(result)

    # Sort by binding affinity (most negative = strongest)
    results.sort(key=lambda r: r.binding_affinity if r.binding_affinity else float("inf"))

    return results


def optimize_lead(
    lead_smiles: str,
    receptor: str,
    iterations: int = 5,
    api_key: Optional[str] = None,
    backend: str = "ibm_torino",
) -> List[DockingResult]:
    """
    Optimize a lead compound using quantum-guided modifications.

    Args:
        lead_smiles: SMILES of lead compound
        receptor: PDB ID of receptor
        iterations: Number of optimization iterations
        api_key: BioQL API key
        backend: Quantum backend

    Returns:
        List of DockingResult for original + optimized variants

    Example:
        >>> from qpharos import optimize_lead
        >>> results = optimize_lead(
        ...     lead_smiles='COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2',
        ...     receptor='6B3J',
        ...     iterations=3
        ... )
        >>> for r in results:
        ...     print(f"{r.ligand_smiles}: {r.binding_affinity} kcal/mol")
    """

    if api_key is None:
        api_key = os.getenv("BIOQL_API_KEY")

    results = []

    # Dock original lead
    original = dock(lead_smiles, receptor, api_key=api_key, backend=backend)
    results.append(original)

    for i in range(iterations):
        # Use QGAN to generate variants
        design_result = design_drug(
            target_protein=receptor,
            scaffold=lead_smiles,
            api_key=api_key,
            backend=backend,
            shots=2000,
        )

        # Dock best variant from this iteration
        if design_result.molecules:
            best_variant = design_result.molecules[0]
            variant_result = dock(best_variant.smiles, receptor, api_key=api_key, backend=backend)
            results.append(variant_result)

    return results
