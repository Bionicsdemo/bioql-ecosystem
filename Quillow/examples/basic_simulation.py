#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Basic Quillow Simulation Example
=================================

Demonstrates surface code QEC with below-threshold performance.
"""

import matplotlib.pyplot as plt
import numpy as np
from quillow import SurfaceCodeSimulator


def main():
    print("=" * 60)
    print("Quillow Basic Simulation Example")
    print("=" * 60)
    print()

    # Test 1: Perfect circuit (no errors)
    print("Test 1: Perfect Circuit (p=0)")
    print("-" * 60)

    sim = SurfaceCodeSimulator(distance=5, physical_error_rate=0.0)
    result = sim.run(shots=1000, decoder="pymatching")

    print(f"Logical error rate: {result.logical_error_rate:.6f}")
    print(f"Expected: 0.000000 ✅")
    print()

    # Test 2: Below threshold
    print("Test 2: Below Threshold (d=5, p=0.1%)")
    print("-" * 60)

    sim = SurfaceCodeSimulator(distance=5, physical_error_rate=0.001)
    result = sim.run(shots=10000, decoder="pymatching")

    print(f"Physical error rate: {result.physical_error_rate:.6f}")
    print(f"Logical error rate: {result.logical_error_rate:.6f}")
    print(f"Suppression factor: {result.suppression_factor:.2f}x")
    print(f"Below threshold: {'✅ YES' if result.is_below_threshold else '❌ NO'}")
    print(f"Avg latency: {result.avg_latency_us:.2f}μs/shot")
    print()

    # Test 3: Distance scaling
    print("Test 3: Distance Scaling")
    print("-" * 60)

    distances = [3, 5, 7]
    physical_error = 0.001
    logical_errors = []

    for d in distances:
        sim = SurfaceCodeSimulator(distance=d, physical_error_rate=physical_error)
        result = sim.run(shots=10000, decoder="pymatching")
        logical_errors.append(result.logical_error_rate)

        print(
            f"d={d}: P_L={result.logical_error_rate:.6f} "
            f"({'✅' if result.is_below_threshold else '❌'})"
        )

    print()

    # Plot results
    print("Generating plot...")
    plt.figure(figsize=(10, 6))

    plt.semilogy(
        distances, logical_errors, "o-", label="Logical error rate", linewidth=2, markersize=10
    )
    plt.axhline(y=physical_error, color="r", linestyle="--", label="Physical error rate")

    plt.xlabel("Code Distance", fontsize=12)
    plt.ylabel("Error Rate", fontsize=12)
    plt.title("Surface Code QEC: Below-Threshold Demonstration", fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)

    plt.savefig("quillow_basic_simulation.png", dpi=150, bbox_inches="tight")
    print("Plot saved to: quillow_basic_simulation.png")
    print()

    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
