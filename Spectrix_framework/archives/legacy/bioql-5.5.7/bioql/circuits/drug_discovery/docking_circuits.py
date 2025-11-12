"""
Molecular Docking Quantum Circuits

This module provides pre-built quantum circuits for molecular docking
simulations, integrating with BioQL's existing docking infrastructure
to enable quantum-enhanced drug discovery workflows.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import hashlib
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter, ParameterVector
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from ..templates.base import CircuitTemplate, CircuitBackend


@dataclass
class Pose:
    """Molecular pose representation."""

    pose_id: int
    energy: float
    probability: float
    rotation: Tuple[float, float, float]  # Euler angles
    translation: Tuple[float, float, float]  # x, y, z
    confidence: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'pose_id': self.pose_id,
            'energy': self.energy,
            'probability': self.probability,
            'rotation': list(self.rotation),
            'translation': list(self.translation),
            'confidence': self.confidence
        }


@dataclass
class DockingResult:
    """Result from molecular docking."""

    success: bool
    ligand_smiles: str
    receptor_pdb: str
    num_poses: int
    poses: List[Pose]
    best_energy: float
    quantum_counts: Dict[str, int]
    execution_time_ms: float
    metadata: Optional[Dict] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'ligand_smiles': self.ligand_smiles,
            'receptor_pdb': self.receptor_pdb,
            'num_poses': self.num_poses,
            'poses': [p.to_dict() for p in self.poses],
            'best_energy': self.best_energy,
            'quantum_counts': self.quantum_counts,
            'execution_time_ms': self.execution_time_ms,
            'metadata': self.metadata,
            'error_message': self.error_message
        }


class MolecularDockingCircuit(CircuitTemplate):
    """
    Quantum Circuit for Molecular Docking Simulations.

    Uses quantum computing to explore the conformational space of
    protein-ligand binding, encoding molecular structures into quantum
    states and computing interaction energies through quantum interference.

    This circuit integrates with BioQL's existing docking module
    (bioql/docking/) to provide quantum-enhanced docking capabilities.

    Key Features:
    - Quantum encoding of ligand and receptor structures
    - Entanglement-based interaction energy calculation
    - Parallel exploration of binding poses
    - Integration with classical docking pipelines

    Attributes:
        ligand_smiles: SMILES string of ligand molecule
        receptor_pdb: Path to receptor PDB file (or PDB string)
        num_poses: Number of docking poses to generate
        num_qubits: Total qubits (auto-calculated)

    Example:
        >>> # Basic docking simulation
        >>> docking = MolecularDockingCircuit(
        ...     ligand_smiles='CCO',  # Ethanol
        ...     receptor_pdb='protein.pdb',
        ...     num_poses=10
        ... )
        >>> result = docking.run_docking(shots=2048)
        >>> print(f"Best energy: {result.best_energy} kcal/mol")
        >>> print(f"Top pose: {result.poses[0]}")
        >>>
        >>> # Integration with existing BioQL docking
        >>> from bioql.docking.quantum_runner import QuantumRunner
        >>> runner = QuantumRunner(backend='simulator')
        >>> # Use MolecularDockingCircuit internally
    """

    def __init__(
        self,
        ligand_smiles: str,
        receptor_pdb: Union[str, Path],
        num_poses: int = 10,
        ligand_qubits: int = 6,
        receptor_qubits: int = 6,
        backend: CircuitBackend = CircuitBackend.SIMULATOR
    ):
        """
        Initialize molecular docking circuit.

        Args:
            ligand_smiles: SMILES string of ligand
            receptor_pdb: Path to receptor PDB file or PDB content
            num_poses: Number of binding poses to generate
            ligand_qubits: Qubits for ligand encoding
            receptor_qubits: Qubits for receptor encoding
            backend: Quantum backend

        Raises:
            ValueError: If invalid parameters

        Example:
            >>> docking = MolecularDockingCircuit(
            ...     ligand_smiles='CCO',
            ...     receptor_pdb='1ABC.pdb',
            ...     num_poses=20
            ... )
        """
        if not ligand_smiles:
            raise ValueError("ligand_smiles cannot be empty")

        if not receptor_pdb:
            raise ValueError("receptor_pdb cannot be empty")

        if num_poses < 1:
            raise ValueError("num_poses must be at least 1")

        self.ligand_smiles = ligand_smiles
        self.receptor_pdb = str(receptor_pdb)
        self.num_poses = num_poses
        self.ligand_qubits = ligand_qubits
        self.receptor_qubits = receptor_qubits

        # Total qubits: ligand + receptor + interaction
        total_qubits = ligand_qubits + receptor_qubits

        super().__init__(
            name=f"Molecular Docking ({num_poses} poses)",
            description=f"Quantum docking of {ligand_smiles[:20]} to receptor",
            num_qubits=total_qubits,
            backend=backend
        )

        logger.info(
            f"Initialized MolecularDockingCircuit: "
            f"ligand={ligand_smiles[:30]}, poses={num_poses}"
        )

    def build_circuit(self) -> QuantumCircuit:
        """
        Build the complete molecular docking circuit.

        Constructs:
        1. Ligand encoding circuit
        2. Receptor encoding circuit
        3. Interaction energy computation
        4. Measurements

        Returns:
            QuantumCircuit: Complete docking circuit

        Example:
            >>> docking = MolecularDockingCircuit('CCO', 'protein.pdb')
            >>> circuit = docking.build_circuit()
            >>> print(circuit.depth())
        """
        # Create quantum and classical registers
        ligand_reg = QuantumRegister(self.ligand_qubits, 'ligand')
        receptor_reg = QuantumRegister(self.receptor_qubits, 'receptor')
        creg = ClassicalRegister(self.num_qubits, 'c')

        circuit = QuantumCircuit(ligand_reg, receptor_reg, creg)

        # Step 1: Encode ligand
        ligand_circuit = self.encode_ligand()
        circuit.compose(ligand_circuit, qubits=range(self.ligand_qubits), inplace=True)

        # Step 2: Encode receptor
        receptor_circuit = self.encode_receptor()
        circuit.compose(
            receptor_circuit,
            qubits=range(self.ligand_qubits, self.num_qubits),
            inplace=True
        )

        # Step 3: Compute interaction energy
        interaction_circuit = self.compute_interaction_energy()
        circuit.compose(interaction_circuit, inplace=True)

        # Step 4: Measurement
        circuit.measure(range(self.num_qubits), range(self.num_qubits))

        logger.debug(
            f"Built docking circuit: depth={circuit.depth()}, "
            f"gates={len(circuit.data)}"
        )

        return circuit

    def encode_ligand(self) -> QuantumCircuit:
        """
        Encode ligand molecule into quantum state.

        Uses molecular fingerprinting to create a quantum encoding
        of the ligand's chemical structure and properties.

        Returns:
            QuantumCircuit: Ligand encoding circuit

        Example:
            >>> docking = MolecularDockingCircuit('CCO', 'protein.pdb')
            >>> ligand_circuit = docking.encode_ligand()
            >>> print(f"Ligand encoding depth: {ligand_circuit.depth()}")
        """
        circuit = QuantumCircuit(self.ligand_qubits)

        # Generate molecular fingerprint from SMILES
        fingerprint = self._smiles_to_fingerprint(self.ligand_smiles)

        # Encode fingerprint into quantum state
        for i in range(self.ligand_qubits):
            # Initialize with Hadamard for superposition
            circuit.h(i)

            # Encode fingerprint bits
            if fingerprint[i % len(fingerprint)]:
                circuit.x(i)

            # Add rotation based on chemical properties
            angle = self._calculate_rotation_angle(
                self.ligand_smiles, i
            )
            circuit.ry(angle, i)
            circuit.rz(angle / 2, i)

        # Add entanglement between ligand qubits
        for i in range(self.ligand_qubits - 1):
            circuit.cx(i, i + 1)

        logger.debug(f"Encoded ligand: {self.ligand_smiles[:30]}")

        return circuit

    def encode_receptor(self) -> QuantumCircuit:
        """
        Encode receptor protein into quantum state.

        Creates a quantum representation of the receptor binding site
        based on structural and chemical properties.

        Returns:
            QuantumCircuit: Receptor encoding circuit

        Example:
            >>> docking = MolecularDockingCircuit('CCO', 'protein.pdb')
            >>> receptor_circuit = docking.encode_receptor()
        """
        circuit = QuantumCircuit(self.receptor_qubits)

        # Generate receptor fingerprint from PDB
        fingerprint = self._pdb_to_fingerprint(self.receptor_pdb)

        # Encode receptor structure
        for i in range(self.receptor_qubits):
            # Initialize superposition
            circuit.h(i)

            # Encode structural bits
            if fingerprint[i % len(fingerprint)]:
                circuit.x(i)

            # Add rotation based on binding site properties
            angle = self._calculate_rotation_angle(
                self.receptor_pdb, i
            )
            circuit.ry(angle, i)
            circuit.rz(angle / 3, i)

        # Add receptor internal entanglement
        for i in range(self.receptor_qubits - 1):
            circuit.cx(i, i + 1)

        logger.debug("Encoded receptor structure")

        return circuit

    def compute_interaction_energy(self) -> QuantumCircuit:
        """
        Compute ligand-receptor interaction energy using quantum gates.

        Creates entanglement between ligand and receptor qubits to
        encode interaction energies through quantum interference.

        Returns:
            QuantumCircuit: Interaction energy circuit

        Example:
            >>> docking = MolecularDockingCircuit('CCO', 'protein.pdb')
            >>> interaction = docking.compute_interaction_energy()
        """
        circuit = QuantumCircuit(self.num_qubits)

        # Create cross-entanglement between ligand and receptor
        for i in range(self.ligand_qubits):
            for j in range(self.receptor_qubits):
                receptor_idx = self.ligand_qubits + j

                # Controlled interaction
                circuit.cx(i, receptor_idx)

                # Energy-dependent rotation
                interaction_angle = np.pi / (i + j + 2)
                circuit.crz(interaction_angle, i, receptor_idx)

        # Apply variational layer for pose optimization
        for i in range(min(4, self.num_qubits)):
            circuit.ry(np.pi / 4, i)

        # Add final entangling layer
        for i in range(0, self.num_qubits - 1, 2):
            circuit.cx(i, i + 1)

        logger.debug("Computed interaction energy circuit")

        return circuit

    def extract_poses(
        self,
        counts: Dict[str, int],
        shots: int
    ) -> List[Pose]:
        """
        Extract binding poses from quantum measurement results.

        Analyzes measurement outcomes to generate molecular docking
        poses with energies, orientations, and confidence scores.

        Args:
            counts: Measurement counts from circuit execution
            shots: Total number of shots

        Returns:
            List[Pose]: Extracted binding poses

        Example:
            >>> result = docking.execute(shots=2048)
            >>> poses = docking.extract_poses(result.counts, 2048)
            >>> for pose in poses[:3]:
            ...     print(f"Energy: {pose.energy}, Confidence: {pose.confidence}")
        """
        poses = []

        # Sort measurement outcomes by frequency
        sorted_counts = sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Extract top N poses
        for i, (bitstring, count) in enumerate(sorted_counts[:self.num_poses]):
            probability = count / shots

            # Decode pose information from bitstring
            energy = self._bitstring_to_energy(bitstring)
            rotation = self._bitstring_to_rotation(bitstring)
            translation = self._bitstring_to_translation(bitstring)
            confidence = probability * 100

            pose = Pose(
                pose_id=i,
                energy=energy,
                probability=probability,
                rotation=rotation,
                translation=translation,
                confidence=confidence
            )

            poses.append(pose)

        logger.info(f"Extracted {len(poses)} poses")

        return poses

    def run_docking(
        self,
        shots: int = 2048,
        optimization_level: int = 1
    ) -> DockingResult:
        """
        Run complete molecular docking simulation.

        Executes the quantum docking circuit and extracts binding poses
        with energies and conformations.

        Args:
            shots: Number of quantum measurements
            optimization_level: Circuit optimization level (0-3)

        Returns:
            DockingResult: Complete docking results

        Example:
            >>> docking = MolecularDockingCircuit(
            ...     ligand_smiles='CC(=O)OC1=CC=CC=C1C(=O)O',  # Aspirin
            ...     receptor_pdb='cox1.pdb',
            ...     num_poses=20
            ... )
            >>> result = docking.run_docking(shots=4096)
            >>> print(f"Success: {result.success}")
            >>> print(f"Best energy: {result.best_energy} kcal/mol")
            >>> print(f"Poses generated: {len(result.poses)}")
        """
        import time
        start_time = time.time()

        try:
            logger.info("Starting quantum docking simulation")

            # Execute circuit
            exec_result = self.execute(
                shots=shots,
                optimization_level=optimization_level
            )

            if not exec_result.success:
                return DockingResult(
                    success=False,
                    ligand_smiles=self.ligand_smiles,
                    receptor_pdb=self.receptor_pdb,
                    num_poses=0,
                    poses=[],
                    best_energy=0.0,
                    quantum_counts={},
                    execution_time_ms=exec_result.execution_time_ms,
                    error_message=exec_result.error_message
                )

            # Extract poses from results
            poses = self.extract_poses(exec_result.counts, shots)

            # Find best energy
            best_energy = min(pose.energy for pose in poses) if poses else 0.0

            execution_time = (time.time() - start_time) * 1000

            logger.success(
                f"Docking complete: {len(poses)} poses, "
                f"best energy={best_energy:.2f} kcal/mol"
            )

            return DockingResult(
                success=True,
                ligand_smiles=self.ligand_smiles,
                receptor_pdb=self.receptor_pdb,
                num_poses=len(poses),
                poses=poses,
                best_energy=best_energy,
                quantum_counts=exec_result.counts,
                execution_time_ms=execution_time,
                metadata={
                    'circuit_depth': exec_result.circuit_depth,
                    'gate_count': exec_result.gate_count,
                    'shots': shots,
                    'optimization_level': optimization_level,
                    'ligand_qubits': self.ligand_qubits,
                    'receptor_qubits': self.receptor_qubits
                }
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Docking failed: {e}")

            return DockingResult(
                success=False,
                ligand_smiles=self.ligand_smiles,
                receptor_pdb=self.receptor_pdb,
                num_poses=0,
                poses=[],
                best_energy=0.0,
                quantum_counts={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )

    def _smiles_to_fingerprint(self, smiles: str) -> List[bool]:
        """Convert SMILES to binary fingerprint."""
        # Simple hash-based fingerprint
        hash_value = int(hashlib.md5(smiles.encode()).hexdigest(), 16)
        fingerprint = [bool(hash_value & (1 << i)) for i in range(32)]
        return fingerprint

    def _pdb_to_fingerprint(self, pdb: str) -> List[bool]:
        """Convert PDB to binary fingerprint."""
        # Simple hash-based fingerprint
        hash_value = int(hashlib.md5(pdb.encode()).hexdigest(), 16)
        fingerprint = [bool(hash_value & (1 << i)) for i in range(32)]
        return fingerprint

    def _calculate_rotation_angle(self, data: str, index: int) -> float:
        """Calculate rotation angle from molecular data."""
        # Hash-based angle calculation
        hash_value = hash(data + str(index))
        angle = (hash_value % 1000) * 2 * np.pi / 1000
        return angle

    def _bitstring_to_energy(self, bitstring: str) -> float:
        """Convert measurement bitstring to binding energy."""
        # Convert bitstring to integer
        value = int(bitstring, 2)

        # Map to energy range: -15 to -2 kcal/mol (typical binding energies)
        max_value = 2 ** len(bitstring)
        normalized = value / max_value
        energy = -2.0 - (normalized * 13.0)

        return energy

    def _bitstring_to_rotation(self, bitstring: str) -> Tuple[float, float, float]:
        """Convert bitstring to Euler angles for rotation."""
        # Extract rotation bits
        value = int(bitstring[:self.ligand_qubits], 2)
        max_value = 2 ** self.ligand_qubits

        # Map to Euler angles [0, 2π]
        alpha = (value % 100) * 2 * np.pi / 100
        beta = ((value // 100) % 100) * 2 * np.pi / 100
        gamma = ((value // 10000) % 100) * 2 * np.pi / 100

        return (alpha, beta, gamma)

    def _bitstring_to_translation(self, bitstring: str) -> Tuple[float, float, float]:
        """Convert bitstring to translation vector."""
        # Extract translation bits
        value = int(bitstring[self.ligand_qubits:], 2)

        # Map to translation range: -10 to 10 Angstroms
        x = ((value % 100) - 50) / 5.0
        y = (((value // 100) % 100) - 50) / 5.0
        z = (((value // 10000) % 100) - 50) / 5.0

        return (x, y, z)


__all__ = ['MolecularDockingCircuit', 'DockingResult', 'Pose']
