# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum_graph Stripe Billing Integration
=========================================

Integrates Quantum_graph visualization costs with existing BioQL Stripe billing

Pricing Model:
- Quantum visualization jobs charged based on:
  * Backend used (simulator=free, IBM/Azure/AWS=paid)
  * Logical qubits used
  * Physical qubits (QEC overhead)
  * Shots executed
  * Time to solution

Integrates with:
- /Users/heinzjungbluth/Desktop/Server_bioql/billing/stripe_integration.py
- Existing BioQL auth server billing

Author: Spectrix R&D / BioQL Team
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# Add Server_bioql to path
sys.path.append("/Users/heinzjungbluth/Desktop/Server_bioql")

try:
    from billing.stripe_integration import StripeConfig, StripeIntegration

    STRIPE_AVAILABLE = True
except ImportError:
    print("⚠️  Stripe integration not available")
    STRIPE_AVAILABLE = False

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from quantum_core.optimizers.adaptive_quantum_optimizer import QuantumConfig

# Quantum_graph Pricing Configuration
QUANTUM_GRAPH_PRICING = {
    # Backend costs (per qubit-hour)
    "backend_costs": {
        "simulator": 0.0,  # Free
        "ibm_quantum": 1.20,  # $1.20/qubit-hour
        "azure_quantum": 1.50,  # $1.50/qubit-hour (premium)
        "aws_braket": 1.00,  # $1.00/qubit-hour
    },
    # Visualization type base costs (one-time fee per job)
    "visualization_base_costs": {
        "structure_3d": 0.50,  # $0.50
        "energy_landscape": 1.00,  # $1.00
        "binding_affinity": 2.50,  # $2.50
        "conformational_sampling": 2.00,  # $2.00
        "electron_density": 3.00,  # $3.00
        "molecular_orbitals": 3.50,  # $3.50
        "reaction_pathway": 2.50,  # $2.50
        "protein_folding": 3.00,  # $3.00
        "docking_simulation": 2.50,  # $2.50
        "secondary_structure": 0.75,  # $0.75
        "metabolic_network": 1.50,  # $1.50
        "metabolite_heatmap": 1.00,  # $1.00
        "flux_analysis": 1.25,  # $1.25
    },
    # Shot costs (per 1000 shots)
    "shot_costs": {
        "simulator": 0.01,  # $0.01/1000 shots
        "ibm_quantum": 0.50,  # $0.50/1000 shots
        "azure_quantum": 0.60,  # $0.60/1000 shots
        "aws_braket": 0.45,  # $0.45/1000 shots
    },
    # QEC overhead multipliers
    "qec_multipliers": {
        "None": 1.0,
        "Surface-3": 1.2,
        "Surface-5": 1.4,
        "Surface-7": 1.6,
        "Surface-9": 1.8,
        "Surface-11": 2.0,
        "Surface-13": 2.2,
        "Surface-15": 2.5,
        "Surface-17": 2.8,
        "Surface-19": 3.0,
        "Surface-21": 3.3,
        "Surface-23": 3.6,
        "Surface-25": 4.0,
    },
    # Free tier
    "free_tier": {
        "visualizations_per_month": 10,  # 10 free viz/month (simulator only)
        "max_atoms_free": 100,  # Up to 100 atoms free
        "max_shots_free": 1000,  # Up to 1000 shots free
    },
    # Minimum charge
    "minimum_charge_usd": 0.10,  # Minimum $0.10 per job
}


@dataclass
class QuantumVisualizationCharge:
    """Charge record for a quantum visualization job"""

    job_id: str
    user_id: str
    timestamp: str
    visualization_type: str
    backend: str
    logical_qubits: int
    physical_qubits: int
    shots: int
    qec_code: str
    time_hours: float

    # Cost breakdown
    base_cost: float
    backend_cost: float
    shot_cost: float
    qec_overhead: float
    total_cost: float

    # Metadata
    molecule_type: str
    num_atoms: int
    success: bool


class QuantumGraphBilling:
    """
    Billing integration for Quantum_graph
    """

    def __init__(self, auth_server_url: str = "http://localhost:5001"):
        """
        Initialize billing integration

        Args:
            auth_server_url: URL of BioQL auth server
        """
        self.auth_server_url = auth_server_url
        self.pricing = QUANTUM_GRAPH_PRICING

        # Try to initialize Stripe
        if STRIPE_AVAILABLE:
            try:
                self.stripe = StripeIntegration()
                self.stripe_enabled = True
                print("✅ Stripe billing enabled for Quantum_graph")
            except Exception as e:
                print(f"⚠️  Stripe initialization failed: {e}")
                self.stripe_enabled = False
        else:
            self.stripe_enabled = False

    def calculate_visualization_cost(
        self,
        config: QuantumConfig,
        viz_type: str,
        molecule_data: Dict[str, Any],
        use_free_tier: bool = False,
    ) -> float:
        """
        Calculate cost for a quantum visualization job

        Args:
            config: Quantum configuration
            viz_type: Type of visualization
            molecule_data: Molecular data
            use_free_tier: Whether to apply free tier

        Returns:
            Total cost in USD
        """
        # Check free tier eligibility
        if use_free_tier and config.backend_type == "simulator":
            num_atoms = molecule_data.get("num_atoms", 0)
            if (
                num_atoms <= self.pricing["free_tier"]["max_atoms_free"]
                and config.shots <= self.pricing["free_tier"]["max_shots_free"]
            ):
                return 0.0  # Free!

        # Base cost for visualization type
        base_cost = self.pricing["visualization_base_costs"].get(viz_type, 1.0)

        # Backend cost (qubit-hours)
        backend_rate = self.pricing["backend_costs"].get(config.backend_type, 0.0)
        backend_cost = backend_rate * config.physical_qubits * config.time_to_solution_hours

        # Shot cost
        shot_rate = self.pricing["shot_costs"].get(config.backend_type, 0.0)
        shot_cost = shot_rate * (config.shots / 1000.0)

        # QEC overhead
        qec_multiplier = self.pricing["qec_multipliers"].get(config.qec_code, 1.0)
        qec_overhead = (backend_cost + shot_cost) * (qec_multiplier - 1.0)

        # Total cost
        total_cost = base_cost + backend_cost + shot_cost + qec_overhead

        # Apply minimum charge
        if total_cost > 0 and total_cost < self.pricing["minimum_charge_usd"]:
            total_cost = self.pricing["minimum_charge_usd"]

        return round(total_cost, 2)

    def create_charge_record(
        self,
        job_id: str,
        user_id: str,
        config: QuantumConfig,
        viz_type: str,
        molecule_data: Dict[str, Any],
        success: bool = True,
    ) -> QuantumVisualizationCharge:
        """
        Create a charge record for a visualization job

        Args:
            job_id: Job ID
            user_id: User ID
            config: Quantum configuration
            viz_type: Visualization type
            molecule_data: Molecular data
            success: Whether job succeeded

        Returns:
            QuantumVisualizationCharge record
        """
        # Calculate costs
        base_cost = self.pricing["visualization_base_costs"].get(viz_type, 1.0)

        backend_rate = self.pricing["backend_costs"].get(config.backend_type, 0.0)
        backend_cost = backend_rate * config.physical_qubits * config.time_to_solution_hours

        shot_rate = self.pricing["shot_costs"].get(config.backend_type, 0.0)
        shot_cost = shot_rate * (config.shots / 1000.0)

        qec_multiplier = self.pricing["qec_multipliers"].get(config.qec_code, 1.0)
        qec_overhead = (backend_cost + shot_cost) * (qec_multiplier - 1.0)

        total_cost = base_cost + backend_cost + shot_cost + qec_overhead

        if total_cost > 0 and total_cost < self.pricing["minimum_charge_usd"]:
            total_cost = self.pricing["minimum_charge_usd"]

        # Only charge if job succeeded
        if not success:
            total_cost = 0.0

        return QuantumVisualizationCharge(
            job_id=job_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            visualization_type=viz_type,
            backend=config.backend_type,
            logical_qubits=config.logical_qubits,
            physical_qubits=config.physical_qubits,
            shots=config.shots,
            qec_code=config.qec_code,
            time_hours=config.time_to_solution_hours,
            base_cost=base_cost,
            backend_cost=backend_cost,
            shot_cost=shot_cost,
            qec_overhead=qec_overhead,
            total_cost=round(total_cost, 2),
            molecule_type=molecule_data.get("type", "unknown"),
            num_atoms=molecule_data.get("num_atoms", 0),
            success=success,
        )

    def submit_charge_to_auth_server(self, charge: QuantumVisualizationCharge) -> Dict[str, Any]:
        """
        Submit charge to BioQL auth server for billing

        Args:
            charge: Charge record

        Returns:
            Response from auth server
        """
        try:
            # Prepare charge data
            charge_data = {
                "user_id": charge.user_id,
                "job_id": charge.job_id,
                "service": "quantum_visualization",
                "amount_usd": charge.total_cost,
                "metadata": {
                    "visualization_type": charge.visualization_type,
                    "backend": charge.backend,
                    "logical_qubits": charge.logical_qubits,
                    "physical_qubits": charge.physical_qubits,
                    "shots": charge.shots,
                    "qec_code": charge.qec_code,
                    "time_hours": charge.time_hours,
                    "molecule_type": charge.molecule_type,
                    "num_atoms": charge.num_atoms,
                },
                "timestamp": charge.timestamp,
            }

            # Submit to auth server
            response = requests.post(
                f"{self.auth_server_url}/api/billing/charge", json=charge_data, timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Auth server returned {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a user

        Args:
            user_id: User ID

        Returns:
            Usage statistics
        """
        try:
            response = requests.get(
                f"{self.auth_server_url}/api/billing/usage/{user_id}", timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Add Quantum_graph specific filtering
                return {
                    "user_id": user_id,
                    "quantum_visualizations": data.get("quantum_visualizations", 0),
                    "total_quantum_viz_cost": data.get("total_quantum_viz_cost", 0.0),
                    "free_tier_remaining": self.pricing["free_tier"]["visualizations_per_month"]
                    - data.get("quantum_visualizations", 0),
                }
            else:
                return {"error": f"Failed to fetch usage stats: {response.status_code}"}

        except Exception as e:
            return {"error": str(e)}

    def estimate_cost_before_execution(
        self,
        config: QuantumConfig,
        viz_type: str,
        molecule_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate cost before executing a visualization job

        Args:
            config: Quantum configuration
            viz_type: Visualization type
            molecule_data: Molecular data
            user_id: User ID (for free tier check)

        Returns:
            Cost estimate with breakdown
        """
        # Check free tier if user_id provided
        use_free_tier = False
        if user_id:
            usage = self.get_user_usage_stats(user_id)
            if usage.get("free_tier_remaining", 0) > 0:
                use_free_tier = True

        # Calculate cost
        total_cost = self.calculate_visualization_cost(
            config, viz_type, molecule_data, use_free_tier
        )

        # Build estimate
        base_cost = self.pricing["visualization_base_costs"].get(viz_type, 1.0)
        backend_rate = self.pricing["backend_costs"].get(config.backend_type, 0.0)
        backend_cost = backend_rate * config.physical_qubits * config.time_to_solution_hours
        shot_rate = self.pricing["shot_costs"].get(config.backend_type, 0.0)
        shot_cost = shot_rate * (config.shots / 1000.0)

        return {
            "total_cost_usd": total_cost,
            "free_tier_applied": use_free_tier and total_cost == 0.0,
            "breakdown": {
                "base_visualization_fee": base_cost,
                "backend_compute_cost": backend_cost,
                "shot_measurement_cost": shot_cost,
                "qec_overhead": (backend_cost + shot_cost)
                * (self.pricing["qec_multipliers"].get(config.qec_code, 1.0) - 1.0),
            },
            "config": {
                "backend": config.backend_type,
                "logical_qubits": config.logical_qubits,
                "physical_qubits": config.physical_qubits,
                "shots": config.shots,
                "qec_code": config.qec_code,
                "estimated_time_hours": config.time_to_solution_hours,
            },
            "message": (
                "Free tier applied"
                if (use_free_tier and total_cost == 0.0)
                else f"Estimated cost: ${total_cost:.2f}"
            ),
        }


# Example usage
if __name__ == "__main__":
    from quantum_core.optimizers.adaptive_quantum_optimizer import (
        AdaptiveQuantumOptimizer,
        MoleculeType,
        VisualizationType,
    )

    # Initialize billing
    billing = QuantumGraphBilling()

    # Example: Protein visualization
    optimizer = AdaptiveQuantumOptimizer()
    config = optimizer.optimize(
        molecule_data={"num_atoms": 1000, "num_residues": 100},
        molecule_type=MoleculeType.PROTEIN,
        viz_type=VisualizationType.CONFORMATIONAL_SAMPLING,
        backend_preference="ibm_quantum",
    )

    # Estimate cost
    estimate = billing.estimate_cost_before_execution(
        config,
        "conformational_sampling",
        {"num_atoms": 1000, "type": "protein"},
        user_id="test_user",
    )

    print(json.dumps(estimate, indent=2))

    # Create charge
    charge = billing.create_charge_record(
        job_id="test_job_123",
        user_id="test_user",
        config=config,
        viz_type="conformational_sampling",
        molecule_data={"num_atoms": 1000, "type": "protein"},
        success=True,
    )

    print(f"\n💰 Charge created:")
    print(f"   Total: ${charge.total_cost:.2f}")
    print(f"   Backend: {charge.backend}")
    print(f"   Qubits: {charge.physical_qubits}")
    print(f"   Shots: {charge.shots}")
