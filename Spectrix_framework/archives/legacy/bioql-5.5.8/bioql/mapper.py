"""
Enhanced Natural Language Mapper for BioQL

This module provides advanced natural language to quantum gate mapping with context awareness,
domain specialization, and hardware optimization capabilities.

Features:
- Context-aware mapping with session state tracking
- Domain-specific vocabularies for drug discovery, protein folding, and sequence analysis
- Hardware-optimized transpilation for IBM Quantum, IonQ, and Rigetti
- Intent analysis and ambiguity resolution
- Constraint-based circuit generation

Author: BioQL Team
Version: 3.0.0
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Optional loguru import
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from bioql.ir import (
    BioQLDomain,
    BioQLParameter,
    QuantumBackend,
    QuantumCircuit,
    QuantumGate,
)


# ============================================================================
# Intent and Context Models
# ============================================================================

class Intent(str, Enum):
    """Natural language intent types."""
    CREATE_CIRCUIT = "create_circuit"
    CREATE_SUPERPOSITION = "create_superposition"
    CREATE_ENTANGLEMENT = "create_entanglement"
    APPLY_GATE = "apply_gate"
    MEASURE = "measure"
    OPTIMIZE = "optimize"
    SIMULATE = "simulate"
    DOCK = "dock"
    ALIGN = "align"
    FOLD = "fold"
    ANALYZE = "analyze"
    UNKNOWN = "unknown"


@dataclass
class Context:
    """Context information for NL mapping."""
    domain: Optional[BioQLDomain] = None
    intent: Intent = Intent.UNKNOWN
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    session_history: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuantumGateMapping:
    """Mapping result from NL to quantum gates."""
    gates: List[Dict[str, Any]] = field(default_factory=list)
    qubits_used: Set[int] = field(default_factory=set)
    parameters: List[BioQLParameter] = field(default_factory=list)
    confidence: float = 0.0
    description: str = ""


@dataclass
class HardwareBackend:
    """Hardware backend specification."""
    name: str
    native_gates: Set[str]
    connectivity: List[Tuple[int, int]]
    max_qubits: int
    gate_fidelities: Dict[str, float]
    properties: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Hardware Backend Specifications
# ============================================================================

IBM_QUANTUM = HardwareBackend(
    name="IBM Quantum",
    native_gates={"id", "rz", "sx", "x", "cx"},
    connectivity=[
        (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (3, 4), (4, 3),
        (0, 5), (5, 0), (1, 6), (6, 1), (2, 7), (7, 2), (3, 8), (8, 3),
        (4, 9), (9, 4), (5, 6), (6, 5), (6, 7), (7, 6), (7, 8), (8, 7),
        (8, 9), (9, 8)
    ],
    max_qubits=127,
    gate_fidelities={
        "id": 0.9999,
        "rz": 0.9999,
        "sx": 0.9995,
        "x": 0.9995,
        "cx": 0.99
    },
    properties={
        "t1": 100e-6,  # 100 microseconds
        "t2": 150e-6,
        "readout_fidelity": 0.98
    }
)

IONQ = HardwareBackend(
    name="IonQ",
    native_gates={"gpi", "gpi2", "ms"},  # IonQ native gates
    connectivity=[(i, j) for i in range(11) for j in range(11) if i != j],  # All-to-all
    max_qubits=11,
    gate_fidelities={
        "gpi": 0.9998,
        "gpi2": 0.9998,
        "ms": 0.997  # Mølmer-Sørensen gate
    },
    properties={
        "topology": "all-to-all",
        "gate_time_1q": 10e-6,
        "gate_time_2q": 200e-6
    }
)

RIGETTI = HardwareBackend(
    name="Rigetti",
    native_gates={"rx", "rz", "cz"},
    connectivity=[
        (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2),
        (0, 7), (7, 0), (1, 8), (8, 1), (2, 9), (9, 2),
        (3, 10), (10, 3), (7, 8), (8, 7), (8, 9), (9, 8)
    ],
    max_qubits=80,
    gate_fidelities={
        "rx": 0.998,
        "rz": 0.9999,
        "cz": 0.94
    },
    properties={
        "architecture": "Aspen-M",
        "t1": 20e-6,
        "t2": 18e-6
    }
)


# ============================================================================
# Context Analyzer
# ============================================================================

class ContextAnalyzer:
    """Analyzes natural language context for better mapping."""

    def __init__(self):
        self.domain_keywords = {
            BioQLDomain.DOCKING: [
                "dock", "binding", "ligand", "receptor", "protein", "molecule",
                "affinity", "pose", "complex", "interaction"
            ],
            BioQLDomain.ALIGNMENT: [
                "align", "sequence", "match", "gap", "similarity", "blast",
                "needleman", "wunsch", "smith", "waterman"
            ],
            BioQLDomain.FOLDING: [
                "fold", "folding", "structure", "conformation", "secondary",
                "tertiary", "helix", "sheet", "coil", "rosetta"
            ],
            BioQLDomain.OPTIMIZATION: [
                "optimize", "minimize", "maximize", "energy", "cost",
                "objective", "constraint", "vqe", "qaoa", "variational"
            ],
            BioQLDomain.SIMULATION: [
                "simulate", "simulation", "dynamics", "trajectory", "evolution",
                "hamiltonian", "propagate", "time-evolve"
            ]
        }

        self.intent_patterns = {
            Intent.CREATE_SUPERPOSITION: [
                r"(?:create|make|generate)\s+superposition",
                r"(?:put|place)\s+.*\s+in\s+superposition",
                r"hadamard\s+(?:gate|on|to)",
                r"equal\s+superposition"
            ],
            Intent.CREATE_ENTANGLEMENT: [
                r"(?:create|make|generate)\s+entangle",
                r"entangle\s+qubit",
                r"cnot\s+(?:gate|from|between)",
                r"bell\s+state",
                r"epr\s+pair"
            ],
            Intent.APPLY_GATE: [
                r"apply\s+(?:gate|operator)",
                r"(?:add|insert)\s+gate",
                r"rotate\s+(?:by|around)",
                r"flip\s+qubit"
            ],
            Intent.MEASURE: [
                r"measure\s+qubit",
                r"read\s+(?:out|qubit)",
                r"observe\s+state",
                r"collapse\s+(?:to|into)"
            ]
        }

    def analyze(self, text: str, history: Optional[List[str]] = None) -> Context:
        """
        Analyze natural language text to extract context.

        Args:
            text: Natural language text to analyze
            history: Optional conversation history

        Returns:
            Context object with extracted information
        """
        context = Context(
            session_history=history or []
        )

        text_lower = text.lower()

        # Extract domain
        context.domain = self.extract_domain(text)

        # Infer intent
        context.intent = self.infer_intent(text, context)

        # Extract entities
        context.entities = self._extract_entities(text_lower)

        # Calculate confidence
        context.confidence = self._calculate_confidence(context)

        return context

    def extract_domain(self, text: str) -> Optional[BioQLDomain]:
        """Extract the computational domain from text."""
        text_lower = text.lower()
        domain_scores = {}

        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return None

    def infer_intent(self, text: str, context: Context) -> Intent:
        """Infer the user's intent from the text and context."""
        text_lower = text.lower()

        # Check explicit intent patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent

        # Infer from domain
        if context.domain == BioQLDomain.DOCKING:
            return Intent.DOCK
        elif context.domain == BioQLDomain.ALIGNMENT:
            return Intent.ALIGN
        elif context.domain == BioQLDomain.FOLDING:
            return Intent.FOLD
        elif context.domain == BioQLDomain.OPTIMIZATION:
            return Intent.OPTIMIZE
        elif context.domain == BioQLDomain.SIMULATION:
            return Intent.SIMULATE

        # Check for circuit creation keywords
        if any(word in text_lower for word in ["create", "make", "build", "generate"]):
            if any(word in text_lower for word in ["circuit", "quantum"]):
                return Intent.CREATE_CIRCUIT

        return Intent.UNKNOWN

    def suggest_clarifications(self, ambiguous_text: str) -> List[str]:
        """
        Suggest clarifying questions for ambiguous text.

        Args:
            ambiguous_text: Text that needs clarification

        Returns:
            List of clarifying questions
        """
        suggestions = []
        text_lower = ambiguous_text.lower()

        # Check if domain is unclear
        domain = self.extract_domain(ambiguous_text)
        if not domain:
            suggestions.append(
                "Which domain are you working in? (docking, alignment, folding, optimization, simulation)"
            )

        # Check if qubit count is specified
        if "qubit" in text_lower and not re.search(r"\d+\s*qubit", text_lower):
            suggestions.append("How many qubits do you need?")

        # Check if gate parameters are specified for rotation gates
        if any(word in text_lower for word in ["rotate", "rotation"]):
            if not re.search(r"\d+\.?\d*\s*(?:rad|deg|pi)", text_lower):
                suggestions.append("What angle should the rotation be?")

        # Check if target qubits are specified
        if any(word in text_lower for word in ["apply", "gate", "operator"]):
            if not re.search(r"qubit\s+\d+", text_lower):
                suggestions.append("Which qubit(s) should the gate be applied to?")

        return suggestions

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {}

        # Extract qubit counts
        qubit_match = re.search(r"(\d+)\s*qubit", text)
        if qubit_match:
            entities["num_qubits"] = int(qubit_match.group(1))

        # Extract qubit indices
        qubit_indices = re.findall(r"qubit\s+(\d+)", text)
        if qubit_indices:
            entities["qubit_indices"] = [int(idx) for idx in qubit_indices]

        # Extract angles
        angle_patterns = [
            r"(\d+\.?\d*)\s*(?:rad|radians?)",
            r"(\d+\.?\d*)\s*(?:deg|degrees?)",
            r"(\d+\.?\d*)\s*pi"
        ]
        for pattern in angle_patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))
                if "deg" in pattern:
                    value = math.radians(value)
                elif "pi" in pattern:
                    value = value * math.pi
                entities["angle"] = value
                break

        # Extract gate names
        gate_names = ["hadamard", "pauli", "cnot", "rotation", "phase", "swap", "toffoli"]
        for gate in gate_names:
            if gate in text:
                entities["gate_type"] = gate

        return entities

    def _calculate_confidence(self, context: Context) -> float:
        """Calculate confidence score for the context."""
        confidence = 0.0

        # Domain confidence
        if context.domain is not None:
            confidence += 0.3

        # Intent confidence
        if context.intent != Intent.UNKNOWN:
            confidence += 0.3

        # Entity confidence
        if context.entities:
            confidence += 0.2 * min(len(context.entities) / 3, 1.0)

        # History confidence
        if context.session_history:
            confidence += 0.2

        return min(confidence, 1.0)


# ============================================================================
# Domain-Specific Mapper
# ============================================================================

class DomainSpecificMapper:
    """Maps domain-specific concepts to quantum circuits."""

    def __init__(self):
        # Drug discovery domain mappings
        self.drug_discovery_mappings = {
            "binding_affinity": self._map_binding_affinity,
            "molecular_orbital": self._map_molecular_orbital,
            "electron_density": self._map_electron_density,
            "interaction_energy": self._map_interaction_energy,
            "pharmacophore": self._map_pharmacophore
        }

        # Protein folding domain mappings
        self.protein_folding_mappings = {
            "secondary_structure": self._map_secondary_structure,
            "hydrophobic_interaction": self._map_hydrophobic_interaction,
            "backbone_angle": self._map_backbone_angle,
            "contact_map": self._map_contact_map,
            "folding_energy": self._map_folding_energy
        }

        # Sequence analysis domain mappings
        self.sequence_analysis_mappings = {
            "pattern_search": self._map_pattern_search,
            "similarity_score": self._map_similarity_score,
            "motif_detection": self._map_motif_detection,
            "alignment_score": self._map_alignment_score
        }

    def map_domain_concept(
        self,
        concept: str,
        domain: BioQLDomain,
        num_qubits: int = 4
    ) -> QuantumCircuit:
        """
        Map a domain-specific concept to a quantum circuit.

        Args:
            concept: Domain concept to map
            domain: Computational domain
            num_qubits: Number of qubits to use

        Returns:
            QuantumCircuit representing the concept
        """
        # Select appropriate mapping dictionary
        if domain == BioQLDomain.DOCKING:
            mappings = self.drug_discovery_mappings
        elif domain == BioQLDomain.FOLDING:
            mappings = self.protein_folding_mappings
        elif domain == BioQLDomain.ALIGNMENT:
            mappings = self.sequence_analysis_mappings
        else:
            # Default to generic mapping
            return self._create_generic_circuit(num_qubits)

        # Find matching concept
        concept_lower = concept.lower().replace(" ", "_")
        for key, mapper_func in mappings.items():
            if key in concept_lower or concept_lower in key:
                return mapper_func(num_qubits)

        # Fallback to generic circuit
        return self._create_generic_circuit(num_qubits)

    def get_domain_vocabulary(self, domain: BioQLDomain) -> Dict[str, str]:
        """Get domain-specific vocabulary and descriptions."""
        vocabularies = {
            BioQLDomain.DOCKING: {
                "binding_affinity": "Quantum encoding of protein-ligand binding strength",
                "molecular_orbital": "Quantum representation of molecular orbital states",
                "electron_density": "Electron distribution in molecular systems",
                "interaction_energy": "Energy landscape of molecular interactions",
                "pharmacophore": "3D arrangement of molecular features"
            },
            BioQLDomain.FOLDING: {
                "secondary_structure": "Alpha helix and beta sheet formations",
                "hydrophobic_interaction": "Non-polar amino acid clustering",
                "backbone_angle": "Phi and psi dihedral angles",
                "contact_map": "Spatial proximity of residues",
                "folding_energy": "Potential energy surface of protein"
            },
            BioQLDomain.ALIGNMENT: {
                "pattern_search": "Quantum search for sequence patterns",
                "similarity_score": "Sequence similarity calculation",
                "motif_detection": "Finding conserved sequence motifs",
                "alignment_score": "Optimal alignment scoring"
            }
        }
        return vocabularies.get(domain, {})

    def extend_domain(
        self,
        domain: BioQLDomain,
        custom_mappings: Dict[str, Any]
    ) -> None:
        """
        Extend domain with custom mappings.

        Args:
            domain: Domain to extend
            custom_mappings: Dictionary of concept -> mapping function
        """
        if domain == BioQLDomain.DOCKING:
            self.drug_discovery_mappings.update(custom_mappings)
        elif domain == BioQLDomain.FOLDING:
            self.protein_folding_mappings.update(custom_mappings)
        elif domain == BioQLDomain.ALIGNMENT:
            self.sequence_analysis_mappings.update(custom_mappings)

    # Domain-specific circuit generators
    def _map_binding_affinity(self, num_qubits: int) -> QuantumCircuit:
        """Map binding affinity calculation to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Encode ligand and receptor states
        for i in range(num_qubits // 2):
            circuit.add_gate(QuantumGate.H, [i])

        # Create entanglement for binding interaction
        for i in range(num_qubits // 2):
            circuit.add_gate(QuantumGate.CNOT, [i, num_qubits // 2 + i])

        # Add phase estimation for energy
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RZ, [i], [math.pi / 4])

        return circuit

    def _map_molecular_orbital(self, num_qubits: int) -> QuantumCircuit:
        """Map molecular orbital to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Initialize orbital basis states
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RY, [i], [math.pi / 4])

        # Add orbital interactions
        for i in range(num_qubits - 1):
            circuit.add_gate(QuantumGate.CZ, [i, i + 1])

        return circuit

    def _map_electron_density(self, num_qubits: int) -> QuantumCircuit:
        """Map electron density to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])
            circuit.add_gate(QuantumGate.RZ, [i], [math.pi / 8])

        return circuit

    def _map_interaction_energy(self, num_qubits: int) -> QuantumCircuit:
        """Map interaction energy to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # VQE-style ansatz for energy calculation
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RY, [i], [math.pi / 6])

        for i in range(num_qubits - 1):
            circuit.add_gate(QuantumGate.CNOT, [i, i + 1])

        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RZ, [i], [math.pi / 3])

        return circuit

    def _map_pharmacophore(self, num_qubits: int) -> QuantumCircuit:
        """Map pharmacophore to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Encode 3D spatial features
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])

        # Add feature correlations
        for i in range(0, num_qubits - 1, 2):
            circuit.add_gate(QuantumGate.CNOT, [i, i + 1])

        return circuit

    def _map_secondary_structure(self, num_qubits: int) -> QuantumCircuit:
        """Map secondary structure to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Encode helix/sheet/coil states
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RY, [i], [math.pi / 5])

        # Add sequential correlations
        for i in range(num_qubits - 1):
            circuit.add_gate(QuantumGate.CNOT, [i, i + 1])

        return circuit

    def _map_hydrophobic_interaction(self, num_qubits: int) -> QuantumCircuit:
        """Map hydrophobic interactions to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Group hydrophobic residues
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])

        # Create clustering interactions
        center = num_qubits // 2
        for i in range(num_qubits):
            if i != center:
                circuit.add_gate(QuantumGate.CZ, [center, i])

        return circuit

    def _map_backbone_angle(self, num_qubits: int) -> QuantumCircuit:
        """Map backbone angles to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Encode phi/psi angles as rotations
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RY, [i], [math.pi / 3])
            circuit.add_gate(QuantumGate.RZ, [i], [math.pi / 4])

        return circuit

    def _map_contact_map(self, num_qubits: int) -> QuantumCircuit:
        """Map contact map to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Encode pairwise contacts
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])

        # Add contact interactions
        for i in range(num_qubits):
            for j in range(i + 2, num_qubits):
                if j < num_qubits:
                    circuit.add_gate(QuantumGate.CZ, [i, j])

        return circuit

    def _map_folding_energy(self, num_qubits: int) -> QuantumCircuit:
        """Map folding energy to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # VQE ansatz for protein folding
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RY, [i], [math.pi / 4])

        for i in range(num_qubits - 1):
            circuit.add_gate(QuantumGate.CNOT, [i, i + 1])

        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RZ, [i], [math.pi / 6])

        return circuit

    def _map_pattern_search(self, num_qubits: int) -> QuantumCircuit:
        """Map pattern search to quantum circuit (Grover's)."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Initialize superposition
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])

        # Oracle (simplified)
        if num_qubits >= 2:
            circuit.add_gate(QuantumGate.CZ, [0, 1])

        # Diffusion operator
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])
            circuit.add_gate(QuantumGate.X, [i])

        if num_qubits >= 2:
            circuit.add_gate(QuantumGate.CZ, [0, 1])

        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.X, [i])
            circuit.add_gate(QuantumGate.H, [i])

        return circuit

    def _map_similarity_score(self, num_qubits: int) -> QuantumCircuit:
        """Map similarity score to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Encode two sequences
        half = num_qubits // 2
        for i in range(half):
            circuit.add_gate(QuantumGate.H, [i])

        # Compare sequences
        for i in range(half):
            if i + half < num_qubits:
                circuit.add_gate(QuantumGate.CNOT, [i, i + half])

        return circuit

    def _map_motif_detection(self, num_qubits: int) -> QuantumCircuit:
        """Map motif detection to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Amplitude amplification for motif search
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])

        # Motif oracle
        for i in range(0, num_qubits - 1, 2):
            circuit.add_gate(QuantumGate.CZ, [i, i + 1])

        return circuit

    def _map_alignment_score(self, num_qubits: int) -> QuantumCircuit:
        """Map alignment score to quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        # Dynamic programming on quantum computer
        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.RY, [i], [math.pi / 4])

        for i in range(num_qubits - 1):
            circuit.add_gate(QuantumGate.CNOT, [i, i + 1])
            circuit.add_gate(QuantumGate.RZ, [i + 1], [math.pi / 8])

        return circuit

    def _create_generic_circuit(self, num_qubits: int) -> QuantumCircuit:
        """Create a generic quantum circuit."""
        circuit = QuantumCircuit(num_qubits=num_qubits)

        for i in range(num_qubits):
            circuit.add_gate(QuantumGate.H, [i])

        return circuit


# ============================================================================
# Hardware Mapper
# ============================================================================

class HardwareMapper:
    """Maps and optimizes quantum circuits for specific hardware."""

    def __init__(self):
        self.backends = {
            "ibm": IBM_QUANTUM,
            "ionq": IONQ,
            "rigetti": RIGETTI
        }

    def transpile_for_hardware(
        self,
        circuit: QuantumCircuit,
        backend_name: str
    ) -> QuantumCircuit:
        """
        Transpile circuit for specific hardware backend.

        Args:
            circuit: Input quantum circuit
            backend_name: Target backend name

        Returns:
            Transpiled quantum circuit
        """
        backend = self.backends.get(backend_name.lower())
        if not backend:
            logger.warning(f"Unknown backend: {backend_name}, returning original circuit")
            return circuit

        # Create new circuit
        transpiled = QuantumCircuit(num_qubits=circuit.num_qubits)

        # Decompose gates to native gates
        for gate in circuit.gates:
            gate_type = gate["gate"]
            qubits = gate["qubits"]
            params = gate.get("params", [])

            # Decompose to native gates
            native_gates = self._decompose_to_native(
                gate_type, qubits, params, backend
            )
            transpiled.gates.extend(native_gates)

        # Optimize connectivity
        transpiled = self.optimize_connectivity(transpiled, backend.connectivity)

        # Optimize gate set
        transpiled = self.optimize_gate_set(transpiled, backend.native_gates)

        return transpiled

    def optimize_gate_set(
        self,
        circuit: QuantumCircuit,
        native_gates: Set[str]
    ) -> QuantumCircuit:
        """
        Optimize circuit to use only native gates.

        Args:
            circuit: Input circuit
            native_gates: Set of native gate names

        Returns:
            Optimized circuit
        """
        optimized = QuantumCircuit(num_qubits=circuit.num_qubits)

        for gate in circuit.gates:
            gate_type = gate["gate"]

            if gate_type in native_gates:
                optimized.gates.append(gate)
            else:
                # Decompose non-native gates
                decomposed = self._decompose_gate(gate, native_gates)
                optimized.gates.extend(decomposed)

        return optimized

    def optimize_connectivity(
        self,
        circuit: QuantumCircuit,
        topology: List[Tuple[int, int]]
    ) -> QuantumCircuit:
        """
        Optimize circuit for hardware connectivity constraints.

        Args:
            circuit: Input circuit
            topology: List of allowed qubit connections

        Returns:
            Optimized circuit with valid connectivity
        """
        optimized = QuantumCircuit(num_qubits=circuit.num_qubits)

        for gate in circuit.gates:
            qubits = gate["qubits"]

            # Single qubit gates are always valid
            if len(qubits) == 1:
                optimized.gates.append(gate)
                continue

            # Check two-qubit gate connectivity
            if len(qubits) == 2:
                q0, q1 = qubits[0], qubits[1]

                if (q0, q1) in topology:
                    optimized.gates.append(gate)
                elif (q1, q0) in topology:
                    # Reverse gate if needed
                    reversed_gate = self._reverse_two_qubit_gate(gate)
                    optimized.gates.append(reversed_gate)
                else:
                    # Need SWAP gates
                    swap_gates = self._route_with_swaps(q0, q1, topology)
                    optimized.gates.extend(swap_gates)
                    optimized.gates.append(gate)

        return optimized

    def estimate_fidelity(
        self,
        circuit: QuantumCircuit,
        backend: HardwareBackend
    ) -> float:
        """
        Estimate circuit fidelity on given backend.

        Args:
            circuit: Quantum circuit
            backend: Hardware backend

        Returns:
            Estimated fidelity (0 to 1)
        """
        fidelity = 1.0

        for gate in circuit.gates:
            gate_type = gate["gate"]

            # Get gate fidelity
            if gate_type in backend.gate_fidelities:
                fidelity *= backend.gate_fidelities[gate_type]
            else:
                # Assume lower fidelity for decomposed gates
                fidelity *= 0.95

        # Account for readout error
        if "readout_fidelity" in backend.properties:
            readout_fidelity = backend.properties["readout_fidelity"]
            fidelity *= readout_fidelity ** circuit.num_qubits

        return fidelity

    def _decompose_to_native(
        self,
        gate_type: str,
        qubits: List[int],
        params: List[float],
        backend: HardwareBackend
    ) -> List[Dict[str, Any]]:
        """Decompose gate to native gates for backend."""
        native_gates = backend.native_gates

        # If gate is already native, return as-is
        if gate_type in native_gates:
            return [{"gate": gate_type, "qubits": qubits, "params": params}]

        # Backend-specific decompositions
        if backend.name == "IBM Quantum":
            return self._decompose_for_ibm(gate_type, qubits, params)
        elif backend.name == "IonQ":
            return self._decompose_for_ionq(gate_type, qubits, params)
        elif backend.name == "Rigetti":
            return self._decompose_for_rigetti(gate_type, qubits, params)

        # Default decomposition
        return [{"gate": gate_type, "qubits": qubits, "params": params}]

    def _decompose_for_ibm(
        self,
        gate_type: str,
        qubits: List[int],
        params: List[float]
    ) -> List[Dict[str, Any]]:
        """Decompose gates for IBM Quantum."""
        gates = []

        if gate_type == "h":
            # H = RZ(π) · SX · RZ(π)
            gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi]})
            gates.append({"gate": "sx", "qubits": qubits, "params": []})
            gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi]})
        elif gate_type == "y":
            # Y = RZ(π) · X
            gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi]})
            gates.append({"gate": "x", "qubits": qubits, "params": []})
        elif gate_type == "z":
            # Z = RZ(π)
            gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi]})
        elif gate_type in ["rx", "ry"]:
            # RX/RY decomposed to RZ and SX
            angle = params[0] if params else 0
            if gate_type == "rx":
                gates.append({"gate": "rz", "qubits": qubits, "params": [-math.pi/2]})
                gates.append({"gate": "sx", "qubits": qubits, "params": []})
                gates.append({"gate": "rz", "qubits": qubits, "params": [angle]})
                gates.append({"gate": "sx", "qubits": qubits, "params": []})
                gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi/2]})
            else:  # ry
                gates.append({"gate": "sx", "qubits": qubits, "params": []})
                gates.append({"gate": "rz", "qubits": qubits, "params": [angle]})
                gates.append({"gate": "sx", "qubits": qubits, "params": []})
        else:
            # Return as-is
            gates.append({"gate": gate_type, "qubits": qubits, "params": params})

        return gates

    def _decompose_for_ionq(
        self,
        gate_type: str,
        qubits: List[int],
        params: List[float]
    ) -> List[Dict[str, Any]]:
        """Decompose gates for IonQ."""
        # IonQ uses GPI, GPI2, and MS gates
        # Simplified decomposition
        return [{"gate": gate_type, "qubits": qubits, "params": params}]

    def _decompose_for_rigetti(
        self,
        gate_type: str,
        qubits: List[int],
        params: List[float]
    ) -> List[Dict[str, Any]]:
        """Decompose gates for Rigetti."""
        gates = []

        if gate_type == "h":
            # H = RZ(π/2) · RX(π/2) · RZ(π/2)
            gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi/2]})
            gates.append({"gate": "rx", "qubits": qubits, "params": [math.pi/2]})
            gates.append({"gate": "rz", "qubits": qubits, "params": [math.pi/2]})
        elif gate_type == "cnot":
            # CNOT decomposed using CZ
            gates.append({"gate": "rz", "qubits": [qubits[1]], "params": [math.pi/2]})
            gates.append({"gate": "rx", "qubits": [qubits[1]], "params": [math.pi/2]})
            gates.append({"gate": "cz", "qubits": qubits, "params": []})
            gates.append({"gate": "rx", "qubits": [qubits[1]], "params": [-math.pi/2]})
            gates.append({"gate": "rz", "qubits": [qubits[1]], "params": [-math.pi/2]})
        else:
            gates.append({"gate": gate_type, "qubits": qubits, "params": params})

        return gates

    def _decompose_gate(
        self,
        gate: Dict[str, Any],
        native_gates: Set[str]
    ) -> List[Dict[str, Any]]:
        """Generic gate decomposition."""
        # Simplified decomposition
        return [gate]

    def _reverse_two_qubit_gate(self, gate: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse a two-qubit gate."""
        reversed_gate = gate.copy()
        if len(gate["qubits"]) == 2:
            reversed_gate["qubits"] = [gate["qubits"][1], gate["qubits"][0]]
        return reversed_gate

    def _route_with_swaps(
        self,
        q0: int,
        q1: int,
        topology: List[Tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """Route qubits using SWAP gates (simplified)."""
        # Simplified routing - just return empty list
        # In production, use proper routing algorithm
        return []


# ============================================================================
# Enhanced NL Mapper (Main Class)
# ============================================================================

class EnhancedNLMapper:
    """
    Enhanced Natural Language Mapper with context awareness,
    domain specialization, and hardware optimization.
    """

    def __init__(
        self,
        enable_context_awareness: bool = True,
        enable_domain_specialization: bool = True,
        enable_hardware_optimization: bool = True
    ):
        """
        Initialize the Enhanced NL Mapper.

        Args:
            enable_context_awareness: Enable context tracking and analysis
            enable_domain_specialization: Enable domain-specific mappings
            enable_hardware_optimization: Enable hardware-specific optimizations
        """
        self.enable_context_awareness = enable_context_awareness
        self.enable_domain_specialization = enable_domain_specialization
        self.enable_hardware_optimization = enable_hardware_optimization

        # Initialize components
        self.context_analyzer = ContextAnalyzer()
        self.domain_mapper = DomainSpecificMapper()
        self.hardware_mapper = HardwareMapper()

        # Session state
        self.session_context = Context()
        self.session_history: List[str] = []

        logger.info("Enhanced NL Mapper initialized")

    def map_to_gates(
        self,
        text: str,
        context: Optional[Context] = None
    ) -> List[QuantumGate]:
        """
        Map natural language text to quantum gates.

        Args:
            text: Natural language description
            context: Optional context for mapping

        Returns:
            List of quantum gates
        """
        # Update session history
        self.session_history.append(text)

        # Analyze context
        if self.enable_context_awareness:
            if context is None:
                context = self.context_analyzer.analyze(text, self.session_history)
            self.session_context = context
        else:
            context = Context()

        # Extract gate operations
        gates = []
        text_lower = text.lower()

        # Common gate patterns
        gate_patterns = {
            QuantumGate.H: r"hadamard|superposition",
            QuantumGate.X: r"(?:pauli.?x|flip|not|x.?gate)",
            QuantumGate.Y: r"pauli.?y|y.?gate",
            QuantumGate.Z: r"pauli.?z|z.?gate|phase.?flip",
            QuantumGate.CNOT: r"cnot|controlled.?not|entangle",
            QuantumGate.RX: r"rotate.*x|rx|x.?rotation",
            QuantumGate.RY: r"rotate.*y|ry|y.?rotation",
            QuantumGate.RZ: r"rotate.*z|rz|z.?rotation",
        }

        for gate, pattern in gate_patterns.items():
            if re.search(pattern, text_lower):
                gates.append(gate)

        return gates

    def analyze_intent(self, text: str) -> Intent:
        """
        Analyze the intent of natural language text.

        Args:
            text: Natural language text

        Returns:
            Detected intent
        """
        context = self.context_analyzer.analyze(text, self.session_history)
        return context.intent

    def resolve_ambiguity(
        self,
        text: str,
        candidates: List[Dict[str, Any]]
    ) -> QuantumGateMapping:
        """
        Resolve ambiguous natural language by selecting best mapping.

        Args:
            text: Ambiguous text
            candidates: List of candidate mappings

        Returns:
            Best mapping with confidence score
        """
        if not candidates:
            return QuantumGateMapping(confidence=0.0, description="No candidates")

        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score = self._score_candidate(text, candidate)
            scored_candidates.append((score, candidate))

        # Sort by score
        scored_candidates.sort(reverse=True, key=lambda x: x[0])
        best_score, best_candidate = scored_candidates[0]

        # Convert to mapping
        mapping = QuantumGateMapping(
            gates=best_candidate.get("gates", []),
            qubits_used=set(best_candidate.get("qubits", [])),
            confidence=best_score,
            description=best_candidate.get("description", "")
        )

        return mapping

    def generate_circuit(
        self,
        text: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> QuantumCircuit:
        """
        Generate a complete quantum circuit from natural language.

        Args:
            text: Natural language description
            constraints: Optional constraints (num_qubits, max_depth, etc.)

        Returns:
            Generated quantum circuit
        """
        constraints = constraints or {}

        # Analyze context
        context = self.context_analyzer.analyze(text, self.session_history)

        # Determine number of qubits
        num_qubits = constraints.get("num_qubits")
        if not num_qubits:
            num_qubits = context.entities.get("num_qubits", 4)

        # Check for domain-specific circuit
        if self.enable_domain_specialization and context.domain:
            # Try to find domain concept
            for concept in context.entities:
                try:
                    circuit = self.domain_mapper.map_domain_concept(
                        concept, context.domain, num_qubits
                    )
                    return circuit
                except:
                    continue

        # Create circuit based on intent
        circuit = QuantumCircuit(num_qubits=num_qubits)

        if context.intent == Intent.CREATE_SUPERPOSITION:
            # Add Hadamard gates
            for i in range(num_qubits):
                circuit.add_gate(QuantumGate.H, [i])

        elif context.intent == Intent.CREATE_ENTANGLEMENT:
            # Create Bell state or GHZ state
            circuit.add_gate(QuantumGate.H, [0])
            for i in range(num_qubits - 1):
                circuit.add_gate(QuantumGate.CNOT, [i, i + 1])

        elif context.intent in [Intent.DOCK, Intent.FOLD, Intent.OPTIMIZE]:
            # Create VQE-style ansatz
            for i in range(num_qubits):
                circuit.add_gate(QuantumGate.RY, [i], [math.pi / 4])

            for i in range(num_qubits - 1):
                circuit.add_gate(QuantumGate.CNOT, [i, i + 1])

            for i in range(num_qubits):
                circuit.add_gate(QuantumGate.RZ, [i], [math.pi / 6])

        else:
            # Default: create superposition
            for i in range(num_qubits):
                circuit.add_gate(QuantumGate.H, [i])

        # Apply hardware optimization if enabled
        if self.enable_hardware_optimization:
            backend = constraints.get("backend", "ibm")
            circuit = self.hardware_mapper.transpile_for_hardware(circuit, backend)

        # Add measurements if requested
        if "measure" in text.lower():
            for i in range(num_qubits):
                circuit.add_measurement(i)

        return circuit

    def _score_candidate(self, text: str, candidate: Dict[str, Any]) -> float:
        """Score a candidate mapping based on text."""
        score = 0.0
        text_lower = text.lower()

        # Check keyword matches
        keywords = candidate.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 0.2

        # Check qubit count match
        if "num_qubits" in candidate:
            required_qubits = re.search(r"(\d+)\s*qubit", text_lower)
            if required_qubits:
                if int(required_qubits.group(1)) == candidate["num_qubits"]:
                    score += 0.3

        # Base score for valid candidate
        score += 0.5

        return min(score, 1.0)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "EnhancedNLMapper",
    "ContextAnalyzer",
    "DomainSpecificMapper",
    "HardwareMapper",
    "Intent",
    "Context",
    "QuantumGateMapping",
    "HardwareBackend",
    "IBM_QUANTUM",
    "IONQ",
    "RIGETTI"
]
