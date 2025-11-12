# Quantum Graph API Testing Guide

## Overview

The Quantum Graph API has been updated with real quantum execution and file download capabilities.

## New Features

1. **Asynchronous Job Queue System**
   - Jobs are queued and processed in the background
   - Real-time progress tracking
   - Cost estimation and monitoring

2. **Real Quantum Execution**
   - Executes on quantum backends (simulators or real hardware)
   - Generates actual quantum measurement results
   - Creates visualizations from quantum data

3. **File Download System**
   - Download individual files (PNG, HTML)
   - Download all files as ZIP archive
   - Proper CORS headers for browser downloads

## API Endpoints

### 1. Submit Quantum Job (Async)

**Endpoint:** `POST /api/optimize/quantum`

**Description:** Submit a quantum visualization job. Returns immediately with job_id.

**Example Request:**

```bash
curl -X POST http://localhost:9000/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {
      "smiles": "CCO",
      "num_atoms": 9,
      "num_electrons": 20
    },
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 2048,
    "accuracy_target": 0.95,
    "budget_usd": 10.0,
    "max_time_hours": 1.0
  }'
```

**Example Response:**

```json
{
  "success": true,
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Quantum job queued successfully",
  "estimated_cost_usd": 2.45,
  "estimated_time_hours": 0.25,
  "status_endpoint": "/api/jobs/{job_id}/status",
  "result_endpoint": "/api/jobs/{job_id}/result"
}
```

---

### 2. Get Job Status

**Endpoint:** `GET /api/jobs/{job_id}/status`

**Description:** Get current status and progress of a job.

**Example Request:**

```bash
curl http://localhost:9000/api/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status
```

**Example Response (Running):**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "progress": 45.0,
  "created_at": "2025-10-25T10:30:00.000000",
  "started_at": "2025-10-25T10:30:05.000000",
  "completed_at": null,
  "estimated_time_remaining": 120.5,
  "estimated_cost_usd": 2.45,
  "actual_cost_usd": null,
  "job_type": "quantum_optimization"
}
```

**Example Response (Completed):**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": 100.0,
  "created_at": "2025-10-25T10:30:00.000000",
  "started_at": "2025-10-25T10:30:05.000000",
  "completed_at": "2025-10-25T10:35:42.000000",
  "estimated_time_remaining": 0,
  "estimated_cost_usd": 2.45,
  "actual_cost_usd": 2.048,
  "job_type": "quantum_optimization"
}
```

---

### 3. Get Job Result

**Endpoint:** `GET /api/jobs/{job_id}/result`

**Description:** Get complete results including quantum data and visualization files.

**Example Request:**

```bash
curl http://localhost:9000/api/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/result
```

**Example Response:**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "result": {
    "status": "completed",
    "quantum_result": {
      "backend": "qiskit_simulator",
      "counts": {
        "0000": 245,
        "0001": 198,
        "0010": 156,
        "0011": 142,
        "...": "..."
      },
      "execution_time": 3.45,
      "cost_usd": 2.048
    },
    "quantum_config": {
      "logical_qubits": 4,
      "physical_qubits": 4,
      "shots": 2048,
      "circuit_depth": 12,
      "backend_type": "qiskit_simulator",
      "estimated_cost_usd": 2.45,
      "time_to_solution_hours": 0.001
    },
    "molecular_complexity": {
      "num_atoms": 9,
      "num_heavy_atoms": 3,
      "num_electrons": 20,
      "molecular_weight": 46.07,
      "conformational_space_size": 512
    },
    "visualization_files": {
      "energy_histogram": "/tmp/quantum_viz/a1b2c3d4_energy_histogram.png",
      "state_distribution": "/tmp/quantum_viz/a1b2c3d4_state_distribution.png",
      "molecular_3d": "/tmp/quantum_viz/a1b2c3d4_molecular_3d.png",
      "interactive": "/tmp/quantum_viz/a1b2c3d4_interactive.html",
      "report": "/tmp/quantum_viz/a1b2c3d4_report.txt"
    },
    "execution_metrics": {
      "total_time_seconds": 342.5,
      "accuracy": 0.95,
      "total_cost_usd": 2.048
    }
  },
  "created_at": "2025-10-25T10:30:00.000000",
  "completed_at": "2025-10-25T10:35:42.000000",
  "execution_time_seconds": 342.5
}
```

---

### 4. Download All Files (ZIP)

**Endpoint:** `GET /api/jobs/{job_id}/download`

**Description:** Download all visualization files as a ZIP archive.

**Example Request:**

```bash
curl -O -J http://localhost:9000/api/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download
```

**Response:**
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename=quantum_job_{job_id}_results.zip`
- Downloads file named: `quantum_job_a1b2c3d4_results.zip`

**ZIP Contents:**
```
energy_histogram_a1b2c3d4_energy_histogram.png
state_distribution_a1b2c3d4_state_distribution.png
molecular_3d_a1b2c3d4_molecular_3d.png
interactive_a1b2c3d4_interactive.html
report_a1b2c3d4_report.txt
```

---

### 5. Download Individual File

**Endpoint:** `GET /api/jobs/{job_id}/files/{filename}`

**Description:** Download or view a specific visualization file.

**Example Requests:**

```bash
# View PNG image in browser
curl http://localhost:9000/api/jobs/a1b2c3d4/files/a1b2c3d4_energy_histogram.png \
  --output energy_histogram.png

# View interactive HTML
curl http://localhost:9000/api/jobs/a1b2c3d4/files/a1b2c3d4_interactive.html \
  --output interactive.html

# View report
curl http://localhost:9000/api/jobs/a1b2c3d4/files/a1b2c3d4_report.txt
```

**Response:**
- Content-Type: Appropriate for file type (image/png, text/html, etc.)
- File content

---

### 6. Queue Statistics

**Endpoint:** `GET /api/queue/stats`

**Description:** Get job queue statistics.

**Example Request:**

```bash
curl http://localhost:9000/api/queue/stats
```

**Example Response:**

```json
{
  "total_jobs": 15,
  "pending": 3,
  "running": 2,
  "completed": 8,
  "failed": 2,
  "max_concurrent": 2,
  "can_start_new": false
}
```

---

### 7. Delete Job

**Endpoint:** `DELETE /api/jobs/{job_id}`

**Description:** Delete a job and all associated files.

**Example Request:**

```bash
curl -X DELETE http://localhost:9000/api/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Example Response:**

```json
{
  "message": "Job a1b2c3d4-e5f6-7890-abcd-ef1234567890 deleted successfully"
}
```

---

## Complete Workflow Example

### Step 1: Submit Job

```bash
JOB_RESPONSE=$(curl -s -X POST http://localhost:9000/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {"smiles": "CCO", "num_atoms": 9, "num_electrons": 20},
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 1024
  }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"
```

### Step 2: Poll Status

```bash
while true; do
  STATUS=$(curl -s http://localhost:9000/api/jobs/$JOB_ID/status | jq -r '.status')
  PROGRESS=$(curl -s http://localhost:9000/api/jobs/$JOB_ID/status | jq -r '.progress')

  echo "Status: $STATUS, Progress: $PROGRESS%"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi

  sleep 5
done
```

### Step 3: Get Results

```bash
curl -s http://localhost:9000/api/jobs/$JOB_ID/result | jq '.'
```

### Step 4: Download Files

```bash
# Download ZIP of all files
curl -O -J http://localhost:9000/api/jobs/$JOB_ID/download

# Or download individual files
curl http://localhost:9000/api/jobs/$JOB_ID/files/${JOB_ID}_energy_histogram.png \
  --output energy_histogram.png
```

---

## Python Example

```python
import requests
import time
import json

# Base URL
BASE_URL = "http://localhost:9000"

# Step 1: Submit job
response = requests.post(f"{BASE_URL}/api/optimize/quantum", json={
    "molecule_data": {
        "smiles": "CCO",
        "num_atoms": 9,
        "num_electrons": 20
    },
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 1024
})

job_data = response.json()
job_id = job_data['job_id']
print(f"Job submitted: {job_id}")

# Step 2: Poll for completion
while True:
    status_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}/status")
    status_data = status_response.json()

    print(f"Status: {status_data['status']}, Progress: {status_data['progress']}%")

    if status_data['status'] in ['completed', 'failed']:
        break

    time.sleep(5)

# Step 3: Get results
if status_data['status'] == 'completed':
    result_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}/result")
    result_data = result_response.json()

    print(f"Quantum counts: {result_data['result']['quantum_result']['counts']}")
    print(f"Cost: ${result_data['result']['execution_metrics']['total_cost_usd']}")

    # Step 4: Download ZIP
    download_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}/download")
    with open(f"quantum_job_{job_id}.zip", 'wb') as f:
        f.write(download_response.content)
    print(f"Downloaded results.zip")
```

---

## Error Handling

### Job Not Found (404)

```bash
curl http://localhost:9000/api/jobs/invalid-id/status
```

Response:
```json
{
  "detail": "Job not found"
}
```

### Job Not Completed (400)

```bash
curl http://localhost:9000/api/jobs/{pending_job_id}/result
```

Response:
```json
{
  "detail": "Job not completed yet. Status: pending"
}
```

### Job Failed

Check status endpoint for error details:
```json
{
  "status": "failed",
  "error": "Quantum execution failed: Circuit too deep",
  "error_type": "CircuitError"
}
```

---

## Starting the Server

```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
python3 backend/api/quantum_viz_api.py
```

Server starts on: `http://localhost:9000`

API docs: `http://localhost:9000/docs`

---

## Notes

1. **File Storage**: Visualization files are stored in `/tmp/quantum_viz/` by default
2. **Cleanup**: Use the DELETE endpoint to clean up old jobs and files
3. **Concurrency**: Max 2 concurrent jobs by default (configurable in job_queue.py)
4. **Cost Tracking**: Real costs are tracked and returned in results
5. **CORS**: Enabled for all origins with proper headers for file downloads

---

## Troubleshooting

### Import Errors

If you get import errors, ensure you're in the project root:
```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 backend/api/quantum_viz_api.py
```

### Missing Dependencies

```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime matplotlib plotly numpy
```

### Files Not Found

Ensure `/tmp/quantum_viz` directory exists:
```bash
mkdir -p /tmp/quantum_viz
```
