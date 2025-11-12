#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Example - API Key Required for ALL executions
This is how users will use BioQL after installing with pip
"""

# After: pip install bioql
from bioql import quantum


def main():
    print("🧬 BioQL Example - API Key Authentication Required")
    print("=" * 60)

    # Example 1: Without API key - WILL FAIL
    print("\n❌ Example 1: Without API key (will fail)")
    try:
        result = quantum("Create a Bell state")  # Missing api_key parameter
        print("This should NOT print")
    except TypeError as e:
        print(f"   Error: {e}")
        print("   💡 API key is now required for ALL executions!")

    # Example 2: With invalid API key - WILL FAIL
    print("\n❌ Example 2: With invalid API key (will fail)")
    try:
        result = quantum(
            program="Create a Bell state", api_key="invalid_key_123", backend="simulator"
        )
        print("This should NOT print")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 3: With valid API key - SUCCESS
    print("\n✅ Example 3: With valid API key (will work)")
    try:
        # Use demo1 API key for testing
        result = quantum(
            program="Create a 2-qubit Bell state circuit with Hadamard and CNOT gates",
            api_key="__BIOQL_REDACTED__",  # demo1
            backend="simulator",
            shots=100,
        )

        print(f"   Success: {result.success}")
        print(f"   Results: {result.counts}")
        print(f"   Cost: ${result.cost_estimate:.4f}")
        print(f"   Total shots: {result.total_shots}")

    except Exception as e:
        print(f"   Error: {e}")

    # Example 4: Premium backend - requires Pro/Enterprise plan
    print("\n🔒 Example 4: Premium backend access")
    try:
        result = quantum(
            program="Create a Bell state",
            api_key="__BIOQL_REDACTED__",  # demo1 (basic plan)
            backend="ibm_quantum",  # Requires Pro+ plan
            shots=100,
        )
        print("   This might fail if demo1 doesn't have Pro plan")

    except Exception as e:
        print(f"   Expected error for basic plan: {e}")

    print("\n📋 Summary:")
    print("   • pip install bioql - Users install the package")
    print("   • API key required for EVERY quantum() call")
    print("   • No API key = immediate error")
    print("   • Invalid API key = authentication error")
    print("   • Valid API key = execution + billing tracking")
    print("   • Premium backends require Pro/Enterprise plans")
    print("\n🌐 Get API key: https://bioql.com/signup")
    print("💰 Pricing: https://bioql.com/pricing")


if __name__ == "__main__":
    main()
