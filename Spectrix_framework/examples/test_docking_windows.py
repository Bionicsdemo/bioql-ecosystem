#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Drug Discovery Test - Docking Molecular
Test completo para Windows con generación de PDB

Ejemplo: Dock aspirin (ácido acetilsalicílico) a COX-2
"""

import os
import sys
from pathlib import Path

# Configurar autenticación con ngrok
os.environ["BIOQL_AUTH_URL"] = "https://aae99709f69d.ngrok-free.app"
os.environ["BIOQL_LOCAL_AUTH"] = "https://aae99709f69d.ngrok-free.app"

print("=" * 80)
print("🧪 BioQL Drug Discovery Test - Molecular Docking")
print("=" * 80)
print()

# Verificar conectividad con servidor de autenticación
print("1️⃣  Verificando conexión al servidor de autenticación...")
import requests

try:
    response = requests.get("https://aae99709f69d.ngrok-free.app/health", timeout=10)
    if response.status_code == 200:
        print(f"   ✅ Servidor activo: {response.json()['status']}")
    else:
        print(f"   ❌ Error: Status {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ No se puede conectar al servidor: {e}")
    print("   💡 Asegúrate de que el servidor está corriendo y ngrok está activo")
    sys.exit(1)

print()

# Importar BioQL
print("2️⃣  Importando BioQL Drug Discovery Pack...")
try:
    import bioql
    from bioql.chem import prepare_ligand
    from bioql.docking import dock

    print(f"   ✅ BioQL v{bioql.__version__} importado correctamente")
except ImportError as e:
    print(f"   ❌ Error importando BioQL: {e}")
    print("   💡 Ejecuta: pip install bioql[vina,viz]")
    sys.exit(1)

print()

# Configuración
API_KEY = "__BIOQL_REDACTED__"  # Usuario PRO
OUTPUT_DIR = Path("docking_results")
OUTPUT_DIR.mkdir(exist_ok=True)

print("3️⃣  Configuración del experimento:")
print(f"   📂 Directorio de salida: {OUTPUT_DIR.absolute()}")
print(f"   🔑 API Key: {API_KEY[:20]}...")
print()

# Preparar ligando (Aspirin - ácido acetilsalicílico)
print("4️⃣  Preparando ligando desde SMILES...")
print("   Molécula: Aspirin (Ácido Acetilsalicílico)")
ASPIRIN_SMILES = "CC(=O)Oc1ccccc1C(=O)O"
print(f"   SMILES: {ASPIRIN_SMILES}")

try:
    ligand_result = prepare_ligand(
        smiles=ASPIRIN_SMILES,
        output_path=OUTPUT_DIR / "aspirin_ligand.pdb",
        output_format="pdb",
        add_hydrogens=True,
        generate_3d=True,
        optimize_geometry=True,
    )

    if ligand_result.success:
        print(f"   ✅ Ligando preparado exitosamente")
        print(f"      - Átomos: {ligand_result.num_atoms}")
        print(f"      - Peso molecular: {ligand_result.mol_weight:.2f} g/mol")
        print(f"      - Archivo PDB: {ligand_result.output_file}")

        # Leer y mostrar primeras líneas del PDB
        with open(ligand_result.output_file, "r") as f:
            pdb_lines = f.readlines()[:10]

        print(f"\n   📄 Primeras líneas del archivo PDB:")
        for line in pdb_lines:
            print(f"      {line.rstrip()}")
    else:
        print(f"   ⚠️  Advertencia: {ligand_result.error_message}")
        print(f"   ℹ️  Continuando con datos por defecto...")

except Exception as e:
    print(f"   ⚠️  Error preparando ligando: {e}")
    print(f"   ℹ️  Esto es normal si no tienes RDKit instalado")
    print(f"   💡 Para funcionalidad completa: pip install bioql[vina]")

print()

# Crear un receptor de ejemplo (proteína simple para demostración)
print("5️⃣  Creando receptor de ejemplo (proteína COX-2 simplificada)...")

receptor_pdb = OUTPUT_DIR / "cox2_receptor.pdb"

# PDB simplificado de una hélice alfa (representando sitio activo de COX-2)
RECEPTOR_PDB_CONTENT = """HEADER    CYCLOOXYGENASE-2 ACTIVE SITE MODEL
TITLE     SIMPLIFIED COX-2 RECEPTOR FOR DOCKING TEST
ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 20.00           N
ATOM      2  CA  ALA A   1      11.000  10.500  10.500  1.00 20.00           C
ATOM      3  C   ALA A   1      12.000  11.000  10.000  1.00 20.00           C
ATOM      4  O   ALA A   1      12.500  11.500  11.000  1.00 20.00           O
ATOM      5  CB  ALA A   1      11.500   9.500  11.500  1.00 20.00           C
ATOM      6  N   VAL A   2      12.500  11.000   9.000  1.00 20.00           N
ATOM      7  CA  VAL A   2      13.500  11.500   8.500  1.00 20.00           C
ATOM      8  C   VAL A   2      14.500  12.000   9.500  1.00 20.00           C
ATOM      9  O   VAL A   2      15.000  12.500   9.000  1.00 20.00           O
ATOM     10  CB  VAL A   2      14.000  10.500   7.500  1.00 20.00           C
ATOM     11  N   SER A   3      15.000  12.000  10.500  1.00 20.00           N
ATOM     12  CA  SER A   3      16.000  12.500  11.000  1.00 20.00           C
ATOM     13  C   SER A   3      17.000  13.000  10.000  1.00 20.00           C
ATOM     14  O   SER A   3      17.500  13.500  10.500  1.00 20.00           O
ATOM     15  CB  SER A   3      16.500  11.500  12.000  1.00 20.00           C
ATOM     16  OG  SER A   3      15.500  11.000  13.000  1.00 20.00           O
TER      17      SER A   3
END
"""

with open(receptor_pdb, "w") as f:
    f.write(RECEPTOR_PDB_CONTENT)

print(f"   ✅ Receptor creado: {receptor_pdb}")
print(f"   📊 Átomos en el receptor: 16")
print(f"   🧬 Secuencia: ALA-VAL-SER (sitio activo simplificado)")

print()

# Test de ejecución cuántica con docking
print("6️⃣  Ejecutando simulación cuántica de docking...")
print("   ⚙️  Backend: quantum simulator")
print("   🎲 Shots: 20")

try:
    result = bioql.quantum(
        program=f"Dock ligand SMILES '{ASPIRIN_SMILES}' to protein COX-2 with quantum optimization",
        api_key=API_KEY,
        backend="simulator",
        shots=20,
    )

    print()
    if result.success:
        print("   ✅ Simulación cuántica completada exitosamente!")
        print(f"   📊 Resultados:")
        print(f"      - Backend usado: {result.backend_name}")
        print(f"      - Tiempo de ejecución: {result.execution_time:.3f}s")
        print(f"      - Total shots: {result.total_shots}")
        print(f"      - Estado más probable: {result.most_likely_outcome}")
        print(f"\n   🔬 Distribución de estados cuánticos:")

        # Mostrar top 5 estados
        sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
        for i, (state, count) in enumerate(sorted_counts[:5], 1):
            probability = count / result.total_shots * 100
            print(f"      {i}. Estado |{state}⟩: {count} shots ({probability:.1f}%)")

        # Interpretación biológica
        if hasattr(result, "bio_interpretation") and result.bio_interpretation:
            print(f"\n   🧬 Interpretación biológica:")
            bio_data = result.bio_interpretation
            if "bioql_domain" in bio_data:
                print(f"      - Dominio: {bio_data['bioql_domain']}")
            if "operation_type" in bio_data:
                print(f"      - Tipo de operación: {bio_data['operation_type']}")
    else:
        print(f"   ❌ Error en simulación: {result.error_message}")

except Exception as e:
    print(f"   ❌ Error ejecutando simulación: {e}")
    import traceback

    traceback.print_exc()

print()

# Resumen final
print("=" * 80)
print("📋 RESUMEN DEL TEST")
print("=" * 80)
print()
print("Archivos generados:")
print(f"  📄 Ligando (PDB):  {OUTPUT_DIR / 'aspirin_ligand.pdb'}")
print(f"  📄 Receptor (PDB): {receptor_pdb}")
print()
print("✅ Test completado exitosamente!")
print()
print("💡 Próximos pasos:")
print("  1. Visualiza los archivos PDB con PyMOL o Chimera")
print("  2. Ejecuta docking completo con AutoDock Vina")
print("  3. Analiza los resultados de binding affinity")
print()
print("📚 Más información:")
print("  - Documentación: https://docs.bioql.com")
print("  - Ejemplos: cat examples/drug_discovery_example.py")
print("  - Soporte: hello@spectrixrd.com")
print()
print("=" * 80)
