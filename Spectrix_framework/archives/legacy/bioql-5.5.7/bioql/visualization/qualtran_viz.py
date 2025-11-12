"""
BioQL 5.0.0 - QEC Visualization Module

This module provides comprehensive visualization capabilities for quantum error
correction analysis, including resource estimation, overhead comparison, error
rate tracking, and cost analysis using matplotlib and plotly.
"""

import io
import base64
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..qec import SurfaceCodeQEC, SteaneCodeQEC, ShorCodeQEC


@dataclass
class ResourceEstimation:
    """Data class for resource estimation results"""
    physical_qubits: int
    logical_qubits: int
    magic_states: int
    t_gates: int
    circuit_depth: int
    time_to_solution_ms: float
    overhead_factor: float
    error_rate: float
    code_distance: int
    qec_type: str


class QECVisualizer:
    """
    Comprehensive QEC Visualization Engine

    Provides methods for visualizing quantum error correction overhead,
    resource requirements, error rates, and cost analysis.

    Features:
        - Resource estimation graphs
        - Physical vs logical qubit plots
        - Error rate visualizations
        - Cost analysis charts
        - QEC overhead comparison plots
        - Interactive HTML reports
        - Export to PNG/SVG

    Example:
        >>> viz = QECVisualizer()
        >>> fig = viz.plot_qubit_overhead([surface_qec, steane_qec, shor_qec])
        >>> viz.save_figure(fig, 'overhead_comparison.png')
    """

    def __init__(self, style: str = 'seaborn-v0_8-darkgrid', figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize QECVisualizer

        Args:
            style: Matplotlib style to use
            figsize: Default figure size (width, height)
        """
        self.style = style
        self.figsize = figsize
        self.colors = {
            'surface': '#1f77b4',
            'steane': '#ff7f0e',
            'shor': '#2ca02c',
            'error': '#d62728',
            'cost': '#9467bd',
            'physical': '#8c564b',
            'logical': '#e377c2'
        }

        # Set matplotlib style
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')

    def estimate_resources(
        self,
        circuit: Any,
        qec_config: Dict[str, Any]
    ) -> ResourceEstimation:
        """
        Estimate quantum resources for a circuit with QEC

        Args:
            circuit: Quantum circuit to analyze
            qec_config: QEC configuration dict with 'type', 'distance', 'error_rate'

        Returns:
            ResourceEstimation object with all resource metrics
        """
        qec_type = qec_config.get('type', 'surface')
        code_distance = qec_config.get('distance', 5)
        error_rate = qec_config.get('error_rate', 0.001)

        # Get logical qubit count from circuit
        logical_qubits = circuit.num_qubits if hasattr(circuit, 'num_qubits') else 10

        # Create appropriate QEC instance
        if qec_type == 'surface':
            qec = SurfaceCodeQEC(code_distance=code_distance, error_rate=error_rate)
        elif qec_type == 'steane':
            qec = SteaneCodeQEC(error_rate=error_rate)
        elif qec_type == 'shor':
            qec = ShorCodeQEC(error_rate=error_rate)
        else:
            qec = SurfaceCodeQEC(code_distance=code_distance, error_rate=error_rate)

        # Calculate overhead
        overhead = qec.calculate_overhead()
        physical_qubits = int(logical_qubits * overhead['qubit_overhead'])

        # Count T-gates (approximate from circuit depth)
        circuit_depth = getattr(circuit, 'depth', lambda: 100)()
        t_gates = int(circuit_depth * 0.15)  # Estimate ~15% T-gates

        # Estimate magic states (1 per T-gate)
        magic_states = t_gates

        # Calculate time to solution (in ms)
        gate_time_us = 0.1  # 100 ns per gate
        qec_overhead_factor = overhead['time_overhead']
        time_to_solution_ms = circuit_depth * gate_time_us * qec_overhead_factor / 1000

        return ResourceEstimation(
            physical_qubits=physical_qubits,
            logical_qubits=logical_qubits,
            magic_states=magic_states,
            t_gates=t_gates,
            circuit_depth=circuit_depth,
            time_to_solution_ms=time_to_solution_ms,
            overhead_factor=overhead['qubit_overhead'],
            error_rate=overhead['logical_error_rate'],
            code_distance=code_distance,
            qec_type=qec_type
        )

    def plot_qubit_overhead(
        self,
        qec_configs: List[Dict[str, Any]],
        logical_qubits_range: Optional[List[int]] = None
    ) -> Figure:
        """
        Plot physical vs logical qubit overhead for different QEC codes

        Args:
            qec_configs: List of QEC config dicts
            logical_qubits_range: Range of logical qubits to plot

        Returns:
            Matplotlib Figure object
        """
        if logical_qubits_range is None:
            logical_qubits_range = [5, 10, 20, 50, 100, 200, 500]

        fig, ax = plt.subplots(figsize=self.figsize)

        for config in qec_configs:
            qec_type = config.get('type', 'surface')
            code_distance = config.get('distance', 5)
            error_rate = config.get('error_rate', 0.001)

            # Create QEC instance
            if qec_type == 'surface':
                qec = SurfaceCodeQEC(code_distance=code_distance, error_rate=error_rate)
                label = f'Surface Code (d={code_distance})'
                color = self.colors['surface']
            elif qec_type == 'steane':
                qec = SteaneCodeQEC(error_rate=error_rate)
                label = 'Steane Code (7-qubit)'
                color = self.colors['steane']
            elif qec_type == 'shor':
                qec = ShorCodeQEC(error_rate=error_rate)
                label = 'Shor Code (9-qubit)'
                color = self.colors['shor']
            else:
                continue

            # Calculate physical qubits for each logical qubit count
            overhead = qec.calculate_overhead()
            overhead_factor = overhead['qubit_overhead']
            physical_qubits = [int(lq * overhead_factor) for lq in logical_qubits_range]

            ax.plot(logical_qubits_range, physical_qubits, marker='o',
                   linewidth=2, markersize=8, label=label, color=color)

        ax.set_xlabel('Logical Qubits', fontsize=12, fontweight='bold')
        ax.set_ylabel('Physical Qubits', fontsize=12, fontweight='bold')
        ax.set_title('QEC Overhead: Physical vs Logical Qubits',
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')
        ax.set_yscale('log')

        plt.tight_layout()
        return fig

    def plot_error_rates(
        self,
        results: List[Dict[str, Any]],
        show_threshold: bool = True
    ) -> Figure:
        """
        Plot error rates comparison for different QEC schemes

        Args:
            results: List of result dicts with 'qec_type', 'raw_error', 'corrected_error'
            show_threshold: Whether to show error correction threshold

        Returns:
            Matplotlib Figure object
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)

        qec_types = [r['qec_type'] for r in results]
        raw_errors = [r['raw_error'] for r in results]
        corrected_errors = [r['corrected_error'] for r in results]

        # Plot 1: Raw vs Corrected Error Rates
        x = np.arange(len(qec_types))
        width = 0.35

        bars1 = ax1.bar(x - width/2, raw_errors, width, label='Raw Error Rate',
                       color=self.colors['error'], alpha=0.8)
        bars2 = ax1.bar(x + width/2, corrected_errors, width,
                       label='Corrected Error Rate',
                       color=self.colors['surface'], alpha=0.8)

        ax1.set_xlabel('QEC Code', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Error Rate', fontsize=12, fontweight='bold')
        ax1.set_title('Raw vs Corrected Error Rates', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(qec_types)
        ax1.legend(fontsize=10)
        ax1.set_yscale('log')
        ax1.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2e}', ha='center', va='bottom', fontsize=8)

        # Plot 2: Error Suppression Factor
        suppression_factors = [raw / corr if corr > 0 else 0
                              for raw, corr in zip(raw_errors, corrected_errors)]

        bars3 = ax2.bar(qec_types, suppression_factors,
                       color=[self.colors['surface'], self.colors['steane'],
                             self.colors['shor']][:len(qec_types)],
                       alpha=0.8)

        ax2.set_xlabel('QEC Code', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Error Suppression Factor', fontsize=12, fontweight='bold')
        ax2.set_title('QEC Error Suppression Performance', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar in bars3:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}x', ha='center', va='bottom', fontsize=10)

        if show_threshold:
            ax1.axhline(y=0.01, color='r', linestyle='--', linewidth=2,
                       label='Typical Threshold', alpha=0.7)
            ax1.legend(fontsize=10)

        plt.tight_layout()
        return fig

    def plot_cost_breakdown(
        self,
        qec_config: Dict[str, Any],
        shots: int = 1000
    ) -> Figure:
        """
        Plot cost breakdown for QEC implementation

        Args:
            qec_config: QEC configuration dict
            shots: Number of circuit shots

        Returns:
            Matplotlib Figure object
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)

        qec_type = qec_config.get('type', 'surface')
        code_distance = qec_config.get('distance', 5)
        error_rate = qec_config.get('error_rate', 0.001)

        # Create QEC instance
        if qec_type == 'surface':
            qec = SurfaceCodeQEC(code_distance=code_distance, error_rate=error_rate)
        elif qec_type == 'steane':
            qec = SteaneCodeQEC(error_rate=error_rate)
        else:
            qec = ShorCodeQEC(error_rate=error_rate)

        overhead = qec.calculate_overhead()

        # Cost components (normalized)
        costs = {
            'Qubit Overhead': overhead['qubit_overhead'] * 10,
            'Time Overhead': overhead['time_overhead'] * 5,
            'Gate Overhead': overhead.get('gate_overhead', 1.5) * 15,
            'Measurement': shots * 0.01,
            'Error Syndrome': code_distance * 2
        }

        # Plot 1: Pie chart
        colors_pie = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc']
        explode = (0.1, 0, 0, 0, 0)

        ax1.pie(costs.values(), labels=costs.keys(), autopct='%1.1f%%',
               startangle=90, colors=colors_pie, explode=explode,
               textprops={'fontsize': 10})
        ax1.set_title(f'Cost Breakdown: {qec_type.title()} Code',
                     fontsize=14, fontweight='bold')

        # Plot 2: Bar chart with total cost
        bars = ax2.bar(costs.keys(), costs.values(),
                      color=colors_pie, alpha=0.8, edgecolor='black')

        ax2.set_xlabel('Cost Component', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Relative Cost', fontsize=12, fontweight='bold')
        ax2.set_title('Detailed Cost Analysis', fontsize=14, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=9)

        # Add total cost line
        total_cost = sum(costs.values())
        ax2.axhline(y=total_cost/len(costs), color='r', linestyle='--',
                   linewidth=2, label=f'Average: {total_cost/len(costs):.1f}')
        ax2.legend(fontsize=10)

        plt.tight_layout()
        return fig

    def plot_code_distance_scaling(
        self,
        qec_type: str = 'surface',
        distance_range: Optional[List[int]] = None,
        error_rate: float = 0.001
    ) -> Figure:
        """
        Plot how resources scale with code distance

        Args:
            qec_type: Type of QEC code ('surface', 'steane', 'shor')
            distance_range: List of code distances to plot
            error_rate: Physical error rate

        Returns:
            Matplotlib Figure object
        """
        if distance_range is None:
            distance_range = [3, 5, 7, 9, 11, 13, 15]

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        qubit_overheads = []
        time_overheads = []
        logical_errors = []

        for d in distance_range:
            if qec_type == 'surface':
                qec = SurfaceCodeQEC(code_distance=d, error_rate=error_rate)
            else:
                qec = SurfaceCodeQEC(code_distance=d, error_rate=error_rate)

            overhead = qec.calculate_overhead()
            qubit_overheads.append(overhead['qubit_overhead'])
            time_overheads.append(overhead['time_overhead'])
            logical_errors.append(overhead['logical_error_rate'])

        # Plot 1: Qubit overhead vs distance
        ax1.plot(distance_range, qubit_overheads, marker='o', linewidth=2,
                markersize=8, color=self.colors['surface'])
        ax1.set_xlabel('Code Distance', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Qubit Overhead Factor', fontsize=12, fontweight='bold')
        ax1.set_title('Qubit Overhead Scaling', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # Plot 2: Time overhead vs distance
        ax2.plot(distance_range, time_overheads, marker='s', linewidth=2,
                markersize=8, color=self.colors['steane'])
        ax2.set_xlabel('Code Distance', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Time Overhead Factor', fontsize=12, fontweight='bold')
        ax2.set_title('Time Overhead Scaling', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # Plot 3: Logical error rate vs distance
        ax3.semilogy(distance_range, logical_errors, marker='^', linewidth=2,
                    markersize=8, color=self.colors['error'])
        ax3.set_xlabel('Code Distance', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Logical Error Rate', fontsize=12, fontweight='bold')
        ax3.set_title('Error Rate Improvement', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Plot 4: Physical qubits for 100 logical qubits
        physical_qubits = [int(100 * qo) for qo in qubit_overheads]
        ax4.plot(distance_range, physical_qubits, marker='D', linewidth=2,
                markersize=8, color=self.colors['physical'])
        ax4.set_xlabel('Code Distance', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Physical Qubits (for 100 logical)', fontsize=12, fontweight='bold')
        ax4.set_title('Total Physical Qubits Required', fontsize=13, fontweight='bold')
        ax4.grid(True, alpha=0.3)

        fig.suptitle(f'{qec_type.title()} Code Scaling Analysis (p={error_rate})',
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        return fig

    def generate_qec_report(
        self,
        result: ResourceEstimation,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive HTML report with QEC analysis

        Args:
            result: ResourceEstimation object
            output_path: Optional path to save HTML file

        Returns:
            HTML string of the report
        """
        # Create summary statistics
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BioQL QEC Resource Estimation Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 40px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                    border-left: 4px solid #3498db;
                    padding-left: 10px;
                }}
                .metric {{
                    display: inline-block;
                    margin: 15px;
                    padding: 20px;
                    background-color: #ecf0f1;
                    border-radius: 8px;
                    min-width: 200px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                .metric-label {{
                    font-size: 14px;
                    color: #7f8c8d;
                    text-transform: uppercase;
                    font-weight: bold;
                }}
                .metric-value {{
                    font-size: 28px;
                    color: #2c3e50;
                    font-weight: bold;
                    margin-top: 5px;
                }}
                .highlight {{
                    background-color: #3498db;
                    color: white;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>BioQL 5.0.0 - QEC Resource Estimation Report</h1>

                <h2>Summary Metrics</h2>
                <div class="metric highlight">
                    <div class="metric-label">Physical Qubits</div>
                    <div class="metric-value">{result.physical_qubits:,}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Logical Qubits</div>
                    <div class="metric-value">{result.logical_qubits}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Overhead Factor</div>
                    <div class="metric-value">{result.overhead_factor:.1f}x</div>
                </div>
                <div class="metric">
                    <div class="metric-label">T-Gates</div>
                    <div class="metric-value">{result.t_gates:,}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Magic States</div>
                    <div class="metric-value">{result.magic_states:,}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Circuit Depth</div>
                    <div class="metric-value">{result.circuit_depth:,}</div>
                </div>

                <h2>QEC Configuration</h2>
                <table>
                    <tr>
                        <th>Parameter</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>QEC Type</td>
                        <td>{result.qec_type.title()}</td>
                    </tr>
                    <tr>
                        <td>Code Distance</td>
                        <td>{result.code_distance}</td>
                    </tr>
                    <tr>
                        <td>Logical Error Rate</td>
                        <td>{result.error_rate:.2e}</td>
                    </tr>
                    <tr>
                        <td>Time to Solution</td>
                        <td>{result.time_to_solution_ms:.2f} ms</td>
                    </tr>
                </table>

                <h2>Resource Breakdown</h2>
                <table>
                    <tr>
                        <th>Resource</th>
                        <th>Count</th>
                        <th>Percentage of Total</th>
                    </tr>
                    <tr>
                        <td>Physical Qubits</td>
                        <td>{result.physical_qubits:,}</td>
                        <td>100%</td>
                    </tr>
                    <tr>
                        <td>Data Qubits</td>
                        <td>{int(result.physical_qubits * 0.6):,}</td>
                        <td>60%</td>
                    </tr>
                    <tr>
                        <td>Ancilla Qubits</td>
                        <td>{int(result.physical_qubits * 0.4):,}</td>
                        <td>40%</td>
                    </tr>
                    <tr>
                        <td>T-Gate Magic States</td>
                        <td>{result.magic_states:,}</td>
                        <td>-</td>
                    </tr>
                </table>

                <div class="footer">
                    <p>Generated by BioQL 5.0.0 - Phase 1B: Qualtran Visualization & Resource Estimation</p>
                    <p>Report Date: {np.datetime64('today')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        if output_path:
            Path(output_path).write_text(html)

        return html

    def save_figure(
        self,
        fig: Figure,
        output_path: str,
        dpi: int = 300,
        format: str = 'png'
    ) -> None:
        """
        Save matplotlib figure to file

        Args:
            fig: Matplotlib Figure object
            output_path: Path to save file
            dpi: Dots per inch for raster formats
            format: Output format ('png', 'svg', 'pdf')
        """
        fig.savefig(output_path, dpi=dpi, format=format, bbox_inches='tight')
        print(f"Figure saved to: {output_path}")

    def create_interactive_plot(
        self,
        qec_configs: List[Dict[str, Any]],
        logical_qubits_range: Optional[List[int]] = None
    ) -> go.Figure:
        """
        Create interactive plotly visualization of QEC overhead

        Args:
            qec_configs: List of QEC configuration dicts
            logical_qubits_range: Range of logical qubits

        Returns:
            Plotly Figure object
        """
        if logical_qubits_range is None:
            logical_qubits_range = [5, 10, 20, 50, 100, 200, 500]

        fig = go.Figure()

        for config in qec_configs:
            qec_type = config.get('type', 'surface')
            code_distance = config.get('distance', 5)
            error_rate = config.get('error_rate', 0.001)

            # Create QEC instance
            if qec_type == 'surface':
                qec = SurfaceCodeQEC(code_distance=code_distance, error_rate=error_rate)
                name = f'Surface Code (d={code_distance})'
            elif qec_type == 'steane':
                qec = SteaneCodeQEC(error_rate=error_rate)
                name = 'Steane Code (7-qubit)'
            elif qec_type == 'shor':
                qec = ShorCodeQEC(error_rate=error_rate)
                name = 'Shor Code (9-qubit)'
            else:
                continue

            overhead = qec.calculate_overhead()
            physical_qubits = [int(lq * overhead['qubit_overhead'])
                             for lq in logical_qubits_range]

            fig.add_trace(go.Scatter(
                x=logical_qubits_range,
                y=physical_qubits,
                mode='lines+markers',
                name=name,
                hovertemplate='<b>%{fullData.name}</b><br>' +
                             'Logical Qubits: %{x}<br>' +
                             'Physical Qubits: %{y:,}<br>' +
                             f'Overhead: {overhead["qubit_overhead"]:.1f}x<br>' +
                             f'Error Rate: {overhead["logical_error_rate"]:.2e}<br>' +
                             '<extra></extra>'
            ))

        fig.update_layout(
            title='Interactive QEC Overhead Analysis',
            xaxis_title='Logical Qubits',
            yaxis_title='Physical Qubits',
            xaxis_type='log',
            yaxis_type='log',
            hovermode='closest',
            template='plotly_white',
            font=dict(size=12),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        return fig

    def export_interactive_html(
        self,
        fig: go.Figure,
        output_path: str
    ) -> None:
        """
        Export interactive plotly figure to HTML

        Args:
            fig: Plotly Figure object
            output_path: Path to save HTML file
        """
        fig.write_html(output_path)
        print(f"Interactive plot saved to: {output_path}")
