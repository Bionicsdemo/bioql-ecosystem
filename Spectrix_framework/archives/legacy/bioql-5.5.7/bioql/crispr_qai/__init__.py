"""
BioQL CRISPR-QAI Module v1.1.0
Quantum-enhanced CRISPR design and clinical therapy development

This module provides quantum computing capabilities for:
- gRNA energy collapse estimation (DNA-Cas9 affinity)
- Guide sequence optimization and ranking
- Off-target phenotype inference and CFD scoring
- Safety-first simulation (no wet-lab execution)
- Clinical therapy design (20+ genes, AAV/LNP delivery)
- IND-ready regulatory documentation
- Real gene sequences from NCBI database

Compatible with:
- AWS Braket (SV1, DM1)
- IBM Qiskit (Aer, IBM Runtime)
- Local simulator (built-in)

Author: BioQL Team
License: Proprietary
"""

__version__ = "1.1.0"

# Core imports
from .featurization import encode_guide_sequence, guide_to_angles
from .energies import (
    estimate_energy_collapse_simulator,
    estimate_energy_collapse_braket,
    estimate_energy_collapse_qiskit,
    compute_classical_baseline,
    generate_decoy_sequences,
    compute_normalized_energy,
    estimate_with_uncertainty
)
from .guide_opt import rank_guides_batch
from .phenotype import infer_offtarget_phenotype
from .io import load_guides_csv, save_results_csv
from .safety import check_simulation_only

# Clinical therapy design imports (NEW in v1.1.0)
from .ncbi_gene_fetcher import NCBIGeneFetcher
from .offtarget_predictor import OffTargetPredictor, get_precision_limits
from .delivery_systems import DeliverySystemDesigner
from .regulatory_docs import RegulatoryDocGenerator

# Adapter imports
from .adapters.base import QuantumEngine
from .adapters.simulator import LocalSimulatorEngine
try:
    from .adapters.braket_adapter import BraketEngine
    HAVE_BRAKET = True
except ImportError:
    HAVE_BRAKET = False

try:
    from .adapters.qiskit_adapter import QiskitEngine
    HAVE_QISKIT = True
except ImportError:
    HAVE_QISKIT = False

# Public API
__all__ = [
    # Featurization
    'encode_guide_sequence',
    'guide_to_angles',

    # Energy estimation
    'estimate_energy_collapse_simulator',
    'estimate_energy_collapse_braket',
    'estimate_energy_collapse_qiskit',
    'compute_classical_baseline',           # NEW: Classical baseline calibration
    'generate_decoy_sequences',             # NEW: Decoy controls for z-score
    'compute_normalized_energy',            # NEW: ΔE, z-score, percentile
    'estimate_with_uncertainty',            # NEW: Mean ± SD, multi-repeat

    # Optimization
    'rank_guides_batch',

    # Phenotype inference
    'infer_offtarget_phenotype',

    # I/O
    'load_guides_csv',
    'save_results_csv',

    # Safety
    'check_simulation_only',

    # Clinical therapy design (NEW in v1.1.0)
    'NCBIGeneFetcher',
    'OffTargetPredictor',
    'get_precision_limits',                 # NEW: In-silico precision limits
    'DeliverySystemDesigner',
    'RegulatoryDocGenerator',

    # Adapters
    'QuantumEngine',
    'LocalSimulatorEngine',
]

if HAVE_BRAKET:
    __all__.append('BraketEngine')

if HAVE_QISKIT:
    __all__.append('QiskitEngine')
