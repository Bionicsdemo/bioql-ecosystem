"""
Compiler Factory for BioQL

This module provides a factory for creating backend-specific compilers.
"""

from typing import Type

# Optional loguru import
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from bioql.ir import QuantumBackend
from .base import BaseCompiler, CompilationError
from .cirq_compiler import CirqCompiler
from .qiskit_compiler import QiskitCompiler


class CompilerFactory:
    """Factory for creating backend-specific compilers."""

    _compilers = {
        QuantumBackend.QISKIT: QiskitCompiler,
        QuantumBackend.CIRQ: CirqCompiler,
        QuantumBackend.SIMULATOR: QiskitCompiler,  # Default to Qiskit for simulator
    }

    @classmethod
    def create_compiler(cls, backend: QuantumBackend) -> BaseCompiler:
        """
        Create a compiler for the specified backend.

        Args:
            backend: Target quantum backend

        Returns:
            Compiler instance

        Raises:
            CompilationError: If backend is not supported
        """
        if backend not in cls._compilers:
            raise CompilationError(f"Unsupported backend: {backend}")

        compiler_class = cls._compilers[backend]
        try:
            return compiler_class()
        except Exception as e:
            logger.error(f"Failed to create compiler for {backend}: {e}")
            # Fallback to simulator
            if backend != QuantumBackend.SIMULATOR:
                logger.warning(f"Falling back to simulator for {backend}")
                return cls._compilers[QuantumBackend.SIMULATOR]()
            raise CompilationError(f"Failed to create compiler: {e}")

    @classmethod
    def register_compiler(cls, backend: QuantumBackend, compiler_class: Type[BaseCompiler]) -> None:
        """
        Register a new compiler for a backend.

        Args:
            backend: Target quantum backend
            compiler_class: Compiler class
        """
        cls._compilers[backend] = compiler_class
        logger.info(f"Registered compiler {compiler_class.__name__} for backend {backend}")

    @classmethod
    def get_supported_backends(cls) -> list[QuantumBackend]:
        """Get list of supported backends."""
        return list(cls._compilers.keys())


# Convenience function
def create_compiler(backend: QuantumBackend) -> BaseCompiler:
    """
    Convenience function to create a compiler.

    Args:
        backend: Target quantum backend

    Returns:
        Compiler instance
    """
    return CompilerFactory.create_compiler(backend)


# Export main classes and functions
__all__ = [
    "CompilerFactory",
    "create_compiler"
]