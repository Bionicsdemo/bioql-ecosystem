"""
BioQL Natural Language Parser Module

This module provides natural language parsing capabilities for BioQL,
including pattern-based, LLM-powered, and semantic parsers.
"""

# Core parser imports (always available)
from .nl_parser import (
    MoleculeExtractor,
    NaturalLanguageParser,
    ParameterExtractor,
    ParseError,
    PatternMatcher,
)

# Semantic parser imports (always available)
from .semantic_parser import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    SemanticGraph,
    SemanticParser,
    parse_semantic,
)

# Optional LLM parser imports (requires additional dependencies)
try:
    from .llm_parser import (
        HybridParser,
        LLMConfig,
        LLMParser,
        LLMParsingError,
        parse_natural_language,
    )
    _llm_parser_available = True
except ImportError:
    _llm_parser_available = False
    # Provide stub classes
    HybridParser = None
    LLMConfig = None
    LLMParser = None
    LLMParsingError = None
    parse_natural_language = None

__all__ = [
    # Core parsing classes
    "NaturalLanguageParser",
    "PatternMatcher",
    "MoleculeExtractor",
    "ParameterExtractor",
    "ParseError",
    # Semantic parsing classes
    "Entity",
    "EntityType",
    "Relation",
    "RelationType",
    "SemanticGraph",
    "SemanticParser",
    "parse_semantic",
]

# Add LLM parser exports if available
if _llm_parser_available:
    __all__.extend([
        "LLMConfig",
        "LLMParser",
        "LLMParsingError",
        "HybridParser",
        "parse_natural_language",
    ])