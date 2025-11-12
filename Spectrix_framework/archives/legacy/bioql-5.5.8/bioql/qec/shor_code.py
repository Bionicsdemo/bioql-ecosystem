"""
Shor Code QEC implementation for BioQL 5.0.0.

This module implements the 9-qubit Shor code, the first quantum error correction
code ever developed. The Shor code can correct arbitrary single-qubit errors by
concatenating bit-flip and phase-flip codes.

Example:
    >>> from bioql.qec import ShorCodeQEC
    >>> qec = ShorCodeQEC(error_rate=0.001)
    >>> overhead = qec.calculate_overhead()
    >>> print(f"Overhead: {overhead}x")  # 9x
"""

from typing import Optional
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class ShorCodeQEC:
    """
    Shor Code Quantum Error Correction.

    The Shor code is a [[9,1,3]] code that encodes 1 logical qubit using
    9 physical qubits. It was the first quantum error correction code,
    developed by Peter Shor in 1995. The code works by concatenating a
    phase-flip code with a bit-flip code.

    Key properties:
    - Encodes 1 logical qubit in 9 physical qubits
    - Can correct any single-qubit error
    - Conceptually simple but not resource-optimal
    - Historical significance as the first QEC code

    Attributes:
        error_rate: Physical hardware error rate (probability of error per gate)

    Example:
        >>> qec = ShorCodeQEC(error_rate=0.001)
        >>> qec.validate()
        >>> physical = qec.get_physical_qubits(logical_qubits=10)
        >>> print(f"Need {physical} physical qubits for 10 logical qubits")
    """

    error_rate: float = 0.001

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()
        logger.info(f"Initialized Shor Code QEC: error_rate={self.error_rate}")

    @property
    def overhead(self) -> int:
        """
        Qubit overhead for Shor code.

        The Shor code always requires exactly 9 physical qubits per logical qubit.

        Returns:
            9 (constant overhead)
        """
        return 9

    def calculate_overhead(self) -> int:
        """
        Calculate the qubit overhead for the Shor code.

        Returns:
            9 physical qubits per logical qubit (constant)

        Example:
            >>> qec = ShorCodeQEC()
            >>> overhead = qec.calculate_overhead()
            >>> print(f"Overhead: {overhead}x")
        """
        return self.overhead

    def validate(self) -> bool:
        """
        Validate Shor code parameters.

        Checks:
        - Error rate is in valid range (0 < error_rate < 0.1)

        Returns:
            True if all parameters are valid

        Raises:
            ValueError: If error rate is invalid

        Example:
            >>> qec = ShorCodeQEC(error_rate=0.001)
            >>> qec.validate()  # Returns True
            >>> qec = ShorCodeQEC(error_rate=0.5)
            ValueError: error_rate must be between 0 and 0.1
        """
        if not (0 < self.error_rate < 0.1):
            raise ValueError(
                f"error_rate must be between 0 and 0.1, got {self.error_rate}"
            )

        return True

    def get_physical_qubits(self, logical_qubits: int) -> int:
        """
        Calculate total physical qubits needed for a given number of logical qubits.

        Args:
            logical_qubits: Number of logical qubits to encode

        Returns:
            Total number of physical qubits required (logical_qubits * 9)

        Raises:
            ValueError: If logical_qubits is not positive

        Example:
            >>> qec = ShorCodeQEC()
            >>> physical = qec.get_physical_qubits(logical_qubits=10)
            >>> print(f"Need {physical} physical qubits")  # 90
        """
        if logical_qubits < 1:
            raise ValueError(f"logical_qubits must be positive, got {logical_qubits}")

        return logical_qubits * self.overhead

    def estimate_logical_error_rate(self) -> float:
        """
        Estimate the logical error rate after error correction.

        For the Shor code (distance d=3), the logical error rate is
        approximately p_L ≈ 42 * p^2, where p is the physical error rate.
        This assumes the physical error rate is below the threshold (~2.7e-3).

        Returns:
            Estimated logical error rate

        Example:
            >>> qec = ShorCodeQEC(error_rate=0.001)
            >>> logical_error = qec.estimate_logical_error_rate()
            >>> print(f"Logical error rate: {logical_error:.2e}")
        """
        p = self.error_rate
        threshold = 2.7e-3  # Approximate threshold for Shor code

        if p >= threshold:
            logger.warning(
                f"Physical error rate {p} is at or above threshold {threshold}. "
                "Error correction may not be effective."
            )
            return p

        # For distance-3 codes, logical error rate ≈ 42 * p^2
        # This is an approximation based on error correction theory
        logical_error_rate = 42 * (p ** 2)

        return min(logical_error_rate, p)  # Can't be worse than no correction

    def get_stabilizers(self) -> dict:
        """
        Get the stabilizer generators for the Shor code.

        The Shor code has 8 stabilizer generators that check for bit-flip
        and phase-flip errors across the 9 qubits.

        Returns:
            Dictionary containing stabilizer generators

        Example:
            >>> qec = ShorCodeQEC()
            >>> stabilizers = qec.get_stabilizers()
            >>> print(len(stabilizers['generators']))  # 8
        """
        # Shor code stabilizers: 6 for bit-flips, 2 for phase-flips
        return {
            'generators': [
                # Bit-flip stabilizers (within each block of 3)
                'ZZIIIIIII',  # Check qubits 0,1
                'IZZIIIIII',  # Check qubits 1,2
                'IIIZZIII',   # Check qubits 3,4
                'IIIIZZII',   # Check qubits 4,5
                'IIIIIIZZI',  # Check qubits 6,7
                'IIIIIIIZZ',  # Check qubits 7,8
                # Phase-flip stabilizers (across blocks)
                'XXXXXXIII',  # Check blocks 0,1
                'IIIXXXXXX',  # Check blocks 1,2
            ],
            'description': 'Concatenated bit-flip and phase-flip code'
        }

    def get_logical_operators(self) -> dict:
        """
        Get the logical X and Z operators for the Shor code.

        Returns:
            Dictionary containing logical X and Z operators

        Example:
            >>> qec = ShorCodeQEC()
            >>> operators = qec.get_logical_operators()
            >>> print(operators['X'])
        """
        return {
            'X': 'XXXXXXXXX',  # Logical X (apply X to all 9 qubits)
            'Z': 'ZZZIIIII',   # Logical Z (apply Z to first block)
        }

    def get_encoding_circuit_depth(self) -> int:
        """
        Get the depth of the encoding circuit.

        The Shor code encoding circuit has depth proportional to the
        concatenation structure.

        Returns:
            Circuit depth for encoding (approximately 8 layers)

        Example:
            >>> qec = ShorCodeQEC()
            >>> depth = qec.get_encoding_circuit_depth()
            >>> print(f"Encoding depth: {depth}")
        """
        return 8

    def get_syndrome_circuit_depth(self) -> int:
        """
        Get the depth of the syndrome measurement circuit.

        Returns:
            Circuit depth for syndrome measurement (approximately 5 layers)

        Example:
            >>> qec = ShorCodeQEC()
            >>> depth = qec.get_syndrome_circuit_depth()
            >>> print(f"Syndrome depth: {depth}")
        """
        return 5

    def get_code_structure(self) -> dict:
        """
        Get information about the Shor code's concatenated structure.

        Returns:
            Dictionary describing the code structure

        Example:
            >>> qec = ShorCodeQEC()
            >>> structure = qec.get_code_structure()
            >>> print(structure['description'])
        """
        return {
            'description': 'Concatenation of phase-flip and bit-flip codes',
            'outer_code': '3-qubit phase-flip code',
            'inner_code': '3-qubit bit-flip code',
            'blocks': 3,
            'qubits_per_block': 3,
            'total_qubits': 9,
            'correctable_errors': 'Any single-qubit error (X, Y, or Z)',
        }

    def __repr__(self) -> str:
        """String representation of the Shor code configuration."""
        return (
            f"ShorCodeQEC(error_rate={self.error_rate}, "
            f"overhead={self.overhead}x)"
        )

    def to_dict(self) -> dict:
        """
        Convert Shor code configuration to dictionary.

        Returns:
            Dictionary representation of the configuration

        Example:
            >>> qec = ShorCodeQEC(error_rate=0.001)
            >>> config = qec.to_dict()
            >>> print(config)
        """
        return {
            'code_type': 'shor',
            'code_parameters': [9, 1, 3],  # [[n, k, d]] notation
            'error_rate': self.error_rate,
            'overhead': self.overhead,
            'estimated_logical_error_rate': self.estimate_logical_error_rate(),
            'encoding_circuit_depth': self.get_encoding_circuit_depth(),
            'syndrome_circuit_depth': self.get_syndrome_circuit_depth(),
            'code_structure': self.get_code_structure(),
        }
