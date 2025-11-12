"""
BioQL Model Inference Engine
=============================

Fast inference for BioQL foundational model.

Features:
- vLLM integration for high-throughput inference
- Quantization support (4-bit, 8-bit)
- Batch processing
- Streaming generation
- Multiple backend support (local, API)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Iterator
from pathlib import Path
import json

# Optional dependencies
try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TextStreamer
    )
    _transformers_available = True
except ImportError:
    _transformers_available = False

try:
    from peft import PeftModel
    _peft_available = True
except ImportError:
    _peft_available = False

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """
    Configuration for code generation.

    Example:
        >>> config = GenerationConfig(
        ...     max_length=512,
        ...     temperature=0.7,
        ...     top_p=0.9
        ... )
    """
    max_length: int = 512
    max_new_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    num_return_sequences: int = 1
    early_stopping: bool = True


@dataclass
class InferenceResult:
    """Result from inference."""
    generated_code: str
    prompt: str
    metadata: Dict[str, Any]


if _transformers_available:
    class BioQLInference:
        """
        Inference engine for BioQL foundational model.

        Supports:
        - Local inference
        - Quantization (4-bit, 8-bit)
        - Batch processing
        - Streaming

        Example:
            >>> # Load model
            >>> inference = BioQLInference(
            ...     model_path="./bioql-7b-finetuned",
            ...     quantization="4bit"
            ... )
            >>>
            >>> # Generate code
            >>> result = inference.generate("Create a Bell state")
            >>> print(result.generated_code)
        """

        def __init__(
            self,
            model_path: Optional[str] = None,
            model_name: Optional[str] = None,
            quantization: Optional[str] = None,  # "4bit", "8bit", None
            device: str = "auto",
            use_vllm: bool = False
        ):
            """
            Initialize inference engine.

            Args:
                model_path: Path to fine-tuned model (LoRA adapters)
                model_name: Base model name if model_path is LoRA
                quantization: Quantization method
                device: Device to use
                use_vllm: Use vLLM for fast inference
            """
            self.model_path = model_path
            self.model_name = model_name
            self.quantization = quantization
            self.device = device
            self.use_vllm = use_vllm

            self.model = None
            self.tokenizer = None

            logger.info("BioQLInference initialized")

        def load_model(self):
            """Load model and tokenizer."""
            logger.info("Loading model...")

            if self.use_vllm:
                self._load_vllm()
            else:
                self._load_transformers()

            logger.info("✅ Model loaded")

        def _load_transformers(self):
            """Load model with HuggingFace Transformers."""
            # Quantization config
            quantization_config = None
            if self.quantization == "4bit":
                logger.info("Using 4-bit quantization")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True
                )
            elif self.quantization == "8bit":
                logger.info("Using 8-bit quantization")
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)

            # Load tokenizer
            tokenizer_path = self.model_path or self.model_name
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
            self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load model
            if self.model_path and _peft_available:
                # Load base + LoRA adapters
                logger.info(f"Loading base model: {self.model_name}")
                base_model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map=self.device if self.device != "auto" else "auto",
                    trust_remote_code=True
                )

                logger.info(f"Loading LoRA adapters: {self.model_path}")
                self.model = PeftModel.from_pretrained(base_model, self.model_path)
            else:
                # Load full model
                model_path = self.model_path or self.model_name
                logger.info(f"Loading model: {model_path}")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    quantization_config=quantization_config,
                    device_map=self.device if self.device != "auto" else "auto",
                    trust_remote_code=True
                )

            self.model.eval()

        def _load_vllm(self):
            """Load model with vLLM for fast inference."""
            try:
                from vllm import LLM, SamplingParams
                self.vllm = LLM
                self.sampling_params_cls = SamplingParams

                model_path = self.model_path or self.model_name
                logger.info(f"Loading model with vLLM: {model_path}")

                self.model = self.vllm(
                    model=model_path,
                    quantization=self.quantization,
                    dtype="float16"
                )

                logger.info("✅ vLLM model loaded")
            except ImportError:
                logger.error("vLLM not available, falling back to transformers")
                self.use_vllm = False
                self._load_transformers()

        def generate(
            self,
            prompt: str,
            config: Optional[GenerationConfig] = None,
            stream: bool = False
        ) -> InferenceResult:
            """
            Generate BioQL code from prompt.

            Args:
                prompt: Natural language description
                config: Generation configuration
                stream: Stream output

            Returns:
                InferenceResult with generated code

            Example:
                >>> inference = BioQLInference(model_path="./bioql-7b")
                >>> result = inference.generate("Create a Bell state")
                >>> print(result.generated_code)
            """
            if self.model is None:
                self.load_model()

            if config is None:
                config = GenerationConfig()

            logger.info(f"Generating code for: {prompt}")

            if self.use_vllm:
                generated = self._generate_vllm(prompt, config)
            else:
                generated = self._generate_transformers(prompt, config, stream)

            result = InferenceResult(
                generated_code=generated,
                prompt=prompt,
                metadata={
                    "quantization": self.quantization,
                    "model": self.model_path or self.model_name,
                    "config": config.__dict__
                }
            )

            return result

        def _generate_transformers(
            self,
            prompt: str,
            config: GenerationConfig,
            stream: bool = False
        ) -> str:
            """Generate with HuggingFace Transformers."""
            # Format prompt
            formatted_prompt = f"""Generate BioQL code for the following task:

Task: {prompt}

Code:
"""

            # Tokenize
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                padding=True
            ).to(self.model.device)

            # Generate
            with torch.no_grad():
                if stream:
                    # Streaming generation
                    streamer = TextStreamer(
                        self.tokenizer,
                        skip_prompt=True,
                        skip_special_tokens=True
                    )

                    outputs = self.model.generate(
                        **inputs,
                        max_length=config.max_length,
                        max_new_tokens=config.max_new_tokens,
                        temperature=config.temperature,
                        top_p=config.top_p,
                        top_k=config.top_k,
                        repetition_penalty=config.repetition_penalty,
                        do_sample=config.do_sample,
                        num_return_sequences=config.num_return_sequences,
                        early_stopping=config.early_stopping,
                        streamer=streamer,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                else:
                    # Regular generation
                    outputs = self.model.generate(
                        **inputs,
                        max_length=config.max_length,
                        max_new_tokens=config.max_new_tokens,
                        temperature=config.temperature,
                        top_p=config.top_p,
                        top_k=config.top_k,
                        repetition_penalty=config.repetition_penalty,
                        do_sample=config.do_sample,
                        num_return_sequences=config.num_return_sequences,
                        early_stopping=config.early_stopping,
                        pad_token_id=self.tokenizer.eos_token_id
                    )

            # Decode
            generated = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )

            # Extract code (remove prompt)
            if "Code:" in generated:
                generated = generated.split("Code:")[-1].strip()

            return generated

        def _generate_vllm(self, prompt: str, config: GenerationConfig) -> str:
            """Generate with vLLM."""
            # Format prompt
            formatted_prompt = f"""Generate BioQL code for the following task:

Task: {prompt}

Code:
"""

            # Sampling params
            sampling_params = self.sampling_params_cls(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_tokens=config.max_new_tokens or 512,
                repetition_penalty=config.repetition_penalty
            )

            # Generate
            outputs = self.model.generate([formatted_prompt], sampling_params)

            # Extract text
            generated = outputs[0].outputs[0].text

            return generated.strip()

        def batch_generate(
            self,
            prompts: List[str],
            config: Optional[GenerationConfig] = None
        ) -> List[InferenceResult]:
            """
            Generate code for multiple prompts.

            Args:
                prompts: List of prompts
                config: Generation configuration

            Returns:
                List of InferenceResults

            Example:
                >>> prompts = [
                ...     "Create a Bell state",
                ...     "Run QFT on 4 qubits",
                ...     "Simulate protein folding"
                ... ]
                >>> results = inference.batch_generate(prompts)
            """
            logger.info(f"Batch generating for {len(prompts)} prompts")

            results = []
            for prompt in prompts:
                result = self.generate(prompt, config)
                results.append(result)

            return results

        def generate_stream(
            self,
            prompt: str,
            config: Optional[GenerationConfig] = None
        ) -> Iterator[str]:
            """
            Stream generated code.

            Args:
                prompt: Natural language prompt
                config: Generation configuration

            Yields:
                Generated text chunks

            Example:
                >>> for chunk in inference.generate_stream("Create a Bell state"):
                ...     print(chunk, end="", flush=True)
            """
            # Not implemented yet - placeholder
            result = self.generate(prompt, config)
            yield result.generated_code

else:
    # Stub when transformers not available
    class BioQLInference:
        def __init__(self, *args, **kwargs):
            raise ImportError("transformers required for inference")


def quick_inference(
    prompt: str,
    model_path: str,
    model_name: Optional[str] = None,
    quantization: Optional[str] = None,
    **kwargs
) -> str:
    """
    Quick inference helper.

    Args:
        prompt: Natural language prompt
        model_path: Path to model
        model_name: Base model name
        quantization: Quantization method
        **kwargs: Additional generation config

    Returns:
        Generated code

    Example:
        >>> code = quick_inference(
        ...     "Create a Bell state",
        ...     model_path="./bioql-7b-finetuned",
        ...     model_name="meta-llama/Llama-2-7b-hf",
        ...     quantization="4bit"
        ... )
        >>> print(code)
    """
    if not _transformers_available:
        raise ImportError("transformers required")

    # Create inference engine
    inference = BioQLInference(
        model_path=model_path,
        model_name=model_name,
        quantization=quantization
    )

    # Generate
    config = GenerationConfig(**kwargs)
    result = inference.generate(prompt, config)

    return result.generated_code
