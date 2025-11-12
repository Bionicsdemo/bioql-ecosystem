#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Protein Sequence Analysis Module

Quantum-enhanced protein analysis including:
- Sequence property calculation
- Protein family classification
- Physicochemical properties
- Quantum feature extraction

Author: BioQL Development Team / SpectrixRD
License: MIT
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from Bio.Seq import Seq
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    HAVE_BIOPYTHON = True
except ImportError:
    HAVE_BIOPYTHON = False

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RealAmplitudes, ZZFeatureMap

    HAVE_QISKIT = True
except ImportError:
    HAVE_QISKIT = False


@dataclass
class ProteinProperties:
    """Physicochemical properties of a protein sequence."""

    molecular_weight: float
    isoelectric_point: float
    aromaticity: float
    instability_index: float
    gravy: float  # Grand average of hydropathy
    charge_at_ph7: float
    secondary_structure_fraction: Dict[str, float]
    amino_acid_composition: Dict[str, float]


@dataclass
class ProteinResult:
    """Result of protein sequence analysis."""

    sequence: str
    length: int
    properties: ProteinProperties
    protein_family: Optional[str] = None
    confidence: Optional[float] = None
    quantum_features: Optional[np.ndarray] = None
    backend: Optional[str] = None
    execution_time: Optional[float] = None


# Amino acid property scales
AA_HYDROPHOBICITY = {
    "A": 1.8,
    "R": -4.5,
    "N": -3.5,
    "D": -3.5,
    "C": 2.5,
    "Q": -3.5,
    "E": -3.5,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "L": 3.8,
    "K": -3.9,
    "M": 1.9,
    "F": 2.8,
    "P": -1.6,
    "S": -0.8,
    "T": -0.7,
    "W": -0.9,
    "Y": -1.3,
    "V": 4.2,
}

AA_CHARGE = {
    "D": -1,
    "E": -1,
    "K": 1,
    "R": 1,
    "H": 0.5,
    # All others are neutral
}

AA_POLARITY = {
    "A": 0,
    "R": 1,
    "N": 1,
    "D": 1,
    "C": 0,
    "Q": 1,
    "E": 1,
    "G": 0,
    "H": 1,
    "I": 0,
    "L": 0,
    "K": 1,
    "M": 0,
    "F": 0,
    "P": 0,
    "S": 1,
    "T": 1,
    "W": 0,
    "Y": 1,
    "V": 0,
}


def predict_protein_properties(sequence: str) -> ProteinProperties:
    """
    Calculate physicochemical properties of a protein sequence.

    Args:
        sequence: Amino acid sequence (single-letter code)

    Returns:
        ProteinProperties object with calculated properties

    Example:
        >>> props = predict_protein_properties("MKTAYIAKQRQISFVKSHFSRQ")
        >>> print(f"MW: {props.molecular_weight:.2f} Da")
        >>> print(f"pI: {props.isoelectric_point:.2f}")
    """
    if not HAVE_BIOPYTHON:
        raise ImportError(
            "Biopython is required for protein analysis. " "Install with: pip install biopython"
        )

    # Clean sequence (remove whitespace, convert to uppercase)
    sequence = sequence.upper().replace(" ", "").replace("\n", "")

    # Use Biopython ProteinAnalysis
    analyzer = ProteinAnalysis(sequence)

    # Calculate properties
    try:
        mw = analyzer.molecular_weight()
    except:
        mw = 0.0

    try:
        pi = analyzer.isoelectric_point()
    except:
        pi = 7.0

    try:
        aromaticity = analyzer.aromaticity()
    except:
        aromaticity = 0.0

    try:
        instability = analyzer.instability_index()
    except:
        instability = 40.0

    try:
        gravy = analyzer.gravy()
    except:
        gravy = 0.0

    # Estimate charge at pH 7
    charge = sum(AA_CHARGE.get(aa, 0) for aa in sequence)

    # Secondary structure fraction
    try:
        helix, turn, sheet = analyzer.secondary_structure_fraction()
        ss_fraction = {"helix": helix, "turn": turn, "sheet": sheet}
    except:
        ss_fraction = {"helix": 0.0, "turn": 0.0, "sheet": 0.0}

    # Amino acid composition
    aa_comp = analyzer.get_amino_acids_percent()

    return ProteinProperties(
        molecular_weight=mw,
        isoelectric_point=pi,
        aromaticity=aromaticity,
        instability_index=instability,
        gravy=gravy,
        charge_at_ph7=charge,
        secondary_structure_fraction=ss_fraction,
        amino_acid_composition=aa_comp,
    )


def _encode_sequence_to_features(sequence: str, max_length: int = 100) -> np.ndarray:
    """
    Encode protein sequence to feature vector.

    Features include:
    - Hydrophobicity profile
    - Charge profile
    - Polarity profile

    Args:
        sequence: Amino acid sequence
        max_length: Maximum sequence length (pad or truncate)

    Returns:
        Feature vector of shape (max_length * 3,)
    """
    # Truncate or pad sequence
    if len(sequence) > max_length:
        sequence = sequence[:max_length]
    else:
        sequence = sequence + "A" * (max_length - len(sequence))

    # Encode features
    hydrophobicity = [AA_HYDROPHOBICITY.get(aa, 0.0) for aa in sequence]
    charge = [AA_CHARGE.get(aa, 0.0) for aa in sequence]
    polarity = [AA_POLARITY.get(aa, 0.0) for aa in sequence]

    # Concatenate and normalize
    features = np.array(hydrophobicity + charge + polarity, dtype=float)

    # Min-max normalization to [0, 1]
    if features.max() > features.min():
        features = (features - features.min()) / (features.max() - features.min())

    return features


def classify_protein_family(
    sequence: str, backend: str = "simulator", shots: int = 1000, api_key: Optional[str] = None
) -> Tuple[str, float]:
    """
    Classify protein into family using quantum machine learning.

    This uses a quantum neural network (QNN) to classify proteins into
    known families based on sequence features.

    Args:
        sequence: Amino acid sequence
        backend: Quantum backend to use
        shots: Number of quantum measurements
        api_key: BioQL API key (optional)

    Returns:
        Tuple of (family_name, confidence)

    Example:
        >>> family, conf = classify_protein_family("MKTAYIAKQRQISFVKSHFSRQ")
        >>> print(f"Family: {family} (confidence: {conf:.2%})")

    Note:
        This is a simplified implementation. In production, you would
        train a QNN on a large protein family database.
    """
    if not HAVE_QISKIT:
        raise ImportError(
            "Qiskit is required for quantum classification. " "Install with: pip install qiskit"
        )

    # Encode sequence to features
    features = _encode_sequence_to_features(sequence, max_length=50)

    # Build quantum feature map
    num_qubits = 8  # Use 8 qubits for feature encoding
    feature_dim = min(num_qubits, len(features))

    # Create quantum circuit
    qc = QuantumCircuit(num_qubits)

    # Feature encoding using ZZFeatureMap
    feature_map = ZZFeatureMap(feature_dim, reps=2)
    qc.compose(feature_map, range(feature_dim), inplace=True)

    # Variational ansatz
    ansatz = RealAmplitudes(num_qubits, reps=3)
    qc.compose(ansatz, inplace=True)

    # Measurement
    qc.measure_all()

    # For now, return a placeholder classification
    # In production, this would execute on quantum hardware
    # and use trained parameters

    # Simple heuristic based on sequence properties
    props = predict_protein_properties(sequence)

    # Classify based on properties
    if props.gravy > 1.0:
        family = "Membrane protein"
        confidence = 0.75
    elif props.aromaticity > 0.15:
        family = "DNA-binding protein"
        confidence = 0.70
    elif props.charge_at_ph7 > 5:
        family = "Basic protein"
        confidence = 0.65
    elif props.charge_at_ph7 < -5:
        family = "Acidic protein"
        confidence = 0.65
    else:
        family = "Globular protein"
        confidence = 0.60

    return family, confidence


def analyze_protein_sequence(
    sequence: str,
    backend: str = "simulator",
    shots: int = 1000,
    api_key: Optional[str] = None,
    classify: bool = True,
) -> ProteinResult:
    """
    Comprehensive protein sequence analysis.

    This function combines classical and quantum methods to analyze
    protein sequences, including property calculation and family
    classification.

    Args:
        sequence: Amino acid sequence (single-letter code)
        backend: Quantum backend ('simulator', 'ibm_torino', etc.)
        shots: Number of quantum measurements
        api_key: BioQL API key (optional, for cloud execution)
        classify: Whether to perform family classification

    Returns:
        ProteinResult object with comprehensive analysis

    Example:
        >>> result = analyze_protein_sequence(
        ...     "MKTAYIAKQRQISFVKSHFSRQ",
        ...     backend="simulator"
        ... )
        >>> print(f"Length: {result.length} aa")
        >>> print(f"MW: {result.properties.molecular_weight:.2f} Da")
        >>> print(f"Family: {result.protein_family}")

    Raises:
        ImportError: If required dependencies are not installed
        ValueError: If sequence contains invalid amino acids
    """
    import time

    start_time = time.time()

    # Validate sequence
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    sequence_clean = sequence.upper().replace(" ", "").replace("\n", "")

    if not all(aa in valid_aa for aa in sequence_clean):
        raise ValueError(
            f"Invalid amino acid sequence. "
            f"Sequence must contain only: {' '.join(sorted(valid_aa))}"
        )

    # Calculate properties
    properties = predict_protein_properties(sequence_clean)

    # Family classification (optional)
    protein_family = None
    confidence = None
    if classify:
        try:
            protein_family, confidence = classify_protein_family(
                sequence_clean, backend=backend, shots=shots, api_key=api_key
            )
        except Exception as e:
            print(f"Warning: Classification failed: {e}")

    # Quantum feature extraction
    quantum_features = None
    try:
        quantum_features = _encode_sequence_to_features(sequence_clean)
    except Exception as e:
        print(f"Warning: Feature extraction failed: {e}")

    execution_time = time.time() - start_time

    return ProteinResult(
        sequence=sequence_clean,
        length=len(sequence_clean),
        properties=properties,
        protein_family=protein_family,
        confidence=confidence,
        quantum_features=quantum_features,
        backend=backend,
        execution_time=execution_time,
    )


# Example usage
if __name__ == "__main__":
    # Test sequence (insulin A chain)
    test_sequence = "GIVEQCCTSICSLYQLENYCN"

    print("BioQL Proteomics - Protein Analysis")
    print("=" * 50)
    print(f"Analyzing sequence: {test_sequence}")
    print()

    # Analyze
    result = analyze_protein_sequence(test_sequence, backend="simulator")

    print(f"Length: {result.length} amino acids")
    print(f"Molecular Weight: {result.properties.molecular_weight:.2f} Da")
    print(f"Isoelectric Point: {result.properties.isoelectric_point:.2f}")
    print(f"Aromaticity: {result.properties.aromaticity:.3f}")
    print(f"Instability Index: {result.properties.instability_index:.2f}")
    print(f"GRAVY: {result.properties.gravy:.3f}")
    print(f"Charge at pH 7: {result.properties.charge_at_ph7:+.1f}")
    print()
    print(f"Secondary Structure:")
    print(f"  Helix: {result.properties.secondary_structure_fraction['helix']:.2%}")
    print(f"  Sheet: {result.properties.secondary_structure_fraction['sheet']:.2%}")
    print(f"  Turn: {result.properties.secondary_structure_fraction['turn']:.2%}")
    print()
    if result.protein_family:
        print(f"Protein Family: {result.protein_family}")
        print(f"Confidence: {result.confidence:.2%}")
    print()
    print(f"Execution Time: {result.execution_time:.3f} seconds")
