"""
BioQL Model Training Infrastructure
====================================

Training pipeline for BioQL foundational model.
"""

try:
    from .dataset import (
        BioQLDatasetGenerator,
        BioQLDataset,
        TrainingExample,
        TaskType,
        create_training_dataset
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
