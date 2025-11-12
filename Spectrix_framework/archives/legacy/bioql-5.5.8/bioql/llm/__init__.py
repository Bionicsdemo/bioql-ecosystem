"""
BioQL LLM Integration Module
=============================

Multi-agent system for quantum code generation, optimization, and execution.

Features:
- Specialized BioQL code generation with LLMs (Claude, GPT, Local models)
- Multi-agent orchestration for complex quantum programs
- Hybrid compiler: Classical → Quantum automatic translation
- Auto-optimization of quantum circuits
- Quantum computer inference support

Architecture:
    User Intent
        ↓
    [Agent Orchestrator]
        ↓
    ┌────────────────────────────────┐
    │  Specialized Agents:           │
    │  - Code Generator Agent        │
    │  - Circuit Optimizer Agent     │
    │  - Error Correction Agent      │
    │  - Bioinformatics Expert Agent │
    │  - Hardware Selector Agent     │
    └────────────────────────────────┘
        ↓
    [Hybrid Compiler]
        ↓
    Classical → Quantum Translation
        ↓
    [Quantum Execution]
        ↓
    Results + Optimization Feedback

Usage:
    >>> from bioql.llm import QuantumCodeAgent, HybridCompiler
    >>>
    >>> # Generate quantum code from natural language
    >>> agent = QuantumCodeAgent(model="claude-3-5-sonnet")
    >>> code = agent.generate("Simulate drug binding to GLP1R receptor")
    >>>
    >>> # Hybrid compilation
    >>> compiler = HybridCompiler()
    >>> quantum_circuit = compiler.compile(classical_function)
    >>>
    >>> # Multi-agent orchestration
    >>> from bioql.llm import AgentOrchestrator
    >>> orchestrator = AgentOrchestrator()
    >>> result = orchestrator.execute("Design a new diabetes drug")
"""

from typing import Optional

__version__ = "3.1.0-alpha"

# Core agent imports
try:
    from .agents.code_generator import CodeGeneratorAgent
    from .agents.optimizer import CircuitOptimizerAgent
    from .agents.bioinformatics import BioinformaticsAgent
    from .agents.orchestrator import AgentOrchestrator
    _agents_available = True
except ImportError:
    _agents_available = False
    CodeGeneratorAgent = None
    CircuitOptimizerAgent = None
    BioinformaticsAgent = None
    AgentOrchestrator = None

# Model adapters
try:
    from .models.claude_adapter import ClaudeAdapter
    from .models.gpt_adapter import GPTAdapter
    from .models.ollama_adapter import OllamaAdapter
    _models_available = True
except ImportError:
    _models_available = False
    ClaudeAdapter = None
    GPTAdapter = None
    OllamaAdapter = None

# Hybrid compiler
try:
    from .optimizers.hybrid_compiler import HybridCompiler
    from .optimizers.auto_optimizer import AutoOptimizer
    _optimizer_available = True
except ImportError:
    _optimizer_available = False
    HybridCompiler = None
    AutoOptimizer = None

__all__ = [
    # Version
    "__version__",

    # Agents
    "CodeGeneratorAgent",
    "CircuitOptimizerAgent",
    "BioinformaticsAgent",
    "AgentOrchestrator",

    # Models
    "ClaudeAdapter",
    "GPTAdapter",
    "OllamaAdapter",

    # Optimizers
    "HybridCompiler",
    "AutoOptimizer",
]


def check_llm_availability() -> dict:
    """Check which LLM features are available."""
    return {
        "agents": _agents_available,
        "models": _models_available,
        "optimizers": _optimizer_available,
        "version": __version__
    }
