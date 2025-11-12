#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Usage Examples

This file demonstrates how to use the core BioQL functionality
for quantum computing in bioinformatics applications.
"""

import os
import sys

# Add the bioql package to the path
sys.path.insert(0, os.path.dirname(__file__))

from bioql import QuantumResult, configure_debug_mode, get_info, quantum


def example_basic_usage():
    """Basic usage examples."""
    print("=== Basic BioQL Usage ===")

    # Simple quantum program
    print("1. Creating a Bell state:")
    result = quantum("Create a Bell state and measure both qubits")
    print(f"   Counts: {result.counts}")
    print(f"   Most likely outcome: {result.most_likely_outcome}")

    # Superposition example
    print("\n2. Creating superposition:")
    result = quantum("Put qubit in superposition", shots=2048)
    print(f"   Counts: {result.counts}")
    print(f"   Probabilities: {result.probabilities()}")

    # Random number generation
    print("\n3. Quantum random number generation:")
    result = quantum("Generate random bit", shots=1000)
    print(f"   Counts: {result.counts}")
    print(f"   Random outcome: {result.most_likely_outcome}")


def example_biotech_applications():
    """Biotechnology-specific examples."""
    print("\n=== Biotechnology Applications ===")

    # Protein folding simulation
    print("1. Protein folding simulation:")
    result = quantum(
        "Model protein folding with 4 amino acids using quantum superposition", shots=1024
    )
    print(f"   Protein conformations: {result.counts}")
    print(f"   Bio interpretation: {result.bio_interpretation}")

    # Drug discovery
    print("\n2. Drug discovery optimization:")
    result = quantum(
        "Optimize molecular binding affinity using quantum variational algorithm", shots=512
    )
    print(f"   Binding states: {result.counts}")
    print(f"   Metadata: {result.metadata}")

    # DNA sequence analysis
    print("\n3. DNA sequence analysis:")
    result = quantum(
        "Search DNA sequence patterns using quantum amplitude amplification", shots=256
    )
    print(f"   Search results: {result.counts}")


def example_debug_mode():
    """Debug mode examples."""
    print("\n=== Debug Mode Examples ===")

    # Enable debug mode globally
    configure_debug_mode(True)

    print("1. Debug mode execution:")
    result = quantum(
        "Create entanglement between qubits for quantum chemistry", debug=True, shots=100
    )
    print(f"   Success: {result.success}")
    print(f"   Statevector available: {result.statevector is not None}")
    print(f"   Detailed metadata: {result.metadata}")

    # Disable debug mode
    configure_debug_mode(False)


def example_error_handling():
    """Error handling examples."""
    print("\n=== Error Handling Examples ===")

    # Invalid program
    print("1. Handling invalid program:")
    result = quantum("", shots=10)
    if not result.success:
        print(f"   Error handled: {result.error_message}")

    # Invalid parameters
    print("\n2. Handling invalid parameters:")
    try:
        result = quantum("Valid program", shots=-1)
    except Exception as e:
        print(f"   Exception caught: {str(e)}")


def example_advanced_features():
    """Advanced feature examples."""
    print("\n=== Advanced Features ===")

    # Different backends
    print("1. Using different backends:")
    result = quantum("Create Bell state", backend="simulator", shots=100)
    print(f"   Backend: {result.metadata.get('backend', 'unknown')}")

    # Custom shots
    print("\n2. Custom shot counts:")
    for shots in [10, 100, 1000]:
        result = quantum("Random quantum state", shots=shots)
        print(f"   {shots} shots: {result.total_shots} total")

    # Bio interpretation
    print("\n3. Biological interpretation:")
    result = quantum("Quantum molecular dynamics simulation", shots=200)
    print(f"   Bio interpretation status: {result.bio_interpretation}")


def main():
    """Main example function."""
    print("BioQL Core Implementation Examples")
    print("=" * 50)

    # Show system information
    info = get_info()
    print(f"BioQL Version: {info['version']}")
    print(f"Python Version: {info['python_version']}")
    print(f"Qiskit Available: {info['qiskit_available']}")
    print()

    try:
        # Run examples
        example_basic_usage()
        example_biotech_applications()
        example_debug_mode()
        example_error_handling()
        example_advanced_features()

        print("\n" + "=" * 50)
        print("✓ All examples completed successfully!")
        print("\nFor more advanced usage, see:")
        print("- bioql/examples/ directory")
        print("- Documentation at docs/")
        print("- Tests in tests/ directory")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()
        print("\nMake sure all dependencies are installed:")
        print("pip install -r requirements.txt")


if __name__ == "__main__":
    main()
