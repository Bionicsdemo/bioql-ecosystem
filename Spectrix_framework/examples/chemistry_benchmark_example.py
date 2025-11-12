# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Chemistry Benchmarks Example - BioQL v3.1.2+

Demonstrates how to use the chemistry benchmarks module to validate
BioQL's quantum chemistry accuracy against exact literature values.

This example shows:
- Single molecule benchmarking
- Multi-molecule benchmark suite
- Backend comparison
- Statistical analysis
"""

from bioql.benchmarks import (
    LITERATURE_DATA,
    ChemistryBenchmark,
    quick_benchmark,
)


def simple_benchmark():
    """
    Simple single-molecule benchmark.
    """
    print("=" * 80)
    print("SIMPLE BENCHMARK: H2 Molecule")
    print("=" * 80)
    print()

    # Quick benchmark using convenience function
    result = quick_benchmark("H2", backend="simulator")

    print(f"Molecule: {result.molecule}")
    print(f"Backend: {result.backend}")
    print(f"Computed energy: {result.computed_energy:.6f} Hartree")
    print(f"Literature energy: {result.literature_energy:.6f} Hartree")
    print(f"Absolute error: {result.absolute_error:.6f} Hartree")
    print(f"Relative error: {result.relative_error:.2f}%")
    print(f"Execution time: {result.execution_time:.2f}s")
    print()

    if result.passes_threshold(0.05):
        print("✅ PASSED: Result within 5% threshold")
    else:
        print("❌ FAILED: Result exceeds 5% threshold")
    print()


def full_benchmark_suite():
    """
    Run complete benchmark suite across multiple molecules.
    """
    print("=" * 80)
    print("FULL BENCHMARK SUITE")
    print("=" * 80)
    print()

    # Create benchmark instance
    benchmark = ChemistryBenchmark(api_key="__BIOQL_REDACTED__")

    # Run suite on smaller molecules (H2, LiH)
    # Note: Larger molecules (H2O, BeH2, N2) require more qubits and time
    molecules = ["H2", "LiH"]

    print(f"Running benchmark suite for: {', '.join(molecules)}")
    print()

    suite = benchmark.run_suite(
        molecules=molecules,
        backends=["simulator"],
        shots=1024,
        seed=42,  # For reproducibility
    )

    # Display statistics
    print()
    stats = suite.get_statistics()
    print("SUITE STATISTICS:")
    print("-" * 80)
    print(f"Total benchmarks: {stats['total_benchmarks']}")
    print(f"Mean error: {stats['mean_error']:.2f}%")
    print(f"Median error: {stats['median_error']:.2f}%")
    print(f"Std deviation: {stats['std_error']:.2f}%")
    print(f"Error range: {stats['min_error']:.2f}% to {stats['max_error']:.2f}%")
    print(f"Pass rate (5% threshold): {stats['pass_rate_5pct']*100:.1f}%")
    print(f"Mean execution time: {stats['mean_time']:.2f}s")
    print()

    # Generate and display report
    print(suite.generate_report())

    # Save report to file
    suite.save_report("chemistry_benchmark_report.txt")
    print()
    print("✅ Report saved to: chemistry_benchmark_report.txt")
    print()


def backend_comparison():
    """
    Compare accuracy across different backends.
    """
    print("=" * 80)
    print("BACKEND COMPARISON: H2 Molecule")
    print("=" * 80)
    print()

    benchmark = ChemistryBenchmark()

    # Compare simulator with different backends
    # Note: For real backends (ibm, ionq), you need valid API credentials
    backends = ["simulator"]  # Add "ibm", "ionq" if you have credentials

    results = benchmark.compare_backends(
        molecule="H2",
        backends=backends,
        shots=1024,
    )

    print()
    print("COMPARISON RESULTS:")
    print("-" * 80)
    print(f"{'Backend':<15} {'Energy (Ha)':<15} {'Error %':<12} {'Time (s)':<12}")
    print("-" * 80)

    for backend, result in results.items():
        status = "✅" if result.passes_threshold(0.05) else "❌"
        print(
            f"{backend:<15} {result.computed_energy:<15.6f} "
            f"{result.relative_error:>10.2f}% {status} {result.execution_time:>10.2f}s"
        )

    print()


def explore_literature_data():
    """
    Explore available molecules in the benchmark database.
    """
    print("=" * 80)
    print("AVAILABLE BENCHMARK MOLECULES")
    print("=" * 80)
    print()

    print(f"Total molecules: {len(LITERATURE_DATA)}")
    print()

    for mol_id, mol_data in LITERATURE_DATA.items():
        print(f"{mol_id}: {mol_data['name']} ({mol_data['formula']})")
        print(f"  Ground state energy: {mol_data['ground_state_energy']:.3f} Hartree")
        print(f"  Bond distance: {mol_data.get('bond_distance', 'N/A')} Å")
        print(f"  Qubits required: {mol_data['num_qubits']}")
        print(f"  Basis set: {mol_data['basis_set']}")
        print(f"  Source: {mol_data['source']}")
        print()


def main():
    """
    Main example runner.
    """
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "BioQL Chemistry Benchmarks Example" + " " * 24 + "║")
    print("║" + " " * 31 + "v3.1.2" + " " * 41 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # 1. Simple benchmark
    simple_benchmark()

    # 2. Explore available molecules
    explore_literature_data()

    # 3. Full benchmark suite
    full_benchmark_suite()

    # 4. Backend comparison
    backend_comparison()

    print()
    print("=" * 80)
    print("✅ BENCHMARK EXAMPLES COMPLETE")
    print("=" * 80)
    print()
    print("Key Features Demonstrated:")
    print("  ✅ Single molecule benchmarking")
    print("  ✅ Multi-molecule benchmark suite")
    print("  ✅ Statistical analysis")
    print("  ✅ Literature value comparison")
    print("  ✅ Backend comparison")
    print("  ✅ Automated report generation")
    print()
    print("Next Steps:")
    print("  - Add more backends to comparison (ibm, ionq)")
    print("  - Benchmark larger molecules (H2O, BeH2, N2)")
    print("  - Integrate with error mitigation for better accuracy")
    print("  - Use provenance logging to track benchmark history")
    print()


if __name__ == "__main__":
    main()
