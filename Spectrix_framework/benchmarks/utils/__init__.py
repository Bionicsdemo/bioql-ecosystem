# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Benchmark utilities package.

This package provides utilities for:
- PDB file handling and ligand extraction
- AutoDock Vina docking and RMSD calculations
- Chemical validation and property calculations
- Report generation (JSON and HTML)
"""

from .chem_utils import (
    calculate_molecular_properties,
    check_brenk,
    check_lipinski,
    check_pains,
    check_reactive_groups,
    check_veber,
    sanitize_molecule,
)
from .pdb_utils import calculate_binding_site, download_pdb, extract_crystal_ligand
from .report_utils import calculate_pass_fail_criteria, generate_html_report, generate_json_report
from .vina_utils import (
    calculate_ki_from_delta_g,
    calculate_rmsd,
    prepare_ligand_pdbqt,
    run_vina_docking,
)

__all__ = [
    # PDB utils
    "download_pdb",
    "extract_crystal_ligand",
    "calculate_binding_site",
    # Vina utils
    "prepare_ligand_pdbqt",
    "run_vina_docking",
    "calculate_rmsd",
    "calculate_ki_from_delta_g",
    # Chem utils
    "sanitize_molecule",
    "check_lipinski",
    "check_veber",
    "check_pains",
    "check_brenk",
    "check_reactive_groups",
    "calculate_molecular_properties",
    # Report utils
    "generate_json_report",
    "generate_html_report",
    "calculate_pass_fail_criteria",
]

__version__ = "1.0.0"
