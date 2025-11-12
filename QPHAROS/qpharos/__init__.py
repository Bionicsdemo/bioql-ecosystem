# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS - Quantum Pharmaceutical Optimization System
5-Layer Quantum Drug Discovery Platform

QPHAROS offers 4 usage schemas for different user types:

Schema 1 - Simple API (Beginners):
    from qpharos.simple import quick_dock, is_drug_like, test_molecule
    affinity = quick_dock('CCO', '6B3J')

Schema 2 - Functional API (Normal Users):
    from qpharos import dock, predict_admet, design_drug
    result = dock(ligand='CCO', receptor='6B3J', backend='ibm_torino')

Schema 3 - OOP API (Programmers):
    from qpharos import QPHAROSAnalyzer, QPHAROSConfig
    analyzer = QPHAROSAnalyzer(config)
    result = analyzer.dock('CCO', '6B3J')

Schema 4 - Layer-by-Layer (Quantum Experts):
    from qpharos.layers import QuantumFeatureEncoder, QuantumScoringFunction
    encoder = QuantumFeatureEncoder(backend)
    encoded = encoder.encode_molecule('CCO')
"""

__version__ = "1.1.0"
__author__ = "Heinz Jungbluth"
__email__ = "heinz@bionics-ai.biz"

# Schema 4: Layer-by-Layer API
# Schema 1: Simple API (convenience)
from . import layers, simple

# Schema 3: OOP API
from .analyzer import QPHAROSAnalyzer

# Schema 2: Functional API (default/main API)
from .api import design_drug, dock, optimize_lead, predict_admet, screen_library
from .core import quantum_backend
from .core.config import QPHAROSConfig

# Data Models
from .models import ADMETResult, DockingResult, DrugDesignResult, GeneratedMolecule

__all__ = [
    # Main API (Schema 2)
    "dock",
    "design_drug",
    "predict_admet",
    "screen_library",
    "optimize_lead",
    # OOP API (Schema 3)
    "QPHAROSAnalyzer",
    "QPHAROSConfig",
    # Models
    "DockingResult",
    "DrugDesignResult",
    "ADMETResult",
    "GeneratedMolecule",
    # Modules
    "simple",  # Schema 1
    "layers",  # Schema 4
    "quantum_backend",
    # Meta
    "__version__",
]
