# Quantum Job Queue System

Robust asynchronous job tracking system for managing quantum computation jobs using SQLite.

## Overview

The job queue system provides:
- **Thread-safe** database operations with proper locking
- **Job lifecycle management** (PENDING → RUNNING → COMPLETED/FAILED)
- **Result persistence** with file-based storage
- **Cost tracking** and resource management
- **Error handling** with automatic retry logic
- **Background worker** for asynchronous job processing

## Architecture

```
┌─────────────────┐
│   Client/API    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   JobQueue      │◄────►│   jobs.db        │
│   (Thread-safe) │      │   (SQLite)       │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   Worker        │◄────►│   results/       │
│   (Background)  │      │   (File storage) │
└─────────────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  QuantumViz     │
│  Engine         │
└─────────────────┘
```

## Files

### Core Components

1. **`job_queue.py`** - Job queue manager
   - Thread-safe SQLite operations
   - Job CRUD operations
   - Status management
   - Result persistence

2. **`worker.py`** - Background worker process
   - Polls for pending jobs
   - Executes quantum circuits
   - Updates job status
   - Handles errors and retries

3. **`init_db.py`** - Database initialization
   - Creates database schema
   - Sets up directory structure
   - Initializes indexes

4. **`example_usage.py`** - Usage examples
   - Demonstrates all features
   - Best practices
   - Common patterns

## Database Schema

### Jobs Table

| Column          | Type    | Description                              |
|----------------|---------|------------------------------------------|
| id             | TEXT    | Unique job identifier (UUID)             |
| status         | TEXT    | Job status (PENDING/RUNNING/COMPLETED/FAILED) |
| backend        | TEXT    | Quantum backend name                     |
| molecule_type  | TEXT    | Type of molecule (protein/dna/metabolite)|
| created_at     | TEXT    | Creation timestamp (ISO format)          |
| started_at     | TEXT    | Start timestamp                          |
| completed_at   | TEXT    | Completion timestamp                     |
| result_path    | TEXT    | Path to result JSON file                 |
| error_message  | TEXT    | Error message if failed                  |
| cost           | REAL    | Execution cost in USD                    |
| shots          | INTEGER | Number of quantum circuit shots          |
| molecule_data  | TEXT    | Molecular structure data (JSON)          |
| quantum_config | TEXT    | Quantum configuration (JSON)             |
| progress       | REAL    | Job progress (0-100)                     |
| retry_count    | INTEGER | Current retry attempt                    |
| max_retries    | INTEGER | Maximum retries allowed                  |

### Indexes

- `idx_status` - ON jobs(status)
- `idx_created_at` - ON jobs(created_at DESC)
- `idx_backend` - ON jobs(backend)

## Installation

### 1. Initialize Database

```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
python backend/init_db.py
```

This creates:
- `backend/jobs.db` - SQLite database
- `backend/results/` - Results directory
  - `visualizations/` - Visualization output
  - `logs/` - Log files
  - `exports/` - Export files

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `aiosqlite==0.19.0` - Async SQLite support
- `fastapi==0.104.1` - REST API framework
- `qiskit==0.45.1` - Quantum computing SDK

## Usage

### Starting the Worker

The worker continuously polls for pending jobs and executes them.

**Basic usage:**
```bash
python backend/worker.py
```

**With custom poll interval:**
```bash
python backend/worker.py --poll-interval 10.0
```

**As background daemon (Linux/macOS):**
```bash
nohup python backend/worker.py > worker.log 2>&1 &
```

**Graceful shutdown:**
- Press `Ctrl+C` or send SIGTERM/SIGINT signal
- Worker will complete current job before stopping

### Python API

#### 1. Create Job Queue

```python
from backend.job_queue import JobQueue, JobStatus

# Create queue instance
queue = JobQueue()

# Or with custom paths
queue = JobQueue(
    db_path="/path/to/jobs.db",
    results_dir="/path/to/results"
)
```

#### 2. Submit Job

```python
# Define molecular data
molecule_data = {
    'name': 'my_protein',
    'num_atoms': 250,
    'num_bonds': 245,
    'num_conformations': 15,
    'sequence': 'MKFLKFSLLT...'
}

# Submit job
job_id = queue.create_job(
    molecule_data=molecule_data,
    backend='ibm_quantum',      # Backend: ibm_quantum, aws_braket, auto
    shots=1000,                 # Number of circuit shots
    molecule_type='protein',    # protein, dna, rna, metabolite
    max_retries=3              # Maximum retry attempts
)

print(f"Job ID: {job_id}")
```

#### 3. Monitor Job Status

```python
# Get current status
status = queue.get_job_status(job_id)

print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}%")
print(f"Cost: ${status['cost']:.2f}")
```

#### 4. Get Job Result

```python
# Get result (only for COMPLETED jobs)
result = queue.get_job_result(job_id)

if result['status'] == 'COMPLETED':
    print(f"Energy: {result['data']['ground_state_energy']}")
    print(f"Conformations: {result['data']['num_conformations']}")
    print(f"Visualizations: {result['data']['visualization_files']}")
```

#### 5. Update Job Status (for custom workflows)

```python
# Update status
queue.update_job_status(
    job_id,
    JobStatus.RUNNING,
    progress=50.0
)

# Complete with results
result_data = {
    'energy': -123.45,
    'cost': 2.50,
    'quantum_config': {...}
}

queue.update_job_status(
    job_id,
    JobStatus.COMPLETED,
    result_data=result_data,
    progress=100.0
)
```

#### 6. List Jobs

```python
# Get pending jobs
pending = queue.get_pending_jobs(limit=10)

# Get jobs by status
completed = queue.get_jobs_by_status(JobStatus.COMPLETED, limit=20)
failed = queue.get_jobs_by_status(JobStatus.FAILED, limit=10)

# Get all jobs with pagination
all_jobs = queue.get_all_jobs(limit=100, offset=0)
```

#### 7. Get Statistics

```python
stats = queue.get_statistics()

print(f"Total jobs: {stats['total_jobs']}")
print(f"Total cost: ${stats['total_cost_usd']:.2f}")
print(f"Avg execution time: {stats['avg_execution_time_minutes']:.1f} min")
print(f"Status counts: {stats['status_counts']}")
```

#### 8. Cleanup

```python
# Delete specific job
queue.delete_job(job_id)

# Delete jobs older than 30 days
deleted_count = queue.cleanup_old_jobs(days=30)
print(f"Deleted {deleted_count} old jobs")
```

### REST API Integration

The job queue can be integrated with the existing FastAPI server:

```python
from fastapi import FastAPI, BackgroundTasks
from backend.job_queue import JobQueue, JobStatus

app = FastAPI()
queue = JobQueue()

@app.post("/api/jobs/submit")
async def submit_job(molecule_data: dict, backend: str = "auto"):
    job_id = queue.create_job(
        molecule_data=molecule_data,
        backend=backend,
        molecule_type="protein"
    )
    return {"job_id": job_id, "status": "pending"}

@app.get("/api/jobs/{job_id}/status")
async def get_status(job_id: str):
    status = queue.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@app.get("/api/jobs/{job_id}/result")
async def get_result(job_id: str):
    result = queue.get_job_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return result
```

## Job Status Flow

```
┌─────────┐
│ PENDING │ ◄── Job created
└────┬────┘
     │
     │ Worker picks up job
     ▼
┌─────────┐
│ RUNNING │ ◄── Executing quantum circuit
└────┬────┘
     │
     ├─► Success ──► ┌───────────┐
     │               │ COMPLETED │ ◄── Results stored
     │               └───────────┘
     │
     ├─► Failure ──► ┌──────────┐
     │               │  FAILED  │ ◄── Error message stored
     │               └──────────┘
     │                     │
     └─► Retry? ───────────┘
         (if retry_count < max_retries)
```

## Error Handling

### Automatic Retries

Jobs that fail are automatically retried up to `max_retries` times:

```python
job_id = queue.create_job(
    molecule_data=data,
    backend='ibm_quantum',
    max_retries=3  # Try up to 3 times
)
```

### Manual Retry

```python
# Increment retry count (resets to PENDING)
can_retry = queue.increment_retry_count(job_id)

if not can_retry:
    print("Max retries exceeded - job marked as FAILED")
```

### Error Information

```python
status = queue.get_job_status(job_id)

if status['status'] == 'FAILED':
    print(f"Error: {status['error_message']}")
    print(f"Retries: {status['retry_count']}/{status['max_retries']}")
```

## Configuration

### Database Path

Default: `backend/jobs.db`

Custom:
```python
queue = JobQueue(db_path="/custom/path/jobs.db")
```

### Results Directory

Default: `backend/results/`

Custom:
```python
queue = JobQueue(results_dir="/custom/path/results")
```

### Worker Poll Interval

Default: 5.0 seconds

Custom:
```bash
python backend/worker.py --poll-interval 10.0
```

### Max Concurrent Jobs

Currently: 1 (sequential processing)

Future: Support for parallel job execution

## Performance

### Thread Safety

All database operations use `threading.RLock()` for thread-safe access:
- Multiple threads can submit jobs
- Worker can process jobs concurrently (future)
- No race conditions on status updates

### Database Indexes

Optimized queries with indexes on:
- `status` - Fast pending job lookup
- `created_at` - Chronological ordering
- `backend` - Backend-specific queries

### Result Storage

- Small results (< 1MB): Stored in database
- Large results: Stored as JSON files in `results/`
- Visualizations: Stored as PNG files in job-specific subdirectories

## Monitoring

### Logs

Worker logs to:
- Console (stdout)
- `worker.log` file

Log levels:
- INFO: Normal operations
- ERROR: Failures and exceptions
- WARNING: Retry attempts

### Statistics

```python
stats = queue.get_statistics()
# Returns:
# - total_jobs
# - total_cost_usd
# - avg_execution_time_minutes
# - status_counts (by status)
```

## Examples

See `backend/example_usage.py` for comprehensive examples:

```bash
python backend/example_usage.py
```

Examples include:
1. Basic job submission
2. Job monitoring with progress
3. Batch job submission
4. Error handling and retries
5. Queue statistics
6. Complete job lifecycle

## Troubleshooting

### Worker not picking up jobs

1. Check worker is running:
   ```bash
   ps aux | grep worker.py
   ```

2. Check database path matches:
   ```python
   queue = JobQueue()  # Uses default path
   ```

3. Check job status:
   ```python
   status = queue.get_job_status(job_id)
   print(status['status'])  # Should be PENDING
   ```

### Jobs stuck in RUNNING

1. Check worker logs:
   ```bash
   tail -f worker.log
   ```

2. Manually reset job:
   ```python
   queue.update_job_status(job_id, JobStatus.PENDING)
   ```

### Database locked errors

- Increase timeout (SQLite default: 5s)
- Reduce concurrent access
- Use connection pooling (future enhancement)

## Future Enhancements

- [ ] Async/await support with aiosqlite
- [ ] Multiple concurrent workers
- [ ] Priority queue
- [ ] Job dependencies (workflow)
- [ ] WebSocket status updates
- [ ] Job cancellation
- [ ] Scheduled jobs
- [ ] Job templates
- [ ] Performance metrics
- [ ] Distributed worker pool

## License

Copyright © 2025 Spectrix R&D / BioQL Team

---

**Last Updated:** October 25, 2025
