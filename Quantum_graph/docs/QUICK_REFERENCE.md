# Quick Reference: Quantum Graph API

## 🚀 Start Server
```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
python3 backend/api/quantum_viz_api.py
```
**URL**: http://localhost:9000
**Docs**: http://localhost:9000/docs

---

## 📋 Endpoints Cheat Sheet

### 1️⃣ Submit Job (Async)
```bash
curl -X POST http://localhost:9000/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {"smiles": "CCO", "num_atoms": 9, "num_electrons": 20},
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 1024
  }'
```
**Returns**: `job_id`, `estimated_cost`, `estimated_time`

---

### 2️⃣ Check Status
```bash
curl http://localhost:9000/api/jobs/{JOB_ID}/status
```
**Returns**: `status`, `progress`, `estimated_time_remaining`

---

### 3️⃣ Get Results
```bash
curl http://localhost:9000/api/jobs/{JOB_ID}/result
```
**Returns**: quantum counts, config, visualization files, metrics

---

### 4️⃣ Download ZIP
```bash
curl -O -J http://localhost:9000/api/jobs/{JOB_ID}/download
```
**Returns**: `quantum_job_{JOB_ID}_results.zip`

---

### 5️⃣ Download File
```bash
curl http://localhost:9000/api/jobs/{JOB_ID}/files/{FILENAME} -o file.png
```
**Returns**: Individual PNG, HTML, or TXT file

---

### 6️⃣ Queue Stats
```bash
curl http://localhost:9000/api/queue/stats
```
**Returns**: total, pending, running, completed, failed

---

### 7️⃣ Delete Job
```bash
curl -X DELETE http://localhost:9000/api/jobs/{JOB_ID}
```
**Returns**: Success message

---

## 🔄 Complete Workflow (One-Liner)

```bash
# Submit and capture job_id
JOB_ID=$(curl -s -X POST http://localhost:9000/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{"molecule_data":{"smiles":"CCO","num_atoms":9,"num_electrons":20},"molecule_type":"small_molecule","viz_type":"energy_landscape","backend_preference":"qiskit_simulator","shots":1024}' \
  | jq -r '.job_id') && echo "Job ID: $JOB_ID"

# Poll status (repeat until completed)
curl http://localhost:9000/api/jobs/$JOB_ID/status | jq '.status, .progress'

# Get results
curl http://localhost:9000/api/jobs/$JOB_ID/result | jq '.result.quantum_result.backend'

# Download
curl -O -J http://localhost:9000/api/jobs/$JOB_ID/download
```

---

## 🐍 Python Example

```python
import requests
import time

# Submit job
r = requests.post('http://localhost:9000/api/optimize/quantum', json={
    "molecule_data": {"smiles": "CCO", "num_atoms": 9, "num_electrons": 20},
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 1024
})
job_id = r.json()['job_id']
print(f"Job: {job_id}")

# Poll
while True:
    s = requests.get(f'http://localhost:9000/api/jobs/{job_id}/status').json()
    print(f"{s['status']}: {s['progress']}%")
    if s['status'] in ['completed', 'failed']:
        break
    time.sleep(5)

# Results
result = requests.get(f'http://localhost:9000/api/jobs/{job_id}/result').json()
print(f"Cost: ${result['result']['execution_metrics']['total_cost_usd']}")

# Download
with open(f'{job_id}.zip', 'wb') as f:
    f.write(requests.get(f'http://localhost:9000/api/jobs/{job_id}/download').content)
```

---

## 📊 Response Formats

### Job Status States
- `pending` → Job queued, not started
- `running` → Currently executing
- `completed` → Finished successfully
- `failed` → Error occurred

### Molecule Types
`protein`, `dna`, `rna`, `small_molecule`, `antibody`, `protein_complex`, `metabolite`

### Visualization Types
`structure_3d`, `energy_landscape`, `binding_affinity`, `conformational_sampling`, `electron_density`, `molecular_orbitals`, `reaction_pathway`, `protein_folding`, `docking_simulation`

### Backends
`qiskit_simulator`, `ibm_torino`, `ibm_brisbane`, `ionq_simulator`, `ionq_forte`, `aws_sv1`

---

## 💰 Pricing

| Backend | Cost/Shot |
|---------|-----------|
| Qiskit Simulator | $0.01 |
| IBM Quantum | $3.00 |
| IonQ Simulator | $0.01 |
| IonQ QPU | $2.00 |

---

## 🧪 Test Scripts

```bash
# Validate setup
python3 validate_imports.py

# Full API test
./test_api.sh
```

---

## 📁 Files Generated

Each completed job produces:
- `{job_id}_energy_histogram.png`
- `{job_id}_state_distribution.png`
- `{job_id}_molecular_3d.png`
- `{job_id}_interactive.html`
- `{job_id}_report.txt`

---

## ⚠️ Common Issues

**Import errors?**
```bash
export PYTHONPATH=$PYTHONPATH:/Users/heinzjungbluth/Desktop/Quantum_graph
```

**Port 9000 in use?**
Edit line 516 in `quantum_viz_api.py` to use different port

**Missing qiskit?**
```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime
```

---

## 📚 Documentation

- **Full API Docs**: `QUANTUM_API_TESTING.md`
- **Update Summary**: `API_UPDATE_SUMMARY.md`
- **Implementation**: `IMPLEMENTATION_COMPLETE.md`
- **This Guide**: `QUICK_REFERENCE.md`

---

## ✅ Validation

```bash
python3 validate_imports.py
```

Expected output:
```
✓ job_queue imported successfully
✓ QuantumExecutor imported successfully
✓ quantum_viz_api imported successfully
✓ All endpoints registered
✓ ALL VALIDATIONS PASSED
```

---

**Ready to use!** 🎉
