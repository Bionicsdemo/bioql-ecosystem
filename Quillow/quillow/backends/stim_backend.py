#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Stim Backend
============

Fast stabilizer circuit simulator backend using Stim.

Stim is an ultra-fast stabilizer circuit simulator designed for
quantum error correction. It can simulate millions of shots per second.

Performance:
- 1-10M shots/second for surface codes
- Exact sampling (no approximation)
- Memory efficient (sparse representations)
"""

import time
from typing import Any, Dict, Optional

import numpy as np
import stim
from loguru import logger

from .abstract_backend import AbstractBackend, BackendResult


class StimBackend(AbstractBackend):
    """
    Stim simulator backend.

    Ultra-fast for stabilizer circuits and QEC codes.
    """

    def __init__(self):
        """Initialize Stim backend."""
        super().__init__(name="Stim")
        logger.info("Stim backend initialized")

    def execute(
        self, circuit: stim.Circuit, shots: int = 1024, separate_observables: bool = True, **kwargs
    ) -> BackendResult:
        """
        Execute circuit on Stim simulator.

        Args:
            circuit: Stim circuit
            shots: Number of shots
            separate_observables: Return observables separately
            **kwargs: Additional options

        Returns:
            BackendResult with syndromes and observables
        """
        logger.info(f"Executing circuit on Stim: {shots} shots")

        start = time.time()

        # Compile sampler
        sampler = circuit.compile_detector_sampler()

        # Sample
        if separate_observables:
            syndromes, observables = sampler.sample(shots=shots, separate_observables=True)
        else:
            combined = sampler.sample(shots=shots)
            # Split detectors and observables
            num_detectors = circuit.num_detectors
            syndromes = combined[:, :num_detectors]
            observables = combined[:, num_detectors:]

        runtime = time.time() - start

        logger.success(
            f"Stim execution complete: {shots} shots in {runtime:.3f}s "
            f"({shots/runtime:.1f} shots/sec)"
        )

        return BackendResult(
            syndromes=syndromes,
            observables=observables,
            metadata={
                "runtime": runtime,
                "throughput": shots / runtime,
                "num_detectors": circuit.num_detectors,
                "num_observables": circuit.num_observables,
                "num_measurements": circuit.num_measurements,
            },
            backend_name="Stim",
        )

    def compile_sampler(self, circuit: stim.Circuit):
        """Pre-compile sampler for repeated use."""
        return circuit.compile_detector_sampler()

    def sample_batch(self, sampler: Any, batch_sizes: list, **kwargs) -> list:
        """
        Sample multiple batches efficiently.

        Useful for streaming or progressive sampling.
        """
        results = []

        for batch_size in batch_sizes:
            syndromes, observables = sampler.sample(shots=batch_size, separate_observables=True)

            results.append(
                {"syndromes": syndromes, "observables": observables, "batch_size": batch_size}
            )

        return results


__all__ = ["StimBackend"]
