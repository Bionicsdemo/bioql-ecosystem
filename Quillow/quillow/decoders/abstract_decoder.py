#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Abstract Decoder Base Class
===========================

Defines interface for all syndrome decoders.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import stim


@dataclass
class DecoderResult:
    """Results from decoding operation."""

    predicted_observables: np.ndarray
    decode_time_seconds: float
    num_shots: int
    decoder_name: str

    @property
    def throughput(self) -> float:
        """Shots decoded per second."""
        return self.num_shots / self.decode_time_seconds if self.decode_time_seconds > 0 else 0

    @property
    def avg_latency_us(self) -> float:
        """Average latency per shot in microseconds."""
        return (self.decode_time_seconds / self.num_shots) * 1e6 if self.num_shots > 0 else 0


class AbstractDecoder(ABC):
    """
    Abstract base class for syndrome decoders.

    All decoders must implement:
    - decode_single(): Decode one syndrome
    - decode_batch(): Decode multiple syndromes (vectorized)
    """

    def __init__(self, name: str = "AbstractDecoder"):
        """Initialize decoder."""
        self.name = name
        self.decode_count = 0
        self.total_decode_time = 0.0

    @abstractmethod
    def decode_single(
        self, syndrome: np.ndarray, dem: Optional[stim.DetectorErrorModel] = None
    ) -> int:
        """
        Decode a single syndrome.

        Args:
            syndrome: Binary syndrome vector
            dem: Detector error model (optional)

        Returns:
            Predicted logical observable (0 or 1)
        """
        pass

    @abstractmethod
    def decode_batch(
        self, syndromes: np.ndarray, circuit: Optional[stim.Circuit] = None
    ) -> np.ndarray:
        """
        Decode multiple syndromes in batch.

        Args:
            syndromes: Array of syndromes (shots × detectors)
            circuit: Stim circuit (for extracting DEM)

        Returns:
            Array of predicted observables (shots,)
        """
        pass

    def get_statistics(self) -> Dict:
        """Get decoder performance statistics."""
        return {
            "name": self.name,
            "decode_count": self.decode_count,
            "total_time": self.total_decode_time,
            "avg_time_per_shot": (
                self.total_decode_time / self.decode_count if self.decode_count > 0 else 0
            ),
            "throughput": (
                self.decode_count / self.total_decode_time if self.total_decode_time > 0 else 0
            ),
        }

    def reset_statistics(self):
        """Reset performance counters."""
        self.decode_count = 0
        self.total_decode_time = 0.0
