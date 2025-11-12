#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Advanced Genomics Module - v6.0.0

Quantum-enhanced genomics analysis including:
- Variant calling (SNPs, InDels, SVs)
- Epigenetics (methylation, histone marks)
- RNA-Seq analysis
- ChIP-Seq and ATAC-Seq analysis
- DNA structure analysis

Author: BioQL Development Team / SpectrixRD
License: MIT
"""

# Variant calling
try:
    from .variant_calling import Variant, VariantResult, call_variants

    HAVE_VARIANT_CALLING = True
except ImportError:
    call_variants = None
    Variant = None
    VariantResult = None
    HAVE_VARIANT_CALLING = False

# Epigenetics
try:
    from .epigenetics import (
        HistoneResult,
        MethylationResult,
        analyze_histone_marks,
        analyze_methylation,
    )

    HAVE_EPIGENETICS = True
except ImportError:
    analyze_methylation = None
    analyze_histone_marks = None
    MethylationResult = None
    HistoneResult = None
    HAVE_EPIGENETICS = False

# RNA-Seq
try:
    from .rna_seq import RNASeqResult, analyze_rna_seq

    HAVE_RNA_SEQ = True
except ImportError:
    analyze_rna_seq = None
    RNASeqResult = None
    HAVE_RNA_SEQ = False

__all__ = [
    "call_variants",
    "Variant",
    "VariantResult",
    "analyze_methylation",
    "analyze_histone_marks",
    "MethylationResult",
    "HistoneResult",
    "analyze_rna_seq",
    "RNASeqResult",
    "HAVE_VARIANT_CALLING",
    "HAVE_EPIGENETICS",
    "HAVE_RNA_SEQ",
]

__version__ = "6.0.0"
