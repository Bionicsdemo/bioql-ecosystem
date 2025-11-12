#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Circuit Cache Usage Examples

This script demonstrates how to use the CircuitCache for efficient
circuit compilation and caching in BioQL.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from bioql.cache import CacheKey, CircuitCache, get_global_cache, integrate_with_quantum_connector
from bioql.ir.schema import BioQLProgram, DataType, DockingOperation, Molecule


def example_1_basic_usage():
    """Example 1: Basic cache usage."""
    print("=" * 60)
    print("Example 1: Basic Cache Usage")
    print("=" * 60)

    # Create a cache
    cache = CircuitCache(max_size=100, ttl_hours=24)

    # Create a cache key from IR
    ir_program = "LOAD protein.pdb\nDOCK ligand.sdf"
    key = CacheKey.from_ir(ir_program, backend_target="qiskit", optimization_level=1)

    # Store a circuit
    mock_circuit = "compiled_quantum_circuit"
    cache.put(
        key,
        mock_circuit,
        metadata={"backend": "qiskit", "optimization_level": 1, "compile_time_ms": 125},
    )

    # Retrieve the circuit
    cached = cache.get(key)
    if cached:
        print(f"✓ Retrieved cached circuit")
        print(f"  Circuit: {cached.circuit}")
        print(f"  Access count: {cached.access_count}")
        print(f"  Age: {cached.age_seconds():.2f}s")
        print(f"  Metadata: {cached.metadata}")
    else:
        print("✗ Cache miss")

    print(f"\nCache stats: {cache.get_stats()}")
    print()


def example_2_lru_eviction():
    """Example 2: LRU eviction behavior."""
    print("=" * 60)
    print("Example 2: LRU Eviction")
    print("=" * 60)

    # Create small cache to demonstrate eviction
    cache = CircuitCache(max_size=5, ttl_hours=24)

    print("Adding 10 circuits to cache with max_size=5...")

    # Add more circuits than max_size
    for i in range(10):
        key = CacheKey(
            program_fingerprint=f"program_{i}",
            backend_target="qiskit",
            optimization_level=1,
            parameters_hash="default",
        )
        cache.put(key, f"circuit_{i}", {"index": i})

    print(f"Cache size after adding 10: {len(cache)} (max: 5)")
    print(f"Evictions: {cache.get_stats()['evictions']}")

    # First entries should be evicted
    old_key = CacheKey("program_0", "qiskit", 1, "default")
    print(f"\nTrying to retrieve old entry 'program_0': ", end="")
    if cache.get(old_key):
        print("Found (unexpected!)")
    else:
        print("Not found (evicted as expected)")

    # Recent entries should still be there
    new_key = CacheKey("program_9", "qiskit", 1, "default")
    print(f"Trying to retrieve recent entry 'program_9': ", end="")
    if cache.get(new_key):
        print("Found (as expected)")
    else:
        print("Not found (unexpected!)")

    print()


def example_3_pattern_invalidation():
    """Example 3: Pattern-based cache invalidation."""
    print("=" * 60)
    print("Example 3: Pattern-Based Invalidation")
    print("=" * 60)

    cache = CircuitCache(max_size=50, ttl_hours=24)

    # Add circuits for different backends
    backends = ["qiskit", "cirq", "pennylane"]
    for backend in backends:
        for i in range(5):
            key = CacheKey(
                program_fingerprint=f"program_{backend}_{i}",
                backend_target=backend,
                optimization_level=1,
                parameters_hash="default",
            )
            cache.put(key, f"circuit_{backend}_{i}", {"backend": backend})

    print(f"Initial cache size: {len(cache)}")

    # Invalidate all qiskit entries
    print("\nInvalidating all 'qiskit' backend entries...")
    invalidated = cache.invalidate_backend("qiskit")
    print(f"Invalidated {invalidated} entries")
    print(f"Remaining cache size: {len(cache)}")

    # Custom pattern invalidation
    print("\nInvalidating entries with optimization_level=1 for cirq...")
    pattern = r".*:cirq:1:.*"
    invalidated = cache.invalidate(pattern)
    print(f"Invalidated {invalidated} entries")
    print(f"Final cache size: {len(cache)}")

    print()


def example_4_cache_warming():
    """Example 4: Pre-warming the cache."""
    print("=" * 60)
    print("Example 4: Cache Warming")
    print("=" * 60)

    cache = CircuitCache(max_size=100, ttl_hours=24)

    # Prepare circuits to warm the cache
    common_circuits = [
        ("LOAD protein1.pdb\nDOCK ligand1.sdf", "circuit_1", {"common": True}),
        ("LOAD protein2.pdb\nDOCK ligand2.sdf", "circuit_2", {"common": True}),
        ("LOAD protein3.pdb\nDOCK ligand3.sdf", "circuit_3", {"common": True}),
    ]

    print("Warming cache with common circuits...")
    count = cache.warm_cache(common_circuits, backend_target="qiskit", optimization_level=1)
    print(f"Warmed cache with {count} circuits")

    print(f"\nCache info:")
    info = cache.get_cache_info()
    print(f"  Size: {info['size']}")
    print(f"  Hit rate: {info['stats']['hit_rate']:.2%}")

    # Verify circuits are cached
    print("\nVerifying cached circuits:")
    for ir_program, _, _ in common_circuits:
        key = CacheKey.from_ir(ir_program, "qiskit", 1)
        cached = cache.get(key)
        print(f"  {ir_program[:30]+'...': <35} {'✓ Found' if cached else '✗ Not found'}")

    print()


def example_5_cache_optimization():
    """Example 5: Cache optimization and analysis."""
    print("=" * 60)
    print("Example 5: Cache Optimization")
    print("=" * 60)

    cache = CircuitCache(max_size=20, ttl_hours=24)

    # Simulate various access patterns
    print("Simulating circuit compilation and access patterns...")

    # Add frequently accessed circuit
    hot_key = CacheKey("hot_program", "qiskit", 1, "params")
    cache.put(hot_key, "hot_circuit", {"type": "frequently_used"})

    # Access it many times
    for _ in range(50):
        cache.get(hot_key)

    # Add some circuits with single access
    for i in range(15):
        key = CacheKey(f"cold_{i}", "qiskit", 1, "params")
        cache.put(key, f"cold_circuit_{i}", {"type": "rarely_used"})
        cache.get(key)  # Access once

    # Run optimization
    print("\nRunning cache optimization...")
    report = cache.optimize_cache()

    print(f"\nOptimization Report:")
    print(f"  Initial size: {report['initial_size']}")
    print(f"  Final size: {report['final_size']}")
    print(f"  Expired removed: {report['expired_removed']}")
    print(f"  Cold entries: {report['cold_entries']}")
    print(f"  Avg access count: {report['avg_access_count']:.2f}")
    print(f"  Hit rate: {report['hit_rate']:.2%}")

    if report["recommendations"]:
        print("\n  Recommendations:")
        for rec in report["recommendations"]:
            print(f"    - {rec}")

    print()


def example_6_global_cache():
    """Example 6: Using global cache instance."""
    print("=" * 60)
    print("Example 6: Global Cache Instance")
    print("=" * 60)

    # Get global cache (singleton pattern)
    cache1 = get_global_cache(max_size=100, ttl_hours=24)
    cache2 = get_global_cache()  # Same instance

    print(f"cache1 is cache2: {cache1 is cache2}")

    # Use global cache
    key = CacheKey.from_ir("global_program", "qiskit", 1)
    cache1.put(key, "global_circuit", {})

    # Access from "different" cache instance
    cached = cache2.get(key)
    print(f"Cached circuit retrieved from cache2: {cached is not None}")

    print(f"\nGlobal cache stats: {cache1.get_stats()}")
    print()


def example_7_with_bioql_program():
    """Example 7: Using with BioQL IR Program."""
    print("=" * 60)
    print("Example 7: Integration with BioQL IR")
    print("=" * 60)

    cache = CircuitCache(max_size=100, ttl_hours=24)

    # Create a BioQL program
    program = BioQLProgram(
        name="Drug Discovery Docking",
        description="Dock ligand to protein target",
        inputs=[
            Molecule(id="protein_1", type=DataType.PROTEIN, format="pdb", data="protein.pdb"),
            Molecule(id="ligand_1", type=DataType.LIGAND, format="sdf", data="ligand.sdf"),
        ],
        operations=[
            DockingOperation(
                receptor=Molecule(
                    id="protein_1", type=DataType.PROTEIN, format="pdb", data="protein.pdb"
                ),
                ligand=Molecule(
                    id="ligand_1", type=DataType.LIGAND, format="sdf", data="ligand.sdf"
                ),
                num_poses=10,
            )
        ],
    )

    # Create cache key from BioQL program
    key = CacheKey.from_ir(
        program, backend_target="qiskit", optimization_level=2  # Pass BioQLProgram object directly
    )

    print(f"Created cache key from BioQL program:")
    print(f"  Program fingerprint: {key.program_fingerprint[:16]}...")
    print(f"  Backend: {key.backend_target}")
    print(f"  Optimization level: {key.optimization_level}")

    # Cache the compiled circuit
    cache.put(
        key,
        "compiled_docking_circuit",
        {
            "program_name": program.name,
            "num_operations": len(program.operations),
            "compile_time_ms": 234,
        },
    )

    # Retrieve from cache
    cached = cache.get(key)
    if cached:
        print(f"\n✓ Successfully cached and retrieved BioQL program circuit")
        print(f"  Metadata: {cached.metadata}")

    print()


def example_8_performance_metrics():
    """Example 8: Performance metrics and monitoring."""
    print("=" * 60)
    print("Example 8: Performance Metrics")
    print("=" * 60)

    cache = CircuitCache(max_size=50, ttl_hours=24, enable_stats=True)

    # Simulate workload
    print("Simulating workload with hits and misses...")

    programs = [f"program_{i}" for i in range(20)]
    keys = []

    # Populate cache
    for prog in programs[:10]:
        key = CacheKey(prog, "qiskit", 1, "params")
        keys.append(key)
        cache.put(key, f"circuit_{prog}", {})

    # Simulate hits and misses
    import random

    for _ in range(100):
        if random.random() < 0.7:  # 70% hit rate
            key = random.choice(keys[:10])
            cache.get(key)
        else:
            key = CacheKey(random.choice(programs[10:]), "qiskit", 1, "params")
            cache.get(key)

    # Display performance metrics
    stats = cache.get_stats()
    print(f"\nPerformance Metrics:")
    print(f"  Total requests: {stats['hits'] + stats['misses']}")
    print(f"  Cache hits: {stats['hits']}")
    print(f"  Cache misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.2%}")
    print(f"  Miss rate: {stats['miss_rate']:.2%}")
    print(f"  Evictions: {stats['evictions']}")
    print(f"  Cache utilization: {stats['utilization']:.1%}")

    # Detailed cache info
    print(f"\nCache state: {cache}")

    print()


def main():
    """Run all examples."""
    print("\n")
    print("=" * 60)
    print("BioQL Circuit Cache Examples")
    print("=" * 60)
    print()

    example_1_basic_usage()
    example_2_lru_eviction()
    example_3_pattern_invalidation()
    example_4_cache_warming()
    example_5_cache_optimization()
    example_6_global_cache()
    example_7_with_bioql_program()
    example_8_performance_metrics()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
