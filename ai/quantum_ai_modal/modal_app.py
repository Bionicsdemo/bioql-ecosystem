# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

from __future__ import annotations

import json
import math
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import modal

sys.path.append("/root")

import backends  # noqa: E402

DEFAULT_BASE_MODEL = os.environ.get("BASE_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
DATASET_PATH = Path("/root/data/instruction_dataset.jsonl")
CHECKPOINT_DIR = Path("/checkpoints/instruction_model")
METRICS_PATH = CHECKPOINT_DIR / "metrics.json"
PROMPT_SPLITTER = "### Response:"


def _secret_from_env(var: str) -> Optional[modal.Secret]:
    value = os.environ.get(var)
    if not value:
        return None
    return modal.Secret.from_dict({var: value})


_secrets: List[modal.Secret] = [
    s
    for s in (
        _secret_from_env("BIOQL_API_KEY"),
        _secret_from_env("IBM_QUANTUM_API_KEY"),
        _secret_from_env("QPHAROS_API_KEY"),
    )
    if s
]

checkpoint_volume = modal.Volume.from_name("quantum-ai-checkpoints", create_if_missing=True)

data_mount = modal.Mount.from_local_dir("data", remote_path="/root/data")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.3.0",
        "fastapi[standard]>=0.111.0",
        "numpy>=1.26.0",
        "qiskit>=1.1.0",
        "qiskit-ibm-runtime>=0.25.0",
        "qiskit-aer>=0.14.0",
        "bioql>=5.3",
        "quillow==1.0.0",
        "qpharos==1.1.0",
        "transformers>=4.41.1",
        "datasets>=2.19.1",
        "accelerate>=0.31.0",
        "peft>=0.11.1",
        "bitsandbytes>=0.43.1",
        "sentencepiece>=0.2.0",
        "httpx>=0.27.0",
    )
    .add_local_file("backends.py", remote_path="/root/backends.py")
)

app = modal.App("quantum_ai_modal", image=image)

MODEL_CACHE: Dict[str, Tuple[Any, Any, str, bool]] = {}


def _ensure_checkpoint_dir() -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def _format_prompt(instruction: str, input_text: Optional[str] = None) -> str:
    instruction = instruction.strip()
    if input_text:
        return (
            f"### Instruction:\n{instruction}\n\n"
            f"### Input:\n{input_text.strip()}\n\n"
            "### Response:\n"
        )
    return f"### Instruction:\n{instruction}\n\n### Response:\n"


def _format_training_example(example: Dict[str, Any]) -> str:
    return _format_prompt(example["instruction"], example.get("input")) + example["output"].strip()


def _checkpoint_exists() -> bool:
    return (CHECKPOINT_DIR / "config.json").exists()


def _model_source() -> Tuple[str, bool]:
    if _checkpoint_exists():
        return str(CHECKPOINT_DIR), True
    return DEFAULT_BASE_MODEL, False


@lru_cache(maxsize=2)
def _load_tokenizer(source: str) -> Any:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(source, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return tokenizer


def _load_model_for_inference() -> Tuple[Any, Any, str, bool]:
    import torch
    from transformers import AutoModelForCausalLM

    source, is_finetuned = _model_source()
    cache_key = "finetuned" if is_finetuned else source
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(source, torch_dtype=dtype)
    if torch.cuda.is_available():
        model.to("cuda")
    model.eval()
    tokenizer = _load_tokenizer(source)
    MODEL_CACHE[cache_key] = (model, tokenizer, source, is_finetuned)
    return MODEL_CACHE[cache_key]


def _reset_model_cache() -> None:
    MODEL_CACHE.clear()
    _load_tokenizer.cache_clear()


def _load_instruction_dataset() -> List[Dict[str, Any]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Expected dataset at {DATASET_PATH}, but the file is missing.")
    with DATASET_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _tokenize_dataset(
    examples: List[Dict[str, Any]],
    tokenizer: Any,
    max_seq_length: int,
) -> Tuple[Any, Optional[Any]]:
    from datasets import Dataset

    dataset = Dataset.from_list(examples)
    if len(dataset) > 4:
        split = dataset.train_test_split(test_size=max(1, len(dataset) // 5), seed=42, shuffle=True)
        train_ds = split["train"]
        eval_ds = split["test"]
    else:
        train_ds = dataset
        eval_ds = None

    def tokenize(batch: Dict[str, Any]) -> Dict[str, Any]:
        text = _format_training_example(batch)
        tokens = tokenizer(
            text,
            truncation=True,
            max_length=max_seq_length,
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    train_tokenized = train_ds.map(tokenize, remove_columns=train_ds.column_names)
    eval_tokenized = eval_ds.map(tokenize, remove_columns=eval_ds.column_names) if eval_ds else None
    return train_tokenized, eval_tokenized


def _save_metrics(metrics: Dict[str, Any]) -> None:
    _ensure_checkpoint_dir()
    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)


def _generate_reply(
    instruction: str,
    input_payload: Optional[str],
    max_new_tokens: int = 256,
    temperature: float = 0.2,
    top_p: float = 0.9,
) -> Dict[str, Any]:
    import torch

    model, tokenizer, source, is_finetuned = _load_model_for_inference()
    prompt = _format_prompt(instruction, input_payload)
    encoded = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=tokenizer.model_max_length,
    )
    encoded = {k: v.to(model.device) for k, v in encoded.items()}
    with torch.no_grad():
        generated = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tokenizer.eos_token_id,
        )
    full_text = tokenizer.decode(generated[0], skip_special_tokens=True)
    if PROMPT_SPLITTER in full_text:
        response_text = full_text.split(PROMPT_SPLITTER, 1)[1].strip()
    else:
        response_text = full_text[len(prompt) :].strip()
    return {
        "prompt": prompt,
        "response": response_text,
        "raw": full_text,
        "model_source": source,
        "fine_tuned": is_finetuned,
    }


def _normalize_input_payload(input_payload: Optional[Any]) -> Optional[str]:
    if input_payload is None:
        return None
    if isinstance(input_payload, str):
        return input_payload
    return json.dumps(input_payload, indent=2, sort_keys=True)


def _execute_action_plan(plan_text: str) -> Dict[str, Any]:
    try:
        plan = json.loads(plan_text)
    except json.JSONDecodeError:
        return {"status": "plain_text", "output": plan_text}
    return {"status": "executed", "result": _dispatch_plan(plan)}


def _dispatch_plan(payload: Any) -> Any:
    if isinstance(payload, list):
        return [_dispatch_plan(item) for item in payload]
    if isinstance(payload, dict):
        if "steps" in payload and isinstance(payload["steps"], list):
            return [_dispatch_plan(step) for step in payload["steps"]]
        action = payload.get("action")
        if not action:
            return {"unhandled": payload}
        args = {k: v for k, v in payload.items() if k != "action"}
        return _dispatch_action(action, args)
    return {"unhandled": payload}


def _dispatch_action(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if action == "qiskit.run_bell":
            backend = args.get("backend", "aer_sampler")
            shots = args.get("shots", 2048)
            if backend == "ibm":
                backend_name = args.get("backend_name") or args.get("name") or "ibm_brisbane"
                return {
                    "action": action,
                    "backend": backend_name,
                    "result": backends.run_qiskit_ibm(backend_name),
                    "shots": shots,
                }
            return {
                "action": action,
                "backend": backend,
                "result": backends.run_qiskit_local(),
                "shots": shots,
            }
        if action == "bioql.configure_backend":
            return backends.bioql_configure_backend(
                backend=args.get("backend"),
                shots=args.get("shots"),
                post_check=args.get("post_check"),
            )
        if action == "bioql.status.readiness":
            return backends.bioql_status_readiness()
        if action == "bioql.log_event":
            return backends.bioql_log_event(event=args.get("event"), metadata=args.get("metadata"))
        if action == "bioql.set_mode":
            return backends.bioql_set_mode(args.get("mode"))
        if action == "bioql.execute_program":
            return backends.bioql_execute_program(
                program=args.get("program"),
                backend=args.get("backend"),
                shots=args.get("shots"),
                api_key=args.get("api_key"),
                extra_payload=args.get("extra_payload"),
            )
        if action == "qpharos.list_calibrations":
            return backends.qpharos_list_calibrations(
                filters=args.get("filters"), response_mode=args.get("response_mode")
            )
        if action == "qpharos.update_job":
            return backends.qpharos_update_job(
                job_id=args.get("job_id"),
                backend=args.get("backend"),
                note=args.get("note"),
            )
        if action == "qpharos.execute_calibration":
            return backends.qpharos_execute_calibration(args.get("script"))
        if action == "quillow.estimate_error":
            return backends.quillow_estimate_error(
                distance=args.get("distance"),
                p_error=args.get("p_error"),
                rounds=args.get("rounds"),
            )
        if action == "quillow.benchmark_decoder":
            return backends.quillow_benchmark_decoder(args.get("shots"))
        if action == "notify":
            return backends.send_notification(
                channel=args.get("channel"), condition=args.get("condition")
            )
    except Exception as exc:
        return {"action": action, "error": str(exc), "payload": args}
    return {"action": action, "note": "No handler implemented", "payload": args}


@app.function(
    gpu="A10G",
    timeout=3600,
    secrets=_secrets,
    volumes={"/checkpoints": checkpoint_volume},
    mounts=[data_mount],
)
def train_model(
    base_model_name: str = DEFAULT_BASE_MODEL,
    num_train_epochs: int = 4,
    learning_rate: float = 5e-5,
    per_device_batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    max_seq_length: int = 768,
) -> Dict[str, Any]:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    dataset = _load_instruction_dataset()
    tokenizer = _load_tokenizer(base_model_name)
    train_ds, eval_ds = _tokenize_dataset(dataset, tokenizer, max_seq_length)

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=dtype,
    )

    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR),
        overwrite_output_dir=True,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        fp16=torch.cuda.is_available(),
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        evaluation_strategy="epoch" if eval_ds is not None else "no",
        save_strategy="epoch",
        save_total_limit=1,
        weight_decay=0.01,
        warmup_steps=10,
        logging_steps=5,
        report_to=[],
    )

    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
    )

    train_metrics = trainer.train()
    eval_metrics: Dict[str, Any] = {}
    if eval_ds is not None:
        eval_metrics = trainer.evaluate()

    trainer.save_model(str(CHECKPOINT_DIR))
    tokenizer.save_pretrained(str(CHECKPOINT_DIR))
    _reset_model_cache()

    eval_perplexity = None
    if eval_metrics.get("eval_loss") is not None:
        loss = eval_metrics["eval_loss"]
        if loss < 20:
            eval_perplexity = math.exp(loss)

    metrics = {
        "base_model": base_model_name,
        "num_examples": len(dataset),
        "train_epochs": num_train_epochs,
        "train_loss": train_metrics.training_loss,
        "train_runtime": train_metrics.metrics.get("train_runtime"),
        "eval_loss": eval_metrics.get("eval_loss"),
        "eval_perplexity": eval_perplexity,
        "checkpoint_dir": str(CHECKPOINT_DIR),
    }
    _save_metrics(metrics)
    return metrics


@app.function(
    timeout=600,
    secrets=_secrets,
    volumes={"/checkpoints": checkpoint_volume},
    mounts=[data_mount],
)
def assistant_reply(
    instruction: str,
    input_payload: Optional[Dict[str, Any]] = None,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
    top_p: float = 0.9,
) -> Dict[str, Any]:
    return _generate_reply(
        instruction=instruction,
        input_payload=_normalize_input_payload(input_payload),
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )


@app.function(
    timeout=600,
    secrets=_secrets,
    volumes={"/checkpoints": checkpoint_volume},
    mounts=[data_mount],
)
def assistant_orchestrator(
    instruction: str,
    input_payload: Optional[Dict[str, Any]] = None,
    execute_tools: bool = True,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
    top_p: float = 0.9,
) -> Dict[str, Any]:
    generation = _generate_reply(
        instruction=instruction,
        input_payload=_normalize_input_payload(input_payload),
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    tool_result = None
    if execute_tools:
        tool_result = _execute_action_plan(generation["response"])

    return {"generation": generation, "tool_result": tool_result}


@app.function(timeout=600, secrets=_secrets)
def qiskit_hello_world(backend: str = "local", ibm_backend: Optional[str] = None):
    if backend == "local":
        result = backends.run_qiskit_local()
    elif backend == "ibm":
        name = ibm_backend or "ibm_brisbane"
        result = backends.run_qiskit_ibm(name)
    else:
        result = {"error": f"Unknown backend '{backend}'"}
    return result


@app.function(timeout=600, secrets=_secrets)
def quillow_demo():
    return backends.quillow_demo()


@app.function(timeout=600, secrets=_secrets)
def bioql_demo():
    return backends.bioql_demo()


@app.function(timeout=600, secrets=_secrets)
def qpharos_demo():
    return backends.qpharos_demo()


@app.local_entrypoint()
def main(
    instruction: str = "Set BioQL to IBM Toronto backend and prepare 4k-shot run.",
    run_training: bool = False,
):
    if run_training:
        train_metrics = train_model.remote()
        print("\n[train_model]")
        print(json.dumps(train_metrics, indent=2))

    print("\n[assistant_orchestrator]")
    orchestration = assistant_orchestrator.remote(
        instruction=instruction,
        execute_tools=True,
    )
    print(json.dumps(orchestration, indent=2))


@app.function(
    timeout=600,
    secrets=_secrets,
    volumes={"/checkpoints": checkpoint_volume},
    mounts=[data_mount],
)
@modal.fastapi_endpoint()
def predict_endpoint():
    from fastapi import Body, FastAPI, HTTPException

    api = FastAPI()

    @api.get("/")
    async def health():
        source, trained = _model_source()
        return {
            "status": "ok",
            "model_source": source,
            "fine_tuned": trained,
            "dataset_available": DATASET_PATH.exists(),
            "checkpoint_exists": _checkpoint_exists(),
        }

    @api.post("/")
    async def generate(
        payload: Dict[str, Any] = Body(default={"instruction": "Describe the Spectrix toolchain."}),
    ):
        instruction = payload.get("instruction")
        if not instruction:
            raise HTTPException(status_code=400, detail="Missing 'instruction'.")
        input_payload = payload.get("input")
        execute_tools = payload.get("execute_tools", False)
        generation = _generate_reply(
            instruction=instruction,
            input_payload=_normalize_input_payload(input_payload),
            max_new_tokens=payload.get("max_new_tokens", 256),
            temperature=payload.get("temperature", 0.2),
            top_p=payload.get("top_p", 0.9),
        )
        tool_result = None
        if execute_tools:
            tool_result = _execute_action_plan(generation["response"])
        return {"generation": generation, "tool_result": tool_result}

    return api
