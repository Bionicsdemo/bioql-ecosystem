#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Profiler Integration Demo

This demonstrates real-world integration of the Profiler with BioQL's
enhanced_quantum function for production use cases.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioql.enhanced_quantum import enhanced_quantum
from bioql.profiler import Profiler, ProfilingMode, profile_quantum


def demo_1_basic_integration():
    """Demo 1: Basic profiling of enhanced_quantum"""
    print("=" * 70)
    print("Demo 1: Basic Profiling Integration")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.STANDARD)

    # Profile a simple quantum circuit
    result = profiler.profile_quantum(
        enhanced_quantum,
        program="Create a Bell state with H and CNOT gates",
        api_key="bioql_demo_key_12345",
        backend="simulator",
        shots=1024,
        use_nlp=False,  # Use traditional processing
    )

    if result["success"]:
        print("\n✓ Quantum execution successful!")

        summary = result["profiling"]
        print(f"\n📊 Performance Summary:")
        print(f"  - Total Duration: {summary['total_duration']:.3f}s")
        print(f"  - Profiling Overhead: {summary['overhead_percentage']:.2f}%")

        if summary["circuit_metrics"]:
            cm = summary["circuit_metrics"]
            print(f"\n🔬 Circuit Metrics:")
            print(f"  - Qubits: {cm['qubits']}")
            print(f"  - Circuit Depth: {cm['depth']}")
            print(f"  - Total Gates: {cm['gate_count']}")
            print(f"  - Optimization Score: {cm['optimization_score']:.1f}/100")

        if summary["bottlenecks"]:
            print(f"\n⚠️  Found {len(summary['bottlenecks'])} performance issues")
        else:
            print(f"\n✅ No performance bottlenecks detected!")
    else:
        print(f"\n❌ Execution failed: {result['error']}")


def demo_2_cost_tracking():
    """Demo 2: Cost tracking for budget planning"""
    print("\n" + "=" * 70)
    print("Demo 2: Cost Tracking and Budget Planning")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Profile a more complex circuit
    result = profiler.profile_quantum(
        enhanced_quantum,
        program="Run VQE algorithm for molecular energy calculation",
        api_key="bioql_demo_key_12345",
        backend="qiskit",
        shots=2048,
        use_nlp=False,
    )

    if result["success"]:
        summary = result["profiling"]

        if summary["cost_metrics"]:
            cost = summary["cost_metrics"]
            print(f"\n💰 Cost Analysis:")
            print(f"  - This Execution: ${cost['total_cost']:.4f}")
            print(f"  - Base Cost/Shot: ${cost['base_cost_per_shot']:.4f}")
            print(f"  - Complexity Multiplier: {cost['complexity_multiplier']:.2f}x")
            print(f"  - Algorithm Multiplier: {cost['algorithm_multiplier']:.2f}x")
            print(f"\n📈 Projections (100 runs/day):")
            print(f"  - Monthly Cost: ${cost['projected_monthly_cost']:.2f}")
            print(f"  - Annual Cost: ${cost['projected_annual_cost']:.2f}")

            # Budget recommendations
            monthly = cost["projected_monthly_cost"]
            if monthly > 10000:
                print(f"\n💡 Recommendation: Consider circuit optimization to reduce costs")
            elif monthly > 1000:
                print(f"\n💡 Recommendation: Monitor usage closely")
            else:
                print(f"\n✓ Cost projection looks reasonable")


def demo_3_backend_comparison():
    """Demo 3: Compare performance across backends"""
    print("\n" + "=" * 70)
    print("Demo 3: Backend Performance Comparison")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.STANDARD)

    # Compare different backends
    backends = ["simulator", "qiskit"]
    print(f"\nComparing backends: {', '.join(backends)}")
    print("This may take a moment...\n")

    comparison = profiler.compare_backends(
        enhanced_quantum,
        backends,
        program="Create Bell state and measure",
        api_key="bioql_demo_key_12345",
        shots=1024,
        use_nlp=False,
    )

    print(f"📊 Comparison Results:\n")

    # Show results for each backend
    for backend, data in comparison["results"].items():
        print(f"{backend.upper()}:")
        print(f"  - Duration: {data['total_duration']:.3f}s")
        print(f"  - Overhead: {data['overhead_percentage']:.2f}%")

        if data.get("cost_metrics"):
            print(f"  - Cost: ${data['cost_metrics']['total_cost']:.4f}")

        bottleneck_count = len(data.get("bottlenecks", []))
        print(f"  - Bottlenecks: {bottleneck_count}")
        print()

    # Show winners
    print(f"🏆 Best Backend by Criteria:")
    winners = comparison["winner"]
    for criterion, winner in winners.items():
        if winner:
            print(f"  - {criterion.replace('_', ' ').title()}: {winner}")


def demo_4_bottleneck_analysis():
    """Demo 4: Detailed bottleneck analysis and recommendations"""
    print("\n" + "=" * 70)
    print("Demo 4: Bottleneck Analysis and Recommendations")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Simulate a complex workload
    result = profiler.profile_quantum(
        enhanced_quantum,
        program="Run quantum algorithm with deep circuit on multiple qubits",
        api_key="bioql_demo_key_12345",
        backend="simulator",
        shots=4096,
        use_nlp=False,
    )

    if result["success"]:
        summary = result["profiling"]

        if summary["bottlenecks"]:
            print(f"\n⚠️  Performance Analysis: {len(summary['bottlenecks'])} issues detected\n")

            for i, bottleneck in enumerate(summary["bottlenecks"], 1):
                # Severity emoji
                severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                emoji = severity_emoji.get(bottleneck["severity"], "⚪")

                print(
                    f"{i}. {emoji} {bottleneck['type'].upper()} - {bottleneck['severity'].upper()}"
                )
                print(f"   Current: {bottleneck['metric_value']:.2f}")
                print(f"   Threshold: {bottleneck['threshold_value']:.2f}")
                print(f"   Impact: {bottleneck['impact_percentage']:.1f}%")

                if bottleneck.get("stage"):
                    print(f"   Stage: {bottleneck['stage']}")

                print(f"   Recommendations:")
                for rec in bottleneck["recommendations"][:3]:
                    print(f"     • {rec}")
                print()
        else:
            print(f"\n✅ No performance bottlenecks detected!")
            print(f"Your quantum circuit is well-optimized.")


def demo_5_export_reports():
    """Demo 5: Export profiling reports for documentation"""
    print("\n" + "=" * 70)
    print("Demo 5: Export Profiling Reports")
    print("=" * 70)

    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Run profiling
    result = profiler.profile_quantum(
        enhanced_quantum,
        program="Quantum circuit for drug discovery simulation",
        api_key="bioql_demo_key_12345",
        backend="simulator",
        shots=1024,
        use_nlp=False,
    )

    if result["success"]:
        # Create reports directory
        reports_dir = Path(__file__).parent.parent / "reports" / "profiling"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Export JSON report
        json_path = reports_dir / "quantum_execution_report.json"
        profiler.export_report(json_path, format="json")
        print(f"\n✓ JSON report exported to:")
        print(f"  {json_path}")

        # Export Markdown report
        md_path = reports_dir / "quantum_execution_report.md"
        profiler.export_report(md_path, format="markdown")
        print(f"\n✓ Markdown report exported to:")
        print(f"  {md_path}")

        print(f"\n📄 Reports can be:")
        print(f"  - Shared with team members")
        print(f"  - Included in documentation")
        print(f"  - Used for performance tracking over time")
        print(f"  - Submitted for cost analysis")


def demo_6_decorator_pattern():
    """Demo 6: Using decorator pattern for automatic profiling"""
    print("\n" + "=" * 70)
    print("Demo 6: Decorator Pattern for Automatic Profiling")
    print("=" * 70)

    # Create reports directory
    reports_dir = Path(__file__).parent.parent / "reports" / "profiling"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "decorated_execution.json"

    # Define a wrapped function with automatic profiling
    @profile_quantum(mode=ProfilingMode.STANDARD, export_path=report_path, export_format="json")
    def run_quantum_workflow(program, api_key, **kwargs):
        """Execute quantum workflow with automatic profiling"""
        return enhanced_quantum(program, api_key, **kwargs)

    print("\nExecuting function with @profile_quantum decorator...")

    # Call the decorated function
    result = run_quantum_workflow(
        program="Quantum annealing for optimization",
        api_key="bioql_demo_key_12345",
        backend="simulator",
        shots=1024,
        use_nlp=False,
    )

    if result["success"]:
        print("\n✓ Execution completed!")
        print(f"✓ Profiling data automatically captured")
        print(f"✓ Report automatically exported to: {report_path}")

        summary = result["profiling"]
        print(f"\n📊 Quick Stats:")
        print(f"  - Duration: {summary['total_duration']:.3f}s")
        print(f"  - Overhead: {summary['overhead_percentage']:.2f}%")

        print(f"\n💡 Decorator Benefits:")
        print(f"  - Zero manual profiling code")
        print(f"  - Consistent profiling across functions")
        print(f"  - Automatic report generation")
        print(f"  - Easy to enable/disable")


def demo_7_production_workflow():
    """Demo 7: Complete production workflow"""
    print("\n" + "=" * 70)
    print("Demo 7: Complete Production Workflow")
    print("=" * 70)

    print("\nScenario: Running a production quantum workload")
    print("with comprehensive profiling and cost tracking\n")

    # Initialize profiler with detailed mode
    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Execute quantum workload
    result = profiler.profile_quantum(
        enhanced_quantum,
        program="Production quantum circuit for molecular simulation",
        api_key="bioql_demo_key_12345",
        backend="qiskit",
        shots=2048,
        use_nlp=False,
        debug=False,
    )

    if result["success"]:
        summary = result["profiling"]

        # Performance summary
        print("📊 PERFORMANCE SUMMARY")
        print("-" * 40)
        print(f"Total Duration: {summary['total_duration']:.3f}s")
        print(f"Profiling Overhead: {summary['overhead_percentage']:.2f}%")

        # Stage breakdown
        print(f"\n⏱️  STAGE BREAKDOWN")
        print("-" * 40)
        for stage_name, stage_data in summary["stages"].items():
            print(f"{stage_name:20} {stage_data['duration']:>8.3f}s")

        # Circuit metrics
        if summary["circuit_metrics"]:
            cm = summary["circuit_metrics"]
            print(f"\n🔬 CIRCUIT METRICS")
            print("-" * 40)
            print(f"Qubits: {cm['qubits']}")
            print(f"Depth: {cm['depth']}")
            print(f"Gates: {cm['gate_count']}")
            print(f"Optimization Score: {cm['optimization_score']:.1f}/100")

        # Cost analysis
        if summary["cost_metrics"]:
            cost = summary["cost_metrics"]
            print(f"\n💰 COST ANALYSIS")
            print("-" * 40)
            print(f"This Run: ${cost['total_cost']:.4f}")
            print(f"Projected Monthly: ${cost['projected_monthly_cost']:.2f}")
            print(f"Projected Annual: ${cost['projected_annual_cost']:.2f}")

        # Bottleneck summary
        bottleneck_count = len(summary["bottlenecks"])
        print(f"\n⚠️  BOTTLENECK SUMMARY")
        print("-" * 40)
        if bottleneck_count > 0:
            print(f"Issues Found: {bottleneck_count}")
            for b in summary["bottlenecks"]:
                print(f"  - {b['type']} ({b['severity']})")
        else:
            print("No bottlenecks detected ✓")

        # Export report
        reports_dir = Path(__file__).parent.parent / "reports" / "profiling"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "production_workflow.md"
        profiler.export_report(report_path, format="markdown")

        print(f"\n📄 Full report exported to:")
        print(f"   {report_path}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("BioQL Profiler - Integration Demos")
    print("=" * 70)

    demos = [
        ("Basic Integration", demo_1_basic_integration),
        ("Cost Tracking", demo_2_cost_tracking),
        ("Backend Comparison", demo_3_backend_comparison),
        ("Bottleneck Analysis", demo_4_bottleneck_analysis),
        ("Export Reports", demo_5_export_reports),
        ("Decorator Pattern", demo_6_decorator_pattern),
        ("Production Workflow", demo_7_production_workflow),
    ]

    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")

    print("\nRunning selected demos...\n")

    # Run key demos (not all to save time)
    selected_demos = [0, 1, 3, 6]  # Basic, Cost, Bottleneck, Production

    for idx in selected_demos:
        try:
            name, demo_func = demos[idx]
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Integration demos completed!")
    print("=" * 70)
    print("\n💡 Next Steps:")
    print("  - Review generated reports in ./reports/profiling/")
    print("  - Integrate profiler into your quantum workflows")
    print("  - Set up automated profiling for production")
    print("  - Use cost projections for budget planning")


if __name__ == "__main__":
    main()
