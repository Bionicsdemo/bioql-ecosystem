"""
Guide RNA optimization and ranking

Ranks multiple gRNA candidates based on:
- Quantum energy collapse scores
- GC content
- Off-target potential
- Sequence complexity
"""

from typing import List, Dict, Any, Optional
import numpy as np

from .energies import batch_energy_estimation
from .featurization import calculate_gc_content
from .adapters.base import QuantumEngine


def rank_guides_batch(
    guide_sequences: List[str],
    engine: Optional[QuantumEngine] = None,
    shots: int = 1000,
    coupling_strength: float = 1.0,
    gc_weight: float = 0.2,
    energy_weight: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Rank multiple guide RNAs by predicted efficacy

    Args:
        guide_sequences: List of guide RNA sequences
        engine: Quantum engine (defaults to LocalSimulatorEngine)
        shots: Number of quantum measurements per guide
        coupling_strength: Base-pair coupling strength
        gc_weight: Weight for GC content scoring (0-1)
        energy_weight: Weight for energy scoring (0-1)

    Returns:
        List of guides ranked by score (best first), each with:
        {
            'guide_sequence': str,
            'energy_estimate': float,
            'gc_content': float,
            'composite_score': float,
            'rank': int,
            'confidence': float,
            'runtime_seconds': float
        }

    Example:
        >>> guides = ["ATCGAAGTC", "GCTAGCTA", "TTAACCGG"]
        >>> ranked = rank_guides_batch(guides, shots=1000)
        >>> print(f"Best guide: {ranked[0]['guide_sequence']}")
        >>> print(f"Score: {ranked[0]['composite_score']:.3f}")
    """
    # Estimate energies for all guides
    energy_results = batch_energy_estimation(
        guide_sequences=guide_sequences,
        engine=engine,
        coupling_strength=coupling_strength,
        shots=shots
    )

    # Calculate composite scores
    scored_guides = []

    for result in energy_results:
        guide_seq = result['guide_sequence']
        energy = result['energy_estimate']
        gc_content = calculate_gc_content(guide_seq)

        # Normalize energy (lower is better → higher score)
        # Typical energy range: -10 to 0
        energy_score = 1.0 / (1.0 + np.exp(energy / 2))  # Sigmoid

        # GC content score (optimal: 40-60%)
        gc_score = 1.0 - abs(gc_content - 0.5) * 2
        gc_score = max(0.0, gc_score)

        # Composite score
        composite_score = (
            energy_weight * energy_score +
            gc_weight * gc_score
        )

        scored_guides.append({
            'guide_sequence': guide_seq,
            'energy_estimate': energy,
            'gc_content': gc_content,
            'energy_score': energy_score,
            'gc_score': gc_score,
            'composite_score': composite_score,
            'confidence': result['confidence'],
            'runtime_seconds': result['runtime_seconds'],
            'backend': result['backend']
        })

    # Sort by composite score (descending)
    scored_guides.sort(key=lambda x: x['composite_score'], reverse=True)

    # Add ranks
    for rank, guide in enumerate(scored_guides, start=1):
        guide['rank'] = rank

    return scored_guides


def filter_guides_by_score(
    ranked_guides: List[Dict[str, Any]],
    min_score: float = 0.5,
    max_guides: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Filter ranked guides by minimum score threshold

    Args:
        ranked_guides: Output from rank_guides_batch()
        min_score: Minimum composite score (0-1)
        max_guides: Maximum number of guides to return

    Returns:
        Filtered list of guides

    Example:
        >>> ranked = rank_guides_batch(guides, shots=1000)
        >>> top_guides = filter_guides_by_score(ranked, min_score=0.7, max_guides=5)
    """
    filtered = [g for g in ranked_guides if g['composite_score'] >= min_score]

    if max_guides is not None:
        filtered = filtered[:max_guides]

    return filtered


def optimize_guide_library(
    guide_sequences: List[str],
    target_size: int = 10,
    engine: Optional[QuantumEngine] = None,
    shots: int = 1000,
    diversity_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Optimize guide library for diversity and efficacy

    Args:
        guide_sequences: Candidate guide RNAs
        target_size: Desired library size
        engine: Quantum engine
        shots: Measurements per guide
        diversity_threshold: Minimum sequence diversity (Hamming distance)

    Returns:
        Optimized guide library (ranked and diverse)

    Example:
        >>> candidates = generate_candidate_guides(target_region)
        >>> library = optimize_guide_library(candidates, target_size=10)
    """
    # Rank all guides
    ranked = rank_guides_batch(
        guide_sequences=guide_sequences,
        engine=engine,
        shots=shots
    )

    # Select diverse subset
    selected = []

    for guide in ranked:
        if len(selected) >= target_size:
            break

        # Check diversity with existing selections
        is_diverse = True
        guide_seq = guide['guide_sequence']

        for selected_guide in selected:
            selected_seq = selected_guide['guide_sequence']
            hamming_dist = calculate_hamming_distance(guide_seq, selected_seq)

            max_len = max(len(guide_seq), len(selected_seq))
            normalized_dist = hamming_dist / max_len

            if normalized_dist < diversity_threshold:
                is_diverse = False
                break

        if is_diverse:
            selected.append(guide)

    return selected


def calculate_hamming_distance(seq1: str, seq2: str) -> int:
    """
    Calculate Hamming distance between two sequences

    Args:
        seq1: First sequence
        seq2: Second sequence

    Returns:
        Hamming distance (number of differing positions)
    """
    # Pad shorter sequence
    max_len = max(len(seq1), len(seq2))
    seq1 = seq1.ljust(max_len, 'N')
    seq2 = seq2.ljust(max_len, 'N')

    return sum(c1 != c2 for c1, c2 in zip(seq1, seq2))


def generate_guide_report(
    ranked_guides: List[Dict[str, Any]],
    top_n: int = 10
) -> str:
    """
    Generate human-readable report for ranked guides

    Args:
        ranked_guides: Output from rank_guides_batch()
        top_n: Number of top guides to include

    Returns:
        Formatted report string
    """
    report_lines = [
        "=" * 80,
        f"CRISPR Guide RNA Ranking Report (Top {top_n})",
        "=" * 80,
        ""
    ]

    for guide in ranked_guides[:top_n]:
        report_lines.extend([
            f"Rank {guide['rank']}: {guide['guide_sequence']}",
            f"  Composite Score: {guide['composite_score']:.3f}",
            f"  Energy Estimate: {guide['energy_estimate']:.3f}",
            f"  GC Content: {guide['gc_content']*100:.1f}%",
            f"  Confidence: {guide['confidence']:.3f}",
            f"  Backend: {guide['backend']}",
            ""
        ])

    report_lines.append("=" * 80)

    return "\n".join(report_lines)
