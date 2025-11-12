#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quillow Command Line Interface
==============================

Terminal interface for Quillow QEC system and BioQL integration.

Commands:
---------
quillow simulate        - Run surface code simulation
quillow benchmark       - Run benchmarks
quillow protect-bioql   - Protect BioQL query with QEC
quillow optimize        - Optimize circuit with QEC
quillow deploy-gpu      - Deploy GPU decoder to Modal

Examples:
---------
$ quillow simulate --distance 5 --shots 10000 --decoder pymatching
$ quillow benchmark threshold --distances 3,5,7
$ quillow protect-bioql --query "dock aspirin to COX-2" --backend ibm_torino
$ quillow optimize --bioql-circuit vqe_h2.qasm --qec-distance 5
"""

import json
import sys
from pathlib import Path

import click
import numpy as np
from loguru import logger

# Configure logger for CLI
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Quillow: Willow-Style Quantum Error Correction System

    Advanced fault-tolerant quantum computing with surface codes,
    MWPM decoding, and BioQL integration.
    """
    pass


@cli.command()
@click.option("--distance", "-d", type=int, default=5, help="Surface code distance")
@click.option("--shots", "-s", type=int, default=10000, help="Number of shots")
@click.option("--error-rate", "-p", type=float, default=0.001, help="Physical error rate")
@click.option("--decoder", type=str, default="pymatching", help="Decoder type")
@click.option("--backend", type=str, default="stim", help="Simulation backend")
@click.option("--rounds", "-r", type=int, default=None, help="QEC rounds (default: distance)")
@click.option("--output", "-o", type=str, default=None, help="Output file (JSON)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def simulate(distance, shots, error_rate, decoder, backend, rounds, output, verbose):
    """
    Run surface code simulation.

    Example:
        quillow simulate -d 5 -s 10000 -p 0.001 --decoder pymatching
    """
    from quillow.core import SurfaceCodeSimulator

    logger.info(f"Starting simulation: d={distance}, shots={shots}, p={error_rate}")

    # Create simulator
    sim = SurfaceCodeSimulator(
        distance=distance, physical_error_rate=error_rate, rounds=rounds or distance
    )

    # Run simulation
    result = sim.run(shots=shots, decoder=decoder, backend=backend)

    # Display results
    click.echo("\n" + "=" * 60)
    click.echo("QUILLOW SIMULATION RESULTS")
    click.echo("=" * 60)
    click.echo(f"Distance: {result.distance}")
    click.echo(f"Rounds: {result.rounds}")
    click.echo(f"Shots: {result.shots}")
    click.echo(f"Physical error rate: {result.physical_error_rate:.6f}")
    click.echo(f"Logical error rate: {result.logical_error_rate:.6f}")
    click.echo(f"Suppression factor: {result.suppression_factor:.2f}x")
    click.echo(f"Below threshold: {'✅ YES' if result.is_below_threshold else '❌ NO'}")
    click.echo(f"Runtime: {result.runtime_seconds:.3f}s")
    click.echo(f"Avg latency: {result.avg_latency_us:.2f}μs/shot")
    click.echo("=" * 60 + "\n")

    # Save to file if requested
    if output:
        result_dict = result.to_dict()
        with open(output, "w") as f:
            json.dump(result_dict, f, indent=2)
        click.echo(f"Results saved to: {output}")

    # Exit with appropriate code
    sys.exit(0 if result.is_below_threshold else 1)


@cli.group()
def benchmark():
    """Run various benchmarks."""
    pass


@benchmark.command()
@click.option("--distances", type=str, default="3,5,7", help="Comma-separated distances")
@click.option("--error-rates", type=str, default="0.0005,0.001,0.002,0.005", help="Error rates")
@click.option("--shots", type=int, default=50000, help="Shots per point")
@click.option("--decoder", type=str, default="pymatching", help="Decoder")
@click.option("--output", "-o", type=str, default="threshold_analysis.json", help="Output file")
def threshold(distances, error_rates, shots, decoder, output):
    """
    Analyze QEC threshold.

    Example:
        quillow benchmark threshold --distances 3,5,7 --error-rates 0.001,0.002,0.005
    """
    from quillow.core import SurfaceCodeSimulator

    distances_list = [int(d) for d in distances.split(",")]
    error_rates_list = [float(p) for p in error_rates.split(",")]

    logger.info(f"Threshold analysis: distances={distances_list}, error_rates={error_rates_list}")

    results = []

    for d in distances_list:
        for p in error_rates_list:
            logger.info(f"Testing d={d}, p={p:.6f}...")

            sim = SurfaceCodeSimulator(distance=d, physical_error_rate=p)
            result = sim.run(shots=shots, decoder=decoder)

            results.append(
                {
                    "distance": d,
                    "physical_error_rate": p,
                    "logical_error_rate": result.logical_error_rate,
                    "suppression_factor": result.suppression_factor,
                    "below_threshold": result.is_below_threshold,
                }
            )

            click.echo(
                f"  d={d}, p={p:.6f}: P_L={result.logical_error_rate:.6f} "
                f"({'✅' if result.is_below_threshold else '❌'})"
            )

    # Save results
    with open(output, "w") as f:
        json.dump(results, f, indent=2)

    click.echo(f"\n✅ Threshold analysis complete. Results saved to: {output}")


@benchmark.command()
@click.option("--decoders", type=str, default="pymatching,unionfind", help="Decoders to compare")
@click.option("--distance", type=int, default=5, help="Code distance")
@click.option("--shots", type=int, default=10000, help="Number of shots")
@click.option("--output", "-o", type=str, default="decoder_comparison.json", help="Output file")
def decoders(decoders, distance, shots, output):
    """
    Compare decoder performance.

    Example:
        quillow benchmark decoders --decoders pymatching,unionfind,gpu
    """
    from quillow.core import RotatedSurfaceCode
    from quillow.decoders import benchmark_decoder, get_decoder

    decoder_list = decoders.split(",")

    logger.info(f"Comparing decoders: {decoder_list}")

    # Build test circuit
    surface_code = RotatedSurfaceCode(distance=distance, rounds=distance)
    circuit = surface_code.build_stim_circuit()

    results = []

    for decoder_name in decoder_list:
        try:
            logger.info(f"Benchmarking {decoder_name}...")

            decoder = get_decoder(decoder_name)
            result = benchmark_decoder(decoder, circuit, num_shots=shots)

            results.append(result)

            click.echo(f"\n{decoder_name}:")
            click.echo(f"  Throughput: {result['throughput']:.1f} shots/sec")
            click.echo(f"  Avg latency: {result['avg_latency_us']:.2f}μs")
            click.echo(f"  Logical error rate: {result['logical_error_rate']:.6f}")

        except Exception as e:
            logger.error(f"Error benchmarking {decoder_name}: {e}")

    # Save results
    with open(output, "w") as f:
        json.dump(results, f, indent=2)

    click.echo(f"\n✅ Decoder comparison complete. Results saved to: {output}")


@cli.command()
@click.option("--query", type=str, required=True, help="BioQL query")
@click.option("--backend", type=str, default="simulator", help="Quantum backend")
@click.option("--shots", type=int, default=2048, help="Number of shots")
@click.option("--qec-distance", type=int, default=5, help="QEC code distance")
@click.option("--api-key", type=str, default=None, help="BioQL API key (or set BIOQL_API_KEY)")
@click.option("--output", "-o", type=str, default=None, help="Output file (JSON)")
@click.option("--no-qec", is_flag=True, help="Disable QEC protection")
def protect_bioql(query, backend, shots, qec_distance, api_key, output, no_qec):
    """
    Protect BioQL query with QEC.

    Example:
        quillow protect-bioql --query "dock aspirin to COX-2" --backend ibm_torino
    """
    from quillow.backends import BioQLOptimizer

    logger.info(f"Protecting BioQL query: {query}")
    logger.info(f"Backend: {backend}, Shots: {shots}, QEC: d={qec_distance}")

    # Create optimizer
    optimizer = BioQLOptimizer(api_key=api_key, qec_distance=qec_distance, auto_optimize=not no_qec)

    # Execute with QEC
    try:
        result = optimizer.execute_with_qec(bioql_query=query, backend=backend, shots=shots)

        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("BIOQL QEC-PROTECTED EXECUTION")
        click.echo("=" * 60)
        click.echo(f"Query: {query}")
        click.echo(f"Backend: {backend}")
        click.echo(f"Shots: {shots}")
        click.echo(f"QEC Distance: {qec_distance}")
        click.echo("-" * 60)

        if result.get("energy"):
            click.echo(f"Energy: {result['energy']:.6f}")
        if result.get("raw_energy"):
            click.echo(f"Raw Energy (no QEC): {result['raw_energy']:.6f}")
        if result.get("logical_error_rate"):
            click.echo(f"Logical Error Rate: {result['logical_error_rate']:.6f}")

        click.echo("=" * 60 + "\n")

        # Save to file
        if output:
            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            click.echo(f"Results saved to: {output}")

        logger.success("BioQL query executed successfully")

    except Exception as e:
        logger.error(f"Error executing BioQL query: {e}")
        sys.exit(1)


@cli.command()
@click.option("--bioql-circuit", type=str, required=True, help="BioQL circuit file (QASM/Stim)")
@click.option("--qec-distance", type=int, default=5, help="QEC distance")
@click.option("--backend", type=str, default="simulator", help="Quantum backend")
@click.option("--shots", type=int, default=2048, help="Number of shots")
@click.option("--output", "-o", type=str, default=None, help="Output file")
def optimize(bioql_circuit, qec_distance, backend, shots, output):
    """
    Optimize BioQL circuit with QEC.

    Example:
        quillow optimize --bioql-circuit vqe_h2.qasm --qec-distance 5
    """
    from quillow.backends import BioQLOptimizer

    # Read circuit file
    circuit_path = Path(bioql_circuit)
    if not circuit_path.exists():
        click.echo(f"Error: Circuit file not found: {bioql_circuit}")
        sys.exit(1)

    circuit_content = circuit_path.read_text()

    logger.info(f"Optimizing circuit: {bioql_circuit}")

    optimizer = BioQLOptimizer(qec_distance=qec_distance)

    try:
        # Execute
        result = optimizer.execute_with_qec(
            bioql_query=circuit_content, backend=backend, shots=shots
        )

        click.echo("\n✅ Optimization complete")
        click.echo(f"Energy: {result.get('energy', 'N/A')}")
        click.echo(f"Logical error rate: {result.get('logical_error_rate', 'N/A')}")

        if output:
            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            click.echo(f"Results saved to: {output}")

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        sys.exit(1)


@cli.command()
def deploy_gpu():
    """
    Deploy GPU decoder to Modal cloud.

    Example:
        quillow deploy-gpu
    """
    import subprocess

    click.echo("Deploying Quillow GPU decoder to Modal...")

    try:
        # Deploy Modal app
        result = subprocess.run(
            ["modal", "deploy", "decoders/gpu_decoder_modal.py"],
            cwd="/Users/heinzjungbluth/Desktop/Quillow",
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            click.echo("\n✅ GPU decoder deployed successfully!")
            click.echo("\nYou can now use GPU decoding:")
            click.echo("  from quillow.decoders import ModalGPUDecoder")
            click.echo("  decoder = ModalGPUDecoder()")
        else:
            click.echo(f"\n❌ Deployment failed:")
            click.echo(result.stderr)
            sys.exit(1)

    except FileNotFoundError:
        click.echo("❌ Error: Modal CLI not found. Install with: pip install modal")
        sys.exit(1)


@cli.command()
def check_bioql():
    """
    Check BioQL API connection.

    Example:
        quillow check-bioql
    """
    from quillow.backends import BioQLBackend, BioQLConfig

    click.echo("Checking BioQL API connection...")

    config = BioQLConfig.from_env()

    if not config.api_key:
        click.echo("❌ No API key found. Set BIOQL_API_KEY environment variable.")
        sys.exit(1)

    backend = BioQLBackend(config)

    # Validate API key
    if backend.validate_api_key():
        click.echo("✅ API key valid")

        # Check quota
        quota = backend.check_quota()
        if "error" not in quota:
            click.echo(f"\nQuota information:")
            click.echo(f"  User ID: {quota.get('user_id')}")
            click.echo(f"  Tier: {quota.get('tier')}")
            click.echo(f"  Balance: ${quota.get('balance', 0):.2f}")
            click.echo(f"  Monthly usage: {quota.get('monthly_usage', 0)} shots")
        else:
            click.echo(f"⚠️  Could not fetch quota: {quota['error']}")
    else:
        click.echo("❌ API key validation failed")
        sys.exit(1)


@cli.command()
def info():
    """Display system information."""
    import quillow

    click.echo("\n" + "=" * 60)
    click.echo("QUILLOW SYSTEM INFORMATION")
    click.echo("=" * 60)
    click.echo(f"Version: 1.0.0")
    click.echo(f"Installation: /Users/heinzjungbluth/Desktop/Quillow")
    click.echo("\nComponents:")
    click.echo("  ✅ Surface codes (d=3,5,7,9,...)")
    click.echo("  ✅ MWPM decoder (PyMatching)")
    click.echo("  ✅ Union-Find decoder")
    click.echo("  ✅ GPU decoder (Modal)")
    click.echo("  ✅ BioQL integration")
    click.echo("  ✅ Stim backend")
    click.echo("\nBioQL API: https://api.bioql.bio")
    click.echo("Documentation: /Users/heinzjungbluth/Desktop/Quillow/docs/")
    click.echo("=" * 60 + "\n")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()


__all__ = ["cli", "main"]
