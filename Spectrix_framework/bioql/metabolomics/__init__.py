#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Metabolomics Module - v6.0.0

Quantum-enhanced metabolomics analysis including:
- Metabolite identification
- Pathway analysis
- Metabolic flux analysis (MFA/FBA)
- NMR and MS analysis

Author: BioQL Development Team / SpectrixRD
License: MIT
"""

# Core metabolite analysis
try:
    from .metabolite_analysis import (
        Metabolite,
        MetaboliteResult,
        identify_metabolite,
        quantify_metabolites,
    )

    HAVE_METABOLITE_ANALYSIS = True
except ImportError:
    identify_metabolite = None
    quantify_metabolites = None
    Metabolite = None
    MetaboliteResult = None
    HAVE_METABOLITE_ANALYSIS = False

# Pathway analysis
try:
    from .pathway_analysis import (
        KEGGMap,
        PathwayResult,
        analyze_metabolic_pathway,
        map_to_kegg_pathway,
    )

    HAVE_PATHWAY_ANALYSIS = True
except ImportError:
    analyze_metabolic_pathway = None
    map_to_kegg_pathway = None
    PathwayResult = None
    KEGGMap = None
    HAVE_PATHWAY_ANALYSIS = False

# Flux analysis
try:
    from .flux_analysis import FBAResult, MFAResult, perform_flux_balance_analysis, perform_mfa

    HAVE_FLUX_ANALYSIS = True
except ImportError:
    perform_flux_balance_analysis = None
    perform_mfa = None
    FBAResult = None
    MFAResult = None
    HAVE_FLUX_ANALYSIS = False

# Quantum circuits
try:
    from .quantum_metabolomics import flux_optimization_circuit, pathway_correlation_circuit

    HAVE_QUANTUM_METABOLOMICS = True
except ImportError:
    flux_optimization_circuit = None
    pathway_correlation_circuit = None
    HAVE_QUANTUM_METABOLOMICS = False

__all__ = [
    # Metabolite analysis
    "identify_metabolite",
    "quantify_metabolites",
    "Metabolite",
    "MetaboliteResult",
    # Pathway analysis
    "analyze_metabolic_pathway",
    "map_to_kegg_pathway",
    "PathwayResult",
    "KEGGMap",
    # Flux analysis
    "perform_flux_balance_analysis",
    "perform_mfa",
    "FBAResult",
    "MFAResult",
    # Quantum circuits
    "flux_optimization_circuit",
    "pathway_correlation_circuit",
    # Availability flags
    "HAVE_METABOLITE_ANALYSIS",
    "HAVE_PATHWAY_ANALYSIS",
    "HAVE_FLUX_ANALYSIS",
    "HAVE_QUANTUM_METABOLOMICS",
]

__version__ = "6.0.0"
