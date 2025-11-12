"""
BioQL 5.0.0 - QEC Cost Analysis Example

This example demonstrates how to analyze cost vs fidelity trade-offs
and visualize the economic aspects of different QEC implementations.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from qiskit import QuantumCircuit
import matplotlib.pyplot as plt
import numpy as np

from bioql.visualization import QECVisualizer, ResourceEstimator


def create_application_circuit(circuit_type: str = 'chemistry') -> QuantumCircuit:
    """
    Create application-specific quantum circuits

    Args:
        circuit_type: Type of application ('chemistry', 'optimization', 'simulation')

    Returns:
        Qiskit QuantumCircuit
    """
    if circuit_type == 'chemistry':
        # Molecular simulation circuit
        qc = QuantumCircuit(12)
        for i in range(12):
            qc.h(i)
        for i in range(0, 11, 2):
            qc.cx(i, i + 1)
        for i in range(12):
            qc.t(i)  # Many T-gates for chemistry
        for i in range(0, 10, 3):
            qc.ccx(i, i + 1, i + 2)  # Toffoli gates
        qc.measure_all()

    elif circuit_type == 'optimization':
        # QAOA-style circuit
        qc = QuantumCircuit(10)
        layers = 5
        for _ in range(layers):
            for i in range(10):
                qc.h(i)
            for i in range(0, 9):
                qc.cx(i, i + 1)
            for i in range(10):
                qc.rz(0.5, i)
        qc.measure_all()

    else:  # simulation
        # General quantum simulation
        qc = QuantumCircuit(15)
        for _ in range(10):
            for i in range(15):
                qc.h(i)
            for i in range(0, 14, 2):
                qc.cx(i, i + 1)
            for i in range(0, 15, 3):
                qc.t(i)
        qc.measure_all()

    return qc


def analyze_cost_breakdown():
    """
    Analyze and visualize cost breakdown for different QEC codes

    This shows how different cost components (qubits, time, gates, etc.)
    contribute to the total implementation cost.
    """
    print("=" * 70)
    print("BioQL 5.0.0 - QEC Cost Breakdown Analysis")
    print("=" * 70)

    viz = QECVisualizer()

    # Test different QEC configurations
    configs = [
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    print("\nGenerating cost breakdown visualizations...\n")

    for config in configs:
        qec_type = config['type']
        distance = config['distance']

        # Create cost breakdown plot
        fig = viz.plot_cost_breakdown(config, shots=1000)

        # Save figure
        output_path = output_dir / f"cost_breakdown_{qec_type}_d{distance}.png"
        viz.save_figure(fig, str(output_path), dpi=300)
        print(f"✓ Saved {qec_type.title()} cost breakdown to: {output_path}")

    plt.show()


def cost_vs_fidelity_analysis():
    """
    Analyze cost vs fidelity trade-offs

    This demonstrates how increasing code distance (better fidelity)
    increases resource costs, allowing users to find optimal balance.
    """
    print("\n" + "=" * 70)
    print("Cost vs Fidelity Trade-Off Analysis")
    print("=" * 70)

    # Create test circuit
    circuit = create_application_circuit('chemistry')
    estimator = ResourceEstimator()

    # Test different code distances
    distances = [3, 5, 7, 9, 11, 13]

    print(f"\nTest Circuit: Chemistry Application")
    print(f"  • Qubits: {circuit.num_qubits}")
    print(f"  • Depth: {circuit.depth()}")

    print("\n" + "-" * 70)
    print("Cost vs Fidelity Trade-Offs:")
    print("-" * 70)

    # Collect data
    physical_qubits_list = []
    error_rates_list = []
    time_list = []

    for distance in distances:
        config = {'type': 'surface', 'distance': distance, 'error_rate': 0.001}
        est = estimator.estimate_resources(circuit, config)

        physical_qubits_list.append(est.physical_qubits)
        error_rates_list.append(est.error_rate)
        time_list.append(est.time_to_solution_ms)

        # Calculate "cost score" (normalized combination of resources)
        cost_score = (est.physical_qubits / 100) + (est.time_to_solution_ms / 10)

        print(f"\nCode Distance d={distance}:")
        print(f"  Physical Qubits: {est.physical_qubits:,}")
        print(f"  Error Rate: {est.error_rate:.2e}")
        print(f"  Time to Solution: {est.time_to_solution_ms:.2f} ms")
        print(f"  Cost Score: {cost_score:.2f}")
        print(f"  Cost/Fidelity Ratio: {cost_score / (1/est.error_rate):.2e}")

    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Physical Qubits vs Error Rate
    ax1.plot(error_rates_list, physical_qubits_list, 'o-', linewidth=2, markersize=8)
    ax1.set_xlabel('Logical Error Rate', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Physical Qubits Required', fontsize=12, fontweight='bold')
    ax1.set_title('Qubit Cost vs Error Rate', fontsize=13, fontweight='bold')
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.invert_xaxis()  # Lower error rate (better) on right

    # Plot 2: Time vs Error Rate
    ax2.plot(error_rates_list, time_list, 's-', linewidth=2, markersize=8, color='orange')
    ax2.set_xlabel('Logical Error Rate', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Time to Solution (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('Time Cost vs Error Rate', fontsize=13, fontweight='bold')
    ax2.set_xscale('log')
    ax2.grid(True, alpha=0.3)
    ax2.invert_xaxis()

    # Plot 3: Total Cost vs Code Distance
    cost_scores = [(pq / 100) + (t / 10) for pq, t in zip(physical_qubits_list, time_list)]
    ax3.bar(distances, cost_scores, alpha=0.7, color='green', edgecolor='black')
    ax3.set_xlabel('Code Distance', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Normalized Cost Score', fontsize=12, fontweight='bold')
    ax3.set_title('Total Cost vs Code Distance', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for i, (d, cs) in enumerate(zip(distances, cost_scores)):
        ax3.text(d, cs, f'{cs:.1f}', ha='center', va='bottom', fontsize=9)

    # Plot 4: Pareto frontier
    # Normalize metrics to [0, 1]
    norm_qubits = np.array(physical_qubits_list) / max(physical_qubits_list)
    norm_errors = np.array(error_rates_list) / max(error_rates_list)

    ax4.scatter(norm_errors, norm_qubits, s=200, alpha=0.6, c=distances, cmap='viridis')
    ax4.set_xlabel('Normalized Error Rate', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Normalized Qubit Cost', fontsize=12, fontweight='bold')
    ax4.set_title('Pareto Frontier: Error vs Cost', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # Add colorbar for code distance
    sm = plt.cm.ScalarMappable(cmap='viridis',
                               norm=plt.Normalize(vmin=min(distances), vmax=max(distances)))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax4)
    cbar.set_label('Code Distance', fontsize=10)

    # Annotate points
    for i, d in enumerate(distances):
        ax4.annotate(f'd={d}', (norm_errors[i], norm_qubits[i]),
                    xytext=(5, 5), textcoords='offset points', fontsize=9)

    fig.suptitle('Cost vs Fidelity Trade-Off Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_path = output_dir / "cost_fidelity_tradeoff.png"
    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved trade-off analysis to: {output_path}")

    plt.show()


def application_specific_cost_analysis():
    """
    Analyze costs for different application types

    This compares the cost of QEC for different quantum applications
    (chemistry, optimization, simulation).
    """
    print("\n" + "=" * 70)
    print("Application-Specific Cost Analysis")
    print("=" * 70)

    estimator = ResourceEstimator()
    viz = QECVisualizer()

    # Test different applications
    applications = ['chemistry', 'optimization', 'simulation']
    app_names = ['Molecular Chemistry', 'QAOA Optimization', 'Quantum Simulation']

    # QEC config
    qec_config = {'type': 'surface', 'distance': 5, 'error_rate': 0.001}

    print("\n" + "-" * 70)
    print(f"{'Application':<25} {'Qubits':<12} {'T-Gates':<12} {'Phys. Qubits':<15} {'Time (ms)':<12}")
    print("-" * 70)

    results_data = []

    for app, app_name in zip(applications, app_names):
        circuit = create_application_circuit(app)
        est = estimator.estimate_resources(circuit, qec_config)

        print(f"{app_name:<25} {est.logical_qubits:<12} {est.t_gates:<12} "
              f"{est.physical_qubits:<15,} {est.time_to_solution_ms:<12.2f}")

        results_data.append({
            'app': app_name,
            'logical_qubits': est.logical_qubits,
            't_gates': est.t_gates,
            'physical_qubits': est.physical_qubits,
            'time_ms': est.time_to_solution_ms
        })

    print("-" * 70)

    # Create comparison visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    apps_short = [r['app'] for r in results_data]
    colors = ['#3498db', '#e74c3c', '#2ecc71']

    # Plot 1: Physical Qubits by Application
    ax1.bar(apps_short, [r['physical_qubits'] for r in results_data],
           color=colors, alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Physical Qubits', fontsize=12, fontweight='bold')
    ax1.set_title('Physical Qubit Requirements', fontsize=13, fontweight='bold')
    ax1.tick_params(axis='x', rotation=15)
    ax1.grid(True, alpha=0.3, axis='y')

    # Plot 2: T-Gates by Application
    ax2.bar(apps_short, [r['t_gates'] for r in results_data],
           color=colors, alpha=0.7, edgecolor='black')
    ax2.set_ylabel('T-Gates', fontsize=12, fontweight='bold')
    ax2.set_title('Magic State Requirements', fontsize=13, fontweight='bold')
    ax2.tick_params(axis='x', rotation=15)
    ax2.grid(True, alpha=0.3, axis='y')

    # Plot 3: Execution Time
    ax3.bar(apps_short, [r['time_ms'] for r in results_data],
           color=colors, alpha=0.7, edgecolor='black')
    ax3.set_ylabel('Time to Solution (ms)', fontsize=12, fontweight='bold')
    ax3.set_title('Execution Time', fontsize=13, fontweight='bold')
    ax3.tick_params(axis='x', rotation=15)
    ax3.grid(True, alpha=0.3, axis='y')

    # Plot 4: Cost Comparison (normalized)
    # Normalize all metrics to [0, 1] and combine
    max_qubits = max(r['physical_qubits'] for r in results_data)
    max_time = max(r['time_ms'] for r in results_data)
    max_tgates = max(r['t_gates'] for r in results_data)

    total_costs = []
    for r in results_data:
        norm_cost = (r['physical_qubits'] / max_qubits * 0.4 +
                    r['time_ms'] / max_time * 0.3 +
                    r['t_gates'] / max_tgates * 0.3)
        total_costs.append(norm_cost * 100)  # Convert to percentage

    bars = ax4.barh(apps_short, total_costs, color=colors, alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Normalized Total Cost (%)', fontsize=12, fontweight='bold')
    ax4.set_title('Overall Resource Cost', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for bar, cost in zip(bars, total_costs):
        width = bar.get_width()
        ax4.text(width, bar.get_y() + bar.get_height()/2,
                f'{cost:.1f}%', ha='left', va='center', fontsize=10)

    fig.suptitle('Application-Specific QEC Cost Analysis (Surface Code d=5)',
                fontsize=16, fontweight='bold')
    plt.tight_layout()

    # Save figure
    output_dir = Path(__file__).parent / "output"
    output_path = output_dir / "application_cost_analysis.png"
    viz.save_figure(fig, str(output_path), dpi=300)
    print(f"\n✓ Saved application analysis to: {output_path}")

    plt.show()


def budget_optimization():
    """
    Optimize QEC choice based on resource budget constraints

    This helps users select the best QEC configuration given
    constraints on physical qubits, time, or error requirements.
    """
    print("\n" + "=" * 70)
    print("Budget-Constrained QEC Optimization")
    print("=" * 70)

    estimator = ResourceEstimator()

    # Create test circuit
    circuit = create_application_circuit('chemistry')

    # Define budget constraints
    budgets = [
        {'name': 'Low Budget', 'max_qubits': 500, 'max_time_ms': 100},
        {'name': 'Medium Budget', 'max_qubits': 2000, 'max_time_ms': 500},
        {'name': 'High Budget', 'max_qubits': 10000, 'max_time_ms': 2000},
    ]

    # Test configurations
    configs = [
        {'type': 'surface', 'distance': 3, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 5, 'error_rate': 0.001},
        {'type': 'surface', 'distance': 7, 'error_rate': 0.001},
        {'type': 'steane', 'distance': 7, 'error_rate': 0.001},
        {'type': 'shor', 'distance': 9, 'error_rate': 0.001},
    ]

    print("\n" + "=" * 70)
    print("BUDGET OPTIMIZATION RECOMMENDATIONS:")
    print("=" * 70)

    for budget in budgets:
        print(f"\n{budget['name']}:")
        print(f"  Constraints: Max {budget['max_qubits']:,} qubits, "
              f"Max {budget['max_time_ms']} ms")
        print(f"  Recommended QEC Configurations:")

        suitable_configs = []

        for config in configs:
            est = estimator.estimate_resources(circuit, config)

            if (est.physical_qubits <= budget['max_qubits'] and
                est.time_to_solution_ms <= budget['max_time_ms']):

                suitable_configs.append({
                    'config': config,
                    'estimation': est
                })

        if suitable_configs:
            # Sort by error rate (best first)
            suitable_configs.sort(key=lambda x: x['estimation'].error_rate)

            for i, sc in enumerate(suitable_configs[:3], 1):  # Top 3
                est = sc['estimation']
                cfg = sc['config']
                print(f"\n    {i}. {cfg['type'].title()} (d={cfg['distance']}):")
                print(f"       • Physical Qubits: {est.physical_qubits:,}")
                print(f"       • Error Rate: {est.error_rate:.2e}")
                print(f"       • Time: {est.time_to_solution_ms:.2f} ms")
                print(f"       • Overhead: {est.overhead_factor:.1f}x")
        else:
            print("\n    ⚠ No configurations meet budget constraints!")
            print("    Consider: Increasing budget or simplifying circuit")


def roi_analysis():
    """
    Return on Investment (ROI) analysis for QEC

    This analyzes the cost-benefit of investing in better QEC
    in terms of error reduction per resource unit.
    """
    print("\n" + "=" * 70)
    print("QEC Return on Investment (ROI) Analysis")
    print("=" * 70)

    estimator = ResourceEstimator()
    circuit = create_application_circuit('simulation')

    distances = [3, 5, 7, 9, 11]

    print("\n" + "-" * 70)
    print(f"{'Distance':<12} {'Cost':<15} {'Error Rate':<15} {'ROI Score':<15}")
    print("-" * 70)

    baseline_cost = None
    baseline_error = None

    for distance in distances:
        config = {'type': 'surface', 'distance': distance, 'error_rate': 0.001}
        est = estimator.estimate_resources(circuit, config)

        # Calculate normalized cost
        cost = (est.physical_qubits / 100) + (est.time_to_solution_ms / 10)

        if baseline_cost is None:
            baseline_cost = cost
            baseline_error = est.error_rate

        # ROI: (error reduction) / (cost increase)
        error_reduction = baseline_error / est.error_rate
        cost_increase = cost / baseline_cost
        roi_score = error_reduction / cost_increase

        print(f"d={distance:<10} {cost:<15.2f} {est.error_rate:<15.2e} {roi_score:<15.2f}")

    print("-" * 70)
    print("\nInterpretation:")
    print("  • Higher ROI Score = Better error reduction per cost unit")
    print("  • ROI typically decreases with higher code distance")
    print("  • Optimal choice balances ROI with absolute error requirements")


def main():
    """Run all cost analysis examples"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "BioQL 5.0.0 - QEC Cost Analysis Examples" + " " * 12 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run analyses
    analyze_cost_breakdown()
    cost_vs_fidelity_analysis()
    application_specific_cost_analysis()
    budget_optimization()
    roi_analysis()

    print("\n" + "=" * 70)
    print("All cost analysis examples completed successfully!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • Higher code distance = Better fidelity but higher cost")
    print("  • Application type significantly affects resource needs")
    print("  • Budget constraints guide optimal QEC selection")
    print("  • ROI analysis helps find cost-effective configurations")
    print("\nVisualizations saved to 'output' directory.")


if __name__ == "__main__":
    main()
