#!/usr/bin/env python3
"""
BioQL Benchmark Runner
======================
Orchestrates all benchmark suites and produces unified reports.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Ensure agents are importable
_agents_dir = str(Path(__file__).resolve().parent.parent / "BioQL_MCP" / "src" / "agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

_benchmarks_dir = str(Path(__file__).resolve().parent)
if _benchmarks_dir not in sys.path:
    sys.path.insert(0, _benchmarks_dir)

from qmem_benchmark import QMEMBenchmark
from mhce_benchmark import MHCEBenchmark


class BenchmarkRunner:
    """
    Unified benchmark runner for BioQL quantum capabilities.

    Usage:
        runner = BenchmarkRunner()
        results = runner.run_quick("H2")  # Fast CI benchmark
        results = runner.run_all()         # Full publication benchmark
    """

    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_quick(self, molecule: str = "H2") -> dict:
        """
        Quick benchmark for CI/CD (< 2 minutes on simulator).

        Runs QMEM + MHCE on a single molecule with few seeds.
        """
        start = time.time()

        results = {
            "type": "quick",
            "molecule": molecule,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # QMEM quick
        qmem = QMEMBenchmark(use_hardware=False)
        results["qmem"] = qmem.run_mitigation_comparison(molecule, seed=42)

        # MHCE quick
        mhce = MHCEBenchmark()
        results["mhce"] = mhce.run_compression_comparison(molecule)

        results["total_runtime_seconds"] = time.time() - start

        # Save
        self._save(results, "quick_benchmark.json")

        return results

    def run_all(
        self,
        molecules: Optional[list] = None,
        n_seeds: int = 10,
    ) -> dict:
        """
        Full publication-grade benchmark suite.

        Args:
            molecules: List of molecule names (default: ["H2", "H2_4q"])
            n_seeds: Number of random seeds for statistical analysis
        """
        if molecules is None:
            molecules = ["H2", "H2_4q"]

        start = time.time()

        results = {
            "type": "full",
            "molecules": molecules,
            "n_seeds": n_seeds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "qmem": {},
            "mhce": {},
        }

        # QMEM full analysis
        qmem = QMEMBenchmark(use_hardware=False)
        for mol in molecules:
            try:
                results["qmem"][mol] = qmem.run_statistical_analysis(mol, n_seeds=n_seeds)
            except Exception as e:
                results["qmem"][mol] = {"error": str(e)}

        # MHCE analysis
        mhce = MHCEBenchmark()
        for mol in molecules:
            try:
                results["mhce"][mol] = mhce.run_compression_comparison(mol)
            except Exception as e:
                results["mhce"][mol] = {"error": str(e)}

        results["total_runtime_seconds"] = time.time() - start

        # Save JSON
        self._save(results, "full_benchmark.json")

        # Generate Markdown reports
        for mol in molecules:
            if mol in results["qmem"] and "error" not in results["qmem"][mol]:
                report = qmem.generate_report(results["qmem"][mol])
                self._save_text(report, f"qmem_report_{mol}.md")

            if mol in results["mhce"] and "error" not in results["mhce"][mol]:
                report = mhce.generate_report(results["mhce"][mol])
                self._save_text(report, f"mhce_report_{mol}.md")

        # Summary report
        summary = self._generate_summary(results)
        self._save_text(summary, "BENCHMARK_SUMMARY.md")

        return results

    def _generate_summary(self, results: dict) -> str:
        """Generate unified summary report."""
        lines = [
            "# BioQL Quantum Benchmark Summary",
            f"\nGenerated: {results['timestamp']}",
            f"Type: {results['type']}",
            f"Total Runtime: {results.get('total_runtime_seconds', 0):.1f}s",
            "",
        ]

        # QMEM summary
        lines.append("## QMEM (Error Mitigation)")
        for mol, data in results.get("qmem", {}).items():
            if "error" in data:
                lines.append(f"\n### {mol}: ERROR — {data['error']}")
                continue
            if "best_technique" in data:
                lines.append(f"\n### {mol}")
                lines.append(f"- Best technique: **{data['best_technique']}**")
                best_stats = data.get("technique_stats", {}).get(data["best_technique"], {})
                lines.append(f"- Mean error: {best_stats.get('mean_error_kcal_mol', '?'):.2f} kcal/mol")
                lines.append(f"- Chemical accuracy rate: {best_stats.get('chemical_accuracy_rate', 0)*100:.0f}%")

        # MHCE summary
        lines.append("\n## MHCE (Hamiltonian Compression)")
        for mol, data in results.get("mhce", {}).items():
            if "error" in data:
                lines.append(f"\n### {mol}: ERROR — {data['error']}")
                continue
            summary = data.get("summary", {})
            lines.append(f"\n### {mol}")
            lines.append(f"- Best strategy: **{summary.get('best_strategy', '?')}**")
            lines.append(f"- Max qubit reduction: {summary.get('max_qubit_reduction', 0):.1f}%")

        # Qiskit version
        try:
            import qiskit
            lines.append(f"\n## Environment")
            lines.append(f"- Qiskit: {qiskit.__version__}")
        except ImportError:
            pass

        return "\n".join(lines)

    def _save(self, data: dict, filename: str):
        """Save JSON results."""
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2, default=str))

    def _save_text(self, text: str, filename: str):
        """Save text report."""
        path = self.output_dir / filename
        path.write_text(text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BioQL Benchmark Runner")
    parser.add_argument("--quick", action="store_true", help="Quick benchmark (H2 only)")
    parser.add_argument("--full", action="store_true", help="Full benchmark suite")
    parser.add_argument("--molecule", default="H2", help="Molecule for quick benchmark")
    parser.add_argument("--seeds", type=int, default=10, help="Number of seeds for full benchmark")
    parser.add_argument("--output", default="benchmark_results", help="Output directory")
    args = parser.parse_args()

    runner = BenchmarkRunner(output_dir=args.output)

    if args.full:
        print("Running full benchmark suite...")
        results = runner.run_all(n_seeds=args.seeds)
        print(f"Done in {results['total_runtime_seconds']:.1f}s")
        print(f"Reports saved to {args.output}/")
    else:
        print(f"Running quick benchmark on {args.molecule}...")
        results = runner.run_quick(args.molecule)
        print(f"Done in {results['total_runtime_seconds']:.1f}s")
        print(json.dumps(results, indent=2, default=str)[:2000])
