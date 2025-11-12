# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Complete QPHAROS Pipeline Example
Full drug discovery workflow for GLP-1R agonist development
"""

import os
import sys

# Add QPHAROS to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import QPHAROSConfig
from core.pipeline import QuantumDrugDesignPipeline


def main():
    """
    Complete drug discovery workflow example
    Target: GLP-1R receptor for diabetes/obesity
    """

    print("\n" + "=" * 80)
    print("🧬 QPHAROS COMPLETE PIPELINE EXAMPLE")
    print("=" * 80 + "\n")

    # Configure QPHAROS
    config = QPHAROSConfig(
        backend="ibm_torino",
        shots=4096,
        qec_enabled=True,
        qec_type="surface_code",
        logical_qubits=2,
        max_iterations=50,
    )

    # Initialize pipeline
    pipeline = QuantumDrugDesignPipeline(
        target_protein="6B3J",  # GLP-1R structure
        disease_profile="type 2 diabetes and obesity",
        config=config,
        backend="ibm_torino",
    )

    # Optional: Provide seed molecules (known GLP-1R agonists)
    seed_molecules = [
        "CCCCCCCCCCCCCCCCCC(=O)NCCC(=O)N[C@@H](CCCCN)C(=O)N[C@@H](C)C(=O)N[C@@H](CCCCN)C(=O)O",  # Liraglutide-like
        "CC(C)C[C@H](NC(=O)[C@H](CCCCN)NC(=O)[C@H](C)N)C(=O)O",  # Semaglutide-like
    ]

    # Run drug design
    print("\n🚀 Starting quantum drug design...\n")

    results = pipeline.design_drug(
        iterations=20, seed_molecules=seed_molecules, save_results=True  # Reduced for example
    )

    # Print summary
    print("\n" + "=" * 80)
    print("📊 DESIGN RESULTS SUMMARY")
    print("=" * 80 + "\n")

    print(f"Best Molecule: {results['molecule']}")
    print(f"Overall Score: {results['score']:.4f}")

    binding = results.get("binding", {})
    if binding.get("binding_affinity"):
        print(f"\nBinding Affinity: {binding['binding_affinity']:.2f} kcal/mol")
    if binding.get("ki"):
        print(f"Ki: {binding['ki']:.2f} nM")

    admet = results.get("admet", {})
    dl = admet.get("drug_likeness", {})
    print(f"\nDrug-likeness Score: {dl.get('qed_score', 0):.2f}")
    print(f"Lipinski Compliant: {'Yes' if dl.get('lipinski_pass') else 'No'}")

    print(f"\nResidence Time: {results.get('residence_time', 0):.2e} seconds")

    # Validate final candidate
    print("\n" + "=" * 80)
    print("✅ VALIDATING FINAL CANDIDATE")
    print("=" * 80 + "\n")

    validation = pipeline.validate_drug(results["molecule"])

    print(f"Efficacy: {validation['efficacy']:.1%}")
    print(f"Safety (low toxicity): {100-validation['toxicity']*100:.1%}")
    print(f"Bioavailability: {validation['bioavailability']:.1%}")

    # Next steps
    print("\n" + "=" * 80)
    print("🔬 RECOMMENDED NEXT STEPS")
    print("=" * 80 + "\n")

    print("1. Synthesize top candidates in medicinal chemistry lab")
    print("2. Run in-vitro binding assays with GLP-1R")
    print("3. Test ADMET properties experimentally")
    print("4. Conduct toxicology studies")
    print("5. Begin preclinical animal studies")
    print("6. If successful, proceed to clinical trials")

    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
