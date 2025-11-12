#!/usr/bin/env python3
"""
Tiered billing system with rate limiting and usage analytics
"""

import sqlite3
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import calendar

def get_database_path() -> Path:
    """Get the path to the billing database"""
    db_path = Path(__file__).parent.parent / "data" / "databases" / "bioql_billing.db"
    return db_path

def authenticate_user(api_key: str) -> Optional[Dict[str, Any]]:
    """Authenticate user by API key and load tier information"""
    if not api_key:
        return None

    try:
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get user with tier information
        cursor.execute("""
            SELECT
                u.id, u.email, u.name,
                u.current_plan, u.is_active, u.tier_id,
                ak.id as api_key_id,
                t.name as tier_name,
                t.display_name as tier_display_name,
                t.quota_simulator, t.quota_gpu, t.quota_quantum,
                t.rate_limit_per_minute,
                t.overage_simulator, t.overage_gpu, t.overage_quantum
            FROM users u
            JOIN api_keys ak ON u.id = ak.user_id
            LEFT JOIN pricing_tiers t ON u.tier_id = t.id
            WHERE ak.key_hash = ? AND ak.is_active = 1 AND u.is_active = 1
        """, (api_key_hash,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'user_id': result['id'],
                'email': result['email'],
                'name': result['name'] or 'Unknown',
                'plan': result['current_plan'],
                'api_key_id': result['api_key_id'],
                'tier_id': result['tier_id'] or 'tier_free',
                'tier_name': result['tier_name'] or 'free',
                'tier_display_name': result['tier_display_name'] or 'Free Trial',
                'quota_simulator': result['quota_simulator'] or 50,
                'quota_gpu': result['quota_gpu'] or 10,
                'quota_quantum': result['quota_quantum'] or 3,
                'rate_limit_per_minute': result['rate_limit_per_minute'] or 10,
                'overage_simulator': result['overage_simulator'] or 0.0,
                'overage_gpu': result['overage_gpu'] or 0.0,
                'overage_quantum': result['overage_quantum'] or 0.0
            }

        return None

    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def check_rate_limit(user_id: str, rate_limit: int) -> Tuple[bool, int]:
    """
    Check if user has exceeded rate limit
    Returns: (is_allowed, requests_remaining)
    """
    try:
        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        cursor = conn.cursor()

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)

        # Clean old entries
        cursor.execute("""
            DELETE FROM rate_limit_tracker
            WHERE window_end < ?
        """, (window_start.isoformat(),))

        # Get current window count
        cursor.execute("""
            SELECT requests_count
            FROM rate_limit_tracker
            WHERE user_id = ? AND window_start >= ?
        """, (user_id, window_start.isoformat()))

        result = cursor.fetchone()
        current_count = result[0] if result else 0

        if current_count >= rate_limit:
            conn.close()
            return False, 0

        # Increment counter
        tracker_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT OR REPLACE INTO rate_limit_tracker
            (id, user_id, window_start, window_end, requests_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tracker_id, user_id, window_start.isoformat(),
            now.isoformat(), current_count + 1, now.isoformat()
        ))

        conn.commit()
        conn.close()

        return True, rate_limit - (current_count + 1)

    except Exception as e:
        print(f"Rate limit check error: {e}")
        return True, rate_limit  # Fail open

def get_monthly_usage(user_id: str) -> Dict[str, int]:
    """Get current month's usage"""
    try:
        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.utcnow()
        year = now.year
        month = now.month

        cursor.execute("""
            SELECT simulator_used, gpu_used, quantum_used
            FROM monthly_usage_summary
            WHERE user_id = ? AND year = ? AND month = ?
        """, (user_id, year, month))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'simulator': result['simulator_used'],
                'gpu': result['gpu_used'],
                'quantum': result['quantum_used']
            }

        return {'simulator': 0, 'gpu': 0, 'quantum': 0}

    except Exception as e:
        print(f"Get usage error: {e}")
        return {'simulator': 0, 'gpu': 0, 'quantum': 0}

def check_quota(user_id: str, backend_type: str, user_info: Dict) -> Tuple[bool, str]:
    """
    Check if user has quota remaining
    Returns: (is_allowed, reason)
    """
    usage = get_monthly_usage(user_id)

    if backend_type == 'simulator':
        quota = user_info['quota_simulator']
        used = usage['simulator']
        backend_name = 'simulator'
    elif backend_type == 'gpu':
        quota = user_info['quota_gpu']
        used = usage['gpu']
        backend_name = 'GPU'
    elif backend_type == 'quantum':
        quota = user_info['quota_quantum']
        used = usage['quantum']
        backend_name = 'quantum'
    else:
        return True, ""  # Unknown backend type, allow

    # Unlimited quota
    if quota >= 999999:
        return True, ""

    if used >= quota:
        overage_key = f'overage_{backend_type}'
        overage_price = user_info.get(overage_key, 0.0)

        if overage_price > 0:
            return True, f"⚠️  Quota exceeded. Overage billing at ${overage_price}/request"
        else:
            return False, f"❌ Monthly {backend_name} quota exceeded ({used}/{quota}). Upgrade tier or wait for next billing cycle."

    remaining = quota - used
    return True, f"✅ Quota remaining: {remaining}/{quota}"

def increment_usage(user_id: str, backend_type: str, count: int = 1) -> None:
    """Increment monthly usage counter"""
    try:
        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        cursor = conn.cursor()

        now = datetime.utcnow()
        year = now.year
        month = now.month

        summary_id = str(uuid.uuid4())

        # Get current tier quotas
        cursor.execute("""
            SELECT quota_simulator, quota_gpu, quota_quantum
            FROM pricing_tiers t
            JOIN users u ON u.tier_id = t.id
            WHERE u.id = ?
        """, (user_id,))

        quotas = cursor.fetchone()
        if not quotas:
            quotas = (50, 10, 3)  # Default free tier

        # Update or insert monthly summary
        cursor.execute("""
            INSERT INTO monthly_usage_summary (
                id, user_id, year, month,
                simulator_used, gpu_used, quantum_used,
                simulator_quota, gpu_quota, quantum_quota,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, year, month) DO UPDATE SET
                simulator_used = simulator_used + ?,
                gpu_used = gpu_used + ?,
                quantum_used = quantum_used + ?,
                updated_at = ?
        """, (
            summary_id, user_id, year, month,
            count if backend_type == 'simulator' else 0,
            count if backend_type == 'gpu' else 0,
            count if backend_type == 'quantum' else 0,
            quotas[0], quotas[1], quotas[2],
            now.isoformat(), now.isoformat(),
            count if backend_type == 'simulator' else 0,
            count if backend_type == 'gpu' else 0,
            count if backend_type == 'quantum' else 0,
            now.isoformat()
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Increment usage error: {e}")

def calculate_backend_cost(backend: str, backend_type: str, shots: int, user_info: Dict) -> float:
    """Calculate cost based on backend type and pricing tier from database"""

    # Base pricing per shot (within quota) - 50% of overage price
    base_pricing = {
        'simulator': 0.00005,  # Half of overage ($0.0001)
        'gpu': 0.005,  # Half of overage ($0.01)
        'quantum': 2.5,  # Half of overage ($5.0)
    }

    # Check for overage
    usage = get_monthly_usage(user_info['user_id'])
    quota_key = f'quota_{backend_type}'
    usage_key = backend_type

    quota = user_info.get(quota_key, 0)
    used = usage.get(usage_key, 0)

    if used >= quota and quota < 999999:  # Over quota - use overage pricing
        overage_key = f'overage_{backend_type}'
        # Get overage price from user's tier (from database)
        cost_per_shot = user_info.get(overage_key, base_pricing.get(backend_type, 0.0))
    else:
        # Within quota - use base pricing
        cost_per_shot = base_pricing.get(backend_type, 0.0)

    # Total cost = shots × price per shot
    total_cost = cost_per_shot * shots
    return total_cost

def log_usage(user_id: str, api_key_id: str, program: str, backend: str, shots: int,
              success: bool, execution_time: float, error_message: str = None,
              cost: float = 0.0, result_data: Dict = None, user_info: Dict = None) -> None:
    """Log quantum usage with tier-aware pricing"""

    try:
        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        cursor = conn.cursor()

        usage_id = str(uuid.uuid4())
        program_hash = hashlib.sha256(program.encode()).hexdigest()
        now = datetime.utcnow().isoformat()

        # Classify backend type
        backend_type = classify_backend_type(backend)

        # Calculate real cost
        if user_info:
            real_cost = calculate_backend_cost(backend, backend_type, shots, user_info)
        else:
            real_cost = cost

        # Estimate circuit parameters
        qubits = estimate_qubits_from_program(program)
        algorithm = classify_algorithm(program)

        # Insert usage log (using only columns that exist in the table)
        cursor.execute("""
            INSERT INTO usage_logs (
                id, user_id, api_key_id, shots_executed, backend_used,
                algorithm_type, total_cost, execution_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usage_id, user_id, api_key_id, shots if success else 0, backend,
            algorithm, real_cost, execution_time, now
        ))

        # Increment usage counter
        if success:
            increment_usage(user_id, backend_type, 1)

        # Update usage analytics
        update_usage_analytics(user_id, backend_type, success, execution_time, real_cost)

        conn.commit()
        conn.close()

        tier_name = user_info.get('tier_display_name', 'Unknown') if user_info else 'Unknown'
        print(f"💰 [{tier_name}] {user_id[:8]}... | {backend_type} | ${real_cost:.4f}")

    except Exception as e:
        print(f"Billing error: {e}")

def update_usage_analytics(user_id: str, backend_type: str, success: bool,
                          execution_time: float, cost: float) -> None:
    """Update usage analytics for the current period"""
    try:
        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        cursor = conn.cursor()

        now = datetime.utcnow()
        # Current month period
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        period_end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

        analytics_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO usage_analytics (
                id, user_id, period_start, period_end,
                total_requests, simulator_requests, gpu_requests, quantum_requests,
                successful_requests, failed_requests,
                avg_execution_time, total_execution_time,
                total_cost, simulator_cost, gpu_cost, quantum_cost,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, period_start, period_end) DO UPDATE SET
                total_requests = total_requests + 1,
                simulator_requests = simulator_requests + ?,
                gpu_requests = gpu_requests + ?,
                quantum_requests = quantum_requests + ?,
                successful_requests = successful_requests + ?,
                failed_requests = failed_requests + ?,
                total_execution_time = total_execution_time + ?,
                total_cost = total_cost + ?,
                simulator_cost = simulator_cost + ?,
                gpu_cost = gpu_cost + ?,
                quantum_cost = quantum_cost + ?,
                updated_at = ?
        """, (
            analytics_id, user_id,
            period_start.isoformat(), period_end.isoformat(),
            1,  # total_requests
            1 if backend_type == 'simulator' else 0,
            1 if backend_type == 'gpu' else 0,
            1 if backend_type == 'quantum' else 0,
            1 if success else 0,
            0 if success else 1,
            execution_time, execution_time,
            cost,
            cost if backend_type == 'simulator' else 0,
            cost if backend_type == 'gpu' else 0,
            cost if backend_type == 'quantum' else 0,
            now.isoformat(), now.isoformat(),
            # ON CONFLICT updates
            1 if backend_type == 'simulator' else 0,
            1 if backend_type == 'gpu' else 0,
            1 if backend_type == 'quantum' else 0,
            1 if success else 0,
            0 if success else 1,
            execution_time,
            cost,
            cost if backend_type == 'simulator' else 0,
            cost if backend_type == 'gpu' else 0,
            cost if backend_type == 'quantum' else 0,
            now.isoformat()
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Analytics update error: {e}")

def estimate_qubits_from_program(program: str) -> int:
    """Estimate number of qubits from program description"""
    program_lower = program.lower()

    if "2-qubit" in program_lower or "2 qubit" in program_lower or "bell" in program_lower:
        return 2
    elif "4-qubit" in program_lower or "4 qubit" in program_lower:
        return 4
    elif "6-qubit" in program_lower or "6 qubit" in program_lower:
        return 6
    elif "8-qubit" in program_lower or "8 qubit" in program_lower:
        return 8

    if "molecular" in program_lower or "protein" in program_lower or "docking" in program_lower:
        return 6
    elif "vqe" in program_lower or "variational" in program_lower:
        return 4

    return 2

def classify_algorithm(program: str) -> str:
    """Classify algorithm type from program description"""
    program_lower = program.lower()

    if "vqe" in program_lower or "variational" in program_lower:
        return "vqe"
    elif "grover" in program_lower:
        return "grover"
    elif "qaoa" in program_lower:
        return "qaoa"
    elif "docking" in program_lower or "molecular" in program_lower:
        return "molecular_docking"
    else:
        return "basic"

def classify_backend_type(backend: str) -> str:
    """Classify backend type"""
    backend_lower = backend.lower()

    if 'simulator' in backend_lower or 'aer' in backend_lower or backend_lower == 'sim':
        return 'simulator'
    elif 'gpu' in backend_lower or 'vina' in backend_lower or 'modal' in backend_lower:
        return 'gpu'
    elif 'ibm' in backend_lower or 'ionq' in backend_lower or 'quantum' in backend_lower:
        return 'quantum'
    else:
        return 'simulator'  # Default to simulator

def get_user_analytics(user_id: str) -> Dict[str, Any]:
    """Get user's usage analytics for current month"""
    try:
        conn = sqlite3.connect(str(get_database_path()), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        cursor.execute("""
            SELECT * FROM usage_analytics
            WHERE user_id = ? AND period_start >= ?
        """, (user_id, period_start.isoformat()))

        result = cursor.fetchone()
        conn.close()

        if result:
            return dict(result)

        return {}

    except Exception as e:
        print(f"Get analytics error: {e}")
        return {}
