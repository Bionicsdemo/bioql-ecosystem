"""
Abstract base class for quantum engines in CRISPR-QAI

All quantum backends must implement this interface for:
- Energy collapse estimation (gRNA-DNA affinity)
- Quantum circuit execution
- Result parsing and validation
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import numpy as np


class QuantumEngine(ABC):
    """
    Abstract interface for quantum computing backends

    Subclasses must implement:
    - run_energy_estimation(): Execute quantum circuit and return energy
    - validate_backend(): Check if backend is available and configured
    """

    def __init__(self, backend_name: str, shots: int = 1000):
        """
        Initialize quantum engine

        Args:
            backend_name: Name of quantum backend (e.g., 'simulator', 'ibm_torino', 'sv1')
            shots: Number of quantum measurements
        """
        self.backend_name = backend_name
        self.shots = shots
        self.validated = False

    @abstractmethod
    def run_energy_estimation(
        self,
        angles: List[float],
        coupling_strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute quantum circuit for energy estimation

        Args:
            angles: Rotation angles encoding gRNA sequence (radians)
            coupling_strength: Coupling between qubits (default: 1.0)
            metadata: Additional context (guide_id, target_sequence, etc.)

        Returns:
            {
                'energy_estimate': float,  # Estimated binding energy
                'confidence': float,       # Measurement confidence (0-1)
                'runtime_seconds': float,  # Execution time
                'backend': str,            # Backend used
                'shots': int,              # Total measurements
                'metadata': dict           # Original metadata
            }
        """
        pass

    @abstractmethod
    def validate_backend(self) -> bool:
        """
        Check if quantum backend is available and properly configured

        Returns:
            True if backend is ready, False otherwise
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Get backend information

        Returns:
            Dictionary with backend details
        """
        return {
            'backend_name': self.backend_name,
            'shots': self.shots,
            'validated': self.validated,
            'engine_type': self.__class__.__name__
        }

    def _validate_angles(self, angles: List[float]) -> None:
        """
        Validate input angles

        Args:
            angles: Rotation angles to validate

        Raises:
            ValueError: If angles are invalid
        """
        if not angles:
            raise ValueError("angles cannot be empty")

        if not all(isinstance(a, (int, float)) for a in angles):
            raise ValueError("All angles must be numeric")

        if not all(0 <= a <= 2*np.pi for a in angles):
            raise ValueError("All angles must be in range [0, 2π]")

    def _calculate_confidence(self, counts: Dict[str, int]) -> float:
        """
        Calculate measurement confidence from counts

        Args:
            counts: Measurement results {bitstring: count}

        Returns:
            Confidence score (0-1), higher = more uniform distribution
        """
        if not counts:
            return 0.0

        total_shots = sum(counts.values())
        probabilities = [count / total_shots for count in counts.values()]

        # Shannon entropy normalized to [0, 1]
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
        max_entropy = np.log2(len(counts))

        if max_entropy == 0:
            return 0.0

        return entropy / max_entropy
