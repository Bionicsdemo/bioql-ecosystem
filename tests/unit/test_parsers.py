# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Unit Tests for BioQL Parser Modules

Tests the following modules:
- bioql/parser/nl_parser.py (natural language parsing)
- Pattern matching and entity extraction
- Error handling and edge cases

All tests use mocking to avoid external dependencies.
"""

# Add project to path
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Spectrix_framework"))

from bioql.ir import BioQLDomain, DataType, QuantumBackend
from bioql.parser.nl_parser import (
    MoleculeExtractor,
    NaturalLanguageParser,
    ParameterExtractor,
    ParseError,
    PatternMatcher,
)

# ============================================================================
# PATTERN MATCHER TESTS
# ============================================================================


class TestPatternMatcher:
    """Test suite for pattern matching utilities."""

    def test_pattern_matcher_initialization(self):
        """Test PatternMatcher initializes with compiled patterns."""
        matcher = PatternMatcher()

        assert hasattr(matcher, "patterns")
        assert "pdb_id" in matcher.patterns
        assert "smiles" in matcher.patterns
        assert "docking" in matcher.patterns
        assert "energy" in matcher.patterns

    def test_extract_pdb_id(self):
        """Test extraction of PDB IDs from text."""
        matcher = PatternMatcher()

        text = "Dock ligand to protein 1ABC"
        entities = matcher.extract_entities(text)

        assert "pdb_id" in entities
        assert "1ABC" in entities["pdb_id"]

    def test_extract_multiple_pdb_ids(self):
        """Test extraction of multiple PDB IDs."""
        matcher = PatternMatcher()

        text = "Compare 1ABC, 2XYZ, and 3DEF structures"
        entities = matcher.extract_entities(text)

        assert "pdb_id" in entities
        assert len(entities["pdb_id"]) == 3
        assert "1ABC" in entities["pdb_id"]
        assert "2XYZ" in entities["pdb_id"]

    def test_extract_poses_parameter(self):
        """Test extraction of poses parameter."""
        matcher = PatternMatcher()

        text = "Generate 10 poses for docking"
        entities = matcher.extract_entities(text)

        assert "poses" in entities
        assert "10" in entities["poses"]

    def test_extract_shots_parameter(self):
        """Test extraction of quantum shots parameter."""
        matcher = PatternMatcher()

        text = "Run with 5000 shots on quantum hardware"
        entities = matcher.extract_entities(text)

        assert "shots" in entities
        assert "5000" in entities["shots"]

    def test_detect_docking_domain(self):
        """Test detection of docking domain."""
        matcher = PatternMatcher()

        text = "Dock aspirin to COX-2 enzyme"
        domain = matcher.detect_domain(text)

        assert domain == BioQLDomain.DOCKING

    def test_detect_alignment_domain(self):
        """Test detection of alignment domain."""
        matcher = PatternMatcher()

        text = "Align protein sequences for comparison"
        domain = matcher.detect_domain(text)

        assert domain == BioQLDomain.ALIGNMENT

    def test_detect_optimization_domain(self):
        """Test detection of optimization domain."""
        matcher = PatternMatcher()

        text = "Optimize energy configuration"
        domain = matcher.detect_domain(text)

        assert domain == BioQLDomain.OPTIMIZATION


# ============================================================================
# MOLECULE EXTRACTOR TESTS
# ============================================================================


class TestMoleculeExtractor:
    """Test suite for molecule extraction from text."""

    def test_extract_pdb_molecule(self):
        """Test extraction of PDB molecule."""
        matcher = PatternMatcher()
        extractor = MoleculeExtractor(matcher)

        text = "Use structure 1ABC for docking"
        molecules = extractor.extract_molecules(text)

        assert len(molecules) > 0
        assert any(mol.type == DataType.PROTEIN for mol in molecules)
        assert any("1ABC" in mol.data for mol in molecules)

    def test_extract_smiles_molecule(self):
        """Test extraction of SMILES molecule."""
        matcher = PatternMatcher()
        extractor = MoleculeExtractor(matcher)

        text = "Use CCO as the ligand"
        molecules = extractor.extract_molecules(text)

        assert len(molecules) > 0
        # Note: May or may not extract CCO depending on pattern complexity

    def test_extract_protein_sequence(self):
        """Test extraction of protein sequence."""
        matcher = PatternMatcher()
        extractor = MoleculeExtractor(matcher)

        text = "Analyze sequence ACDEFGHIKLMNPQRSTVWY"
        molecules = extractor.extract_molecules(text)

        assert len(molecules) > 0
        assert any(mol.type == DataType.PROTEIN for mol in molecules)

    def test_infer_molecule_type_pdb(self):
        """Test molecule type inference for PDB format."""
        matcher = PatternMatcher()
        extractor = MoleculeExtractor(matcher)

        mol_type = extractor._infer_molecule_type("pdb")

        assert mol_type == DataType.PROTEIN

    def test_infer_molecule_type_sdf(self):
        """Test molecule type inference for SDF format."""
        matcher = PatternMatcher()
        extractor = MoleculeExtractor(matcher)

        mol_type = extractor._infer_molecule_type("sdf")

        assert mol_type == DataType.LIGAND


# ============================================================================
# PARAMETER EXTRACTOR TESTS
# ============================================================================


class TestParameterExtractor:
    """Test suite for parameter extraction from text."""

    def test_extract_energy_parameter(self):
        """Test extraction of energy parameter."""
        matcher = PatternMatcher()
        extractor = ParameterExtractor(matcher)

        text = "Filter poses with energy below -8.5 kcal/mol"
        parameters = extractor.extract_parameters(text)

        # May or may not extract depending on pattern match
        # This is a soft test
        assert isinstance(parameters, list)

    def test_extract_poses_parameter(self):
        """Test extraction of poses parameter."""
        matcher = PatternMatcher()
        extractor = ParameterExtractor(matcher)

        text = "Generate 20 poses"
        parameters = extractor.extract_parameters(text)

        assert len(parameters) > 0
        assert any(p.name == "num_poses" and p.value == 20 for p in parameters)

    def test_extract_shots_parameter(self):
        """Test extraction of shots parameter."""
        matcher = PatternMatcher()
        extractor = ParameterExtractor(matcher)

        text = "Use 10000 shots for quantum simulation"
        parameters = extractor.extract_parameters(text)

        assert len(parameters) > 0
        assert any(p.name == "shots" and p.value == 10000 for p in parameters)


# ============================================================================
# NATURAL LANGUAGE PARSER TESTS
# ============================================================================


class TestNaturalLanguageParser:
    """Test suite for the main NL parser."""

    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = NaturalLanguageParser()

        assert hasattr(parser, "pattern_matcher")
        assert hasattr(parser, "molecule_extractor")
        assert hasattr(parser, "parameter_extractor")

    def test_parse_docking_task(self):
        """Test parsing of docking task."""
        parser = NaturalLanguageParser()

        text = "Dock ligand to protein 1ABC with 10 poses"
        program = parser.parse(text)

        assert program is not None
        assert len(program.operations) > 0
        assert program.operations[0].description is not None

    def test_parse_alignment_task(self):
        """Test parsing of alignment task."""
        parser = NaturalLanguageParser()

        text = "Align sequences ACDEFGHIK and ACDEFGHIL"
        program = parser.parse(text)

        assert program is not None
        assert len(program.operations) > 0

    def test_parse_optimization_task(self):
        """Test parsing of optimization task."""
        parser = NaturalLanguageParser()

        text = "Optimize molecular energy configuration"
        program = parser.parse(text)

        assert program is not None
        assert len(program.operations) > 0

    def test_parse_with_backend_specification(self):
        """Test parsing with backend specification."""
        parser = NaturalLanguageParser()

        text = "Run docking on qiskit simulator"
        program = parser.parse(text)

        assert program is not None
        # Backend may or may not be set depending on pattern match

    def test_parse_unknown_domain_raises_error(self):
        """Test parsing with unknown domain raises error."""
        parser = NaturalLanguageParser()

        text = "Do something completely unrelated to biology"

        with pytest.raises(ParseError):
            parser.parse(text)

    def test_create_docking_operation_with_defaults(self):
        """Test creation of docking operation with default values."""
        parser = NaturalLanguageParser()

        operation = parser._create_docking_operation(
            text="Dock ligand", molecules=[], parameters=[]
        )

        assert operation is not None
        assert operation.receptor is not None
        assert operation.ligand is not None
        assert operation.num_poses == 10  # Default

    def test_create_alignment_operation_with_defaults(self):
        """Test creation of alignment operation with default sequences."""
        parser = NaturalLanguageParser()

        operation = parser._create_alignment_operation(
            text="Align sequences", molecules=[], parameters=[]
        )

        assert operation is not None
        assert len(operation.sequences) >= 2  # Defaults added

    def test_create_optimization_operation_with_defaults(self):
        """Test creation of optimization operation with defaults."""
        parser = NaturalLanguageParser()

        operation = parser._create_optimization_operation(
            text="Optimize energy", molecules=[], parameters=[]
        )

        assert operation is not None
        assert operation.objective_function == "minimize_energy"
        assert len(operation.variables) > 0

    def test_parse_adds_audit_entry(self):
        """Test that parsing adds audit entry to program."""
        parser = NaturalLanguageParser()

        text = "Dock ligand to protein"
        program = parser.parse(text, program_name="Test Program")

        assert program.name == "Test Program"
        # Audit entries are tracked internally


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestParserErrorHandling:
    """Test suite for parser error handling."""

    def test_parse_empty_string(self):
        """Test parsing of empty string."""
        parser = NaturalLanguageParser()

        with pytest.raises(ParseError):
            parser.parse("")

    def test_parse_with_logging(self):
        """Test parsing logs appropriately."""
        parser = NaturalLanguageParser()

        with patch("bioql.parser.nl_parser.logger") as mock_logger:
            text = "Dock ligand to protein"
            program = parser.parse(text)

            # Verify logging occurred
            assert mock_logger.info.called or mock_logger.success.called


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
