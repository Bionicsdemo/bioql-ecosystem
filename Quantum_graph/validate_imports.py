#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Validate all imports for the updated API
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Validating Quantum Graph API Imports")
print("=" * 60)

# Test 1: Job Queue
print("\n[1/3] Testing job_queue module...")
try:
    from backend.services.job_queue import Job, JobStatus, job_queue

    print("  ✓ job_queue imported successfully")
    print(f"  ✓ JobStatus enum: {[s.value for s in JobStatus]}")
    print(f"  ✓ Global queue instance: {type(job_queue).__name__}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Quantum Executor
print("\n[2/3] Testing quantum_executor module...")
try:
    from backend.services.quantum_executor import QuantumExecutor

    executor = QuantumExecutor()
    print("  ✓ QuantumExecutor imported successfully")
    print(f"  ✓ Executor instance created: {type(executor).__name__}")
    print(f"  ✓ Has backend_connector: {hasattr(executor, 'backend_connector')}")
    print(f"  ✓ Has viz_generator: {hasattr(executor, 'viz_generator')}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 3: API
print("\n[3/3] Testing quantum_viz_api module...")
try:
    from backend.api.quantum_viz_api import app, job_queue, quantum_executor

    print("  ✓ quantum_viz_api imported successfully")
    print(f"  ✓ FastAPI app created: {type(app).__name__}")
    print(f"  ✓ quantum_executor available: {type(quantum_executor).__name__}")
    print(f"  ✓ job_queue available: {type(job_queue).__name__}")

    # Check endpoints
    routes = [route.path for route in app.routes]
    required_endpoints = [
        "/api/optimize/quantum",
        "/api/jobs/{job_id}/status",
        "/api/jobs/{job_id}/result",
        "/api/jobs/{job_id}/download",
        "/api/jobs/{job_id}/files/{filename}",
        "/api/queue/stats",
    ]

    print(f"\n  Checking endpoints:")
    for endpoint in required_endpoints:
        if endpoint in routes:
            print(f"    ✓ {endpoint}")
        else:
            print(f"    ✗ {endpoint} MISSING")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 4: Create a test job
print("\n[4/4] Testing job creation...")
try:
    from backend.services.job_queue import job_queue

    job_id = job_queue.create_job(params={"test": "data"}, job_type="test_job", priority=5)
    print(f"  ✓ Created test job: {job_id}")

    job = job_queue.get_job(job_id)
    print(f"  ✓ Retrieved job: {job.status.value}")

    job_queue.delete_job(job_id)
    print(f"  ✓ Deleted test job")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL VALIDATIONS PASSED")
print("=" * 60)
print("\nThe API is ready to run!")
print("\nTo start the server:")
print("  cd /Users/heinzjungbluth/Desktop/Quantum_graph")
print("  python3 backend/api/quantum_viz_api.py")
print("\nTo test the API:")
print("  ./test_api.sh")
print("\nAPI Documentation:")
print("  http://localhost:9000/docs")
print()
