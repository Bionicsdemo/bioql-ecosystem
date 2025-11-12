"""
QEC Metrics implementation for BioQL 5.0.0.

This module provides comprehensive metrics tracking for quantum error correction
performance, including physical/logical qubit counts, error rates, fidelity,
and overhead calculations.

Example:
    >>> from bioql.qec import QECMetrics
    >>> metrics = QECMetrics(
    ...     physical_qubits=100,
    ...     logical_qubits=10,
    ...     raw_error_rate=0.001,
    ...     corrected_error_rate=0.00001
    ... )
    >>> print(metrics)
"""

from typing import Optional
from dataclasses import dataclass, field
import math

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class QECMetrics:
    """
    Quantum Error Correction Performance Metrics.

    Tracks comprehensive metrics for QEC performance including qubit counts,
    error rates, fidelity, success rates, and resource overhead.

    Attributes:
        physical_qubits: Total number of physical qubits used
        logical_qubits: Number of logical qubits encoded
        raw_error_rate: Physical error rate before correction
        corrected_error_rate: Logical error rate after correction
        fidelity: Circuit fidelity (0-1, where 1 is perfect)
        success_rate: Probability of successful error correction (0-1)
        overhead_ratio: Ratio of physical to logical qubits

    Example:
        >>> metrics = QECMetrics(
        ...     physical_qubits=100,
        ...     logical_qubits=10,
        ...     raw_error_rate=0.001,
        ...     corrected_error_rate=0.00001,
        ...     fidelity=0.99,
        ...     success_rate=0.95
        ... )
        >>> print(metrics)
        >>> print(f"Error suppression: {metrics.error_suppression_factor:.1f}x")
    """

    physical_qubits: int
    logical_qubits: int
    raw_error_rate: float
    corrected_error_rate: float
    fidelity: float = 0.99
    success_rate: float = 0.95
    overhead_ratio: Optional[float] = None

    def __post_init__(self):
        """Calculate derived metrics and validate parameters."""
        # Calculate overhead ratio if not provided
        if self.overhead_ratio is None:
            if self.logical_qubits > 0:
                self.overhead_ratio = self.physical_qubits / self.logical_qubits
            else:
                self.overhead_ratio = 0.0

        # Validate
        self.validate()

        logger.debug(
            f"QEC Metrics initialized: {self.physical_qubits} physical qubits, "
            f"{self.logical_qubits} logical qubits, "
            f"overhead={self.overhead_ratio:.1f}x"
        )

    def validate(self) -> bool:
        """
        Validate all metric parameters.

        Checks:
        - Qubit counts are positive
        - Error rates are in valid range (0 < rate < 1)
        - Fidelity is in valid range (0 < fidelity <= 1)
        - Success rate is in valid range (0 < rate <= 1)
        - Physical qubits >= logical qubits

        Returns:
            True if all parameters are valid

        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate qubit counts
        if self.physical_qubits < 1:
            raise ValueError(
                f"physical_qubits must be positive, got {self.physical_qubits}"
            )

        if self.logical_qubits < 1:
            raise ValueError(
                f"logical_qubits must be positive, got {self.logical_qubits}"
            )

        if self.physical_qubits < self.logical_qubits:
            raise ValueError(
                f"physical_qubits ({self.physical_qubits}) must be >= "
                f"logical_qubits ({self.logical_qubits})"
            )

        # Validate error rates
        if not (0 < self.raw_error_rate < 1):
            raise ValueError(
                f"raw_error_rate must be between 0 and 1, got {self.raw_error_rate}"
            )

        if not (0 < self.corrected_error_rate < 1):
            raise ValueError(
                f"corrected_error_rate must be between 0 and 1, "
                f"got {self.corrected_error_rate}"
            )

        # Validate fidelity
        if not (0 < self.fidelity <= 1):
            raise ValueError(
                f"fidelity must be between 0 and 1, got {self.fidelity}"
            )

        # Validate success rate
        if not (0 < self.success_rate <= 1):
            raise ValueError(
                f"success_rate must be between 0 and 1, got {self.success_rate}"
            )

        return True

    @property
    def error_suppression_factor(self) -> float:
        """
        Calculate error suppression factor.

        The factor by which error correction reduces the error rate.

        Returns:
            Ratio of raw to corrected error rate

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> print(f"Error suppression: {metrics.error_suppression_factor}x")
            Error suppression: 100.0x
        """
        if self.corrected_error_rate == 0:
            return float('inf')
        return self.raw_error_rate / self.corrected_error_rate

    @property
    def effective_fidelity(self) -> float:
        """
        Calculate effective fidelity including error correction success rate.

        Returns:
            Effective fidelity accounting for correction failures

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001,
            ...     fidelity=0.99, success_rate=0.95
            ... )
            >>> print(f"Effective fidelity: {metrics.effective_fidelity:.4f}")
        """
        return self.fidelity * self.success_rate

    @property
    def qubit_efficiency(self) -> float:
        """
        Calculate qubit efficiency (logical/physical ratio).

        Returns:
            Fraction of physical qubits that are logical (0-1)

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> print(f"Efficiency: {metrics.qubit_efficiency:.1%}")
            Efficiency: 10.0%
        """
        if self.physical_qubits == 0:
            return 0.0
        return self.logical_qubits / self.physical_qubits

    @property
    def code_distance(self) -> int:
        """
        Estimate code distance from overhead ratio.

        For surface codes: overhead ≈ (2d-1)^2, so d ≈ (sqrt(overhead) + 1) / 2

        Returns:
            Estimated code distance

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=81, logical_qubits=1,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> print(f"Estimated code distance: {metrics.code_distance}")
            Estimated code distance: 5
        """
        if self.overhead_ratio is None or self.overhead_ratio <= 0:
            return 1

        # Estimate from surface code formula: overhead = (2d-1)^2
        d = (math.sqrt(self.overhead_ratio) + 1) / 2
        return max(1, int(round(d)))

    def calculate_logical_error_probability(self, circuit_depth: int) -> float:
        """
        Calculate logical error probability for a circuit.

        Args:
            circuit_depth: Depth of the quantum circuit

        Returns:
            Probability of logical error

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> prob = metrics.calculate_logical_error_probability(circuit_depth=100)
            >>> print(f"Logical error probability: {prob:.2%}")
        """
        # Simplified model: P_error ≈ 1 - (1 - p_L)^depth
        p_L = self.corrected_error_rate
        prob_no_error = (1 - p_L) ** circuit_depth
        return 1 - prob_no_error

    def estimate_runtime_overhead(self, base_runtime: float) -> float:
        """
        Estimate total runtime including QEC overhead.

        Args:
            base_runtime: Runtime without QEC (in arbitrary units)

        Returns:
            Estimated runtime with QEC

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> total_time = metrics.estimate_runtime_overhead(base_runtime=1.0)
            >>> print(f"Runtime overhead: {total_time:.1f}x")
        """
        # Runtime overhead includes:
        # 1. More qubits to control (overhead_ratio)
        # 2. Syndrome measurement rounds (~code_distance)
        # 3. Classical processing (~log(overhead))

        qubit_overhead = self.overhead_ratio or 1.0
        syndrome_overhead = self.code_distance
        processing_overhead = math.log2(qubit_overhead + 1)

        total_overhead = qubit_overhead * syndrome_overhead * (1 + 0.1 * processing_overhead)

        return base_runtime * total_overhead

    def to_dict(self) -> dict:
        """
        Convert metrics to dictionary representation.

        Returns:
            Dictionary containing all metrics and derived values

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> data = metrics.to_dict()
            >>> print(data.keys())
        """
        return {
            'physical_qubits': self.physical_qubits,
            'logical_qubits': self.logical_qubits,
            'raw_error_rate': self.raw_error_rate,
            'corrected_error_rate': self.corrected_error_rate,
            'fidelity': self.fidelity,
            'success_rate': self.success_rate,
            'overhead_ratio': self.overhead_ratio,
            'error_suppression_factor': self.error_suppression_factor,
            'effective_fidelity': self.effective_fidelity,
            'qubit_efficiency': self.qubit_efficiency,
            'estimated_code_distance': self.code_distance,
        }

    def __repr__(self) -> str:
        """
        Detailed string representation of QEC metrics.

        Returns:
            Formatted string with all key metrics

        Example:
            >>> metrics = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> print(metrics)
        """
        return (
            f"QECMetrics(\n"
            f"  Physical qubits: {self.physical_qubits}\n"
            f"  Logical qubits: {self.logical_qubits}\n"
            f"  Overhead: {self.overhead_ratio:.1f}x\n"
            f"  Raw error rate: {self.raw_error_rate:.2e}\n"
            f"  Corrected error rate: {self.corrected_error_rate:.2e}\n"
            f"  Error suppression: {self.error_suppression_factor:.1f}x\n"
            f"  Fidelity: {self.fidelity:.4f}\n"
            f"  Success rate: {self.success_rate:.4f}\n"
            f"  Effective fidelity: {self.effective_fidelity:.4f}\n"
            f"  Qubit efficiency: {self.qubit_efficiency:.1%}\n"
            f"  Estimated code distance: {self.code_distance}\n"
            f")"
        )

    def __str__(self) -> str:
        """
        Concise string representation.

        Returns:
            Brief summary of key metrics
        """
        return (
            f"QEC: {self.physical_qubits}→{self.logical_qubits} qubits "
            f"({self.overhead_ratio:.1f}x), "
            f"error: {self.raw_error_rate:.2e}→{self.corrected_error_rate:.2e} "
            f"({self.error_suppression_factor:.1f}x suppression)"
        )

    def compare(self, other: 'QECMetrics') -> dict:
        """
        Compare this metrics with another QEC configuration.

        Args:
            other: Another QECMetrics instance to compare with

        Returns:
            Dictionary containing comparison results

        Example:
            >>> metrics1 = QECMetrics(
            ...     physical_qubits=100, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.00001
            ... )
            >>> metrics2 = QECMetrics(
            ...     physical_qubits=200, logical_qubits=10,
            ...     raw_error_rate=0.001, corrected_error_rate=0.000001
            ... )
            >>> comparison = metrics1.compare(metrics2)
            >>> print(comparison['better_error_suppression'])
        """
        return {
            'overhead_diff': self.overhead_ratio - other.overhead_ratio,
            'error_suppression_ratio': (
                self.error_suppression_factor / other.error_suppression_factor
            ),
            'fidelity_diff': self.effective_fidelity - other.effective_fidelity,
            'efficiency_diff': self.qubit_efficiency - other.qubit_efficiency,
            'better_error_suppression': (
                self.error_suppression_factor > other.error_suppression_factor
            ),
            'better_fidelity': self.effective_fidelity > other.effective_fidelity,
            'more_efficient': self.qubit_efficiency > other.qubit_efficiency,
        }
