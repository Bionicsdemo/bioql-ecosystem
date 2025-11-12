"""
Natural Language Parser for BioQL

This module converts natural language descriptions into BioQL IR using
schema-guided extraction and pattern matching.
"""

import re
from typing import Any, Dict, List, Optional, Pattern, Tuple, Union

# Optional loguru import
try:
    from loguru import logger
except ImportError:
    # Fallback to standard logging
    import logging
    logger = logging.getLogger(__name__)

from bioql.ir import (
    AlignmentOperation,
    BioQLDomain,
    BioQLParameter,
    BioQLProgram,
    DataType,
    DockingOperation,
    Molecule,
    QuantumOptimizationOperation,
    QuantumBackend,
)


class ParseError(Exception):
    """Exception raised when parsing fails."""
    pass


class PatternMatcher:
    """Pattern matching utilities for natural language processing."""

    def __init__(self):
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, Pattern[str]]:
        """Compile regex patterns for entity extraction."""
        return {
            # Molecular identifiers
            "pdb_id": re.compile(r"\b([1-9][A-Za-z0-9]{3})\b", re.IGNORECASE),
            "smiles": re.compile(r"\b([CONSPFHcnopsfh\[\]()@=#\-+\\\/]+)\b"),
            "sequence": re.compile(r"\b([ACDEFGHIKLMNPQRSTVWY]{3,})\b"),

            # Operations
            "docking": re.compile(r"\b(dock|docking|bind|binding|complex|pose)\b", re.IGNORECASE),
            "alignment": re.compile(r"\b(align|alignment|match|sequence)\b", re.IGNORECASE),
            "optimization": re.compile(r"\b(optimize|optimization|minimize|energy)\b", re.IGNORECASE),

            # Parameters
            "energy": re.compile(r"(-?\d+(?:\.\d+)?)\s*(kcal|kj|ev|hartree)", re.IGNORECASE),
            "poses": re.compile(r"(\d+)\s*poses?", re.IGNORECASE),
            "shots": re.compile(r"(\d+)\s*shots?", re.IGNORECASE),

            # File formats
            "pdb_file": re.compile(r"(\S+\.pdb)", re.IGNORECASE),
            "mol2_file": re.compile(r"(\S+\.mol2)", re.IGNORECASE),
            "sdf_file": re.compile(r"(\S+\.sdf)", re.IGNORECASE),
            "fasta_file": re.compile(r"(\S+\.fasta)", re.IGNORECASE),

            # Quantum backends
            "backend": re.compile(r"\b(qiskit|cirq|pennylane|braket|simulator)\b", re.IGNORECASE),
        }

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using compiled patterns."""
        entities = {}
        for entity_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                entities[entity_type] = matches
        return entities

    def detect_domain(self, text: str) -> Optional[BioQLDomain]:
        """Detect the computational domain from text."""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ["dock", "binding", "complex", "pose"]):
            return BioQLDomain.DOCKING
        elif any(keyword in text_lower for keyword in ["align", "sequence", "match"]):
            return BioQLDomain.ALIGNMENT
        elif any(keyword in text_lower for keyword in ["optimize", "energy", "minimize"]):
            return BioQLDomain.OPTIMIZATION

        return None


class MoleculeExtractor:
    """Extracts molecule information from natural language."""

    def __init__(self, pattern_matcher: PatternMatcher):
        self.pattern_matcher = pattern_matcher

    def extract_molecules(self, text: str) -> List[Molecule]:
        """Extract molecule definitions from text."""
        molecules = []
        entities = self.pattern_matcher.extract_entities(text)

        # Extract PDB molecules
        if "pdb_id" in entities:
            for pdb_id in entities["pdb_id"]:
                molecules.append(Molecule(
                    id=f"pdb_{pdb_id}",
                    type=DataType.PROTEIN,
                    format="pdb",
                    data=pdb_id,
                    name=f"PDB structure {pdb_id}"
                ))

        # Extract SMILES molecules
        if "smiles" in entities:
            for i, smiles in enumerate(entities["smiles"]):
                molecules.append(Molecule(
                    id=f"smiles_{i}",
                    type=DataType.LIGAND,
                    format="smiles",
                    data=smiles,
                    name=f"SMILES ligand {i}"
                ))

        # Extract sequence molecules
        if "sequence" in entities:
            for i, sequence in enumerate(entities["sequence"]):
                # Determine if DNA/RNA or protein
                mol_type = DataType.PROTEIN
                if all(base in "ATCGUN" for base in sequence.upper()):
                    mol_type = DataType.DNA if "T" in sequence.upper() else DataType.RNA

                molecules.append(Molecule(
                    id=f"sequence_{i}",
                    type=mol_type,
                    format="fasta",
                    data=sequence,
                    name=f"Sequence {i}"
                ))

        # Extract file-based molecules
        file_patterns = ["pdb_file", "mol2_file", "sdf_file", "fasta_file"]
        for pattern_name in file_patterns:
            if pattern_name in entities:
                for file_path in entities[pattern_name]:
                    format_type = pattern_name.split("_")[0]
                    mol_type = self._infer_molecule_type(format_type)

                    molecules.append(Molecule(
                        id=f"file_{file_path}",
                        type=mol_type,
                        format=format_type,
                        data=file_path,
                        name=f"Molecule from {file_path}"
                    ))

        return molecules

    def _infer_molecule_type(self, format_type: str) -> DataType:
        """Infer molecule type from file format."""
        if format_type in ["pdb"]:
            return DataType.PROTEIN
        elif format_type in ["mol2", "sdf"]:
            return DataType.LIGAND
        elif format_type in ["fasta"]:
            return DataType.PROTEIN  # Could be DNA/RNA, but default to protein
        else:
            return DataType.PROTEIN


class ParameterExtractor:
    """Extracts parameters from natural language."""

    def __init__(self, pattern_matcher: PatternMatcher):
        self.pattern_matcher = pattern_matcher

    def extract_parameters(self, text: str) -> List[BioQLParameter]:
        """Extract parameters from text."""
        parameters = []
        entities = self.pattern_matcher.extract_entities(text)

        # Extract energy parameters
        if "energy" in entities:
            for energy_match in entities["energy"]:
                if isinstance(energy_match, tuple) and len(energy_match) == 2:
                    value, unit = energy_match
                    parameters.append(BioQLParameter(
                        name="energy_threshold",
                        value=float(value),
                        unit=unit,
                        description="Energy threshold for filtering"
                    ))

        # Extract number of poses
        if "poses" in entities:
            for poses_str in entities["poses"]:
                parameters.append(BioQLParameter(
                    name="num_poses",
                    value=int(poses_str),
                    description="Number of poses to generate"
                ))

        # Extract quantum shots
        if "shots" in entities:
            for shots_str in entities["shots"]:
                parameters.append(BioQLParameter(
                    name="shots",
                    value=int(shots_str),
                    description="Number of quantum shots"
                ))

        return parameters


class NaturalLanguageParser:
    """Main parser for converting natural language to BioQL IR."""

    def __init__(self):
        self.pattern_matcher = PatternMatcher()
        self.molecule_extractor = MoleculeExtractor(self.pattern_matcher)
        self.parameter_extractor = ParameterExtractor(self.pattern_matcher)

    def parse(self, text: str, program_name: Optional[str] = None) -> BioQLProgram:
        """
        Parse natural language text into a BioQL program.

        Args:
            text: Natural language description
            program_name: Optional program name

        Returns:
            BioQLProgram instance

        Raises:
            ParseError: If parsing fails
        """
        try:
            logger.info(f"Parsing text: {text[:100]}...")

            # Detect domain
            domain = self.pattern_matcher.detect_domain(text)
            if not domain:
                raise ParseError("Could not detect computational domain from text")

            # Extract molecules and parameters
            molecules = self.molecule_extractor.extract_molecules(text)
            parameters = self.parameter_extractor.extract_parameters(text)

            # Extract backend preference
            entities = self.pattern_matcher.extract_entities(text)
            backend = QuantumBackend.SIMULATOR
            if "backend" in entities:
                backend_str = entities["backend"][0].lower()
                if backend_str in [b.value for b in QuantumBackend]:
                    backend = QuantumBackend(backend_str)

            # Create operation based on domain
            operations = []
            if domain == BioQLDomain.DOCKING:
                operations.append(self._create_docking_operation(text, molecules, parameters))
            elif domain == BioQLDomain.ALIGNMENT:
                operations.append(self._create_alignment_operation(text, molecules, parameters))
            elif domain == BioQLDomain.OPTIMIZATION:
                operations.append(self._create_optimization_operation(text, molecules, parameters))

            # Create program
            program = BioQLProgram(
                name=program_name or "Parsed BioQL Program",
                description=f"Generated from: {text}",
                inputs=molecules,
                operations=operations,
                backend=backend
            )

            # Add audit entry
            program.add_audit_entry("parsed", {
                "source": "natural_language",
                "domain": domain.value,
                "input_text": text
            })

            logger.success(f"Successfully parsed program with {len(operations)} operations")
            return program

        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            raise ParseError(f"Failed to parse text: {e}")

    def _create_docking_operation(
        self,
        text: str,
        molecules: List[Molecule],
        parameters: List[BioQLParameter]
    ) -> DockingOperation:
        """Create a docking operation from extracted information."""
        # Find receptor and ligand
        receptor = None
        ligand = None

        for mol in molecules:
            if mol.type == DataType.PROTEIN:
                receptor = mol
            elif mol.type == DataType.LIGAND:
                ligand = mol

        if not receptor:
            # Create a default receptor if none found
            receptor = Molecule(
                id="default_receptor",
                type=DataType.PROTEIN,
                format="pdb",
                data="receptor.pdb",
                name="Default receptor"
            )

        if not ligand:
            # Create a default ligand if none found
            ligand = Molecule(
                id="default_ligand",
                type=DataType.LIGAND,
                format="smiles",
                data="CCO",  # ethanol as default
                name="Default ligand"
            )

        # Extract docking-specific parameters
        num_poses = 10
        energy_threshold = -6.0

        for param in parameters:
            if param.name == "num_poses":
                num_poses = int(param.value)
            elif param.name == "energy_threshold":
                energy_threshold = float(param.value)

        return DockingOperation(
            description=f"Docking operation from: {text}",
            receptor=receptor,
            ligand=ligand,
            num_poses=num_poses,
            energy_threshold=energy_threshold,
            parameters=parameters
        )

    def _create_alignment_operation(
        self,
        text: str,
        molecules: List[Molecule],
        parameters: List[BioQLParameter]
    ) -> AlignmentOperation:
        """Create an alignment operation from extracted information."""
        # Need at least 2 sequences for alignment
        sequences = [mol for mol in molecules if mol.type in [DataType.PROTEIN, DataType.DNA, DataType.RNA]]

        if len(sequences) < 2:
            # Create default sequences if needed
            while len(sequences) < 2:
                sequences.append(Molecule(
                    id=f"default_seq_{len(sequences)}",
                    type=DataType.PROTEIN,
                    format="fasta",
                    data="ACDEFGHIKLMNPQRSTVWY",
                    name=f"Default sequence {len(sequences)}"
                ))

        return AlignmentOperation(
            description=f"Alignment operation from: {text}",
            sequences=sequences,
            parameters=parameters
        )

    def _create_optimization_operation(
        self,
        text: str,
        molecules: List[Molecule],
        parameters: List[BioQLParameter]
    ) -> QuantumOptimizationOperation:
        """Create an optimization operation from extracted information."""
        # Default optimization variables
        variables = parameters or [
            BioQLParameter(
                name="energy",
                value=0.0,
                unit="kcal/mol",
                description="Energy to minimize"
            )
        ]

        return QuantumOptimizationOperation(
            description=f"Optimization operation from: {text}",
            objective_function="minimize_energy",
            variables=variables,
            parameters=parameters
        )


# Export main classes
__all__ = [
    "NaturalLanguageParser",
    "PatternMatcher",
    "MoleculeExtractor",
    "ParameterExtractor",
    "ParseError"
]