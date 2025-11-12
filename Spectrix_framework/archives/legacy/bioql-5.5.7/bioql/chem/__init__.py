"""
BioQL Chemistry Module

Provides chemical structure manipulation, conversion, and preparation
for drug discovery applications.

Main Features:
- Ligand preparation from SMILES
- Receptor (protein) preparation from PDB
- Format conversions (PDB, PDBQT, MOL2, SDF)
- 3D conformer generation
- Energy minimization

Example:
    >>> from bioql.chem import prepare_ligand, prepare_receptor
    >>> ligand = prepare_ligand("CCO")  # Ethanol SMILES
    >>> receptor = prepare_receptor("protein.pdb")
"""

__all__ = [
    "prepare_ligand",
    "prepare_receptor",
    "GeometryOptimizer",
    "calculate_pharmaceutical_scores",
    "PharmaceuticalScores",
    "neutralize_smiles",
]

# Lazy imports to avoid hard dependencies
def prepare_ligand(*args, **kwargs):
    """Prepare ligand from SMILES string for docking."""
    from .ligand_prep import prepare_ligand as _prepare_ligand
    return _prepare_ligand(*args, **kwargs)


def prepare_receptor(*args, **kwargs):
    """Prepare protein receptor from PDB file for docking."""
    from .receptor_prep import prepare_receptor as _prepare_receptor
    return _prepare_receptor(*args, **kwargs)


class GeometryOptimizer:
    """Molecular geometry optimization using available backends."""

    def __init__(self):
        from .geometry import GeometryOptimizer as _GeometryOptimizer
        self._optimizer = _GeometryOptimizer()

    def optimize(self, *args, **kwargs):
        return self._optimizer.optimize(*args, **kwargs)


def calculate_pharmaceutical_scores(*args, **kwargs):
    """Calculate pharmaceutical scores (Lipinski, QED, SA Score, etc.)."""
    from .pharma_scores import calculate_pharmaceutical_scores as _calc_scores
    return _calc_scores(*args, **kwargs)


class PharmaceuticalScores:
    """Pharmaceutical scoring for drug candidates."""

    def __init__(self):
        from .pharma_scores import PharmaceuticalScores as _PharmaScores
        self._scorer = _PharmaScores()

    def calculate_all(self, *args, **kwargs):
        return self._scorer.calculate_all(*args, **kwargs)


def neutralize_smiles(*args, **kwargs):
    """Neutralize charged SMILES for AutoDock Vina compatibility."""
    from .neutralize import neutralize_smiles as _neutralize
    return _neutralize(*args, **kwargs)