#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL QEC Protection Example
=============================

Demonstrates protecting BioQL quantum chemistry calculations with QEC.
"""

import os

from quillow import BioQLOptimizer


def main():
    print("=" * 60)
    print("BioQL QEC Protection Example")
    print("=" * 60)
    print()

    # Check API key
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        print("❌ BIOQL_API_KEY not set")
        print("Set with: export BIOQL_API_KEY='your_key'")
        return

    print(f"Using API key: {api_key[:20]}...")
    print()

    # Create optimizer
    print("Creating BioQL optimizer with QEC (d=5)...")
    optimizer = BioQLOptimizer(api_key=api_key, qec_distance=5)
    print("✅ Optimizer ready")
    print()

    # Test 1: Simple molecule on simulator
    print("Test 1: H2 Molecule on Simulator")
    print("-" * 60)

    result = optimizer.execute_with_qec(
        bioql_query="apply VQE to H2 molecule", backend="simulator", shots=1024
    )

    print(f"Energy: {result.get('energy', 'N/A')}")
    print(f"Logical error rate: {result.get('logical_error_rate', 'N/A')}")
    print(f"QEC enabled: {result['qec_enabled']}")
    print()

    # Test 2: Drug docking
    print("Test 2: Molecular Docking")
    print("-" * 60)

    result = optimizer.execute_with_qec(
        bioql_query="dock aspirin to COX-2", backend="simulator", shots=2048
    )

    print(f"Result: {result.get('energy', 'N/A')}")
    print()

    # Benchmark QEC overhead
    print("Test 3: QEC Overhead Analysis")
    print("-" * 60)

    # Simple test circuit
    test_circuit = {"type": "test", "qubits": 4}

    overhead = optimizer.benchmark_qec_overhead(
        circuit=test_circuit, distances=[3, 5, 7], shots=1000
    )

    for key, data in overhead.items():
        print(f"{key}: {data['runtime']:.3f}s " f"(overhead: {data['overhead_factor']:.2f}x)")

    print()
    print("=" * 60)
    print("✅ BioQL integration tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
