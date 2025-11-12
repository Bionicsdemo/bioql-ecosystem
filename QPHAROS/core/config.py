# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Configuration
Contains all system-wide settings and constants
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class QPHAROSConfig:
    """Main configuration for QPHAROS system"""

    # Quantum Backend Settings
    backend: str = "ibm_torino"
    shots: int = 4096
    qec_enabled: bool = True
    qec_type: str = "surface_code"
    logical_qubits: int = 2

    # BioQL API Settings
    api_key: Optional[str] = None
    api_endpoint: str = "https://api.bioql.bio"

    # Molecular Encoding
    qubits_per_atom: int = 3
    max_molecular_weight: float = 500.0

    # Binding Prediction
    binding_layers: int = 6
    binding_qubits: int = 20

    # ADMET Constraints (Lipinski's Rule of Five)
    max_molecular_weight_admet: float = 500.0
    logP_range: tuple = (-0.4, 5.6)
    max_h_bond_donors: int = 5
    max_h_bond_acceptors: int = 10

    # Molecular Generation
    generator_qubits: int = 15
    generator_layers: int = 8
    discriminator_qubits: int = 12

    # Molecular Dynamics
    md_time_steps: int = 100
    md_timestep: float = 0.01  # femtoseconds
    trotter_order: int = 4

    # Optimization
    max_iterations: int = 100
    convergence_threshold: float = 1e-4

    # Weights for combined scoring
    binding_weight: float = 0.4
    admet_weight: float = 0.3
    stability_weight: float = 0.3

    def __post_init__(self):
        """Load API key from environment if not provided"""
        if self.api_key is None:
            self.api_key = os.getenv("BIOQL_API_KEY", "your_api_key_here")

    @classmethod
    def from_dict(cls, config_dict: dict):
        """Create config from dictionary"""
        return cls(**config_dict)

    def to_dict(self):
        """Convert config to dictionary"""
        return {
            "backend": self.backend,
            "shots": self.shots,
            "qec_enabled": self.qec_enabled,
            "qec_type": self.qec_type,
            "logical_qubits": self.logical_qubits,
            "api_key": self.api_key,
            "api_endpoint": self.api_endpoint,
            "qubits_per_atom": self.qubits_per_atom,
            "max_molecular_weight": self.max_molecular_weight,
            "binding_layers": self.binding_layers,
            "binding_qubits": self.binding_qubits,
            "max_molecular_weight_admet": self.max_molecular_weight_admet,
            "logP_range": self.logP_range,
            "max_h_bond_donors": self.max_h_bond_donors,
            "max_h_bond_acceptors": self.max_h_bond_acceptors,
            "generator_qubits": self.generator_qubits,
            "generator_layers": self.generator_layers,
            "discriminator_qubits": self.discriminator_qubits,
            "md_time_steps": self.md_time_steps,
            "md_timestep": self.md_timestep,
            "trotter_order": self.trotter_order,
            "max_iterations": self.max_iterations,
            "convergence_threshold": self.convergence_threshold,
            "binding_weight": self.binding_weight,
            "admet_weight": self.admet_weight,
            "stability_weight": self.stability_weight,
        }


# Atomic properties for quantum encoding
ATOMIC_PROPERTIES = {
    "H": {"mass": 1.008, "electronegativity": 2.20, "radius": 0.53},
    "C": {"mass": 12.011, "electronegativity": 2.55, "radius": 0.77},
    "N": {"mass": 14.007, "electronegativity": 3.04, "radius": 0.75},
    "O": {"mass": 15.999, "electronegativity": 3.44, "radius": 0.73},
    "F": {"mass": 18.998, "electronegativity": 3.98, "radius": 0.71},
    "P": {"mass": 30.974, "electronegativity": 2.19, "radius": 1.10},
    "S": {"mass": 32.065, "electronegativity": 2.58, "radius": 1.03},
    "Cl": {"mass": 35.453, "electronegativity": 3.16, "radius": 0.99},
    "Br": {"mass": 79.904, "electronegativity": 2.96, "radius": 1.14},
    "I": {"mass": 126.904, "electronegativity": 2.66, "radius": 1.33},
}

# Bond types and their strengths
BOND_TYPES = {"single": 1.0, "double": 2.0, "triple": 3.0, "aromatic": 1.5}

# Quantum circuit depth recommendations
CIRCUIT_DEPTH = {"shallow": 2, "medium": 4, "deep": 8, "very_deep": 16}

# Error mitigation strategies
ERROR_MITIGATION = {
    "none": None,
    "readout": "readout_correction",
    "zne": "zero_noise_extrapolation",
    "cdr": "clifford_data_regression",
}
