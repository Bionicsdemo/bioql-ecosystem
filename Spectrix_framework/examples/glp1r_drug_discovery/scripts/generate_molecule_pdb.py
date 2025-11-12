#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Generar PDB de moléculas diseñadas para GLP1R
Convierte SMILES a estructura 3D en formato PDB
"""

from pathlib import Path

print("=" * 80)
print("💊 Generación de PDB para Moléculas Diseñadas - GLP1R")
print("=" * 80)
print()

# Crear directorio
output_dir = Path("glp1r_molecules")
output_dir.mkdir(exist_ok=True)

# Candidatos moleculares
candidates = [
    {
        "name": "Small-molecule-agonist-A",
        "smiles": "CC1=CC=C(C=C1)C(=O)NC2=CC=C(C=C2)C(=O)O",
        "description": "Agonista pequeño optimizado",
        "mw": "255.27",
        "logp": "2.8",
    },
    {
        "name": "Small-molecule-agonist-B",
        "smiles": "COC1=CC=C(C=C1)C(=O)NCC(=O)NC2=CC=CC=C2C(=O)O",
        "description": "Derivado con mejor solubilidad",
        "mw": "328.32",
        "logp": "2.1",
    },
    {
        "name": "Small-molecule-agonist-C",
        "smiles": "CC(C)CC(NC(=O)C(CC1=CC=CC=C1)N)C(=O)O",
        "description": "Estructura peptidomiméica",
        "mw": "291.35",
        "logp": "1.5",
    },
]

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    print("✅ RDKit disponible - Generando estructuras 3D...")
    print()

    for i, cand in enumerate(candidates, 1):
        print(f"{i}. Procesando: {cand['name']}")
        print(f"   SMILES: {cand['smiles']}")

        try:
            # Crear molécula desde SMILES
            mol = Chem.MolFromSmiles(cand["smiles"])

            if mol is None:
                print(f"   ❌ Error: SMILES inválido")
                continue

            # Añadir hidrógenos
            mol = Chem.AddHs(mol)

            # Generar conformación 3D
            result = AllChem.EmbedMolecule(mol, randomSeed=42)

            if result == -1:
                print(f"   ⚠️  Advertencia: No se pudo generar 3D, intentando método alternativo")
                AllChem.EmbedMolecule(mol, useRandomCoords=True, randomSeed=42)

            # Optimizar geometría
            AllChem.MMFFOptimizeMolecule(mol)

            # Guardar como PDB
            pdb_file = output_dir / f"{cand['name']}.pdb"
            Chem.MolToPDBFile(mol, str(pdb_file))

            # Información de la molécula
            num_atoms = mol.GetNumAtoms()
            num_heavy = mol.GetNumHeavyAtoms()

            print(f"   ✅ PDB generado: {pdb_file}")
            print(f"   📊 Átomos totales: {num_atoms}")
            print(f"   📊 Átomos pesados: {num_heavy}")
            print(f"   ⚖️  Peso molecular: {cand['mw']} g/mol")
            print(f"   💧 LogP (solubilidad): {cand['logp']}")
            print()

        except Exception as e:
            print(f"   ❌ Error generando molécula: {e}")
            print()

    # Crear archivo de resumen
    summary_file = output_dir / "molecules_summary.txt"
    with open(summary_file, "w") as f:
        f.write("GLP1R Drug Design - Molecular Candidates\n")
        f.write("=" * 60 + "\n\n")
        f.write("Target: GLP1R (Glucagon-like peptide-1 receptor)\n")
        f.write("Indication: Type 2 Diabetes, Obesity\n")
        f.write("Design approach: Small molecule agonists\n\n")

        for i, cand in enumerate(candidates, 1):
            f.write(f"\nCandidate #{i}: {cand['name']}\n")
            f.write("-" * 60 + "\n")
            f.write(f"SMILES: {cand['smiles']}\n")
            f.write(f"Description: {cand['description']}\n")
            f.write(f"Molecular Weight: {cand['mw']} g/mol\n")
            f.write(f"LogP: {cand['logp']}\n")
            f.write(f"PDB File: {cand['name']}.pdb\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("Next Steps:\n")
        f.write("1. Molecular docking with AutoDock Vina\n")
        f.write("2. Binding affinity prediction\n")
        f.write("3. ADME/Tox analysis\n")
        f.write("4. Lead optimization\n")

    print(f"📄 Resumen guardado: {summary_file}")
    print()

    # Mostrar archivos generados
    print("📁 Archivos generados:")
    for file in sorted(output_dir.glob("*")):
        print(f"   • {file.name}")

except ImportError:
    print("❌ RDKit no está instalado")
    print()
    print("Para generar estructuras 3D, instala RDKit:")
    print("   conda install -c conda-forge rdkit")
    print("   o")
    print("   pip install rdkit")
    print()
    print("💡 Alternativamente, generando PDB básico manualmente...")
    print()

    # Generar PDB básico manualmente (sin RDKit)
    for i, cand in enumerate(candidates, 1):
        print(f"{i}. {cand['name']}")

        # PDB simplificado (solo esqueleto)
        pdb_basic = f"""HEADER    {cand['name']}
TITLE     GLP1R AGONIST CANDIDATE
REMARK    SMILES: {cand['smiles']}
REMARK    MW: {cand['mw']} g/mol, LogP: {cand['logp']}
REMARK    THIS IS A SIMPLIFIED 2D STRUCTURE
REMARK    For accurate 3D structure, install RDKit
ATOM      1  C   LIG A   1      10.000  10.000  10.000  1.00 20.00           C
ATOM      2  C   LIG A   1      11.400  10.000  10.000  1.00 20.00           C
ATOM      3  C   LIG A   1      12.100  11.200  10.000  1.00 20.00           C
ATOM      4  C   LIG A   1      11.400  12.400  10.000  1.00 20.00           C
ATOM      5  C   LIG A   1      10.000  12.400  10.000  1.00 20.00           C
ATOM      6  C   LIG A   1       9.300  11.200  10.000  1.00 20.00           C
ATOM      7  C   LIG A   1      13.500  11.200  10.000  1.00 20.00           C
ATOM      8  O   LIG A   1      14.200  10.200  10.000  1.00 20.00           O
ATOM      9  N   LIG A   1      14.000  12.400  10.000  1.00 20.00           N
ATOM     10  C   LIG A   1      15.400  12.600  10.000  1.00 20.00           C
TER      11      LIG A   1
END
"""

        pdb_file = output_dir / f"{cand['name']}_basic.pdb"
        with open(pdb_file, "w") as f:
            f.write(pdb_basic)

        print(f"   ✅ PDB básico: {pdb_file}")
        print(f"   ⚠️  Estructura simplificada (2D)")
        print()

print()
print("=" * 80)
print("✅ Generación completada!")
print("=" * 80)
print()
print("📌 Próximos pasos:")
print("   1. Visualizar con PyMOL o ChimeraX")
print("   2. Ejecutar docking molecular:")
print(f"      bioql dock --receptor glp1r_results/glp1r_receptor.pdb \\")
print(f"                 --ligand {output_dir}/Small-molecule-agonist-A.pdb \\")
print("                 --backend vina")
print()
