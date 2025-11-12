#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Metabolite Identification and Quantification Module

Author: BioQL Development Team / SpectrixRD
License: MIT
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class Metabolite:
    """Metabolite information."""

    name: str
    hmdb_id: str
    kegg_id: str
    formula: str
    mass: float
    smiles: str
    concentration: Optional[float] = None  # mM or μM


@dataclass
class MetaboliteResult:
    """Metabolite identification result."""

    query_mass: float
    matches: List[Metabolite]
    total_matches: int
    confidence: float
    backend: Optional[str] = None


# Small metabolite database (in production, use full HMDB/KEGG)
METABOLITE_DB = {
    "Glucose": Metabolite(
        name="Glucose",
        hmdb_id="HMDB0000122",
        kegg_id="C00031",
        formula="C6H12O6",
        mass=180.156,
        smiles="OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
    ),
    "Lactate": Metabolite(
        name="Lactate",
        hmdb_id="HMDB0000190",
        kegg_id="C00186",
        formula="C3H6O3",
        mass=90.078,
        smiles="CC(O)C(O)=O",
    ),
    "Pyruvate": Metabolite(
        name="Pyruvate",
        hmdb_id="HMDB0000243",
        kegg_id="C00022",
        formula="C3H4O3",
        mass=88.062,
        smiles="CC(=O)C(O)=O",
    ),
    "ATP": Metabolite(
        name="ATP",
        hmdb_id="HMDB0000538",
        kegg_id="C00002",
        formula="C10H16N5O13P3",
        mass=507.181,
        smiles="C1=NC(=C2C(=N1)N(C=N2)[C@H]3[C@@H]([C@@H]([C@H](O3)COP(=O)(O)OP(=O)(O)OP(=O)(O)O)O)O)N",
    ),
    "ADP": Metabolite(
        name="ADP",
        hmdb_id="HMDB0001341",
        kegg_id="C00008",
        formula="C10H15N5O10P2",
        mass=427.201,
        smiles="C1=NC(=C2C(=N1)N(C=N2)[C@H]3[C@@H]([C@@H]([C@H](O3)COP(=O)(O)OP(=O)(O)O)O)O)N",
    ),
}


def identify_metabolite(
    mass: float, formula: str = None, tolerance: float = 0.01, backend: str = "simulator"
) -> MetaboliteResult:
    """
    Identify metabolite by mass and/or formula.

    Args:
        mass: Exact mass (Da)
        formula: Molecular formula (optional)
        tolerance: Mass tolerance (Da)
        backend: Quantum backend

    Returns:
        MetaboliteResult with matching metabolites

    Example:
        >>> result = identify_metabolite(180.156)
        >>> for match in result.matches:
        ...     print(f"{match.name}: {match.hmdb_id}")
    """
    matches = []

    for metabolite in METABOLITE_DB.values():
        mass_diff = abs(metabolite.mass - mass)

        if mass_diff <= tolerance:
            # Check formula if provided
            if formula and metabolite.formula != formula:
                continue

            # Calculate confidence based on mass match
            confidence = 1.0 - (mass_diff / tolerance)
            metabolite_copy = Metabolite(
                name=metabolite.name,
                hmdb_id=metabolite.hmdb_id,
                kegg_id=metabolite.kegg_id,
                formula=metabolite.formula,
                mass=metabolite.mass,
                smiles=metabolite.smiles,
            )
            matches.append(metabolite_copy)

    # Sort by mass difference
    matches.sort(key=lambda m: abs(m.mass - mass))

    confidence = 0.9 if matches else 0.0

    return MetaboliteResult(
        query_mass=mass,
        matches=matches,
        total_matches=len(matches),
        confidence=confidence,
        backend=backend,
    )


def quantify_metabolites(
    nmr_spectrum: np.ndarray, reference_metabolites: List[str] = None
) -> Dict[str, float]:
    """
    Quantify metabolites from NMR spectrum.

    Args:
        nmr_spectrum: 1D NMR spectrum (ppm vs intensity)
        reference_metabolites: List of expected metabolites

    Returns:
        Dictionary of metabolite concentrations (mM)

    Example:
        >>> spectrum = np.random.rand(1000)
        >>> conc = quantify_metabolites(spectrum, ["Glucose", "Lactate"])
        >>> print(f"Glucose: {conc['Glucose']:.2f} mM")
    """
    # Stub implementation - in production, use peak integration
    concentrations = {}

    if reference_metabolites is None:
        reference_metabolites = list(METABOLITE_DB.keys())

    for metabolite_name in reference_metabolites:
        if metabolite_name in METABOLITE_DB:
            # Simulate concentration (random for now)
            conc = np.random.uniform(0.1, 10.0)
            concentrations[metabolite_name] = conc

    return concentrations


# Example usage
if __name__ == "__main__":
    print("BioQL Metabolomics - Metabolite Identification")
    print("=" * 50)

    # Test mass-based identification
    result = identify_metabolite(180.156, tolerance=0.01)
    print(f"\nQuery mass: {result.query_mass:.3f} Da")
    print(f"Matches found: {result.total_matches}")
    for match in result.matches:
        print(f"  - {match.name} ({match.formula})")
        print(f"    HMDB: {match.hmdb_id}, KEGG: {match.kegg_id}")
        print(f"    Mass: {match.mass:.3f} Da")
