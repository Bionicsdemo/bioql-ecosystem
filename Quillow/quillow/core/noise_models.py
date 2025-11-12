#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum Noise Models
===================

Implements realistic noise models for quantum error correction simulation.

Physical Noise Channels:
------------------------

1. Depolarizing Channel:
   ρ → (1-p)ρ + p/3(XρX + YρY + ZρZ)
   Represents uniform random Pauli errors

2. Bit Flip Channel:
   ρ → (1-p)ρ + pXρX
   X errors only (amplitude damping approximation)

3. Phase Flip Channel:
   ρ → (1-p)ρ + pZρZ
   Z errors only (dephasing)

4. Amplitude Damping:
   Models T1 relaxation (energy decay)
   |1⟩ → |0⟩ with probability p

5. Phase Damping:
   Models T2 dephasing (coherence loss)
   Preserves populations, destroys coherences

Mathematical Formulation:
------------------------
Kraus operators for depolarizing:
K_0 = √(1-3p/4) I
K_1 = √(p/4) X
K_2 = √(p/4) Y
K_3 = √(p/4) Z
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import stim
from loguru import logger


@dataclass
class NoiseParameters:
    """Physical noise parameters."""

    single_qubit_gate_error: float = 0.001  # 0.1%
    two_qubit_gate_error: float = 0.010  # 1.0%
    measurement_error: float = 0.001  # 0.1%
    idle_error_per_us: float = 0.0001  # 0.01% per μs
    T1_us: float = 100.0  # Amplitude damping time
    T2_us: float = 50.0  # Phase damping time
    reset_error: float = 0.001  # 0.1%

    def scale(self, factor: float) -> "NoiseParameters":
        """Scale all error rates by a factor."""
        return NoiseParameters(
            single_qubit_gate_error=self.single_qubit_gate_error * factor,
            two_qubit_gate_error=self.two_qubit_gate_error * factor,
            measurement_error=self.measurement_error * factor,
            idle_error_per_us=self.idle_error_per_us * factor,
            T1_us=self.T1_us / factor if factor > 0 else self.T1_us,
            T2_us=self.T2_us / factor if factor > 0 else self.T2_us,
            reset_error=self.reset_error * factor,
        )


class NoiseModel(ABC):
    """
    Abstract base class for noise models.

    Subclasses implement specific noise channels.
    """

    def __init__(self, error_rate: float):
        """
        Initialize noise model.

        Args:
            error_rate: Base error probability
        """
        self.error_rate = error_rate
        logger.info(f"Initialized {self.__class__.__name__} with p={error_rate:.6f}")

    @abstractmethod
    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """Generate noise for single-qubit gates."""
        pass

    @abstractmethod
    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """Generate noise for two-qubit gates."""
        pass

    @abstractmethod
    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        """Generate measurement noise."""
        pass

    @abstractmethod
    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        """Generate idle/waiting noise."""
        pass

    def after_reset_noise(self, num_qubits: int) -> stim.Circuit:
        """Noise after qubit reset."""
        circuit = stim.Circuit()
        circuit.append("DEPOLARIZE1", range(num_qubits), self.error_rate)
        return circuit


class DepolarizingNoise(NoiseModel):
    """
    Depolarizing noise model.

    Most commonly used for simulations due to mathematical tractability.

    Channel: ρ → (1-p)ρ + p/3(XρX + YρY + ZρZ)

    Physical interpretation:
    - With probability (1-p): no error
    - With probability p/3 each: random X, Y, or Z error
    """

    def __init__(self, error_rate: float, params: Optional[NoiseParameters] = None):
        super().__init__(error_rate)
        self.params = params or NoiseParameters(
            single_qubit_gate_error=error_rate,
            two_qubit_gate_error=error_rate * 10,
            measurement_error=error_rate,
        )

    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """
        Depolarizing noise after single-qubit gate.

        Stim DEPOLARIZE1(p): applies Pauli with probability p
        """
        circuit = stim.Circuit()
        circuit.append("DEPOLARIZE1", qubits, self.params.single_qubit_gate_error)
        return circuit

    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """
        Depolarizing noise after two-qubit gate.

        DEPOLARIZE2(p): applies random two-qubit Pauli with probability p
        """
        circuit = stim.Circuit()
        circuit.append("DEPOLARIZE2", qubits, self.params.two_qubit_gate_error)
        return circuit

    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        """
        Measurement bit-flip noise.

        X_ERROR(p): flips measurement outcome with probability p
        """
        circuit = stim.Circuit()
        circuit.append("X_ERROR", range(num_qubits), self.params.measurement_error)
        return circuit

    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        """
        Idle depolarizing noise.

        Error rate scales with time.
        """
        idle_error = min(self.params.idle_error_per_us * time_us, 0.75)
        circuit = stim.Circuit()
        circuit.append("DEPOLARIZE1", qubits, idle_error)
        return circuit


class BitFlipNoise(NoiseModel):
    """
    Bit flip (X) noise only.

    Channel: ρ → (1-p)ρ + pXρX

    Useful for testing X-error correction.
    """

    def __init__(self, error_rate: float):
        super().__init__(error_rate)

    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, self.error_rate)
        return circuit

    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        circuit = stim.Circuit()
        # Independent X errors on each qubit
        circuit.append("X_ERROR", qubits, self.error_rate)
        return circuit

    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        circuit = stim.Circuit()
        circuit.append("X_ERROR", range(num_qubits), self.error_rate)
        return circuit

    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, self.error_rate * time_us)
        return circuit


class PhaseFlipNoise(NoiseModel):
    """
    Phase flip (Z) noise only.

    Channel: ρ → (1-p)ρ + pZρZ

    Useful for testing Z-error correction (dephasing).
    """

    def __init__(self, error_rate: float):
        super().__init__(error_rate)

    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        circuit = stim.Circuit()
        circuit.append("Z_ERROR", qubits, self.error_rate)
        return circuit

    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        circuit = stim.Circuit()
        circuit.append("Z_ERROR", qubits, self.error_rate)
        return circuit

    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        # Phase flip before measurement = bit flip of outcome
        circuit = stim.Circuit()
        circuit.append("Z_ERROR", range(num_qubits), self.error_rate)
        return circuit

    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        circuit = stim.Circuit()
        circuit.append("Z_ERROR", qubits, self.error_rate * time_us)
        return circuit


class AmplitudeDampingNoise(NoiseModel):
    """
    Amplitude damping (T1 relaxation).

    Models energy decay: |1⟩ → |0⟩

    Non-unital channel (doesn't preserve trace of all states).

    Kraus operators:
    K_0 = [[1, 0], [0, √(1-γ)]]
    K_1 = [[0, √γ], [0, 0]]

    where γ = 1 - exp(-t/T1)
    """

    def __init__(self, T1_us: float = 100.0):
        """
        Initialize with T1 time.

        Args:
            T1_us: Amplitude damping time in microseconds
        """
        self.T1_us = T1_us
        super().__init__(error_rate=0.0)  # Rate depends on time
        logger.info(f"Amplitude damping: T1={T1_us:.1f}μs")

    def _damping_probability(self, time_us: float) -> float:
        """Calculate damping probability for given time."""
        return 1.0 - np.exp(-time_us / self.T1_us)

    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """Assume single-qubit gates take ~20ns."""
        gate_time = 0.02  # μs
        p = self._damping_probability(gate_time)
        circuit = stim.Circuit()
        # Approximate with X error (|1⟩ → |0⟩)
        circuit.append("X_ERROR", qubits, p)
        return circuit

    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """Assume two-qubit gates take ~40ns."""
        gate_time = 0.04  # μs
        p = self._damping_probability(gate_time)
        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, p)
        return circuit

    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        """Measurement takes ~1μs."""
        meas_time = 1.0  # μs
        p = self._damping_probability(meas_time)
        circuit = stim.Circuit()
        circuit.append("X_ERROR", range(num_qubits), p)
        return circuit

    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        """Direct calculation from idle time."""
        p = self._damping_probability(time_us)
        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, p)
        return circuit


class CoherenceNoise(NoiseModel):
    """
    Combined T1/T2 coherence noise.

    Most realistic model combining:
    - Amplitude damping (T1)
    - Phase damping (T2)

    T2 ≤ 2*T1 (fundamental bound)

    Effective error rate:
    p_amp = 1 - exp(-t/T1)
    p_phase = 1 - exp(-t/T2)
    """

    def __init__(self, T1_us: float = 100.0, T2_us: float = 50.0):
        """
        Initialize with coherence times.

        Args:
            T1_us: Amplitude damping time
            T2_us: Phase damping time (T2 ≤ 2*T1)
        """
        if T2_us > 2 * T1_us:
            logger.warning(
                f"T2={T2_us}μs > 2*T1={2*T1_us}μs violates physical bound. " f"Setting T2=2*T1."
            )
            T2_us = 2 * T1_us

        self.T1_us = T1_us
        self.T2_us = T2_us
        super().__init__(error_rate=0.0)

        logger.info(f"Coherence noise: T1={T1_us:.1f}μs, T2={T2_us:.1f}μs")

    def _error_probabilities(self, time_us: float) -> Tuple[float, float]:
        """
        Calculate amplitude and phase error probabilities.

        Returns:
            (p_amplitude, p_phase)
        """
        p_amp = 1.0 - np.exp(-time_us / self.T1_us)
        p_phase = 1.0 - np.exp(-time_us / self.T2_us)
        return p_amp, p_phase

    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        gate_time = 0.02  # 20ns
        p_amp, p_phase = self._error_probabilities(gate_time)

        circuit = stim.Circuit()
        # Amplitude damping ≈ X error
        circuit.append("X_ERROR", qubits, p_amp)
        # Phase damping ≈ Z error
        circuit.append("Z_ERROR", qubits, p_phase)
        return circuit

    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        gate_time = 0.04  # 40ns
        p_amp, p_phase = self._error_probabilities(gate_time)

        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, p_amp)
        circuit.append("Z_ERROR", qubits, p_phase)
        return circuit

    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        meas_time = 1.0  # 1μs
        p_amp, p_phase = self._error_probabilities(meas_time)

        circuit = stim.Circuit()
        circuit.append("X_ERROR", range(num_qubits), p_amp)
        circuit.append("Z_ERROR", range(num_qubits), p_phase)
        return circuit

    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        p_amp, p_phase = self._error_probabilities(time_us)

        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, p_amp)
        circuit.append("Z_ERROR", qubits, p_phase)
        return circuit


class CircuitLevelNoise(NoiseModel):
    """
    Circuit-level noise model matching experimental hardware.

    Based on typical superconducting qubit parameters:
    - Single-qubit gate: 0.1% error
    - Two-qubit gate: 1.0% error
    - Measurement: 0.5% error
    - T1 = 100μs, T2 = 50μs
    """

    def __init__(self, params: Optional[NoiseParameters] = None):
        """
        Initialize with realistic parameters.

        Args:
            params: Noise parameters (uses defaults if None)
        """
        self.params = params or NoiseParameters()
        super().__init__(self.params.single_qubit_gate_error)

        logger.info(
            f"Circuit-level noise initialized:\n"
            f"  Single-qubit gate: {self.params.single_qubit_gate_error:.4f}\n"
            f"  Two-qubit gate: {self.params.two_qubit_gate_error:.4f}\n"
            f"  Measurement: {self.params.measurement_error:.4f}\n"
            f"  T1: {self.params.T1_us:.1f}μs\n"
            f"  T2: {self.params.T2_us:.1f}μs"
        )

    def single_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """Depolarizing noise for single-qubit gates."""
        circuit = stim.Circuit()
        circuit.append("DEPOLARIZE1", qubits, self.params.single_qubit_gate_error)
        return circuit

    def two_qubit_gate_noise(self, qubits: List[int]) -> stim.Circuit:
        """Depolarizing noise for two-qubit gates."""
        circuit = stim.Circuit()
        circuit.append("DEPOLARIZE2", qubits, self.params.two_qubit_gate_error)
        return circuit

    def measurement_noise(self, num_qubits: int) -> stim.Circuit:
        """Measurement readout error."""
        circuit = stim.Circuit()
        circuit.append("X_ERROR", range(num_qubits), self.params.measurement_error)
        return circuit

    def idle_noise(self, qubits: List[int], time_us: float) -> stim.Circuit:
        """
        Coherence-limited idle noise.

        Uses T1/T2 to compute error probability.
        """
        p_amp = 1.0 - np.exp(-time_us / self.params.T1_us)
        p_phase = 1.0 - np.exp(-time_us / self.params.T2_us)

        circuit = stim.Circuit()
        circuit.append("X_ERROR", qubits, min(p_amp, 0.75))
        circuit.append("Z_ERROR", qubits, min(p_phase, 0.75))
        return circuit


def get_noise_model(model_type: str, error_rate: float = 0.001, **kwargs) -> NoiseModel:
    """
    Factory function to create noise models.

    Args:
        model_type: Type of noise model
        error_rate: Base error rate
        **kwargs: Additional parameters

    Returns:
        NoiseModel instance

    Available models:
    - 'depolarizing': Uniform Pauli errors
    - 'bitflip': X errors only
    - 'phaseflip': Z errors only
    - 'amplitude_damping': T1 relaxation
    - 'coherence': T1/T2 combined
    - 'circuit_level': Realistic hardware model
    """
    models = {
        "depolarizing": DepolarizingNoise,
        "bitflip": BitFlipNoise,
        "phaseflip": PhaseFlipNoise,
        "amplitude_damping": AmplitudeDampingNoise,
        "coherence": CoherenceNoise,
        "circuit_level": CircuitLevelNoise,
    }

    if model_type not in models:
        raise ValueError(f"Unknown noise model: {model_type}. " f"Available: {list(models.keys())}")

    model_class = models[model_type]

    # Pass appropriate parameters
    if model_type in ["depolarizing", "bitflip", "phaseflip"]:
        return model_class(error_rate)
    elif model_type == "amplitude_damping":
        T1_us = kwargs.get("T1_us", 100.0)
        return model_class(T1_us=T1_us)
    elif model_type == "coherence":
        T1_us = kwargs.get("T1_us", 100.0)
        T2_us = kwargs.get("T2_us", 50.0)
        return model_class(T1_us=T1_us, T2_us=T2_us)
    elif model_type == "circuit_level":
        params = kwargs.get("params", None)
        return model_class(params=params)

    return model_class(error_rate)


# Pre-configured noise models for common scenarios
WILLOW_NOISE = CircuitLevelNoise(
    NoiseParameters(
        single_qubit_gate_error=0.001,  # 0.1%
        two_qubit_gate_error=0.006,  # 0.6%
        measurement_error=0.001,  # 0.1%
        T1_us=100.0,
        T2_us=80.0,
    )
)

IBM_QUANTUM_NOISE = CircuitLevelNoise(
    NoiseParameters(
        single_qubit_gate_error=0.0003,  # 0.03%
        two_qubit_gate_error=0.007,  # 0.7%
        measurement_error=0.015,  # 1.5%
        T1_us=120.0,
        T2_us=90.0,
    )
)

IONQ_NOISE = CircuitLevelNoise(
    NoiseParameters(
        single_qubit_gate_error=0.0001,  # 0.01%
        two_qubit_gate_error=0.005,  # 0.5%
        measurement_error=0.002,  # 0.2%
        T1_us=1000.0,  # Trapped ions have long coherence
        T2_us=500.0,
    )
)
