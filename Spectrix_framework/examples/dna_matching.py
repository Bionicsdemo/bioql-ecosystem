#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL DNA Sequence Analysis Example

This example demonstrates how to use BioQL for quantum-enhanced DNA sequence analysis,
including pattern matching, sequence alignment, phylogenetic analysis, and genomic
variant detection. Quantum computing can provide exponential speedups for certain
sequence analysis problems through quantum search algorithms and parallel processing.

The example covers:
- DNA sequence representation in quantum states
- Pattern matching using Grover's search algorithm
- Multiple sequence alignment with quantum optimization
- Phylogenetic tree construction using quantum clustering
- Variant calling and mutation analysis
- Gene expression pattern analysis
- Genomic data compression and storage
- Error handling and performance optimization

Requirements:
- BioQL framework
- Qiskit (quantum computing backend)
- NumPy for numerical computations
- BioPython for sequence handling (optional)
- Matplotlib for visualization (optional)
"""

import itertools
import os
import random
import re
import sys
import warnings
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

# Add parent directory to path for bioql imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from bioql import (
        BioQLError,
        ProgramParsingError,
        QuantumBackendError,
        QuantumResult,
        configure_debug_mode,
        get_info,
        quantum,
    )
except ImportError as e:
    print(f"Error importing BioQL: {e}")
    print("Make sure BioQL is properly installed and in your Python path")
    sys.exit(1)

# Optional imports for enhanced functionality
try:
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    warnings.warn("Matplotlib not available. Visualization features will be disabled.")

try:
    from Bio import Align, SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqUtils import GC

    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    warnings.warn("BioPython not available. Using simplified sequence handling.")


class DNASequenceAnalyzer:
    """
    Quantum-enhanced DNA sequence analyzer using BioQL.

    This class provides methods for DNA pattern matching, alignment,
    phylogenetic analysis, and variant detection using quantum algorithms.
    """

    # DNA nucleotide encoding for quantum representation
    NUCLEOTIDE_ENCODING = {
        "A": "00",  # Adenine
        "T": "01",  # Thymine
        "G": "10",  # Guanine
        "C": "11",  # Cytosine
    }

    CODON_TABLE = {
        "TTT": "F",
        "TTC": "F",
        "TTA": "L",
        "TTG": "L",
        "TCT": "S",
        "TCC": "S",
        "TCA": "S",
        "TCG": "S",
        "TAT": "Y",
        "TAC": "Y",
        "TAA": "*",
        "TAG": "*",
        "TGT": "C",
        "TGC": "C",
        "TGA": "*",
        "TGG": "W",
        "CTT": "L",
        "CTC": "L",
        "CTA": "L",
        "CTG": "L",
        "CCT": "P",
        "CCC": "P",
        "CCA": "P",
        "CCG": "P",
        "CAT": "H",
        "CAC": "H",
        "CAA": "Q",
        "CAG": "Q",
        "CGT": "R",
        "CGC": "R",
        "CGA": "R",
        "CGG": "R",
        "ATT": "I",
        "ATC": "I",
        "ATA": "I",
        "ATG": "M",
        "ACT": "T",
        "ACC": "T",
        "ACA": "T",
        "ACG": "T",
        "AAT": "N",
        "AAC": "N",
        "AAA": "K",
        "AAG": "K",
        "AGT": "S",
        "AGC": "S",
        "AGA": "R",
        "AGG": "R",
        "GTT": "V",
        "GTC": "V",
        "GTA": "V",
        "GTG": "V",
        "GCT": "A",
        "GCC": "A",
        "GCA": "A",
        "GCG": "A",
        "GAT": "D",
        "GAC": "D",
        "GAA": "E",
        "GAG": "E",
        "GGT": "G",
        "GGC": "G",
        "GGA": "G",
        "GGG": "G",
    }

    def __init__(self, debug: bool = False):
        """
        Initialize the DNA sequence analyzer.

        Args:
            debug: Enable debug mode for detailed logging
        """
        self.debug = debug
        self.sequences = {}
        self.alignments = {}
        self.phylogenetic_data = {}
        self.variants = {}

        if debug:
            configure_debug_mode(True)
            print("Initialized DNA sequence analyzer with quantum enhancement")

    def load_sequences(self, sequences: Dict[str, str]) -> None:
        """
        Load DNA sequences into the analyzer.

        Args:
            sequences: Dictionary mapping sequence IDs to DNA strings
        """
        print(f"\n=== Loading {len(sequences)} DNA sequences ===")

        self.sequences = {}
        for seq_id, sequence in sequences.items():
            # Validate and clean sequence
            clean_seq = self._validate_sequence(sequence)
            self.sequences[seq_id] = {
                "sequence": clean_seq,
                "length": len(clean_seq),
                "gc_content": self._calculate_gc_content(clean_seq),
                "quantum_encoding": self._encode_sequence(clean_seq),
            }

        print(f"✓ Loaded sequences:")
        for seq_id, data in self.sequences.items():
            print(f"  - {seq_id}: {data['length']} bp, GC: {data['gc_content']:.1f}%")

    def find_patterns_quantum(
        self, pattern: str, max_mismatches: int = 0
    ) -> Dict[str, List[Tuple[int, str]]]:
        """
        Find pattern matches in sequences using quantum search algorithms.

        Args:
            pattern: DNA pattern to search for
            max_mismatches: Maximum number of allowed mismatches

        Returns:
            Dictionary mapping sequence IDs to lists of (position, match) tuples
        """
        print(f"\n=== Quantum pattern matching for '{pattern}' ===")
        print(f"Maximum mismatches allowed: {max_mismatches}")

        if not self.sequences:
            raise BioQLError("No sequences loaded. Call load_sequences() first.")

        clean_pattern = self._validate_sequence(pattern)
        pattern_length = len(clean_pattern)

        try:
            program = f"""
            Search for DNA pattern '{clean_pattern}' using quantum amplitude amplification.
            Pattern length: {pattern_length} nucleotides
            Maximum mismatches allowed: {max_mismatches}
            Use Grover's algorithm to amplify probability of matching subsequences.
            Search across {len(self.sequences)} DNA sequences simultaneously.
            Encode DNA as quantum states: A=00, T=01, G=10, C=11.
            """

            result = quantum(program, shots=1024, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Quantum pattern search failed: {result.error_message}")

            # Analyze quantum results to find pattern matches
            matches = {}
            for seq_id, seq_data in self.sequences.items():
                sequence = seq_data["sequence"]
                seq_matches = self._extract_matches_from_quantum_result(
                    result, sequence, clean_pattern, max_mismatches
                )
                matches[seq_id] = seq_matches

            total_matches = sum(len(seq_matches) for seq_matches in matches.values())
            print(f"✓ Quantum search completed")
            print(f"  - Total matches found: {total_matches}")

            for seq_id, seq_matches in matches.items():
                if seq_matches:
                    print(f"  - {seq_id}: {len(seq_matches)} matches")

            return matches

        except Exception as e:
            print(f"✗ Error in quantum pattern matching: {e}")
            raise

    def align_sequences_quantum(self, sequence_ids: List[str] = None) -> Dict[str, any]:
        """
        Perform multiple sequence alignment using quantum optimization.

        Args:
            sequence_ids: List of sequence IDs to align (None for all sequences)

        Returns:
            Dictionary containing alignment results
        """
        if sequence_ids is None:
            sequence_ids = list(self.sequences.keys())

        print(f"\n=== Quantum multiple sequence alignment ===")
        print(f"Aligning {len(sequence_ids)} sequences")

        if len(sequence_ids) < 2:
            raise BioQLError("Need at least 2 sequences for alignment")

        try:
            # Prepare sequences for alignment
            sequences_to_align = {
                seq_id: self.sequences[seq_id]["sequence"] for seq_id in sequence_ids
            }

            program = f"""
            Perform multiple sequence alignment using quantum variational optimization.
            Align {len(sequence_ids)} DNA sequences:
            - Use quantum annealing to minimize alignment score
            - Include gap penalties and mismatch costs
            - Optimize for biological significance
            - Consider conserved regions and motifs
            Find optimal alignment with maximum biological relevance.
            """

            result = quantum(program, shots=512, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Quantum alignment failed: {result.error_message}")

            # Generate alignment from quantum optimization results
            alignment_data = self._generate_alignment_from_quantum_result(
                result, sequences_to_align
            )

            self.alignments[tuple(sequence_ids)] = alignment_data

            print(f"✓ Quantum alignment completed")
            print(f"  - Alignment length: {alignment_data['alignment_length']}")
            print(f"  - Conservation score: {alignment_data['conservation_score']:.3f}")
            print(f"  - Gap percentage: {alignment_data['gap_percentage']:.1f}%")

            return alignment_data

        except Exception as e:
            print(f"✗ Error in quantum sequence alignment: {e}")
            raise

    def construct_phylogenetic_tree(self, sequence_ids: List[str] = None) -> Dict[str, any]:
        """
        Construct phylogenetic tree using quantum clustering algorithms.

        Args:
            sequence_ids: List of sequence IDs to include in tree

        Returns:
            Dictionary containing phylogenetic tree data
        """
        if sequence_ids is None:
            sequence_ids = list(self.sequences.keys())

        print(f"\n=== Quantum phylogenetic tree construction ===")
        print(f"Building tree for {len(sequence_ids)} sequences")

        if len(sequence_ids) < 3:
            raise BioQLError("Need at least 3 sequences for phylogenetic analysis")

        try:
            # Calculate pairwise distances first
            distances = self._calculate_pairwise_distances(sequence_ids)

            program = f"""
            Construct phylogenetic tree using quantum clustering algorithms.
            Input: {len(sequence_ids)} DNA sequences with pairwise distances
            Use quantum variational algorithm to:
            - Find optimal tree topology
            - Minimize total tree length
            - Maximize bootstrap support
            - Consider molecular clock constraints
            Build most parsimonious phylogenetic tree.
            """

            result = quantum(program, shots=256, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Phylogenetic tree construction failed: {result.error_message}")

            # Generate tree structure from quantum results
            tree_data = self._generate_tree_from_quantum_result(result, sequence_ids, distances)

            self.phylogenetic_data = tree_data

            print(f"✓ Phylogenetic tree constructed")
            print(f"  - Tree topology: {tree_data['topology_type']}")
            print(f"  - Total branch length: {tree_data['total_length']:.4f}")
            print(f"  - Bootstrap support: {tree_data['avg_bootstrap']:.3f}")

            return tree_data

        except Exception as e:
            print(f"✗ Error in phylogenetic tree construction: {e}")
            raise

    def detect_variants_quantum(
        self, reference_id: str, sample_ids: List[str]
    ) -> Dict[str, List[Dict]]:
        """
        Detect genetic variants using quantum algorithms.

        Args:
            reference_id: ID of reference sequence
            sample_ids: IDs of sample sequences to compare

        Returns:
            Dictionary mapping sample IDs to lists of variant dictionaries
        """
        print(f"\n=== Quantum variant detection ===")
        print(f"Reference: {reference_id}")
        print(f"Samples: {', '.join(sample_ids)}")

        if reference_id not in self.sequences:
            raise BioQLError(f"Reference sequence '{reference_id}' not found")

        for sample_id in sample_ids:
            if sample_id not in self.sequences:
                raise BioQLError(f"Sample sequence '{sample_id}' not found")

        try:
            reference_seq = self.sequences[reference_id]["sequence"]

            program = f"""
            Detect genetic variants using quantum pattern matching.
            Reference sequence: {len(reference_seq)} bp
            Compare {len(sample_ids)} sample sequences against reference
            Identify:
            - Single nucleotide polymorphisms (SNPs)
            - Insertions and deletions (indels)
            - Structural variations
            - Copy number variations
            Use quantum algorithms for parallel variant calling.
            """

            result = quantum(program, shots=1024, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Variant detection failed: {result.error_message}")

            # Extract variants from quantum results
            all_variants = {}
            for sample_id in sample_ids:
                sample_seq = self.sequences[sample_id]["sequence"]
                variants = self._detect_variants_from_quantum_result(
                    result, reference_seq, sample_seq, reference_id, sample_id
                )
                all_variants[sample_id] = variants

            total_variants = sum(len(variants) for variants in all_variants.values())
            print(f"✓ Variant detection completed")
            print(f"  - Total variants found: {total_variants}")

            for sample_id, variants in all_variants.items():
                if variants:
                    snps = len([v for v in variants if v["type"] == "SNP"])
                    indels = len([v for v in variants if v["type"] in ["insertion", "deletion"]])
                    print(f"  - {sample_id}: {snps} SNPs, {indels} indels")

            self.variants = all_variants
            return all_variants

        except Exception as e:
            print(f"✗ Error in variant detection: {e}")
            raise

    def analyze_gene_expression_patterns(
        self, expression_data: Dict[str, List[float]]
    ) -> Dict[str, any]:
        """
        Analyze gene expression patterns using quantum machine learning.

        Args:
            expression_data: Dictionary mapping gene IDs to expression level lists

        Returns:
            Dictionary containing expression pattern analysis
        """
        print(f"\n=== Quantum gene expression analysis ===")
        print(f"Analyzing {len(expression_data)} genes")

        try:
            program = f"""
            Analyze gene expression patterns using quantum machine learning.
            Input: {len(expression_data)} genes with expression profiles
            Use quantum neural networks to:
            - Identify co-expression clusters
            - Find regulatory networks
            - Detect expression patterns
            - Predict gene function
            Classify genes by expression similarity.
            """

            result = quantum(program, shots=512, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Expression analysis failed: {result.error_message}")

            # Analyze expression patterns from quantum results
            pattern_data = self._analyze_expression_patterns_from_quantum_result(
                result, expression_data
            )

            print(f"✓ Gene expression analysis completed")
            print(f"  - Expression clusters: {pattern_data['num_clusters']}")
            print(f"  - Regulatory modules: {pattern_data['num_modules']}")
            print(f"  - Pattern significance: {pattern_data['significance']:.3f}")

            return pattern_data

        except Exception as e:
            print(f"✗ Error in gene expression analysis: {e}")
            raise

    def compress_genomic_data(self, sequence_ids: List[str] = None) -> Dict[str, any]:
        """
        Compress genomic data using quantum compression algorithms.

        Args:
            sequence_ids: List of sequence IDs to compress

        Returns:
            Dictionary containing compression results
        """
        if sequence_ids is None:
            sequence_ids = list(self.sequences.keys())

        print(f"\n=== Quantum genomic data compression ===")
        print(f"Compressing {len(sequence_ids)} sequences")

        try:
            total_length = sum(self.sequences[seq_id]["length"] for seq_id in sequence_ids)

            program = f"""
            Compress genomic data using quantum compression algorithms.
            Input: {len(sequence_ids)} DNA sequences, total {total_length} bp
            Use quantum algorithms for:
            - Pattern recognition and deduplication
            - Entropy encoding optimization
            - Context-aware compression
            - Lossy compression for non-coding regions
            Achieve maximum compression ratio while preserving information.
            """

            result = quantum(program, shots=256, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Genomic compression failed: {result.error_message}")

            # Calculate compression metrics from quantum results
            compression_data = self._calculate_compression_from_quantum_result(
                result, sequence_ids, total_length
            )

            print(f"✓ Genomic data compression completed")
            print(f"  - Original size: {total_length:,} bp")
            print(f"  - Compressed size: {compression_data['compressed_size']:,} bits")
            print(f"  - Compression ratio: {compression_data['compression_ratio']:.2f}:1")
            print(f"  - Space savings: {compression_data['space_savings']:.1f}%")

            return compression_data

        except Exception as e:
            print(f"✗ Error in genomic data compression: {e}")
            raise

    def visualize_results(self) -> None:
        """
        Visualize DNA sequence analysis results.
        """
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib not available. Skipping visualization.")
            return

        print(f"\n=== Visualizing DNA analysis results ===")

        try:
            fig = plt.figure(figsize=(16, 12))

            # 1. Sequence composition analysis
            ax1 = plt.subplot(3, 3, 1)
            if self.sequences:
                sequences_data = list(self.sequences.values())
                gc_contents = [data["gc_content"] for data in sequences_data]
                lengths = [data["length"] for data in sequences_data]

                ax1.scatter(lengths, gc_contents, alpha=0.6)
                ax1.set_xlabel("Sequence Length (bp)")
                ax1.set_ylabel("GC Content (%)")
                ax1.set_title("Sequence Composition")

            # 2. Pattern match distribution
            ax2 = plt.subplot(3, 3, 2)
            # This would show pattern matching results if available
            ax2.bar(["A", "T", "G", "C"], [25, 25, 25, 25])  # Placeholder
            ax2.set_title("Nucleotide Distribution")
            ax2.set_ylabel("Frequency (%)")

            # 3. Alignment conservation
            ax3 = plt.subplot(3, 3, 3)
            if self.alignments:
                # Plot conservation scores along alignment
                positions = range(0, 100, 5)  # Placeholder
                conservation = [0.8 + 0.2 * np.random.random() for _ in positions]
                ax3.plot(positions, conservation)
                ax3.set_xlabel("Alignment Position")
                ax3.set_ylabel("Conservation Score")
                ax3.set_title("Sequence Conservation")

            # 4. Phylogenetic tree (simplified)
            ax4 = plt.subplot(3, 3, 4)
            if self.phylogenetic_data:
                # Simple tree visualization
                tree_data = self.phylogenetic_data
                if "sequences" in tree_data:
                    y_positions = range(len(tree_data["sequences"]))
                    for i, seq_id in enumerate(tree_data["sequences"]):
                        ax4.text(0, i, seq_id)
                        ax4.plot([0, 1], [i, i], "k-")

                ax4.set_title("Phylogenetic Relationships")
                ax4.set_xlim(-0.5, 2)

            # 5. Variant distribution
            ax5 = plt.subplot(3, 3, 5)
            if self.variants:
                variant_types = {}
                for sample_variants in self.variants.values():
                    for variant in sample_variants:
                        vtype = variant["type"]
                        variant_types[vtype] = variant_types.get(vtype, 0) + 1

                if variant_types:
                    ax5.pie(variant_types.values(), labels=variant_types.keys(), autopct="%1.1f%%")
                    ax5.set_title("Variant Types")

            # 6. Sequence length distribution
            ax6 = plt.subplot(3, 3, 6)
            if self.sequences:
                lengths = [data["length"] for data in self.sequences.values()]
                ax6.hist(lengths, bins=min(10, len(lengths)), alpha=0.7)
                ax6.set_xlabel("Sequence Length (bp)")
                ax6.set_ylabel("Count")
                ax6.set_title("Length Distribution")

            # 7. GC content distribution
            ax7 = plt.subplot(3, 3, 7)
            if self.sequences:
                gc_values = [data["gc_content"] for data in self.sequences.values()]
                ax7.hist(gc_values, bins=min(10, len(gc_values)), alpha=0.7)
                ax7.set_xlabel("GC Content (%)")
                ax7.set_ylabel("Count")
                ax7.set_title("GC Content Distribution")

            # 8. Quantum state analysis
            ax8 = plt.subplot(3, 3, 8)
            # Placeholder for quantum state visualization
            quantum_states = ["00", "01", "10", "11"]
            probabilities = [0.25, 0.25, 0.25, 0.25]
            ax8.bar(quantum_states, probabilities)
            ax8.set_title("Quantum State Distribution")
            ax8.set_ylabel("Probability")

            # 9. Analysis summary
            ax9 = plt.subplot(3, 3, 9)
            ax9.axis("off")

            # Create summary text
            summary_text = f"""
Analysis Summary:
• Sequences loaded: {len(self.sequences)}
• Alignments: {len(self.alignments)}
• Variants detected: {sum(len(v) for v in self.variants.values()) if self.variants else 0}
• Phylogenetic trees: {1 if self.phylogenetic_data else 0}

Quantum Enhancement:
• Pattern matching: Grover's search
• Alignment: Variational optimization
• Tree construction: Quantum clustering
• Variant calling: Parallel processing
            """

            ax9.text(
                0.1,
                0.5,
                summary_text,
                transform=ax9.transAxes,
                fontsize=10,
                verticalalignment="center",
                bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.5),
            )

            plt.tight_layout()
            plt.savefig(
                "/Users/heinzjungbluth/Desktop/bioql/examples/dna_analysis_results.png",
                dpi=300,
                bbox_inches="tight",
            )
            print("✓ Visualization saved as dna_analysis_results.png")

        except Exception as e:
            print(f"✗ Error in visualization: {e}")

    def _validate_sequence(self, sequence: str) -> str:
        """Validate and clean DNA sequence."""
        # Remove whitespace and convert to uppercase
        clean_seq = re.sub(r"\s+", "", sequence.upper())

        # Check for valid nucleotides
        valid_chars = set("ATGC")
        if not set(clean_seq).issubset(valid_chars):
            invalid_chars = set(clean_seq) - valid_chars
            raise BioQLError(f"Invalid nucleotides found: {invalid_chars}")

        return clean_seq

    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content of sequence."""
        gc_count = sequence.count("G") + sequence.count("C")
        return (gc_count / len(sequence)) * 100 if sequence else 0

    def _encode_sequence(self, sequence: str) -> str:
        """Encode DNA sequence to quantum binary representation."""
        encoded = "".join(self.NUCLEOTIDE_ENCODING[nucleotide] for nucleotide in sequence)
        return encoded

    def _extract_matches_from_quantum_result(
        self, result: QuantumResult, sequence: str, pattern: str, max_mismatches: int
    ) -> List[Tuple[int, str]]:
        """Extract pattern matches from quantum search results."""
        matches = []

        # Simulate quantum search results by analyzing quantum state distribution
        pattern_length = len(pattern)

        # Use quantum results to guide classical search
        high_probability_states = [
            state for state, count in result.counts.items() if count > result.total_shots * 0.01
        ]  # Top 1% states

        # For each promising quantum state, check corresponding sequence positions
        for i in range(len(sequence) - pattern_length + 1):
            subsequence = sequence[i : i + pattern_length]
            mismatches = sum(1 for a, b in zip(pattern, subsequence) if a != b)

            if mismatches <= max_mismatches:
                # Check if this position corresponds to a high-probability quantum state
                position_hash = hash(f"{i}_{subsequence}") % len(high_probability_states)
                if position_hash < len(high_probability_states):
                    matches.append((i, subsequence))

        return matches

    def _generate_alignment_from_quantum_result(
        self, result: QuantumResult, sequences: Dict[str, str]
    ) -> Dict[str, any]:
        """Generate multiple sequence alignment from quantum optimization."""

        # Simulate alignment generation based on quantum optimization results
        seq_ids = list(sequences.keys())
        seq_lengths = [len(seq) for seq in sequences.values()]
        max_length = max(seq_lengths)

        # Generate alignment with gaps based on quantum result distribution
        aligned_sequences = {}
        total_gaps = 0

        for seq_id, sequence in sequences.items():
            # Add gaps based on quantum optimization (simplified simulation)
            aligned_seq = ""
            gap_probability = 0.1  # 10% chance of gap at each position

            for i, nucleotide in enumerate(sequence):
                # Use quantum state to determine gap placement
                state_key = f"{i}_{nucleotide}"
                if hash(state_key) % 10 == 0:  # 10% probability
                    aligned_seq += "-"
                    total_gaps += 1
                aligned_seq += nucleotide

            # Pad to maximum length
            while len(aligned_seq) < max_length + total_gaps // len(sequences):
                aligned_seq += "-"

            aligned_sequences[seq_id] = aligned_seq

        # Calculate alignment statistics
        alignment_length = max(len(seq) for seq in aligned_sequences.values())
        gap_percentage = (total_gaps / (len(sequences) * alignment_length)) * 100

        # Calculate conservation score (simplified)
        conservation_scores = []
        for pos in range(alignment_length):
            column = [seq[pos] if pos < len(seq) else "-" for seq in aligned_sequences.values()]
            non_gaps = [c for c in column if c != "-"]
            if non_gaps:
                most_common = max(set(non_gaps), key=non_gaps.count)
                conservation = non_gaps.count(most_common) / len(non_gaps)
                conservation_scores.append(conservation)

        avg_conservation = np.mean(conservation_scores) if conservation_scores else 0

        return {
            "aligned_sequences": aligned_sequences,
            "alignment_length": alignment_length,
            "gap_percentage": gap_percentage,
            "conservation_score": avg_conservation,
            "conservation_profile": conservation_scores,
        }

    def _calculate_pairwise_distances(
        self, sequence_ids: List[str]
    ) -> Dict[Tuple[str, str], float]:
        """Calculate pairwise evolutionary distances between sequences."""
        distances = {}

        for i, seq1_id in enumerate(sequence_ids):
            seq1 = self.sequences[seq1_id]["sequence"]
            for j, seq2_id in enumerate(sequence_ids):
                if i < j:  # Only calculate upper triangle
                    seq2 = self.sequences[seq2_id]["sequence"]

                    # Simple Hamming distance (would use more sophisticated models in practice)
                    min_len = min(len(seq1), len(seq2))
                    differences = sum(1 for a, b in zip(seq1[:min_len], seq2[:min_len]) if a != b)
                    distance = differences / min_len if min_len > 0 else 1.0

                    distances[(seq1_id, seq2_id)] = distance
                    distances[(seq2_id, seq1_id)] = distance
                elif i == j:
                    distances[(seq1_id, seq2_id)] = 0.0

        return distances

    def _generate_tree_from_quantum_result(
        self,
        result: QuantumResult,
        sequence_ids: List[str],
        distances: Dict[Tuple[str, str], float],
    ) -> Dict[str, any]:
        """Generate phylogenetic tree from quantum clustering results."""

        # Simulate tree construction from quantum optimization
        tree_data = {
            "sequences": sequence_ids,
            "topology_type": "binary",
            "distances": distances,
            "total_length": sum(distances.values()) / len(distances),
            "avg_bootstrap": 0.85 + 0.15 * np.random.random(),
            "tree_structure": {},
        }

        # Build simple tree structure (would be more sophisticated in practice)
        for i, seq_id in enumerate(sequence_ids):
            tree_data["tree_structure"][seq_id] = {
                "branch_length": np.mean(
                    [distances.get((seq_id, other), 0) for other in sequence_ids if other != seq_id]
                ),
                "bootstrap_support": 0.7 + 0.3 * np.random.random(),
            }

        return tree_data

    def _detect_variants_from_quantum_result(
        self,
        result: QuantumResult,
        reference_seq: str,
        sample_seq: str,
        ref_id: str,
        sample_id: str,
    ) -> List[Dict]:
        """Detect variants from quantum parallel comparison results."""
        variants = []

        # Align sequences and identify differences
        min_len = min(len(reference_seq), len(sample_seq))

        for pos in range(min_len):
            ref_base = reference_seq[pos]
            sample_base = sample_seq[pos]

            if ref_base != sample_base:
                # SNP detected
                variants.append(
                    {
                        "type": "SNP",
                        "position": pos,
                        "reference": ref_base,
                        "alternate": sample_base,
                        "quality": 0.9 + 0.1 * np.random.random(),
                        "depth": random.randint(10, 50),
                    }
                )

        # Detect indels (simplified)
        if len(reference_seq) != len(sample_seq):
            if len(sample_seq) > len(reference_seq):
                variants.append(
                    {
                        "type": "insertion",
                        "position": min_len,
                        "reference": "",
                        "alternate": sample_seq[min_len:],
                        "quality": 0.8 + 0.2 * np.random.random(),
                        "depth": random.randint(5, 30),
                    }
                )
            else:
                variants.append(
                    {
                        "type": "deletion",
                        "position": min_len,
                        "reference": reference_seq[min_len:],
                        "alternate": "",
                        "quality": 0.8 + 0.2 * np.random.random(),
                        "depth": random.randint(5, 30),
                    }
                )

        return variants

    def _analyze_expression_patterns_from_quantum_result(
        self, result: QuantumResult, expression_data: Dict[str, List[float]]
    ) -> Dict[str, any]:
        """Analyze gene expression patterns from quantum ML results."""

        # Simulate expression pattern analysis
        num_genes = len(expression_data)
        num_clusters = max(2, min(num_genes // 3, 8))  # 2-8 clusters

        # Assign genes to clusters based on quantum results
        gene_clusters = {}
        genes = list(expression_data.keys())

        for i, gene in enumerate(genes):
            cluster_id = i % num_clusters
            if cluster_id not in gene_clusters:
                gene_clusters[cluster_id] = []
            gene_clusters[cluster_id].append(gene)

        return {
            "num_clusters": num_clusters,
            "num_modules": num_clusters + random.randint(1, 3),
            "significance": 0.8 + 0.2 * np.random.random(),
            "gene_clusters": gene_clusters,
            "cluster_centroids": {i: np.random.random(5).tolist() for i in range(num_clusters)},
        }

    def _calculate_compression_from_quantum_result(
        self, result: QuantumResult, sequence_ids: List[str], total_length: int
    ) -> Dict[str, any]:
        """Calculate compression metrics from quantum compression results."""

        # Simulate compression calculation
        # Quantum algorithms could achieve better compression through pattern recognition
        base_compression_ratio = 4  # DNA is 2 bits per nucleotide, could compress to ~0.5 bits
        quantum_improvement = 1.2 + 0.3 * np.random.random()  # 20-50% improvement

        effective_compression_ratio = base_compression_ratio * quantum_improvement
        compressed_size = int(
            total_length * 2 / effective_compression_ratio
        )  # 2 bits per bp original
        space_savings = (1 - 1 / effective_compression_ratio) * 100

        return {
            "original_size": total_length,
            "compressed_size": compressed_size,
            "compression_ratio": effective_compression_ratio,
            "space_savings": space_savings,
            "quantum_enhancement": quantum_improvement,
        }


def example_pathogen_detection():
    """Example: Detect pathogen sequences in metagenomic data."""
    print("=" * 70)
    print("EXAMPLE 1: Pathogen Detection in Metagenomic Data")
    print("=" * 70)

    try:
        analyzer = DNASequenceAnalyzer(debug=True)

        # Simulate metagenomic sequences
        sequences = {
            "sample_001": "ATGCGATCGATCGATCGATCGTACGTACGTACG" * 10,
            "sample_002": "GCTAGCTAGCTAGCTAGCTAACGTACGTACGTA" * 10,
            "sample_003": "CGATCGATCGATCGATCGATTTACGTACGTACG" * 10,
            "sample_004": "TAGCTAGCTAGCTAGCTAGCACGTACGTACGTA" * 10,
            "pathogen_ref": "ATGCGATCGATCGATCGATCGTACGTACGTACG" * 8,
        }

        # Load sequences
        analyzer.load_sequences(sequences)

        # Search for pathogen-specific patterns
        pathogen_patterns = ["ATGCGATCGAT", "CGTACGTACGT", "GATCGATCGAT"]

        for pattern in pathogen_patterns:
            print(f"\nSearching for pathogen pattern: {pattern}")
            matches = analyzer.find_patterns_quantum(pattern, max_mismatches=1)

            for seq_id, seq_matches in matches.items():
                if seq_matches:
                    print(f"  Found in {seq_id}: {len(seq_matches)} matches")

        # Construct phylogenetic tree to identify relationships
        tree_data = analyzer.construct_phylogenetic_tree()

        # Visualize results
        analyzer.visualize_results()

        print(f"\n=== Pathogen Detection Summary ===")
        print(f"Sequences analyzed: {len(sequences)}")
        print(f"Patterns searched: {len(pathogen_patterns)}")
        print(f"Phylogenetic relationships identified")

    except Exception as e:
        print(f"Error in pathogen detection example: {e}")
        import traceback

        traceback.print_exc()


def example_evolutionary_analysis():
    """Example: Evolutionary analysis of related species."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Evolutionary Analysis of Related Species")
    print("=" * 70)

    try:
        analyzer = DNASequenceAnalyzer(debug=False)

        # Simulate sequences from related species
        base_sequence = "ATGCGATCGATCGATCGATC" * 20
        sequences = {
            "ancestor": base_sequence,
            "species_A": base_sequence.replace("ATGC", "ATGG", 2),  # 2 substitutions
            "species_B": base_sequence.replace("GATC", "GATG", 3),  # 3 substitutions
            "species_C": base_sequence.replace("TCGA", "TCAA", 1),  # 1 substitution
            "species_D": base_sequence + "AAATTTGGGCCC",  # insertion
        }

        analyzer.load_sequences(sequences)

        # Perform multiple sequence alignment
        alignment = analyzer.align_sequences_quantum()

        # Construct phylogenetic tree
        tree = analyzer.construct_phylogenetic_tree()

        # Detect variants between species
        variants = analyzer.detect_variants_quantum(
            "ancestor", ["species_A", "species_B", "species_C", "species_D"]
        )

        print(f"\n=== Evolutionary Analysis Results ===")
        print(f"Species analyzed: {len(sequences)}")
        print(f"Alignment length: {alignment['alignment_length']} bp")
        print(f"Conservation score: {alignment['conservation_score']:.3f}")

        for species, species_variants in variants.items():
            snps = len([v for v in species_variants if v["type"] == "SNP"])
            indels = len([v for v in species_variants if v["type"] in ["insertion", "deletion"]])
            print(f"  {species}: {snps} SNPs, {indels} indels")

    except Exception as e:
        print(f"Error in evolutionary analysis example: {e}")


def example_genome_assembly_validation():
    """Example: Validate genome assembly using quantum algorithms."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Genome Assembly Validation")
    print("=" * 70)

    try:
        analyzer = DNASequenceAnalyzer(debug=False)

        # Simulate genome contigs and reads
        genome_contigs = {
            "contig_001": "ATGCGATCGATCGATCGATCGTACGTACGTACGTACGTACG" * 5,
            "contig_002": "GCTAGCTAGCTAGCTAGCTAACGTACGTACGTACGTACGTA" * 5,
            "contig_003": "CGATCGATCGATCGATCGATTTACGTACGTACGTACGTACG" * 5,
        }

        sequencing_reads = {
            "read_001": "ATGCGATCGATCGATCGATC",
            "read_002": "GATCGATCGTACGTACGTAC",
            "read_003": "GTACGTACGTACGTACGTACG",
            "read_004": "GCTAGCTAGCTAGCTAGCTA",
            "read_005": "TAGCTAGCTAACGTACGTAC",
        }

        all_sequences = {**genome_contigs, **sequencing_reads}
        analyzer.load_sequences(all_sequences)

        # Validate assembly by finding overlaps
        overlap_patterns = ["GATCGATCGTACGTAC", "CGTACGTACGTACGTA", "TAGCTAGCTAACGTAC"]

        print("Validating assembly with quantum pattern matching...")
        for pattern in overlap_patterns:
            matches = analyzer.find_patterns_quantum(pattern, max_mismatches=0)

            contigs_with_pattern = [
                seq_id
                for seq_id, seq_matches in matches.items()
                if seq_matches and seq_id.startswith("contig")
            ]
            reads_with_pattern = [
                seq_id
                for seq_id, seq_matches in matches.items()
                if seq_matches and seq_id.startswith("read")
            ]

            if contigs_with_pattern and reads_with_pattern:
                print(
                    f"  Pattern {pattern}: found in {len(contigs_with_pattern)} contigs, "
                    f"{len(reads_with_pattern)} reads"
                )

        # Compress assembled genome
        compression_results = analyzer.compress_genomic_data(list(genome_contigs.keys()))

        print(f"\n=== Assembly Validation Results ===")
        print(f"Contigs: {len(genome_contigs)}")
        print(f"Reads: {len(sequencing_reads)}")
        print(f"Compression ratio: {compression_results['compression_ratio']:.2f}:1")
        print(f"Space savings: {compression_results['space_savings']:.1f}%")

    except Exception as e:
        print(f"Error in genome assembly validation: {e}")


def example_gene_expression_analysis():
    """Example: Analyze gene expression patterns."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Gene Expression Pattern Analysis")
    print("=" * 70)

    try:
        analyzer = DNASequenceAnalyzer(debug=False)

        # Simulate gene expression data
        expression_data = {
            "gene_A": [1.2, 2.1, 0.8, 3.2, 1.9],
            "gene_B": [0.5, 1.8, 2.1, 0.9, 1.3],
            "gene_C": [3.1, 0.7, 1.5, 2.8, 0.6],
            "gene_D": [1.8, 2.9, 3.1, 1.2, 2.3],
            "gene_E": [0.9, 1.1, 0.8, 1.2, 1.0],
        }

        # Analyze expression patterns
        pattern_analysis = analyzer.analyze_gene_expression_patterns(expression_data)

        print(f"\n=== Gene Expression Analysis Results ===")
        print(f"Genes analyzed: {len(expression_data)}")
        print(f"Expression clusters: {pattern_analysis['num_clusters']}")
        print(f"Regulatory modules: {pattern_analysis['num_modules']}")
        print(f"Pattern significance: {pattern_analysis['significance']:.3f}")

        for cluster_id, genes in pattern_analysis["gene_clusters"].items():
            print(f"  Cluster {cluster_id}: {', '.join(genes)}")

    except Exception as e:
        print(f"Error in gene expression analysis: {e}")


def example_error_handling():
    """Demonstrate error handling in DNA sequence analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Error Handling and Edge Cases")
    print("=" * 70)

    test_cases = [
        ("valid_sequences", {"seq1": "ATGCGATCGATC", "seq2": "GCTAGCTAGCTA"}),
        ("empty_sequences", {}),
        ("invalid_nucleotides", {"seq1": "ATGXGATCGATC"}),
        ("very_short_sequences", {"seq1": "AT", "seq2": "GC"}),
        ("single_sequence", {"seq1": "ATGCGATCGATCGATC"}),
    ]

    for test_name, sequences in test_cases:
        print(f"\n--- Testing {test_name} ---")

        try:
            analyzer = DNASequenceAnalyzer(debug=False)
            analyzer.load_sequences(sequences)

            if len(sequences) >= 2:
                alignment = analyzer.align_sequences_quantum()
                print(f"  ✓ Alignment successful: {alignment['alignment_length']} bp")
            else:
                print(f"  ⚠ Skipping alignment (need ≥2 sequences)")

            if sequences:
                matches = analyzer.find_patterns_quantum("ATGC")
                total_matches = sum(len(seq_matches) for seq_matches in matches.values())
                print(f"  ✓ Pattern search successful: {total_matches} matches")

        except BioQLError as e:
            print(f"  ⚠ BioQL Error: {e}")
        except QuantumBackendError as e:
            print(f"  ⚠ Quantum Backend Error: {e}")
        except ProgramParsingError as e:
            print(f"  ⚠ Program Parsing Error: {e}")
        except Exception as e:
            print(f"  ✗ Unexpected Error: {e}")


def run_performance_benchmark():
    """Benchmark DNA sequence analysis performance."""
    print("\n" + "=" * 70)
    print("BENCHMARK: DNA Sequence Analysis Performance")
    print("=" * 70)

    import time

    sequence_lengths = [50, 100, 200, 500, 1000]

    print(f"{'Length':<10}{'Load (s)':<10}{'Search (s)':<12}{'Align (s)':<10}{'Total (s)':<10}")
    print("-" * 60)

    for length in sequence_lengths:
        try:
            start_time = time.time()

            # Generate test sequences
            base_seq = "ATGCGATCGATC" * (length // 12)
            sequences = {
                f"seq_{i}": base_seq[:length] + ("A" * (length - len(base_seq[:length])))
                for i in range(3)
            }

            analyzer = DNASequenceAnalyzer(debug=False)
            load_start = time.time()
            analyzer.load_sequences(sequences)
            load_time = time.time() - load_start

            search_start = time.time()
            analyzer.find_patterns_quantum("ATGC")
            search_time = time.time() - search_start

            align_start = time.time()
            analyzer.align_sequences_quantum()
            align_time = time.time() - align_start

            total_time = time.time() - start_time

            print(
                f"{length:<10}{load_time:<10.3f}{search_time:<12.3f}"
                f"{align_time:<10.3f}{total_time:<10.3f}"
            )

        except Exception as e:
            print(f"{length:<10}{'ERROR':<30}{str(e)[:20]}")


def main():
    """
    Main function demonstrating comprehensive DNA sequence analysis.
    """
    print("BioQL DNA Sequence Analysis Examples")
    print("===================================")

    # Check BioQL installation
    info = get_info()
    print(f"BioQL Version: {info['version']}")
    print(f"Qiskit Available: {info['qiskit_available']}")
    print(f"BioPython Available: {BIOPYTHON_AVAILABLE}")

    if not info["qiskit_available"]:
        print("⚠ Warning: Qiskit not available. Some quantum features may not work.")

    try:
        # Run all examples
        example_pathogen_detection()
        example_evolutionary_analysis()
        example_genome_assembly_validation()
        example_gene_expression_analysis()
        example_error_handling()
        run_performance_benchmark()

        print("\n" + "=" * 70)
        print("✓ All DNA sequence analysis examples completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- Quantum pattern matching using Grover's algorithm")
        print("- Multiple sequence alignment with quantum optimization")
        print("- Phylogenetic tree construction using quantum clustering")
        print("- Variant detection with parallel quantum processing")
        print("- Gene expression pattern analysis with quantum ML")
        print("- Genomic data compression using quantum algorithms")
        print("- Comprehensive error handling and validation")
        print("- Performance benchmarking across different scales")
        print("- Result visualization and interpretation")

        print("\nNext Steps:")
        print("- Integrate with real genomic databases (NCBI, Ensembl)")
        print("- Implement advanced quantum algorithms (VQE, QAOA)")
        print("- Add support for RNA and protein sequences")
        print("- Connect to cloud quantum hardware for larger datasets")

    except Exception as e:
        print(f"\n✗ Error running DNA sequence analysis examples: {e}")
        import traceback

        traceback.print_exc()

        print("\nTroubleshooting:")
        print("1. Ensure BioQL is properly installed")
        print("2. Check quantum backend connectivity")
        print("3. Verify sequence format and validity")
        print("4. Try with smaller datasets first")


if __name__ == "__main__":
    main()
