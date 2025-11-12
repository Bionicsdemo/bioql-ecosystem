# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS - Quantum Pharmaceutical Optimization System
Multi-layer hybrid quantum-classical architecture for drug discovery

Version: 1.0.0
Author: BioQL Team
License: MIT
"""

__version__ = "1.0.0"
__author__ = "BioQL Team"

from .core.config import QPHAROSConfig
from .core.pipeline import QuantumDrugDesignPipeline
from .core.quantum_backend import QuantumBackend
from .layers.layer1_encoding import QuantumMolecularEncoder
from .layers.layer2_binding import QuantumBindingPredictor
from .layers.layer3_admet import QuantumADMETOptimizer
from .layers.layer4_generation import QuantumMolecularGAN
from .layers.layer5_dynamics import QuantumMolecularDynamics

__all__ = [
    # Core
    "QPHAROSConfig",
    "QuantumBackend",
    "QuantumDrugDesignPipeline",
    # Layers
    "QuantumMolecularEncoder",
    "QuantumBindingPredictor",
    "QuantumADMETOptimizer",
    "QuantumMolecularGAN",
    "QuantumMolecularDynamics",
]
