#!/usr/bin/env python3
"""
BioQL Profiler Module - Performance Profiling and Optimization Analysis

This module provides comprehensive profiling capabilities for BioQL quantum operations,
including timing analysis, circuit metrics tracking, cost analysis, bottleneck detection,
and memory profiling with minimal overhead (<5%).

Features:
- Thread-safe profiling context management
- Stage-based timing analysis
- Circuit complexity metrics
- Cost tracking and projections
- Bottleneck detection with recommendations
- Memory profiling with tracemalloc
- Export to JSON and Markdown formats
- Backend comparison capabilities
- Decorator-based profiling
"""

import time
import tracemalloc
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from datetime import datetime
from functools import wraps
import json
from pathlib import Path
import psutil
import os

# Optional loguru import
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class ProfilingMode(Enum):
    """Profiling modes with different levels of detail"""
    MINIMAL = "minimal"          # Basic timing only
    STANDARD = "standard"        # Timing + circuit metrics
    DETAILED = "detailed"        # Standard + cost analysis
    DEBUG = "debug"              # All metrics + memory profiling


class BottleneckSeverity(Enum):
    """Severity levels for detected bottlenecks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BottleneckType(Enum):
    """Types of performance bottlenecks"""
    CIRCUIT_DEPTH = "circuit_depth"
    GATE_COUNT = "gate_count"
    QUBIT_COUNT = "qubit_count"
    MEMORY_USAGE = "memory_usage"
    EXECUTION_TIME = "execution_time"
    COST = "cost"
    BACKEND_OVERHEAD = "backend_overhead"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class StageMetrics:
    """Metrics for a single profiling stage"""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_delta_mb: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if stage has completed"""
        return self.end_time > 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CircuitMetrics:
    """Quantum circuit complexity metrics"""
    qubits: int = 0
    depth: int = 0
    gate_count: int = 0
    two_qubit_gates: int = 0
    single_qubit_gates: int = 0
    optimization_score: float = 0.0  # 0-100, higher is better
    backend: str = "unknown"
    shots: int = 0

    # Advanced metrics
    entanglement_score: float = 0.0
    parallelism_score: float = 0.0

    def calculate_optimization_score(self) -> float:
        """Calculate circuit optimization score (0-100)"""
        if self.qubits == 0:
            return 0.0

        # Ideal depth is roughly qubits * 2
        ideal_depth = self.qubits * 2
        depth_penalty = min(self.depth / max(ideal_depth, 1), 2.0)

        # Penalize excessive gates
        gates_per_qubit = self.gate_count / max(self.qubits, 1)
        gate_penalty = min(gates_per_qubit / 10.0, 2.0)

        # Two-qubit gates are more expensive
        two_qubit_ratio = self.two_qubit_gates / max(self.gate_count, 1)
        two_qubit_penalty = two_qubit_ratio * 0.5

        # Calculate score (100 = perfect)
        raw_score = 100.0 - (depth_penalty * 30.0) - (gate_penalty * 20.0) - (two_qubit_penalty * 10.0)
        self.optimization_score = max(0.0, min(100.0, raw_score))

        return self.optimization_score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CostMetrics:
    """Cost analysis metrics"""
    total_cost: float = 0.0
    backend_cost: float = 0.0
    shot_cost: float = 0.0
    complexity_cost: float = 0.0
    algorithm_cost: float = 0.0

    # Cost breakdown
    base_cost_per_shot: float = 0.0
    complexity_multiplier: float = 1.0
    algorithm_multiplier: float = 1.0
    shots: int = 0

    # Projections
    projected_monthly_cost: float = 0.0
    projected_annual_cost: float = 0.0
    cost_per_qubit: float = 0.0

    def calculate_projections(self, executions_per_day: int = 100) -> None:
        """Calculate cost projections"""
        daily_cost = self.total_cost * executions_per_day
        self.projected_monthly_cost = daily_cost * 30
        self.projected_annual_cost = daily_cost * 365

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Bottleneck:
    """Detected performance bottleneck"""
    severity: BottleneckSeverity
    type: BottleneckType
    metric_value: float
    threshold_value: float
    impact_percentage: float  # % impact on overall performance
    recommendations: List[str] = field(default_factory=list)
    stage: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'severity': self.severity.value,
            'type': self.type.value,
            'metric_value': self.metric_value,
            'threshold_value': self.threshold_value,
            'impact_percentage': self.impact_percentage,
            'recommendations': self.recommendations,
            'stage': self.stage
        }


# ============================================================================
# PROFILER CONTEXT
# ============================================================================

class ProfilerContext:
    """Thread-safe profiling context manager"""

    def __init__(self, mode: ProfilingMode = ProfilingMode.STANDARD):
        self.mode = mode
        self.stages: Dict[str, StageMetrics] = {}
        self.current_stage: Optional[str] = None
        self.start_time = time.perf_counter()
        self.process = psutil.Process(os.getpid())
        self._lock = threading.Lock()
        self._memory_tracking = mode in [ProfilingMode.DEBUG, ProfilingMode.DETAILED]

        # Start memory tracking if in debug mode
        if self._memory_tracking:
            tracemalloc.start()

        self.initial_memory = self._get_memory_usage()

    def start_stage(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start profiling a new stage"""
        with self._lock:
            if self.current_stage:
                logger.warning(f"Stage '{self.current_stage}' not ended before starting '{name}'")
                self.end_stage(self.current_stage)

            stage = StageMetrics(
                name=name,
                start_time=time.perf_counter(),
                cpu_percent=self.process.cpu_percent(),
                memory_mb=self._get_memory_usage(),
                metadata=metadata or {}
            )

            self.stages[name] = stage
            self.current_stage = name

            if self.mode == ProfilingMode.DEBUG:
                logger.debug(f"Started profiling stage: {name}")

    def end_stage(self, name: Optional[str] = None) -> StageMetrics:
        """End profiling current or specified stage"""
        with self._lock:
            stage_name = name or self.current_stage

            if not stage_name or stage_name not in self.stages:
                raise ValueError(f"Stage '{stage_name}' not found or not started")

            stage = self.stages[stage_name]
            stage.end_time = time.perf_counter()
            stage.duration = stage.end_time - stage.start_time
            stage.cpu_percent = self.process.cpu_percent()

            current_memory = self._get_memory_usage()
            stage.memory_mb = current_memory
            stage.memory_delta_mb = current_memory - self.initial_memory

            if stage_name == self.current_stage:
                self.current_stage = None

            if self.mode == ProfilingMode.DEBUG:
                logger.debug(
                    f"Ended stage '{name}': {stage.duration:.3f}s, "
                    f"CPU: {stage.cpu_percent:.1f}%, "
                    f"Memory: {stage.memory_mb:.1f}MB"
                )

            return stage

    def get_stage(self, name: str) -> Optional[StageMetrics]:
        """Get metrics for a specific stage"""
        return self.stages.get(name)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        if self._memory_tracking:
            try:
                return self.process.memory_info().rss / 1024 / 1024
            except:
                pass
        return 0.0

    def get_total_duration(self) -> float:
        """Get total profiling duration"""
        return time.perf_counter() - self.start_time

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.current_stage:
            self.end_stage(self.current_stage)

        if self._memory_tracking:
            tracemalloc.stop()

        return False


# ============================================================================
# MAIN PROFILER CLASS
# ============================================================================

class Profiler:
    """Main profiler class for BioQL quantum operations"""

    def __init__(self, mode: ProfilingMode = ProfilingMode.STANDARD):
        self.mode = mode
        self.context: Optional[ProfilerContext] = None
        self.circuit_metrics: Optional[CircuitMetrics] = None
        self.cost_metrics: Optional[CostMetrics] = None
        self.bottlenecks: List[Bottleneck] = []
        self.metadata: Dict[str, Any] = {}

    def profile_quantum(
        self,
        quantum_func: Callable,
        *args,
        extract_metrics: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Profile a quantum function execution

        Args:
            quantum_func: The quantum function to profile
            *args: Positional arguments for the function
            extract_metrics: Extract circuit metrics from result
            **kwargs: Keyword arguments for the function

        Returns:
            Dictionary containing result and profiling data
        """
        self.context = ProfilerContext(self.mode)

        with self.context:
            # Stage 1: Pre-execution
            self.context.start_stage("pre_execution")
            program = args[0] if args else kwargs.get('program', '')
            backend = kwargs.get('backend', 'simulator')
            shots = kwargs.get('shots', 1024)
            self.context.end_stage("pre_execution")

            # Stage 2: Execution
            self.context.start_stage("quantum_execution", {
                'backend': backend,
                'shots': shots,
                'program_length': len(str(program))
            })

            try:
                result = quantum_func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                logger.error(f"Quantum execution failed: {e}")

            self.context.end_stage("quantum_execution")

            # Stage 3: Post-processing
            self.context.start_stage("post_processing")

            if extract_metrics and result:
                self._extract_circuit_metrics(result, backend, shots)
                self._extract_cost_metrics(result, program, backend, shots)

            self.context.end_stage("post_processing")

            # Stage 4: Analysis
            self.context.start_stage("bottleneck_analysis")
            self._detect_bottlenecks()
            self.context.end_stage("bottleneck_analysis")

        return {
            'result': result,
            'success': success,
            'error': error,
            'profiling': self.get_summary()
        }

    def _extract_circuit_metrics(self, result: Any, backend: str, shots: int) -> None:
        """Extract circuit metrics from quantum result"""
        self.circuit_metrics = CircuitMetrics(backend=backend, shots=shots)

        # Try to extract from result metadata
        if hasattr(result, 'metadata') and result.metadata:
            metadata = result.metadata
            self.circuit_metrics.qubits = metadata.get('qubits', 0)
            self.circuit_metrics.depth = metadata.get('circuit_depth', 0)
            self.circuit_metrics.gate_count = metadata.get('gate_count', 0)
            self.circuit_metrics.two_qubit_gates = metadata.get('two_qubit_gates', 0)
            self.circuit_metrics.single_qubit_gates = metadata.get('single_qubit_gates', 0)

        # Calculate optimization score
        if self.circuit_metrics.qubits > 0:
            self.circuit_metrics.calculate_optimization_score()

    def _extract_cost_metrics(self, result: Any, program: str, backend: str, shots: int) -> None:
        """Extract cost metrics from quantum result"""
        from .simple_billing import (
            get_backend_cost_per_shot,
            get_complexity_multiplier,
            get_algorithm_multiplier,
            estimate_qubits_from_program,
            classify_algorithm
        )

        self.cost_metrics = CostMetrics(shots=shots)

        # Calculate costs using billing module
        qubits = estimate_qubits_from_program(program)
        algorithm = classify_algorithm(program)

        self.cost_metrics.base_cost_per_shot = get_backend_cost_per_shot(backend)
        self.cost_metrics.complexity_multiplier = get_complexity_multiplier(qubits)
        self.cost_metrics.algorithm_multiplier = get_algorithm_multiplier(algorithm)

        self.cost_metrics.shot_cost = self.cost_metrics.base_cost_per_shot * shots
        self.cost_metrics.complexity_cost = self.cost_metrics.shot_cost * self.cost_metrics.complexity_multiplier
        self.cost_metrics.total_cost = (
            shots *
            self.cost_metrics.base_cost_per_shot *
            self.cost_metrics.complexity_multiplier *
            self.cost_metrics.algorithm_multiplier
        )

        # Calculate projections
        self.cost_metrics.calculate_projections()

        # Cost per qubit
        if qubits > 0:
            self.cost_metrics.cost_per_qubit = self.cost_metrics.total_cost / qubits

    def _detect_bottlenecks(self) -> None:
        """Detect performance bottlenecks"""
        self.bottlenecks = []

        # Check circuit metrics
        if self.circuit_metrics:
            # Circuit depth bottleneck
            if self.circuit_metrics.depth > 100:
                severity = (
                    BottleneckSeverity.CRITICAL if self.circuit_metrics.depth > 500 else
                    BottleneckSeverity.HIGH if self.circuit_metrics.depth > 200 else
                    BottleneckSeverity.MEDIUM
                )
                impact = min((self.circuit_metrics.depth / 100.0) * 10, 100)

                self.bottlenecks.append(Bottleneck(
                    severity=severity,
                    type=BottleneckType.CIRCUIT_DEPTH,
                    metric_value=self.circuit_metrics.depth,
                    threshold_value=100,
                    impact_percentage=impact,
                    recommendations=[
                        "Consider circuit optimization techniques",
                        "Use gate cancellation and commutation rules",
                        "Apply circuit compilation with optimization level 3",
                        "Consider breaking into smaller subcircuits"
                    ]
                ))

            # Gate count bottleneck
            if self.circuit_metrics.gate_count > 500:
                severity = (
                    BottleneckSeverity.HIGH if self.circuit_metrics.gate_count > 1000 else
                    BottleneckSeverity.MEDIUM
                )
                impact = min((self.circuit_metrics.gate_count / 500.0) * 15, 100)

                self.bottlenecks.append(Bottleneck(
                    severity=severity,
                    type=BottleneckType.GATE_COUNT,
                    metric_value=self.circuit_metrics.gate_count,
                    threshold_value=500,
                    impact_percentage=impact,
                    recommendations=[
                        "Reduce gate count through optimization",
                        "Use native gates for target backend",
                        "Consider alternative algorithm implementations"
                    ]
                ))

            # Qubit count bottleneck
            if self.circuit_metrics.qubits > 20:
                severity = (
                    BottleneckSeverity.CRITICAL if self.circuit_metrics.qubits > 50 else
                    BottleneckSeverity.HIGH
                )
                impact = min((self.circuit_metrics.qubits / 20.0) * 20, 100)

                self.bottlenecks.append(Bottleneck(
                    severity=severity,
                    type=BottleneckType.QUBIT_COUNT,
                    metric_value=self.circuit_metrics.qubits,
                    threshold_value=20,
                    impact_percentage=impact,
                    recommendations=[
                        "Consider qubit reduction techniques",
                        "Use symmetry to reduce problem size",
                        "Evaluate if all qubits are necessary",
                        "Consider classical preprocessing"
                    ]
                ))

        # Check execution time
        if self.context:
            exec_stage = self.context.get_stage("quantum_execution")
            if exec_stage and exec_stage.duration > 10.0:
                severity = (
                    BottleneckSeverity.CRITICAL if exec_stage.duration > 60.0 else
                    BottleneckSeverity.HIGH if exec_stage.duration > 30.0 else
                    BottleneckSeverity.MEDIUM
                )
                impact = min((exec_stage.duration / 10.0) * 25, 100)

                self.bottlenecks.append(Bottleneck(
                    severity=severity,
                    type=BottleneckType.EXECUTION_TIME,
                    metric_value=exec_stage.duration,
                    threshold_value=10.0,
                    impact_percentage=impact,
                    recommendations=[
                        "Consider using a faster backend",
                        "Reduce circuit complexity",
                        "Use caching for repeated executions",
                        "Parallelize independent circuits"
                    ],
                    stage="quantum_execution"
                ))

            # Check memory usage
            if exec_stage and exec_stage.memory_delta_mb > 500:
                severity = (
                    BottleneckSeverity.HIGH if exec_stage.memory_delta_mb > 1000 else
                    BottleneckSeverity.MEDIUM
                )
                impact = min((exec_stage.memory_delta_mb / 500.0) * 15, 100)

                self.bottlenecks.append(Bottleneck(
                    severity=severity,
                    type=BottleneckType.MEMORY_USAGE,
                    metric_value=exec_stage.memory_delta_mb,
                    threshold_value=500,
                    impact_percentage=impact,
                    recommendations=[
                        "Reduce shot count if possible",
                        "Process results in batches",
                        "Clear intermediate results",
                        "Use streaming results processing"
                    ],
                    stage="quantum_execution"
                ))

        # Check cost metrics
        if self.cost_metrics and self.cost_metrics.total_cost > 1.0:
            severity = (
                BottleneckSeverity.HIGH if self.cost_metrics.total_cost > 10.0 else
                BottleneckSeverity.MEDIUM
            )
            impact = min((self.cost_metrics.total_cost / 1.0) * 20, 100)

            self.bottlenecks.append(Bottleneck(
                severity=severity,
                type=BottleneckType.COST,
                metric_value=self.cost_metrics.total_cost,
                threshold_value=1.0,
                impact_percentage=impact,
                recommendations=[
                    "Use simulator for development/testing",
                    "Reduce shot count if accuracy allows",
                    "Optimize circuit to reduce complexity multiplier",
                    f"Projected monthly cost: ${self.cost_metrics.projected_monthly_cost:.2f}"
                ]
            ))

    def get_summary(self) -> Dict[str, Any]:
        """Get profiling summary"""
        summary = {
            'mode': self.mode.value,
            'timestamp': datetime.utcnow().isoformat(),
            'total_duration': self.context.get_total_duration() if self.context else 0.0,
            'stages': {},
            'circuit_metrics': None,
            'cost_metrics': None,
            'bottlenecks': [],
            'overhead_percentage': 0.0
        }

        # Add stage metrics
        if self.context:
            for name, stage in self.context.stages.items():
                summary['stages'][name] = stage.to_dict()

            # Calculate profiling overhead
            total_time = self.context.get_total_duration()
            exec_time = self.context.stages.get('quantum_execution')
            if exec_time and total_time > 0:
                overhead = ((total_time - exec_time.duration) / total_time) * 100
                summary['overhead_percentage'] = round(overhead, 2)

        # Add circuit metrics
        if self.circuit_metrics:
            summary['circuit_metrics'] = self.circuit_metrics.to_dict()

        # Add cost metrics
        if self.cost_metrics:
            summary['cost_metrics'] = self.cost_metrics.to_dict()

        # Add bottlenecks
        summary['bottlenecks'] = [b.to_dict() for b in self.bottlenecks]

        # Add metadata
        summary['metadata'] = self.metadata

        return summary

    def export_report(self, filepath: Union[str, Path], format: str = 'json') -> None:
        """
        Export profiling report to file

        Args:
            filepath: Path to output file
            format: Export format ('json' or 'markdown')
        """
        filepath = Path(filepath)
        summary = self.get_summary()

        if format.lower() == 'json':
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Exported JSON report to {filepath}")

        elif format.lower() == 'markdown':
            md_content = self._generate_markdown_report(summary)
            with open(filepath, 'w') as f:
                f.write(md_content)
            logger.info(f"Exported Markdown report to {filepath}")

        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_markdown_report(self, summary: Dict[str, Any]) -> str:
        """Generate Markdown report from summary"""
        lines = [
            "# BioQL Quantum Profiling Report",
            "",
            f"**Generated:** {summary['timestamp']}",
            f"**Profiling Mode:** {summary['mode']}",
            f"**Total Duration:** {summary['total_duration']:.3f}s",
            f"**Profiling Overhead:** {summary['overhead_percentage']:.2f}%",
            "",
            "## Stage Breakdown",
            ""
        ]

        # Stages table
        if summary['stages']:
            lines.extend([
                "| Stage | Duration (s) | CPU % | Memory (MB) | Memory Delta (MB) |",
                "|-------|-------------|--------|-------------|-------------------|"
            ])
            for name, stage in summary['stages'].items():
                lines.append(
                    f"| {name} | {stage['duration']:.3f} | "
                    f"{stage['cpu_percent']:.1f} | {stage['memory_mb']:.1f} | "
                    f"{stage['memory_delta_mb']:.1f} |"
                )
            lines.append("")

        # Circuit metrics
        if summary['circuit_metrics']:
            cm = summary['circuit_metrics']
            lines.extend([
                "## Circuit Metrics",
                "",
                f"- **Qubits:** {cm['qubits']}",
                f"- **Circuit Depth:** {cm['depth']}",
                f"- **Total Gates:** {cm['gate_count']}",
                f"- **Single-Qubit Gates:** {cm['single_qubit_gates']}",
                f"- **Two-Qubit Gates:** {cm['two_qubit_gates']}",
                f"- **Optimization Score:** {cm['optimization_score']:.1f}/100",
                f"- **Backend:** {cm['backend']}",
                f"- **Shots:** {cm['shots']}",
                ""
            ])

        # Cost metrics
        if summary['cost_metrics']:
            cost = summary['cost_metrics']
            lines.extend([
                "## Cost Analysis",
                "",
                f"- **Total Cost:** ${cost['total_cost']:.4f}",
                f"- **Base Cost per Shot:** ${cost['base_cost_per_shot']:.4f}",
                f"- **Complexity Multiplier:** {cost['complexity_multiplier']:.2f}x",
                f"- **Algorithm Multiplier:** {cost['algorithm_multiplier']:.2f}x",
                f"- **Projected Monthly Cost:** ${cost['projected_monthly_cost']:.2f}",
                f"- **Projected Annual Cost:** ${cost['projected_annual_cost']:.2f}",
                ""
            ])

        # Bottlenecks
        if summary['bottlenecks']:
            lines.extend([
                "## Detected Bottlenecks",
                ""
            ])
            for i, bottleneck in enumerate(summary['bottlenecks'], 1):
                severity_emoji = {
                    'low': '🟢',
                    'medium': '🟡',
                    'high': '🟠',
                    'critical': '🔴'
                }
                emoji = severity_emoji.get(bottleneck['severity'], '⚪')

                lines.extend([
                    f"### {i}. {emoji} {bottleneck['type'].upper()} ({bottleneck['severity'].upper()})",
                    "",
                    f"- **Metric Value:** {bottleneck['metric_value']:.2f}",
                    f"- **Threshold:** {bottleneck['threshold_value']:.2f}",
                    f"- **Impact:** {bottleneck['impact_percentage']:.1f}%",
                    ""
                ])

                if bottleneck['recommendations']:
                    lines.append("**Recommendations:**")
                    for rec in bottleneck['recommendations']:
                        lines.append(f"- {rec}")
                    lines.append("")
        else:
            lines.extend([
                "## Performance Status",
                "",
                "✅ No significant bottlenecks detected!",
                ""
            ])

        return "\n".join(lines)

    def compare_backends(
        self,
        quantum_func: Callable,
        backends: List[str],
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Compare performance across multiple backends

        Args:
            quantum_func: The quantum function to profile
            backends: List of backend names to compare
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function (backend will be overridden)

        Returns:
            Dictionary with comparison results
        """
        results = {}

        for backend in backends:
            logger.info(f"Profiling backend: {backend}")

            # Create new profiler for each backend
            profiler = Profiler(self.mode)

            # Update kwargs with current backend
            backend_kwargs = kwargs.copy()
            backend_kwargs['backend'] = backend

            # Profile execution
            result = profiler.profile_quantum(quantum_func, *args, **backend_kwargs)
            results[backend] = result['profiling']

        # Generate comparison summary
        comparison = {
            'backends': backends,
            'comparison_timestamp': datetime.utcnow().isoformat(),
            'results': results,
            'winner': self._determine_best_backend(results)
        }

        return comparison

    def _determine_best_backend(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Determine best backend based on different criteria"""
        winner = {
            'fastest': None,
            'cheapest': None,
            'best_optimization': None,
            'least_bottlenecks': None
        }

        fastest_time = float('inf')
        lowest_cost = float('inf')
        best_opt_score = 0.0
        fewest_bottlenecks = float('inf')

        for backend, data in results.items():
            # Fastest
            duration = data.get('total_duration', float('inf'))
            if duration < fastest_time:
                fastest_time = duration
                winner['fastest'] = backend

            # Cheapest
            cost_metrics = data.get('cost_metrics')
            if cost_metrics:
                cost = cost_metrics.get('total_cost', float('inf'))
                if cost < lowest_cost:
                    lowest_cost = cost
                    winner['cheapest'] = backend

            # Best optimization
            circuit_metrics = data.get('circuit_metrics')
            if circuit_metrics:
                opt_score = circuit_metrics.get('optimization_score', 0.0)
                if opt_score > best_opt_score:
                    best_opt_score = opt_score
                    winner['best_optimization'] = backend

            # Least bottlenecks
            bottleneck_count = len(data.get('bottlenecks', []))
            if bottleneck_count < fewest_bottlenecks:
                fewest_bottlenecks = bottleneck_count
                winner['least_bottlenecks'] = backend

        return winner


# ============================================================================
# DECORATOR
# ============================================================================

def profile_quantum(
    mode: ProfilingMode = ProfilingMode.STANDARD,
    export_path: Optional[Union[str, Path]] = None,
    export_format: str = 'json'
):
    """
    Decorator for profiling quantum functions

    Args:
        mode: Profiling mode
        export_path: Optional path to export report
        export_format: Export format ('json' or 'markdown')

    Example:
        @profile_quantum(mode=ProfilingMode.DETAILED, export_path='./reports/profile.json')
        def my_quantum_function(program, api_key, **kwargs):
            return enhanced_quantum(program, api_key, **kwargs)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = Profiler(mode)

            result = profiler.profile_quantum(func, *args, **kwargs)

            if export_path:
                profiler.export_report(export_path, export_format)

            # Log summary
            summary = profiler.get_summary()
            logger.info(
                f"Profiling complete: {summary['total_duration']:.3f}s, "
                f"Overhead: {summary['overhead_percentage']:.2f}%"
            )

            if summary['bottlenecks']:
                logger.warning(f"Detected {len(summary['bottlenecks'])} bottlenecks")

            return result

        return wrapper
    return decorator


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'Profiler',
    'ProfilerContext',
    'ProfilingMode',
    'BottleneckSeverity',
    'BottleneckType',
    'StageMetrics',
    'CircuitMetrics',
    'CostMetrics',
    'Bottleneck',
    'profile_quantum'
]
