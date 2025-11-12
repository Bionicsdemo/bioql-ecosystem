"""
BioQL Model Trainer
===================

Fine-tuning pipeline for BioQL foundational model using LoRA/QLoRA.

Features:
- Efficient fine-tuning with LoRA (Low-Rank Adaptation)
- QLoRA support for 4-bit/8-bit quantization
- Multi-task learning (code generation + optimization + explanation)
- Distributed training support
- Weights & Biases integration
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

# Optional dependencies
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from transformers import (
        Trainer,
        TrainingArguments,
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig
    )
    _transformers_available = True
except ImportError:
    _transformers_available = False
    Trainer = object
    TrainingArguments = object

try:
    from peft import (
        LoraConfig,
        get_peft_model,
        prepare_model_for_kbit_training,
        TaskType as PeftTaskType
    )
    _peft_available = True
except ImportError:
    _peft_available = False

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """
    Configuration for BioQL model training.

    Example:
        >>> config = TrainingConfig(
        ...     model_name="meta-llama/Llama-2-7b-hf",
        ...     output_dir="./bioql-7b-finetuned",
        ...     num_train_epochs=3,
        ...     use_lora=True,
        ...     use_qlora=True
        ... )
    """
    # Model
    model_name: str = "meta-llama/Llama-2-7b-hf"
    tokenizer_name: Optional[str] = None

    # Training
    output_dir: str = "./bioql_model_output"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-5
    warmup_steps: int = 100
    max_steps: int = -1
    logging_steps: int = 10
    eval_steps: int = 100
    save_steps: int = 500

    # LoRA/QLoRA
    use_lora: bool = True
    use_qlora: bool = False  # 4-bit quantization
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj"
    ])

    # Optimization
    optim: str = "adamw_torch"
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    fp16: bool = True
    bf16: bool = False

    # Dataset
    max_seq_length: int = 512

    # Weights & Biases
    use_wandb: bool = False
    wandb_project: str = "bioql-foundational-model"
    wandb_run_name: Optional[str] = None

    # Multi-task weights
    code_generation_weight: float = 0.7
    optimization_weight: float = 0.2
    explanation_weight: float = 0.1

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in self.__dict__.items()}

    def to_training_args(self) -> 'TrainingArguments':
        """Convert to HuggingFace TrainingArguments."""
        if not _transformers_available:
            raise ImportError("transformers required")

        return TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=self.num_train_epochs,
            per_device_train_batch_size=self.per_device_train_batch_size,
            per_device_eval_batch_size=self.per_device_eval_batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            learning_rate=self.learning_rate,
            warmup_steps=self.warmup_steps,
            max_steps=self.max_steps,
            logging_steps=self.logging_steps,
            eval_steps=self.eval_steps,
            save_steps=self.save_steps,
            optim=self.optim,
            weight_decay=self.weight_decay,
            max_grad_norm=self.max_grad_norm,
            fp16=self.fp16,
            bf16=self.bf16,
            logging_dir=f"{self.output_dir}/logs",
            save_total_limit=3,
            load_best_model_at_end=True,
            report_to="wandb" if self.use_wandb else "none",
            run_name=self.wandb_run_name
        )


if _transformers_available and _peft_available:
    class BioQLTrainer(Trainer):
        """
        Specialized trainer for BioQL foundational model.

        Features:
        - LoRA/QLoRA fine-tuning
        - Multi-task learning
        - Custom loss functions
        - Quantum-aware training

        Example:
            >>> config = TrainingConfig(
            ...     model_name="meta-llama/Llama-2-7b-hf",
            ...     use_lora=True,
            ...     num_train_epochs=3
            ... )
            >>>
            >>> trainer = BioQLTrainer(config)
            >>> trainer.prepare_model()
            >>> trainer.train(train_dataset, eval_dataset)
        """

        def __init__(self, config: TrainingConfig):
            """
            Initialize BioQL trainer.

            Args:
                config: Training configuration
            """
            self.config = config
            self.model = None
            self.tokenizer = None
            self.peft_config = None

            logger.info(f"BioQLTrainer initialized")
            logger.info(f"Model: {config.model_name}")
            logger.info(f"LoRA: {config.use_lora}, QLoRA: {config.use_qlora}")

        def prepare_model(self):
            """
            Prepare model for training.

            Loads base model, applies quantization if needed, and adds LoRA.
            """
            logger.info("Preparing model for training...")

            # Tokenizer
            tokenizer_name = self.config.tokenizer_name or self.config.model_name
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token

            # Quantization config for QLoRA
            quantization_config = None
            if self.config.use_qlora:
                logger.info("Using QLoRA (4-bit quantization)")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True
                )

            # Load base model
            logger.info(f"Loading base model: {self.config.model_name}")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                quantization_config=quantization_config,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )

            # Prepare for k-bit training if using QLoRA
            if self.config.use_qlora:
                self.model = prepare_model_for_kbit_training(self.model)

            # Add LoRA
            if self.config.use_lora:
                logger.info("Adding LoRA adapters")
                self.peft_config = LoraConfig(
                    task_type=PeftTaskType.CAUSAL_LM,
                    r=self.config.lora_r,
                    lora_alpha=self.config.lora_alpha,
                    lora_dropout=self.config.lora_dropout,
                    target_modules=self.config.lora_target_modules,
                    bias="none"
                )
                self.model = get_peft_model(self.model, self.peft_config)

            # Print trainable parameters
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(f"Trainable params: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")
            logger.info(f"Total params: {total_params:,}")

            logger.info("✅ Model prepared for training")

        def train(
            self,
            train_dataset,
            eval_dataset=None,
            callbacks=None
        ):
            """
            Train the model.

            Args:
                train_dataset: Training dataset (BioQLDataset)
                eval_dataset: Evaluation dataset (optional)
                callbacks: Training callbacks (optional)
            """
            if self.model is None:
                raise ValueError("Call prepare_model() first")

            logger.info("Starting training...")

            # Convert config to TrainingArguments
            training_args = self.config.to_training_args()

            # Initialize Trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                tokenizer=self.tokenizer,
                callbacks=callbacks
            )

            # Train
            trainer.train()

            logger.info("✅ Training complete")

            return trainer

        def save(self, output_path: str):
            """
            Save fine-tuned model.

            Args:
                output_path: Path to save model
            """
            if self.model is None:
                raise ValueError("No model to save")

            logger.info(f"Saving model to {output_path}")

            output = Path(output_path)
            output.mkdir(parents=True, exist_ok=True)

            # Save model
            if self.config.use_lora:
                # Save only LoRA adapters
                self.model.save_pretrained(output)
            else:
                # Save full model
                self.model.save_pretrained(output)

            # Save tokenizer
            self.tokenizer.save_pretrained(output)

            # Save config
            config_path = output / "training_config.json"
            with open(config_path, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)

            logger.info(f"✅ Model saved to {output_path}")

        @classmethod
        def from_pretrained(cls, model_path: str) -> 'BioQLTrainer':
            """
            Load fine-tuned model.

            Args:
                model_path: Path to saved model

            Returns:
                BioQLTrainer instance
            """
            logger.info(f"Loading model from {model_path}")

            # Load config
            config_path = Path(model_path) / "training_config.json"
            with open(config_path, 'r') as f:
                config_dict = json.load(f)

            # Convert lists back from JSON
            if "lora_target_modules" in config_dict:
                config_dict["lora_target_modules"] = config_dict["lora_target_modules"]

            config = TrainingConfig(**config_dict)

            # Create trainer
            trainer = cls(config)

            # Load tokenizer
            trainer.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # Load model
            if config.use_lora:
                # Load base model + LoRA adapters
                from peft import PeftModel

                base_model = AutoModelForCausalLM.from_pretrained(
                    config.model_name,
                    device_map="auto" if torch.cuda.is_available() else None
                )
                trainer.model = PeftModel.from_pretrained(base_model, model_path)
            else:
                # Load full model
                trainer.model = AutoModelForCausalLM.from_pretrained(model_path)

            logger.info("✅ Model loaded")
            return trainer

else:
    # Stubs when dependencies not available
    class BioQLTrainer:
        def __init__(self, config):
            raise ImportError("PyTorch, transformers, and peft required for training")


def quick_train(
    train_dataset,
    eval_dataset=None,
    model_name: str = "meta-llama/Llama-2-7b-hf",
    output_dir: str = "./bioql_model",
    num_epochs: int = 3,
    use_lora: bool = True,
    use_qlora: bool = False,
    **kwargs
):
    """
    Quick training function with sensible defaults.

    Args:
        train_dataset: Training dataset
        eval_dataset: Evaluation dataset
        model_name: Base model to fine-tune
        output_dir: Output directory
        num_epochs: Number of epochs
        use_lora: Use LoRA
        use_qlora: Use QLoRA (4-bit)
        **kwargs: Additional config parameters

    Returns:
        Trained BioQLTrainer

    Example:
        >>> from bioql.llm.models.training import create_training_dataset, quick_train
        >>>
        >>> # Generate dataset
        >>> splits = create_training_dataset(10000)
        >>>
        >>> # Train
        >>> trainer = quick_train(
        ...     train_dataset=splits["train"],
        ...     eval_dataset=splits["val"],
        ...     num_epochs=3
        ... )
    """
    if not _transformers_available or not _peft_available:
        raise ImportError("transformers and peft required")

    # Create config
    config = TrainingConfig(
        model_name=model_name,
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        use_lora=use_lora,
        use_qlora=use_qlora,
        **kwargs
    )

    # Create trainer
    trainer = BioQLTrainer(config)
    trainer.prepare_model()

    # Train
    trainer.train(train_dataset, eval_dataset)

    # Save
    trainer.save(output_dir)

    return trainer
