# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Unit Tests for BioQL Chemistry Modules

Tests the following modules:
- bioql/chem/geometry.py (molecular geometry optimization)
- bioql/chem/ligand_prep.py (ligand preparation from SMILES)
- bioql/chem/receptor_prep.py (receptor/protein preparation)
- bioql/chem/neutralize.py (SMILES neutralization)

All tests use mocking to avoid external dependencies (RDKit, OpenBabel, Biopython).
"""

# Add project to path
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Spectrix_framework"))


# ============================================================================
# GEOMETRY MODULE TESTS (bioql/chem/geometry.py)
# ============================================================================


class TestGeometryOptimizer:
    """Test suite for molecular geometry optimization."""

    @patch("bioql.chem.geometry.Chem")
    @patch("bioql.chem.geometry.AllChem")
    def test_optimize_from_smiles_success(self, mock_allchem, mock_chem):
        """Test successful geometry optimization from SMILES string."""
        from bioql.chem.geometry import GeometryOptimizer

        # Setup mocks
        mock_mol = MagicMock()
        mock_chem.MolFromSmiles.return_value = mock_mol
        mock_chem.AddHs.return_value = mock_mol
        mock_allchem.EmbedMolecule.return_value = 0  # Success

        mock_ff = MagicMock()
        mock_ff.CalcEnergy.side_effect = [100.0, 50.0]  # Initial, final energy
        mock_allchem.MMFFGetMoleculeForceField.return_value = mock_ff
        mock_allchem.MMFFOptimizeMolecule.return_value = 10  # Iterations

        # Test optimization
        optimizer = GeometryOptimizer(backend="rdkit")
        result = optimizer.optimize(smiles="CCO", max_iterations=200)

        assert result.success is True
        assert result.initial_energy == 100.0
        assert result.final_energy == 50.0
        assert result.num_iterations == 10
        assert result.method == "rdkit_mmff94"
        mock_chem.MolFromSmiles.assert_called_once_with("CCO")

    @patch("bioql.chem.geometry.Chem")
    def test_optimize_invalid_smiles_failure(self, mock_chem):
        """Test optimization with invalid SMILES string."""
        from bioql.chem.geometry import GeometryOptimizer

        mock_chem.MolFromSmiles.return_value = None

        optimizer = GeometryOptimizer(backend="rdkit")
        result = optimizer.optimize(smiles="INVALID")

        assert result.success is False
        assert "Failed to load molecule" in result.error_message

    @patch("bioql.chem.geometry.Chem")
    @patch("bioql.chem.geometry.AllChem")
    def test_optimize_from_pdb_file(self, mock_allchem, mock_chem):
        """Test geometry optimization from PDB file."""
        from bioql.chem.geometry import GeometryOptimizer

        mock_mol = MagicMock()
        mock_chem.MolFromPDBFile.return_value = mock_mol

        mock_ff = MagicMock()
        mock_ff.CalcEnergy.side_effect = [150.0, 80.0]
        mock_allchem.UFFGetMoleculeForceField.return_value = mock_ff
        mock_allchem.UFFOptimizeMolecule.return_value = 15

        optimizer = GeometryOptimizer(backend="rdkit")
        result = optimizer.optimize(molecule_path="/tmp/test.pdb", force_field="UFF")

        assert result.success is True
        assert result.method == "rdkit_uff"

    def test_optimize_no_input_failure(self):
        """Test optimization with no input provided."""
        from bioql.chem.geometry import GeometryOptimizer

        optimizer = GeometryOptimizer()
        result = optimizer.optimize()

        assert result.success is False
        assert "Either molecule_path or smiles must be provided" in result.error_message

    @patch("bioql.chem.geometry.HAS_OPENBABEL", True)
    @patch("bioql.chem.geometry.ob")
    def test_optimize_with_openbabel_backend(self, mock_ob):
        """Test geometry optimization using OpenBabel backend."""
        from bioql.chem.geometry import GeometryOptimizer

        # Setup OpenBabel mocks
        mock_mol = MagicMock()
        mock_conv = MagicMock()
        mock_ff = MagicMock()

        mock_ob.OBMol.return_value = mock_mol
        mock_ob.OBConversion.return_value = mock_conv
        mock_ob.OBForceField.FindForceField.return_value = mock_ff

        mock_ff.Energy.side_effect = [200.0, 100.0]

        optimizer = GeometryOptimizer(backend="openbabel")
        result = optimizer.optimize(smiles="CCO")

        assert result.success is True
        assert result.method == "openbabel_mmff94"


# ============================================================================
# LIGAND PREPARATION MODULE TESTS (bioql/chem/ligand_prep.py)
# ============================================================================


class TestLigandPreparation:
    """Test suite for ligand preparation from SMILES."""

    @patch("bioql.chem.ligand_prep.Chem")
    @patch("bioql.chem.ligand_prep.AllChem")
    def test_prepare_ligand_basic_success(self, mock_allchem, mock_chem):
        """Test basic ligand preparation from SMILES."""
        from bioql.chem.ligand_prep import prepare_ligand

        # Setup mocks
        mock_mol = MagicMock()
        mock_mol.GetNumAtoms.return_value = 9
        mock_chem.MolFromSmiles.return_value = mock_mol
        mock_chem.AddHs.return_value = mock_mol
        mock_allchem.EmbedMolecule.return_value = 0

        # Mock Descriptors
        with patch("bioql.chem.ligand_prep.Descriptors") as mock_descriptors:
            mock_descriptors.MolWt.return_value = 46.07  # Ethanol

            result = prepare_ligand(smiles="CCO", output_format="pdb")

        assert result.success is True
        assert result.smiles == "CCO"
        assert result.num_atoms == 9
        assert result.molecular_weight == 46.07
        assert result.format == "pdb"

    @patch("bioql.chem.ligand_prep.Chem")
    def test_prepare_ligand_invalid_smiles(self, mock_chem):
        """Test ligand preparation with invalid SMILES."""
        from bioql.chem.ligand_prep import prepare_ligand

        mock_chem.MolFromSmiles.return_value = None

        result = prepare_ligand(smiles="INVALID_SMILES")

        assert result.success is False
        assert "Invalid SMILES string" in result.error_message

    @patch("bioql.chem.ligand_prep.Chem")
    @patch("bioql.chem.ligand_prep.AllChem")
    def test_prepare_ligand_pdbqt_format_no_meeko(self, mock_allchem, mock_chem):
        """Test PDBQT preparation without Meeko available."""
        from bioql.chem.ligand_prep import prepare_ligand

        mock_mol = MagicMock()
        mock_chem.MolFromSmiles.return_value = mock_mol
        mock_chem.AddHs.return_value = mock_mol
        mock_allchem.EmbedMolecule.return_value = 0

        with patch("bioql.chem.ligand_prep.Descriptors"):
            result = prepare_ligand(smiles="CCO", output_format="pdbqt")

        assert result.success is False
        assert "Meeko required" in result.error_message

    @patch("bioql.chem.ligand_prep.Chem")
    @patch("bioql.chem.ligand_prep.AllChem")
    def test_prepare_ligand_3d_embedding_failure(self, mock_allchem, mock_chem):
        """Test handling of 3D embedding failure."""
        from bioql.chem.ligand_prep import prepare_ligand

        mock_mol = MagicMock()
        mock_chem.MolFromSmiles.return_value = mock_mol
        mock_chem.AddHs.return_value = mock_mol
        mock_allchem.EmbedMolecule.side_effect = [1, 0]  # First fails, second succeeds

        with patch("bioql.chem.ligand_prep.Descriptors"):
            result = prepare_ligand(smiles="CCO", generate_3d=True, optimize_geometry=False)

        # Should retry with random coords
        assert mock_allchem.EmbedMolecule.call_count == 2

    @patch("bioql.chem.ligand_prep.Chem")
    def test_validate_smiles_valid(self, mock_chem):
        """Test SMILES validation with valid input."""
        from bioql.chem.ligand_prep import validate_smiles

        mock_mol = MagicMock()
        mock_chem.MolFromSmiles.return_value = mock_mol

        assert validate_smiles("CCO") is True

    @patch("bioql.chem.ligand_prep.Chem")
    def test_validate_smiles_invalid(self, mock_chem):
        """Test SMILES validation with invalid input."""
        from bioql.chem.ligand_prep import validate_smiles

        mock_chem.MolFromSmiles.return_value = None

        assert validate_smiles("INVALID") is False


# ============================================================================
# RECEPTOR PREPARATION MODULE TESTS (bioql/chem/receptor_prep.py)
# ============================================================================


class TestReceptorPreparation:
    """Test suite for protein receptor preparation."""

    def test_prepare_receptor_file_not_found(self):
        """Test receptor preparation with non-existent file."""
        from bioql.chem.receptor_prep import prepare_receptor

        result = prepare_receptor("/nonexistent/file.pdb")

        assert result.success is False
        assert "File not found" in result.error_message

    @patch("bioql.chem.receptor_prep.PDB")
    def test_prepare_receptor_with_biopython(self, mock_pdb):
        """Test receptor preparation using Biopython."""
        from bioql.chem.receptor_prep import prepare_receptor

        # Create temporary PDB file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as f:
            f.write("ATOM      1  N   MET A   1       0.000   0.000   0.000\n")
            temp_path = f.name

        try:
            # Setup mocks
            mock_parser = MagicMock()
            mock_structure = MagicMock()
            mock_chain = MagicMock()
            mock_chain.id = "A"

            mock_pdb.PDBParser.return_value = mock_parser
            mock_parser.get_structure.return_value = mock_structure
            mock_structure.get_residues.return_value = [MagicMock()] * 100
            mock_structure.get_atoms.return_value = [MagicMock()] * 500
            mock_structure.get_chains.return_value = [mock_chain]

            with patch("bioql.chem.receptor_prep.PDBIO"):
                result = prepare_receptor(temp_path, chains=["A"], remove_waters=True)

            assert result.success is True
            assert result.num_residues == 100
            assert result.num_atoms == 500
            assert result.chains == ["A"]
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_prepare_receptor_text_processing_fallback(self):
        """Test receptor preparation with text processing fallback."""
        from bioql.chem.receptor_prep import prepare_receptor

        # Create temporary PDB file
        pdb_content = """
ATOM      1  N   MET A   1       0.000   0.000   0.000
ATOM      2  CA  MET A   1       1.000   1.000   1.000
HETATM    3  O   HOH A 100       2.000   2.000   2.000
END
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as f:
            f.write(pdb_content)
            temp_path = f.name

        try:
            with patch("bioql.chem.receptor_prep.PDB", side_effect=ImportError):
                result = prepare_receptor(temp_path, remove_waters=True, remove_heteroatoms=False)

            assert result.success is True
            assert result.num_atoms == 2  # Should exclude water
            assert result.metadata["method"] == "text_processing"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("bioql.chem.receptor_prep.PDB")
    @patch("bioql.chem.receptor_prep.np")
    def test_get_binding_site_residues(self, mock_np, mock_pdb):
        """Test binding site residue identification."""
        from bioql.chem.receptor_prep import get_binding_site_residues

        # Setup mocks
        mock_parser = MagicMock()
        mock_pdb.PDBParser.return_value = mock_parser

        mock_residue = MagicMock()
        mock_residue.parent.id = "A"
        mock_residue.id = (None, 123, None)
        mock_residue.resname = "ALA"

        mock_atom = MagicMock()
        mock_atom.coord = [1.0, 1.0, 1.0]
        mock_residue.get_atoms.return_value = [mock_atom]

        mock_protein = MagicMock()
        mock_protein.get_residues.return_value = [mock_residue]

        mock_ligand = MagicMock()
        mock_lig_atom = MagicMock()
        mock_lig_atom.coord = [1.5, 1.5, 1.5]
        mock_ligand.get_atoms.return_value = [mock_lig_atom]

        mock_parser.get_structure.side_effect = [mock_protein, mock_ligand]
        mock_np.linalg.norm.return_value = 0.86  # Distance < 5.0 Å

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".pdb", delete=False) as f1:
            protein_path = f1.name
        with tempfile.NamedTemporaryFile(suffix=".pdb", delete=False) as f2:
            ligand_path = f2.name

        try:
            residues = get_binding_site_residues(protein_path, ligand_path, distance=5.0)

            assert len(residues) > 0
            assert residues[0] == ("A", 123, "ALA")
        finally:
            Path(protein_path).unlink(missing_ok=True)
            Path(ligand_path).unlink(missing_ok=True)


# ============================================================================
# NEUTRALIZE MODULE TESTS (bioql/chem/neutralize.py)
# ============================================================================


class TestNeutralize:
    """Test suite for SMILES neutralization."""

    @patch("bioql.chem.neutralize.Chem")
    def test_neutralize_already_neutral(self, mock_chem):
        """Test neutralization of already neutral molecule."""
        from bioql.chem.neutralize import neutralize_smiles

        mock_mol = MagicMock()
        mock_atom = MagicMock()
        mock_atom.GetFormalCharge.return_value = 0
        mock_mol.GetAtoms.return_value = [mock_atom, mock_atom]
        mock_chem.MolFromSmiles.return_value = mock_mol
        mock_chem.MolToSmiles.return_value = "CCO"

        result = neutralize_smiles("CCO")

        assert result == "CCO"

    @patch("bioql.chem.neutralize.Chem")
    @patch("bioql.chem.neutralize.HAS_MOL_STANDARDIZE", True)
    @patch("bioql.chem.neutralize.rdMolStandardize")
    def test_neutralize_with_standardize(self, mock_standardize, mock_chem):
        """Test neutralization using rdMolStandardize."""
        from bioql.chem.neutralize import neutralize_smiles

        mock_mol = MagicMock()
        mock_atom = MagicMock()
        mock_atom.GetFormalCharge.return_value = -1
        mock_mol.GetAtoms.return_value = [mock_atom]

        mock_neutral_mol = MagicMock()
        mock_neutral_atom = MagicMock()
        mock_neutral_atom.GetFormalCharge.return_value = 0
        mock_neutral_mol.GetAtoms.return_value = [mock_neutral_atom]

        mock_chem.MolFromSmiles.return_value = mock_mol

        mock_uncharger = MagicMock()
        mock_uncharger.uncharge.return_value = mock_neutral_mol
        mock_standardize.Uncharger.return_value = mock_uncharger

        mock_chem.MolToSmiles.return_value = "CC(=O)O"

        result = neutralize_smiles("CC(=O)[O-]")

        assert result == "CC(=O)O"

    @patch("bioql.chem.neutralize.Chem")
    def test_neutralize_manual_carboxylate(self, mock_chem):
        """Test manual neutralization of carboxylate."""
        from bioql.chem.neutralize import _manual_neutralize

        mock_mol = MagicMock()
        mock_rwmol = MagicMock()
        mock_chem.RWMol.return_value = mock_rwmol

        mock_oxygen = MagicMock()
        mock_oxygen.GetFormalCharge.return_value = -1
        mock_oxygen.GetSymbol.return_value = "O"
        mock_oxygen.GetNumExplicitHs.return_value = 0

        mock_rwmol.GetAtoms.return_value = [mock_oxygen]
        mock_chem.MolToSmiles.return_value = "CC(=O)O"

        result = _manual_neutralize(mock_mol, strict=False)

        assert result == "CC(=O)O"
        mock_oxygen.SetFormalCharge.assert_called_with(0)

    @patch("bioql.chem.neutralize.Chem")
    def test_neutralize_invalid_smiles(self, mock_chem):
        """Test neutralization with invalid SMILES."""
        from bioql.chem.neutralize import neutralize_smiles

        mock_chem.MolFromSmiles.return_value = None

        result = neutralize_smiles("INVALID")

        assert result == "INVALID"  # Returns original on failure

    @patch("bioql.chem.neutralize.Chem")
    def test_validate_neutral_smiles_success(self, mock_chem):
        """Test validation of neutral SMILES."""
        from bioql.chem.neutralize import validate_neutral_smiles

        mock_mol = MagicMock()
        mock_atom = MagicMock()
        mock_atom.GetFormalCharge.return_value = 0
        mock_mol.GetAtoms.return_value = [mock_atom]
        mock_chem.MolFromSmiles.return_value = mock_mol

        with patch("bioql.chem.neutralize.AllChem") as mock_allchem:
            mock_test_mol = MagicMock()
            mock_chem.AddHs.return_value = mock_test_mol
            mock_allchem.EmbedMolecule.return_value = 0

            is_valid, message = validate_neutral_smiles("CCO")

        assert is_valid is True
        assert "Valid" in message

    @patch("bioql.chem.neutralize.Chem")
    def test_validate_neutral_smiles_charged(self, mock_chem):
        """Test validation rejects charged SMILES."""
        from bioql.chem.neutralize import validate_neutral_smiles

        mock_mol = MagicMock()
        mock_atom = MagicMock()
        mock_atom.GetFormalCharge.return_value = -1
        mock_mol.GetAtoms.return_value = [mock_atom]
        mock_chem.MolFromSmiles.return_value = mock_mol

        is_valid, message = validate_neutral_smiles("CC(=O)[O-]")

        assert is_valid is False
        assert "net charge" in message


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
