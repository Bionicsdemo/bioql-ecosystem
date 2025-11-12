"""
Molecular Geometry Optimization Module

Provides geometry optimization using available backends (RDKit, OpenMM, OpenBabel).
"""

import tempfile
from pathlib import Path
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationResult:
    """Result of geometry optimization."""

    input_path: Optional[Path]
    output_path: Optional[Path]
    success: bool
    initial_energy: Optional[float] = None
    final_energy: Optional[float] = None
    num_iterations: Optional[int] = None
    method: Optional[str] = None
    error_message: Optional[str] = None


class GeometryOptimizer:
    """Molecular geometry optimization using available backends."""

    def __init__(self, backend: str = "auto"):
        """
        Initialize geometry optimizer.

        Args:
            backend: Backend to use (auto, rdkit, openmm, openbabel)
        """
        self.backend = backend
        logger.info(f"Initializing GeometryOptimizer with backend: {backend}")

    def optimize(
        self,
        molecule_path: Optional[Union[str, Path]] = None,
        smiles: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        max_iterations: int = 200,
        force_field: str = "MMFF94",
    ) -> OptimizationResult:
        """
        Optimize molecular geometry.

        Args:
            molecule_path: Path to input molecule file (PDB, MOL2, SDF)
            smiles: SMILES string (alternative to molecule_path)
            output_path: Path to save optimized structure
            max_iterations: Maximum optimization iterations
            force_field: Force field to use (MMFF94, UFF)

        Returns:
            OptimizationResult object

        Example:
            >>> optimizer = GeometryOptimizer()
            >>> result = optimizer.optimize(smiles="CCO")
            >>> print(f"Energy: {result.final_energy}")
        """
        if molecule_path is None and smiles is None:
            return OptimizationResult(
                input_path=None,
                output_path=None,
                success=False,
                error_message="Either molecule_path or smiles must be provided",
            )

        logger.info("Starting geometry optimization")

        # Try backends in order
        if self.backend == "auto":
            backends = ["rdkit", "openmm", "openbabel"]
        else:
            backends = [self.backend]

        for backend in backends:
            try:
                if backend == "rdkit":
                    return self._optimize_rdkit(
                        molecule_path, smiles, output_path, max_iterations, force_field
                    )
                elif backend == "openmm":
                    return self._optimize_openmm(
                        molecule_path, smiles, output_path, max_iterations
                    )
                elif backend == "openbabel":
                    return self._optimize_openbabel(
                        molecule_path, smiles, output_path, max_iterations, force_field
                    )
            except ImportError:
                logger.warning(f"Backend {backend} not available")
                continue
            except Exception as e:
                logger.error(f"Backend {backend} failed: {e}")
                continue

        return OptimizationResult(
            input_path=Path(molecule_path) if molecule_path else None,
            output_path=None,
            success=False,
            error_message="No optimization backend available",
        )

    def _optimize_rdkit(
        self, molecule_path, smiles, output_path, max_iterations, force_field
    ) -> OptimizationResult:
        """Optimize using RDKit."""
        from rdkit import Chem
        from rdkit.Chem import AllChem

        # Load or create molecule
        if smiles:
            mol = Chem.MolFromSmiles(smiles)
            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, randomSeed=42)
        else:
            if str(molecule_path).endswith(".pdb"):
                mol = Chem.MolFromPDBFile(str(molecule_path))
            elif str(molecule_path).endswith(".mol2"):
                mol = Chem.MolFromMol2File(str(molecule_path))
            else:
                mol = Chem.MolFromMolFile(str(molecule_path))

            if mol is None:
                raise ValueError("Failed to load molecule")

        # Get force field
        if force_field.upper() == "MMFF94":
            ff = AllChem.MMFFGetMoleculeForceField(mol)
            initial_energy = ff.CalcEnergy()
            result = AllChem.MMFFOptimizeMolecule(mol, maxIters=max_iterations)
            final_energy = ff.CalcEnergy()
        else:  # UFF
            ff = AllChem.UFFGetMoleculeForceField(mol)
            initial_energy = ff.CalcEnergy()
            result = AllChem.UFFOptimizeMolecule(mol, maxIters=max_iterations)
            final_energy = ff.CalcEnergy()

        # Save optimized structure
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".pdb"))
        else:
            output_path = Path(output_path)

        Chem.MolToPDBFile(mol, str(output_path))

        logger.info(f"RDKit optimization complete: {initial_energy:.2f} → {final_energy:.2f}")

        return OptimizationResult(
            input_path=Path(molecule_path) if molecule_path else None,
            output_path=output_path,
            success=True,
            initial_energy=initial_energy,
            final_energy=final_energy,
            num_iterations=result,
            method="rdkit_" + force_field.lower(),
        )

    def _optimize_openmm(
        self, molecule_path, smiles, output_path, max_iterations
    ) -> OptimizationResult:
        """Optimize using OpenMM."""
        logger.warning("OpenMM optimization not yet implemented")
        raise NotImplementedError("OpenMM optimization coming soon")

    def _optimize_openbabel(
        self, molecule_path, smiles, output_path, max_iterations, force_field
    ) -> OptimizationResult:
        """Optimize using OpenBabel."""
        from openbabel import openbabel as ob

        # Load or create molecule
        mol = ob.OBMol()
        conv = ob.OBConversion()

        if smiles:
            conv.SetInFormat("smi")
            conv.ReadString(mol, smiles)
            mol.AddHydrogens()
            builder = ob.OBBuilder()
            builder.Build(mol)
        else:
            conv.SetInFormat(Path(molecule_path).suffix[1:])
            conv.ReadFile(mol, str(molecule_path))

        # Get force field
        ff = ob.OBForceField.FindForceField(force_field)
        if not ff:
            raise ValueError(f"Force field {force_field} not found")

        ff.Setup(mol)
        initial_energy = ff.Energy()
        ff.ConjugateGradients(max_iterations)
        ff.GetCoordinates(mol)
        final_energy = ff.Energy()

        # Save optimized structure
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".pdb"))
        else:
            output_path = Path(output_path)

        conv.SetOutFormat("pdb")
        conv.WriteFile(mol, str(output_path))

        logger.info(f"OpenBabel optimization complete: {initial_energy:.2f} → {final_energy:.2f}")

        return OptimizationResult(
            input_path=Path(molecule_path) if molecule_path else None,
            output_path=output_path,
            success=True,
            initial_energy=initial_energy,
            final_energy=final_energy,
            num_iterations=max_iterations,
            method="openbabel_" + force_field.lower(),
        )