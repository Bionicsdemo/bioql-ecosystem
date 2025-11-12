# Quick Start Guide - Quantum Job Queue

Get up and running with the quantum job queue system in 5 minutes.

## Step 1: Initialize Database (1 minute)

```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
python backend/init_db.py
```

Expected output:
```
✅ Database created: backend/jobs.db
✅ Results directory created: backend/results/
```

## Step 2: Start the Worker (1 minute)

Open a **new terminal** and run:

```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
python backend/worker.py
```

Expected output:
```
🚀 Quantum Worker started
📊 Poll interval: 5.0s
⚡ Max concurrent jobs: 1
```

**Keep this terminal open!** The worker needs to run continuously.

## Step 3: Submit Your First Job (1 minute)

Open **another terminal** or Python shell:

```python
from backend.job_queue import JobQueue

# Create queue
queue = JobQueue()

# Submit job
job_id = queue.create_job(
    molecule_data={
        'name': 'my_first_protein',
        'num_atoms': 100,
        'num_bonds': 98
    },
    backend='ibm_quantum',
    shots=1000,
    molecule_type='protein'
)

print(f"Job ID: {job_id}")
```

## Step 4: Monitor the Job (2 minutes)

Check status:

```python
# Get status
status = queue.get_job_status(job_id)
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}%")
```

Watch the worker terminal - you'll see it pick up and process your job!

Wait for completion (usually 30-60 seconds), then get results:

```python
# Get result
result = queue.get_job_result(job_id)

if result['status'] == 'COMPLETED':
    print("✅ Job completed!")
    print(f"Energy: {result['data']['ground_state_energy']}")
    print(f"Cost: ${result['data']['cost']:.2f}")
    print(f"Visualizations: {result['data']['visualization_files']}")
else:
    print(f"Status: {result['status']}")
```

## Step 5: View Results

Check the results directory:

```bash
ls -lh backend/results/{job_id}/
```

You'll find:
- `{name}_3d.png` - 3D molecular structure
- `{name}_energy.png` - Energy landscape

## That's It! 🎉

You now have a fully functional quantum job queue system.

## Next Steps

### Run Examples

See all features in action:

```bash
python backend/example_usage.py
```

### Integrate with API

See `backend/api_integration_example.py` for REST API integration.

### Read Full Documentation

See `backend/JOB_QUEUE_README.md` for complete documentation.

## Common Commands

### Submit a job:
```python
job_id = queue.create_job(molecule_data={...})
```

### Check status:
```python
status = queue.get_job_status(job_id)
```

### Get result:
```python
result = queue.get_job_result(job_id)
```

### Get statistics:
```python
stats = queue.get_statistics()
```

### List all jobs:
```python
jobs = queue.get_all_jobs(limit=10)
```

## Troubleshooting

### Worker not processing jobs?

1. Make sure worker is running:
   ```bash
   ps aux | grep worker.py
   ```

2. Check worker logs:
   ```bash
   tail -f worker.log
   ```

### Job stuck in PENDING?

1. Restart the worker:
   - Press Ctrl+C in worker terminal
   - Run `python backend/worker.py` again

### Need help?

Check the full documentation: `backend/JOB_QUEUE_README.md`

---

**You're ready to process quantum computations asynchronously!**
