"""
Base classes and types for BioQL Circuit Library.

This module provides the foundational abstractions for defining and working
with quantum circuit templates in BioQL.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import numpy as np


class CircuitCategory(Enum):
    """Categories of quantum circuits available in BioQL."""
    ALGORITHM = "algorithm"
    DRUG_DISCOVERY = "drug_discovery"
    CHEMISTRY = "chemistry"
    OPTIMIZATION = "optimization"
    SIMULATION = "simulation"
    UTILITY = "utility"


class ComplexityRating(Enum):
    """Complexity rating for circuit templates."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented


@dataclass
class ParameterSpec:
    """
    Specification for a circuit parameter.

    Attributes:
        name: Parameter name
        type: Expected type (e.g., 'int', 'float', 'str')
        description: Human-readable description
        default: Default value if not provided
        required: Whether parameter is required
        constraints: Optional validation constraints
        range: Optional tuple of (min, max) for numeric parameters

    Example:
        >>> param = ParameterSpec(
        ...     name="num_qubits",
        ...     type="int",
        ...     description="Number of qubits in the circuit",
        ...     required=True,
        ...     range=(1, 100)
        ... )
    """
    name: str
    type: str
    description: str
    default: Optional[Any] = None
    required: bool = False
    constraints: Optional[Dict[str, Any]] = None
    range: Optional[tuple] = None

    def validate(self, value: Any) -> bool:
        """
        Validate a parameter value against this spec.

        Args:
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        # Type validation
        if self.type == "int" and not isinstance(value, int):
            return False
        elif self.type == "float" and not isinstance(value, (int, float)):
            return False
        elif self.type == "str" and not isinstance(value, str):
            return False
        elif self.type == "list" and not isinstance(value, list):
            return False

        # Range validation
        if self.range and isinstance(value, (int, float)):
            min_val, max_val = self.range
            if value < min_val or value > max_val:
                return False

        # Custom constraints
        if self.constraints:
            for constraint_name, constraint_value in self.constraints.items():
                if constraint_name == "min_length" and len(value) < constraint_value:
                    return False
                elif constraint_name == "max_length" and len(value) > constraint_value:
                    return False
                elif constraint_name == "one_of" and value not in constraint_value:
                    return False

        return True


@dataclass
class ResourceEstimate:
    """
    Estimated resource requirements for a circuit.

    Attributes:
        num_qubits: Number of qubits required
        circuit_depth: Estimated circuit depth
        gate_count: Total number of gates
        two_qubit_gates: Number of two-qubit gates
        measurement_count: Number of measurements
        classical_memory: Classical memory required (bits)
        execution_time_estimate: Estimated execution time in seconds
        error_budget: Estimated error budget

    Example:
        >>> estimate = ResourceEstimate(
        ...     num_qubits=10,
        ...     circuit_depth=50,
        ...     gate_count=200,
        ...     two_qubit_gates=40
        ... )
    """
    num_qubits: int
    circuit_depth: int
    gate_count: int
    two_qubit_gates: int = 0
    measurement_count: int = 1
    classical_memory: int = 0
    execution_time_estimate: float = 0.0
    error_budget: float = 0.01

    def is_feasible(self, max_qubits: int = 100, max_depth: int = 1000) -> bool:
        """
        Check if circuit is feasible given constraints.

        Args:
            max_qubits: Maximum available qubits
            max_depth: Maximum allowed circuit depth

        Returns:
            True if feasible, False otherwise
        """
        return self.num_qubits <= max_qubits and self.circuit_depth <= max_depth

    def quality_score(self) -> float:
        """
        Calculate a quality score based on resource efficiency.

        Returns:
            Quality score between 0 and 1 (higher is better)
        """
        # Simple heuristic: prefer shallow circuits with fewer gates
        depth_score = 1.0 / (1.0 + self.circuit_depth / 100.0)
        gate_score = 1.0 / (1.0 + self.gate_count / 1000.0)
        two_qubit_score = 1.0 / (1.0 + self.two_qubit_gates / 100.0)

        return (depth_score + gate_score + two_qubit_score) / 3.0


class CircuitTemplate(ABC):
    """
    Abstract base class for all circuit templates.

    All circuit templates in the BioQL library must inherit from this class
    and implement the required abstract methods.

    Attributes:
        name: Unique identifier for the template
        description: Human-readable description
        category: Circuit category
        complexity: Complexity rating
        parameters: List of parameter specifications
        tags: Searchable tags
        use_cases: List of use cases
        references: Academic or technical references

    Example:
        >>> class MyCircuit(CircuitTemplate):
        ...     def __init__(self):
        ...         super().__init__(
        ...             name="my_circuit",
        ...             description="A custom circuit",
        ...             category=CircuitCategory.ALGORITHM
        ...         )
        ...
        ...     def build(self, **kwargs):
        ...         # Implementation
        ...         pass
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: CircuitCategory,
        complexity: ComplexityRating = ComplexityRating.MEDIUM,
        parameters: Optional[List[ParameterSpec]] = None,
        tags: Optional[List[str]] = None,
        use_cases: Optional[List[str]] = None,
        references: Optional[List[str]] = None
    ):
        """
        Initialize circuit template.

        Args:
            name: Unique identifier
            description: Human-readable description
            category: Circuit category
            complexity: Complexity rating
            parameters: Parameter specifications
            tags: Searchable tags
            use_cases: Use case descriptions
            references: Academic/technical references
        """
        self.name = name
        self.description = description
        self.category = category
        self.complexity = complexity
        self.parameters = parameters or []
        self.tags = tags or []
        self.use_cases = use_cases or []
        self.references = references or []

    @abstractmethod
    def build(self, **kwargs) -> Any:
        """
        Build the quantum circuit with given parameters.

        Args:
            **kwargs: Circuit parameters

        Returns:
            Quantum circuit object (backend-specific)
        """
        pass

    @abstractmethod
    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """
        Estimate resource requirements for given parameters.

        Args:
            **kwargs: Circuit parameters

        Returns:
            Resource estimate
        """
        pass

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate provided parameters against specifications.

        Args:
            **kwargs: Parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required parameters
        for param_spec in self.parameters:
            if param_spec.required and param_spec.name not in kwargs:
                return False, f"Missing required parameter: {param_spec.name}"

        # Validate provided parameters
        for param_name, param_value in kwargs.items():
            # Find parameter spec
            param_spec = next(
                (p for p in self.parameters if p.name == param_name),
                None
            )

            if param_spec is None:
                return False, f"Unknown parameter: {param_name}"

            if not param_spec.validate(param_value):
                return False, f"Invalid value for parameter {param_name}: {param_value}"

        return True, None

    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameter values.

        Returns:
            Dictionary of parameter names to default values
        """
        return {
            param.name: param.default
            for param in self.parameters
            if param.default is not None
        }

    def matches_query(self, query: str) -> bool:
        """
        Check if template matches a search query.

        Args:
            query: Search query string

        Returns:
            True if matches, False otherwise
        """
        query_lower = query.lower()

        # Search in name
        if query_lower in self.name.lower():
            return True

        # Search in description
        if query_lower in self.description.lower():
            return True

        # Search in tags
        if any(query_lower in tag.lower() for tag in self.tags):
            return True

        # Search in use cases
        if any(query_lower in use_case.lower() for use_case in self.use_cases):
            return True

        return False

    def __repr__(self) -> str:
        return f"CircuitTemplate(name='{self.name}', category={self.category.value})"

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


@dataclass
class CircuitMetadata:
    """
    Metadata for a circuit template.

    Attributes:
        version: Template version
        author: Template author
        created_date: Creation date
        last_modified: Last modification date
        license: License information
        experimental: Whether template is experimental
        deprecated: Whether template is deprecated
        replacement: Replacement template name if deprecated
    """
    version: str = "1.0.0"
    author: Optional[str] = None
    created_date: Optional[str] = None
    last_modified: Optional[str] = None
    license: str = "Apache-2.0"
    experimental: bool = False
    deprecated: bool = False
    replacement: Optional[str] = None
