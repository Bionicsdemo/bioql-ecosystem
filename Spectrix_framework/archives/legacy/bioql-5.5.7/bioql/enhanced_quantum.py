"""
Enhanced BioQL Quantum Function with NL→IR→Quantum Pipeline

This module integrates the DevKit capabilities with the existing BioQL SaaS
to provide natural language processing, IR compilation, and quantum execution
with mandatory API key authentication.
"""

from typing import Dict, List, Optional, Union, Any
import logging
# Optional loguru import
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .quantum_connector import quantum as original_quantum, QuantumResult
from .parser.nl_parser import NaturalLanguageParser, ParseError
from .compilers.factory import create_compiler
from .ir import BioQLProgram, QuantumBackend


def enhanced_quantum(
    program: str,
    api_key: str,  # REQUIRED - Maintained from original
    backend: str = 'simulator',
    shots: int = 1024,
    debug: bool = False,
    token: Optional[str] = None,
    instance: Optional[str] = None,
    timeout: int = 3600,
    auto_select: bool = False,
    use_nlp: bool = True,  # NEW: Enable NL→IR processing
    use_ir_compiler: bool = True,  # NEW: Use DevKit compilers
    return_ir: bool = False  # NEW: Also return the IR
) -> Union[QuantumResult, Dict[str, Any]]:
    """
    Enhanced quantum function with Natural Language → IR → Quantum pipeline.

    This function extends the original quantum() with DevKit capabilities:
    1. Natural language parsing to BioQL-IR
    2. IR-based quantum compilation
    3. Multi-backend execution (Qiskit, Cirq)
    4. Maintains API key authentication for monetization

    Args:
        program: Natural language description OR BioQL program
        api_key: REQUIRED API key for authentication (SpectrixRD)
        backend: Quantum backend ('simulator', 'qiskit', 'cirq', 'ibm_eagle', etc.)
        shots: Number of quantum shots
        debug: Enable debug logging
        token: IBM Quantum token (for IBM backends)
        instance: IBM Quantum instance
        timeout: Execution timeout
        auto_select: Auto-select best backend
        use_nlp: Use natural language processing (NEW)
        use_ir_compiler: Use DevKit IR compilers (NEW)
        return_ir: Return IR along with results (NEW)

    Returns:
        QuantumResult with execution results, optionally with IR

    Examples:
        >>> # Enhanced NL processing with docking
        >>> result = enhanced_quantum(
        ...     "Dock ligand SMILES 'CCO' to protein PDB 1ABC with 20 poses",
        ...     api_key="bioql_your_key_here",
        ...     use_nlp=True,
        ...     backend='qiskit'
        ... )
        >>> print(result.bio_interpretation)

        >>> # Traditional usage (backwards compatible)
        >>> result = enhanced_quantum(
        ...     "Create a Bell state and measure",
        ...     api_key="bioql_your_key_here",
        ...     use_nlp=False
        ... )
    """

    # Configure debug logging
    if debug:
        logger.debug(f"Enhanced quantum execution: use_nlp={use_nlp}, use_ir_compiler={use_ir_compiler}")

    # Check if we should use NL processing
    if use_nlp and _should_use_nlp(program):
        try:
            # Parse natural language to BioQL IR
            logger.info("🧠 Using Natural Language → IR processing")
            parser = NaturalLanguageParser()
            bioql_program = parser.parse(program, "Enhanced BioQL Program")

            if debug:
                logger.debug(f"Generated IR: {bioql_program.name}")
                logger.debug(f"Operations: {len(bioql_program.operations)}")
                logger.debug(f"Domain: {bioql_program.operations[0].domain if bioql_program.operations else 'none'}")

            # Use IR compiler if enabled and backend supports it
            if use_ir_compiler and _backend_supports_ir(backend):
                logger.info("⚡ Using IR → Quantum compilation")

                # Map BioQL backend to quantum backend
                quantum_backend = _map_backend(bioql_program.backend.value, backend)

                # Execute using DevKit compiler
                result = _execute_with_ir_compiler(
                    bioql_program=bioql_program,
                    api_key=api_key,
                    backend=quantum_backend,
                    shots=shots,
                    debug=debug
                )

                # Add enhanced metadata
                result.metadata = result.metadata or {}
                result.metadata.update({
                    'enhanced_processing': True,
                    'nlp_used': True,
                    'ir_compiler_used': True,
                    'original_program': program,
                    'bioql_domain': bioql_program.operations[0].domain.value if bioql_program.operations else 'unknown'
                })

                # Add biological interpretation based on IR
                result.bio_interpretation = _enhance_bio_interpretation(
                    result.bio_interpretation or {},
                    bioql_program
                )

                if return_ir:
                    return {
                        'result': result,
                        'ir': bioql_program,
                        'enhanced': True
                    }

                return result

        except ParseError as e:
            logger.warning(f"NL parsing failed: {e}, falling back to original quantum()")
        except Exception as e:
            logger.warning(f"Enhanced processing failed: {e}, falling back to original quantum()")

    # Fallback to original quantum function
    logger.info("🔄 Using original BioQL quantum processing")
    result = original_quantum(
        program=program,
        api_key=api_key,
        backend=backend,
        shots=shots,
        debug=debug,
        token=token,
        instance=instance,
        timeout=timeout,
        auto_select=auto_select
    )

    # Add metadata to indicate processing type
    result.metadata = result.metadata or {}
    result.metadata.update({
        'enhanced_processing': False,
        'nlp_used': False,
        'ir_compiler_used': False,
        'fallback_reason': 'Original processing used'
    })

    if return_ir:
        return {
            'result': result,
            'ir': None,
            'enhanced': False
        }

    return result


def _should_use_nlp(program: str) -> bool:
    """Determine if natural language processing should be used."""
    # Use NLP if the program contains bioinformatics keywords
    bio_keywords = [
        'dock', 'docking', 'protein', 'ligand', 'bind', 'binding',
        'align', 'alignment', 'sequence', 'dna', 'rna',
        'fold', 'folding', 'structure', 'energy', 'minimize',
        'pdb', 'smiles', 'fasta', 'poses'
    ]

    text_lower = program.lower()
    return any(keyword in text_lower for keyword in bio_keywords)


def _backend_supports_ir(backend: str) -> bool:
    """Check if backend supports IR compilation."""
    supported_backends = ['simulator', 'qiskit', 'cirq', 'sim', 'aer']
    backend_lower = backend.lower()

    # Support IBM backends through Qiskit
    if backend_lower.startswith('ibm_'):
        return True

    return any(supported in backend_lower for supported in supported_backends)


def _map_backend(bioql_backend: str, requested_backend: str) -> str:
    """Map BioQL IR backend to quantum backend."""
    # If user specified a backend, use that
    if requested_backend and requested_backend != 'simulator':
        return requested_backend

    # Otherwise use the IR's suggestion
    backend_mapping = {
        'qiskit': 'simulator',  # Map to local simulator for safety
        'cirq': 'simulator',
        'simulator': 'simulator',
        'pennylane': 'simulator',
        'braket': 'simulator'
    }

    return backend_mapping.get(bioql_backend, 'simulator')


def _execute_with_ir_compiler(
    bioql_program: BioQLProgram,
    api_key: str,
    backend: str,
    shots: int,
    debug: bool
) -> QuantumResult:
    """Execute BioQL program using DevKit IR compiler."""
    from uuid import uuid4

    try:
        # Determine quantum backend
        if backend == 'cirq':
            quantum_backend = QuantumBackend.CIRQ
        elif backend == 'qiskit' or backend.startswith('ibm_'):
            quantum_backend = QuantumBackend.QISKIT
        else:
            quantum_backend = QuantumBackend.SIMULATOR

        # Create compiler
        compiler = create_compiler(quantum_backend)

        # Compile BioQL program to quantum circuit
        compiled_circuit = compiler.compile_program(bioql_program)

        if debug:
            logger.debug(f"Compiled to quantum circuit: {type(compiled_circuit)}")

        # Execute quantum circuit (with API key authentication)
        result = compiler.execute(compiled_circuit, shots=shots, program_id=bioql_program.id)

        # The IR compiler returns BioQLResult, we need to convert to QuantumResult
        quantum_result = _convert_bioql_to_quantum_result(result, bioql_program)

        return quantum_result

    except Exception as e:
        logger.error(f"IR compilation failed: {e}")
        # Return failed result compatible with original system
        from .quantum_connector import QuantumResult
        return QuantumResult(
            success=False,
            error_message=f"IR compilation failed: {str(e)}",
            metadata={'ir_compilation_error': True}
        )


def _convert_bioql_to_quantum_result(bioql_result, bioql_program: BioQLProgram) -> QuantumResult:
    """Convert BioQLResult to QuantumResult for compatibility."""
    from .quantum_connector import QuantumResult

    # Extract counts from BioQL result
    counts = {}
    if bioql_result.results and 'counts' in bioql_result.results:
        counts = bioql_result.results['counts']

    # Create compatible QuantumResult
    return QuantumResult(
        counts=counts,
        success=bioql_result.status == 'success',
        error_message=bioql_result.error_message,
        metadata={
            'bioql_program_id': str(bioql_result.program_id),
            'backend_used': bioql_result.backend_used.value if bioql_result.backend_used else 'unknown',
            'execution_time': bioql_result.execution_time,
            'shots_executed': bioql_result.shots_executed,
            'circuit_depth': bioql_result.results.get('circuit_depth') if bioql_result.results else None,
            'gate_count': bioql_result.results.get('gate_count') if bioql_result.results else None,
            'ir_enhanced': True
        },
        execution_time=bioql_result.execution_time,
        job_id=str(bioql_result.execution_id) if bioql_result.execution_id else None,
        backend_name=bioql_result.backend_used.value if bioql_result.backend_used else None,
        bio_interpretation={}  # Will be enhanced separately
    )


def _enhance_bio_interpretation(existing_interp: Dict[str, Any], bioql_program: BioQLProgram) -> Dict[str, Any]:
    """Enhance biological interpretation using BioQL IR information."""
    enhanced = existing_interp.copy()

    if bioql_program.operations:
        operation = bioql_program.operations[0]

        # Add domain-specific interpretation
        enhanced['bioql_domain'] = operation.domain.value
        enhanced['operation_type'] = operation.operation_type

        # Add operation-specific details
        if hasattr(operation, 'receptor') and hasattr(operation, 'ligand'):
            enhanced['docking'] = {
                'receptor': operation.receptor.name,
                'ligand': operation.ligand.name,
                'expected_poses': getattr(operation, 'num_poses', 'unknown'),
                'energy_threshold': getattr(operation, 'energy_threshold', 'unknown')
            }
        elif hasattr(operation, 'sequences'):
            enhanced['alignment'] = {
                'sequence_count': len(operation.sequences),
                'sequences': [seq.name for seq in operation.sequences[:3]]  # First 3
            }
        elif hasattr(operation, 'objective_function'):
            enhanced['optimization'] = {
                'objective': operation.objective_function,
                'variables': len(operation.variables) if hasattr(operation, 'variables') else 0
            }

    enhanced['enhanced_by_ir'] = True
    return enhanced


# Export the enhanced function
__all__ = ['enhanced_quantum']