# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Esquema 1: Simple API
Ultra-simplified interface for beginners
"""

import os
from typing import Optional

from .api import dock as _dock
from .api import predict_admet as _predict_admet
from .models import ADMETResult, DockingResult


def quick_dock(ligand: str, receptor: str) -> float:
    """
    Ultra-simple docking - returns only binding affinity.

    Args:
        ligand: SMILES string
        receptor: PDB ID

    Returns:
        Binding affinity in kcal/mol (negative = good binding)

    Example:
        >>> from qpharos.simple import quick_dock
        >>> affinity = quick_dock('CCO', '6B3J')
        >>> print(f"Affinity: {affinity} kcal/mol")
        -6.2 kcal/mol
    """
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        raise ValueError(
            "Set BIOQL_API_KEY environment variable first:\n"
            "export BIOQL_API_KEY='your_key_here'\n"
            "Get key at: https://bioql.bio/signup"
        )

    result = _dock(
        ligand=ligand,
        receptor=receptor,
        api_key=api_key,
        backend="ibm_torino",
        shots=2000,
        qec=True,
    )

    return result.binding_affinity if result.binding_affinity else 0.0


def is_drug_like(smiles: str) -> bool:
    """
    Check if molecule is drug-like (Lipinski Rule of 5).

    Args:
        smiles: SMILES string

    Returns:
        True if drug-like, False otherwise

    Example:
        >>> from qpharos.simple import is_drug_like
        >>> is_drug_like('CCO')
        True
    """
    api_key = os.getenv("BIOQL_API_KEY")
    result = _predict_admet(smiles, api_key=api_key)
    return result.lipinski_pass if result.lipinski_pass is not None else False


def test_molecule(ligand: str, receptor: str) -> dict:
    """
    Quick test: docking + drug-likeness in one call.

    Args:
        ligand: SMILES string
        receptor: PDB ID

    Returns:
        dict with 'affinity', 'drug_like', 'recommendation'

    Example:
        >>> from qpharos.simple import test_molecule
        >>> result = test_molecule('CCO', '6B3J')
        >>> print(result)
        {
            'affinity': -6.2,
            'drug_like': True,
            'recommendation': 'Good candidate - proceed to optimization'
        }
    """
    api_key = os.getenv("BIOQL_API_KEY")

    # Docking
    dock_result = _dock(ligand, receptor, api_key=api_key, shots=2000)
    affinity = dock_result.binding_affinity or 0.0

    # ADMET
    admet_result = _predict_admet(ligand, api_key=api_key, shots=1500)
    drug_like = admet_result.lipinski_pass or False
    qed = admet_result.qed_score or 0.0

    # Recommendation
    if affinity < -8.0 and drug_like and qed > 0.6:
        recommendation = "Excellent candidate - ready for further testing"
    elif affinity < -7.0 and drug_like:
        recommendation = "Good candidate - proceed to optimization"
    elif affinity < -6.0:
        recommendation = "Moderate binding - consider modifications"
    else:
        recommendation = "Weak binding - not recommended"

    return {
        "affinity": affinity,
        "ki_nM": dock_result.ki,
        "drug_like": drug_like,
        "qed_score": qed,
        "recommendation": recommendation,
        "job_id": dock_result.job_id,
    }


# Convenience aliases
dock = quick_dock
druglike = is_drug_like
test = test_molecule
