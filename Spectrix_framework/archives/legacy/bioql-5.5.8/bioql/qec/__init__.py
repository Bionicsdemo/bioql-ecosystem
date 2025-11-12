"""
BioQL 5.0.0 - Quantum Error Correction Module

This module provides quantum error correction (QEC) implementations for BioQL,
including surface codes, Steane codes, Shor codes, error mitigation techniques,
and comprehensive metrics tracking.

Available QEC Codes:
    - SurfaceCodeQEC: Topological surface codes with configurable distance
    - SteaneCodeQEC: 7-qubit Steane code for error correction
    - ShorCodeQEC: 9-qubit Shor code for error correction

Error Mitigation:
    - ErrorMitigation: Zero-noise extrapolation, PEC, readout calibration

Metrics:
    - QECMetrics: Comprehensive QEC performance tracking

Example:
    >>> from bioql.qec import SurfaceCodeQEC, ErrorMitigation, QECMetrics
    >>>
    >>> # Setup surface code QEC
    >>> qec = SurfaceCodeQEC(code_distance=5, error_rate=0.001)
    >>> overhead = qec.calculate_overhead()
    >>>
    >>> # Apply error mitigation
    >>> em = ErrorMitigation(techniques=['zne', 'readout'])
    >>> mitigated_result = em.apply_mitigation(raw_counts)
    >>>
    >>> # Track metrics
    >>> metrics = QECMetrics(
    ...     physical_qubits=100,
    ...     logical_qubits=10,
    ...     raw_error_rate=0.001,
    ...     corrected_error_rate=0.00001
    ... )
"""

from typing import List

from .surface_code import SurfaceCodeQEC
from .steane_code import SteaneCodeQEC
from .shor_code import ShorCodeQEC
from .error_mitigation import ErrorMitigation
from .metrics import QECMetrics

__version__ = "5.0.0"

__all__: List[str] = [
    "SurfaceCodeQEC",
    "SteaneCodeQEC",
    "ShorCodeQEC",
    "ErrorMitigation",
    "QECMetrics",
]
