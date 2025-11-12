#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Billing Integration for Quantum Graphs
============================================

Integrates Quantum_graph with BioQL authentication and Stripe billing system.

Features:
- API key validation via BioQL auth server
- Usage tracking and metering
- Automatic Stripe billing
- Quota enforcement (free tier vs paid)
- Cost calculation and tracking

Dependencies:
    pip install requests stripe

Configuration:
    BIOQL_AUTH_SERVER_URL: URL of BioQL auth server
    STRIPE_SECRET_KEY: Stripe API key (optional, uses BioQL's)
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
# Use internal localhost connection for faster response (same server)
BIOQL_AUTH_SERVER_URL = os.getenv("BIOQL_AUTH_SERVER_URL", "http://127.0.0.1:5001")

# Pricing configuration (matches BioQL auth server)
PRICING = {
    "simulator_cost_per_shot": 0.01,  # $0.01 per shot (simulator)
    "quantum_cost_per_shot": 3.00,  # $3.00 per shot (quantum hardware)
    "llm_inference_cost": 0.0005,  # $0.0005 per inference
    "free_tier_shots": 1000,  # Free tier: 1000 shots/month
    "free_tier_inferences": 100,  # Free tier: 100 LLM calls/month
    # QEC (Quantum Error Correction) overhead pricing
    "qec_multiplier": {"surface_code": 1.5, "steane": 2.0, "shor": 2.5, "none": 1.0},
    "qubit_overhead_cost": 0.0001,
}

# Backend pricing
BACKEND_PRICING = {
    # Simulators (cheap)
    "qiskit_simulator": 0.00,  # FREE
    "ionq_simulator": 0.01,  # $0.01/shot
    "aws_sv1": 0.01,  # $0.01/shot
    # Quantum Hardware (expensive)
    "ibm_torino": 3.00,  # $3.00/shot
    "ibm_brisbane": 1.25,  # $1.25/shot
    "ionq_forte": 3.00,  # $3.00/shot
    "ionq_qpu": 2.00,  # $2.00/shot
}


@dataclass
class UserQuota:
    """User quota and usage information."""

    user_id: str
    email: str
    tier: str  # 'free', 'pro', 'enterprise'
    shots_used: int
    shots_limit: int
    inferences_used: int
    inferences_limit: int
    current_balance: float  # USD
    stripe_customer_id: Optional[str] = None

    @property
    def shots_remaining(self) -> int:
        """Calculate remaining shots."""
        if self.tier != "free":
            return float("inf")  # Unlimited for paid tiers
        return max(0, self.shots_limit - self.shots_used)

    @property
    def can_execute(self) -> bool:
        """Check if user can execute more jobs."""
        if self.tier != "free":
            return True  # Paid tiers always allowed
        return self.shots_remaining > 0


class BillingIntegration:
    """Main billing integration class for Quantum Graphs."""

    def __init__(self, auth_server_url: str = BIOQL_AUTH_SERVER_URL):
        """Initialize billing integration.

        Args:
            auth_server_url: URL of BioQL auth server
        """
        self.auth_server_url = auth_server_url
        self.cache = {}  # Simple in-memory cache for user data
        self.cache_ttl = timedelta(minutes=5)

        logger.info(f"✅ Billing integration initialized (auth server: {auth_server_url})")

    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate API key with BioQL auth server.

        Args:
            api_key: BioQL API key

        Returns:
            Tuple of (is_valid, user_data)
        """
        try:
            response = requests.post(
                f"{self.auth_server_url}/auth/validate", json={"api_key": api_key}, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    user_data = data.get("user", {})
                    logger.info(f"✅ API key validated for user: {user_data.get('email')}")
                    return True, user_data

            logger.warning(f"❌ Invalid API key")
            return False, None

        except Exception as e:
            logger.error(f"❌ API key validation error: {e}")
            return False, None

    def get_user_quota(self, api_key: str) -> Optional[UserQuota]:
        """Get user quota and usage information.

        Args:
            api_key: BioQL API key

        Returns:
            UserQuota object or None if invalid
        """
        # Check cache first
        cache_key = hashlib.sha256(api_key.encode()).hexdigest()
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                logger.info("📦 Using cached quota data")
                return cached_data

        # Validate API key and get user data with quota
        # NOTE: /auth/validate returns both user data AND quota in a single response
        try:
            response = requests.post(
                f"{self.auth_server_url}/auth/validate", json={"api_key": api_key}, timeout=5
            )

            if response.status_code == 200:
                data = response.json()

                if not data.get("valid"):
                    logger.warning("❌ Invalid API key")
                    return None

                user_data = data.get("user", {})
                quota_data = data.get("quota", {})

                logger.info(
                    f"📊 Quota data received: shots_used={quota_data.get('shots_used')}, balance={user_data.get('balance')}"
                )

                # Create UserQuota object
                quota = UserQuota(
                    user_id=user_data.get("id"),
                    email=user_data.get("email"),
                    tier=user_data.get("tier", "free"),
                    shots_used=quota_data.get("shots_used", 0),
                    shots_limit=PRICING["free_tier_shots"],
                    inferences_used=quota_data.get("inferences_used", 0),
                    inferences_limit=PRICING["free_tier_inferences"],
                    current_balance=user_data.get("balance", 0.0),
                    stripe_customer_id=user_data.get("stripe_customer_id"),
                )

                # Cache the result
                self.cache[cache_key] = (quota, datetime.now())

                logger.info(
                    f"✅ Quota loaded for {user_data.get('email')}: tier={quota.tier}, shots_remaining={quota.shots_remaining}"
                )
                return quota
            else:
                logger.error(f"❌ Failed to validate API key: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error fetching quota: {e}")
            import traceback

            logger.error(traceback.format_exc())

        return None

    def calculate_job_cost(
        self, shots: int, backend: str, qec_type: str = "none", num_qubits: int = 10
    ) -> float:
        """Calculate cost for a quantum job.

        Args:
            shots: Number of circuit shots
            backend: Quantum backend name
            qec_type: QEC code type
            num_qubits: Number of qubits

        Returns:
            Cost in USD
        """
        # Get base cost per shot
        cost_per_shot = BACKEND_PRICING.get(backend, PRICING["quantum_cost_per_shot"])

        # Calculate base cost
        base_cost = shots * cost_per_shot

        # Apply QEC multiplier
        qec_multiplier = PRICING["qec_multiplier"].get(qec_type, 1.0)
        total_cost = base_cost * qec_multiplier

        # Add qubit overhead
        qubit_overhead = num_qubits * PRICING["qubit_overhead_cost"]
        total_cost += qubit_overhead

        return round(total_cost, 4)

    def check_quota_and_charge(
        self, api_key: str, shots: int, backend: str, qec_type: str = "none", num_qubits: int = 10
    ) -> Tuple[bool, Optional[str], float]:
        """Check if user has quota and can be charged.

        Args:
            api_key: BioQL API key
            shots: Number of shots
            backend: Quantum backend
            qec_type: QEC code type
            num_qubits: Number of qubits

        Returns:
            Tuple of (success, error_message, cost)
        """
        # Get user quota
        quota = self.get_user_quota(api_key)
        if not quota:
            return False, "Invalid API key", 0.0

        # Calculate cost
        cost = self.calculate_job_cost(shots, backend, qec_type, num_qubits)

        # Check quota for free tier
        if quota.tier == "free":
            if quota.shots_used + shots > quota.shots_limit:
                shots_remaining = quota.shots_remaining
                return (
                    False,
                    f"Quota exceeded. Free tier allows {quota.shots_limit} shots/month. You have {shots_remaining} shots remaining.",
                    cost,
                )

        # For paid tiers or if within free tier, proceed
        logger.info(f"✅ Quota check passed for {quota.email}: {shots} shots, ${cost:.4f}")
        return True, None, cost

    def record_usage(
        self,
        api_key: str,
        shots: int,
        backend: str,
        cost: float,
        job_id: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Record usage to BioQL auth server and Stripe.

        Args:
            api_key: BioQL API key
            shots: Number of shots executed
            backend: Quantum backend used
            cost: Actual cost in USD
            job_id: Quantum job ID
            metadata: Additional metadata

        Returns:
            True if successful
        """
        try:
            # Invalidate cache for this user
            cache_key = hashlib.sha256(api_key.encode()).hexdigest()
            if cache_key in self.cache:
                del self.cache[cache_key]

            # Record usage via auth server
            response = requests.post(
                f"{self.auth_server_url}/auth/usage",
                json={
                    "api_key": api_key,
                    "service": "quantum_graphs",
                    "shots": shots,
                    "backend": backend,
                    "cost": cost,
                    "job_id": job_id,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata or {},
                },
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f"✅ Usage recorded: {shots} shots, ${cost:.4f}, backend={backend}")
                return True
            else:
                logger.error(f"❌ Failed to record usage: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error recording usage: {e}")
            return False

    def get_pricing_info(self) -> Dict[str, Any]:
        """Get pricing information.

        Returns:
            Dictionary with pricing details
        """
        return {
            "backends": BACKEND_PRICING,
            "qec_multipliers": PRICING["qec_multiplier"],
            "free_tier": {
                "shots_per_month": PRICING["free_tier_shots"],
                "inferences_per_month": PRICING["free_tier_inferences"],
            },
            "currency": "USD",
            "notes": "Costs are per shot. QEC multipliers apply to base cost.",
        }


# Singleton instance
_billing_integration = None


def get_billing_integration() -> BillingIntegration:
    """Get singleton billing integration instance."""
    global _billing_integration
    if _billing_integration is None:
        _billing_integration = BillingIntegration()
    return _billing_integration


# Example usage
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("BIOQL BILLING INTEGRATION - TEST")
    print("=" * 80)

    billing = BillingIntegration()

    # Test pricing calculation
    print("\n1. PRICING CALCULATION TEST")
    print("-" * 80)

    test_cases = [
        ("qiskit_simulator", 1000, "none", 10),
        ("ionq_simulator", 1000, "none", 15),
        ("ibm_torino", 1000, "surface_code", 20),
        ("ionq_forte", 5000, "surface_code", 25),
    ]

    for backend, shots, qec, qubits in test_cases:
        cost = billing.calculate_job_cost(shots, backend, qec, qubits)
        print(f"{backend:20} | {shots:5} shots | QEC:{qec:12} | {qubits:2} qubits | ${cost:8.4f}")

    # Test API key validation (will fail without real key)
    print("\n2. API KEY VALIDATION TEST")
    print("-" * 80)
    print("Testing with dummy API key (expected to fail):")

    test_key = "bioql_test_key_12345"
    is_valid, user_data = billing.validate_api_key(test_key)
    print(f"Valid: {is_valid}")
    if user_data:
        print(f"User: {user_data}")

    # Show pricing info
    print("\n3. PRICING INFORMATION")
    print("-" * 80)
    pricing_info = billing.get_pricing_info()
    print(json.dumps(pricing_info, indent=2))

    print("\n" + "=" * 80)
    print("✅ Billing integration test complete")
    print("=" * 80)
