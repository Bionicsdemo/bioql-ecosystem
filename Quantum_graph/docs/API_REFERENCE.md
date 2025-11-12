# Quantum Graphs API Reference

Complete API documentation for quantum-enhanced scientific visualization.

## Base URL

```
http://localhost:9000
```

Production: `https://api.quantum-graphs.bio`

## Authentication

All API requests require a BioQL API key for quantum hardware backends. Simulators can be used without authentication.

### Headers

```http
Authorization: Bearer YOUR_BIOQL_API_KEY
```

Or:

```http
X-API-Key: YOUR_BIOQL_API_KEY
```

Get your API key at: [https://api.bioql.bio/signup](https://api.bioql.bio/signup)

---

## Endpoints

### 1. Quantum Optimization Job

**POST** `/api/optimize/quantum`

Execute a quantum computing job for molecular visualization with automatic parameter optimization.

#### Request Body

```json
{
  "molecule_data": {
    "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "num_atoms": 23,
    "molecular_weight": 206.28
  },
  "molecule_type": "small_molecule",
  "viz_type": "conformational_sampling",
  "backend_preference": "ibm_torino",
  "shots": 1024,
  "budget_usd": 100.0,
  "max_time_hours": 24.0,
  "accuracy_target": 0.95
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `molecule_data` | object | Yes | Molecular structure data |
| `molecule_type` | string | Yes | Type of molecule (see [Molecule Types](#molecule-types)) |
| `viz_type` | string | Yes | Visualization type (see [Visualization Types](#visualization-types)) |
| `backend_preference` | string | No | Quantum backend (default: "auto") |
| `shots` | integer | No | Number of quantum measurements (100-100000, default: 1024) |
| `budget_usd` | float | No | Maximum budget in USD |
| `max_time_hours` | float | No | Maximum time constraint in hours |
| `accuracy_target` | float | No | Target accuracy 0-1 (default: 0.95) |

#### Molecule Types

- `protein` - Protein structures
- `dna` - DNA sequences
- `rna` - RNA sequences
- `small_molecule` - Small organic molecules
- `antibody` - Antibody structures
- `protein_complex` - Multi-protein complexes
- `metabolite` - Metabolic compounds

#### Visualization Types

- `structure_3d` - 3D molecular structure
- `energy_landscape` - Energy landscape visualization
- `binding_affinity` - Drug-target binding
- `conformational_sampling` - Conformational space sampling
- `electron_density` - Electron density maps
- `molecular_orbitals` - Molecular orbital visualization
- `reaction_pathway` - Chemical reaction pathways
- `protein_folding` - Protein folding dynamics
- `docking_simulation` - Molecular docking simulation

#### Response

```json
{
  "success": true,
  "job_id": "a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6",
  "status": "pending",
  "message": "Quantum job queued successfully",
  "estimated_cost_usd": 3.072,
  "estimated_time_hours": 0.0156,
  "backend": "ibm_torino",
  "shots": 1024,
  "logical_qubits": 12,
  "physical_qubits": 576,
  "status_endpoint": "/api/jobs/a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6/status",
  "result_endpoint": "/api/jobs/a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6/result",
  "quota_info": {
    "tier": "pro",
    "shots_remaining": "unlimited"
  }
}
```

#### Example: cURL

```bash
curl -X POST http://localhost:9000/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "molecule_data": {
      "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
      "num_atoms": 21
    },
    "molecule_type": "small_molecule",
    "viz_type": "conformational_sampling",
    "backend_preference": "ibm_torino",
    "shots": 1024
  }'
```

#### Example: Python

```python
import requests

url = "http://localhost:9000/api/optimize/quantum"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}
data = {
    "molecule_data": {
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
        "num_atoms": 21
    },
    "molecule_type": "small_molecule",
    "viz_type": "conformational_sampling",
    "backend_preference": "ibm_torino",
    "shots": 1024
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
job_id = result['job_id']
print(f"Job created: {job_id}")
```

---

### 2. Get Job Status

**GET** `/api/jobs/{job_id}/status`

Check the status of a quantum job.

#### Response

```json
{
  "job_id": "a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6",
  "status": "completed",
  "progress": 100.0,
  "created_at": "2025-10-26T12:00:00Z",
  "started_at": "2025-10-26T12:00:05Z",
  "completed_at": "2025-10-26T12:15:30Z",
  "estimated_time_remaining": 0,
  "estimated_cost_usd": 3.072,
  "actual_cost_usd": 3.072,
  "job_type": "quantum_optimization"
}
```

#### Job Status Values

- `pending` - Job queued, not yet started
- `running` - Job executing on quantum hardware
- `completed` - Job finished successfully
- `failed` - Job encountered an error

#### Example: cURL

```bash
curl http://localhost:9000/api/jobs/a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6/status
```

#### Example: Python (Polling)

```python
import time
import requests

job_id = "a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6"
url = f"http://localhost:9000/api/jobs/{job_id}/status"

while True:
    response = requests.get(url)
    status = response.json()

    print(f"Status: {status['status']} - Progress: {status['progress']:.1f}%")

    if status['status'] in ['completed', 'failed']:
        break

    time.sleep(5)  # Check every 5 seconds
```

---

### 3. Get Job Result

**GET** `/api/jobs/{job_id}/result`

Retrieve the complete results of a completed quantum job.

#### Response

```json
{
  "job_id": "a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6",
  "status": "completed",
  "result": {
    "quantum_result": {
      "backend": "ibm_torino",
      "counts": {
        "000000000000": 234,
        "000000000001": 189,
        "000000000010": 156,
        "...": "..."
      },
      "execution_time": 923.4,
      "cost_usd": 3.072
    },
    "quantum_config": {
      "logical_qubits": 12,
      "physical_qubits": 576,
      "shots": 1024,
      "circuit_depth": 240,
      "backend_type": "ibm_torino",
      "estimated_cost_usd": 3.072,
      "time_to_solution_hours": 0.0156
    },
    "molecular_complexity": {
      "num_atoms": 21,
      "num_heavy_atoms": 17,
      "num_electrons": 126,
      "molecular_weight": 180.16,
      "conformational_space_size": 8.77
    },
    "visualization_files": {
      "energy_landscape": "/tmp/job_a7f2b3c4_energy_landscape.png",
      "histogram": "/tmp/job_a7f2b3c4_histogram.png",
      "statevector": "/tmp/job_a7f2b3c4_statevector.png",
      "report": "/tmp/job_a7f2b3c4_report.txt"
    },
    "execution_metrics": {
      "total_time_seconds": 923.4,
      "accuracy": 0.95,
      "total_cost_usd": 3.072
    }
  },
  "created_at": "2025-10-26T12:00:00Z",
  "completed_at": "2025-10-26T12:15:30Z",
  "execution_time_seconds": 930.0
}
```

#### Example: cURL

```bash
curl http://localhost:9000/api/jobs/a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6/result
```

---

### 4. Download Visualization Files

**GET** `/api/jobs/{job_id}/download`

Download all visualization files as a ZIP archive.

#### Response

Binary ZIP file containing:
- All PNG visualizations
- Interactive HTML plots
- Report file (TXT)

#### Example: cURL

```bash
curl http://localhost:9000/api/jobs/a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6/download \
  -o results.zip
```

#### Example: Python

```python
import requests

job_id = "a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6"
url = f"http://localhost:9000/api/jobs/{job_id}/download"

response = requests.get(url)
with open('quantum_results.zip', 'wb') as f:
    f.write(response.content)

print("Results downloaded!")
```

---

### 5. Get Individual File

**GET** `/api/jobs/{job_id}/files/{filename}`

Download a specific visualization file.

#### Example: cURL

```bash
curl http://localhost:9000/api/jobs/a7f2b3c4/files/energy_landscape_job_a7f2b3c4.png \
  -o energy_landscape.png
```

---

### 6. Queue Statistics

**GET** `/api/queue/stats`

Get statistics about the job queue.

#### Response

```json
{
  "total_jobs": 45,
  "pending_jobs": 3,
  "running_jobs": 2,
  "completed_jobs": 38,
  "failed_jobs": 2,
  "total_shots_processed": 156742,
  "total_cost_usd": 523.45
}
```

---

### 7. Health Check

**GET** `/health`

Check API health status.

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-10-26T12:30:45Z",
  "active_jobs": 2
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid molecule_type. Must be one of: protein, dna, rna, small_molecule, antibody, protein_complex, metabolite"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid API key. Get your API key at https://api.bioql.bio"
}
```

### 402 Payment Required

```json
{
  "detail": {
    "error": "Quota exceeded",
    "quota_info": {
      "tier": "free",
      "shots_used": 1200,
      "shots_limit": 1000,
      "shots_remaining": 0
    },
    "upgrade_url": "https://api.bioql.bio/pricing"
  }
}
```

### 404 Not Found

```json
{
  "detail": "Job not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Quantum execution failed: Backend timeout"
}
```

---

## Rate Limits

### Free Tier

- 1000 shots/month
- 10 requests/minute
- Simulator backends only

### Pro Tier ($49/month)

- Unlimited shots
- 100 requests/minute
- All backends available
- Priority queue

### Enterprise Tier (Custom)

- Unlimited shots
- Unlimited requests
- Dedicated resources
- Custom SLA

---

## Cost Calculation

### Backend Pricing

| Backend | Type | Cost per Shot |
|---------|------|---------------|
| `qiskit_simulator` | Simulator | $0.00 (FREE) |
| `ionq_simulator` | Simulator | $0.01 |
| `aws_sv1` | Simulator | $0.01 |
| `ibm_torino` | Hardware | $3.00 |
| `ibm_brisbane` | Hardware | $1.25 |
| `ionq_forte` | Hardware | $3.00 |
| `ionq_qpu` | Hardware | $2.00 |

### Example Calculations

**Small molecule, 1024 shots, IBM Torino:**
```
Cost = 1024 shots × $3.00/shot = $3,072.00
```

**Protein, 5000 shots, IonQ Simulator:**
```
Cost = 5000 shots × $0.01/shot = $50.00
```

**DNA, 2048 shots, Qiskit Simulator:**
```
Cost = 2048 shots × $0.00/shot = $0.00
```

### QEC Overhead

Quantum Error Correction codes increase physical qubit requirements:

- **Surface Code**: 1.5x multiplier
- **Steane Code**: 2.0x multiplier
- **Shor Code**: 2.5x multiplier

---

## Best Practices

### 1. Start with Simulators

Test your workflows with free simulators before using expensive quantum hardware:

```json
{
  "backend_preference": "qiskit_simulator",
  "shots": 1024
}
```

### 2. Use Budget Constraints

Set budget limits to prevent unexpected costs:

```json
{
  "budget_usd": 50.0,
  "max_time_hours": 2.0
}
```

### 3. Optimize Shot Count

Use minimum shots needed for your accuracy target:

- Quick tests: 1024 shots
- Standard: 2048-4096 shots
- High accuracy: 8192+ shots

### 4. Poll Status Efficiently

Check job status every 5-10 seconds, not continuously:

```python
time.sleep(5)  # Good
# time.sleep(0.1)  # Too frequent
```

### 5. Handle Errors Gracefully

```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 402:
        print("Quota exceeded - upgrade at api.bioql.bio")
    else:
        print(f"Error: {e}")
```

---

## Code Examples

### Complete Workflow (Python)

```python
import requests
import time

# Configuration
API_KEY = "your_bioql_api_key"
BASE_URL = "http://localhost:9000"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Step 1: Submit job
job_data = {
    "molecule_data": {
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "num_atoms": 21
    },
    "molecule_type": "small_molecule",
    "viz_type": "conformational_sampling",
    "backend_preference": "qiskit_simulator",
    "shots": 1024
}

response = requests.post(
    f"{BASE_URL}/api/optimize/quantum",
    headers=headers,
    json=job_data
)
result = response.json()
job_id = result['job_id']
print(f"✅ Job created: {job_id}")
print(f"💰 Estimated cost: ${result['estimated_cost_usd']:.2f}")

# Step 2: Poll for completion
while True:
    status = requests.get(f"{BASE_URL}/api/jobs/{job_id}/status").json()
    print(f"Status: {status['status']} ({status['progress']:.0f}%)")

    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        print(f"❌ Job failed: {status.get('error')}")
        exit(1)

    time.sleep(5)

# Step 3: Get results
result = requests.get(f"{BASE_URL}/api/jobs/{job_id}/result").json()
print(f"✅ Job completed!")
print(f"Qubits used: {result['result']['quantum_config']['logical_qubits']}")
print(f"Total cost: ${result['result']['execution_metrics']['total_cost_usd']:.2f}")

# Step 4: Download files
download = requests.get(f"{BASE_URL}/api/jobs/{job_id}/download")
with open('results.zip', 'wb') as f:
    f.write(download.content)
print(f"📦 Results downloaded to results.zip")
```

### JavaScript/TypeScript

```javascript
const API_KEY = 'your_bioql_api_key';
const BASE_URL = 'http://localhost:9000';

async function runQuantumJob() {
  // Submit job
  const response = await fetch(`${BASE_URL}/api/optimize/quantum`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      molecule_data: {
        smiles: 'CC(=O)OC1=CC=CC=C1C(=O)O',
        num_atoms: 21
      },
      molecule_type: 'small_molecule',
      viz_type: 'conformational_sampling',
      backend_preference: 'qiskit_simulator',
      shots: 1024
    })
  });

  const result = await response.json();
  const jobId = result.job_id;
  console.log(`✅ Job created: ${jobId}`);

  // Poll for completion
  while (true) {
    const statusRes = await fetch(`${BASE_URL}/api/jobs/${jobId}/status`);
    const status = await statusRes.json();
    console.log(`Status: ${status.status} (${status.progress}%)`);

    if (status.status === 'completed') break;
    if (status.status === 'failed') {
      console.error('Job failed');
      return;
    }

    await new Promise(resolve => setTimeout(resolve, 5000));
  }

  // Get results
  const resultRes = await fetch(`${BASE_URL}/api/jobs/${jobId}/result`);
  const finalResult = await resultRes.json();
  console.log('✅ Job completed!', finalResult);
}

runQuantumJob();
```

---

## WebSocket Support (Coming Soon)

Real-time job status updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:9000/ws/jobs/{job_id}');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Progress: ${update.progress}%`);
};
```

---

## Support

- Documentation: [https://docs.quantum-graphs.bio](https://docs.quantum-graphs.bio)
- API Issues: [https://github.com/bioql/quantum-graphs/issues](https://github.com/bioql/quantum-graphs/issues)
- Email: support@quantum-graphs.bio
- Discord: [https://discord.gg/bioql](https://discord.gg/bioql)
