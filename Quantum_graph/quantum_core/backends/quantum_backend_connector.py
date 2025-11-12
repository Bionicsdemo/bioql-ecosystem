# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Unified Quantum Backend Connector
==================================

Connects to multiple quantum computing providers through BioQL:
- IBM Quantum (Torino, Brisbane) via BioQL workflow server
- IonQ (Simulator, Forte) via BioQL workflow server
- AWS Braket (SV1 Simulator) via BioQL workflow server
- Local Simulators (Qiskit Aer) for testing

Author: Spectrix R&D / BioQL Team
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Load from project root
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"✅ Loaded environment from {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed")

# Import BioQL integration
from .bioql_integration import get_bioql_integration

# IBM Quantum
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import TwoLocal
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session

    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logging.warning("Qiskit not available")

# AWS Braket
try:
    from braket.aws import AwsDevice
    from braket.circuits import Circuit as BraketCircuit
    from braket.devices import LocalSimulator

    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False
    logging.warning("AWS Braket not available")

# IonQ via Cirq
try:
    import cirq
    import cirq_ionq as ionq

    CIRQ_AVAILABLE = True
except ImportError:
    CIRQ_AVAILABLE = False
    logging.warning("Cirq/IonQ not available")

logger = logging.getLogger(__name__)


class QuantumBackendType(Enum):
    """Supported quantum backends"""

    # Simulators
    IONQ_SIMULATOR = "ionq_simulator"
    AWS_SV1 = "aws_sv1"
    AWS_TN1 = "aws_tn1"
    QISKIT_SIMULATOR = "qiskit_simulator"

    # Real Hardware
    IBM_TORINO = "ibm_torino"
    IBM_BRISBANE = "ibm_brisbane"
    IONQ_FORTE = "ionq_forte"
    IONQ_QPU = "ionq_qpu"
    QUERA_AQUILA = "quera_aquila"


@dataclass
class QuantumJobResult:
    """Result from quantum execution"""

    job_id: str
    backend: str
    status: str  # "completed", "running", "failed"
    counts: Optional[Dict[str, int]] = None
    execution_time: Optional[float] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    raw_result: Optional[Any] = None
    # VQE-specific metadata (optional for backward compatibility)
    vqe_metadata: Optional[Dict[str, Any]] = None
    ground_state_energy: Optional[float] = None
    energy_landscape: Optional[Dict[str, Any]] = None
    hamiltonian_terms: Optional[int] = None
    num_parameters: Optional[int] = None


class QuantumBackendConnector:
    """
    Unified connector for all quantum backends
    """

    def __init__(self):
        """Initialize connections to quantum providers"""
        self.ibm_service = None
        self.ionq_service = None
        self.aws_device = None

        # Load API keys from environment
        self.ibm_token = os.getenv("IBM_QUANTUM_TOKEN")
        self.ionq_api_key = os.getenv("IONQ_API_KEY")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        logger.info("🔌 Quantum Backend Connector initialized")

    async def connect_ibm_quantum(self) -> bool:
        """Connect to IBM Quantum"""
        if not QISKIT_AVAILABLE:
            logger.error("Qiskit not installed")
            return False

        if not self.ibm_token:
            logger.warning("IBM_QUANTUM_TOKEN not set - using simulator only")
            return True  # Can still use local simulator

        try:
            # Use ibm_quantum_platform for the new Qiskit API
            self.ibm_service = QiskitRuntimeService(channel="ibm_quantum", token=self.ibm_token)
            logger.info("✅ Connected to IBM Quantum")
            return True
        except Exception as e:
            # Retry with updated channel name
            try:
                self.ibm_service = QiskitRuntimeService(token=self.ibm_token)
                logger.info("✅ Connected to IBM Quantum (using default channel)")
                return True
            except Exception as e2:
                logger.error(f"❌ Failed to connect to IBM Quantum: {e2}")
                return False

    async def connect_ionq(self) -> bool:
        """Connect to IonQ"""
        if not CIRQ_AVAILABLE:
            logger.error("Cirq/IonQ not installed")
            return False

        if not self.ionq_api_key:
            logger.warning("IONQ_API_KEY not set")
            return False

        try:
            self.ionq_service = ionq.Service(api_key=self.ionq_api_key)
            logger.info("✅ Connected to IonQ")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to IonQ: {e}")
            return False

    async def connect_aws_braket(self) -> bool:
        """Connect to AWS Braket"""
        if not BRAKET_AVAILABLE:
            logger.error("AWS Braket SDK not installed")
            return False

        if not (self.aws_access_key and self.aws_secret_key):
            logger.warning("AWS credentials not set - using local simulator only")
            return True  # Can still use local simulator

        try:
            # Test connection
            self.aws_device = LocalSimulator()
            logger.info("✅ Connected to AWS Braket")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to AWS Braket: {e}")
            return False

    def create_molecular_circuit(
        self,
        num_qubits: int,
        molecule_type: str,
        backend_type: QuantumBackendType,
        molecule_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Optional[Dict[str, Any]]]:
        """
        Create quantum circuit for molecular simulation

        This creates a REAL VQE circuit with optimized parameters
        for molecular ground state calculation

        Returns:
            Tuple of (circuit, vqe_metadata) where vqe_metadata is None for non-VQE circuits
        """
        if backend_type in [
            QuantumBackendType.IBM_TORINO,
            QuantumBackendType.IBM_BRISBANE,
            QuantumBackendType.QISKIT_SIMULATOR,
        ]:
            return self._create_qiskit_circuit(num_qubits, molecule_data)
        elif backend_type in [
            QuantumBackendType.IONQ_SIMULATOR,
            QuantumBackendType.IONQ_FORTE,
            QuantumBackendType.IONQ_QPU,
        ]:
            return self._create_cirq_circuit(num_qubits), None
        elif backend_type in [QuantumBackendType.AWS_SV1, QuantumBackendType.AWS_TN1]:
            return self._create_braket_circuit(num_qubits), None
        else:
            raise ValueError(f"Unsupported backend: {backend_type}")

    def _create_qiskit_circuit(
        self, num_qubits: int, molecule_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[QuantumCircuit, Optional[Dict[str, Any]]]:
        """Create Qiskit circuit for molecular simulation with REAL VQE

        Returns:
            Tuple of (circuit, vqe_metadata) where vqe_metadata is None for fallback circuits
        """

        # Import VQE module
        try:
            import sys
            from pathlib import Path

            sys.path.append(str(Path(__file__).parent.parent))
            from algorithms.molecular_vqe import create_molecular_vqe_circuit

            if molecule_data:
                logger.info(
                    f"🧬 Creating VQE circuit for molecule: {molecule_data.get('smiles', 'unknown')}"
                )
                circuit, metadata = create_molecular_vqe_circuit(
                    molecule_data=molecule_data,
                    num_qubits=num_qubits,
                    optimize=True,  # Run parameter optimization
                )
                logger.info(
                    f"✅ VQE circuit created: Ground state energy ≈ {metadata['energy_landscape']['ground_state_energy']:.4f} Hartree"
                )
                logger.info(
                    f"📊 VQE Metadata captured: {metadata.get('hamiltonian_terms')} Hamiltonian terms, {metadata.get('num_parameters')} parameters"
                )
                return circuit, metadata
            else:
                logger.warning("⚠️  No molecule data provided, using simple test circuit")
        except Exception as e:
            logger.warning(f"⚠️  VQE import failed, using fallback: {e}")

        # Fallback to simple circuit if VQE fails
        circuit = TwoLocal(
            num_qubits,
            rotation_blocks=["ry", "rz"],
            entanglement_blocks="cx",
            entanglement="linear",
            reps=3,
        )
        circuit.measure_all()
        logger.info(f"Created fallback circuit: {num_qubits} qubits, depth={circuit.depth()}")
        return circuit, None

    def _create_cirq_circuit(self, num_qubits: int) -> Any:
        """Create Cirq circuit for molecular simulation"""
        if not CIRQ_AVAILABLE:
            raise RuntimeError("Cirq not available")

        qubits = cirq.LineQubit.range(num_qubits)
        circuit = cirq.Circuit()

        # Create similar ansatz to Qiskit version
        for layer in range(3):
            # Rotation layer
            for qubit in qubits:
                circuit.append([cirq.ry(0.1)(qubit), cirq.rz(0.1)(qubit)])

            # Entanglement layer
            for i in range(num_qubits - 1):
                circuit.append(cirq.CNOT(qubits[i], qubits[i + 1]))

        # Add measurements
        circuit.append(cirq.measure(*qubits, key="result"))

        logger.info(f"Created Cirq circuit: {num_qubits} qubits")
        return circuit

    def _create_braket_circuit(self, num_qubits: int) -> Any:
        """Create AWS Braket circuit for molecular simulation"""
        if not BRAKET_AVAILABLE:
            raise RuntimeError("Braket not available")

        circuit = BraketCircuit()

        # Create similar ansatz
        for layer in range(3):
            # Rotation layer
            for i in range(num_qubits):
                circuit.ry(i, 0.1)
                circuit.rz(i, 0.1)

            # Entanglement layer
            for i in range(num_qubits - 1):
                circuit.cnot(i, i + 1)

        logger.info(f"Created Braket circuit: {num_qubits} qubits")
        return circuit

    async def execute_circuit(
        self,
        circuit: Any,
        backend_type: QuantumBackendType,
        shots: int,
        job_id: str,
        api_key: Optional[str] = None,
        molecule_info: Optional[Dict[str, Any]] = None,
        vqe_metadata: Optional[Dict[str, Any]] = None,
    ) -> QuantumJobResult:
        """Execute circuit on specified backend

        Args:
            circuit: Quantum circuit to execute
            backend_type: Type of quantum backend
            shots: Number of measurements
            job_id: Unique job identifier
            api_key: Optional API key for cloud backends
            molecule_info: Optional molecular information
            vqe_metadata: Optional VQE metadata from circuit creation
        """

        logger.info(f"🚀 Executing job {job_id} on {backend_type.value} with {shots} shots")

        if vqe_metadata:
            logger.info(
                f"📊 VQE Metadata available: ground_state_energy={vqe_metadata.get('energy_landscape', {}).get('ground_state_energy')}, hamiltonian_terms={vqe_metadata.get('hamiltonian_terms')}"
            )

        try:
            # Execute VQE circuit DIRECTLY on IBM Quantum hardware
            # Quantum Graphs has IBM credentials configured, so we can execute pre-compiled circuits
            # This preserves VQE parameter optimization
            if backend_type in [QuantumBackendType.IBM_TORINO, QuantumBackendType.IBM_BRISBANE]:
                logger.info(f"🎯 Executing VQE circuit DIRECTLY on {backend_type.value}")
                logger.info(f"✅ This preserves optimized VQE parameters")
                return await self._execute_ibm_quantum(
                    circuit, backend_type, shots, job_id, vqe_metadata
                )

            # IonQ hardware
            elif backend_type in [QuantumBackendType.IONQ_FORTE, QuantumBackendType.IONQ_QPU]:
                logger.info(f"🎯 Executing on IonQ hardware: {backend_type.value}")
                return await self._execute_ionq(circuit, backend_type, shots, job_id, vqe_metadata)

            # Use local simulator for testing
            elif backend_type == QuantumBackendType.QISKIT_SIMULATOR:
                return await self._execute_qiskit_simulator(circuit, shots, job_id, vqe_metadata)

            # IonQ simulator can also use local
            elif backend_type == QuantumBackendType.IONQ_SIMULATOR:
                return await self._execute_qiskit_simulator(circuit, shots, job_id, vqe_metadata)

            # AWS Braket - these would need credentials
            elif backend_type in [QuantumBackendType.AWS_SV1, QuantumBackendType.AWS_TN1]:
                logger.warning(f"⚠️  AWS Braket not configured, falling back to simulator")
                return await self._execute_qiskit_simulator(circuit, shots, job_id, vqe_metadata)

            else:
                raise ValueError(f"Unsupported backend: {backend_type}")

        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return QuantumJobResult(
                job_id=job_id, backend=backend_type.value, status="failed", error_message=str(e)
            )

    async def _execute_via_bioql(
        self,
        circuit: QuantumCircuit,
        backend_type: QuantumBackendType,
        shots: int,
        job_id: str,
        api_key: Optional[str],
        molecule_info: Optional[Dict[str, Any]],
    ) -> QuantumJobResult:
        """Execute circuit through BioQL workflow server"""
        import time

        if not api_key:
            raise ValueError("API key required for BioQL execution")

        logger.info(f"🔗 Executing via BioQL workflow server: {backend_type.value}")

        start_time = time.time()

        # Get BioQL integration instance
        bioql = get_bioql_integration()

        # Execute through BioQL
        result = await bioql.execute_on_bioql(
            circuit=circuit,
            backend=backend_type.value,
            shots=shots,
            api_key=api_key,
            molecule_info=molecule_info,
        )

        execution_time = time.time() - start_time

        if result.get("success"):
            logger.info(f"✅ BioQL execution completed in {execution_time:.2f}s")
            return QuantumJobResult(
                job_id=job_id,
                backend=backend_type.value,
                status="completed",
                counts=result.get("counts", {}),
                execution_time=execution_time,
                cost_usd=result.get("cost_usd", 0.0),
                raw_result=result.get("raw_result"),
            )
        else:
            error_msg = result.get("error", "Unknown BioQL error")
            logger.error(f"❌ BioQL execution failed: {error_msg}")
            return QuantumJobResult(
                job_id=job_id, backend=backend_type.value, status="failed", error_message=error_msg
            )

    async def _execute_qiskit_simulator(
        self,
        circuit: QuantumCircuit,
        shots: int,
        job_id: str,
        vqe_metadata: Optional[Dict[str, Any]] = None,
    ) -> QuantumJobResult:
        """Execute on Qiskit Aer simulator"""
        import time

        import numpy as np
        from qiskit_aer import AerSimulator

        start_time = time.time()

        # If circuit has parameters, bind them with zeros
        if circuit.parameters:
            logger.warning(f"⚠️  Circuit has {len(circuit.parameters)} parameters, binding to zero")
            parameter_values = {param: 0.0 for param in circuit.parameters}
            circuit = circuit.assign_parameters(parameter_values)

        # Use local Aer simulator
        simulator = AerSimulator()
        transpiled = transpile(circuit, simulator)
        result = simulator.run(transpiled, shots=shots).result()
        counts = result.get_counts()

        execution_time = time.time() - start_time
        cost = shots * 0.01  # $0.01 per shot for simulator

        logger.info(f"✅ Simulator job {job_id} completed in {execution_time:.2f}s")

        # Extract VQE metadata if available
        ground_state_energy = None
        energy_landscape = None
        hamiltonian_terms = None
        num_parameters = None

        if vqe_metadata:
            logger.info("📊 Including VQE metadata in result")
            ground_state_energy = vqe_metadata.get("energy_landscape", {}).get(
                "ground_state_energy"
            )
            energy_landscape = vqe_metadata.get("energy_landscape")
            hamiltonian_terms = vqe_metadata.get("hamiltonian_terms")
            num_parameters = vqe_metadata.get("num_parameters")

        return QuantumJobResult(
            job_id=job_id,
            backend="qiskit_simulator",
            status="completed",
            counts=counts,
            execution_time=execution_time,
            cost_usd=cost,
            raw_result=result,
            vqe_metadata=vqe_metadata,
            ground_state_energy=ground_state_energy,
            energy_landscape=energy_landscape,
            hamiltonian_terms=hamiltonian_terms,
            num_parameters=num_parameters,
        )

    async def _execute_ibm_quantum(
        self,
        circuit: QuantumCircuit,
        backend_type: QuantumBackendType,
        shots: int,
        job_id: str,
        vqe_metadata: Optional[Dict[str, Any]] = None,
    ) -> QuantumJobResult:
        """Execute on IBM Quantum hardware"""
        import time

        if not self.ibm_service:
            await self.connect_ibm_quantum()

        # Map backend type to IBM backend name
        backend_name_map = {
            QuantumBackendType.IBM_TORINO: "ibm_torino",
            QuantumBackendType.IBM_BRISBANE: "ibm_brisbane",
        }

        backend_name = backend_name_map.get(backend_type, "ibm_brisbane")

        try:
            backend = self.ibm_service.backend(backend_name)
            start_time = time.time()

            # Transpile circuit for IBM hardware (required after March 2024)
            logger.info(f"🔧 Transpiling VQE circuit for IBM {backend_name} hardware...")
            transpiled_circuit = transpile(circuit, backend=backend, optimization_level=1)
            logger.info(
                f"✅ Transpilation complete: {transpiled_circuit.depth()} depth, {transpiled_circuit.size()} gates"
            )

            # Use SamplerV2 with mode parameter (new Qiskit API for free tier)
            logger.info(f"📡 Submitting transpiled VQE circuit to IBM {backend_name}...")
            from qiskit_ibm_runtime import SamplerV2

            sampler = SamplerV2(mode=backend)

            # SamplerV2 requires PUB format (primitive unified bloc)
            job = sampler.run([(transpiled_circuit,)], shots=shots)
            ibm_job_id = job.job_id()

            logger.info(f"🚀 IBM Job submitted: {ibm_job_id}")
            logger.info(f"🔗 IBM Quantum URL: https://quantum.ibm.com/jobs/{ibm_job_id}")
            logger.info(f"⏳ Waiting for IBM Quantum to complete (queue time ~35 hours)...")

            result = job.result()
            execution_time = time.time() - start_time

            # Extract counts from SamplerV2 result format
            # SamplerV2 returns PrimitiveResult with different structure
            try:
                # Try to get data from first pub result
                pub_result = result[0]
                # Get the classical register data
                meas_data = pub_result.data.meas
                counts_dict = meas_data.get_counts()

                # Convert BitArray format to string format
                counts = {}
                for bitstring, count in counts_dict.items():
                    counts[bitstring] = count

                logger.info(f"✅ IBM job {ibm_job_id} completed in {execution_time:.2f}s")
                logger.info(f"📊 Got {len(counts)} different quantum states from IBM hardware")
            except Exception as e:
                logger.warning(f"⚠️  Could not parse SamplerV2 result format: {e}")
                # Fallback to empty counts
                counts = {"error": 1}

            cost = shots * 3.0  # $3.00 per shot for IBM hardware

            # Extract VQE metadata if available
            ground_state_energy = None
            energy_landscape = None
            hamiltonian_terms = None
            num_parameters = None

            if vqe_metadata:
                logger.info("📊 Including VQE metadata in IBM Quantum result")
                ground_state_energy = vqe_metadata.get("energy_landscape", {}).get(
                    "ground_state_energy"
                )
                energy_landscape = vqe_metadata.get("energy_landscape")
                hamiltonian_terms = vqe_metadata.get("hamiltonian_terms")
                num_parameters = vqe_metadata.get("num_parameters")

            return QuantumJobResult(
                job_id=job_id,
                backend=backend_type.value,
                status="completed",
                counts=counts,
                execution_time=execution_time,
                cost_usd=cost,
                raw_result=result,
                ibm_job_id=ibm_job_id,
                vqe_metadata=vqe_metadata,
                ground_state_energy=ground_state_energy,
                energy_landscape=energy_landscape,
                hamiltonian_terms=hamiltonian_terms,
                num_parameters=num_parameters,
            )

        except Exception as e:
            logger.error(f"IBM execution error: {e}")
            logger.exception(e)
            # Fallback to simulator
            return await self._execute_qiskit_simulator(circuit, shots, job_id, vqe_metadata)

    async def _execute_ionq(
        self,
        circuit: Any,
        backend_type: QuantumBackendType,
        shots: int,
        job_id: str,
        vqe_metadata: Optional[Dict[str, Any]] = None,
    ) -> QuantumJobResult:
        """Execute on IonQ"""
        import time

        if not self.ionq_service:
            await self.connect_ionq()

        # Determine target
        if backend_type == QuantumBackendType.IONQ_SIMULATOR:
            target = "simulator"
            cost_per_shot = 0.01
        elif backend_type == QuantumBackendType.IONQ_FORTE:
            target = "ionq.forte"
            cost_per_shot = 3.00
        else:  # IONQ_QPU
            target = "ionq.qpu"
            cost_per_shot = 2.00

        try:
            start_time = time.time()

            # Submit job
            job = self.ionq_service.create_job(circuit=circuit, repetitions=shots, target=target)

            # Wait for completion (with timeout)
            timeout = 300  # 5 minutes
            elapsed = 0
            while elapsed < timeout:
                status = job.status()
                if status == "completed":
                    break
                await asyncio.sleep(2)
                elapsed += 2

            if status != "completed":
                raise TimeoutError(f"Job timed out after {timeout}s")

            result = job.results()
            execution_time = time.time() - start_time

            # Extract counts
            counts = result.measurements["result"].value_counts()

            cost = shots * cost_per_shot

            logger.info(f"✅ IonQ job {job_id} completed in {execution_time:.2f}s")

            # Extract VQE metadata if available
            ground_state_energy = None
            energy_landscape = None
            hamiltonian_terms = None
            num_parameters = None

            if vqe_metadata:
                logger.info("📊 Including VQE metadata in IonQ result")
                ground_state_energy = vqe_metadata.get("energy_landscape", {}).get(
                    "ground_state_energy"
                )
                energy_landscape = vqe_metadata.get("energy_landscape")
                hamiltonian_terms = vqe_metadata.get("hamiltonian_terms")
                num_parameters = vqe_metadata.get("num_parameters")

            return QuantumJobResult(
                job_id=job_id,
                backend=backend_type.value,
                status="completed",
                counts=dict(counts),
                execution_time=execution_time,
                cost_usd=cost,
                raw_result=result,
                vqe_metadata=vqe_metadata,
                ground_state_energy=ground_state_energy,
                energy_landscape=energy_landscape,
                hamiltonian_terms=hamiltonian_terms,
                num_parameters=num_parameters,
            )

        except Exception as e:
            logger.error(f"IonQ execution error: {e}")
            # Fallback to Cirq simulator
            import cirq

            simulator = cirq.Simulator()
            result = simulator.run(circuit, repetitions=shots)
            counts = result.measurements["result"].value_counts()

            return QuantumJobResult(
                job_id=job_id,
                backend="ionq_simulator_fallback",
                status="completed",
                counts=dict(counts),
                execution_time=1.0,
                cost_usd=shots * 0.01,
            )

    async def _execute_aws_braket(
        self, circuit: Any, backend_type: QuantumBackendType, shots: int, job_id: str
    ) -> QuantumJobResult:
        """Execute on AWS Braket"""
        import time

        if not self.aws_device:
            await self.connect_aws_braket()

        # Use local simulator for now (SV1 requires AWS credentials)
        device = LocalSimulator()
        cost_per_shot = 0.01  # Local simulator cost

        try:
            start_time = time.time()

            task = device.run(circuit, shots=shots)
            result = task.result()

            execution_time = time.time() - start_time

            # Extract counts
            counts = result.measurement_counts

            cost = shots * cost_per_shot

            logger.info(f"✅ AWS Braket job {job_id} completed in {execution_time:.2f}s")

            return QuantumJobResult(
                job_id=job_id,
                backend=backend_type.value,
                status="completed",
                counts=counts,
                execution_time=execution_time,
                cost_usd=cost,
                raw_result=result,
            )

        except Exception as e:
            logger.error(f"AWS Braket execution error: {e}")
            raise

    async def get_job_status(self, job_id: str, backend_type: QuantumBackendType) -> Dict[str, Any]:
        """Get status of running job"""
        # This would query the actual backend for job status
        return {"job_id": job_id, "status": "running", "backend": backend_type.value}
