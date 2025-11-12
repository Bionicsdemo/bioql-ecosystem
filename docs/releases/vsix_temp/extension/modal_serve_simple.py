# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL VS Code Model Server - Modal Deployment (Simplified)
Sirve el modelo entrenado descargándolo desde Modal artifacts
"""
import modal
import os

# Create Modal app
app = modal.App("bioql-vscode")

# GPU image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "numpy==1.26.4",  # Fix: NumPy <2.0 required for bitsandbytes
        "scipy==1.11.4",  # Fix: scipy required for bitsandbytes
        "torch==2.1.0",
        "transformers==4.37.0",
        "peft==0.7.1",
        "accelerate==0.25.0",
        "bitsandbytes==0.41.3",
        "fastapi==0.108.0",
        "pydantic==2.5.0"
    )
)


@app.cls(
    image=image,
    gpu="A10G",  # GPU más pequeña y barata
    timeout=600,
    scaledown_window=300
)
class BioQLServer:
    """BioQL Code Generation Server"""

    @modal.enter()
    def load_model(self):
        """Load model on container startup"""
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        print("🔄 Loading model...")
        base_model = "Qwen/Qwen2.5-7B-Instruct"

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model,
            trust_remote_code=True
        )

        # Model with 8-bit quantization (more stable than 4-bit)
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
            load_in_8bit=True  # Changed from 4-bit to 8-bit for stability
        )

        self.model.eval()
        print("✅ Model loaded and ready!")

    @modal.method()
    def generate(self, prompt: str, max_length: int = 300, temperature: float = 0.7) -> dict:
        """Generate BioQL code from prompt"""
        import torch

        # Format prompt for BioQL code generation
        formatted_prompt = f"""You are a BioQL quantum programming expert. Generate clean, working BioQL Python code.

Task: {prompt}

Generate only the Python code using the bioql library:
```python
from bioql import quantum

"""

        # Tokenize
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.model.device)

        # Generate - use greedy decoding for stability with quantized base model
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_length,
                do_sample=False,  # Greedy decoding (most stable)
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract code - look for the generated part after the prompt
        if "```python" in generated:
            code = generated.split("```python")[-1].split("```")[0].strip()
        else:
            # Extract everything after the prompt
            code = generated[len(formatted_prompt):].strip()
            # Clean up
            if "```" in code:
                code = code.split("```")[0].strip()

        return {
            "code": code,
            "success": True
        }


@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    """FastAPI web endpoint"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    web_app = FastAPI(
        title="BioQL VS Code Server",
        description="AI-powered BioQL code generation for VS Code"
    )

    # Enable CORS for VS Code extension
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class GenerateRequest(BaseModel):
        prompt: str
        max_length: int = 300
        temperature: float = 0.7

    class GenerateResponse(BaseModel):
        code: str
        success: bool

    @web_app.get("/")
    async def root():
        return {
            "service": "BioQL VS Code Server",
            "status": "running",
            "endpoints": ["/health", "/generate"]
        }

    @web_app.get("/health")
    async def health():
        return {"status": "healthy", "model": "Qwen2.5-7B-Instruct"}

    @web_app.post("/generate", response_model=GenerateResponse)
    async def generate_endpoint(request: GenerateRequest):
        """Generate BioQL code from natural language prompt"""
        try:
            server = BioQLServer()
            result = server.generate.remote(
                request.prompt,
                request.max_length,
                request.temperature
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return web_app


# For testing locally
@app.local_entrypoint()
def test():
    """Test the server"""
    server = BioQLServer()

    test_prompts = [
        "Create a Bell state",
        "Generate a 3-qubit GHZ state",
        "Apply Hadamard to qubit 0 and measure"
    ]

    print("\n" + "="*70)
    print("Testing BioQL VS Code Server")
    print("="*70 + "\n")

    for prompt in test_prompts:
        print(f"📝 Prompt: {prompt}")
        result = server.generate.remote(prompt)
        print(f"✅ Generated code:")
        print(result['code'])
        print("\n" + "-"*70 + "\n")
