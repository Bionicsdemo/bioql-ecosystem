#!/usr/bin/env python3
"""
Simple billing integration for quantum() function
"""

import sqlite3
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

def get_database_path() -> Path:
    """Get the path to the billing database"""
    # Database is now in data/databases/
    db_path = Path(__file__).parent.parent / "data" / "databases" / "bioql_billing.db"
    return db_path

def authenticate_user(api_key: str) -> Optional[Dict[str, Any]]:
    """Authenticate user by API key"""
    if not api_key:
        return None

    try:
        # Hash the API key to match database storage
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Connect to billing database
        conn = sqlite3.connect(str(get_database_path()))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Find user by API key hash
        cursor.execute("""
            SELECT u.id, u.email, u.first_name, u.last_name, u.current_plan, u.is_active, ak.id as api_key_id
            FROM users u
            JOIN api_keys ak ON u.id = ak.user_id
            WHERE ak.key_hash = ? AND ak.is_active = 1 AND u.is_active = 1
        """, (api_key_hash,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'user_id': result['id'],
                'email': result['email'],
                'name': f"{result['first_name']} {result['last_name']}".strip(),
                'plan': result['current_plan'],
                'api_key_id': result['api_key_id']
            }

        return None

    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def log_usage(user_id: str, api_key_id: str, program: str, backend: str, shots: int,
              success: bool, execution_time: float, error_message: str = None,
              cost: float = 0.0, result_data: Dict = None) -> None:
    """Log quantum usage to database"""

    try:
        conn = sqlite3.connect(str(get_database_path()))
        cursor = conn.cursor()

        # Generate usage log entry
        usage_id = str(uuid.uuid4())
        program_hash = hashlib.sha256(program.encode()).hexdigest()
        now = datetime.utcnow().isoformat()

        # Estimate circuit complexity based on program content
        qubits = estimate_qubits_from_program(program)
        algorithm = classify_algorithm(program)

        # Calculate pricing
        base_cost_per_shot = get_backend_cost_per_shot(backend)
        complexity_multiplier = get_complexity_multiplier(qubits)
        algorithm_multiplier = get_algorithm_multiplier(algorithm)

        total_cost = shots * base_cost_per_shot * complexity_multiplier * algorithm_multiplier

        # Insert usage log
        cursor.execute("""
            INSERT INTO usage_logs (
                id, user_id, api_key_id, program_text, program_hash,
                circuit_qubits, circuit_depth, circuit_gates,
                algorithm_type, backend_requested, backend_used, backend_type,
                shots_requested, shots_executed, success, execution_time,
                error_message, base_cost_per_shot, complexity_multiplier,
                algorithm_multiplier, total_cost, billed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usage_id, user_id, api_key_id, program[:1000], program_hash,
            qubits, 0, 0,  # circuit_depth and circuit_gates estimated as 0 for now
            algorithm, backend, backend, classify_backend_type(backend),
            shots, shots if success else 0, success, execution_time,
            error_message, str(base_cost_per_shot), complexity_multiplier,
            algorithm_multiplier, str(total_cost), False, now, now
        ))

        conn.commit()
        conn.close()

        print(f"💰 Usage logged: {user_id[:8]}... | {shots} shots | ${total_cost:.4f}")

    except Exception as e:
        print(f"Billing error: {e}")

def estimate_qubits_from_program(program: str) -> int:
    """Estimate number of qubits from program description"""
    program_lower = program.lower()

    # Look for explicit qubit counts
    if "2-qubit" in program_lower or "2 qubit" in program_lower or "bell" in program_lower:
        return 2
    elif "4-qubit" in program_lower or "4 qubit" in program_lower:
        return 4
    elif "6-qubit" in program_lower or "6 qubit" in program_lower:
        return 6
    elif "8-qubit" in program_lower or "8 qubit" in program_lower:
        return 8
    elif "3-qubit" in program_lower or "3 qubit" in program_lower:
        return 3
    elif "5-qubit" in program_lower or "5 qubit" in program_lower:
        return 5

    # Keywords that suggest more qubits
    if "molecular" in program_lower or "protein" in program_lower:
        return 6
    elif "vqe" in program_lower or "variational" in program_lower:
        return 4
    elif "grover" in program_lower:
        return 3
    elif "fourier" in program_lower or "qft" in program_lower:
        return 4

    # Default to 2 qubits for simple circuits
    return 2

def classify_algorithm(program: str) -> str:
    """Classify algorithm type from program description"""
    program_lower = program.lower()

    if "vqe" in program_lower or "variational" in program_lower:
        return "vqe"
    elif "grover" in program_lower:
        return "grover"
    elif "shor" in program_lower:
        return "shor"
    elif "qaoa" in program_lower:
        return "qaoa"
    elif "fourier" in program_lower or "qft" in program_lower:
        return "qft"
    elif "bell" in program_lower:
        return "bell"
    else:
        return "basic"

def get_backend_cost_per_shot(backend: str) -> float:
    """Get cost per shot for different backends"""
    backend_costs = {
        'simulator': 0.001,
        'aer': 0.001,
        'sim': 0.001,
        'ibm_': 0.01,  # Any IBM backend
        'ionq_': 0.02  # Any IonQ backend
    }

    backend_lower = backend.lower()
    for prefix, cost in backend_costs.items():
        if backend_lower.startswith(prefix):
            return cost

    return 0.005  # Default cost

def get_complexity_multiplier(qubits: int) -> float:
    """Get complexity multiplier based on number of qubits"""
    if qubits <= 2:
        return 1.0
    elif qubits <= 4:
        return 1.5
    elif qubits <= 6:
        return 2.0
    elif qubits <= 8:
        return 3.0
    else:
        return 5.0

def get_algorithm_multiplier(algorithm: str) -> float:
    """Get algorithm complexity multiplier"""
    multipliers = {
        'basic': 1.0,
        'bell': 1.0,
        'qft': 1.5,
        'grover': 2.0,
        'vqe': 2.5,
        'qaoa': 2.5,
        'shor': 3.0
    }
    return multipliers.get(algorithm, 1.0)

def classify_backend_type(backend: str) -> str:
    """Classify backend type"""
    backend_lower = backend.lower()
    if backend_lower in ['simulator', 'aer', 'sim']:
        return 'simulator'
    elif backend_lower.startswith('ibm_'):
        return 'ibm_quantum'
    elif backend_lower.startswith('ionq_'):
        return 'ionq'
    else:
        return 'unknown'