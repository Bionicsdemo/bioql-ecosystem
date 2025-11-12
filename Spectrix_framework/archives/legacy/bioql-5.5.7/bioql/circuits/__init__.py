"""
BioQL Circuit Library

A comprehensive library of quantum circuit templates for bioinformatics
and drug discovery applications.

This module provides:
- Abstract base classes for circuit templates
- A searchable catalog of pre-built circuits
- Algorithm implementations (VQE, QAOA, Grover)
- Drug discovery specific circuits
- Reusable ansatz templates
- Circuit composition utilities

Quick Start:
    >>> from bioql.circuits import get_catalog, CircuitCategory
    >>>
    >>> # Get the global circuit catalog
    >>> catalog = get_catalog()
    >>>
    >>> # Search for circuits
    >>> circuits = catalog.search("drug discovery")
    >>>
    >>> # Get circuits by category
    >>> drug_circuits = catalog.get_by_category(CircuitCategory.DRUG_DISCOVERY)
    >>>
    >>> # Get recommendations
    >>> from bioql.circuits import ResourceConstraints
    >>> constraints = ResourceConstraints(max_qubits=20, max_depth=100)
    >>> recommendations = catalog.recommend(
    ...     use_case="molecular docking",
    ...     constraints=constraints
    ... )

Circuit Categories:
    - ALGORITHM: General quantum algorithms (VQE, QAOA, Grover)
    - DRUG_DISCOVERY: Drug discovery specific circuits
    - CHEMISTRY: Quantum chemistry circuits
    - OPTIMIZATION: Optimization algorithms
    - SIMULATION: Quantum simulation circuits
    - UTILITY: Utility circuits and building blocks
"""

# Base classes and types
from .base import (
    CircuitTemplate,
    CircuitCategory,
    ComplexityRating,
    ParameterSpec,
    ResourceEstimate,
    CircuitMetadata
)

# Catalog
from .catalog import (
    CircuitCatalog,
    ResourceConstraints,
    SearchFilters,
    get_catalog,
    register_template,
    search_templates
)

# Algorithm circuits
from .algorithms import (
    VQECircuit,
    QAOACircuit,
    GroverCircuit
)

# Drug discovery circuits
from .drug_discovery import (
    MolecularDockingCircuit,
    ProteinFoldingCircuit,
    BindingAffinityCircuit
)

# Template circuits
from .templates import (
    HardwareEfficientAnsatz,
    UCCSDAnsatz
)

# Composition utilities
from .composition import (
    CircuitComposer,  # Legacy template composer
    CircuitPipeline,
    QiskitCircuitComposer,
    CircuitStitcher,
    ModularCircuitBuilder,
    CompositionStrategy,
    StitchingStrategy,
    WiringMode
)


# Register all circuits in the global catalog
def _register_default_circuits():
    """Register all default circuit templates."""
    catalog = get_catalog()

    # Algorithm circuits
    catalog.register(VQECircuit())
    catalog.register(QAOACircuit())
    catalog.register(GroverCircuit())

    # Drug discovery circuits
    catalog.register(MolecularDockingCircuit())
    catalog.register(ProteinFoldingCircuit())
    catalog.register(BindingAffinityCircuit())

    # Template circuits
    catalog.register(HardwareEfficientAnsatz())
    catalog.register(UCCSDAnsatz())


# Auto-register on import
_register_default_circuits()


# Public API
__all__ = [
    # Base classes
    "CircuitTemplate",
    "CircuitCategory",
    "ComplexityRating",
    "ParameterSpec",
    "ResourceEstimate",
    "CircuitMetadata",

    # Catalog
    "CircuitCatalog",
    "ResourceConstraints",
    "SearchFilters",
    "get_catalog",
    "register_template",
    "search_templates",

    # Algorithm circuits
    "VQECircuit",
    "QAOACircuit",
    "GroverCircuit",

    # Drug discovery circuits
    "MolecularDockingCircuit",
    "ProteinFoldingCircuit",
    "BindingAffinityCircuit",

    # Template circuits
    "HardwareEfficientAnsatz",
    "UCCSDAnsatz",

    # Composition (Legacy)
    "CircuitComposer",
    "CircuitPipeline",

    # Composition (New Tools)
    "QiskitCircuitComposer",
    "CircuitStitcher",
    "ModularCircuitBuilder",
    "CompositionStrategy",
    "StitchingStrategy",
    "WiringMode",
]


__version__ = "1.0.0"
