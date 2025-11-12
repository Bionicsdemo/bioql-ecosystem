# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
GNINA rescoring benchmark module.

This module rescores docked ligands using GNINA's CNN scoring function.
GNINA uses deep learning to predict binding affinity from 3D structures.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_gnina_rescoring(receptor: Path, ligands: List[Path]) -> Dict[str, Any]:
    """
    Run GNINA rescoring on docked ligands.

    GNINA is executed in score_only mode to compute CNN-based affinity scores
    for pre-docked ligand poses.

    Args:
        receptor: Path to receptor PDB/PDBQT file
        ligands: List of paths to ligand SDF/PDBQT files

    Returns:
        Dictionary containing:
        - gnina_skipped: bool indicating if GNINA was not available
        - total_ligands: Number of ligands processed
        - successful: Number successfully scored
        - failed: Number that failed scoring
        - results: List of individual ligand results
        - error: Error message if GNINA not found
    """
    # Check if GNINA is available
    gnina_path = shutil.which("gnina")

    if gnina_path is None:
        logger.warning("GNINA binary not found in PATH. Skipping rescoring.")
        return {
            "gnina_skipped": True,
            "reason": "GNINA binary not found",
            "total_ligands": len(ligands),
            "successful": 0,
            "failed": 0,
        }

    logger.info(f"Found GNINA at: {gnina_path}")

    # Validate receptor file
    if not receptor.exists():
        logger.error(f"Receptor file not found: {receptor}")
        return {"gnina_skipped": True, "reason": "Receptor file not found", "error": str(receptor)}

    logger.info(f"Receptor: {receptor}")
    logger.info(f"Rescoring {len(ligands)} ligands")

    # Create artifacts directory
    artifacts_dir = Path("/Users/heinzjungbluth/Desktop/artifacts/gnina")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Process each ligand
    results = []
    successful = 0
    failed = 0

    for idx, ligand_path in enumerate(ligands, 1):
        logger.info(f"Processing ligand {idx}/{len(ligands)}: {ligand_path.name}")

        # Extract ligand ID from filename
        ligand_id = ligand_path.stem

        # Score the ligand
        score_result = _score_ligand(receptor, ligand_path, ligand_id, artifacts_dir)

        if score_result["success"]:
            successful += 1
        else:
            failed += 1

        results.append(score_result)

    # Summary
    logger.info(f"Rescoring complete: {successful} successful, {failed} failed")

    return {
        "gnina_skipped": False,
        "total_ligands": len(ligands),
        "successful": successful,
        "failed": failed,
        "success_rate": round(successful / len(ligands) * 100, 2) if ligands else 0,
        "results": results,
    }


def _score_ligand(
    receptor: Path, ligand: Path, ligand_id: str, artifacts_dir: Path
) -> Dict[str, Any]:
    """
    Score a single ligand using GNINA.

    Args:
        receptor: Path to receptor file
        ligand: Path to ligand file
        ligand_id: Identifier for the ligand
        artifacts_dir: Directory to save results

    Returns:
        Dictionary with scoring results
    """
    result = {
        "ligand_id": ligand_id,
        "ligand_file": str(ligand),
        "success": False,
        "cnn_score": None,
        "error": None,
    }

    # Check if ligand file exists
    if not ligand.exists():
        result["error"] = "Ligand file not found"
        logger.error(f"Ligand file not found: {ligand}")
        return result

    try:
        # Build GNINA command
        # --score_only: Only score, don't dock
        # --seed: For reproducibility
        cmd = [
            "gnina",
            "--receptor",
            str(receptor),
            "--ligand",
            str(ligand),
            "--score_only",
            "--seed",
            "12345",
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        # Execute GNINA
        process = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout per ligand
        )

        # Check if execution was successful
        if process.returncode != 0:
            result["error"] = f"GNINA failed with return code {process.returncode}"
            logger.error(f"GNINA error for {ligand_id}: {process.stderr}")
            return result

        # Parse output to extract CNN affinity
        cnn_score = _parse_gnina_output(process.stdout)

        if cnn_score is None:
            result["error"] = "Could not parse CNN score from output"
            logger.warning(f"Failed to parse CNN score for {ligand_id}")
            logger.debug(f"GNINA stdout: {process.stdout}")
            return result

        result["success"] = True
        result["cnn_score"] = cnn_score

        # Save individual result JSON
        _save_ligand_result(artifacts_dir, ligand_id, cnn_score)

        logger.info(f"Successfully scored {ligand_id}: CNN score = {cnn_score:.3f}")

    except subprocess.TimeoutExpired:
        result["error"] = "GNINA execution timeout (>300s)"
        logger.error(f"Timeout scoring {ligand_id}")

    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Error scoring {ligand_id}: {e}", exc_info=True)

    return result


def _parse_gnina_output(output: str) -> float:
    """
    Parse GNINA output to extract CNN affinity score.

    GNINA score_only mode outputs lines like:
    "Affinity: -8.123 (kcal/mol)"
    or in newer versions:
    "CNNaffinity: -8.123"

    Args:
        output: GNINA stdout text

    Returns:
        CNN affinity score (float) or None if not found
    """
    lines = output.strip().split("\n")

    for line in lines:
        # Look for CNNaffinity or CNN_affinity
        if "CNNaffinity" in line or "CNN_affinity" in line or "cnn_affinity" in line:
            try:
                # Extract the numeric value
                parts = line.split()
                for i, part in enumerate(parts):
                    if "affinity" in part.lower():
                        # Next part should be the score
                        if i + 1 < len(parts):
                            score_str = parts[i + 1].strip()
                            # Remove any trailing units or punctuation
                            score_str = score_str.rstrip("(kcal/mol)").strip(":")
                            return float(score_str)
            except (ValueError, IndexError):
                continue

        # Fallback: look for "Affinity:" pattern
        if line.strip().startswith("Affinity:"):
            try:
                # Extract number after "Affinity:"
                parts = line.split(":")
                if len(parts) > 1:
                    score_str = parts[1].split()[0]  # Get first token after colon
                    return float(score_str)
            except (ValueError, IndexError):
                continue

    # If we couldn't find a score, return None
    logger.debug("Could not parse CNN affinity from GNINA output")
    return None


def _save_ligand_result(artifacts_dir: Path, ligand_id: str, cnn_score: float) -> None:
    """
    Save individual ligand scoring result to JSON.

    Args:
        artifacts_dir: Directory for artifacts
        ligand_id: Ligand identifier
        cnn_score: CNN affinity score
    """
    output_file = artifacts_dir / f"{ligand_id}.json"

    result_data = {"ligand_id": ligand_id, "cnn_score": cnn_score, "units": "kcal/mol"}

    with open(output_file, "w") as f:
        json.dump(result_data, f, indent=2)

    logger.debug(f"Saved result to: {output_file}")


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 2:
        receptor_path = Path(sys.argv[1])
        ligand_paths = [Path(p) for p in sys.argv[2:]]
    else:
        # Default example
        receptor_path = Path("/Users/heinzjungbluth/Desktop/data/receptors/protein.pdbqt")
        ligand_paths = [
            Path("/Users/heinzjungbluth/Desktop/data/ligands/ligand1.pdbqt"),
            Path("/Users/heinzjungbluth/Desktop/data/ligands/ligand2.pdbqt"),
        ]

    result = run_gnina_rescoring(receptor_path, ligand_paths)
    print(json.dumps(result, indent=2))
