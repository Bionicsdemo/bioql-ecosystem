#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Example Usage of Quantum Executor
==================================

This script demonstrates how to use the quantum executor module
to run molecular simulations on various quantum backends.

Author: BioQL Team / Quantum_graph Integration
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from circuit_builder import (
    MolecularCircuitBuilder,
    MolecularData,
    build_molecular_circuit,
    create_drug_circuit,
    create_protein_circuit,
)
from quantum_executor import BackendType, QuantumExecutor, execute_on_backend


def example_1_basic_execution():
    """Example 1: Basic circuit execution on simulator"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Circuit Execution")
    print("=" * 70)

    # Create a molecular circuit
    circuit = build_molecular_circuit(num_qubits=4, molecule_type="drug", complexity=0.5)

    print(f"\nCircuit created: {circuit.num_qubits} qubits, depth={circuit.depth()}")

    # Execute on local simulator
    result = execute_on_backend(circuit, BackendType.QISKIT_SIMULATOR, shots=1024)

    print(f"\nExecution Results:")
    print(f"  - Backend: {result.backend}")
    print(f"  - Total shots: {result.total_shots}")
    print(f"  - Execution time: {result.execution_time:.3f}s")
    print(f"  - Cost: ${result.cost:.2f}")
    print(f"  - Most likely outcome: {result.most_likely_outcome}")

    # Show top 5 outcomes
    print(f"\n  Top 5 outcomes:")
    sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
    for outcome, count in sorted_counts[:5]:
        prob = count / result.total_shots
        print(f"    {outcome}: {count:4d} ({prob:6.1%})")


def example_2_protein_simulation():
    """Example 2: Protein folding simulation"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Protein Folding Simulation")
    print("=" * 70)

    # Create protein circuit
    circuit = create_protein_circuit(num_residues=20, folding_complexity=0.75)

    print(f"\nProtein circuit: {circuit.num_qubits} qubits, depth={circuit.depth()}")

    # Execute
    executor = QuantumExecutor()
    result = executor.execute_circuit(circuit, BackendType.QISKIT_SIMULATOR, shots=2048)

    print(f"\nResults:")
    print(f"  - Total outcomes: {len(result.counts)}")
    print(f"  - Execution time: {result.execution_time:.3f}s")

    # Analyze distribution
    probs = result.probabilities()
    max_prob = max(probs.values())
    print(f"  - Maximum probability: {max_prob:.1%}")


def example_3_drug_discovery():
    """Example 3: Drug-target binding simulation"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Drug-Target Binding")
    print("=" * 70)

    # Create drug circuit
    circuit = create_drug_circuit(molecular_weight=450.0, binding_affinity=0.6)

    print(f"\nDrug circuit: {circuit.num_qubits} qubits")

    # Execute
    result = execute_on_backend(circuit, BackendType.QISKIT_SIMULATOR, shots=1024)

    print(f"\nBinding Analysis:")
    print(f"  - Total states measured: {len(result.counts)}")
    print(f"  - Dominant state: {result.most_likely_outcome}")

    # Calculate state diversity (entropy-like measure)
    probs = result.probabilities()
    diversity = len([p for p in probs.values() if p > 0.01])  # States with >1% probability
    print(f"  - State diversity: {diversity} significant states")


def example_4_cost_estimation():
    """Example 4: Cost estimation for different backends"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Cost Estimation")
    print("=" * 70)

    circuit = build_molecular_circuit(8, "protein", 0.7)
    shots = 1024

    print(f"\nCircuit: {circuit.num_qubits} qubits, {circuit.depth()} depth")
    print(f"Shots: {shots}\n")

    executor = QuantumExecutor()

    backends_to_test = [
        BackendType.QISKIT_SIMULATOR,
        BackendType.IONQ_SIMULATOR,
        BackendType.AWS_SV1,
        BackendType.IBM_BRISBANE,
        BackendType.IBM_TORINO,
        BackendType.IONQ_FORTE,
    ]

    print("Cost Estimates:")
    print("-" * 70)

    for backend in backends_to_test:
        cost = executor.estimate_cost(backend, shots)
        info = executor.get_backend_info(backend)

        backend_type = "Simulator" if info.is_simulator else "Hardware"
        print(f"{info.name:20s} ({backend_type:10s}): ${cost:10.2f}")


def example_5_molecular_data_structure():
    """Example 5: Using MolecularData structure"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Molecular Data Structure")
    print("=" * 70)

    # Create detailed molecular data
    mol_data = MolecularData(
        molecule_type="antibody",
        complexity=0.85,
        num_atoms=150,
        num_bonds=165,
        energy_estimate=-450.5,
        properties={"name": "Anti-EGFR antibody", "binding_sites": 2, "molecular_weight": 150000.0},
    )

    print(f"\nMolecular Data:")
    print(f"  - Type: {mol_data.molecule_type}")
    print(f"  - Complexity: {mol_data.complexity}")
    print(f"  - Atoms: {mol_data.num_atoms}")
    print(f"  - Bonds: {mol_data.num_bonds}")
    print(f"  - Properties: {mol_data.properties}")

    # Build circuit from data
    builder = MolecularCircuitBuilder()
    circuit = builder.build_circuit(mol_data)

    print(f"\nGenerated Circuit:")
    print(f"  - Qubits: {circuit.num_qubits}")
    print(f"  - Depth: {circuit.depth()}")
    print(f"  - Parameters: {circuit.num_parameters}")


def example_6_batch_execution():
    """Example 6: Batch execution of multiple molecules"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Batch Execution")
    print("=" * 70)

    # Create multiple circuits
    molecules = [
        ("drug_A", create_drug_circuit(350.0, 0.4)),
        ("drug_B", create_drug_circuit(420.0, 0.6)),
        ("drug_C", create_drug_circuit(500.0, 0.8)),
    ]

    print(f"\nExecuting {len(molecules)} molecules...")

    executor = QuantumExecutor()
    results = []

    for name, circuit in molecules:
        result = executor.execute_circuit(circuit, BackendType.QISKIT_SIMULATOR, shots=512)
        results.append((name, result))
        print(f"  - {name}: {result.total_shots} shots, {result.execution_time:.3f}s")

    # Summary
    total_time = sum(r.execution_time for _, r in results)
    total_cost = sum(r.cost for _, r in results)

    print(f"\nBatch Summary:")
    print(f"  - Total molecules: {len(molecules)}")
    print(f"  - Total execution time: {total_time:.3f}s")
    print(f"  - Total cost: ${total_cost:.2f}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("QUANTUM EXECUTOR EXAMPLES")
    print("=" * 70)

    examples = [
        example_1_basic_execution,
        example_2_protein_simulation,
        example_3_drug_discovery,
        example_4_cost_estimation,
        example_5_molecular_data_structure,
        example_6_batch_execution,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Example failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
