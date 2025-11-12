# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Example Usage of Job Queue System
==================================

Demonstrates how to use the quantum job queue system for
submitting and tracking quantum computation jobs.

Author: Spectrix R&D / BioQL Team
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import json

from backend.job_queue import JobQueue, JobStatus


def example_1_basic_job_submission():
    """Example 1: Basic job submission and tracking"""
    print("=" * 80)
    print("EXAMPLE 1: Basic Job Submission")
    print("=" * 80)

    # Create job queue
    queue = JobQueue()

    # Define molecule data
    molecule_data = {
        "name": "example_protein",
        "num_atoms": 250,
        "num_bonds": 245,
        "num_conformations": 15,
        "description": "Small protein for quantum conformational sampling",
    }

    # Submit job
    print("\n📤 Submitting job...")
    job_id = queue.create_job(
        molecule_data=molecule_data, backend="ibm_quantum", shots=1000, molecule_type="protein"
    )

    print(f"✅ Job submitted: {job_id}")

    # Check status
    status = queue.get_job_status(job_id)
    print(f"\n📊 Job Status:")
    print(json.dumps(status, indent=2))

    return job_id


def example_2_job_monitoring():
    """Example 2: Job monitoring with status updates"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Job Monitoring")
    print("=" * 80)

    queue = JobQueue()

    # Create a job
    molecule_data = {"name": "monitoring_example", "num_atoms": 100, "num_bonds": 98}

    job_id = queue.create_job(
        molecule_data=molecule_data, backend="aws_braket", shots=2000, molecule_type="protein"
    )

    print(f"\n📝 Created job: {job_id}")

    # Simulate job lifecycle
    print("\n🔄 Simulating job execution...")

    # Start job
    queue.update_job_status(job_id, JobStatus.RUNNING, progress=0.0)
    print("   ⏳ Job started (0%)")
    time.sleep(0.5)

    # Update progress
    for progress in [25.0, 50.0, 75.0]:
        queue.update_job_status(job_id, JobStatus.RUNNING, progress=progress)
        print(f"   ⏳ Progress: {progress}%")
        time.sleep(0.5)

    # Complete job
    result_data = {
        "energy": -234.56,
        "conformations": 12,
        "cost": 5.75,
        "quantum_config": {
            "logical_qubits": 30,
            "physical_qubits": 150,
            "shots": 2000,
            "backend": "aws_braket",
        },
    }

    queue.update_job_status(job_id, JobStatus.COMPLETED, result_data=result_data, progress=100.0)
    print("   ✅ Job completed (100%)")

    # Get final status
    status = queue.get_job_status(job_id)
    print(f"\n📊 Final Status:")
    print(f"   Status: {status['status']}")
    print(f"   Progress: {status['progress']}%")
    print(f"   Cost: ${status['cost']:.2f}")

    # Get result
    result = queue.get_job_result(job_id)
    print(f"\n📦 Result Data:")
    print(json.dumps(result, indent=2, default=str))


def example_3_batch_jobs():
    """Example 3: Submitting multiple jobs"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Batch Job Submission")
    print("=" * 80)

    queue = JobQueue()

    # Submit multiple jobs
    job_ids = []

    molecules = [
        {"name": "protein_A", "num_atoms": 150, "type": "protein"},
        {"name": "dna_fragment", "num_atoms": 80, "type": "dna"},
        {"name": "metabolite_X", "num_atoms": 45, "type": "small_molecule"},
    ]

    print("\n📤 Submitting batch jobs...")
    for mol in molecules:
        molecule_data = {
            "name": mol["name"],
            "num_atoms": mol["num_atoms"],
            "num_bonds": mol["num_atoms"] - 2,
        }

        job_id = queue.create_job(
            molecule_data=molecule_data, backend="auto", shots=1000, molecule_type=mol["type"]
        )

        job_ids.append(job_id)
        print(f"   ✅ {mol['name']}: {job_id}")

    # List all pending jobs
    pending = queue.get_pending_jobs(limit=10)
    print(f"\n📋 Pending Jobs: {len(pending)}")
    for job in pending:
        print(f"   - {job['id'][:8]}... ({job['molecule_type']})")


def example_4_error_handling():
    """Example 4: Error handling and retries"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Error Handling and Retries")
    print("=" * 80)

    queue = JobQueue()

    # Create job
    molecule_data = {"name": "error_test", "num_atoms": 50}
    job_id = queue.create_job(
        molecule_data=molecule_data, backend="ibm_quantum", molecule_type="protein", max_retries=3
    )

    print(f"\n📝 Created job: {job_id}")
    print("   Max retries: 3")

    # Simulate failure and retries
    queue.update_job_status(job_id, JobStatus.RUNNING, progress=20.0)
    print("\n❌ Simulating job failure...")

    for attempt in range(1, 4):
        # Increment retry
        can_retry = queue.increment_retry_count(job_id)

        if can_retry:
            print(f"   🔄 Retry {attempt}/3 - Job reset to PENDING")
        else:
            print(f"   💀 Max retries exceeded - Job marked as FAILED")
            break

    # Check final status
    status = queue.get_job_status(job_id)
    print(f"\n📊 Final Status:")
    print(f"   Status: {status['status']}")
    print(f"   Retry count: {status['retry_count']}/{status['max_retries']}")
    if status["error_message"]:
        print(f"   Error: {status['error_message']}")


def example_5_statistics():
    """Example 5: Queue statistics"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Queue Statistics")
    print("=" * 80)

    queue = JobQueue()

    # Get statistics
    stats = queue.get_statistics()

    print("\n📈 Queue Statistics:")
    print("-" * 80)
    print(f"Total Jobs:           {stats['total_jobs']}")
    print(f"Total Cost:           ${stats['total_cost_usd']:.2f}")
    print(f"Avg Execution Time:   {stats['avg_execution_time_minutes']:.2f} minutes")

    print("\nJobs by Status:")
    for status, count in stats["status_counts"].items():
        print(f"   {status:12s}: {count}")

    # Get all jobs
    all_jobs = queue.get_all_jobs(limit=10)
    print(f"\n📋 Recent Jobs (last 10):")
    print("-" * 80)
    for job in all_jobs:
        print(
            f"   {job['id'][:8]}... | {job['status']:10s} | {job['molecule_type']:15s} | ${job['cost']:.2f}"
        )


def example_6_job_lifecycle():
    """Example 6: Complete job lifecycle"""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Complete Job Lifecycle")
    print("=" * 80)

    queue = JobQueue()

    # Create job with detailed molecule data
    molecule_data = {
        "name": "insulin_fragment",
        "num_atoms": 450,
        "num_bonds": 445,
        "num_conformations": 20,
        "sequence": "FVNQHLCGSHLVEALYLVCGERGFFYTPKA",
        "molecular_weight": 3496.9,
    }

    print("\n📤 Creating job for insulin fragment...")
    job_id = queue.create_job(
        molecule_data=molecule_data, backend="ibm_quantum", shots=5000, molecule_type="protein"
    )

    print(f"✅ Job ID: {job_id}")

    # Monitor through lifecycle
    statuses = [
        (JobStatus.RUNNING, 0.0, "Initializing quantum circuit"),
        (JobStatus.RUNNING, 20.0, "Optimizing quantum parameters"),
        (JobStatus.RUNNING, 40.0, "Executing quantum sampling"),
        (JobStatus.RUNNING, 60.0, "Processing quantum measurements"),
        (JobStatus.RUNNING, 80.0, "Generating visualizations"),
    ]

    print("\n📊 Job Progress:")
    for status, progress, message in statuses:
        queue.update_job_status(job_id, status, progress=progress)
        print(f"   [{progress:5.1f}%] {message}")
        time.sleep(0.3)

    # Complete with results
    result_data = {
        "structure_name": "insulin_fragment",
        "num_atoms": 450,
        "num_conformations": 20,
        "ground_state_energy": -1234.56,
        "visualization_files": {
            "3d_structure": f"/path/to/results/{job_id}/structure.png",
            "energy_landscape": f"/path/to/results/{job_id}/energy.png",
        },
        "quantum_config": {
            "logical_qubits": 40,
            "physical_qubits": 200,
            "shots": 5000,
            "backend": "ibm_quantum",
            "circuit_depth": 150,
        },
        "cost": 12.50,
        "execution_time_seconds": 45.2,
    }

    queue.update_job_status(job_id, JobStatus.COMPLETED, result_data=result_data, progress=100.0)
    print(f"   [100.0%] Job completed successfully!")

    # Display final result
    result = queue.get_job_result(job_id)
    print(f"\n✅ Job Complete!")
    print("-" * 80)
    print(f"Structure:      {result['data']['structure_name']}")
    print(f"Atoms:          {result['data']['num_atoms']}")
    print(f"Conformations:  {result['data']['num_conformations']}")
    print(f"Energy:         {result['data']['ground_state_energy']:.2f} kcal/mol")
    print(f"Cost:           ${result['data']['cost']:.2f}")
    print(f"Execution Time: {result['data']['execution_time_seconds']:.1f}s")

    print("\nQuantum Configuration:")
    qc = result["quantum_config"]
    print(f"   Logical Qubits:  {qc['logical_qubits']}")
    print(f"   Physical Qubits: {qc['physical_qubits']}")
    print(f"   Circuit Depth:   {qc['circuit_depth']}")
    print(f"   Backend:         {qc['backend']}")


def main():
    """Run all examples"""
    print("\n")
    print("🔬" + "=" * 78 + "🔬")
    print("   QUANTUM JOB QUEUE SYSTEM - USAGE EXAMPLES")
    print("🔬" + "=" * 78 + "🔬")

    try:
        # Run examples
        example_1_basic_job_submission()
        example_2_job_monitoring()
        example_3_batch_jobs()
        example_4_error_handling()
        example_5_statistics()
        example_6_job_lifecycle()

        print("\n" + "=" * 80)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
