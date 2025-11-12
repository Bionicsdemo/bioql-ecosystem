"""
Ligand Preparation Module

Converts SMILES strings to 3D structures suitable for molecular docking.
Supports multiple output formats (PDB, PDBQT, MOL2, SDF).
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class LigandResult:
    """Result of ligand preparation."""

    smiles: str
    output_path: Optional[Path]
    format: str
    success: bool
    error_message: Optional[str] = None
    num_atoms: Optional[int] = None
    molecular_weight: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


def prepare_ligand(
    smiles: str,
    output_path: Optional[Union[str, Path]] = None,
    output_format: str = "pdbqt",
    add_hydrogens: bool = True,
    generate_3d: bool = True,
    optimize_geometry: bool = True,
    ph: float = 7.4,
) -> LigandResult:
    """
    Prepare ligand from SMILES string for molecular docking.

    Args:
        smiles: SMILES string representation of the ligand
        output_path: Path to save prepared ligand (auto-generated if None)
        output_format: Output format (pdbqt, pdb, mol2, sdf)
        add_hydrogens: Whether to add hydrogen atoms
        generate_3d: Whether to generate 3D coordinates
        optimize_geometry: Whether to optimize molecular geometry
        ph: pH for protonation state (default: 7.4)

    Returns:
        LigandResult object with preparation results

    Example:
        >>> result = prepare_ligand("CC(=O)OC1=CC=CC=C1C(=O)O")  # Aspirin
        >>> print(result.output_path)
        >>> print(f"Molecular weight: {result.molecular_weight}")
    """
    logger.info(f"Preparing ligand from SMILES: {smiles}")

    try:
        # Try RDKit first (most common)
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, Descriptors

            # Parse SMILES
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES string: {smiles}")

            # Add hydrogens
            if add_hydrogens:
                mol = Chem.AddHs(mol)
                logger.debug("Added hydrogen atoms")

            # Generate 3D coordinates
            if generate_3d:
                result = AllChem.EmbedMolecule(mol, randomSeed=42)
                if result != 0:
                    logger.warning("3D embedding failed, trying with random coordinates")
                    AllChem.EmbedMolecule(mol, randomSeed=42, useRandomCoords=True)

            # Optimize geometry
            if optimize_geometry and generate_3d:
                AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
                logger.debug("Optimized molecular geometry")

            # Get molecular properties
            num_atoms = mol.GetNumAtoms()
            molecular_weight = Descriptors.MolWt(mol)

            # Generate output path if not provided
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix=f".{output_format}"))
            else:
                output_path = Path(output_path)

            # Write output file
            if output_format.lower() == "pdb":
                Chem.MolToPDBFile(mol, str(output_path))
            elif output_format.lower() == "mol2":
                # Try to use meeko if available
                try:
                    from meeko import MoleculePreparation

                    preparator = MoleculePreparation()
                    preparator.prepare(mol)
                    preparator.write_pdbqt_file(str(output_path).replace(".mol2", ".pdbqt"))
                    output_format = "pdbqt"
                    logger.info("Used Meeko for PDBQT generation")
                except ImportError:
                    logger.warning("Meeko not available, using PDB format instead")
                    Chem.MolToPDBFile(mol, str(output_path).replace(".mol2", ".pdb"))
                    output_format = "pdb"
            elif output_format.lower() == "pdbqt":
                # Requires Meeko
                try:
                    from meeko import MoleculePreparation

                    preparator = MoleculePreparation()
                    preparator.prepare(mol)
                    preparator.write_pdbqt_file(str(output_path))
                    logger.info("Generated PDBQT file using Meeko")
                except ImportError:
                    logger.error("Meeko required for PDBQT format")
                    logger.info("Install with: pip install bioql[vina]")
                    return LigandResult(
                        smiles=smiles,
                        output_path=None,
                        format=output_format,
                        success=False,
                        error_message="Meeko required for PDBQT format. Install bioql[vina]",
                    )
            elif output_format.lower() == "sdf":
                writer = Chem.SDWriter(str(output_path))
                writer.write(mol)
                writer.close()
            else:
                raise ValueError(f"Unsupported output format: {output_format}")

            logger.info(f"Ligand prepared successfully: {output_path}")

            return LigandResult(
                smiles=smiles,
                output_path=output_path,
                format=output_format,
                success=True,
                num_atoms=num_atoms,
                molecular_weight=molecular_weight,
                metadata={"method": "rdkit"},
            )

        except ImportError:
            logger.warning("RDKit not available, trying OpenBabel...")

            # Fallback to OpenBabel
            try:
                from openbabel import openbabel as ob

                # Create molecule from SMILES
                mol = ob.OBMol()
                conv = ob.OBConversion()
                conv.SetInFormat("smi")
                conv.ReadString(mol, smiles)

                if add_hydrogens:
                    mol.AddHydrogens()

                if generate_3d:
                    builder = ob.OBBuilder()
                    builder.Build(mol)

                if optimize_geometry and generate_3d:
                    ff = ob.OBForceField.FindForceField("MMFF94")
                    if ff:
                        ff.Setup(mol)
                        ff.ConjugateGradients(200)
                        ff.GetCoordinates(mol)

                # Generate output path if not provided
                if output_path is None:
                    output_path = Path(tempfile.mktemp(suffix=f".{output_format}"))
                else:
                    output_path = Path(output_path)

                # Write output
                conv.SetOutFormat(output_format)
                conv.WriteFile(mol, str(output_path))

                num_atoms = mol.NumAtoms()
                molecular_weight = mol.GetMolWt()

                logger.info(f"Ligand prepared using OpenBabel: {output_path}")

                return LigandResult(
                    smiles=smiles,
                    output_path=output_path,
                    format=output_format,
                    success=True,
                    num_atoms=num_atoms,
                    molecular_weight=molecular_weight,
                    metadata={"method": "openbabel"},
                )

            except ImportError:
                error_msg = "Neither RDKit nor OpenBabel available. Install with: pip install bioql[vina]"
                logger.error(error_msg)
                return LigandResult(
                    smiles=smiles,
                    output_path=None,
                    format=output_format,
                    success=False,
                    error_message=error_msg,
                )

    except Exception as e:
        logger.error(f"Error preparing ligand: {e}")
        return LigandResult(
            smiles=smiles,
            output_path=None,
            format=output_format,
            success=False,
            error_message=str(e),
        )


def validate_smiles(smiles: str) -> bool:
    """
    Validate SMILES string.

    Args:
        smiles: SMILES string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)
        return mol is not None
    except ImportError:
        logger.warning("RDKit not available for SMILES validation")
        return True  # Assume valid if we can't check