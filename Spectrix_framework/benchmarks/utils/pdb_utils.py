# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
PDB utilities for downloading and processing protein structures.
"""

import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional


def download_pdb(pdb_id: str, output_dir: str) -> Path:
    """
    Download a PDB file from RCSB PDB.

    Args:
        pdb_id: 4-letter PDB identifier
        output_dir: Directory to save the downloaded PDB file

    Returns:
        Path to the downloaded PDB file

    Raises:
        ValueError: If PDB ID format is invalid
        urllib.error.URLError: If download fails
    """
    # Validate PDB ID format
    pdb_id = pdb_id.strip().lower()
    if not re.match(r"^[0-9a-z]{4}$", pdb_id):
        raise ValueError(f"Invalid PDB ID format: {pdb_id}. Expected 4 alphanumeric characters.")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Download PDB file
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    output_file = output_path / f"{pdb_id}.pdb"

    try:
        urllib.request.urlretrieve(url, output_file)
    except urllib.error.HTTPError as e:
        raise urllib.error.URLError(f"Failed to download PDB {pdb_id}: {e}")

    if not output_file.exists() or output_file.stat().st_size == 0:
        raise ValueError(f"Downloaded PDB file is empty or missing: {output_file}")

    return output_file


def extract_crystal_ligand(pdb_file: Path, output_file: Path) -> bool:
    """
    Extract the crystal ligand (HETATM records) from a PDB file.

    Extracts all HETATM records except water (HOH) and common ions/cofactors.

    Args:
        pdb_file: Path to input PDB file
        output_file: Path to output ligand PDB file

    Returns:
        True if ligand was extracted successfully, False otherwise

    Raises:
        FileNotFoundError: If input PDB file doesn't exist
    """
    if not pdb_file.exists():
        raise FileNotFoundError(f"PDB file not found: {pdb_file}")

    # Common solvent/ion/cofactor residues to exclude
    exclude_residues = {
        "HOH",
        "WAT",
        "H2O",  # Water
        "NA",
        "CL",
        "K",
        "CA",
        "MG",
        "ZN",
        "FE",
        "MN",
        "CU",
        "NI",
        "CO",  # Ions
        "SO4",
        "PO4",
        "GOL",
        "EDO",
        "PEG",
        "ACT",
        "DMS",
        "BME",  # Common crystallization additives
        "ADP",
        "ATP",
        "NAD",
        "NAP",
        "FAD",
        "FMN",
        "HEM",
        "SAH",
        "SAM",  # Common cofactors
    }

    ligand_lines = []
    found_ligand = False

    try:
        with open(pdb_file, "r") as f:
            for line in f:
                if line.startswith("HETATM"):
                    # Extract residue name (columns 18-20 in PDB format)
                    residue_name = line[17:20].strip()

                    if residue_name not in exclude_residues:
                        ligand_lines.append(line)
                        found_ligand = True

        if found_ligand:
            # Create output directory if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w") as f:
                f.writelines(ligand_lines)
                f.write("END\n")

            return True
        else:
            return False

    except Exception as e:
        print(f"Error extracting ligand: {e}")
        return False


def calculate_binding_site(ligand_pdb: Path, buffer: float = 10.0) -> dict:
    """
    Calculate binding site box parameters from a ligand PDB file.

    Calculates the center and size of a docking box that encompasses
    the ligand with an additional buffer.

    Args:
        ligand_pdb: Path to ligand PDB file
        buffer: Additional space around ligand in Angstroms (default: 10.0)

    Returns:
        Dictionary with keys: center_x, center_y, center_z, size_x, size_y, size_z

    Raises:
        FileNotFoundError: If ligand PDB file doesn't exist
        ValueError: If no coordinates found in PDB file
    """
    if not ligand_pdb.exists():
        raise FileNotFoundError(f"Ligand PDB file not found: {ligand_pdb}")

    coordinates = []

    try:
        with open(ligand_pdb, "r") as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    try:
                        # PDB format: x (31-38), y (39-46), z (47-54)
                        x = float(line[30:38].strip())
                        y = float(line[38:46].strip())
                        z = float(line[46:54].strip())
                        coordinates.append((x, y, z))
                    except (ValueError, IndexError):
                        continue

        if not coordinates:
            raise ValueError(f"No valid coordinates found in {ligand_pdb}")

        # Calculate min/max for each dimension
        x_coords = [coord[0] for coord in coordinates]
        y_coords = [coord[1] for coord in coordinates]
        z_coords = [coord[2] for coord in coordinates]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        min_z, max_z = min(z_coords), max(z_coords)

        # Calculate center
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2

        # Calculate size with buffer
        size_x = (max_x - min_x) + 2 * buffer
        size_y = (max_y - min_y) + 2 * buffer
        size_z = (max_z - min_z) + 2 * buffer

        return {
            "center_x": round(center_x, 3),
            "center_y": round(center_y, 3),
            "center_z": round(center_z, 3),
            "size_x": round(size_x, 3),
            "size_y": round(size_y, 3),
            "size_z": round(size_z, 3),
        }

    except Exception as e:
        raise ValueError(f"Error calculating binding site: {e}")
