# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Hybrid Compiler and Auto-Optimizers
==========================================

Automatic translation: Classical → Quantum
Inspired by CUDA for GPUs, but for quantum computers.
"""

try:
    from .auto_optimizer import AutoOptimizer
    from .hybrid_compiler import HybridCompiler

    _available = True
except ImportError:
    _available = False
    HybridCompiler = None
    AutoOptimizer = None

__all__ = ["HybridCompiler", "AutoOptimizer"]
