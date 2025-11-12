#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Simple Example
Demonstrates the simplified PyPI API
"""

from qpharos import dock

# Simple docking - QPHAROS uses BioQL internally
result = dock(
    ligand="COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2",  # Berberine
    receptor="6B3J",  # GLP1R
    api_key="__BIOQL_REDACTED__",
    backend="ibm_torino",
    shots=2000,
)

# Print results
print(result)

# Access specific fields
if result.success:
    print(f"\n✅ Docking Successful!")
    print(f"   Binding Affinity: {result.binding_affinity} kcal/mol")
    print(f"   Ki: {result.ki} nM")
    print(f"   IBM Job: https://quantum.ibm.com/jobs/{result.job_id}")
