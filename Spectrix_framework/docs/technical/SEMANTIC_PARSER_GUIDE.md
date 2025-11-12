# BioQL Semantic Parser - Advanced Natural Language Understanding

## Overview

The BioQL Semantic Parser provides sophisticated semantic analysis of natural language queries for bioinformatics tasks. It builds semantic graphs that represent entities, relations, and dependencies in complex multi-step workflows.

**File Location:** `/Users/heinzjungbluth/Desktop/bioql/bioql/parser/semantic_parser.py`

## Key Features

### 1. **Entity Extraction**
Identifies and categorizes key components in natural language:

- **Molecules**: PDB IDs (1A2G), SMILES (CC(C)O), sequences
- **Proteins**: Protein structures and targets
- **Properties**: Binding affinity, toxicity, solubility, energy
- **Operations**: dock, align, optimize, predict, calculate, filter
- **Parameters**: shots, poses, temperature, optimization levels
- **Values**: Numerical values and units
- **Conditions**: Conditional logic expressions
- **Quantifiers**: all, any, top 10, bottom 5
- **References**: Coreference entities (it, the protein, that)

### 2. **Relation Detection**
Identifies relationships between entities:

- **DOCK**: Ligand-receptor binding relationships
- **CALCULATE**: Property calculation operations
- **PREDICT**: Prediction tasks
- **FILTER**: Filtering and selection criteria
- **SEQUENCE**: Temporal ordering of operations
- **PARAMETER_OF**: Parameters belonging to operations
- **PROPERTY_OF**: Properties of molecules/operations
- **TARGETS**: Operation targets
- **PRODUCES**: Output relationships
- **REQUIRES**: Dependency relationships
- **CONDITIONAL**: If-then logic
- **NEGATION**: Negated properties
- **COREFERENCE**: Reference resolution

### 3. **Semantic Graph Construction**
Builds a directed graph representing query structure:

- **Nodes**: Entities with metadata
- **Edges**: Relations between entities
- **Traversal**: Topologically sorted execution order
- **Visualization**: Text-based graph diagrams

### 4. **Advanced Language Features**

#### Coreference Resolution
Resolves pronouns and definite references to concrete entities:

```python
"Load protein 1A2G and dock it with ligand CCCC"
# "it" → resolves to "protein 1A2G"
```

#### Negation Handling
Detects and processes negations:

```python
"Find molecules that are not toxic"
# Identifies negation of "toxic" property
```

#### Conditional Logic
Extracts if-then statements:

```python
"If affinity > -8 then optimize the complex"
# Creates conditional relationship
```

#### Quantifiers
Processes quantification expressions:

```python
"Select the top 10 results"  # Top-N quantifier
"Process all ligands"        # Universal quantifier
"Find any match"             # Existential quantifier
```

## Core Classes

### SemanticParser

Main parser class for semantic analysis.

```python
from bioql.parser import SemanticParser

parser = SemanticParser(use_spacy=True)
graph = parser.parse_semantic_structure(query)
```

**Methods:**
- `parse_semantic_structure(text)` → SemanticGraph
- `extract_entities(text)` → List[Entity]
- `extract_relations(text, entities)` → List[Relation]
- `resolve_references(graph, text, context)` → None

### SemanticGraph

Graph representation of semantic structure.

```python
graph = SemanticGraph()
graph.add_node(entity)
graph.add_edge(relation)

# Query the graph
entities = graph.get_entities_by_type(EntityType.PROTEIN)
relations = graph.get_relations_by_type(RelationType.DOCK)

# Get execution order
execution_order = graph.traverse()

# Visualize
print(graph.visualize())
```

**Methods:**
- `add_node(entity)` - Add entity to graph
- `add_edge(relation)` - Add relation to graph
- `get_entities_by_type(type)` - Filter entities
- `get_relations_by_type(type)` - Filter relations
- `get_outgoing_relations(entity)` - Get outgoing edges
- `get_incoming_relations(entity)` - Get incoming edges
- `traverse()` - Topological sort for execution order
- `visualize()` - Generate text visualization

### Entity

Represents a semantic entity.

```python
entity = Entity(
    id="protein_1",
    type=EntityType.PROTEIN,
    value="1A2G",
    text="protein 1A2G",
    confidence=1.0,
    metadata={"format": "pdb"},
    start_pos=10,
    end_pos=22
)
```

**Attributes:**
- `id`: Unique identifier
- `type`: EntityType enum
- `value`: Extracted value
- `text`: Original text span
- `confidence`: Confidence score (0-1)
- `metadata`: Additional information
- `start_pos`: Character position in text
- `end_pos`: End position in text

### Relation

Represents a relationship between entities.

```python
relation = Relation(
    type=RelationType.DOCK,
    source=ligand_entity,
    target=protein_entity,
    confidence=1.0,
    metadata={"operation": "docking"}
)
```

**Attributes:**
- `type`: RelationType enum
- `source`: Source entity
- `target`: Target entity
- `confidence`: Confidence score
- `metadata`: Additional information

## Usage Examples

### Example 1: Basic Entity Extraction

```python
from bioql.parser import SemanticParser

parser = SemanticParser(use_spacy=False)
query = "Dock ligand CCCC to protein 1A2G with 10 poses"
graph = parser.parse_semantic_structure(query)

print(f"Entities: {len(graph.nodes)}")
for entity in graph.nodes:
    print(f"  {entity.type.value}: {entity.text}")
```

Output:
```
Entities: 3
  protein: 1A2G
  operation: Dock
  parameter: 10 poses
```

### Example 2: Multi-Step Workflow

```python
query = """
Dock ligand to protein 1A2G,
then calculate binding affinity,
and filter results where energy < -8
"""

graph = parser.parse_semantic_structure(query)

# Get execution order
execution_order = graph.traverse()
for i, op in enumerate(execution_order, 1):
    print(f"{i}. {op.text}")
```

Output:
```
1. Dock
2. calculate
3. filter
```

### Example 3: Coreference Resolution

```python
query = "Load protein 1A2G and dock it with ligand CCCC"

graph = parser.parse_semantic_structure(query)

# The parser automatically resolves "it" to "protein 1A2G"
coref_relations = graph.get_relations_by_type(RelationType.COREFERENCE)
for rel in coref_relations:
    print(f"'{rel.source.text}' → '{rel.target.text}'")
```

### Example 4: Graph Visualization

```python
from bioql.parser import parse_semantic

query = "Dock CCCC to 1A2G, then optimize and calculate affinity"
graph = parse_semantic(query, use_spacy=False)

print(graph.visualize())
```

Output:
```
Semantic Graph Visualization
==================================================

ENTITIES:

  PROTEIN (1):
    - protein_1: 1A2G = 1A2G

  OPERATION (3):
    - operation_2: Dock = docking
    - operation_3: optimize = optimization
    - operation_4: calculate = calculation

  PROPERTY (1):
    - property_5: affinity = affinity

RELATIONS:

  SEQUENCE (2):
    - operation_2 -> operation_3
    - operation_3 -> operation_4

  PROPERTY_OF (1):
    - property_5 -> operation_4

EXECUTION ORDER:
  1. Dock (docking)
  2. optimize (optimization)
  3. calculate (calculation)
```

### Example 5: Complex Query with Quantifiers

```python
query = """
Dock all candidate ligands to protein 3CL.
Calculate binding affinity for each result.
Filter out molecules that are toxic.
Select the top 10 candidates by affinity.
"""

graph = parser.parse_semantic_structure(query)

from bioql.parser import EntityType
quantifiers = graph.get_entities_by_type(EntityType.QUANTIFIER)
for q in quantifiers:
    print(f"Quantifier: {q.text} → {q.value}")
```

## Integration with Existing Parsers

The semantic parser integrates seamlessly with existing BioQL parsers:

```python
from bioql.parser import (
    NaturalLanguageParser,  # Pattern-based parser
    SemanticParser,         # Semantic graph parser
    LLMParser              # LLM-powered parser (if available)
)

# Use semantic parser for analysis
semantic_parser = SemanticParser()
graph = semantic_parser.parse_semantic_structure(query)

# Use NL parser for IR generation
nl_parser = NaturalLanguageParser()
program = nl_parser.parse(query)

# Combined approach
execution_order = graph.traverse()
# Use execution_order to guide program construction
```

## spaCy Integration

For enhanced NLP capabilities, install spaCy:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

Then enable spaCy in the parser:

```python
parser = SemanticParser(use_spacy=True)
```

With spaCy enabled:
- Better entity recognition
- Dependency parsing for relations
- Part-of-speech tagging
- Named entity recognition
- Improved coreference resolution

## Entity Types Reference

```python
class EntityType(str, Enum):
    MOLECULE = "molecule"      # Generic molecule
    PROTEIN = "protein"        # Protein structure
    LIGAND = "ligand"          # Small molecule ligand
    PROPERTY = "property"      # Molecular property
    OPERATION = "operation"    # Computational operation
    PARAMETER = "parameter"    # Operation parameter
    VALUE = "value"            # Numerical value
    CONDITION = "condition"    # Conditional expression
    QUANTIFIER = "quantifier"  # Quantification
    REFERENCE = "reference"    # Coreference entity
```

## Relation Types Reference

```python
class RelationType(str, Enum):
    DOCK = "dock"              # Docking relation
    CALCULATE = "calculate"    # Calculation relation
    PREDICT = "predict"        # Prediction relation
    FILTER = "filter"          # Filtering relation
    SEQUENCE = "sequence"      # Temporal ordering
    PARAMETER_OF = "parameter_of"  # Parameter ownership
    PROPERTY_OF = "property_of"    # Property ownership
    TARGETS = "targets"        # Operation target
    PRODUCES = "produces"      # Output relation
    REQUIRES = "requires"      # Dependency relation
    CONDITIONAL = "conditional"    # Conditional logic
    NEGATION = "negation"      # Negation relation
    COREFERENCE = "coreference"    # Reference resolution
```

## Pattern Matching Reference

The semantic parser uses comprehensive regex patterns:

- **Molecular IDs**: PDB (1A2G), SMILES, sequences
- **Operations**: dock, align, optimize, predict, calculate, filter
- **Properties**: affinity, toxicity, solubility, energy
- **Parameters**: shots, poses, temperature
- **Quantifiers**: all, any, top N, bottom N
- **Negation**: not, no, never, without, exclude
- **Conditionals**: if, when, where, provided, then
- **References**: it, that, this, the [noun]

## Performance Considerations

- **Regex mode** (default): Fast, no dependencies, good for simple queries
- **spaCy mode**: Slower but more accurate, requires installation
- **Graph traversal**: O(V + E) complexity using Kahn's algorithm
- **Entity matching**: Linear scan with position-based optimization

## Error Handling

```python
try:
    graph = parser.parse_semantic_structure(query)
except Exception as e:
    logger.error(f"Parsing failed: {e}")
    # Fallback to basic pattern matching
```

## Testing

Run the comprehensive demo:

```bash
cd /Users/heinzjungbluth/Desktop/bioql
python examples/semantic_parser_demo.py
```

## API Summary

### Main Functions

```python
# Convenience function
from bioql.parser import parse_semantic

graph = parse_semantic(text, use_spacy=True)
```

### Core Classes

```python
from bioql.parser import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    SemanticGraph,
    SemanticParser
)
```

## Future Enhancements

Planned improvements:
- Neural coreference resolution
- Temporal relation extraction
- Multi-sentence context handling
- Knowledge graph integration
- Confidence scoring with ML
- Interactive graph editing
- Export to visualization tools (GraphViz, Cytoscape)

## Contributing

To extend the semantic parser:

1. Add new entity types to `EntityType` enum
2. Add new relation types to `RelationType` enum
3. Update pattern dictionary in `_compile_patterns()`
4. Add extraction logic in `extract_entities()` or `extract_relations()`
5. Add tests in demo script

## Support

For issues or questions:
- Check the demo script: `examples/semantic_parser_demo.py`
- Review this guide: `docs/SEMANTIC_PARSER_GUIDE.md`
- Examine source code: `bioql/parser/semantic_parser.py`

---

**Version:** 1.0.0
**Last Updated:** October 2025
**Status:** Production Ready ✅
