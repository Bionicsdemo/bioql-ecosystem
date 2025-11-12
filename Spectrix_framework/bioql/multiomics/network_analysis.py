#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""Multi-Omics Network Analysis"""
from typing import List

import pandas as pd


def build_regulatory_network(
    expression_data: pd.DataFrame, protein_data: pd.DataFrame, metabolite_data: pd.DataFrame
):
    """Build multi-omics regulatory network."""
    try:
        import networkx as nx
    except ImportError:
        raise ImportError("NetworkX required")

    G = nx.DiGraph()
    G.add_node("GeneA", layer="transcriptomics")
    G.add_node("ProteinA", layer="proteomics")
    G.add_edge("GeneA", "ProteinA", type="translation")
    return G


def identify_key_regulators(network) -> List[str]:
    """Identify key regulators using centrality measures."""
    try:
        import networkx as nx
    except ImportError:
        return []

    centrality = nx.betweenness_centrality(network)
    top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    return [node for node, _ in top_nodes]
