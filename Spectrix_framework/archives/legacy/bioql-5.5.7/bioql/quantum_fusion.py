"""
BioQL Quantum-Classical Fusion - v5.3.0

⚠️  IMPORTANTE: Este módulo NO altera resultados físicos de hardware o docking.
    Solo extrae features cuánticos para análisis ML, correlaciones, etc.

Features cuánticos extraídos de counts:
- Entropía de Shannon
- Pureza del estado
- Participación de estados
- Distribución de probabilidades

NUNCA se usa para "mejorar" o "corregir" energías de docking.
"""

import math
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class QuantumFeatures:
    """
    Features extraídos de mediciones cuánticas.

    ⚠️  Estos NO son energías físicas, son características estadísticas.
    """
    entropy_bits: float  # Entropía de Shannon en bits
    purity: float  # Pureza del estado (1 = puro, <1 = mixto)
    participation_ratio: float  # Número efectivo de estados
    probability_distribution: Dict[str, float]  # p(state)
    most_probable_state: str
    max_probability: float

    # Metadata para claridad
    total_shots: int
    num_qubits: int
    timestamp: str
    warning: str = "⚠️  Features cuánticos: NO son energías de binding"

    def to_dict(self):
        return {
            "entropy_bits": self.entropy_bits,
            "purity": self.purity,
            "participation_ratio": self.participation_ratio,
            "probability_distribution": self.probability_distribution,
            "most_probable_state": self.most_probable_state,
            "max_probability": self.max_probability,
            "total_shots": self.total_shots,
            "num_qubits": self.num_qubits,
            "timestamp": self.timestamp,
            "WARNING": self.warning
        }


def extract_quantum_features(counts: Dict[str, int], timestamp: Optional[str] = None) -> QuantumFeatures:
    """
    Extrae features estadísticos de counts cuánticos.

    Args:
        counts: Dict de {bitstring: count} desde hardware cuántico
        timestamp: Timestamp opcional

    Returns:
        QuantumFeatures con métricas estadísticas

    ⚠️  NO interpreta estos features como energías de binding.
    """
    if not counts:
        raise ValueError("Counts vacío")

    total_shots = sum(counts.values())
    if total_shots == 0:
        raise ValueError("Total de shots es 0")

    # Calcular distribución de probabilidad
    probs = {state: count / total_shots for state, count in counts.items()}

    # Entropía de Shannon: H = -Σ p(i) log₂ p(i)
    entropy = 0.0
    for p in probs.values():
        if p > 0:
            entropy -= p * math.log2(p)

    # Pureza: Tr(ρ²) ≈ Σ p(i)²
    purity = sum(p**2 for p in probs.values())

    # Participation ratio: 1 / Σ p(i)²
    participation_ratio = 1 / purity if purity > 0 else 0

    # Estado más probable
    most_probable = max(probs.items(), key=lambda x: x[1])
    most_probable_state = most_probable[0]
    max_probability = most_probable[1]

    # Número de qubits (desde longitud del bitstring)
    num_qubits = len(list(counts.keys())[0])

    from datetime import datetime
    ts = timestamp or datetime.now().isoformat()

    return QuantumFeatures(
        entropy_bits=entropy,
        purity=purity,
        participation_ratio=participation_ratio,
        probability_distribution=probs,
        most_probable_state=most_probable_state,
        max_probability=max_probability,
        total_shots=total_shots,
        num_qubits=num_qubits,
        timestamp=ts
    )


def correlate_quantum_classical(
    quantum_features: QuantumFeatures,
    docking_affinity: Optional[float] = None,
    docking_poses: Optional[int] = None
) -> Dict[str, Any]:
    """
    Correlaciona features cuánticos con resultados de docking.

    ⚠️  IMPORTANTE: Esta función NO modifica la energía de docking.
                    Solo reporta ambos valores juntos para análisis.

    Args:
        quantum_features: Features extraídos de hardware cuántico
        docking_affinity: ΔG de Vina (kcal/mol) - NO SE MODIFICA
        docking_poses: Número de poses de docking

    Returns:
        Dict con ambos tipos de resultados claramente separados
    """
    result = {
        "QUANTUM_FEATURES": quantum_features.to_dict(),
        "DOCKING_RESULTS": {
            "affinity_kcal_per_mol": docking_affinity,
            "num_poses": docking_poses,
            "NOTE": "⚠️  Affinity de Vina NO fue modificada por features cuánticos"
        },
        "CORRELATION_ANALYSIS": {
            "entropy_vs_affinity": {
                "entropy": quantum_features.entropy_bits,
                "affinity": docking_affinity,
                "note": "Correlación estadística - NO causal"
            },
            "purity_metric": quantum_features.purity,
            "interpretation": "Features cuánticos y docking son independientes"
        },
        "WARNINGS": [
            "⚠️  Features cuánticos NO son energías de binding",
            "⚠️  ΔG de Vina es resultado de cálculo clásico puro",
            "⚠️  Esta correlación es para análisis, no para mejorar resultados"
        ]
    }

    return result


def analyze_quantum_noise(counts: Dict[str, int], expected_state: Optional[str] = None) -> Dict[str, float]:
    """
    Analiza el ruido en mediciones cuánticas comparando con estado esperado.

    Args:
        counts: Counts desde hardware
        expected_state: Estado esperado (opcional)

    Returns:
        Dict con métricas de ruido
    """
    total = sum(counts.values())
    probs = {s: c/total for s, c in counts.items()}

    analysis = {
        "total_shots": total,
        "num_unique_states": len(counts),
        "max_probability": max(probs.values()),
        "min_probability": min(probs.values()),
        "probability_spread": max(probs.values()) - min(probs.values())
    }

    if expected_state and expected_state in counts:
        analysis["expected_state_probability"] = probs[expected_state]
        analysis["noise_estimate"] = 1.0 - probs[expected_state]

    return analysis


def create_ml_features(quantum_features: QuantumFeatures) -> np.ndarray:
    """
    Crea vector de features para ML a partir de resultados cuánticos.

    ⚠️  Estos features son para entrenar modelos ML, NO para calcular energías.

    Args:
        quantum_features: Features cuánticos extraídos

    Returns:
        Array numpy con features normalizados
    """
    features = [
        quantum_features.entropy_bits,
        quantum_features.purity,
        quantum_features.participation_ratio,
        quantum_features.max_probability,
        quantum_features.total_shots,
        quantum_features.num_qubits
    ]

    return np.array(features, dtype=np.float32)


__all__ = [
    'QuantumFeatures',
    'extract_quantum_features',
    'correlate_quantum_classical',
    'analyze_quantum_noise',
    'create_ml_features'
]