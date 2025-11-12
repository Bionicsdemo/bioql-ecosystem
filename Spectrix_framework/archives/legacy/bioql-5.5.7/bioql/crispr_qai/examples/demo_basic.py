#!/usr/bin/env python3
"""
Basic CRISPR-QAI Demo

Demonstrates:
- Single guide energy estimation
- Multiple guide ranking
- Off-target prediction
"""

from bioql.crispr_qai import (
    estimate_energy_collapse_simulator,
    rank_guides_batch,
    infer_offtarget_phenotype,
)


def demo_single_guide():
    """Demo: Score single guide RNA"""
    print("=" * 80)
    print("DEMO 1: Single Guide Energy Estimation")
    print("=" * 80)

    guide = "ATCGAAGTCGCTAGCTA"
    print(f"Guide sequence: {guide}")
    print()

    # Estimate binding energy
    result = estimate_energy_collapse_simulator(
        guide_seq=guide,
        shots=1000,
        seed=42
    )

    print(f"Energy estimate: {result['energy_estimate']:.4f}")
    print(f"Confidence: {result['confidence']:.4f}")
    print(f"Runtime: {result['runtime_seconds']:.3f}s")
    print(f"Qubits used: {result['num_qubits']}")
    print()


def demo_rank_guides():
    """Demo: Rank multiple guides"""
    print("=" * 80)
    print("DEMO 2: Guide Ranking")
    print("=" * 80)

    # Example guides for BRCA1 gene
    guides = [
        "ATCGAAGTCGCTAGCTA",
        "GCTAGCTACGATCCGA",
        "TTAACCGGTTAACCGG",
        "CGCGATCGCGATCGCG",
        "AAAAAAAACCCCCCCC",  # Low complexity (should rank lower)
    ]

    print(f"Ranking {len(guides)} guide sequences...")
    print()

    # Rank guides
    ranked = rank_guides_batch(
        guide_sequences=guides,
        shots=1000
    )

    # Display top 3
    print("Top 3 guides:")
    for i, guide in enumerate(ranked[:3], 1):
        print(f"\n{i}. {guide['guide_sequence']}")
        print(f"   Score: {guide['composite_score']:.4f}")
        print(f"   Energy: {guide['energy_estimate']:.4f}")
        print(f"   GC content: {guide['gc_content']*100:.1f}%")
    print()


def demo_offtarget_prediction():
    """Demo: Off-target prediction"""
    print("=" * 80)
    print("DEMO 3: Off-Target Prediction")
    print("=" * 80)

    guide = "ATCGAAGTCGCTAGCTA"
    print(f"Guide sequence: {guide}")
    print()

    # Predict off-targets (heuristic, no genome provided)
    result = infer_offtarget_phenotype(
        guide_seq=guide,
        genome_regions=None
    )

    print(f"Off-target risk: {result['offtarget_risk'].upper()}")
    print(f"Risk score: {result['risk_score']:.3f}")
    print()

    print("Recommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")
    print()


def main():
    """Run all demos"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                       CRISPR-QAI Basic Demo                                ║")
    print("║                    Quantum-Enhanced Guide Design                           ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print()

    # Run demos
    demo_single_guide()
    demo_rank_guides()
    demo_offtarget_prediction()

    print("=" * 80)
    print("✅ Demo completed successfully!")
    print()
    print("Next steps:")
    print("  1. Try with your own guide sequences")
    print("  2. Use real quantum backends (AWS Braket, IBM Qiskit)")
    print("  3. Load guides from CSV/FASTA files")
    print("  4. Export results for validation")
    print()
    print("Command-line interface:")
    print("  bioql-crispr score-energy ATCGAAGTC")
    print("  bioql-crispr rank-guides guides.csv -o ranked.csv")
    print("  bioql-crispr infer-phenotype ATCGAAGTC")
    print("=" * 80)


if __name__ == "__main__":
    main()
