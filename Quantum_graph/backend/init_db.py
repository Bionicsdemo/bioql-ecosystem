# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Database Initialization Script
===============================

Initializes the job queue database and creates necessary directories.

Usage:
    python init_db.py

Author: Spectrix R&D / BioQL Team
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.job_queue import JobQueue


def init_database():
    """
    Initialize the job queue database and directory structure
    """
    print("=" * 80)
    print("🔬 QUANTUM JOB QUEUE - DATABASE INITIALIZATION")
    print("=" * 80)

    backend_dir = Path(__file__).parent
    db_path = backend_dir / "jobs.db"
    results_dir = backend_dir / "results"

    print(f"\n📂 Backend directory: {backend_dir}")
    print(f"💾 Database path: {db_path}")
    print(f"📁 Results directory: {results_dir}")

    # Create job queue (this will initialize the database)
    print("\n⚙️  Creating database tables...")
    queue = JobQueue(db_path=str(db_path), results_dir=str(results_dir))

    # Verify database was created
    if db_path.exists():
        print(f"✅ Database created: {db_path}")
        print(f"   Size: {db_path.stat().st_size} bytes")
    else:
        print(f"❌ Failed to create database")
        return False

    # Verify results directory
    if results_dir.exists():
        print(f"✅ Results directory created: {results_dir}")
    else:
        print(f"❌ Failed to create results directory")
        return False

    # Create subdirectories
    subdirs = ["visualizations", "logs", "exports"]
    for subdir in subdirs:
        subdir_path = results_dir / subdir
        subdir_path.mkdir(exist_ok=True, parents=True)
        print(f"✅ Created subdirectory: {subdir_path}")

    # Display schema information
    print("\n📊 Database Schema:")
    print("-" * 80)
    print(
        """
    Table: jobs
    -----------
    - id                TEXT PRIMARY KEY      : Unique job identifier (UUID)
    - status            TEXT NOT NULL         : Job status (PENDING/RUNNING/COMPLETED/FAILED)
    - backend           TEXT NOT NULL         : Quantum backend name
    - molecule_type     TEXT NOT NULL         : Type of molecule (protein/dna/metabolite)
    - created_at        TEXT NOT NULL         : Creation timestamp (ISO format)
    - started_at        TEXT                  : Start timestamp
    - completed_at      TEXT                  : Completion timestamp
    - result_path       TEXT                  : Path to result file
    - error_message     TEXT                  : Error message if failed
    - cost              REAL DEFAULT 0.0      : Execution cost in USD
    - shots             INTEGER DEFAULT 1000  : Number of quantum circuit shots
    - molecule_data     TEXT                  : Molecular structure data (JSON)
    - quantum_config    TEXT                  : Quantum configuration (JSON)
    - progress          REAL DEFAULT 0.0      : Job progress (0-100)
    - retry_count       INTEGER DEFAULT 0     : Current retry count
    - max_retries       INTEGER DEFAULT 3     : Maximum retries allowed

    Indexes:
    --------
    - idx_status      : ON jobs(status)
    - idx_created_at  : ON jobs(created_at DESC)
    - idx_backend     : ON jobs(backend)
    """
    )

    # Get initial statistics
    stats = queue.get_statistics()
    print("\n📈 Initial Statistics:")
    print("-" * 80)
    print(f"Total jobs:       {stats['total_jobs']}")
    print(f"Status counts:    {stats['status_counts']}")
    print(f"Total cost:       ${stats['total_cost_usd']:.2f}")
    print(f"Avg exec time:    {stats['avg_execution_time_minutes']:.1f} minutes")

    print("\n" + "=" * 80)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("=" * 80)

    print("\n📖 Next Steps:")
    print("-" * 80)
    print("1. Start the worker:")
    print("   python backend/worker.py")
    print()
    print("2. Or with custom poll interval:")
    print("   python backend/worker.py --poll-interval 10.0")
    print()
    print("3. Submit jobs via API or programmatically:")
    print("   from backend.job_queue import JobQueue")
    print("   queue = JobQueue()")
    print("   job_id = queue.create_job(molecule_data, backend='ibm_quantum')")
    print()
    print("4. Monitor jobs:")
    print("   status = queue.get_job_status(job_id)")
    print("   result = queue.get_job_result(job_id)")
    print()

    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
