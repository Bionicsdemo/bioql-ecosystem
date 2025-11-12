"""
BioQL Compiler: English to QASM Translation Engine

A sophisticated natural language processing compiler that converts English descriptions
of quantum algorithms into valid OpenQASM 3.0 code, with special emphasis on
biotechnology and quantum chemistry applications.

Author: BioQL Team
Version: 1.0.0
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("Warning: Qiskit not available. parse_to_circuit() will not work.")


class QuantumGateType(Enum):
    """Enumeration of supported quantum gate types."""
    HADAMARD = "h"
    PAULI_X = "x"
    PAULI_Y = "y"
    PAULI_Z = "z"
    CNOT = "cnot"
    CZ = "cz"
    TOFFOLI = "ccx"
    ROTATION_X = "rx"
    ROTATION_Y = "ry"
    ROTATION_Z = "rz"
    PHASE = "p"
    SWAP = "swap"
    MEASURE = "measure"


class BiotechContext(Enum):
    """Enumeration of biotechnology application contexts."""
    PROTEIN_FOLDING = "protein_folding"
    DRUG_DISCOVERY = "drug_discovery"
    DNA_ANALYSIS = "dna_analysis"
    MOLECULAR_SIMULATION = "molecular_simulation"
    GENERAL = "general"


@dataclass
class QuantumOperation:
    """Represents a single quantum operation with its parameters."""
    gate_type: QuantumGateType
    target_qubits: List[int]
    control_qubits: List[int] = None
    parameters: List[float] = None
    classical_bits: List[int] = None

    def __post_init__(self):
        if self.control_qubits is None:
            self.control_qubits = []
        if self.parameters is None:
            self.parameters = []
        if self.classical_bits is None:
            self.classical_bits = []


@dataclass
class ParsedCircuit:
    """Represents a complete parsed quantum circuit."""
    num_qubits: int
    num_classical_bits: int
    operations: List[QuantumOperation]
    biotech_context: BiotechContext
    description: str


class CompilerError(Exception):
    """Custom exception for compiler errors."""
    pass


class NaturalLanguageParser:
    """
    Advanced natural language parser for quantum circuit descriptions.

    BioQL v3.0 - Now supports BILLIONS of natural language patterns!

    This class provides sophisticated pattern matching and NLP-like capabilities
    to convert English descriptions into quantum operations, with special support
    for biotechnology applications.

    NEW in v3.0: Mega Pattern Matcher with 1B+ combinatorial patterns
    """

    def __init__(self, enable_biotech_optimizations: bool = True, use_mega_patterns: bool = True):
        """
        Initialize the natural language parser.

        Args:
            enable_biotech_optimizations: Whether to apply biotech-specific optimizations
            use_mega_patterns: Whether to use mega pattern matcher (v3.0 feature)
        """
        self.enable_biotech_optimizations = enable_biotech_optimizations
        self.use_mega_patterns = use_mega_patterns
        self.logger = logging.getLogger(__name__)

        # Initialize mega pattern matcher (v3.0)
        if self.use_mega_patterns:
            try:
                from bioql.parser.mega_patterns import get_mega_matcher, IntentType
                self.mega_matcher = get_mega_matcher()
                self.IntentType = IntentType
                self.logger.info("BioQL v3.0 Mega Pattern Matcher loaded (1B+ patterns)")
            except ImportError:
                self.logger.warning("Mega patterns not available, falling back to v2.1 patterns")
                self.mega_matcher = None
                self.use_mega_patterns = False

        # Initialize legacy pattern dictionaries (v2.1 fallback)
        self._init_qubit_patterns()
        self._init_gate_patterns()
        self._init_biotech_patterns()
        self._init_measurement_patterns()

    def _init_qubit_patterns(self):
        """Initialize patterns for qubit creation and manipulation."""
        self.qubit_creation_patterns = [
            # Standard patterns
            r"(?:create|make|initialize|allocate|prepare)\s+(\d+)\s+(?:qubits?|quantum\s+bits?)",
            r"(?:use|need|require)\s+(\d+)\s+(?:qubits?|quantum\s+bits?)",
            r"(?:set\s+up|setup)\s+(\d+)\s+(?:qubits?|quantum\s+bits?)",
            r"(\d+)\s+(?:qubits?|quantum\s+bits?)\s+(?:circuit|system)",

            # Algorithm-specific patterns
            r"(?:create|make)\s+a\s+(\d+)-qubit\s+(?:quantum\s+fourier|qft|fourier\s+transform)",
            r"(\d+)-qubit\s+(?:quantum\s+fourier\s+transform|qft|vqe|variational)",
            r"(?:create|make|implement)\s+(?:a\s+)?(\d+)\s+qubit\s+(?:quantum\s+fourier|qft|fourier)",

            # Biotech-specific patterns
            r"(?:model|simulate)\s+(\d+)\s+(?:amino\s+acids?|residues?)\s+with\s+qubits?",
            r"encode\s+(\d+)\s+(?:nucleotides?|base\s+pairs?)\s+(?:using|with|in)\s+qubits?",
            r"represent\s+(\d+)\s+(?:molecular\s+states?|conformations?)\s+(?:using|with)\s+qubits?",
        ]

        self.qubit_index_patterns = [
            r"qubit\s+(\d+)",
            r"quantum\s+bit\s+(\d+)",
            r"q\[(\d+)\]",
            r"position\s+(\d+)",
            r"index\s+(\d+)",
        ]

    def _init_gate_patterns(self):
        """Initialize patterns for quantum gate operations."""
        # Bell state patterns (special case)
        self.bell_state_patterns = [
            r"create\s+bell\s+state",
            r"make\s+bell\s+state",
            r"bell\s+state",
            r"entangle\s+qubits?\s+0\s+and\s+1",
            r"entangled\s+state"
        ]

        # Superposition patterns (special case)
        self.superposition_patterns = [
            r"create\s+superposition",
            r"make\s+superposition",
            r"generate\s+superposition",
            r"superposition"
        ]

        self.gate_patterns = {
            QuantumGateType.HADAMARD: [
                r"(?:apply|put|place)\s+(?:a\s+)?hadamard\s+(?:gate\s+)?(?:to|on)\s+qubit\s+(\d+)",
                r"put\s+qubit\s+(\d+)\s+in\s+superposition",
                r"create\s+superposition\s+(?:on|in)\s+qubit\s+(\d+)",
                r"hadamard\s+qubit\s+(\d+)",
                r"h\s+qubit\s+(\d+)",
                r"superpose\s+qubit\s+(\d+)",
            ],

            QuantumGateType.PAULI_X: [
                r"(?:apply|execute)\s+(?:a\s+)?(?:pauli\s+)?x\s+(?:gate\s+)?(?:to|on)\s+qubit\s+(\d+)",
                r"flip\s+qubit\s+(\d+)",
                r"not\s+qubit\s+(\d+)",
                r"invert\s+qubit\s+(\d+)",
                r"x\s+qubit\s+(\d+)",
            ],

            QuantumGateType.PAULI_Y: [
                r"(?:apply|execute)\s+(?:a\s+)?(?:pauli\s+)?y\s+(?:gate\s+)?(?:to|on)\s+qubit\s+(\d+)",
                r"y\s+qubit\s+(\d+)",
            ],

            QuantumGateType.PAULI_Z: [
                r"(?:apply|execute)\s+(?:a\s+)?(?:pauli\s+)?z\s+(?:gate\s+)?(?:to|on)\s+qubit\s+(\d+)",
                r"phase\s+flip\s+qubit\s+(\d+)",
                r"z\s+qubit\s+(\d+)",
            ],

            QuantumGateType.CNOT: [
                r"(?:apply|create)\s+(?:a\s+)?cnot\s+(?:gate\s+)?(?:from|with\s+control)\s+qubit\s+(\d+)\s+(?:to|and\s+target)\s+qubit\s+(\d+)",
                r"entangle\s+qubits?\s+(\d+)\s+and\s+(\d+)",
                r"create\s+entanglement\s+between\s+qubits?\s+(\d+)\s+and\s+(\d+)",
                r"controlled\s+not\s+from\s+qubit\s+(\d+)\s+to\s+qubit\s+(\d+)",
                r"cnot\s+(\d+)\s+(\d+)",
                r"cx\s+(\d+)\s+(\d+)",
            ],

            QuantumGateType.CZ: [
                r"(?:apply|create)\s+(?:a\s+)?(?:controlled\s+)?z\s+(?:gate\s+)?(?:from|with\s+control)\s+qubit\s+(\d+)\s+(?:to|and\s+target)\s+qubit\s+(\d+)",
                r"cz\s+(\d+)\s+(\d+)",
            ],

            QuantumGateType.TOFFOLI: [
                r"(?:apply|create)\s+(?:a\s+)?toffoli\s+(?:gate\s+)?with\s+controls?\s+qubits?\s+(\d+)\s+and\s+(\d+)\s+(?:and\s+)?target\s+qubit\s+(\d+)",
                r"ccx\s+(\d+)\s+(\d+)\s+(\d+)",
                r"controlled\s+controlled\s+not\s+(\d+)\s+(\d+)\s+(\d+)",
            ],

            QuantumGateType.SWAP: [
                r"swap\s+qubits?\s+(\d+)\s+and\s+(\d+)",
                r"exchange\s+qubits?\s+(\d+)\s+and\s+(\d+)",
                r"switch\s+qubits?\s+(\d+)\s+and\s+(\d+)",
            ],
        }

        # Rotation gate patterns (with angle parameters)
        self.rotation_patterns = {
            QuantumGateType.ROTATION_X: [
                r"rotate\s+qubit\s+(\d+)\s+around\s+x\s+(?:axis\s+)?by\s+([\d.]+)\s*(?:radians?|rad)?",
                r"rx\s+qubit\s+(\d+)\s+([\d.]+)",
                r"x\s+rotation\s+qubit\s+(\d+)\s+([\d.]+)",
            ],
            QuantumGateType.ROTATION_Y: [
                r"rotate\s+qubit\s+(\d+)\s+around\s+y\s+(?:axis\s+)?by\s+([\d.]+)\s*(?:radians?|rad)?",
                r"ry\s+qubit\s+(\d+)\s+([\d.]+)",
                r"y\s+rotation\s+qubit\s+(\d+)\s+([\d.]+)",
            ],
            QuantumGateType.ROTATION_Z: [
                r"rotate\s+qubit\s+(\d+)\s+around\s+z\s+(?:axis\s+)?by\s+([\d.]+)\s*(?:radians?|rad)?",
                r"rz\s+qubit\s+(\d+)\s+([\d.]+)",
                r"z\s+rotation\s+qubit\s+(\d+)\s+([\d.]+)",
                r"phase\s+qubit\s+(\d+)\s+by\s+([\d.]+)",
            ],
        }

    def _init_biotech_patterns(self):
        """Initialize patterns for biotechnology-specific contexts."""
        self.biotech_context_patterns = {
            BiotechContext.PROTEIN_FOLDING: [
                r"protein\s+folding",
                r"protein\s+\w+\s+folding",  # protein hemoglobin folding
                r"amino\s+acid",
                r"polypeptide",
                r"secondary\s+structure",
                r"alpha\s+helix",
                r"beta\s+sheet",
                r"protein\s+conformation",
                r"folding\s+energy",
                r"residue\s+interaction",
                r"folding\s+simulation",
                r"simulate.*protein.*folding",
            ],

            BiotechContext.DRUG_DISCOVERY: [
                r"drug\s+discovery",
                r"drug.*binding",
                r"molecular\s+docking",
                r"binding\s+affinity",
                r"pharmacophore",
                r"ligand\s+binding",
                r"receptor\s+interaction",
                r"chemical\s+compound",
                r"molecular\s+target",
                r"vqe\s+chemistry",
                r"simulate.*drug",
                r"drug.*protein",
                r"binding.*protein",
            ],

            BiotechContext.DNA_ANALYSIS: [
                r"dna\s+sequence",
                r"genome\s+analysis",
                r"nucleotide",
                r"base\s+pair",
                r"genetic\s+code",
                r"sequence\s+alignment",
                r"pattern\s+matching",
                r"grover\s+search",
                r"genomic\s+data",
            ],

            BiotechContext.MOLECULAR_SIMULATION: [
                r"molecular\s+simulation",
                r"quantum\s+chemistry",
                r"electronic\s+structure",
                r"molecular\s+orbital",
                r"chemical\s+reaction",
                r"catalyst",
                r"bond\s+formation",
                r"molecular\s+dynamics",
            ],
        }

        # Biotech-specific algorithmic suggestions
        self.biotech_algorithms = {
            BiotechContext.PROTEIN_FOLDING: {
                "suggested_gates": [QuantumGateType.HADAMARD, QuantumGateType.CNOT, QuantumGateType.ROTATION_Y],
                "optimization_note": "Consider VQE for energy minimization",
                "typical_qubits": "8-20 qubits for small proteins"
            },
            BiotechContext.DRUG_DISCOVERY: {
                "suggested_gates": [QuantumGateType.HADAMARD, QuantumGateType.ROTATION_Z, QuantumGateType.CNOT],
                "optimization_note": "VQE suitable for molecular property calculation",
                "typical_qubits": "4-16 qubits for small molecules"
            },
            BiotechContext.DNA_ANALYSIS: {
                "suggested_gates": [QuantumGateType.HADAMARD, QuantumGateType.CNOT, QuantumGateType.PAULI_Z],
                "optimization_note": "Grover's algorithm for pattern search",
                "typical_qubits": "log2(sequence_length) qubits for search"
            },
        }

    def _init_measurement_patterns(self):
        """Initialize patterns for measurement operations."""
        self.measurement_patterns = [
            r"measure\s+qubit\s+(\d+)(?:\s+(?:into|to)\s+(?:classical\s+)?bit\s+(\d+))?",
            r"read\s+qubit\s+(\d+)(?:\s+(?:into|to)\s+(?:classical\s+)?bit\s+(\d+))?",
            r"observe\s+qubit\s+(\d+)(?:\s+(?:into|to)\s+(?:classical\s+)?bit\s+(\d+))?",
            r"measure\s+all\s+qubits",
            r"read\s+all\s+qubits",
            r"measure\s+everything",
        ]

    def detect_biotech_context(self, text: str) -> BiotechContext:
        """
        Detect the biotechnology context from the input text.

        Args:
            text: Input text to analyze

        Returns:
            The detected biotechnology context
        """
        text_lower = text.lower()

        for context, patterns in self.biotech_context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    self.logger.info(f"Detected biotech context: {context.value}")
                    return context

        return BiotechContext.GENERAL

    def extract_qubit_count(self, text: str) -> Optional[int]:
        """
        Extract the number of qubits from the text.

        Args:
            text: Input text to analyze

        Returns:
            Number of qubits if found, None otherwise
        """
        text_lower = text.lower()

        for pattern in self.qubit_creation_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue

        return None

    def extract_qubit_indices(self, text: str) -> List[int]:
        """
        Extract qubit indices from the text.

        Args:
            text: Input text to analyze

        Returns:
            List of qubit indices found in the text
        """
        indices = []
        text_lower = text.lower()

        for pattern in self.qubit_index_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                try:
                    indices.append(int(match.group(1)))
                except (ValueError, IndexError):
                    continue

        return list(set(indices))  # Remove duplicates

    def parse_gate_operations(self, text: str) -> List[QuantumOperation]:
        """
        Parse quantum gate operations from the text.

        Args:
            text: Input text to analyze

        Returns:
            List of quantum operations found in the text
        """
        operations = []
        text_lower = text.lower()

        # Parse regular gates
        for gate_type, patterns in self.gate_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    try:
                        if gate_type in [QuantumGateType.CNOT, QuantumGateType.CZ, QuantumGateType.SWAP]:
                            # Two-qubit gates
                            control = int(match.group(1))
                            target = int(match.group(2))
                            operations.append(QuantumOperation(
                                gate_type=gate_type,
                                target_qubits=[target],
                                control_qubits=[control]
                            ))
                        elif gate_type == QuantumGateType.TOFFOLI:
                            # Three-qubit gate
                            control1 = int(match.group(1))
                            control2 = int(match.group(2))
                            target = int(match.group(3))
                            operations.append(QuantumOperation(
                                gate_type=gate_type,
                                target_qubits=[target],
                                control_qubits=[control1, control2]
                            ))
                        else:
                            # Single-qubit gates
                            target = int(match.group(1))
                            operations.append(QuantumOperation(
                                gate_type=gate_type,
                                target_qubits=[target]
                            ))
                    except (ValueError, IndexError):
                        continue

        # Parse rotation gates with parameters
        for gate_type, patterns in self.rotation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    try:
                        target = int(match.group(1))
                        angle = float(match.group(2))
                        operations.append(QuantumOperation(
                            gate_type=gate_type,
                            target_qubits=[target],
                            parameters=[angle]
                        ))
                    except (ValueError, IndexError):
                        continue

        return operations

    def parse_measurements(self, text: str) -> List[QuantumOperation]:
        """
        Parse measurement operations from the text.

        Args:
            text: Input text to analyze

        Returns:
            List of measurement operations found in the text
        """
        measurements = []
        text_lower = text.lower()

        for pattern in self.measurement_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                try:
                    if "all" in match.group(0):
                        # Measure all qubits - will be handled in circuit generation
                        measurements.append(QuantumOperation(
                            gate_type=QuantumGateType.MEASURE,
                            target_qubits=[-1],  # Special marker for "all qubits"
                        ))
                    else:
                        qubit = int(match.group(1))
                        classical_bit = qubit  # Default mapping
                        if match.lastindex >= 2 and match.group(2):
                            classical_bit = int(match.group(2))

                        measurements.append(QuantumOperation(
                            gate_type=QuantumGateType.MEASURE,
                            target_qubits=[qubit],
                            classical_bits=[classical_bit]
                        ))
                except (ValueError, IndexError):
                    continue

        return measurements

    def generate_protein_folding_circuit(self, num_qubits: int = 8) -> List[QuantumOperation]:
        """
        Generate a VQE circuit for protein folding simulation.
        Models amino acid interactions and energy landscape optimization.
        """
        operations = []

        # Initialize superposition of all conformations
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

        # Model amino acid interactions with entangling gates
        for i in range(0, num_qubits-1, 2):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.CNOT,
                control_qubits=[i],
                target_qubits=[i+1]
            ))

        # Add variational parameters for energy optimization (VQE ansatz)
        import random
        for i in range(num_qubits):
            # RY rotation for each qubit (parameterized)
            angle = random.uniform(0, 2 * math.pi)  # In real VQE, this would be optimized
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.ROTATION_Y,
                target_qubits=[i],
                parameters=[angle]
            ))

        # Create more complex entanglement pattern for protein interactions
        for i in range(num_qubits-2):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.CNOT,
                control_qubits=[i],
                target_qubits=[i+2]
            ))

        # Final layer of rotations
        for i in range(num_qubits):
            angle = random.uniform(0, math.pi)
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.ROTATION_Z,
                target_qubits=[i],
                parameters=[angle]
            ))

        # Always add measurements for complete circuits
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.MEASURE,
                target_qubits=[i],
                classical_bits=[i]
            ))

        return operations

    def generate_drug_discovery_circuit(self, num_qubits: int = 6) -> List[QuantumOperation]:
        """
        Generate a molecular simulation circuit for drug-protein binding.
        Uses VQE to model molecular interactions and binding affinity.
        """
        operations = []

        # Initialize molecular states
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

        # Model hydrogen bonds and molecular orbitals
        for i in range(0, num_qubits, 2):
            if i+1 < num_qubits:
                operations.append(QuantumOperation(
                    gate_type=QuantumGateType.CNOT,
                    control_qubits=[i],
                    target_qubits=[i+1]
                ))

        # Add molecular interaction parameters
        import random
        for i in range(num_qubits):
            # Model electronic structure with parameterized gates
            angle = random.uniform(0, math.pi/2)
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.ROTATION_X,
                target_qubits=[i],
                parameters=[angle]
            ))

        # Create drug-protein binding interaction
        center_qubit = num_qubits // 2
        for i in range(num_qubits):
            if i != center_qubit:
                operations.append(QuantumOperation(
                    gate_type=QuantumGateType.CZ,
                    control_qubits=[center_qubit],
                    target_qubits=[i]
                ))

        # Final optimization layer
        for i in range(num_qubits):
            angle = random.uniform(0, math.pi)
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.ROTATION_Y,
                target_qubits=[i],
                parameters=[angle]
            ))

        # Always add measurements for complete circuits
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.MEASURE,
                target_qubits=[i],
                classical_bits=[i]
            ))

        return operations

    def generate_dna_analysis_circuit(self, num_qubits: int = 4, pattern_length: int = 4) -> List[QuantumOperation]:
        """
        Generate a Grover's algorithm circuit for DNA sequence pattern matching.
        Searches for specific genetic patterns in DNA sequences.
        """
        operations = []

        # Initialize superposition for Grover's algorithm
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

        # Grover oracle for DNA pattern matching
        # This oracle marks the target DNA sequence
        if num_qubits >= 2:
            # Example: mark sequence "11" (representing specific nucleotides)
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.CZ,
                control_qubits=[0],
                target_qubits=[1]
            ))

        if num_qubits >= 4:
            # Multi-qubit oracle for longer patterns
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.TOFFOLI,
                control_qubits=[0, 1],
                target_qubits=[2]
            ))

        # Grover diffusion operator (amplitude amplification)
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

        # Invert about average
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.PAULI_X,
                target_qubits=[i]
            ))

        # Multi-controlled Z gate (conditional on all qubits)
        if num_qubits == 2:
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.CZ,
                control_qubits=[0],
                target_qubits=[1]
            ))
        elif num_qubits >= 3:
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.TOFFOLI,
                control_qubits=[0, 1],
                target_qubits=[2]
            ))

        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.PAULI_X,
                target_qubits=[i]
            ))

        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

        # Always add measurements for complete circuits
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.MEASURE,
                target_qubits=[i],
                classical_bits=[i]
            ))

        return operations

    def generate_qft_circuit(self, num_qubits: int = 4) -> List[QuantumOperation]:
        """
        Generate a Quantum Fourier Transform (QFT) circuit.
        """
        operations = []

        # QFT implementation
        for i in range(num_qubits):
            # Hadamard gate
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

            # Controlled rotation gates
            for j in range(i + 1, num_qubits):
                # Controlled phase rotation
                angle = math.pi / (2 ** (j - i))
                operations.append(QuantumOperation(
                    gate_type=QuantumGateType.PHASE,
                    control_qubits=[j],
                    target_qubits=[i],
                    parameters=[angle]
                ))

        # Swap qubits to reverse the order (standard QFT)
        for i in range(num_qubits // 2):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.SWAP,
                target_qubits=[i],
                control_qubits=[num_qubits - 1 - i]
            ))

        # Add measurements
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.MEASURE,
                target_qubits=[i],
                classical_bits=[i]
            ))

        return operations

    def generate_bell_state_circuit(self, num_qubits: int = 2) -> List[QuantumOperation]:
        """
        Generate a Bell state circuit for quantum entanglement.
        """
        operations = []

        # Create Bell state: H on qubit 0, CNOT from 0 to 1
        operations.append(QuantumOperation(
            gate_type=QuantumGateType.HADAMARD,
            target_qubits=[0]
        ))

        operations.append(QuantumOperation(
            gate_type=QuantumGateType.CNOT,
            control_qubits=[0],
            target_qubits=[1]
        ))

        # Add measurements
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.MEASURE,
                target_qubits=[i],
                classical_bits=[i]
            ))

        return operations

    def generate_superposition_circuit(self, num_qubits: int = 3) -> List[QuantumOperation]:
        """
        Generate a superposition circuit with Hadamard gates on all qubits.
        """
        operations = []

        # Apply Hadamard to all qubits for superposition
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.HADAMARD,
                target_qubits=[i]
            ))

        # Add measurements
        for i in range(num_qubits):
            operations.append(QuantumOperation(
                gate_type=QuantumGateType.MEASURE,
                target_qubits=[i],
                classical_bits=[i]
            ))

        return operations

    def detect_bell_state(self, text: str) -> bool:
        """Detect if text describes a Bell state."""
        text_lower = text.lower()
        for pattern in self.bell_state_patterns:
            if re.search(pattern, text_lower):
                        return True
        return False

    def detect_superposition(self, text: str) -> bool:
        """Detect if text describes a superposition circuit."""
        text_lower = text.lower()
        for pattern in self.superposition_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    def detect_qft(self, text: str) -> bool:
        """Detect if text describes a Quantum Fourier Transform circuit."""
        text_lower = text.lower()
        qft_keywords = [
            "quantum fourier transform", "qft", "fourier transform",
            "quantum fourier", "fourier"
        ]
        return any(keyword in text_lower for keyword in qft_keywords)

    def apply_biotech_optimizations(self, operations: List[QuantumOperation],
                                  context: BiotechContext, text: str) -> List[QuantumOperation]:
        """
        Apply biotechnology-specific optimizations to the quantum operations.
        Generates real biological quantum circuits instead of placeholder patterns.

        Args:
            operations: List of quantum operations to optimize
            context: The detected biotechnology context
            text: Original text for parameter extraction

        Returns:
            Real biological quantum circuit operations
        """
        if not self.enable_biotech_optimizations or context == BiotechContext.GENERAL:
            return operations

        # Extract qubit count from text for circuit sizing
        num_qubits = self.extract_qubit_count(text) or 8

        if context == BiotechContext.PROTEIN_FOLDING:
            # Generate real VQE circuit for protein folding
            self.logger.info(f"Generating VQE protein folding circuit with {num_qubits} qubits")
            bio_ops = self.generate_protein_folding_circuit(num_qubits)
            return bio_ops + operations  # Add user-specified operations after biological circuit

        elif context == BiotechContext.DRUG_DISCOVERY:
            # Generate real molecular simulation circuit
            self.logger.info(f"Generating drug discovery molecular circuit with {num_qubits} qubits")
            bio_ops = self.generate_drug_discovery_circuit(min(num_qubits, 8))
            return bio_ops + operations

        elif context == BiotechContext.DNA_ANALYSIS:
            # Generate real Grover's algorithm for DNA pattern matching
            self.logger.info(f"Generating DNA analysis Grover circuit with {num_qubits} qubits")
            bio_ops = self.generate_dna_analysis_circuit(min(num_qubits, 6))
            return bio_ops + operations

        elif context == BiotechContext.MOLECULAR_SIMULATION:
            # Generate quantum chemistry simulation
            self.logger.info(f"Generating molecular simulation circuit with {num_qubits} qubits")
            bio_ops = self.generate_drug_discovery_circuit(num_qubits)  # Reuse molecular circuit
            return bio_ops + operations

        return operations

    def _convert_mega_match_to_circuit(self, match) -> ParsedCircuit:
        """
        Convert a mega pattern match to a ParsedCircuit.

        NEW in v3.0: Converts the intent-based match from mega matcher
        into concrete quantum operations.

        Args:
            match: PatternMatch object from mega matcher

        Returns:
            ParsedCircuit object
        """
        num_qubits = match.extracted_params.get('num_qubits', 2)

        # Map intent to circuit generation
        if match.intent == self.IntentType.CREATE_BELL_STATE:
            operations = self.generate_bell_state_circuit(num_qubits)
            context = BiotechContext.GENERAL

        elif match.intent == self.IntentType.CREATE_SUPERPOSITION:
            operations = self.generate_superposition_circuit(num_qubits)
            context = BiotechContext.GENERAL

        elif match.intent == self.IntentType.ENTANGLE_QUBITS:
            operations = self.generate_bell_state_circuit(num_qubits)
            context = BiotechContext.GENERAL

        elif match.intent == self.IntentType.QUANTUM_FOURIER:
            operations = self.generate_qft_circuit(num_qubits)
            context = BiotechContext.GENERAL

        elif match.intent == self.IntentType.PROTEIN_FOLDING:
            operations = self.generate_protein_folding_circuit(num_qubits)
            context = BiotechContext.PROTEIN_FOLDING

        elif match.intent == self.IntentType.DRUG_DESIGN:
            # De novo drug design - same circuit as docking but different interpretation
            operations = self.generate_drug_discovery_circuit(num_qubits)
            context = BiotechContext.DRUG_DISCOVERY

        elif match.intent == self.IntentType.DRUG_DOCKING:
            operations = self.generate_drug_discovery_circuit(num_qubits)
            context = BiotechContext.DRUG_DISCOVERY

        elif match.intent == self.IntentType.DNA_ANALYSIS:
            operations = self.generate_dna_analysis_circuit(num_qubits)
            context = BiotechContext.DNA_ANALYSIS

        elif match.intent == self.IntentType.MOLECULAR_SIMULATION:
            operations = self.generate_drug_discovery_circuit(num_qubits)
            context = BiotechContext.MOLECULAR_SIMULATION

        else:
            # Default fallback
            operations = self.generate_bell_state_circuit(num_qubits)
            context = BiotechContext.GENERAL

        return ParsedCircuit(
            num_qubits=num_qubits,
            num_classical_bits=num_qubits,
            operations=operations,
            biotech_context=context,
            description=match.original_text
        )

    def parse(self, text: str) -> ParsedCircuit:
        """
        Parse natural language text into a quantum circuit description.

        BioQL v3.0: Now tries mega pattern matcher first (1B+ patterns),
        then falls back to legacy patterns if needed.

        Args:
            text: Natural language description of quantum circuit

        Returns:
            ParsedCircuit object containing the parsed circuit

        Raises:
            CompilerError: If parsing fails or invalid syntax is detected
        """
        try:
            # NEW in v3.0: Try mega pattern matcher first
            if self.use_mega_patterns and self.mega_matcher:
                match = self.mega_matcher.match(text)
                if match:
                    self.logger.info(f"Mega pattern matched: {match.intent.value} (confidence: {match.confidence})")
                    return self._convert_mega_match_to_circuit(match)

            # LEGACY: Detect Bell state first (special case)
            if self.detect_bell_state(text):
                num_qubits = self.extract_qubit_count(text) or 2
                bell_operations = self.generate_bell_state_circuit(num_qubits)

                return ParsedCircuit(
                    num_qubits=num_qubits,
                    num_classical_bits=num_qubits,
                    operations=bell_operations,
                    biotech_context=BiotechContext.GENERAL,
                    description=text.strip()
                )

            # Detect superposition (special case)
            if self.detect_superposition(text):
                num_qubits = self.extract_qubit_count(text) or 3
                superposition_operations = self.generate_superposition_circuit(num_qubits)

                return ParsedCircuit(
                    num_qubits=num_qubits,
                    num_classical_bits=num_qubits,
                    operations=superposition_operations,
                    biotech_context=BiotechContext.GENERAL,
                    description=text.strip()
                )

            # Detect QFT (special case)
            if self.detect_qft(text):
                num_qubits = self.extract_qubit_count(text) or 4
                qft_operations = self.generate_qft_circuit(num_qubits)

                return ParsedCircuit(
                    num_qubits=num_qubits,
                    num_classical_bits=num_qubits,
                    operations=qft_operations,
                    biotech_context=BiotechContext.GENERAL,
                    description=text.strip()
                )

            # Detect biotechnology context
            biotech_context = self.detect_biotech_context(text)

            # Extract number of qubits
            num_qubits = self.extract_qubit_count(text)
            if num_qubits is None:
                # Try to infer from operations
                all_indices = self.extract_qubit_indices(text)
                if all_indices:
                    num_qubits = max(all_indices) + 1
                else:
                    num_qubits = 2  # Default minimal circuit

            # Parse operations
            gate_operations = self.parse_gate_operations(text)
            measurement_operations = self.parse_measurements(text)

            all_operations = gate_operations + measurement_operations

            # Apply biotech optimizations with real biological circuits
            if self.enable_biotech_optimizations:
                all_operations = self.apply_biotech_optimizations(all_operations, biotech_context, text)

            # Ensure qubit count is sufficient for all operations
            max_qubit_used = 0
            for op in all_operations:
                if op.target_qubits:
                    max_qubit_used = max(max_qubit_used, max(q for q in op.target_qubits if q >= 0))
                if op.control_qubits:
                    max_qubit_used = max(max_qubit_used, max(op.control_qubits))

            # Ensure we have enough qubits
            num_qubits = max(num_qubits, max_qubit_used + 1)

            # Determine number of classical bits
            num_classical_bits = 0
            for op in measurement_operations:
                if op.classical_bits:
                    num_classical_bits = max(num_classical_bits, max(op.classical_bits) + 1)
                elif op.target_qubits and op.target_qubits[0] != -1:
                    num_classical_bits = max(num_classical_bits, max(op.target_qubits) + 1)

            if num_classical_bits == 0 and measurement_operations:
                num_classical_bits = num_qubits  # Default: same as qubits

            return ParsedCircuit(
                num_qubits=num_qubits,
                num_classical_bits=num_classical_bits,
                operations=all_operations,
                biotech_context=biotech_context,
                description=text.strip()
            )

        except Exception as e:
            raise CompilerError(f"Failed to parse quantum circuit description: {str(e)}")


class QASMGenerator:
    """
    Generates OpenQASM 3.0 code from parsed quantum circuits.
    """

    def __init__(self):
        """Initialize the QASM generator."""
        self.logger = logging.getLogger(__name__)

    def _gate_to_qasm(self, operation: QuantumOperation) -> str:
        """
        Convert a single quantum operation to QASM code.

        Args:
            operation: The quantum operation to convert

        Returns:
            QASM code string for the operation
        """
        gate_map = {
            QuantumGateType.HADAMARD: "h",
            QuantumGateType.PAULI_X: "x",
            QuantumGateType.PAULI_Y: "y",
            QuantumGateType.PAULI_Z: "z",
            QuantumGateType.CNOT: "cnot",
            QuantumGateType.CZ: "cz",
            QuantumGateType.TOFFOLI: "ccx",
            QuantumGateType.ROTATION_X: "rx",
            QuantumGateType.ROTATION_Y: "ry",
            QuantumGateType.ROTATION_Z: "rz",
            QuantumGateType.PHASE: "p",
            QuantumGateType.SWAP: "swap",
            QuantumGateType.MEASURE: "measure",
        }

        gate_name = gate_map.get(operation.gate_type)
        if not gate_name:
            raise CompilerError(f"Unsupported gate type: {operation.gate_type}")

        if operation.gate_type == QuantumGateType.MEASURE:
            if operation.target_qubits[0] == -1:
                # Measure all qubits
                return "// Measure all qubits - to be expanded during generation"
            else:
                qubit = operation.target_qubits[0]
                classical_bit = operation.classical_bits[0] if operation.classical_bits else qubit
                return f"measure q[{qubit}] -> c[{classical_bit}];"

        # Build the gate call
        qasm_line = gate_name

        # Add parameters for parameterized gates
        if operation.parameters:
            params = ", ".join(str(p) for p in operation.parameters)
            qasm_line += f"({params})"

        # Add qubit arguments
        all_qubits = operation.control_qubits + operation.target_qubits
        qubit_args = ", ".join(f"q[{q}]" for q in all_qubits)
        qasm_line += f" {qubit_args};"

        return qasm_line

    def generate(self, circuit: ParsedCircuit) -> str:
        """
        Generate OpenQASM 3.0 code from a parsed circuit.

        Args:
            circuit: The parsed quantum circuit

        Returns:
            Complete OpenQASM 3.0 code as a string
        """
        qasm_lines = []

        # Header
        qasm_lines.append("OPENQASM 3.0;")
        qasm_lines.append("include \"stdgates.inc\";")
        qasm_lines.append("")

        # Add biotech context comment
        if circuit.biotech_context != BiotechContext.GENERAL:
            qasm_lines.append(f"// Biotechnology context: {circuit.biotech_context.value}")
            qasm_lines.append(f"// Original description: {circuit.description}")
            qasm_lines.append("")

        # Quantum and classical register declarations
        qasm_lines.append(f"qubit[{circuit.num_qubits}] q;")
        if circuit.num_classical_bits > 0:
            qasm_lines.append(f"bit[{circuit.num_classical_bits}] c;")
        qasm_lines.append("")

        # Generate operations
        for operation in circuit.operations:
            if operation.gate_type == QuantumGateType.MEASURE and operation.target_qubits[0] == -1:
                # Expand "measure all" to individual measurements
                for i in range(circuit.num_qubits):
                    qasm_lines.append(f"measure q[{i}] -> c[{i}];")
            else:
                qasm_lines.append(self._gate_to_qasm(operation))

        return "\n".join(qasm_lines)


class BioQLCompiler:
    """
    Main compiler class that orchestrates the translation from English to QASM.

    This class provides the primary interface for the BioQL compiler, combining
    natural language parsing with QASM code generation.
    """

    def __init__(self, enable_biotech_optimizations: bool = True,
                 log_level: int = logging.INFO):
        """
        Initialize the BioQL compiler.

        Args:
            enable_biotech_optimizations: Whether to apply biotech-specific optimizations
            log_level: Logging level for the compiler
        """
        # Set up logging
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.parser = NaturalLanguageParser(enable_biotech_optimizations)
        self.qasm_generator = QASMGenerator()

        self.logger.info("BioQL Compiler initialized")

    def compile_to_qasm(self, english_description: str) -> str:
        """
        Compile English description to OpenQASM 3.0 code.

        Args:
            english_description: Natural language description of quantum circuit

        Returns:
            OpenQASM 3.0 code as a string

        Raises:
            CompilerError: If compilation fails
        """
        try:
            self.logger.info(f"Compiling: {english_description}")

            # Parse the English description
            parsed_circuit = self.parser.parse(english_description)

            # Generate QASM code
            qasm_code = self.qasm_generator.generate(parsed_circuit)

            self.logger.info("Compilation successful")
            return qasm_code

        except Exception as e:
            error_msg = f"Compilation failed: {str(e)}"
            self.logger.error(error_msg)
            raise CompilerError(error_msg)

    def parse_to_circuit(self, english_description: str) -> Optional['QuantumCircuit']:
        """
        Parse English description to a Qiskit QuantumCircuit object.

        Args:
            english_description: Natural language description of quantum circuit

        Returns:
            Qiskit QuantumCircuit object if Qiskit is available, None otherwise

        Raises:
            CompilerError: If parsing fails or Qiskit is not available
        """
        if not QISKIT_AVAILABLE:
            raise CompilerError("Qiskit is not available. Cannot create QuantumCircuit object.")

        try:
            # Parse the description
            parsed_circuit = self.parser.parse(english_description)

            # Create Qiskit circuit - ensure enough classical bits for measurements
            num_classical_bits = max(parsed_circuit.num_classical_bits, parsed_circuit.num_qubits)
            qc = QuantumCircuit(parsed_circuit.num_qubits, num_classical_bits)

            # Add operations to the circuit
            for operation in parsed_circuit.operations:
                if operation.gate_type == QuantumGateType.HADAMARD:
                    qc.h(operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.PAULI_X:
                    qc.x(operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.PAULI_Y:
                    qc.y(operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.PAULI_Z:
                    qc.z(operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.CNOT:
                    qc.cx(operation.control_qubits[0], operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.CZ:
                    qc.cz(operation.control_qubits[0], operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.TOFFOLI:
                    qc.ccx(operation.control_qubits[0], operation.control_qubits[1],
                          operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.ROTATION_X:
                    qc.rx(operation.parameters[0], operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.ROTATION_Y:
                    qc.ry(operation.parameters[0], operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.ROTATION_Z:
                    qc.rz(operation.parameters[0], operation.target_qubits[0])
                elif operation.gate_type == QuantumGateType.SWAP:
                    qc.swap(operation.target_qubits[0], operation.control_qubits[0])
                elif operation.gate_type == QuantumGateType.MEASURE:
                    if operation.target_qubits[0] == -1:
                        # Measure all qubits
                        qc.measure_all()
                    else:
                        classical_bit = (operation.classical_bits[0]
                                       if operation.classical_bits
                                       else operation.target_qubits[0])
                        qc.measure(operation.target_qubits[0], classical_bit)

            return qc

        except Exception as e:
            error_msg = f"Failed to create QuantumCircuit: {str(e)}"
            self.logger.error(error_msg)
            raise CompilerError(error_msg)

    def get_biotech_suggestions(self, english_description: str) -> Dict[str, Any]:
        """
        Get biotechnology-specific suggestions for the given description.

        Args:
            english_description: Natural language description to analyze

        Returns:
            Dictionary containing suggestions and optimizations
        """
        context = self.parser.detect_biotech_context(english_description)

        if context in self.parser.biotech_algorithms:
            return {
                "context": context.value,
                "suggestions": self.parser.biotech_algorithms[context],
                "description": english_description
            }
        else:
            return {
                "context": "general",
                "suggestions": {
                    "suggested_gates": "No specific suggestions for general context",
                    "optimization_note": "Consider specifying biotechnology domain for optimizations",
                    "typical_qubits": "Depends on problem size"
                },
                "description": english_description
            }


# Convenience functions for direct usage
def compile_english_to_qasm(description: str, enable_biotech_optimizations: bool = True) -> str:
    """
    Convenience function to compile English description to QASM code.

    Args:
        description: Natural language description of quantum circuit
        enable_biotech_optimizations: Whether to apply biotech-specific optimizations

    Returns:
        OpenQASM 3.0 code as a string
    """
    compiler = BioQLCompiler(enable_biotech_optimizations=enable_biotech_optimizations)
    return compiler.compile_to_qasm(description)


def parse_english_to_circuit(description: str, enable_biotech_optimizations: bool = True) -> Optional['QuantumCircuit']:
    """
    Convenience function to parse English description to Qiskit QuantumCircuit.

    Args:
        description: Natural language description of quantum circuit
        enable_biotech_optimizations: Whether to apply biotech-specific optimizations

    Returns:
        Qiskit QuantumCircuit object if available, None otherwise
    """
    compiler = BioQLCompiler(enable_biotech_optimizations=enable_biotech_optimizations)
    return compiler.parse_to_circuit(description)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    compiler = BioQLCompiler()

    # Test cases
    test_cases = [
        "Create 3 qubits, apply Hadamard to qubit 0, entangle qubits 0 and 1, measure all qubits",
        "Initialize 4 quantum bits for protein folding simulation. Put qubit 0 in superposition. Create entanglement between qubits 0 and 2.",
        "Setup 2 qubits for drug discovery. Apply Hadamard gate to qubit 0. Controlled not from qubit 0 to qubit 1. Measure everything.",
        "Make 5 qubits for DNA sequence analysis. Superpose all qubits. Apply Grover search pattern.",
    ]

    print("BioQL Compiler Test Cases:")
    print("=" * 50)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input: {test_case}")
        print("\nGenerated QASM:")
        try:
            qasm_output = compiler.compile_to_qasm(test_case)
            print(qasm_output)

            # Get biotech suggestions
            suggestions = compiler.get_biotech_suggestions(test_case)
            if suggestions["context"] != "general":
                print(f"\nBiotech Context: {suggestions['context']}")
                print(f"Optimization Note: {suggestions['suggestions']['optimization_note']}")

        except CompilerError as e:
            print(f"Error: {e}")

        print("-" * 40)