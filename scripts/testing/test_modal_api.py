#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

import json

import requests

url = "https://spectrix--bioql-agent-create-fastapi-app.modal.run/generate"

payload = {
    "prompt": 'Dock my clinical molecule with SMILES="COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2" against GLP1R receptor (PDB: 6B3J) using IBM Torino with 2000 shots and surface_code QEC',
    "max_length": 2048,
    "temperature": 0.7,
}

print("🔄 Testing Modal API...")
print(f"URL: {url}")
print(f"Prompt: {payload['prompt'][:80]}...")

response = requests.post(url, json=payload)

if response.status_code == 200:
    result = response.json()
    print("\n✅ SUCCESS!")
    print("\n" + "=" * 80)
    print("GENERATED CODE:")
    print("=" * 80)
    print(result["code"])
    print("=" * 80)

    # Check for qec_config (WRONG)
    if "qec_config" in result["code"]:
        print("\n❌ ERROR: Code contains qec_config!")
    else:
        print("\n✅ CORRECT: No qec_config found")

    # Check for qec_enabled (CORRECT)
    if "qec_enabled=True" in result["code"]:
        print("✅ CORRECT: qec_enabled=True found")
    else:
        print("❌ ERROR: qec_enabled=True NOT found")

else:
    print(f"\n❌ ERROR: {response.status_code}")
    print(response.text)
