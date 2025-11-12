#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Pauli Frame Tracking
===================

Implements Pauli frame tracking for fault-tolerant quantum computing.

Mathematical Foundation:
-----------------------
A Pauli frame tracks the accumulated Pauli corrections applied to qubits.
Instead of physically applying corrections, we track them classically and
update the interpretation of measurement outcomes.

Pauli Group:
-----------
P_n = {±I, ±iI, ±X, ±iX, ±Y, ±iY, ±Z, ±iZ}^⊗n

Commutation Relations:
---------------------
XZ = -ZX  (anticommute)
XY = iZ
YZ = iX
ZX = -XZ

Frame Update Rule:
-----------------
If correction C is applied, frame F → F' where:
F' = C · F · C†

Logical Operations:
------------------
Logical X: X̄ = X^⊗d (horizontal chain)
Logical Z: Z̄ = Z^⊗d (vertical chain)
"""

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from loguru import logger


class PauliType(Enum):
    """Pauli operator types."""

    I = 0  # Identity
    X = 1  # Bit flip
    Y = 2  # Both
    Z = 3  # Phase flip


@dataclass
class PauliOperator:
    """
    Single-qubit Pauli operator.

    Represented as (type, phase) where phase ∈ {0, π/2, π, 3π/2}
    corresponding to coefficients {1, i, -1, -i}.
    """

    type: PauliType
    phase: int = 0  # 0, 1, 2, 3 for 1, i, -1, -i

    def __mul__(self, other: "PauliOperator") -> "PauliOperator":
        """
        Multiply two Pauli operators.

        Uses commutation relations:
        XX = I, YY = I, ZZ = I
        XY = iZ, YZ = iX, ZX = iY (cyclic)
        YX = -iZ, ZY = -iX, XZ = -iY (anti-cyclic)
        """
        if self.type == PauliType.I:
            return PauliOperator(other.type, (self.phase + other.phase) % 4)
        if other.type == PauliType.I:
            return PauliOperator(self.type, (self.phase + other.phase) % 4)

        # Same operator: gives identity
        if self.type == other.type:
            return PauliOperator(PauliType.I, (self.phase + other.phase) % 4)

        # Different operators: use multiplication table
        # X*Y = iZ, Y*Z = iX, Z*X = iY
        # Y*X = -iZ, Z*Y = -iX, X*Z = -iY

        table = {
            (PauliType.X, PauliType.Y): (PauliType.Z, 1),  # iZ
            (PauliType.Y, PauliType.Z): (PauliType.X, 1),  # iX
            (PauliType.Z, PauliType.X): (PauliType.Y, 1),  # iY
            (PauliType.Y, PauliType.X): (PauliType.Z, 3),  # -iZ
            (PauliType.Z, PauliType.Y): (PauliType.X, 3),  # -iX
            (PauliType.X, PauliType.Z): (PauliType.Y, 3),  # -iY
        }

        result_type, phase_shift = table[(self.type, other.type)]
        return PauliOperator(result_type, (self.phase + other.phase + phase_shift) % 4)

    def commutes_with(self, other: "PauliOperator") -> bool:
        """Check if this operator commutes with another."""
        if self.type == PauliType.I or other.type == PauliType.I:
            return True
        if self.type == other.type:
            return True
        return False

    def to_string(self) -> str:
        """String representation."""
        phase_symbols = ["", "i", "-", "-i"]
        return f"{phase_symbols[self.phase]}{self.type.name}"

    def __str__(self) -> str:
        return self.to_string()


@dataclass
class PauliString:
    """
    Multi-qubit Pauli string P = P_1 ⊗ P_2 ⊗ ... ⊗ P_n.
    """

    operators: List[PauliOperator]

    def __post_init__(self):
        """Ensure all operators are PauliOperator instances."""
        self.operators = [
            op if isinstance(op, PauliOperator) else PauliOperator(PauliType[op], 0)
            for op in self.operators
        ]

    @property
    def num_qubits(self) -> int:
        return len(self.operators)

    @property
    def weight(self) -> int:
        """Number of non-identity operators."""
        return sum(1 for op in self.operators if op.type != PauliType.I)

    def __mul__(self, other: "PauliString") -> "PauliString":
        """Multiply two Pauli strings."""
        if self.num_qubits != other.num_qubits:
            raise ValueError("Pauli strings must have same length")

        result = [self.operators[i] * other.operators[i] for i in range(self.num_qubits)]
        return PauliString(result)

    def commutes_with(self, other: "PauliString") -> bool:
        """
        Check if two Pauli strings commute.

        Two Paulis commute iff they have even number of anticommuting pairs.
        """
        if self.num_qubits != other.num_qubits:
            return False

        anticommute_count = 0
        for i in range(self.num_qubits):
            if not self.operators[i].commutes_with(other.operators[i]):
                anticommute_count += 1

        return anticommute_count % 2 == 0

    def support(self) -> Set[int]:
        """Indices of non-identity operators."""
        return {i for i, op in enumerate(self.operators) if op.type != PauliType.I}

    def to_string(self) -> str:
        """String representation."""
        return " ⊗ ".join(op.to_string() for op in self.operators)

    def __str__(self) -> str:
        return self.to_string()

    @staticmethod
    def from_string(s: str) -> "PauliString":
        """Create from string like 'XIXYZ'."""
        operators = [PauliOperator(PauliType[c], 0) for c in s]
        return PauliString(operators)


class PauliFrame:
    """
    Pauli frame for tracking accumulated corrections.

    Maintains separate X and Z frames (since Y = iXZ).
    """

    def __init__(self, num_qubits: int):
        """
        Initialize identity frame.

        Args:
            num_qubits: Number of qubits
        """
        self.num_qubits = num_qubits
        self.x_frame = np.zeros(num_qubits, dtype=np.uint8)  # X corrections
        self.z_frame = np.zeros(num_qubits, dtype=np.uint8)  # Z corrections

    def apply_correction(self, correction: PauliString):
        """
        Apply correction to frame.

        Updates frame based on correction operators.
        """
        if correction.num_qubits != self.num_qubits:
            raise ValueError("Correction size mismatch")

        for i, op in enumerate(correction.operators):
            if op.type == PauliType.X:
                self.x_frame[i] ^= 1
            elif op.type == PauliType.Z:
                self.z_frame[i] ^= 1
            elif op.type == PauliType.Y:
                self.x_frame[i] ^= 1
                self.z_frame[i] ^= 1

    def get_correction_for_qubit(self, qubit: int) -> PauliOperator:
        """Get accumulated correction for a specific qubit."""
        x_bit = self.x_frame[qubit]
        z_bit = self.z_frame[qubit]

        if x_bit == 0 and z_bit == 0:
            return PauliOperator(PauliType.I)
        elif x_bit == 1 and z_bit == 0:
            return PauliOperator(PauliType.X)
        elif x_bit == 0 and z_bit == 1:
            return PauliOperator(PauliType.Z)
        else:  # x_bit == 1 and z_bit == 1
            return PauliOperator(PauliType.Y)

    def get_full_correction(self) -> PauliString:
        """Get full correction as Pauli string."""
        operators = [self.get_correction_for_qubit(i) for i in range(self.num_qubits)]
        return PauliString(operators)

    def propagate_through_gate(self, gate: str, qubits: List[int]):
        """
        Propagate frame through a quantum gate.

        Uses gate conjugation: F' = G F G†
        """
        if gate == "H":
            # H: X ↔ Z
            qubit = qubits[0]
            self.x_frame[qubit], self.z_frame[qubit] = self.z_frame[qubit], self.x_frame[qubit]

        elif gate == "S":
            # S: X → Y, Y → -X, Z → Z
            qubit = qubits[0]
            if self.x_frame[qubit]:
                self.z_frame[qubit] ^= 1

        elif gate == "CNOT":
            # CNOT: X_c → X_c X_t, Z_c → Z_c, X_t → X_t, Z_t → Z_c Z_t
            control, target = qubits
            self.x_frame[target] ^= self.x_frame[control]
            self.z_frame[control] ^= self.z_frame[target]

        elif gate == "CZ":
            # CZ: X_c → X_c Z_t, X_t → Z_c X_t, Z_c → Z_c, Z_t → Z_t
            qubit1, qubit2 = qubits
            self.z_frame[qubit1] ^= self.x_frame[qubit2]
            self.z_frame[qubit2] ^= self.x_frame[qubit1]

    def update_from_measurement(self, qubit: int, basis: str, outcome: int) -> int:
        """
        Update frame from measurement and return corrected outcome.

        Args:
            qubit: Measured qubit
            basis: 'X' or 'Z'
            outcome: Raw measurement outcome (0 or 1)

        Returns:
            Corrected outcome
        """
        if basis == "Z":
            corrected = outcome ^ self.z_frame[qubit]
            self.x_frame[qubit] = 0  # Measurement collapses X
        else:  # basis == 'X'
            corrected = outcome ^ self.x_frame[qubit]
            self.z_frame[qubit] = 0  # Measurement collapses Z

        return corrected

    def copy(self) -> "PauliFrame":
        """Create deep copy of frame."""
        frame = PauliFrame(self.num_qubits)
        frame.x_frame = self.x_frame.copy()
        frame.z_frame = self.z_frame.copy()
        return frame

    def to_string(self) -> str:
        """String representation."""
        return self.get_full_correction().to_string()


@dataclass
class LogicalOperator:
    """
    Logical operator for error-corrected qubit.

    Represented as a Pauli string on physical qubits.
    """

    pauli_string: PauliString
    type: str  # 'X' or 'Z'
    code_distance: int

    def evaluate_on_frame(self, frame: PauliFrame) -> int:
        """
        Evaluate logical operator given Pauli frame.

        Returns:
            0 or 1 indicating logical outcome
        """
        result = 0
        for i in frame.support():
            op = frame.get_correction_for_qubit(i)
            if self.pauli_string.operators[i].type != PauliType.I:
                # Check if correction anticommutes with logical operator
                if not op.commutes_with(self.pauli_string.operators[i]):
                    result ^= 1
        return result


class PauliFrameTracker:
    """
    Tracks Pauli frames across multiple qubits and QEC rounds.

    Maintains history for debugging and analysis.
    """

    def __init__(self, num_data_qubits: int, num_syndrome_qubits: int):
        """
        Initialize tracker.

        Args:
            num_data_qubits: Number of data qubits
            num_syndrome_qubits: Number of syndrome qubits
        """
        self.num_data = num_data_qubits
        self.num_syndrome = num_syndrome_qubits
        self.num_total = num_data_qubits + num_syndrome_qubits

        # Separate frames for data and syndrome qubits
        self.data_frame = PauliFrame(num_data_qubits)
        self.syndrome_frame = PauliFrame(num_syndrome_qubits)

        # History
        self.frame_history: List[PauliFrame] = []

        logger.info(
            f"Initialized PauliFrameTracker: "
            f"{num_data_qubits} data qubits, "
            f"{num_syndrome_qubits} syndrome qubits"
        )

    def apply_correction_from_decoder(self, correction: np.ndarray):
        """
        Apply correction from decoder output.

        Args:
            correction: Binary array indicating which qubits to correct
        """
        # Convert to Pauli string (assume X corrections)
        operators = [
            PauliOperator(PauliType.X if correction[i] else PauliType.I)
            for i in range(self.num_data)
        ]
        pauli_correction = PauliString(operators)

        # Apply to data frame
        self.data_frame.apply_correction(pauli_correction)

        # Save to history
        self.frame_history.append(self.data_frame.copy())

    def compute_logical_outcome(
        self, logical_operator: LogicalOperator, measurement_outcomes: np.ndarray
    ) -> int:
        """
        Compute logical measurement outcome.

        Takes into account Pauli frame corrections.

        Args:
            logical_operator: Logical X or Z operator
            measurement_outcomes: Raw measurement results

        Returns:
            Corrected logical outcome (0 or 1)
        """
        # XOR measurement outcomes on logical operator support
        logical_outcome = 0
        for i in logical_operator.pauli_string.support():
            logical_outcome ^= measurement_outcomes[i]

        # Correct based on frame
        frame_correction = logical_operator.evaluate_on_frame(self.data_frame)
        corrected_outcome = logical_outcome ^ frame_correction

        return corrected_outcome

    def reset(self):
        """Reset frames to identity."""
        self.data_frame = PauliFrame(self.num_data)
        self.syndrome_frame = PauliFrame(self.num_syndrome)
        self.frame_history.clear()

    def get_statistics(self) -> Dict:
        """Get statistics on frame evolution."""
        if not self.frame_history:
            return {}

        weights = [frame.get_full_correction().weight for frame in self.frame_history]

        return {
            "num_rounds": len(self.frame_history),
            "avg_weight": np.mean(weights),
            "max_weight": np.max(weights),
            "final_weight": weights[-1],
            "total_corrections": sum(weights),
        }


def create_logical_operators(
    code_distance: int, qubit_layout: "QubitLayout"
) -> Tuple[LogicalOperator, LogicalOperator]:
    """
    Create logical X and Z operators for surface code.

    Args:
        code_distance: Distance of surface code
        qubit_layout: Qubit layout from surface code

    Returns:
        (logical_X, logical_Z)
    """
    num_data = len(qubit_layout.data_qubits)

    # Logical Z: vertical chain
    z_operators = [PauliOperator(PauliType.I) for _ in range(num_data)]
    for i in range(code_distance):
        qubit_idx = i  # First column
        z_operators[qubit_idx] = PauliOperator(PauliType.Z)

    logical_z = LogicalOperator(
        pauli_string=PauliString(z_operators), type="Z", code_distance=code_distance
    )

    # Logical X: horizontal chain
    x_operators = [PauliOperator(PauliType.I) for _ in range(num_data)]
    for j in range(code_distance):
        qubit_idx = j * code_distance  # First row
        x_operators[qubit_idx] = PauliOperator(PauliType.X)

    logical_x = LogicalOperator(
        pauli_string=PauliString(x_operators), type="X", code_distance=code_distance
    )

    return logical_x, logical_z
