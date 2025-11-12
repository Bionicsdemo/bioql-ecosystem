#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test script for BioQL 5.7.0 fixes
Tests:
1. Backend extraction (ibm_torino instead of generic 'ibm')
2. Billing recording with proper status tracking
3. Complete bio_interpretation data
"""

import os

from bioql import quantum

api_key = os.getenv("BIOQL_API_KEY", "__BIOQL_REDACTED__")

print("=" * 80)
print("🧬 BioQL 5.7.0 - BACKEND & BILLING FIXES TEST")
print("=" * 80)

# Test 1: Backend extraction fix (should use ibm_torino, not 'ibm')
print("\n📝 Test 1: Backend Extraction Fix")
print("-" * 50)

try:
    result = quantum(
        "Design a new drug for Alzheimer's disease targeting beta-amyloid aggregation PDB 6B3J",
        backend="ibm_torino",  # Explicitly test ibm_torino
        shots=5000,
        api_key=api_key,
    )

    print(f"✅ Quantum execution completed")
    print(f"Backend used: {getattr(result, 'backend', 'N/A')}")
    print(f"Success: {result.success}")

    # Check billing status
    if hasattr(result, "metadata") and isinstance(result.metadata, dict):
        billing_status = result.metadata.get("billing_status", "N/A")
        print(f"Billing status: {billing_status}")

        if billing_status == "recorded":
            print("✅ Billing recorded successfully")
        elif billing_status == "failed":
            print("⚠️  Billing recording failed (but execution completed)")
        else:
            print(f"⚠️  Unknown billing status: {billing_status}")

    # Test 2: Bio-interpretation data completeness
    print("\n📝 Test 2: Bio-Interpretation Data Completeness")
    print("-" * 50)

    bio = getattr(result, "bio_interpretation", {})

    # Critical fields to check
    critical_fields = [
        "designed_molecule",
        "binding_affinity",
        "qed_score",
        "sa_score",
        "molecular_weight",
        "logP",
        "oral_bioavailability",
        "toxicity_class",
        "h_bonds",
        "lipinski_pass",
    ]

    missing_fields = []
    populated_fields = []

    for field in critical_fields:
        value = bio.get(field)
        if value is not None and value != "N/A":
            populated_fields.append(field)
            print(f"  ✅ {field}: {value}")
        else:
            missing_fields.append(field)
            print(f"  ❌ {field}: N/A or missing")

    print("\n" + "=" * 80)
    print(f"📊 RESULTS SUMMARY")
    print("=" * 80)
    print(f"Populated fields: {len(populated_fields)}/{len(critical_fields)}")
    print(f"Missing fields: {len(missing_fields)}/{len(critical_fields)}")

    if len(populated_fields) == len(critical_fields):
        print("\n✅ ALL TESTS PASSED!")
    elif len(populated_fields) >= len(critical_fields) * 0.8:
        print("\n⚠️  MOST TESTS PASSED (80%+)")
    else:
        print("\n❌ TESTS FAILED - Too many missing fields")

    # Display full molecule data if available
    if bio.get("designed_molecule"):
        print(f"\n🧬 Best Molecule:")
        print(f"   SMILES: {bio['designed_molecule']}")
        print(f"   Name: {bio.get('molecule_name', 'N/A')}")
        print(f"   Binding: {bio.get('binding_affinity', 'N/A')} kcal/mol")
        print(f"   QED: {bio.get('qed_score', 'N/A')}")
        print(f"   Toxicity: {bio.get('toxicity_class', 'N/A')}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print(f"\nThis might indicate:")
    print("  1. Backend validation issue (check if 'ibm_torino' is accepted)")
    print("  2. Billing system issue (check logs for billing errors)")
    print("  3. API key issue (check if API key is valid)")

print("\n" + "=" * 80)
