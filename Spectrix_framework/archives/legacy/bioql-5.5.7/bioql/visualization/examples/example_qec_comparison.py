"""
BioQL 5.0.0 - QEC Code Comparison Example

This example demonstrates how to compare different QEC codes
(Surface, Steane, Shor) and analyze their trade-offs.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from qiskit import QuantumCircuit
import matplotlib.pyplot as plt
import numpy as np

from bioql.visualization import QECVisualizer, ResourceEstimator
from bioql.qec import SurfaceCodeQEC, SteaneCodeQEC, ShorCodeQEC


def create_test_circuit(num_qubits: int = 15, depth: int = 150) -> QuantumCircuit:
    """
    Create a test quantum circuit

    Args:
        num_qubits: Number of qubits
        depth: Circuit depth

    Returns:
        Qiskit QuantumCircuit
    """
    qc = QuantumCircuit(num_qubits)

    # Create layered circuit structure
    for layer in range(depth // 5):
        # Hadamard gates
        for i in range(0, num_qubits, 2):
            qc.h(i)

        # CNOT gates
        for i in range(0, num_qubits - 1, 2):
            qc.cx(i, i + 1)

        # T-gates (critical for magic state counting)
        for i in range(0, num_qubits, 4):
            qc.t(i)

        # S-gates
        for i in range(1, num_qubits, 3):
            qc.s(i)

        # Rotation gates
        for i in range(num_qubits):
            if i % 2 == 0:
                qc.rz(0.5, i)

    qc.measure_all()
    return qc


def compare_qec_overhead():
    """
    Compare qubit overhead across different QEC codes

    This demonstrates the trade-offs between surface codes,
    Steane codes, and Shor codes.
    """
    print("=" * 70)
    print("BioQL 5.0.0 - QEC Code Comparison: Overhead Analysis")
    print("=" * 70)

    # Create visualizer
    viz = QECVisualizer()

    # Define different QEC configurations
    qec_configs = [
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    # Create overhead comparison plot
    fig = viz.plot_qubit_overhead(
        qec_configs,
        logical_qubits_range=[5, 10, 20, 50, 100, 200, 500]
    )

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "qec_overhead_comparison.png"

    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved overhead comparison to: {output_path}")

    plt.show()


def compare_error_rates():
    """
    Compare error rates across different QEC codes

    This shows how different codes suppress errors and their
    relative performance.
    """
    print("\n" + "=" * 70)
    print("QEC Error Rate Comparison")
    print("=" * 70)

    # Create QEC instances
    surface = SurfaceCodeQEC(code_distance=5, error_rate=0.001)
    steane = SteaneCodeQEC(error_rate=0.001)
    shor = ShorCodeQEC(error_rate=0.001)

    # Get overhead metrics
    surface_overhead = surface.calculate_overhead()
    steane_overhead = steane.calculate_overhead()
    shor_overhead = shor.calculate_overhead()

    # Prepare results for plotting
    results = [
        {
            'qec_type': 'Surface (d=5)',
            'raw_error': 0.001,
            'corrected_error': surface_overhead['logical_error_rate']
        },
        {
            'qec_type': 'Steane (7-qubit)',
            'raw_error': 0.001,
            'corrected_error': steane_overhead['logical_error_rate']
        },
        {
            'qec_type': 'Shor (9-qubit)',
            'raw_error': 0.001,
            'corrected_error': shor_overhead['logical_error_rate']
        }
    ]

    # Create visualizer
    viz = QECVisualizer()

    # Create error rate comparison plot
    fig = viz.plot_error_rates(results, show_threshold=True)

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "qec_error_comparison.png"

    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved error comparison to: {output_path}")

    # Print numerical comparison
    print("\n" + "-" * 70)
    print("Error Suppression Factors:")
    print("-" * 70)

    for result in results:
        suppression = result['raw_error'] / result['corrected_error']
        print(f"{result['qec_type']:20s}: {suppression:8.1f}x error suppression")

    plt.show()


def compare_resources_detailed():
    """
    Detailed resource comparison across QEC codes

    This provides a comprehensive comparison of all resource
    metrics for different QEC implementations.
    """
    print("\n" + "=" * 70)
    print("Detailed Resource Comparison")
    print("=" * 70)

    # Create test circuit
    circuit = create_test_circuit(num_qubits=20, depth=200)

    print(f"\nTest Circuit:")
    print(f"  • Qubits: {circuit.num_qubits}")
    print(f"  • Depth: {circuit.depth()}")
    print(f"  • Total Gates: {sum(circuit.count_ops().values())}")

    # Create resource estimator
    estimator = ResourceEstimator()

    # Test different QEC codes
    qec_configs = [
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    print("\n" + "=" * 70)
    print(" " * 20 + "RESOURCE COMPARISON TABLE")
    print("=" * 70)

    # Print header
    print(f"{'Metric':<25} {'Surface (d=5)':<20} {'Steane':<20} {'Shor':<20}")
    print("-" * 85)

    # Estimate resources for each code
    estimations = []
    for config in qec_configs:
        estimation = estimator.estimate_resources(circuit, config)
        estimations.append(estimation)

    # Compare metrics
    metrics = [
        ('Physical Qubits', 'physical_qubits', ','),
        ('Overhead Factor', 'overhead_factor', '.1f'),
        ('T-Gates', 't_gates', ','),
        ('Magic States', 'magic_states', ','),
        ('Circuit Depth', 'circuit_depth', ','),
        ('Error Rate', 'error_rate', '.2e'),
        ('Time (ms)', 'time_to_solution_ms', '.2f'),
    ]

    for metric_name, metric_attr, fmt in metrics:
        values = [getattr(est, metric_attr) for est in estimations]
        if ',' in fmt:
            formatted = [f"{v:,}" for v in values]
        else:
            formatted = [f"{v:{fmt}}" for v in values]

        print(f"{metric_name:<25} {formatted[0]:<20} {formatted[1]:<20} {formatted[2]:<20}")

    print("=" * 85)

    # Identify best code for each metric
    print("\n" + "=" * 70)
    print("Best QEC Code by Metric:")
    print("=" * 70)

    code_names = ['Surface (d=5)', 'Steane (7-qubit)', 'Shor (9-qubit)']

    # Physical qubits (lower is better)
    phys_qubits = [est.physical_qubits for est in estimations]
    best_phys_idx = np.argmin(phys_qubits)
    print(f"  Lowest Physical Qubits: {code_names[best_phys_idx]} ({phys_qubits[best_phys_idx]:,})")

    # Error rate (lower is better)
    error_rates = [est.error_rate for est in estimations]
    best_error_idx = np.argmin(error_rates)
    print(f"  Lowest Error Rate: {code_names[best_error_idx]} ({error_rates[best_error_idx]:.2e})")

    # Time (lower is better)
    times = [est.time_to_solution_ms for est in estimations]
    best_time_idx = np.argmin(times)
    print(f"  Fastest Execution: {code_names[best_time_idx]} ({times[best_time_idx]:.2f} ms)")


def compare_multiple_distances():
    """
    Compare surface codes at different distances with other codes

    This shows how surface code performance changes with distance
    and compares to fixed-distance Steane and Shor codes.
    """
    print("\n" + "=" * 70)
    print("Multi-Distance Comparison")
    print("=" * 70)

    # Create visualizer
    viz = QECVisualizer()

    # Define configurations
    qec_configs = [
        {'type': 'surface', 'distance': 3, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 7, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    # Create comparison plot
    fig = viz.plot_qubit_overhead(
        qec_configs,
        logical_qubits_range=[10, 20, 50, 100, 200, 500]
    )

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_path = output_dir / "qec_multi_comparison.png"

    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved multi-distance comparison to: {output_path}")

    plt.show()


def create_comparison_report():
    """
    Generate comprehensive comparison report

    This creates an interactive HTML report comparing all QEC codes.
    """
    print("\n" + "=" * 70)
    print("Interactive QEC Comparison Report")
    print("=" * 70)

    # Create visualizer
    viz = QECVisualizer()

    # Define all configurations to compare
    qec_configs = [
        {'type': 'surface', 'distance': 3, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 7, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    # Create interactive plot
    fig = viz.create_interactive_plot(
        qec_configs,
        logical_qubits_range=[5, 10, 20, 50, 100, 200, 500, 1000]
    )

    # Save as HTML
    output_dir = Path(__file__).parent / "output"
    output_path = output_dir / "qec_comparison_interactive.html"

    viz.export_interactive_html(fig, str(output_path))
    print(f"\n✓ Saved interactive comparison to: {output_path}")
    print(f"  Open in browser to explore QEC trade-offs!")


def analyze_qec_tradeoffs():
    """
    Analyze trade-offs between different QEC schemes

    This provides insights into when to use each type of QEC code.
    """
    print("\n" + "=" * 70)
    print("QEC Trade-Off Analysis")
    print("=" * 70)

    # Create test circuit
    circuit = create_test_circuit(num_qubits=30, depth=300)
    estimator = ResourceEstimator()

    # Test configurations
    configs = [
        {'type': 'surface', 'distance': 3, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 7, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    print("\n" + "-" * 70)
    print("RECOMMENDATIONS:")
    print("-" * 70)

    for config in configs:
        est = estimator.estimate_resources(circuit, config)
        code_name = f"{config['type'].title()} (d={config['distance']})"

        print(f"\n{code_name}:")

        # Analyze characteristics
        if est.error_rate < 1e-6:
            print(f"  ✓ Excellent error suppression ({est.error_rate:.2e})")
        elif est.error_rate < 1e-5:
            print(f"  • Good error suppression ({est.error_rate:.2e})")
        else:
            print(f"  ⚠ Moderate error suppression ({est.error_rate:.2e})")

        if est.physical_qubits < 1000:
            print(f"  ✓ Low qubit overhead ({est.physical_qubits:,} physical qubits)")
        elif est.physical_qubits < 5000:
            print(f"  • Moderate qubit overhead ({est.physical_qubits:,} physical qubits)")
        else:
            print(f"  ⚠ High qubit overhead ({est.physical_qubits:,} physical qubits)")

        if est.time_to_solution_ms < 100:
            print(f"  ✓ Fast execution ({est.time_to_solution_ms:.2f} ms)")
        elif est.time_to_solution_ms < 500:
            print(f"  • Moderate execution time ({est.time_to_solution_ms:.2f} ms)")
        else:
            print(f"  ⚠ Slow execution ({est.time_to_solution_ms:.2f} ms)")

        # Overall recommendation
        if config['type'] == 'surface' and config['distance'] == 5:
            print(f"  → RECOMMENDED: Best balance for most applications")
        elif config['type'] == 'steane':
            print(f"  → SUITABLE: Good for moderate-scale circuits")
        elif config['type'] == 'shor':
            print(f"  → SUITABLE: Good for small-scale, high-fidelity needs")


def main():
    """Run all QEC comparison examples"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 12 + "BioQL 5.0.0 - QEC Code Comparison Examples" + " " * 13 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run comparisons
    compare_qec_overhead()
    compare_error_rates()
    compare_resources_detailed()
    compare_multiple_distances()
    create_comparison_report()
    analyze_qec_tradeoffs()

    print("\n" + "=" * 70)
    print("All comparison examples completed successfully!")
    print("=" * 70)
    print("\nKey Insights:")
    print("  • Surface codes offer flexible distance tuning")
    print("  • Steane codes provide good balance for medium circuits")
    print("  • Shor codes excel at small-scale, high-fidelity tasks")
    print("\nCheck 'output' directory for visualizations.")


if __name__ == "__main__":
    main()
