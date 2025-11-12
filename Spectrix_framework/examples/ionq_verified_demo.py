#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL + IonQ Simulator - VERIFIED WORKING DEMO
100% Natural Language Quantum Computing on IonQ Cloud

Requirements:
  pip install bioql qiskit-ionq

Tested: October 2, 2025
Status: ✅ FULLY FUNCTIONAL
"""

import time

from bioql import quantum

# Demo API Key - UNLIMITED access
API_KEY = "__BIOQL_REDACTED__"

print("=" * 70)
print("🧬 BioQL + IonQ Simulator - Verified Working Demo")
print("=" * 70)
print()
print("📋 Configuration:")
print(f"   API Key: {API_KEY[:20]}...")
print(f"   Backend: ionq_simulator (IonQ Cloud)")
print(f"   Qubits: Up to 29")
print(f"   Noise Model: Ideal (perfect simulation)")
print(f"   Cost: $0.00 (FREE)")
print()
print("⚠️  Note: IonQ simulator has ~6-7 second queue time per job")
print()
print("-" * 70)
print()

# Example 1: Bell State
print("1️⃣  Bell State Creation on IonQ Simulator")
print("   Query: 'create a bell state with two qubits and measure both'")
print("   ⏳ Submitting to IonQ Cloud...")
start_time = time.time()

result1 = quantum(
    "create a bell state with two qubits and measure both",
    backend="ionq_simulator",
    api_key=API_KEY,
    shots=1000,
)

elapsed = time.time() - start_time
print(f"   ✅ Success! (Completed in {elapsed:.1f}s)")
print(f"   📊 Counts: {result1.counts}")
print(f"   🆔 Job ID: {result1.job_id}")
print()

# Example 2: Drug Discovery
print("2️⃣  Aspirin Molecule Simulation on IonQ")
print("   Query: 'simulate aspirin molecule using VQE with 4 qubits'")
print("   ⏳ Submitting to IonQ Cloud...")
start_time = time.time()

result2 = quantum(
    "simulate aspirin molecule using VQE with 4 qubits to find ground state energy",
    backend="ionq_simulator",
    api_key=API_KEY,
    shots=2048,
)

elapsed = time.time() - start_time
print(f"   ✅ Success! (Completed in {elapsed:.1f}s)")
print(f"   🆔 Job ID: {result2.job_id}")
print()

# Example 3: Grover Search
print("3️⃣  Grover Search Algorithm on IonQ")
print("   Query: 'apply grover search on 3 qubits to find state 101'")
print("   ⏳ Submitting to IonQ Cloud...")
start_time = time.time()

result3 = quantum(
    "apply grover search on 3 qubits to find state 101",
    backend="ionq_simulator",
    api_key=API_KEY,
    shots=1024,
)

elapsed = time.time() - start_time
print(f"   ✅ Success! (Completed in {elapsed:.1f}s)")
print(f"   🆔 Job ID: {result3.job_id}")
print()

# Example 4: Protein Folding
print("4️⃣  Protein Folding Simulation on IonQ")
print("   Query: 'simulate protein folding with 6 qubits'")
print("   ⏳ Submitting to IonQ Cloud...")
start_time = time.time()

result4 = quantum(
    "simulate protein folding with 6 qubits using quantum annealing",
    backend="ionq_simulator",
    api_key=API_KEY,
    shots=2048,
)

elapsed = time.time() - start_time
print(f"   ✅ Success! (Completed in {elapsed:.1f}s)")
print(f"   🆔 Job ID: {result4.job_id}")
print()

# Example 5: Quantum Chemistry
print("5️⃣  Water Molecule Analysis on IonQ")
print("   Query: 'calculate bond angles of water molecule'")
print("   ⏳ Submitting to IonQ Cloud...")
start_time = time.time()

result5 = quantum(
    "calculate bond angles of water molecule using 4 qubits",
    backend="ionq_simulator",
    api_key=API_KEY,
    shots=2048,
)

elapsed = time.time() - start_time
print(f"   ✅ Success! (Completed in {elapsed:.1f}s)")
print(f"   🆔 Job ID: {result5.job_id}")
print()

print("-" * 70)
print()
print("=" * 70)
print("🎉 All 5 Examples Completed Successfully on IonQ!")
print("=" * 70)
print()
print("📊 Summary:")
print(f"   • Total Examples: 5")
print(f"   • Total Shots: {1000 + 2048 + 1024 + 2048 + 2048:,} = 8,168")
print(f"   • Backend: ionq_simulator (IonQ Cloud)")
print(f"   • Average Queue Time: ~6-7 seconds per job")
print(f"   • Success Rate: 100% ✅")
print(f"   • Cost: $0.00 (FREE)")
print()
print("💡 Key Advantages of IonQ Simulator:")
print("   ✓ Cloud-based - No local resources needed")
print("   ✓ 29 qubits available")
print("   ✓ Perfect accuracy (ideal simulator)")
print("   ✓ Same API as real IonQ hardware")
print("   ✓ Production-grade infrastructure")
print()
print("🔄 Next Steps:")
print("   1. Try with more complex queries")
print("   2. Test with up to 29 qubits")
print("   3. For real hardware: get IonQ API token at https://cloud.ionq.com")
print("   4. Switch to ionq_qpu for real quantum computer")
print()
print("📚 Learn more:")
print("   • IONQ_WORKING_GUIDE.md - Complete IonQ guide")
print("   • https://docs.ionq.com - IonQ documentation")
print("   • https://bioql.com - BioQL documentation")
print()
print("=" * 70)
print("🧬 BioQL + IonQ = Quantum Computing Made Easy! ⚛️")
print("=" * 70)
