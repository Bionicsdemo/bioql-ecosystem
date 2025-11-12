"""
BioQL 5.0.0 - Surface Code Visualization Example

This example demonstrates how to visualize surface code overhead
and analyze resource requirements for different code distances.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from qiskit import QuantumCircuit
import matplotlib.pyplot as plt

from bioql.visualization import QECVisualizer, ResourceEstimator
from bioql.qec import SurfaceCodeQEC


def create_sample_circuit(num_qubits: int = 10, depth: int = 100) -> QuantumCircuit:
    """
    Create a sample quantum circuit for testing

    Args:
        num_qubits: Number of qubits
        depth: Circuit depth

    Returns:
        Qiskit QuantumCircuit
    """
    qc = QuantumCircuit(num_qubits)

    # Add gates to create realistic circuit
    for layer in range(depth // 4):
        # Hadamard layer
        for i in range(num_qubits):
            qc.h(i)

        # CNOT layer
        for i in range(0, num_qubits - 1, 2):
            qc.cx(i, i + 1)

        # T-gate layer (non-Clifford)
        for i in range(0, num_qubits, 3):
            qc.t(i)

        # Rotation layer
        for i in range(num_qubits):
            qc.rz(0.5, i)

    # Add measurements
    qc.measure_all()

    return qc


def example_surface_code_scaling():
    """
    Demonstrate surface code scaling with code distance

    This shows how resource requirements scale as we increase
    the code distance for better error correction.
    """
    print("=" * 70)
    print("BioQL 5.0.0 - Surface Code Scaling Analysis")
    print("=" * 70)

    # Create visualizer
    viz = QECVisualizer()

    # Test different code distances
    distances = [3, 5, 7, 9, 11, 13, 15]

    # Create plot
    fig = viz.plot_code_distance_scaling(
        qec_type='surface',
        distance_range=distances,
        error_rate=0.001
    )

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "surface_code_scaling.png"

    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved scaling analysis to: {output_path}")

    plt.show()


def example_resource_estimation():
    """
    Estimate resources for a quantum circuit with surface code QEC

    This demonstrates how to use the ResourceEstimator to analyze
    a circuit and generate comprehensive resource estimates.
    """
    print("\n" + "=" * 70)
    print("Surface Code Resource Estimation")
    print("=" * 70)

    # Create sample circuit
    num_qubits = 20
    circuit = create_sample_circuit(num_qubits=num_qubits, depth=200)

    print(f"\nCircuit Statistics:")
    print(f"  • Qubits: {circuit.num_qubits}")
    print(f"  • Depth: {circuit.depth()}")
    print(f"  • Gates: {sum(circuit.count_ops().values())}")

    # Create resource estimator
    estimator = ResourceEstimator()

    # Test different code distances
    distances = [3, 5, 7, 9]

    print("\n" + "-" * 70)
    print("Resource Estimates for Different Code Distances:")
    print("-" * 70)

    for distance in distances:
        qec_config = {
            'type': 'surface',
            'distance': distance,
            'error_rate': 0.001
        }

        # Estimate resources
        resources = estimator.estimate_resources(circuit, qec_config)

        print(f"\nCode Distance d={distance}:")
        print(f"  Physical Qubits: {resources.physical_qubits:,}")
        print(f"  Overhead Factor: {resources.overhead_factor:.1f}x")
        print(f"  T-Gates: {resources.t_gates:,}")
        print(f"  Magic States: {resources.magic_states:,}")
        print(f"  Logical Error Rate: {resources.error_rate:.2e}")
        print(f"  Time to Solution: {resources.time_to_solution_ms:.2f} ms")


def example_overhead_visualization():
    """
    Visualize surface code overhead for different configurations

    This creates a comprehensive plot showing how overhead scales
    with code distance and logical qubit count.
    """
    print("\n" + "=" * 70)
    print("Surface Code Overhead Visualization")
    print("=" * 70)

    # Create visualizer
    viz = QECVisualizer()

    # Define different surface code configurations
    qec_configs = [
        {'type': 'surface', 'distance': 3, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 7, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 9, 'error_rate': 0.001},
    ]

    # Create overhead plot
    fig = viz.plot_qubit_overhead(
        qec_configs,
        logical_qubits_range=[5, 10, 20, 50, 100, 200, 500, 1000]
    )

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "surface_code_overhead.png"

    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved overhead plot to: {output_path}")

    plt.show()


def example_interactive_plot():
    """
    Create interactive plotly visualization

    This generates an interactive HTML plot that can be explored
    in a web browser with hover information and zoom capabilities.
    """
    print("\n" + "=" * 70)
    print("Interactive Surface Code Visualization")
    print("=" * 70)

    # Create visualizer
    viz = QECVisualizer()

    # Define surface code configurations
    qec_configs = [
        {'type': 'surface', 'distance': 3, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 7, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 9, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 11, 'error_rate': 0.001},
    ]

    # Create interactive plot
    fig = viz.create_interactive_plot(
        qec_configs,
        logical_qubits_range=[5, 10, 20, 50, 100, 200, 500, 1000]
    )

    # Save as HTML
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "surface_code_interactive.html"

    viz.export_interactive_html(fig, str(output_path))
    print(f"\n✓ Saved interactive plot to: {output_path}")
    print(f"  Open this file in a web browser to explore!")


def example_qec_report():
    """
    Generate comprehensive HTML report

    This creates a detailed HTML report with all QEC metrics
    and resource estimates for a specific configuration.
    """
    print("\n" + "=" * 70)
    print("QEC Resource Estimation Report")
    print("=" * 70)

    # Create circuit
    circuit = create_sample_circuit(num_qubits=50, depth=500)

    # Create estimator and visualizer
    estimator = ResourceEstimator()
    viz = QECVisualizer()

    # Estimate resources
    qec_config = {
        'type': 'surface',
        'distance': 7,
        'error_rate': 0.001
    }

    resources = estimator.estimate_resources(circuit, qec_config)

    # Generate HTML report
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "surface_code_report.html"

    html = viz.generate_qec_report(resources, str(output_path))

    print(f"\n✓ Generated QEC report: {output_path}")
    print(f"  Open this file in a web browser to view!")

    # Also print text summary
    summary = estimator.generate_resource_summary(resources)
    print(summary)


def main():
    """Run all surface code visualization examples"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "BioQL 5.0.0 - Surface Code Visualization Examples" + " " * 8 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run examples
    example_surface_code_scaling()
    example_resource_estimation()
    example_overhead_visualization()
    example_interactive_plot()
    example_qec_report()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
    print("\nCheck the 'output' directory for generated visualizations.")


if __name__ == "__main__":
    main()
