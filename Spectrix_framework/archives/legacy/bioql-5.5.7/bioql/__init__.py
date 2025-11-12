#!/usr/bin/env python3
"""
BioQL v5.0.1: Enterprise Quantum Computing with Full QEC Control

BioQL is a quantum computing framework specifically designed for bioinformatics
applications. It provides a natural language interface for quantum programming
and integrates with popular quantum computing backends.

🆕 NEW in v5.0.1 - AWS BRAKET EXAMPLES:
- **AWS Braket Setup Scripts**: Complete automated setup for Amazon Braket
- **Example Circuits**: Bell state, GHZ, and more in OpenQASM 3.0
- **Integration Guides**: Step-by-step AWS Braket + BioQL integration
- **Verified Results**: 100% quantum entanglement confirmed on SV1

🚀 FEATURES from v5.0.0 - FULL QEC CONTROL EDITION:
- **Full Qubit Management**: Control physical vs logical qubits explicitly
- **Advanced QEC Codes**: Surface Code, Steane Code, Shor Code implementations
- **Qualtran Visualization**: Resource estimation and QEC overhead graphs
- **Error Mitigation**: ZNE, PEC, readout calibration, symmetry verification
- **QEC Metrics**: Comprehensive fidelity and error rate tracking
- **Dynamic Pricing**: QEC overhead cost calculation with multipliers
- **Target Fidelity**: Set minimum fidelity requirements (95-99.9%)

Previous features (v4.1.0):
- Quantum Error Correction (QEC) Module - Target 95-100% accuracy
  * OpenFermion: Molecular Hamiltonians (H2, LiH, H2O, N2, BeH2)
  * Qualtran: QEC gates cost analysis, RSA ModExp factorization
  * Advanced error mitigation: ZNE, PEC, readout correction, symmetry
- Multi-backend support: IBM Torino (133 qubits), IonQ, AWS Braket
- Error mitigation strategies (readout error, ZNE, PEC)
- Provenance & compliance logging (21 CFR Part 11 aligned)
- Cryptographic audit trails with signed records
- Reproducibility tracking with full parameter logging
- Chemistry benchmarks vs. literature (H2, LiH, H2O, BeH2, N2)

✨ Features from v3.1.0:
- Performance profiling system with <5% overhead
- Interactive HTML dashboards with Plotly charts
- Circuit optimization (35% gate/depth reduction)
- Smart caching (24x speedup with 70% hit rate)
- Intelligent job batching (18-30% cost savings)
- Pre-built circuit library (Grover, VQE, QAOA, drug discovery templates)
- Enhanced semantic NL parsing with context awareness
- Circuit composition and stitching tools

Main Features:
- Natural language quantum programming (164B+ patterns!)
- Advanced profiling and performance optimization
- Circuit library with drug discovery templates
- Integration with Qiskit and other quantum backends
- Biological interpretation of quantum results
- Cloud authentication & billing system
- Drug discovery and protein folding support

Basic Usage:
    >>> from bioql import quantum, QuantumResult
    >>> from bioql.profiler import Profiler
    >>> from bioql.error_mitigation import mitigate_counts
    >>> from bioql.provenance import enable_compliance_logging
    >>> from bioql.benchmarks import quick_benchmark
    >>>
    >>> # Enable compliance logging
    >>> enable_compliance_logging()
    >>>
    >>> # Profile quantum execution
    >>> profiler = Profiler()
    >>> result = profiler.profile_quantum("dock aspirin to COX-1", api_key="bioql_...")
    >>>
    >>> # Apply error mitigation
    >>> mitigated = mitigate_counts(result.counts, num_qubits=4)
    >>>
    >>> # Run chemistry benchmark
    >>> benchmark = quick_benchmark("H2", backend="simulator")
    >>> print(f"Accuracy: {100 - abs(benchmark.relative_error):.1f}%")
    >>>
    >>> # Use circuit library
    >>> from bioql.circuits import VQECircuit, get_catalog
    >>> vqe = VQECircuit(hamiltonian="H2")
    >>> circuit = vqe.build(num_qubits=4, num_layers=2)

QEC Module Usage (NEW in v4.0.0):
    >>> from bioql import quick_chemistry_test, quick_qec_demo, demo_error_mitigation
    >>>
    >>> # OpenFermion: Quantum chemistry
    >>> h2 = quick_chemistry_test('H2')
    >>> print(f"Energy: {h2.energy_ground_state:.4f} Hartrees")
    >>> print(f"Accuracy: {h2.accuracy_percent:.1f}%")
    >>>
    >>> # Qualtran: QEC analysis & RSA ModExp
    >>> qec_result, rsa_result = quick_qec_demo()
    >>> print(f"Qubits: {qec_result.num_logical_qubits} → {qec_result.num_physical_qubits}")
    >>> print(f"RSA factorization cost: {rsa_result.qec_gates_cost}")
    >>>
    >>> # Advanced error mitigation
    >>> em = demo_error_mitigation()
    >>> print(f"Accuracy: {em.accuracy_original:.1f}% → {em.accuracy_mitigated:.1f}%")
"""

__version__ = "5.5.8"
__author__ = "BioQL Development Team / SpectrixRD"
__email__ = "bioql@spectrixrd.com"
__license__ = "MIT"

# Core imports
from .quantum_connector import (
    quantum,
    QuantumResult,
    QuantumSimulator,
    BioQLError,
    QuantumBackendError,
    ProgramParsingError,
    list_available_backends
)

# DevKit enhanced features
try:
    from .enhanced_quantum import enhanced_quantum
except ImportError:
    enhanced_quantum = None

# Optional imports with graceful fallbacks
try:
    from .compiler import compile_bioql
except ImportError:
    compile_bioql = None

try:
    from .bio_interpreter import interpret_bio_results
except ImportError:
    interpret_bio_results = None

try:
    from .quantum_chemistry import (
        QuantumMolecule,
        smiles_to_geometry,
        build_molecular_hamiltonian,
        validate_hamiltonian,
        hamiltonian_to_qiskit,
        auto_select_active_space
    )
except ImportError:
    QuantumMolecule = None
    smiles_to_geometry = None
    build_molecular_hamiltonian = None
    validate_hamiltonian = None
    hamiltonian_to_qiskit = None
    auto_select_active_space = None

try:
    from .molecular_benchmarks import (
        run_benchmark,
        run_all_benchmarks,
        BENCHMARK_MOLECULES,
        BenchmarkResult
    )
except ImportError:
    run_benchmark = None
    run_all_benchmarks = None
    BENCHMARK_MOLECULES = None
    BenchmarkResult = None

# NEW in v5.3.0 - Auditable logging system
try:
    from .auditable_logs import (
        HardwareExecution,
        DockingExecution,
        PostprocessExecution,
        QualtranVisualization,
        AuditableSession,
        configure_audit_logging
    )
except ImportError:
    HardwareExecution = None
    DockingExecution = None
    PostprocessExecution = None
    QualtranVisualization = None
    AuditableSession = None
    configure_audit_logging = None

# NEW in v5.3.0 - Real molecular docking with Vina
try:
    from .docking.real_vina import (
        dock_smiles_to_receptor,
        VinaResult,
        VinaPose,
        HAVE_RDKIT,
        HAVE_MEEKO,
        VINA_BIN
    )
except ImportError:
    dock_smiles_to_receptor = None
    VinaResult = None
    VinaPose = None
    HAVE_RDKIT = False
    HAVE_MEEKO = False
    VINA_BIN = None

# NEW in v5.3.0 - Quantum-classical fusion (NO modifica energías)
try:
    from .quantum_fusion import (
        extract_quantum_features,
        correlate_quantum_classical,
        analyze_quantum_noise,
        QuantumFeatures
    )
except ImportError:
    extract_quantum_features = None
    correlate_quantum_classical = None
    analyze_quantum_noise = None
    QuantumFeatures = None

try:
    from .logger import get_logger, configure_logging
except ImportError:
    get_logger = None
    configure_logging = None

# Dynamic library bridge (NEW - meta-wrapper for any Python library)
try:
    from .dynamic_bridge import dynamic_call, register_library
except ImportError:
    dynamic_call = None
    register_library = None

# NEW in v3.1.2+ Enterprise features (optional)
try:
    from .error_mitigation import (
        ErrorMitigator,
        ReadoutErrorMitigation,
        mitigate_counts
    )
except ImportError:
    ErrorMitigator = None
    ReadoutErrorMitigation = None
    mitigate_counts = None

try:
    from .provenance import (
        ProvenanceRecord,
        ProvenanceChain,
        ComplianceLogger,
        enable_compliance_logging,
        get_compliance_logger
    )
except ImportError:
    ProvenanceRecord = None
    ProvenanceChain = None
    ComplianceLogger = None
    enable_compliance_logging = None
    get_compliance_logger = None

try:
    from .benchmarks import (
        ChemistryBenchmark,
        BenchmarkResult,
        BenchmarkSuite,
        quick_benchmark,
        LITERATURE_DATA
    )
except ImportError:
    ChemistryBenchmark = None
    BenchmarkResult = None
    BenchmarkSuite = None
    quick_benchmark = None
    LITERATURE_DATA = None

# NEW in v4.0.0 - Quantum Error Correction (QEC) Module
try:
    from .chemistry_qec import (
        QuantumChemistry,
        MoleculeResult,
        quick_chemistry_test
    )
except ImportError:
    QuantumChemistry = None
    MoleculeResult = None
    quick_chemistry_test = None

try:
    from .qualtran_qec import (
        QuantumErrorCorrection,
        QECAnalysisResult,
        RSAModExpResult,
        quick_qec_demo
    )
except ImportError:
    QuantumErrorCorrection = None
    QECAnalysisResult = None
    RSAModExpResult = None
    quick_qec_demo = None

try:
    from .advanced_qec import (
        AdvancedErrorMitigation,
        ErrorMitigationResult,
        demo_error_mitigation
    )
except ImportError:
    AdvancedErrorMitigation = None
    ErrorMitigationResult = None
    demo_error_mitigation = None

# NEW in v5.0.0 - Full QEC Control & Visualization
try:
    from .qec import (
        SurfaceCodeQEC,
        SteaneCodeQEC,
        ShorCodeQEC,
        ErrorMitigation,
        QECMetrics
    )
except ImportError:
    SurfaceCodeQEC = None
    SteaneCodeQEC = None
    ShorCodeQEC = None
    ErrorMitigation = None
    QECMetrics = None

try:
    from .visualization import (
        QECVisualizer,
        ResourceEstimator,
        ResourceEstimation
    )
except ImportError:
    QECVisualizer = None
    ResourceEstimator = None
    ResourceEstimation = None

# NEW in v5.4.3 - CRISPR-QAI Module
try:
    from .crispr_qai import (
        # Featurization
        encode_guide_sequence,
        guide_to_angles,
        # Energy estimation
        estimate_energy_collapse_simulator,
        estimate_energy_collapse_braket,
        estimate_energy_collapse_qiskit,
        # Optimization
        rank_guides_batch,
        # Phenotype inference
        infer_offtarget_phenotype,
        # I/O
        load_guides_csv,
        save_results_csv,
        # Safety
        check_simulation_only,
        # Adapters
        QuantumEngine,
        LocalSimulatorEngine,
    )
    HAVE_CRISPR_QAI = True
except ImportError:
    # CRISPR-QAI not available
    encode_guide_sequence = None
    guide_to_angles = None
    estimate_energy_collapse_simulator = None
    estimate_energy_collapse_braket = None
    estimate_energy_collapse_qiskit = None
    rank_guides_batch = None
    infer_offtarget_phenotype = None
    load_guides_csv = None
    save_results_csv = None
    check_simulation_only = None
    QuantumEngine = None
    LocalSimulatorEngine = None
    HAVE_CRISPR_QAI = False

# Define what gets exported when using "from bioql import *"
__all__ = [
    # Core functionality
    "quantum",
    "QuantumResult",
    "QuantumSimulator",

    # Exceptions
    "BioQLError",
    "QuantumBackendError",
    "ProgramParsingError",

    # Version and metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]

# Add optional exports if available
if compile_bioql is not None:
    __all__.append("compile_bioql")

if interpret_bio_results is not None:
    __all__.append("interpret_bio_results")

if get_logger is not None and configure_logging is not None:
    __all__.extend(["get_logger", "configure_logging"])

if enhanced_quantum is not None:
    __all__.append("enhanced_quantum")

if dynamic_call is not None:
    __all__.extend(["dynamic_call", "register_library"])

# Add v3.1.2+ enterprise features if available
if ErrorMitigator is not None:
    __all__.extend(["ErrorMitigator", "ReadoutErrorMitigation", "mitigate_counts"])

if ComplianceLogger is not None:
    __all__.extend([
        "ProvenanceRecord", "ProvenanceChain", "ComplianceLogger",
        "enable_compliance_logging", "get_compliance_logger"
    ])

if ChemistryBenchmark is not None:
    __all__.extend([
        "ChemistryBenchmark", "BenchmarkResult", "BenchmarkSuite",
        "quick_benchmark", "LITERATURE_DATA"
    ])

# Add QEC modules if available
if QuantumChemistry is not None:
    __all__.extend([
        "QuantumChemistry", "MoleculeResult", "quick_chemistry_test"
    ])

if QuantumErrorCorrection is not None:
    __all__.extend([
        "QuantumErrorCorrection", "QECAnalysisResult", "RSAModExpResult",
        "quick_qec_demo"
    ])

if AdvancedErrorMitigation is not None:
    __all__.extend([
        "AdvancedErrorMitigation", "ErrorMitigationResult", "demo_error_mitigation"
    ])

# Add CRISPR-QAI modules if available
if HAVE_CRISPR_QAI:
    __all__.extend([
        # Featurization
        "encode_guide_sequence",
        "guide_to_angles",
        # Energy estimation
        "estimate_energy_collapse_simulator",
        "estimate_energy_collapse_braket",
        "estimate_energy_collapse_qiskit",
        # Optimization
        "rank_guides_batch",
        # Phenotype inference
        "infer_offtarget_phenotype",
        # I/O
        "load_guides_csv",
        "save_results_csv",
        # Safety
        "check_simulation_only",
        # Adapters
        "QuantumEngine",
        "LocalSimulatorEngine",
    ])


def get_version() -> str:
    """Return the current version of BioQL."""
    return __version__


def get_info() -> dict:
    """Return information about the BioQL installation."""
    info = {
        "version": __version__,
        "author": __author__,
        "license": __license__,
        "python_version": None,
        "qiskit_available": False,
        "optional_modules": {}
    }

    # Check Python version
    import sys
    info["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Check Qiskit availability
    try:
        import qiskit
        info["qiskit_available"] = True
        info["qiskit_version"] = qiskit.__version__
    except ImportError:
        pass

    # Check optional modules
    info["optional_modules"]["compiler"] = compile_bioql is not None
    info["optional_modules"]["bio_interpreter"] = interpret_bio_results is not None
    info["optional_modules"]["logger"] = get_logger is not None

    return info


def check_installation() -> bool:
    """
    Check if BioQL is properly installed with all dependencies.

    Returns:
        True if installation is complete, False otherwise
    """
    try:
        # Check core quantum functionality
        result = quantum("test installation", shots=10)
        return result.success
    except Exception:
        return False


def configure_debug_mode(enabled: bool = True) -> None:
    """
    Enable or disable debug mode globally for BioQL.

    Args:
        enabled: Whether to enable debug mode
    """
    import logging

    if enabled:
        logging.basicConfig(level=logging.DEBUG)
        print("BioQL debug mode enabled")
    else:
        logging.basicConfig(level=logging.INFO)
        print("BioQL debug mode disabled")


# Package initialization message
def _show_startup_info():
    """Show startup information when the package is imported."""
    import warnings

    # Check if qiskit is available
    try:
        import qiskit
    except ImportError:
        warnings.warn(
            "Qiskit not found. Install with: pip install qiskit qiskit-aer",
            ImportWarning,
            stacklevel=2
        )

# Show startup info when imported (can be disabled by setting environment variable)
import os
if not os.environ.get("BIOQL_QUIET_IMPORT"):
    _show_startup_info()