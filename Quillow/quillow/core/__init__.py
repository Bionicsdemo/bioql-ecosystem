# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quillow Core Module
===================

Core quantum error correction functionality including:
- Surface code implementations (d=3, 5, 7)
- Syndrome extraction
- Pauli frame tracking
- Noise models
"""

from .noise_models import (
    AmplitudeDampingNoise,
    BitFlipNoise,
    CoherenceNoise,
    DepolarizingNoise,
    NoiseModel,
    PhaseFlipNoise,
)
from .pauli_frame import (
    LogicalOperator,
    PauliFrame,
    PauliFrameTracker,
)
from .surface_code import (
    RotatedSurfaceCode,
    SurfaceCode,
    SurfaceCodeSimulator,
)
from .syndrome import (
    DetectorErrorModel,
    SyndromeExtractor,
    SyndromeGraph,
)

__all__ = [
    # Surface codes
    "SurfaceCode",
    "SurfaceCodeSimulator",
    "RotatedSurfaceCode",
    # Syndrome extraction
    "SyndromeExtractor",
    "DetectorErrorModel",
    "SyndromeGraph",
    # Pauli frames
    "PauliFrame",
    "PauliFrameTracker",
    "LogicalOperator",
    # Noise models
    "NoiseModel",
    "DepolarizingNoise",
    "BitFlipNoise",
    "PhaseFlipNoise",
    "AmplitudeDampingNoise",
    "CoherenceNoise",
]

__version__ = "1.0.0"
