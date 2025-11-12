"""
Command-line interface for CRISPR-QAI

Provides `bioql-crispr` command with subcommands:
- score-energy: Calculate energy for single guide
- rank-guides: Rank multiple guides from file
- infer-phenotype: Predict off-target effects
- safety-check: Display safety information
"""

import argparse
import sys
import os
from typing import Optional

from . import __version__
from .safety import print_safety_disclaimer, validate_research_use, check_simulation_only
from .energies import estimate_energy_collapse_simulator
from .guide_opt import rank_guides_batch, generate_guide_report
from .phenotype import infer_offtarget_phenotype
from .io import batch_load_guides, save_results_csv, save_results_json


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='bioql-crispr',
        description='CRISPR-QAI: Quantum-enhanced CRISPR guide design',
        epilog='For more information: https://bioql.com/docs/crispr-qai'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'CRISPR-QAI v{__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # score-energy command
    score_parser = subparsers.add_parser(
        'score-energy',
        help='Calculate binding energy for single guide RNA'
    )
    score_parser.add_argument('sequence', help='Guide RNA sequence (e.g., ATCGAAGTC)')
    score_parser.add_argument('--shots', type=int, default=1000, help='Quantum shots')
    score_parser.add_argument('--coupling', type=float, default=1.0, help='Coupling strength')
    score_parser.add_argument('--backend', default='simulator', help='Quantum backend')

    # rank-guides command
    rank_parser = subparsers.add_parser(
        'rank-guides',
        help='Rank multiple guide RNAs from file'
    )
    rank_parser.add_argument('input_file', help='Input file (CSV or FASTA)')
    rank_parser.add_argument('-o', '--output', help='Output file (CSV or JSON)')
    rank_parser.add_argument('--shots', type=int, default=1000, help='Quantum shots')
    rank_parser.add_argument('--top-n', type=int, default=10, help='Show top N results')
    rank_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Output format')

    # infer-phenotype command
    phenotype_parser = subparsers.add_parser(
        'infer-phenotype',
        help='Predict off-target effects for guide RNA'
    )
    phenotype_parser.add_argument('sequence', help='Guide RNA sequence')
    phenotype_parser.add_argument('--genome', help='Genome regions file (FASTA)')
    phenotype_parser.add_argument('--max-mismatches', type=int, default=3, help='Max mismatches')

    # safety-check command
    safety_parser = subparsers.add_parser(
        'safety-check',
        help='Display safety information and disclaimer'
    )

    args = parser.parse_args()

    # Show help if no command
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Safety check on startup
    check_simulation_only()

    # Route to command handlers
    try:
        if args.command == 'score-energy':
            cmd_score_energy(args)
        elif args.command == 'rank-guides':
            cmd_rank_guides(args)
        elif args.command == 'infer-phenotype':
            cmd_infer_phenotype(args)
        elif args.command == 'safety-check':
            cmd_safety_check(args)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_score_energy(args):
    """Handle score-energy command"""
    print(f"Scoring guide RNA: {args.sequence}")
    print(f"Backend: {args.backend}, Shots: {args.shots}")
    print()

    # Calculate energy
    result = estimate_energy_collapse_simulator(
        guide_seq=args.sequence,
        shots=args.shots,
        coupling_strength=args.coupling
    )

    # Display results
    print("Results:")
    print(f"  Energy Estimate: {result['energy_estimate']:.4f}")
    print(f"  Confidence: {result['confidence']:.4f}")
    print(f"  Runtime: {result['runtime_seconds']:.3f}s")
    print(f"  Num Qubits: {result['num_qubits']}")
    print()


def cmd_rank_guides(args):
    """Handle rank-guides command"""
    print(f"Loading guides from: {args.input_file}")

    # Load guides
    guides = batch_load_guides(args.input_file)
    print(f"Loaded {len(guides)} guides")
    print()

    # Rank guides
    print(f"Ranking guides (shots={args.shots})...")
    ranked = rank_guides_batch(guides, shots=args.shots)

    # Display report
    report = generate_guide_report(ranked, top_n=args.top_n)
    print(report)

    # Save if output specified
    if args.output:
        if args.format == 'csv':
            save_results_csv(ranked, args.output)
        else:
            save_results_json(ranked, args.output)

        print(f"Results saved to: {args.output}")


def cmd_infer_phenotype(args):
    """Handle infer-phenotype command"""
    print(f"Analyzing guide RNA: {args.sequence}")
    print()

    # Load genome if provided
    genome_regions = None
    if args.genome:
        from .io import load_fasta
        print(f"Loading genome from: {args.genome}")
        fasta_data = load_fasta(args.genome)
        genome_regions = [s['sequence'] for s in fasta_data]
        print(f"Loaded {len(genome_regions)} genome regions")
        print()

    # Infer phenotype
    result = infer_offtarget_phenotype(
        guide_seq=args.sequence,
        genome_regions=genome_regions,
        max_mismatches=args.max_mismatches
    )

    # Display results
    print("Off-Target Analysis:")
    print(f"  Risk Level: {result['offtarget_risk'].upper()}")
    print(f"  Risk Score: {result['risk_score']:.3f}")
    print(f"  Potential Off-Targets: {result['num_potential_offtargets']}")
    print()

    if result['offtarget_sites']:
        print("Top Off-Target Sites:")
        for i, site in enumerate(result['offtarget_sites'][:5], 1):
            print(f"  {i}. {site['sequence']} "
                  f"(similarity: {site['similarity']:.2f}, "
                  f"mismatches: {site['mismatches']})")
        print()

    print("Recommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")
    print()


def cmd_safety_check(args):
    """Handle safety-check command"""
    print_safety_disclaimer()


if __name__ == '__main__':
    main()
