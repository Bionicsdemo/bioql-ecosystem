#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Semantic Parser Demo for BioQL

This script demonstrates the advanced semantic parsing capabilities,
including entity extraction, relation detection, coreference resolution,
and semantic graph visualization.
"""

import sys
from pathlib import Path

# Add bioql to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioql.parser import SemanticParser, parse_semantic


def demo_basic_parsing():
    """Demonstrate basic entity and relation extraction."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Entity and Relation Extraction")
    print("=" * 70)

    query = "Dock ligand CC(C)Cc1ccc(cc1)C(C)C to protein 1A2G with 10 poses"

    parser = SemanticParser(use_spacy=False)  # Use regex-based parsing
    graph = parser.parse_semantic_structure(query)

    print(f"\nQuery: {query}")
    print(f"\nExtracted {len(graph.nodes)} entities:")
    for node in graph.nodes:
        print(f"  - {node.type.value}: {node.text} = {node.value}")

    print(f"\nExtracted {len(graph.edges)} relations:")
    for edge in graph.edges:
        print(f"  - {edge.type.value}: {edge.source.text} -> {edge.target.text}")


def demo_multi_step_query():
    """Demonstrate multi-step query parsing with execution order."""
    print("\n" + "=" * 70)
    print("DEMO 2: Multi-Step Query with Execution Order")
    print("=" * 70)

    query = """
    Dock aspirin to protein 1A2G, then calculate binding affinity,
    and finally filter results with energy less than -8 kcal/mol
    """

    parser = SemanticParser(use_spacy=False)
    graph = parser.parse_semantic_structure(query)

    print(f"\nQuery: {query.strip()}")
    print(f"\nExtracted {len(graph.nodes)} entities")
    print(f"Extracted {len(graph.edges)} relations")

    print("\nExecution order:")
    execution_order = graph.traverse()
    for i, op in enumerate(execution_order, 1):
        print(f"  {i}. {op.text} ({op.value})")


def demo_coreference_resolution():
    """Demonstrate coreference resolution."""
    print("\n" + "=" * 70)
    print("DEMO 3: Coreference Resolution")
    print("=" * 70)

    query = """
    Load protein 1A2G and dock it with ligand CCCC.
    Then optimize the complex and calculate its binding energy.
    """

    parser = SemanticParser(use_spacy=False)
    graph = parser.parse_semantic_structure(query)

    print(f"\nQuery: {query.strip()}")

    # Find coreference relations
    coref_relations = graph.get_relations_by_type(
        parser.patterns and "COREFERENCE" in dir(parser) or None
    )

    print(f"\nExtracted {len(graph.nodes)} entities")
    print(f"Extracted {len(graph.edges)} relations")

    # Show entities by type
    from bioql.parser import EntityType

    proteins = graph.get_entities_by_type(EntityType.PROTEIN)
    ligands = graph.get_entities_by_type(EntityType.LIGAND)
    operations = graph.get_entities_by_type(EntityType.OPERATION)

    print(f"\nProteins: {[p.text for p in proteins]}")
    print(f"Ligands: {[l.text for l in ligands]}")
    print(f"Operations: {[o.text for o in operations]}")


def demo_quantifiers_and_filtering():
    """Demonstrate quantifier handling."""
    print("\n" + "=" * 70)
    print("DEMO 4: Quantifiers and Filtering")
    print("=" * 70)

    query = "Dock all ligands to 1A2G and select the top 5 results"

    parser = SemanticParser(use_spacy=False)
    graph = parser.parse_semantic_structure(query)

    print(f"\nQuery: {query}")

    from bioql.parser import EntityType

    quantifiers = graph.get_entities_by_type(EntityType.QUANTIFIER)

    print(f"\nExtracted quantifiers:")
    for q in quantifiers:
        print(f"  - {q.text}: {q.value}")


def demo_negation_handling():
    """Demonstrate negation detection."""
    print("\n" + "=" * 70)
    print("DEMO 5: Negation Handling")
    print("=" * 70)

    query = "Find molecules that are not toxic and have high solubility"

    parser = SemanticParser(use_spacy=False)
    graph = parser.parse_semantic_structure(query)

    print(f"\nQuery: {query}")

    from bioql.parser import RelationType

    negations = graph.get_relations_by_type(RelationType.NEGATION)

    print(f"\nDetected negations:")
    for neg in negations:
        print(f"  - NOT {neg.target.text}")


def demo_conditional_logic():
    """Demonstrate conditional logic extraction."""
    print("\n" + "=" * 70)
    print("DEMO 6: Conditional Logic")
    print("=" * 70)

    query = "Dock ligand to protein, and if affinity > -8 then optimize the complex"

    parser = SemanticParser(use_spacy=False)
    graph = parser.parse_semantic_structure(query)

    print(f"\nQuery: {query}")

    from bioql.parser import EntityType, RelationType

    conditionals = graph.get_relations_by_type(RelationType.CONDITIONAL)
    conditions = graph.get_entities_by_type(EntityType.CONDITION)

    print(f"\nDetected conditions:")
    for cond in conditions:
        print(f"  - {cond.text}")


def demo_graph_visualization():
    """Demonstrate semantic graph visualization."""
    print("\n" + "=" * 70)
    print("DEMO 7: Complete Semantic Graph Visualization")
    print("=" * 70)

    query = """
    Dock ligand CC(C)Cc1ccc(cc1)C(C)C to protein 1A2G with 10 poses,
    then calculate binding affinity and filter results where energy < -7
    """

    graph = parse_semantic(query, use_spacy=False)

    print(f"\nQuery: {query.strip()}\n")
    print(graph.visualize())


def demo_complex_workflow():
    """Demonstrate a complex multi-step workflow."""
    print("\n" + "=" * 70)
    print("DEMO 8: Complex Drug Discovery Workflow")
    print("=" * 70)

    query = """
    Load protein 3CL and all candidate ligands.
    Dock each ligand to the protein with 20 poses.
    Calculate binding affinity for all poses.
    Filter results where affinity > -9 and toxicity is not high.
    Select the top 10 candidates.
    Optimize the top candidates and predict their drug-likeness.
    """

    graph = parse_semantic(query, use_spacy=False)

    print(f"\nQuery: {query.strip()}\n")

    # Show summary
    from bioql.parser import EntityType

    print(f"Total entities: {len(graph.nodes)}")
    print(f"Total relations: {len(graph.edges)}")

    print("\nEntity breakdown:")
    for entity_type in EntityType:
        entities = graph.get_entities_by_type(entity_type)
        if entities:
            print(f"  {entity_type.value}: {len(entities)}")

    print("\nExecution plan:")
    execution_order = graph.traverse()
    for i, op in enumerate(execution_order, 1):
        print(f"  Step {i}: {op.text}")


def demo_with_spacy():
    """Demonstrate spaCy-enhanced parsing (if available)."""
    print("\n" + "=" * 70)
    print("DEMO 9: spaCy-Enhanced Parsing")
    print("=" * 70)

    query = "The protein binds to aspirin and forms a stable complex"

    try:
        parser = SemanticParser(use_spacy=True)
        if parser.use_spacy:
            graph = parser.parse_semantic_structure(query)
            print(f"\nQuery: {query}")
            print("\nspaCy parsing enabled - enhanced entity recognition active")
            print(f"Extracted {len(graph.nodes)} entities with NLP analysis")
        else:
            print("\nspaCy not available. Install with:")
            print("  pip install spacy")
            print("  python -m spacy download en_core_web_sm")
    except Exception as e:
        print(f"\nspaCy parsing failed: {e}")
        print("Falling back to regex-based parsing")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "BioQL Semantic Parser Demo" + " " * 27 + "║")
    print("║" + " " * 10 + "Advanced Natural Language Understanding" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")

    demos = [
        ("Basic Parsing", demo_basic_parsing),
        ("Multi-Step Query", demo_multi_step_query),
        ("Coreference Resolution", demo_coreference_resolution),
        ("Quantifiers", demo_quantifiers_and_filtering),
        ("Negation Handling", demo_negation_handling),
        ("Conditional Logic", demo_conditional_logic),
        ("Graph Visualization", demo_graph_visualization),
        ("Complex Workflow", demo_complex_workflow),
        ("spaCy Integration", demo_with_spacy),
    ]

    # Run all demos
    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Demo '{name}' failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("All demos completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
