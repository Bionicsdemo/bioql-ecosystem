# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum Executor
================

Executes quantum computing jobs with visualization generation

Author: Spectrix R&D / BioQL Team
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from quantum_core.backends.quantum_backend_connector import (
    QuantumBackendConnector,
    QuantumBackendType,
)
from quantum_core.backends.visualization_generator import VisualizationGenerator
from quantum_core.optimizers.adaptive_quantum_optimizer import (
    AdaptiveQuantumOptimizer,
    QuantumConfig,
)
from visualization.quantum_viz_engine import MoleculeType, VisualizationType

logger = logging.getLogger(__name__)


class QuantumExecutor:
    """
    Executes quantum computing jobs and generates visualizations
    """

    def __init__(self):
        """Initialize quantum executor"""
        self.backend_connector = QuantumBackendConnector()
        self.viz_generator = VisualizationGenerator()
        logger.info("🚀 Quantum Executor initialized")

    async def execute_job(
        self,
        job_id: str,
        molecule_data: Dict[str, Any],
        molecule_type: str,
        viz_type: str,
        backend_preference: str = "auto",
        shots: int = 1024,
        budget_usd: Optional[float] = None,
        max_time_hours: Optional[float] = None,
        accuracy_target: float = 0.95,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a quantum job and generate visualizations

        Args:
            job_id: Unique job identifier
            molecule_data: Molecular structure data
            molecule_type: Type of molecule (protein, dna, etc.)
            viz_type: Type of visualization
            backend_preference: Preferred quantum backend
            shots: Number of quantum measurements
            budget_usd: Budget constraint
            max_time_hours: Time constraint
            accuracy_target: Target accuracy
            api_key: BioQL API key for quantum hardware execution

        Returns:
            Dict with execution results and visualization paths
        """
        logger.info(f"⚛️  Starting quantum execution for job {job_id}")
        start_time = datetime.utcnow()

        try:
            # Step 1: Optimize quantum configuration
            logger.info("🔧 Optimizing quantum parameters...")
            optimizer = AdaptiveQuantumOptimizer(
                budget_usd=budget_usd,
                max_time_hours=max_time_hours,
                accuracy_target=accuracy_target,
            )

            mol_type = MoleculeType(molecule_type)
            viz_type_enum = VisualizationType(viz_type)

            quantum_config = optimizer.optimize(
                molecule_data=molecule_data,
                molecule_type=mol_type,
                viz_type=viz_type_enum,
                backend_preference=backend_preference,
            )

            # Override shots if provided
            if shots:
                quantum_config.shots = shots

            # Get complexity metrics
            complexity = optimizer.estimate_molecular_complexity(molecule_data, mol_type)

            # Step 2: Map backend preference to backend type
            backend_type = self._get_backend_type(quantum_config.backend_type)

            # Step 3: Create quantum circuit with REAL VQE
            logger.info(f"🔬 Creating quantum circuit ({quantum_config.logical_qubits} qubits)...")
            circuit, vqe_metadata = self.backend_connector.create_molecular_circuit(
                num_qubits=quantum_config.logical_qubits,
                molecule_type=molecule_type,
                backend_type=backend_type,
                molecule_data=molecule_data,  # Pass molecule data for VQE
            )

            # Log VQE metadata if available
            if vqe_metadata:
                logger.info(f"📊 VQE Metadata captured from circuit creation:")
                logger.info(
                    f"   - Ground state energy: {vqe_metadata.get('energy_landscape', {}).get('ground_state_energy')} Hartree"
                )
                logger.info(f"   - Hamiltonian terms: {vqe_metadata.get('hamiltonian_terms')}")
                logger.info(f"   - Number of parameters: {vqe_metadata.get('num_parameters')}")
            else:
                logger.warning("⚠️  No VQE metadata available (using fallback circuit)")

            # Step 4: Execute on quantum backend
            logger.info(
                f"⚡ Executing on {backend_type.value} with {quantum_config.shots} shots..."
            )

            # Prepare molecule info for BioQL integration
            molecule_info = {
                "molecule_type": molecule_type,
                "molecule_data": molecule_data,
                "viz_type": viz_type,
                "smiles": molecule_data.get("smiles"),
                "protein_id": molecule_data.get("protein_id"),
                "num_qubits": quantum_config.logical_qubits,
            }

            quantum_result = await self.backend_connector.execute_circuit(
                circuit=circuit,
                backend_type=backend_type,
                shots=quantum_config.shots,
                job_id=job_id,
                api_key=api_key,
                molecule_info=molecule_info,
                vqe_metadata=vqe_metadata,  # Pass VQE metadata to execution
            )

            if quantum_result.status != "completed":
                raise Exception(f"Quantum execution failed: {quantum_result.error_message}")

            # Step 5: Generate visualizations with VQE metadata
            logger.info("📊 Generating visualizations...")

            # Extract VQE data from quantum result
            vqe_energies = None
            ground_state_energy = quantum_result.ground_state_energy
            energy_landscape_data = None
            hamiltonian_terms = quantum_result.hamiltonian_terms
            convergence_history = None

            if quantum_result.energy_landscape:
                energy_landscape_data = quantum_result.energy_landscape.get("energies", [])
                logger.info(
                    f"📊 Passing VQE energy landscape to visualizations ({len(energy_landscape_data) if energy_landscape_data else 0} points)"
                )

            if ground_state_energy:
                logger.info(
                    f"📊 Passing ground state energy to visualizations: {ground_state_energy:.4f} Hartree"
                )

            visualization_files = self.viz_generator.generate_from_quantum_results(
                job_id=job_id,
                counts=quantum_result.counts,
                num_qubits=quantum_config.logical_qubits,
                molecule_type=molecule_type,
                viz_type=viz_type,
                vqe_energies=vqe_energies,
                ground_state_energy=ground_state_energy,
                energy_landscape=energy_landscape_data,
                hamiltonian_terms=hamiltonian_terms,
                convergence_history=convergence_history,
            )

            # Step 6: Create report
            report_file = self.viz_generator.create_report_pdf(
                job_id=job_id,
                quantum_config={
                    "backend_type": quantum_config.backend_type,
                    "logical_qubits": quantum_config.logical_qubits,
                    "physical_qubits": quantum_config.physical_qubits,
                    "shots": quantum_config.shots,
                    "estimated_cost_usd": quantum_config.estimated_cost_usd,
                    "time_to_solution_hours": quantum_config.time_to_solution_hours,
                },
                results=quantum_result.__dict__,
                visualization_files=visualization_files,
            )

            visualization_files["report"] = report_file

            # Calculate total execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"✅ Job {job_id} completed successfully in {execution_time:.2f}s")

            return {
                "status": "completed",
                "job_id": job_id,
                "quantum_result": {
                    "backend": quantum_result.backend,
                    "counts": quantum_result.counts,
                    "execution_time": quantum_result.execution_time,
                    "cost_usd": quantum_result.cost_usd,
                },
                "quantum_config": {
                    "logical_qubits": quantum_config.logical_qubits,
                    "physical_qubits": quantum_config.physical_qubits,
                    "shots": quantum_config.shots,
                    "circuit_depth": quantum_config.circuit_depth,
                    "backend_type": quantum_config.backend_type,
                    "estimated_cost_usd": quantum_config.estimated_cost_usd,
                    "time_to_solution_hours": quantum_config.time_to_solution_hours,
                },
                "molecular_complexity": {
                    "num_atoms": complexity.num_atoms,
                    "num_heavy_atoms": complexity.num_heavy_atoms,
                    "num_electrons": complexity.num_electrons,
                    "molecular_weight": complexity.molecular_weight,
                    "conformational_space_size": complexity.conformational_space_size,
                },
                "visualization_files": visualization_files,
                "execution_metrics": {
                    "total_time_seconds": execution_time,
                    "accuracy": accuracy_target,
                    "total_cost_usd": quantum_result.cost_usd,
                },
                "completed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Job {job_id} failed: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

            return {
                "status": "failed",
                "job_id": job_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "failed_at": datetime.utcnow().isoformat(),
            }

    def _get_backend_type(self, backend_name: str) -> QuantumBackendType:
        """Map backend name to QuantumBackendType enum"""
        backend_map = {
            "ibm_torino": QuantumBackendType.IBM_TORINO,
            "ibm_brisbane": QuantumBackendType.IBM_BRISBANE,
            "ionq_simulator": QuantumBackendType.IONQ_SIMULATOR,
            "ionq_forte": QuantumBackendType.IONQ_FORTE,
            "ionq_qpu": QuantumBackendType.IONQ_QPU,
            "aws_sv1": QuantumBackendType.AWS_SV1,
            "aws_tn1": QuantumBackendType.AWS_TN1,
            "qiskit_simulator": QuantumBackendType.QISKIT_SIMULATOR,
        }

        # Default to simulator if not found
        return backend_map.get(backend_name, QuantumBackendType.QISKIT_SIMULATOR)
