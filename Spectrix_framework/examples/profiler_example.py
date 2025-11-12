#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Profiler Usage Examples

This script demonstrates how to use the BioQL Profiler module for
performance analysis, cost tracking, and bottleneck detection.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioql.enhanced_quantum import enhanced_quantum
from bioql.profiler import Profiler, ProfilerContext, ProfilingMode, profile_quantum


def example_1_basic_profiling():
    """Example 1: Basic profiling with context manager"""
    print("=" * 70)
    print("Example 1: Basic Profiling with Context Manager")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.STANDARD)

    # Mock quantum function for demonstration
    def mock_quantum_job(program, api_key, backend="simulator", shots=1024):
        import time

        time.sleep(0.5)  # Simulate execution

        # Mock result with metadata
        class MockResult:
            def __init__(self):
                self.success = True
                self.counts = {"00": 512, "11": 512}
                self.metadata = {
                    "qubits": 2,
                    "circuit_depth": 3,
                    "gate_count": 4,
                    "two_qubit_gates": 1,
                    "single_qubit_gates": 3,
                }

        return MockResult()

    # Profile the execution
    result = profiler.profile_quantum(
        mock_quantum_job,
        program="Create a Bell state and measure",
        api_key="bioql_demo_key",
        backend="simulator",
        shots=1024,
    )

    # Display results
    summary = profiler.get_summary()
    print(f"\n✓ Total Duration: {summary['total_duration']:.3f}s")
    print(f"✓ Profiling Overhead: {summary['overhead_percentage']:.2f}%")

    print("\n📊 Stage Breakdown:")
    for stage_name, stage_data in summary["stages"].items():
        print(f"  - {stage_name}: {stage_data['duration']:.3f}s")

    if summary["circuit_metrics"]:
        cm = summary["circuit_metrics"]
        print(f"\n🔬 Circuit Metrics:")
        print(f"  - Qubits: {cm['qubits']}")
        print(f"  - Depth: {cm['depth']}")
        print(f"  - Gates: {cm['gate_count']}")
        print(f"  - Optimization Score: {cm['optimization_score']:.1f}/100")

    if summary["bottlenecks"]:
        print(f"\n⚠️  Detected {len(summary['bottlenecks'])} bottlenecks")
    else:
        print("\n✅ No bottlenecks detected!")


def example_2_detailed_profiling_with_costs():
    """Example 2: Detailed profiling with cost analysis"""
    print("\n" + "=" * 70)
    print("Example 2: Detailed Profiling with Cost Analysis")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Mock quantum function
    def mock_vqe_job(program, api_key, backend="qiskit", shots=2048):
        import time

        time.sleep(1.2)  # Simulate longer execution

        class MockResult:
            def __init__(self):
                self.success = True
                self.counts = {"0000": 1024, "1111": 1024}
                self.metadata = {
                    "qubits": 4,
                    "circuit_depth": 25,
                    "gate_count": 48,
                    "two_qubit_gates": 12,
                    "single_qubit_gates": 36,
                }

        return MockResult()

    # Profile the execution
    result = profiler.profile_quantum(
        mock_vqe_job,
        program="Run VQE for H2 molecule with 4 qubits",
        api_key="bioql_demo_key",
        backend="qiskit",
        shots=2048,
    )

    summary = profiler.get_summary()

    print(f"\n✓ Total Duration: {summary['total_duration']:.3f}s")

    # Display cost metrics
    if summary["cost_metrics"]:
        cost = summary["cost_metrics"]
        print(f"\n💰 Cost Analysis:")
        print(f"  - Total Cost: ${cost['total_cost']:.4f}")
        print(f"  - Base Cost/Shot: ${cost['base_cost_per_shot']:.4f}")
        print(f"  - Complexity Multiplier: {cost['complexity_multiplier']:.2f}x")
        print(f"  - Algorithm Multiplier: {cost['algorithm_multiplier']:.2f}x")
        print(f"  - Projected Monthly: ${cost['projected_monthly_cost']:.2f}")
        print(f"  - Projected Annual: ${cost['projected_annual_cost']:.2f}")


def example_3_decorator_usage():
    """Example 3: Using the @profile_quantum decorator"""
    print("\n" + "=" * 70)
    print("Example 3: Using @profile_quantum Decorator")
    print("=" * 70)

    # Define function with profiling decorator
    @profile_quantum(mode=ProfilingMode.STANDARD, export_path=None)  # Set to path to export report
    def run_bell_state(program, api_key, **kwargs):
        import time

        time.sleep(0.3)

        class MockResult:
            def __init__(self):
                self.success = True
                self.counts = {"00": 256, "11": 256}
                self.metadata = {"qubits": 2, "circuit_depth": 2, "gate_count": 3}

        return MockResult()

    # Call the decorated function
    result = run_bell_state(
        program="Create Bell state", api_key="bioql_demo_key", backend="simulator", shots=512
    )

    print(f"\n✓ Function executed with automatic profiling")
    print(f"✓ Result contains profiling data and quantum results")


def example_4_bottleneck_detection():
    """Example 4: Bottleneck detection and recommendations"""
    print("\n" + "=" * 70)
    print("Example 4: Bottleneck Detection and Recommendations")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Mock quantum function with performance issues
    def mock_complex_circuit(program, api_key, backend="simulator", shots=1024):
        import time

        time.sleep(2.5)  # Simulate slow execution

        class MockResult:
            def __init__(self):
                self.success = True
                self.counts = {}
                self.metadata = {
                    "qubits": 12,  # High qubit count
                    "circuit_depth": 250,  # Very deep circuit
                    "gate_count": 800,  # Many gates
                    "two_qubit_gates": 200,
                    "single_qubit_gates": 600,
                }

        return MockResult()

    # Profile the execution
    result = profiler.profile_quantum(
        mock_complex_circuit,
        program="Run complex quantum algorithm on 12 qubits",
        api_key="bioql_demo_key",
        backend="simulator",
        shots=1024,
    )

    summary = profiler.get_summary()

    # Display bottlenecks
    if summary["bottlenecks"]:
        print(f"\n⚠️  Detected {len(summary['bottlenecks'])} performance bottlenecks:\n")

        for i, bottleneck in enumerate(summary["bottlenecks"], 1):
            severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
            emoji = severity_emoji.get(bottleneck["severity"], "⚪")

            print(f"{i}. {emoji} {bottleneck['type'].upper()} - {bottleneck['severity'].upper()}")
            print(
                f"   Value: {bottleneck['metric_value']:.2f} (threshold: {bottleneck['threshold_value']:.2f})"
            )
            print(f"   Impact: {bottleneck['impact_percentage']:.1f}%")
            print(f"   Recommendations:")
            for rec in bottleneck["recommendations"][:3]:  # Show first 3
                print(f"     • {rec}")
            print()


def example_5_backend_comparison():
    """Example 5: Compare performance across multiple backends"""
    print("\n" + "=" * 70)
    print("Example 5: Backend Comparison")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.STANDARD)

    # Mock quantum function
    def mock_quantum_circuit(program, api_key, backend="simulator", shots=1024):
        import random
        import time

        # Simulate different execution times for different backends
        backend_times = {"simulator": 0.3, "qiskit": 0.5, "cirq": 0.4}
        time.sleep(backend_times.get(backend, 0.5))

        class MockResult:
            def __init__(self):
                self.success = True
                self.counts = {"00": 512, "11": 512}
                self.metadata = {"qubits": 2, "circuit_depth": 3, "gate_count": 4}

        return MockResult()

    # Compare backends
    backends = ["simulator", "qiskit", "cirq"]
    comparison = profiler.compare_backends(
        mock_quantum_circuit,
        backends,
        program="Create Bell state",
        api_key="bioql_demo_key",
        shots=1024,
    )

    print(f"\n📊 Comparison Results:\n")
    print(f"Backends tested: {', '.join(backends)}")
    print(f"\n🏆 Winners:")
    for criterion, winner in comparison["winner"].items():
        if winner:
            print(f"  - {criterion.replace('_', ' ').title()}: {winner}")


def example_6_export_reports():
    """Example 6: Export profiling reports"""
    print("\n" + "=" * 70)
    print("Example 6: Export Profiling Reports")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Mock quantum function
    def mock_quantum_job(program, api_key, backend="simulator", shots=1024):
        import time

        time.sleep(0.4)

        class MockResult:
            def __init__(self):
                self.success = True
                self.counts = {"00": 512, "11": 512}
                self.metadata = {"qubits": 2, "circuit_depth": 5, "gate_count": 8}

        return MockResult()

    # Profile the execution
    result = profiler.profile_quantum(
        mock_quantum_job,
        program="Create Bell state with measurements",
        api_key="bioql_demo_key",
        backend="simulator",
        shots=1024,
    )

    # Create reports directory
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Export JSON report
    json_path = reports_dir / "profile_report.json"
    profiler.export_report(json_path, format="json")
    print(f"\n✓ JSON report exported to: {json_path}")

    # Export Markdown report
    md_path = reports_dir / "profile_report.md"
    profiler.export_report(md_path, format="markdown")
    print(f"✓ Markdown report exported to: {md_path}")


def example_7_context_manager():
    """Example 7: Using ProfilerContext directly for custom profiling"""
    print("\n" + "=" * 70)
    print("Example 7: Direct ProfilerContext Usage")
    print("=" * 70)

    with ProfilerContext(mode=ProfilingMode.DEBUG) as ctx:
        # Stage 1: Data preparation
        ctx.start_stage("data_preparation")
        import time

        time.sleep(0.2)
        ctx.end_stage("data_preparation")

        # Stage 2: Circuit compilation
        ctx.start_stage("circuit_compilation", metadata={"backend": "qiskit"})
        time.sleep(0.3)
        ctx.end_stage("circuit_compilation")

        # Stage 3: Execution
        ctx.start_stage("execution")
        time.sleep(0.5)
        ctx.end_stage("execution")

        # Stage 4: Post-processing
        ctx.start_stage("post_processing")
        time.sleep(0.1)
        ctx.end_stage("post_processing")

    print(f"\n✓ Total Duration: {ctx.get_total_duration():.3f}s")
    print(f"\n📊 Stage Breakdown:")
    for stage_name, stage in ctx.stages.items():
        print(
            f"  - {stage_name}: {stage.duration:.3f}s "
            f"(CPU: {stage.cpu_percent:.1f}%, Memory: {stage.memory_mb:.1f}MB)"
        )


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("BioQL Profiler - Usage Examples")
    print("=" * 70)

    examples = [
        ("Basic Profiling", example_1_basic_profiling),
        ("Detailed Profiling with Costs", example_2_detailed_profiling_with_costs),
        ("Decorator Usage", example_3_decorator_usage),
        ("Bottleneck Detection", example_4_bottleneck_detection),
        ("Backend Comparison", example_5_backend_comparison),
        ("Export Reports", example_6_export_reports),
        ("Context Manager", example_7_context_manager),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...\n")

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
