"""
Unified Docking Pipeline

Provides high-level interface for molecular docking with automatic
backend selection and fallback handling.
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..logger import get_logger
from ..chem import prepare_ligand, prepare_receptor

logger = get_logger(__name__)


@dataclass
class DockingResult:
    """Unified docking result."""

    success: bool
    job_id: str
    backend: str
    score: Optional[float]  # kcal/mol
    ligand_smiles: Optional[str]
    receptor_path: Optional[Path]
    output_complex: Optional[Path]
    output_ligand: Optional[Path]
    results_json: Optional[Path]
    poses: Optional[list]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


def dock(
    receptor: Union[str, Path],
    ligand_smiles: Optional[str] = None,
    ligand_file: Optional[Union[str, Path]] = None,
    backend: str = "auto",
    center: Optional[Tuple[float, float, float]] = None,
    box_size: Tuple[float, float, float] = (20, 20, 20),
    output_dir: Optional[Union[str, Path]] = None,
    exhaustiveness: int = 8,
    num_modes: int = 9,
    api_key: Optional[str] = None,
    shots: int = 1024,
    job_id: Optional[str] = None,
) -> DockingResult:
    """
    Perform molecular docking with automatic backend selection.

    This is the main entry point for BioQL docking operations.

    Args:
        receptor: Path to receptor PDB file
        ligand_smiles: Ligand SMILES string
        ligand_file: Path to ligand file (alternative to SMILES)
        backend: Docking backend (auto, vina, quantum)
        center: Binding site center (x, y, z) - auto-calculated if None
        box_size: Search box size (width, height, depth)
        output_dir: Output directory (auto-generated if None)
        exhaustiveness: Vina exhaustiveness parameter
        num_modes: Number of binding modes to generate
        api_key: API key for quantum backend
        shots: Number of quantum shots
        job_id: Job identifier (auto-generated if None)

    Returns:
        DockingResult object

    Examples:
        >>> # Vina docking
        >>> result = dock(
        ...     receptor="protein.pdb",
        ...     ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        ...     backend="vina",
        ... )

        >>> # Quantum docking
        >>> result = dock(
        ...     receptor="protein.pdb",
        ...     ligand_smiles="CCO",
        ...     backend="quantum",
        ...     api_key="your_key",
        ... )

        >>> # Auto backend selection
        >>> result = dock(
        ...     receptor="protein.pdb",
        ...     ligand_smiles="CCO",
        ...     backend="auto",
        ... )
    """
    # Generate job ID
    if job_id is None:
        job_id = f"dock_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    logger.info(f"Starting docking job: {job_id}")
    logger.info(f"Backend: {backend}")

    # Setup output directory
    if output_dir is None:
        output_dir = Path(f"outputs/{job_id}")
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate inputs
    receptor_path = Path(receptor)
    if not receptor_path.exists():
        return DockingResult(
            success=False,
            job_id=job_id,
            backend=backend,
            score=None,
            ligand_smiles=ligand_smiles,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=None,
            poses=None,
            error_message=f"Receptor file not found: {receptor_path}",
            timestamp=datetime.now().isoformat(),
        )

    if ligand_smiles is None and ligand_file is None:
        return DockingResult(
            success=False,
            job_id=job_id,
            backend=backend,
            score=None,
            ligand_smiles=None,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=None,
            poses=None,
            error_message="Either ligand_smiles or ligand_file must be provided",
            timestamp=datetime.now().isoformat(),
        )

    # Backend selection
    if backend == "auto":
        backend = _select_backend()
        logger.info(f"Auto-selected backend: {backend}")

    # Execute docking based on backend
    if backend == "vina":
        return _dock_vina(
            job_id=job_id,
            receptor_path=receptor_path,
            ligand_smiles=ligand_smiles,
            ligand_file=ligand_file,
            center=center,
            box_size=box_size,
            output_dir=output_dir,
            exhaustiveness=exhaustiveness,
            num_modes=num_modes,
        )

    elif backend == "quantum":
        return _dock_quantum(
            job_id=job_id,
            receptor_path=receptor_path,
            ligand_smiles=ligand_smiles,
            output_dir=output_dir,
            api_key=api_key,
            shots=shots,
        )

    else:
        return DockingResult(
            success=False,
            job_id=job_id,
            backend=backend,
            score=None,
            ligand_smiles=ligand_smiles,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=None,
            poses=None,
            error_message=f"Unknown backend: {backend}",
            timestamp=datetime.now().isoformat(),
        )


def _select_backend() -> str:
    """Auto-select best available docking backend."""
    # Try Vina first
    try:
        from .vina_runner import VinaRunner

        runner = VinaRunner()
        if runner.check_available():
            logger.info("Vina available - using Vina backend")
            return "vina"
    except Exception:
        pass

    # Fallback to quantum
    try:
        from .quantum_runner import QuantumRunner

        runner = QuantumRunner()
        if runner.check_available():
            logger.info("Quantum backend available - using quantum")
            return "quantum"
    except Exception:
        pass

    # Default to quantum (will fail gracefully if not available)
    logger.warning("No docking backend available - defaulting to quantum")
    return "quantum"


def _dock_vina(
    job_id: str,
    receptor_path: Path,
    ligand_smiles: Optional[str],
    ligand_file: Optional[Path],
    center: Optional[Tuple[float, float, float]],
    box_size: Tuple[float, float, float],
    output_dir: Path,
    exhaustiveness: int,
    num_modes: int,
) -> DockingResult:
    """Execute Vina docking."""
    logger.info("Executing Vina docking")

    try:
        from .vina_runner import VinaRunner

        runner = VinaRunner()

        # Prepare receptor
        logger.info("Preparing receptor...")
        receptor_result = prepare_receptor(
            receptor_path,
            output_path=output_dir / "receptor_prepared.pdb",
            output_format="pdb",  # Vina needs PDBQT but we'll handle conversion
        )

        if not receptor_result.success:
            return DockingResult(
                success=False,
                job_id=job_id,
                backend="vina",
                score=None,
                ligand_smiles=ligand_smiles,
                receptor_path=receptor_path,
                output_complex=None,
                output_ligand=None,
                results_json=None,
                poses=None,
                error_message=f"Receptor preparation failed: {receptor_result.error_message}",
                timestamp=datetime.now().isoformat(),
            )

        # Prepare ligand
        logger.info("Preparing ligand...")
        if ligand_smiles:
            ligand_result = prepare_ligand(
                ligand_smiles,
                output_path=output_dir / "ligand_prepared.pdbqt",
                output_format="pdbqt",
            )
        else:
            # Copy ligand file
            ligand_result = None  # Placeholder

        if ligand_result and not ligand_result.success:
            return DockingResult(
                success=False,
                job_id=job_id,
                backend="vina",
                score=None,
                ligand_smiles=ligand_smiles,
                receptor_path=receptor_path,
                output_complex=None,
                output_ligand=None,
                results_json=None,
                poses=None,
                error_message=f"Ligand preparation failed: {ligand_result.error_message}",
                timestamp=datetime.now().isoformat(),
            )

        # Calculate center if not provided
        if center is None:
            center = _calculate_binding_site_center(receptor_path)
            logger.info(f"Auto-calculated binding site center: {center}")

        # Note: This is a simplified version. Full implementation would need
        # to convert PDB to PDBQT using external tools
        logger.warning("PDBQT conversion requires external tools (prepare_receptor4.py)")
        logger.info("For full Vina support, install AutoDock Tools")

        return DockingResult(
            success=False,
            job_id=job_id,
            backend="vina",
            score=None,
            ligand_smiles=ligand_smiles,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=None,
            poses=None,
            error_message="PDBQT conversion not yet implemented. Install AutoDock Tools.",
            metadata={"note": "Partial implementation - requires ADT for PDBQT conversion"},
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Vina docking failed: {e}")
        return DockingResult(
            success=False,
            job_id=job_id,
            backend="vina",
            score=None,
            ligand_smiles=ligand_smiles,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=None,
            poses=None,
            error_message=str(e),
            timestamp=datetime.now().isoformat(),
        )


def _dock_quantum(
    job_id: str,
    receptor_path: Path,
    ligand_smiles: str,
    output_dir: Path,
    api_key: Optional[str],
    shots: int,
) -> DockingResult:
    """Execute quantum docking."""
    logger.info("Executing quantum docking")

    try:
        from .quantum_runner import QuantumRunner

        runner = QuantumRunner(api_key=api_key)

        result = runner.dock(
            receptor_pdb=receptor_path,
            ligand_smiles=ligand_smiles,
            shots=shots,
            output_dir=output_dir,
        )

        if not result.success:
            return DockingResult(
                success=False,
                job_id=job_id,
                backend="quantum",
                score=result.score,
                ligand_smiles=ligand_smiles,
                receptor_path=receptor_path,
                output_complex=None,
                output_ligand=None,
                results_json=None,
                poses=None,
                error_message=result.error_message,
                timestamp=datetime.now().isoformat(),
            )

        # Save results
        results_json = output_dir / "results.json"
        import json

        with open(results_json, 'w') as f:
            json.dump({
                "job_id": job_id,
                "backend": "quantum",
                "score": result.score,
                "energy": result.energy,
                "ligand_smiles": ligand_smiles,
                "receptor": str(receptor_path),
                "shots": shots,
                "metadata": result.metadata,
            }, f, indent=2)

        logger.info(f"Quantum docking complete. Score: {result.score}")

        return DockingResult(
            success=True,
            job_id=job_id,
            backend="quantum",
            score=result.score,
            ligand_smiles=ligand_smiles,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=results_json,
            poses=result.poses,
            metadata=result.metadata,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Quantum docking failed: {e}")
        return DockingResult(
            success=False,
            job_id=job_id,
            backend="quantum",
            score=None,
            ligand_smiles=ligand_smiles,
            receptor_path=receptor_path,
            output_complex=None,
            output_ligand=None,
            results_json=None,
            poses=None,
            error_message=str(e),
            timestamp=datetime.now().isoformat(),
        )


def _calculate_binding_site_center(pdb_path: Path) -> Tuple[float, float, float]:
    """
    Calculate geometric center of protein for binding site.

    This is a simple implementation. More sophisticated methods would
    identify actual binding pockets.
    """
    try:
        from Bio import PDB

        parser = PDB.PDBParser(QUIET=True)
        structure = parser.get_structure("protein", str(pdb_path))

        coords = []
        for atom in structure.get_atoms():
            coords.append(atom.coord)

        import numpy as np

        coords = np.array(coords)
        center = np.mean(coords, axis=0)

        return tuple(center)

    except Exception as e:
        logger.warning(f"Could not calculate binding site center: {e}")
        # Return default center
        return (0.0, 0.0, 0.0)