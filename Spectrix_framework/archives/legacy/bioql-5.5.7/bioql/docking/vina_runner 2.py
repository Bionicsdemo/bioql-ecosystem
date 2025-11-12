"""
AutoDock Vina Backend Runner

Executes molecular docking using AutoDock Vina external binary.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Union, Dict, Any, List, Tuple
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class VinaDockingResult:
    """Result from Vina docking."""

    success: bool
    score: Optional[float]  # kcal/mol
    poses: List[str]
    output_pdbqt: Optional[Path]
    log_file: Optional[Path]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VinaRunner:
    """
    AutoDock Vina runner for molecular docking.

    Handles preparation, execution, and parsing of Vina docking jobs.
    """

    def __init__(self, vina_executable: Optional[str] = None):
        """
        Initialize Vina runner.

        Args:
            vina_executable: Path to vina executable (auto-detected if None)
        """
        self.vina_executable = vina_executable or self._find_vina()
        logger.info(f"Initialized VinaRunner: {self.vina_executable}")

    def _find_vina(self) -> Optional[str]:
        """Find Vina executable in PATH or common locations."""
        # Try common names
        for name in ["vina", "vina_1.2.5", "autodock_vina"]:
            path = shutil.which(name)
            if path:
                logger.debug(f"Found Vina at: {path}")
                return path

        # Try common install locations
        common_paths = [
            "/usr/local/bin/vina",
            "/opt/vina/bin/vina",
            Path.home() / "vina" / "bin" / "vina",
        ]

        for path in common_paths:
            path = Path(path)
            if path.exists() and path.is_file():
                logger.debug(f"Found Vina at: {path}")
                return str(path)

        logger.warning("Vina executable not found. Please install AutoDock Vina.")
        return None

    def check_available(self) -> bool:
        """Check if Vina is available."""
        if not self.vina_executable:
            return False

        try:
            result = subprocess.run(
                [self.vina_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def dock(
        self,
        receptor_pdbqt: Union[str, Path],
        ligand_pdbqt: Union[str, Path],
        center: Tuple[float, float, float],
        box_size: Tuple[float, float, float] = (20, 20, 20),
        exhaustiveness: int = 8,
        num_modes: int = 9,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> VinaDockingResult:
        """
        Run Vina docking.

        Args:
            receptor_pdbqt: Path to receptor PDBQT file
            ligand_pdbqt: Path to ligand PDBQT file
            center: Box center coordinates (x, y, z)
            box_size: Box size (width, height, depth) in Angstroms
            exhaustiveness: Exhaustiveness of search (default: 8)
            num_modes: Number of binding modes to generate (default: 9)
            output_dir: Output directory (auto-generated if None)

        Returns:
            VinaDockingResult object

        Example:
            >>> runner = VinaRunner()
            >>> result = runner.dock(
            ...     receptor_pdbqt="receptor.pdbqt",
            ...     ligand_pdbqt="ligand.pdbqt",
            ...     center=(10.0, 15.0, 20.0),
            ...     box_size=(20, 20, 20),
            ... )
        """
        logger.info("Starting Vina docking")

        if not self.vina_executable:
            return VinaDockingResult(
                success=False,
                score=None,
                poses=[],
                output_pdbqt=None,
                log_file=None,
                error_message="Vina executable not found. Please install AutoDock Vina.",
            )

        receptor_pdbqt = Path(receptor_pdbqt)
        ligand_pdbqt = Path(ligand_pdbqt)

        if not receptor_pdbqt.exists():
            return VinaDockingResult(
                success=False,
                score=None,
                poses=[],
                output_pdbqt=None,
                log_file=None,
                error_message=f"Receptor file not found: {receptor_pdbqt}",
            )

        if not ligand_pdbqt.exists():
            return VinaDockingResult(
                success=False,
                score=None,
                poses=[],
                output_pdbqt=None,
                log_file=None,
                error_message=f"Ligand file not found: {ligand_pdbqt}",
            )

        # Setup output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="bioql_vina_"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_pdbqt = output_dir / "docked.pdbqt"
        log_file = output_dir / "vina.log"

        # Build Vina command
        cmd = [
            self.vina_executable,
            "--receptor", str(receptor_pdbqt),
            "--ligand", str(ligand_pdbqt),
            "--out", str(output_pdbqt),
            "--center_x", str(center[0]),
            "--center_y", str(center[1]),
            "--center_z", str(center[2]),
            "--size_x", str(box_size[0]),
            "--size_y", str(box_size[1]),
            "--size_z", str(box_size[2]),
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
        ]

        logger.debug(f"Vina command: {' '.join(cmd)}")

        try:
            # Run Vina
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            # Save log
            with open(log_file, 'w') as f:
                f.write(result.stdout)
                f.write(result.stderr)

            if result.returncode != 0:
                return VinaDockingResult(
                    success=False,
                    score=None,
                    poses=[],
                    output_pdbqt=None,
                    log_file=log_file,
                    error_message=f"Vina failed with return code {result.returncode}",
                )

            # Parse results
            scores, poses = self._parse_vina_output(output_pdbqt)

            if not scores:
                return VinaDockingResult(
                    success=False,
                    score=None,
                    poses=[],
                    output_pdbqt=output_pdbqt,
                    log_file=log_file,
                    error_message="No docking poses generated",
                )

            logger.info(f"Docking complete. Best score: {scores[0]} kcal/mol")

            return VinaDockingResult(
                success=True,
                score=scores[0],  # Best score
                poses=poses,
                output_pdbqt=output_pdbqt,
                log_file=log_file,
                metadata={
                    "all_scores": scores,
                    "num_poses": len(poses),
                    "exhaustiveness": exhaustiveness,
                },
            )

        except subprocess.TimeoutExpired:
            return VinaDockingResult(
                success=False,
                score=None,
                poses=[],
                output_pdbqt=None,
                log_file=log_file if log_file.exists() else None,
                error_message="Vina docking timed out (10 minutes)",
            )

        except Exception as e:
            logger.error(f"Vina docking error: {e}")
            return VinaDockingResult(
                success=False,
                score=None,
                poses=[],
                output_pdbqt=None,
                log_file=log_file if log_file.exists() else None,
                error_message=str(e),
            )

    def _parse_vina_output(self, output_file: Path) -> Tuple[List[float], List[str]]:
        """
        Parse Vina output PDBQT file to extract scores and poses.

        Args:
            output_file: Path to docked PDBQT file

        Returns:
            (scores, poses) tuple
        """
        scores = []
        poses = []
        current_pose = []

        try:
            with open(output_file, 'r') as f:
                for line in f:
                    if line.startswith("REMARK VINA RESULT:"):
                        # Extract score from REMARK line
                        parts = line.split()
                        if len(parts) >= 4:
                            score = float(parts[3])
                            scores.append(score)

                        # Save previous pose if exists
                        if current_pose:
                            poses.append("".join(current_pose))
                            current_pose = []

                    elif line.startswith("MODEL"):
                        current_pose = [line]
                    elif current_pose:
                        current_pose.append(line)
                        if line.startswith("ENDMDL"):
                            # Pose complete
                            pass

                # Add last pose
                if current_pose:
                    poses.append("".join(current_pose))

        except Exception as e:
            logger.error(f"Error parsing Vina output: {e}")

        return scores, poses