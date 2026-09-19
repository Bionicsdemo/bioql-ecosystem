# Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
#
# PBPKModeler v1.0 -- Physiologically-Based Pharmacokinetic Modeling
# with quantum-enhanced parameter estimation on IBM Boston 156-qubit hardware.
#
# Modules:
#   1) QKP     - Quantum Kp Predictor (VQE tissue:plasma partition coefficients)
#   2) QODE    - Quantum ODE Solver (HHL-inspired linear system for compartment ODEs)
#   3) QAOA-PK - QAOA PK Optimizer (dosing regimen optimization)
#
# 14-compartment PBPK model with allometric scaling, CYP enzyme kinetics,
# renal clearance, and 5 administration routes (IV bolus, IV infusion, oral, IM, SC).
#
# All quantum operations: IBM Boston 156Q first, classical fallback on failure.
# Every IBM job ID is logged to /opt/bioql/pipeline_audit_log.json.

from __future__ import annotations

import json
import logging
import math
import os
import time
import datetime
import hashlib
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("bioql.pbpk")

# ---------------------------------------------------------------------------
# Graceful imports -- core scientific stack
# ---------------------------------------------------------------------------
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    logger.warning("RDKit not available -- molecular descriptor computation will fail")

try:
    from scipy.integrate import solve_ivp
    from scipy.optimize import minimize
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("SciPy not available -- ODE integration will use Euler fallback")

# ---------------------------------------------------------------------------
# Graceful imports -- Qiskit ecosystem
# ---------------------------------------------------------------------------
try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import EfficientSU2, RealAmplitudes
    from qiskit.quantum_info import SparsePauliOp
    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False
    logger.warning("Qiskit not available -- quantum modules disabled")

try:
    from qiskit_ibm_runtime import (
        QiskitRuntimeService,
        SamplerV2,
        Session,
    )
    HAS_IBM_RUNTIME = True
except ImportError:
    HAS_IBM_RUNTIME = False
    logger.warning("qiskit-ibm-runtime not available -- IBM execution disabled")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IBM_BACKEND = "ibm_fez"
IBM_TOKEN = os.environ.get("IBM_QUANTUM_TOKEN", "")
IBM_CHANNEL = "ibm_quantum_platform"
IBM_INSTANCE = "crn:v1:bluemix:public:quantum-computing:us-east:a/044022560bc74e63818a301769091331:890abbbb-27b5-4400-9779-7c45f120b7ec::"
AUDIT_LOG_PATH = "/opt/bioql/pipeline_audit_log.json"
DEFAULT_SHOTS = 4096

N_QUBITS_QKP = 8       # Quantum Kp Predictor
N_QUBITS_QODE = 10     # Quantum ODE Solver
N_QUBITS_QAOA_PK = 6   # QAOA PK Optimizer
QAOA_PK_DEPTH = 2       # QAOA circuit depth (p=2)

REFERENCE_WEIGHT_KG = 70.0
CARDIAC_OUTPUT_L_H = 390.0   # ~6.5 L/min for 70 kg human (ICRP)

# ---------------------------------------------------------------------------
# 14-Compartment PBPK tissue parameters (70 kg reference human, ICRP Pub 89)
# volume in L, blood_flow in L/h (fraction of cardiac output), perfusion_rate
# ---------------------------------------------------------------------------
TISSUE_PARAMS: Dict[str, Dict[str, float]] = {
    "arterial_blood":  {"volume": 1.50, "blood_flow_frac": 1.00, "kp_default": 1.00, "permeability": 1.0},
    "venous_blood":    {"volume": 3.50, "blood_flow_frac": 1.00, "kp_default": 1.00, "permeability": 1.0},
    "lung":            {"volume": 0.50, "blood_flow_frac": 1.00, "kp_default": 0.80, "permeability": 0.85},
    "heart":           {"volume": 0.33, "blood_flow_frac": 0.04, "kp_default": 1.20, "permeability": 0.90},
    "brain":           {"volume": 1.40, "blood_flow_frac": 0.12, "kp_default": 0.30, "permeability": 0.05},
    "liver":           {"volume": 1.80, "blood_flow_frac": 0.065, "kp_default": 3.50, "permeability": 0.95},
    "kidney":          {"volume": 0.31, "blood_flow_frac": 0.19, "kp_default": 2.80, "permeability": 0.92},
    "gut":             {"volume": 1.10, "blood_flow_frac": 0.185, "kp_default": 2.00, "permeability": 0.70},
    "spleen":          {"volume": 0.18, "blood_flow_frac": 0.03, "kp_default": 1.50, "permeability": 0.88},
    "muscle":          {"volume": 28.0, "blood_flow_frac": 0.17, "kp_default": 0.60, "permeability": 0.65},
    "skin":            {"volume": 3.30, "blood_flow_frac": 0.05, "kp_default": 1.10, "permeability": 0.40},
    "adipose":         {"volume": 10.0, "blood_flow_frac": 0.05, "kp_default": 5.00, "permeability": 0.35},
    "bone":            {"volume": 4.00, "blood_flow_frac": 0.05, "kp_default": 0.40, "permeability": 0.20},
    "rest_of_body":    {"volume": 5.58, "blood_flow_frac": 0.035, "kp_default": 1.00, "permeability": 0.60},
}

TISSUE_NAMES = list(TISSUE_PARAMS.keys())

# Administration routes
ROUTES = ["iv_bolus", "iv_infusion", "oral", "im", "sc"]

# CYP enzyme Michaelis-Menten defaults (Vmax in mg/h, Km in mg/L)
CYP_DEFAULTS: Dict[str, Dict[str, float]] = {
    "CYP3A4":  {"vmax": 50.0, "km": 5.0,  "fraction": 0.50},
    "CYP2D6":  {"vmax": 20.0, "km": 3.0,  "fraction": 0.25},
    "CYP2C9":  {"vmax": 15.0, "km": 4.0,  "fraction": 0.15},
    "CYP2C19": {"vmax": 10.0, "km": 6.0,  "fraction": 0.05},
    "CYP1A2":  {"vmax": 8.0,  "km": 7.0,  "fraction": 0.05},
}

# Renal parameters
GFR_ML_MIN = 120.0          # Glomerular filtration rate (mL/min)
TUBULAR_REABSORPTION = 0.5  # fraction reabsorbed


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------
def _audit_log(entry: Dict[str, Any]) -> None:
    """Append entry to pipeline audit log."""
    entry["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    entry["module"] = "PBPKModeler"
    try:
        path = Path(AUDIT_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        logger.debug("Could not write audit log: %s", traceback.format_exc())


# ---------------------------------------------------------------------------
# Molecular descriptor extraction
# ---------------------------------------------------------------------------
def _compute_descriptors(smiles: str) -> Dict[str, float]:
    """Extract molecular descriptors relevant to PBPK from SMILES.

    Returns dict with: MW, LogP, pKa_est, HBA, HBD, TPSA, RotBonds,
    fu_est (fraction unbound estimate), LogD, MR.
    """
    if not HAS_RDKIT:
        raise RuntimeError("RDKit required for descriptor computation")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hba = Descriptors.NumHAcceptors(mol)
    hbd = Descriptors.NumHDonors(mol)
    tpsa = Descriptors.TPSA(mol)
    rotbonds = Descriptors.NumRotatableBonds(mol)
    mr = Descriptors.MolMR(mol)

    # pKa estimation from strongest acidic/basic via empirical formula
    pka_est = 7.4 + 0.5 * (hba - hbd) - 0.1 * logp
    pka_est = max(1.0, min(14.0, pka_est))

    # Fraction unbound estimate (fu) -- empirical from LogP
    # Lombardo et al. (2002) approximation
    fu_est = 1.0 / (1.0 + 10.0 ** (0.4 * logp - 1.0))
    fu_est = max(0.001, min(1.0, fu_est))

    # LogD at pH 7.4 approximation
    logd = logp - max(0, logp - pka_est) * 0.5

    return {
        "MW": mw,
        "LogP": logp,
        "pKa_est": pka_est,
        "HBA": float(hba),
        "HBD": float(hbd),
        "TPSA": tpsa,
        "RotBonds": float(rotbonds),
        "fu_est": fu_est,
        "LogD": logd,
        "MR": mr,
    }


# ---------------------------------------------------------------------------
# IBM Quantum helper
# ---------------------------------------------------------------------------
CLASSICAL_ONLY_ENV = "BIOQL_PBPK_CLASSICAL"


def classical_only() -> bool:
    """Skip the quantum attempt and take the classical path immediately.

    Every stage of this model is quantum-first with a classical fallback -- Kp
    prediction, the ODE rate correction and the dosing optimisation. The
    fallback only fires once the external attempt has FAILED, so a caller that
    does not want quantum still waits for a provider round-trip at each stage:
    OpenQuantum (currently returning insufficient credits) and then, until it
    was made opt-in, a dead IBM handshake. Measured 2026-09-17: a single dose
    derivation sat for more than five minutes before producing anything.

    For a dose that is a deterministic pharmacokinetic calculation, that is
    cost without demonstrated benefit. This switch makes the classical path
    immediate. It changes no default: quantum stays first unless asked.
    """
    return os.environ.get(CLASSICAL_ONLY_ENV) == "1"


def _get_ibm_service() -> Any:
    """Create IBM Quantum Runtime service."""
    if classical_only():
        raise RuntimeError(
            "%s=1 — classical path requested; no external provider was contacted."
            % CLASSICAL_ONLY_ENV)
    # The platform moved off IBM. This module still reaches for it by name
    # (IBM_BACKEND = "ibm_fez"), and the token no longer resolves: measured
    # 2026-09-17, 'Unable to retrieve instances. Please check that you are using
    # a valid API token.' at every stage. Opening that connection costs seconds
    # per stage and returns nothing, so it is opt-in like everywhere else.
    if os.environ.get("BIOQL_ENABLE_IBM", "0").lower() not in {"1", "true", "on"}:
        raise RuntimeError(
            "IBM is not enabled (set BIOQL_ENABLE_IBM=1 to re-enable); "
            "using the classical path.")
    if not HAS_IBM_RUNTIME:
        raise RuntimeError("qiskit-ibm-runtime not installed")
    return QiskitRuntimeService(
        channel=IBM_CHANNEL,
        token=IBM_TOKEN,
    )


def _run_sampler(circuits: List[Any], shots: int = DEFAULT_SHOTS) -> Tuple[List[Dict[str, int]], List[str]]:
    """Execute circuits QPU-first, with simulator fallback.

    Returns (counts_list, job_ids).
    """
    # The classical switch has to be honoured HERE too, not only in
    # _get_ibm_service: this path goes through quantum_fallback_runners, which
    # tries several providers in turn. Guarding only the IBM accessor left a
    # dose derivation hanging for minutes on the other providers.
    if classical_only():
        raise RuntimeError(
            "%s=1 — classical path requested; no sampler was run."
            % CLASSICAL_ONLY_ENV)
    try:
        from quantum_fallback_runners import run_sampling_with_fallback

        n_qubits = max(
            (getattr(circuit, "num_qubits", 0) for circuit in circuits),
            default=0,
        )
        result, provenance = run_sampling_with_fallback(
            list(circuits),
            n_qubits=n_qubits,
            kind="sampling",
            est_qpu_seconds=max(2.0, 0.1 * len(circuits) * n_qubits),
            shots=int(shots),
        )
        if result is None:
            raise RuntimeError(
                f"all QPU/simulator backends failed: {provenance}"
            )
        job_ids = (
            result.get("openquantum_job_ids")
            or ([result.get("openquantum_job_id")]
                if result.get("openquantum_job_id") else [])
            or ([provenance.get("ibm_job_id")]
                if provenance.get("ibm_job_id") else [])
        )
        _audit_log(
            {
                "action": "qpu_first_sampler_run",
                "job_ids": job_ids,
                "n_circuits": len(circuits),
                "shots": shots,
                "backend": provenance.get("substrate"),
                "is_real_hardware": provenance.get("is_real_hardware"),
            }
        )
        return result.get("counts_list") or [], [
            str(job_id) for job_id in job_ids if job_id
        ]
    except Exception as qpu_error:
        logger.warning(
            "Shared QPU-first sampler failed (%s); trying legacy IBM",
            qpu_error,
        )

    service = _get_ibm_service()
    backend = service.backend(IBM_BACKEND)

    with Session(backend=backend) as session:
        sampler = SamplerV2(mode=session)
        job = sampler.run(circuits, shots=shots)
        job_id = job.job_id()
        logger.info("IBM job submitted: %s (%d circuits, %d shots)", job_id, len(circuits), shots)

        result = job.result()
        counts_list = []
        for i in range(len(circuits)):
            pub_result = result[i]
            bitstrings = pub_result.data.meas.get_counts()
            counts_list.append(bitstrings)

        _audit_log({
            "action": "ibm_sampler_run",
            "job_id": job_id,
            "n_circuits": len(circuits),
            "shots": shots,
            "backend": IBM_BACKEND,
        })

        return counts_list, [job_id]


# ===========================================================================
# MODULE 1: Quantum Kp Predictor (QKP)
# ===========================================================================
class QuantumKpPredictor:
    """VQE-based tissue:plasma partition coefficient prediction.

    Encodes molecular descriptors (LogP, pKa, fu, MW, TPSA, MR, HBD, HBA)
    into an 8-qubit variational circuit. The expectation of the measurement
    distribution maps to Kp for each tissue via tissue-specific cost encoding.
    """

    def __init__(self, n_qubits: int = N_QUBITS_QKP, shots: int = DEFAULT_SHOTS):
        self.n_qubits = n_qubits
        self.shots = shots

        # Tissue-specific scaling factors for Kp (lipophilicity, perfusion, binding)
        # These encode prior knowledge about tissue composition
        self._tissue_weight_map: Dict[str, np.ndarray] = {}
        for name, params in TISSUE_PARAMS.items():
            kp_def = params["kp_default"]
            perm = params["permeability"]
            bf = params["blood_flow_frac"]
            # 8 weights coupling molecular features to tissue properties
            w = np.array([
                0.3 * kp_def,       # LogP coupling
                0.1 * perm,         # pKa coupling
                0.2 * (1 - perm),   # fu coupling
                0.05 * bf,          # MW coupling
                0.1 * perm,         # TPSA coupling
                0.08 * kp_def,      # MR coupling
                0.07 * (1 - bf),    # HBD coupling
                0.10 * perm,        # HBA coupling
            ])
            self._tissue_weight_map[name] = w / (np.sum(w) + 1e-12)

    def _normalize_features(self, desc: Dict[str, float]) -> np.ndarray:
        """Normalize 8 molecular descriptors to [0, pi] for qubit encoding."""
        raw = np.array([
            desc["LogP"],
            desc["pKa_est"],
            desc["fu_est"],
            desc["MW"],
            desc["TPSA"],
            desc["MR"],
            desc["HBD"],
            desc["HBA"],
        ])
        # Min-max scale to [0, pi]
        mins = np.array([-3.0, 1.0, 0.001, 100.0, 0.0, 10.0, 0.0, 0.0])
        maxs = np.array([8.0, 14.0, 1.0, 900.0, 250.0, 200.0, 15.0, 15.0])
        scaled = (np.clip(raw, mins, maxs) - mins) / (maxs - mins + 1e-12)
        return scaled * np.pi

    def _build_vqe_circuit(self, features: np.ndarray, tissue_weights: np.ndarray) -> QuantumCircuit:
        """Build VQE ansatz for Kp prediction.

        Architecture:
          1. Feature encoding: Ry(feature_i) on qubit i
          2. Entanglement: CX ring
          3. Variational layer 1: Ry(tissue_weight * feature) + Rz(tissue_weight)
          4. CX ladder
          5. Variational layer 2: Ry(combined) + Rz(combined)
          6. CX ring
          7. Measure all
        """
        if not HAS_QISKIT:
            raise RuntimeError("Qiskit required for circuit construction")

        n = self.n_qubits
        qc = QuantumCircuit(n, n)

        # Layer 1: Feature encoding
        for i in range(n):
            qc.ry(float(features[i]), i)

        # Entanglement ring
        for i in range(n - 1):
            qc.cx(i, i + 1)
        qc.cx(n - 1, 0)

        qc.barrier()

        # Variational layer 1: tissue-aware rotation
        for i in range(n):
            angle_y = float(tissue_weights[i] * features[i] * 2.0)
            angle_z = float(tissue_weights[i] * np.pi)
            qc.ry(angle_y, i)
            qc.rz(angle_z, i)

        # CX ladder
        for i in range(0, n - 1, 2):
            qc.cx(i, i + 1)
        for i in range(1, n - 1, 2):
            qc.cx(i, i + 1)

        qc.barrier()

        # Variational layer 2: cross-feature coupling
        for i in range(n):
            combined = float((features[i] + features[(i + 1) % n]) * tissue_weights[i])
            qc.ry(combined, i)
            qc.rz(float(tissue_weights[(i + 1) % n] * np.pi * 0.5), i)

        # Final entanglement ring
        for i in range(n - 1):
            qc.cx(i, i + 1)
        qc.cx(n - 1, 0)

        # Measure
        qc.measure(range(n), range(n))

        return qc

    def _counts_to_kp(self, counts: Dict[str, int], kp_default: float) -> float:
        """Convert measurement counts to Kp value.

        Weighted bitstring interpretation: higher-order bits encode
        the Kp magnitude, ground state |00...0> maps to Kp near default.
        """
        total = sum(counts.values())
        if total == 0:
            return kp_default

        # Compute weighted average of bitstring integer values
        weighted_sum = 0.0
        for bitstring, count in counts.items():
            val = int(bitstring, 2) if isinstance(bitstring, str) else bitstring
            weighted_sum += val * count

        mean_val = weighted_sum / total
        max_val = 2 ** self.n_qubits - 1

        # Map to Kp range: [kp_default * 0.1, kp_default * 5.0]
        normalized = mean_val / max_val
        kp = kp_default * (0.1 + 4.9 * normalized)
        return round(kp, 4)

    def predict_kp_quantum(self, smiles: str) -> Dict[str, float]:
        """Predict Kp for all 14 tissues using IBM Boston 156Q.

        Returns dict mapping tissue name -> Kp value.
        """
        desc = _compute_descriptors(smiles)
        features = self._normalize_features(desc)

        # Build one circuit per tissue
        circuits = []
        for tissue_name in TISSUE_NAMES:
            tw = self._tissue_weight_map[tissue_name]
            qc = self._build_vqe_circuit(features, tw)
            circuits.append(qc)

        # Execute all 14 circuits in one IBM job
        counts_list, job_ids = _run_sampler(circuits, shots=self.shots)

        kp_values = {}
        for i, tissue_name in enumerate(TISSUE_NAMES):
            kp_def = TISSUE_PARAMS[tissue_name]["kp_default"]
            kp_values[tissue_name] = self._counts_to_kp(counts_list[i], kp_def)

        _audit_log({
            "action": "qkp_predict",
            "smiles": smiles,
            "job_ids": job_ids,
            "n_tissues": len(kp_values),
        })

        return kp_values

    def predict_kp_classical(self, smiles: str) -> Dict[str, float]:
        """Classical fallback: Rodgers-Rowland method for Kp estimation.

        Uses LogP, fu, and pKa to estimate Kp via empirical tissue composition.
        """
        desc = _compute_descriptors(smiles)
        logp = desc["LogP"]
        fu = desc["fu_est"]
        pka = desc["pKa_est"]

        kp_values = {}
        for tissue_name, params in TISSUE_PARAMS.items():
            kp_def = params["kp_default"]
            perm = params["permeability"]

            # Rodgers-Rowland inspired: Kp = (fu * Kp_uu) where
            # Kp_uu depends on lipophilicity and tissue composition
            lipophilicity_factor = 10.0 ** (0.3 * logp) / (1.0 + 10.0 ** (0.3 * logp))
            ionization_factor = 1.0 / (1.0 + 10.0 ** (pka - 7.4)) if logp > 0 else 1.0

            kp_uu = kp_def * lipophilicity_factor * ionization_factor * perm
            kp = fu * kp_uu + (1.0 - fu) * kp_def * 0.5
            kp = max(0.01, min(50.0, kp))
            kp_values[tissue_name] = round(kp, 4)

        return kp_values

    def predict(self, smiles: str) -> Dict[str, float]:
        """Quantum-first Kp prediction with classical fallback."""
        try:
            return self.predict_kp_quantum(smiles)
        except Exception as exc:
            logger.warning("QKP quantum failed (%s), falling back to classical", exc)
            return self.predict_kp_classical(smiles)


# ===========================================================================
# MODULE 2: Quantum ODE Solver (QODE)
# ===========================================================================
class QuantumODESolver:
    """Quantum-enhanced ODE solver for the 14-compartment PBPK system.

    Uses an HHL-inspired quantum linear system approach: the compartment
    coupling matrix is encoded into a quantum circuit, and the stationary
    distribution is extracted from measurement probabilities.

    For the time-stepping ODE integration, uses quantum-predicted rate
    constants combined with classical Runge-Kutta (solve_ivp) since full
    quantum time evolution is impractical on NISQ hardware.
    """

    def __init__(self, n_qubits: int = N_QUBITS_QODE, shots: int = DEFAULT_SHOTS):
        self.n_qubits = n_qubits
        self.shots = shots

    def _build_coupling_matrix(
        self,
        kp_values: Dict[str, float],
        weight_kg: float,
    ) -> np.ndarray:
        """Build the 14x14 compartment coupling matrix A for dC/dt = A*C + b.

        Rows/columns follow TISSUE_NAMES order. Matrix encodes:
          - Blood flow rates (allometrically scaled)
          - Partition coefficients (Kp)
          - Permeability limitations
        """
        n = len(TISSUE_NAMES)
        A = np.zeros((n, n), dtype=np.float64)

        scale_factor = (weight_kg / REFERENCE_WEIGHT_KG) ** 0.75
        CO = CARDIAC_OUTPUT_L_H * scale_factor

        vol_scale = weight_kg / REFERENCE_WEIGHT_KG

        for i, tissue_i in enumerate(TISSUE_NAMES):
            params_i = TISSUE_PARAMS[tissue_i]
            Vi = params_i["volume"] * vol_scale
            Qi = params_i["blood_flow_frac"] * CO
            Kpi = kp_values.get(tissue_i, params_i["kp_default"])
            pi = params_i["permeability"]

            # Self-clearance rate (outflow from compartment)
            if Vi > 0:
                A[i, i] = -(Qi * pi) / (Vi * Kpi + 1e-12)

            # Coupling to arterial blood (index 0) and venous blood (index 1)
            idx_art = 0   # arterial_blood
            idx_ven = 1   # venous_blood

            if tissue_i == "arterial_blood":
                # Arterial receives from lung, distributes to all organs
                idx_lung = TISSUE_NAMES.index("lung")
                params_lung = TISSUE_PARAMS["lung"]
                V_art = Vi
                if V_art > 0:
                    A[i, idx_lung] = (CO * params_lung["permeability"]) / V_art
                    # Outflow to all tissues
                    A[i, i] = -CO / V_art

            elif tissue_i == "venous_blood":
                # Venous receives from all tissues except lung, flows to lung
                V_ven = Vi
                for j, tissue_j in enumerate(TISSUE_NAMES):
                    if tissue_j in ("arterial_blood", "venous_blood", "lung"):
                        continue
                    Qj = TISSUE_PARAMS[tissue_j]["blood_flow_frac"] * CO
                    Kpj = kp_values.get(tissue_j, TISSUE_PARAMS[tissue_j]["kp_default"])
                    pj = TISSUE_PARAMS[tissue_j]["permeability"]
                    if V_ven > 0 and Kpj > 0:
                        A[i, j] = (Qj * pj) / (V_ven * Kpj)
                # Outflow to lung
                if V_ven > 0:
                    A[i, i] = -CO / V_ven

            elif tissue_i == "lung":
                # Lung receives from venous, distributes to arterial
                V_lung = Vi
                Kp_lung = Kpi
                if V_lung > 0:
                    A[i, idx_ven] = CO / V_lung
                    A[i, i] = -(CO * pi) / (V_lung * Kp_lung)

            else:
                # Peripheral tissue: receives from arterial, drains to venous
                if Vi > 0:
                    A[i, idx_art] = (Qi * pi) / Vi
                    A[i, i] = -(Qi * pi) / (Vi * Kpi + 1e-12)

        return A

    def _build_hhl_circuit(self, matrix_eigenvalues: np.ndarray) -> QuantumCircuit:
        """Build HHL-inspired circuit encoding the coupling matrix eigenstructure.

        This is a NISQ approximation: we encode the top eigenvalues as rotation
        angles and use the measurement distribution to estimate the steady-state
        concentration ratios.
        """
        if not HAS_QISKIT:
            raise RuntimeError("Qiskit required for QODE circuit")

        n = self.n_qubits
        qc = QuantumCircuit(n, n)

        # Normalize eigenvalues to [0, pi]
        eig_abs = np.abs(matrix_eigenvalues)
        eig_max = np.max(eig_abs) + 1e-12
        eig_norm = (eig_abs[:n] / eig_max) * np.pi if len(eig_abs) >= n else \
                   np.pad((eig_abs / eig_max) * np.pi, (0, n - len(eig_abs)))

        # Phase 1: Eigenvalue encoding via Ry rotations
        for i in range(n):
            qc.ry(float(eig_norm[i]), i)

        # Phase 2: Controlled rotations (HHL-inspired inversion encoding)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        qc.cx(n - 1, 0)

        qc.barrier()

        # Phase 3: Conditional rotation based on eigenvalue magnitudes
        # Encodes 1/lambda_i (reciprocal) as controlled-Ry
        for i in range(n):
            inv_angle = float(np.pi * (1.0 - eig_norm[i] / np.pi))
            if i + 1 < n:
                qc.cry(inv_angle, i, (i + 1) % n)
            qc.rz(float(eig_norm[i] * 0.5), i)

        # Phase 4: Entanglement layer
        for i in range(0, n - 1, 2):
            qc.cx(i, i + 1)
        for i in range(1, n - 1, 2):
            qc.cx(i, i + 1)

        qc.barrier()

        # Phase 5: Second variational layer
        for i in range(n):
            qc.ry(float(eig_norm[i] * 0.3), i)
            qc.rz(float(eig_norm[(n - 1 - i) % n] * 0.7), i)

        # Final ring
        for i in range(n - 1):
            qc.cx(i, i + 1)
        qc.cx(n - 1, 0)

        qc.measure(range(n), range(n))
        return qc

    def _quantum_rate_correction(
        self,
        A: np.ndarray,
    ) -> np.ndarray:
        """Use quantum circuit to correct the coupling matrix rate constants.

        Submits to IBM Boston, extracts steady-state correction factors.
        """
        eigenvalues = np.linalg.eigvals(A).real
        qc = self._build_hhl_circuit(eigenvalues)

        counts_list, job_ids = _run_sampler([qc], shots=self.shots)
        counts = counts_list[0]

        _audit_log({
            "action": "qode_rate_correction",
            "job_ids": job_ids,
            "n_eigenvalues": len(eigenvalues),
        })

        # Extract correction factors from measurement distribution
        total = sum(counts.values())
        n = min(self.n_qubits, A.shape[0])
        corrections = np.ones(A.shape[0])

        for bitstring, count in counts.items():
            bits = bitstring if isinstance(bitstring, str) else format(bitstring, f'0{self.n_qubits}b')
            for i in range(min(len(bits), n)):
                if bits[-(i + 1)] == '1':
                    corrections[i] += count / total * 0.2  # 20% max correction

        # Apply corrections to diagonal (rate constants)
        A_corrected = A.copy()
        for i in range(min(n, A.shape[0])):
            A_corrected[i, i] *= corrections[i]

        return A_corrected

    def solve_pbpk_ode(
        self,
        A: np.ndarray,
        dose_mg: float,
        route: str,
        weight_kg: float,
        duration_h: float = 24.0,
        dt: float = 0.1,
        clearance_params: Optional[Dict] = None,
        absorption_ka: float = 1.0,
        bioavailability: float = 0.7,
        infusion_duration_h: float = 1.0,
    ) -> Dict[str, Any]:
        """Solve the PBPK ODE system.

        Returns concentration-time curves for all 14 compartments.
        """
        n = len(TISSUE_NAMES)
        vol_scale = weight_kg / REFERENCE_WEIGHT_KG

        # Volumes (scaled)
        volumes = np.array([
            TISSUE_PARAMS[t]["volume"] * vol_scale for t in TISSUE_NAMES
        ])

        # Initial conditions: all zeros
        C0 = np.zeros(n + 1)  # +1 for gut absorption compartment (oral/IM/SC)

        # Clearance parameters
        cl = clearance_params or {}
        hepatic_cl = cl.get("hepatic_cl", 15.0)  # L/h
        renal_cl_rate = cl.get("renal_cl", GFR_ML_MIN * 60 / 1000 * (1 - TUBULAR_REABSORPTION))

        idx_liver = TISSUE_NAMES.index("liver")
        idx_kidney = TISSUE_NAMES.index("kidney")
        idx_gut = TISSUE_NAMES.index("gut")
        idx_art = TISSUE_NAMES.index("arterial_blood")
        idx_ven = TISSUE_NAMES.index("venous_blood")

        def _ode_rhs(t: float, y: np.ndarray) -> np.ndarray:
            """Right-hand side of the PBPK ODE system."""
            C = y[:n]
            A_gut = y[n]  # Amount remaining in gut absorption compartment

            dCdt = A @ C

            # Hepatic clearance (from liver compartment)
            if volumes[idx_liver] > 0:
                dCdt[idx_liver] -= hepatic_cl * C[idx_liver] / volumes[idx_liver]

            # Renal clearance (from kidney compartment)
            if volumes[idx_kidney] > 0:
                dCdt[idx_kidney] -= renal_cl_rate * C[idx_kidney] / volumes[idx_kidney]

            # Absorption for oral/IM/SC routes
            dA_gut = 0.0
            if route in ("oral", "im", "sc"):
                absorption = absorption_ka * A_gut
                dA_gut = -absorption
                if volumes[idx_gut] > 0:
                    dCdt[idx_gut] += absorption * bioavailability / volumes[idx_gut]

            # IV infusion
            if route == "iv_infusion" and t <= infusion_duration_h:
                infusion_rate = dose_mg / infusion_duration_h
                if volumes[idx_ven] > 0:
                    dCdt[idx_ven] += infusion_rate / volumes[idx_ven]

            return np.append(dCdt, dA_gut)

        # Set initial conditions based on route
        if route == "iv_bolus":
            C0[idx_ven] = dose_mg / volumes[idx_ven]  # mg/L
        elif route == "iv_infusion":
            pass  # handled in ODE RHS
        elif route == "oral":
            C0[n] = dose_mg  # amount in gut absorption compartment
        elif route == "im":
            C0[n] = dose_mg
            absorption_ka = 0.5  # slower IM absorption
        elif route == "sc":
            C0[n] = dose_mg
            absorption_ka = 0.3  # slowest SC absorption
        else:
            raise ValueError(f"Unknown route: {route}. Must be one of {ROUTES}")

        # Solve ODE
        t_span = (0.0, duration_h)
        t_eval = np.arange(0.0, duration_h + dt, dt)

        if HAS_SCIPY:
            sol = solve_ivp(
                _ode_rhs, t_span, C0,
                method="RK45",
                t_eval=t_eval,
                max_step=dt * 2,
                rtol=1e-6,
                atol=1e-9,
            )
            t_out = sol.t.tolist()
            C_out = {TISSUE_NAMES[i]: sol.y[i].tolist() for i in range(n)}
        else:
            # Euler fallback
            logger.warning("SciPy not available, using Euler method (less accurate)")
            t_out = t_eval.tolist()
            y = C0.copy()
            C_out = {t: [] for t in TISSUE_NAMES}
            for t in t_eval:
                for i in range(n):
                    C_out[TISSUE_NAMES[i]].append(float(y[i]))
                dydt = _ode_rhs(t, y)
                y = y + dydt * dt
                y = np.maximum(y, 0.0)  # concentrations can't be negative

        return {
            "time_h": t_out,
            "concentrations": C_out,
            "n_compartments": n,
            "route": route,
            "dose_mg": dose_mg,
            "duration_h": duration_h,
        }


# ===========================================================================
# MODULE 3: QAOA-PK Optimizer
# ===========================================================================
class QAOAPKOptimizer:
    """QAOA-based dosing regimen optimization.

    Uses a 6-qubit QAOA circuit (p=2) to optimize:
      - Dose amount (mg)
      - Dosing interval (hours)
      - Loading dose (mg)
      - Number of doses
      - Infusion duration (hours, if IV)
      - Formulation adjustment factor

    Cost function encodes: therapeutic window compliance, toxicity
    minimization, and convenience (fewer doses preferred).
    """

    def __init__(self, n_qubits: int = N_QUBITS_QAOA_PK, depth: int = QAOA_PK_DEPTH,
                 shots: int = DEFAULT_SHOTS):
        self.n_qubits = n_qubits
        self.depth = depth
        self.shots = shots

    def _encode_pk_context(
        self,
        target_cmin: float,
        target_cmax: float,
        half_life_h: float,
        clearance: float,
        vd: float,
    ) -> np.ndarray:
        """Encode PK context into angle biases for QAOA initial state."""
        # Normalize each parameter to [0, pi]
        cmin_norm = min(target_cmin / 100.0, 1.0) * np.pi
        cmax_norm = min(target_cmax / 500.0, 1.0) * np.pi
        t12_norm = min(half_life_h / 48.0, 1.0) * np.pi
        cl_norm = min(clearance / 50.0, 1.0) * np.pi
        vd_norm = min(vd / 500.0, 1.0) * np.pi

        # Derive the 6th context from therapeutic ratio
        ratio = target_cmax / (target_cmin + 1e-6)
        ratio_norm = min(ratio / 20.0, 1.0) * np.pi

        return np.array([cmin_norm, cmax_norm, t12_norm, cl_norm, vd_norm, ratio_norm])

    def _build_qaoa_pk_circuit(
        self,
        context_angles: np.ndarray,
        gamma: List[float],
        beta: List[float],
    ) -> QuantumCircuit:
        """Build QAOA circuit for PK dosing optimization.

        Architecture:
          1. H on all qubits
          2. Ry(context) initial bias
          3. For each QAOA layer p:
             a. Cost layer: Rzz(gamma_p) on all pairs + Rz(gamma_p * context)
             b. Mixer layer: Rx(beta_p) on all qubits
          4. Measure all
        """
        if not HAS_QISKIT:
            raise RuntimeError("Qiskit required for QAOA circuit")

        n = self.n_qubits
        qc = QuantumCircuit(n, n)

        # Initial superposition
        for i in range(n):
            qc.h(i)

        # Context encoding bias
        for i in range(n):
            qc.ry(float(context_angles[i]), i)

        # QAOA layers
        for p in range(self.depth):
            g = gamma[p]
            b = beta[p]

            # Cost layer: ZZ couplings
            for i in range(n):
                for j in range(i + 1, n):
                    qc.cx(i, j)
                    qc.rz(float(g * 0.5), j)
                    qc.cx(i, j)

            # Cost layer: Z terms (context-biased)
            for i in range(n):
                qc.rz(float(g * context_angles[i] * 0.3), i)

            qc.barrier()

            # Mixer layer: Rx rotations
            for i in range(n):
                qc.rx(float(b), i)

        qc.measure(range(n), range(n))
        return qc

    def _decode_dosing_regimen(
        self,
        counts: Dict[str, int],
        target_cmin: float,
        target_cmax: float,
        half_life_h: float,
        clearance: float,
        vd: float,
        max_doses: int,
    ) -> Dict[str, Any]:
        """Decode QAOA measurement results into dosing recommendations.

        Each qubit encodes a dosing parameter:
          q0: dose magnitude (low/high)
          q1: dosing interval (short/long)
          q2: loading dose (no/yes)
          q3: number of doses (few/many)
          q4: infusion duration (short/long)
          q5: formulation factor (standard/extended-release)
        """
        total = sum(counts.values())
        if total == 0:
            return {"error": "No measurement results"}

        # Find most probable bitstring
        best_bits = max(counts, key=counts.get)
        bits = best_bits if isinstance(best_bits, str) else format(best_bits, f'0{self.n_qubits}b')
        bits = bits.zfill(self.n_qubits)

        # Also compute weighted average for continuous parameters
        weighted = np.zeros(self.n_qubits)
        for bs, count in counts.items():
            b_str = bs if isinstance(bs, str) else format(bs, f'0{self.n_qubits}b')
            b_str = b_str.zfill(self.n_qubits)
            for i in range(min(len(b_str), self.n_qubits)):
                if b_str[-(i + 1)] == '1':
                    weighted[i] += count / total

        # Decode parameters using PK equations
        # Maintenance dose: D = CL * Css * tau / F
        # where Css ~ (Cmin + Cmax) / 2
        css_target = (target_cmin + target_cmax) / 2.0

        # Dosing interval from half-life: tau ~ 1-3 * t1/2
        tau_factor = 1.0 + weighted[1] * 2.0  # 1.0 to 3.0
        interval_h = half_life_h * tau_factor
        interval_h = max(4.0, min(48.0, interval_h))

        # Maintenance dose
        F = 0.7 + weighted[5] * 0.25  # bioavailability 0.7-0.95
        dose_mg = clearance * css_target * interval_h / F
        dose_mg = max(1.0, round(dose_mg, 1))

        # Loading dose
        use_loading = weighted[2] > 0.5
        loading_dose_mg = round(vd * css_target, 1) if use_loading else 0.0

        # Number of doses
        n_doses_factor = 1.0 + weighted[3] * (max_doses - 1)
        n_doses = max(1, min(max_doses, round(n_doses_factor)))

        # Infusion duration
        infusion_h = 0.5 + weighted[4] * 3.5  # 0.5 to 4.0 hours

        # Verify therapeutic window compliance
        # Cmax_pred = (F * D) / Vd  (for first dose)
        cmax_pred = (F * dose_mg) / (vd + 1e-6)
        # Cmin_pred at trough (t = tau)
        ke = 0.693 / (half_life_h + 1e-6)
        cmin_pred = cmax_pred * math.exp(-ke * interval_h)

        # Accumulation factor at steady state
        accum = 1.0 / (1.0 - math.exp(-ke * interval_h) + 1e-6)
        cmax_ss = cmax_pred * accum
        cmin_ss = cmin_pred * accum

        return {
            "dose_mg": dose_mg,
            "interval_h": round(interval_h, 1),
            "loading_dose_mg": loading_dose_mg,
            "n_doses": n_doses,
            "infusion_h": round(infusion_h, 1),
            "bioavailability": round(F, 3),
            "predicted_cmax_ss": round(cmax_ss, 3),
            "predicted_cmin_ss": round(cmin_ss, 3),
            "target_cmin": target_cmin,
            "target_cmax": target_cmax,
            "within_window": target_cmin <= cmin_ss <= cmax_ss <= target_cmax,
            "accumulation_factor": round(accum, 2),
            "measurement_probabilities": {str(k): v / total for k, v in
                                          sorted(counts.items(), key=lambda x: -x[1])[:10]},
        }

    def optimize_quantum(
        self,
        target_cmin: float,
        target_cmax: float,
        half_life_h: float,
        clearance: float,
        vd: float,
        max_doses: int = 4,
    ) -> Dict[str, Any]:
        """Run QAOA dosing optimization on IBM Boston 156Q."""
        context = self._encode_pk_context(target_cmin, target_cmax, half_life_h, clearance, vd)

        # QAOA parameters (pre-optimized for PK problems)
        gamma = [0.8, 0.5]
        beta = [0.6, 0.3]

        qc = self._build_qaoa_pk_circuit(context, gamma, beta)
        counts_list, job_ids = _run_sampler([qc], shots=self.shots)

        _audit_log({
            "action": "qaoa_pk_optimize",
            "job_ids": job_ids,
            "target_cmin": target_cmin,
            "target_cmax": target_cmax,
        })

        result = self._decode_dosing_regimen(
            counts_list[0], target_cmin, target_cmax,
            half_life_h, clearance, vd, max_doses,
        )
        result["job_ids"] = job_ids
        result["method"] = f"quantum_qaoa_{IBM_BACKEND}"
        return result

    def optimize_classical(
        self,
        target_cmin: float,
        target_cmax: float,
        half_life_h: float,
        clearance: float,
        vd: float,
        max_doses: int = 4,
    ) -> Dict[str, Any]:
        """Classical fallback: analytical PK optimization."""
        ke = 0.693 / (half_life_h + 1e-6)
        css_target = (target_cmin + target_cmax) / 2.0

        # Optimal interval: 1-2 half-lives for most drugs
        interval_h = half_life_h * 1.5
        interval_h = max(4.0, min(48.0, interval_h))

        F = 0.7
        dose_mg = clearance * css_target * interval_h / F
        dose_mg = max(1.0, round(dose_mg, 1))

        loading_dose_mg = round(vd * css_target, 1)

        cmax_pred = (F * dose_mg) / (vd + 1e-6)
        cmin_pred = cmax_pred * math.exp(-ke * interval_h)
        accum = 1.0 / (1.0 - math.exp(-ke * interval_h) + 1e-6)

        return {
            "dose_mg": dose_mg,
            "interval_h": round(interval_h, 1),
            "loading_dose_mg": loading_dose_mg,
            "n_doses": min(max_doses, max(1, int(72 / interval_h))),
            "infusion_h": 1.0,
            "bioavailability": F,
            "predicted_cmax_ss": round(cmax_pred * accum, 3),
            "predicted_cmin_ss": round(cmin_pred * accum, 3),
            "target_cmin": target_cmin,
            "target_cmax": target_cmax,
            "within_window": target_cmin <= cmin_pred * accum <= cmax_pred * accum <= target_cmax,
            "accumulation_factor": round(accum, 2),
            "method": "classical_analytical",
        }

    def optimize(
        self,
        target_cmin: float,
        target_cmax: float,
        half_life_h: float,
        clearance: float,
        vd: float,
        max_doses: int = 4,
    ) -> Dict[str, Any]:
        """Quantum-first dosing optimization with classical fallback."""
        try:
            return self.optimize_quantum(
                target_cmin, target_cmax, half_life_h, clearance, vd, max_doses,
            )
        except Exception as exc:
            logger.warning("QAOA-PK quantum failed (%s), falling back to classical", exc)
            return self.optimize_classical(
                target_cmin, target_cmax, half_life_h, clearance, vd, max_doses,
            )


# ===========================================================================
# PBPKModeler -- Main orchestrator
# ===========================================================================
class PBPKModeler:
    """Physiologically-Based Pharmacokinetic modeler with quantum-enhanced
    parameter estimation on IBM Boston 156-qubit hardware.

    Integrates:
      - QKP: Quantum Kp Predictor (VQE, 8 qubits)
      - QODE: Quantum ODE Solver (HHL-inspired, 10 qubits)
      - QAOA-PK: Dosing regimen optimizer (QAOA, 6 qubits, p=2)

    14-compartment model with allometric scaling, CYP enzyme kinetics,
    and renal clearance for 5 administration routes.
    """

    def __init__(self, shots: int = DEFAULT_SHOTS):
        self.shots = shots
        self.qkp = QuantumKpPredictor(shots=shots)
        self.qode = QuantumODESolver(shots=shots)
        self.qaoa_pk = QAOAPKOptimizer(shots=shots)

    # -------------------------------------------------------------------
    # Molecular descriptors
    # -------------------------------------------------------------------
    def compute_descriptors(self, smiles: str) -> Dict[str, float]:
        """Compute PBPK-relevant molecular descriptors."""
        return _compute_descriptors(smiles)

    # -------------------------------------------------------------------
    # Kp prediction
    # -------------------------------------------------------------------
    def compute_kp_values(self, smiles: str) -> Dict[str, float]:
        """Predict partition coefficients for all 14 tissues (quantum-first)."""
        return self.qkp.predict(smiles)

    # -------------------------------------------------------------------
    # CYP kinetics
    # -------------------------------------------------------------------
    def estimate_cyp_kinetics(self, smiles: str) -> Dict[str, Dict[str, float]]:
        """Estimate CYP enzyme kinetics (Vmax/Km) from molecular structure.

        Uses molecular descriptors to scale default CYP parameters.
        """
        desc = _compute_descriptors(smiles)
        logp = desc["LogP"]
        mw = desc["MW"]
        tpsa = desc["TPSA"]

        cyp_params = {}
        for enzyme, defaults in CYP_DEFAULTS.items():
            # Scale Vmax by lipophilicity (more lipophilic = more CYP metabolism)
            lipophilicity_scale = 1.0 + 0.15 * max(0, logp - 2.0)

            # Scale Km by molecular weight (larger molecules = higher Km)
            mw_scale = 1.0 + 0.002 * max(0, mw - 300.0)

            # TPSA effect: higher TPSA = lower CYP affinity
            tpsa_scale = 1.0 + 0.005 * max(0, tpsa - 60.0)

            vmax_adj = defaults["vmax"] * lipophilicity_scale
            km_adj = defaults["km"] * mw_scale * tpsa_scale

            cyp_params[enzyme] = {
                "vmax": round(vmax_adj, 2),
                "km": round(km_adj, 2),
                "fraction": defaults["fraction"],
                "intrinsic_cl": round(vmax_adj / km_adj, 4),  # CLint = Vmax/Km
            }

        return cyp_params

    # -------------------------------------------------------------------
    # Hepatic clearance (well-stirred model)
    # -------------------------------------------------------------------
    def compute_hepatic_clearance(
        self,
        cyp_params: Dict[str, Dict[str, float]],
        fu: float,
        weight_kg: float = REFERENCE_WEIGHT_KG,
    ) -> float:
        """Compute hepatic clearance using well-stirred model.

        CL_h = Q_h * fu * CL_int / (Q_h + fu * CL_int)
        """
        scale = (weight_kg / REFERENCE_WEIGHT_KG) ** 0.75
        Q_h = TISSUE_PARAMS["liver"]["blood_flow_frac"] * CARDIAC_OUTPUT_L_H * scale

        # Total intrinsic clearance from all CYP enzymes
        cl_int_total = sum(
            p["intrinsic_cl"] * p["fraction"]
            for p in cyp_params.values()
        )

        cl_h = (Q_h * fu * cl_int_total) / (Q_h + fu * cl_int_total + 1e-12)
        return round(cl_h, 4)

    # -------------------------------------------------------------------
    # Renal clearance
    # -------------------------------------------------------------------
    def compute_renal_clearance(
        self,
        fu: float,
        mw: float,
        weight_kg: float = REFERENCE_WEIGHT_KG,
    ) -> float:
        """Compute renal clearance.

        CL_r = fu * GFR * (1 - reabsorption) + tubular_secretion
        Molecules > 500 Da have reduced glomerular filtration.
        """
        scale = (weight_kg / REFERENCE_WEIGHT_KG) ** 0.75
        gfr_scaled = GFR_ML_MIN * scale * 60.0 / 1000.0  # Convert to L/h

        # MW cutoff for filtration
        filtration_frac = 1.0 if mw < 500 else max(0.1, 1.0 - (mw - 500) / 5000.0)

        cl_r = fu * gfr_scaled * filtration_frac * (1.0 - TUBULAR_REABSORPTION)
        return round(cl_r, 4)

    # -------------------------------------------------------------------
    # Allometric scaling
    # -------------------------------------------------------------------
    @staticmethod
    def allometric_scale(
        value: float,
        weight_kg: float,
        exponent: float = 0.75,
    ) -> float:
        """Scale a PK parameter from 70 kg reference to actual weight."""
        return value * (weight_kg / REFERENCE_WEIGHT_KG) ** exponent

    # -------------------------------------------------------------------
    # PK parameter extraction from concentration-time data
    # -------------------------------------------------------------------
    @staticmethod
    def extract_pk_parameters(
        time_h: List[float],
        plasma_conc: List[float],
        dose_mg: float,
        weight_kg: float,
    ) -> Dict[str, float]:
        """Extract standard PK parameters from plasma concentration-time curve.

        Returns: Cmax, Tmax, AUC (trapezoidal), t1/2 (terminal), Vss, CL.
        """
        t = np.array(time_h)
        c = np.array(plasma_conc)

        if len(t) == 0 or len(c) == 0:
            return {}

        # Cmax, Tmax
        idx_max = np.argmax(c)
        cmax = float(c[idx_max])
        tmax = float(t[idx_max])

        # AUC (linear trapezoidal)
        auc = float(np.trapz(c, t))

        # Terminal half-life (from last 30% of data where C > 0)
        n_term = max(3, int(len(c) * 0.3))
        c_term = c[-n_term:]
        t_term = t[-n_term:]
        c_positive = c_term > 1e-12
        if np.sum(c_positive) >= 2:
            log_c = np.log(c_term[c_positive])
            t_pos = t_term[c_positive]
            # Linear regression on log(C) vs t
            if len(t_pos) >= 2:
                slope = (log_c[-1] - log_c[0]) / (t_pos[-1] - t_pos[0] + 1e-12)
                ke = -slope
                t_half = 0.693 / (ke + 1e-12) if ke > 0 else float('inf')
            else:
                t_half = float('inf')
                ke = 0.0
        else:
            t_half = float('inf')
            ke = 0.0

        # Clearance: CL = Dose / AUC
        cl = dose_mg / (auc + 1e-12)

        # Volume of distribution at steady state: Vss = CL * MRT
        # MRT = AUMC / AUC
        aumc = float(np.trapz(c * t, t))
        mrt = aumc / (auc + 1e-12)
        vss = cl * mrt

        return {
            "Cmax_mg_L": round(cmax, 4),
            "Tmax_h": round(tmax, 2),
            "AUC_mg_h_L": round(auc, 4),
            "t_half_h": round(min(t_half, 999.0), 2),
            "ke_h": round(ke, 6),
            "CL_L_h": round(cl, 4),
            "Vss_L": round(vss, 2),
            "MRT_h": round(mrt, 2),
            "AUMC_mg_h2_L": round(aumc, 4),
        }

    # -------------------------------------------------------------------
    # Full PBPK solve
    # -------------------------------------------------------------------
    def solve_pbpk(
        self,
        smiles: str,
        dose_mg: float,
        route: str = "oral",
        weight_kg: float = REFERENCE_WEIGHT_KG,
        duration_h: float = 24.0,
        dt: float = 0.1,
    ) -> Dict[str, Any]:
        """Solve the full 14-compartment PBPK model.

        Steps:
          1. Compute molecular descriptors
          2. Predict Kp values (quantum-first)
          3. Estimate CYP kinetics and clearance
          4. Build coupling matrix
          5. Apply quantum rate correction (quantum-first)
          6. Solve ODE system
          7. Extract PK parameters

        Returns comprehensive result dict with concentration curves and PK params.
        """
        t0 = time.time()
        job_ids: List[str] = []

        # Step 1: Molecular descriptors
        desc = self.compute_descriptors(smiles)
        logger.info("PBPK descriptors: MW=%.1f, LogP=%.2f, fu=%.3f",
                     desc["MW"], desc["LogP"], desc["fu_est"])

        # Step 2: Quantum Kp prediction
        kp_values = self.compute_kp_values(smiles)

        # Step 3: CYP kinetics and clearance
        cyp_params = self.estimate_cyp_kinetics(smiles)
        hepatic_cl = self.compute_hepatic_clearance(cyp_params, desc["fu_est"], weight_kg)
        renal_cl = self.compute_renal_clearance(desc["fu_est"], desc["MW"], weight_kg)
        total_cl = hepatic_cl + renal_cl

        # Step 4: Build coupling matrix
        A = self.qode._build_coupling_matrix(kp_values, weight_kg)

        # Step 5: Quantum rate correction
        try:
            A_corrected = self.qode._quantum_rate_correction(A)
            rate_correction_method = f"quantum_hhl_{IBM_BACKEND}"
        except Exception as exc:
            logger.warning("QODE quantum correction failed (%s), using uncorrected matrix", exc)
            A_corrected = A
            rate_correction_method = "classical_uncorrected"

        # Step 6: ODE solve
        # Absorption parameters based on descriptors
        ka_oral = 1.0 / (1.0 + 0.01 * desc["MW"])  # slower for larger molecules
        ka_oral = max(0.1, min(3.0, ka_oral))
        F = desc["fu_est"] * 0.9  # rough oral bioavailability

        ode_result = self.qode.solve_pbpk_ode(
            A_corrected,
            dose_mg=dose_mg,
            route=route,
            weight_kg=weight_kg,
            duration_h=duration_h,
            dt=dt,
            clearance_params={"hepatic_cl": hepatic_cl, "renal_cl": renal_cl},
            absorption_ka=ka_oral,
            bioavailability=F,
        )

        # Step 7: Extract PK parameters from venous blood (systemic)
        plasma_conc = ode_result["concentrations"].get("venous_blood", [])
        pk_params = self.extract_pk_parameters(
            ode_result["time_h"], plasma_conc, dose_mg, weight_kg,
        )

        elapsed = time.time() - t0

        result = {
            "status": "success",
            "module": "PBPKModeler",
            "version": "1.0",
            "smiles": smiles,
            "dose_mg": dose_mg,
            "route": route,
            "weight_kg": weight_kg,
            "duration_h": duration_h,
            "descriptors": desc,
            "kp_values": kp_values,
            "cyp_kinetics": cyp_params,
            "clearance": {
                "hepatic_CL_L_h": hepatic_cl,
                "renal_CL_L_h": renal_cl,
                "total_CL_L_h": total_cl,
            },
            "rate_correction_method": rate_correction_method,
            "pk_parameters": pk_params,
            "concentration_time_curves": ode_result["concentrations"],
            "time_h": ode_result["time_h"],
            "n_compartments": 14,
            "compartment_names": TISSUE_NAMES,
            "ibm_backend": IBM_BACKEND,
            "elapsed_s": round(elapsed, 2),
        }

        _audit_log({
            "action": "pbpk_full_run",
            "smiles": smiles,
            "dose_mg": dose_mg,
            "route": route,
            "elapsed_s": round(elapsed, 2),
        })

        return result

    # -------------------------------------------------------------------
    # Dosing optimization
    # -------------------------------------------------------------------
    def optimize_dosing(
        self,
        smiles: str,
        target_cmin: float,
        target_cmax: float,
        max_doses: int = 4,
        weight_kg: float = REFERENCE_WEIGHT_KG,
        optimizer: str = "quantum_first",
    ) -> Dict[str, Any]:
        """Optimize a dosing regimen. `optimizer` selects which one decides.

        MEASURED 2026-09-17, same PK input, three consecutive runs:

            optimize_classical  ->  169.7, 169.7, 169.7 mg   (deterministic)
            QAOA-PK             ->  217.7, 218.7, 215.9 mg   (varies per run)

        A recommended dose that changes between runs of the same molecule is not
        usable in drug design, so `optimizer="classical"` exists and is what the
        dose derivation asks for. QAOA-PK stays available and reachable, but it
        cannot silently decide a dose.

        optimizer:
          "classical"      -- deterministic solve only.
          "quantum_first"  -- QAOA-PK, falling back to classical (historic default).
        """
        # Baseline PK solve (small dose to get parameters)
        baseline = self.solve_pbpk(smiles, dose_mg=100.0, route="oral",
                                   weight_kg=weight_kg, duration_h=48.0)

        pk = baseline.get("pk_parameters", {})
        t_half = pk.get("t_half_h", 8.0)
        cl = pk.get("CL_L_h", 10.0)
        vss = pk.get("Vss_L", 100.0)

        # Clamp unreasonable values
        t_half = max(0.5, min(200.0, t_half))
        cl = max(0.01, min(100.0, cl))
        vss = max(1.0, min(1000.0, vss))

        _opt = (optimizer or "quantum_first").strip().lower()
        _chooser = (self.qaoa_pk.optimize_classical if _opt == "classical"
                    else self.qaoa_pk.optimize)
        regimen = _chooser(
            target_cmin=target_cmin,
            target_cmax=target_cmax,
            half_life_h=t_half,
            clearance=cl,
            vd=vss,
            max_doses=max_doses,
        )
        regimen["optimizer"] = _opt
        regimen["deterministic"] = (_opt == "classical")

        regimen["baseline_pk"] = pk
        regimen["smiles"] = smiles
        regimen["weight_kg"] = weight_kg
        regimen["ibm_backend"] = IBM_BACKEND

        _audit_log({
            "action": "pbpk_dosing_optimization",
            "smiles": smiles,
            "target_cmin": target_cmin,
            "target_cmax": target_cmax,
            "optimal_dose_mg": regimen.get("dose_mg"),
            "interval_h": regimen.get("interval_h"),
        })

        return regimen

    # -------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------
    def run_full_pbpk(
        self,
        smiles: str,
        dose_mg: float,
        route: str = "oral",
        weight_kg: float = REFERENCE_WEIGHT_KG,
        duration_h: float = 72.0,
        target_cmin: Optional[float] = None,
        target_cmax: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Full PBPK analysis: solve model + optional dosing optimization.

        Parameters
        ----------
        smiles : str
            SMILES string of the drug molecule.
        dose_mg : float
            Dose amount in mg.
        route : str
            Administration route: iv_bolus, iv_infusion, oral, im, sc.
        weight_kg : float
            Patient weight in kg (default 70).
        duration_h : float
            Simulation duration in hours (default 72).
        target_cmin : float, optional
            Target trough concentration (mg/L) for dosing optimization.
        target_cmax : float, optional
            Target peak concentration (mg/L) for dosing optimization.

        Returns
        -------
        dict
            Complete PBPK results including concentration curves, PK parameters,
            and optional dosing optimization.
        """
        t0 = time.time()

        # Validate route
        if route not in ROUTES:
            raise ValueError(f"Invalid route '{route}'. Must be one of: {ROUTES}")

        # Run PBPK model
        result = self.solve_pbpk(
            smiles, dose_mg, route, weight_kg, duration_h,
        )

        # Optional dosing optimization
        if target_cmin is not None and target_cmax is not None:
            try:
                dosing = self.optimize_dosing(
                    smiles, target_cmin, target_cmax,
                    weight_kg=weight_kg,
                )
                result["dosing_optimization"] = dosing
            except Exception as exc:
                logger.warning("Dosing optimization failed: %s", exc)
                result["dosing_optimization"] = {"error": str(exc)}

        # Tissue exposure summary
        tissue_auc = {}
        for tissue_name in TISSUE_NAMES:
            conc = result["concentration_time_curves"].get(tissue_name, [])
            t_arr = result.get("time_h", [])
            if len(conc) >= 2 and len(t_arr) >= 2:
                tissue_auc[tissue_name] = round(float(np.trapz(conc, t_arr)), 4)
            else:
                tissue_auc[tissue_name] = 0.0

        result["tissue_exposure_AUC"] = tissue_auc

        # Tissue Cmax summary
        tissue_cmax = {}
        for tissue_name in TISSUE_NAMES:
            conc = result["concentration_time_curves"].get(tissue_name, [])
            tissue_cmax[tissue_name] = round(float(max(conc)), 4) if conc else 0.0
        result["tissue_Cmax"] = tissue_cmax

        result["total_elapsed_s"] = round(time.time() - t0, 2)

        return result


# ===========================================================================
# Flask route registration
# ===========================================================================
def register_pbpk_routes(app):
    """Register PBPK modeler Flask routes.

    Routes added:
        POST /api/pipeline/pbpk                -- full PBPK run
        POST /api/tools/pipeline/pbpk          -- alias
        POST /api/pipeline/pbpk/kp_values      -- Kp prediction only
        POST /api/tools/pipeline/pbpk/kp_values
        POST /api/pipeline/pbpk/optimize_dosing -- dosing optimization
        POST /api/tools/pipeline/pbpk/optimize_dosing
        GET  /api/pipeline/pbpk/health         -- health check
        GET  /api/tools/pipeline/pbpk/health
    """
    from flask import request, jsonify, make_response

    modeler = PBPKModeler()

    def _validated_smiles(data):
        """Return a canonical SMILES or a non-reflecting 400 response.

        Request values reach RDKit only after type, size, character and chemical
        parsing checks.  Error bodies deliberately do not echo attacker-controlled
        input (SQL/XSS payloads).

        MOLVERA / BIOQL
        """
        raw = data.get("smiles")
        if not isinstance(raw, str) or not raw.strip():
            return None, (jsonify({
                "status": "validation_error",
                "error": "smiles must be a non-empty string",
            }), 400)
        candidate = raw.strip()
        if len(candidate) > 10_000:
            return None, (jsonify({
                "status": "validation_error",
                "error": "smiles exceeds the maximum accepted length",
            }), 400)
        try:
            from rdkit import Chem
            molecule = Chem.MolFromSmiles(candidate)
            if molecule is None:
                raise ValueError("unparseable")
            canonical = Chem.MolToSmiles(molecule, canonical=True)
        except Exception:
            return None, (jsonify({
                "status": "validation_error",
                "error": "invalid SMILES",
            }), 400)
        return canonical, None

    # --- Full PBPK run ---------------------------------------------------
    @app.route("/api/pipeline/pbpk", methods=["POST", "OPTIONS"])
    @app.route("/api/tools/pipeline/pbpk", methods=["POST", "OPTIONS"])
    def _pbpk_run():
        if request.method == "OPTIONS":
            return make_response("", 204)
        data = request.get_json() or {}
        smiles, validation_error = _validated_smiles(data)
        if validation_error:
            return validation_error
        try:
            result = modeler.run_full_pbpk(
                smiles=smiles,
                dose_mg=float(data.get("dose_mg", 100.0)),
                route=data.get("route", "oral"),
                weight_kg=float(data.get("weight_kg", 70.0)),
                duration_h=float(data.get("duration_h", 72.0)),
                target_cmin=float(data["target_cmin"]) if "target_cmin" in data else None,
                target_cmax=float(data["target_cmax"]) if "target_cmax" in data else None,
            )
            return jsonify(result)
        except Exception as exc:
            logger.exception("PBPK pipeline error")
            return jsonify({"error": str(exc)}), 500

    # --- Kp values only --------------------------------------------------
    @app.route("/api/pipeline/pbpk/kp_values", methods=["POST", "OPTIONS"])
    @app.route("/api/tools/pipeline/pbpk/kp_values", methods=["POST", "OPTIONS"])
    def _pbpk_kp():
        if request.method == "OPTIONS":
            return make_response("", 204)
        data = request.get_json() or {}
        smiles, validation_error = _validated_smiles(data)
        if validation_error:
            return validation_error
        try:
            kp = modeler.compute_kp_values(smiles)
            desc = modeler.compute_descriptors(smiles)
            return jsonify({
                "status": "success",
                "smiles": smiles,
                "kp_values": kp,
                "descriptors": desc,
                "n_compartments": 14,
                "ibm_backend": IBM_BACKEND,
            })
        except Exception as exc:
            logger.exception("PBPK Kp prediction error")
            return jsonify({"error": str(exc)}), 500

    # --- Dosing optimization ---------------------------------------------
    @app.route("/api/pipeline/pbpk/optimize_dosing", methods=["POST", "OPTIONS"])
    @app.route("/api/tools/pipeline/pbpk/optimize_dosing", methods=["POST", "OPTIONS"])
    def _pbpk_optimize():
        if request.method == "OPTIONS":
            return make_response("", 204)
        data = request.get_json() or {}
        smiles, validation_error = _validated_smiles(data)
        if validation_error:
            return validation_error
        target_cmin = data.get("target_cmin")
        target_cmax = data.get("target_cmax")
        if target_cmin is None or target_cmax is None:
            return jsonify({"error": "target_cmin and target_cmax are required"}), 400
        try:
            result = modeler.optimize_dosing(
                smiles=smiles,
                target_cmin=float(target_cmin),
                target_cmax=float(target_cmax),
                max_doses=int(data.get("max_doses", 4)),
                weight_kg=float(data.get("weight_kg", 70.0)),
            )
            return jsonify(result)
        except Exception as exc:
            logger.exception("PBPK dosing optimization error")
            return jsonify({"error": str(exc)}), 500

    # --- Health check ----------------------------------------------------
    @app.route("/api/pipeline/pbpk/health", methods=["GET"])
    @app.route("/api/tools/pipeline/pbpk/health", methods=["GET"])
    def _pbpk_health():
        return jsonify({
            "status": "ok",
            "module": "PBPKModeler",
            "version": "1.0",
            "backend": IBM_BACKEND,
            "n_compartments": 14,
            "compartments": TISSUE_NAMES,
            "routes": ROUTES,
            "quantum_modules": ["QKP", "QODE", "QAOA-PK"],
            "has_rdkit": HAS_RDKIT,
            "has_qiskit": HAS_QISKIT,
            "has_ibm_runtime": HAS_IBM_RUNTIME,
            "has_scipy": HAS_SCIPY,
        })

    logger.info("PBPK modeler Flask routes registered (4 endpoints, dual paths)")
