#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Multi-Omics Integration Module - v6.0.0

Quantum-enhanced multi-omics data integration and analysis.

Author: BioQL Development Team / SpectrixRD
License: MIT
"""

try:
    from .integration import Factor, IntegratedResult, integrate_omics_layers

    HAVE_INTEGRATION = True
except ImportError:
    integrate_omics_layers = None
    IntegratedResult = None
    Factor = None
    HAVE_INTEGRATION = False

try:
    from .network_analysis import build_regulatory_network, identify_key_regulators

    HAVE_NETWORK = True
except ImportError:
    build_regulatory_network = None
    identify_key_regulators = None
    HAVE_NETWORK = False

try:
    from .quantum_integration import multiomics_integration_circuit

    HAVE_QUANTUM_MULTIOMICS = True
except ImportError:
    multiomics_integration_circuit = None
    HAVE_QUANTUM_MULTIOMICS = False

__all__ = [
    "integrate_omics_layers",
    "IntegratedResult",
    "Factor",
    "build_regulatory_network",
    "identify_key_regulators",
    "multiomics_integration_circuit",
    "HAVE_INTEGRATION",
    "HAVE_NETWORK",
    "HAVE_QUANTUM_MULTIOMICS",
]

__version__ = "6.0.0"
