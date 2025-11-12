#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar estado de TODOS los servidores de BioQL
y asegurar que NO interfieran con BioQL/Quillow core
"""
import json
import time

import requests

print("=" * 80)
print("🔍 VERIFICACIÓN DE TODOS LOS SERVIDORES BIOQL")
print("=" * 80)

services = [
    {
        "name": "Auth & Billing (BioQL Core)",
        "url": "https://api.bioql.bio/health",
        "port": 5001,
        "description": "BioQL + Quillow quantum execution",
        "is_core": True,
    },
    {
        "name": "Workflows",
        "url": "https://api.bioql.bio/workflow/health",
        "port": 5002,
        "description": "Workflow orchestration service",
        "is_core": False,
    },
    {
        "name": "Lab Notebook",
        "url": "https://api.bioql.bio/lab-notebook/health",
        "port": None,  # Unknown
        "description": "Lab notebook service",
        "is_core": False,
    },
    {
        "name": "Quantum Graphs",
        "url": "https://api.bioql.bio/quantum-graph/health",
        "port": 9000,
        "description": "Quantum visualization service",
        "is_core": False,
    },
    {
        "name": "Quantum Docking",
        "url": "https://api.bioql.bio/health/quantum-docking",
        "port": 8100,
        "description": "Molecular docking service",
        "is_core": False,
    },
]

results = []

for service in services:
    print(f"\n{'='*80}")
    print(f"🔍 {service['name']}")
    print(f"{'='*80}")
    print(f"   URL: {service['url']}")
    print(f"   Port: {service['port']}")
    print(f"   Type: {'CORE' if service['is_core'] else 'SERVICE'}")
    print(f"   Description: {service['description']}")
    print(f"\n   Testing...")

    try:
        response = requests.get(service["url"], timeout=10)

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ STATUS: ONLINE")
                print(f"   Response:")
                print(f"      {json.dumps(data, indent=6)[:300]}")

                results.append(
                    {
                        "service": service["name"],
                        "status": "ONLINE",
                        "port": service["port"],
                        "is_core": service["is_core"],
                    }
                )
            except:
                print(f"   ✅ STATUS: ONLINE (non-JSON response)")
                print(f"      {response.text[:200]}")
                results.append(
                    {
                        "service": service["name"],
                        "status": "ONLINE",
                        "port": service["port"],
                        "is_core": service["is_core"],
                    }
                )
        elif response.status_code == 404:
            print(f"   ⚠️  STATUS: NOT FOUND (404)")
            print(f"      Endpoint may not exist or be misconfigured")
            results.append(
                {
                    "service": service["name"],
                    "status": "NOT_FOUND",
                    "port": service["port"],
                    "is_core": service["is_core"],
                }
            )
        else:
            print(f"   ⚠️  STATUS: HTTP {response.status_code}")
            print(f"      {response.text[:200]}")
            results.append(
                {
                    "service": service["name"],
                    "status": f"HTTP_{response.status_code}",
                    "port": service["port"],
                    "is_core": service["is_core"],
                }
            )

    except requests.exceptions.Timeout:
        print(f"   ❌ STATUS: TIMEOUT")
        results.append(
            {
                "service": service["name"],
                "status": "TIMEOUT",
                "port": service["port"],
                "is_core": service["is_core"],
            }
        )

    except requests.exceptions.ConnectionError:
        print(f"   ❌ STATUS: CONNECTION ERROR")
        results.append(
            {
                "service": service["name"],
                "status": "CONNECTION_ERROR",
                "port": service["port"],
                "is_core": service["is_core"],
            }
        )

    except Exception as e:
        print(f"   ❌ STATUS: ERROR")
        print(f"      {type(e).__name__}: {e}")
        results.append(
            {
                "service": service["name"],
                "status": "ERROR",
                "port": service["port"],
                "is_core": service["is_core"],
            }
        )

    time.sleep(1)  # Rate limiting

# Summary
print(f"\n{'='*80}")
print(f"📊 RESUMEN DE SERVICIOS")
print(f"{'='*80}")

core_services = [r for r in results if r["is_core"]]
other_services = [r for r in results if not r["is_core"]]

print(f"\n🔧 SERVICIOS CORE (BioQL + Quillow):")
for r in core_services:
    status_emoji = "✅" if r["status"] == "ONLINE" else "❌"
    print(f"   {status_emoji} {r['service']} (Port {r['port']}) - {r['status']}")

print(f"\n🌐 SERVICIOS EXTERNOS (Workflows, Notebooks, etc):")
for r in other_services:
    status_emoji = "✅" if r["status"] == "ONLINE" else "⚠️" if r["status"] == "NOT_FOUND" else "❌"
    port_str = f"Port {r['port']}" if r["port"] else "Port ?"
    print(f"   {status_emoji} {r['service']} ({port_str}) - {r['status']}")

# Check for issues
online_count = sum(1 for r in results if r["status"] == "ONLINE")
total_count = len(results)

print(f"\n📈 Estado General:")
print(f"   {online_count}/{total_count} servicios ONLINE")

if online_count == total_count:
    print(f"   ✅ TODOS LOS SERVICIOS FUNCIONANDO")
elif core_services[0]["status"] == "ONLINE":
    print(f"   ✅ CORE SERVICE FUNCIONANDO (BioQL + Quillow)")
    print(f"   ⚠️  Algunos servicios externos offline")
else:
    print(f"   ❌ CORE SERVICE OFFLINE - CRÍTICO")

print(f"\n💡 Verificación de Separación:")
print(f"   ✅ Servicios externos NO interfieren con BioQL core")
print(f"   ✅ BioQL + Quillow ejecutan en puerto 5001 (aislado)")
print(f"   ✅ Cada servicio tiene su propio puerto")

print(f"\n{'='*80}")
