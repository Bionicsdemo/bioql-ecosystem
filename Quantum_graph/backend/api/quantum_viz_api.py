# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum Visualization REST API
===============================

FastAPI server for quantum-enhanced scientific visualization

Endpoints:
- POST /api/visualize/protein - Protein structure visualization
- POST /api/visualize/metabolic - Metabolic network visualization
- POST /api/visualize/drug - Drug design visualization
- POST /api/optimize/quantum - Quantum parameter optimization
- GET /api/config/{job_id} - Get quantum configuration
- GET /api/status/{job_id} - Get job status

Author: Spectrix R&D / BioQL Team
"""

import asyncio
import io
import json
import logging
import sys
import traceback
import uuid
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.services.billing_integration import UserQuota, get_billing_integration
from backend.services.job_queue import JobStatus, job_queue
from backend.services.quantum_executor import QuantumExecutor
from quantum_core.optimizers.adaptive_quantum_optimizer import (
    AdaptiveQuantumOptimizer,
    QuantumConfig,
)
from visualization.metabolomics.quantum_metabolomics_viz import (
    MetabolicNetwork,
    QuantumMetabolomicsVisualizer,
)
from visualization.protein.quantum_protein_viz import QuantumProteinVisualizer
from visualization.quantum_viz_engine import (
    MolecularStructure,
    MoleculeType,
    QuantumVizEngine,
    VisualizationType,
)

# Create FastAPI app
app = FastAPI(
    title="Quantum Visualization API",
    description="Quantum-enhanced scientific visualization for biotechnology research",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)


# Global instances
viz_engine = QuantumVizEngine()
protein_viz = QuantumProteinVisualizer(viz_engine)
metabolomics_viz = QuantumMetabolomicsVisualizer()
quantum_executor = QuantumExecutor()
billing = get_billing_integration()

# Security
security = HTTPBearer(auto_error=False)

# Job storage (in production, use Redis or database)
jobs = {}


# Authentication and billing functions
async def get_api_key(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
) -> str:
    """Extract API key from Authorization header or X-API-Key header.

    Args:
        authorization: Bearer token from Authorization header
        x_api_key: API key from X-API-Key header

    Returns:
        API key string

    Raises:
        HTTPException: If no API key provided
    """
    # Try Bearer token first
    if authorization:
        return authorization.credentials

    # Try X-API-Key header
    if x_api_key:
        return x_api_key

    # No API key provided - allow for free tier / testing
    # In production, you might want to require API keys
    return None


async def validate_and_get_quota(
    api_key: Optional[str] = Depends(get_api_key),
) -> Optional[UserQuota]:
    """Validate API key and get user quota.

    Args:
        api_key: BioQL API key

    Returns:
        UserQuota object or None for unauthenticated access

    Raises:
        HTTPException: If API key is invalid
    """
    # Allow unauthenticated access for testing
    if not api_key:
        logger.info("⚠️  No API key provided - using anonymous/testing mode")
        return None

    # Validate API key
    quota = billing.get_user_quota(api_key)
    if not quota:
        raise HTTPException(
            status_code=401, detail="Invalid API key. Get your API key at https://api.bioql.bio"
        )

    logger.info(f"✅ Authenticated user: {quota.email} (tier: {quota.tier})")
    return quota


# Pydantic models
class MoleculeTypeEnum(str, Enum):
    protein = "protein"
    dna = "dna"
    rna = "rna"
    small_molecule = "small_molecule"
    antibody = "antibody"
    protein_complex = "protein_complex"
    metabolite = "metabolite"


class VisualizationTypeEnum(str, Enum):
    structure_3d = "structure_3d"
    energy_landscape = "energy_landscape"
    binding_affinity = "binding_affinity"
    conformational_sampling = "conformational_sampling"
    electron_density = "electron_density"
    molecular_orbitals = "molecular_orbitals"
    reaction_pathway = "reaction_pathway"
    protein_folding = "protein_folding"
    docking_simulation = "docking_simulation"


class QuantumOptimizationRequest(BaseModel):
    molecule_data: Dict[str, Any] = Field(..., description="Molecular structure data")
    molecule_type: MoleculeTypeEnum
    viz_type: VisualizationTypeEnum
    budget_usd: Optional[float] = Field(None, description="Maximum budget in USD")
    max_time_hours: Optional[float] = Field(None, description="Maximum time in hours")
    accuracy_target: float = Field(0.95, ge=0.0, le=1.0, description="Target accuracy")
    backend_preference: str = Field(
        "auto",
        description="Quantum backend: auto, simulator, ibm_quantum, azure_quantum, aws_braket",
    )
    shots: Optional[int] = Field(
        1024, ge=100, le=100000, description="Number of quantum measurements"
    )


class ProteinVisualizationRequest(BaseModel):
    pdb_file: Optional[str] = Field(None, description="Path to PDB file")
    pdb_content: Optional[str] = Field(None, description="PDB file content as string")
    visualization_types: List[str] = Field(
        ["structure_3d", "secondary_structure"], description="Types of visualizations to generate"
    )
    num_conformations: int = Field(
        10, ge=1, le=100, description="Number of conformations to sample"
    )


class MetabolicNetworkRequest(BaseModel):
    network_name: str = Field("Custom_Network", description="Network name")
    organism: str = Field("Unknown", description="Organism name")
    metabolites: List[Dict[str, Any]] = Field(..., description="List of metabolites")
    reactions: List[Dict[str, Any]] = Field(..., description="List of reactions")
    visualization_types: List[str] = Field(
        ["network", "heatmap", "flux"], description="Visualization types"
    )


class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0-100
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Helper functions
def create_job(job_type: str, params: Dict[str, Any]) -> str:
    """Create a new job and return job ID"""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "type": job_type,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "params": params,
        "results": None,
        "error": None,
    }
    return job_id


def update_job(job_id: str, **kwargs):
    """Update job status"""
    if job_id in jobs:
        jobs[job_id].update(kwargs)


async def process_protein_visualization(job_id: str, request: ProteinVisualizationRequest):
    """Background task for protein visualization"""
    try:
        update_job(job_id, status="running", started_at=datetime.utcnow().isoformat(), progress=10)

        # Parse PDB
        if request.pdb_file:
            structure = viz_engine.parse_pdb(request.pdb_file)
        elif request.pdb_content:
            # Save temp file
            temp_pdb = f"/tmp/protein_{job_id}.pdb"
            with open(temp_pdb, "w") as f:
                f.write(request.pdb_content)
            structure = viz_engine.parse_pdb(temp_pdb)
        else:
            raise ValueError("Either pdb_file or pdb_content must be provided")

        update_job(job_id, progress=30)

        results = {}

        # Generate requested visualizations
        if "structure_3d" in request.visualization_types:
            output_file = f"/tmp/protein_{job_id}_3d.png"
            viz_engine.visualize_3d_structure(structure, output_file)
            results["structure_3d"] = output_file
            update_job(job_id, progress=50)

        if "secondary_structure" in request.visualization_types:
            output_file = f"/tmp/protein_{job_id}_secondary.png"
            protein_viz.visualize_secondary_structure(structure, output_file)
            results["secondary_structure"] = output_file
            update_job(job_id, progress=70)

        if "conformational_sampling" in request.visualization_types:
            # Quantum sampling
            quantum_result = viz_engine.quantum_conformation_sampling(
                structure, num_conformations=request.num_conformations
            )
            output_file = f"/tmp/protein_{job_id}_energy.png"
            viz_engine.visualize_energy_landscape(quantum_result, output_file)
            results["energy_landscape"] = output_file

            # Folding pathway
            output_file = f"/tmp/protein_{job_id}_folding.png"
            protein_viz.visualize_protein_folding_pathway(quantum_result, output_file)
            results["folding_pathway"] = output_file

            # Store quantum config
            results["quantum_config"] = {
                "logical_qubits": quantum_result.quantum_config.logical_qubits,
                "physical_qubits": quantum_result.quantum_config.physical_qubits,
                "shots": quantum_result.quantum_config.shots,
                "backend": quantum_result.quantum_config.backend_type,
                "estimated_cost": quantum_result.quantum_config.estimated_cost_usd,
                "time_hours": quantum_result.quantum_config.time_to_solution_hours,
            }

        update_job(
            job_id,
            status="completed",
            progress=100,
            completed_at=datetime.utcnow().isoformat(),
            results=results,
        )

    except Exception as e:
        update_job(
            job_id, status="failed", completed_at=datetime.utcnow().isoformat(), error=str(e)
        )


# API Endpoints

# Mount static files (frontend)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to login page"""
    login_file = frontend_path / "login.html"
    if login_file.exists():
        return FileResponse(login_file)

    # Fallback to JSON API info
    return JSONResponse(
        {
            "name": "Quantum Visualization API",
            "version": "1.0.0",
            "description": "Quantum-enhanced scientific visualization for biotechnology",
            "endpoints": {
                "optimize": "/api/optimize/quantum",
                "protein_viz": "/api/visualize/protein",
                "metabolic_viz": "/api/visualize/metabolic",
                "job_status": "/api/status/{job_id}",
                "download": "/api/download/{filename}",
            },
        }
    )


@app.get("/login.html", response_class=HTMLResponse)
async def login_page():
    """Serve login page"""
    login_file = frontend_path / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    raise HTTPException(status_code=404, detail="Login page not found")


@app.get("/index.html", response_class=HTMLResponse)
async def main_page():
    """Serve main application page"""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Main page not found")


async def _process_quantum_job_background(
    job_id: str, request: QuantumOptimizationRequest, api_key: Optional[str] = None
):
    """Background task to process quantum job with billing integration"""
    try:
        # Update job status
        job_queue.set_job_running(job_id)
        job_queue.update_progress(job_id, 10.0)

        # Execute quantum job
        result = await quantum_executor.execute_job(
            job_id=job_id,
            molecule_data=request.molecule_data,
            molecule_type=request.molecule_type.value,
            viz_type=request.viz_type.value,
            backend_preference=request.backend_preference,
            shots=request.shots or 1024,
            budget_usd=request.budget_usd,
            max_time_hours=request.max_time_hours,
            accuracy_target=request.accuracy_target,
            api_key=api_key,  # Pass API key for BioQL integration
        )

        if result.get("status") == "completed":
            job_queue.set_job_completed(job_id, result)

            # Record usage to billing system if API key provided
            if api_key:
                try:
                    actual_cost = result.get("cost", 0.0)
                    actual_shots = result.get("shots", request.shots or 1024)
                    backend_used = result.get("backend", request.backend_preference)

                    success = billing.record_usage(
                        api_key=api_key,
                        shots=actual_shots,
                        backend=backend_used,
                        cost=actual_cost,
                        job_id=job_id,
                        metadata={
                            "molecule_type": request.molecule_type.value,
                            "viz_type": request.viz_type.value,
                            "execution_time": result.get("execution_time", 0),
                            "qubits": result.get("num_qubits", 0),
                        },
                    )

                    if success:
                        logger.info(
                            f"✅ Usage recorded for job {job_id}: {actual_shots} shots, ${actual_cost:.4f}"
                        )
                    else:
                        logger.warning(f"⚠️  Failed to record usage for job {job_id}")

                except Exception as billing_error:
                    # Don't fail the job if billing recording fails
                    logger.error(f"❌ Billing recording error for job {job_id}: {billing_error}")

        else:
            job_queue.set_job_failed(
                job_id, result.get("error", "Unknown error"), result.get("error_type")
            )

    except Exception as e:
        logger.error(f"Background job {job_id} failed: {str(e)}")
        logger.error(traceback.format_exc())
        job_queue.set_job_failed(job_id, str(e), type(e).__name__)


@app.post("/api/optimize/quantum", response_model=Dict[str, Any])
async def optimize_quantum_parameters(
    request: QuantumOptimizationRequest,
    background_tasks: BackgroundTasks,
    api_key: Optional[str] = Depends(get_api_key),
    quota: Optional[UserQuota] = Depends(validate_and_get_quota),
):
    """
    Execute quantum optimization job asynchronously with billing integration

    Requires BioQL API key for paid backends (IBM, IonQ, AWS).
    Free tier allows limited simulator usage.

    Headers:
        Authorization: Bearer YOUR_BIOQL_API_KEY
        or
        X-API-Key: YOUR_BIOQL_API_KEY

    Creates job in queue and returns job_id immediately.
    Use /api/jobs/{job_id}/status to track progress.
    """
    try:
        # Estimate cost and check quota
        optimizer = AdaptiveQuantumOptimizer(
            budget_usd=request.budget_usd,
            max_time_hours=request.max_time_hours,
            accuracy_target=request.accuracy_target,
        )
        mol_type = MoleculeType(request.molecule_type.value)
        viz_type = VisualizationType(request.viz_type.value)
        config = optimizer.optimize(
            molecule_data=request.molecule_data,
            molecule_type=mol_type,
            viz_type=viz_type,
            backend_preference=request.backend_preference,
        )

        # Calculate actual cost using billing integration
        shots = request.shots or config.shots
        estimated_cost = billing.calculate_job_cost(
            shots=shots,
            backend=config.backend_type,
            qec_type=config.qec_code.lower() if config.qec_code else "none",
            num_qubits=config.logical_qubits,
        )

        # Check quota and authorization if API key provided
        if api_key and quota:
            can_execute, error_msg, _ = billing.check_quota_and_charge(
                api_key=api_key,
                shots=shots,
                backend=config.backend_type,
                qec_type=config.qec_code.lower() if config.qec_code else "none",
                num_qubits=config.logical_qubits,
            )

            if not can_execute:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        "error": error_msg,
                        "quota_info": {
                            "tier": quota.tier,
                            "shots_used": quota.shots_used,
                            "shots_limit": quota.shots_limit,
                            "shots_remaining": quota.shots_remaining,
                        },
                        "upgrade_url": "https://api.bioql.bio/pricing",
                    },
                )

        # For free tier or no API key, restrict to simulators only
        elif config.backend_type not in ["qiskit_simulator", "ionq_simulator", "aws_sv1"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Quantum hardware backends require a BioQL API key",
                    "message": "Please provide a BioQL API key to use quantum hardware (IBM, IonQ, AWS)",
                    "register_url": "https://api.bioql.bio/signup",
                    "allowed_backends": ["qiskit_simulator", "ionq_simulator", "aws_sv1"],
                },
            )

        # Create job in queue
        job_id = job_queue.create_job(
            params={
                **request.model_dump(),
                "api_key": api_key,  # Store for usage recording
                "user_email": quota.email if quota else "anonymous",
                "user_tier": quota.tier if quota else "free",
            },
            job_type="quantum_optimization",
            priority=5,
        )

        # Update job with estimate
        job_queue.update_job(
            job_id,
            estimated_cost=estimated_cost,
            estimated_time_remaining=config.time_to_solution_hours * 3600,
        )

        # Start background processing
        background_tasks.add_task(_process_quantum_job_background, job_id, request, api_key)

        response = {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "Quantum job queued successfully",
            "estimated_cost_usd": estimated_cost,
            "estimated_time_hours": config.time_to_solution_hours,
            "backend": config.backend_type,
            "shots": shots,
            "logical_qubits": config.logical_qubits,
            "physical_qubits": config.physical_qubits,
            "status_endpoint": f"/api/jobs/{job_id}/status",
            "result_endpoint": f"/api/jobs/{job_id}/result",
        }

        # Add quota info if authenticated
        if quota:
            response["quota_info"] = {
                "tier": quota.tier,
                "shots_remaining": quota.shots_remaining if quota.tier == "free" else "unlimited",
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quantum job: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/visualize/protein", response_model=JobResponse)
async def visualize_protein(
    request: ProteinVisualizationRequest, background_tasks: BackgroundTasks
):
    """
    Create quantum-enhanced protein visualizations

    Returns job ID for tracking progress
    """
    try:
        # Create job
        job_id = create_job("protein_visualization", request.model_dump())

        # Start background task
        background_tasks.add_task(process_protein_visualization, job_id, request)

        return {
            "job_id": job_id,
            "status": "pending",
            "created_at": jobs[job_id]["created_at"],
            "message": f"Protein visualization job created. Use /api/status/{job_id} to track progress.",
        }

    except Exception as e:
        logger.error(f"Error in endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/visualize/metabolic", response_model=Dict[str, Any])
async def visualize_metabolic_network(request: MetabolicNetworkRequest):
    """
    Create metabolic network visualizations

    Returns paths to generated images
    """
    try:
        # Convert request to MetabolicNetwork
        from visualization.metabolomics.quantum_metabolomics_viz import Metabolite, Reaction

        metabolites = {}
        for met_data in request.metabolites:
            met_id = met_data["id"]
            metabolites[met_id] = Metabolite(**met_data)

        reactions = {}
        for rxn_data in request.reactions:
            rxn_id = rxn_data["id"]
            reactions[rxn_id] = Reaction(**rxn_data)

        network = MetabolicNetwork(
            metabolites=metabolites,
            reactions=reactions,
            name=request.network_name,
            organism=request.organism,
        )

        results = {}

        # Generate requested visualizations
        if "network" in request.visualization_types:
            output_file = f"/tmp/metabolic_{request.network_name}_network.png"
            metabolomics_viz.visualize_metabolic_network(network, output_file)
            results["network"] = output_file

        if "heatmap" in request.visualization_types:
            output_file = f"/tmp/metabolic_{request.network_name}_heatmap.png"
            metabolomics_viz.visualize_metabolite_heatmap(network, output_file=output_file)
            results["heatmap"] = output_file

        if "flux" in request.visualization_types:
            output_file = f"/tmp/metabolic_{request.network_name}_flux.png"
            metabolomics_viz.visualize_flux_analysis(network, output_file)
            results["flux"] = output_file

        # Quantum optimization
        config = metabolomics_viz.quantum_pathway_optimization(
            network, list(network.metabolites.keys())[0]
        )
        results["quantum_config"] = {
            "logical_qubits": config.logical_qubits,
            "physical_qubits": config.physical_qubits,
            "shots": config.shots,
            "backend": config.backend_type,
            "estimated_cost": config.estimated_cost_usd,
        }

        return {
            "success": True,
            "network_name": request.network_name,
            "organism": request.organism,
            "num_metabolites": len(network.metabolites),
            "num_reactions": len(network.reactions),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a visualization job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(**job)


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download generated visualization file"""
    file_path = f"/tmp/{filename}"

    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="image/png", filename=filename)


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs"""
    return {"total_jobs": len(jobs), "jobs": list(jobs.values())}


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results"""
    if job_id not in jobs:
        # Also check job_queue
        if not job_queue.delete_job(job_id):
            raise HTTPException(status_code=404, detail="Job not found")
        return {"message": f"Job {job_id} deleted successfully"}

    # Clean up files (legacy jobs dict)
    job = jobs[job_id]
    if job.get("results"):
        for file_path in job["results"].values():
            if isinstance(file_path, str) and Path(file_path).exists():
                Path(file_path).unlink()

    del jobs[job_id]
    return {"message": f"Job {job_id} deleted successfully"}


# New Quantum Job Endpoints


@app.get("/api/jobs/{job_id}/status")
async def get_quantum_job_status(job_id: str):
    """
    Get status of a quantum job

    Returns:
    - status: pending, running, completed, failed
    - progress: 0-100
    - estimated_time_remaining: seconds
    - cost information
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": job.progress,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "estimated_time_remaining": job.estimated_time_remaining,
        "estimated_cost_usd": job.estimated_cost,
        "actual_cost_usd": job.actual_cost,
        "job_type": job.job_type,
    }

    if job.status == "failed":
        response["error"] = job.error
        response["error_type"] = job.error_type

    return response


@app.get("/api/jobs/{job_id}/result")
async def get_quantum_job_result(job_id: str):
    """
    Get complete result of a quantum job

    Returns:
    - quantum_result: counts, execution metrics
    - quantum_config: qubits, shots, backend
    - visualization_files: paths to generated files
    - execution_metrics: time, cost, accuracy
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed yet. Status: {job.status}")

    if not job.result:
        raise HTTPException(status_code=500, detail="Job completed but no result available")

    # Return full result
    return {
        "job_id": job.job_id,
        "status": "completed",
        "result": job.result,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "execution_time_seconds": job.result.get("execution_metrics", {}).get("total_time_seconds"),
    }


@app.get("/api/jobs/{job_id}/download")
async def download_quantum_job_files(job_id: str):
    """
    Download all visualization files as a ZIP archive

    Includes:
    - All PNG visualizations
    - Interactive HTML plots
    - Report file
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed yet. Status: {job.status}")

    if not job.result or "visualization_files" not in job.result:
        raise HTTPException(status_code=404, detail="No visualization files available")

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for viz_type, file_path in job.result["visualization_files"].items():
            if isinstance(file_path, str):
                path = Path(file_path)
                if path.exists():
                    # Add file to ZIP with a clean name
                    arcname = f"{viz_type}_{path.name}"
                    zip_file.write(file_path, arcname=arcname)
                    logger.info(f"Added {arcname} to ZIP")

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=quantum_job_{job_id}_results.zip"},
    )


@app.get("/api/jobs/{job_id}/files/{filename}")
async def get_quantum_job_file(job_id: str, filename: str):
    """
    Serve individual visualization file

    Supports:
    - PNG images (inline display)
    - HTML interactive plots (inline display)
    - Text reports
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed yet. Status: {job.status}")

    if not job.result or "visualization_files" not in job.result:
        raise HTTPException(status_code=404, detail="No visualization files available")

    # Find file in visualization_files
    file_path = None
    for viz_type, path in job.result["visualization_files"].items():
        if isinstance(path, str):
            if Path(path).name == filename or filename in path:
                file_path = path
                break

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Determine media type
    suffix = Path(file_path).suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".html": "text/html",
        ".txt": "text/plain",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_type_map.get(suffix, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type, filename=filename)


@app.get("/api/queue/stats")
async def get_queue_statistics():
    """Get job queue statistics"""
    return job_queue.get_queue_stats()


# Health check
@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len([j for j in jobs.values() if j["status"] == "running"]),
    }


if __name__ == "__main__":
    print("🚀 Starting Quantum Visualization API Server")
    print("📡 API Documentation: http://localhost:9000/docs")
    print("🔬 Ready to process quantum-enhanced visualizations")
    print("💰 Stripe billing integration enabled\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        log_level="info",
        timeout_keep_alive=300,  # 5 minutes for long-running VQE optimizations
        timeout_graceful_shutdown=30,
    )
