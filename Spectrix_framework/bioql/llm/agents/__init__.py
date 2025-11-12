# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Multi-Agent System
========================

Specialized agents for quantum code generation and optimization.
"""

from typing import Optional

try:
    from .bioinformatics import BioinformaticsAgent
    from .code_generator import CodeGeneratorAgent
    from .optimizer import CircuitOptimizerAgent
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
