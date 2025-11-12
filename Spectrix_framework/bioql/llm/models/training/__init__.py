# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Model Training Infrastructure
====================================

Training pipeline for BioQL foundational model.
"""

try:
    from .dataset import (
        BioQLDataset,
        BioQLDatasetGenerator,
        TaskType,
        TrainingExample,
        create_training_dataset,
    )
    from .trainer import BioQLTrainer, TrainingConfig

    _available = True
except ImportError:
    _available = False
    BioQLDatasetGenerator = None
    BioQLDataset = None
    TrainingExample = None
    TaskType = None
    create_training_dataset = None
    BioQLTrainer = None
    TrainingConfig = None

__all__ = [
    "BioQLDatasetGenerator",
    "BioQLDataset",
    "TrainingExample",
    "TaskType",
    "create_training_dataset",
    "BioQLTrainer",
    "TrainingConfig",
]
