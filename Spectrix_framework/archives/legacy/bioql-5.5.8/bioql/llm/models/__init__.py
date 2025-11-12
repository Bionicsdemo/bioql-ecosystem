"""
BioQL Foundational Model
=========================

MODELO FUNDACIONAL PROPIO especializado en programación cuántica con BioQL.

Arquitectura:
    - Base: Transformer (similar a GPT/Claude)
    - Especialización: Código cuántico + Bioinformática
    - Tamaño: 7B-13B parámetros (escalable)
    - Entrenamiento: Fine-tuning sobre modelos base (LLaMA, Mistral)

Capacidades:
    1. Generar código BioQL desde lenguaje natural
    2. Optimizar circuitos cuánticos
    3. Explicar algoritmos cuánticos
    4. Corregir errores de código
    5. Traducir entre frameworks (Qiskit, Cirq → BioQL)
    6. Inferencia en computadora cuántica real

Dataset de entrenamiento:
    - 100K+ ejemplos de código BioQL
    - Documentación de algoritmos cuánticos
    - Casos de uso en bioinformática
    - Errores comunes y correcciones
    - Optimizaciones de circuitos

Training Stack:
    - PyTorch / JAX para entrenamiento
    - HuggingFace Transformers para arquitectura
    - LoRA / QLoRA para fine-tuning eficiente
    - Weights & Biases para tracking
    - vLLM para inferencia rápida
"""

__version__ = "1.0.0-alpha"
__model_name__ = "BioQL-CodeGen-7B"

from typing import Optional

# Core model components
try:
    from .bioql_model import BioQLFoundationalModel, BioQLConfig, create_model
    from .training.trainer import BioQLTrainer, TrainingConfig, quick_train
    from .training.dataset import (
        BioQLDataset,
        BioQLDatasetGenerator,
        TrainingExample,
        create_training_dataset
    )
    from .inference import BioQLInference, GenerationConfig, quick_inference
    from .evaluation import BioQLEvaluator, quick_evaluate
    from .serving import BioQLServingAPI, serve_model
    _available = True
except ImportError as e:
    _available = False
    BioQLFoundationalModel = None
    BioQLConfig = None
    create_model = None
    BioQLTrainer = None
    TrainingConfig = None
    quick_train = None
    BioQLDataset = None
    BioQLDatasetGenerator = None
    TrainingExample = None
    create_training_dataset = None
    BioQLInference = None
    GenerationConfig = None
    quick_inference = None
    BioQLEvaluator = None
    quick_evaluate = None
    BioQLServingAPI = None
    serve_model = None
    _import_error = str(e)

__all__ = [
    "__version__",
    "__model_name__",
    "BioQLFoundationalModel",
    "BioQLConfig",
    "create_model",
    "BioQLTrainer",
    "TrainingConfig",
    "quick_train",
    "BioQLDataset",
    "BioQLDatasetGenerator",
    "TrainingExample",
    "create_training_dataset",
    "BioQLInference",
    "GenerationConfig",
    "quick_inference",
    "BioQLEvaluator",
    "quick_evaluate",
    "BioQLServingAPI",
    "serve_model",
]


def model_info() -> dict:
    """Get information about the BioQL foundational model."""
    return {
        "name": __model_name__,
        "version": __version__,
        "type": "Transformer (Decoder-only)",
        "specialization": "Quantum Computing + Bioinformatics",
        "base_architecture": "LLaMA-2 / Mistral compatible",
        "parameters": "7B-13B (scalable)",
        "training_method": "Fine-tuning with LoRA/QLoRA",
        "supported_tasks": [
            "Code generation (Natural Language → BioQL)",
            "Circuit optimization",
            "Error correction",
            "Code explanation",
            "Framework translation (Qiskit/Cirq → BioQL)",
            "Quantum inference"
        ],
        "available": _available,
        "error": None if _available else _import_error
    }


def get_model(
    model_size: str = "7B",
    device: str = "auto",
    quantization: Optional[str] = None
) -> Optional[object]:
    """
    Load BioQL foundational model.

    Args:
        model_size: Model size ("7B", "13B")
        device: Device to load on ("auto", "cuda", "cpu")
        quantization: Quantization method ("4bit", "8bit", None)

    Returns:
        BioQLFoundationalModel instance

    Example:
        >>> model = get_model(model_size="7B", quantization="4bit")
        >>> code = model.generate("Create a Bell state")
    """
    if not _available:
        raise ImportError(f"BioQL model not available: {_import_error}")

    if BioQLInference is None:
        raise ImportError("BioQLInference not available")

    inference = BioQLInference(
        model_size=model_size,
        device=device,
        quantization=quantization
    )

    return inference.load_model()
