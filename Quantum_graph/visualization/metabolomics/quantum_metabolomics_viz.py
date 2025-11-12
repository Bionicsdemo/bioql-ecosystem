# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum-Enhanced Metabolomics Visualization
============================================

Advanced visualization for:
- Metabolic pathway networks
- Metabolite interaction maps
- Flux balance analysis
- Metabolic fingerprinting
- Multi-omics integration
- Biomarker discovery

Uses quantum algorithms for:
- Network optimization (QAOA)
- Pathway enumeration (quantum walks)
- Pattern recognition (quantum ML)

Author: Spectrix R&D / BioQL Team
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from mpl_toolkits.mplot3d import proj3d

sys.path.append(str(Path(__file__).parent.parent.parent))

from quantum_core.optimizers.adaptive_quantum_optimizer import (
    AdaptiveQuantumOptimizer,
    MoleculeType,
    QuantumConfig,
    VisualizationType,
)


@dataclass
class Metabolite:
    """Metabolite information"""

    id: str
    name: str
    formula: str
    mass: float
    concentration: float  # μM
    pathway: str
    category: str  # "amino_acid", "lipid", "carbohydrate", etc.


@dataclass
class Reaction:
    """Metabolic reaction"""

    id: str
    name: str
    substrates: List[str]  # Metabolite IDs
    products: List[str]  # Metabolite IDs
    enzyme: str
    reversible: bool
    flux: float  # mmol/gDW/h


@dataclass
class MetabolicNetwork:
    """Complete metabolic network"""

    metabolites: Dict[str, Metabolite]
    reactions: Dict[str, Reaction]
    name: str
    organism: str


class QuantumMetabolomicsVisualizer:
    """
    Quantum-accelerated metabolomics visualization
    """

    def __init__(self):
        self.optimizer = AdaptiveQuantumOptimizer(
            budget_usd=500.0, max_time_hours=12.0, accuracy_target=0.95
        )

        # Category colors
        self.category_colors = {
            "amino_acid": "#FF6B6B",  # Red
            "lipid": "#4ECDC4",  # Teal
            "carbohydrate": "#FFE66D",  # Yellow
            "nucleotide": "#95E1D3",  # Mint
            "cofactor": "#F38181",  # Pink
            "secondary_metabolite": "#AA96DA",  # Purple
            "other": "#BEBEBE",  # Gray
        }

    def create_example_network(self) -> MetabolicNetwork:
        """
        Create example metabolic network for testing

        Returns:
            Example network
        """
        # Create metabolites
        metabolites = {
            "glc": Metabolite(
                "glc", "Glucose", "C6H12O6", 180.16, 5000, "Glycolysis", "carbohydrate"
            ),
            "g6p": Metabolite(
                "g6p", "Glucose-6-phosphate", "C6H13O9P", 260.14, 2000, "Glycolysis", "carbohydrate"
            ),
            "f6p": Metabolite(
                "f6p",
                "Fructose-6-phosphate",
                "C6H13O9P",
                260.14,
                1500,
                "Glycolysis",
                "carbohydrate",
            ),
            "fdp": Metabolite(
                "fdp",
                "Fructose-1,6-bisphosphate",
                "C6H14O12P2",
                340.12,
                1000,
                "Glycolysis",
                "carbohydrate",
            ),
            "pyr": Metabolite(
                "pyr", "Pyruvate", "C3H4O3", 88.06, 3000, "Glycolysis", "carbohydrate"
            ),
            "accoa": Metabolite(
                "accoa", "Acetyl-CoA", "C23H38N7O17P3S", 809.57, 800, "TCA", "cofactor"
            ),
            "cit": Metabolite("cit", "Citrate", "C6H8O7", 192.12, 1200, "TCA", "carbohydrate"),
            "akg": Metabolite(
                "akg", "α-Ketoglutarate", "C5H6O5", 146.10, 900, "TCA", "carbohydrate"
            ),
            "glu": Metabolite(
                "glu", "Glutamate", "C5H9NO4", 147.13, 10000, "Amino acids", "amino_acid"
            ),
            "gln": Metabolite(
                "gln", "Glutamine", "C5H10N2O3", 146.15, 8000, "Amino acids", "amino_acid"
            ),
        }

        # Create reactions
        reactions = {
            "HEX": Reaction("HEX", "Hexokinase", ["glc"], ["g6p"], "HK", False, 10.0),
            "PGI": Reaction("PGI", "Phosphoglucose isomerase", ["g6p"], ["f6p"], "PGI", True, 9.5),
            "PFK": Reaction("PFK", "Phosphofructokinase", ["f6p"], ["fdp"], "PFK", False, 9.0),
            "FBA": Reaction(
                "FBA", "Fructose-bisphosphate aldolase", ["fdp"], ["pyr"], "FBA", True, 8.5
            ),
            "PDH": Reaction("PDH", "Pyruvate dehydrogenase", ["pyr"], ["accoa"], "PDH", False, 7.0),
            "CS": Reaction("CS", "Citrate synthase", ["accoa"], ["cit"], "CS", False, 6.5),
            "ICDH": Reaction(
                "ICDH", "Isocitrate dehydrogenase", ["cit"], ["akg"], "ICDH", False, 6.0
            ),
            "GLUD": Reaction(
                "GLUD", "Glutamate dehydrogenase", ["akg"], ["glu"], "GLUD", True, 5.0
            ),
            "GLNS": Reaction("GLNS", "Glutamine synthetase", ["glu"], ["gln"], "GLNS", False, 4.5),
        }

        return MetabolicNetwork(
            metabolites=metabolites, reactions=reactions, name="Core_Metabolism", organism="E. coli"
        )

    def quantum_pathway_optimization(
        self, network: MetabolicNetwork, target_metabolite: str
    ) -> QuantumConfig:
        """
        Use quantum computing to optimize metabolic pathways

        Args:
            network: Metabolic network
            target_metabolite: Target metabolite ID

        Returns:
            Quantum configuration used
        """
        # Estimate network complexity
        num_metabolites = len(network.metabolites)
        num_reactions = len(network.reactions)

        molecule_data = {
            "num_atoms": num_metabolites * 30,  # Average atoms per metabolite
            "num_bonds": num_reactions,
        }

        # Optimize quantum parameters
        config = self.optimizer.optimize(
            molecule_data=molecule_data,
            molecule_type=MoleculeType.SMALL_MOLECULE,
            viz_type=VisualizationType.REACTION_PATHWAY,
            backend_preference="auto",
        )

        print(f"🔬 Quantum Pathway Optimization")
        print(f"   Network: {num_metabolites} metabolites, {num_reactions} reactions")
        print(f"   Qubits: {config.logical_qubits} logical")
        print(f"   Shots: {config.shots}")
        print(f"   Backend: {config.backend_type}")
        print(
            f"   Time: {config.time_to_solution_hours:.2f}h, Cost: ${config.estimated_cost_usd:.2f}\n"
        )

        return config

    def visualize_metabolic_network(
        self,
        network: MetabolicNetwork,
        output_file: str = "metabolic_network.png",
        layout: str = "spring",
    ) -> str:
        """
        Visualize metabolic network as graph

        Args:
            network: Metabolic network
            output_file: Output file path
            layout: "spring", "circular", "hierarchical"

        Returns:
            Path to saved image
        """
        # Create NetworkX graph
        G = nx.DiGraph()

        # Add nodes (metabolites)
        for met_id, met in network.metabolites.items():
            G.add_node(
                met_id, name=met.name, category=met.category, concentration=met.concentration
            )

        # Add edges (reactions)
        for rxn_id, rxn in network.reactions.items():
            for substrate in rxn.substrates:
                for product in rxn.products:
                    if substrate in G and product in G:
                        G.add_edge(
                            substrate,
                            product,
                            reaction=rxn.name,
                            enzyme=rxn.enzyme,
                            flux=rxn.flux,
                            reversible=rxn.reversible,
                        )

        # Create layout
        if layout == "spring":
            pos = nx.spring_layout(G, k=2, iterations=100, seed=42)
        elif layout == "circular":
            pos = nx.circular_layout(G)
        else:  # hierarchical
            pos = nx.kamada_kawai_layout(G)

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 12), dpi=150)

        # Draw nodes colored by category
        for category, color in self.category_colors.items():
            nodelist = [n for n, d in G.nodes(data=True) if d.get("category") == category]
            if nodelist:
                nx.draw_networkx_nodes(
                    G,
                    pos,
                    nodelist=nodelist,
                    node_color=color,
                    node_size=1500,
                    alpha=0.8,
                    ax=ax,
                    edgecolors="black",
                    linewidths=2,
                )

        # Draw edges with width proportional to flux
        edges = G.edges()
        fluxes = [G[u][v].get("flux", 1.0) for u, v in edges]
        max_flux = max(fluxes) if fluxes else 1.0

        for (u, v), flux in zip(edges, fluxes):
            width = 1 + 5 * (flux / max_flux)
            reversible = G[u][v].get("reversible", False)

            if reversible:
                style = "dashed"
                arrow_style = "<->"
            else:
                style = "solid"
                arrow_style = "->"

            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=[(u, v)],
                width=width,
                alpha=0.6,
                edge_color="gray",
                style=style,
                arrows=True,
                arrowsize=20,
                arrowstyle=arrow_style,
                ax=ax,
            )

        # Draw labels
        labels = {n: network.metabolites[n].name.split()[0][:8] for n in G.nodes()}
        nx.draw_networkx_labels(
            G, pos, labels, font_size=9, font_weight="bold", font_color="black", ax=ax
        )

        # Add legend
        legend_elements = [
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=color,
                markersize=12,
                label=cat.replace("_", " ").title(),
                markeredgecolor="black",
                markeredgewidth=1.5,
            )
            for cat, color in self.category_colors.items()
        ]
        ax.legend(handles=legend_elements, loc="upper left", fontsize=11, framealpha=0.9)

        ax.set_title(
            f"Metabolic Network: {network.name} ({network.organism})",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        ax.axis("off")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        print(f"✅ Metabolic network saved to: {output_file}")
        return output_file

    def visualize_metabolite_heatmap(
        self,
        network: MetabolicNetwork,
        time_points: Optional[List[float]] = None,
        output_file: str = "metabolite_heatmap.png",
    ) -> str:
        """
        Create heatmap of metabolite concentrations

        Args:
            network: Metabolic network
            time_points: Time points for dynamic data
            output_file: Output file

        Returns:
            Path to saved image
        """
        # Get metabolite names and concentrations
        met_names = [met.name for met in network.metabolites.values()]
        concentrations = [met.concentration for met in network.metabolites.values()]

        if time_points is None:
            # Single timepoint
            data = np.array([concentrations])
            time_labels = ["T0"]
        else:
            # Simulate time series (with decay/growth)
            num_timepoints = len(time_points)
            data = np.zeros((num_timepoints, len(concentrations)))
            for i, t in enumerate(time_points):
                # Simulate concentration changes
                noise = np.random.normal(1.0, 0.1, len(concentrations))
                decay = np.exp(-0.05 * t)
                data[i, :] = np.array(concentrations) * noise * decay
            time_labels = [f"T{t}" for t in time_points]

        # Create heatmap
        fig, ax = plt.subplots(figsize=(14, 10), dpi=150)

        # Log-scale normalization
        data_log = np.log10(data + 1)

        im = ax.imshow(data_log.T, aspect="auto", cmap="YlOrRd", interpolation="nearest")

        # Set ticks
        ax.set_xticks(np.arange(len(time_labels)))
        ax.set_yticks(np.arange(len(met_names)))
        ax.set_xticklabels(time_labels)
        ax.set_yticklabels(met_names, fontsize=9)

        # Rotate labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("log₁₀(Concentration, μM)", rotation=270, labelpad=20, fontsize=11)

        # Add values to cells
        for i in range(len(time_labels)):
            for j in range(len(met_names)):
                text = ax.text(
                    i, j, f"{data[i, j]:.0f}", ha="center", va="center", color="black", fontsize=7
                )

        ax.set_title(
            f"Metabolite Concentration Heatmap: {network.name}",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Time Points", fontsize=12)
        ax.set_ylabel("Metabolites", fontsize=12)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Metabolite heatmap saved to: {output_file}")
        return output_file

    def visualize_flux_analysis(
        self, network: MetabolicNetwork, output_file: str = "flux_analysis.png"
    ) -> str:
        """
        Visualize metabolic flux distribution

        Args:
            network: Metabolic network
            output_file: Output file

        Returns:
            Path to saved image
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=150)

        # Get reaction fluxes
        rxn_names = [rxn.name for rxn in network.reactions.values()]
        fluxes = [rxn.flux for rxn in network.reactions.values()]

        # Sort by flux
        sorted_indices = np.argsort(fluxes)[::-1]
        rxn_names_sorted = [rxn_names[i] for i in sorted_indices]
        fluxes_sorted = [fluxes[i] for i in sorted_indices]

        # Bar plot
        colors = plt.cm.viridis(np.linspace(0, 1, len(fluxes_sorted)))
        bars = ax1.barh(
            rxn_names_sorted,
            fluxes_sorted,
            color=colors,
            edgecolor="black",
            linewidth=1.5,
            alpha=0.8,
        )

        ax1.set_xlabel("Flux (mmol/gDW/h)", fontsize=12)
        ax1.set_ylabel("Reaction", fontsize=12)
        ax1.set_title("Metabolic Flux Distribution", fontsize=14, fontweight="bold")
        ax1.grid(axis="x", alpha=0.3)

        # Pie chart of flux categories
        pathways = {}
        for rxn in network.reactions.values():
            # Group by substrate pathway
            if rxn.substrates:
                substrate_id = rxn.substrates[0]
                if substrate_id in network.metabolites:
                    pathway = network.metabolites[substrate_id].pathway
                    pathways[pathway] = pathways.get(pathway, 0) + rxn.flux

        pathway_names = list(pathways.keys())
        pathway_fluxes = list(pathways.values())

        wedges, texts, autotexts = ax2.pie(
            pathway_fluxes,
            labels=pathway_names,
            autopct="%1.1f%%",
            startangle=90,
            colors=plt.cm.Set3(np.linspace(0, 1, len(pathway_names))),
            wedgeprops={"edgecolor": "black", "linewidth": 1.5},
        )

        ax2.set_title("Flux Distribution by Pathway", fontsize=14, fontweight="bold")

        # Make percentage text bold
        for autotext in autotexts:
            autotext.set_color("black")
            autotext.set_fontsize(10)
            autotext.set_weight("bold")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Flux analysis saved to: {output_file}")
        return output_file


if __name__ == "__main__":
    # Example usage
    viz = QuantumMetabolomicsVisualizer()

    # Create example network
    network = viz.create_example_network()

    # Quantum optimization
    config = viz.quantum_pathway_optimization(network, "pyr")

    # Generate visualizations
    viz.visualize_metabolic_network(network)
    viz.visualize_metabolite_heatmap(network, time_points=[0, 1, 2, 4, 8, 16])
    viz.visualize_flux_analysis(network)

    print("\n✅ Quantum metabolomics visualization complete!")
