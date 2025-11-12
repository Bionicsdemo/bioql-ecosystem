# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Core Module
Quantum Pharmaceutical Optimization System
"""

from .config import QPHAROSConfig
from .quantum_backend import QuantumBackend

__version__ = "1.0.0"
__all__ = ["QPHAROSConfig", "QuantumBackend"]
