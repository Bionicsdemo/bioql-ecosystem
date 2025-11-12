#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Syndrome Extraction and Detector Error Model
============================================

Implements syndrome extraction from stabilizer measurements and construction
of detector error models for minimum-weight perfect matching decoding.

Mathematical Foundation:
-----------------------
A syndrome is a binary vector s ∈ {0,1}^m where m is the number of stabilizers.
Each bit s[i] indicates whether the i-th stabilizer measurement eigenvalue is +1 (0) or -1 (1).

For an error chain E, the syndrome is:
    s[i] = ⟨ψ|E†S_i E|ψ⟩ mod 2

Detector Error Model (DEM):
--------------------------
Maps errors to syndromes: DEM = {(error, syndrome, probability)}
Used to construct decoding graph for MWPM algorithm.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import stim
from loguru import logger


@dataclass
class SyndromeVector:
    """Sparse representation of syndrome measurement."""

    detector_indices: np.ndarray  # Indices of triggered detectors
    round: int
    timestamp: float = 0.0

    @property
    def weight(self) -> int:
        """Hamming weight of syndrome."""
        return len(self.detector_indices)

    @property
    def is_trivial(self) -> bool:
        """Check if syndrome is all zeros."""
        return self.weight == 0

    def to_dense(self, num_detectors: int) -> np.ndarray:
        """Convert to dense binary vector."""
        dense = np.zeros(num_detectors, dtype=np.uint8)
        dense[self.detector_indices] = 1
        return dense


@dataclass
class DetectorEvent:
    """Single detector firing event."""

    detector_id: int
    round: int
    qubit_coords: Tuple[float, float]
    stabilizer_type: str  # 'X' or 'Z'

    def distance_to(self, other: "DetectorEvent") -> float:
        """Manhattan distance to another detector."""
        return abs(self.qubit_coords[0] - other.qubit_coords[0]) + abs(
            self.qubit_coords[1] - other.qubit_coords[1]
        )


class SyndromeExtractor:
    """
    Extracts syndromes from measurement records.

    Handles temporal correlation between consecutive QEC rounds.
    """

    def __init__(self, circuit: stim.Circuit):
        """
        Initialize syndrome extractor.

        Args:
            circuit: Stim circuit with detectors and observables
        """
        self.circuit = circuit
        self.num_detectors = circuit.num_detectors
        self.num_observables = circuit.num_observables

        # Parse detector metadata
        self.detector_coords = self._parse_detector_coords()

        logger.info(
            f"Initialized SyndromeExtractor: "
            f"{self.num_detectors} detectors, "
            f"{self.num_observables} observables"
        )

    def _parse_detector_coords(self) -> Dict[int, Tuple]:
        """Parse detector coordinates from circuit."""
        coords = {}
        detector_id = 0

        for instruction in self.circuit:
            if instruction.name == "DETECTOR":
                # Extract coordinates from instruction args
                if len(instruction.gate_args_copy()) > 0:
                    coords[detector_id] = tuple(instruction.gate_args_copy())
                else:
                    coords[detector_id] = (detector_id, 0)
                detector_id += 1

        return coords

    def extract_batch(self, measurements: np.ndarray) -> List[SyndromeVector]:
        """
        Extract syndromes from batch of measurements.

        Args:
            measurements: Shape (shots, num_measurements)

        Returns:
            List of syndrome vectors, one per shot
        """
        shots = measurements.shape[0]
        syndromes = []

        # Compile syndrome extraction circuit
        sampler = self.circuit.compile_detector_sampler()

        for shot_idx in range(shots):
            # Get triggered detectors
            detection_events = np.where(measurements[shot_idx] == 1)[0]

            syndrome = SyndromeVector(
                detector_indices=detection_events, round=0  # Will be set by temporal analysis
            )
            syndromes.append(syndrome)

        return syndromes

    def extract_temporal_correlation(
        self, syndrome_history: List[SyndromeVector]
    ) -> List[SyndromeVector]:
        """
        Extract temporal correlation between rounds.

        For surface codes, we XOR consecutive rounds to get space-time
        syndrome that indicates error chains.

        Args:
            syndrome_history: Syndromes from consecutive rounds

        Returns:
            Correlated syndrome vectors
        """
        if len(syndrome_history) < 2:
            return syndrome_history

        correlated = []
        for i in range(1, len(syndrome_history)):
            prev = syndrome_history[i - 1].to_dense(self.num_detectors)
            curr = syndrome_history[i].to_dense(self.num_detectors)

            # XOR to get changes
            diff = np.bitwise_xor(prev, curr)
            triggered = np.where(diff == 1)[0]

            correlated.append(SyndromeVector(detector_indices=triggered, round=i))

        return correlated


class DetectorErrorModel:
    """
    Detector Error Model for decoding.

    Maps error mechanisms to detector firing patterns.
    Constructs weighted graph for MWPM decoding.
    """

    def __init__(self, circuit: stim.Circuit):
        """
        Initialize DEM from circuit.

        Args:
            circuit: Stim circuit
        """
        self.circuit = circuit
        self.dem = circuit.detector_error_model(
            decompose_errors=True, approximate_disjoint_errors=True
        )

        # Parse DEM into graph structure
        self.graph = self._build_decoding_graph()

        logger.info(f"Built DEM: {len(self.graph.nodes)} nodes, " f"{len(self.graph.edges)} edges")

    def _build_decoding_graph(self) -> nx.Graph:
        """
        Build decoding graph from DEM.

        Nodes: detectors and boundary
        Edges: error mechanisms with weights -log(p)
        """
        G = nx.Graph()

        # Add detector nodes
        num_detectors = self.circuit.num_detectors
        for i in range(num_detectors):
            G.add_node(f"D{i}", type="detector", detector_id=i)

        # Add boundary node (for odd-weight syndromes)
        G.add_node("boundary", type="boundary")

        # Parse DEM instructions
        for instruction in self.dem:
            if instruction.type == "error":
                prob = instruction.args_copy()[0]
                targets = instruction.targets_copy()

                # Extract detector IDs from targets
                detectors = []
                for target in targets:
                    if target.is_relative_detector_id():
                        detectors.append(target.val)

                # Add edges for error mechanisms
                if len(detectors) == 2:
                    # Two detectors: regular edge
                    weight = -np.log(prob) if prob > 0 else 1e10
                    G.add_edge(
                        f"D{detectors[0]}", f"D{detectors[1]}", weight=weight, probability=prob
                    )
                elif len(detectors) == 1:
                    # Single detector: edge to boundary
                    weight = -np.log(prob) if prob > 0 else 1e10
                    G.add_edge(f"D{detectors[0]}", "boundary", weight=weight, probability=prob)

        return G

    def get_edge_weights(self) -> Dict[Tuple[int, int], float]:
        """
        Get edge weights for MWPM decoder.

        Returns:
            Dictionary mapping (detector1, detector2) -> weight
        """
        weights = {}
        for u, v, data in self.graph.edges(data=True):
            if u != "boundary" and v != "boundary":
                u_id = int(u[1:]) if u.startswith("D") else -1
                v_id = int(v[1:]) if v.startswith("D") else -1
                if u_id >= 0 and v_id >= 0:
                    weights[(u_id, v_id)] = data["weight"]
                    weights[(v_id, u_id)] = data["weight"]  # Symmetric
        return weights

    def export_to_file(self, filename: str):
        """Export DEM to .dem file format."""
        with open(filename, "w") as f:
            f.write(str(self.dem))
        logger.info(f"Exported DEM to {filename}")


class SyndromeGraph:
    """
    Graph representation of syndrome for decoding.

    Nodes: triggered detectors
    Edges: potential error chains
    """

    def __init__(self, syndrome: SyndromeVector, dem: DetectorErrorModel):
        """
        Initialize syndrome graph.

        Args:
            syndrome: Syndrome vector
            dem: Detector error model
        """
        self.syndrome = syndrome
        self.dem = dem
        self.graph = self._build_syndrome_graph()

    def _build_syndrome_graph(self) -> nx.Graph:
        """
        Build graph for MWPM.

        Only includes triggered detectors and relevant edges.
        """
        G = nx.Graph()

        # Add triggered detector nodes
        for det_id in self.syndrome.detector_indices:
            G.add_node(det_id, triggered=True)

        # Add boundary node if odd number of detectors
        if len(self.syndrome.detector_indices) % 2 == 1:
            G.add_node(-1, type="boundary")

        # Add edges from DEM
        for u, v, data in self.dem.graph.edges(data=True):
            u_id = int(u[1:]) if u.startswith("D") else -1
            v_id = int(v[1:]) if v.startswith("D") else -1

            # Only add if both nodes are triggered or one is boundary
            if (u_id in self.syndrome.detector_indices or u_id == -1) and (
                v_id in self.syndrome.detector_indices or v_id == -1
            ):
                G.add_edge(u_id, v_id, **data)

        return G

    def get_matching_problem(self) -> Tuple[List[int], Dict]:
        """
        Format for MWPM solver.

        Returns:
            (list of node IDs, edge weight dict)
        """
        nodes = list(self.graph.nodes())

        weights = {}
        for u, v, data in self.graph.edges(data=True):
            weights[(u, v)] = data["weight"]
            weights[(v, u)] = data["weight"]

        return nodes, weights

    def visualize(self, filename: Optional[str] = None):
        """Visualize syndrome graph."""
        import matplotlib.pyplot as plt

        pos = nx.spring_layout(self.graph)

        # Draw nodes
        triggered = [n for n in self.graph.nodes() if n >= 0]
        boundary = [n for n in self.graph.nodes() if n < 0]

        nx.draw_networkx_nodes(
            self.graph, pos, nodelist=triggered, node_color="red", label="Triggered"
        )
        if boundary:
            nx.draw_networkx_nodes(
                self.graph,
                pos,
                nodelist=boundary,
                node_color="blue",
                node_shape="s",
                label="Boundary",
            )

        # Draw edges with weights
        edge_labels = nx.get_edge_attributes(self.graph, "weight")
        edge_labels = {k: f"{v:.2f}" for k, v in edge_labels.items()}

        nx.draw_networkx_edges(self.graph, pos)
        nx.draw_networkx_labels(self.graph, pos)
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels)

        plt.legend()
        plt.title(f"Syndrome Graph (weight={self.syndrome.weight})")

        if filename:
            plt.savefig(filename, dpi=300, bbox_inches="tight")
            logger.info(f"Saved syndrome graph to {filename}")
        else:
            plt.show()

        plt.close()


class TemporalSyndromeTracker:
    """
    Tracks syndrome evolution across multiple QEC rounds.

    Maintains history for temporal correlation analysis.
    """

    def __init__(self, max_rounds: int = 100):
        """
        Initialize tracker.

        Args:
            max_rounds: Maximum rounds to track
        """
        self.max_rounds = max_rounds
        self.history: List[SyndromeVector] = []
        self.round_counter = 0

    def add_syndrome(self, syndrome: SyndromeVector):
        """Add syndrome measurement to history."""
        syndrome.round = self.round_counter
        self.history.append(syndrome)
        self.round_counter += 1

        # Keep only recent history
        if len(self.history) > self.max_rounds:
            self.history.pop(0)

    def get_correlated_syndromes(self) -> List[SyndromeVector]:
        """Get temporally correlated syndromes."""
        if len(self.history) < 2:
            return self.history

        correlated = []
        for i in range(1, len(self.history)):
            # XOR consecutive syndromes
            prev_set = set(self.history[i - 1].detector_indices)
            curr_set = set(self.history[i].detector_indices)

            # Symmetric difference = XOR
            diff = prev_set.symmetric_difference(curr_set)

            if len(diff) > 0:
                correlated.append(
                    SyndromeVector(
                        detector_indices=np.array(list(diff)), round=self.history[i].round
                    )
                )

        return correlated

    def detect_syndrome_pattern(self) -> Optional[str]:
        """
        Detect repeating syndrome patterns.

        Useful for identifying systematic errors.
        """
        if len(self.history) < 3:
            return None

        # Check for oscillation
        last_three = self.history[-3:]
        weights = [s.weight for s in last_three]

        if weights[0] == weights[2] and weights[0] != weights[1]:
            return "oscillation"

        # Check for growth
        if all(weights[i] < weights[i + 1] for i in range(len(weights) - 1)):
            return "growth"

        # Check for decay
        if all(weights[i] > weights[i + 1] for i in range(len(weights) - 1)):
            return "decay"

        return "stable"

    def get_statistics(self) -> Dict:
        """Get syndrome statistics over time."""
        if not self.history:
            return {}

        weights = [s.weight for s in self.history]

        return {
            "num_rounds": len(self.history),
            "avg_weight": np.mean(weights),
            "std_weight": np.std(weights),
            "max_weight": np.max(weights),
            "min_weight": np.min(weights),
            "trivial_rounds": sum(1 for s in self.history if s.is_trivial),
            "pattern": self.detect_syndrome_pattern(),
        }


def analyze_syndrome_distribution(syndromes: List[SyndromeVector]) -> Dict:
    """
    Analyze distribution of syndrome weights.

    Useful for understanding error characteristics.
    """
    weights = [s.weight for s in syndromes]

    # Hamming weight distribution
    weight_counts = defaultdict(int)
    for w in weights:
        weight_counts[w] += 1

    # Statistical measures
    weights_array = np.array(weights)

    return {
        "total_syndromes": len(syndromes),
        "weight_distribution": dict(weight_counts),
        "mean_weight": np.mean(weights_array),
        "median_weight": np.median(weights_array),
        "std_weight": np.std(weights_array),
        "max_weight": np.max(weights_array),
        "trivial_fraction": sum(1 for s in syndromes if s.is_trivial) / len(syndromes),
    }
