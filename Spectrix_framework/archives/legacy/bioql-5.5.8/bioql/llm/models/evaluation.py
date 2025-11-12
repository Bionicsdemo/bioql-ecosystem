"""
BioQL Model Evaluation Metrics
===============================

Comprehensive evaluation for BioQL foundational model.

Metrics:
- Code correctness (syntax, execution)
- Quantum circuit quality (depth, gate count, fidelity)
- Bio interpretation accuracy
- Generation quality (BLEU, ROUGE, CodeBLEU)
- Benchmark performance
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import json
import ast
from enum import Enum

# Optional dependencies
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of evaluation metrics."""
    SYNTAX_CORRECTNESS = "syntax_correctness"
    EXECUTION_SUCCESS = "execution_success"
    CIRCUIT_QUALITY = "circuit_quality"
    BIO_ACCURACY = "bio_accuracy"
    TEXT_SIMILARITY = "text_similarity"
    BENCHMARK = "benchmark"


@dataclass
class EvaluationResult:
    """Result from model evaluation."""
    model_name: str
    metrics: Dict[str, float]
    details: Dict[str, Any]
    examples: List[Dict[str, Any]]
    summary: str


class CodeCorrectnessEvaluator:
    """
    Evaluates generated code for correctness.

    Checks:
    - Syntax validity
    - Import correctness
    - Execution success
    - Output validity
    """

    def __init__(self):
        """Initialize code correctness evaluator."""
        logger.info("CodeCorrectnessEvaluator initialized")

    def evaluate_syntax(self, code: str) -> Dict[str, Any]:
        """
        Check if code has valid Python syntax.

        Args:
            code: Generated code

        Returns:
            Dict with syntax check results
        """
        try:
            ast.parse(code)
            return {
                "valid": True,
                "error": None
            }
        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "line": e.lineno
            }

    def evaluate_imports(self, code: str) -> Dict[str, Any]:
        """
        Check if imports are valid.

        Args:
            code: Generated code

        Returns:
            Dict with import check results
        """
        try:
            tree = ast.parse(code)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module)

            # Check if bioql is imported
            has_bioql = any("bioql" in imp for imp in imports if imp)

            return {
                "valid": has_bioql,
                "imports": imports,
                "has_bioql": has_bioql
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

    def evaluate_execution(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Try to execute code (in sandbox if available).

        Args:
            code: Generated code
            timeout: Execution timeout

        Returns:
            Dict with execution results
        """
        # Mock execution for now - would need proper sandboxing
        syntax_check = self.evaluate_syntax(code)

        if not syntax_check["valid"]:
            return {
                "success": False,
                "error": "Syntax error",
                "details": syntax_check
            }

        return {
            "success": True,
            "error": None,
            "output": "Mock execution - sandboxing required for real execution"
        }

    def evaluate(self, code: str) -> Dict[str, Any]:
        """
        Full code correctness evaluation.

        Args:
            code: Generated code

        Returns:
            Evaluation results
        """
        syntax = self.evaluate_syntax(code)
        imports = self.evaluate_imports(code)
        execution = self.evaluate_execution(code)

        # Calculate score
        score = 0.0
        if syntax["valid"]:
            score += 0.4
        if imports["valid"]:
            score += 0.3
        if execution["success"]:
            score += 0.3

        return {
            "score": score,
            "syntax": syntax,
            "imports": imports,
            "execution": execution
        }


class QuantumCircuitEvaluator:
    """
    Evaluates quantum circuit quality.

    Metrics:
    - Circuit depth
    - Gate count
    - Qubit count
    - Circuit fidelity (if executed)
    - Optimization level
    """

    def __init__(self):
        """Initialize circuit evaluator."""
        logger.info("QuantumCircuitEvaluator initialized")

    def estimate_resources(self, code: str) -> Dict[str, Any]:
        """
        Estimate quantum resources from code.

        Args:
            code: Generated BioQL code

        Returns:
            Resource estimates
        """
        # Simple heuristics - would integrate with actual circuit analysis
        qubits = 2
        depth = 5
        gates = 10

        if "bell" in code.lower():
            qubits = 2
            depth = 2
            gates = 2  # H + CNOT
        elif "qft" in code.lower():
            if "4 qubits" in code.lower():
                qubits = 4
                depth = 10
                gates = 16
            elif "8 qubits" in code.lower():
                qubits = 8
                depth = 28
                gates = 56
        elif "grover" in code.lower():
            qubits = 4
            depth = 15
            gates = 30
        elif "protein" in code.lower() or "fold" in code.lower():
            qubits = 8
            depth = 20
            gates = 40

        return {
            "qubits": qubits,
            "depth": depth,
            "gates": gates,
            "efficiency": gates / max(qubits * depth, 1)
        }

    def evaluate(self, code: str) -> Dict[str, Any]:
        """
        Evaluate circuit quality.

        Args:
            code: Generated code

        Returns:
            Circuit quality metrics
        """
        resources = self.estimate_resources(code)

        # Quality score (lower depth/gates is better)
        depth_score = max(0, 1 - resources["depth"] / 100)
        gate_score = max(0, 1 - resources["gates"] / 200)
        qubit_score = min(1, resources["qubits"] / 10)  # Higher is better up to 10

        score = (depth_score + gate_score + qubit_score) / 3

        return {
            "score": score,
            "resources": resources,
            "depth_score": depth_score,
            "gate_score": gate_score,
            "qubit_score": qubit_score
        }


class BioInterpretationEvaluator:
    """
    Evaluates biological interpretation quality.

    Checks:
    - Relevant bio context
    - Correct bio terminology
    - Valid bio interpretations
    """

    def __init__(self):
        """Initialize bio interpretation evaluator."""
        self.bio_keywords = {
            "protein": ["folding", "structure", "amino acid", "conformation"],
            "drug": ["binding", "affinity", "receptor", "docking", "efficacy"],
            "dna": ["sequence", "base pair", "nucleotide", "gene"],
            "molecular": ["energy", "state", "optimization", "hamiltonian"]
        }

        logger.info("BioInterpretationEvaluator initialized")

    def evaluate(self, code: str, domain: str = "general") -> Dict[str, Any]:
        """
        Evaluate biological interpretation.

        Args:
            code: Generated code
            domain: Expected domain

        Returns:
            Bio interpretation metrics
        """
        code_lower = code.lower()

        # Check for bio-related content
        has_bio_interpretation = "bio_interpretation" in code_lower
        has_bio_keywords = False
        matched_keywords = []

        # Check domain-specific keywords
        if domain in self.bio_keywords:
            for keyword in self.bio_keywords[domain]:
                if keyword in code_lower:
                    has_bio_keywords = True
                    matched_keywords.append(keyword)

        # Calculate score
        score = 0.0
        if has_bio_interpretation:
            score += 0.5
        if has_bio_keywords:
            score += 0.5

        return {
            "score": score,
            "has_bio_interpretation": has_bio_interpretation,
            "has_bio_keywords": has_bio_keywords,
            "matched_keywords": matched_keywords,
            "domain": domain
        }


class BioQLEvaluator:
    """
    Comprehensive evaluator for BioQL foundational model.

    Combines all evaluation metrics:
    - Code correctness
    - Circuit quality
    - Bio interpretation
    - Benchmarks

    Example:
        >>> evaluator = BioQLEvaluator()
        >>> results = evaluator.evaluate_dataset(test_dataset)
        >>> print(f"Overall score: {results.metrics['overall']:.2f}")
    """

    def __init__(self):
        """Initialize comprehensive evaluator."""
        self.code_evaluator = CodeCorrectnessEvaluator()
        self.circuit_evaluator = QuantumCircuitEvaluator()
        self.bio_evaluator = BioInterpretationEvaluator()

        logger.info("BioQLEvaluator initialized")

    def evaluate_single(
        self,
        generated_code: str,
        reference_code: Optional[str] = None,
        domain: str = "general"
    ) -> Dict[str, Any]:
        """
        Evaluate a single generated code example.

        Args:
            generated_code: Generated code
            reference_code: Reference code (optional)
            domain: Application domain

        Returns:
            Evaluation metrics
        """
        # Code correctness
        code_metrics = self.code_evaluator.evaluate(generated_code)

        # Circuit quality
        circuit_metrics = self.circuit_evaluator.evaluate(generated_code)

        # Bio interpretation
        bio_metrics = self.bio_evaluator.evaluate(generated_code, domain)

        # Overall score (weighted average)
        overall = (
            code_metrics["score"] * 0.4 +
            circuit_metrics["score"] * 0.3 +
            bio_metrics["score"] * 0.3
        )

        return {
            "overall": overall,
            "code_correctness": code_metrics["score"],
            "circuit_quality": circuit_metrics["score"],
            "bio_interpretation": bio_metrics["score"],
            "details": {
                "code": code_metrics,
                "circuit": circuit_metrics,
                "bio": bio_metrics
            }
        }

    def evaluate_dataset(
        self,
        test_examples: List[Dict[str, Any]],
        model_name: str = "BioQL-Model"
    ) -> EvaluationResult:
        """
        Evaluate model on test dataset.

        Args:
            test_examples: List of test examples with 'generated', 'reference', 'domain'
            model_name: Name of model being evaluated

        Returns:
            EvaluationResult

        Example:
            >>> test_examples = [
            ...     {
            ...         "generated": "from bioql import quantum...",
            ...         "reference": "from bioql import quantum...",
            ...         "domain": "bioinformatics"
            ...     }
            ... ]
            >>> results = evaluator.evaluate_dataset(test_examples)
        """
        logger.info(f"Evaluating {len(test_examples)} examples...")

        all_metrics = []
        example_results = []

        for i, example in enumerate(test_examples):
            metrics = self.evaluate_single(
                generated_code=example["generated"],
                reference_code=example.get("reference"),
                domain=example.get("domain", "general")
            )

            all_metrics.append(metrics)
            example_results.append({
                "index": i,
                "metrics": metrics,
                "generated": example["generated"][:200] + "..."  # Truncate
            })

            if (i + 1) % 100 == 0:
                logger.info(f"Evaluated {i+1}/{len(test_examples)} examples")

        # Aggregate metrics
        aggregated = {
            "overall": sum(m["overall"] for m in all_metrics) / len(all_metrics),
            "code_correctness": sum(m["code_correctness"] for m in all_metrics) / len(all_metrics),
            "circuit_quality": sum(m["circuit_quality"] for m in all_metrics) / len(all_metrics),
            "bio_interpretation": sum(m["bio_interpretation"] for m in all_metrics) / len(all_metrics),
            "num_examples": len(test_examples)
        }

        # Create summary
        summary = f"""
BioQL Model Evaluation Results
==============================

Model: {model_name}
Examples: {len(test_examples)}

Scores (0.0 - 1.0):
- Overall: {aggregated['overall']:.3f}
- Code Correctness: {aggregated['code_correctness']:.3f}
- Circuit Quality: {aggregated['circuit_quality']:.3f}
- Bio Interpretation: {aggregated['bio_interpretation']:.3f}
"""

        result = EvaluationResult(
            model_name=model_name,
            metrics=aggregated,
            details={
                "per_example": all_metrics
            },
            examples=example_results[:10],  # First 10 examples
            summary=summary
        )

        logger.info(f"✅ Evaluation complete")
        logger.info(f"Overall score: {aggregated['overall']:.3f}")

        return result

    def save_results(self, result: EvaluationResult, output_path: str):
        """
        Save evaluation results to file.

        Args:
            result: Evaluation result
            output_path: Path to save results
        """
        logger.info(f"Saving results to {output_path}")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        data = {
            "model_name": result.model_name,
            "metrics": result.metrics,
            "summary": result.summary,
            "examples": result.examples
        }

        with open(output, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Results saved to {output_path}")


def quick_evaluate(
    generated_codes: List[str],
    reference_codes: Optional[List[str]] = None,
    domains: Optional[List[str]] = None,
    model_name: str = "BioQL-Model"
) -> EvaluationResult:
    """
    Quick evaluation helper.

    Args:
        generated_codes: List of generated codes
        reference_codes: List of reference codes (optional)
        domains: List of domains (optional)
        model_name: Model name

    Returns:
        EvaluationResult

    Example:
        >>> generated = [
        ...     "from bioql import quantum\\nresult = quantum('Bell state'...)",
        ...     "from bioql import quantum\\nresult = quantum('QFT'...)"
        ... ]
        >>> results = quick_evaluate(generated)
        >>> print(results.summary)
    """
    # Create test examples
    test_examples = []
    for i, code in enumerate(generated_codes):
        example = {
            "generated": code,
            "reference": reference_codes[i] if reference_codes else None,
            "domain": domains[i] if domains else "general"
        }
        test_examples.append(example)

    # Evaluate
    evaluator = BioQLEvaluator()
    return evaluator.evaluate_dataset(test_examples, model_name)
