#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Integration Module for Quantum Graphs

This module integrates Quantum Graphs with the existing BioQL workflow server
to execute quantum circuits on real quantum hardware (IBM Torino, IonQ, etc.)
"""

import json
import logging
from typing import Any, Dict, Optional

import requests
from qiskit import QuantumCircuit

logger = logging.getLogger(__name__)


class BioQLIntegration:
    """Integration with BioQL workflow server for quantum execution"""

    def __init__(self, bioql_server_url: str = "http://127.0.0.1:5002"):
        """
        Initialize BioQL integration

        Args:
            bioql_server_url: URL of BioQL workflow server (default: http://127.0.0.1:5002)
        """
        self.bioql_server_url = bioql_server_url
        self.api_endpoint = f"{bioql_server_url}/workflow/execute-node"
        logger.info(f"🔗 BioQL Integration initialized: {bioql_server_url}")

    def circuit_to_bioql_query(self, circuit: QuantumCircuit, molecule_info: Dict[str, Any]) -> str:
        """
        Convert quantum circuit to BioQL query

        Args:
            circuit: Qiskit QuantumCircuit
            molecule_info: Information about the molecule being analyzed

        Returns:
            BioQL query string
        """
        molecule_type = molecule_info.get("molecule_type", "protein")
        smiles = molecule_info.get("smiles", "")
        num_qubits = circuit.num_qubits

        # Create BioQL query based on molecule type
        if molecule_type == "small_molecule" and smiles:
            query = f"SELECT structure, binding_affinity FROM molecules WHERE smiles='{smiles}'"
        elif molecule_type == "protein":
            protein_id = molecule_info.get("protein_id", "unknown")
            query = f"SELECT structure, folding_energy FROM proteins WHERE id='{protein_id}'"
        else:
            query = f"SELECT * FROM molecules WHERE qubits={num_qubits}"

        return query

    async def execute_on_bioql(
        self,
        circuit: QuantumCircuit,
        backend: str,
        shots: int,
        api_key: str,
        molecule_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute quantum circuit through BioQL workflow server

        Args:
            circuit: Qiskit QuantumCircuit to execute
            backend: Backend name (ibm_torino, ibm_brisbane, ionq_forte, etc.)
            shots: Number of measurement shots
            api_key: BioQL API key for authentication
            molecule_info: Optional molecule information for query generation

        Returns:
            Dict containing execution results
        """
        try:
            logger.info(f"🚀 Executing PRE-COMPILED VQE circuit on BioQL backend: {backend}")
            logger.info(
                f"📊 Circuit: {circuit.num_qubits} qubits, {shots} shots, depth={circuit.depth()}"
            )

            # Try to export circuit as QASM and pass it to BioQL
            # BioQL's compiler might recognize QASM syntax
            try:
                # Export to OpenQASM 2.0 (standard format)
                from qiskit import qasm2

                qasm_str = qasm2.dumps(circuit)
                logger.info(f"📦 Exported VQE circuit to QASM ({len(qasm_str)} bytes)")
                logger.info(f"🔍 QASM preview: {qasm_str[:200]}...")

                # Pass QASM string as the "problem" - maybe BioQL recognizes it
                bioql_problem = qasm_str
                use_qasm = True
                circuit_b64 = None
            except Exception as e:
                logger.warning(f"⚠️  Could not export to QASM: {e}, using fallback")
                # Fallback to query-based generation
                if molecule_info is None:
                    molecule_info = {"molecule_type": "generic", "qubits": circuit.num_qubits}
                bioql_problem = self.circuit_to_bioql_query(circuit, molecule_info)
                circuit_b64 = None
                use_qasm = False

            # Send to BioQL workflow server
            logger.info(f"📤 Sending {'QASM circuit' if use_qasm else 'query'} to BioQL...")

            payload = {
                "node_type": "new-quantum-algorithm",
                "node_id": f"quantum_graph_vqe_{backend}_{shots}",
                "inputs": {
                    "algorithm": "VQE",
                    "problem": bioql_problem,
                    "backend": backend,
                    "shots": shots,
                    "num_qubits": circuit.num_qubits,
                    "circuit_depth": circuit.depth(),
                    "optimization_level": 0,
                    "serialized_circuit": circuit_b64,  # Pass serialized circuit
                },
            }

            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                timeout=300,  # 5 minute timeout for quantum execution
            )

            if response.status_code != 200:
                error_msg = f"BioQL workflow server returned status {response.status_code}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Response: {response.text[:500]}")
                return {"success": False, "error": error_msg, "status_code": response.status_code}

            result = response.json()
            logger.info(f"✅ BioQL execution completed successfully")

            # Parse result from new-quantum-algorithm executor
            if result.get("success"):
                data = result.get("data", {})
                job_id = data.get("job_id")

                logger.info(f"🔍 IBM Quantum Job ID: {job_id}")
                if job_id:
                    logger.info(f"🔗 IBM Quantum URL: https://quantum.ibm.com/jobs/{job_id}")

                return {
                    "success": True,
                    "backend": backend,
                    "shots": shots,
                    "counts": data.get("raw_counts", {}),
                    "cost_usd": data.get("cost_usd", 0.0),
                    "execution_time": data.get("execution_time", 0.0),
                    "job_id": job_id,
                    "ibm_job_url": data.get("ibm_job_url"),
                    "raw_result": result,
                }
            else:
                error_msg = result.get("error", "Unknown error from BioQL")
                logger.error(f"❌ BioQL execution failed: {error_msg}")
                return {"success": False, "error": error_msg, "raw_result": result}

        except requests.exceptions.Timeout:
            error_msg = "BioQL workflow server timeout (>5 minutes)"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to BioQL workflow server at {self.bioql_server_url}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error in BioQL integration: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception(e)
            return {"success": False, "error": error_msg}

    def check_bioql_status(self) -> Dict[str, Any]:
        """
        Check if BioQL workflow server is accessible

        Returns:
            Dict with status information
        """
        try:
            response = requests.get(f"{self.bioql_server_url}/api/info", timeout=5)
            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "info": response.json() if response.status_code == 200 else None,
            }
        except Exception as e:
            logger.warning(f"⚠️  BioQL workflow server not accessible: {e}")
            return {"available": False, "error": str(e)}


# Global instance
_bioql_integration = None


def get_bioql_integration() -> BioQLIntegration:
    """Get or create BioQL integration singleton"""
    global _bioql_integration
    if _bioql_integration is None:
        _bioql_integration = BioQLIntegration()
    return _bioql_integration
