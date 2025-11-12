"""
BioQL Benchmarks Package

Provides standardized benchmarks for quantum chemistry calculations
against exact literature values.

Features:
- Chemistry benchmarks (H2, LiH, H2O, BeH2, N2)
- Backend comparison tools
- Statistical analysis of accuracy
- Performance profiling

Example:
    >>> from bioql.benchmarks import quick_benchmark, ChemistryBenchmark
    >>> result = quick_benchmark("H2", backend="simulator")
    >>> print(f"Error: {result.relative_error:.2f}%")
"""

from .chemistry import (
    LITERATURE_DATA,
    BenchmarkResult,
    BenchmarkSuite,
    ChemistryBenchmark,
    quick_benchmark,
)

__all__ = [
    "LITERATURE_DATA",
    "BenchmarkResult",
    "BenchmarkSuite",
    "ChemistryBenchmark",
    "quick_benchmark",
]

__version__ = "3.1.2"
