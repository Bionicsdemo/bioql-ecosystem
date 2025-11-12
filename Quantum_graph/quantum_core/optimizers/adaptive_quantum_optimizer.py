# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Adaptive Quantum Optimizer for Scientific Visualization
=========================================================

This module implements an intelligent optimization algorithm that automatically
determines the optimal quantum configuration (qubits, shots, circuit depth, QEC)
for computational biology and chemistry visualizations.

Key Features:
- Auto-scales qubits based on molecular complexity
- Optimizes shot count for statistical accuracy
- Selects appropriate QEC codes (Surface, Bacon-Shor, etc.)
- Estimates computational resources and costs
- Integrates with BioQL and Spectrix frameworks

Author: Spectrix R&D / BioQL Team
License: Proprietary
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class MoleculeType(Enum):
    """Types of molecular systems"""

    PROTEIN = "protein"
    DNA = "dna"
    RNA = "rna"
    SMALL_MOLECULE = "small_molecule"
    ANTIBODY = "antibody"
    PROTEIN_COMPLEX = "protein_complex"
    METABOLITE = "metabolite"


class VisualizationType(Enum):
    """Types of scientific visualizations"""

    STRUCTURE_3D = "structure_3d"
    ENERGY_LANDSCAPE = "energy_landscape"
    BINDING_AFFINITY = "binding_affinity"
    CONFORMATIONAL_SAMPLING = "conformational_sampling"
    ELECTRON_DENSITY = "electron_density"
    MOLECULAR_ORBITALS = "molecular_orbitals"
    REACTION_PATHWAY = "reaction_pathway"
    PROTEIN_FOLDING = "protein_folding"
    DOCKING_SIMULATION = "docking_simulation"


@dataclass
class QuantumConfig:
    """Quantum computing configuration"""

    logical_qubits: int
    physical_qubits: int
    shots: int
    circuit_depth: int
    qec_code: str
    gate_fidelity: float
    t_gates: int
    rotation_gates: int
    cnot_gates: int
    time_to_solution_hours: float
    estimated_cost_usd: float
    backend_type: str  # "simulator", "ibm_quantum", "azure_quantum", "aws_braket"


@dataclass
class MolecularComplexity:
    """Molecular complexity metrics"""

    num_atoms: int
    num_bonds: int
    num_residues: int  # For proteins
    molecular_weight: float
    num_electrons: int
    num_heavy_atoms: int
    rotatable_bonds: int
    conformational_space_size: float  # Log10 of conformation count


class AdaptiveQuantumOptimizer:
    """
    Intelligent optimizer that determines optimal quantum parameters
    for molecular visualization and simulation tasks.
    """

    def __init__(
        self,
        budget_usd: Optional[float] = None,
        max_time_hours: Optional[float] = None,
        accuracy_target: float = 0.95,
    ):
        """
        Initialize the optimizer

        Args:
            budget_usd: Maximum budget for computation
            max_time_hours: Maximum time allowed for computation
            accuracy_target: Target accuracy (0-1)
        """
        self.budget_usd = budget_usd
        self.max_time_hours = max_time_hours
        self.accuracy_target = accuracy_target

        # Quantum hardware parameters (based on current state-of-the-art)
        self.ibm_qubit_fidelity = 0.9995  # IBM Quantum Eagle
        self.azure_qubit_fidelity = 0.9998  # Azure Quantum
        self.aws_qubit_fidelity = 0.9993  # AWS Braket

        # Surface code parameters
        self.surface_code_distance_min = 3
        self.surface_code_distance_max = 25

        # Cost models (USD per shot) - Updated pricing
        self.cost_per_shot = {
            # Simulators
            "ionq_simulator": 0.01,
            "aws_sv1": 0.01,
            "aws_tn1": 0.02,
            "simulator": 0.01,  # Default simulator
            # Quantum Hardware
            "ibm_torino": 3.00,
            "ibm_brisbane": 3.00,
            "ionq_forte": 3.00,
            "ionq_qpu": 2.00,
            "quera_aquila": 5.00,
            # Aliases for backward compatibility
            "ibm_quantum": 3.00,
            "azure_quantum": 3.00,
            "aws_braket": 2.00,
        }

        # Backend qubit limits
        self.backend_qubit_limits = {
            "ionq_simulator": 29,
            "aws_sv1": 34,
            "aws_tn1": 50,
            "ibm_torino": 133,
            "ibm_brisbane": 127,
            "ionq_forte": 36,
            "ionq_qpu": 36,
            "quera_aquila": 256,
        }

    def estimate_molecular_complexity(
        self, molecule_data: Dict[str, Any], molecule_type: MoleculeType
    ) -> MolecularComplexity:
        """
        Estimate molecular complexity from input data

        Args:
            molecule_data: Dictionary with molecular information
            molecule_type: Type of molecule

        Returns:
            MolecularComplexity object
        """
        num_atoms = molecule_data.get("num_atoms", 0)

        # Estimate other properties if not provided
        if molecule_type == MoleculeType.PROTEIN:
            num_residues = molecule_data.get("num_residues", num_atoms // 10)
            num_bonds = int(num_atoms * 1.2)
            num_electrons = num_atoms * 6  # Average for protein atoms
            molecular_weight = num_residues * 110  # Average residue weight
            rotatable_bonds = num_residues * 4
            conformational_space = math.log10(3**rotatable_bonds)

        elif molecule_type == MoleculeType.DNA:
            num_residues = molecule_data.get("num_base_pairs", num_atoms // 30)
            num_bonds = int(num_atoms * 1.1)
            num_electrons = num_atoms * 7
            molecular_weight = num_residues * 330  # Average base pair weight
            rotatable_bonds = num_residues * 6
            conformational_space = math.log10(3**rotatable_bonds)

        elif molecule_type == MoleculeType.ANTIBODY:
            num_residues = molecule_data.get("num_residues", 1300)  # ~150 kDa
            num_bonds = int(num_atoms * 1.2)
            num_electrons = num_atoms * 6
            molecular_weight = num_residues * 110
            rotatable_bonds = num_residues * 4
            conformational_space = math.log10(3**rotatable_bonds)

        else:  # Small molecule, metabolite
            num_residues = 0
            num_bonds = molecule_data.get("num_bonds", int(num_atoms * 1.1))
            num_electrons = molecule_data.get("num_electrons", num_atoms * 6)
            molecular_weight = molecule_data.get("molecular_weight", num_atoms * 15)
            rotatable_bonds = molecule_data.get("rotatable_bonds", max(1, num_atoms // 5))
            conformational_space = math.log10(3**rotatable_bonds) if rotatable_bonds > 0 else 1.0

        num_heavy_atoms = int(num_atoms * 0.85)  # Estimate ~85% non-hydrogen

        return MolecularComplexity(
            num_atoms=num_atoms,
            num_bonds=num_bonds,
            num_residues=num_residues,
            molecular_weight=molecular_weight,
            num_electrons=num_electrons,
            num_heavy_atoms=num_heavy_atoms,
            rotatable_bonds=rotatable_bonds,
            conformational_space_size=conformational_space,
        )

    def calculate_required_qubits(
        self, complexity: MolecularComplexity, viz_type: VisualizationType
    ) -> int:
        """
        Calculate the number of logical qubits needed

        Uses heuristics based on:
        - Electronic structure: log2(basis_functions)
        - Conformational sampling: log2(conformations)
        - Binding calculations: combination of both

        Args:
            complexity: Molecular complexity metrics
            viz_type: Type of visualization

        Returns:
            Number of logical qubits required
        """
        if viz_type == VisualizationType.ELECTRON_DENSITY:
            # Need qubits for molecular orbitals
            # Rule of thumb: 1 qubit per 2 electrons for active space
            active_electrons = min(complexity.num_electrons, 50)  # Active space approximation
            qubits = math.ceil(active_electrons / 2)

        elif viz_type == VisualizationType.MOLECULAR_ORBITALS:
            # Full molecular orbital calculation
            # Scaling: log2(basis_functions) where basis ~ 4 * num_heavy_atoms
            basis_functions = max(1, complexity.num_heavy_atoms * 4)
            qubits = math.ceil(math.log2(basis_functions)) + 5  # +5 for ancillas

        elif viz_type == VisualizationType.CONFORMATIONAL_SAMPLING:
            # Need to sample conformational space
            # Qubits ~ log2(conformations)
            qubits = math.ceil(complexity.conformational_space_size / math.log10(2)) + 3

        elif viz_type == VisualizationType.BINDING_AFFINITY:
            # Combined protein-ligand system
            total_electrons = complexity.num_electrons
            active_space = min(total_electrons, 100)
            qubits = math.ceil(active_space / 2) + 10  # +10 for binding site representation

        elif viz_type == VisualizationType.ENERGY_LANDSCAPE:
            # Sampling energy surface
            qubits = math.ceil(math.log2(max(1, complexity.num_atoms))) + 8

        elif viz_type == VisualizationType.PROTEIN_FOLDING:
            # Protein folding simulation
            qubits = math.ceil(math.log2(max(1, complexity.num_residues))) + 12

        elif viz_type == VisualizationType.REACTION_PATHWAY:
            # Reaction coordinate calculation
            qubits = math.ceil(complexity.num_heavy_atoms / 3) + 8

        elif viz_type == VisualizationType.DOCKING_SIMULATION:
            # Molecular docking
            qubits = math.ceil(math.log2(max(1, complexity.rotatable_bonds))) + 15

        else:  # STRUCTURE_3D - basic visualization
            qubits = math.ceil(math.log2(max(1, complexity.num_atoms))) + 5

        # Clamp to reasonable range
        return max(4, min(qubits, 200))

    def calculate_required_shots(
        self, logical_qubits: int, accuracy_target: float, measurement_basis: int = 100
    ) -> int:
        """
        Calculate optimal number of shots for statistical accuracy

        Uses quantum statistical theory:
        σ² = 1/N_shots for measurement uncertainty

        Args:
            logical_qubits: Number of logical qubits
            accuracy_target: Target accuracy (0-1)
            measurement_basis: Number of measurement bases

        Returns:
            Optimal number of shots
        """
        # Standard quantum measurement uncertainty
        # For accuracy ε, need shots ~ 1/ε²
        base_shots = int(1 / ((1 - accuracy_target) ** 2))

        # Scale with number of qubits (more qubits = more shots for same accuracy)
        qubit_scaling_factor = math.sqrt(logical_qubits)

        # Scale with measurement bases
        basis_scaling_factor = math.sqrt(measurement_basis)

        total_shots = int(base_shots * qubit_scaling_factor * basis_scaling_factor)

        # Round to nice numbers
        if total_shots < 1000:
            shots = 1000
        elif total_shots < 10000:
            shots = (total_shots // 1000) * 1000
        else:
            shots = (total_shots // 10000) * 10000

        # Clamp to reasonable range
        return max(1000, min(shots, 10000000))

    def select_qec_code(
        self, logical_qubits: int, target_error_rate: float, backend_fidelity: float
    ) -> Tuple[str, int, int]:
        """
        Select optimal QEC code and calculate physical qubits

        Args:
            logical_qubits: Number of logical qubits needed
            target_error_rate: Target logical error rate
            backend_fidelity: Physical gate fidelity

        Returns:
            (qec_code_name, code_distance, physical_qubits)
        """
        # Calculate required code distance for Surface Code
        # Error rate scales as (p/p_th)^((d+1)/2) where p_th ~ 0.01
        physical_error = 1 - backend_fidelity
        threshold = 0.01

        if physical_error >= threshold:
            # Need better hardware or different approach
            code_distance = self.surface_code_distance_max
        else:
            # Calculate distance needed
            ratio = physical_error / threshold

            # Validate inputs to avoid math domain errors
            if ratio <= 0 or ratio >= 1 or target_error_rate <= 0 or target_error_rate >= 1:
                code_distance = self.surface_code_distance_min
            else:
                try:
                    exponent = math.log(target_error_rate) / math.log(ratio)
                    code_distance = max(self.surface_code_distance_min, int(2 * exponent - 1))
                    code_distance = min(code_distance, self.surface_code_distance_max)
                except (ValueError, ZeroDivisionError):
                    # Fallback to minimum distance if calculation fails
                    code_distance = self.surface_code_distance_min

        # Ensure odd distance (required for surface codes)
        if code_distance % 2 == 0:
            code_distance += 1

        # Physical qubits for surface code: 2*d²
        physical_qubits_per_logical = 2 * (code_distance**2)
        total_physical_qubits = logical_qubits * physical_qubits_per_logical

        # Add ancilla qubits (~20% overhead)
        total_physical_qubits = int(total_physical_qubits * 1.2)

        qec_code = f"Surface-{code_distance}"

        return qec_code, code_distance, total_physical_qubits

    def estimate_circuit_complexity(
        self, logical_qubits: int, viz_type: VisualizationType, complexity: MolecularComplexity
    ) -> Dict[str, int]:
        """
        Estimate gate counts for the quantum circuit

        Args:
            logical_qubits: Number of logical qubits
            viz_type: Visualization type
            complexity: Molecular complexity

        Returns:
            Dict with gate counts
        """
        # Base gate counts (heuristic models)
        if viz_type == VisualizationType.ELECTRON_DENSITY:
            # VQE-like circuit
            depth = logical_qubits * 20
            t_gates = logical_qubits**2 * 10
            rotation_gates = logical_qubits * 30
            cnot_gates = logical_qubits**2 * 5

        elif viz_type == VisualizationType.CONFORMATIONAL_SAMPLING:
            # QAOA-like circuit
            depth = logical_qubits * 15
            t_gates = logical_qubits * 20
            rotation_gates = logical_qubits * 40
            cnot_gates = logical_qubits * 30

        elif viz_type == VisualizationType.BINDING_AFFINITY:
            # Quantum annealing simulation
            depth = logical_qubits * 25
            t_gates = logical_qubits**2 * 15
            rotation_gates = logical_qubits * 50
            cnot_gates = logical_qubits**2 * 8

        else:
            # Generic quantum circuit
            depth = logical_qubits * 10
            t_gates = logical_qubits * 15
            rotation_gates = logical_qubits * 25
            cnot_gates = logical_qubits * 20

        return {
            "depth": depth,
            "t_gates": t_gates,
            "rotation_gates": rotation_gates,
            "cnot_gates": cnot_gates,
            "total_gates": t_gates + rotation_gates + cnot_gates,
        }

    def estimate_runtime_and_cost(
        self,
        physical_qubits: int,
        shots: int,
        circuit_depth: int,
        code_distance: int,
        backend: str = "ibm_quantum",
    ) -> Tuple[float, float]:
        """
        Estimate time to solution and computational cost

        Args:
            physical_qubits: Number of physical qubits
            shots: Number of measurement shots
            circuit_depth: Circuit depth
            code_distance: QEC code distance
            backend: Quantum backend type

        Returns:
            (time_hours, cost_usd)
        """
        # QEC cycle time (microseconds) - time for one syndrome measurement
        qec_cycle_time_us = 1.0  # Modern systems ~1 μs

        # Logical gate time = code_distance * qec_cycle_time
        logical_gate_time_us = code_distance * qec_cycle_time_us

        # Circuit execution time
        circuit_time_us = circuit_depth * logical_gate_time_us

        # Total time for all shots
        total_time_us = shots * circuit_time_us

        # Convert to hours
        time_hours = total_time_us / (1e6 * 3600)

        # Add overhead for compilation, initialization, readout
        time_hours *= 1.5

        # Cost calculation (per-shot pricing model)
        if backend in ["simulator", "ionq_simulator", "aws_sv1", "aws_tn1"]:
            # Simulators charge per shot
            cost_per_shot = self.cost_per_shot.get(backend, 0.01)
            cost_usd = (shots / 1000) * (cost_per_shot * 1000)  # Price is per 1000 shots
        else:
            # Quantum hardware charges per shot
            cost_per_shot = self.cost_per_shot.get(backend, 3.0)
            cost_usd = (shots / 1000) * (cost_per_shot * 1000)

        return time_hours, cost_usd

    def optimize(
        self,
        molecule_data: Dict[str, Any],
        molecule_type: MoleculeType,
        viz_type: VisualizationType,
        backend_preference: str = "auto",
    ) -> QuantumConfig:
        """
        Main optimization function - determines optimal quantum configuration

        Args:
            molecule_data: Molecular structure information
            molecule_type: Type of molecule
            viz_type: Type of visualization
            backend_preference: "auto", "simulator", "ibm_quantum", "azure_quantum", "aws_braket"

        Returns:
            Optimized QuantumConfig
        """
        # Step 1: Analyze molecular complexity
        complexity = self.estimate_molecular_complexity(molecule_data, molecule_type)

        # Step 2: Calculate required logical qubits
        logical_qubits = self.calculate_required_qubits(complexity, viz_type)

        # Step 3: Calculate required shots
        shots = self.calculate_required_shots(logical_qubits, self.accuracy_target)

        # Step 4: Select backend
        if backend_preference == "auto":
            # Auto-select based on problem size and constraints
            if logical_qubits <= 10:
                backend = "simulator"
            elif self.budget_usd and self.budget_usd < 100:
                backend = "simulator"
            elif self.max_time_hours and self.max_time_hours < 1:
                backend = "ibm_quantum"  # Fastest real hardware
            else:
                backend = "azure_quantum"  # Best quality
        else:
            backend = backend_preference

        # Step 5: Get backend fidelity
        backend_fidelity = {
            "simulator": 1.0,
            "ibm_quantum": self.ibm_qubit_fidelity,
            "azure_quantum": self.azure_qubit_fidelity,
            "aws_braket": self.aws_qubit_fidelity,
        }.get(backend, 0.999)

        # Step 6: Select QEC code and calculate physical qubits
        target_error = 1 - self.accuracy_target
        qec_code, code_distance, physical_qubits = self.select_qec_code(
            logical_qubits, target_error, backend_fidelity
        )

        # For simulator, no QEC overhead
        if backend == "simulator":
            physical_qubits = logical_qubits
            qec_code = "None"
            code_distance = 1

        # Step 7: Estimate circuit complexity
        circuit_stats = self.estimate_circuit_complexity(logical_qubits, viz_type, complexity)

        # Step 8: Estimate runtime and cost
        time_hours, cost_usd = self.estimate_runtime_and_cost(
            physical_qubits, shots, circuit_stats["depth"], code_distance, backend
        )

        # Step 9: Check constraints and adjust if needed
        if self.budget_usd and cost_usd > self.budget_usd:
            # Reduce shots to fit budget
            cost_ratio = self.budget_usd / cost_usd
            shots = int(shots * cost_ratio)
            shots = max(1000, shots)
            time_hours, cost_usd = self.estimate_runtime_and_cost(
                physical_qubits, shots, circuit_stats["depth"], code_distance, backend
            )

        if self.max_time_hours and time_hours > self.max_time_hours:
            # Switch to simulator if too slow
            if backend != "simulator":
                backend = "simulator"
                physical_qubits = logical_qubits
                qec_code = "None"
                time_hours, cost_usd = self.estimate_runtime_and_cost(
                    physical_qubits, shots, circuit_stats["depth"], 1, backend
                )

        # Create configuration
        config = QuantumConfig(
            logical_qubits=logical_qubits,
            physical_qubits=physical_qubits,
            shots=shots,
            circuit_depth=circuit_stats["depth"],
            qec_code=qec_code,
            gate_fidelity=backend_fidelity,
            t_gates=circuit_stats["t_gates"],
            rotation_gates=circuit_stats["rotation_gates"],
            cnot_gates=circuit_stats["cnot_gates"],
            time_to_solution_hours=time_hours,
            estimated_cost_usd=cost_usd,
            backend_type=backend,
        )

        return config

    def get_optimization_report(
        self, config: QuantumConfig, complexity: MolecularComplexity
    ) -> str:
        """
        Generate human-readable optimization report

        Args:
            config: Quantum configuration
            complexity: Molecular complexity

        Returns:
            Formatted report string
        """
        report = f"""
╔═══════════════════════════════════════════════════════════════╗
║        QUANTUM VISUALIZATION OPTIMIZATION REPORT              ║
╠═══════════════════════════════════════════════════════════════╣
║ MOLECULAR SYSTEM                                              ║
╠═══════════════════════════════════════════════════════════════╣
║ Atoms:              {complexity.num_atoms:>6}                              ║
║ Heavy Atoms:        {complexity.num_heavy_atoms:>6}                              ║
║ Electrons:          {complexity.num_electrons:>6}                              ║
║ Molecular Weight:   {complexity.molecular_weight:>10.2f} Da                    ║
║ Rotatable Bonds:    {complexity.rotatable_bonds:>6}                              ║
║ Conformations:      ~10^{complexity.conformational_space_size:>.1f}                          ║
╠═══════════════════════════════════════════════════════════════╣
║ QUANTUM CONFIGURATION                                         ║
╠═══════════════════════════════════════════════════════════════╣
║ Logical Qubits:     {config.logical_qubits:>6}                              ║
║ Physical Qubits:    {config.physical_qubits:>6}                              ║
║ QEC Code:           {config.qec_code:<15}                      ║
║ Gate Fidelity:      {config.gate_fidelity:>6.4f}                            ║
║ Measurement Shots:  {config.shots:>10}                          ║
╠═══════════════════════════════════════════════════════════════╣
║ CIRCUIT COMPLEXITY                                            ║
╠═══════════════════════════════════════════════════════════════╣
║ Circuit Depth:      {config.circuit_depth:>10}                          ║
║ T Gates:            {config.t_gates:>10}                          ║
║ Rotation Gates:     {config.rotation_gates:>10}                          ║
║ CNOT Gates:         {config.cnot_gates:>10}                          ║
╠═══════════════════════════════════════════════════════════════╣
║ RESOURCE ESTIMATES                                            ║
╠═══════════════════════════════════════════════════════════════╣
║ Backend:            {config.backend_type:<20}                 ║
║ Time to Solution:   {config.time_to_solution_hours:>10.4f} hours                ║
║ Estimated Cost:     ${config.estimated_cost_usd:>10.2f} USD                   ║
╚═══════════════════════════════════════════════════════════════╝
"""
        return report


# Example usage
if __name__ == "__main__":
    # Example: Protein structure visualization
    optimizer = AdaptiveQuantumOptimizer(
        budget_usd=500.0, max_time_hours=24.0, accuracy_target=0.95
    )

    # Antibody molecule
    antibody_data = {"num_atoms": 10000, "num_residues": 1300, "molecular_weight": 150000}

    config = optimizer.optimize(
        molecule_data=antibody_data,
        molecule_type=MoleculeType.ANTIBODY,
        viz_type=VisualizationType.STRUCTURE_3D,
        backend_preference="auto",
    )

    complexity = optimizer.estimate_molecular_complexity(antibody_data, MoleculeType.ANTIBODY)
    print(optimizer.get_optimization_report(config, complexity))
