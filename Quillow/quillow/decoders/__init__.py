# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quillow Decoders Module
=======================

Syndrome decoding algorithms for quantum error correction.

Available Decoders:
------------------
- MWPM (PyMatching): Minimum-weight perfect matching
- Union-Find: Fast approximate decoder
- Fusion Blossom: Ultra-fast exact decoder
- ML Decoder: Machine learning-based (GPU)
- GPU Decoder: CUDA-accelerated matching
"""

from .abstract_decoder import AbstractDecoder, DecoderResult
from .mwpm import MWPMDecoder, PyMatchingDecoder
from .union_find import UnionFindDecoder

# GPU decoder (optional, requires CUDA)
try:
    from .gpu_decoder import GPUDecoder

    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

__all__ = [
    "AbstractDecoder",
    "DecoderResult",
    "MWPMDecoder",
    "PyMatchingDecoder",
    "UnionFindDecoder",
    "get_decoder",
]

if GPU_AVAILABLE:
    __all__.append("GPUDecoder")


def get_decoder(decoder_type: str, **kwargs):
    """
    Factory function to create decoders.

    Args:
        decoder_type: Type of decoder
        **kwargs: Decoder-specific parameters

    Returns:
        Decoder instance
    """
    decoders = {
        "pymatching": PyMatchingDecoder,
        "mwpm": MWPMDecoder,
        "unionfind": UnionFindDecoder,
    }

    if GPU_AVAILABLE:
        decoders["gpu"] = GPUDecoder
        decoders["pymatching_gpu"] = lambda **kw: GPUDecoder(algorithm="pymatching", **kw)

    if decoder_type not in decoders:
        available = list(decoders.keys())
        raise ValueError(f"Unknown decoder: {decoder_type}. " f"Available: {available}")

    return decoders[decoder_type](**kwargs)
