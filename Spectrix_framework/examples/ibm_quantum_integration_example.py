#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL IBM Quantum Integration Example

This script demonstrates how to use the enhanced quantum_connector.py
with real IBM Quantum hardware integration.

To use this example:
1. Set your IBM Quantum token: export IBM_QUANTUM_TOKEN="your_token_here"
2. Run: python examples/ibm_quantum_integration_example.py
"""

import os
import sys
from pathlib import Path

# Add bioql to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioql.quantum_connector import (
    estimate_job_cost,
    get_backend_recommendations,
    list_available_backends,
    parse_bioql_program,
    quantum,
)


def main():
    """Demonstrate IBM Quantum integration features."""

    print("=== BioQL IBM Quantum Integration Demo ===\n")

    # Get IBM Quantum token from environment
    token = os.getenv("IBM_QUANTUM_TOKEN")
    if not token:
        print("Warning: IBM_QUANTUM_TOKEN not set. Simulator-only examples will run.\n")

    # 1. Test basic functionality with simulator
    print("1. Testing basic quantum execution (simulator):")
    result = quantum("Create Bell state", backend="simulator", debug=True)

    if result.success:
        print(f"   ✓ Success! Backend: {result.metadata.get('backend_used')}")
        print(f"   ✓ Most likely outcome: {result.most_likely_outcome}")
        print(f"   ✓ Total shots: {result.total_shots}")
    else:
        print(f"   ✗ Failed: {result.error_message}")

    print()

    # 2. List available backends
    print("2. Listing available backends:")
    backends_info = list_available_backends(token)

    print(f"   Simulators available: {len(backends_info['simulators'])}")
    print(f"   IBM hardware available: {len(backends_info['ibm_hardware'])}")

    # Show a few examples
    for name in list(backends_info["simulators"].keys())[:2]:
        info = backends_info["simulators"][name]
        print(f"     - {name}: {info['qubits']} qubits, ${info['cost_per_shot']:.4f}/shot")

    for name in list(backends_info["ibm_hardware"].keys())[:3]:
        info = backends_info["ibm_hardware"][name]
        print(f"     - {name}: {info['qubits']} qubits, ${info['cost_per_shot']:.4f}/shot")

    print()

    # 3. Cost estimation
    print("3. Testing cost estimation:")
    circuit = parse_bioql_program("Create superposition")

    # Estimate for simulator
    sim_cost = estimate_job_cost(circuit, "simulator", shots=1024)
    print(f"   Simulator cost: ${sim_cost['cost_usd']:.4f} for {sim_cost['shots']} shots")

    # Estimate for IBM hardware
    hw_cost = estimate_job_cost(circuit, "ibm_eagle", shots=1024)
    print(f"   IBM Eagle cost: ${hw_cost['cost_usd']:.4f} for {hw_cost['shots']} shots")
    print(f"   Estimated time: {hw_cost['time_estimate_minutes']} minutes")

    if hw_cost["warnings"]:
        print(f"   Warnings: {hw_cost['warnings']}")

    print()

    # 4. Backend recommendations
    print("4. Getting backend recommendations:")
    try:
        if token:
            # This requires IBM Quantum access
            from qiskit_ibm_runtime import QiskitRuntimeService

            service = QiskitRuntimeService(token=token)
            recommendations = get_backend_recommendations(circuit, service)
        else:
            # Fallback without real service
            recommendations = get_backend_recommendations(circuit, None)

        print(f"   Circuit requirements: {recommendations['circuit_analysis']}")
        if "best_simulator" in recommendations["recommended_backends"]:
            print(f"   Best simulator: {recommendations['recommended_backends']['best_simulator']}")
        if "best_hardware" in recommendations["recommended_backends"]:
            print(f"   Best hardware: {recommendations['recommended_backends']['best_hardware']}")

        if recommendations["warnings"]:
            print(f"   Warnings: {recommendations['warnings']}")

    except Exception as e:
        print(f"   Could not get recommendations: {str(e)}")

    print()

    # 5. IBM Quantum execution (if token is available)
    if token:
        print("5. Testing IBM Quantum execution:")
        print("   Note: This would run on real hardware and incur costs.")
        print("   Uncomment the code below to actually run on IBM hardware.")
        print()

        # Uncomment to run on real hardware (will incur costs!)
        """
        result = quantum(
            "Create Bell state",
            backend='ibm_eagle',  # or 'auto' for automatic selection
            shots=1024,
            token=token,
            debug=True
        )

        if result.success:
            print(f"   ✓ IBM Quantum execution successful!")
            print(f"   ✓ Backend: {result.backend_name}")
            print(f"   ✓ Job ID: {result.job_id}")
            print(f"   ✓ Cost: ${result.cost_estimate:.4f}")
            print(f"   ✓ Execution time: {result.execution_time:.1f}s")
            print(f"   ✓ Results: {result.counts}")
        else:
            print(f"   ✗ IBM Quantum execution failed: {result.error_message}")
        """

        # Instead, show what would happen
        print("   Example output (simulation of IBM execution):")
        print("   ✓ Backend: ibm_eagle")
        print("   ✓ Estimated cost: $1.28")
        print("   ✓ Queue time: 15 minutes")
        print("   ✓ Job submitted with ID: example-job-123")

    else:
        print("5. IBM Quantum execution:")
        print("   Set IBM_QUANTUM_TOKEN environment variable to test real hardware.")

    print()

    # 6. Auto-selection demo
    print("6. Testing automatic backend selection:")
    result = quantum("Generate random bits", backend="auto", auto_select=True, token=token)

    if result.success:
        requested = result.metadata.get("backend_requested", "unknown")
        used = result.metadata.get("backend_used", "unknown")
        print(f"   ✓ Requested: {requested}, Used: {used}")
        print(f"   ✓ Auto-selection successful!")
    else:
        print(f"   ✗ Auto-selection failed: {result.error_message}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
