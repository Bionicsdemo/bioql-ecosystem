# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Job Queue Manager
==================

Manages quantum job queue with background processing

Author: Spectrix R&D / BioQL Team
"""

import asyncio
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status states"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job data structure"""

    job_id: str
    status: JobStatus
    created_at: str
    params: Dict[str, Any]

    # Execution tracking
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0  # 0-100

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

    # Metrics
    estimated_time_remaining: Optional[float] = None  # seconds
    estimated_cost: Optional[float] = None  # USD
    actual_cost: Optional[float] = None  # USD

    # Job type and metadata
    job_type: str = "quantum_visualization"
    priority: int = 5  # 1-10, higher = more important

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["status"] = self.status.value
        return data


class JobQueue:
    """
    Job queue with background processing

    Thread-safe job management with async execution
    """

    def __init__(self, max_concurrent_jobs: int = 2):
        """
        Initialize job queue

        Args:
            max_concurrent_jobs: Maximum number of jobs to run concurrently
        """
        self.jobs: Dict[str, Job] = {}
        self.max_concurrent_jobs = max_concurrent_jobs
        self.lock = threading.Lock()
        self._running_jobs = 0

        logger.info(f"📋 Job Queue initialized (max concurrent: {max_concurrent_jobs})")

    def create_job(
        self, params: Dict[str, Any], job_type: str = "quantum_visualization", priority: int = 5
    ) -> str:
        """
        Create a new job

        Args:
            params: Job parameters
            job_type: Type of job
            priority: Job priority (1-10)

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow().isoformat(),
            params=params,
            job_type=job_type,
            priority=priority,
        )

        with self.lock:
            self.jobs[job_id] = job

        logger.info(f"📝 Created job {job_id} (type: {job_type}, priority: {priority})")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs) -> bool:
        """
        Update job fields

        Args:
            job_id: Job ID
            **kwargs: Fields to update

        Returns:
            True if updated, False if job not found
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            return True

    def set_job_running(self, job_id: str) -> bool:
        """Mark job as running"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job.status != JobStatus.PENDING:
                return False

            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat()
            job.progress = 5.0
            self._running_jobs += 1

            logger.info(f"▶️  Job {job_id} started running")
            return True

    def set_job_completed(
        self, job_id: str, result: Dict[str, Any], actual_cost: Optional[float] = None
    ) -> bool:
        """Mark job as completed with results"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow().isoformat()
            job.progress = 100.0
            job.result = result
            job.actual_cost = actual_cost or result.get("execution_metrics", {}).get(
                "total_cost_usd"
            )

            if job.status == JobStatus.RUNNING:
                self._running_jobs = max(0, self._running_jobs - 1)

            logger.info(f"✅ Job {job_id} completed")
            return True

    def set_job_failed(self, job_id: str, error: str, error_type: Optional[str] = None) -> bool:
        """Mark job as failed"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow().isoformat()
            job.error = error
            job.error_type = error_type

            if job.status == JobStatus.RUNNING:
                self._running_jobs = max(0, self._running_jobs - 1)

            logger.error(f"❌ Job {job_id} failed: {error}")
            return True

    def update_progress(
        self, job_id: str, progress: float, estimated_time_remaining: Optional[float] = None
    ) -> bool:
        """Update job progress"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            job.progress = min(100.0, max(0.0, progress))
            if estimated_time_remaining is not None:
                job.estimated_time_remaining = estimated_time_remaining

            return True

    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        """Get pending jobs sorted by priority"""
        with self.lock:
            pending = [job for job in self.jobs.values() if job.status == JobStatus.PENDING]
            # Sort by priority (descending) then by created_at (ascending)
            pending.sort(key=lambda j: (-j.priority, j.created_at))
            return pending[:limit]

    def get_running_jobs(self) -> list[Job]:
        """Get all running jobs"""
        with self.lock:
            return [job for job in self.jobs.values() if job.status == JobStatus.RUNNING]

    def can_start_new_job(self) -> bool:
        """Check if we can start a new job"""
        with self.lock:
            return self._running_jobs < self.max_concurrent_jobs

    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]

                # Clean up result files if present
                if job.result and "visualization_files" in job.result:
                    for file_path in job.result["visualization_files"].values():
                        if isinstance(file_path, str):
                            path = Path(file_path)
                            if path.exists():
                                try:
                                    path.unlink()
                                    logger.info(f"🗑️  Deleted file: {path}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete {path}: {e}")

                del self.jobs[job_id]
                logger.info(f"🗑️  Deleted job {job_id}")
                return True
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            stats = {
                "total_jobs": len(self.jobs),
                "pending": sum(1 for j in self.jobs.values() if j.status == JobStatus.PENDING),
                "running": sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING),
                "completed": sum(1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED),
                "failed": sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED),
                "max_concurrent": self.max_concurrent_jobs,
                "can_start_new": self.can_start_new_job(),
            }
            return stats

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of jobs deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted = 0

        with self.lock:
            jobs_to_delete = []

            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    if job.completed_at:
                        completed_time = datetime.fromisoformat(job.completed_at)
                        if completed_time < cutoff_time:
                            jobs_to_delete.append(job_id)

            for job_id in jobs_to_delete:
                self.delete_job(job_id)
                deleted += 1

        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old jobs")

        return deleted


# Global job queue instance
job_queue = JobQueue(max_concurrent_jobs=2)
