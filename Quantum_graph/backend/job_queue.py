# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Job Queue System for Quantum Computations
==========================================

SQLite-based job tracking system for managing asynchronous quantum execution jobs.

Features:
- Thread-safe database operations
- Job lifecycle management (PENDING -> RUNNING -> COMPLETED/FAILED)
- Result persistence and retrieval
- Cost tracking and resource management
- Error handling and retry logic

Author: Spectrix R&D / BioQL Team
"""

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class JobStatus(str, Enum):
    """Job execution status"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class JobRecord:
    """Job record structure"""

    id: str
    status: JobStatus
    backend: str
    molecule_type: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    cost: float = 0.0
    shots: int = 1000
    molecule_data: Optional[Dict[str, Any]] = None
    quantum_config: Optional[Dict[str, Any]] = None
    progress: float = 0.0
    retry_count: int = 0
    max_retries: int = 3


class JobQueue:
    """
    Thread-safe job queue system using SQLite

    Manages quantum computation jobs with persistence and tracking.
    """

    def __init__(self, db_path: str = None, results_dir: str = None):
        """
        Initialize job queue

        Args:
            db_path: Path to SQLite database (default: backend/jobs.db)
            results_dir: Directory for storing results (default: backend/results/)
        """
        if db_path is None:
            db_path = str(Path(__file__).parent / "jobs.db")

        if results_dir is None:
            results_dir = str(Path(__file__).parent / "results")

        self.db_path = db_path
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True, parents=True)

        # Thread lock for database operations
        self._lock = threading.RLock()

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    backend TEXT NOT NULL,
                    molecule_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result_path TEXT,
                    error_message TEXT,
                    cost REAL DEFAULT 0.0,
                    shots INTEGER DEFAULT 1000,
                    molecule_data TEXT,
                    quantum_config TEXT,
                    progress REAL DEFAULT 0.0,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """
            )

            # Create indexes for common queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status
                ON jobs(status)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON jobs(created_at DESC)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend
                ON jobs(backend)
            """
            )

            conn.commit()
            conn.close()

    def create_job(
        self,
        molecule_data: Dict[str, Any],
        backend: str = "auto",
        shots: int = 1000,
        molecule_type: str = "protein",
        max_retries: int = 3,
    ) -> str:
        """
        Create a new job in the queue

        Args:
            molecule_data: Molecular structure data
            backend: Quantum backend to use
            shots: Number of quantum circuit shots
            molecule_type: Type of molecule
            max_retries: Maximum retry attempts

        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid.uuid4())

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO jobs (
                    id, status, backend, molecule_type, created_at,
                    molecule_data, shots, max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    job_id,
                    JobStatus.PENDING.value,
                    backend,
                    molecule_type,
                    datetime.utcnow().isoformat(),
                    json.dumps(molecule_data),
                    shots,
                    max_retries,
                ),
            )

            conn.commit()
            conn.close()

        print(f"✅ Created job {job_id} - Status: PENDING")
        return job_id

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        progress: Optional[float] = None,
    ) -> bool:
        """
        Update job status and optionally store results

        Args:
            job_id: Job identifier
            status: New job status
            result_data: Results to store (for COMPLETED status)
            error_message: Error message (for FAILED status)
            progress: Job progress (0-100)

        Returns:
            bool: True if update successful
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get current job data
            cursor.execute("SELECT status, started_at FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                print(f"❌ Job {job_id} not found")
                return False

            current_status, started_at = row

            # Build update query dynamically
            updates = ["status = ?"]
            params = [status.value]

            # Set timestamps based on status transition
            if status == JobStatus.RUNNING and not started_at:
                updates.append("started_at = ?")
                params.append(datetime.utcnow().isoformat())

            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                updates.append("completed_at = ?")
                params.append(datetime.utcnow().isoformat())

            # Handle result data
            if result_data and status == JobStatus.COMPLETED:
                # Save results to file
                result_path = self.results_dir / f"{job_id}_result.json"
                with open(result_path, "w") as f:
                    json.dump(result_data, f, indent=2)

                updates.append("result_path = ?")
                params.append(str(result_path))

                # Store cost if available
                if "cost" in result_data:
                    updates.append("cost = ?")
                    params.append(result_data["cost"])

                # Store quantum config
                if "quantum_config" in result_data:
                    updates.append("quantum_config = ?")
                    params.append(json.dumps(result_data["quantum_config"]))

            # Handle error message
            if error_message and status == JobStatus.FAILED:
                updates.append("error_message = ?")
                params.append(error_message)

            # Handle progress
            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)

            # Execute update
            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            conn.commit()
            conn.close()

        print(f"📝 Updated job {job_id} - Status: {status.value}")
        return True

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status and metadata

        Args:
            job_id: Job identifier

        Returns:
            dict: Job status information or None if not found
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, status, backend, molecule_type, created_at,
                       started_at, completed_at, cost, shots, progress,
                       retry_count, max_retries, error_message
                FROM jobs WHERE id = ?
            """,
                (job_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return dict(row)

    def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job result data

        Args:
            job_id: Job identifier

        Returns:
            dict: Job results or None if not available
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT status, result_path, error_message, quantum_config
                FROM jobs WHERE id = ?
            """,
                (job_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            status, result_path, error_message, quantum_config = row

            result = {"job_id": job_id, "status": status, "error_message": error_message}

            # Load result data from file if available
            if result_path and Path(result_path).exists():
                with open(result_path, "r") as f:
                    result["data"] = json.load(f)

            # Add quantum config
            if quantum_config:
                result["quantum_config"] = json.loads(quantum_config)

            return result

    def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending jobs for processing

        Args:
            limit: Maximum number of jobs to return

        Returns:
            list: List of pending job records
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, backend, molecule_type, molecule_data, shots, retry_count
                FROM jobs
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT ?
            """,
                (JobStatus.PENDING.value, limit),
            )

            jobs = [dict(row) for row in cursor.fetchall()]
            conn.close()

            # Parse JSON fields
            for job in jobs:
                if job["molecule_data"]:
                    job["molecule_data"] = json.loads(job["molecule_data"])

            return jobs

    def increment_retry_count(self, job_id: str) -> bool:
        """
        Increment retry counter for a job

        Args:
            job_id: Job identifier

        Returns:
            bool: True if retry allowed, False if max retries exceeded
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT retry_count, max_retries FROM jobs WHERE id = ?
            """,
                (job_id,),
            )

            row = cursor.fetchone()
            if not row:
                conn.close()
                return False

            retry_count, max_retries = row
            new_retry_count = retry_count + 1

            if new_retry_count > max_retries:
                # Exceeded max retries - mark as failed
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = ?, error_message = ?, completed_at = ?
                    WHERE id = ?
                """,
                    (
                        JobStatus.FAILED.value,
                        f"Maximum retries ({max_retries}) exceeded",
                        datetime.utcnow().isoformat(),
                        job_id,
                    ),
                )
                conn.commit()
                conn.close()
                return False

            # Increment retry count and reset to PENDING
            cursor.execute(
                """
                UPDATE jobs
                SET retry_count = ?, status = ?
                WHERE id = ?
            """,
                (new_retry_count, JobStatus.PENDING.value, job_id),
            )

            conn.commit()
            conn.close()
            return True

    def get_jobs_by_status(self, status: JobStatus, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get jobs by status

        Args:
            status: Job status to filter by
            limit: Maximum number of jobs

        Returns:
            list: List of job records
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, status, backend, molecule_type, created_at,
                       started_at, completed_at, cost, progress
                FROM jobs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (status.value, limit),
            )

            jobs = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return jobs

    def get_all_jobs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all jobs with pagination

        Args:
            limit: Maximum number of jobs
            offset: Number of jobs to skip

        Returns:
            list: List of job records
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, status, backend, molecule_type, created_at,
                       started_at, completed_at, cost, progress, error_message
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

            jobs = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return jobs

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get job queue statistics

        Returns:
            dict: Statistics about jobs
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Count by status
            cursor.execute(
                """
                SELECT status, COUNT(*) as count
                FROM jobs
                GROUP BY status
            """
            )
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Total cost
            cursor.execute(
                "SELECT SUM(cost) FROM jobs WHERE status = ?", (JobStatus.COMPLETED.value,)
            )
            total_cost = cursor.fetchone()[0] or 0.0

            # Average execution time
            cursor.execute(
                """
                SELECT AVG(
                    CAST((julianday(completed_at) - julianday(started_at)) * 24 * 60 AS REAL)
                ) as avg_minutes
                FROM jobs
                WHERE status = ? AND started_at IS NOT NULL AND completed_at IS NOT NULL
            """,
                (JobStatus.COMPLETED.value,),
            )
            avg_execution_time = cursor.fetchone()[0] or 0.0

            conn.close()

            return {
                "status_counts": status_counts,
                "total_cost_usd": total_cost,
                "avg_execution_time_minutes": avg_execution_time,
                "total_jobs": sum(status_counts.values()),
            }

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and its results

        Args:
            job_id: Job identifier

        Returns:
            bool: True if deleted successfully
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get result path
            cursor.execute("SELECT result_path FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()

            if row and row[0]:
                result_path = Path(row[0])
                if result_path.exists():
                    result_path.unlink()

            # Delete job
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            deleted = cursor.rowcount > 0

            conn.commit()
            conn.close()

            return deleted

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete jobs older than specified days

        Args:
            days: Age threshold in days

        Returns:
            int: Number of jobs deleted
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.utcnow().isoformat()

            # Get old job IDs and result paths
            cursor.execute(
                """
                SELECT id, result_path FROM jobs
                WHERE julianday(?) - julianday(created_at) > ?
            """,
                (cutoff_date, days),
            )

            old_jobs = cursor.fetchall()

            # Delete result files
            for job_id, result_path in old_jobs:
                if result_path:
                    path = Path(result_path)
                    if path.exists():
                        path.unlink()

            # Delete from database
            cursor.execute(
                """
                DELETE FROM jobs
                WHERE julianday(?) - julianday(created_at) > ?
            """,
                (cutoff_date, days),
            )

            deleted_count = cursor.rowcount

            conn.commit()
            conn.close()

            return deleted_count


# Example usage
if __name__ == "__main__":
    # Create job queue
    queue = JobQueue()

    print("🔬 Quantum Job Queue System")
    print("=" * 60)

    # Create test job
    molecule_data = {"num_atoms": 100, "num_bonds": 98, "name": "test_protein"}

    job_id = queue.create_job(
        molecule_data=molecule_data, backend="ibm_quantum", shots=1000, molecule_type="protein"
    )

    print(f"\n📊 Job Created: {job_id}")

    # Get status
    status = queue.get_job_status(job_id)
    print(f"\n📝 Job Status:")
    print(json.dumps(status, indent=2))

    # Simulate job execution
    queue.update_job_status(job_id, JobStatus.RUNNING, progress=0.0)
    queue.update_job_status(job_id, JobStatus.RUNNING, progress=50.0)

    # Complete job with results
    result_data = {
        "energy": -123.45,
        "conformations": 10,
        "cost": 2.50,
        "quantum_config": {
            "logical_qubits": 20,
            "physical_qubits": 100,
            "shots": 1000,
            "backend": "ibm_quantum",
        },
    }

    queue.update_job_status(job_id, JobStatus.COMPLETED, result_data=result_data, progress=100.0)

    # Get result
    result = queue.get_job_result(job_id)
    print(f"\n✅ Job Result:")
    print(json.dumps(result, indent=2, default=str))

    # Get statistics
    stats = queue.get_statistics()
    print(f"\n📈 Queue Statistics:")
    print(json.dumps(stats, indent=2))
