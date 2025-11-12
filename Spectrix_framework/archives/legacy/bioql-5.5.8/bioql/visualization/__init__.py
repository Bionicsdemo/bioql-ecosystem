"""
BioQL 5.0.0 - Phase 1B: Qualtran Visualization & Resource Estimation Module

This module provides comprehensive visualization and resource estimation capabilities
for quantum error correction (QEC) using Qualtran's resource counting framework.

Features:
    - QEC overhead visualization (surface code, Steane, Shor)
    - Resource estimation (physical qubits, magic states, circuit depth)
    - Error rate comparison plots
    - Cost analysis and trade-off visualization
    - Interactive HTML reports with graphs
    - Export to PNG/SVG formats

Classes:
    QECVisualizer: Main visualization class for QEC analysis
    ResourceEstimator: Qualtran-based resource estimation engine

Example:
    >>> from bioql.visualization import QECVisualizer, ResourceEstimator
    >>> from bioql.qec import SurfaceCodeQEC
    >>>
    >>> # Create visualizer
    >>> viz = QECVisualizer()
    >>>
    >>> # Estimate resources
    >>> estimator = ResourceEstimator()
    >>> resources = estimator.estimate_resources(circuit, qec_config)
    >>>
    >>> # Generate visualizations
    >>> fig = viz.plot_qubit_overhead([qec1, qec2, qec3])
    >>> viz.plot_error_rates(results)
    >>> report = viz.generate_qec_report(resources)
"""

from typing import List

from .qualtran_viz import QECVisualizer
from .resource_estimator import ResourceEstimator, ResourceEstimation

__version__ = "5.0.0"

__all__: List[str] = [
    "QECVisualizer",
    "ResourceEstimator",
    "ResourceEstimation",
]
