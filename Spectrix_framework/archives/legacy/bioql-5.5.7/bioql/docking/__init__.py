"""
BioQL Molecular Docking Module

Provides molecular docking capabilities using multiple backends:
- AutoDock Vina (classical)
- Quantum computing (BioQL native)

Main Features:
- Automated ligand-receptor docking
- Multiple backend support with fallbacks
- Result scoring and pose generation
- Integration with visualization

Example:
    >>> from bioql.docking import dock
    >>> result = dock(
    ...     receptor="protein.pdb",
    ...     ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
    ...     backend="vina"
    ... )
    >>> print(f"Binding affinity: {result.score} kcal/mol")
"""

__all__ = [
    "dock",
    "DockingResult",
    "VinaRunner",
    "QuantumRunner",
]

from .pipeline import dock, DockingResult

# Lazy imports for backends
def get_vina_runner():
    from .vina_runner import VinaRunner
    return VinaRunner


def get_quantum_runner():
    from .quantum_runner import QuantumRunner
    return QuantumRunner


# Export runner classes
VinaRunner = property(lambda self: get_vina_runner())
QuantumRunner = property(lambda self: get_quantum_runner())