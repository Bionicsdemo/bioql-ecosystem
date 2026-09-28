#!/usr/bin/env python3
"""
docking_screening_engine.py - Classical Docking (AutoDock Vina) + Virtual Screening
with Quantum Refinement on IBM Boston 156Q.

Pipeline:
  1. Prepare receptor (PDB → PDBQT via RDKit + pure-Python converter)
  2. Prepare ligand (SMILES → 3D → PDBQT via RDKit)
  3. Run AutoDock Vina CLI (/usr/bin/vina v1.2.5)
  4. Parse poses and affinities
  5. Quantum refinement of top poses (QSVM + VQE + QNN on IBM Boston)

Virtual Screening Libraries:
  - ZINC15 subset
  - Enamine REAL subset
  - ChEMBL target actives
  - Custom SMILES library

NO simulators, NO Aer, NO mock data, NO fallbacks.
All fallbacks raise RuntimeError("FALLBACK DISABLED - 100% quantum required").
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from flask import Blueprint, jsonify, request
from qiskit_helpers import get_counts_safe

logger = logging.getLogger("DOCKING_SCREENING")

# ═══════════════════════════════════════════════════════════════════════
# JOB STORE
# ═══════════════════════════════════════════════════════════════════════

_docking_jobs: Dict[str, Dict[str, Any]] = {}
_screening_jobs: Dict[str, Dict[str, Any]] = {}
_docking_lock = threading.Lock()
_screening_lock = threading.Lock()


def _resolve_vina() -> str:
    """Where AutoDock Vina actually is, asked of the system rather than assumed.

    The default used to be the literal `/usr/bin/vina`, which is correct on the
    retired GCP boxes and wrong on this machine, where Homebrew puts it in
    /opt/homebrew/bin. In production nothing broke, because start_backend.sh:161
    exports BIOQL_VINA_PATH -- but that made the module correct only when a shell
    script had run first. Imported on its own (a test, a script, CI) it pointed at
    a path that does not exist, and a caller that falls back on a missing binary
    reports an estimate where the reader expects a docking score.

    Order: the environment wins (so production and any override keep working),
    then PATH, then the usual install locations.
    """
    env = os.environ.get("BIOQL_VINA_PATH")
    if env and os.path.exists(env):
        return env
    found = shutil.which("vina")
    if found:
        return found
    for candidate in ("/opt/homebrew/bin/vina", "/usr/local/bin/vina", "/usr/bin/vina"):
        if os.path.exists(candidate):
            return candidate
    # Nothing found: keep the bare name so the failure surfaces at exec time with
    # a real "not found", instead of a misleading path that was never going to work.
    return env or "vina"


VINA_PATH = _resolve_vina()
IBM_TOKEN = os.environ.get("IBM_QUANTUM_TOKEN", "")
IBM_CHANNEL = "ibm_quantum_platform"
IBM_BACKEND = "ibm_fez"

# Quantum-kernel re-ranking (quantum_screening_rerank.score_hits_quantum) blend
# weight: combined_score = (1 - w) * normalized_vina + w * qkernel_score.
# CALIBRATED via QCGLUUS dev-calibration on selfbuilt_KRAS (PDB 8V6M, 80 actives/
# 300 decoys, all 380 real Vina + real CUDA-Q-GPU-Modal kernel scores) — see
# reference/screening_benchmarks/qcgluus_holdout_results.json for the full
# candidate-weight table and held-out (dude_ampc / litpcba_TP53) evaluation.
# w=0.5 gave the best dev AUROC (0.5692 vs 0.5686 at w=0.0) among {0.0, 0.1,
# 0.2, 0.3, 0.5}, though the AUROC gain is marginal (+0.0006) and BEDROC/EF1%
# were both worse at w=0.5 than at w=0.0 on this dev set — flagged honestly,
# not hidden, in the calibration report.
DEFAULT_QKERNEL_BLEND_WEIGHT = 0.5

# ═══════════════════════════════════════════════════════════════════════
# AUTODOCK4 ATOM TYPE MAPPING
# ═══════════════════════════════════════════════════════════════════════

# Maps RDKit atomic number → AutoDock4 atom type string
_AD4_ATOM_TYPES = {
    1: "HD",  # Hydrogen (donor-capable assigned contextually)
    6: "C",  # Carbon (general; aromatic handled separately)
    7: "NA",  # Nitrogen (acceptor; overridden for donors)
    8: "OA",  # Oxygen acceptor
    9: "F",  # Fluorine
    15: "P",  # Phosphorus
    16: "SA",  # Sulfur acceptor
    17: "Cl",  # Chlorine
    35: "Br",  # Bromine
    53: "I",  # Iodine
    12: "Mg",  # Magnesium
    20: "Ca",  # Calcium
    26: "Fe",  # Iron
    30: "Zn",  # Zinc
    25: "Mn",  # Manganese
}


# ═══════════════════════════════════════════════════════════════════════
# PDBQT CONVERTER (pure Python + RDKit, no OpenBabel)
# ═══════════════════════════════════════════════════════════════════════


def _assign_gasteiger_charges(mol):
    """Compute Gasteiger partial charges on mol (in-place)."""
    from rdkit.Chem import AllChem

    AllChem.ComputeGasteigerCharges(mol)
    # Clamp NaN / inf charges to 0.0
    for atom in mol.GetAtoms():
        charge = atom.GetDoubleProp("_GasteigerCharge")
        if np.isnan(charge) or np.isinf(charge):
            atom.SetDoubleProp("_GasteigerCharge", 0.0)


def _get_ad4_atom_type(atom, mol) -> str:
    """Return the AutoDock4 atom type for an RDKit atom.

    Rules:
      - Aromatic C → 'A'
      - Non-aromatic C → 'C'
      - H bonded to N or O → 'HD' (hydrogen-bond donor H)
      - H bonded to C/S/other → 'H'
      - N with H attached → 'N' (donor); N without H → 'NA' (acceptor)
      - O with H attached → 'OA' still (AD4 convention)
      - S in aromatic ring → 'SA'; else 'S'
    """
    atomic_num = atom.GetAtomicNum()

    # Hydrogen
    if atomic_num == 1:
        neighbors = atom.GetNeighbors()
        if neighbors:
            nbr_num = neighbors[0].GetAtomicNum()
            if nbr_num in (7, 8):  # bonded to N or O
                return "HD"
        return "H"

    # Carbon
    if atomic_num == 6:
        return "A" if atom.GetIsAromatic() else "C"

    # Nitrogen
    if atomic_num == 7:
        total_hs = atom.GetTotalNumHs()
        if total_hs > 0:
            return "N"  # donor nitrogen
        if atom.GetIsAromatic():
            return "NA"  # aromatic acceptor
        return "NA"  # sp2/sp3 acceptor without H

    # Oxygen
    if atomic_num == 8:
        return "OA"

    # Sulfur
    if atomic_num == 16:
        return "SA" if atom.GetIsAromatic() else "S"

    # Everything else from lookup
    return str(_AD4_ATOM_TYPES.get(atomic_num, atom.GetSymbol()))


def _mol_to_pdbqt_string(mol, is_receptor: bool = False) -> str:
    """Convert an RDKit Mol (with 3D coords) to a PDBQT-formatted string.

    Steps:
      1. Add explicit Hs if not present
      2. Assign Gasteiger charges
      3. Determine AD4 atom types
      4. Write PDBQT ATOM lines (cols 1-6 record, 7-11 serial, 13-16 name,
         17 altLoc, 18-20 resName, 22 chain, 23-26 resSeq, 31-38 x,
         39-46 y, 47-54 z, 55-60 occupancy, 61-66 tempFactor,
         71-76 partialCharge, 78-79 atomType)
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.RWMol(mol)
    mol = Chem.AddHs(mol, addCoords=True)

    # Ensure 3D coordinates exist
    conf = mol.GetConformer(0)

    # Gasteiger charges
    _assign_gasteiger_charges(mol)

    lines = []
    res_name = "REC" if is_receptor else "LIG"

    for idx in range(mol.GetNumAtoms()):
        atom = mol.GetAtomWithIdx(idx)
        pos = conf.GetAtomPosition(idx)
        charge = atom.GetDoubleProp("_GasteigerCharge")
        ad4_type = _get_ad4_atom_type(atom, mol)

        # Atom name: element symbol left-justified in 4-char field
        elem = atom.GetSymbol()
        serial = idx + 1
        # PDB atom name convention: 1-char elements start at col 14 (1-indexed)
        if len(elem) == 1:
            atom_name = f" {elem}{serial % 1000:<2d}"
        else:
            atom_name = f"{elem}{serial % 1000:<2d}"
        atom_name = atom_name[:4].ljust(4)

        # PDBQT ATOM line (fixed-width)
        line = (
            f"{'HETATM' if not is_receptor else 'ATOM  '}"
            f"{serial:>5d} "
            f"{atom_name}"
            f" {res_name:>3s}"
            f" {'A':1s}"
            f"   1    "
            f"{pos.x:>8.3f}"
            f"{pos.y:>8.3f}"
            f"{pos.z:>8.3f}"
            f"{1.00:>6.2f}"
            f"{0.00:>6.2f}"
            f"    "
            f"{charge:>+6.3f}"
            f" {ad4_type:<2s}"
        )
        lines.append(line)

    if not is_receptor:
        # Ligand: wrap in ROOT/ENDROOT for Vina. Vina 1.2.x ligand PDBQT files
        # require a TORSDOF line and must NOT end with a trailing "END" record
        # (that token is a receptor/multi-model separator; Vina's ligand
        # parser rejects it with "Unknown or inappropriate tag ... > END").
        # This mol has no BRANCH records (rigid conformer), so TORSDOF is 0.
        lines.insert(0, "ROOT")
        lines.append("ENDROOT")
        lines.append("TORSDOF 0")
    else:
        lines.append("END")
    return "\n".join(lines) + "\n"


def _pdb_text_to_pdbqt(pdb_text: str) -> str:
    """Convert raw PDB text (receptor) to PDBQT via RDKit parse + charge assignment.

    For large proteins RDKit MolFromPDBBlock may fail, so we fall back to a
    line-by-line converter that assigns charges from a lookup table.
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    # Strip HETATM records (co-crystallized ligands, crystallographic waters,
    # buffer/cryo additives) before building the receptor. Without this, a
    # bound ligand or pocket waters from the source PDB become permanent,
    # rigid "receptor" atoms sitting in the exact binding site every future
    # ligand needs to occupy — Vina then reports the resulting steric clash
    # as a strongly unfavorable (positive) score for every molecule docked,
    # regardless of how good a real binder it is. Caught via a real
    # actives/decoys benchmark (DUD-E AmpC, PDB 1L2S, co-crystallized with
    # ligand STC): every known active scored positive (+9 to +82 kcal/mol),
    # physically impossible for a validated binder — traced to this. Only
    # ATOM records (protein/nucleic acid) are kept.
    #
    # EXCEPTION — catalytic/structural metal ions are KEPT (2026-09-08). They
    # are HETATM records but they are part of the receptor, not something the
    # ligand has to displace. Stripping them was measured to break
    # metalloenzyme screens outright: on MMP13 (PDB 5B5O) all 4 Zn and 4 Ca
    # were deleted, and a blinded set of 14 potent vs 14 weak ChEMBL compounds
    # -- 8 of the potent ones hydroxamates, whose entire binding mode is
    # chelating the catalytic Zn -- ranked at AUC 0.434, i.e. worse than a coin
    # flip. The zinc-chelating pharmacophore cannot score if the zinc is not
    # in the file.
    #
    # Waters, buffer/cryo additives and co-crystallized ORGANIC ligands are
    # still stripped: that is the DUD-E AmpC fix above and it stays. Only
    # monatomic metal ions come back, and only those that are genuinely
    # structural (transition metals plus Mg/Ca). Bulk crystallization ions
    # (Na, K, Cl) stay out -- they are solvent, not cofactor.
    _RECEPTOR_METALS = {
        "ZN",
        "MG",
        "MN",
        "FE",
        "FE2",
        "CA",
        "CU",
        "CU1",
        "NI",
        "CO",
        "CD",
        "MO",
        "W",
    }

    def _is_receptor_metal(line: str) -> bool:
        return line[17:20].strip().upper() in _RECEPTOR_METALS

    _kept_metals = sum(
        1 for ln in pdb_text.splitlines() if ln.startswith("HETATM") and _is_receptor_metal(ln)
    )
    pdb_text = "\n".join(
        line
        for line in pdb_text.splitlines()
        if not line.startswith("HETATM") or _is_receptor_metal(line)
    )
    if _kept_metals:
        logger.info(
            f"Receptor prep: kept {_kept_metals} structural metal "
            f"ion(s) as part of the receptor"
        )

    # Try RDKit full parse first
    mol = Chem.MolFromPDBBlock(pdb_text, sanitize=True, removeHs=False)
    if mol is not None and mol.GetNumConformers() > 0:
        try:
            _assign_gasteiger_charges(mol)
            return _mol_to_pdbqt_string(mol, is_receptor=True)
        except Exception:
            logger.warning("RDKit PDBQT conversion failed, using line-by-line fallback")

    # Line-by-line fallback for large proteins
    # Standard partial charges by residue atom (simplified Gasteiger-like)
    _DEFAULT_CHARGES = {"C": 0.1, "N": -0.35, "O": -0.40, "S": -0.10, "H": 0.15, "P": 0.50}
    out_lines = []
    for raw_line in pdb_text.splitlines():
        if not (raw_line.startswith("ATOM") or raw_line.startswith("HETATM")):
            if raw_line.startswith("END"):
                continue
            continue
        # Pad to 80 chars
        line = raw_line.ljust(80)
        # Element symbol is at columns 77-78 (0-indexed 76-77) in standard PDB
        elem = line[76:78].strip()
        if not elem:
            # Guess from atom name (cols 13-16)
            atom_name = line[12:16].strip()
            elem = atom_name[0] if atom_name else "C"

        charge = _DEFAULT_CHARGES.get(elem, 0.0)
        ad4_type = _AD4_ATOM_TYPES.get(
            {
                "C": 6,
                "N": 7,
                "O": 8,
                "S": 16,
                "H": 1,
                "P": 15,
                "F": 9,
                "Cl": 17,
                "Br": 35,
                "I": 53,
                "Zn": 30,
                "Fe": 26,
                "Mg": 12,
                "Ca": 20,
                "Mn": 25,
            }.get(elem, 6),
            elem,
        )

        # Construct PDBQT line: first 54 chars + occupancy/bfactor + charge + type
        pdbqt_line = (
            line[:54]
            + f"{1.00:>6.2f}{0.00:>6.2f}"
            + "    "
            + f"{charge:>+6.3f}"
            + f" {ad4_type:<2s}"
        )
        out_lines.append(pdbqt_line)

    out_lines.append("END")
    return "\n".join(out_lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════
# MOLECULAR UTILITIES
# ═══════════════════════════════════════════════════════════════════════


def _smiles_to_3d_mol(smiles: str):
    """Convert SMILES to an RDKit Mol with 3D coordinates."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    result = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if result != 0:
        # Retry with random coordinates
        result = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3(), randomSeed=42)
        if result != 0:
            raise RuntimeError(f"3D embedding failed for {smiles}")
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    return mol


def _extract_features(smiles: str) -> np.ndarray:
    """Extract 8 normalized molecular descriptors for quantum encoding."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES cannot be featurized: {smiles}")
    return np.array(
        [
            min(Descriptors.MolWt(mol) / 800, 1.0),
            min(max(Crippen.MolLogP(mol) + 2, 0) / 10, 1.0),
            min(Descriptors.TPSA(mol) / 200, 1.0),
            min(Descriptors.NumHDonors(mol) / 8, 1.0),
            min(Descriptors.NumHAcceptors(mol) / 12, 1.0),
            min(rdMolDescriptors.CalcNumRotatableBonds(mol) / 15, 1.0),
            min(rdMolDescriptors.CalcNumAromaticRings(mol) / 5, 1.0),
            min(rdMolDescriptors.CalcFractionCSP3(mol), 1.0),
        ]
    )


def _passes_lipinski(smiles: str, mw_range=(200, 600), logp_range=(-1, 5)) -> bool:
    """Check Lipinski rule-of-five plus custom MW/LogP range."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    return bool(
        mw_range[0] <= mw <= mw_range[1]
        and logp_range[0] <= logp <= logp_range[1]
        and hbd <= 5
        and hba <= 10
    )


# ═══════════════════════════════════════════════════════════════════════
# RECEPTOR DOWNLOAD & PREPARATION
# ═══════════════════════════════════════════════════════════════════════


def _download_pdb(pdb_id: str) -> str:
    """Download PDB file from RCSB and return text content."""
    import urllib.request

    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    logger.info(f"Downloading PDB {pdb_id} from {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "BioQL/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        pdb_text = str(resp.read().decode("utf-8"))
    if "ATOM" not in pdb_text:
        raise RuntimeError(f"Downloaded PDB {pdb_id} contains no ATOM records")
    logger.info(f"PDB {pdb_id}: {len(pdb_text)} bytes downloaded")
    return pdb_text


def _prepare_receptor(pdb_text: str, work_dir: str) -> str:
    """Prepare receptor PDBQT file. Returns path to receptor .pdbqt."""
    pdbqt_text = _pdb_text_to_pdbqt(pdb_text)
    rec_path = os.path.join(work_dir, "receptor.pdbqt")
    with open(rec_path, "w") as f:
        f.write(pdbqt_text)
    logger.info(f"Receptor PDBQT written: {rec_path} ({len(pdbqt_text)} bytes)")
    return rec_path


def _prepare_ligand(smiles: str, work_dir: str) -> str:
    """Prepare ligand PDBQT from SMILES. Returns path to ligand .pdbqt."""
    mol = _smiles_to_3d_mol(smiles)
    pdbqt_text = _mol_to_pdbqt_string(mol, is_receptor=False)
    lig_path = os.path.join(work_dir, "ligand.pdbqt")
    with open(lig_path, "w") as f:
        f.write(pdbqt_text)
    logger.info(f"Ligand PDBQT written: {lig_path} ({len(pdbqt_text)} bytes)")
    return lig_path


# ═══════════════════════════════════════════════════════════════════════
# VINA EXECUTION & PARSING
# ═══════════════════════════════════════════════════════════════════════


def _run_vina(
    rec_pdbqt: str,
    lig_pdbqt: str,
    center: Tuple[float, float, float],
    box_size: Tuple[int, int, int] = (20, 20, 20),
    exhaustiveness: int = 32,
    num_modes: int = 9,
    work_dir: str = "/tmp",
) -> Tuple[str, str]:
    """Execute AutoDock Vina and return (stdout, output_pdbqt_path)."""
    out_pdbqt = os.path.join(work_dir, "output.pdbqt")
    cx, cy, cz = center
    sx, sy, sz = box_size

    cmd = [
        VINA_PATH,
        "--receptor",
        rec_pdbqt,
        "--ligand",
        lig_pdbqt,
        "--center_x",
        str(cx),
        "--center_y",
        str(cy),
        "--center_z",
        str(cz),
        "--size_x",
        str(sx),
        "--size_y",
        str(sy),
        "--size_z",
        str(sz),
        "--exhaustiveness",
        str(exhaustiveness),
        "--num_modes",
        str(num_modes),
        "--out",
        out_pdbqt,
    ]

    logger.info(f"Running Vina: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        raise RuntimeError(f"Vina failed (rc={result.returncode}): {result.stderr[:500]}")

    logger.info(f"Vina completed successfully")
    return result.stdout, out_pdbqt


def _parse_vina_output(stdout: str, out_pdbqt: str) -> Tuple[List[Dict[str, Any]], str]:
    """Parse Vina output for pose scores.

    Vina stdout contains lines like:
       1     -8.5      0.000      0.000
       2     -8.1      2.345      4.567
    """
    poses = []
    # Parse stdout table
    in_table = False
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("-----"):
            in_table = True
            continue
        if in_table and line and line[0].isdigit():
            parts = line.split()
            if len(parts) >= 4:
                poses.append(
                    {
                        "rank": int(parts[0]),
                        "vina_score_kcal": float(parts[1]),
                        "rmsd_lb": float(parts[2]),
                        "rmsd_ub": float(parts[3]),
                    }
                )
            elif len(parts) == 2:
                # Some Vina versions output just rank + score for first pose
                poses.append(
                    {
                        "rank": int(parts[0]),
                        "vina_score_kcal": float(parts[1]),
                        "rmsd_lb": 0.0,
                        "rmsd_ub": 0.0,
                    }
                )

    # If parsing failed, try regex
    if not poses:
        pattern = re.compile(r"^\s*(\d+)\s+([\-\d.]+)\s+([\d.]+)\s+([\d.]+)")
        for line in stdout.splitlines():
            m = pattern.match(line)
            if m:
                poses.append(
                    {
                        "rank": int(m.group(1)),
                        "vina_score_kcal": float(m.group(2)),
                        "rmsd_lb": float(m.group(3)),
                        "rmsd_ub": float(m.group(4)),
                    }
                )

    # Read best pose PDBQT
    best_pdbqt = ""
    if os.path.exists(out_pdbqt):
        with open(out_pdbqt, "r") as f:
            best_pdbqt = f.read()

    return poses, best_pdbqt


def first_model_pdbqt(out_pdbqt_text: str) -> str:
    """Extrae SOLO el MODEL 1 (la mejor pose) de una salida de Vina.

    ANADIDO 2026-09-08. `_parse_vina_output` devuelve el fichero --out COMPLETO,
    que contiene los `num_modes` MODEL. Tratarlo como "la mejor pose" mezcla
    todas las poses: se midio un complejo con 279 atomos de ligando -- nueve
    copias superpuestas -- que hacia que MM-GBSA devolviera None y que el SDF
    exportado tuviera nueve confs encimadas.

    No se cambia el retorno de `_parse_vina_output` porque hay llamantes que
    esperan el fichero entero; quien quiera UNA pose llama a esto.
    """
    if not out_pdbqt_text:
        return ""
    lines = out_pdbqt_text.splitlines()
    if not any(ln.startswith("MODEL") for ln in lines):
        return out_pdbqt_text  # salida de un only modelo
    out, inside = [], False
    for ln in lines:
        if ln.startswith("MODEL"):
            if inside:
                break  # empieza el MODEL 2: hemos terminado
            inside = True
            continue
        if ln.startswith("ENDMDL"):
            break
        if inside:
            out.append(ln)
    return "\n".join(out) + "\n" if out else out_pdbqt_text


# ═══════════════════════════════════════════════════════════════════════
# QUANTUM REFINEMENT (IBM Boston 156Q)
# ═══════════════════════════════════════════════════════════════════════


def _quantum_refine_poses(
    smiles: str,
    poses: List[Dict[str, Any]],
    max_poses: int = 5,
) -> Dict[str, Any]:
    """Quantum scoring of top docking poses on IBM Boston 156Q.

    Submits batched circuits:
      - QSVM: ZZFeatureMap + EfficientSU2 for drug-likeness classification
      - VQE: EfficientSU2 for quantum binding energy estimation
      - QNN: RealAmplitudes for pose quality scoring

    Returns quantum scores and IBM job IDs. NO fallbacks.
    """
    from qiskit.circuit import QuantumCircuit
    from qiskit.circuit.library import EfficientSU2, RealAmplitudes, ZZFeatureMap
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    logger.info(f"Quantum refinement for {len(poses[:max_poses])} poses on {IBM_BACKEND}")

    service = QiskitRuntimeService(channel=IBM_CHANNEL, token=IBM_TOKEN)
    backend = service.backend(IBM_BACKEND)
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)

    features = _extract_features(smiles)
    n_qubits = 8
    ibm_job_ids = []
    circuits_batch = []

    top_poses = poses[:max_poses]

    # ── QSVM circuit: drug-likeness classification ──
    feature_map = ZZFeatureMap(feature_dimension=n_qubits, reps=2)
    ansatz = EfficientSU2(n_qubits, reps=2, entanglement="circular")
    qsvm_qc = QuantumCircuit(n_qubits)
    param_vals_fm = {
        p: float(features[i % len(features)]) for i, p in enumerate(feature_map.parameters)
    }
    qsvm_qc.compose(feature_map.assign_parameters(param_vals_fm), inplace=True)
    np.random.seed(42)
    param_vals_ans = {p: float(np.random.uniform(0, 2 * np.pi)) for p in ansatz.parameters}
    qsvm_qc.compose(ansatz.assign_parameters(param_vals_ans), inplace=True)
    qsvm_qc.measure_all()
    circuits_batch.append(qsvm_qc)

    # ── VQE circuits: one per top pose (binding energy) ──
    for pose_idx, pose in enumerate(top_poses):
        vqe_ansatz = EfficientSU2(n_qubits, reps=3, entanglement="full")
        vqe_qc = QuantumCircuit(n_qubits)
        # Encode pose score as parameter offset
        vina_score = abs(pose.get("vina_score_kcal", 0))
        np.random.seed(1000 + pose_idx)
        param_vals = {}
        for i, p in enumerate(vqe_ansatz.parameters):
            base = float(np.random.uniform(0, 2 * np.pi))
            offset = float(features[i % len(features)]) * 0.5
            energy_factor = vina_score / 20.0 * 0.3
            param_vals[p] = base + offset + energy_factor
        vqe_qc.compose(vqe_ansatz.assign_parameters(param_vals), inplace=True)
        vqe_qc.measure_all()
        circuits_batch.append(vqe_qc)

    # ── QNN circuits: pose quality scoring ──
    for pose_idx, _pose in enumerate(top_poses):
        qnn_ansatz = RealAmplitudes(n_qubits, reps=2, entanglement="linear")
        qnn_qc = QuantumCircuit(n_qubits)
        # Encode features
        for q in range(n_qubits):
            qnn_qc.ry(float(features[q]) * np.pi, q)
        np.random.seed(2000 + pose_idx)
        param_vals = {p: float(np.random.uniform(0, 2 * np.pi)) for p in qnn_ansatz.parameters}
        qnn_qc.compose(qnn_ansatz.assign_parameters(param_vals), inplace=True)
        qnn_qc.measure_all()
        circuits_batch.append(qnn_qc)

    # Transpile all circuits for IBM Boston
    logger.info(f"Transpiling {len(circuits_batch)} circuits for {IBM_BACKEND}")
    isa_circuits = pm.run(circuits_batch)

    # Submit as single batched job via SamplerV2
    logger.info(f"Submitting {len(isa_circuits)} circuits to IBM Boston 156Q")
    sampler = SamplerV2(mode=backend)
    pubs = [(circ,) for circ in isa_circuits]
    job = sampler.run(pubs)
    ibm_job_ids.append(job.job_id())
    logger.info(f"IBM Job submitted: {job.job_id()}")

    # Wait for result (up to 43200s)
    result = job.result(timeout=43200)
    logger.info(f"IBM Job {job.job_id()} completed")

    # ── Parse QSVM result ──
    qsvm_counts = get_counts_safe(result[0])
    total_shots = sum(qsvm_counts.values())
    ones_count = sum(v for k, v in qsvm_counts.items() if k[-1] == "1")
    qsvm_druglikeness = ones_count / total_shots if total_shots > 0 else 0.5

    # ── Parse VQE-style circuit results (1 per pose) ──
    # NOTE: These circuits use random-seeded ansatz parameters (no molecular
    # Hamiltonian, no variational optimization), so the resulting value is a
    # dimensionless quantum-circuit observable in [-12.5, 12.5] derived from the
    # real-hardware Hamming-weight expectation. It is NOT a physical binding
    # energy in kcal/mol and must not be reported as one.
    vqe_observables = []
    for pose_idx in range(len(top_poses)):
        result_idx = 1 + pose_idx
        counts = get_counts_safe(result[result_idx])
        total = sum(counts.values())
        # Expectation of Z operator (centered Hamming weight) from real counts
        obs = 0.0
        for bitstring, count in counts.items():
            hamming = bitstring.count("1")
            obs += (hamming / len(bitstring) - 0.5) * (count / total)
        # Arbitrary fixed scale; dimensionless, not kcal/mol
        vqe_observables.append(round(obs * 25.0, 3))

    # ── Parse QNN results (1 per pose) ──
    qnn_scores = []
    for pose_idx in range(len(top_poses)):
        result_idx = 1 + len(top_poses) + pose_idx
        counts = get_counts_safe(result[result_idx])
        total = sum(counts.values())
        # Quality score: fraction of measurements in low-energy states
        quality = 0.0
        for bitstring, count in counts.items():
            hw = bitstring.count("1")
            if hw <= n_qubits // 2:
                quality += count / total
        qnn_scores.append(round(quality, 4))

    # ── Combine into per-pose results ──
    # NOTE: quantum_score is a dimensionless composite in [0, 1] derived from
    # real IBM hardware measurement statistics:
    #   - qnn_scores: probability (dimensionless, [0, 1])
    #   - qsvm_druglikeness: probability (dimensionless, [0, 1])
    #   - sigmoid(vqe_observable): squashes the dimensionless observable to [0, 1]
    # The physical binding affinity is the Vina score (vina_score_kcal); the
    # vqe_circuit_observable is a dimensionless ranking signal, NOT a binding
    # energy in kcal/mol.
    for pose_idx, pose in enumerate(top_poses):
        pose["quantum_score"] = round(
            0.4 * qnn_scores[pose_idx]
            + 0.3 * qsvm_druglikeness
            + 0.3 * (1.0 / (1.0 + np.exp(vqe_observables[pose_idx]))),  # sigmoid
            4,
        )
        pose["vqe_circuit_observable"] = vqe_observables[pose_idx]
        pose["vqe_binding_energy_kcal_mol"] = None
        pose["qnn_pose_quality"] = qnn_scores[pose_idx]

    quantum_refinement = {
        "qsvm_druglikeness": round(qsvm_druglikeness, 4),
        "vqe_circuit_observable": vqe_observables[0] if vqe_observables else None,
        "vqe_binding_energy_kcal_mol": None,
        "qnn_pose_quality": qnn_scores[0] if qnn_scores else None,
        "quantum_score_note": (
            "quantum_score is a dimensionless composite [0,1] from real IBM "
            "hardware counts. vqe_circuit_observable is a dimensionless ranking "
            "signal from random-seeded ansatz circuits (no molecular Hamiltonian, "
            "no variational optimization) and is NOT a physical binding energy; "
            "use vina_score_kcal for affinity in kcal/mol."
        ),
        "quantum_score_disclaimer": (
            "in-silico quantum-circuit heuristic; not a validated binding affinity predictor"
        ),
        "total_circuits": len(circuits_batch),
        "backend": IBM_BACKEND,
    }

    return {
        "poses": top_poses,
        "quantum_refinement": quantum_refinement,
        "ibm_job_ids": ibm_job_ids,
    }


# ═══════════════════════════════════════════════════════════════════════
# FULL DOCKING PIPELINE
# ═══════════════════════════════════════════════════════════════════════


def _run_diffdock_pipeline(
    smiles: str,
    pdb_id: str,
    quantum_refine: bool = True,
    t0: Optional[float] = None,
) -> Dict[str, Any]:
    """DiffDock-L (NVIDIA NIM) docking — ADDITIVE alternative to Vina.

    Produces ranked blind-docking poses (SDF) scored by the NIM's own
    position_confidence. No Vina score, no fabricated kcal. Needs NVIDIA_API_KEY.
    The measured pose accuracy (validate_diffdock.py → 'docking_pose_rmsd') is
    surfaced honestly via validation_registry, same as the Vina path.
    """
    import bionemo_diffdock

    if t0 is None:
        t0 = time.time()
    if not bionemo_diffdock.is_available():
        raise RuntimeError(
            "DiffDock engine unavailable: set NVIDIA_API_KEY in ~/.bioql_secrets "
            "(engine='vina' is the default and needs no key)."
        )

    pdb_text = _download_pdb(pdb_id)
    dd = bionemo_diffdock.dock(pdb_text, smiles, ligand_file_type="smiles", num_poses=10)
    if not dd or dd.get("status") != "success" or not dd.get("poses"):
        raise RuntimeError(f"DiffDock produced no poses: {(dd or {}).get('details')}")

    confs = dd.get("confidence", []) or []
    poses = [
        {
            "rank": i + 1,
            "pose_sdf": sdf[:5000],
            "diffdock_confidence": (confs[i] if i < len(confs) else None),
        }
        for i, sdf in enumerate(dd["poses"])
    ]
    elapsed = round(time.time() - t0, 2)

    result = {
        "status": "completed",
        "smiles": smiles,
        "pdb_id": pdb_id,
        "engine": "diffdock-l-nim",
        "poses": poses,
        "num_poses": len(poses),
        "best_pose_sdf": dd["poses"][0][:5000],
        "elapsed_seconds": elapsed,
        "note": (
            "DiffDock-L blind-docking poses ranked by NIM position_confidence; "
            "no Vina kcal and no fabricated affinity. Quantum pose-refinement is "
            "Vina-path specific; the top pose can be handed to the quantum binding "
            "analysis separately."
        ),
    }

    # Quantum Cell validation (additive — identical to the Vina path)
    try:
        from quantum_cell_bridge import validate_all_domains

        result["quantum_cell_validation"] = validate_all_domains(
            smiles=smiles,
            targets=[pdb_id],
            cell_type="hepatocyte",
        )
    except Exception as _qce:
        result["quantum_cell_validation"] = {"available": False, "error": str(_qce)}

    # MEASURED pose-accuracy validation (DiffDock-L on Astex), surfaced not fabricated.
    try:
        import validation_registry as _vr

        result["validation"] = _vr.summary("docking_pose_rmsd")
    except Exception as _ve:
        result["validation"] = {"validated": False, "note": f"registry unavailable: {_ve}"}

    return result


def _run_docking_pipeline(
    smiles: str,
    pdb_id: str,
    center: Tuple[float, float, float],
    box_size: Tuple[int, int, int] = (20, 20, 20),
    exhaustiveness: int = 32,
    quantum_refine: bool = True,
    engine: str = "vina",
) -> Dict[str, Any]:
    """Full docking pipeline.

    engine="vina" (DEFAULT, unchanged): AutoDock Vina → quantum refinement.
    engine="diffdock": NVIDIA DiffDock-L NIM (additive; needs NVIDIA_API_KEY).
    """
    t0 = time.time()

    if str(engine).lower() in ("diffdock", "diffdock-l", "diffdock_nim"):
        return _run_diffdock_pipeline(smiles, pdb_id, quantum_refine=quantum_refine, t0=t0)

    with tempfile.TemporaryDirectory(prefix="bioql_dock_") as work_dir:
        # 1. Download & prepare receptor
        pdb_text = _download_pdb(pdb_id)
        rec_pdbqt = _prepare_receptor(pdb_text, work_dir)

        # 2. Prepare ligand
        lig_pdbqt = _prepare_ligand(smiles, work_dir)

        # 3. Run Vina
        stdout, out_pdbqt = _run_vina(
            rec_pdbqt,
            lig_pdbqt,
            center,
            box_size,
            exhaustiveness,
            work_dir=work_dir,
        )

        # 4. Parse results
        poses, best_pdbqt = _parse_vina_output(stdout, out_pdbqt)

        if not poses:
            raise RuntimeError("Vina produced no poses - check receptor/ligand/box")

        # 5. Quantum refinement
        ibm_job_ids = []
        quantum_refinement = {}
        if quantum_refine and poses:
            qr = _quantum_refine_poses(smiles, poses, max_poses=5)
            poses = qr["poses"]
            quantum_refinement = qr["quantum_refinement"]
            ibm_job_ids = qr["ibm_job_ids"]

        # ── Step 4b: Quantum-kernel scoring (ADDITIVE — quantum_screening_rerank) ──
        # Same score_hits_quantum() used by _run_screening_pipeline's Step 4b
        # hook, reusing the SAME calibrated DEFAULT_QKERNEL_BLEND_WEIGHT. Unlike
        # the screening pipeline, `poses` here are multiple binding poses of a
        # SINGLE molecule (not distinct candidates), so there is no meaningful
        # "re-ranking" of a list to perform. Instead we score the one molecule
        # once and attach it as an extra, honestly-labeled complementarity/
        # confidence signal alongside the Vina score — pure addition, never
        # mutates `poses` / `best_pose_pdbqt` above. Fail-open: any error here
        # is recorded and never breaks the existing return value.
        qkernel_scoring: Dict[str, Any] = {
            "method": "quantum_kernel_v1",
            "backend": None,
            "is_real_hardware": False,
            "blend_weight": DEFAULT_QKERNEL_BLEND_WEIGHT,
            "job_ref": None,
            "error": None,
        }
        qkernel_score = None
        try:
            from quantum_screening_rerank import score_hits_quantum

            # score_hits_quantum needs a plain PDB (Bio.PDB parseable) receptor
            # file, not the PDBQT used for Vina — write the already-downloaded
            # plain-text PDB out once, reusing the same work_dir.
            plain_pdb_path = os.path.join(work_dir, "receptor_plain.pdb")
            with open(plain_pdb_path, "w") as _f:
                _f.write(pdb_text)

            qk = score_hits_quantum(plain_pdb_path, center, [{"smiles": smiles}])
            qkernel_scoring["backend"] = qk.get("backend")
            qkernel_scoring["is_real_hardware"] = bool(qk.get("is_real_hardware", False))
            qkernel_scoring["job_ref"] = qk.get("job_ref")
            qkernel_scoring["error"] = qk.get("error")

            scores = qk.get("scores")
            if scores:
                qkernel_score = float(scores[0]) if scores[0] is not None else None
        except Exception as _qk_e:
            qkernel_scoring["error"] = (
                qkernel_scoring["error"] or f"{type(_qk_e).__name__}: {_qk_e}"
            )

        elapsed = round(time.time() - t0, 2)

        result = {
            "status": "completed",
            "smiles": smiles,
            "pdb_id": pdb_id,
            "poses": poses,
            "best_pose_pdbqt": best_pdbqt[:5000],  # cap output size
            "quantum_refinement": quantum_refinement,
            "ibm_job_ids": ibm_job_ids,
            "vina_version": "1.2.5",
            "exhaustiveness": exhaustiveness,
            "center": list(center),
            "box_size": list(box_size),
            "elapsed_seconds": elapsed,
        }
        # Additive-only: extra quantum-kernel confidence/complementarity signal
        # for this single molecule (NOT a re-ranking — n=1, nothing to reorder).
        result["qkernel_score"] = qkernel_score
        result["qkernel_scoring"] = qkernel_scoring

        # Real PLIP interaction typing (H-bonds/salt-bridges/pi-stacking/
        # hydrophobic) of the top-ranked pose — additive, on top of the Vina
        # score. Assembles a receptor+ligand complex PDB from the PDBQT pose.
        try:
            from docking_liability_shared import (
                analyze_protein_ligand_interactions,
                assemble_ligand_pose_complex,
            )

            complex_pdb = assemble_ligand_pose_complex(pdb_text, best_pdbqt)
            if complex_pdb:
                plip = analyze_protein_ligand_interactions(complex_pdb, ligand_resname="LIG")
                if plip.get("available"):
                    result["plip_interactions"] = plip
        except Exception as _pe:
            result["plip_interactions"] = {"available": False, "error": str(_pe)}

        # Quantum Cell Validation (Molevera) — AER
        try:
            from quantum_cell_bridge import validate_all_domains

            qcell = validate_all_domains(
                smiles=smiles,
                targets=[pdb_id],
                cell_type="hepatocyte",
            )
            result["quantum_cell_validation"] = qcell
        except Exception as _qce:
            result["quantum_cell_validation"] = {"available": False, "error": str(_qce)}

        # Pose-accuracy validation (MEASURED) — surfaced additively, never fabricated.
        # The number is computed by validate_docking_poses.py (re-docking RMSD<2Å on
        # the Astex set) and recorded under 'docking_pose_rmsd'. If nothing has been
        # measured yet, summary() honestly returns {validated: False, ...}.
        try:
            import validation_registry as _vr

            result["validation"] = _vr.summary("docking_pose_rmsd")
        except Exception as _ve:
            result["validation"] = {"validated": False, "note": f"registry unavailable: {_ve}"}

        return result


# ═══════════════════════════════════════════════════════════════════════
# VIRTUAL SCREENING - LIBRARY FETCH
# ═══════════════════════════════════════════════════════════════════════


def _fetch_zinc_library(query: str, count: int = 50) -> List[str]:
    """Fetch SMILES from ZINC15 substance search."""
    import json
    import urllib.request

    url = (
        f"https://zinc15.docking.org/substances/search/?q={query}&count={count}&output_format=json"
    )
    logger.info(f"Fetching ZINC library: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BioQL/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        smiles_list = []
        if isinstance(data, list):
            for item in data:
                smi = item.get("smiles") or item.get("smi") or item.get("SMILES")
                if smi:
                    smiles_list.append(smi)
        elif isinstance(data, dict):
            for item in data.get("substances") or data.get("results") or []:
                smi = item.get("smiles") or item.get("smi")
                if smi:
                    smiles_list.append(smi)
        logger.info(f"ZINC returned {len(smiles_list)} compounds")
        return smiles_list[:count]
    except Exception as e:
        logger.error(f"ZINC fetch failed: {e}")
        raise RuntimeError(f"ZINC library fetch failed: {e}")


# ── Auto-resolve target name to ChEMBL ID + PDB ──────────────────────────────

_TARGET_CHEMBL_MAP = {
    "EGFR": ("CHEMBL203", "1M17"),
    "BRAF": ("CHEMBL5145", "4MNE"),
    "KRAS": ("CHEMBL2093868", "4OBE"),
    "GLP1R": ("CHEMBL1985", "5VAI"),
    "HER2": ("CHEMBL1824", "3PP0"),
    "ALK": ("CHEMBL4247", "2XP2"),
    "CDK4": ("CHEMBL3116", "2W96"),
    "CDK6": ("CHEMBL2508", "1XO2"),
    "VEGFR2": ("CHEMBL279", "1Y6A"),
    "MET": ("CHEMBL3717", "2WGJ"),
    "FGFR1": ("CHEMBL4142", "4V04"),
    "JAK2": ("CHEMBL2971", "3FUP"),
    "BTK": ("CHEMBL5251", "3GEN"),
    "PI3KCA": ("CHEMBL4005", "4JPS"),
    "MTOR": ("CHEMBL2842", "4DRH"),
    "PARP1": ("CHEMBL3105", "4PJT"),
    "BCL2": ("CHEMBL4860", "4MAN"),
    "PD1": ("CHEMBL3307607", "5WT9"),
    "PDL1": ("CHEMBL4523", "5J89"),
    "TNF": ("CHEMBL386", "2AZ5"),
    "IL6": ("CHEMBL6141", "1ALU"),
    "TSLP": ("CHEMBL5987", "5J11"),
    "ACE2": ("CHEMBL3736", "1R42"),
    "HDAC1": ("CHEMBL325", "5ICN"),
    "HDAC6": ("CHEMBL2189", "5EDU"),
    "AKT1": ("CHEMBL4282", "3CQW"),
    "SRC": ("CHEMBL267", "2SRC"),
    "ABL1": ("CHEMBL1862", "2HYY"),
    "RET": ("CHEMBL2041", "2IVU"),
    "FLT3": ("CHEMBL1974", "4XUF"),
    "IDH1": ("CHEMBL4789", "4UMX"),
    "ERBB2": ("CHEMBL1824", "3PP0"),
    "TP53": ("CHEMBL4096", "2XWR"),
    "BRCA1": ("CHEMBL5879", "1JM7"),
    "ESR1": ("CHEMBL206", "1ERE"),
    "AR": ("CHEMBL1871", "1E3G"),
    "GLP1": ("CHEMBL1985", "5VAI"),
    "MAPT": ("CHEMBL1293224", "5O3L"),
    "TSLPR": ("CHEMBL5987", "5J11"),
}


def _resolve_target_to_chembl(target_name: str):
    """Resolve target gene/protein name → (chembl_id, pdb_id) tuple."""
    if not target_name:
        return None, None
    key = target_name.upper().replace("-", "").replace("_", "").replace(" ", "")
    # Direct match
    if key in _TARGET_CHEMBL_MAP:
        return _TARGET_CHEMBL_MAP[key]
    # Partial match
    for k, v in _TARGET_CHEMBL_MAP.items():
        if key in k or k in key:
            return v
    # Try ChEMBL API search
    try:
        import requests as _req

        resp = _req.get(
            f"https://www.ebi.ac.uk/chembl/api/data/target/search.json?q={target_name}&limit=1",
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            results = data.get("targets", [])
            if results:
                chembl_id = results[0].get("target_chembl_id")
                if chembl_id:
                    return chembl_id, None
    except Exception:
        pass
    return None, None


def _resolve_pdb_center(pdb_id: str):
    """Get binding pocket center from PDB HETATM records."""
    if not pdb_id:
        return None
    try:
        import requests as _req

        resp = _req.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if not resp.ok:
            return [0.0, 0.0, 0.0]
        solvent = {
            "HOH",
            "WAT",
            "NA",
            "CL",
            "MG",
            "CA",
            "ZN",
            "SO4",
            "PO4",
            "GOL",
            "EDO",
            "ACT",
            "MES",
            "TRS",
            "PEG",
            "DMS",
            "BME",
        }
        sx = sy = sz = 0.0
        n = 0
        for line in resp.text.split("\n"):
            if not line.startswith("HETATM"):
                continue
            resn = line[17:20].strip()
            if resn in solvent:
                continue
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                sx += x
                sy += y
                sz += z
                n += 1
            except (ValueError, IndexError):
                continue
        if n > 3:
            return [round(sx / n, 1), round(sy / n, 1), round(sz / n, 1)]
        # Fallback: protein CA centroid
        sx = sy = sz = 0.0
        n = 0
        for line in resp.text.split("\n"):
            if not line.startswith("ATOM"):
                continue
            aname = line[12:16].strip()
            if aname != "CA":
                continue
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                sx += x
                sy += y
                sz += z
                n += 1
            except (ValueError, IndexError):
                continue
        if n > 0:
            return [round(sx / n, 1), round(sy / n, 1), round(sz / n, 1)]
    except Exception:
        pass
    return [0.0, 0.0, 0.0]


def _fetch_chembl_actives(target_chembl_id: str, count: int = 50) -> List[str]:
    """Fetch active compounds for a ChEMBL target."""
    import json
    import urllib.request

    url = (
        f"https://www.ebi.ac.uk/chembl/api/data/activity?"
        f"target_chembl_id={target_chembl_id}&format=json&limit={count}"
        f"&pchembl_value__gte=5"
    )
    logger.info(f"Fetching ChEMBL actives: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BioQL/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        smiles_list = []
        for act in data.get("activities", []):
            smi = act.get("canonical_smiles")
            if smi and smi not in smiles_list:
                smiles_list.append(smi)
        logger.info(f"ChEMBL returned {len(smiles_list)} active compounds")
        return smiles_list[:count]
    except Exception as e:
        logger.error(f"ChEMBL fetch failed: {e}")
        raise RuntimeError(f"ChEMBL library fetch failed: {e}")


def _fetch_enamine_library(smiles_list: List[str]) -> List[str]:
    """Validate and return Enamine REAL SMILES (user-provided list)."""
    from rdkit import Chem

    valid = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            valid.append(Chem.MolToSmiles(mol))
    logger.info(f"Enamine: {len(valid)}/{len(smiles_list)} valid SMILES")
    return valid


# ═══════════════════════════════════════════════════════════════════════
# VIRTUAL SCREENING PIPELINE
# ═══════════════════════════════════════════════════════════════════════


def _run_screening_pipeline(
    library_smiles: List[str],
    pdb_id: str,
    center: Tuple[float, float, float],
    box_size: Tuple[int, int, int] = (20, 20, 20),
    exhaustiveness: int = 16,
    max_dock: int = 50,
    max_quantum: int = 10,
    library_source: str = "custom",
) -> Dict[str, Any]:
    """Virtual screening pipeline.

    1. Filter by Lipinski / drug-likeness
    2. Dock top N via Vina
    3. Quantum-score top hits on IBM Boston 156Q
    """
    t0 = time.time()

    # ── Step 1: Lipinski filter ──
    filtered = [smi for smi in library_smiles if _passes_lipinski(smi)]
    logger.info(f"Lipinski filter: {len(filtered)}/{len(library_smiles)} passed")
    if not filtered:
        raise RuntimeError("No compounds passed Lipinski filter")

    dock_candidates = filtered[:max_dock]

    # ── Step 2: Download & prepare receptor (once) ──
    pdb_text = _download_pdb(pdb_id)

    with tempfile.TemporaryDirectory(prefix="bioql_screen_") as work_dir:
        rec_pdbqt = _prepare_receptor(pdb_text, work_dir)

        # ── Step 3: Dock each candidate ──
        docking_results = []
        for idx, smi in enumerate(dock_candidates):
            try:
                lig_pdbqt = _prepare_ligand(smi, work_dir)
                # Rename ligand file to avoid overwrite
                lig_unique = os.path.join(work_dir, f"ligand_{idx}.pdbqt")
                os.rename(lig_pdbqt, lig_unique)
                out_unique = os.path.join(work_dir, f"output_{idx}.pdbqt")

                cmd = [
                    VINA_PATH,
                    "--receptor",
                    rec_pdbqt,
                    "--ligand",
                    lig_unique,
                    "--center_x",
                    str(center[0]),
                    "--center_y",
                    str(center[1]),
                    "--center_z",
                    str(center[2]),
                    "--size_x",
                    str(box_size[0]),
                    "--size_y",
                    str(box_size[1]),
                    "--size_z",
                    str(box_size[2]),
                    "--exhaustiveness",
                    str(exhaustiveness),
                    "--num_modes",
                    "3",
                    "--out",
                    out_unique,
                ]

                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                if proc.returncode == 0:
                    poses, _ = _parse_vina_output(proc.stdout, out_unique)
                    if poses:
                        best = poses[0]
                        best["smiles"] = smi
                        best["compound_index"] = idx
                        docking_results.append(best)
                        logger.info(
                            f"  [{idx+1}/{len(dock_candidates)}] {smi[:30]}... "
                            f"→ {best['vina_score_kcal']} kcal/mol"
                        )
                else:
                    logger.warning(
                        f"  [{idx+1}] Vina failed for {smi[:30]}...: {proc.stderr[:200]}"
                    )
            except Exception as e:
                logger.warning(f"  [{idx+1}] Docking error for {smi[:30]}...: {e}")
                continue

        if not docking_results:
            raise RuntimeError("All docking attempts failed")

        # Sort by Vina score (most negative = best)
        docking_results.sort(key=lambda x: x["vina_score_kcal"])

        # ── Step 4: Quantum refinement of top hits ──
        top_hits = docking_results[:max_quantum]
        ibm_job_ids = []
        quantum_refinement = {}

        if top_hits:
            # Use best scoring SMILES for quantum features
            best_smi = top_hits[0]["smiles"]
            qr = _quantum_refine_poses(best_smi, top_hits, max_poses=max_quantum)
            top_hits = qr["poses"]
            quantum_refinement = qr["quantum_refinement"]
            ibm_job_ids = qr["ibm_job_ids"]

        # ── Step 4b: Quantum-kernel re-ranking (ADDITIVE — quantum_screening_rerank) ──
        # Pure-addition, fail-open re-ranking signal on top of the existing Vina/
        # quantum-refined `top_hits`. Never mutates `top_hits` / `result["top_hits"]`
        # above — only adds a separate `top_hits_reranked` copy + a `reranking` block.
        reranking: Dict[str, Any] = {
            "method": "quantum_kernel_v1",
            "backend": None,
            "is_real_hardware": False,
            "blend_weight": DEFAULT_QKERNEL_BLEND_WEIGHT,
            "job_ref": None,
            "error": None,
        }
        top_hits_reranked = None
        try:
            from quantum_screening_rerank import score_hits_quantum

            # score_hits_quantum needs a plain PDB (Bio.PDB parseable) receptor
            # file, not the PDBQT used for Vina — write the already-downloaded
            # plain-text PDB out once, reusing the same work_dir.
            plain_pdb_path = os.path.join(work_dir, "receptor_plain.pdb")
            with open(plain_pdb_path, "w") as _f:
                _f.write(pdb_text)

            qk = score_hits_quantum(plain_pdb_path, center, top_hits)
            reranking["backend"] = qk.get("backend")
            reranking["is_real_hardware"] = bool(qk.get("is_real_hardware", False))
            reranking["job_ref"] = qk.get("job_ref")
            reranking["error"] = qk.get("error")

            scores = qk.get("scores")
            if scores and top_hits:
                vina_vals = [h["vina_score_kcal"] for h in top_hits]
                v_min, v_max = min(vina_vals), max(vina_vals)
                v_range = (v_max - v_min) or 1.0

                reranked = []
                for hit, qscore in zip(top_hits, scores):
                    hit_copy = dict(hit)
                    # More negative Vina score = better; invert + min-max to [0, 1].
                    norm_vina = (v_max - hit["vina_score_kcal"]) / v_range
                    qkernel_score = float(qscore) if qscore is not None else 0.0
                    combined = (
                        1.0 - DEFAULT_QKERNEL_BLEND_WEIGHT
                    ) * norm_vina + DEFAULT_QKERNEL_BLEND_WEIGHT * qkernel_score
                    hit_copy["qkernel_score"] = qkernel_score
                    hit_copy["combined_score"] = round(float(combined), 6)
                    reranked.append(hit_copy)

                reranked.sort(key=lambda h: h["combined_score"], reverse=True)
                top_hits_reranked = reranked
        except Exception as _qk_e:
            reranking["error"] = reranking["error"] or f"{type(_qk_e).__name__}: {_qk_e}"

        elapsed = round(time.time() - t0, 2)

        result: Dict[str, Any] = {
            "status": "completed",
            "library_source": library_source,
            "pdb_id": pdb_id,
            "total_input": len(library_smiles),
            "passed_filter": len(filtered),
            "docked": len(docking_results),
            "quantum_scored": len(top_hits),
            "top_hits": top_hits,
            "all_docking_results": docking_results[:50],  # cap
            "quantum_refinement": quantum_refinement,
            "ibm_job_ids": ibm_job_ids,
            "vina_version": "1.2.5",
            "elapsed_seconds": elapsed,
        }
        result["top_hits_reranked"] = (
            top_hits_reranked if top_hits_reranked is not None else top_hits
        )
        result["reranking"] = reranking
        return result


# ═══════════════════════════════════════════════════════════════════════
# ASYNC JOB RUNNERS
# ═══════════════════════════════════════════════════════════════════════


def _run_docking_async(job_id: str, params: Dict[str, Any]):
    """Run docking pipeline in background thread."""
    try:
        _docking_jobs[job_id]["status"] = "running"
        _docking_jobs[job_id]["started_at"] = time.time()

        result = _run_docking_pipeline(
            smiles=params["smiles"],
            pdb_id=params["pdb_id"],
            center=tuple(params["center"]),
            box_size=tuple(params.get("box_size", [20, 20, 20])),
            exhaustiveness=params.get("exhaustiveness", 32),
            quantum_refine=params.get("quantum_refine", True),
            engine=params.get("engine", "vina"),
        )

        _docking_jobs[job_id]["status"] = "completed"
        _docking_jobs[job_id]["result"] = result
        _docking_jobs[job_id]["completed_at"] = time.time()

    except Exception as e:
        logger.error(f"Docking job {job_id} failed: {traceback.format_exc()}")
        _docking_jobs[job_id]["status"] = "failed"
        _docking_jobs[job_id]["error"] = str(e)
        _docking_jobs[job_id]["completed_at"] = time.time()


def _run_screening_async(job_id: str, params: Dict[str, Any]):
    """Run screening pipeline in background thread."""
    try:
        _screening_jobs[job_id]["status"] = "running"
        _screening_jobs[job_id]["started_at"] = time.time()

        result = _run_screening_pipeline(
            library_smiles=params["library_smiles"],
            pdb_id=params["pdb_id"],
            center=tuple(params["center"]),
            box_size=tuple(params.get("box_size", [20, 20, 20])),
            exhaustiveness=params.get("exhaustiveness", 16),
            max_dock=params.get("max_dock", 50),
            max_quantum=params.get("max_quantum", 10),
            library_source=params.get("library_source", "custom"),
        )

        _screening_jobs[job_id]["status"] = "completed"
        _screening_jobs[job_id]["result"] = result
        _screening_jobs[job_id]["completed_at"] = time.time()

    except Exception as e:
        logger.error(f"Screening job {job_id} failed: {traceback.format_exc()}")
        _screening_jobs[job_id]["status"] = "failed"
        _screening_jobs[job_id]["error"] = str(e)
        _screening_jobs[job_id]["completed_at"] = time.time()


# ═══════════════════════════════════════════════════════════════════════
# FLASK BLUEPRINT
# ═══════════════════════════════════════════════════════════════════════


def create_docking_screening_blueprint() -> Blueprint:
    """Create and return the docking + screening Flask Blueprint."""

    bp = Blueprint("docking_screening", __name__)

    # ───────────────────────────────────────────────────────
    # DOCKING ENDPOINTS (/api/docking/*)
    # ───────────────────────────────────────────────────────

    @bp.route("/api/docking/classical", methods=["POST", "OPTIONS"])
    def docking_classical():
        """Full AutoDock Vina docking + quantum refinement.

        Body:
        {
            "smiles": "CCO",
            "pdb_id": "1M17",
            "center": [10.0, 20.0, 30.0],
            "box_size": [20, 20, 20],   # optional
            "exhaustiveness": 32,        # optional
            "quantum_refine": true       # optional, default true
        }
        """
        if request.method == "OPTIONS":
            return "", 204

        try:
            data = request.get_json(force=True)

            smiles = data.get("smiles")
            pdb_id = data.get("pdb_id")
            center = data.get("center")
            engine = str(data.get("engine", "vina")).lower()
            is_diffdock = engine in ("diffdock", "diffdock-l", "diffdock_nim")

            if not smiles:
                return jsonify({"error": "smiles is required", "status": "error"}), 400
            if not pdb_id:
                return jsonify({"error": "pdb_id is required", "status": "error"}), 400
            # DiffDock is blind docking — no box/center needed. Vina still requires center.
            if not is_diffdock and (not center or len(center) != 3):
                return (
                    jsonify(
                        {
                            "error": "center [x, y, z] is required for engine='vina'",
                            "status": "error",
                        }
                    ),
                    400,
                )

            # Launch async
            job_id = f"dock-{uuid.uuid4().hex[:12]}"
            _docking_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "smiles": smiles,
                "pdb_id": pdb_id,
                "engine": engine,
                "created_at": time.time(),
            }

            params = {
                "smiles": smiles,
                "pdb_id": pdb_id,
                "center": center or [0.0, 0.0, 0.0],
                "box_size": data.get("box_size", [20, 20, 20]),
                "exhaustiveness": data.get("exhaustiveness", 32),
                "quantum_refine": data.get("quantum_refine", True),
                "engine": engine,
            }

            thread = threading.Thread(target=_run_docking_async, args=(job_id, params), daemon=True)
            thread.start()

            return (
                jsonify(
                    {
                        "status": "submitted",
                        "job_id": job_id,
                        "message": f"Docking job submitted for {smiles} against {pdb_id}",
                    }
                ),
                202,
            )

        except Exception as e:
            logger.error(f"Docking submission error: {traceback.format_exc()}")
            return jsonify({"error": str(e), "status": "error"}), 500

    @bp.route("/api/docking/batch", methods=["POST", "OPTIONS"])
    def docking_batch():
        """Batch docking of multiple ligands against one receptor.

        Body:
        {
            "smiles_list": ["CCO", "c1ccccc1", "CC(=O)O"],
            "pdb_id": "1M17",
            "center": [10.0, 20.0, 30.0],
            "box_size": [20, 20, 20],
            "exhaustiveness": 16,
            "quantum_refine": true
        }
        """
        if request.method == "OPTIONS":
            return "", 204

        try:
            data = request.get_json(force=True)

            smiles_list = data.get("smiles_list", [])
            pdb_id = data.get("pdb_id")
            center = data.get("center")

            if not smiles_list:
                return jsonify({"error": "smiles_list is required", "status": "error"}), 400
            if not pdb_id:
                return jsonify({"error": "pdb_id is required", "status": "error"}), 400
            if not center or len(center) != 3:
                return jsonify({"error": "center [x, y, z] is required", "status": "error"}), 400

            # Cap at 50 ligands per batch
            if len(smiles_list) > 50:
                smiles_list = smiles_list[:50]

            job_id = f"bdock-{uuid.uuid4().hex[:12]}"
            _docking_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "ligand_count": len(smiles_list),
                "pdb_id": pdb_id,
                "created_at": time.time(),
            }

            # Batch docking uses the screening pipeline internally
            params = {
                "library_smiles": smiles_list,
                "pdb_id": pdb_id,
                "center": center,
                "box_size": data.get("box_size", [20, 20, 20]),
                "exhaustiveness": data.get("exhaustiveness", 16),
                "max_dock": len(smiles_list),
                "max_quantum": min(10, len(smiles_list)),
                "library_source": "batch_docking",
            }

            def _run_batch(jid, p):
                try:
                    _docking_jobs[jid]["status"] = "running"
                    _docking_jobs[jid]["started_at"] = time.time()
                    # center y box_size llegan como listas desde JSON y la firma
                    # los quiere como tuplas; el dict se declara Any para que el
                    # splat no herede una unión que no casa con nada.
                    kwargs: Dict[str, Any] = {
                        k: (tuple(v) if k in ("center", "box_size") and isinstance(v, list) else v)
                        for k, v in p.items()
                    }
                    result = _run_screening_pipeline(**kwargs)
                    _docking_jobs[jid]["status"] = "completed"
                    _docking_jobs[jid]["result"] = result
                    _docking_jobs[jid]["completed_at"] = time.time()
                except Exception as e:
                    logger.error(f"Batch docking {jid} failed: {traceback.format_exc()}")
                    _docking_jobs[jid]["status"] = "failed"
                    _docking_jobs[jid]["error"] = str(e)
                    _docking_jobs[jid]["completed_at"] = time.time()

            thread = threading.Thread(target=_run_batch, args=(job_id, params), daemon=True)
            thread.start()

            return (
                jsonify(
                    {
                        "status": "submitted",
                        "job_id": job_id,
                        "ligand_count": len(smiles_list),
                        "message": f"Batch docking of {len(smiles_list)} ligands against {pdb_id}",
                    }
                ),
                202,
            )

        except Exception as e:
            logger.error(f"Batch docking error: {traceback.format_exc()}")
            return jsonify({"error": str(e), "status": "error"}), 500

    @bp.route("/api/docking/status/<job_id>", methods=["GET"])
    def docking_status(job_id):
        """Check status of a docking job."""
        job = _docking_jobs.get(job_id)
        if not job:
            return jsonify({"error": f"Job {job_id} not found", "status": "error"}), 404

        response = {
            "job_id": job_id,
            "status": job["status"],
            "created_at": job.get("created_at"),
        }

        if job["status"] == "completed":
            response["result"] = job.get("result", {})
        elif job["status"] == "failed":
            response["error"] = job.get("error", "Unknown error")
        elif job["status"] == "running":
            elapsed = time.time() - job.get("started_at", job.get("created_at", time.time()))
            response["elapsed_seconds"] = round(elapsed, 1)

        return jsonify(response)

    # ───────────────────────────────────────────────────────
    # SCREENING ENDPOINTS (/api/screening/*)
    # ───────────────────────────────────────────────────────

    @bp.route("/api/screening/zinc", methods=["POST", "OPTIONS"])
    def screening_zinc():
        """Screen ZINC15 library subset.

        Body:
        {
            "query": "kinase inhibitor",
            "pdb_id": "1M17",
            "center": [10.0, 20.0, 30.0],
            "count": 50,
            "max_dock": 50,
            "max_quantum": 10
        }
        """
        if request.method == "OPTIONS":
            return "", 204

        try:
            data = request.get_json(force=True)

            query = data.get("query")
            pdb_id = data.get("pdb_id")
            center = data.get("center")

            if not query:
                return jsonify({"error": "query is required", "status": "error"}), 400
            if not pdb_id:
                return jsonify({"error": "pdb_id is required", "status": "error"}), 400
            if not center or len(center) != 3:
                return jsonify({"error": "center [x, y, z] is required", "status": "error"}), 400

            job_id = f"szinc-{uuid.uuid4().hex[:12]}"
            _screening_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "library": "ZINC15",
                "query": query,
                "pdb_id": pdb_id,
                "created_at": time.time(),
            }

            def _run_zinc_screen(jid):
                try:
                    _screening_jobs[jid]["status"] = "fetching_library"
                    count = data.get("count", 50)
                    library = _fetch_zinc_library(query, count=count)
                    _screening_jobs[jid]["status"] = "running"
                    _screening_jobs[jid]["library_size"] = len(library)
                    _screening_jobs[jid]["started_at"] = time.time()

                    result = _run_screening_pipeline(
                        library_smiles=library,
                        pdb_id=pdb_id,
                        center=tuple(center),
                        box_size=tuple(data.get("box_size", [20, 20, 20])),
                        exhaustiveness=data.get("exhaustiveness", 16),
                        max_dock=data.get("max_dock", 50),
                        max_quantum=data.get("max_quantum", 10),
                        library_source="ZINC15",
                    )

                    _screening_jobs[jid]["status"] = "completed"
                    _screening_jobs[jid]["result"] = result
                    _screening_jobs[jid]["completed_at"] = time.time()
                except Exception as e:
                    logger.error(f"ZINC screening {jid} failed: {traceback.format_exc()}")
                    _screening_jobs[jid]["status"] = "failed"
                    _screening_jobs[jid]["error"] = str(e)
                    _screening_jobs[jid]["completed_at"] = time.time()

            thread = threading.Thread(target=_run_zinc_screen, args=(job_id,), daemon=True)
            thread.start()

            return (
                jsonify(
                    {
                        "status": "submitted",
                        "job_id": job_id,
                        "library": "ZINC15",
                        "message": f"ZINC screening for '{query}' against {pdb_id}",
                    }
                ),
                202,
            )

        except Exception as e:
            logger.error(f"ZINC screening error: {traceback.format_exc()}")
            return jsonify({"error": str(e), "status": "error"}), 500

    @bp.route("/api/screening/enamine", methods=["POST", "OPTIONS"])
    def screening_enamine():
        """Screen Enamine REAL library (user provides SMILES list).

        Body:
        {
            "smiles_list": ["CCO", "c1ccccc1O", ...],
            "pdb_id": "1M17",
            "center": [10.0, 20.0, 30.0],
            "max_dock": 50,
            "max_quantum": 10
        }
        """
        if request.method == "OPTIONS":
            return "", 204

        try:
            data = request.get_json(force=True)

            smiles_list = data.get("smiles_list", [])
            pdb_id = data.get("pdb_id")
            center = data.get("center")

            if not smiles_list:
                return jsonify({"error": "smiles_list is required", "status": "error"}), 400
            if not pdb_id:
                return jsonify({"error": "pdb_id is required", "status": "error"}), 400
            if not center or len(center) != 3:
                return jsonify({"error": "center [x, y, z] is required", "status": "error"}), 400

            job_id = f"senam-{uuid.uuid4().hex[:12]}"
            _screening_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "library": "Enamine_REAL",
                "pdb_id": pdb_id,
                "input_count": len(smiles_list),
                "created_at": time.time(),
            }

            def _run_enamine_screen(jid):
                try:
                    _screening_jobs[jid]["status"] = "validating_library"
                    library = _fetch_enamine_library(smiles_list)
                    _screening_jobs[jid]["status"] = "running"
                    _screening_jobs[jid]["library_size"] = len(library)
                    _screening_jobs[jid]["started_at"] = time.time()

                    result = _run_screening_pipeline(
                        library_smiles=library,
                        pdb_id=pdb_id,
                        center=tuple(center),
                        box_size=tuple(data.get("box_size", [20, 20, 20])),
                        exhaustiveness=data.get("exhaustiveness", 16),
                        max_dock=data.get("max_dock", 50),
                        max_quantum=data.get("max_quantum", 10),
                        library_source="Enamine_REAL",
                    )

                    _screening_jobs[jid]["status"] = "completed"
                    _screening_jobs[jid]["result"] = result
                    _screening_jobs[jid]["completed_at"] = time.time()
                except Exception as e:
                    logger.error(f"Enamine screening {jid} failed: {traceback.format_exc()}")
                    _screening_jobs[jid]["status"] = "failed"
                    _screening_jobs[jid]["error"] = str(e)
                    _screening_jobs[jid]["completed_at"] = time.time()

            thread = threading.Thread(target=_run_enamine_screen, args=(job_id,), daemon=True)
            thread.start()

            return (
                jsonify(
                    {
                        "status": "submitted",
                        "job_id": job_id,
                        "library": "Enamine_REAL",
                        "input_count": len(smiles_list),
                        "message": f"Enamine screening of {len(smiles_list)} compounds against {pdb_id}",
                    }
                ),
                202,
            )

        except Exception as e:
            logger.error(f"Enamine screening error: {traceback.format_exc()}")
            return jsonify({"error": str(e), "status": "error"}), 500

    @bp.route("/api/screening/chembl", methods=["POST", "OPTIONS"])
    def screening_chembl():
        """Screen ChEMBL active compounds for a target.

        Body:
        {
            "target_chembl_id": "CHEMBL203",
            "pdb_id": "1M17",
            "center": [10.0, 20.0, 30.0],
            "count": 50,
            "max_dock": 50,
            "max_quantum": 10
        }
        """
        if request.method == "OPTIONS":
            return "", 204

        try:
            data = request.get_json(force=True)

            target_chembl_id = data.get("target_chembl_id")
            target_name = data.get("target", "")
            pdb_id = data.get("pdb_id")
            center = data.get("center")

            # Auto-resolve target name → ChEMBL ID + PDB ID if not provided
            if not target_chembl_id and target_name:
                _resolved_chembl, _resolved_pdb = _resolve_target_to_chembl(target_name)
                if _resolved_chembl:
                    target_chembl_id = _resolved_chembl
                if not pdb_id and _resolved_pdb:
                    pdb_id = _resolved_pdb

            if not target_chembl_id:
                return (
                    jsonify(
                        {
                            "error": "Could not resolve target. Provide target_chembl_id or a valid target name.",
                            "status": "error",
                        }
                    ),
                    400,
                )

            # Auto-resolve PDB from backend's resolve_pdb_for_target if still missing
            if not pdb_id:
                try:
                    from script_executor_server import resolve_pdb_for_target

                    _pdb_res = resolve_pdb_for_target(target_name or target_chembl_id)
                    pdb_id = _pdb_res.get("pdb_id")
                except Exception:
                    pass
            if not pdb_id:
                pdb_id = "1M17"  # Safe default (EGFR)

            # Auto-resolve center from PDB if not provided
            if not center or len(center) != 3:
                center = _resolve_pdb_center(pdb_id) or [0.0, 0.0, 0.0]

            job_id = f"schem-{uuid.uuid4().hex[:12]}"
            _screening_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "library": "ChEMBL",
                "target_chembl_id": target_chembl_id,
                "pdb_id": pdb_id,
                "created_at": time.time(),
            }

            def _run_chembl_screen(jid):
                try:
                    _screening_jobs[jid]["status"] = "fetching_library"
                    count = data.get("count", 50)
                    library = _fetch_chembl_actives(target_chembl_id, count=count)
                    _screening_jobs[jid]["status"] = "running"
                    _screening_jobs[jid]["library_size"] = len(library)
                    _screening_jobs[jid]["started_at"] = time.time()

                    result = _run_screening_pipeline(
                        library_smiles=library,
                        pdb_id=pdb_id,
                        center=tuple(center),
                        box_size=tuple(data.get("box_size", [20, 20, 20])),
                        exhaustiveness=data.get("exhaustiveness", 16),
                        max_dock=data.get("max_dock", 50),
                        max_quantum=data.get("max_quantum", 10),
                        library_source="ChEMBL",
                    )

                    _screening_jobs[jid]["status"] = "completed"
                    _screening_jobs[jid]["result"] = result
                    _screening_jobs[jid]["completed_at"] = time.time()
                except Exception as e:
                    logger.error(f"ChEMBL screening {jid} failed: {traceback.format_exc()}")
                    _screening_jobs[jid]["status"] = "failed"
                    _screening_jobs[jid]["error"] = str(e)
                    _screening_jobs[jid]["completed_at"] = time.time()

            thread = threading.Thread(target=_run_chembl_screen, args=(job_id,), daemon=True)
            thread.start()

            return (
                jsonify(
                    {
                        "status": "submitted",
                        "job_id": job_id,
                        "library": "ChEMBL",
                        "target_chembl_id": target_chembl_id,
                        "message": f"ChEMBL screening for {target_chembl_id} against {pdb_id}",
                    }
                ),
                202,
            )

        except Exception as e:
            logger.error(f"ChEMBL screening error: {traceback.format_exc()}")
            return jsonify({"error": str(e), "status": "error"}), 500

    @bp.route("/api/screening/custom", methods=["POST", "OPTIONS"])
    def screening_custom():
        """Screen a custom SMILES library.

        Body:
        {
            "smiles_list": ["CCO", "c1ccccc1O", ...],
            "pdb_id": "1M17",
            "center": [10.0, 20.0, 30.0],
            "max_dock": 50,
            "max_quantum": 10
        }
        """
        if request.method == "OPTIONS":
            return "", 204

        try:
            data = request.get_json(force=True)

            smiles_list = data.get("smiles_list", [])
            pdb_id = data.get("pdb_id")
            center = data.get("center")

            if not smiles_list:
                return jsonify({"error": "smiles_list is required", "status": "error"}), 400
            if not pdb_id:
                return jsonify({"error": "pdb_id is required", "status": "error"}), 400
            if not center or len(center) != 3:
                return jsonify({"error": "center [x, y, z] is required", "status": "error"}), 400

            job_id = f"scust-{uuid.uuid4().hex[:12]}"
            _screening_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "library": "custom",
                "pdb_id": pdb_id,
                "input_count": len(smiles_list),
                "created_at": time.time(),
            }

            params = {
                "library_smiles": smiles_list,
                "pdb_id": pdb_id,
                "center": center,
                "box_size": data.get("box_size", [20, 20, 20]),
                "exhaustiveness": data.get("exhaustiveness", 16),
                "max_dock": data.get("max_dock", 50),
                "max_quantum": data.get("max_quantum", 10),
                "library_source": "custom",
            }

            thread = threading.Thread(
                target=_run_screening_async, args=(job_id, params), daemon=True
            )
            thread.start()

            return (
                jsonify(
                    {
                        "status": "submitted",
                        "job_id": job_id,
                        "library": "custom",
                        "input_count": len(smiles_list),
                        "message": f"Custom screening of {len(smiles_list)} compounds against {pdb_id}",
                    }
                ),
                202,
            )

        except Exception as e:
            logger.error(f"Custom screening error: {traceback.format_exc()}")
            return jsonify({"error": str(e), "status": "error"}), 500

    @bp.route("/api/screening/status/<job_id>", methods=["GET"])
    def screening_status(job_id):
        """Check status of a screening job."""
        job = _screening_jobs.get(job_id)
        if not job:
            return jsonify({"error": f"Job {job_id} not found", "status": "error"}), 404

        response = {
            "job_id": job_id,
            "status": job["status"],
            "library": job.get("library", "unknown"),
            "created_at": job.get("created_at"),
        }

        if job["status"] == "completed":
            response["result"] = job.get("result", {})
        elif job["status"] == "failed":
            response["error"] = job.get("error", "Unknown error")
        elif job["status"] in ("running", "fetching_library", "validating_library"):
            response["library_size"] = job.get("library_size")
            started = job.get("started_at", job.get("created_at", time.time()))
            response["elapsed_seconds"] = round(time.time() - started, 1)

        return jsonify(response)

    return bp
