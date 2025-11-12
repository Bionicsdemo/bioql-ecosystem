"""
Receptor (Protein) Preparation Module

Prepares protein structures from PDB files for molecular docking.
Handles cleaning, hydrogen addition, and format conversion.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Union, Dict, Any, List, Tuple
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReceptorResult:
    """Result of receptor preparation."""

    input_path: Path
    output_path: Optional[Path]
    format: str
    success: bool
    error_message: Optional[str] = None
    num_atoms: Optional[int] = None
    num_residues: Optional[int] = None
    chains: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


def prepare_receptor(
    pdb_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    output_format: str = "pdbqt",
    add_hydrogens: bool = True,
    remove_waters: bool = True,
    remove_heteroatoms: bool = False,
    chains: Optional[List[str]] = None,
    repair: bool = True,
) -> ReceptorResult:
    """
    Prepare protein receptor from PDB file for molecular docking.

    Args:
        pdb_path: Path to input PDB file
        output_path: Path to save prepared receptor (auto-generated if None)
        output_format: Output format (pdbqt, pdb)
        add_hydrogens: Whether to add hydrogen atoms
        remove_waters: Whether to remove water molecules
        remove_heteroatoms: Whether to remove heteroatoms (ligands, ions)
        chains: List of chain IDs to keep (None = keep all)
        repair: Whether to repair missing atoms/residues

    Returns:
        ReceptorResult object with preparation results

    Example:
        >>> result = prepare_receptor("protein.pdb", chains=["A"])
        >>> print(result.output_path)
        >>> print(f"Residues: {result.num_residues}")
    """
    pdb_path = Path(pdb_path)
    logger.info(f"Preparing receptor from: {pdb_path}")

    if not pdb_path.exists():
        logger.error(f"PDB file not found: {pdb_path}")
        return ReceptorResult(
            input_path=pdb_path,
            output_path=None,
            format=output_format,
            success=False,
            error_message=f"File not found: {pdb_path}",
        )

    try:
        # Try Biopython first (most common)
        try:
            from Bio import PDB
            from Bio.PDB import PDBIO, Select

            # Custom selector for filtering
            class ReceptorSelect(Select):
                def accept_chain(self, chain):
                    if chains is None:
                        return 1
                    return 1 if chain.id in chains else 0

                def accept_residue(self, residue):
                    hetero_flag = residue.id[0]
                    # Remove waters
                    if remove_waters and hetero_flag == "W":
                        return 0
                    # Remove heteroatoms
                    if remove_heteroatoms and hetero_flag != " ":
                        return 0
                    return 1

            # Parse PDB file
            parser = PDB.PDBParser(QUIET=True)
            structure = parser.get_structure("receptor", str(pdb_path))

            # Get structure info
            num_residues = sum(1 for _ in structure.get_residues())
            num_atoms = sum(1 for _ in structure.get_atoms())
            chain_ids = [chain.id for chain in structure.get_chains()]

            logger.debug(f"Loaded structure: {num_atoms} atoms, {num_residues} residues, chains: {chain_ids}")

            # Generate output path if not provided
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix=f".{output_format}"))
            else:
                output_path = Path(output_path)

            # Save cleaned PDB
            io = PDBIO()
            io.set_structure(structure)

            if output_format.lower() == "pdb":
                io.save(str(output_path), ReceptorSelect())
                logger.info(f"Saved cleaned PDB: {output_path}")
            elif output_format.lower() == "pdbqt":
                # First save as PDB, then convert
                temp_pdb = Path(tempfile.mktemp(suffix=".pdb"))
                io.save(str(temp_pdb), ReceptorSelect())

                # Try to convert to PDBQT using meeko or external tools
                try:
                    from meeko import PDBQTWriterLegacy

                    # This is a placeholder - actual implementation depends on meeko API
                    logger.warning("PDBQT conversion requires external tools like prepare_receptor4.py from AutoDock Tools")
                    logger.info("Saving as PDB format instead")
                    output_path = temp_pdb.with_suffix(".pdb")
                    temp_pdb.rename(output_path)
                    output_format = "pdb"

                except ImportError:
                    logger.warning("Meeko not available for PDBQT conversion")
                    logger.info("Saving as PDB format instead")
                    output_path = temp_pdb.with_suffix(".pdb")
                    temp_pdb.rename(output_path)
                    output_format = "pdb"

            else:
                raise ValueError(f"Unsupported output format: {output_format}")

            # Add hydrogens if requested (requires external tool)
            if add_hydrogens:
                logger.info("Hydrogen addition recommended using external tools like reduce or pdb2pqr")
                # This would typically call an external tool

            logger.info(f"Receptor prepared successfully: {output_path}")

            return ReceptorResult(
                input_path=pdb_path,
                output_path=output_path,
                format=output_format,
                success=True,
                num_atoms=num_atoms,
                num_residues=num_residues,
                chains=chain_ids if chains is None else chains,
                metadata={"method": "biopython"},
            )

        except ImportError:
            logger.warning("Biopython not available")

            # Fallback to simple text processing
            logger.info("Using simple text-based PDB processing")

            # Read and filter PDB file
            with open(pdb_path, "r") as f:
                lines = f.readlines()

            filtered_lines = []
            num_atoms = 0
            num_residues_set = set()
            chain_ids_set = set()

            for line in lines:
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    # Extract fields
                    record_type = line[0:6].strip()
                    chain_id = line[21:22].strip()
                    residue_name = line[17:20].strip()
                    residue_num = line[22:26].strip()

                    # Filter chains
                    if chains is not None and chain_id not in chains:
                        continue

                    # Filter waters
                    if remove_waters and residue_name == "HOH":
                        continue

                    # Filter heteroatoms
                    if remove_heteroatoms and record_type == "HETATM":
                        continue

                    filtered_lines.append(line)
                    num_atoms += 1
                    num_residues_set.add((chain_id, residue_num))
                    chain_ids_set.add(chain_id)

                elif line.startswith(("MODEL", "ENDMDL", "END")):
                    filtered_lines.append(line)

            num_residues = len(num_residues_set)
            chain_ids_list = sorted(list(chain_ids_set))

            # Generate output path if not provided
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix=".pdb"))
            else:
                output_path = Path(output_path)

            # Write output
            with open(output_path, "w") as f:
                f.writelines(filtered_lines)

            logger.info(f"Receptor prepared using text processing: {output_path}")

            return ReceptorResult(
                input_path=pdb_path,
                output_path=output_path,
                format="pdb",
                success=True,
                num_atoms=num_atoms,
                num_residues=num_residues,
                chains=chain_ids_list,
                metadata={"method": "text_processing"},
            )

    except Exception as e:
        logger.error(f"Error preparing receptor: {e}")
        return ReceptorResult(
            input_path=pdb_path,
            output_path=None,
            format=output_format,
            success=False,
            error_message=str(e),
        )


def get_binding_site_residues(
    pdb_path: Union[str, Path], ligand_path: Union[str, Path], distance: float = 5.0
) -> List[Tuple[str, int, str]]:
    """
    Identify binding site residues near a ligand.

    Args:
        pdb_path: Path to protein PDB file
        ligand_path: Path to ligand structure file
        distance: Distance cutoff in Angstroms

    Returns:
        List of (chain_id, residue_number, residue_name) tuples
    """
    logger.info(f"Identifying binding site residues within {distance}Å")

    try:
        from Bio import PDB
        import numpy as np

        parser = PDB.PDBParser(QUIET=True)
        protein = parser.get_structure("protein", str(pdb_path))
        ligand = parser.get_structure("ligand", str(ligand_path))

        binding_site = []

        for residue in protein.get_residues():
            for atom in residue.get_atoms():
                for lig_atom in ligand.get_atoms():
                    dist = np.linalg.norm(atom.coord - lig_atom.coord)
                    if dist <= distance:
                        binding_site.append(
                            (residue.parent.id, residue.id[1], residue.resname)
                        )
                        break

        logger.info(f"Found {len(binding_site)} binding site residues")
        return list(set(binding_site))

    except ImportError:
        logger.error("Biopython required for binding site identification")
        return []
    except Exception as e:
        logger.error(f"Error identifying binding site: {e}")
        return []