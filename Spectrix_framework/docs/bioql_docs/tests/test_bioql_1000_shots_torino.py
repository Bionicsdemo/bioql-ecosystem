#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Test Script - 1000 shots on IBM Torino
User: Heinz Jungbluth (heinz@bionics-ai.biz)
API Key: __BIOQL_REDACTED__
Backend: IBM Torino (133-qubit quantum processor)
"""

import os

from bioql import quantum

# Set API key
API_KEY = "__BIOQL_REDACTED__"
os.environ["BIOQL_API_KEY"] = API_KEY

print("=" * 80)
print("🧬 BioQL Test Script - IBM Torino Backend")
print("=" * 80)
print(f"👤 User: Heinz Jungbluth")
print(f"📧 Email: heinz@bionics-ai.biz")
print(f"🔑 API Key: {API_KEY}")
print(f"🖥️  Backend: IBM Torino (133-qubit processor)")
print(f"🎯 Shots: 1000")
print("=" * 80)

# Test 1: Drug Discovery for Cancer
print("\n🔬 Test 1: Cancer Drug Discovery (EGFR inhibitor)")
print("-" * 80)

try:
    result1 = quantum(
        "Design a novel drug molecule that inhibits EGFR for lung cancer treatment",
        backend="ibm_torino",
        shots=1000,
        api_key=API_KEY,
    )

    print("✅ Test 1 Complete!")
    print(f"   Best Molecule: {result1.best_molecule}")
    print(f"   SMILES: {result1.smiles}")
    print(f"   Quantum Score: {result1.quantum_score}")
    print(f"   Properties: {result1.properties}")

except Exception as e:
    print(f"❌ Test 1 Failed: {e}")

print("\n" + "=" * 80)
print("📊 Expected Dashboard Updates:")
print("=" * 80)
print("• Total Shots: 1000")
print("• Backend: IBM Torino (100%)")
print("• Molecules Designed: 1+")
print("• Cost: ~$1.00 (based on IBM Torino pricing)")
print("• Daily Usage Chart: Should show spike for today")
print("=" * 80)

print("\n✅ Script completed!")
print("🌐 Check dashboard at: file:///Users/heinzjungbluth/Desktop/bioql_website/dashboard.html")
print("=" * 80)
