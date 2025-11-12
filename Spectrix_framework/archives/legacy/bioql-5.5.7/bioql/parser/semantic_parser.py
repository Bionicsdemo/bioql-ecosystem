"""
Advanced Semantic Parser for BioQL

This module provides sophisticated semantic analysis of natural language queries,
building semantic graphs that represent the structure, entities, relations, and
dependencies in complex bioinformatics tasks.

Features:
- Semantic graph construction with entities and relations
- Coreference resolution (handling pronouns like "it", "the protein")
- Negation handling ("not toxic", "avoid")
- Conditional logic ("if affinity > -8")
- Quantifiers ("all", "any", "top 10")
- Dependency graph for execution ordering
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Optional spaCy import for advanced NLP
try:
    import spacy
    from spacy.tokens import Doc, Span, Token
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    Doc = Any
    Span = Any
    Token = Any

# Optional loguru import
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from bioql.ir import DataType, BioQLDomain


class EntityType(str, Enum):
    """Types of entities in semantic graphs."""

    MOLECULE = "molecule"
    PROTEIN = "protein"
    LIGAND = "ligand"
    PROPERTY = "property"
    OPERATION = "operation"
    PARAMETER = "parameter"
    VALUE = "value"
    CONDITION = "condition"
    QUANTIFIER = "quantifier"
    REFERENCE = "reference"  # For coreference resolution


class RelationType(str, Enum):
    """Types of relations between entities."""

    DOCK = "dock"
    CALCULATE = "calculate"
    PREDICT = "predict"
    FILTER = "filter"
    SEQUENCE = "sequence"
    PARAMETER_OF = "parameter_of"
    PROPERTY_OF = "property_of"
    TARGETS = "targets"
    PRODUCES = "produces"
    REQUIRES = "requires"
    CONDITIONAL = "conditional"
    NEGATION = "negation"
    COREFERENCE = "coreference"


@dataclass
class Entity:
    """Represents an entity in the semantic graph."""

    id: str
    type: EntityType
    value: Any
    text: str  # Original text span
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_pos: int = 0
    end_pos: int = 0

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id


@dataclass
class Relation:
    """Represents a relation between entities."""

    type: RelationType
    source: Entity
    target: Entity
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.type, self.source.id, self.target.id))


@dataclass
class SemanticGraph:
    """
    Semantic graph representation of parsed natural language.

    Contains entities (nodes) and relations (edges) that represent
    the semantic structure of a query.
    """

    nodes: List[Entity] = field(default_factory=list)
    edges: List[Relation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, entity: Entity) -> None:
        """Add an entity node to the graph."""
        if entity not in self.nodes:
            self.nodes.append(entity)

    def add_edge(self, relation: Relation) -> None:
        """Add a relation edge to the graph."""
        # Ensure both entities are in the graph
        self.add_node(relation.source)
        self.add_node(relation.target)

        if relation not in self.edges:
            self.edges.append(relation)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [node for node in self.nodes if node.type == entity_type]

    def get_relations_by_type(self, relation_type: RelationType) -> List[Relation]:
        """Get all relations of a specific type."""
        return [edge for edge in self.edges if edge.type == relation_type]

    def get_outgoing_relations(self, entity: Entity) -> List[Relation]:
        """Get all relations where entity is the source."""
        return [edge for edge in self.edges if edge.source == entity]

    def get_incoming_relations(self, entity: Entity) -> List[Relation]:
        """Get all relations where entity is the target."""
        return [edge for edge in self.edges if edge.target == entity]

    def traverse(self) -> List[Entity]:
        """
        Traverse the graph to determine execution order.

        Returns a topologically sorted list of operation entities.
        Uses Kahn's algorithm for topological sorting.
        """
        # Build adjacency list and in-degree count
        adj_list: Dict[str, List[str]] = {node.id: [] for node in self.nodes}
        in_degree: Dict[str, int] = {node.id: 0 for node in self.nodes}
        node_map: Dict[str, Entity] = {node.id: node for node in self.nodes}

        for edge in self.edges:
            # SEQUENCE relations define execution order
            if edge.type == RelationType.SEQUENCE:
                adj_list[edge.source.id].append(edge.target.id)
                in_degree[edge.target.id] += 1
            # REQUIRES relations also define dependencies
            elif edge.type == RelationType.REQUIRES:
                adj_list[edge.target.id].append(edge.source.id)
                in_degree[edge.source.id] += 1

        # Start with nodes that have no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current_id = queue.pop(0)
            current_node = node_map[current_id]

            # Only include operation entities in execution order
            if current_node.type == EntityType.OPERATION:
                result.append(current_node)

            # Reduce in-degree for neighbors
            for neighbor_id in adj_list[current_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        return result

    def visualize(self) -> str:
        """
        Generate a text-based visualization of the graph.

        Returns a multi-line string representation.
        """
        lines = ["Semantic Graph Visualization", "=" * 50, ""]

        # Show entities by type
        lines.append("ENTITIES:")
        entity_types = set(node.type for node in self.nodes)
        for entity_type in sorted(entity_types, key=lambda x: x.value):
            entities = self.get_entities_by_type(entity_type)
            lines.append(f"\n  {entity_type.value.upper()} ({len(entities)}):")
            for entity in entities:
                lines.append(f"    - {entity.id}: {entity.text} = {entity.value}")

        # Show relations by type
        lines.append("\n\nRELATIONS:")
        relation_types = set(edge.type for edge in self.edges)
        for relation_type in sorted(relation_types, key=lambda x: x.value):
            relations = self.get_relations_by_type(relation_type)
            lines.append(f"\n  {relation_type.value.upper()} ({len(relations)}):")
            for relation in relations:
                lines.append(
                    f"    - {relation.source.id} -> {relation.target.id}"
                )

        # Show execution order
        lines.append("\n\nEXECUTION ORDER:")
        execution_order = self.traverse()
        for i, entity in enumerate(execution_order, 1):
            lines.append(f"  {i}. {entity.text} ({entity.value})")

        return "\n".join(lines)


class SemanticParser:
    """
    Advanced semantic parser for BioQL natural language queries.

    Extracts entities, relations, and builds semantic graphs for
    complex multi-step queries with coreference resolution and
    advanced linguistic features.
    """

    def __init__(self, use_spacy: bool = True):
        """
        Initialize the semantic parser.

        Args:
            use_spacy: Whether to use spaCy for NLP (requires installation)
        """
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        self.nlp = None
        self._entity_counter = 0

        if self.use_spacy:
            try:
                # Try to load English model
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model for semantic parsing")
            except OSError:
                logger.warning(
                    "spaCy model not found. Run: python -m spacy download en_core_web_sm"
                )
                self.use_spacy = False

        # Compile regex patterns for fallback parsing
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for entity extraction."""
        self.patterns = {
            # Molecular identifiers
            "pdb_id": re.compile(r"\b([1-9][A-Za-z0-9]{3})\b", re.IGNORECASE),
            "smiles": re.compile(r"\b([CONSPFHcnopsfh\[\]()@=#\-+\\\/]{5,})\b"),
            "sequence": re.compile(r"\b([ACDEFGHIKLMNPQRSTVWY]{6,})\b"),

            # Operations
            "dock": re.compile(r"\b(dock|docking|bind|binding)\b", re.IGNORECASE),
            "align": re.compile(r"\b(align|alignment|match)\b", re.IGNORECASE),
            "optimize": re.compile(r"\b(optimize|optimization|minimize)\b", re.IGNORECASE),
            "predict": re.compile(r"\b(predict|prediction|forecast)\b", re.IGNORECASE),
            "calculate": re.compile(r"\b(calculate|compute|determine)\b", re.IGNORECASE),
            "filter": re.compile(r"\b(filter|select|choose|where)\b", re.IGNORECASE),

            # Properties
            "affinity": re.compile(r"\b(affinity|binding\s+affinity)\b", re.IGNORECASE),
            "toxicity": re.compile(r"\b(toxic|toxicity)\b", re.IGNORECASE),
            "solubility": re.compile(r"\b(solubility|soluble)\b", re.IGNORECASE),
            "energy": re.compile(r"\b(energy|energies)\b", re.IGNORECASE),

            # Parameters
            "shots": re.compile(r"(\d+)\s*shots?", re.IGNORECASE),
            "poses": re.compile(r"(\d+)\s*poses?", re.IGNORECASE),
            "temperature": re.compile(r"(\d+(?:\.\d+)?)\s*[CKF°]", re.IGNORECASE),

            # Values and numbers
            "number": re.compile(r"-?\d+(?:\.\d+)?"),
            "comparison": re.compile(r"([<>=]=?|(?:less|greater|more)\s+than)"),

            # Quantifiers
            "quantifier_all": re.compile(r"\b(all|every|each)\b", re.IGNORECASE),
            "quantifier_any": re.compile(r"\b(any|some)\b", re.IGNORECASE),
            "quantifier_top": re.compile(r"\b(top|best|highest)\s+(\d+)\b", re.IGNORECASE),
            "quantifier_bottom": re.compile(r"\b(bottom|worst|lowest)\s+(\d+)\b", re.IGNORECASE),

            # Negation
            "negation": re.compile(r"\b(not|no|never|without|exclude)\b", re.IGNORECASE),

            # Conditionals
            "if": re.compile(r"\b(if|when|where|provided)\b", re.IGNORECASE),
            "then": re.compile(r"\b(then|do|perform)\b", re.IGNORECASE),

            # References (for coreference)
            "pronoun": re.compile(r"\b(it|its|that|this|them|those|these)\b", re.IGNORECASE),
            "definite": re.compile(r"\bthe\s+(\w+)\b", re.IGNORECASE),
        }

    def _generate_entity_id(self, entity_type: EntityType) -> str:
        """Generate a unique entity ID."""
        self._entity_counter += 1
        return f"{entity_type.value}_{self._entity_counter}"

    def parse_semantic_structure(self, text: str) -> SemanticGraph:
        """
        Parse text into a semantic graph.

        Args:
            text: Natural language query text

        Returns:
            SemanticGraph representing the query structure
        """
        logger.info(f"Parsing semantic structure: {text[:100]}...")

        graph = SemanticGraph()

        if self.use_spacy and self.nlp:
            # Use spaCy for advanced parsing
            doc = self.nlp(text)
            entities = self._extract_entities_spacy(doc)
            relations = self._extract_relations_spacy(doc, entities)
        else:
            # Fall back to regex-based parsing
            entities = self.extract_entities(text)
            relations = self.extract_relations(text, entities)

        # Build graph
        for entity in entities:
            graph.add_node(entity)

        for relation in relations:
            graph.add_edge(relation)

        # Resolve coreferences
        self.resolve_references(graph, text)

        # Extract conditional logic
        self._extract_conditionals(graph, text)

        logger.success(
            f"Parsed semantic graph: {len(graph.nodes)} entities, {len(graph.edges)} relations"
        )

        return graph

    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text using regex patterns.

        Args:
            text: Input text

        Returns:
            List of extracted entities
        """
        entities = []

        # Extract molecules
        for match in self.patterns["pdb_id"].finditer(text):
            entity = Entity(
                id=self._generate_entity_id(EntityType.PROTEIN),
                type=EntityType.PROTEIN,
                value=match.group(1),
                text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                metadata={"format": "pdb", "data_type": DataType.PROTEIN}
            )
            entities.append(entity)

        for match in self.patterns["smiles"].finditer(text):
            entity = Entity(
                id=self._generate_entity_id(EntityType.LIGAND),
                type=EntityType.LIGAND,
                value=match.group(1),
                text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                metadata={"format": "smiles", "data_type": DataType.LIGAND}
            )
            entities.append(entity)

        # Extract operations
        operation_patterns = {
            "dock": BioQLDomain.DOCKING,
            "align": BioQLDomain.ALIGNMENT,
            "optimize": BioQLDomain.OPTIMIZATION,
            "predict": "prediction",
            "calculate": "calculation",
            "filter": "filtering"
        }

        for pattern_name, operation_value in operation_patterns.items():
            for match in self.patterns[pattern_name].finditer(text):
                entity = Entity(
                    id=self._generate_entity_id(EntityType.OPERATION),
                    type=EntityType.OPERATION,
                    value=operation_value,
                    text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"operation_type": pattern_name}
                )
                entities.append(entity)

        # Extract properties
        property_patterns = ["affinity", "toxicity", "solubility", "energy"]
        for prop_name in property_patterns:
            for match in self.patterns[prop_name].finditer(text):
                entity = Entity(
                    id=self._generate_entity_id(EntityType.PROPERTY),
                    type=EntityType.PROPERTY,
                    value=prop_name,
                    text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                entities.append(entity)

        # Extract parameters
        parameter_patterns = ["shots", "poses", "temperature"]
        for param_name in parameter_patterns:
            for match in self.patterns[param_name].finditer(text):
                value_str = match.group(1)
                entity = Entity(
                    id=self._generate_entity_id(EntityType.PARAMETER),
                    type=EntityType.PARAMETER,
                    value={"name": param_name, "value": float(value_str)},
                    text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"parameter_name": param_name}
                )
                entities.append(entity)

        # Extract quantifiers
        for match in self.patterns["quantifier_top"].finditer(text):
            entity = Entity(
                id=self._generate_entity_id(EntityType.QUANTIFIER),
                type=EntityType.QUANTIFIER,
                value={"type": "top", "count": int(match.group(2))},
                text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end()
            )
            entities.append(entity)

        for match in self.patterns["quantifier_all"].finditer(text):
            entity = Entity(
                id=self._generate_entity_id(EntityType.QUANTIFIER),
                type=EntityType.QUANTIFIER,
                value={"type": "all"},
                text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end()
            )
            entities.append(entity)

        return entities

    def _extract_entities_spacy(self, doc: Doc) -> List[Entity]:
        """Extract entities using spaCy NLP."""
        entities = []

        # Extract named entities
        for ent in doc.ents:
            entity_type = EntityType.MOLECULE
            if ent.label_ in ["ORG", "PRODUCT"]:
                entity_type = EntityType.MOLECULE

            entity = Entity(
                id=self._generate_entity_id(entity_type),
                type=entity_type,
                value=ent.text,
                text=ent.text,
                start_pos=ent.start_char,
                end_pos=ent.end_char,
                metadata={"spacy_label": ent.label_}
            )
            entities.append(entity)

        # Extract verbs as operations
        for token in doc:
            if token.pos_ == "VERB":
                operation_type = self._verb_to_operation(token.lemma_)
                if operation_type:
                    entity = Entity(
                        id=self._generate_entity_id(EntityType.OPERATION),
                        type=EntityType.OPERATION,
                        value=operation_type,
                        text=token.text,
                        start_pos=token.idx,
                        end_pos=token.idx + len(token.text),
                        metadata={"lemma": token.lemma_, "pos": token.pos_}
                    )
                    entities.append(entity)

        # Fall back to regex for molecular identifiers
        regex_entities = self.extract_entities(doc.text)
        entities.extend(regex_entities)

        return entities

    def _verb_to_operation(self, verb_lemma: str) -> Optional[str]:
        """Map verb lemmas to operation types."""
        operation_map = {
            "dock": BioQLDomain.DOCKING.value,
            "bind": BioQLDomain.DOCKING.value,
            "align": BioQLDomain.ALIGNMENT.value,
            "match": BioQLDomain.ALIGNMENT.value,
            "optimize": BioQLDomain.OPTIMIZATION.value,
            "minimize": BioQLDomain.OPTIMIZATION.value,
            "predict": "prediction",
            "calculate": "calculation",
            "compute": "calculation",
            "filter": "filtering",
            "select": "filtering",
        }
        return operation_map.get(verb_lemma)

    def extract_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """
        Extract relations between entities.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of relations
        """
        relations = []

        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_pos)

        # Extract DOCK relations (ligand-receptor pairs)
        operations = [e for e in entities if e.type == EntityType.OPERATION]
        molecules = [e for e in entities if e.type in [EntityType.PROTEIN, EntityType.LIGAND, EntityType.MOLECULE]]

        for operation in operations:
            if operation.value == BioQLDomain.DOCKING.value:
                # Find nearest molecules
                ligands = [m for m in molecules if m.type == EntityType.LIGAND]
                proteins = [m for m in molecules if m.type == EntityType.PROTEIN]

                for ligand in ligands:
                    for protein in proteins:
                        relation = Relation(
                            type=RelationType.DOCK,
                            source=ligand,
                            target=protein,
                            metadata={"operation": operation.id}
                        )
                        relations.append(relation)

        # Extract PARAMETER_OF relations
        parameters = [e for e in entities if e.type == EntityType.PARAMETER]
        for param in parameters:
            # Find nearest operation
            nearest_op = self._find_nearest_entity(
                param, operations, lambda e: e.type == EntityType.OPERATION
            )
            if nearest_op:
                relation = Relation(
                    type=RelationType.PARAMETER_OF,
                    source=param,
                    target=nearest_op
                )
                relations.append(relation)

        # Extract PROPERTY_OF relations
        properties = [e for e in entities if e.type == EntityType.PROPERTY]
        for prop in properties:
            # Find nearest molecule or operation
            nearest = self._find_nearest_entity(
                prop, sorted_entities,
                lambda e: e.type in [EntityType.MOLECULE, EntityType.OPERATION]
            )
            if nearest:
                relation = Relation(
                    type=RelationType.PROPERTY_OF,
                    source=prop,
                    target=nearest
                )
                relations.append(relation)

        # Extract SEQUENCE relations (temporal ordering)
        for i in range(len(operations) - 1):
            if operations[i].start_pos < operations[i + 1].start_pos:
                relation = Relation(
                    type=RelationType.SEQUENCE,
                    source=operations[i],
                    target=operations[i + 1],
                    metadata={"order": i}
                )
                relations.append(relation)

        # Extract negation relations
        negation_matches = list(self.patterns["negation"].finditer(text))
        for match in negation_matches:
            neg_pos = match.start()
            # Find entity immediately after negation
            following_entities = [e for e in sorted_entities if e.start_pos > neg_pos]
            if following_entities:
                target = following_entities[0]
                # Create a negation entity
                neg_entity = Entity(
                    id=self._generate_entity_id(EntityType.CONDITION),
                    type=EntityType.CONDITION,
                    value="negation",
                    text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                relation = Relation(
                    type=RelationType.NEGATION,
                    source=neg_entity,
                    target=target
                )
                relations.append(relation)

        return relations

    def _extract_relations_spacy(self, doc: Doc, entities: List[Entity]) -> List[Relation]:
        """Extract relations using spaCy dependency parsing."""
        relations = []

        # Use dependency parsing to find relations
        for token in doc:
            # Find subject-verb-object patterns
            if token.pos_ == "VERB":
                subjects = [child for child in token.children if child.dep_ in ["nsubj", "nsubjpass"]]
                objects = [child for child in token.children if child.dep_ in ["dobj", "pobj"]]

                for subj in subjects:
                    for obj in objects:
                        # Find corresponding entities
                        subj_entity = self._find_entity_at_pos(entities, subj.idx)
                        obj_entity = self._find_entity_at_pos(entities, obj.idx)

                        if subj_entity and obj_entity:
                            relation_type = self._determine_relation_type(token.lemma_)
                            if relation_type:
                                relation = Relation(
                                    type=relation_type,
                                    source=subj_entity,
                                    target=obj_entity,
                                    metadata={"verb": token.lemma_}
                                )
                                relations.append(relation)

        # Fall back to regex-based relation extraction
        regex_relations = self.extract_relations(doc.text, entities)
        relations.extend(regex_relations)

        return relations

    def _determine_relation_type(self, verb_lemma: str) -> Optional[RelationType]:
        """Determine relation type from verb."""
        relation_map = {
            "dock": RelationType.DOCK,
            "bind": RelationType.DOCK,
            "calculate": RelationType.CALCULATE,
            "compute": RelationType.CALCULATE,
            "predict": RelationType.PREDICT,
            "filter": RelationType.FILTER,
            "select": RelationType.FILTER,
        }
        return relation_map.get(verb_lemma)

    def _find_entity_at_pos(self, entities: List[Entity], pos: int) -> Optional[Entity]:
        """Find entity at a specific text position."""
        for entity in entities:
            if entity.start_pos <= pos < entity.end_pos:
                return entity
        return None

    def _find_nearest_entity(
        self,
        entity: Entity,
        candidates: List[Entity],
        filter_fn=None
    ) -> Optional[Entity]:
        """Find the nearest entity to a given entity."""
        if filter_fn:
            candidates = [c for c in candidates if filter_fn(c)]

        if not candidates:
            return None

        # Find closest by position
        closest = min(
            candidates,
            key=lambda c: abs(c.start_pos - entity.start_pos)
        )
        return closest

    def resolve_references(self, graph: SemanticGraph, text: str, context: Optional[Dict] = None) -> None:
        """
        Resolve coreferences (pronouns and definite references).

        Args:
            graph: Semantic graph to update with resolved references
            text: Original text
            context: Optional context from previous queries
        """
        # Find reference entities (pronouns, "the protein", etc.)
        reference_patterns = ["pronoun", "definite"]
        references = []

        for pattern_name in reference_patterns:
            for match in self.patterns[pattern_name].finditer(text):
                ref_entity = Entity(
                    id=self._generate_entity_id(EntityType.REFERENCE),
                    type=EntityType.REFERENCE,
                    value=match.group(0),
                    text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"pattern": pattern_name}
                )
                references.append(ref_entity)

        # Resolve each reference to a concrete entity
        for ref in references:
            # Find most recent entity of compatible type before the reference
            candidates = [
                e for e in graph.nodes
                if e.start_pos < ref.start_pos
                and e.type in [EntityType.PROTEIN, EntityType.LIGAND, EntityType.MOLECULE]
            ]

            if candidates:
                # Take the most recent one
                target = max(candidates, key=lambda e: e.start_pos)

                # Add coreference relation
                relation = Relation(
                    type=RelationType.COREFERENCE,
                    source=ref,
                    target=target,
                    metadata={"resolved": True}
                )
                graph.add_edge(relation)

                logger.debug(f"Resolved reference '{ref.text}' to '{target.text}'")

    def _extract_conditionals(self, graph: SemanticGraph, text: str) -> None:
        """
        Extract conditional logic (if-then statements).

        Args:
            graph: Semantic graph to update
            text: Original text
        """
        # Find "if" keywords
        if_matches = list(self.patterns["if"].finditer(text))

        for if_match in if_matches:
            if_pos = if_match.start()

            # Look for comparison operations after "if"
            comparison_matches = [
                m for m in self.patterns["comparison"].finditer(text)
                if m.start() > if_pos
            ]

            if comparison_matches:
                # Create condition entity
                comp_match = comparison_matches[0]

                # Extract the full conditional clause
                end_pos = comp_match.end() + 20  # Look ahead for value
                conditional_text = text[if_pos:min(end_pos, len(text))]

                cond_entity = Entity(
                    id=self._generate_entity_id(EntityType.CONDITION),
                    type=EntityType.CONDITION,
                    value=conditional_text,
                    text=conditional_text,
                    start_pos=if_pos,
                    end_pos=end_pos
                )

                # Find entities involved in the condition
                involved_entities = [
                    e for e in graph.nodes
                    if if_pos < e.start_pos < end_pos
                ]

                # Link condition to involved entities
                for entity in involved_entities:
                    relation = Relation(
                        type=RelationType.CONDITIONAL,
                        source=cond_entity,
                        target=entity
                    )
                    graph.add_edge(relation)

                logger.debug(f"Extracted conditional: {conditional_text}")


# Convenience function
def parse_semantic(text: str, use_spacy: bool = True) -> SemanticGraph:
    """
    Convenience function to parse text into a semantic graph.

    Args:
        text: Natural language query
        use_spacy: Whether to use spaCy if available

    Returns:
        SemanticGraph instance
    """
    parser = SemanticParser(use_spacy=use_spacy)
    return parser.parse_semantic_structure(text)


__all__ = [
    "EntityType",
    "RelationType",
    "Entity",
    "Relation",
    "SemanticGraph",
    "SemanticParser",
    "parse_semantic"
]
