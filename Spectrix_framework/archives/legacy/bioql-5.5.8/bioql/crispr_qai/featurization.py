"""
Guide RNA sequence encoding for quantum circuits

Converts gRNA sequences (ATCG) into rotation angles for quantum gates:
- Each nucleotide → rotation angle
- Preserves sequence patterns
- Compatible with all quantum backends
"""

from typing import List, Dict
import numpy as np


# Nucleotide to angle mapping (radians)
NUCLEOTIDE_TO_ANGLE = {
    'A': 0.0,           # Adenine → 0°
    'T': np.pi / 2,     # Thymine → 90°
    'C': np.pi,         # Cytosine → 180°
    'G': 3 * np.pi / 2, # Guanine → 270°
}


def encode_guide_sequence(guide_seq: str) -> List[float]:
    """
    Encode gRNA sequence into rotation angles

    Args:
        guide_seq: Guide RNA sequence (e.g., "ATCGAAGTC")

    Returns:
        List of rotation angles (radians)

    Example:
        >>> encode_guide_sequence("ATCG")
        [0.0, 1.5707963267948966, 3.141592653589793, 4.71238898038469]
    """
    guide_seq = guide_seq.upper().strip()

    # Validate sequence
    if not guide_seq:
        raise ValueError("guide_seq cannot be empty")

    if not all(nuc in NUCLEOTIDE_TO_ANGLE for nuc in guide_seq):
        invalid = set(guide_seq) - set(NUCLEOTIDE_TO_ANGLE.keys())
        raise ValueError(
            f"Invalid nucleotides in sequence: {invalid}. "
            f"Expected: A, T, C, G"
        )

    # Convert to angles
    angles = [NUCLEOTIDE_TO_ANGLE[nuc] for nuc in guide_seq]

    return angles


def guide_to_angles(
    guide_seq: str,
    target_length: int = 20,
    pad_value: float = 0.0
) -> List[float]:
    """
    Convert gRNA to fixed-length angle list (for consistent circuit size)

    Args:
        guide_seq: Guide RNA sequence
        target_length: Desired number of qubits
        pad_value: Padding angle for short sequences (default: 0.0)

    Returns:
        Fixed-length list of rotation angles

    Example:
        >>> guide_to_angles("ATCG", target_length=6)
        [0.0, 1.5707963267948966, 3.141592653589793, 4.71238898038469, 0.0, 0.0]
    """
    angles = encode_guide_sequence(guide_seq)

    if len(angles) > target_length:
        # Truncate if too long
        return angles[:target_length]

    elif len(angles) < target_length:
        # Pad if too short
        padding = [pad_value] * (target_length - len(angles))
        return angles + padding

    else:
        # Exact length
        return angles


def decode_angles(angles: List[float], tolerance: float = 0.1) -> str:
    """
    Decode rotation angles back to nucleotide sequence

    Args:
        angles: List of rotation angles (radians)
        tolerance: Tolerance for angle matching (radians)

    Returns:
        Decoded nucleotide sequence

    Example:
        >>> angles = [0.0, 1.5707963267948966, 3.141592653589793]
        >>> decode_angles(angles)
        'ATC'
    """
    sequence = []

    for angle in angles:
        # Normalize angle to [0, 2π)
        angle = angle % (2 * np.pi)

        # Find closest nucleotide
        closest_nuc = None
        min_diff = float('inf')

        for nuc, nuc_angle in NUCLEOTIDE_TO_ANGLE.items():
            diff = abs(angle - nuc_angle)
            if diff < min_diff:
                min_diff = diff
                closest_nuc = nuc

        if min_diff > tolerance:
            sequence.append('N')  # Unknown
        else:
            sequence.append(closest_nuc)

    return ''.join(sequence)


def calculate_gc_content(guide_seq: str) -> float:
    """
    Calculate GC content of guide sequence

    Args:
        guide_seq: Guide RNA sequence

    Returns:
        GC content (0.0 - 1.0)
    """
    guide_seq = guide_seq.upper()
    gc_count = guide_seq.count('G') + guide_seq.count('C')
    total = len(guide_seq)

    if total == 0:
        return 0.0

    return gc_count / total


def encode_with_features(guide_seq: str) -> Dict[str, any]:
    """
    Encode guide with additional sequence features

    Args:
        guide_seq: Guide RNA sequence

    Returns:
        Dictionary with angles and features
    """
    angles = encode_guide_sequence(guide_seq)
    gc_content = calculate_gc_content(guide_seq)

    return {
        'angles': angles,
        'sequence': guide_seq,
        'length': len(guide_seq),
        'gc_content': gc_content,
        'num_qubits': len(angles)
    }
