"""
Steane Code QEC implementation for BioQL 5.0.0.

This module implements the 7-qubit Steane code, a CSS (Calderbank-Shor-Steane)
code that can correct arbitrary single-qubit errors. The Steane code encodes
one logical qubit using 7 physical qubits.

Example:
    >>> from bioql.qec import SteaneCodeQEC
    >>> qec = SteaneCodeQEC(error_rate=0.001)
    >>> overhead = qec.calculate_overhead()
    >>> print(f"Overhead: {overhead}x")  # 7x
"""

from typing import Optional
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class SteaneCodeQEC:
    """
    Steane Code Quantum Error Correction.

    The Steane code is a [[7,1,3]] CSS code that encodes 1 logical qubit
    using 7 physical qubits with distance 3. It can correct any single-qubit
    error (bit flip, phase flip, or both).

    Key properties:
    - Encodes 1 logical qubit in 7 physical qubits
    - Can correct 1 error per block
    - Enables fault-tolerant quantum computation
    - Supports transversal CNOT gate

    Attributes:
        error_rate: Physical hardware error rate (probability of error per gate)

    Example:
        >>> qec = SteaneCodeQEC(error_rate=0.001)
        >>> qec.validate()
        >>> physical = qec.get_physical_qubits(logical_qubits=10)
        >>> print(f"Need {physical} physical qubits for 10 logical qubits")
    """

    error_rate: float = 0.001

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()
        logger.info(f"Initialized Steane Code QEC: error_rate={self.error_rate}")

    @property
    def overhead(self) -> int:
        """
        Qubit overhead for Steane code.

        The Steane code always requires exactly 7 physical qubits per logical qubit.

        Returns:
            7 (constant overhead)
        """
        return 7

    def calculate_overhead(self) -> int:
        """
        Calculate the qubit overhead for the Steane code.

        Returns:
            7 physical qubits per logical qubit (constant)

        Example:
            >>> qec = SteaneCodeQEC()
            >>> overhead = qec.calculate_overhead()
            >>> print(f"Overhead: {overhead}x")
        """
        return self.overhead

    def validate(self) -> bool:
        """
        Validate Steane code parameters.

        Checks:
        - Error rate is in valid range (0 < error_rate < 0.1)

        Returns:
            True if all parameters are valid

        Raises:
            ValueError: If error rate is invalid

        Example:
            >>> qec = SteaneCodeQEC(error_rate=0.001)
            >>> qec.validate()  # Returns True
            >>> qec = SteaneCodeQEC(error_rate=0.5)
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
            Total number of physical qubits required (logical_qubits * 7)

        Raises:
            ValueError: If logical_qubits is not positive

        Example:
            >>> qec = SteaneCodeQEC()
            >>> physical = qec.get_physical_qubits(logical_qubits=10)
            >>> print(f"Need {physical} physical qubits")  # 70
        """
        if logical_qubits < 1:
            raise ValueError(f"logical_qubits must be positive, got {logical_qubits}")

        return logical_qubits * self.overhead

    def estimate_logical_error_rate(self) -> float:
        """
        Estimate the logical error rate after error correction.

        For the Steane code (distance d=3), the logical error rate is
        approximately p_L ≈ 35 * p^2, where p is the physical error rate.
        This assumes the physical error rate is below the threshold (~2.9e-3).

        Returns:
            Estimated logical error rate

        Example:
            >>> qec = SteaneCodeQEC(error_rate=0.001)
            >>> logical_error = qec.estimate_logical_error_rate()
            >>> print(f"Logical error rate: {logical_error:.2e}")
        """
        p = self.error_rate
        threshold = 2.9e-3  # Approximate threshold for Steane code

        if p >= threshold:
            logger.warning(
                f"Physical error rate {p} is at or above threshold {threshold}. "
                "Error correction may not be effective."
            )
            return p

        # For distance-3 codes, logical error rate ≈ 35 * p^2
        # This is an approximation based on error correction theory
        logical_error_rate = 35 * (p ** 2)

        return min(logical_error_rate, p)  # Can't be worse than no correction

    def get_stabilizers(self) -> dict:
        """
        Get the stabilizer generators for the Steane code.

        The Steane code has 6 stabilizer generators (3 for X errors, 3 for Z errors).

        Returns:
            Dictionary containing X and Z stabilizers

        Example:
            >>> qec = SteaneCodeQEC()
            >>> stabilizers = qec.get_stabilizers()
            >>> print(stabilizers['X'])
        """
        return {
            'X': [
                'IIIXXXX',  # X stabilizer 1
                'IXXIIXX',  # X stabilizer 2
                'XIXIXIX',  # X stabilizer 3
            ],
            'Z': [
                'IIIZZZZ',  # Z stabilizer 1
                'IZZIIZZ',  # Z stabilizer 2
                'ZIZIZIZ',  # Z stabilizer 3
            ]
        }

    def get_logical_operators(self) -> dict:
        """
        Get the logical X and Z operators for the Steane code.

        Returns:
            Dictionary containing logical X and Z operators

        Example:
            >>> qec = SteaneCodeQEC()
            >>> operators = qec.get_logical_operators()
            >>> print(operators['X'])
        """
        return {
            'X': 'XXXXXXX',  # Logical X
            'Z': 'ZZZZZZZ',  # Logical Z
        }

    def get_encoding_circuit_depth(self) -> int:
        """
        Get the depth of the encoding circuit.

        The Steane code encoding circuit has constant depth.

        Returns:
            Circuit depth for encoding (approximately 6 layers)

        Example:
            >>> qec = SteaneCodeQEC()
            >>> depth = qec.get_encoding_circuit_depth()
            >>> print(f"Encoding depth: {depth}")
        """
        return 6

    def get_syndrome_circuit_depth(self) -> int:
        """
        Get the depth of the syndrome measurement circuit.

        Returns:
            Circuit depth for syndrome measurement (approximately 4 layers)

        Example:
            >>> qec = SteaneCodeQEC()
            >>> depth = qec.get_syndrome_circuit_depth()
            >>> print(f"Syndrome depth: {depth}")
        """
        return 4

    def __repr__(self) -> str:
        """String representation of the Steane code configuration."""
        return (
            f"SteaneCodeQEC(error_rate={self.error_rate}, "
            f"overhead={self.overhead}x)"
        )

    def to_dict(self) -> dict:
        """
        Convert Steane code configuration to dictionary.

        Returns:
            Dictionary representation of the configuration

        Example:
            >>> qec = SteaneCodeQEC(error_rate=0.001)
            >>> config = qec.to_dict()
            >>> print(config)
        """
        return {
            'code_type': 'steane',
            'code_parameters': [7, 1, 3],  # [[n, k, d]] notation
            'error_rate': self.error_rate,
            'overhead': self.overhead,
            'estimated_logical_error_rate': self.estimate_logical_error_rate(),
            'encoding_circuit_depth': self.get_encoding_circuit_depth(),
            'syndrome_circuit_depth': self.get_syndrome_circuit_depth(),
        }
