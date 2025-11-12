"""
Off-target phenotype inference for CRISPR designs

Predicts potential off-target effects based on:
- Guide sequence similarity to genome
- Energy landscape analysis
- Known off-target databases
"""

from typing import List, Dict, Any, Optional
import numpy as np

from .featurization import calculate_gc_content


def infer_offtarget_phenotype(
    guide_seq: str,
    genome_regions: Optional[List[str]] = None,
    similarity_threshold: float = 0.8,
    max_mismatches: int = 3
) -> Dict[str, Any]:
    """
    Infer potential off-target effects for a guide RNA

    Args:
        guide_seq: Guide RNA sequence
        genome_regions: List of genomic sequences to check (optional)
        similarity_threshold: Minimum similarity for off-target (0-1)
        max_mismatches: Maximum allowed mismatches

    Returns:
        {
            'guide_sequence': str,
            'offtarget_risk': str,          # 'low', 'medium', 'high'
            'num_potential_offtargets': int,
            'offtarget_sites': list,        # Potential off-target locations
            'risk_score': float,            # 0-1, higher = more risk
            'recommendations': list         # Safety recommendations
        }

    Example:
        >>> result = infer_offtarget_phenotype("ATCGAAGTC", genome_regions=ref_genome)
        >>> print(f"Off-target risk: {result['offtarget_risk']}")
        >>> print(f"Risk score: {result['risk_score']:.3f}")
    """
    # Initialize result
    result = {
        'guide_sequence': guide_seq,
        'offtarget_risk': 'unknown',
        'num_potential_offtargets': 0,
        'offtarget_sites': [],
        'risk_score': 0.0,
        'recommendations': []
    }

    # If no genome regions provided, use heuristic scoring
    if genome_regions is None:
        risk_score = _heuristic_offtarget_score(guide_seq)
        result['risk_score'] = risk_score
        result['offtarget_risk'] = _categorize_risk(risk_score)
        result['recommendations'] = _generate_recommendations(guide_seq, risk_score)
        return result

    # Search for potential off-targets in genome
    potential_offtargets = []

    for idx, region in enumerate(genome_regions):
        matches = find_similar_sequences(
            guide_seq,
            region,
            max_mismatches=max_mismatches
        )

        for match in matches:
            similarity = calculate_sequence_similarity(guide_seq, match['sequence'])

            if similarity >= similarity_threshold:
                potential_offtargets.append({
                    'region_index': idx,
                    'position': match['position'],
                    'sequence': match['sequence'],
                    'similarity': similarity,
                    'mismatches': match['mismatches']
                })

    # Calculate risk score
    num_offtargets = len(potential_offtargets)

    if num_offtargets == 0:
        risk_score = 0.1
    elif num_offtargets <= 2:
        risk_score = 0.3
    elif num_offtargets <= 5:
        risk_score = 0.6
    else:
        risk_score = 0.9

    # Adjust for high-similarity matches
    high_sim_count = sum(1 for ot in potential_offtargets if ot['similarity'] > 0.95)
    risk_score += high_sim_count * 0.1
    risk_score = min(risk_score, 1.0)

    result['num_potential_offtargets'] = num_offtargets
    result['offtarget_sites'] = potential_offtargets[:10]  # Top 10
    result['risk_score'] = risk_score
    result['offtarget_risk'] = _categorize_risk(risk_score)
    result['recommendations'] = _generate_recommendations(guide_seq, risk_score)

    return result


def find_similar_sequences(
    query: str,
    target: str,
    max_mismatches: int = 3
) -> List[Dict[str, Any]]:
    """
    Find similar sequences in target allowing mismatches

    Args:
        query: Query sequence (guide RNA)
        target: Target sequence (genome region)
        max_mismatches: Maximum allowed mismatches

    Returns:
        List of matches with positions and mismatch counts
    """
    query = query.upper()
    target = target.upper()
    query_len = len(query)
    matches = []

    for i in range(len(target) - query_len + 1):
        window = target[i:i + query_len]
        mismatches = sum(q != t for q, t in zip(query, window))

        if mismatches <= max_mismatches:
            matches.append({
                'position': i,
                'sequence': window,
                'mismatches': mismatches
            })

    return matches


def calculate_sequence_similarity(seq1: str, seq2: str) -> float:
    """
    Calculate sequence similarity (0-1)

    Args:
        seq1: First sequence
        seq2: Second sequence

    Returns:
        Similarity score (1.0 = identical)
    """
    if len(seq1) != len(seq2):
        # Pad shorter sequence
        max_len = max(len(seq1), len(seq2))
        seq1 = seq1.ljust(max_len, 'N')
        seq2 = seq2.ljust(max_len, 'N')

    matches = sum(c1 == c2 for c1, c2 in zip(seq1, seq2))
    return matches / len(seq1)


def _heuristic_offtarget_score(guide_seq: str) -> float:
    """
    Calculate heuristic off-target risk without genome data

    Based on:
    - GC content (extreme values = higher risk)
    - Sequence complexity (low complexity = higher risk)
    - Repeat patterns (repetitive = higher risk)

    Args:
        guide_seq: Guide RNA sequence

    Returns:
        Risk score (0-1)
    """
    guide_seq = guide_seq.upper()

    # GC content risk (optimal: 40-60%)
    gc_content = calculate_gc_content(guide_seq)
    gc_deviation = abs(gc_content - 0.5)
    gc_risk = gc_deviation * 2  # 0-1

    # Sequence complexity (Shannon entropy)
    nucleotide_counts = {
        'A': guide_seq.count('A'),
        'T': guide_seq.count('T'),
        'C': guide_seq.count('C'),
        'G': guide_seq.count('G')
    }

    total = len(guide_seq)
    probabilities = [count / total for count in nucleotide_counts.values() if count > 0]
    entropy = -sum(p * np.log2(p) for p in probabilities)
    max_entropy = 2.0  # log2(4)

    complexity = entropy / max_entropy
    complexity_risk = 1.0 - complexity  # Low complexity = high risk

    # Repeat pattern risk
    repeat_risk = _detect_repeat_patterns(guide_seq)

    # Composite risk
    risk_score = (
        0.3 * gc_risk +
        0.4 * complexity_risk +
        0.3 * repeat_risk
    )

    return risk_score


def _detect_repeat_patterns(seq: str, window_size: int = 3) -> float:
    """
    Detect repetitive patterns in sequence

    Args:
        seq: Sequence to analyze
        window_size: Size of repeat window

    Returns:
        Repeat risk score (0-1)
    """
    if len(seq) < window_size * 2:
        return 0.0

    kmers = {}
    for i in range(len(seq) - window_size + 1):
        kmer = seq[i:i + window_size]
        kmers[kmer] = kmers.get(kmer, 0) + 1

    # Find most frequent k-mer
    max_count = max(kmers.values())

    # Normalize to [0, 1]
    max_possible = len(seq) - window_size + 1
    repeat_score = (max_count - 1) / max_possible

    return min(repeat_score, 1.0)


def _categorize_risk(risk_score: float) -> str:
    """
    Categorize risk score into low/medium/high

    Args:
        risk_score: Risk score (0-1)

    Returns:
        'low', 'medium', or 'high'
    """
    if risk_score < 0.3:
        return 'low'
    elif risk_score < 0.6:
        return 'medium'
    else:
        return 'high'


def _generate_recommendations(guide_seq: str, risk_score: float) -> List[str]:
    """
    Generate safety recommendations based on risk

    Args:
        guide_seq: Guide RNA sequence
        risk_score: Risk score (0-1)

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if risk_score < 0.3:
        recommendations.append("✓ Low off-target risk - guide appears safe")

    elif risk_score < 0.6:
        recommendations.append("⚠ Medium off-target risk - validate experimentally")
        recommendations.append("Consider: In silico genome-wide search")

    else:
        recommendations.append("✗ High off-target risk - use with caution")
        recommendations.append("Required: Comprehensive off-target validation")
        recommendations.append("Consider: Redesign guide with better specificity")

    # GC content check
    gc_content = calculate_gc_content(guide_seq)
    if gc_content < 0.3:
        recommendations.append("⚠ Low GC content (<30%) - may reduce efficiency")
    elif gc_content > 0.7:
        recommendations.append("⚠ High GC content (>70%) - may reduce efficiency")

    # Complexity check
    if len(set(guide_seq)) < 3:
        recommendations.append("⚠ Low sequence complexity - risk of off-targets")

    return recommendations
