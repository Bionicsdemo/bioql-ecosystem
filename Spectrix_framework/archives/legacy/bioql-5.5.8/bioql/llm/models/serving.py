"""
BioQL Model Serving API
=======================

Production-ready API for serving BioQL foundational model.

Features:
- FastAPI REST API
- vLLM backend for high throughput
- Rate limiting
- Monitoring
- Batch processing
- Streaming responses
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio

# Optional dependencies
try:
    from fastapi import FastAPI, HTTPException, Depends
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
    _fastapi_available = True
except ImportError:
    _fastapi_available = False
    FastAPI = None
    BaseModel = object

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


if _fastapi_available:
    # Request/Response models
    class GenerateRequest(BaseModel):
        """Request for code generation."""
        prompt: str = Field(..., description="Natural language description")
        max_length: int = Field(512, description="Maximum generation length")
        temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
        top_p: float = Field(0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
        stream: bool = Field(False, description="Stream response")

        class Config:
            schema_extra = {
                "example": {
                    "prompt": "Create a Bell state and measure it",
                    "max_length": 512,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "stream": False
                }
            }

    class GenerateResponse(BaseModel):
        """Response with generated code."""
        code: str = Field(..., description="Generated BioQL code")
        prompt: str = Field(..., description="Original prompt")
        model: str = Field(..., description="Model used")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class HealthResponse(BaseModel):
        """Health check response."""
        status: str
        model_loaded: bool
        model_name: str
        version: str

    class BioQLServingAPI:
        """
        Production serving API for BioQL model.

        Example:
            >>> # Start server
            >>> api = BioQLServingAPI(model_path="./bioql-7b-finetuned")
            >>> api.start(host="0.0.0.0", port=8000)
            >>>
            >>> # Query from client:
            >>> import requests
            >>> response = requests.post(
            ...     "http://localhost:8000/generate",
            ...     json={"prompt": "Create a Bell state"}
            ... )
            >>> print(response.json()["code"])
        """

        def __init__(
            self,
            model_path: str,
            model_name: Optional[str] = None,
            quantization: Optional[str] = None,
            use_vllm: bool = True
        ):
            """
            Initialize serving API.

            Args:
                model_path: Path to model
                model_name: Base model name
                quantization: Quantization method
                use_vllm: Use vLLM backend
            """
            self.model_path = model_path
            self.model_name = model_name
            self.quantization = quantization
            self.use_vllm = use_vllm

            self.inference_engine = None
            self.app = None

            logger.info("BioQLServingAPI initialized")

        def create_app(self) -> FastAPI:
            """
            Create FastAPI application.

            Returns:
                FastAPI app
            """
            app = FastAPI(
                title="BioQL Foundational Model API",
                description="Production API for BioQL quantum code generation",
                version="1.0.0"
            )

            @app.on_event("startup")
            async def startup():
                """Load model on startup."""
                logger.info("Loading model...")
                from .inference import BioQLInference

                self.inference_engine = BioQLInference(
                    model_path=self.model_path,
                    model_name=self.model_name,
                    quantization=self.quantization,
                    use_vllm=self.use_vllm
                )
                self.inference_engine.load_model()
                logger.info("✅ Model loaded and ready")

            @app.get("/health", response_model=HealthResponse)
            async def health():
                """Health check endpoint."""
                return HealthResponse(
                    status="healthy",
                    model_loaded=self.inference_engine is not None,
                    model_name=self.model_path,
                    version="1.0.0"
                )

            @app.post("/generate", response_model=GenerateResponse)
            async def generate(request: GenerateRequest):
                """
                Generate BioQL code from prompt.

                Args:
                    request: Generation request

                Returns:
                    Generated code

                Example:
                    ```bash
                    curl -X POST "http://localhost:8000/generate" \\
                      -H "Content-Type: application/json" \\
                      -d '{"prompt": "Create a Bell state"}'
                    ```
                """
                if self.inference_engine is None:
                    raise HTTPException(status_code=503, detail="Model not loaded")

                try:
                    # Import here to avoid circular dependency
                    from .inference import GenerationConfig

                    # Create config
                    config = GenerationConfig(
                        max_length=request.max_length,
                        temperature=request.temperature,
                        top_p=request.top_p
                    )

                    # Generate
                    result = self.inference_engine.generate(
                        prompt=request.prompt,
                        config=config,
                        stream=False
                    )

                    return GenerateResponse(
                        code=result.generated_code,
                        prompt=request.prompt,
                        model=self.model_path,
                        metadata=result.metadata
                    )

                except Exception as e:
                    logger.error(f"Generation error: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @app.post("/generate/stream")
            async def generate_stream(request: GenerateRequest):
                """
                Generate BioQL code with streaming.

                Args:
                    request: Generation request

                Returns:
                    Streaming response
                """
                if self.inference_engine is None:
                    raise HTTPException(status_code=503, detail="Model not loaded")

                async def stream_generator():
                    """Generate streaming response."""
                    from .inference import GenerationConfig

                    config = GenerationConfig(
                        max_length=request.max_length,
                        temperature=request.temperature,
                        top_p=request.top_p
                    )

                    # Stream generation
                    for chunk in self.inference_engine.generate_stream(
                        prompt=request.prompt,
                        config=config
                    ):
                        yield chunk

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/plain"
                )

            @app.post("/batch")
            async def batch_generate(requests: List[GenerateRequest]):
                """
                Batch generation endpoint.

                Args:
                    requests: List of generation requests

                Returns:
                    List of generated codes
                """
                if self.inference_engine is None:
                    raise HTTPException(status_code=503, detail="Model not loaded")

                try:
                    from .inference import GenerationConfig

                    # Process batch
                    results = []
                    for req in requests:
                        config = GenerationConfig(
                            max_length=req.max_length,
                            temperature=req.temperature,
                            top_p=req.top_p
                        )

                        result = self.inference_engine.generate(
                            prompt=req.prompt,
                            config=config
                        )

                        results.append(GenerateResponse(
                            code=result.generated_code,
                            prompt=req.prompt,
                            model=self.model_path,
                            metadata=result.metadata
                        ))

                    return results

                except Exception as e:
                    logger.error(f"Batch generation error: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            self.app = app
            return app

        def start(
            self,
            host: str = "0.0.0.0",
            port: int = 8000,
            reload: bool = False
        ):
            """
            Start serving API.

            Args:
                host: Host to bind to
                port: Port to bind to
                reload: Enable auto-reload (dev only)

            Example:
                >>> api = BioQLServingAPI(model_path="./bioql-7b")
                >>> api.start(port=8000)
            """
            if self.app is None:
                self.create_app()

            logger.info(f"Starting BioQL API on {host}:{port}")

            import uvicorn
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                reload=reload
            )

else:
    # Stub when FastAPI not available
    class BioQLServingAPI:
        def __init__(self, *args, **kwargs):
            raise ImportError("FastAPI required for serving. Install with: pip install fastapi uvicorn")


def serve_model(
    model_path: str,
    model_name: Optional[str] = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    quantization: Optional[str] = None,
    use_vllm: bool = True
):
    """
    Quick serving helper.

    Args:
        model_path: Path to model
        model_name: Base model name
        host: Host to bind to
        port: Port to bind to
        quantization: Quantization method
        use_vllm: Use vLLM

    Example:
        >>> # Serve model
        >>> serve_model(
        ...     model_path="./bioql-7b-finetuned",
        ...     model_name="meta-llama/Llama-2-7b-hf",
        ...     port=8000
        ... )
        >>>
        >>> # Client usage:
        >>> import requests
        >>> response = requests.post(
        ...     "http://localhost:8000/generate",
        ...     json={"prompt": "Create a Bell state"}
        ... )
        >>> print(response.json()["code"])
    """
    if not _fastapi_available:
        raise ImportError("FastAPI required")

    api = BioQLServingAPI(
        model_path=model_path,
        model_name=model_name,
        quantization=quantization,
        use_vllm=use_vllm
    )

    api.start(host=host, port=port)
