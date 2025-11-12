#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Complete BioQL Integration Demo

This comprehensive demo showcases all major BioQL features and their integration:
1. Natural Language Quantum Programming
2. Circuit Profiling and Performance Analysis
3. Circuit Optimization
4. Smart Batching
5. Circuit Caching
6. Circuit Library/Catalog
7. Semantic Parsing
8. Enhanced NL Mapping
9. Dashboard Generation
10. Drug Discovery Workflows

Author: BioQL Development Team
Version: 1.0.0
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Core BioQL
from bioql import QuantumResult, quantum

# Advanced features
try:
    from bioql.batcher import BatchingStrategy, QuantumJob, SmartBatcher
    from bioql.cache import CircuitCache
    from bioql.circuits.catalog import CircuitCatalog
    from bioql.dashboard import ProfilingDashboard
    from bioql.mapper import EnhancedNLMapper
    from bioql.optimizer import CircuitOptimizer, OptimizationLevel
    from bioql.parser.semantic_parser import SemanticParser
    from bioql.profiler import Profiler, ProfilingMode

    ADVANCED_FEATURES = True
except ImportError as e:
    print(f"⚠️  Some advanced features not available: {e}")
    print("Continuing with basic demo...\n")
    ADVANCED_FEATURES = False


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_result(label: str, value: Any):
    """Print a labeled result."""
    print(f"  ✓ {label}: {value}")


def demo_1_basic_natural_language():
    """Demo 1: Basic Natural Language Quantum Programming."""
    print_section("Demo 1: Natural Language Quantum Programming")

    queries = [
        "Create a Bell state",
        "Create 3-qubit GHZ state",
        "Apply Hadamard to all qubits",
        "Create superposition on 4 qubits",
    ]

    for query in queries:
        print(f"Query: '{query}'")
        result = quantum(query, shots=100)

        if result.success:
            print_result("Status", "Success ✓")
            print_result("Counts", dict(list(result.counts.items())[:3]))
        else:
            print_result("Status", "Failed ✗")

        print()


def demo_2_profiling_workflow():
    """Demo 2: End-to-End Profiling Workflow."""
    if not ADVANCED_FEATURES:
        print_section("Demo 2: Profiling (SKIPPED - Advanced features not available)")
        return

    print_section("Demo 2: End-to-End Profiling with Dashboard")

    # Create profiler
    profiler = Profiler(mode=ProfilingMode.DETAILED)

    # Profile a complex workflow
    with profiler.profile("drug_screening"):
        # Stage 1: Molecule preparation
        with profiler.stage("molecule_prep"):
            time.sleep(0.05)  # Simulate work
            profiler.record_metadata({"molecules_prepared": 10, "validation_passed": True})

        # Stage 2: Docking simulation
        with profiler.stage("docking"):
            result = quantum("Dock aspirin to COX-2", shots=200)
            profiler.record_circuit_metrics(num_qubits=8, gate_count=45, circuit_depth=22)
            profiler.record_cost(base_cost=0.05, complexity_cost=0.02, total_cost=0.07)

        # Stage 3: ADME prediction
        with profiler.stage("adme_prediction"):
            result = quantum("Predict bioavailability", shots=150)
            profiler.record_circuit_metrics(num_qubits=6, gate_count=30, circuit_depth=15)

        # Stage 4: Results analysis
        with profiler.stage("analysis"):
            time.sleep(0.03)
            profiler.record_metadata({"candidates_identified": 3, "confidence_score": 0.87})

    # Get profiling summary
    summary = profiler.get_summary()
    workflow_data = summary["drug_screening"]

    print_result("Total Time", f"{workflow_data['total_time']:.3f}s")
    print_result("Stages", len(workflow_data["stages"]))
    print_result("Total Cost", f"${workflow_data['costs']['total_cost']:.4f}")

    # Generate dashboard
    dashboard = ProfilingDashboard(theme="light")
    html_content = dashboard.generate_html(workflow_data)

    # Save dashboard
    output_path = Path("bioql_profiling_dashboard.html")
    output_path.write_text(html_content)
    print_result("Dashboard", f"Saved to {output_path.absolute()}")

    # Print stage breakdown
    print("\n  Stage Breakdown:")
    for stage_name, stage_data in workflow_data["stages"].items():
        print(f"    • {stage_name}: {stage_data['duration']:.3f}s")


def demo_3_circuit_optimization():
    """Demo 3: Circuit Optimization Pipeline."""
    if not ADVANCED_FEATURES:
        print_section("Demo 3: Circuit Optimization (SKIPPED)")
        return

    print_section("Demo 3: Circuit Library + Optimization")

    try:
        from qiskit import QuantumCircuit

        # Create an inefficient circuit
        print("Creating inefficient circuit with redundant gates...")
        qc = QuantumCircuit(4, 4)

        # Add some redundant operations
        qc.h(0)
        qc.h(0)  # Cancel out
        qc.x(1)
        qc.x(1)  # Cancel out
        qc.cx(0, 1)
        qc.cx(0, 2)
        qc.h(3)
        qc.measure([0, 1, 2, 3], [0, 1, 2, 3])

        original_depth = qc.depth()
        original_size = qc.size()

        print_result("Original Circuit Depth", original_depth)
        print_result("Original Gate Count", original_size)

        # Optimize circuit
        print("\nOptimizing circuit...")
        optimizer = CircuitOptimizer(optimization_level=OptimizationLevel.O2)
        result = optimizer.optimize_with_analysis(qc)

        optimized_circuit = result["optimized_circuit"]
        metrics = result["metrics"]

        print_result("Optimized Circuit Depth", optimized_circuit.depth())
        print_result("Optimized Gate Count", optimized_circuit.size())
        print_result("Gates Removed", metrics.gates_removed)
        print_result("Depth Reduction", f"{metrics.depth_reduction_percent:.1f}%")

    except ImportError:
        print("  ⚠️  Qiskit not available for circuit optimization demo")


def demo_4_smart_batching():
    """Demo 4: Smart Batching for Cost Optimization."""
    if not ADVANCED_FEATURES:
        print_section("Demo 4: Smart Batching (SKIPPED)")
        return

    print_section("Demo 4: Smart Batching for Multiple Circuits")

    # Create smart batcher
    batcher = SmartBatcher(strategy=BatchingStrategy.ADAPTIVE)

    # Create multiple quantum jobs
    print("Creating 10 quantum jobs...")
    jobs = []

    job_queries = [
        "Create Bell state",
        "Create EPR pair",
        "Create GHZ state with 3 qubits",
        "Apply Grover search",
        "Create superposition",
        "Entangle 2 qubits",
        "Apply VQE",
        "Create Bell pair",
        "Run quantum Fourier transform",
        "Create maximally entangled state",
    ]

    for i, query in enumerate(job_queries):
        job = QuantumJob(job_id=f"job_{i}", shots=100, backend="simulator", program_text=query)
        jobs.append(job)

    print_result("Total Jobs", len(jobs))

    # Create batches
    print("\nCreating optimized batches...")
    batches = batcher.create_batches(jobs)

    print_result("Batches Created", len(batches))

    # Calculate savings
    individual_cost = sum(batcher._estimate_job_cost(job) for job in jobs)
    batched_cost = sum(batch.estimated_cost for batch in batches)
    savings = individual_cost - batched_cost
    savings_percent = (savings / individual_cost) * 100 if individual_cost > 0 else 0

    print_result("Individual Cost", f"${individual_cost:.4f}")
    print_result("Batched Cost", f"${batched_cost:.4f}")
    print_result("Savings", f"${savings:.4f} ({savings_percent:.1f}%)")

    # Print batch details
    print("\n  Batch Details:")
    for i, batch in enumerate(batches):
        print(
            f"    Batch {i+1}: {len(batch.jobs)} jobs, "
            f"${batch.estimated_cost:.4f}, "
            f"{batch.estimated_time:.2f}s"
        )


def demo_5_circuit_catalog():
    """Demo 5: Circuit Library/Catalog."""
    if not ADVANCED_FEATURES:
        print_section("Demo 5: Circuit Catalog (SKIPPED)")
        return

    print_section("Demo 5: Circuit Library and Catalog")

    catalog = CircuitCatalog()

    # Search by keywords
    print("Searching for 'bell' circuits...")
    bell_templates = catalog.search_by_keywords(["bell", "entangle"])

    print_result("Templates Found", len(bell_templates))

    if bell_templates:
        print("\n  Sample Templates:")
        for template in bell_templates[:3]:
            print(f"    • {template.name}")
            print(f"      - Qubits: {template.qubits}")
            print(f"      - Description: {template.description[:60]}...")

    # Search by category
    print("\n\nSearching for drug discovery circuits...")
    drug_templates = catalog.search_by_keywords(["drug", "docking", "binding"])

    print_result("Drug Discovery Templates", len(drug_templates))


def demo_6_semantic_parsing():
    """Demo 6: Advanced Semantic Parsing."""
    if not ADVANCED_FEATURES:
        print_section("Demo 6: Semantic Parsing (SKIPPED)")
        return

    print_section("Demo 6: Semantic Parsing and NL Mapping")

    # Create parser and mapper
    parser = SemanticParser()
    mapper = EnhancedNLMapper()

    queries = [
        "Create a Bell state and measure it",
        "Dock ligand to protein receptor",
        "Predict toxicity of compound",
    ]

    for query in queries:
        print(f"Query: '{query}'")

        # Parse semantically
        semantic_graph = parser.parse(query)
        print_result("Entities Found", len(semantic_graph.entities))
        print_result("Relations Found", len(semantic_graph.relations))

        # Map to gates
        mapping = mapper.map_to_gates(query)
        print_result("Gates Mapped", len(mapping.gates))
        print_result("Confidence", f"{mapping.confidence:.2f}")
        print()


def demo_7_caching():
    """Demo 7: Circuit Caching."""
    if not ADVANCED_FEATURES:
        print_section("Demo 7: Circuit Caching (SKIPPED)")
        return

    print_section("Demo 7: Circuit Caching for Performance")

    cache = CircuitCache(max_size=100, ttl_seconds=3600)

    query = "Create a 5-qubit superposition state"

    # First execution - cache miss
    print("First execution (cache miss)...")
    start = time.time()
    result1 = quantum(query, shots=100)
    time1 = time.time() - start

    print_result("Execution Time", f"{time1:.3f}s")
    print_result("Cache Stats", cache.get_stats())

    # Second execution - should be faster if caching works
    print("\nSecond execution (potential cache hit)...")
    start = time.time()
    result2 = quantum(query, shots=100)
    time2 = time.time() - start

    print_result("Execution Time", f"{time2:.3f}s")
    print_result("Speedup", f"{(time1/time2):.2f}x" if time2 > 0 else "N/A")


def demo_8_drug_discovery_workflow():
    """Demo 8: Complete Drug Discovery Workflow."""
    print_section("Demo 8: Drug Discovery Workflow")

    if ADVANCED_FEATURES:
        profiler = Profiler(mode=ProfilingMode.DETAILED)

        with profiler.profile("drug_discovery_pipeline"):
            # Virtual screening
            with profiler.stage("virtual_screening"):
                print("Running virtual screening...")
                result = quantum("Screen compound library against target", shots=200)
                print_result("Screening", "Complete")

            # Binding affinity
            with profiler.stage("binding_affinity"):
                print("\nCalculating binding affinity...")
                result = quantum("Calculate binding affinity", shots=150)
                print_result("Binding Affinity", "Calculated")

            # ADME prediction
            with profiler.stage("adme"):
                print("\nPredicting ADME properties...")
                result = quantum("Predict bioavailability and absorption", shots=150)
                print_result("ADME", "Predicted")

            # Toxicity prediction
            with profiler.stage("toxicity"):
                print("\nPredicting toxicity...")
                result = quantum("Predict hepatotoxicity", shots=150)
                print_result("Toxicity", "Assessed")

        summary = profiler.get_summary()
        workflow = summary["drug_discovery_pipeline"]

        print(f"\n  Total Pipeline Time: {workflow['total_time']:.3f}s")
        print(f"  Total Cost: ${workflow['costs']['total_cost']:.4f}")

    else:
        # Basic demo without profiling
        print("Running drug discovery stages...")
        result1 = quantum("Screen compound library", shots=100)
        print_result("Virtual Screening", "Complete")

        result2 = quantum("Calculate binding affinity", shots=100)
        print_result("Binding Affinity", "Calculated")

        result3 = quantum("Predict ADME properties", shots=100)
        print_result("ADME", "Predicted")


def demo_9_full_stack_integration():
    """Demo 9: Full Stack Integration."""
    if not ADVANCED_FEATURES:
        print_section("Demo 9: Full Stack Integration (SKIPPED)")
        return

    print_section("Demo 9: Full Stack Integration (NL → Dashboard)")

    # Initialize all components
    parser = SemanticParser()
    mapper = EnhancedNLMapper()
    catalog = CircuitCatalog()
    optimizer = CircuitOptimizer(optimization_level=OptimizationLevel.O2)
    profiler = Profiler(mode=ProfilingMode.DETAILED)

    query = "Create a Bell state for quantum communication"

    with profiler.profile("full_stack"):
        # 1. Semantic parsing
        with profiler.stage("semantic_parse"):
            semantic_graph = parser.parse(query)
            profiler.record_metadata(
                {
                    "entities": len(semantic_graph.entities),
                    "relations": len(semantic_graph.relations),
                }
            )

        # 2. Circuit library lookup
        with profiler.stage("library_lookup"):
            templates = catalog.search_by_keywords(["bell", "communication"])
            profiler.record_metadata({"templates_found": len(templates)})

        # 3. NL mapping
        with profiler.stage("nl_mapping"):
            mapping = mapper.map_to_gates(query)
            profiler.record_metadata(
                {"gates_mapped": len(mapping.gates), "confidence": mapping.confidence}
            )

        # 4. Circuit execution
        with profiler.stage("execution"):
            result = quantum(query, shots=200)
            profiler.record_circuit_metrics(num_qubits=2, gate_count=5, circuit_depth=3)

        # 5. Dashboard generation
        with profiler.stage("dashboard"):
            dashboard = ProfilingDashboard()
            html = dashboard.generate_html(profiler.get_summary()["full_stack"])
            Path("full_stack_dashboard.html").write_text(html)

    summary = profiler.get_summary()["full_stack"]

    print_result("Query", query)
    print_result("Stages Completed", len(summary["stages"]))
    print_result("Total Time", f"{summary['total_time']:.3f}s")
    print_result("Success", result.success)
    print_result("Dashboard", "Saved to full_stack_dashboard.html")


def demo_10_backward_compatibility():
    """Demo 10: Backward Compatibility."""
    print_section("Demo 10: Backward Compatibility")

    print("Testing legacy quantum() calls...")

    # Old-style basic call
    result1 = quantum("Create Bell state", shots=100)
    print_result("Basic Call", "Works ✓" if result1.success else "Failed ✗")

    # With backend specification
    result2 = quantum("Apply Hadamard", shots=50, backend="simulator")
    print_result("With Backend", "Works ✓" if result2.success else "Failed ✗")

    # Multiple operations
    result3 = quantum("Create GHZ state with 3 qubits", shots=100)
    print_result("Complex Query", "Works ✓" if result3.success else "Failed ✗")

    # Check result object attributes
    has_counts = hasattr(result1, "counts")
    has_success = hasattr(result1, "success")
    has_circuit = hasattr(result1, "circuit")

    print_result(
        "Result Attributes",
        "All present ✓" if all([has_counts, has_success, has_circuit]) else "Missing some ✗",
    )


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  BioQL Complete Integration Demo")
    print("  Showcasing all advanced features and workflows")
    print("=" * 80)

    demos = [
        ("Natural Language Programming", demo_1_basic_natural_language),
        ("Profiling Workflow", demo_2_profiling_workflow),
        ("Circuit Optimization", demo_3_circuit_optimization),
        ("Smart Batching", demo_4_smart_batching),
        ("Circuit Catalog", demo_5_circuit_catalog),
        ("Semantic Parsing", demo_6_semantic_parsing),
        ("Circuit Caching", demo_7_caching),
        ("Drug Discovery", demo_8_drug_discovery_workflow),
        ("Full Stack Integration", demo_9_full_stack_integration),
        ("Backward Compatibility", demo_10_backward_compatibility),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\n  ⚠️  Demo {i} ({name}) encountered an error: {e}")
            import traceback

            traceback.print_exc()

    print_section("Demo Complete!")
    print("All demos finished. Check generated HTML files for dashboards.")
    print()


if __name__ == "__main__":
    main()
