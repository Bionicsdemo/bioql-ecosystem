"""
BioQL Hybrid Compiler and Auto-Optimizers
==========================================

Automatic translation: Classical → Quantum
Inspired by CUDA for GPUs, but for quantum computers.
"""

try:
    from .hybrid_compiler import HybridCompiler
    from .auto_optimizer import AutoOptimizer
    _available = True
except ImportError:
    _available = False
    HybridCompiler = None
    AutoOptimizer = None

__all__ = ["HybridCompiler", "AutoOptimizer"]
