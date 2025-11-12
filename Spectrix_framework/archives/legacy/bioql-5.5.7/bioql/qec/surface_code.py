"""
Surface Code QEC implementation for BioQL 5.0.0.

This module implements topological surface codes with configurable code distance
for quantum error correction. Surface codes are among the most promising QEC
codes for near-term quantum computers due to their high threshold error rates
and local connectivity requirements.

Example:
    >>> from bioql.qec import SurfaceCodeQEC
    >>> qec = SurfaceCodeQEC(code_distance=5, error_rate=0.001)
    >>> overhead = qec.calculate_overhead()
    >>> physical_qubits = qec.get_physical_qubits(logical_qubits=10)
    >>> print(f"Physical qubits needed: {physical_qubits}")
"""

from typing import Literal, Optional
from dataclasses import dataclass
import math

from ..logger import get_logger

logger = get_logger(__name__)


DecoderType = Literal['mwpm', 'union_find']


@dataclass
class SurfaceCodeQEC:
    """
    Surface Code Quantum Error Correction.

    Surface codes are topological codes that encode logical qubits using a 2D
    lattice of physical qubits. They offer high error thresholds (~1%) and
    require only nearest-neighbor interactions.

    Attributes:
        code_distance: Distance of the surface code (d=3,5,7,9). Higher distance
            provides better error correction but requires more qubits.
        error_rate: Physical hardware error rate (probability of error per gate)
        correction_rounds: Number of syndrome measurement rounds per logical operation
        decoder: Decoding algorithm ('mwpm' = Minimum Weight Perfect Matching,
            'union_find' = Union-Find decoder)

    Example:
        >>> qec = SurfaceCodeQEC(code_distance=5, error_rate=0.001)
        >>> qec.validate()
        >>> print(f"Overhead: {qec.calculate_overhead()}x")
        >>> print(f"Ancilla qubits: {qec.ancilla_qubits}")
    """

    code_distance: int = 5
    error_rate: float = 0.001
    correction_rounds: int = 1
    decoder: DecoderType = 'mwpm'

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()
        logger.info(
            f"Initialized Surface Code QEC: d={self.code_distance}, "
            f"error_rate={self.error_rate}, decoder={self.decoder}"
        )

    @property
    def ancilla_qubits(self) -> int:
        """
        Calculate number of ancilla qubits needed for syndrome measurement.

        For a distance-d surface code, we need approximately (d-1)^2 ancilla
        qubits for syndrome extraction (measuring stabilizers).

        Returns:
            Number of ancilla qubits required
        """
        d = self.code_distance
        return (d - 1) ** 2

    @property
    def logical_overhead(self) -> int:
        """
        Calculate total qubit overhead per logical qubit.

        For a distance-d surface code, we need (2d-1)^2 physical qubits
        to encode one logical qubit (including data and ancilla qubits).

        Returns:
            Number of physical qubits per logical qubit
        """
        d = self.code_distance
        return (2 * d - 1) ** 2

    def calculate_overhead(self) -> int:
        """
        Calculate the total qubit overhead for the surface code.

        This is the primary method for determining resource requirements.
        The overhead includes both data qubits and ancilla qubits needed
        for syndrome measurement.

        Returns:
            Total physical qubits needed per logical qubit

        Example:
            >>> qec = SurfaceCodeQEC(code_distance=3)
            >>> overhead = qec.calculate_overhead()
            >>> print(f"Need {overhead} physical qubits per logical qubit")
        """
        return self.logical_overhead

    def validate(self) -> bool:
        """
        Validate surface code parameters.

        Checks:
        - Code distance is valid (3, 5, 7, or 9)
        - Error rate is in valid range (0 < error_rate < 0.1)
        - Correction rounds is positive
        - Decoder type is supported

        Returns:
            True if all parameters are valid

        Raises:
            ValueError: If any parameter is invalid

        Example:
            >>> qec = SurfaceCodeQEC(code_distance=5, error_rate=0.001)
            >>> qec.validate()  # Returns True
            >>> qec = SurfaceCodeQEC(code_distance=4, error_rate=0.001)
            ValueError: code_distance must be one of [3, 5, 7, 9]
        """
        # Validate code distance
        valid_distances = [3, 5, 7, 9]
        if self.code_distance not in valid_distances:
            raise ValueError(
                f"code_distance must be one of {valid_distances}, "
                f"got {self.code_distance}"
            )

        # Validate error rate
        if not (0 < self.error_rate < 0.1):
            raise ValueError(
                f"error_rate must be between 0 and 0.1, got {self.error_rate}"
            )

        # Validate correction rounds
        if self.correction_rounds < 1:
            raise ValueError(
                f"correction_rounds must be positive, got {self.correction_rounds}"
            )

        # Validate decoder
        valid_decoders: list[DecoderType] = ['mwpm', 'union_find']
        if self.decoder not in valid_decoders:
            raise ValueError(
                f"decoder must be one of {valid_decoders}, got {self.decoder}"
            )

        return True

    def get_physical_qubits(self, logical_qubits: int) -> int:
        """
        Calculate total physical qubits needed for a given number of logical qubits.

        Args:
            logical_qubits: Number of logical qubits to encode

        Returns:
            Total number of physical qubits required

        Example:
            >>> qec = SurfaceCodeQEC(code_distance=5)
            >>> physical = qec.get_physical_qubits(logical_qubits=10)
            >>> print(f"Need {physical} physical qubits for 10 logical qubits")
        """
        if logical_qubits < 1:
            raise ValueError(f"logical_qubits must be positive, got {logical_qubits}")

        overhead = self.calculate_overhead()
        return logical_qubits * overhead

    def estimate_logical_error_rate(self) -> float:
        """
        Estimate the logical error rate after error correction.

        Uses the formula: p_L ≈ (p/p_th)^((d+1)/2) where:
        - p is the physical error rate
        - p_th is the threshold error rate (~0.01 for surface codes)
        - d is the code distance

        Returns:
            Estimated logical error rate

        Example:
            >>> qec = SurfaceCodeQEC(code_distance=5, error_rate=0.001)
            >>> logical_error = qec.estimate_logical_error_rate()
            >>> print(f"Logical error rate: {logical_error:.2e}")
        """
        p = self.error_rate
        p_threshold = 0.01  # Surface code threshold is approximately 1%
        d = self.code_distance

        # If physical error rate is above threshold, no improvement
        if p >= p_threshold:
            logger.warning(
                f"Physical error rate {p} is at or above threshold {p_threshold}. "
                "Error correction may not be effective."
            )
            return p

        # Logical error rate scales as (p/p_th)^((d+1)/2)
        exponent = (d + 1) / 2
        logical_error_rate = (p / p_threshold) ** exponent

        return logical_error_rate

    def get_syndrome_circuit_depth(self) -> int:
        """
        Calculate the circuit depth for syndrome measurement.

        The syndrome extraction circuit depth depends on the code distance
        and the decoder architecture.

        Returns:
            Circuit depth for one syndrome measurement round

        Example:
            >>> qec = SurfaceCodeQEC(code_distance=5)
            >>> depth = qec.get_syndrome_circuit_depth()
            >>> print(f"Syndrome circuit depth: {depth}")
        """
        # Surface code syndrome extraction requires O(d) depth
        # Typically 4-6 layers of operations
        base_depth = 4
        distance_factor = self.code_distance // 2
        return base_depth + distance_factor

    def __repr__(self) -> str:
        """String representation of the surface code configuration."""
        return (
            f"SurfaceCodeQEC(code_distance={self.code_distance}, "
            f"error_rate={self.error_rate}, "
            f"correction_rounds={self.correction_rounds}, "
            f"decoder='{self.decoder}', "
            f"overhead={self.logical_overhead}x)"
        )

    def to_dict(self) -> dict:
        """
        Convert surface code configuration to dictionary.

        Returns:
            Dictionary representation of the configuration

        Example:
            >>> qec = SurfaceCodeQEC(code_distance=5)
            >>> config = qec.to_dict()
            >>> print(config)
        """
        return {
            'code_distance': self.code_distance,
            'error_rate': self.error_rate,
            'correction_rounds': self.correction_rounds,
            'decoder': self.decoder,
            'ancilla_qubits': self.ancilla_qubits,
            'logical_overhead': self.logical_overhead,
            'estimated_logical_error_rate': self.estimate_logical_error_rate(),
            'syndrome_circuit_depth': self.get_syndrome_circuit_depth(),
        }
