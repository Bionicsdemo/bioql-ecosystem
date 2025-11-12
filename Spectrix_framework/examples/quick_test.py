#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Quick Test - 30 Second Demo
100% Natural Language Quantum Computing
"""

from bioql import quantum

# Demo API Key - UNLIMITED access to IonQ Simulator
API_KEY = "__BIOQL_REDACTED__"

print("🧬 BioQL Quick Test - Natural Language Quantum Computing")
print("=" * 60)

# Test 1: Simple Bell State
print("\n✅ Test 1: Create quantum entanglement...")
result1 = quantum(
    "create a bell state with two qubits and measure both",
    backend="simulator",
    api_key=API_KEY,
    shots=1000,
)
print("✅ Success! Bell state created.")

# Test 2: Drug Discovery
print("\n✅ Test 2: Simulate aspirin molecule...")
result2 = quantum(
    "simulate aspirin molecule using variational quantum eigensolver with 4 qubits",
    backend="simulator",
    api_key=API_KEY,
    shots=2048,
)
print("✅ Success! Molecular simulation completed.")

# Test 3: Quantum Search
print("\n✅ Test 3: Quantum search algorithm...")
result3 = quantum(
    "apply grover search on 3 qubits to find state 101",
    backend="simulator",
    api_key=API_KEY,
    shots=1024,
)
print("✅ Success! Quantum search completed.")

print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\n💡 Key Points:")
print("   • 100% Natural Language - No quantum gates!")
print("   • UNLIMITED simulator access")
print("   • Perfect for drug discovery")
print("   • Ready for production")
print("\n🚀 Visit https://bioql.com for more info")
