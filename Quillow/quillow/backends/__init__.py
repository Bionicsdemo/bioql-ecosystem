# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quillow Backends Module
=======================

Backend connectors for quantum execution.

Available Backends:
------------------
- Stim: Fast stabilizer circuit simulator
- BioQL: Integration with BioQL quantum chemistry
- Modal: Cloud GPU execution
- Qiskit: IBM Quantum hardware/simulators
"""

from .abstract_backend import AbstractBackend, BackendResult
from .stim_backend import StimBackend

# Optional backends
try:
    from .bioql_backend import BioQLBackend, BioQLOptimizer

    BIOQL_AVAILABLE = True
except ImportError:
    BIOQL_AVAILABLE = False

try:
    from .modal_backend import ModalBackend

    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False

__all__ = [
    "AbstractBackend",
    "BackendResult",
    "StimBackend",
    "get_backend",
]

if BIOQL_AVAILABLE:
    __all__.extend(["BioQLBackend", "BioQLOptimizer"])

if MODAL_AVAILABLE:
    __all__.append("ModalBackend")


def get_backend(backend_type: str, **kwargs):
    """
    Factory function to create backends.

    Args:
        backend_type: Type of backend
        **kwargs: Backend-specific parameters

    Returns:
        Backend instance
    """
    backends = {
        "stim": StimBackend,
    }

    if BIOQL_AVAILABLE:
        backends["bioql"] = BioQLBackend

    if MODAL_AVAILABLE:
        backends["modal"] = ModalBackend

    if backend_type not in backends:
        available = list(backends.keys())
        raise ValueError(f"Unknown backend: {backend_type}. " f"Available: {available}")

    return backends[backend_type](**kwargs)
