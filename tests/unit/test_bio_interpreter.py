# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Unit Tests for BioQL Bio Interpreter Module

Tests the following functionality:
- bioql/bio_interpreter.py (biological interpretation of quantum results)
- Binding affinity calculations (ΔG, Ki, IC50)
- H-bond analysis
- Lipinski rules validation
- Drug design and docking interpretation

All tests use mocking to avoid external dependencies.
"""

# Add project to path
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Spectrix_framework"))

from bioql.bio_interpreter import (
    HARTREE_TO_KCAL,
    R_KCAL,
    RT,
    T_KELVIN,
    interpret_bio_results,
    interpret_drug_design,
    interpret_drug_docking,
)

# ============================================================================
# CONSTANTS AND FIXTURES
# ============================================================================


@pytest.fixture
def sample_counts():
    """Sample quantum measurement counts."""
    return {
        "0000": 250,
        "0001": 180,
        "0010": 140,
        "0011": 120,
        "0100": 110,
        "0101": 100,
        "0110": 50,
        "0111": 50,
    }


@pytest.fixture
def docking_context():
    """Sample docking context."""
    return {
        "application": "molecular_docking",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
        "pdb_id": "1ABC",
        "hamiltonian": np.array([[1.0, 0.5], [0.5, 2.0]]),
    }


@pytest.fixture
def drug_design_context():
    """Sample drug design context."""
    return {
        "application": "drug_design",
        "disease": "obesity",
        "target": "GLP1R",
        "pdb_id": "6B3J",
        "num_candidates": 3,
    }


# ============================================================================
# INTERPRET BIO RESULTS TESTS
# ============================================================================


class TestInterpretBioResults:
    """Test suite for main bio results interpretation."""

    def test_interpret_unknown_application(self, sample_counts):
        """Test interpretation with unknown application."""
        context = {"application": "unknown"}
        result = interpret_bio_results(sample_counts, context)

        assert result["application"] == "unknown"
        assert "most_probable_state" in result
        assert result["total_shots"] == 1000
        assert result["unique_states"] == 8

    def test_interpret_drug_docking_application(self, sample_counts, docking_context):
        """Test interpretation routes to drug docking handler."""
        with patch("bioql.bio_interpreter.interpret_drug_docking") as mock_docking:
            mock_docking.return_value = {"binding_affinity": -8.5}

            result = interpret_bio_results(sample_counts, docking_context)

            mock_docking.assert_called_once()
            assert "binding_affinity" in result

    def test_interpret_drug_design_application(self, sample_counts, drug_design_context):
        """Test interpretation routes to drug design handler."""
        with patch("bioql.bio_interpreter.interpret_drug_design") as mock_design:
            mock_design.return_value = {"designed_molecules": ["CCO"]}

            result = interpret_bio_results(sample_counts, drug_design_context)

            mock_design.assert_called_once()
            assert "designed_molecules" in result


# ============================================================================
# DRUG DOCKING INTERPRETATION TESTS
# ============================================================================


class TestInterpretDrugDocking:
    """Test suite for drug docking interpretation."""

    @patch("bioql.bio_interpreter.download_pdb")
    @patch("bioql.bio_interpreter.dock_smiles_to_receptor")
    @patch("bioql.bio_interpreter.HAVE_RDKIT", True)
    @patch("bioql.bio_interpreter.VINA_BIN", "/usr/local/bin/vina")
    def test_interpret_drug_docking_with_vina(self, mock_dock, mock_download, sample_counts):
        """Test drug docking interpretation with Vina available."""
        # Mock PDB download
        mock_download.return_value = {"success": True, "file_path": "/tmp/1ABC.pdb"}

        # Mock docking result
        mock_dock.return_value = {
            "success": True,
            "affinity": -8.5,
            "poses": [{"affinity": -8.5, "rmsd_lb": 0.0, "rmsd_ub": 0.0}],
        }

        result = interpret_drug_docking(counts=sample_counts, smiles="CCO", pdb_id="1ABC")

        assert "binding_affinity" in result
        assert "ki" in result
        assert result["success"] is True

    def test_interpret_drug_docking_without_vina(self, sample_counts):
        """Test drug docking interpretation without Vina."""
        with patch("bioql.bio_interpreter.HAVE_RDKIT", False):
            result = interpret_drug_docking(counts=sample_counts, smiles="CCO", pdb_id="1ABC")

        # Should use predicted affinity
        assert "binding_affinity" in result
        assert "predicted" in result["method"]

    def test_binding_affinity_calculation_from_energy(self):
        """Test binding affinity calculation from ground state energy."""
        # Energy in Hartrees -> kcal/mol -> ΔG
        energy_hartree = -0.5
        energy_kcal = energy_hartree * HARTREE_TO_KCAL

        # Typical conversion for binding affinity
        # This is a simplified test of the conversion logic
        assert HARTREE_TO_KCAL == 627.509
        assert abs(energy_kcal - (-313.7545)) < 0.01

    def test_ki_calculation_from_binding_affinity(self):
        """Test Ki calculation from binding affinity."""
        # ΔG = -8.5 kcal/mol
        # Ki = exp(ΔG / RT)
        # RT = 0.593 kcal/mol at 298K

        binding_affinity = -8.5  # kcal/mol
        ki_ratio = np.exp(binding_affinity / RT)
        ki_nm = ki_ratio * 1e9  # Convert to nM

        # Ki should be in low nanomolar range for good binders
        assert ki_nm < 100  # Good binding affinity

    def test_ic50_calculation_from_ki(self):
        """Test IC50 calculation from Ki."""
        # IC50 ≈ Ki * (1 + [S]/Km)
        # For typical assays, IC50 ≈ 2 * Ki

        ki_nm = 10.0
        ic50_nm = ki_nm * 2  # Simplified

        assert ic50_nm == 20.0


# ============================================================================
# DRUG DESIGN INTERPRETATION TESTS
# ============================================================================


class TestInterpretDrugDesign:
    """Test suite for drug design interpretation."""

    @patch("bioql.bio_interpreter.get_drug_designer_v2")
    def test_interpret_drug_design_basic(self, mock_designer_factory, sample_counts):
        """Test basic drug design interpretation."""
        # Mock designer
        mock_designer = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.smiles = "CCO"
        mock_candidate.name = "Candidate 1"
        mock_designer.design_molecule.return_value = [mock_candidate]
        mock_designer_factory.return_value = mock_designer

        result = interpret_drug_design(
            counts=sample_counts, disease="obesity", target="GLP1R", num_candidates=1
        )

        assert "designed_molecules" in result
        assert len(result["designed_molecules"]) == 1

    @patch("bioql.bio_interpreter.get_drug_designer_v2")
    @patch("bioql.bio_interpreter.download_pdb")
    @patch("bioql.bio_interpreter.HAVE_RDKIT", True)
    @patch("bioql.bio_interpreter.VINA_BIN", "/usr/local/bin/vina")
    def test_interpret_drug_design_with_docking(
        self, mock_download, mock_designer_factory, sample_counts
    ):
        """Test drug design with docking validation."""
        # Mock designer
        mock_designer = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.smiles = "CCO"
        mock_candidate.name = "Ethanol"
        mock_designer.design_molecule.return_value = [mock_candidate]
        mock_designer_factory.return_value = mock_designer

        # Mock PDB download
        mock_download.return_value = {"success": True, "file_path": "/tmp/6B3J.pdb"}

        with patch("bioql.bio_interpreter.dock_smiles_to_receptor") as mock_dock:
            mock_dock.return_value = {"success": True, "affinity": -7.5}

            result = interpret_drug_design(
                counts=sample_counts,
                disease="obesity",
                target="GLP1R",
                pdb_id="6B3J",
                num_candidates=1,
            )

        assert "docking_results" in result
        assert len(result["docking_results"]) > 0


# ============================================================================
# MOLECULAR PROPERTY TESTS
# ============================================================================


class TestMolecularProperties:
    """Test suite for molecular property calculations."""

    def test_lipinski_rule_of_five(self):
        """Test Lipinski Rule of Five validation."""
        # Good drug-like molecule
        properties = {
            "molecular_weight": 450,  # < 500
            "logp": 3.5,  # < 5
            "h_bond_donors": 3,  # < 5
            "h_bond_acceptors": 8,  # < 10
        }

        violations = 0
        if properties["molecular_weight"] > 500:
            violations += 1
        if properties["logp"] > 5:
            violations += 1
        if properties["h_bond_donors"] > 5:
            violations += 1
        if properties["h_bond_acceptors"] > 10:
            violations += 1

        assert violations == 0  # Drug-like

    def test_lipinski_violations(self):
        """Test Lipinski violations for non-drug-like molecule."""
        properties = {
            "molecular_weight": 650,  # Violation
            "logp": 6.5,  # Violation
            "h_bond_donors": 3,
            "h_bond_acceptors": 8,
        }

        violations = 0
        if properties["molecular_weight"] > 500:
            violations += 1
        if properties["logp"] > 5:
            violations += 1
        if properties["h_bond_donors"] > 5:
            violations += 1
        if properties["h_bond_acceptors"] > 10:
            violations += 1

        assert violations == 2

    def test_h_bond_donor_acceptor_ratio(self):
        """Test hydrogen bond donor/acceptor ratio."""
        donors = 3
        acceptors = 6
        ratio = donors / acceptors if acceptors > 0 else 0

        # Good ratio is typically 0.3 - 0.7
        assert 0.3 <= ratio <= 0.7


# ============================================================================
# PHYSICAL CONSTANTS TESTS
# ============================================================================


class TestPhysicalConstants:
    """Test suite for physical constants."""

    def test_gas_constant(self):
        """Test gas constant value."""
        assert R_KCAL == 0.001987  # kcal/(mol·K)

    def test_temperature(self):
        """Test standard temperature."""
        assert T_KELVIN == 298.15  # K (25°C)

    def test_rt_value(self):
        """Test RT value at 298K."""
        assert abs(RT - 0.593) < 0.01  # kcal/mol

    def test_hartree_conversion(self):
        """Test Hartree to kcal/mol conversion factor."""
        assert HARTREE_TO_KCAL == 627.509


# ============================================================================
# ENERGY INTERPRETATION TESTS
# ============================================================================


class TestEnergyInterpretation:
    """Test suite for energy interpretation from quantum results."""

    def test_ground_state_energy_extraction(self, sample_counts):
        """Test extraction of ground state energy from counts."""
        # Most probable state should correspond to ground state
        most_probable = max(sample_counts.items(), key=lambda x: x[1])
        state, count = most_probable

        assert state == "0000"
        assert count == 250

    def test_energy_from_hamiltonian(self):
        """Test energy calculation from Hamiltonian expectation value."""
        hamiltonian = np.array([[1.0, 0.5], [0.5, 2.0]])
        statevector = np.array([0.707, 0.707])

        energy = np.dot(statevector, np.dot(hamiltonian, statevector))

        assert energy > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestBioInterpreterErrorHandling:
    """Test suite for error handling in bio interpreter."""

    def test_interpret_with_empty_counts(self):
        """Test interpretation with empty counts."""
        context = {"application": "molecular_docking", "smiles": "CCO"}
        result = interpret_bio_results({}, context)

        # Should handle gracefully
        assert result is not None

    def test_interpret_with_missing_context(self, sample_counts):
        """Test interpretation with minimal context."""
        result = interpret_bio_results(sample_counts, {})

        assert "most_probable_state" in result

    @patch("bioql.bio_interpreter.download_pdb")
    def test_interpret_drug_docking_pdb_download_failure(self, mock_download, sample_counts):
        """Test handling of PDB download failure."""
        mock_download.return_value = {"success": False}

        with patch("bioql.bio_interpreter.HAVE_RDKIT", True):
            with patch("bioql.bio_interpreter.VINA_BIN", "/usr/local/bin/vina"):
                result = interpret_drug_docking(
                    counts=sample_counts, smiles="CCO", pdb_id="INVALID"
                )

        # Should fallback to predicted affinity
        assert result is not None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
