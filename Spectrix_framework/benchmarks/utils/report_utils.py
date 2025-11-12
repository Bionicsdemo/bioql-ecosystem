# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Report generation utilities for benchmark results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def generate_json_report(results: Dict[str, Any], output_path: Path) -> None:
    """
    Generate a JSON report from benchmark results.

    Args:
        results: Dictionary containing benchmark results
        output_path: Path to output JSON file

    Raises:
        IOError: If file cannot be written
    """
    try:
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata
        report = {
            "metadata": {"timestamp": datetime.now().isoformat(), "version": "1.0"},
            "results": results,
        }

        # Write JSON with pretty formatting
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

    except Exception as e:
        raise IOError(f"Failed to write JSON report: {e}")


def generate_html_report(results: Dict[str, Any], output_path: Path) -> None:
    """
    Generate an HTML report from benchmark results using Jinja2.

    Args:
        results: Dictionary containing benchmark results
        output_path: Path to output HTML file

    Raises:
        ImportError: If Jinja2 is not installed
        IOError: If file cannot be written
    """
    try:
        from jinja2 import Template
    except ImportError:
        raise ImportError(
            "Jinja2 is required for HTML report generation. Install with: pip install jinja2"
        )

    # HTML template
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benchmark Results Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 2px solid #ecf0f1;
        }

        h3 {
            color: #7f8c8d;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .metadata {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }

        .metadata p {
            margin: 5px 0;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .summary-card {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }

        .summary-card h3 {
            margin-top: 0;
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
        }

        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }

        .pass {
            color: #27ae60;
        }

        .fail {
            color: #e74c3c;
        }

        .warning {
            color: #f39c12;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        th {
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }

        tr:hover {
            background-color: #f5f5f5;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .badge-success {
            background-color: #d4edda;
            color: #155724;
        }

        .badge-danger {
            background-color: #f8d7da;
            color: #721c24;
        }

        .badge-warning {
            background-color: #fff3cd;
            color: #856404;
        }

        .badge-info {
            background-color: #d1ecf1;
            color: #0c5460;
        }

        .molecule-details {
            background-color: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 3px solid #95a5a6;
        }

        .property-list {
            list-style: none;
            padding: 0;
        }

        .property-list li {
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }

        .property-list li:last-child {
            border-bottom: none;
        }

        .property-name {
            font-weight: 600;
            color: #7f8c8d;
            display: inline-block;
            min-width: 200px;
        }

        .property-value {
            color: #2c3e50;
        }

        .alert {
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }

        .alert-info {
            background-color: #d1ecf1;
            border-color: #0c5460;
            color: #0c5460;
        }

        .alert-warning {
            background-color: #fff3cd;
            border-color: #856404;
            color: #856404;
        }

        .alert-danger {
            background-color: #f8d7da;
            border-color: #721c24;
            color: #721c24;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Benchmark Results Report</h1>

        <div class="metadata">
            <p><strong>Generated:</strong> {{ timestamp }}</p>
            {% if results.metadata %}
            <p><strong>Benchmark:</strong> {{ results.metadata.get('benchmark_name', 'N/A') }}</p>
            <p><strong>PDB ID:</strong> {{ results.metadata.get('pdb_id', 'N/A') }}</p>
            {% endif %}
        </div>

        {% if summary %}
        <h2>Summary</h2>
        <div class="summary">
            {% if summary.total_molecules is defined %}
            <div class="summary-card">
                <h3>Total Molecules</h3>
                <div class="value">{{ summary.total_molecules }}</div>
            </div>
            {% endif %}

            {% if summary.passed is defined %}
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value pass">{{ summary.passed }}</div>
            </div>
            {% endif %}

            {% if summary.failed is defined %}
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value fail">{{ summary.failed }}</div>
            </div>
            {% endif %}

            {% if summary.success_rate is defined %}
            <div class="summary-card">
                <h3>Success Rate</h3>
                <div class="value">{{ "%.1f"|format(summary.success_rate) }}%</div>
            </div>
            {% endif %}

            {% if summary.avg_affinity is defined %}
            <div class="summary-card">
                <h3>Avg Affinity</h3>
                <div class="value">{{ "%.2f"|format(summary.avg_affinity) }} kcal/mol</div>
            </div>
            {% endif %}

            {% if summary.avg_rmsd is defined %}
            <div class="summary-card">
                <h3>Avg RMSD</h3>
                <div class="value">{{ "%.2f"|format(summary.avg_rmsd) }} Å</div>
            </div>
            {% endif %}
        </div>
        {% endif %}

        {% if results.molecules %}
        <h2>Molecule Results</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>SMILES</th>
                    <th>Status</th>
                    <th>Affinity (kcal/mol)</th>
                    <th>RMSD (Å)</th>
                    <th>Lipinski</th>
                    <th>Alerts</th>
                </tr>
            </thead>
            <tbody>
                {% for mol in results.molecules %}
                <tr>
                    <td>{{ mol.id or loop.index }}</td>
                    <td style="font-family: monospace; font-size: 0.85em;">{{ mol.smiles[:50] }}{% if mol.smiles|length > 50 %}...{% endif %}</td>
                    <td>
                        {% if mol.success %}
                        <span class="badge badge-success">Success</span>
                        {% else %}
                        <span class="badge badge-danger">Failed</span>
                        {% endif %}
                    </td>
                    <td>{{ "%.2f"|format(mol.affinity) if mol.affinity is not none else 'N/A' }}</td>
                    <td>{{ "%.2f"|format(mol.rmsd) if mol.rmsd is not none else 'N/A' }}</td>
                    <td>
                        {% if mol.lipinski and mol.lipinski.passes %}
                        <span class="badge badge-success">Pass</span>
                        {% elif mol.lipinski %}
                        <span class="badge badge-warning">{{ mol.lipinski.violations }} violations</span>
                        {% else %}
                        <span class="badge badge-info">N/A</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if mol.pains_alerts or mol.brenk_alerts or mol.reactive_groups %}
                        <span class="badge badge-warning">{{ (mol.pains_alerts|length or 0) + (mol.brenk_alerts|length or 0) + (mol.reactive_groups|length or 0) }}</span>
                        {% else %}
                        <span class="badge badge-success">None</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if results.criteria %}
        <h2>Pass/Fail Criteria</h2>
        <div class="molecule-details">
            <ul class="property-list">
                {% for key, value in results.criteria.items() %}
                <li>
                    <span class="property-name">{{ key.replace('_', ' ').title() }}:</span>
                    <span class="property-value">
                        {% if value is sameas true %}
                        <span class="pass">✓ Pass</span>
                        {% elif value is sameas false %}
                        <span class="fail">✗ Fail</span>
                        {% else %}
                        {{ value }}
                        {% endif %}
                    </span>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        {% if results.errors %}
        <h2>Errors & Warnings</h2>
        {% for error in results.errors %}
        <div class="alert alert-danger">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endfor %}
        {% endif %}

        <div class="footer">
            <p>Generated by Benchmark Suite v1.0</p>
        </div>
    </div>
</body>
</html>
    """

    try:
        # Create template
        template = Template(html_template)

        # Prepare data for template
        context = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
            "summary": results.get("summary", {}),
        }

        # Render HTML
        html_content = template.render(**context)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write HTML file
        with open(output_path, "w") as f:
            f.write(html_content)

    except Exception as e:
        raise IOError(f"Failed to write HTML report: {e}")


def calculate_pass_fail_criteria(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate pass/fail criteria from benchmark results.

    Evaluates:
    - Overall success rate
    - Lipinski compliance rate
    - PAINS/Brenk alert rate
    - Affinity distribution
    - RMSD distribution

    Args:
        results: Dictionary containing benchmark results with 'molecules' key

    Returns:
        Dictionary with pass/fail criteria and statistics
    """
    if "molecules" not in results or not results["molecules"]:
        return {
            "total_molecules": 0,
            "passed": 0,
            "failed": 0,
            "success_rate": 0.0,
            "overall_pass": False,
            "criteria_met": {},
        }

    molecules = results["molecules"]
    total = len(molecules)

    # Count successes
    successful = [m for m in molecules if m.get("success", False)]
    num_successful = len(successful)
    success_rate = (num_successful / total * 100) if total > 0 else 0.0

    # Lipinski compliance
    lipinski_compliant = [m for m in molecules if m.get("lipinski", {}).get("passes", False)]
    lipinski_rate = (len(lipinski_compliant) / total * 100) if total > 0 else 0.0

    # PAINS/Brenk alerts
    molecules_with_alerts = [
        m
        for m in molecules
        if (m.get("pains_alerts") and len(m["pains_alerts"]) > 0)
        or (m.get("brenk_alerts") and len(m["brenk_alerts"]) > 0)
    ]
    alert_rate = (len(molecules_with_alerts) / total * 100) if total > 0 else 0.0

    # Reactive groups
    molecules_with_reactive = [
        m for m in molecules if m.get("reactive_groups") and len(m["reactive_groups"]) > 0
    ]
    reactive_rate = (len(molecules_with_reactive) / total * 100) if total > 0 else 0.0

    # Affinity statistics
    affinities = [m.get("affinity") for m in successful if m.get("affinity") is not None]
    if affinities:
        avg_affinity = sum(affinities) / len(affinities)
        min_affinity = min(affinities)
        max_affinity = max(affinities)
        strong_binders = [a for a in affinities if a < -7.0]  # < -7 kcal/mol
    else:
        avg_affinity = None
        min_affinity = None
        max_affinity = None
        strong_binders = []

    # RMSD statistics
    rmsds = [m.get("rmsd") for m in successful if m.get("rmsd") is not None]
    if rmsds:
        avg_rmsd = sum(rmsds) / len(rmsds)
        good_rmsd = [r for r in rmsds if r < 2.0]  # < 2.0 Å considered good
    else:
        avg_rmsd = None
        good_rmsd = []

    # Define pass/fail criteria
    criteria_met = {
        "success_rate_above_80": success_rate >= 80.0,
        "lipinski_compliance_above_70": lipinski_rate >= 70.0,
        "alert_rate_below_30": alert_rate < 30.0,
        "reactive_rate_below_20": reactive_rate < 20.0,
    }

    if affinities:
        criteria_met["avg_affinity_below_minus_6"] = avg_affinity < -6.0
        criteria_met["strong_binders_above_50_percent"] = (
            len(strong_binders) / len(affinities) * 100
        ) >= 50.0

    if rmsds:
        criteria_met["avg_rmsd_below_3"] = avg_rmsd < 3.0
        criteria_met["good_rmsd_above_60_percent"] = (len(good_rmsd) / len(rmsds) * 100) >= 60.0

    # Overall pass: at least 75% of criteria must be met
    criteria_pass_rate = (
        (sum(criteria_met.values()) / len(criteria_met) * 100) if criteria_met else 0.0
    )
    overall_pass = criteria_pass_rate >= 75.0

    return {
        "total_molecules": total,
        "passed": num_successful,
        "failed": total - num_successful,
        "success_rate": round(success_rate, 2),
        "lipinski_compliant": len(lipinski_compliant),
        "lipinski_rate": round(lipinski_rate, 2),
        "molecules_with_alerts": len(molecules_with_alerts),
        "alert_rate": round(alert_rate, 2),
        "molecules_with_reactive_groups": len(molecules_with_reactive),
        "reactive_rate": round(reactive_rate, 2),
        "avg_affinity": round(avg_affinity, 3) if avg_affinity is not None else None,
        "min_affinity": round(min_affinity, 3) if min_affinity is not None else None,
        "max_affinity": round(max_affinity, 3) if max_affinity is not None else None,
        "strong_binders": len(strong_binders),
        "strong_binders_rate": (
            round(len(strong_binders) / len(affinities) * 100, 2) if affinities else None
        ),
        "avg_rmsd": round(avg_rmsd, 3) if avg_rmsd is not None else None,
        "good_rmsd_count": len(good_rmsd),
        "good_rmsd_rate": round(len(good_rmsd) / len(rmsds) * 100, 2) if rmsds else None,
        "criteria_met": criteria_met,
        "criteria_pass_rate": round(criteria_pass_rate, 2),
        "overall_pass": overall_pass,
    }
