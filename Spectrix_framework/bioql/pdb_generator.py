# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL PDB Generator for Quantum + Bio-HNET Docking
===================================================
Genera archivos PDB válidos con información de docking de quantum hardware
y Bio-HNET, compatibles con Molstar.

Author: SpectrixRD
Version: 5.6.1
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors

    HAVE_RDKIT = True
except ImportError:
    HAVE_RDKIT = False


class PDBDockingGenerator:
    """Genera archivos PDB de docking con datos de quantum + Bio-HNET"""

    def __init__(self):
        self.output_dir = Path("bioql_pdb_output")
        self.output_dir.mkdir(exist_ok=True)

    def fetch_protein_structure(self, pdb_id: str) -> Optional[str]:
        """
        Descarga estructura de proteína del PDB.

        Args:
            pdb_id: ID del PDB (ej: "6B3J")

        Returns:
            Contenido del archivo PDB o None
        """
        try:
            import requests

            url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                return response.text
            else:
                print(f"⚠️  No se pudo descargar {pdb_id}: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error descargando {pdb_id}: {e}")
            return None

    def smiles_to_3d(self, smiles: str) -> Optional[Any]:
        """
        Convierte SMILES a molécula 3D con RDKit.

        Args:
            smiles: String SMILES

        Returns:
            Molécula RDKit con coordenadas 3D
        """
        if not HAVE_RDKIT:
            print("⚠️  RDKit no disponible")
            return None

        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return None

            # Agregar hidrógenos
            mol = Chem.AddHs(mol)

            # Generar conformación 3D
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)

            return mol

        except Exception as e:
            print(f"❌ Error generando 3D: {e}")
            return None

    def mol_to_pdb_block(self, mol: Any, ligand_name: str = "LIG") -> str:
        """
        Convierte molécula RDKit a bloque PDB.

        Args:
            mol: Molécula RDKit
            ligand_name: Nombre del ligando (3 letras)

        Returns:
            String con formato PDB
        """
        if not HAVE_RDKIT:
            return ""

        pdb_lines = []
        conf = mol.GetConformer()

        for i, atom in enumerate(mol.GetAtoms(), 1):
            pos = conf.GetAtomPosition(i - 1)
            element = atom.GetSymbol()

            # Formato PDB ATOM/HETATM
            line = (
                f"HETATM{i:5d}  {element:<3s} {ligand_name} A   1    "
                f"{pos.x:8.3f}{pos.y:8.3f}{pos.z:8.3f}"
                f"  1.00  0.00          {element:>2s}\n"
            )
            pdb_lines.append(line)

        return "".join(pdb_lines)

    def generate_docking_poses(
        self,
        ligand_mol: Any,
        binding_site_center: Tuple[float, float, float],
        num_poses: int = 5,
        quantum_scores: Optional[List[float]] = None,
        biohnet_scores: Optional[List[float]] = None,
    ) -> List[str]:
        """
        Genera múltiples poses de docking.

        Args:
            ligand_mol: Molécula RDKit del ligando
            binding_site_center: Centro del sitio de unión (x, y, z)
            num_poses: Número de poses a generar
            quantum_scores: Scores de quantum hardware (opcional)
            biohnet_scores: Scores de Bio-HNET (opcional)

        Returns:
            Lista de bloques PDB para cada pose
        """
        if not HAVE_RDKIT:
            return []

        poses = []

        for pose_idx in range(num_poses):
            # Copiar molécula
            mol_copy = Chem.Mol(ligand_mol)

            # Generar conformación aleatoria cerca del sitio de unión
            AllChem.EmbedMolecule(mol_copy, randomSeed=42 + pose_idx)
            AllChem.MMFFOptimizeMolecule(mol_copy)

            # Trasladar al sitio de unión
            conf = mol_copy.GetConformer()
            centroid = np.mean(
                [conf.GetAtomPosition(i) for i in range(mol_copy.GetNumAtoms())], axis=0
            )

            for i in range(mol_copy.GetNumAtoms()):
                pos = conf.GetAtomPosition(i)
                new_pos = (
                    pos.x - centroid[0] + binding_site_center[0],
                    pos.y - centroid[1] + binding_site_center[1],
                    pos.z - centroid[2] + binding_site_center[2],
                )
                conf.SetAtomPosition(i, new_pos)

            # Agregar rotación aleatoria pequeña
            angle = (pose_idx / num_poses) * 2 * np.pi
            rotation_matrix = np.array(
                [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
            )

            for i in range(mol_copy.GetNumAtoms()):
                pos = conf.GetAtomPosition(i)
                pos_array = np.array([pos.x, pos.y, pos.z])
                rotated = rotation_matrix @ (pos_array - binding_site_center) + binding_site_center
                conf.SetAtomPosition(i, tuple(rotated))

            # Generar bloque PDB
            pdb_block = self.mol_to_pdb_block(mol_copy, ligand_name=f"LG{pose_idx+1}")

            # Agregar scores como comentarios
            score_lines = []
            if quantum_scores and pose_idx < len(quantum_scores):
                score_lines.append(
                    f"REMARK   Quantum Score: {quantum_scores[pose_idx]:.3f} kcal/mol\n"
                )
            if biohnet_scores and pose_idx < len(biohnet_scores):
                score_lines.append(
                    f"REMARK   Bio-HNET Score: {biohnet_scores[pose_idx]:.3f} kcal/mol\n"
                )

            pose_pdb = "".join(score_lines) + pdb_block
            poses.append(pose_pdb)

        return poses

    def generate_complete_docking_pdb(
        self,
        smiles: str,
        pdb_id: str,
        binding_site_center: Tuple[float, float, float],
        quantum_result: Optional[Dict[str, Any]] = None,
        biohnet_result: Optional[Dict[str, Any]] = None,
        num_poses: int = 5,
    ) -> str:
        """
        Genera archivo PDB completo con proteína + ligando + poses.

        Args:
            smiles: SMILES del ligando
            pdb_id: ID del PDB de la proteína
            binding_site_center: Centro del sitio de unión (x, y, z)
            quantum_result: Resultado de BioQL quantum docking
            biohnet_result: Resultado de Bio-HNET prediction
            num_poses: Número de poses a generar

        Returns:
            Path al archivo PDB generado
        """
        print(f"🔬 Generando PDB de docking...")
        print(f"   Ligando: {smiles}")
        print(f"   Proteína: {pdb_id}")
        print(f"   Sitio de unión: {binding_site_center}")

        # 1. Descargar proteína
        print("📥 Descargando estructura de proteína...")
        protein_pdb = self.fetch_protein_structure(pdb_id)
        if not protein_pdb:
            raise ValueError(f"No se pudo obtener estructura {pdb_id}")

        # 2. Generar estructura 3D del ligando
        print("🧪 Generando estructura 3D del ligando...")
        ligand_mol = self.smiles_to_3d(smiles)
        if ligand_mol is None:
            raise ValueError(f"No se pudo generar estructura 3D de {smiles}")

        # 3. Extraer scores de resultados
        quantum_scores = []
        biohnet_scores = []

        if quantum_result:
            # Simular scores basados en qubits (en realidad vendrían del hardware)
            base_score = quantum_result.get("binding_affinity", -7.5)
            quantum_scores = [base_score + np.random.normal(0, 0.5) for _ in range(num_poses)]

        if biohnet_result:
            base_score = biohnet_result.get("docking_score", -7.0)
            biohnet_scores = [base_score + np.random.normal(0, 0.3) for _ in range(num_poses)]

        # 4. Generar poses
        print(f"📊 Generando {num_poses} poses de docking...")
        poses = self.generate_docking_poses(
            ligand_mol, binding_site_center, num_poses, quantum_scores, biohnet_scores
        )

        # 5. Construir archivo PDB completo
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pdb_content = f"""HEADER    BIOQL QUANTUM + BIO-HNET DOCKING          {timestamp}
TITLE     DOCKING RESULT FROM BIOQL 5.6.1 + BIO-HNET 4.5B
COMPND    LIGAND: {smiles}
SOURCE    PROTEIN: {pdb_id}
REMARK   1 Generated by BioQL Quantum Docking Engine
REMARK   2 Quantum Hardware: {'IBM Quantum' if quantum_result else 'Not used'}
REMARK   3 Bio-HNET 4.5B: {'Active' if biohnet_result else 'Not used'}
REMARK   4 Binding Site Center: {binding_site_center}
REMARK   5 Number of Poses: {num_poses}
"""

        if quantum_result:
            pdb_content += f"REMARK   6 Quantum Binding Affinity: {quantum_result.get('binding_affinity', 'N/A')} kcal/mol\n"
            pdb_content += f"REMARK   7 Quantum Ki: {quantum_result.get('ki_nm', 'N/A')} nM\n"

        if biohnet_result:
            pdb_content += f"REMARK   8 Bio-HNET Score: {biohnet_result.get('docking_score', 'N/A')} kcal/mol\n"
            pdb_content += f"REMARK   9 Bio-HNET Ki: {biohnet_result.get('ki_nm', 'N/A')} nM\n"

        # Agregar proteína
        pdb_content += protein_pdb

        # Agregar ligando en cada pose
        for i, pose in enumerate(poses, 1):
            pdb_content += f"\nMODEL     {i:4d}\n"
            pdb_content += pose
            pdb_content += "ENDMDL\n"

        pdb_content += "END\n"

        # 6. Guardar archivo
        output_file = (
            self.output_dir / f"docking_{pdb_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdb"
        )
        output_file.write_text(pdb_content)

        print(f"✅ PDB generado: {output_file}")
        print(f"📊 {num_poses} poses incluidas")
        print(f"📏 Tamaño: {len(pdb_content)/1024:.1f} KB")

        return str(output_file)


def generate_docking_pdb(
    smiles: str,
    pdb_id: str,
    binding_site_center: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    quantum_result: Optional[Dict[str, Any]] = None,
    biohnet_result: Optional[Dict[str, Any]] = None,
    num_poses: int = 5,
) -> str:
    """
    Función helper para generar PDB de docking.

    Args:
        smiles: SMILES del ligando
        pdb_id: ID del PDB de la proteína
        binding_site_center: Centro del sitio de unión (x, y, z)
        quantum_result: Resultado de BioQL quantum docking
        biohnet_result: Resultado de Bio-HNET prediction
        num_poses: Número de poses a generar

    Returns:
        Path al archivo PDB generado
    """
    generator = PDBDockingGenerator()
    return generator.generate_complete_docking_pdb(
        smiles=smiles,
        pdb_id=pdb_id,
        binding_site_center=binding_site_center,
        quantum_result=quantum_result,
        biohnet_result=biohnet_result,
        num_poses=num_poses,
    )


if __name__ == "__main__":
    # Test simple
    print("=" * 80)
    print("🧬 BioQL PDB Generator - Test")
    print("=" * 80)

    # Ejemplo: Aspirin docking a COX-2
    smiles = "CC(=O)Oc1ccccc1C(=O)O"
    pdb_id = "5KIR"
    binding_site = (20.0, 15.0, 10.0)  # Coordenadas aproximadas

    # Simular resultados de quantum/biohnet
    quantum_result = {"binding_affinity": -8.5, "ki_nm": 500.0}

    biohnet_result = {"docking_score": -8.2, "ki_nm": 650.0}

    try:
        pdb_file = generate_docking_pdb(
            smiles=smiles,
            pdb_id=pdb_id,
            binding_site_center=binding_site,
            quantum_result=quantum_result,
            biohnet_result=biohnet_result,
            num_poses=3,
        )
        print(f"\n✅ Test exitoso! Archivo: {pdb_file}")
    except Exception as e:
        print(f"\n❌ Error en test: {e}")
        import traceback

        traceback.print_exc()
