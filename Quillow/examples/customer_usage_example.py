#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Customer Usage Example for Quillow
===================================

This example shows how end-users would use Quillow after installing from PyPI.

Installation:
    pip install quillow

Configuration:
    export BIOQL_API_KEY="__BIOQL_REDACTED__"

Author: SpectrixRD
Date: 2025-10-26
"""

import os

import stim
from backends.bioql_backend import BioQLBackend, BioQLConfig, BioQLOptimizer
from core import RotatedSurfaceCode


def example_1_basic_qec_simulation():
    """Example 1: Basic QEC simulation without BioQL."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Surface Code Simulation")
    print("=" * 70)

    # Create surface code
    surface_code = RotatedSurfaceCode(distance=5, rounds=5)

    # Build circuit
    circuit = surface_code.build_stim_circuit()

    # Sample with noise
    sampler = circuit.compile_detector_sampler()
    syndromes, observables = sampler.sample(shots=10000, separate_observables=True)

    print(f"✅ Simulated d=5 surface code")
    print(f"   Shots: 10,000")
    print(f"   Syndromes shape: {syndromes.shape}")
    print(f"   Observables shape: {observables.shape}")

    # Compute error rate
    from decoders import PyMatchingDecoder

    decoder = PyMatchingDecoder()
    predictions = decoder.decode_batch(syndromes, circuit)

    logical_errors = (predictions != observables[:, 0]).sum()
    logical_error_rate = logical_errors / 10000

    print(f"   Logical error rate: {logical_error_rate:.6f}")
    print(f"   {'✅ Below threshold!' if logical_error_rate < 0.001 else '⚠️  Above threshold'}")


def example_2_bioql_connection():
    """Example 2: Connect to BioQL and validate API key."""
    print("\n" + "=" * 70)
    print("Example 2: BioQL API Connection")
    print("=" * 70)

    # Get API key from environment
    api_key = os.getenv("BIOQL_API_KEY")

    if not api_key:
        print("❌ BIOQL_API_KEY not set in environment")
        print("   Set it with: export BIOQL_API_KEY='bioql_...'")
        return

    print(f"🔑 Using API key: {api_key[:15]}...{api_key[-10:]}")

    # Configure backend
    config = BioQLConfig(api_key=api_key, base_url="https://api.bioql.bio")

    backend = BioQLBackend(config, qec_distance=5)

    # Validate API key
    print("🔍 Validating API key...")
    if backend.validate_api_key():
        print("✅ API key valid!")
    else:
        print("❌ API key invalid")
        return

    # Check quota
    print("💰 Checking account balance...")
    quota = backend.check_quota()

    if "error" not in quota:
        print(f"✅ Balance: ${quota.get('balance', 'N/A')}")
        print(f"   Tier: {quota.get('tier', 'N/A')}")
        print(f"   Monthly shots used: {quota.get('shots_used', 'N/A')}")
    else:
        print(f"⚠️  Could not retrieve quota: {quota['error']}")


def example_3_simple_qec_execution():
    """Example 3: Execute circuit on BioQL simulator with QEC."""
    print("\n" + "=" * 70)
    print("Example 3: BioQL Simulator with QEC Protection")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        print("❌ BIOQL_API_KEY not set. Skipping this example.")
        return

    # Initialize backend
    config = BioQLConfig(api_key=api_key)
    backend = BioQLBackend(config, qec_distance=3)  # Use d=3 for faster execution

    # Create simple test circuit
    circuit = stim.Circuit(
        """
        H 0
        CNOT 0 1
        CNOT 1 2
        M 0 1 2
    """
    )

    print("🔧 Executing circuit on BioQL simulator with d=3 QEC...")
    print("   Backend: simulator")
    print("   Shots: 1000")

    try:
        result = backend.execute(circuit, shots=1000, backend="simulator")

        print("✅ Execution complete!")
        print(f"   Logical error rate: {result.metadata.get('logical_error_rate', 'N/A')}")
        print(f"   QEC distance: {result.metadata.get('qec_distance')}")
        print(f"   Backend: {result.backend_name}")

    except Exception as e:
        print(f"❌ Execution failed: {e}")


def example_4_quantum_chemistry():
    """Example 4: Quantum chemistry calculation with QEC."""
    print("\n" + "=" * 70)
    print("Example 4: Quantum Chemistry with QEC Protection")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        print("❌ BIOQL_API_KEY not set. Skipping this example.")
        return

    # Initialize optimizer
    optimizer = BioQLOptimizer(qec_distance=5)

    print("🧪 Optimizing H2 molecule with VQE + QEC")
    print("   Backend: simulator (use 'ibm_torino' for real hardware)")
    print("   QEC Distance: 5")
    print("   Shots: 1000")

    try:
        result = optimizer.execute_with_qec(
            bioql_query="optimize H2 molecule with VQE", backend="simulator", shots=1000
        )

        print("✅ Calculation complete!")
        print(f"   Energy: {result.get('energy', 'N/A')} Hartree")

        if result.get("raw_energy"):
            print(f"   Raw Energy (no QEC): {result['raw_energy']} Hartree")
            improvement = abs(result["raw_energy"] - result["energy"])
            print(f"   QEC Improvement: {improvement:.6f} Hartree")

        print(f"   Logical error rate: {result.get('logical_error_rate', 'N/A')}")
        print(f"   QEC overhead: 1.5x cost (d=5)")

    except Exception as e:
        print(f"❌ Calculation failed: {e}")


def example_5_real_hardware():
    """Example 5: Execute on real quantum hardware (IBM Torino)."""
    print("\n" + "=" * 70)
    print("Example 5: Real Quantum Hardware Execution")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        print("❌ BIOQL_API_KEY not set. Skipping this example.")
        return

    print("⚠️  This example executes on REAL quantum hardware (IBM Torino)")
    print("   Cost: ~$2-3 per job with QEC (d=5, 2048 shots)")
    print("   Queue time: 5-30 minutes")
    print()

    # Uncomment to actually run on real hardware
    run_on_hardware = False

    if not run_on_hardware:
        print("🛑 Set run_on_hardware=True to execute (currently disabled)")
        return

    # Initialize optimizer
    optimizer = BioQLOptimizer(qec_distance=5)

    print("🚀 Submitting job to IBM Torino...")
    print("   Query: Optimize aspirin molecule")
    print("   Shots: 2048")
    print("   QEC: d=5 surface code")

    try:
        result = optimizer.execute_with_qec(
            bioql_query="optimize aspirin molecule with VQE", backend="ibm_torino", shots=2048
        )

        print("✅ Hardware execution complete!")
        print(f"   Energy: {result['energy']:.6f} Hartree")
        print(f"   Logical error rate: {result['logical_error_rate']:.6f}")
        print(f"   Total cost: ~${2048 * 0.001 * 1.5:.2f}")

    except Exception as e:
        print(f"❌ Hardware execution failed: {e}")


def example_6_benchmark_qec_overhead():
    """Example 6: Benchmark QEC overhead for different distances."""
    print("\n" + "=" * 70)
    print("Example 6: QEC Overhead Benchmark")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        print("❌ BIOQL_API_KEY not set. Skipping this example.")
        return

    optimizer = BioQLOptimizer()

    # Simple test circuit
    circuit = stim.Circuit(
        """
        H 0
        CNOT 0 1
        M 0 1
    """
    )

    print("📊 Benchmarking QEC overhead for d=3,5,7...")

    try:
        results = optimizer.benchmark_qec_overhead(circuit=circuit, distances=[3, 5, 7], shots=500)

        print("\n📈 Results:")
        print(f"{'Distance':<12} {'Runtime (s)':<15} {'Error Rate':<15} {'Overhead':<12}")
        print("-" * 60)

        for key, data in results.items():
            print(
                f"{key:<12} {data['runtime']:<15.3f} "
                f"{data.get('logical_error_rate', 'N/A'):<15} "
                f"{data['overhead_factor']:.2f}x"
            )

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("🔬 QUILLOW - Customer Usage Examples")
    print("=" * 70)
    print()
    print("These examples demonstrate how to use Quillow after installation:")
    print("   pip install quillow")
    print()

    # Run examples
    example_1_basic_qec_simulation()
    example_2_bioql_connection()
    example_3_simple_qec_execution()
    example_4_quantum_chemistry()
    example_5_real_hardware()
    example_6_benchmark_qec_overhead()

    print("\n" + "=" * 70)
    print("✅ All examples complete!")
    print("=" * 70)
    print()
    print("📖 For more information:")
    print("   • Documentation: https://quillow.readthedocs.io")
    print("   • GitHub: https://github.com/spectrixrd/quillow")
    print("   • BioQL Platform: https://bioql.bio")
    print("   • Support: support@bioql.bio")
    print()


if __name__ == "__main__":
    main()
