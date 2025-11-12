# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Chemical filters benchmark for molecule validation.

This module validates molecules from a SMILES file against various drug-likeness
filters including Lipinski's Rule of Five, Veber's rules, PAINS, Brenk filters,
and reactive group checks.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from rdkit import Chem
from utils.chem_utils import (
    check_brenk,
    check_lipinski,
    check_pains,
    check_reactive_groups,
    check_veber,
    sanitize_molecule,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_chem_filters(ligands_file: Path) -> Dict[str, Any]:
    """
    Run chemical filter validations on molecules from a SMILES file.

    This function reads SMILES from a file, validates each molecule through
    multiple filters (Lipinski, Veber, PAINS, Brenk, reactive groups), and
    saves results to a CSV file.

    Args:
        ligands_file: Path to SMILES file (.smi format)
                     Expected format: SMILES string per line, optionally with name

    Returns:
        Dictionary containing:
        - total_molecules: Total number of molecules processed
        - passed: Number of molecules passing all filters
        - failed: Number of molecules failing any filter
        - output_file: Path to results CSV file
        - summary: Dictionary of failure reasons and counts
    """
    if not ligands_file.exists():
        logger.error(f"Ligands file not found: {ligands_file}")
        return {"error": "File not found", "total_molecules": 0, "passed": 0, "failed": 0}

    logger.info(f"Starting chemical filters validation on: {ligands_file}")

    # Read SMILES from file
    molecules = _read_smiles_file(ligands_file)
    logger.info(f"Loaded {len(molecules)} molecules from file")

    # Process each molecule
    results = []
    passed_count = 0
    failed_count = 0
    failure_reasons = {}

    for idx, (smiles, mol_name) in enumerate(molecules, 1):
        logger.debug(f"Processing molecule {idx}/{len(molecules)}: {mol_name or smiles[:50]}")

        # Validate molecule
        result = _validate_molecule(smiles, mol_name or f"mol_{idx}")

        # Track statistics
        if result["passed"]:
            passed_count += 1
        else:
            failed_count += 1
            # Count failure reasons
            for reason in result["reasons"].split("; "):
                if reason:
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        results.append(result)

    # Save results to CSV
    output_file = _save_results_csv(results)
    logger.info(f"Results saved to: {output_file}")

    # Summary statistics
    logger.info(f"Total molecules: {len(molecules)}")
    logger.info(f"Passed all filters: {passed_count}")
    logger.info(f"Failed any filter: {failed_count}")
    logger.info(f"Pass rate: {passed_count/len(molecules)*100:.1f}%")

    return {
        "total_molecules": len(molecules),
        "passed": passed_count,
        "failed": failed_count,
        "output_file": str(output_file),
        "pass_rate": round(passed_count / len(molecules) * 100, 2) if molecules else 0,
        "summary": failure_reasons,
    }


def _read_smiles_file(file_path: Path) -> List[Tuple[str, str]]:
    """
    Read SMILES from file.

    Supports formats:
    - SMILES only (one per line)
    - SMILES<tab>NAME
    - SMILES<space>NAME

    Args:
        file_path: Path to SMILES file

    Returns:
        List of tuples (smiles, name)
    """
    molecules = []

    with open(file_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse SMILES and optional name
            parts = line.split()
            if len(parts) == 0:
                continue
            elif len(parts) == 1:
                smiles = parts[0]
                name = ""
            else:
                # Check if tab-separated or space-separated
                if "\t" in line:
                    parts = line.split("\t", 1)
                    smiles = parts[0].strip()
                    name = parts[1].strip() if len(parts) > 1 else ""
                else:
                    smiles = parts[0]
                    name = parts[1] if len(parts) > 1 else ""

            molecules.append((smiles, name))

    return molecules


def _validate_molecule(smiles: str, mol_name: str) -> Dict[str, Any]:
    """
    Validate a single molecule through all filters.

    Args:
        smiles: SMILES string
        mol_name: Molecule name/identifier

    Returns:
        Dictionary with validation results and properties
    """
    result = {
        "smiles": smiles,
        "name": mol_name,
        "passed": False,
        "reasons": "",
        "MW": None,
        "logP": None,
        "TPSA": None,
        "HBD": None,
        "HBA": None,
        "rotB": None,
    }

    # Step 1: Sanitize molecule
    is_valid, sanitize_reason = sanitize_molecule(smiles)

    if not is_valid:
        result["reasons"] = f"Sanitization failed: {sanitize_reason}"
        return result

    # Create RDKit mol object
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        result["reasons"] = "Failed to create RDKit molecule"
        return result

    # Collect all failure reasons
    failures = []

    # Step 2: Check Lipinski's Rule of Five
    lipinski_result = check_lipinski(mol)
    result["MW"] = lipinski_result["mw"]
    result["logP"] = lipinski_result["logp"]
    result["HBD"] = lipinski_result["hbd"]
    result["HBA"] = lipinski_result["hba"]

    if not lipinski_result["passes"]:
        failures.append(f"Lipinski violations ({lipinski_result['violations']})")

    # Step 3: Check Veber's rules
    veber_result = check_veber(mol)
    result["TPSA"] = veber_result["psa"]
    result["rotB"] = veber_result["rotatable_bonds"]

    if not veber_result["passes"]:
        failures.append(f"Veber violations ({veber_result['violations']})")

    # Step 4: Check PAINS
    pains_alerts = check_pains(mol)
    if pains_alerts:
        failures.append(f"PAINS alerts ({len(pains_alerts)})")

    # Step 5: Check Brenk filters
    brenk_alerts = check_brenk(mol)
    if brenk_alerts:
        failures.append(f"Brenk alerts ({len(brenk_alerts)})")

    # Step 6: Check reactive groups
    reactive_alerts = check_reactive_groups(mol)
    if reactive_alerts:
        # List specific reactive groups found
        failures.append(f"Reactive groups: {', '.join(reactive_alerts)}")

    # Set final result
    result["passed"] = len(failures) == 0
    result["reasons"] = "; ".join(failures)

    return result


def _save_results_csv(results: List[Dict[str, Any]]) -> Path:
    """
    Save validation results to CSV file.

    Args:
        results: List of validation result dictionaries

    Returns:
        Path to saved CSV file
    """
    # Create artifacts directory
    artifacts_dir = Path("/Users/heinzjungbluth/Desktop/artifacts/chem")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    output_file = artifacts_dir / "filters.csv"

    # Write CSV
    fieldnames = ["smiles", "name", "passed", "reasons", "MW", "logP", "TPSA", "HBD", "HBA", "rotB"]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Only write relevant fields
            row = {k: result.get(k) for k in fieldnames}
            writer.writerow(row)

    return output_file


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        ligands_file = Path(sys.argv[1])
    else:
        ligands_file = Path("/Users/heinzjungbluth/Desktop/data/ligands/examples.smi")

    result = run_chem_filters(ligands_file)
    print(f"\nResults: {result}")
