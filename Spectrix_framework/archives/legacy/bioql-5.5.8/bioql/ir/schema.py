"""
BioQL Intermediate Representation (IR) Schema

This module defines the core IR schema for BioQL operations using Pydantic.
The IR serves as the bridge between natural language and quantum backends.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class BioQLDomain(str, Enum):
    """Supported BioQL computational domains."""

    DOCKING = "docking"
    ALIGNMENT = "alignment"
    FOLDING = "folding"
    OPTIMIZATION = "optimization"
    SIMULATION = "simulation"


class QuantumBackend(str, Enum):
    """Supported quantum computing backends."""

    QISKIT = "qiskit"
    CIRQ = "cirq"
    PENNYLANE = "pennylane"
    BRAKET = "braket"
    SIMULATOR = "simulator"


class DataType(str, Enum):
    """Data types in BioQL IR."""

    PROTEIN = "protein"
    LIGAND = "ligand"
    DNA = "dna"
    RNA = "rna"
    COMPLEX = "complex"
    ENERGY = "energy"
    COORDINATE = "coordinate"


class QuantumGate(str, Enum):
    """Standard quantum gates supported in BioQL."""

    H = "h"          # Hadamard
    X = "x"          # Pauli-X
    Y = "y"          # Pauli-Y
    Z = "z"          # Pauli-Z
    CNOT = "cnot"    # Controlled-NOT
    CZ = "cz"        # Controlled-Z
    RX = "rx"        # Rotation-X
    RY = "ry"        # Rotation-Y
    RZ = "rz"        # Rotation-Z
    MEASURE = "measure"


class BioQLParameter(BaseModel):
    """Parameter definition for BioQL operations."""

    name: str = Field(..., description="Parameter name")
    value: Union[int, float, str, bool, List[float]] = Field(..., description="Parameter value")
    unit: Optional[str] = Field(None, description="Physical unit")
    description: Optional[str] = Field(None, description="Parameter description")


class Molecule(BaseModel):
    """Molecular structure representation."""

    id: str = Field(..., description="Unique molecule identifier")
    type: DataType = Field(..., description="Molecule type")
    format: Literal["pdb", "smiles", "sdf", "mol2", "fasta"] = Field(..., description="Molecular format")
    data: str = Field(..., description="Molecular data (file path or inline data)")
    name: Optional[str] = Field(None, description="Human-readable molecule name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional molecular properties")


class QuantumCircuit(BaseModel):
    """Quantum circuit representation in BioQL IR."""

    num_qubits: int = Field(..., ge=1, description="Number of qubits")
    gates: List[Dict[str, Any]] = Field(default_factory=list, description="Quantum gates")
    measurements: List[int] = Field(default_factory=list, description="Measured qubits")
    parameters: List[BioQLParameter] = Field(default_factory=list, description="Circuit parameters")

    def add_gate(
        self,
        gate: QuantumGate,
        qubits: List[int],
        params: Optional[List[float]] = None
    ) -> None:
        """Add a quantum gate to the circuit."""
        gate_dict = {
            "gate": gate.value,
            "qubits": qubits,
            "params": params or []
        }
        self.gates.append(gate_dict)

    def add_measurement(self, qubit: int) -> None:
        """Add a measurement to the circuit."""
        if qubit not in self.measurements:
            self.measurements.append(qubit)


class BioQLOperation(BaseModel):
    """Base class for BioQL operations."""

    id: UUID = Field(default_factory=uuid4, description="Unique operation ID")
    domain: BioQLDomain = Field(..., description="Computational domain")
    operation_type: str = Field(..., description="Specific operation type")
    description: Optional[str] = Field(None, description="Operation description")
    parameters: List[BioQLParameter] = Field(default_factory=list, description="Operation parameters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DockingOperation(BioQLOperation):
    """Molecular docking operation."""

    domain: Literal[BioQLDomain.DOCKING] = BioQLDomain.DOCKING
    operation_type: Literal["dock"] = "dock"

    receptor: Molecule = Field(..., description="Receptor molecule (usually protein)")
    ligand: Molecule = Field(..., description="Ligand molecule")
    binding_site: Optional[Dict[str, Any]] = Field(None, description="Binding site specification")
    scoring_function: str = Field(default="vina", description="Scoring function to use")
    num_poses: int = Field(default=10, ge=1, le=100, description="Number of poses to generate")
    energy_threshold: float = Field(default=-6.0, description="Energy threshold for poses")


class AlignmentOperation(BioQLOperation):
    """Sequence alignment operation."""

    domain: Literal[BioQLDomain.ALIGNMENT] = BioQLDomain.ALIGNMENT
    operation_type: Literal["align"] = "align"

    sequences: List[Molecule] = Field(..., min_items=2, description="Sequences to align")
    algorithm: str = Field(default="needleman_wunsch", description="Alignment algorithm")
    gap_penalty: float = Field(default=-1.0, description="Gap penalty")
    match_score: float = Field(default=2.0, description="Match score")
    mismatch_penalty: float = Field(default=-1.0, description="Mismatch penalty")


class QuantumOptimizationOperation(BioQLOperation):
    """Quantum optimization operation."""

    domain: Literal[BioQLDomain.OPTIMIZATION] = BioQLDomain.OPTIMIZATION
    operation_type: Literal["optimize"] = "optimize"

    objective_function: str = Field(..., description="Objective function to optimize")
    variables: List[BioQLParameter] = Field(..., description="Optimization variables")
    constraints: List[str] = Field(default_factory=list, description="Optimization constraints")
    algorithm: str = Field(default="qaoa", description="Quantum optimization algorithm")
    max_iterations: int = Field(default=100, ge=1, description="Maximum iterations")


class BioQLProgram(BaseModel):
    """Complete BioQL program representation."""

    id: UUID = Field(default_factory=uuid4, description="Unique program ID")
    name: str = Field(..., description="Program name")
    description: Optional[str] = Field(None, description="Program description")
    version: str = Field(default="1.0.0", description="Program version")

    # Input specifications
    inputs: List[Molecule] = Field(default_factory=list, description="Input molecules")
    operations: List[Union[DockingOperation, AlignmentOperation, QuantumOptimizationOperation]] = Field(
        ..., description="List of operations to perform"
    )

    # Quantum circuit (if applicable)
    quantum_circuit: Optional[QuantumCircuit] = Field(None, description="Quantum circuit")

    # Execution configuration
    backend: QuantumBackend = Field(default=QuantumBackend.SIMULATOR, description="Target backend")
    shots: int = Field(default=1000, ge=1, description="Number of shots for quantum execution")
    optimization_level: int = Field(default=1, ge=0, le=3, description="Circuit optimization level")

    # Output specifications
    output_format: str = Field(default="json", description="Output format")
    output_path: Optional[str] = Field(None, description="Output file path")

    # Compliance and audit
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list, description="Audit trail")

    @validator('operations')
    def validate_operations(cls, v):
        """Validate that operations are not empty."""
        if not v:
            raise ValueError("At least one operation must be specified")
        return v

    def to_json_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for this program."""
        return self.schema()

    def to_json(self, **kwargs) -> str:
        """Serialize to JSON string."""
        return self.json(**kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> BioQLProgram:
        """Deserialize from JSON string."""
        return cls.parse_raw(json_str)

    def add_audit_entry(self, action: str, details: Dict[str, Any]) -> None:
        """Add entry to audit trail."""
        import datetime

        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "details": details
        }
        self.audit_trail.append(entry)


class BioQLResult(BaseModel):
    """Result of BioQL program execution."""

    program_id: UUID = Field(..., description="ID of executed program")
    execution_id: UUID = Field(default_factory=uuid4, description="Unique execution ID")
    status: Literal["success", "failed", "partial"] = Field(..., description="Execution status")

    # Results
    results: Dict[str, Any] = Field(default_factory=dict, description="Execution results")
    output_files: List[str] = Field(default_factory=list, description="Generated output files")

    # Performance metrics
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    quantum_time: Optional[float] = Field(None, description="Quantum execution time")
    memory_usage: Optional[float] = Field(None, description="Peak memory usage in MB")

    # Quantum metrics
    circuit_depth: Optional[int] = Field(None, description="Final circuit depth")
    gate_count: Optional[int] = Field(None, description="Total gate count")
    shots_executed: Optional[int] = Field(None, description="Actual shots executed")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_type: Optional[str] = Field(None, description="Error type")
    stack_trace: Optional[str] = Field(None, description="Stack trace for debugging")

    # Compliance
    execution_timestamp: Optional[str] = Field(None, description="Execution timestamp")
    backend_used: Optional[QuantumBackend] = Field(None, description="Backend actually used")
    version_info: Dict[str, str] = Field(default_factory=dict, description="Version information")


# Export main classes for easy importing
__all__ = [
    "BioQLDomain",
    "QuantumBackend",
    "DataType",
    "QuantumGate",
    "BioQLParameter",
    "Molecule",
    "QuantumCircuit",
    "BioQLOperation",
    "DockingOperation",
    "AlignmentOperation",
    "QuantumOptimizationOperation",
    "BioQLProgram",
    "BioQLResult"
]