#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Abstract Backend Base Class
===========================

Defines interface for all quantum backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class BackendResult:
    """Results from backend execution."""

    syndromes: np.ndarray
    observables: np.ndarray
    metadata: Dict[str, Any]
    backend_name: str

    @property
    def num_shots(self) -> int:
        return self.syndromes.shape[0]


class AbstractBackend(ABC):
    """
    Abstract base class for quantum backends.

    All backends must implement execute() method.
    """

    def __init__(self, name: str = "AbstractBackend"):
        """Initialize backend."""
        self.name = name

    @abstractmethod
    def execute(self, circuit: Any, shots: int = 1024, **kwargs) -> BackendResult:
        """
        Execute circuit on backend.

        Args:
            circuit: Quantum circuit (format depends on backend)
            shots: Number of shots
            **kwargs: Backend-specific options

        Returns:
            BackendResult with syndromes and observables
        """
        pass
