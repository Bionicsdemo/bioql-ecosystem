#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Billing Integration Usage Examples

This file demonstrates how customers can use the billing-enabled BioQL
quantum computing platform with integrated usage tracking, cost calculation,
and quota management.

The integration is designed to be seamless - existing code works unchanged,
but new billing features are available when needed.
"""

import json
import os
from datetime import datetime

# Set up environment for examples (normally done by customer setup)
os.environ["BIOQL_BILLING_ENABLED"] = "true"
os.environ["BIOQL_BILLING_DATABASE_URL"] = "postgresql://user:pass@localhost/bioql_billing"


def example_1_basic_usage():
    """
    Example 1: Basic usage with billing integration

    Shows how existing code works unchanged, but now includes billing metadata.
    """
    print("=== Example 1: Basic Usage with Billing ===")

    # Import the billing-enabled quantum function
    from bioql.billing_integration import create_billing_quantum_function

    # Create billing-enabled quantum function
    quantum_with_billing = create_billing_quantum_function()

    # Use exactly like the original quantum() function
    result = quantum_with_billing(
        "Create a Bell state and measure both qubits", backend="simulator", shots=1024
    )

    # Original functionality works exactly the same
    print(f"Success: {result.success}")
    print(f"Counts: {result.counts}")
    print(f"Most likely outcome: {result.most_likely_outcome}")

    # New billing information is available
    print(f"\nBilling Information:")
    print(f"Cost estimate: ${result.cost_estimate:.4f}")
    print(f"Algorithm type: {result.billing_metadata.get('algorithm_type', 'N/A')}")
    print(f"Billing enabled: {result.billing_metadata.get('billing_enabled', False)}")

    return result


def example_2_api_key_authentication():
    """
    Example 2: Using API key for user authentication and tracking

    Shows how customers authenticate and get personalized billing.
    """
    print("\n=== Example 2: API Key Authentication ===")

    from bioql.billing_integration import create_billing_quantum_function

    quantum_with_billing = create_billing_quantum_function()

    # Customer uses their API key for authentication
    result = quantum_with_billing(
        "Simulate protein folding with 4 qubits using VQE algorithm",
        backend="simulator",
        shots=2048,
        api_key="bioql_api_key_abc123xyz789",  # Customer's API key
    )

    print(f"Success: {result.success}")
    print(f"Backend used: {result.backend_name}")
    print(f"Total shots: {result.total_shots}")

    # Billing information with user context
    print(f"\nPersonalized Billing:")
    print(f"User ID: {result.user_id}")
    print(f"Total cost: ${result.cost_estimate:.4f}")
    print(f"Usage log ID: {result.usage_log_id}")
    print(f"Cost breakdown: {result.cost_breakdown}")

    # Quota information
    quota_status = result.quota_status
    print(f"\nQuota Status:")
    print(f"Quota check: {'✓ Passed' if quota_status.get('allowed', True) else '✗ Exceeded'}")
    if "limits" in quota_status:
        print(f"Current limits: {quota_status['limits']}")

    return result


def example_3_real_hardware_with_cost_awareness():
    """
    Example 3: Using real quantum hardware with cost awareness

    Shows cost estimation and confirmation before expensive operations.
    """
    print("\n=== Example 3: Real Hardware with Cost Awareness ===")

    from bioql.billing_integration import create_billing_quantum_function

    quantum_with_billing = create_billing_quantum_function()

    # Complex quantum program for drug discovery
    complex_program = """
    Create a 8-qubit quantum circuit for drug-target interaction simulation.
    Use QAOA algorithm with 5 layers to optimize molecular binding affinity.
    Apply variational parameters for different drug candidates.
    """

    # First, get cost estimate without execution
    try:
        # This would be a preview/estimation mode
        from bioql.billing_integration import BillingIntegration

        billing = BillingIntegration()

        # Parse circuit for estimation
        from bioql.quantum_connector import parse_bioql_program

        circuit = parse_bioql_program(complex_program)

        cost_estimate = billing.calculate_cost_estimate(
            circuit_qubits=circuit.num_qubits,
            circuit_depth=circuit.depth(),
            backend="ibm_eagle",
            shots=4096,
            program_text=complex_program,
        )

        print(f"Cost Estimation for Real Hardware:")
        print(f"Circuit: {circuit.num_qubits} qubits, {circuit.depth()} depth")
        print(f"Backend: ibm_eagle")
        print(f"Shots: 4096")
        print(f"Estimated cost: ${cost_estimate['total_cost']:.4f}")
        print(f"Algorithm type: {cost_estimate['algorithm_type']}")
        print(f"Complexity multiplier: {cost_estimate['complexity_multiplier']}")

        # Customer confirms execution
        print(f"\nCustomer confirms execution...")

        # Execute on real hardware
        result = quantum_with_billing(
            complex_program,
            backend="ibm_eagle",
            shots=4096,
            api_key="bioql_api_premium_user_456",
            token="ibm_quantum_token_here",  # Customer's IBM Quantum token
        )

        print(f"\nExecution Results:")
        print(f"Success: {result.success}")
        print(f"Actual cost: ${result.cost_estimate:.4f}")
        print(f"Execution time: {result.execution_time:.1f}s")
        print(f"Job ID: {result.job_id}")

        # Detailed billing breakdown
        billing_info = result.billing_metadata
        print(f"\nDetailed Billing:")
        print(
            f"Base cost per shot: ${billing_info.get('cost_breakdown', {}).get('base_cost_per_shot', 0):.6f}"
        )
        print(f"Total shots executed: {result.total_shots}")
        print(
            f"Algorithm complexity factor: {billing_info.get('cost_breakdown', {}).get('complexity_multiplier', 1)}"
        )
        print(
            f"Final amount charged: ${billing_info.get('cost_breakdown', {}).get('total_cost', 0):.4f}"
        )

    except Exception as e:
        print(f"Note: This example requires full billing system setup. Error: {e}")

    return None


def example_4_quota_management():
    """
    Example 4: Quota management and limits

    Shows how the system enforces usage quotas for different user tiers.
    """
    print("\n=== Example 4: Quota Management ===")

    from bioql.billing_integration import create_billing_quantum_function

    quantum_with_billing = create_billing_quantum_function()

    # Free tier user attempting large computation
    print("Free tier user attempting computation...")

    result = quantum_with_billing(
        "Create random quantum circuit with maximum entanglement",
        backend="simulator",
        shots=1500,  # Exceeds free tier limit of 1000 shots/month
        api_key="bioql_api_free_user_789",
    )

    if result.success:
        print(f"✓ Computation successful")
        print(f"Cost: ${result.cost_estimate:.4f}")
    else:
        print(f"✗ Computation blocked: {result.error_message}")
        print(f"Quota status: {result.quota_status}")

        # Show user their current quota usage
        if "current_usage" in result.quota_status:
            usage = result.quota_status["current_usage"]
            limits = result.quota_status["limits"]
            print(f"Current usage: {usage}")
            print(f"Monthly limits: {limits}")
            print(f"Suggestion: Upgrade to premium plan for higher quotas")

    # Premium user with higher quotas
    print(f"\nPremium user with same computation...")

    result = quantum_with_billing(
        "Create random quantum circuit with maximum entanglement",
        backend="simulator",
        shots=1500,
        api_key="bioql_api_premium_user_456",
    )

    print(f"Success: {result.success}")
    if result.success:
        print(f"Cost: ${result.cost_estimate:.4f}")
        print(f"Remaining quota: {result.quota_status.get('remaining', 'Unlimited')}")

    return result


def example_5_session_management():
    """
    Example 5: Session management for grouped operations

    Shows how to group multiple quantum operations into sessions.
    """
    print("\n=== Example 5: Session Management ===")

    from bioql.billing_integration import create_billing_quantum_function

    quantum_with_billing = create_billing_quantum_function()

    # Start a research session
    session_id = f"research_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    api_key = "bioql_api_researcher_123"

    print(f"Starting research session: {session_id}")

    # Multiple related quantum computations
    experiments = [
        ("Test Bell state fidelity", "simulator", 1024),
        ("Protein folding simulation - small molecule", "simulator", 2048),
        ("Drug binding affinity calculation", "simulator", 1024),
        ("Optimization verification", "simulator", 512),
    ]

    session_results = []
    session_total_cost = 0.0

    for i, (program, backend, shots) in enumerate(experiments, 1):
        print(f"\nExperiment {i}: {program}")

        result = quantum_with_billing(
            program,
            backend=backend,
            shots=shots,
            api_key=api_key,
            session_id=session_id,
            client_ip="192.168.1.100",
            user_agent="BioQL Research Client v1.0",
        )

        print(f"  ✓ Success: {result.success}")
        print(f"  Cost: ${result.cost_estimate:.4f}")
        print(f"  Session ID: {result.session_id}")

        session_results.append(result)
        session_total_cost += result.cost_estimate or 0.0

    # Session summary
    print(f"\n=== Session Summary ===")
    print(f"Session ID: {session_id}")
    print(f"Total experiments: {len(experiments)}")
    print(f"Total cost: ${session_total_cost:.4f}")
    print(f"All experiments successful: {all(r.success for r in session_results)}")

    # Each result contains session context
    if session_results:
        billing_meta = session_results[0].billing_metadata
        print(f"User ID: {billing_meta.get('user_id', 'N/A')}")
        print(f"Billing timestamp: {billing_meta.get('billing_timestamp', 'N/A')}")

    return session_results


def example_6_backward_compatibility():
    """
    Example 6: Backward compatibility with existing code

    Shows how existing BioQL code works unchanged.
    """
    print("\n=== Example 6: Backward Compatibility ===")

    # Existing code using standard quantum function
    print("Using original quantum function (no billing):")

    try:
        from bioql.quantum_connector import quantum

        result = quantum("Create GHZ state with 3 qubits", backend="simulator", shots=1024)

        print(f"✓ Success: {result.success}")
        print(f"Counts: {result.counts}")
        print(f"Has billing metadata: {hasattr(result, 'billing_metadata')}")
        if hasattr(result, "billing_metadata"):
            print(f"Billing metadata: {result.billing_metadata}")

    except ImportError as e:
        print(f"Note: Standard quantum function not available: {e}")

    # Same code with auto-billing detection
    print(f"\nUsing auto-billing quantum function:")

    try:
        from bioql.quantum_connector import quantum_auto

        result = quantum_auto(
            "Create GHZ state with 3 qubits",
            backend="simulator",
            shots=1024,
            api_key="bioql_api_user_999",  # Optional billing parameter
        )

        print(f"✓ Success: {result.success}")
        print(f"Counts: {result.counts}")
        print(f"Billing enabled: {result.billing_metadata.get('billing_enabled', False)}")
        if result.billing_metadata.get("billing_enabled"):
            print(f"Cost: ${result.cost_estimate:.4f}")

    except ImportError as e:
        print(f"Note: Auto-billing function not available: {e}")

    return result


def example_7_configuration_and_monitoring():
    """
    Example 7: Configuration and monitoring

    Shows how to configure and monitor the billing system.
    """
    print("\n=== Example 7: Configuration and Monitoring ===")

    # Check billing system status
    try:
        from bioql.billing_integration import configure_billing, get_billing_status
        from bioql.quantum_connector import get_integration_status

        print("Billing System Status:")
        status = get_billing_status()
        for key, value in status.items():
            print(f"  {key}: {value}")

        print(f"\nIntegration Status:")
        integration_status = get_integration_status()
        for key, value in integration_status.items():
            print(f"  {key}: {value}")

        # Configuration example
        print(f"\nConfiguring billing system...")

        # Custom pricing configuration
        custom_pricing = {
            "simulator_cost_per_shot": "0.002",  # Higher cost for premium features
            "hardware_cost_per_shot": "0.015",
            "algorithm_multipliers": {
                "basic": 1.0,
                "vqe": 2.5,  # Higher multiplier for VQE
                "grover": 2.0,
                "shor": 4.0,  # Premium pricing for Shor's algorithm
                "qaoa": 3.0,
            },
        }

        config_result = configure_billing(pricing_config=custom_pricing, enabled=True)

        print(f"Configuration result: {config_result}")

    except ImportError as e:
        print(f"Note: Billing configuration not available: {e}")

    return None


def example_8_error_handling():
    """
    Example 8: Error handling and edge cases

    Shows how billing integration handles various error conditions.
    """
    print("\n=== Example 8: Error Handling ===")

    from bioql.billing_integration import create_billing_quantum_function

    quantum_with_billing = create_billing_quantum_function()

    # Test cases for error handling
    test_cases = [
        {
            "name": "Invalid API key",
            "params": {
                "program": "Create Bell state",
                "api_key": "invalid_key_123",
                "backend": "simulator",
            },
        },
        {
            "name": "Malformed quantum program",
            "params": {
                "program": "This is not a valid quantum program",
                "api_key": "bioql_api_user_999",
                "backend": "simulator",
            },
        },
        {
            "name": "Nonexistent backend",
            "params": {
                "program": "Create Bell state",
                "api_key": "bioql_api_user_999",
                "backend": "nonexistent_backend",
            },
        },
    ]

    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")

        result = quantum_with_billing(**test_case["params"])

        print(f"  Success: {result.success}")
        if not result.success:
            print(f"  Error: {result.error_message}")
            print(f"  Error handling: Billing metadata preserved")
            print(f"  Billing info: {result.billing_metadata}")
        else:
            print(f"  Unexpected success - test may need adjustment")

    return None


def example_9_enterprise_features():
    """
    Example 9: Enterprise features

    Shows advanced features for enterprise customers.
    """
    print("\n=== Example 9: Enterprise Features ===")

    from bioql.billing_integration import create_billing_quantum_function

    # Enterprise configuration with custom database
    quantum_enterprise = create_billing_quantum_function(
        database_url="postgresql://enterprise:secure@corp-db/bioql_billing",
        pricing_config={
            "simulator_cost_per_shot": "0.001",
            "hardware_cost_per_shot": "0.008",  # Enterprise discount
            "algorithm_multipliers": {
                "basic": 1.0,
                "vqe": 1.8,  # Reduced multipliers for enterprise
                "grover": 1.5,
                "shor": 2.5,
                "qaoa": 2.0,
            },
        },
    )

    # Enterprise quantum computation with full metadata
    result = quantum_enterprise(
        "Large-scale drug discovery simulation with 12-qubit system",
        backend="simulator",  # Would be premium hardware in real scenario
        shots=8192,
        api_key="bioql_enterprise_corp_abc123",
        session_id="drug_discovery_batch_2024_q1",
        client_ip="10.0.1.100",
        user_agent="BioQL Enterprise Client v2.1 (Pharmaceutical Research Division)",
    )

    print(f"Enterprise Computation Results:")
    print(f"Success: {result.success}")
    print(f"Cost with enterprise discount: ${result.cost_estimate:.4f}")
    print(f"User ID: {result.user_id}")
    print(f"Session ID: {result.session_id}")

    # Enterprise billing metadata
    billing_meta = result.billing_metadata
    print(f"\nEnterprise Billing Metadata:")
    print(f"Algorithm type: {billing_meta.get('algorithm_type', 'N/A')}")
    print(f"Usage log ID: {billing_meta.get('usage_log_id', 'N/A')}")
    print(f"Cost breakdown: {result.cost_breakdown}")
    print(f"Client metadata preserved: {billing_meta.get('client_metadata', {})}")

    return result


def main():
    """
    Run all billing integration examples.
    """
    print("BioQL Billing Integration Examples")
    print("=" * 50)

    examples = [
        example_1_basic_usage,
        example_2_api_key_authentication,
        example_3_real_hardware_with_cost_awareness,
        example_4_quota_management,
        example_5_session_management,
        example_6_backward_compatibility,
        example_7_configuration_and_monitoring,
        example_8_error_handling,
        example_9_enterprise_features,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\nExample {example_func.__name__} failed: {e}")
            print("This is expected in the demo environment.")

        print("\n" + "-" * 50)

    print("\nAll examples completed!")
    print("\nKey takeaways:")
    print("1. Existing code works unchanged")
    print("2. Billing features are opt-in via API keys")
    print("3. Cost transparency and quota management")
    print("4. Seamless integration with quantum backends")
    print("5. Enterprise-ready with full metadata tracking")


if __name__ == "__main__":
    main()
