"""
BioQL Multi-Agent System
========================

Specialized agents for quantum code generation and optimization.
"""

from typing import Optional

try:
    from .code_generator import CodeGeneratorAgent
    from .optimizer import CircuitOptimizerAgent
    from .bioinformatics import BioinformaticsAgent
    from .orchestrator import AgentOrchestrator
    _available = True
except ImportError:
    _available = False
    CodeGeneratorAgent = None
    CircuitOptimizerAgent = None
    BioinformaticsAgent = None
    AgentOrchestrator = None

__all__ = [
    "CodeGeneratorAgent",
    "CircuitOptimizerAgent",
    "BioinformaticsAgent",
    "AgentOrchestrator",
]
