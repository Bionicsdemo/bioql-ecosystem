"""
BioQL Profiling Dashboard Generator

Creates interactive HTML dashboards for performance profiling and cost analysis.
Generates standalone, mobile-responsive HTML with embedded charts and analytics.
"""

import json
import html
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
from pathlib import Path


def escape_html(text: Any) -> str:
    """
    Escape HTML special characters to prevent XSS attacks.

    Args:
        text: Text to escape (will be converted to string if not already)

    Returns:
        HTML-safe escaped string
    """
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text, quote=True)


def sanitize_json(data: Any) -> str:
    """
    Safely serialize JSON for HTML embedding, preventing XSS.

    Args:
        data: Data to serialize

    Returns:
        JSON string safe for HTML embedding
    """
    json_str = json.dumps(data)
    # Escape < and > to prevent script injection
    return json_str.replace('<', '\\u003c').replace('>', '\\u003e')


class ProfilingDashboard:
    """
    Generates interactive HTML dashboards for BioQL profiling data.

    Features:
    - Interactive Plotly charts for performance visualization
    - Cost breakdown and projections
    - Bottleneck identification and heatmaps
    - Timeline analysis with zoom capabilities
    - Optimization recommendations
    - Dark/light theme toggle
    - Export capabilities
    """

    def __init__(self, theme: str = "light"):
        """
        Initialize the dashboard generator.

        Args:
            theme: Default theme ('light' or 'dark')
        """
        self.theme = theme
        self.plotly_version = "2.27.0"
        self.bootstrap_version = "5.3.2"

    def generate_html(self, profiler_context: Dict[str, Any]) -> str:
        """
        Generate complete standalone HTML dashboard.

        Args:
            profiler_context: Profiling data from BioQL profiler

        Returns:
            Complete HTML string with embedded CSS/JS
        """
        # Extract data
        performance_data = profiler_context.get("performance", {})
        cost_data = profiler_context.get("costs", {})
        circuit_data = profiler_context.get("circuit_metrics", {})
        stages = profiler_context.get("stages", {})
        metadata = profiler_context.get("metadata", {})

        # Generate components
        summary_html = self._create_performance_summary(
            performance_data, cost_data, circuit_data
        )
        timeline_chart = self._create_timeline_chart(stages)
        circuit_charts = self._create_circuit_metrics_charts(circuit_data)
        cost_charts = self._create_cost_breakdown(cost_data)
        bottleneck_viz = self._create_bottleneck_visualization(stages)
        recommendations = self._create_optimization_recommendations(
            profiler_context
        )
        comparison_table = self._create_comparison_table(profiler_context)

        # Embed raw JSON data (sanitized for XSS protection)
        raw_data = sanitize_json(profiler_context)
        raw_data_b64 = base64.b64encode(raw_data.encode()).decode()

        # Escape metadata for safe HTML embedding
        safe_timestamp = escape_html(metadata.get('timestamp', 'N/A'))

        # Build complete HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.plot.ly; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com;">
    <title>BioQL Profiling Dashboard - {safe_timestamp}</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@{self.bootstrap_version}/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Plotly JS -->
    <script src="https://cdn.plot.ly/plotly-{self.plotly_version}.min.js"></script>

    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        {self._get_css_styles()}
    </style>
</head>
<body data-theme="{self.theme}">
    <!-- Header -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="fas fa-chart-line me-2"></i>
                BioQL Profiling Dashboard
            </a>
            <div class="ms-auto d-flex gap-2">
                <button class="btn btn-outline-light btn-sm" onclick="toggleTheme()">
                    <i class="fas fa-moon"></i> Toggle Theme
                </button>
                <button class="btn btn-outline-light btn-sm" onclick="exportToPDF()">
                    <i class="fas fa-file-pdf"></i> Export PDF
                </button>
                <button class="btn btn-outline-light btn-sm" onclick="downloadJSON()">
                    <i class="fas fa-download"></i> Download JSON
                </button>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container-fluid py-4">
        <!-- Metadata Banner -->
        <div class="alert alert-info mb-4">
            <div class="row">
                <div class="col-md-3">
                    <strong>Query:</strong> {metadata.get('query', 'N/A')}
                </div>
                <div class="col-md-3">
                    <strong>Backend:</strong> {metadata.get('backend', 'N/A')}
                </div>
                <div class="col-md-3">
                    <strong>Timestamp:</strong> {metadata.get('timestamp', 'N/A')}
                </div>
                <div class="col-md-3">
                    <strong>Version:</strong> {metadata.get('version', 'N/A')}
                </div>
            </div>
        </div>

        <!-- Executive Summary -->
        <div id="summary-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-tachometer-alt"></i> Executive Summary
            </h2>
            {summary_html}
        </div>

        <!-- Timeline Chart -->
        <div id="timeline-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-clock"></i> Performance Timeline
            </h2>
            <div id="timeline-chart"></div>
        </div>

        <!-- Circuit Metrics -->
        <div id="circuit-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-project-diagram"></i> Circuit Metrics
            </h2>
            <div class="row">
                <div class="col-md-6">
                    <div id="circuit-depth-chart"></div>
                </div>
                <div class="col-md-6">
                    <div id="circuit-gates-chart"></div>
                </div>
            </div>
        </div>

        <!-- Cost Analysis -->
        <div id="cost-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-dollar-sign"></i> Cost Analysis
            </h2>
            <div class="row">
                <div class="col-md-6">
                    <div id="cost-breakdown-chart"></div>
                </div>
                <div class="col-md-6">
                    <div id="cost-projection-chart"></div>
                </div>
            </div>
        </div>

        <!-- Bottleneck Analysis -->
        <div id="bottleneck-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-fire"></i> Bottleneck Heatmap
            </h2>
            <div id="bottleneck-heatmap"></div>
        </div>

        <!-- Optimization Recommendations -->
        <div id="recommendations-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-lightbulb"></i> Optimization Recommendations
            </h2>
            {recommendations}
        </div>

        <!-- Comparison Table -->
        <div id="comparison-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-table"></i> Stage Comparison
            </h2>
            {comparison_table}
        </div>

        <!-- Raw Data Section (Collapsible) -->
        <div id="raw-data-section" class="section-container">
            <h2 class="section-title">
                <i class="fas fa-code"></i> Raw Data
                <button class="btn btn-sm btn-outline-secondary float-end" onclick="toggleRawData()">
                    <i class="fas fa-chevron-down"></i> Toggle
                </button>
            </h2>
            <div id="raw-data-content" class="collapse">
                <pre class="raw-data-pre"><code>{raw_data}</code></pre>
            </div>
        </div>
    </div>

    <!-- Hidden data for export -->
    <div id="raw-data-json" style="display:none">{raw_data_b64}</div>

    <script>
        {self._get_javascript(timeline_chart, circuit_charts, cost_charts, bottleneck_viz)}
    </script>
</body>
</html>"""

        return html

    def _create_performance_summary(
        self,
        performance: Dict[str, Any],
        costs: Dict[str, Any],
        circuit: Dict[str, Any]
    ) -> str:
        """Create executive summary cards."""
        total_time = performance.get("total_time", 0)
        total_cost = costs.get("total_cost", 0)
        circuit_depth = circuit.get("depth", 0)
        num_qubits = circuit.get("num_qubits", 0)
        num_gates = circuit.get("num_gates", 0)

        # Determine bottleneck
        stages_time = performance.get("stages", {})
        bottleneck = "N/A"
        if stages_time:
            bottleneck = max(stages_time.items(), key=lambda x: x[1])[0]

        return f"""
        <div class="row g-4">
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-icon bg-primary">
                        <i class="fas fa-stopwatch"></i>
                    </div>
                    <div class="metric-content">
                        <h6>Total Execution Time</h6>
                        <h3>{total_time:.3f}s</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-icon bg-success">
                        <i class="fas fa-dollar-sign"></i>
                    </div>
                    <div class="metric-content">
                        <h6>Total Cost</h6>
                        <h3>${total_cost:.4f}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-icon bg-info">
                        <i class="fas fa-layer-group"></i>
                    </div>
                    <div class="metric-content">
                        <h6>Circuit Depth</h6>
                        <h3>{circuit_depth}</h3>
                        <small>{num_qubits} qubits, {num_gates} gates</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-icon bg-warning">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="metric-content">
                        <h6>Primary Bottleneck</h6>
                        <h3>{bottleneck}</h3>
                    </div>
                </div>
            </div>
        </div>
        """

    def _create_timeline_chart(self, stages: Dict[str, Any]) -> str:
        """Create interactive timeline chart data."""
        if not stages:
            return "null"

        stage_names = list(stages.keys())
        stage_times = [stages[name].get("duration", 0) for name in stage_names]
        stage_percentages = []
        total = sum(stage_times)
        if total > 0:
            stage_percentages = [(t / total) * 100 for t in stage_times]
        else:
            stage_percentages = [0] * len(stage_times)

        chart_data = {
            "data": [{
                "type": "bar",
                "x": stage_names,
                "y": stage_times,
                "text": [f"{p:.1f}%" for p in stage_percentages],
                "textposition": "auto",
                "hovertemplate": "<b>%{x}</b><br>Time: %{y:.3f}s<br>Percentage: %{text}<extra></extra>",
                "marker": {
                    "color": stage_times,
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "Time (s)"}
                }
            }],
            "layout": {
                "title": "Stage Execution Timeline",
                "xaxis": {"title": "Stage"},
                "yaxis": {"title": "Time (seconds)"},
                "hovermode": "closest",
                "height": 400
            }
        }

        return json.dumps(chart_data)

    def _create_circuit_metrics_charts(self, circuit: Dict[str, Any]) -> Dict[str, str]:
        """Create circuit metrics visualizations."""
        if not circuit:
            return {"depth": "null", "gates": "null"}

        # Depth chart (gauge)
        depth = circuit.get("depth", 0)
        max_depth = max(depth * 1.5, 100)  # Set reasonable max

        depth_chart = {
            "data": [{
                "type": "indicator",
                "mode": "gauge+number+delta",
                "value": depth,
                "title": {"text": "Circuit Depth"},
                "gauge": {
                    "axis": {"range": [0, max_depth]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, max_depth * 0.33], "color": "lightgreen"},
                        {"range": [max_depth * 0.33, max_depth * 0.66], "color": "yellow"},
                        {"range": [max_depth * 0.66, max_depth], "color": "lightcoral"}
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": max_depth * 0.8
                    }
                }
            }],
            "layout": {"height": 350}
        }

        # Gates breakdown (pie chart)
        gate_counts = circuit.get("gate_counts", {})
        if gate_counts:
            gates_chart = {
                "data": [{
                    "type": "pie",
                    "labels": list(gate_counts.keys()),
                    "values": list(gate_counts.values()),
                    "textinfo": "label+percent",
                    "hovertemplate": "<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
                }],
                "layout": {
                    "title": "Gate Distribution",
                    "height": 350
                }
            }
        else:
            # Fallback if no gate counts
            num_gates = circuit.get("num_gates", 0)
            gates_chart = {
                "data": [{
                    "type": "pie",
                    "labels": ["Total Gates"],
                    "values": [num_gates],
                    "textinfo": "label+value"
                }],
                "layout": {
                    "title": "Gate Distribution",
                    "height": 350
                }
            }

        return {
            "depth": json.dumps(depth_chart),
            "gates": json.dumps(gates_chart)
        }

    def _create_cost_breakdown(self, costs: Dict[str, Any]) -> Dict[str, str]:
        """Create cost analysis visualizations."""
        if not costs:
            return {"breakdown": "null", "projection": "null"}

        # Cost breakdown by category
        cost_categories = costs.get("breakdown", {})
        if cost_categories:
            breakdown_chart = {
                "data": [{
                    "type": "pie",
                    "labels": list(cost_categories.keys()),
                    "values": list(cost_categories.values()),
                    "textinfo": "label+percent",
                    "hovertemplate": "<b>%{label}</b><br>Cost: $%{value:.4f}<br>Percentage: %{percent}<extra></extra>",
                    "marker": {
                        "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]
                    }
                }],
                "layout": {
                    "title": "Cost Breakdown by Category",
                    "height": 350
                }
            }
        else:
            total_cost = costs.get("total_cost", 0)
            breakdown_chart = {
                "data": [{
                    "type": "pie",
                    "labels": ["Total Cost"],
                    "values": [total_cost],
                    "textinfo": "label+value"
                }],
                "layout": {
                    "title": "Total Cost",
                    "height": 350
                }
            }

        # Cost projections (bar chart for different scales)
        total_cost = costs.get("total_cost", 0)
        projections = {
            "Current": total_cost,
            "10x Scale": total_cost * 10,
            "100x Scale": total_cost * 100,
            "1000x Scale": total_cost * 1000
        }

        projection_chart = {
            "data": [{
                "type": "bar",
                "x": list(projections.keys()),
                "y": list(projections.values()),
                "text": [f"${v:.4f}" for v in projections.values()],
                "textposition": "auto",
                "marker": {
                    "color": ["#4ECDC4", "#45B7D1", "#FFA07A", "#FF6B6B"]
                }
            }],
            "layout": {
                "title": "Cost Projections at Scale",
                "yaxis": {
                    "title": "Cost ($)",
                    "type": "log"
                },
                "height": 350
            }
        }

        return {
            "breakdown": json.dumps(breakdown_chart),
            "projection": json.dumps(projection_chart)
        }

    def _create_bottleneck_visualization(self, stages: Dict[str, Any]) -> str:
        """Create bottleneck heatmap."""
        if not stages:
            return "null"

        stage_names = list(stages.keys())
        stage_times = [stages[name].get("duration", 0) for name in stage_names]

        # Create heatmap data
        total_time = sum(stage_times)
        stage_percentages = [(t / total_time) * 100 if total_time > 0 else 0
                            for t in stage_times]

        # Sort by time (descending)
        sorted_data = sorted(
            zip(stage_names, stage_times, stage_percentages),
            key=lambda x: x[1],
            reverse=True
        )

        names, times, percentages = zip(*sorted_data) if sorted_data else ([], [], [])

        heatmap_chart = {
            "data": [{
                "type": "heatmap",
                "x": ["Time Consumption"],
                "y": list(names),
                "z": [[t] for t in times],
                "colorscale": "RdYlGn_r",
                "hovertemplate": "<b>%{y}</b><br>Time: %{z:.3f}s<extra></extra>",
                "showscale": True,
                "colorbar": {"title": "Time (s)"}
            }],
            "layout": {
                "title": "Stage Performance Heatmap (Sorted by Time)",
                "height": max(400, len(names) * 40),
                "yaxis": {"tickmode": "linear"}
            }
        }

        return json.dumps(heatmap_chart)

    def _create_optimization_recommendations(
        self,
        profiler_context: Dict[str, Any]
    ) -> str:
        """Generate optimization recommendations based on profiling data."""
        recommendations = []

        # Analyze stages
        stages = profiler_context.get("stages", {})
        if stages:
            stage_times = {name: data.get("duration", 0)
                          for name, data in stages.items()}
            total_time = sum(stage_times.values())

            # Find slowest stage
            if total_time > 0:
                slowest_stage = max(stage_times.items(), key=lambda x: x[1])
                if slowest_stage[1] / total_time > 0.5:
                    recommendations.append({
                        "severity": "high",
                        "title": f"Bottleneck: {slowest_stage[0]}",
                        "description": f"Stage '{slowest_stage[0]}' consumes {(slowest_stage[1]/total_time)*100:.1f}% of total execution time.",
                        "suggestion": "Consider optimizing this stage with caching, parallelization, or algorithm improvements."
                    })

        # Analyze circuit metrics
        circuit = profiler_context.get("circuit_metrics", {})
        if circuit:
            depth = circuit.get("depth", 0)
            num_gates = circuit.get("num_gates", 0)

            if depth > 100:
                recommendations.append({
                    "severity": "medium",
                    "title": "High Circuit Depth",
                    "description": f"Circuit depth of {depth} may lead to increased noise and errors.",
                    "suggestion": "Consider circuit optimization techniques like gate synthesis or decomposition strategies."
                })

            if num_gates > 1000:
                recommendations.append({
                    "severity": "medium",
                    "title": "Large Gate Count",
                    "description": f"Circuit contains {num_gates} gates, which may be expensive to execute.",
                    "suggestion": "Explore gate reduction techniques or consider approximate methods."
                })

        # Analyze costs
        costs = profiler_context.get("costs", {})
        if costs:
            total_cost = costs.get("total_cost", 0)

            if total_cost > 1.0:
                recommendations.append({
                    "severity": "high",
                    "title": "High Execution Cost",
                    "description": f"Total cost of ${total_cost:.4f} is significant.",
                    "suggestion": "Consider using simulators for development, or optimize circuit before running on hardware."
                })
            elif total_cost > 0.1:
                recommendations.append({
                    "severity": "low",
                    "title": "Moderate Cost",
                    "description": f"Cost of ${total_cost:.4f} is reasonable but could be optimized.",
                    "suggestion": "Monitor costs at scale and consider budget limits."
                })

        # Default recommendation if none found
        if not recommendations:
            recommendations.append({
                "severity": "success",
                "title": "Performance Looks Good",
                "description": "No major bottlenecks or issues detected.",
                "suggestion": "Continue monitoring performance as workload scales."
            })

        # Generate HTML
        html_parts = []
        severity_colors = {
            "high": "danger",
            "medium": "warning",
            "low": "info",
            "success": "success"
        }
        severity_icons = {
            "high": "exclamation-circle",
            "medium": "exclamation-triangle",
            "low": "info-circle",
            "success": "check-circle"
        }

        for rec in recommendations:
            severity = rec.get("severity", "info")
            color = severity_colors.get(severity, "secondary")
            icon = severity_icons.get(severity, "info-circle")

            html_parts.append(f"""
            <div class="alert alert-{color} recommendation-card">
                <h5>
                    <i class="fas fa-{icon}"></i> {rec['title']}
                </h5>
                <p><strong>Issue:</strong> {rec['description']}</p>
                <p><strong>Recommendation:</strong> {rec['suggestion']}</p>
            </div>
            """)

        return "\n".join(html_parts)

    def _create_comparison_table(self, profiler_context: Dict[str, Any]) -> str:
        """Create detailed comparison table of all stages."""
        stages = profiler_context.get("stages", {})
        if not stages:
            return "<p class='text-muted'>No stage data available.</p>"

        # Calculate totals
        total_time = sum(data.get("duration", 0) for data in stages.values())
        total_cost = sum(data.get("cost", 0) for data in stages.values())

        # Build table rows
        rows = []
        for stage_name, stage_data in sorted(
            stages.items(),
            key=lambda x: x[1].get("duration", 0),
            reverse=True
        ):
            duration = stage_data.get("duration", 0)
            cost = stage_data.get("cost", 0)
            percentage = (duration / total_time * 100) if total_time > 0 else 0

            # Get additional metrics if available
            memory = stage_data.get("memory_mb", "N/A")
            status = stage_data.get("status", "completed")

            status_badge = f"""
            <span class="badge bg-{'success' if status == 'completed' else 'warning'}">
                {status}
            </span>
            """

            rows.append(f"""
            <tr>
                <td><strong>{stage_name}</strong></td>
                <td>{duration:.3f}s</td>
                <td>
                    <div class="progress">
                        <div class="progress-bar" role="progressbar"
                             style="width: {percentage}%"
                             aria-valuenow="{percentage}"
                             aria-valuemin="0"
                             aria-valuemax="100">
                            {percentage:.1f}%
                        </div>
                    </div>
                </td>
                <td>${cost:.4f}</td>
                <td>{memory if isinstance(memory, str) else f"{memory:.2f} MB"}</td>
                <td>{status_badge}</td>
            </tr>
            """)

        return f"""
        <div class="table-responsive">
            <table class="table table-hover table-striped">
                <thead class="table-dark">
                    <tr>
                        <th>Stage</th>
                        <th>Duration</th>
                        <th>% of Total</th>
                        <th>Cost</th>
                        <th>Memory</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
                <tfoot class="table-secondary">
                    <tr>
                        <td><strong>TOTAL</strong></td>
                        <td><strong>{total_time:.3f}s</strong></td>
                        <td><strong>100%</strong></td>
                        <td><strong>${total_cost:.4f}</strong></td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

    def _get_css_styles(self) -> str:
        """Get embedded CSS styles."""
        return """
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --border-color: #dee2e6;
            --shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        [data-theme="dark"] {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --text-primary: #f8f9fa;
            --text-secondary: #adb5bd;
            --border-color: #495057;
            --shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        body {
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        .section-container {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
            border: 1px solid var(--border-color);
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
            border-bottom: 2px solid #0d6efd;
            padding-bottom: 0.5rem;
        }

        .metric-card {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            gap: 1rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .metric-icon {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
        }

        .metric-content h6 {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-content h3 {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0;
            color: var(--text-primary);
        }

        .metric-content small {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .recommendation-card {
            border-left: 4px solid;
            margin-bottom: 1rem;
        }

        .recommendation-card h5 {
            margin-bottom: 1rem;
        }

        .recommendation-card p {
            margin-bottom: 0.5rem;
        }

        .raw-data-pre {
            background: #282c34;
            color: #abb2bf;
            padding: 1rem;
            border-radius: 4px;
            max-height: 500px;
            overflow: auto;
        }

        [data-theme="dark"] .table {
            color: var(--text-primary);
        }

        [data-theme="dark"] .table-striped tbody tr:nth-of-type(odd) {
            background-color: rgba(255,255,255,0.05);
        }

        [data-theme="dark"] .alert {
            background-color: var(--bg-secondary);
            border-color: var(--border-color);
            color: var(--text-primary);
        }

        .navbar-brand {
            font-weight: 600;
            font-size: 1.25rem;
        }

        @media print {
            .navbar, button {
                display: none !important;
            }

            .section-container {
                page-break-inside: avoid;
            }
        }

        @media (max-width: 768px) {
            .section-container {
                padding: 1rem;
            }

            .metric-card {
                flex-direction: column;
                text-align: center;
            }
        }
        """

    def _get_javascript(
        self,
        timeline_data: str,
        circuit_charts: Dict[str, str],
        cost_charts: Dict[str, str],
        bottleneck_data: str
    ) -> str:
        """Get embedded JavaScript."""
        return f"""
        // Chart data
        const timelineData = {timeline_data};
        const circuitDepthData = {circuit_charts.get('depth', 'null')};
        const circuitGatesData = {circuit_charts.get('gates', 'null')};
        const costBreakdownData = {cost_charts.get('breakdown', 'null')};
        const costProjectionData = {cost_charts.get('projection', 'null')};
        const bottleneckData = {bottleneck_data};

        // Theme configuration
        const lightLayout = {{
            paper_bgcolor: 'white',
            plot_bgcolor: 'white',
            font: {{ color: '#212529' }}
        }};

        const darkLayout = {{
            paper_bgcolor: '#1a1a1a',
            plot_bgcolor: '#2d2d2d',
            font: {{ color: '#f8f9fa' }},
            xaxis: {{ gridcolor: '#495057' }},
            yaxis: {{ gridcolor: '#495057' }}
        }};

        // Apply theme to chart
        function applyTheme(data, baseLayout) {{
            const theme = document.body.getAttribute('data-theme');
            const layout = theme === 'dark' ?
                {{ ...baseLayout, ...darkLayout }} :
                {{ ...baseLayout, ...lightLayout }};
            return layout;
        }}

        // Render charts
        function renderCharts() {{
            const config = {{ responsive: true, displayModeBar: true }};

            if (timelineData) {{
                const layout = applyTheme(timelineData.data, timelineData.layout);
                Plotly.newPlot('timeline-chart', timelineData.data, layout, config);
            }}

            if (circuitDepthData) {{
                const layout = applyTheme(circuitDepthData.data, circuitDepthData.layout);
                Plotly.newPlot('circuit-depth-chart', circuitDepthData.data, layout, config);
            }}

            if (circuitGatesData) {{
                const layout = applyTheme(circuitGatesData.data, circuitGatesData.layout);
                Plotly.newPlot('circuit-gates-chart', circuitGatesData.data, layout, config);
            }}

            if (costBreakdownData) {{
                const layout = applyTheme(costBreakdownData.data, costBreakdownData.layout);
                Plotly.newPlot('cost-breakdown-chart', costBreakdownData.data, layout, config);
            }}

            if (costProjectionData) {{
                const layout = applyTheme(costProjectionData.data, costProjectionData.layout);
                Plotly.newPlot('cost-projection-chart', costProjectionData.data, layout, config);
            }}

            if (bottleneckData) {{
                const layout = applyTheme(bottleneckData.data, bottleneckData.layout);
                Plotly.newPlot('bottleneck-heatmap', bottleneckData.data, layout, config);
            }}
        }}

        // Theme toggle
        function toggleTheme() {{
            const currentTheme = document.body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', newTheme);
            renderCharts();
        }}

        // Raw data toggle
        function toggleRawData() {{
            const content = document.getElementById('raw-data-content');
            if (content.classList.contains('show')) {{
                content.classList.remove('show');
            }} else {{
                content.classList.add('show');
            }}
        }}

        // Download JSON
        function downloadJSON() {{
            const data = document.getElementById('raw-data-json').textContent;
            const decoded = atob(data);
            const blob = new Blob([decoded], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'bioql-profiling-' + new Date().toISOString() + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        // Export to PDF (using browser print)
        function exportToPDF() {{
            window.print();
        }}

        // Initialize on load
        document.addEventListener('DOMContentLoaded', function() {{
            renderCharts();
        }});

        // Re-render on window resize
        window.addEventListener('resize', function() {{
            renderCharts();
        }});
        """

    def save_dashboard(
        self,
        profiler_context: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Generate and save dashboard to file.

        Args:
            profiler_context: Profiling data
            output_path: Path to save HTML file

        Returns:
            Absolute path to saved file
        """
        html_content = self.generate_html(profiler_context)

        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_path)


def create_interactive_charts(profiler_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to create all interactive charts.

    Args:
        profiler_context: Profiling data

    Returns:
        Dictionary of chart configurations
    """
    dashboard = ProfilingDashboard()

    stages = profiler_context.get("stages", {})
    circuit = profiler_context.get("circuit_metrics", {})
    costs = profiler_context.get("costs", {})

    charts = {
        "timeline": dashboard._create_timeline_chart(stages),
        "circuit": dashboard._create_circuit_metrics_charts(circuit),
        "costs": dashboard._create_cost_breakdown(costs),
        "bottleneck": dashboard._create_bottleneck_visualization(stages)
    }

    return charts


# Example usage
if __name__ == "__main__":
    # Sample profiler data for testing
    sample_data = {
        "metadata": {
            "query": "docking ligand.pdb to protein.pdb",
            "backend": "qiskit_aer",
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0"
        },
        "performance": {
            "total_time": 45.234,
            "stages": {
                "parsing": 0.123,
                "compilation": 2.456,
                "optimization": 15.234,
                "execution": 25.123,
                "post_processing": 2.298
            }
        },
        "costs": {
            "total_cost": 0.0234,
            "breakdown": {
                "compilation": 0.001,
                "execution": 0.020,
                "storage": 0.0024
            }
        },
        "circuit_metrics": {
            "depth": 145,
            "num_qubits": 12,
            "num_gates": 456,
            "gate_counts": {
                "CNOT": 120,
                "H": 45,
                "RZ": 234,
                "RX": 57
            }
        },
        "stages": {
            "parsing": {"duration": 0.123, "cost": 0.0001, "memory_mb": 12.3, "status": "completed"},
            "compilation": {"duration": 2.456, "cost": 0.001, "memory_mb": 45.6, "status": "completed"},
            "optimization": {"duration": 15.234, "cost": 0.002, "memory_mb": 123.4, "status": "completed"},
            "execution": {"duration": 25.123, "cost": 0.020, "memory_mb": 234.5, "status": "completed"},
            "post_processing": {"duration": 2.298, "cost": 0.0003, "memory_mb": 34.2, "status": "completed"}
        }
    }

    # Generate dashboard
    dashboard = ProfilingDashboard(theme="light")
    html_output = dashboard.generate_html(sample_data)

    # Save to file
    output_file = dashboard.save_dashboard(
        sample_data,
        "bioql_profiling_dashboard.html"
    )
    print(f"Dashboard saved to: {output_file}")
