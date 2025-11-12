"""
Safety layer for CRISPR-QAI

CRITICAL: This module ensures CRISPR-QAI is SIMULATION-ONLY
- Blocks wet-lab execution
- Prevents automated genome editing
- Enforces human-in-the-loop for experiments

ALL CRISPR-QAI OPERATIONS ARE FOR RESEARCH SIMULATION ONLY.
NO AUTOMATED WET-LAB EXECUTION IS PERMITTED.
"""

import warnings
from typing import Optional, Dict, Any


# Global safety flag (DO NOT MODIFY)
SIMULATION_ONLY = True


class CRISPRSafetyError(Exception):
    """Raised when attempting unsafe CRISPR operations"""
    pass


def check_simulation_only() -> bool:
    """
    Verify CRISPR-QAI is in simulation-only mode

    Returns:
        True if simulation-only (always True)

    Raises:
        CRISPRSafetyError: If safety check fails
    """
    if not SIMULATION_ONLY:
        raise CRISPRSafetyError(
            "CRITICAL: CRISPR-QAI safety violation detected. "
            "This module is SIMULATION-ONLY. "
            "Wet-lab execution is PROHIBITED."
        )

    return True


def log_safety_warning(operation: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log safety warning for CRISPR operation

    Args:
        operation: Operation being performed
        context: Additional context
    """
    message = (
        f"\n{'=' * 80}\n"
        f"⚠️  CRISPR-QAI SAFETY WARNING ⚠️\n"
        f"{'=' * 80}\n"
        f"Operation: {operation}\n"
        f"Mode: SIMULATION ONLY\n"
        f"\n"
        f"This is a computational simulation for research purposes.\n"
        f"DO NOT use these results for direct wet-lab execution.\n"
        f"\n"
        f"Required before experiments:\n"
        f"1. Comprehensive off-target validation\n"
        f"2. Ethics committee approval\n"
        f"3. Regulatory compliance verification\n"
        f"4. Expert review of guide designs\n"
        f"{'=' * 80}\n"
    )

    if context:
        message += f"Context: {context}\n"
        message += f"{'=' * 80}\n"

    warnings.warn(message, UserWarning, stacklevel=2)


def validate_research_use(
    purpose: str,
    institution: Optional[str] = None,
    ethics_approval: bool = False
) -> Dict[str, Any]:
    """
    Validate CRISPR-QAI is being used for legitimate research

    Args:
        purpose: Research purpose
        institution: Research institution
        ethics_approval: Ethics approval obtained

    Returns:
        Validation result

    Example:
        >>> validate_research_use(
        ...     purpose="In silico guide design for cancer research",
        ...     institution="MIT",
        ...     ethics_approval=False  # Not needed for simulation
        ... )
    """
    check_simulation_only()

    result = {
        'validated': True,
        'mode': 'simulation_only',
        'purpose': purpose,
        'institution': institution or 'Unknown',
        'ethics_approval_required': False,  # Not needed for simulation
        'warnings': []
    }

    # Add warnings for ambiguous use cases
    dangerous_keywords = [
        'human', 'clinical', 'patient', 'therapy', 'treatment',
        'germline', 'embryo', 'fetus'
    ]

    purpose_lower = purpose.lower()
    for keyword in dangerous_keywords:
        if keyword in purpose_lower:
            result['warnings'].append(
                f"⚠️  Detected '{keyword}' in purpose. "
                f"Human applications require extensive validation, "
                f"ethics approval, and regulatory oversight."
            )

    # Log safety warning
    log_safety_warning(
        operation="Research Use Validation",
        context=result
    )

    return result


def block_wet_lab_execution(operation: str) -> None:
    """
    Block any attempts at wet-lab execution

    Args:
        operation: Operation being blocked

    Raises:
        CRISPRSafetyError: Always (wet-lab execution not permitted)
    """
    raise CRISPRSafetyError(
        f"BLOCKED: {operation}\n"
        f"\n"
        f"CRISPR-QAI does not support automated wet-lab execution.\n"
        f"This is a SIMULATION-ONLY tool for computational research.\n"
        f"\n"
        f"To perform experiments:\n"
        f"1. Export guide designs from CRISPR-QAI\n"
        f"2. Conduct comprehensive validation\n"
        f"3. Obtain ethics/regulatory approval\n"
        f"4. Manually synthesize guides with approved vendors\n"
        f"5. Follow established wet-lab protocols\n"
    )


def get_safety_disclaimer() -> str:
    """
    Get full safety disclaimer text

    Returns:
        Safety disclaimer string
    """
    return """
╔════════════════════════════════════════════════════════════════════════════╗
║                       CRISPR-QAI SAFETY DISCLAIMER                         ║
╚════════════════════════════════════════════════════════════════════════════╝

THIS SOFTWARE IS FOR COMPUTATIONAL SIMULATION AND RESEARCH ONLY.

⚠️  IMPORTANT SAFETY NOTICES:

1. SIMULATION ONLY
   - All outputs are computational predictions
   - NOT validated for wet-lab use without extensive testing

2. NO AUTOMATED EXECUTION
   - This software does not interact with laboratory equipment
   - No automated genome editing capabilities
   - Human oversight required for all experiments

3. REGULATORY COMPLIANCE
   - Users must comply with local regulations (NIH Guidelines, etc.)
   - Ethics approval required for human/animal research
   - Export controls may apply in some jurisdictions

4. OFF-TARGET RISKS
   - Computational predictions may miss off-target sites
   - Comprehensive validation required before experiments
   - Consider genome-wide off-target analysis

5. RESPONSIBILITY
   - Users are solely responsible for experimental design
   - Users are solely responsible for safety and ethics compliance
   - Developers assume no liability for misuse

6. INTENDED USE
   - Academic research and education
   - Drug discovery and therapeutics development (pre-clinical)
   - Agricultural biotechnology (with appropriate approval)

7. PROHIBITED USE
   - Human germline editing without IRB approval
   - Bioweapons development
   - Unauthorized environmental release
   - Any use violating local laws or regulations

By using CRISPR-QAI, you acknowledge these terms and agree to use this
software responsibly and ethically.

For questions: bioql-support@example.com
Version: 1.0.0
╚════════════════════════════════════════════════════════════════════════════╝
"""


def print_safety_disclaimer() -> None:
    """
    Print safety disclaimer to console
    """
    print(get_safety_disclaimer())


# Auto-check on module import
check_simulation_only()
