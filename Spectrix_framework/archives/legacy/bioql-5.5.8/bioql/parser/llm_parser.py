"""
LLM-powered Natural Language Parser for BioQL

This module provides enhanced natural language parsing using Large Language Models
for more sophisticated understanding of bioinformatics queries.
"""

import json
from typing import Any, Dict, List, Optional, Type, Union

import httpx
from loguru import logger
from pydantic import BaseModel

from bioql.ir import BioQLProgram, validator
from .nl_parser import NaturalLanguageParser, ParseError


class LLMConfig(BaseModel):
    """Configuration for LLM-powered parsing."""

    provider: str = "openai"  # "openai", "anthropic", "local"
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30


class LLMParsingError(ParseError):
    """Exception raised when LLM parsing fails."""
    pass


class PromptTemplate:
    """Templates for LLM prompts."""

    SYSTEM_PROMPT = """You are a expert in quantum bioinformatics and computational biology.
Your task is to convert natural language descriptions into structured BioQL programs.

BioQL is a quantum computing framework for bioinformatics that supports:
- Molecular docking (binding proteins and ligands)
- Sequence alignment (DNA, RNA, protein sequences)
- Quantum optimization (energy minimization, conformational search)

You must respond with valid JSON that follows the BioQL program schema.
"""

    USER_PROMPT_TEMPLATE = """Convert this natural language description into a BioQL program:

"{text}"

Generate a complete BioQL program in JSON format with:
1. Program metadata (name, description)
2. Input molecules (with correct types and formats)
3. Operations (docking, alignment, or optimization)
4. Quantum backend configuration
5. Parameters and constraints

Focus on extracting:
- Molecular identifiers (PDB IDs, SMILES, sequences)
- Operation type and parameters
- File references
- Numerical values and units

Schema example:
{{
  "name": "Program Name",
  "description": "Description",
  "inputs": [
    {{
      "id": "molecule_id",
      "type": "protein|ligand|dna|rna",
      "format": "pdb|smiles|fasta|sdf",
      "data": "data_or_file_path",
      "name": "Human readable name"
    }}
  ],
  "operations": [
    {{
      "domain": "docking|alignment|optimization",
      "operation_type": "dock|align|optimize",
      "description": "Operation description",
      // operation-specific fields
    }}
  ],
  "backend": "simulator|qiskit|cirq|pennylane|braket",
  "shots": 1000
}}

Respond only with valid JSON, no additional text."""


class LLMParser:
    """LLM-powered parser for natural language to BioQL IR conversion."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.fallback_parser = NaturalLanguageParser()
        self.client = self._create_client()

    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client for LLM API calls."""
        headers = {}
        base_url = self.config.base_url

        if self.config.provider == "openai":
            headers["Authorization"] = f"Bearer {self.config.api_key}"
            base_url = base_url or "https://api.openai.com/v1"
        elif self.config.provider == "anthropic":
            headers["x-api-key"] = self.config.api_key
            headers["anthropic-version"] = "2023-06-01"
            base_url = base_url or "https://api.anthropic.com"

        return httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=self.config.timeout
        )

    async def parse_async(self, text: str, program_name: Optional[str] = None) -> BioQLProgram:
        """
        Parse natural language text using LLM (async version).

        Args:
            text: Natural language description
            program_name: Optional program name

        Returns:
            BioQLProgram instance

        Raises:
            LLMParsingError: If LLM parsing fails
        """
        try:
            logger.info(f"Parsing with LLM ({self.config.provider}): {text[:100]}...")

            # Call LLM API
            response_json = await self._call_llm_api(text)

            # Validate and parse the response
            program = validator.validate_program(response_json)

            if program_name:
                program.name = program_name

            # Add audit entry
            program.add_audit_entry("llm_parsed", {
                "provider": self.config.provider,
                "model": self.config.model,
                "input_text": text
            })

            logger.success(f"Successfully parsed with LLM: {program.name}")
            return program

        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}, falling back to pattern matching")
            return self.fallback_parser.parse(text, program_name)

    def parse(self, text: str, program_name: Optional[str] = None) -> BioQLProgram:
        """
        Parse natural language text using LLM (sync version).

        Args:
            text: Natural language description
            program_name: Optional program name

        Returns:
            BioQLProgram instance
        """
        import asyncio
        return asyncio.run(self.parse_async(text, program_name))

    async def _call_llm_api(self, text: str) -> Dict[str, Any]:
        """Call the LLM API and return parsed JSON response."""
        prompt = PromptTemplate.USER_PROMPT_TEMPLATE.format(text=text)

        if self.config.provider == "openai":
            return await self._call_openai_api(prompt)
        elif self.config.provider == "anthropic":
            return await self._call_anthropic_api(prompt)
        else:
            raise LLMParsingError(f"Unsupported LLM provider: {self.config.provider}")

    async def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": PromptTemplate.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"}
        }

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMParsingError(f"Invalid JSON response from OpenAI: {e}")

    async def _call_anthropic_api(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API."""
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": PromptTemplate.SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = await self.client.post("/v1/messages", json=payload)
        response.raise_for_status()

        result = response.json()
        content = result["content"][0]["text"]

        try:
            # Extract JSON from response (Anthropic may include additional text)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_content = content[json_start:json_end]
                return json.loads(json_content)
            else:
                raise LLMParsingError("No JSON found in Anthropic response")
        except json.JSONDecodeError as e:
            raise LLMParsingError(f"Invalid JSON response from Anthropic: {e}")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class HybridParser:
    """Hybrid parser that combines pattern matching and LLM parsing."""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.pattern_parser = NaturalLanguageParser()
        self.llm_parser = LLMParser(llm_config) if llm_config else None

    async def parse_async(
        self,
        text: str,
        program_name: Optional[str] = None,
        use_llm: bool = True
    ) -> BioQLProgram:
        """
        Parse using hybrid approach (async version).

        Args:
            text: Natural language description
            program_name: Optional program name
            use_llm: Whether to try LLM first

        Returns:
            BioQLProgram instance
        """
        if use_llm and self.llm_parser:
            try:
                return await self.llm_parser.parse_async(text, program_name)
            except Exception as e:
                logger.warning(f"LLM parsing failed: {e}, using pattern matching")

        return self.pattern_parser.parse(text, program_name)

    def parse(
        self,
        text: str,
        program_name: Optional[str] = None,
        use_llm: bool = True
    ) -> BioQLProgram:
        """
        Parse using hybrid approach (sync version).

        Args:
            text: Natural language description
            program_name: Optional program name
            use_llm: Whether to try LLM first

        Returns:
            BioQLProgram instance
        """
        import asyncio
        return asyncio.run(self.parse_async(text, program_name, use_llm))

    async def close(self) -> None:
        """Close any open connections."""
        if self.llm_parser:
            await self.llm_parser.close()


# Convenience function for quick parsing
async def parse_natural_language(
    text: str,
    program_name: Optional[str] = None,
    llm_config: Optional[LLMConfig] = None,
    use_llm: bool = True
) -> BioQLProgram:
    """
    Convenience function for parsing natural language.

    Args:
        text: Natural language description
        program_name: Optional program name
        llm_config: Optional LLM configuration
        use_llm: Whether to use LLM if available

    Returns:
        BioQLProgram instance
    """
    parser = HybridParser(llm_config)
    try:
        return await parser.parse_async(text, program_name, use_llm)
    finally:
        await parser.close()


# Export main classes
__all__ = [
    "LLMConfig",
    "LLMParser",
    "LLMParsingError",
    "HybridParser",
    "parse_natural_language"
]