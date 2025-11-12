# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Integration Tests for Quantum Executor
=======================================

Tests the integration of BioQL quantum infrastructure with Quantum_graph.

Run with: python test_quantum_integration.py
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported"""
    print("\n" + "=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)

    try:
        from quantum_executor import (
            BACKEND_CONFIGS,
            BackendType,
            QuantumExecutionResult,
            QuantumExecutor,
        )

        print("✅ quantum_executor imports successful")
    except Exception as e:
        print(f"❌ quantum_executor import failed: {e}")
        return False

    try:
        from circuit_builder import (
            MolecularCircuitBuilder,
            MolecularData,
            build_molecular_circuit,
            create_drug_circuit,
            create_protein_circuit,
        )

        print("✅ circuit_builder imports successful")
    except Exception as e:
        print(f"❌ circuit_builder import failed: {e}")
        return False

    return True


def test_backend_configs():
    """Test backend configuration"""
    print("\n" + "=" * 70)
    print("TEST 2: Backend Configurations")
    print("=" * 70)

    try:
        from quantum_executor import BACKEND_CONFIGS, BackendType

        print("\nAvailable Backends:")
        print("-" * 70)

        for backend_type, config in BACKEND_CONFIGS.items():
            print(f"\n{config.name}:")
            print(f"  - Qubits: {config.qubits}")
            print(f"  - Cost per shot: ${config.cost_per_shot}")
            print(f"  - Simulator: {config.is_simulator}")
            print(f"  - Description: {config.description}")

        print("\n✅ Backend configurations loaded successfully")
        return True

    except Exception as e:
        print(f"❌ Backend configuration test failed: {e}")
        return False


def test_circuit_builder():
    """Test circuit building from molecular data"""
    print("\n" + "=" * 70)
    print("TEST 3: Circuit Builder")
    print("=" * 70)

    try:
        from circuit_builder import MolecularCircuitBuilder, MolecularData

        # Test 1: Protein circuit
        print("\nTest 3a: Building protein circuit...")
        mol_data = MolecularData(
            molecule_type="protein", complexity=0.7, num_atoms=24, num_bonds=26
        )

        builder = MolecularCircuitBuilder()
        circuit = builder.build_circuit(mol_data)

        print(f"  - Qubits: {circuit.num_qubits}")
        print(f"  - Depth: {circuit.depth()}")
        print(f"  - Gates: {len(circuit.data)}")
        print("  ✅ Protein circuit built successfully")

        # Test 2: Drug circuit
        print("\nTest 3b: Building drug circuit...")
        mol_data = MolecularData(molecule_type="drug", complexity=0.4, num_atoms=12, num_bonds=13)

        circuit = builder.build_circuit(mol_data)
        print(f"  - Qubits: {circuit.num_qubits}")
        print(f"  - Depth: {circuit.depth()}")
        print("  ✅ Drug circuit built successfully")

        # Test 3: Using convenience function
        print("\nTest 3c: Using convenience function...")
        from circuit_builder import create_protein_circuit

        circuit = create_protein_circuit(num_residues=20, folding_complexity=0.8)
        print(f"  - Qubits: {circuit.num_qubits}")
        print(f"  - Depth: {circuit.depth()}")
        print("  ✅ Convenience function works")

        return True

    except Exception as e:
        print(f"❌ Circuit builder test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_executor_initialization():
    """Test QuantumExecutor initialization"""
    print("\n" + "=" * 70)
    print("TEST 4: QuantumExecutor Initialization")
    print("=" * 70)

    try:
        from quantum_executor import QuantumExecutor

        executor = QuantumExecutor()
        print("✅ QuantumExecutor initialized successfully")

        # Test backend listing
        backends = executor.list_backends()
        print(f"\n  Available backends: {len(backends)}")

        # Test cost estimation
        from quantum_executor import BackendType

        cost = executor.estimate_cost(BackendType.IONQ_SIMULATOR, shots=1024)
        print(f"  Cost estimate (IonQ Simulator, 1024 shots): ${cost:.2f}")

        cost = executor.estimate_cost(BackendType.IBM_TORINO, shots=1024)
        print(f"  Cost estimate (IBM Torino, 1024 shots): ${cost:.2f}")

        return True

    except Exception as e:
        print(f"❌ Executor initialization test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_simulator_execution():
    """Test execution on local simulator"""
    print("\n" + "=" * 70)
    print("TEST 5: Simulator Execution")
    print("=" * 70)

    try:
        from circuit_builder import build_molecular_circuit
        from quantum_executor import BackendType, QuantumExecutor

        print("\nBuilding test circuit...")
        circuit = build_molecular_circuit(4, "drug", 0.5)
        print(f"  Circuit: {circuit.num_qubits} qubits, depth={circuit.depth()}")

        print("\nExecuting on local simulator...")
        executor = QuantumExecutor()

        result = executor.execute_circuit(circuit, BackendType.QISKIT_SIMULATOR, shots=1024)

        print(f"\n  Execution Results:")
        print(f"  - Success: {result.success}")
        print(f"  - Backend: {result.backend}")
        print(f"  - Total shots: {result.total_shots}")
        print(f"  - Execution time: {result.execution_time:.3f}s")
        print(f"  - Cost: ${result.cost:.2f}")
        print(f"  - Number of outcomes: {len(result.counts)}")

        if result.counts:
            print(f"  - Most likely outcome: {result.most_likely_outcome}")

            # Show top 3 outcomes
            sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
            print(f"\n  Top 3 outcomes:")
            for outcome, count in sorted_counts[:3]:
                prob = count / result.total_shots
                print(f"    {outcome}: {count} ({prob:.1%})")

        print("\n✅ Simulator execution successful")
        return True

    except Exception as e:
        print(f"❌ Simulator execution test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_convenience_function():
    """Test convenience execution function"""
    print("\n" + "=" * 70)
    print("TEST 6: Convenience Function")
    print("=" * 70)

    try:
        from circuit_builder import create_drug_circuit
        from quantum_executor import BackendType, execute_on_backend

        print("\nCreating drug circuit...")
        circuit = create_drug_circuit(molecular_weight=450.0, binding_affinity=0.6)

        print("Executing with convenience function...")
        result = execute_on_backend(circuit, BackendType.QISKIT_SIMULATOR, shots=512)

        print(f"\n  Results:")
        print(f"  - Success: {result.success}")
        print(f"  - Job ID: {result.job_id}")
        print(f"  - Total shots: {result.total_shots}")
        print(f"  - Execution time: {result.execution_time:.3f}s")

        print("\n✅ Convenience function works")
        return True

    except Exception as e:
        print(f"❌ Convenience function test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_molecular_data_conversion():
    """Test converting dict to molecular data"""
    print("\n" + "=" * 70)
    print("TEST 7: Molecular Data Conversion")
    print("=" * 70)

    try:
        from circuit_builder import convert_molecular_data_to_circuit

        print("\nConverting dictionary to circuit...")
        mol_dict = {
            "molecule_type": "protein",
            "complexity": 0.75,
            "num_atoms": 30,
            "num_bonds": 32,
            "properties": {"name": "test_protein", "temperature": 310.15},
        }

        circuit = convert_molecular_data_to_circuit(mol_dict)

        print(f"  - Qubits: {circuit.num_qubits}")
        print(f"  - Depth: {circuit.depth()}")
        print("✅ Molecular data conversion successful")

        return True

    except Exception as e:
        print(f"❌ Molecular data conversion test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "=" * 70)
    print("QUANTUM EXECUTOR INTEGRATION TESTS")
    print("=" * 70)

    tests = [
        ("Module Imports", test_imports),
        ("Backend Configurations", test_backend_configs),
        ("Circuit Builder", test_circuit_builder),
        ("Executor Initialization", test_executor_initialization),
        ("Simulator Execution", test_simulator_execution),
        ("Convenience Function", test_convenience_function),
        ("Molecular Data Conversion", test_molecular_data_conversion),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
