# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
API Integration Example
=======================

Shows how to integrate the job queue system with the existing FastAPI server.

This example demonstrates:
1. Adding job queue endpoints to the API
2. Async job submission
3. Real-time status monitoring
4. Result retrieval

Author: Spectrix R&D / BioQL Team
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.job_queue import JobQueue, JobStatus


# Pydantic models for API
class JobSubmitRequest(BaseModel):
    """Request model for job submission"""

    molecule_data: Dict[str, Any] = Field(..., description="Molecular structure data")
    backend: str = Field(
        "auto", description="Quantum backend: auto, ibm_quantum, aws_braket, azure_quantum"
    )
    shots: int = Field(1000, ge=100, le=100000, description="Number of quantum circuit shots")
    molecule_type: str = Field(
        "protein", description="Type of molecule: protein, dna, rna, metabolite"
    )
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")


class JobStatusResponse(BaseModel):
    """Response model for job status"""

    job_id: str
    status: str
    backend: str
    molecule_type: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    cost: float
    shots: int
    progress: float
    retry_count: int
    max_retries: int
    error_message: Optional[str]


class JobResultResponse(BaseModel):
    """Response model for job result"""

    job_id: str
    status: str
    error_message: Optional[str]
    data: Optional[Dict[str, Any]]
    quantum_config: Optional[Dict[str, Any]]


# Create FastAPI app
app = FastAPI(
    title="Quantum Job Queue API",
    description="Asynchronous job queue for quantum computations",
    version="1.0.0",
)

# Initialize job queue
job_queue = JobQueue()


# API Endpoints


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Quantum Job Queue API",
        "version": "1.0.0",
        "description": "Asynchronous job queue for quantum computations",
        "endpoints": {
            "submit_job": "POST /api/jobs/submit",
            "get_status": "GET /api/jobs/{job_id}/status",
            "get_result": "GET /api/jobs/{job_id}/result",
            "list_jobs": "GET /api/jobs",
            "cancel_job": "DELETE /api/jobs/{job_id}",
            "statistics": "GET /api/jobs/stats",
        },
    }


@app.post("/api/jobs/submit", response_model=Dict[str, str])
async def submit_job(request: JobSubmitRequest):
    """
    Submit a new quantum computation job

    Returns:
        job_id: Unique identifier for tracking the job
    """
    try:
        job_id = job_queue.create_job(
            molecule_data=request.molecule_data,
            backend=request.backend,
            shots=request.shots,
            molecule_type=request.molecule_type,
            max_retries=request.max_retries,
        )

        return {
            "job_id": job_id,
            "status": "pending",
            "message": f"Job submitted successfully. Use GET /api/jobs/{job_id}/status to track progress.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get current status of a job

    Args:
        job_id: Job identifier

    Returns:
        Job status information including progress and cost
    """
    status = job_queue.get_job_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(**status)


@app.get("/api/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """
    Get result of a completed job

    Args:
        job_id: Job identifier

    Returns:
        Job results including quantum configuration and visualizations
    """
    result = job_queue.get_job_result(job_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Check if job is completed
    if result["status"] not in ["COMPLETED", "FAILED"]:
        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "status": result["status"],
                "message": "Job is still processing. Please check status endpoint for progress.",
            },
        )

    return JobResultResponse(**result)


@app.get("/api/jobs/{job_id}/visualization/{filename}")
async def get_visualization(job_id: str, filename: str):
    """
    Download visualization file for a job

    Args:
        job_id: Job identifier
        filename: Filename (e.g., '3d_structure.png', 'energy_landscape.png')

    Returns:
        PNG image file
    """
    # Construct file path
    file_path = Path(job_queue.results_dir) / job_id / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Visualization {filename} not found for job {job_id}"
        )

    return FileResponse(path=str(file_path), media_type="image/png", filename=filename)


@app.get("/api/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 100, offset: int = 0):
    """
    List jobs with optional filtering

    Args:
        status: Filter by status (PENDING, RUNNING, COMPLETED, FAILED)
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip (pagination)

    Returns:
        List of jobs
    """
    try:
        if status:
            # Validate status
            try:
                job_status = JobStatus(status.upper())
                jobs = job_queue.get_jobs_by_status(job_status, limit=limit)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        else:
            jobs = job_queue.get_all_jobs(limit=limit, offset=offset)

        return {"total": len(jobs), "limit": limit, "offset": offset, "jobs": jobs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/pending/count")
async def get_pending_count():
    """Get count of pending jobs"""
    pending_jobs = job_queue.get_pending_jobs(limit=10000)
    return {"pending_count": len(pending_jobs)}


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel/delete a job

    Args:
        job_id: Job identifier

    Returns:
        Success message
    """
    # Check if job exists
    status = job_queue.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Delete job
    success = job_queue.delete_job(job_id)

    if success:
        return {"message": f"Job {job_id} deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to delete job {job_id}")


@app.get("/api/jobs/stats")
async def get_statistics():
    """
    Get job queue statistics

    Returns:
        Statistics including total jobs, costs, execution times
    """
    stats = job_queue.get_statistics()
    return stats


@app.post("/api/jobs/cleanup")
async def cleanup_old_jobs(days: int = 30):
    """
    Cleanup old jobs

    Args:
        days: Delete jobs older than this many days

    Returns:
        Number of jobs deleted
    """
    deleted_count = job_queue.cleanup_old_jobs(days=days)
    return {
        "message": f"Cleaned up {deleted_count} jobs older than {days} days",
        "deleted_count": deleted_count,
    }


@app.get("/health")
async def health_check():
    """
    API health check

    Returns:
        Health status and queue statistics
    """
    stats = job_queue.get_statistics()

    return {
        "status": "healthy",
        "queue": {
            "total_jobs": stats["total_jobs"],
            "pending": stats["status_counts"].get("PENDING", 0),
            "running": stats["status_counts"].get("RUNNING", 0),
            "completed": stats["status_counts"].get("COMPLETED", 0),
            "failed": stats["status_counts"].get("FAILED", 0),
        },
    }


# Example integration with existing quantum_viz_api.py
def integrate_with_existing_api():
    """
    Example of how to integrate job queue with existing API endpoints.

    Add to quantum_viz_api.py:
    """
    example_code = '''
# In quantum_viz_api.py

from backend.job_queue import JobQueue, JobStatus

# Initialize job queue
job_queue = JobQueue()

# Replace in-memory jobs dict with database-backed queue

@app.post("/api/visualize/protein", response_model=JobResponse)
async def visualize_protein(request: ProteinVisualizationRequest, background_tasks: BackgroundTasks):
    """Submit protein visualization job"""
    try:
        # Create job in queue instead of in-memory dict
        job_id = job_queue.create_job(
            molecule_data=request.model_dump(),
            backend='auto',
            molecule_type='protein'
        )

        # No need for background_tasks - worker handles it
        return {
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "message": f"Protein visualization job created. Use /api/status/{job_id} to track progress."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status from queue"""
    status = job_queue.get_job_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    return status


@app.get("/api/result/{job_id}")
async def get_job_result(job_id: str):
    """Get job result from queue"""
    result = job_queue.get_job_result(job_id)

    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    return result
'''
    return example_code


if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("🔬 QUANTUM JOB QUEUE API SERVER")
    print("=" * 80)
    print("\n📡 Starting server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("\n⚠️  Make sure to start the worker in a separate terminal:")
    print("   python backend/worker.py")
    print("=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
