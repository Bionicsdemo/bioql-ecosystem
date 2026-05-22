"""
Tests for the BioQL Benchmark Suite.
"""
import sys
import pytest
import json
from pathlib import Path

_agents_dir = str(Path(__file__).resolve().parent.parent.parent / "src" / "backend" / "BioQL_MCP" / "src" / "agents")
_benchmarks_dir = str(Path(__file__).resolve().parent.parent.parent / "src" / "backend" / "benchmarks")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)
if _benchmarks_dir not in sys.path:
    sys.path.insert(0, _benchmarks_dir)

from qmem_benchmark import QMEMBenchmark
from mhce_benchmark import MHCEBenchmark
from benchmark_runner import BenchmarkRunner


@pytest.mark.timeout(120)
def test_qmem_benchmark_h2():
    """QMEM benchmark on H2 produces valid results."""
    bench = QMEMBenchmark(use_hardware=False)
    results = bench.run_mitigation_comparison("H2", seed=42)

    assert "raw" in results
    assert "zne" in results
    assert "pec" in results
    assert "combined" in results

    for technique, result in results.items():
        assert "energy" in result
        assert "error_ha" in result
        assert "chemical_accuracy" in result
        assert result["error_ha"] >= 0


@pytest.mark.timeout(180)
def test_qmem_statistical_analysis():
    """Statistical analysis produces valid statistics."""
    bench = QMEMBenchmark(use_hardware=False)
    analysis = bench.run_statistical_analysis("H2", n_seeds=3)

    assert "technique_stats" in analysis
    assert "pairwise_tests" in analysis
    assert "best_technique" in analysis

    for technique, stats in analysis["technique_stats"].items():
        assert "mean_error_ha" in stats
        assert "bootstrap_ci_95_ha" in stats
        assert len(stats["bootstrap_ci_95_ha"]) == 2
        # CI lower <= mean <= CI upper
        ci = stats["bootstrap_ci_95_ha"]
        assert ci[0] <= stats["mean_error_ha"] <= ci[1] or abs(ci[0] - ci[1]) < 1e-6


@pytest.mark.timeout(120)
def test_mhce_benchmark_h2():
    """MHCE benchmark on H2 produces valid results."""
    bench = MHCEBenchmark()
    results = bench.run_compression_comparison("H2")

    assert "no_compression" in results
    assert "jw_tapered" in results
    assert "bk" in results
    assert "bk_tapered" in results
    assert "summary" in results

    # Baseline should have 4 qubits (H2 4-qubit Hamiltonian)
    assert results["no_compression"]["qubits"] == 4


@pytest.mark.timeout(120)
def test_qmem_report_format():
    """QMEM Markdown report has expected sections."""
    bench = QMEMBenchmark(use_hardware=False)
    analysis = bench.run_statistical_analysis("H2", n_seeds=3)
    report = bench.generate_report(analysis)

    assert isinstance(report, str)
    assert "# QMEM Benchmark Report" in report
    assert "Per-Technique Results" in report
    assert "Pairwise Statistical Tests" in report
    assert "raw" in report
    assert "combined" in report


@pytest.mark.timeout(120)
def test_mhce_report_format():
    """MHCE Markdown report has expected sections."""
    bench = MHCEBenchmark()
    comparison = bench.run_compression_comparison("H2")
    report = bench.generate_report(comparison)

    assert isinstance(report, str)
    assert "# MHCE Benchmark Report" in report
    assert "Compression Results" in report
    assert "no_compression" in report


@pytest.mark.timeout(180)
def test_benchmark_runner_quick(tmp_path):
    """Quick benchmark runner produces output files."""
    runner = BenchmarkRunner(output_dir=str(tmp_path))
    results = runner.run_quick("H2")

    assert "qmem" in results
    assert "mhce" in results
    assert results["total_runtime_seconds"] > 0

    # Check output file was created
    assert (tmp_path / "quick_benchmark.json").exists()
    data = json.loads((tmp_path / "quick_benchmark.json").read_text())
    assert data["type"] == "quick"


@pytest.mark.timeout(60)
def test_bootstrap_ci_valid():
    """Bootstrap CI produces valid intervals."""
    bench = QMEMBenchmark(use_hardware=False)
    import numpy as np
    data = np.array([0.01, 0.02, 0.015, 0.018, 0.012])
    ci = bench._bootstrap_ci(data)

    assert len(ci) == 2
    assert ci[0] <= ci[1]
    assert ci[0] >= 0
    assert ci[0] <= np.mean(data)
    assert ci[1] >= np.mean(data)
