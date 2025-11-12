"""
Circuit catalog for discovering and managing circuit templates.

This module provides the CircuitCatalog class for searching, filtering,
and recommending quantum circuit templates.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import logging

from .base import (
    CircuitTemplate,
    CircuitCategory,
    ComplexityRating,
    ResourceEstimate
)

logger = logging.getLogger(__name__)


@dataclass
class ResourceConstraints:
    """
    Constraints for circuit resource requirements.

    Attributes:
        max_qubits: Maximum number of qubits available
        max_depth: Maximum allowed circuit depth
        max_gates: Maximum total gate count
        max_two_qubit_gates: Maximum two-qubit gate count
        max_execution_time: Maximum execution time (seconds)
        error_tolerance: Maximum acceptable error rate

    Example:
        >>> constraints = ResourceConstraints(
        ...     max_qubits=50,
        ...     max_depth=500,
        ...     error_tolerance=0.05
        ... )
    """
    max_qubits: Optional[int] = None
    max_depth: Optional[int] = None
    max_gates: Optional[int] = None
    max_two_qubit_gates: Optional[int] = None
    max_execution_time: Optional[float] = None
    error_tolerance: float = 0.01

    def satisfies(self, estimate: ResourceEstimate) -> bool:
        """
        Check if a resource estimate satisfies these constraints.

        Args:
            estimate: Resource estimate to check

        Returns:
            True if estimate satisfies constraints
        """
        if self.max_qubits and estimate.num_qubits > self.max_qubits:
            return False

        if self.max_depth and estimate.circuit_depth > self.max_depth:
            return False

        if self.max_gates and estimate.gate_count > self.max_gates:
            return False

        if self.max_two_qubit_gates and estimate.two_qubit_gates > self.max_two_qubit_gates:
            return False

        if self.max_execution_time and estimate.execution_time_estimate > self.max_execution_time:
            return False

        if estimate.error_budget > self.error_tolerance:
            return False

        return True


@dataclass
class SearchFilters:
    """
    Filters for searching circuit templates.

    Attributes:
        categories: Filter by categories
        complexity_max: Maximum complexity level
        tags: Filter by tags (any match)
        min_quality_score: Minimum quality score
        exclude_experimental: Exclude experimental circuits
        exclude_deprecated: Exclude deprecated circuits
    """
    categories: Optional[List[CircuitCategory]] = None
    complexity_max: Optional[ComplexityRating] = None
    tags: Optional[List[str]] = None
    min_quality_score: Optional[float] = None
    exclude_experimental: bool = True
    exclude_deprecated: bool = True


class CircuitCatalog:
    """
    Catalog for managing and discovering circuit templates.

    The CircuitCatalog provides a searchable registry of all available
    circuit templates with filtering, recommendation, and lazy loading
    capabilities.

    Example:
        >>> catalog = CircuitCatalog()
        >>> catalog.register(my_circuit_template)
        >>> results = catalog.search("VQE")
        >>> for circuit in results:
        ...     print(circuit.name)
    """

    def __init__(self):
        """Initialize empty circuit catalog."""
        self._templates: Dict[str, CircuitTemplate] = {}
        self._lazy_loaders: Dict[str, Callable[[], CircuitTemplate]] = {}
        self._category_index: Dict[CircuitCategory, List[str]] = {
            cat: [] for cat in CircuitCategory
        }
        self._tag_index: Dict[str, List[str]] = {}

    def register(self, template: CircuitTemplate) -> None:
        """
        Register a circuit template in the catalog.

        Args:
            template: Circuit template to register

        Raises:
            ValueError: If template with same name already exists
        """
        if template.name in self._templates:
            logger.warning(f"Overwriting existing template: {template.name}")

        self._templates[template.name] = template

        # Update category index
        if template.name not in self._category_index[template.category]:
            self._category_index[template.category].append(template.name)

        # Update tag index
        for tag in template.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = []
            if template.name not in self._tag_index[tag_lower]:
                self._tag_index[tag_lower].append(template.name)

        logger.debug(f"Registered circuit template: {template.name}")

    def register_lazy(
        self,
        name: str,
        loader: Callable[[], CircuitTemplate],
        category: CircuitCategory,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Register a lazy-loaded circuit template.

        The template will only be instantiated when first accessed.

        Args:
            name: Template name
            loader: Function that returns the template instance
            category: Template category (for indexing)
            tags: Template tags (for indexing)
        """
        self._lazy_loaders[name] = loader

        # Update category index
        if name not in self._category_index[category]:
            self._category_index[category].append(name)

        # Update tag index
        if tags:
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower not in self._tag_index:
                    self._tag_index[tag_lower] = []
                if name not in self._tag_index[tag_lower]:
                    self._tag_index[tag_lower].append(name)

        logger.debug(f"Registered lazy circuit template: {name}")

    def get(self, name: str) -> Optional[CircuitTemplate]:
        """
        Get a circuit template by name.

        Args:
            name: Template name

        Returns:
            Circuit template or None if not found
        """
        # Check if already loaded
        if name in self._templates:
            return self._templates[name]

        # Check if lazy loader exists
        if name in self._lazy_loaders:
            template = self._lazy_loaders[name]()
            self._templates[name] = template
            del self._lazy_loaders[name]  # Remove loader after use
            return template

        return None

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[SearchFilters] = None
    ) -> List[CircuitTemplate]:
        """
        Search for circuit templates.

        Args:
            query: Search query string (searches name, description, tags, use cases)
            filters: Additional search filters

        Returns:
            List of matching circuit templates

        Example:
            >>> catalog = CircuitCatalog()
            >>> # Search by query
            >>> results = catalog.search("drug discovery")
            >>> # Search with filters
            >>> filters = SearchFilters(
            ...     categories=[CircuitCategory.DRUG_DISCOVERY],
            ...     complexity_max=ComplexityRating.MEDIUM
            ... )
            >>> results = catalog.search(filters=filters)
        """
        results = []

        # Get all template names to search
        template_names = set(self._templates.keys()) | set(self._lazy_loaders.keys())

        for name in template_names:
            template = self.get(name)
            if template is None:
                continue

            # Apply filters
            if filters:
                if filters.categories and template.category not in filters.categories:
                    continue

                if filters.complexity_max and template.complexity > filters.complexity_max:
                    continue

                if filters.tags:
                    if not any(tag.lower() in [t.lower() for t in template.tags] for tag in filters.tags):
                        continue

            # Apply query
            if query and not template.matches_query(query):
                continue

            results.append(template)

        return results

    def get_by_category(self, category: CircuitCategory) -> List[CircuitTemplate]:
        """
        Get all templates in a specific category.

        Args:
            category: Circuit category

        Returns:
            List of circuit templates in the category

        Example:
            >>> catalog = CircuitCatalog()
            >>> drug_circuits = catalog.get_by_category(CircuitCategory.DRUG_DISCOVERY)
        """
        template_names = self._category_index.get(category, [])
        templates = []

        for name in template_names:
            template = self.get(name)
            if template:
                templates.append(template)

        return templates

    def get_by_use_case(self, use_case: str) -> List[CircuitTemplate]:
        """
        Get templates suitable for a specific use case.

        Args:
            use_case: Use case description (substring match)

        Returns:
            List of matching circuit templates

        Example:
            >>> catalog = CircuitCatalog()
            >>> circuits = catalog.get_by_use_case("protein folding")
        """
        results = []
        use_case_lower = use_case.lower()

        # Get all template names
        template_names = set(self._templates.keys()) | set(self._lazy_loaders.keys())

        for name in template_names:
            template = self.get(name)
            if template is None:
                continue

            # Check if use case matches any of the template's use cases
            if any(use_case_lower in uc.lower() for uc in template.use_cases):
                results.append(template)

        return results

    def recommend(
        self,
        use_case: Optional[str] = None,
        constraints: Optional[ResourceConstraints] = None,
        **circuit_params
    ) -> List[tuple[CircuitTemplate, float]]:
        """
        Recommend circuit templates based on use case and constraints.

        Args:
            use_case: Target use case
            constraints: Resource constraints
            **circuit_params: Circuit parameters for resource estimation

        Returns:
            List of (template, score) tuples, sorted by score (descending)

        Example:
            >>> catalog = CircuitCatalog()
            >>> constraints = ResourceConstraints(max_qubits=20, max_depth=100)
            >>> recommendations = catalog.recommend(
            ...     use_case="molecular simulation",
            ...     constraints=constraints,
            ...     num_qubits=10
            ... )
            >>> for template, score in recommendations[:5]:
            ...     print(f"{template.name}: {score:.2f}")
        """
        # Start with all templates or filter by use case
        if use_case:
            candidates = self.get_by_use_case(use_case)
        else:
            template_names = set(self._templates.keys()) | set(self._lazy_loaders.keys())
            candidates = [self.get(name) for name in template_names]
            candidates = [t for t in candidates if t is not None]

        scored_templates = []

        for template in candidates:
            try:
                # Estimate resources if parameters provided
                if circuit_params:
                    estimate = template.estimate_resources(**circuit_params)

                    # Check constraints
                    if constraints and not constraints.satisfies(estimate):
                        continue

                    # Calculate score based on resource efficiency
                    score = estimate.quality_score()
                else:
                    # Default score based on complexity
                    score = 1.0 / template.complexity.value

                # Boost score for exact use case matches
                if use_case:
                    use_case_lower = use_case.lower()
                    if any(use_case_lower == uc.lower() for uc in template.use_cases):
                        score *= 1.5

                scored_templates.append((template, score))

            except Exception as e:
                logger.warning(f"Failed to score template {template.name}: {e}")
                continue

        # Sort by score (descending)
        scored_templates.sort(key=lambda x: x[1], reverse=True)

        return scored_templates

    def list_categories(self) -> List[CircuitCategory]:
        """
        Get all categories that have registered templates.

        Returns:
            List of categories with templates
        """
        return [
            cat for cat, templates in self._category_index.items()
            if templates
        ]

    def list_tags(self) -> List[str]:
        """
        Get all tags used in registered templates.

        Returns:
            List of unique tags
        """
        return list(self._tag_index.keys())

    def count(self) -> int:
        """
        Get total number of registered templates.

        Returns:
            Template count
        """
        return len(self._templates) + len(self._lazy_loaders)

    def clear(self) -> None:
        """Clear all registered templates."""
        self._templates.clear()
        self._lazy_loaders.clear()
        self._category_index = {cat: [] for cat in CircuitCategory}
        self._tag_index.clear()
        logger.info("Cleared circuit catalog")

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, name: str) -> bool:
        return name in self._templates or name in self._lazy_loaders

    def __repr__(self) -> str:
        return f"CircuitCatalog(templates={self.count()})"


# Global catalog instance
_global_catalog = CircuitCatalog()


def get_catalog() -> CircuitCatalog:
    """
    Get the global circuit catalog instance.

    Returns:
        Global CircuitCatalog instance
    """
    return _global_catalog


def register_template(template: CircuitTemplate) -> None:
    """
    Register a template in the global catalog.

    Args:
        template: Circuit template to register
    """
    _global_catalog.register(template)


def search_templates(query: str, **kwargs) -> List[CircuitTemplate]:
    """
    Search templates in the global catalog.

    Args:
        query: Search query
        **kwargs: Additional search parameters

    Returns:
        List of matching templates
    """
    return _global_catalog.search(query, **kwargs)
