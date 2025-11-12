"""
Circuit composition utilities.

This module provides tools for composing multiple circuit templates
together to create complex workflows.

Includes both legacy template-based composition and new Qiskit circuit
composition tools.
"""

from typing import Any, List, Optional, Dict
from ..base import CircuitTemplate, ResourceEstimate

# Import new Qiskit-based composition tools
from .composer import (
    CircuitComposer as QiskitCircuitComposer,
    CompositionStrategy,
    CompositionResult
)

from .stitching import (
    CircuitStitcher,
    StitchingStrategy,
    StitchingResult,
    ValidationResult
)

from .modular import (
    ModularCircuitBuilder,
    WiringMode,
    ModuleSpec,
    WiringSpec,
    ArchitectureDiagram
)


class CircuitComposer:
    """
    Utility for composing multiple circuit templates.

    Allows sequential and parallel composition of circuits with
    automatic resource estimation.

    Example:
        >>> composer = CircuitComposer()
        >>> composer.add_sequential(vqe_circuit)
        >>> composer.add_sequential(measurement_circuit)
        >>> combined = composer.build()
    """

    def __init__(self):
        """Initialize circuit composer."""
        self._sequential_circuits: List[tuple[CircuitTemplate, Dict[str, Any]]] = []
        self._parallel_circuits: List[List[tuple[CircuitTemplate, Dict[str, Any]]]] = []

    def add_sequential(
        self,
        template: CircuitTemplate,
        **params
    ) -> 'CircuitComposer':
        """
        Add a circuit to be executed sequentially.

        Args:
            template: Circuit template
            **params: Circuit parameters

        Returns:
            Self for chaining
        """
        self._sequential_circuits.append((template, params))
        return self

    def add_parallel(
        self,
        templates: List[tuple[CircuitTemplate, Dict[str, Any]]]
    ) -> 'CircuitComposer':
        """
        Add circuits to be executed in parallel.

        Args:
            templates: List of (template, params) tuples

        Returns:
            Self for chaining
        """
        self._parallel_circuits.append(templates)
        return self

    def estimate_resources(self) -> ResourceEstimate:
        """
        Estimate total resource requirements.

        Returns:
            Combined resource estimate
        """
        max_qubits = 0
        total_depth = 0
        total_gates = 0
        total_two_qubit = 0
        total_measurements = 0
        total_time = 0.0
        max_error = 0.0

        # Sequential circuits add depth
        for template, params in self._sequential_circuits:
            estimate = template.estimate_resources(**params)
            max_qubits = max(max_qubits, estimate.num_qubits)
            total_depth += estimate.circuit_depth
            total_gates += estimate.gate_count
            total_two_qubit += estimate.two_qubit_gates
            total_measurements += estimate.measurement_count
            total_time += estimate.execution_time_estimate
            max_error = max(max_error, estimate.error_budget)

        # Parallel circuits take max depth
        for parallel_group in self._parallel_circuits:
            max_parallel_depth = 0
            parallel_qubits = 0
            parallel_gates = 0
            parallel_two_qubit = 0
            parallel_measurements = 0
            parallel_time = 0.0

            for template, params in parallel_group:
                estimate = template.estimate_resources(**params)
                parallel_qubits += estimate.num_qubits
                parallel_gates += estimate.gate_count
                parallel_two_qubit += estimate.two_qubit_gates
                parallel_measurements += estimate.measurement_count
                max_parallel_depth = max(max_parallel_depth, estimate.circuit_depth)
                parallel_time = max(parallel_time, estimate.execution_time_estimate)
                max_error = max(max_error, estimate.error_budget)

            max_qubits = max(max_qubits, parallel_qubits)
            total_depth += max_parallel_depth
            total_gates += parallel_gates
            total_two_qubit += parallel_two_qubit
            total_measurements += parallel_measurements
            total_time += parallel_time

        return ResourceEstimate(
            num_qubits=max_qubits,
            circuit_depth=total_depth,
            gate_count=total_gates,
            two_qubit_gates=total_two_qubit,
            measurement_count=total_measurements,
            execution_time_estimate=total_time,
            error_budget=max_error
        )

    def build(self, **global_params) -> Dict[str, Any]:
        """
        Build the composed circuit.

        Args:
            **global_params: Global parameters applied to all circuits

        Returns:
            Composed circuit structure
        """
        sequential = []
        for template, params in self._sequential_circuits:
            merged_params = {**global_params, **params}
            circuit = template.build(**merged_params)
            sequential.append({
                "template": template.name,
                "circuit": circuit,
                "params": merged_params
            })

        parallel = []
        for parallel_group in self._parallel_circuits:
            group_circuits = []
            for template, params in parallel_group:
                merged_params = {**global_params, **params}
                circuit = template.build(**merged_params)
                group_circuits.append({
                    "template": template.name,
                    "circuit": circuit,
                    "params": merged_params
                })
            parallel.append(group_circuits)

        return {
            "type": "composed_circuit",
            "sequential": sequential,
            "parallel": parallel,
            "resource_estimate": self.estimate_resources()
        }

    def clear(self) -> None:
        """Clear all circuits."""
        self._sequential_circuits.clear()
        self._parallel_circuits.clear()


class CircuitPipeline:
    """
    Pipeline for executing circuits with data flow.

    Manages circuit execution order and data dependencies.

    Example:
        >>> pipeline = CircuitPipeline()
        >>> pipeline.add_stage("preparation", prep_circuit)
        >>> pipeline.add_stage("optimization", vqe_circuit, depends_on=["preparation"])
        >>> pipeline.add_stage("measurement", measure_circuit, depends_on=["optimization"])
        >>> result = pipeline.execute()
    """

    def __init__(self):
        """Initialize circuit pipeline."""
        self._stages: Dict[str, Dict[str, Any]] = {}
        self._execution_order: Optional[List[str]] = None

    def add_stage(
        self,
        name: str,
        template: CircuitTemplate,
        params: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None
    ) -> 'CircuitPipeline':
        """
        Add a pipeline stage.

        Args:
            name: Stage name
            template: Circuit template
            params: Circuit parameters
            depends_on: List of stage names this depends on

        Returns:
            Self for chaining
        """
        self._stages[name] = {
            "template": template,
            "params": params or {},
            "depends_on": depends_on or [],
            "result": None
        }
        self._execution_order = None  # Invalidate cached order
        return self

    def _topological_sort(self) -> List[str]:
        """
        Compute execution order via topological sort.

        Returns:
            Ordered list of stage names
        """
        # Build dependency graph
        in_degree = {name: 0 for name in self._stages}
        graph = {name: [] for name in self._stages}

        for name, stage in self._stages.items():
            for dependency in stage["depends_on"]:
                if dependency not in self._stages:
                    raise ValueError(f"Unknown dependency: {dependency}")
                graph[dependency].append(name)
                in_degree[name] += 1

        # Topological sort
        queue = [name for name, degree in in_degree.items() if degree == 0]
        order = []

        while queue:
            current = queue.pop(0)
            order.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._stages):
            raise ValueError("Circular dependency detected in pipeline")

        return order

    def get_execution_order(self) -> List[str]:
        """
        Get the execution order of stages.

        Returns:
            Ordered list of stage names
        """
        if self._execution_order is None:
            self._execution_order = self._topological_sort()
        return self._execution_order

    def estimate_resources(self) -> ResourceEstimate:
        """
        Estimate total pipeline resources.

        Returns:
            Combined resource estimate
        """
        order = self.get_execution_order()

        max_qubits = 0
        total_depth = 0
        total_gates = 0
        total_two_qubit = 0
        total_measurements = 0
        total_time = 0.0
        max_error = 0.0

        for stage_name in order:
            stage = self._stages[stage_name]
            template = stage["template"]
            params = stage["params"]

            estimate = template.estimate_resources(**params)
            max_qubits = max(max_qubits, estimate.num_qubits)
            total_depth += estimate.circuit_depth
            total_gates += estimate.gate_count
            total_two_qubit += estimate.two_qubit_gates
            total_measurements += estimate.measurement_count
            total_time += estimate.execution_time_estimate
            max_error = max(max_error, estimate.error_budget)

        return ResourceEstimate(
            num_qubits=max_qubits,
            circuit_depth=total_depth,
            gate_count=total_gates,
            two_qubit_gates=total_two_qubit,
            measurement_count=total_measurements,
            execution_time_estimate=total_time,
            error_budget=max_error
        )

    def build(self) -> Dict[str, Any]:
        """
        Build the pipeline.

        Returns:
            Pipeline structure with execution order
        """
        order = self.get_execution_order()

        stages = {}
        for stage_name in order:
            stage = self._stages[stage_name]
            template = stage["template"]
            params = stage["params"]

            circuit = template.build(**params)
            stages[stage_name] = {
                "template": template.name,
                "circuit": circuit,
                "params": params,
                "depends_on": stage["depends_on"]
            }

        return {
            "type": "pipeline",
            "execution_order": order,
            "stages": stages,
            "resource_estimate": self.estimate_resources()
        }


# Export composition utilities
__all__ = [
    # Legacy template-based composition
    "CircuitComposer",
    "CircuitPipeline",
    # New Qiskit circuit composition tools
    "QiskitCircuitComposer",
    "CompositionStrategy",
    "CompositionResult",
    "CircuitStitcher",
    "StitchingStrategy",
    "StitchingResult",
    "ValidationResult",
    "ModularCircuitBuilder",
    "WiringMode",
    "ModuleSpec",
    "WiringSpec",
    "ArchitectureDiagram",
]
