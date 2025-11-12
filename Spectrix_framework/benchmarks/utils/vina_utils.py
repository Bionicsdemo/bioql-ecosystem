# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
AutoDock Vina utilities for molecular docking and RMSD calculations.
"""

import math
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def prepare_ligand_pdbqt(smiles: str, output_file: Path, seed: int = 12345) -> bool:
    """
    Convert SMILES to PDBQT format for AutoDock Vina.

    Uses RDKit for 3D coordinate generation and Open Babel for PDBQT conversion.

    Args:
        smiles: SMILES string of the molecule
        output_file: Path to output PDBQT file
        seed: Random seed for 3D coordinate generation (default: 12345)

    Returns:
        True if conversion successful, False otherwise
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        print("Error: RDKit is required for ligand preparation")
        return False

    try:
        # Create molecule from SMILES
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            print(f"Error: Invalid SMILES: {smiles}")
            return False

        # Add hydrogens
        mol = Chem.AddHs(mol)

        # Generate 3D coordinates
        if AllChem.EmbedMolecule(mol, randomSeed=seed) != 0:
            print(f"Error: Failed to generate 3D coordinates for {smiles}")
            return False

        # Optimize geometry
        AllChem.MMFFOptimizeMolecule(mol)

        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save as PDB first
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as tmp:
            tmp_pdb = Path(tmp.name)

        Chem.MolToPDBFile(mol, str(tmp_pdb))

        # Convert PDB to PDBQT using Open Babel
        try:
            result = subprocess.run(
                ["obabel", str(tmp_pdb), "-O", str(output_file), "-p", "7.4"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Clean up temp file
            tmp_pdb.unlink(missing_ok=True)

            if result.returncode != 0:
                print(f"Error converting to PDBQT: {result.stderr}")
                return False

            return output_file.exists()

        except FileNotFoundError:
            print("Error: Open Babel (obabel) not found. Please install it.")
            tmp_pdb.unlink(missing_ok=True)
            return False
        except subprocess.TimeoutExpired:
            print("Error: PDBQT conversion timed out")
            tmp_pdb.unlink(missing_ok=True)
            return False

    except Exception as e:
        print(f"Error preparing ligand: {e}")
        return False


def run_vina_docking(
    receptor: Path,
    ligand: Path,
    center: dict,
    box_size: dict,
    exhaustiveness: int = 8,
    seed: int = 12345,
    num_modes: int = 9,
    energy_range: float = 3.0,
) -> dict:
    """
    Run AutoDock Vina docking.

    Args:
        receptor: Path to receptor PDBQT file
        ligand: Path to ligand PDBQT file
        center: Dictionary with center_x, center_y, center_z keys
        box_size: Dictionary with size_x, size_y, size_z keys
        exhaustiveness: Exhaustiveness of global search (default: 8)
        seed: Random seed for reproducibility (default: 12345)
        num_modes: Number of binding modes to generate (default: 9)
        energy_range: Maximum energy difference from best mode in kcal/mol (default: 3.0)

    Returns:
        Dictionary with keys:
            - success: bool
            - affinity: float (kcal/mol) - best binding affinity
            - output_file: Path to docked ligand PDBQT
            - all_affinities: list of all mode affinities
            - error: str (if success=False)

    Raises:
        FileNotFoundError: If receptor or ligand files don't exist
    """
    if not receptor.exists():
        raise FileNotFoundError(f"Receptor file not found: {receptor}")
    if not ligand.exists():
        raise FileNotFoundError(f"Ligand file not found: {ligand}")

    # Create output file path
    output_file = ligand.parent / f"{ligand.stem}_docked.pdbqt"

    # Prepare Vina command
    cmd = [
        "vina",
        "--receptor",
        str(receptor),
        "--ligand",
        str(ligand),
        "--out",
        str(output_file),
        "--center_x",
        str(center["center_x"]),
        "--center_y",
        str(center["center_y"]),
        "--center_z",
        str(center["center_z"]),
        "--size_x",
        str(box_size["size_x"]),
        "--size_y",
        str(box_size["size_y"]),
        "--size_z",
        str(box_size["size_z"]),
        "--exhaustiveness",
        str(exhaustiveness),
        "--seed",
        str(seed),
        "--num_modes",
        str(num_modes),
        "--energy_range",
        str(energy_range),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600  # 10 minutes timeout
        )

        if result.returncode != 0:
            return {
                "success": False,
                "affinity": None,
                "output_file": None,
                "all_affinities": [],
                "error": result.stderr,
            }

        # Parse output to extract binding affinities
        affinities = []
        for line in result.stdout.split("\n"):
            # Look for lines like "   1        -8.5      0.000      0.000"
            match = re.match(r"\s+\d+\s+([-\d.]+)\s+", line)
            if match:
                affinities.append(float(match.group(1)))

        if not affinities:
            return {
                "success": False,
                "affinity": None,
                "output_file": None,
                "all_affinities": [],
                "error": "No affinities found in Vina output",
            }

        return {
            "success": True,
            "affinity": affinities[0],  # Best affinity
            "output_file": output_file,
            "all_affinities": affinities,
            "error": None,
        }

    except FileNotFoundError:
        return {
            "success": False,
            "affinity": None,
            "output_file": None,
            "all_affinities": [],
            "error": "AutoDock Vina not found. Please install it.",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "affinity": None,
            "output_file": None,
            "all_affinities": [],
            "error": "Vina docking timed out",
        }
    except Exception as e:
        return {
            "success": False,
            "affinity": None,
            "output_file": None,
            "all_affinities": [],
            "error": str(e),
        }


def calculate_rmsd(ref_pdb: Path, docked_pdb: Path) -> float:
    """
    Calculate RMSD between reference and docked ligand structures.

    Uses RDKit for RMSD calculation with alignment.

    Args:
        ref_pdb: Path to reference ligand PDB file
        docked_pdb: Path to docked ligand PDB/PDBQT file

    Returns:
        RMSD value in Angstroms

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If RMSD calculation fails
    """
    if not ref_pdb.exists():
        raise FileNotFoundError(f"Reference PDB not found: {ref_pdb}")
    if not docked_pdb.exists():
        raise FileNotFoundError(f"Docked PDB not found: {docked_pdb}")

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        raise ImportError("RDKit is required for RMSD calculation")

    try:
        # Load reference structure
        ref_mol = Chem.MolFromPDBFile(str(ref_pdb), removeHs=False)
        if ref_mol is None:
            raise ValueError(f"Failed to load reference PDB: {ref_pdb}")

        # Load docked structure (handle both PDB and PDBQT)
        if docked_pdb.suffix == ".pdbqt":
            # Convert PDBQT to PDB temporarily
            with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as tmp:
                tmp_pdb = Path(tmp.name)

            # Simple PDBQT to PDB conversion (remove charges/types)
            with open(docked_pdb, "r") as fin, open(tmp_pdb, "w") as fout:
                for line in fin:
                    if line.startswith(("ATOM", "HETATM")):
                        # Keep only the PDB part (first 66 columns)
                        fout.write(line[:66] + "\n")

            docked_mol = Chem.MolFromPDBFile(str(tmp_pdb), removeHs=False)
            tmp_pdb.unlink(missing_ok=True)
        else:
            docked_mol = Chem.MolFromPDBFile(str(docked_pdb), removeHs=False)

        if docked_mol is None:
            raise ValueError(f"Failed to load docked PDB: {docked_pdb}")

        # Calculate RMSD (without alignment first)
        rmsd = AllChem.GetBestRMS(ref_mol, docked_mol)

        return round(rmsd, 3)

    except Exception as e:
        raise ValueError(f"Error calculating RMSD: {e}")


def calculate_ki_from_delta_g(delta_g: float, temp: float = 298.15) -> float:
    """
    Calculate inhibition constant (Ki) from Gibbs free energy.

    Uses the equation: ΔG = RT ln(Ki)
    Where RT at 298.15K ≈ 0.592 kcal/mol

    Args:
        delta_g: Gibbs free energy in kcal/mol (binding affinity from Vina)
        temp: Temperature in Kelvin (default: 298.15)

    Returns:
        Ki in nanomolar (nM)
    """
    # Gas constant R = 1.987 cal/(mol·K) = 0.001987 kcal/(mol·K)
    R = 0.001987  # kcal/(mol·K)

    # RT in kcal/mol
    RT = R * temp

    # ΔG = RT ln(Ki)
    # Ki = exp(ΔG / RT)
    # Ki is in molar, convert to nanomolar (multiply by 10^9)

    try:
        ki_molar = math.exp(delta_g / RT)
        ki_nanomolar = ki_molar * 1e9

        return round(ki_nanomolar, 3)

    except (OverflowError, ValueError) as e:
        # Handle extreme values
        print(f"Warning: Could not calculate Ki for ΔG={delta_g}: {e}")
        return float("inf") if delta_g > 0 else 0.0
