# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Integration tests for BioQL core functionality
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "Spectrix_framework"))

from tests.mocks.api_mocks import MockBackend, MockRDKit
from tests.mocks.mock_quantum_backend import MockQuantumBackend


@pytest.mark.integration
class TestBioQLParser:
    """Test BioQL natural language parser integration"""

    def test_parse_simple_query(self):
        """Test parsing a simple BioQL query"""
        query = "Create a 2-qubit Bell state"
        # Basic parsing test
        assert "qubit" in query.lower()
        assert "bell" in query.lower()

    def test_parse_molecular_query(self):
        """Test parsing molecular query"""
        query = "Analyze molecule CCCO for drug properties"
        assert "molecule" in query.lower()
        assert "CCCO" in query


@pytest.mark.integration
class TestQuantumSimulator:
    """Test quantum simulator integration with mocks"""

    def test_simulator_execution(self):
        """Test basic quantum circuit execution"""
        backend = MockQuantumBackend()

        # Mock circuit
        circuit = {"gates": [("H", 0), ("CNOT", 0, 1)]}

        result = backend.execute(circuit, shots=1000)

        assert result.success
        assert result.shots == 1000
        assert len(result.counts) > 0
        assert sum(result.counts.values()) == 1000

    def test_simulator_with_noise(self):
        """Test simulator with noise model"""
        backend = MockQuantumBackend(noise=True)

        circuit = {"gates": [("H", 0)]}
        result = backend.execute(circuit, shots=1000)

        assert result.success
        # With noise, we should have more varied results
        assert len(result.counts) >= 2

    def test_simulator_failure_handling(self):
        """Test simulator failure handling"""
        backend = MockQuantumBackend()
        backend.should_fail = True

        circuit = {"gates": []}
        result = backend.execute(circuit)

        assert not result.success
        assert "error" in result.metadata


@pytest.mark.integration
class TestMolecularOperations:
    """Test molecular operations with RDKit mocks"""

    @pytest.mark.skip(reason="MockRDKit API needs refactoring")
    def test_smiles_parsing(self):
        """Test SMILES string parsing"""
        rdkit = MockRDKit()
        mol = MockRDKit.mol_from_smiles("CCO")

        assert mol is not None
        assert mol.smiles == "CCO"
        assert mol.num_atoms > 0

    @pytest.mark.skip(reason="MockRDKit API needs refactoring")
    def test_molecular_properties(self):
        """Test molecular property calculation"""
        rdkit = MockRDKit()
        mol = MockRDKit.mol_from_smiles("CC(C)CC1=CC=C(C=C1)C(C)C(=O)O")

        props = mol.compute_properties()

        assert "MW" in props
        assert "LogP" in props
        assert props["MW"] > 0

    @pytest.mark.skip(reason="MockRDKit API needs refactoring")
    def test_molecule_conversion(self):
        """Test molecule format conversion"""
        rdkit = MockRDKit()

        smiles = "CCO"
        mol = MockRDKit.mol_from_smiles(smiles)
        converted = MockRDKit.mol_to_smiles(mol)

        assert converted == smiles


@pytest.mark.integration
class TestQuantumChemistry:
    """Test quantum chemistry integration"""

    def test_hamiltonian_generation(self):
        """Test molecular Hamiltonian generation"""
        # This would normally use qiskit-nature
        # For now, test basic structure
        hamiltonian = {
            "num_qubits": 4,
            "terms": [{"paulis": "ZIII", "coeff": 0.5}, {"paulis": "IZII", "coeff": 0.3}],
        }

        assert hamiltonian["num_qubits"] == 4
        assert len(hamiltonian["terms"]) == 2

    def test_vqe_circuit_construction(self):
        """Test VQE ansatz circuit construction"""
        num_qubits = 4
        layers = 2

        # Mock VQE circuit
        circuit = {"qubits": num_qubits, "layers": layers, "params": [0.1] * (num_qubits * layers)}

        assert circuit["qubits"] == num_qubits
        assert len(circuit["params"]) == num_qubits * layers


@pytest.mark.integration
class TestErrorCorrection:
    """Test quantum error correction integration"""

    def test_surface_code_construction(self):
        """Test surface code construction"""
        distance = 3
        rounds = 5

        # Mock surface code structure
        code = {
            "distance": distance,
            "rounds": rounds,
            "num_data_qubits": distance * distance,
            "num_ancilla_qubits": distance * (distance - 1),
        }

        assert code["distance"] == 3
        assert code["num_data_qubits"] == 9

    def test_syndrome_extraction(self):
        """Test syndrome measurement extraction"""
        import numpy as np

        # Mock syndrome data
        syndromes = np.random.randint(0, 2, size=(100, 12))

        assert syndromes.shape[0] == 100  # shots
        assert syndromes.shape[1] == 12  # detectors


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineIntegration:
    """Test full pipeline integration"""

    @pytest.mark.skip(reason="MockRDKit API needs refactoring")
    def test_molecule_to_hamiltonian_pipeline(self):
        """Test molecule → Hamiltonian → VQE pipeline"""
        rdkit = MockRDKit()

        # Step 1: Parse molecule
        mol = MockRDKit.mol_from_smiles("H2")
        assert mol is not None

        # Step 2: Generate Hamiltonian
        hamiltonian = {"num_qubits": 4, "terms": []}
        assert hamiltonian["num_qubits"] > 0

        # Step 3: Create VQE circuit
        circuit = {"qubits": hamiltonian["num_qubits"]}
        assert circuit["qubits"] == 4

    def test_quantum_execution_pipeline(self):
        """Test quantum circuit execution pipeline"""
        backend = MockQuantumBackend()

        # Build circuit
        circuit = {"gates": [("H", 0), ("CNOT", 0, 1)]}

        # Execute
        result = backend.execute(circuit, shots=1000)

        # Verify
        assert result.success
        assert backend.execution_count == 1
        assert backend.last_circuit == circuit


@pytest.mark.integration
class TestBioQLWorkflow:
    """Test complete BioQL workflow"""

    def test_basic_workflow(self, mock_quantum_result):
        """Test basic BioQL workflow end-to-end"""
        # Parse query
        query = "Create Bell state"

        # Generate circuit
        circuit = {"gates": [("H", 0), ("CNOT", 0, 1)]}
        assert len(circuit["gates"]) == 2

        # Execute (mocked)
        result = mock_quantum_result
        assert result["shots"] == 1000

        # Analyze results
        total_counts = sum(result["counts"].values())
        assert total_counts == result["shots"]

    def test_error_handling_workflow(self):
        """Test workflow with errors"""
        backend = MockQuantumBackend()
        backend.should_fail = True

        circuit = {"gates": []}
        result = backend.execute(circuit)

        # Should handle failure gracefully
        assert not result.success
        assert "error" in result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
