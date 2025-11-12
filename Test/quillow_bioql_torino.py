#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Script de prueba: Quillow + BioQL en IBM Torino
4 qubits lógicos, 1000 shots
Surface Code QEC con distance 3
"""
import os
import sys

# Add BioQL and Quillow to path
sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework")
sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Quillow")

from bioql import quantum

# API Key
api_key = os.getenv("BIOQL_API_KEY", "__BIOQL_REDACTED__")

print("=" * 80)
print("🧬 BioQL + Quillow QEC en IBM Torino")
print("=" * 80)
print("\n📊 Configuración:")
print("   Backend: IBM Torino (133 qubits)")
print("   Logical Qubits: 4")
print("   Shots: 1000")
print("   QEC: Surface Code (distance 3)")
print("   Correction Level: low")
print("=" * 80)

# Import Quillow for real quantum error correction
print("\n🛡️  Importando Quillow QEC...")
try:
    import importlib

    quillow = importlib.import_module("quillow")
    SurfaceCodeSimulator = getattr(quillow, "SurfaceCodeSimulator", None)
    MWPMDecoder = getattr(quillow, "MWPMDecoder", None)

    if SurfaceCodeSimulator is None or MWPMDecoder is None:
        raise ImportError("quillow installed but missing expected classes")

    QUILLOW_AVAILABLE = True
    print("✅ Quillow QEC engine loaded successfully")

    # Initialize Quillow QEC
    qec_distance = 3
    qec_physical_qubits_per_logical = (2 * qec_distance - 1) ** 2
    total_physical_qubits = qec_physical_qubits_per_logical * 4  # 4 logical qubits

    print(f"\n🔧 Quillow QEC Configuration:")
    print(f"   Distance: d={qec_distance}")
    print(f"   Physical qubits per logical: {qec_physical_qubits_per_logical}")
    print(f"   Total physical qubits needed: {total_physical_qubits}")
    print(f"   Decoder: Minimum Weight Perfect Matching (MWPM)")

    qec_simulator = SurfaceCodeSimulator(distance=qec_distance)
    decoder = MWPMDecoder()
    print("   ✅ QEC Simulator initialized")

except Exception as e:
    QUILLOW_AVAILABLE = False
    print(f"⚠️  Quillow not available: {e}")
    print("   Using BioQL native QEC instead")

print("\n" + "=" * 80)
print("⚛️  EJECUTANDO EN IBM TORINO")
print("=" * 80)

# Execute on IBM Torino with QEC
try:
    result = quantum(
        """Create a 4-qubit quantum circuit for molecular docking simulation.
        Apply Hadamard gates to create superposition.
        Add controlled-NOT gates for entanglement.
        Measure all 4 qubits to get quantum states for molecular interaction analysis.""",
        backend="ibm_torino",
        shots=1000,
        api_key=api_key,
        error_correction="surface_code",
        correction_level="low",
        num_logical_qubits=4,
    )

    print(f"\n✅ Quantum Execution Complete!")
    print(f"   Success: {result.success}")

    if result.success:
        print(f"\n📊 Results:")
        print(f"   Backend: {result.backend_name}")
        print(f"   Shots: {result.shots}")

        # Show counts if available
        if hasattr(result, "counts") and result.counts:
            print(f"\n🔢 Measurement Counts:")
            # Show top 10 states
            sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
            for state, count in sorted_counts[:10]:
                probability = count / result.shots * 100
                bar = "█" * int(probability / 2)
                print(f"   |{state}⟩: {count:4d} ({probability:5.1f}%) {bar}")

        # Show QEC metrics if available
        if hasattr(result, "qec_metrics") and result.qec_metrics:
            print(f"\n🛡️  QEC Metrics:")
            for key, value in result.qec_metrics.items():
                print(f"   {key}: {value}")

        # Show metadata
        if hasattr(result, "metadata") and result.metadata:
            print(f"\n📋 Metadata:")
            for key, value in result.metadata.items():
                if key not in ["raw_result", "circuit"]:  # Skip large objects
                    print(f"   {key}: {value}")

        # Cost estimate
        if hasattr(result, "cost_estimate"):
            print(f"\n💰 Cost Estimate: ${result.cost_estimate:.4f}")

    else:
        print(f"\n❌ Execution failed")
        if hasattr(result, "error"):
            print(f"   Error: {result.error}")

except Exception as e:
    print(f"\n❌ Error during execution:")
    print(f"   {type(e).__name__}: {e}")

    # If authentication error, show helpful message
    if "authentication" in str(e).lower() or "api key" in str(e).lower():
        print(f"\n💡 Tip: Set your BioQL API key:")
        print(f"   export BIOQL_API_KEY='your_key_here'")

print("\n" + "=" * 80)
print("🏁 Script Complete")
print("=" * 80)
