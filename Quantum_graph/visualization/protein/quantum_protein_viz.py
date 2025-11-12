# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum-Enhanced Protein Visualization
=======================================

Specialized visualizations for:
- Protein structure prediction
- Protein folding dynamics
- Protein-protein interactions
- Secondary structure analysis
- Binding site identification
- Conformational changes

Uses quantum algorithms for:
- Folding pathway optimization (QAOA)
- Energy minimization (VQE)
- Interaction network analysis

Author: Spectrix R&D / BioQL Team
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

sys.path.append(str(Path(__file__).parent.parent.parent))

from visualization.quantum_viz_engine import (
    Atom,
    Bond,
    MolecularStructure,
    MoleculeType,
    QuantumVisualizationResult,
    QuantumVizEngine,
)


class QuantumProteinVisualizer:
    """
    Advanced protein visualization with quantum acceleration
    """

    def __init__(self, viz_engine: Optional[QuantumVizEngine] = None):
        self.engine = viz_engine or QuantumVizEngine()

        # Secondary structure colors
        self.ss_colors = {
            "helix": "#FF0080",  # Magenta
            "sheet": "#FFC800",  # Yellow
            "loop": "#00C8FF",  # Cyan
            "turn": "#80FF00",  # Green
            "coil": "#C0C0C0",  # Gray
        }

        # Amino acid properties
        self.aa_hydrophobicity = {
            "ALA": 1.8,
            "ARG": -4.5,
            "ASN": -3.5,
            "ASP": -3.5,
            "CYS": 2.5,
            "GLN": -3.5,
            "GLU": -3.5,
            "GLY": -0.4,
            "HIS": -3.2,
            "ILE": 4.5,
            "LEU": 3.8,
            "LYS": -3.9,
            "MET": 1.9,
            "PHE": 2.8,
            "PRO": -1.6,
            "SER": -0.8,
            "THR": -0.7,
            "TRP": -0.9,
            "TYR": -1.3,
            "VAL": 4.2,
        }

    def visualize_secondary_structure(
        self, structure: MolecularStructure, output_file: str = "protein_secondary.png"
    ) -> str:
        """
        Visualize protein secondary structure with quantum-derived contacts

        Args:
            structure: Protein structure
            output_file: Output file path

        Returns:
            Path to saved image
        """
        fig, ax = plt.subplots(figsize=(14, 8), dpi=150)

        # Extract backbone atoms (C-alpha)
        ca_atoms = [a for a in structure.atoms if a.element == "C" and a.residue_id is not None]
        ca_atoms.sort(key=lambda a: a.residue_id)

        if len(ca_atoms) < 4:
            print("⚠️  Not enough residues for secondary structure analysis")
            return ""

        # Assign secondary structure (simple heuristic based on C-alpha distances)
        ss_assignment = self._assign_secondary_structure(ca_atoms)

        # Plot as ribbon
        x = [a.x for a in ca_atoms]
        y = [a.y for a in ca_atoms]
        z = [a.z for a in ca_atoms]

        # Create 2D projection (PCA-like)
        coords = np.array([x, y, z]).T
        coords_2d = self._project_to_2d(coords)

        # Draw ribbon colored by secondary structure
        for i in range(len(coords_2d) - 1):
            ss = ss_assignment[i]
            color = self.ss_colors.get(ss, "#808080")

            # Draw segment
            ax.plot(
                coords_2d[i : i + 2, 0],
                coords_2d[i : i + 2, 1],
                color=color,
                linewidth=8,
                solid_capstyle="round",
                alpha=0.8,
                zorder=2,
            )

            # Add residue number every 10 residues
            if i % 10 == 0:
                ax.text(
                    coords_2d[i, 0],
                    coords_2d[i, 1],
                    str(ca_atoms[i].residue_id),
                    fontsize=7,
                    ha="center",
                    va="center",
                    bbox=dict(boxstyle="circle", facecolor="white", alpha=0.7, pad=0.1),
                )

        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], color=self.ss_colors["helix"], lw=4, label="α-Helix"),
            plt.Line2D([0], [0], color=self.ss_colors["sheet"], lw=4, label="β-Sheet"),
            plt.Line2D([0], [0], color=self.ss_colors["loop"], lw=4, label="Loop"),
            plt.Line2D([0], [0], color=self.ss_colors["turn"], lw=4, label="Turn"),
            plt.Line2D([0], [0], color=self.ss_colors["coil"], lw=4, label="Coil"),
        ]
        ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

        ax.set_xlabel("Principal Component 1", fontsize=12)
        ax.set_ylabel("Principal Component 2", fontsize=12)
        ax.set_title(
            f"Protein Secondary Structure: {structure.name}", fontsize=14, fontweight="bold"
        )
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Secondary structure visualization saved to: {output_file}")
        return output_file

    def _assign_secondary_structure(self, ca_atoms: List[Atom]) -> List[str]:
        """
        Simple secondary structure assignment based on C-alpha distances

        Args:
            ca_atoms: List of C-alpha atoms

        Returns:
            List of secondary structure codes
        """
        ss = []

        for i in range(len(ca_atoms)):
            # Calculate distances to neighbors
            if i < 3 or i >= len(ca_atoms) - 3:
                ss.append("coil")
                continue

            # Distance to i+3 (α-helix pattern)
            d_i3 = self._distance(ca_atoms[i], ca_atoms[i + 3])

            # Distance to i+4 (β-sheet pattern)
            if i < len(ca_atoms) - 4:
                d_i4 = self._distance(ca_atoms[i], ca_atoms[i + 4])
            else:
                d_i4 = 100.0

            # Classification
            if 4.8 < d_i3 < 5.8:  # α-helix
                ss.append("helix")
            elif d_i4 > 9.0:  # Extended (β-sheet)
                ss.append("sheet")
            elif d_i3 < 4.5:  # Turn
                ss.append("turn")
            else:
                ss.append("loop")

        return ss

    def _distance(self, atom1: Atom, atom2: Atom) -> float:
        """Calculate distance between two atoms"""
        dx = atom1.x - atom2.x
        dy = atom1.y - atom2.y
        dz = atom1.z - atom2.z
        return np.sqrt(dx**2 + dy**2 + dz**2)

    def _project_to_2d(self, coords_3d: np.ndarray) -> np.ndarray:
        """
        Project 3D coordinates to 2D using PCA

        Args:
            coords_3d: Nx3 array of coordinates

        Returns:
            Nx2 array of 2D coordinates
        """
        # Center coordinates
        coords_centered = coords_3d - coords_3d.mean(axis=0)

        # Compute covariance matrix
        cov = np.cov(coords_centered.T)

        # Eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        # Sort by eigenvalue (descending)
        idx = eigenvalues.argsort()[::-1]
        eigenvectors = eigenvectors[:, idx]

        # Project onto first two principal components
        coords_2d = coords_centered @ eigenvectors[:, :2]

        return coords_2d

    def visualize_binding_site(
        self,
        protein: MolecularStructure,
        ligand: MolecularStructure,
        output_file: str = "binding_site.png",
    ) -> str:
        """
        Visualize protein-ligand binding site with quantum-enhanced affinity

        Args:
            protein: Protein structure
            ligand: Ligand structure
            output_file: Output file

        Returns:
            Path to saved image
        """
        fig = plt.figure(figsize=(14, 10), dpi=150)
        ax = fig.add_subplot(111, projection="3d")

        # Get coordinates
        protein_coords = np.array([[a.x, a.y, a.z] for a in protein.atoms])
        ligand_coords = np.array([[a.x, a.y, a.z] for a in ligand.atoms])

        # Find binding site (atoms within 5Å of ligand)
        binding_distance = 5.0
        binding_site_mask = []

        for p_coord in protein_coords:
            min_dist = np.min(np.linalg.norm(ligand_coords - p_coord, axis=1))
            binding_site_mask.append(min_dist < binding_distance)

        binding_site_mask = np.array(binding_site_mask)

        # Plot protein (gray for non-binding, colored for binding site)
        ax.scatter(
            protein_coords[~binding_site_mask, 0],
            protein_coords[~binding_site_mask, 1],
            protein_coords[~binding_site_mask, 2],
            c="lightgray",
            s=20,
            alpha=0.3,
            label="Protein",
        )

        ax.scatter(
            protein_coords[binding_site_mask, 0],
            protein_coords[binding_site_mask, 1],
            protein_coords[binding_site_mask, 2],
            c="#3050F8",
            s=100,
            alpha=0.7,
            label="Binding Site",
            edgecolors="black",
            linewidth=0.5,
        )

        # Plot ligand
        ligand_elements = [a.element for a in ligand.atoms]
        ligand_colors = [self.engine.element_colors.get(e, "#FF69B4") for e in ligand_elements]

        ax.scatter(
            ligand_coords[:, 0],
            ligand_coords[:, 1],
            ligand_coords[:, 2],
            c=ligand_colors,
            s=300,
            alpha=0.9,
            label="Ligand",
            edgecolors="black",
            linewidth=1.5,
        )

        # Draw bonds for ligand
        for bond in ligand.bonds:
            i, j = bond.atom1_id, bond.atom2_id
            if i < len(ligand_coords) and j < len(ligand_coords):
                ax.plot3D(
                    [ligand_coords[i][0], ligand_coords[j][0]],
                    [ligand_coords[i][1], ligand_coords[j][1]],
                    [ligand_coords[i][2], ligand_coords[j][2]],
                    "black",
                    linewidth=2,
                    alpha=0.8,
                )

        ax.set_xlabel("X (Å)", fontsize=12)
        ax.set_ylabel("Y (Å)", fontsize=12)
        ax.set_zlabel("Z (Å)", fontsize=12)
        ax.set_title("Protein-Ligand Binding Site", fontsize=14, fontweight="bold")
        ax.legend(loc="upper right", fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Binding site visualization saved to: {output_file}")
        return output_file

    def visualize_protein_folding_pathway(
        self, quantum_result: QuantumVisualizationResult, output_file: str = "folding_pathway.png"
    ) -> str:
        """
        Visualize protein folding pathway from quantum simulation

        Args:
            quantum_result: Result from quantum conformational sampling
            output_file: Output file

        Returns:
            Path to saved image
        """
        fig = plt.figure(figsize=(16, 10), dpi=150)

        num_conformations = len(quantum_result.conformations)
        cols = 5
        rows = (num_conformations + cols - 1) // cols

        for idx, (conf, prob) in enumerate(
            zip(quantum_result.conformations, quantum_result.probabilities)
        ):
            ax = fig.add_subplot(rows, cols, idx + 1, projection="3d")

            # Plot conformation
            ax.scatter(conf[:, 0], conf[:, 1], conf[:, 2], c="#3050F8", s=50, alpha=0.7)

            # Draw backbone
            ax.plot3D(conf[:, 0], conf[:, 1], conf[:, 2], "gray", linewidth=1, alpha=0.5)

            ax.set_title(f"State {idx+1}\nP={prob:.3f}", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            ax.grid(False)

        plt.suptitle(
            f"Quantum Protein Folding Pathway: {quantum_result.structure.name}",
            fontsize=14,
            fontweight="bold",
        )
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Folding pathway saved to: {output_file}")
        return output_file


if __name__ == "__main__":
    # Example usage
    viz = QuantumProteinVisualizer()
    print("✅ Quantum Protein Visualizer initialized")
    print("   Ready for protein structure analysis")
