# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quillow: Willow-Style Quantum Error Correction System
=====================================================

Advanced fault-tolerant quantum computing framework with surface codes,
MWPM decoding, GPU acceleration, and BioQL integration.

Quick Start:
-----------
>>> from quillow import SurfaceCodeSimulator
>>> sim = SurfaceCodeSimulator(distance=5, physical_error_rate=0.001)
>>> result = sim.run(shots=10000)
>>> print(f"Logical error rate: {result.logical_error_rate:.6f}")

BioQL Integration:
-----------------
>>> from quillow import BioQLOptimizer
>>> optimizer = BioQLOptimizer()
>>> result = optimizer.execute_with_qec(
...     "apply VQE to H2 molecule",
...     backend="ibm_torino",
...     shots=2048
... )
>>> print(f"Energy: {result['energy']:.6f} Hartree")

CLI Usage:
---------
$ quillow simulate --distance 5 --shots 10000
$ quillow protect-bioql --query "dock aspirin to COX-2" --backend ibm_torino
$ quillow benchmark threshold --distances 3,5,7
"""

__version__ = "1.0.0"
__author__ = "Quillow Development Team"
__license__ = "MIT"

# Backends
from .backends import (
    BioQLBackend,
    BioQLOptimizer,
    StimBackend,
    get_backend,
)

# Core QEC components
from .core import (
    CoherenceNoise,
    DepolarizingNoise,
    DetectorErrorModel,
    NoiseModel,
    PauliFrame,
    PauliFrameTracker,
    RotatedSurfaceCode,
    SurfaceCode,
    SurfaceCodeSimulator,
    SyndromeExtractor,
)

# Decoders
from .decoders import (
    MWPMDecoder,
    PyMatchingDecoder,
    UnionFindDecoder,
    get_decoder,
)

# Try to import GPU decoder
try:
    from .decoders import ModalGPUDecoder

    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

__all__ = [
    # Core
    "SurfaceCode",
    "SurfaceCodeSimulator",
    "RotatedSurfaceCode",
    "SyndromeExtractor",
    "DetectorErrorModel",
    "PauliFrame",
    "PauliFrameTracker",
    "NoiseModel",
    "DepolarizingNoise",
    "CoherenceNoise",
    # Decoders
    "PyMatchingDecoder",
    "MWPMDecoder",
    "UnionFindDecoder",
    "get_decoder",
    # Backends
    "StimBackend",
    "BioQLBackend",
    "BioQLOptimizer",
    "get_backend",
    # Constants
    "GPU_AVAILABLE",
    "__version__",
]

if GPU_AVAILABLE:
    __all__.append("ModalGPUDecoder")
