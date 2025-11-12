# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

cat > /root/bioql_quantum_server/quantum_execution_server.py << 'ENDOFFILE'
#!/usr/bin/env python3
"""
BioQL Quantum Execution Server
Executes quantum circuits on real hardware (IBM Torino) or simulators
"""

import json
import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directory to path to import bioql
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Spectrix_framework'))

try:
    from bioql.cloud_auth import authenticate_api_key, record_usage
    from bioql.quantum_connector import QuantumResult
    from bioql.quantum_connector import quantum as quantum_internal
    BIOQL_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importing BioQL: {e}")
    BIOQL_AVAILABLE = False

# Configuration
PORT = int(os.getenv('BIOQL_QUANTUM_PORT', 5002))
HOST = os.getenv('BIOQL_QUANTUM_HOST', '0.0.0.0'))

# Create Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

print("="*80)
print("🌐 BioQL Quantum Execution Server")
print("="*80)
print(f"Port: {PORT}")
print(f"Host: {HOST}")
print(f"BioQL Available: {BIOQL_AVAILABLE}")
print("="*80)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "service": "BioQL Quantum Execution Server",
        "status": "healthy",
        "version": "1.0.0",
        "bioql_available": BIOQL_AVAILABLE
    })


@app.route('/api/quantum/execute', methods=['POST'])
def execute_quantum():
    """Execute quantum program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        program = data.get('program')
        api_key = data.get('api_key')
        backend = data.get('backend', 'simulator')
        shots = data.get('shots', 1024)

        if not program:
            return jsonify({"error": "Missing 'program' field"}), 400
        if not api_key:
            return jsonify({"error": "Missing 'api_key' field"}), 400

        print(f"\n{'='*80}")
        print(f"📊 Quantum Execution Request")
        print(f"{'='*80}")
        print(f"Time: {datetime.now().isoformat()}")
        print(f"Backend: {backend}")
        print(f"Shots: {shots}")
        print(f"{'='*80}\n")

        # Authenticate
        try:
            user_info = authenticate_api_key(api_key)
            print(f"✅ Authenticated: {user_info.get('email', 'unknown')}")
        except Exception as auth_error:
            print(f"❌ Authentication failed: {auth_error}")
            return jsonify({
                "error": "Authentication failed",
                "message": str(auth_error)
            }), 401

        if not BIOQL_AVAILABLE:
            return jsonify({"error": "BioQL not available"}), 500

        # Execute quantum program
        try:
            print(f"🚀 Executing quantum program on {backend}...")
            result = quantum_internal(
                program=program,
                api_key=api_key,
                backend=backend,
                shots=shots,
                debug=False
            )
            print(f"✅ Quantum execution complete!")

            # Convert result to dict
            if isinstance(result, QuantumResult):
                result_dict = {
                    "success": result.success,
                    "backend": result.backend,
                    "shots": result.shots,
                    "counts": result.counts if hasattr(result, 'counts') else {},
                    "bio_interpretation": result.bio_interpretation if hasattr(result, 'bio_interpretation') else {},
                    "message": result.message if hasattr(result, 'message') else "",
                    "execution_time": result.execution_time if hasattr(result, 'execution_time') else 0,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                result_dict = {
                    "success": True,
                    "result": str(result),
                    "backend": backend,
                    "shots": shots,
                    "timestamp": datetime.now().isoformat()
                }

            # Record usage for billing
            try:
                record_usage(
                    api_key=api_key,
                    shots=shots,
                    backend=backend,
                    success=result_dict.get('success', True)
                )
                print(f"✅ Usage recorded for billing")
            except Exception as billing_error:
                print(f"⚠️  Billing recording failed: {billing_error}")

            return jsonify(result_dict), 200

        except Exception as exec_error:
            print(f"❌ Quantum execution failed: {exec_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": "Quantum execution failed",
                "message": str(exec_error),
                "backend": backend,
                "timestamp": datetime.now().isoformat()
            }), 500

    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/stats', methods=['GET'])
def stats():
    """Get server statistics"""
    return jsonify({
        "service": "BioQL Quantum Execution Server",
        "version": "1.0.0",
        "bioql_available": BIOQL_AVAILABLE,
        "endpoints": [
            "POST /api/quantum/execute",
            "GET /health",
            "GET /stats"
        ]
    })


if __name__ == '__main__':
    if not BIOQL_AVAILABLE:
        print("❌ ERROR: BioQL not available!")
        sys.exit(1)

    print(f"\n🚀 Starting BioQL Quantum Execution Server on {HOST}:{PORT}...")
    print(f"   Health: http://{HOST}:{PORT}/health")
    print(f"   Endpoint: http://{HOST}:{PORT}/api/quantum/execute")
    print("\n")

    app.run(host=HOST, port=PORT, debug=False)
ENDOFFILE
