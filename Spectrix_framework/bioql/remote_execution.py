#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Remote Execution via API
Executes quantum circuits on api.bioql.bio instead of locally
"""

import os
from typing import Any, Dict, Optional

import requests
from loguru import logger

# BioQL API endpoint
BIOQL_API_URL = os.getenv("BIOQL_API_URL", "https://api.bioql.bio")


def execute_remote(
    program: str,
    api_key: str,
    backend: str = "simulator",
    shots: int = 1024,
    error_correction: Optional[str] = None,
    correction_level: str = "medium",
    num_logical_qubits: Optional[int] = None,
    timeout: int = 300,
) -> Dict[str, Any]:
    """
    Execute quantum program remotely on BioQL API server

    This sends the request to api.bioql.bio which has IBM Quantum token configured

    Args:
        program: Natural language quantum program description
        api_key: BioQL API key
        backend: Quantum backend (ibm_torino, simulator, etc.)
        shots: Number of shots
        error_correction: QEC type ('surface_code', 'steane', 'shor')
        correction_level: QEC level ('low', 'medium', 'high')
        num_logical_qubits: Number of logical qubits
        timeout: Request timeout in seconds

    Returns:
        Dict with execution results
    """

    logger.info(f"🌐 Executing remotely on {BIOQL_API_URL}")
    logger.info(f"   Backend: {backend}")
    logger.info(f"   Shots: {shots}")
    if error_correction:
        logger.info(f"   QEC: {error_correction} (level: {correction_level})")

    # Prepare request payload
    payload = {
        "program": program,
        "api_key": api_key,
        "backend": backend,
        "shots": shots,
        "qec": {
            "enabled": error_correction is not None,
            "type": error_correction or "surface_code",
            "correction_level": correction_level,
            "num_logical_qubits": num_logical_qubits or 2,
        },
    }

    # Try quantum execution endpoint
    endpoints_to_try = [
        f"{BIOQL_API_URL}/api/quantum/execute",  # Primary endpoint
        f"{BIOQL_API_URL}/api/execute",  # Alternative
        f"{BIOQL_API_URL}/execute",  # Fallback
    ]

    for endpoint in endpoints_to_try:
        try:
            logger.debug(f"Trying endpoint: {endpoint}")

            response = requests.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "BioQL/6.0.1",
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=timeout,
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Remote execution successful")
                return result

            elif response.status_code == 404:
                # Try next endpoint
                continue

            else:
                logger.warning(f"HTTP {response.status_code}: {response.text[:200]}")
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on {endpoint}")
            continue

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on {endpoint}: {e}")
            continue

        except Exception as e:
            logger.warning(f"Error on {endpoint}: {e}")
            continue

    # If all endpoints failed, raise error
    raise ConnectionError(
        f"Unable to connect to BioQL API at {BIOQL_API_URL}\n"
        f"Tried endpoints: {', '.join(endpoints_to_try)}\n"
        f"Please check your internet connection or try again later."
    )


def check_remote_available() -> bool:
    """Check if remote execution API is available"""
    try:
        response = requests.get(f"{BIOQL_API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False
