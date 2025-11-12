"""
BioQL Auditable Logging System - v5.3.0

Sistema de logs que separa claramente:
- HARDWARE_*: Ejecución real en hardware cuántico
- DOCKING_*: Cálculos de docking clásicos (Vina/gnina)
- POSTPROC_*: Post-procesamiento y análisis
- QUALTRAN_*: Visualizaciones y estimaciones

Evita confusión entre resultados reales y simulados.
"""

import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Logger dedicado para auditoría
audit_logger = logging.getLogger("bioql.audit")
audit_logger.setLevel(logging.INFO)


@dataclass
class HardwareExecution:
    """Registro de ejecución REAL en hardware cuántico."""
    backend: str
    job_id: str
    shots: int
    qubits_physical: int
    qubits_logical: int
    program_type: str  # "sampler", "estimator", "vqe", etc.
    runtime_seconds: float
    queue_time_seconds: Optional[float]
    cost_usd: float
    counts: Dict[str, int]
    status: str  # "DONE", "ERROR", "CANCELLED"
    timestamp: str
    provider: str  # "IBM", "IonQ", "AWS Braket", etc.

    def to_dict(self):
        return asdict(self)

    def log(self):
        """Log con prefijo HARDWARE_"""
        audit_logger.info(f"HARDWARE_BACKEND={self.backend}")
        audit_logger.info(f"HARDWARE_JOB_ID={self.job_id}")
        audit_logger.info(f"HARDWARE_SHOTS={self.shots}")
        audit_logger.info(f"HARDWARE_QUBITS_PHYSICAL={self.qubits_physical}")
        audit_logger.info(f"HARDWARE_QUBITS_LOGICAL={self.qubits_logical}")
        audit_logger.info(f"HARDWARE_PROGRAM={self.program_type}")
        audit_logger.info(f"HARDWARE_RUNTIME_S={self.runtime_seconds:.3f}")
        audit_logger.info(f"HARDWARE_COST_USD=${self.cost_usd:.4f}")
        audit_logger.info(f"HARDWARE_COUNTS={json.dumps(self.counts)}")
        audit_logger.info(f"HARDWARE_STATUS={self.status}")
        audit_logger.info(f"HARDWARE_PROVIDER={self.provider}")


@dataclass
class DockingExecution:
    """Registro de docking clásico REAL (Vina/gnina/etc)."""
    engine: str  # "vina", "gnina", "smina", etc.
    ligand_smiles: str
    receptor_pdb: str
    best_affinity_kcal_per_mol: float
    num_poses: int
    runtime_seconds: float
    center: tuple
    box_size: tuple
    output_files: Dict[str, str]  # {"pdbqt": "path", "log": "path"}
    timestamp: str

    def to_dict(self):
        return asdict(self)

    def log(self):
        """Log con prefijo DOCKING_"""
        audit_logger.info(f"DOCKING_ENGINE={self.engine}")
        audit_logger.info(f"DOCKING_LIGAND={self.ligand_smiles}")
        audit_logger.info(f"DOCKING_RECEPTOR={self.receptor_pdb}")
        audit_logger.info(f"DOCKING_BEST_AFFINITY_KCAL={self.best_affinity_kcal_per_mol:.2f}")
        audit_logger.info(f"DOCKING_NUM_POSES={self.num_poses}")
        audit_logger.info(f"DOCKING_RUNTIME_S={self.runtime_seconds:.3f}")
        audit_logger.info(f"DOCKING_OUTPUT_FILES={json.dumps(self.output_files)}")


@dataclass
class PostprocessExecution:
    """Registro de post-procesamiento (NO altera resultados físicos)."""
    method: str  # "quantum_features", "score_fusion", "ml_prediction", etc.
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    description: str
    timestamp: str
    warning: str = "⚠️  POSTPROC: No modifica resultados de hardware/docking reales"

    def to_dict(self):
        return asdict(self)

    def log(self):
        """Log con prefijo POSTPROC_"""
        audit_logger.warning(self.warning)
        audit_logger.info(f"POSTPROC_METHOD={self.method}")
        audit_logger.info(f"POSTPROC_DESCRIPTION={self.description}")
        audit_logger.info(f"POSTPROC_INPUTS={json.dumps(self.inputs, default=str)}")
        audit_logger.info(f"POSTPROC_OUTPUTS={json.dumps(self.outputs, default=str)}")


@dataclass
class QualtranVisualization:
    """Registro de visualizaciones Qualtran (estimaciones, no ejecución real)."""
    available: bool
    circuit_name: str
    estimated_resources: Optional[Dict[str, Any]]
    output_file: Optional[str]
    timestamp: str
    note: str = "ℹ️  Qualtran: Estimaciones teóricas, no ejecución física"

    def to_dict(self):
        return asdict(self)

    def log(self):
        """Log con prefijo QUALTRAN_"""
        audit_logger.info(self.note)
        audit_logger.info(f"QUALTRAN_AVAILABLE={self.available}")
        audit_logger.info(f"QUALTRAN_CIRCUIT={self.circuit_name}")
        if self.estimated_resources:
            audit_logger.info(f"QUALTRAN_ESTIMATED_RESOURCES={json.dumps(self.estimated_resources)}")
        if self.output_file:
            audit_logger.info(f"QUALTRAN_OUTPUT={self.output_file}")


class AuditableSession:
    """Sesión auditable que registra todas las fases."""

    def __init__(self, session_name: str, output_dir: Optional[Path] = None):
        self.session_name = session_name
        self.output_dir = output_dir or Path("bioql_audit_logs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.hardware_executions: list[HardwareExecution] = []
        self.docking_executions: list[DockingExecution] = []
        self.postproc_executions: list[PostprocessExecution] = []
        self.qualtran_visualizations: list[QualtranVisualization] = []

        self.start_time = datetime.now()
        audit_logger.info(f"SESSION_START={self.session_name} at {self.start_time.isoformat()}")

    def add_hardware(self, hw: HardwareExecution):
        """Registra ejecución en hardware cuántico real."""
        hw.log()
        self.hardware_executions.append(hw)

    def add_docking(self, dk: DockingExecution):
        """Registra ejecución de docking clásico real."""
        dk.log()
        self.docking_executions.append(dk)

    def add_postproc(self, pp: PostprocessExecution):
        """Registra post-procesamiento (con advertencia)."""
        pp.log()
        self.postproc_executions.append(pp)

    def add_qualtran(self, qt: QualtranVisualization):
        """Registra visualización Qualtran (estimación)."""
        qt.log()
        self.qualtran_visualizations.append(qt)

    def save_report(self) -> Path:
        """Guarda reporte JSON auditable completo."""
        end_time = datetime.now()

        report = {
            "session_name": self.session_name,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds(),

            "HARDWARE_EXECUTIONS": [hw.to_dict() for hw in self.hardware_executions],
            "DOCKING_EXECUTIONS": [dk.to_dict() for dk in self.docking_executions],
            "POSTPROC_EXECUTIONS": [pp.to_dict() for pp in self.postproc_executions],
            "QUALTRAN_VISUALIZATIONS": [qt.to_dict() for qt in self.qualtran_visualizations],

            "SUMMARY": {
                "total_hardware_jobs": len(self.hardware_executions),
                "total_docking_runs": len(self.docking_executions),
                "total_postproc_steps": len(self.postproc_executions),
                "total_qualtran_viz": len(self.qualtran_visualizations),
                "total_cost_usd": sum(hw.cost_usd for hw in self.hardware_executions),
                "total_shots": sum(hw.shots for hw in self.hardware_executions)
            },

            "NOTES": [
                "HARDWARE_*: Resultados de ejecución REAL en computadoras cuánticas",
                "DOCKING_*: Resultados de software de docking clásico REAL (Vina/gnina)",
                "POSTPROC_*: Análisis derivados que NO modifican resultados físicos",
                "QUALTRAN_*: Visualizaciones y estimaciones teóricas"
            ]
        }

        report_file = self.output_dir / f"{self.session_name}_audit_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        audit_logger.info(f"SESSION_END={self.session_name}")
        audit_logger.info(f"AUDIT_REPORT_SAVED={report_file}")

        return report_file

    def print_summary(self):
        """Imprime resumen claro en consola."""
        print("\n" + "="*80)
        print(f"📊 BioQL Auditable Session: {self.session_name}")
        print("="*80)

        print(f"\n🔬 HARDWARE (Quantum Computing Real):")
        for hw in self.hardware_executions:
            print(f"  ✅ {hw.provider} {hw.backend}: Job {hw.job_id}")
            print(f"     Shots: {hw.shots}, Cost: ${hw.cost_usd:.4f}, Runtime: {hw.runtime_seconds:.1f}s")

        print(f"\n💊 DOCKING (Classical Real):")
        for dk in self.docking_executions:
            print(f"  ✅ {dk.engine}: {dk.ligand_smiles} → {dk.receptor_pdb}")
            print(f"     ΔG = {dk.best_affinity_kcal_per_mol:.2f} kcal/mol ({dk.num_poses} poses)")

        print(f"\n⚙️  POSTPROC (Derived Analysis - NOT physical):")
        for pp in self.postproc_executions:
            print(f"  ⚠️  {pp.method}: {pp.description}")

        print(f"\n📈 QUALTRAN (Theoretical Estimates):")
        for qt in self.qualtran_visualizations:
            status = "Available" if qt.available else "Unavailable"
            print(f"  ℹ️  {status}: {qt.circuit_name}")

        print("\n" + "="*80)
        total_cost = sum(hw.cost_usd for hw in self.hardware_executions)
        print(f"💰 Total Hardware Cost: ${total_cost:.4f}")
        print("="*80 + "\n")


# Configuración global del logger de auditoría
def configure_audit_logging(output_file: Optional[Path] = None):
    """Configura el logger de auditoría para escribir a archivo."""
    if output_file:
        handler = logging.FileHandler(output_file)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)


__all__ = [
    'HardwareExecution',
    'DockingExecution',
    'PostprocessExecution',
    'QualtranVisualization',
    'AuditableSession',
    'configure_audit_logging',
    'audit_logger'
]
