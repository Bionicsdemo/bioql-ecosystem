#!/usr/bin/env python3
"""
Advanced CRISPR-QAI Demo

Demonstrates:
- Custom quantum engines
- Batch processing from files
- Library optimization for diversity
- AWS Braket integration (if available)
"""

import os
from bioql.crispr_qai import (
    estimate_energy_collapse_simulator,
    rank_guides_batch,
    infer_offtarget_phenotype,
)
from bioql.crispr_qai.adapters import LocalSimulatorEngine
from bioql.crispr_qai.guide_opt import optimize_guide_library, generate_guide_report
from bioql.crispr_qai.io import save_results_csv, save_results_json
from bioql.crispr_qai.safety import validate_research_use, print_safety_disclaimer


def demo_custom_engine():
    """Demo: Custom quantum engine configuration"""
    print("=" * 80)
    print("DEMO 1: Custom Quantum Engine")
    print("=" * 80)

    # Create custom simulator with high shots and seed
    engine = LocalSimulatorEngine(shots=5000, seed=123)

    print(f"Engine: {engine.backend_name}")
    print(f"Shots: {engine.shots}")
    print(f"Validated: {engine.validated}")
    print()

    guide = "ATCGAAGTCGCTAGCTA"
    print(f"Testing with guide: {guide}")
    print()

    from bioql.crispr_qai.energies import estimate_energy_custom
    result = estimate_energy_custom(
        guide_seq=guide,
        engine=engine,
        coupling_strength=1.5
    )

    print(f"Energy: {result['energy_estimate']:.4f}")
    print(f"Confidence: {result['confidence']:.4f}")
    print(f"Runtime: {result['runtime_seconds']:.3f}s")
    print()


def demo_library_optimization():
    """Demo: Optimize guide library for diversity"""
    print("=" * 80)
    print("DEMO 2: Library Optimization")
    print("=" * 80)

    # Generate candidate guides
    candidates = [
        "ATCGAAGTCGCTAGCTA",
        "ATCGAAGTCGCTAGCTG",  # Similar to above (should be filtered)
        "GCTAGCTACGATCCGA",
        "GCTAGCTACGATCCGG",  # Similar to above
        "TTAACCGGTTAACCGG",
        "TTAACCGGTTAACCAA",  # Similar to above
        "CGCGATCGCGATCGCG",
        "ATATATATATATATATAT",
        "GCGCGCGCGCGCGCGC",
        "TAGCTAGCTAGCTAGC",
    ]

    print(f"Optimizing library from {len(candidates)} candidates")
    print(f"Target size: 5 guides")
    print()

    # Optimize for diversity
    optimized = optimize_guide_library(
        guide_sequences=candidates,
        target_size=5,
        shots=1000,
        diversity_threshold=0.3
    )

    print(f"Selected {len(optimized)} diverse, high-scoring guides:")
    for i, guide in enumerate(optimized, 1):
        print(f"\n{i}. {guide['guide_sequence']}")
        print(f"   Score: {guide['composite_score']:.4f}")
        print(f"   Energy: {guide['energy_estimate']:.4f}")
    print()


def demo_batch_export():
    """Demo: Batch processing with export"""
    print("=" * 80)
    print("DEMO 3: Batch Processing + Export")
    print("=" * 80)

    guides = [
        "ATCGAAGTCGCTAGCTA",
        "GCTAGCTACGATCCGA",
        "TTAACCGGTTAACCGG",
    ]

    print(f"Processing {len(guides)} guides...")
    print()

    # Rank guides
    ranked = rank_guides_batch(
        guide_sequences=guides,
        shots=1000
    )

    # Generate report
    report = generate_guide_report(ranked, top_n=3)
    print(report)

    # Export results
    output_dir = "/tmp/crispr_qai_demo"
    os.makedirs(output_dir, exist_ok=True)

    csv_path = f"{output_dir}/ranked_guides.csv"
    json_path = f"{output_dir}/ranked_guides.json"

    save_results_csv(ranked, csv_path)
    save_results_json(ranked, json_path)

    print(f"✅ Results exported:")
    print(f"   CSV:  {csv_path}")
    print(f"   JSON: {json_path}")
    print()


def demo_research_validation():
    """Demo: Research use validation"""
    print("=" * 80)
    print("DEMO 4: Research Use Validation")
    print("=" * 80)

    # Validate research use
    result = validate_research_use(
        purpose="In silico CRISPR guide design for cancer research",
        institution="Academic Research Lab",
        ethics_approval=False  # Not needed for simulation
    )

    print(f"Validated: {result['validated']}")
    print(f"Mode: {result['mode']}")
    print(f"Purpose: {result['purpose']}")
    print()

    if result['warnings']:
        print("Warnings:")
        for warning in result['warnings']:
            print(f"  {warning}")
        print()


def demo_braket_integration():
    """Demo: AWS Braket integration (if available)"""
    print("=" * 80)
    print("DEMO 5: AWS Braket Integration")
    print("=" * 80)

    try:
        from bioql.crispr_qai.adapters import BraketEngine
        from bioql.crispr_qai.energies import estimate_energy_collapse_braket

        print("AWS Braket adapter available!")
        print()
        print("Example usage:")
        print("  result = estimate_energy_collapse_braket(")
        print("      'ATCGAAGTC',")
        print("      backend_name='SV1',  # State vector simulator")
        print("      shots=1000")
        print("  )")
        print()
        print("Supported backends:")
        print("  - SV1: State vector simulator (34 qubits)")
        print("  - DM1: Density matrix simulator (17 qubits, noise)")
        print("  - Aspen-M: Rigetti quantum hardware")
        print("  - Harmony: IonQ quantum hardware")
        print()

    except ImportError:
        print("AWS Braket not available (optional dependency)")
        print("Install with: pip install amazon-braket-sdk boto3")
        print()


def main():
    """Run all advanced demos"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                     CRISPR-QAI Advanced Demo                               ║")
    print("║                  Production-Grade Guide Design                             ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print()

    # Show safety disclaimer first
    print_safety_disclaimer()
    print("\n")

    # Run demos
    demo_custom_engine()
    demo_library_optimization()
    demo_batch_export()
    demo_research_validation()
    demo_braket_integration()

    print("=" * 80)
    print("✅ Advanced demo completed successfully!")
    print()
    print("Production features:")
    print("  ✓ Custom quantum engines")
    print("  ✓ Library optimization for diversity")
    print("  ✓ Batch processing with export")
    print("  ✓ Research use validation")
    print("  ✓ Multi-backend support (Simulator, Braket, Qiskit)")
    print()
    print("Ready for production workflows!")
    print("=" * 80)


if __name__ == "__main__":
    main()
