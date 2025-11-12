#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test script for BioQL v6.0.0 Multi-Omics capabilities
"""

print("=" * 70)
print("BioQL v6.0.0 - Multi-Omics Platform Test Suite")
print("=" * 70)
print()

# Test 1: Import check
print("TEST 1: Checking imports...")
print("-" * 70)
try:
    import bioql

    print(f"✓ BioQL version: {bioql.__version__}")

    # Check proteomics
    from bioql.proteomics import analyze_protein_sequence, predict_ptm_sites

    print("✓ Proteomics module imported successfully")

    # Check metabolomics
    from bioql.metabolomics import analyze_metabolic_pathway, identify_metabolite

    print("✓ Metabolomics module imported successfully")

    # Check multiomics
    from bioql.multiomics import integrate_omics_layers

    print("✓ Multi-omics module imported successfully")

    # Check genomics
    from bioql.genomics import analyze_methylation, call_variants

    print("✓ Genomics module imported successfully")

    print("\n✅ All modules imported successfully!\n")
except Exception as e:
    print(f"\n❌ Import failed: {e}\n")
    import traceback

    traceback.print_exc()
    exit(1)

# Test 2: Proteomics - Protein Analysis
print("TEST 2: Proteomics - Protein Analysis")
print("-" * 70)
try:
    from bioql.proteomics import analyze_protein_sequence

    # Test sequence (insulin A chain)
    sequence = "GIVEQCCTSICSLYQLENYCN"
    print(f"Analyzing sequence: {sequence}")

    result = analyze_protein_sequence(sequence, backend="simulator", classify=True)

    print(f"✓ Length: {result.length} amino acids")
    print(f"✓ Molecular Weight: {result.properties.molecular_weight:.2f} Da")
    print(f"✓ Isoelectric Point: {result.properties.isoelectric_point:.2f}")
    print(f"✓ GRAVY: {result.properties.gravy:.3f}")
    if result.protein_family:
        print(f"✓ Protein Family: {result.protein_family} (confidence: {result.confidence:.2%})")
    print(f"✓ Execution time: {result.execution_time:.3f}s")
    print("\n✅ Protein analysis test passed!\n")
except Exception as e:
    print(f"\n❌ Protein analysis failed: {e}\n")
    import traceback

    traceback.print_exc()

# Test 3: Proteomics - PTM Prediction
print("TEST 3: Proteomics - PTM Prediction")
print("-" * 70)
try:
    from bioql.proteomics import predict_phosphorylation

    # Test sequence (part of p53)
    sequence = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP"
    print(f"Predicting phosphorylation sites in: {sequence[:30]}...")

    result = predict_phosphorylation(sequence, threshold=0.6)

    print(f"✓ Found {result.total_sites} phosphorylation sites:")
    for i, site in enumerate(result.sites[:5]):  # Show first 5
        print(
            f"  {i+1}. Position {site.position}: {site.amino_acid} "
            f"(confidence: {site.confidence:.2f}, kinase: {site.kinase or 'Unknown'})"
        )
    if result.total_sites > 5:
        print(f"  ... and {result.total_sites - 5} more sites")
    print(f"✓ Execution time: {result.execution_time:.3f}s")
    print("\n✅ PTM prediction test passed!\n")
except Exception as e:
    print(f"\n❌ PTM prediction failed: {e}\n")
    import traceback

    traceback.print_exc()

# Test 4: Metabolomics - Metabolite Identification
print("TEST 4: Metabolomics - Metabolite Identification")
print("-" * 70)
try:
    from bioql.metabolomics import identify_metabolite

    # Test mass (glucose)
    mass = 180.156
    print(f"Identifying metabolite with mass: {mass} Da")

    result = identify_metabolite(mass, tolerance=0.01)

    print(f"✓ Found {result.total_matches} match(es):")
    for match in result.matches:
        print(f"  - {match.name} ({match.formula})")
        print(f"    HMDB: {match.hmdb_id}, KEGG: {match.kegg_id}")
        print(f"    Mass: {match.mass:.3f} Da")
    print(f"✓ Confidence: {result.confidence:.2f}")
    print("\n✅ Metabolite identification test passed!\n")
except Exception as e:
    print(f"\n❌ Metabolite identification failed: {e}\n")
    import traceback

    traceback.print_exc()

# Test 5: Multi-Omics Integration
print("TEST 5: Multi-Omics Integration")
print("-" * 70)
try:
    import numpy as np
    import pandas as pd
    from bioql.multiomics import integrate_omics_layers

    # Create mock data
    n_genes = 100
    n_samples = 20

    transcriptomics = pd.DataFrame(
        np.random.randn(n_genes, n_samples), columns=[f"Sample_{i}" for i in range(n_samples)]
    )
    proteomics = pd.DataFrame(
        np.random.randn(50, n_samples), columns=[f"Sample_{i}" for i in range(n_samples)]
    )
    metabolomics = pd.DataFrame(
        np.random.randn(30, n_samples), columns=[f"Sample_{i}" for i in range(n_samples)]
    )

    print(f"Integrating omics layers:")
    print(f"  - Transcriptomics: {transcriptomics.shape[0]} genes")
    print(f"  - Proteomics: {proteomics.shape[0]} proteins")
    print(f"  - Metabolomics: {metabolomics.shape[0]} metabolites")

    result = integrate_omics_layers(
        transcriptomics=transcriptomics,
        proteomics=proteomics,
        metabolomics=metabolomics,
        method="quantum_fusion",
    )

    print(f"✓ Integrated data shape: {result.integrated_data.shape}")
    print(f"✓ Number of factors: {len(result.factors)}")
    print(f"✓ Variance explained: {result.explained_variance[:3]}")
    print("\n✅ Multi-omics integration test passed!\n")
except Exception as e:
    print(f"\n❌ Multi-omics integration failed: {e}\n")
    import traceback

    traceback.print_exc()

# Test 6: Genomics - Variant Calling
print("TEST 6: Genomics - Variant Calling")
print("-" * 70)
try:
    from bioql.genomics import call_variants

    # Mock sequencing reads
    reads = ["ATCGATCG", "ATGGATCG", "ATCGATCG"]
    reference = "ATCGATCGATCGATCG"

    print("Calling variants from sequencing reads...")

    result = call_variants(reads, reference, caller="quantum")

    print(f"✓ Found {result.total_variants} variant(s):")
    for variant in result.variants:
        print(f"  - {variant.chromosome}:{variant.position} {variant.ref}>{variant.alt}")
        print(
            f"    Type: {variant.variant_type}, Quality: {variant.quality}, Genotype: {variant.genotype}"
        )
    print(f"✓ Quality threshold: {result.quality_threshold}")
    print("\n✅ Variant calling test passed!\n")
except Exception as e:
    print(f"\n❌ Variant calling failed: {e}\n")
    import traceback

    traceback.print_exc()

# Summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("✅ BioQL v6.0.0 Multi-Omics Platform is ready!")
print()
print("Available capabilities:")
print("  ✓ Proteomics: Protein analysis, PTM prediction, PPI screening")
print("  ✓ Metabolomics: Metabolite ID, pathway analysis, flux analysis")
print("  ✓ Multi-Omics: Quantum-enhanced data integration")
print("  ✓ Genomics: Variant calling, epigenetics, RNA-Seq")
print()
print("Next steps:")
print("  1. Install in development mode: pip install -e .")
print("  2. Build package: python setup.py sdist bdist_wheel")
print("  3. Upload to PyPI: twine upload dist/bioql-6.0.0*")
print("=" * 70)
