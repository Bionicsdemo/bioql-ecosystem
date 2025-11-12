"""
Quantum adapters for CRISPR-QAI energy calculations

Provides backends for:
- Local simulator (built-in Ising model)
- AWS Braket (SV1, DM1)
- IBM Qiskit (Aer, IBM Runtime)
"""

from .base import QuantumEngine
from .simulator import LocalSimulatorEngine

try:
    from .braket_adapter import BraketEngine
    HAVE_BRAKET = True
except ImportError:
    HAVE_BRAKET = False

try:
    from .qiskit_adapter import QiskitEngine
    HAVE_QISKIT = True
except ImportError:
    HAVE_QISKIT = False

__all__ = ['QuantumEngine', 'LocalSimulatorEngine']

if HAVE_BRAKET:
    __all__.append('BraketEngine')

if HAVE_QISKIT:
    __all__.append('QiskitEngine')
