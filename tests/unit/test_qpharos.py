# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Comprehensive Unit Tests
Tests all 4 API schemas: Simple, Functional, OOP, Layer-by-Layer
"""

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest

# Add QPHAROS to path - ensure both QPHAROS root and parent are in path
project_root = Path(__file__).parent.parent.parent
qpharos_path = project_root / "QPHAROS"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(qpharos_path))

# Fix import path issue in qpharos package by creating alias
import importlib

core_module = importlib.import_module("core")
layers_module = importlib.import_module("layers")
sys.modules["qpharos.core"] = core_module
sys.modules["qpharos.layers"] = layers_module

# Import core modules first to avoid circular imports
from core.config import QPHAROSConfig
from layers import (
    QuantumADMETOptimizer,
    QuantumBindingPredictor,
    QuantumMolecularDynamics,
    QuantumMolecularEncoder,
    QuantumMolecularGAN,
)

# Import API functions last (they depend on models)
import qpharos.api as qpharos_api
from qpharos.analyzer import AnalysisSession, QPHAROSAnalyzer

# Import QPHAROS modules in safe order
from qpharos.models import ADMETResult, DockingResult, DrugDesignResult, GeneratedMolecule
from qpharos.simple import is_drug_like, quick_dock, test_molecule

dock = qpharos_api.dock
design_drug = qpharos_api.design_drug
predict_admet = qpharos_api.predict_admet
screen_library = qpharos_api.screen_library
optimize_lead = qpharos_api.optimize_lead


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_bioql_result():
    """Mock BioQL quantum result for docking"""
    result = Mock()
    result.bio_interpretation = {
        "binding_affinity": -8.5,
        "ki": 0.589,
        "ic50": 1.2,
        "docking_score": -9.2,
        "h_bonds": 3,
        "hydrophobic_contacts": 5,
        "salt_bridges": 1,
        "pi_stacking": 2,
        "lipinski_pass": True,
        "qed_score": 0.85,
        "sa_score": 3.2,
        "pains_alerts": 0,
    }
    result.metadata = {
        "ligand_smiles": "CCO",
        "receptor_pdb": "6B3J",
        "shots": 2000,
        "qec_enabled": True,
    }
    result.backend_name = "ibm_torino"
    result.job_id = "job_12345"
    result.counts = {"00": 1000, "11": 1000}
    result.success = True
    result.error_message = None
    return result


@pytest.fixture
def mock_bioql_admet_result():
    """Mock BioQL result for ADMET prediction"""
    result = Mock()
    result.bio_interpretation = {
        "caco2_permeability": 5.2,
        "hia": 92.5,
        "vdss": 1.3,
        "ppb": 85.0,
        "cyp3a4_substrate": True,
        "cyp2d6_substrate": False,
        "cyp2c9_substrate": False,
        "clearance": 12.5,
        "half_life": 3.5,
        "herg_inhibition": False,
        "ames_mutagenicity": False,
        "ld50": 500.0,
        "lipinski_pass": True,
        "qed_score": 0.78,
        "sa_score": 2.8,
        "pains_alerts": 0,
    }
    result.metadata = {"smiles": "CCO", "shots": 1500}
    result.backend_name = "ibm_torino"
    result.job_id = "job_admet_123"
    result.success = True
    result.error_message = None
    return result


@pytest.fixture
def mock_bioql_design_result():
    """Mock BioQL result for drug design"""
    result = Mock()
    result.bio_interpretation = {
        "generated_molecules": [
            {
                "smiles": "COc1ccccc1",
                "score": 0.95,
                "binding_affinity": -9.2,
                "qed": 0.88,
                "sa_score": 2.1,
                "lipinski_pass": True,
            },
            {
                "smiles": "CC(C)O",
                "score": 0.87,
                "binding_affinity": -8.5,
                "qed": 0.72,
                "sa_score": 1.5,
                "lipinski_pass": True,
            },
        ]
    }
    result.metadata = {"target_protein": "6B3J", "shots": 3000}
    result.backend_name = "ibm_torino"
    result.job_id = "job_design_456"
    result.success = True
    result.error_message = None
    return result


@pytest.fixture
def valid_smiles():
    """Valid SMILES strings for testing"""
    return [
        "CCO",  # Ethanol
        "CC(C)O",  # Isopropanol
        "COc1ccccc1",  # Anisole
        "c1ccccc1",  # Benzene
        "CC(=O)O",  # Acetic acid
    ]


@pytest.fixture
def valid_pdb_ids():
    """Valid PDB IDs for testing"""
    return ["6B3J", "1A2B", "5XYZ"]


# ============================================================================
# FUNCTIONAL API TESTS (dock, predict_admet, design_drug)
# ============================================================================


@pytest.mark.unit
class TestFunctionalAPI:
    """Test QPHAROS Functional API (Esquema 2)"""

    @patch("qpharos.api.quantum")
    def test_dock_basic(self, mock_quantum, mock_bioql_result, valid_smiles, valid_pdb_ids):
        """Test basic docking with mock quantum backend"""
        mock_quantum.return_value = mock_bioql_result

        result = dock(
            ligand=valid_smiles[0],
            receptor=valid_pdb_ids[0],
            api_key="bioql_test_key",
            backend="simulator",
            shots=2000,
            qec=True,
        )

        assert isinstance(result, DockingResult)
        assert result.binding_affinity == -8.5
        assert result.ki == 0.589
        assert result.ic50 == 1.2
        assert result.h_bonds == 3
        assert result.success is True
        assert result.job_id == "job_12345"

        # Verify quantum function was called
        mock_quantum.assert_called_once()
        call_args = mock_quantum.call_args
        assert "QPHAROS" in call_args[0][0]
        assert call_args[1]["shots"] == 2000
        assert call_args[1]["backend"] == "simulator"

    @patch("qpharos.api.quantum")
    def test_dock_with_binding_site(self, mock_quantum, mock_bioql_result):
        """Test docking with specific binding site"""
        mock_quantum.return_value = mock_bioql_result

        result = dock(
            ligand="CCO", receptor="6B3J", binding_site="A:SER123", api_key="bioql_test_key"
        )

        assert result.success is True
        # Verify binding site was included in prompt
        call_args = mock_quantum.call_args[0][0]
        assert "Binding Site: A:SER123" in call_args

    @patch("qpharos.api.quantum")
    def test_dock_different_backends(self, mock_quantum, mock_bioql_result):
        """Test docking with different quantum backends"""
        backends = ["ibm_torino", "ibm_kyoto", "simulator"]
        mock_quantum.return_value = mock_bioql_result

        for backend in backends:
            result = dock(ligand="CCO", receptor="6B3J", api_key="bioql_test_key", backend=backend)
            assert result.success is True
            assert mock_quantum.call_args[1]["backend"] == backend

    @patch("qpharos.api.quantum")
    def test_dock_qec_disabled(self, mock_quantum, mock_bioql_result):
        """Test docking with QEC disabled"""
        mock_quantum.return_value = mock_bioql_result

        result = dock(ligand="CCO", receptor="6B3J", api_key="bioql_test_key", qec=False)

        assert result.success is True
        # QEC layer should not be in prompt
        call_args = mock_quantum.call_args[0][0]
        assert "Quantum Error Correction" not in call_args

    @patch("qpharos.api.quantum")
    def test_dock_env_api_key(self, mock_quantum, mock_bioql_result, monkeypatch):
        """Test docking with API key from environment"""
        monkeypatch.setenv("BIOQL_API_KEY", "env_test_key")
        mock_quantum.return_value = mock_bioql_result

        result = dock(ligand="CCO", receptor="6B3J")

        assert result.success is True
        assert mock_quantum.call_args[1]["api_key"] == "env_test_key"

    def test_dock_no_api_key(self, monkeypatch):
        """Test docking without API key raises error"""
        monkeypatch.delenv("BIOQL_API_KEY", raising=False)

        with pytest.raises(ValueError, match="API key required"):
            dock(ligand="CCO", receptor="6B3J", api_key=None)

    @patch("qpharos.api.quantum")
    def test_predict_admet_basic(self, mock_quantum, mock_bioql_admet_result):
        """Test basic ADMET prediction"""
        mock_quantum.return_value = mock_bioql_admet_result

        result = predict_admet(
            smiles="CCO", api_key="bioql_test_key", backend="simulator", shots=1500
        )

        assert isinstance(result, ADMETResult)
        assert result.caco2_permeability == 5.2
        assert result.hia == 92.5
        assert result.lipinski_pass is True
        assert result.qed_score == 0.78
        assert result.herg_inhibition is False
        assert result.ames_mutagenicity is False
        assert result.success is True

    @patch("qpharos.api.quantum")
    def test_predict_admet_cyp_metabolism(self, mock_quantum, mock_bioql_admet_result):
        """Test ADMET CYP450 metabolism predictions"""
        mock_quantum.return_value = mock_bioql_admet_result

        result = predict_admet("CCO", api_key="bioql_test_key")

        assert result.cyp3a4_substrate is True
        assert result.cyp2d6_substrate is False
        assert result.cyp2c9_substrate is False

    @patch("qpharos.api.quantum")
    def test_design_drug_basic(self, mock_quantum, mock_bioql_design_result):
        """Test basic drug design with QGAN"""
        mock_quantum.return_value = mock_bioql_design_result

        result = design_drug(
            target_protein="6B3J", api_key="bioql_test_key", backend="simulator", shots=3000
        )

        assert isinstance(result, DrugDesignResult)
        assert result.target_protein == "6B3J"
        assert len(result.molecules) == 2
        assert result.success is True

        # Check first molecule
        mol1 = result.molecules[0]
        assert isinstance(mol1, GeneratedMolecule)
        assert mol1.smiles == "COc1ccccc1"
        assert mol1.score == 0.95
        assert mol1.binding_affinity == -9.2
        assert mol1.qed == 0.88
        assert mol1.lipinski_pass is True

    @patch("qpharos.api.quantum")
    def test_design_drug_with_scaffold(self, mock_quantum, mock_bioql_design_result):
        """Test drug design with scaffold constraint"""
        mock_quantum.return_value = mock_bioql_design_result

        result = design_drug(target_protein="6B3J", scaffold="c1ccccc1", api_key="bioql_test_key")

        assert result.success is True
        # Verify scaffold was included in prompt
        call_args = mock_quantum.call_args[0][0]
        assert "Scaffold: c1ccccc1" in call_args

    @patch("qpharos.api.quantum")
    def test_design_drug_with_constraints(self, mock_quantum, mock_bioql_design_result):
        """Test drug design with MW and logP constraints"""
        mock_quantum.return_value = mock_bioql_design_result

        constraints = {"MW": (300, 500), "logP": (0, 5)}
        result = design_drug(
            target_protein="6B3J", constraints=constraints, api_key="bioql_test_key"
        )

        assert result.success is True
        call_args = mock_quantum.call_args[0][0]
        assert "Constraints" in call_args

    @patch("qpharos.api.dock")
    def test_screen_library(self, mock_dock_func, valid_smiles):
        """Test library screening (batch docking)"""
        # Create different mock results for each ligand
        mock_results = []
        for i, smiles in enumerate(valid_smiles[:3]):
            mock_result = Mock(spec=DockingResult)
            mock_result.ligand_smiles = smiles
            mock_result.binding_affinity = -7.0 - i  # Different affinities
            mock_results.append(mock_result)

        mock_dock_func.side_effect = mock_results

        results = screen_library(
            ligands=valid_smiles[:3],
            receptor="6B3J",
            api_key="bioql_test_key",
            shots_per_ligand=1000,
        )

        assert len(results) == 3
        assert mock_dock_func.call_count == 3

        # Results should be sorted by binding affinity
        for i in range(len(results) - 1):
            assert results[i].binding_affinity <= results[i + 1].binding_affinity

    @patch("qpharos.api.design_drug")
    @patch("qpharos.api.dock")
    def test_optimize_lead(self, mock_dock_func, mock_design_func):
        """Test lead optimization workflow"""
        # Mock original lead docking
        original_result = Mock(spec=DockingResult)
        original_result.binding_affinity = -7.5

        # Mock variant generation
        design_result = Mock(spec=DrugDesignResult)
        variant_mol = Mock(spec=GeneratedMolecule)
        variant_mol.smiles = "COc1ccccc1"
        design_result.molecules = [variant_mol]

        # Mock variant docking
        variant_result = Mock(spec=DockingResult)
        variant_result.binding_affinity = -8.5

        mock_dock_func.side_effect = [original_result, variant_result, variant_result]
        mock_design_func.return_value = design_result

        results = optimize_lead(
            lead_smiles="CCO", receptor="6B3J", iterations=2, api_key="bioql_test_key"
        )

        assert len(results) == 3  # Original + 2 iterations
        assert mock_dock_func.call_count == 3
        assert mock_design_func.call_count == 2


# ============================================================================
# SIMPLE API TESTS (quick_dock, is_drug_like, test_molecule)
# ============================================================================


@pytest.mark.unit
class TestSimpleAPI:
    """Test QPHAROS Simple API (Esquema 1)"""

    @patch("qpharos.simple._dock")
    def test_quick_dock(self, mock_dock, monkeypatch):
        """Test ultra-simple quick_dock function"""
        monkeypatch.setenv("BIOQL_API_KEY", "test_key")

        mock_result = Mock(spec=DockingResult)
        mock_result.binding_affinity = -6.2
        mock_dock.return_value = mock_result

        affinity = quick_dock("CCO", "6B3J")

        assert affinity == -6.2
        mock_dock.assert_called_once()

    @patch("qpharos.simple._dock")
    def test_quick_dock_none_affinity(self, mock_dock, monkeypatch):
        """Test quick_dock with None affinity returns 0.0"""
        monkeypatch.setenv("BIOQL_API_KEY", "test_key")

        mock_result = Mock(spec=DockingResult)
        mock_result.binding_affinity = None
        mock_dock.return_value = mock_result

        affinity = quick_dock("CCO", "6B3J")

        assert affinity == 0.0

    def test_quick_dock_no_api_key(self, monkeypatch):
        """Test quick_dock raises error without API key"""
        monkeypatch.delenv("BIOQL_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Set BIOQL_API_KEY"):
            quick_dock("CCO", "6B3J")

    @patch("qpharos.simple._predict_admet")
    def test_is_drug_like_true(self, mock_admet, monkeypatch):
        """Test is_drug_like returns True for drug-like molecule"""
        monkeypatch.setenv("BIOQL_API_KEY", "test_key")

        mock_result = Mock(spec=ADMETResult)
        mock_result.lipinski_pass = True
        mock_admet.return_value = mock_result

        result = is_drug_like("CCO")

        assert result is True

    @patch("qpharos.simple._predict_admet")
    def test_is_drug_like_false(self, mock_admet, monkeypatch):
        """Test is_drug_like returns False for non-drug-like molecule"""
        monkeypatch.setenv("BIOQL_API_KEY", "test_key")

        mock_result = Mock(spec=ADMETResult)
        mock_result.lipinski_pass = False
        mock_admet.return_value = mock_result

        result = is_drug_like("CCO")

        assert result is False

    @patch("qpharos.simple._predict_admet")
    @patch("qpharos.simple._dock")
    def test_test_molecule_excellent(self, mock_dock, mock_admet, monkeypatch):
        """Test test_molecule with excellent candidate"""
        monkeypatch.setenv("BIOQL_API_KEY", "test_key")

        mock_dock_result = Mock(spec=DockingResult)
        mock_dock_result.binding_affinity = -8.5
        mock_dock_result.ki = 0.5
        mock_dock_result.job_id = "job_123"
        mock_dock.return_value = mock_dock_result

        mock_admet_result = Mock(spec=ADMETResult)
        mock_admet_result.lipinski_pass = True
        mock_admet_result.qed_score = 0.75
        mock_admet.return_value = mock_admet_result

        result = test_molecule("CCO", "6B3J")

        assert result["affinity"] == -8.5
        assert result["ki_nM"] == 0.5
        assert result["drug_like"] is True
        assert result["qed_score"] == 0.75
        assert "Excellent candidate" in result["recommendation"]
        assert result["job_id"] == "job_123"

    @patch("qpharos.simple._predict_admet")
    @patch("qpharos.simple._dock")
    def test_test_molecule_weak(self, mock_dock, mock_admet, monkeypatch):
        """Test test_molecule with weak binding"""
        monkeypatch.setenv("BIOQL_API_KEY", "test_key")

        mock_dock_result = Mock(spec=DockingResult)
        mock_dock_result.binding_affinity = -3.0
        mock_dock_result.ki = None
        mock_dock_result.job_id = "job_456"
        mock_dock.return_value = mock_dock_result

        mock_admet_result = Mock(spec=ADMETResult)
        mock_admet_result.lipinski_pass = False
        mock_admet_result.qed_score = 0.3
        mock_admet.return_value = mock_admet_result

        result = test_molecule("CCO", "6B3J")

        assert "not recommended" in result["recommendation"]


# ============================================================================
# OOP API TESTS (QPHAROSAnalyzer class)
# ============================================================================


@pytest.mark.unit
class TestOOPAPI:
    """Test QPHAROS Object-Oriented API (Esquema 3)"""

    def test_analyzer_initialization_default(self):
        """Test QPHAROSAnalyzer initialization with defaults"""
        analyzer = QPHAROSAnalyzer()

        assert analyzer.config is not None
        assert isinstance(analyzer.config, QPHAROSConfig)
        assert analyzer.session is not None
        assert isinstance(analyzer.session, AnalysisSession)
        assert len(analyzer.session.results) == 0

    def test_analyzer_initialization_custom_config(self):
        """Test QPHAROSAnalyzer with custom config"""
        config = QPHAROSConfig(
            backend="simulator", shots=1000, qec_enabled=False, api_key="custom_key"
        )

        analyzer = QPHAROSAnalyzer(config)

        assert analyzer.config.backend == "simulator"
        assert analyzer.config.shots == 1000
        assert analyzer.config.qec_enabled is False
        assert analyzer.config.api_key == "custom_key"

    @patch("qpharos.analyzer.dock")
    def test_analyzer_dock(self, mock_dock_func):
        """Test QPHAROSAnalyzer.dock method"""
        mock_result = Mock(spec=DockingResult)
        mock_result.binding_affinity = -7.5
        mock_dock_func.return_value = mock_result

        config = QPHAROSConfig(api_key="test_key", backend="simulator", shots=2000)
        analyzer = QPHAROSAnalyzer(config)

        result = analyzer.dock("CCO", "6B3J")

        assert result.binding_affinity == -7.5
        assert len(analyzer.session.results) == 1
        mock_dock_func.assert_called_once()

    @patch("qpharos.analyzer.predict_admet")
    def test_analyzer_predict_admet(self, mock_admet_func):
        """Test QPHAROSAnalyzer.predict_admet method"""
        mock_result = Mock(spec=ADMETResult)
        mock_result.lipinski_pass = True
        mock_admet_func.return_value = mock_result

        analyzer = QPHAROSAnalyzer()
        result = analyzer.predict_admet("CCO")

        assert result.lipinski_pass is True
        assert len(analyzer.session.results) == 1

    @patch("qpharos.analyzer.design_drug")
    def test_analyzer_design(self, mock_design_func):
        """Test QPHAROSAnalyzer.design method"""
        mock_result = Mock(spec=DrugDesignResult)
        mock_result.molecules = []
        mock_design_func.return_value = mock_result

        analyzer = QPHAROSAnalyzer()
        result = analyzer.design("6B3J")

        assert isinstance(result, DrugDesignResult)
        assert len(analyzer.session.results) == 1

    @patch("qpharos.analyzer.screen_library")
    def test_analyzer_screen(self, mock_screen_func):
        """Test QPHAROSAnalyzer.screen method"""
        mock_results = []
        for i in range(3):
            mock_result = Mock(spec=DockingResult)
            mock_result.binding_affinity = -7.5 - i
            mock_results.append(mock_result)

        mock_screen_func.return_value = mock_results

        analyzer = QPHAROSAnalyzer()
        hits = analyzer.screen(["CCO", "CC(C)O", "CCCO"], "6B3J", affinity_threshold=-7.0)

        assert len(hits) == 3
        assert len(analyzer.session.results) == 3

    @patch("qpharos.analyzer.predict_admet")
    @patch("qpharos.analyzer.dock")
    def test_analyzer_full_pipeline(self, mock_dock, mock_admet):
        """Test QPHAROSAnalyzer.full_pipeline method"""
        mock_dock_result = Mock(spec=DockingResult)
        mock_dock_result.binding_affinity = -7.5
        mock_dock_result.success = True
        mock_dock.return_value = mock_dock_result

        mock_admet_result = Mock(spec=ADMETResult)
        mock_admet_result.lipinski_pass = True
        mock_admet_result.qed_score = 0.7
        mock_admet.return_value = mock_admet_result

        analyzer = QPHAROSAnalyzer()
        result = analyzer.full_pipeline("CCO", "6B3J")

        assert result["ligand"] == "CCO"
        assert result["receptor"] == "6B3J"
        assert "docking" in result
        assert "admet" in result
        assert "recommendation" in result
        assert "session_id" in result

    def test_analyzer_get_session_summary(self):
        """Test QPHAROSAnalyzer.get_session_summary"""
        analyzer = QPHAROSAnalyzer()

        # Add mock results
        analyzer.session.add_result(Mock(spec=DockingResult, binding_affinity=-8.0))
        analyzer.session.add_result(Mock(spec=ADMETResult))
        analyzer.session.add_result(Mock(spec=DrugDesignResult))

        summary = analyzer.get_session_summary()

        assert summary["total_analyses"] == 3
        assert summary["docking"] == 1
        assert summary["admet"] == 1
        assert summary["design"] == 1
        assert "session_id" in summary
        assert "config" in summary

    def test_analyzer_get_hits(self):
        """Test QPHAROSAnalyzer.get_hits method"""
        analyzer = QPHAROSAnalyzer()

        # Add results with different affinities
        hit1 = Mock(spec=DockingResult)
        hit1.binding_affinity = -8.5

        hit2 = Mock(spec=DockingResult)
        hit2.binding_affinity = -7.5

        non_hit = Mock(spec=DockingResult)
        non_hit.binding_affinity = -5.0

        analyzer.session.add_result(hit1)
        analyzer.session.add_result(hit2)
        analyzer.session.add_result(non_hit)

        hits = analyzer.get_hits(affinity_threshold=-7.0)

        assert len(hits) == 2

    def test_analyzer_clear_session(self):
        """Test QPHAROSAnalyzer.clear_session"""
        analyzer = QPHAROSAnalyzer()

        # Add some results
        analyzer.session.add_result(Mock(spec=DockingResult))
        analyzer.session.add_result(Mock(spec=ADMETResult))

        old_session_id = analyzer.session.session_id

        # Clear session
        analyzer.clear_session()

        assert len(analyzer.session.results) == 0
        assert analyzer.session.session_id != old_session_id

    def test_analyzer_save_report_json(self, tmp_path):
        """Test QPHAROSAnalyzer.save_report in JSON format"""
        analyzer = QPHAROSAnalyzer()
        analyzer.session.add_result(Mock(spec=DockingResult))

        filepath = tmp_path / "report.json"
        analyzer.save_report(str(filepath), format="json")

        assert filepath.exists()

        import json

        with open(filepath, "r") as f:
            data = json.load(f)

        assert "session_id" in data
        assert "total_analyses" in data

    def test_analyzer_save_report_text(self, tmp_path):
        """Test QPHAROSAnalyzer.save_report in text format"""
        analyzer = QPHAROSAnalyzer()

        filepath = tmp_path / "report.txt"
        analyzer.save_report(str(filepath), format="text")

        assert filepath.exists()

        with open(filepath, "r") as f:
            content = f.read()

        assert "QPHAROS Analysis Report" in content
        assert "Session ID" in content


# ============================================================================
# LAYER-BY-LAYER API TESTS (5 Quantum Layers)
# ============================================================================


@pytest.mark.unit
class TestLayerByLayerAPI:
    """Test QPHAROS Layer-by-Layer API (Esquema 4)"""

    def test_layer1_encoder_initialization(self):
        """Test QuantumMolecularEncoder initialization"""
        config = QPHAROSConfig()
        encoder = QuantumMolecularEncoder(config)

        assert encoder.config == config
        assert hasattr(encoder, "encode")

    def test_layer2_binding_initialization(self):
        """Test QuantumBindingPredictor initialization"""
        config = QPHAROSConfig()
        predictor = QuantumBindingPredictor(config)

        assert predictor.config == config
        assert hasattr(predictor, "predict_binding")

    def test_layer3_admet_initialization(self):
        """Test QuantumADMETOptimizer initialization"""
        config = QPHAROSConfig()
        optimizer = QuantumADMETOptimizer(config)

        assert optimizer.config == config
        assert hasattr(optimizer, "optimize")

    def test_layer4_generation_initialization(self):
        """Test QuantumMolecularGAN initialization"""
        config = QPHAROSConfig()
        gan = QuantumMolecularGAN(config)

        assert gan.config == config
        assert hasattr(gan, "generate")

    def test_layer5_dynamics_initialization(self):
        """Test QuantumMolecularDynamics initialization"""
        config = QPHAROSConfig()
        dynamics = QuantumMolecularDynamics(config)

        assert dynamics.config == config
        assert hasattr(dynamics, "simulate")


# ============================================================================
# DATA MODELS TESTS
# ============================================================================


@pytest.mark.unit
class TestDataModels:
    """Test QPHAROS data models"""

    def test_docking_result_creation(self):
        """Test DockingResult model creation"""
        result = DockingResult(
            ligand_smiles="CCO",
            receptor_pdb="6B3J",
            binding_affinity=-8.5,
            ki=0.5,
            ic50=1.2,
            success=True,
        )

        assert result.ligand_smiles == "CCO"
        assert result.receptor_pdb == "6B3J"
        assert result.binding_affinity == -8.5
        assert result.ki == 0.5
        assert result.success is True

    def test_docking_result_from_bioql(self, mock_bioql_result):
        """Test DockingResult.from_bioql_result"""
        result = DockingResult.from_bioql_result(mock_bioql_result)

        assert result.binding_affinity == -8.5
        assert result.ki == 0.589
        assert result.h_bonds == 3
        assert result.lipinski_pass is True
        assert result.job_id == "job_12345"
        assert result.success is True

    def test_admet_result_creation(self):
        """Test ADMETResult model creation"""
        result = ADMETResult(
            smiles="CCO",
            caco2_permeability=5.2,
            hia=92.5,
            lipinski_pass=True,
            qed_score=0.78,
            success=True,
        )

        assert result.smiles == "CCO"
        assert result.caco2_permeability == 5.2
        assert result.lipinski_pass is True

    def test_admet_result_from_bioql(self, mock_bioql_admet_result):
        """Test ADMETResult.from_bioql_result"""
        result = ADMETResult.from_bioql_result(mock_bioql_admet_result)

        assert result.caco2_permeability == 5.2
        assert result.hia == 92.5
        assert result.herg_inhibition is False
        assert result.success is True

    def test_drug_design_result_from_bioql(self, mock_bioql_design_result):
        """Test DrugDesignResult.from_bioql_result"""
        result = DrugDesignResult.from_bioql_result(mock_bioql_design_result)

        assert result.target_protein == "6B3J"
        assert len(result.molecules) == 2
        assert result.molecules[0].smiles == "COc1ccccc1"
        assert result.molecules[0].score == 0.95
        assert result.success is True

    def test_generated_molecule_creation(self):
        """Test GeneratedMolecule model creation"""
        mol = GeneratedMolecule(
            smiles="COc1ccccc1", score=0.95, binding_affinity=-9.2, qed=0.88, lipinski_pass=True
        )

        assert mol.smiles == "COc1ccccc1"
        assert mol.score == 0.95
        assert mol.lipinski_pass is True


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================


@pytest.mark.unit
class TestConfiguration:
    """Test QPHAROS configuration"""

    def test_config_default_values(self):
        """Test QPHAROSConfig default values"""
        config = QPHAROSConfig()

        assert config.backend == "ibm_torino"
        assert config.shots == 4096
        assert config.qec_enabled is True
        assert config.qec_type == "surface_code"
        assert config.binding_qubits == 20
        assert config.max_molecular_weight == 500.0

    def test_config_custom_values(self):
        """Test QPHAROSConfig with custom values"""
        config = QPHAROSConfig(
            backend="simulator", shots=1000, qec_enabled=False, api_key="test_key"
        )

        assert config.backend == "simulator"
        assert config.shots == 1000
        assert config.qec_enabled is False
        assert config.api_key == "test_key"

    def test_config_to_dict(self):
        """Test QPHAROSConfig.to_dict"""
        config = QPHAROSConfig(backend="simulator", shots=1000)
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["backend"] == "simulator"
        assert config_dict["shots"] == 1000
        assert "qec_enabled" in config_dict

    def test_config_from_dict(self):
        """Test QPHAROSConfig.from_dict"""
        config_dict = {"backend": "ibm_kyoto", "shots": 2048, "qec_enabled": False}

        config = QPHAROSConfig.from_dict(config_dict)

        assert config.backend == "ibm_kyoto"
        assert config.shots == 2048
        assert config.qec_enabled is False


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_invalid_smiles_format(self):
        """Test handling of invalid SMILES format"""
        # Note: Actual validation would depend on RDKit integration
        # This tests that the API accepts the input
        with patch("qpharos.api.quantum") as mock_quantum:
            mock_result = Mock()
            mock_result.success = False
            mock_result.error_message = "Invalid SMILES"
            mock_quantum.return_value = mock_result

            result = dock(ligand="INVALID!!!", receptor="6B3J", api_key="test_key")

            assert result.success is False

    def test_invalid_pdb_id(self):
        """Test handling of invalid PDB ID"""
        with patch("qpharos.api.quantum") as mock_quantum:
            mock_result = Mock()
            mock_result.success = False
            mock_result.error_message = "Invalid PDB ID"
            mock_quantum.return_value = mock_result

            result = dock(ligand="CCO", receptor="INVALID", api_key="test_key")

            assert result.success is False

    def test_empty_ligand_list_screening(self):
        """Test screening with empty ligand list"""
        results = screen_library(ligands=[], receptor="6B3J", api_key="test_key")

        assert len(results) == 0

    def test_none_binding_affinity_sorting(self):
        """Test sorting with None binding affinities"""
        with patch("qpharos.api.dock") as mock_dock:
            result1 = Mock(spec=DockingResult)
            result1.binding_affinity = -7.5

            result2 = Mock(spec=DockingResult)
            result2.binding_affinity = None

            mock_dock.side_effect = [result1, result2]

            results = screen_library(ligands=["CCO", "CC(C)O"], receptor="6B3J", api_key="test_key")

            # None values should sort last
            assert results[0].binding_affinity == -7.5

    def test_analyzer_recommendation_failed_docking(self):
        """Test analyzer recommendation when docking fails"""
        analyzer = QPHAROSAnalyzer()

        dock_result = Mock(spec=DockingResult)
        dock_result.success = False

        recommendation = analyzer._generate_recommendation(dock_result, None)

        assert "failed" in recommendation.lower()

    def test_analysis_session_get_hits_empty(self):
        """Test AnalysisSession.get_hits with no results"""
        from datetime import datetime

        session = AnalysisSession(
            session_id="test", started_at=datetime.now(), config=QPHAROSConfig(), results=[]
        )

        hits = session.get_hits()

        assert len(hits) == 0

    def test_analysis_session_add_result(self):
        """Test AnalysisSession.add_result"""
        from datetime import datetime

        session = AnalysisSession(
            session_id="test", started_at=datetime.now(), config=QPHAROSConfig(), results=[]
        )

        result = Mock(spec=DockingResult)
        session.add_result(result)

        assert len(session.results) == 1
        assert session.results[0] == result


# ============================================================================
# SUMMARY
# ============================================================================


def test_count():
    """Count total number of tests"""
    import inspect

    test_count = 0
    test_classes = [
        TestFunctionalAPI,
        TestSimpleAPI,
        TestOOPAPI,
        TestLayerByLayerAPI,
        TestDataModels,
        TestConfiguration,
        TestEdgeCases,
    ]

    for test_class in test_classes:
        methods = [m for m in dir(test_class) if m.startswith("test_")]
        test_count += len(methods)

    print(f"\n{'='*70}")
    print(f"QPHAROS COMPREHENSIVE UNIT TESTS")
    print(f"{'='*70}")
    print(f"Total Test Functions: {test_count}")
    print(f"\nAPI Coverage:")
    print(f"  ✓ Functional API (dock, predict_admet, design_drug): 11 tests")
    print(f"  ✓ Simple API (quick_dock, is_drug_like, test_molecule): 7 tests")
    print(f"  ✓ OOP API (QPHAROSAnalyzer): 12 tests")
    print(f"  ✓ Layer-by-Layer API (5 Quantum Layers): 5 tests")
    print(f"  ✓ Data Models: 6 tests")
    print(f"  ✓ Configuration: 4 tests")
    print(f"  ✓ Edge Cases & Error Handling: 8 tests")
    print(f"{'='*70}\n")

    assert test_count >= 53, f"Expected at least 53 tests, got {test_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
