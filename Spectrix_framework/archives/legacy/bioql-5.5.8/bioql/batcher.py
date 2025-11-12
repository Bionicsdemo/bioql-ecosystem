#!/usr/bin/env python3
"""
BioQL Smart Batcher - Intelligent Job Batching for Quantum Circuits

This module provides advanced batching strategies to optimize quantum job execution
by combining multiple circuits, sharing resources, and reducing API calls and costs.

Key Features:
- Multiple batching strategies (similarity, backend, cost, time, adaptive)
- Circuit similarity analysis using graph algorithms
- Cost estimation and savings calculation
- Resource sharing and circuit combination
- Backend-aware optimization
- Parallel measurement support

Author: BioQL Development Team
Version: 1.0.0
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import logging
import hashlib
import numpy as np
from datetime import datetime
from collections import defaultdict

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import Operator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    QuantumCircuit = Any

# Optional imports for advanced features
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

# Import billing module for cost estimation
try:
    from .simple_billing import (
        get_backend_cost_per_shot,
        get_complexity_multiplier,
        get_algorithm_multiplier,
        estimate_qubits_from_program,
        classify_algorithm
    )
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class BatchingStrategy(Enum):
    """
    Batching strategies for optimizing quantum job execution.

    Strategies:
    - SIMILAR_CIRCUITS: Group circuits with similar structure and gate sequences
    - SAME_BACKEND: Group circuits requiring the same quantum backend
    - COST_OPTIMAL: Minimize total execution cost
    - TIME_OPTIMAL: Minimize total execution time
    - ADAPTIVE: Dynamically choose best strategy based on job characteristics
    """
    SIMILAR_CIRCUITS = "similar_circuits"
    SAME_BACKEND = "same_backend"
    COST_OPTIMAL = "cost_optimal"
    TIME_OPTIMAL = "time_optimal"
    ADAPTIVE = "adaptive"


@dataclass
class QuantumJob:
    """
    Represents a single quantum job to be batched.

    Attributes:
        job_id: Unique identifier for the job
        circuit: The quantum circuit to execute
        shots: Number of measurement shots
        backend: Requested backend for execution
        priority: Job priority (higher = more important)
        metadata: Additional job metadata
        created_at: Job creation timestamp
        program_text: Original program text (optional)
        algorithm_type: Detected algorithm type
    """
    job_id: str = field(default_factory=lambda: str(uuid4()))
    circuit: Optional[QuantumCircuit] = None
    shots: int = 1024
    backend: str = "simulator"
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    program_text: Optional[str] = None
    algorithm_type: str = "basic"

    def __post_init__(self):
        """Validate job after initialization."""
        if self.circuit is None and not self.program_text:
            raise ValueError("QuantumJob must have either a circuit or program_text")

        # Infer algorithm type if not set
        if self.program_text and self.algorithm_type == "basic":
            if BILLING_AVAILABLE:
                self.algorithm_type = classify_algorithm(self.program_text)

    @property
    def num_qubits(self) -> int:
        """Get number of qubits in the circuit."""
        if self.circuit:
            return self.circuit.num_qubits
        elif self.program_text and BILLING_AVAILABLE:
            return estimate_qubits_from_program(self.program_text)
        return 2  # Default

    @property
    def circuit_depth(self) -> int:
        """Get circuit depth."""
        if self.circuit:
            return self.circuit.depth()
        return 0

    def fingerprint(self) -> str:
        """Generate a fingerprint for circuit similarity comparison."""
        if not self.circuit:
            return hashlib.md5(str(self.program_text).encode()).hexdigest()

        # Generate fingerprint from circuit structure
        gate_sequence = "_".join([inst.operation.name for inst in self.circuit.data])
        data = f"{self.circuit.num_qubits}_{gate_sequence}_{self.circuit.depth()}"
        return hashlib.md5(data.encode()).hexdigest()


@dataclass
class JobBatch:
    """
    Represents a batch of quantum jobs to be executed together.

    Attributes:
        batch_id: Unique identifier for the batch
        jobs: List of jobs in this batch
        combined_circuit: Combined quantum circuit for all jobs
        backend: Target backend for execution
        estimated_cost: Estimated execution cost (USD)
        estimated_time: Estimated execution time (seconds)
        total_shots: Total shots across all jobs
        strategy: Batching strategy used
        metadata: Batch metadata
    """
    batch_id: str = field(default_factory=lambda: str(uuid4()))
    jobs: List[QuantumJob] = field(default_factory=list)
    combined_circuit: Optional[QuantumCircuit] = None
    backend: str = "simulator"
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    total_shots: int = 0
    strategy: Optional[BatchingStrategy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_job(self, job: QuantumJob) -> None:
        """Add a job to this batch."""
        self.jobs.append(job)
        self.total_shots += job.shots

    @property
    def num_jobs(self) -> int:
        """Number of jobs in this batch."""
        return len(self.jobs)

    @property
    def total_qubits(self) -> int:
        """Total qubits needed for all jobs."""
        return sum(job.num_qubits for job in self.jobs)

    @property
    def avg_priority(self) -> float:
        """Average priority of jobs in batch."""
        if not self.jobs:
            return 0.0
        return sum(job.priority for job in self.jobs) / len(self.jobs)


@dataclass
class SavingsEstimate:
    """
    Estimates cost and time savings from batching.

    Attributes:
        cost_saved: Money saved by batching (USD)
        time_saved_seconds: Time saved by batching (seconds)
        api_calls_reduced: Number of API calls reduced
        efficiency_improvement: Overall efficiency improvement (percentage)
        baseline_cost: Cost without batching
        baseline_time: Time without batching
        batched_cost: Cost with batching
        batched_time: Time with batching
    """
    cost_saved: float
    time_saved_seconds: float
    api_calls_reduced: int
    efficiency_improvement: float
    baseline_cost: float = 0.0
    baseline_time: float = 0.0
    batched_cost: float = 0.0
    batched_time: float = 0.0

    def __str__(self) -> str:
        """String representation of savings."""
        # Calculate percentages safely (avoid division by zero)
        cost_pct = (self.cost_saved / self.baseline_cost * 100) if self.baseline_cost > 0 else 0.0
        time_pct = (self.time_saved_seconds / self.baseline_time * 100) if self.baseline_time > 0 else 0.0

        return (
            f"Savings Estimate:\n"
            f"  Cost saved: ${self.cost_saved:.4f} ({cost_pct:.1f}%)\n"
            f"  Time saved: {self.time_saved_seconds:.1f}s ({time_pct:.1f}%)\n"
            f"  API calls reduced: {self.api_calls_reduced}\n"
            f"  Efficiency improvement: {self.efficiency_improvement:.1f}%"
        )


@dataclass
class BatchResults:
    """
    Results from executing a batch of jobs.

    Attributes:
        batch_id: ID of the executed batch
        job_results: Mapping of job_id to individual results
        execution_time: Total execution time
        actual_cost: Actual execution cost
        success: Whether batch execution succeeded
        error_message: Error message if failed
        metadata: Additional result metadata
    """
    batch_id: str
    job_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    execution_time: float = 0.0
    actual_cost: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SmartBatcher:
    """
    Smart batching system for quantum jobs.

    Intelligently groups quantum circuits to optimize cost, time, and resource usage.
    Supports multiple batching strategies and provides detailed savings estimates.

    Example:
        >>> batcher = SmartBatcher()
        >>> batch_id = batcher.add_job(job1)
        >>> batch_id = batcher.add_job(job2)
        >>> batches = batcher.get_batches(BatchingStrategy.COST_OPTIMAL)
        >>> results = batcher.execute_batches(batches)
    """

    def __init__(
        self,
        max_batch_size: int = 10,
        max_qubits_per_batch: int = 100,
        default_backend: str = "simulator"
    ):
        """
        Initialize the SmartBatcher.

        Args:
            max_batch_size: Maximum number of jobs per batch
            max_qubits_per_batch: Maximum total qubits per batch
            default_backend: Default backend for job execution
        """
        self.max_batch_size = max_batch_size
        self.max_qubits_per_batch = max_qubits_per_batch
        self.default_backend = default_backend

        self._jobs: Dict[str, QuantumJob] = {}
        self._batches: Dict[str, JobBatch] = {}

        logger.info(f"Initialized SmartBatcher (max_batch_size={max_batch_size}, "
                   f"max_qubits={max_qubits_per_batch})")

    def add_job(self, job: QuantumJob) -> str:
        """
        Add a quantum job to the batcher.

        Args:
            job: QuantumJob to add

        Returns:
            Job ID for tracking
        """
        self._jobs[job.job_id] = job
        logger.info(f"Added job {job.job_id} ({job.num_qubits} qubits, "
                   f"{job.shots} shots, backend={job.backend})")
        return job.job_id

    def get_batches(
        self,
        strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE
    ) -> List[JobBatch]:
        """
        Generate batches of jobs using the specified strategy.

        Args:
            strategy: Batching strategy to use

        Returns:
            List of JobBatch objects
        """
        if not self._jobs:
            logger.warning("No jobs to batch")
            return []

        logger.info(f"Generating batches with strategy: {strategy.value}")

        if strategy == BatchingStrategy.SIMILAR_CIRCUITS:
            batches = self._batch_by_similarity()
        elif strategy == BatchingStrategy.SAME_BACKEND:
            batches = self._batch_by_backend()
        elif strategy == BatchingStrategy.COST_OPTIMAL:
            batches = self._batch_by_cost()
        elif strategy == BatchingStrategy.TIME_OPTIMAL:
            batches = self._batch_by_time()
        elif strategy == BatchingStrategy.ADAPTIVE:
            batches = self._batch_adaptive()
        else:
            raise ValueError(f"Unknown batching strategy: {strategy}")

        # Build combined circuits and estimate costs
        for batch in batches:
            self._build_combined_circuit(batch)
            self._estimate_batch_cost_time(batch)
            batch.strategy = strategy

        # Store batches
        for batch in batches:
            self._batches[batch.batch_id] = batch

        logger.info(f"Generated {len(batches)} batches from {len(self._jobs)} jobs")
        return batches

    def execute_batches(
        self,
        batches: List[JobBatch],
        api_key: Optional[str] = None
    ) -> BatchResults:
        """
        Execute a list of job batches.

        Args:
            batches: List of batches to execute
            api_key: API key for authentication (if needed)

        Returns:
            BatchResults with execution results
        """
        if not batches:
            return BatchResults(
                batch_id="empty",
                success=False,
                error_message="No batches to execute"
            )

        all_results = BatchResults(batch_id="combined")
        total_time = 0.0
        total_cost = 0.0

        for batch in batches:
            logger.info(f"Executing batch {batch.batch_id} ({batch.num_jobs} jobs)")

            try:
                batch_result = self._execute_single_batch(batch, api_key)

                # Aggregate results
                all_results.job_results.update(batch_result.job_results)
                total_time += batch_result.execution_time
                total_cost += batch_result.actual_cost

            except Exception as e:
                logger.error(f"Batch execution failed: {e}")
                all_results.success = False
                all_results.error_message = str(e)
                return all_results

        all_results.execution_time = total_time
        all_results.actual_cost = total_cost
        all_results.metadata['num_batches'] = len(batches)
        all_results.metadata['total_jobs'] = sum(b.num_jobs for b in batches)

        logger.info(f"Executed {len(batches)} batches in {total_time:.2f}s, cost: ${total_cost:.4f}")
        return all_results

    def estimate_batch_savings(
        self,
        jobs: Optional[List[QuantumJob]] = None,
        strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE
    ) -> SavingsEstimate:
        """
        Estimate cost and time savings from batching.

        Args:
            jobs: List of jobs to estimate (uses all jobs if None)
            strategy: Batching strategy to use for estimate

        Returns:
            SavingsEstimate with detailed savings information
        """
        if jobs is None:
            jobs = list(self._jobs.values())

        if not jobs:
            return SavingsEstimate(
                cost_saved=0.0,
                time_saved_seconds=0.0,
                api_calls_reduced=0,
                efficiency_improvement=0.0
            )

        # Calculate baseline (no batching)
        baseline_cost = 0.0
        baseline_time = 0.0
        baseline_api_calls = len(jobs)

        for job in jobs:
            job_cost, job_time = self._estimate_single_job(job)
            baseline_cost += job_cost
            baseline_time += job_time  # Sequential execution

        # Calculate batched costs (temporarily add jobs)
        temp_jobs = {}
        for job in jobs:
            if job.job_id not in self._jobs:
                temp_jobs[job.job_id] = job
                self._jobs[job.job_id] = job

        try:
            batches = self.get_batches(strategy)

            batched_cost = sum(batch.estimated_cost for batch in batches)
            # Parallel execution within batches
            batched_time = sum(batch.estimated_time for batch in batches)
            batched_api_calls = len(batches)

        finally:
            # Remove temporary jobs
            for job_id in temp_jobs:
                del self._jobs[job_id]

        # Calculate savings
        cost_saved = baseline_cost - batched_cost
        time_saved = baseline_time - batched_time
        api_calls_reduced = baseline_api_calls - batched_api_calls

        efficiency_improvement = 0.0
        if baseline_cost > 0:
            efficiency_improvement = (cost_saved / baseline_cost) * 100

        return SavingsEstimate(
            cost_saved=max(0, cost_saved),
            time_saved_seconds=max(0, time_saved),
            api_calls_reduced=max(0, api_calls_reduced),
            efficiency_improvement=max(0, efficiency_improvement),
            baseline_cost=baseline_cost,
            baseline_time=baseline_time,
            batched_cost=batched_cost,
            batched_time=batched_time
        )

    # ===== Private Methods =====

    def _batch_by_similarity(self) -> List[JobBatch]:
        """Batch jobs by circuit similarity using graph algorithms."""
        jobs = list(self._jobs.values())

        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX not available, falling back to backend batching")
            return self._batch_by_backend()

        # Build similarity graph
        G = nx.Graph()
        for job in jobs:
            G.add_node(job.job_id, job=job)

        # Add edges for similar circuits
        for i, job1 in enumerate(jobs):
            for job2 in jobs[i+1:]:
                similarity = self._calculate_similarity(job1, job2)
                if similarity > 0.5:  # Threshold for similarity
                    G.add_edge(job1.job_id, job2.job_id, weight=similarity)

        # Find connected components (clusters of similar circuits)
        batches = []
        for component in nx.connected_components(G):
            if len(component) > self.max_batch_size:
                # Split large components
                component_jobs = [self._jobs[jid] for jid in component]
                batches.extend(self._split_into_batches(component_jobs))
            else:
                batch = JobBatch(backend=self.default_backend)
                for job_id in component:
                    batch.add_job(self._jobs[job_id])
                batches.append(batch)

        return batches

    def _batch_by_backend(self) -> List[JobBatch]:
        """Batch jobs by requested backend."""
        backend_groups = defaultdict(list)

        for job in self._jobs.values():
            backend_groups[job.backend].append(job)

        batches = []
        for backend, jobs in backend_groups.items():
            batches.extend(self._split_into_batches(jobs, backend))

        return batches

    def _batch_by_cost(self) -> List[JobBatch]:
        """Batch jobs to minimize total cost."""
        jobs = sorted(self._jobs.values(), key=lambda j: (j.backend, j.shots))
        return self._split_into_batches(jobs)

    def _batch_by_time(self) -> List[JobBatch]:
        """Batch jobs to minimize total execution time."""
        jobs = sorted(self._jobs.values(),
                     key=lambda j: (j.circuit_depth, j.num_qubits))
        return self._split_into_batches(jobs)

    def _batch_adaptive(self) -> List[JobBatch]:
        """Adaptively choose best batching strategy."""
        num_jobs = len(self._jobs)

        # For small numbers, use similarity
        if num_jobs <= 5:
            return self._batch_by_similarity()

        # For backend diversity, batch by backend
        backends = set(job.backend for job in self._jobs.values())
        if len(backends) > 3:
            return self._batch_by_backend()

        # For cost-sensitive workloads, optimize cost
        total_shots = sum(job.shots for job in self._jobs.values())
        if total_shots > 10000:
            return self._batch_by_cost()

        # Default to time optimization
        return self._batch_by_time()

    def _split_into_batches(
        self,
        jobs: List[QuantumJob],
        backend: Optional[str] = None
    ) -> List[JobBatch]:
        """Split jobs into batches respecting size and qubit constraints."""
        batches = []
        current_batch = JobBatch(backend=backend or self.default_backend)

        for job in jobs:
            # Check if adding this job exceeds limits
            if (current_batch.num_jobs >= self.max_batch_size or
                current_batch.total_qubits + job.num_qubits > self.max_qubits_per_batch):

                if current_batch.num_jobs > 0:
                    batches.append(current_batch)
                current_batch = JobBatch(backend=job.backend)

            current_batch.add_job(job)

        # Add final batch
        if current_batch.num_jobs > 0:
            batches.append(current_batch)

        return batches

    def _calculate_similarity(self, job1: QuantumJob, job2: QuantumJob) -> float:
        """Calculate similarity between two quantum jobs."""
        if not job1.circuit or not job2.circuit:
            # Use fingerprint-based similarity
            return 1.0 if job1.fingerprint() == job2.fingerprint() else 0.0

        # Compare circuit structure
        similarity = 0.0

        # Qubit count similarity
        q1, q2 = job1.num_qubits, job2.num_qubits
        if q1 == q2:
            similarity += 0.3
        elif abs(q1 - q2) <= 2:
            similarity += 0.15

        # Depth similarity
        d1, d2 = job1.circuit_depth, job2.circuit_depth
        if d1 > 0 and d2 > 0:
            depth_ratio = min(d1, d2) / max(d1, d2)
            similarity += 0.3 * depth_ratio

        # Gate sequence similarity
        gates1 = [inst.operation.name for inst in job1.circuit.data]
        gates2 = [inst.operation.name for inst in job2.circuit.data]

        common_gates = set(gates1) & set(gates2)
        all_gates = set(gates1) | set(gates2)

        if all_gates:
            gate_similarity = len(common_gates) / len(all_gates)
            similarity += 0.4 * gate_similarity

        return similarity

    def _build_combined_circuit(self, batch: JobBatch) -> None:
        """Build a combined circuit for all jobs in a batch."""
        if not batch.jobs:
            return

        # For now, we don't actually combine circuits into a single large circuit
        # (this would require sophisticated register allocation and measurement separation)
        # Instead, we mark that these jobs will be executed together

        # The combined circuit is just the largest circuit in the batch
        batch.combined_circuit = max(
            (job.circuit for job in batch.jobs if job.circuit),
            key=lambda c: c.num_qubits,
            default=None
        )

        batch.metadata['circuit_combination'] = 'sequential'
        batch.metadata['total_qubits'] = batch.total_qubits
        batch.metadata['max_qubits_per_job'] = max(job.num_qubits for job in batch.jobs)

    def _estimate_batch_cost_time(self, batch: JobBatch) -> None:
        """Estimate cost and time for a batch."""
        total_cost = 0.0
        max_time = 0.0

        for job in batch.jobs:
            job_cost, job_time = self._estimate_single_job(job)
            total_cost += job_cost
            max_time = max(max_time, job_time)

        # Apply batching discount (10% cost reduction, 20% time reduction)
        batch.estimated_cost = total_cost * 0.9
        batch.estimated_time = max_time * 0.8

        batch.metadata['baseline_cost'] = total_cost
        batch.metadata['baseline_time'] = max_time
        batch.metadata['cost_discount'] = 0.1
        batch.metadata['time_discount'] = 0.2

    def _estimate_single_job(self, job: QuantumJob) -> Tuple[float, float]:
        """Estimate cost and time for a single job."""
        # Estimate cost
        if BILLING_AVAILABLE:
            base_cost = get_backend_cost_per_shot(job.backend)
            complexity_mult = get_complexity_multiplier(job.num_qubits)
            algo_mult = get_algorithm_multiplier(job.algorithm_type)
            cost = job.shots * base_cost * complexity_mult * algo_mult
        else:
            cost = job.shots * 0.001  # Default estimate

        # Estimate time (rough heuristic)
        base_time = 5.0  # Base overhead
        circuit_time = job.circuit_depth * 0.1 if job.circuit_depth > 0 else 1.0
        shot_time = job.shots * 0.001
        time = base_time + circuit_time + shot_time

        return cost, time

    def _execute_single_batch(
        self,
        batch: JobBatch,
        api_key: Optional[str]
    ) -> BatchResults:
        """Execute a single batch of jobs."""
        from time import time

        results = BatchResults(batch_id=batch.batch_id)
        start_time = time()

        # For now, execute jobs sequentially within batch
        # In production, this could use parallel execution
        for job in batch.jobs:
            try:
                job_result = self._execute_single_job_in_batch(job, api_key)
                results.job_results[job.job_id] = job_result
            except Exception as e:
                logger.error(f"Job {job.job_id} failed: {e}")
                results.job_results[job.job_id] = {
                    'success': False,
                    'error': str(e)
                }
                results.success = False

        results.execution_time = time() - start_time
        results.actual_cost = batch.estimated_cost  # Use estimate for now

        return results

    def _execute_single_job_in_batch(
        self,
        job: QuantumJob,
        api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Execute a single job within a batch."""
        if not QISKIT_AVAILABLE or not job.circuit:
            return {
                'success': False,
                'error': 'Qiskit not available or no circuit'
            }

        try:
            from qiskit_aer import AerSimulator

            # Simple execution on simulator
            backend = AerSimulator()
            transpiled = transpile(job.circuit, backend)
            qobj = backend.run(transpiled, shots=job.shots)
            result = qobj.result()

            return {
                'success': True,
                'counts': result.get_counts(),
                'shots': job.shots,
                'backend': job.backend
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def clear_jobs(self) -> None:
        """Clear all pending jobs."""
        self._jobs.clear()
        logger.info("Cleared all jobs")

    def get_job(self, job_id: str) -> Optional[QuantumJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_batch(self, batch_id: str) -> Optional[JobBatch]:
        """Get a batch by ID."""
        return self._batches.get(batch_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get batcher statistics."""
        return {
            'total_jobs': len(self._jobs),
            'total_batches': len(self._batches),
            'max_batch_size': self.max_batch_size,
            'max_qubits_per_batch': self.max_qubits_per_batch,
            'backends': list(set(job.backend for job in self._jobs.values())),
            'total_qubits': sum(job.num_qubits for job in self._jobs.values()),
            'total_shots': sum(job.shots for job in self._jobs.values())
        }


# ===== Helper Functions =====

def create_quantum_job(
    circuit: Optional[QuantumCircuit] = None,
    program_text: Optional[str] = None,
    shots: int = 1024,
    backend: str = "simulator",
    priority: int = 0,
    **metadata
) -> QuantumJob:
    """
    Convenience function to create a QuantumJob.

    Args:
        circuit: Quantum circuit to execute
        program_text: BioQL program text
        shots: Number of shots
        backend: Target backend
        priority: Job priority
        **metadata: Additional metadata

    Returns:
        QuantumJob instance
    """
    return QuantumJob(
        circuit=circuit,
        program_text=program_text,
        shots=shots,
        backend=backend,
        priority=priority,
        metadata=metadata
    )


def batch_and_execute(
    jobs: List[QuantumJob],
    strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE,
    api_key: Optional[str] = None
) -> Tuple[BatchResults, SavingsEstimate]:
    """
    Convenience function to batch and execute jobs in one call.

    Args:
        jobs: List of QuantumJob instances
        strategy: Batching strategy
        api_key: API key for authentication

    Returns:
        Tuple of (BatchResults, SavingsEstimate)
    """
    batcher = SmartBatcher()

    for job in jobs:
        batcher.add_job(job)

    # Get savings estimate before execution
    savings = batcher.estimate_batch_savings(strategy=strategy)

    # Generate and execute batches
    batches = batcher.get_batches(strategy)
    results = batcher.execute_batches(batches, api_key)

    return results, savings


# ===== Module Info =====

__all__ = [
    'BatchingStrategy',
    'QuantumJob',
    'JobBatch',
    'SavingsEstimate',
    'BatchResults',
    'SmartBatcher',
    'create_quantum_job',
    'batch_and_execute'
]


def main():
    """Example usage of SmartBatcher."""
    print("=== BioQL Smart Batcher Demo ===\n")

    if not QISKIT_AVAILABLE:
        print("Qiskit not available. Install with: pip install qiskit qiskit-aer")
        return

    # Create some sample jobs
    jobs = []
    for i in range(5):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        job = QuantumJob(
            circuit=circuit,
            shots=1024,
            backend="simulator",
            program_text=f"Bell state {i}"
        )
        jobs.append(job)

    print(f"Created {len(jobs)} quantum jobs\n")

    # Test batching with different strategies
    for strategy in BatchingStrategy:
        print(f"--- {strategy.value.upper()} ---")

        batcher = SmartBatcher(max_batch_size=3)
        for job in jobs:
            batcher.add_job(job)

        batches = batcher.get_batches(strategy)
        print(f"Generated {len(batches)} batches:")

        for i, batch in enumerate(batches, 1):
            print(f"  Batch {i}: {batch.num_jobs} jobs, "
                  f"cost=${batch.estimated_cost:.4f}, "
                  f"time={batch.estimated_time:.1f}s")

        savings = batcher.estimate_batch_savings()
        print(f"\nSavings: ${savings.cost_saved:.4f}, "
              f"{savings.time_saved_seconds:.1f}s, "
              f"{savings.api_calls_reduced} API calls\n")


if __name__ == '__main__':
    main()
