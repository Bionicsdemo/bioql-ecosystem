# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Chemistry utilities for molecule validation and property calculations.
"""

from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors


def sanitize_molecule(smiles: str) -> Tuple[bool, str]:
    """
    Validate and sanitize a SMILES string.

    Args:
        smiles: SMILES string to validate

    Returns:
        Tuple of (is_valid: bool, reason: str)
        If valid, reason is empty string. If invalid, reason explains why.
    """
    if not smiles or not isinstance(smiles, str):
        return False, "Empty or invalid SMILES string"

    smiles = smiles.strip()

    try:
        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            return False, "Invalid SMILES syntax - cannot parse"

        # Try to sanitize
        try:
            Chem.SanitizeMol(mol)
        except Exception as e:
            return False, f"Sanitization failed: {str(e)}"

        # Check for valid structure
        if mol.GetNumAtoms() == 0:
            return False, "Molecule has no atoms"

        if mol.GetNumAtoms() > 200:
            return False, "Molecule too large (>200 atoms)"

        # Check for disconnected fragments
        frags = Chem.GetMolFrags(mol, asMols=True)
        if len(frags) > 1:
            return False, f"Disconnected structure ({len(frags)} fragments)"

        return True, ""

    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def check_lipinski(mol: Chem.Mol) -> Dict[str, any]:
    """
    Check Lipinski's Rule of Five.

    Criteria:
    - Molecular weight ≤ 500 Da
    - LogP ≤ 5
    - H-bond donors ≤ 5
    - H-bond acceptors ≤ 10

    Args:
        mol: RDKit molecule object

    Returns:
        Dictionary with keys:
            - mw: float
            - logp: float
            - hbd: int (H-bond donors)
            - hba: int (H-bond acceptors)
            - passes: bool
            - violations: int
    """
    if mol is None:
        return {
            "mw": None,
            "logp": None,
            "hbd": None,
            "hba": None,
            "passes": False,
            "violations": 4,
        }

    try:
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)

        violations = 0
        if mw > 500:
            violations += 1
        if logp > 5:
            violations += 1
        if hbd > 5:
            violations += 1
        if hba > 10:
            violations += 1

        return {
            "mw": round(mw, 2),
            "logp": round(logp, 2),
            "hbd": hbd,
            "hba": hba,
            "passes": violations == 0,
            "violations": violations,
        }

    except Exception as e:
        print(f"Error calculating Lipinski properties: {e}")
        return {
            "mw": None,
            "logp": None,
            "hbd": None,
            "hba": None,
            "passes": False,
            "violations": 4,
        }


def check_veber(mol: Chem.Mol) -> Dict[str, any]:
    """
    Check Veber's rules for oral bioavailability.

    Criteria:
    - Rotatable bonds ≤ 10
    - Polar surface area (PSA) ≤ 140 Å²

    Args:
        mol: RDKit molecule object

    Returns:
        Dictionary with keys:
            - rotatable_bonds: int
            - psa: float
            - passes: bool
            - violations: int
    """
    if mol is None:
        return {"rotatable_bonds": None, "psa": None, "passes": False, "violations": 2}

    try:
        rotatable_bonds = Descriptors.NumRotatableBonds(mol)
        psa = Descriptors.TPSA(mol)

        violations = 0
        if rotatable_bonds > 10:
            violations += 1
        if psa > 140:
            violations += 1

        return {
            "rotatable_bonds": rotatable_bonds,
            "psa": round(psa, 2),
            "passes": violations == 0,
            "violations": violations,
        }

    except Exception as e:
        print(f"Error calculating Veber properties: {e}")
        return {"rotatable_bonds": None, "psa": None, "passes": False, "violations": 2}


def check_pains(mol: Chem.Mol) -> List[str]:
    """
    Check for Pan-Assay Interference Compounds (PAINS).

    Uses RDKit's built-in PAINS filters.

    Args:
        mol: RDKit molecule object

    Returns:
        List of PAINS alert descriptions (empty if no alerts)
    """
    if mol is None:
        return ["Invalid molecule"]

    try:
        from rdkit.Chem import FilterCatalog

        params = FilterCatalog.FilterCatalogParams()
        params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
        catalog = FilterCatalog.FilterCatalog(params)

        matches = catalog.GetMatches(mol)

        if matches:
            return [match.GetDescription() for match in matches]
        else:
            return []

    except ImportError:
        print("Warning: FilterCatalog not available, skipping PAINS check")
        return []
    except Exception as e:
        print(f"Error checking PAINS: {e}")
        return []


def check_brenk(mol: Chem.Mol) -> List[str]:
    """
    Check for Brenk's structural alerts (unwanted functionalities).

    Uses RDKit's built-in Brenk filter.

    Args:
        mol: RDKit molecule object

    Returns:
        List of Brenk alert descriptions (empty if no alerts)
    """
    if mol is None:
        return ["Invalid molecule"]

    try:
        from rdkit.Chem import FilterCatalog

        params = FilterCatalog.FilterCatalogParams()
        params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)
        catalog = FilterCatalog.FilterCatalog(params)

        matches = catalog.GetMatches(mol)

        if matches:
            return [match.GetDescription() for match in matches]
        else:
            return []

    except ImportError:
        print("Warning: FilterCatalog not available, skipping Brenk check")
        return []
    except Exception as e:
        print(f"Error checking Brenk: {e}")
        return []


def check_reactive_groups(mol: Chem.Mol) -> List[str]:
    """
    Check for reactive functional groups.

    Checks for:
    - Peroxides (O-O)
    - Azides ([N-]=[N+]=N)
    - N-nitroso (N-N=O)
    - Acid halides
    - Epoxides
    - Aziridines

    Args:
        mol: RDKit molecule object

    Returns:
        List of reactive group descriptions found
    """
    if mol is None:
        return ["Invalid molecule"]

    alerts = []

    # Define SMARTS patterns for reactive groups
    reactive_smarts = {
        "Peroxide": "[OX2][OX2]",
        "Azide": "[N-]=[N+]=N",
        "N-nitroso": "[N;X2]=[N+]=[O-]",
        "N-nitroso (alt)": "[NX2](=O)[NX3]",
        "Acid halide": "[CX3](=[OX1])[F,Cl,Br,I]",
        "Acyl cyanide": "[CX3](=[OX1])[CX2]#[NX1]",
        "Epoxide (3-membered ether)": "C1OC1",
        "Aziridine (3-membered amine)": "C1NC1",
        "Isocyanate": "N=C=O",
        "Isothiocyanate": "N=C=S",
        "Diazo": "[C-]=[N+]=[N-]",
        "Nitroso": "[NX2]=O",
        "Hydroxylamine": "[NX3][OH]",
        "Hydroperoxide": "[OX2H][OX2]",
        "Phosphorane": "[P;X5]",
        "Michael acceptor (simple)": "[CX3]=[CX3][CX3](=[OX1])",
    }

    try:
        for name, smarts in reactive_smarts.items():
            pattern = Chem.MolFromSmarts(smarts)
            if pattern is not None and mol.HasSubstructMatch(pattern):
                alerts.append(name)

        return alerts

    except Exception as e:
        print(f"Error checking reactive groups: {e}")
        return []


def calculate_molecular_properties(mol: Chem.Mol) -> Dict[str, any]:
    """
    Calculate comprehensive molecular properties.

    Args:
        mol: RDKit molecule object

    Returns:
        Dictionary with various molecular properties
    """
    if mol is None:
        return {}

    try:
        props = {
            "molecular_weight": round(Descriptors.MolWt(mol), 2),
            "logp": round(Descriptors.MolLogP(mol), 2),
            "hbd": Descriptors.NumHDonors(mol),
            "hba": Descriptors.NumHAcceptors(mol),
            "tpsa": round(Descriptors.TPSA(mol), 2),
            "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
            "aromatic_rings": Descriptors.NumAromaticRings(mol),
            "heavy_atoms": mol.GetNumHeavyAtoms(),
            "num_atoms": mol.GetNumAtoms(),
            "fraction_csp3": round(Lipinski.FractionCsp3(mol), 3),
        }

        return props

    except Exception as e:
        print(f"Error calculating molecular properties: {e}")
        return {}
