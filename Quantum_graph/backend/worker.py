# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Background Worker for Quantum Job Processing
=============================================

Processes quantum computation jobs from the job queue asynchronously.

Features:
- Polls for pending jobs
- Executes quantum circuits using quantum_viz_engine
- Updates job status in real-time
- Error handling and automatic retry logic
- Graceful shutdown support
- Can run as separate process or daemon

Author: Spectrix R&D / BioQL Team
"""

import json
import logging
import signal
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.job_queue import JobQueue, JobStatus
from quantum_core.optimizers.adaptive_quantum_optimizer import (
    AdaptiveQuantumOptimizer,
    VisualizationType,
)
from visualization.quantum_viz_engine import (
    Atom,
    Bond,
    MolecularStructure,
    MoleculeType,
    QuantumVizEngine,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("worker.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class QuantumWorker:
    """
    Background worker for processing quantum computation jobs
    """

    def __init__(
        self,
        job_queue: Optional[JobQueue] = None,
        poll_interval: float = 5.0,
        max_concurrent_jobs: int = 1,
    ):
        """
        Initialize quantum worker

        Args:
            job_queue: JobQueue instance (creates new if None)
            poll_interval: Seconds between polling for new jobs
            max_concurrent_jobs: Maximum number of concurrent jobs (currently only 1 supported)
        """
        self.job_queue = job_queue if job_queue else JobQueue()
        self.poll_interval = poll_interval
        self.max_concurrent_jobs = max_concurrent_jobs

        # Initialize quantum components
        self.optimizer = AdaptiveQuantumOptimizer()
        self.viz_engine = QuantumVizEngine(self.optimizer)

        # Worker state
        self.running = False
        self.current_job_id = None
        self._shutdown_event = threading.Event()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        self.stop()

    def start(self):
        """
        Start the worker process

        Continuously polls for pending jobs and processes them.
        """
        self.running = True
        logger.info("🚀 Quantum Worker started")
        logger.info(f"📊 Poll interval: {self.poll_interval}s")
        logger.info(f"⚡ Max concurrent jobs: {self.max_concurrent_jobs}")

        while self.running:
            try:
                # Check for pending jobs
                pending_jobs = self.job_queue.get_pending_jobs(limit=self.max_concurrent_jobs)

                if pending_jobs:
                    for job_data in pending_jobs:
                        if not self.running:
                            break
                        self._process_job(job_data)
                else:
                    # No jobs - wait before polling again
                    if self._shutdown_event.wait(timeout=self.poll_interval):
                        # Shutdown event was set
                        break

            except Exception as e:
                logger.error(f"❌ Error in worker main loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(self.poll_interval)

        logger.info("🛑 Quantum Worker stopped")

    def stop(self):
        """
        Stop the worker gracefully
        """
        logger.info("🛑 Stopping worker...")
        self.running = False
        self._shutdown_event.set()

    def _process_job(self, job_data: Dict[str, Any]):
        """
        Process a single job

        Args:
            job_data: Job data from queue
        """
        job_id = job_data["id"]
        self.current_job_id = job_id

        logger.info(f"🔬 Processing job {job_id}")

        try:
            # Update status to RUNNING
            self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=0.0)

            # Parse molecule data
            molecule_data = job_data["molecule_data"]
            backend = job_data["backend"]
            shots = job_data["shots"]
            molecule_type = job_data["molecule_type"]

            # Execute quantum computation
            result = self._execute_quantum_computation(
                job_id=job_id,
                molecule_data=molecule_data,
                backend=backend,
                shots=shots,
                molecule_type=molecule_type,
            )

            # Update job with results
            self.job_queue.update_job_status(
                job_id, JobStatus.COMPLETED, result_data=result, progress=100.0
            )

            logger.info(f"✅ Job {job_id} completed successfully")
            logger.info(f"   Cost: ${result.get('cost', 0.0):.2f}")
            logger.info(f"   Execution time: {result.get('execution_time_seconds', 0):.1f}s")

        except Exception as e:
            error_message = f"Job execution failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"❌ Job {job_id} failed: {e}")
            logger.error(traceback.format_exc())

            # Try to retry or mark as failed
            retry_count = job_data.get("retry_count", 0)
            if self.job_queue.increment_retry_count(job_id):
                logger.info(f"🔄 Job {job_id} will be retried (attempt {retry_count + 2})")
            else:
                self.job_queue.update_job_status(
                    job_id, JobStatus.FAILED, error_message=error_message
                )
                logger.error(f"💀 Job {job_id} failed permanently after retries")

        finally:
            self.current_job_id = None

    def _execute_quantum_computation(
        self,
        job_id: str,
        molecule_data: Dict[str, Any],
        backend: str,
        shots: int,
        molecule_type: str,
    ) -> Dict[str, Any]:
        """
        Execute the actual quantum computation

        Args:
            job_id: Job identifier
            molecule_data: Molecular structure data
            backend: Quantum backend to use
            shots: Number of circuit shots
            molecule_type: Type of molecule

        Returns:
            dict: Computation results
        """
        start_time = time.time()

        # Update progress
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=10.0)

        # Create molecular structure from data
        structure = self._create_molecular_structure(molecule_data, molecule_type)

        # Update progress
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=20.0)

        # Optimize quantum parameters
        mol_type = MoleculeType(molecule_type.upper())
        config = self.optimizer.optimize(
            molecule_data=molecule_data,
            molecule_type=mol_type,
            viz_type=VisualizationType.CONFORMATIONAL_SAMPLING,
            backend_preference=backend,
        )

        logger.info(f"⚛️  Quantum Config for {job_id}:")
        logger.info(f"   Logical qubits: {config.logical_qubits}")
        logger.info(f"   Physical qubits: {config.physical_qubits}")
        logger.info(f"   Shots: {shots}")
        logger.info(f"   Backend: {config.backend_type}")
        logger.info(f"   Estimated cost: ${config.estimated_cost_usd:.2f}")

        # Update progress
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=30.0)

        # Run quantum conformational sampling
        num_conformations = molecule_data.get("num_conformations", 10)
        quantum_result = self.viz_engine.quantum_conformation_sampling(
            structure=structure, num_conformations=num_conformations
        )

        # Update progress
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=60.0)

        # Generate visualizations
        results_dir = self.job_queue.results_dir / job_id
        results_dir.mkdir(exist_ok=True, parents=True)

        # 3D structure visualization
        structure_file = results_dir / f"{structure.name}_3d.png"
        self.viz_engine.visualize_3d_structure(structure, str(structure_file))

        # Update progress
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=80.0)

        # Energy landscape visualization
        energy_file = results_dir / f"{structure.name}_energy.png"
        self.viz_engine.visualize_energy_landscape(quantum_result, str(energy_file))

        # Update progress
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING, progress=90.0)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Prepare result data
        result = {
            "job_id": job_id,
            "status": "completed",
            "structure_name": structure.name,
            "molecule_type": molecule_type,
            "num_atoms": len(structure.atoms),
            "num_conformations": len(quantum_result.conformations),
            "ground_state_energy": quantum_result.energy,
            "visualization_files": {
                "3d_structure": str(structure_file),
                "energy_landscape": str(energy_file),
            },
            "quantum_config": {
                "logical_qubits": config.logical_qubits,
                "physical_qubits": config.physical_qubits,
                "shots": shots,
                "backend": config.backend_type,
                "circuit_depth": config.circuit_depth,
                "qec_code": config.qec_code,
            },
            "cost": config.estimated_cost_usd,
            "execution_time_seconds": execution_time,
            "probabilities": quantum_result.probabilities,
        }

        return result

    def _create_molecular_structure(
        self, molecule_data: Dict[str, Any], molecule_type: str
    ) -> MolecularStructure:
        """
        Create MolecularStructure from job data

        Args:
            molecule_data: Molecular data
            molecule_type: Type of molecule

        Returns:
            MolecularStructure object
        """
        # Check if explicit structure is provided
        if "atoms" in molecule_data and "bonds" in molecule_data:
            atoms = [Atom(**atom_data) for atom_data in molecule_data["atoms"]]
            bonds = [Bond(**bond_data) for bond_data in molecule_data["bonds"]]
        else:
            # Generate structure from basic parameters
            atoms, bonds = self._generate_structure_from_params(molecule_data)

        mol_type = MoleculeType(molecule_type.upper())
        name = molecule_data.get("name", f"{molecule_type}_{len(atoms)}_atoms")

        return MolecularStructure(
            atoms=atoms, bonds=bonds, name=name, molecule_type=mol_type, metadata=molecule_data
        )

    def _generate_structure_from_params(self, params: Dict[str, Any]) -> tuple:
        """
        Generate simple molecular structure from parameters

        Args:
            params: Parameters including num_atoms

        Returns:
            tuple: (atoms, bonds)
        """
        import numpy as np

        num_atoms = params.get("num_atoms", 10)
        num_bonds = params.get("num_bonds", max(1, num_atoms - 1))

        atoms = []
        bonds = []

        # Generate atoms in a simple chain or helix pattern
        elements = ["C", "N", "O", "H"]

        for i in range(num_atoms):
            # Helix-like pattern
            angle = i * 60 * (np.pi / 180)
            radius = 2.0
            rise = 1.5

            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = i * rise

            element = elements[i % len(elements)]

            atoms.append(Atom(element=element, x=x, y=y, z=z, atom_id=i))

        # Generate bonds between consecutive atoms
        for i in range(min(num_bonds, num_atoms - 1)):
            bonds.append(Bond(atom1_id=i, atom2_id=i + 1, order=1.0))

        return atoms, bonds

    def get_status(self) -> Dict[str, Any]:
        """
        Get current worker status

        Returns:
            dict: Worker status information
        """
        return {
            "running": self.running,
            "current_job_id": self.current_job_id,
            "poll_interval": self.poll_interval,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "queue_statistics": self.job_queue.get_statistics(),
        }


def run_worker(poll_interval: float = 5.0):
    """
    Run the worker as a standalone process

    Args:
        poll_interval: Seconds between polling for jobs
    """
    logger.info("=" * 80)
    logger.info("🔬 QUANTUM COMPUTATION WORKER")
    logger.info("=" * 80)

    worker = QuantumWorker(poll_interval=poll_interval)

    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("\n⌨️  Keyboard interrupt received")
        worker.stop()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error(traceback.format_exc())
        worker.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quantum Job Queue Worker")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Polling interval in seconds (default: 5.0)",
    )

    args = parser.parse_args()

    run_worker(poll_interval=args.poll_interval)
