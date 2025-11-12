#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL v6.0.0: Multi-Omics Quantum Computing Platform

BioQL is a comprehensive quantum computing framework for bioinformatics with
full multi-omics analysis capabilities including proteomics, metabolomics,
multi-omics integration, and advanced genomics.

🎉 NEW in v6.0.0 - MULTI-OMICS EDITION:
- **Proteomics Module**: Protein analysis, PTM prediction, PPI screening, structure prediction
- **Metabolomics Module**: Metabolite identification, pathway analysis, flux analysis (FBA/MFA)
- **Multi-Omics Integration**: Quantum-enhanced data integration across omics layers
- **Advanced Genomics**: Variant calling, epigenetics (methylation, histone marks), RNA-Seq

Proteomics Features:
- Protein sequence analysis and physicochemical properties
- Post-translational modification (PTM) site prediction
- Protein-protein interaction (PPI) prediction
- Secondary and 3D structure prediction
- Mass spectrometry analysis

Metabolomics Features:
- Metabolite identification (HMDB, KEGG databases)
- Pathway enrichment analysis
- Metabolic flux balance analysis (FBA)
- Metabolic flux analysis (MFA)
- NMR and MS spectral analysis

Multi-Omics Features:
- Quantum neural network data integration
- Regulatory network construction
- Cross-layer correlation analysis
- Pathway enrichment across omics
- Factor analysis and dimensionality reduction

Advanced Genomics Features:
- Variant calling (SNPs, InDels, structural variants)
- DNA methylation analysis (bisulfite sequencing)
- Histone modification analysis (ChIP-Seq)
- RNA-Seq differential expression analysis
- Epigenetic regulation analysis

All Previous Features (v5.x):
- Full QEC control, AWS Braket integration
- Drug discovery and CRISPR-QAI modules
- Provenance logging and compliance
- Multi-backend quantum execution
- Natural language quantum programming

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

__version__ = "6.0.1"
__author__ = "BioQL Development Team / SpectrixRD"
__email__ = "bioql@spectrixrd.com"
__license__ = "MIT"

# Core imports
from .quantum_connector import (
    BioQLError,
    ProgramParsingError,
    QuantumBackendError,
    QuantumResult,
    QuantumSimulator,
    list_available_backends,
    quantum,
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
        auto_select_active_space,
        build_molecular_hamiltonian,
        hamiltonian_to_qiskit,
        smiles_to_geometry,
        validate_hamiltonian,
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
        BENCHMARK_MOLECULES,
        BenchmarkResult,
        run_all_benchmarks,
        run_benchmark,
    )
except ImportError:
    run_benchmark = None
    run_all_benchmarks = None
    BENCHMARK_MOLECULES = None
    BenchmarkResult = None

# NEW in v5.3.0 - Auditable logging system
try:
    from .auditable_logs import (
        AuditableSession,
        DockingExecution,
        HardwareExecution,
        PostprocessExecution,
        QualtranVisualization,
        configure_audit_logging,
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
        HAVE_MEEKO,
        HAVE_RDKIT,
        VINA_BIN,
        VinaPose,
        VinaResult,
        dock_smiles_to_receptor,
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
        QuantumFeatures,
        analyze_quantum_noise,
        correlate_quantum_classical,
        extract_quantum_features,
    )
except ImportError:
    extract_quantum_features = None
    correlate_quantum_classical = None
    analyze_quantum_noise = None
    QuantumFeatures = None

try:
    from .logger import configure_logging, get_logger
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
    from .error_mitigation import ErrorMitigator, ReadoutErrorMitigation, mitigate_counts
except ImportError:
    ErrorMitigator = None
    ReadoutErrorMitigation = None
    mitigate_counts = None

try:
    from .provenance import (
        ComplianceLogger,
        ProvenanceChain,
        ProvenanceRecord,
        enable_compliance_logging,
        get_compliance_logger,
    )
except ImportError:
    ProvenanceRecord = None
    ProvenanceChain = None
    ComplianceLogger = None
    enable_compliance_logging = None
    get_compliance_logger = None

try:
    from .benchmarks import (
        LITERATURE_DATA,
        BenchmarkResult,
        BenchmarkSuite,
        ChemistryBenchmark,
        quick_benchmark,
    )
except ImportError:
    ChemistryBenchmark = None
    BenchmarkResult = None
    BenchmarkSuite = None
    quick_benchmark = None
    LITERATURE_DATA = None

# NEW in v4.0.0 - Quantum Error Correction (QEC) Module
try:
    from .chemistry_qec import MoleculeResult, QuantumChemistry, quick_chemistry_test
except ImportError:
    QuantumChemistry = None
    MoleculeResult = None
    quick_chemistry_test = None

try:
    from .qualtran_qec import (
        QECAnalysisResult,
        QuantumErrorCorrection,
        RSAModExpResult,
        quick_qec_demo,
    )
except ImportError:
    QuantumErrorCorrection = None
    QECAnalysisResult = None
    RSAModExpResult = None
    quick_qec_demo = None

try:
    from .advanced_qec import AdvancedErrorMitigation, ErrorMitigationResult, demo_error_mitigation
except ImportError:
    AdvancedErrorMitigation = None
    ErrorMitigationResult = None
    demo_error_mitigation = None

# NEW in v5.0.0 - Full QEC Control & Visualization
try:
    from .qec import ErrorMitigation, QECMetrics, ShorCodeQEC, SteaneCodeQEC, SurfaceCodeQEC
except ImportError:
    SurfaceCodeQEC = None
    SteaneCodeQEC = None
    ShorCodeQEC = None
    ErrorMitigation = None
    QECMetrics = None

try:
    from .visualization import QECVisualizer, ResourceEstimation, ResourceEstimator
except ImportError:
    QECVisualizer = None
    ResourceEstimator = None
    ResourceEstimation = None

# NEW in v5.4.3 - CRISPR-QAI Module
try:
    from .crispr_qai import (  # Featurization; Energy estimation; Optimization; Phenotype inference; I/O; Safety; Adapters
        LocalSimulatorEngine,
        QuantumEngine,
        check_simulation_only,
        encode_guide_sequence,
        estimate_energy_collapse_braket,
        estimate_energy_collapse_qiskit,
        estimate_energy_collapse_simulator,
        guide_to_angles,
        infer_offtarget_phenotype,
        load_guides_csv,
        rank_guides_batch,
        save_results_csv,
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

# NEW in v5.6.0+ - Advanced Drug Discovery Modules
try:
    from .adme_predictor import (
        ADMEResult,
        ToxicityResult,
        predict_adme_local,
        predict_adme_toxicity,
        predict_toxicity_local,
    )
except ImportError:
    predict_adme_toxicity = None
    predict_adme_local = None
    predict_toxicity_local = None
    ADMEResult = None
    ToxicityResult = None

try:
    from .bioisostere_db import (
        BIOISOSTERE_DATABASE,
        BioisostereReplacement,
        suggest_bioisosteric_replacements,
    )
except ImportError:
    suggest_bioisosteric_replacements = None
    BioisostereReplacement = None
    BIOISOSTERE_DATABASE = None

try:
    from .similarity_search import (
        search_chembl,
        search_drugbank_local,
        search_pubchem,
        similarity_search_pipeline,
    )
except ImportError:
    similarity_search_pipeline = None
    search_chembl = None
    search_pubchem = None
    search_drugbank_local = None

try:
    from .offtarget_panel import OFFTARGET_PANEL, OffTarget, screen_offtargets
except ImportError:
    screen_offtargets = None
    OffTarget = None
    OFFTARGET_PANEL = None

try:
    from .resistance_profiler import RESISTANCE_MUTATIONS, Mutation, analyze_resistance_profile
except ImportError:
    analyze_resistance_profile = None
    Mutation = None
    RESISTANCE_MUTATIONS = None

try:
    from .pipeline_orchestrator import run_complete_pipeline
except ImportError:
    run_complete_pipeline = None

try:
    from .pdb_generator import PDBDockingGenerator, generate_docking_pdb
except ImportError:
    generate_docking_pdb = None
    PDBDockingGenerator = None

# NEW in v6.0.0 - Proteomics Module
try:
    from .proteomics import (
        HAVE_PROTEIN_ANALYSIS,
        PPIResult,
        ProteinResult,
        PTMResult,
        analyze_protein_sequence,
        predict_acetylation,
        predict_phosphorylation,
        predict_protein_properties,
        predict_protein_protein_interaction,
        predict_ptm_sites,
    )
except ImportError:
    analyze_protein_sequence = None
    predict_protein_properties = None
    predict_ptm_sites = None
    predict_phosphorylation = None
    predict_acetylation = None
    predict_protein_protein_interaction = None
    ProteinResult = None
    PTMResult = None
    PPIResult = None
    HAVE_PROTEIN_ANALYSIS = False

# NEW in v6.0.0 - Metabolomics Module
try:
    from .metabolomics import (
        HAVE_METABOLITE_ANALYSIS,
        FBAResult,
        Metabolite,
        MetaboliteResult,
        PathwayResult,
        analyze_metabolic_pathway,
        identify_metabolite,
        perform_flux_balance_analysis,
        quantify_metabolites,
    )
except ImportError:
    identify_metabolite = None
    quantify_metabolites = None
    analyze_metabolic_pathway = None
    perform_flux_balance_analysis = None
    Metabolite = None
    MetaboliteResult = None
    PathwayResult = None
    FBAResult = None
    HAVE_METABOLITE_ANALYSIS = False

# NEW in v6.0.0 - Multi-Omics Integration
try:
    from .multiomics import (
        HAVE_INTEGRATION,
        IntegratedResult,
        build_regulatory_network,
        integrate_omics_layers,
    )
except ImportError:
    integrate_omics_layers = None
    build_regulatory_network = None
    IntegratedResult = None
    HAVE_INTEGRATION = False

# NEW in v6.0.0 - Advanced Genomics
try:
    from .genomics import (
        HAVE_VARIANT_CALLING,
        MethylationResult,
        RNASeqResult,
        Variant,
        analyze_methylation,
        analyze_rna_seq,
        call_variants,
    )
except ImportError:
    call_variants = None
    analyze_methylation = None
    analyze_rna_seq = None
    Variant = None
    MethylationResult = None
    RNASeqResult = None
    HAVE_VARIANT_CALLING = False

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
    __all__.extend(
        [
            "ProvenanceRecord",
            "ProvenanceChain",
            "ComplianceLogger",
            "enable_compliance_logging",
            "get_compliance_logger",
        ]
    )

if ChemistryBenchmark is not None:
    __all__.extend(
        [
            "ChemistryBenchmark",
            "BenchmarkResult",
            "BenchmarkSuite",
            "quick_benchmark",
            "LITERATURE_DATA",
        ]
    )

# Add QEC modules if available
if QuantumChemistry is not None:
    __all__.extend(["QuantumChemistry", "MoleculeResult", "quick_chemistry_test"])

if QuantumErrorCorrection is not None:
    __all__.extend(
        ["QuantumErrorCorrection", "QECAnalysisResult", "RSAModExpResult", "quick_qec_demo"]
    )

if AdvancedErrorMitigation is not None:
    __all__.extend(["AdvancedErrorMitigation", "ErrorMitigationResult", "demo_error_mitigation"])

# Add CRISPR-QAI modules if available
if HAVE_CRISPR_QAI:
    __all__.extend(
        [
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
        ]
    )

# Add v5.6.0+ Advanced Drug Discovery modules if available
if predict_adme_toxicity is not None:
    __all__.extend(
        [
            "predict_adme_toxicity",
            "predict_adme_local",
            "predict_toxicity_local",
            "ADMEResult",
            "ToxicityResult",
        ]
    )

if suggest_bioisosteric_replacements is not None:
    __all__.extend(
        ["suggest_bioisosteric_replacements", "BioisostereReplacement", "BIOISOSTERE_DATABASE"]
    )

if similarity_search_pipeline is not None:
    __all__.extend(
        ["similarity_search_pipeline", "search_chembl", "search_pubchem", "search_drugbank_local"]
    )

if screen_offtargets is not None:
    __all__.extend(["screen_offtargets", "OffTarget", "OFFTARGET_PANEL"])

if analyze_resistance_profile is not None:
    __all__.extend(["analyze_resistance_profile", "Mutation", "RESISTANCE_MUTATIONS"])

if run_complete_pipeline is not None:
    __all__.append("run_complete_pipeline")

if generate_docking_pdb is not None:
    __all__.extend(["generate_docking_pdb", "PDBDockingGenerator"])

# Add v6.0.0+ Multi-Omics modules if available
if analyze_protein_sequence is not None:
    __all__.extend(
        [
            "analyze_protein_sequence",
            "predict_protein_properties",
            "predict_ptm_sites",
            "predict_phosphorylation",
            "predict_acetylation",
            "predict_protein_protein_interaction",
            "ProteinResult",
            "PTMResult",
            "PPIResult",
        ]
    )

if identify_metabolite is not None:
    __all__.extend(
        [
            "identify_metabolite",
            "quantify_metabolites",
            "analyze_metabolic_pathway",
            "perform_flux_balance_analysis",
            "Metabolite",
            "MetaboliteResult",
            "PathwayResult",
            "FBAResult",
        ]
    )

if integrate_omics_layers is not None:
    __all__.extend(["integrate_omics_layers", "build_regulatory_network", "IntegratedResult"])

if call_variants is not None:
    __all__.extend(
        [
            "call_variants",
            "analyze_methylation",
            "analyze_rna_seq",
            "Variant",
            "MethylationResult",
            "RNASeqResult",
        ]
    )


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
        "optional_modules": {},
    }

    # Check Python version
    import sys

    info["python_version"] = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

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
            stacklevel=2,
        )


# Show startup info when imported (can be disabled by setting environment variable)
import os

if not os.environ.get("BIOQL_QUIET_IMPORT"):
    _show_startup_info()
