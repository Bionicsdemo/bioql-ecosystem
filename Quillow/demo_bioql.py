#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
🔗 QUILLOW + BIOQL - Demo de Conexión Real
==========================================

Script simple que muestra la conexión de Quillow con BioQL.
Usa tu API key real para validar y consultar información de cuenta.

Uso:
    python demo_bioql.py
"""

import sys

sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Quillow")

from quillow.backends.bioql_backend import BioQLBackend, BioQLConfig

# Tu API key de BioQL
API_KEY = "__BIOQL_REDACTED__"

print("=" * 70)
print("🔗 QUILLOW + BIOQL - Demo de Conexión")
print("=" * 70)

# Paso 1: Configurar conexión
print("\n📋 Paso 1: Configurando conexión a BioQL...")
print(f"   • API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
print(f"   • URL: https://api.bioql.bio")

config = BioQLConfig(api_key=API_KEY, base_url="https://api.bioql.bio")

# Paso 2: Crear backend con QEC
print("\n🔬 Paso 2: Inicializando Quillow backend con QEC d=5...")
backend = BioQLBackend(config, qec_distance=5)
print("   ✅ Backend creado")
print("   • QEC Distance: 5")
print("   • Overhead esperado: 1.5x")

# Paso 3: Validar API key
print("\n🔑 Paso 3: Validando API key con servidor BioQL...")
try:
    if backend.validate_api_key():
        print("   ✅ API key válida!")

        # Paso 4: Consultar información de cuenta
        print("\n💰 Paso 4: Consultando información de cuenta...")
        quota = backend.check_quota()

        if "error" not in quota:
            print("\n" + "=" * 70)
            print("INFORMACIÓN DE TU CUENTA BIOQL")
            print("=" * 70)
            print(f"Balance:           ${quota.get('balance', 0):.2f}")
            print(f"Tier:              {quota.get('tier', 'N/A')}")
            print(f"Shots usados:      {quota.get('shots_used', 0):,}")
            print(f"Límite de shots:   {quota.get('shots_limit', 'unlimited')}")
            print("=" * 70)

            # Mostrar ejemplo de uso
            print("\n💡 CÓMO USAR QUILLOW CON BIOQL:")
            print("=" * 70)
            print(
                """
from quillow.backends.bioql_backend import BioQLOptimizer

# Inicializar optimizador (QEC automático)
optimizer = BioQLOptimizer(qec_distance=5)

# Ejecutar cálculo cuántico con QEC en hardware real
result = optimizer.execute_with_qec(
    bioql_query="optimize H2 molecule with VQE",
    backend="ibm_torino",  # IBM Quantum hardware
    shots=2048
)

# Ver resultados
print(f"Energía: {result['energy']:.6f} Hartree")
print(f"Error lógico: {result['logical_error_rate']:.6f}")
print(f"Costo: ${result['total_cost']:.2f}")
"""
            )

            print("=" * 70)
            print("\n✅ QUILLOW ESTÁ LISTO PARA USAR CON BIOQL!")
            print("\n🎯 Próximos pasos:")
            print("   1. Ejecuta: python demo_script.py  (demo completa)")
            print("   2. Lee: HOW_QUILLOW_WORKS.md")
            print("   3. Prueba en hardware real con ibm_torino")

        else:
            print(f"   ⚠️  Error al obtener quota: {quota['error']}")

    else:
        print("   ❌ API key inválida")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 70)
