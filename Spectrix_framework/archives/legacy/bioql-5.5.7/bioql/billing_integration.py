#!/usr/bin/env python3
"""
BioQL Billing Integration Module

This module provides seamless integration between the BioQL quantum() function
and the BP&PL billing system. It includes usage tracking, quota enforcement,
cost calculation, and billing metadata while preserving all existing functionality.

Features:
- Automatic user identification via API keys
- Real-time cost calculation based on shots, qubits, algorithm complexity
- Usage quotas enforcement (free users get 1000 shots/month)
- Billing metadata in quantum results
- Optional billing mode (can be disabled for development)
"""

import os
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union, Callable
from functools import wraps
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)

# Environment variable configuration
BILLING_ENABLED = os.getenv('BIOQL_BILLING_ENABLED', 'true').lower() == 'true'
BILLING_DATABASE_URL = os.getenv('BIOQL_BILLING_DATABASE_URL')
BILLING_CONFIG_PATH = os.getenv('BIOQL_BILLING_CONFIG', '/Users/heinzjungbluth/.bioql/billing_config.json')

# Default pricing configuration
DEFAULT_PRICING_CONFIG = {
    "simulator_cost_per_shot": "0.001",
    "hardware_cost_per_shot": "0.01",
    "algorithm_multipliers": {
        "basic": 1.0,
        "vqe": 2.0,
        "grover": 1.5,
        "shor": 3.0,
        "qaoa": 2.5,
        "custom": 1.0
    },
    "free_tier_shots_per_month": 1000,
    "complexity_multipliers": {
        "low": 1.0,    # <= 4 qubits
        "medium": 2.0, # 5-8 qubits
        "high": 5.0    # 9+ qubits
    }
}

# Free tier quotas for new users
FREE_TIER_QUOTAS = [
    {"quota_type": "shots_per_month", "limit": 1000, "period_seconds": 30*24*3600},
    {"quota_type": "api_calls_per_hour", "limit": 100, "period_seconds": 3600},
    {"quota_type": "concurrent_jobs", "limit": 2, "period_seconds": 1}
]


@dataclass
class BillingResult:
    """Enhanced QuantumResult with billing information."""
    # Original QuantumResult fields
    counts: Dict[str, int] = field(default_factory=dict)
    statevector: Optional[Any] = None
    bio_interpretation: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    job_id: Optional[str] = None
    backend_name: Optional[str] = None
    execution_time: Optional[float] = None
    queue_time: Optional[float] = None
    cost_estimate: Optional[float] = None

    # Billing-specific fields
    billing_metadata: Dict[str, Any] = field(default_factory=dict)
    usage_log_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    quota_status: Dict[str, Any] = field(default_factory=dict)
    cost_breakdown: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_shots(self) -> int:
        """Total number of shots executed."""
        return sum(self.counts.values()) if self.counts else 0

    @property
    def most_likely_outcome(self) -> Optional[str]:
        """The measurement outcome with the highest probability."""
        if not self.counts:
            return None
        return max(self.counts.keys(), key=lambda k: self.counts[k])

    def probabilities(self) -> Dict[str, float]:
        """Convert counts to probabilities."""
        if not self.counts:
            return {}
        total = self.total_shots
        return {outcome: count / total for outcome, count in self.counts.items()}


class BillingConnectionManager:
    """Manages database connections and session handling for billing."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or BILLING_DATABASE_URL
        self._db_session = None
        self._engine = None

    def get_session(self):
        """Get or create database session."""
        if not self.database_url:
            logger.warning("No billing database URL configured. Billing features disabled.")
            return None

        if self._db_session is None:
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                if not self._engine:
                    self._engine = create_engine(self.database_url)

                Session = sessionmaker(bind=self._engine)
                self._db_session = Session()
                logger.info("Connected to billing database")

            except ImportError:
                logger.error("SQLAlchemy not available. Install with: pip install sqlalchemy")
                return None
            except Exception as e:
                logger.error(f"Failed to connect to billing database: {e}")
                return None

        return self._db_session

    def close_session(self):
        """Close database session."""
        if self._db_session:
            self._db_session.close()
            self._db_session = None


class BillingIntegration:
    """Main billing integration class that wraps the quantum() function."""

    def __init__(self, pricing_config: Optional[Dict] = None, database_url: Optional[str] = None):
        self.pricing_config = pricing_config or self._load_pricing_config()
        self.db_manager = BillingConnectionManager(database_url)
        self.usage_tracker = None
        self._initialize_billing()

    def _load_pricing_config(self) -> Dict[str, Any]:
        """Load pricing configuration from file or use defaults."""
        try:
            if os.path.exists(BILLING_CONFIG_PATH):
                import json
                with open(BILLING_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded pricing config from {BILLING_CONFIG_PATH}")
                    return {**DEFAULT_PRICING_CONFIG, **config}
        except Exception as e:
            logger.warning(f"Could not load pricing config: {e}. Using defaults.")

        return DEFAULT_PRICING_CONFIG.copy()

    def _initialize_billing(self):
        """Initialize billing components if available."""
        if not BILLING_ENABLED:
            logger.info("Billing disabled via environment variable")
            return

        db_session = self.db_manager.get_session()
        if db_session:
            try:
                # Import BP&PL components
                from ..BP.services.usage_tracker import UsageTracker
                from ..BP.models.user import User, APIKey

                self.usage_tracker = UsageTracker(db_session, self.pricing_config)
                logger.info("Billing integration initialized successfully")

            except ImportError as e:
                logger.warning(f"BP&PL billing components not available: {e}")
                self.usage_tracker = None
            except Exception as e:
                logger.error(f"Failed to initialize billing: {e}")
                self.usage_tracker = None

    def authenticate_user(self, api_key: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Authenticate user via API key or user ID."""
        if not self.usage_tracker:
            return None

        db_session = self.db_manager.get_session()
        if not db_session:
            return None

        try:
            from ..BP.models.user import User, APIKey

            if api_key:
                # Authenticate via API key
                api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                api_key_obj = db_session.query(APIKey).filter_by(key_hash=api_key_hash).first()

                if api_key_obj and api_key_obj.is_valid():
                    user = db_session.query(User).filter_by(id=api_key_obj.user_id).first()
                    if user and user.is_active:
                        api_key_obj.record_usage()
                        db_session.commit()
                        return {
                            'user_id': user.id,
                            'api_key_id': api_key_obj.id,
                            'user': user,
                            'api_key': api_key_obj,
                            'authenticated_via': 'api_key'
                        }

            elif user_id:
                # Direct user ID authentication (for internal use)
                user = db_session.query(User).filter_by(id=user_id).first()
                if user and user.is_active:
                    return {
                        'user_id': user.id,
                        'api_key_id': None,
                        'user': user,
                        'api_key': None,
                        'authenticated_via': 'user_id'
                    }

        except Exception as e:
            logger.error(f"Authentication failed: {e}")

        return None

    def check_quotas(self, user_auth: Dict[str, Any], shots: int) -> Dict[str, Any]:
        """Check user quotas before execution."""
        if not self.usage_tracker:
            return {'allowed': True, 'reason': 'Billing disabled'}

        try:
            quota_check = self.usage_tracker.quota_manager.check_user_quotas(
                user_auth['user_id'],
                shots=shots,
                api_key_id=user_auth.get('api_key_id')
            )
            return quota_check

        except Exception as e:
            logger.error(f"Quota check failed: {e}")
            return {'allowed': False, 'reason': f'Quota check error: {str(e)}'}

    def calculate_cost_estimate(self, circuit_qubits: int, circuit_depth: int,
                               backend: str, shots: int, program_text: str) -> Dict[str, Any]:
        """Calculate cost estimate before execution."""
        try:
            # Determine backend type
            backend_type = 'simulator'
            if any(hw in backend.lower() for hw in ['ibm_', 'ionq_qpu', 'hardware']):
                backend_type = 'real_hardware'

            # Base cost per shot
            if backend_type == 'simulator':
                base_cost = float(self.pricing_config.get('simulator_cost_per_shot', '0.001'))
            else:
                base_cost = float(self.pricing_config.get('hardware_cost_per_shot', '0.01'))

            # Complexity multiplier
            if circuit_qubits <= 4:
                complexity_mult = self.pricing_config['complexity_multipliers']['low']
            elif circuit_qubits <= 8:
                complexity_mult = self.pricing_config['complexity_multipliers']['medium']
            else:
                complexity_mult = self.pricing_config['complexity_multipliers']['high']

            # Algorithm multiplier
            algorithm_type = self._classify_algorithm(program_text)
            algorithm_mult = self.pricing_config['algorithm_multipliers'].get(algorithm_type, 1.0)

            # Calculate total
            total_cost = base_cost * shots * complexity_mult * algorithm_mult

            return {
                'total_cost': total_cost,
                'base_cost_per_shot': base_cost,
                'complexity_multiplier': complexity_mult,
                'algorithm_multiplier': algorithm_mult,
                'algorithm_type': algorithm_type,
                'backend_type': backend_type,
                'breakdown': {
                    'base_cost': base_cost * shots,
                    'complexity_factor': complexity_mult,
                    'algorithm_factor': algorithm_mult,
                    'final_cost': total_cost
                }
            }

        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            return {
                'total_cost': 0.0,
                'error': str(e)
            }

    def _classify_algorithm(self, program_text: str) -> str:
        """Classify algorithm type from program text."""
        program_lower = program_text.lower()

        if any(keyword in program_lower for keyword in ['vqe', 'variational quantum eigensolver']):
            return 'vqe'
        elif any(keyword in program_lower for keyword in ['grover', 'search', 'amplitude amplification']):
            return 'grover'
        elif any(keyword in program_lower for keyword in ['shor', 'factoring', 'period finding']):
            return 'shor'
        elif any(keyword in program_lower for keyword in ['qaoa', 'quantum approximate optimization']):
            return 'qaoa'
        else:
            return 'basic'

    def log_usage(self, user_auth: Dict[str, Any], program_text: str,
                  circuit_qubits: int, circuit_depth: int, circuit_gates: int,
                  backend_requested: str, backend_used: str, shots: int,
                  result: Any, client_metadata: Optional[Dict] = None) -> Optional[str]:
        """Log quantum execution for billing."""
        if not self.usage_tracker:
            return None

        try:
            usage_log = self.usage_tracker.log_quantum_execution(
                user_id=user_auth['user_id'],
                program_text=program_text,
                circuit_qubits=circuit_qubits,
                circuit_depth=circuit_depth,
                circuit_gates=circuit_gates,
                backend_requested=backend_requested,
                backend_used=backend_used,
                shots_requested=shots,
                result=result,
                api_key_id=user_auth.get('api_key_id'),
                client_metadata=client_metadata or {}
            )

            return usage_log.id if usage_log else None

        except Exception as e:
            logger.error(f"Usage logging failed: {e}")
            return None


def create_billing_quantum_function(database_url: Optional[str] = None,
                                   pricing_config: Optional[Dict] = None) -> Callable:
    """
    Factory function to create a billing-enabled quantum function.

    This creates a quantum function that integrates with the BP&PL billing system
    while preserving all existing functionality of the original quantum() function.

    Args:
        database_url: Database URL for billing system (optional)
        pricing_config: Custom pricing configuration (optional)

    Returns:
        Callable quantum function with billing integration

    Examples:
        >>> # Create billing-enabled quantum function
        >>> quantum_with_billing = create_billing_quantum_function()
        >>>
        >>> # Use exactly like the original quantum function
        >>> result = quantum_with_billing("Create Bell state", backend="simulator")
        >>> print(result.counts)
        {'00': 512, '11': 512}
        >>>
        >>> # Access billing information
        >>> print(result.billing_metadata)
        {'usage_log_id': 'abc123', 'total_cost': 0.024, 'algorithm_type': 'basic'}
        >>>
        >>> # Use with API key for user identification
        >>> result = quantum_with_billing(
        ...     "Create Bell state",
        ...     backend="ibm_eagle",
        ...     api_key="your_api_key_here"
        ... )
    """
    billing = BillingIntegration(pricing_config, database_url)

    def quantum_with_billing(
        program: str,
        backend: str = 'simulator',
        shots: int = 1024,
        debug: bool = False,
        token: Optional[str] = None,
        instance: Optional[str] = None,
        timeout: int = 3600,
        auto_select: bool = False,
        # Billing-specific parameters
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        # Internal billing control
        _bypass_billing: bool = False
    ) -> BillingResult:
        """
        Execute quantum program with integrated billing and usage tracking.

        This function provides the same interface as the original quantum() function
        but adds comprehensive billing integration including usage tracking, quota
        enforcement, and cost calculation.

        Args:
            program: Natural language description of the quantum program
            backend: Quantum backend to use ('simulator', 'ibm_eagle', etc.)
            shots: Number of measurement shots
            debug: Enable debug mode
            token: IBM Quantum API token
            instance: IBM Quantum instance
            timeout: Job timeout in seconds
            auto_select: Auto-select best backend
            api_key: BioQL API key for user authentication
            user_id: Direct user ID (for internal use)
            session_id: Session ID for grouping operations
            client_ip: Client IP address
            user_agent: Client user agent
            _bypass_billing: Internal flag to bypass billing (for development)

        Returns:
            BillingResult with quantum results and billing metadata
        """
        start_time = time.time()

        # Import the original quantum function
        try:
            from .quantum_connector import quantum, parse_bioql_program, QuantumResult
        except ImportError:
            # Fallback for different import structures
            try:
                from bioql.quantum_connector import quantum, parse_bioql_program, QuantumResult
            except ImportError as e:
                return BillingResult(
                    success=False,
                    error_message=f"Could not import quantum function: {e}"
                )

        # Initialize billing result
        billing_result = BillingResult()
        billing_metadata = {}

        # Skip billing if disabled or bypassed
        if not BILLING_ENABLED or _bypass_billing:
            logger.info("Billing bypassed - executing original quantum function")
            try:
                original_result = quantum(
                    program=program,
                    backend=backend,
                    shots=shots,
                    debug=debug,
                    token=token,
                    instance=instance,
                    timeout=timeout,
                    auto_select=auto_select
                )

                # Convert to BillingResult
                billing_result = BillingResult(
                    counts=original_result.counts,
                    statevector=original_result.statevector,
                    bio_interpretation=original_result.bio_interpretation,
                    metadata=original_result.metadata,
                    success=original_result.success,
                    error_message=original_result.error_message,
                    job_id=original_result.job_id,
                    backend_name=original_result.backend_name,
                    execution_time=original_result.execution_time,
                    queue_time=original_result.queue_time,
                    cost_estimate=original_result.cost_estimate,
                    billing_metadata={'billing_enabled': False, 'reason': 'Billing disabled or bypassed'}
                )

                return billing_result

            except Exception as e:
                return BillingResult(
                    success=False,
                    error_message=str(e),
                    billing_metadata={'billing_enabled': False, 'error': str(e)}
                )

        # Authenticate user
        user_auth = None
        if api_key or user_id:
            user_auth = billing.authenticate_user(api_key=api_key, user_id=user_id)
            if not user_auth:
                return BillingResult(
                    success=False,
                    error_message="Authentication failed. Invalid API key or user ID.",
                    billing_metadata={'authentication_failed': True}
                )

        # Parse circuit for cost estimation and quota checking
        circuit_qubits = 0
        circuit_depth = 0
        circuit_gates = 0

        try:
            circuit = parse_bioql_program(program)
            circuit_qubits = circuit.num_qubits
            circuit_depth = circuit.depth()
            circuit_gates = len(circuit.data)
        except Exception as e:
            logger.warning(f"Could not parse circuit for billing analysis: {e}")

        # Calculate cost estimate
        cost_breakdown = billing.calculate_cost_estimate(
            circuit_qubits, circuit_depth, backend, shots, program
        )
        billing_metadata['cost_breakdown'] = cost_breakdown

        # Check quotas if user is authenticated
        quota_status = {'checked': False}
        if user_auth:
            quota_status = billing.check_quotas(user_auth, shots)
            billing_metadata['quota_status'] = quota_status

            if not quota_status.get('allowed', True):
                return BillingResult(
                    success=False,
                    error_message=f"Quota exceeded: {quota_status.get('reason', 'Unknown quota limit')}",
                    billing_metadata=billing_metadata,
                    quota_status=quota_status,
                    cost_breakdown=cost_breakdown,
                    user_id=user_auth['user_id']
                )

        # Execute the original quantum function
        try:
            logger.info(f"Executing quantum program with billing integration")
            original_result = quantum(
                program=program,
                backend=backend,
                shots=shots,
                debug=debug,
                token=token,
                instance=instance,
                timeout=timeout,
                auto_select=auto_select
            )

            execution_time = time.time() - start_time
            if not original_result.execution_time:
                original_result.execution_time = execution_time

        except Exception as e:
            # Create failed result
            original_result = QuantumResult(
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

        # Log usage if user is authenticated
        usage_log_id = None
        if user_auth:
            client_metadata = {
                'client_ip': client_ip,
                'user_agent': user_agent,
                'session_id': session_id,
                'execution_timestamp': datetime.utcnow().isoformat(),
                'cost_breakdown': cost_breakdown
            }

            usage_log_id = billing.log_usage(
                user_auth=user_auth,
                program_text=program,
                circuit_qubits=circuit_qubits,
                circuit_depth=circuit_depth,
                circuit_gates=circuit_gates,
                backend_requested=backend,
                backend_used=original_result.backend_name or backend,
                shots=shots,
                result=original_result,
                client_metadata=client_metadata
            )

        # Build comprehensive billing metadata
        billing_metadata.update({
            'billing_enabled': True,
            'usage_log_id': usage_log_id,
            'user_authenticated': user_auth is not None,
            'algorithm_type': cost_breakdown.get('algorithm_type', 'basic'),
            'total_cost': cost_breakdown.get('total_cost', 0.0),
            'cost_currency': 'USD',
            'billing_timestamp': datetime.utcnow().isoformat()
        })

        if user_auth:
            billing_metadata.update({
                'user_id': user_auth['user_id'],
                'api_key_id': user_auth.get('api_key_id'),
                'authenticated_via': user_auth['authenticated_via']
            })

        # Create enhanced result
        billing_result = BillingResult(
            counts=original_result.counts,
            statevector=original_result.statevector,
            bio_interpretation=original_result.bio_interpretation,
            metadata=original_result.metadata,
            success=original_result.success,
            error_message=original_result.error_message,
            job_id=original_result.job_id,
            backend_name=original_result.backend_name,
            execution_time=original_result.execution_time,
            queue_time=original_result.queue_time,
            cost_estimate=cost_breakdown.get('total_cost', 0.0),
            # Billing-specific fields
            billing_metadata=billing_metadata,
            usage_log_id=usage_log_id,
            user_id=user_auth['user_id'] if user_auth else None,
            session_id=session_id,
            quota_status=quota_status,
            cost_breakdown=cost_breakdown
        )

        # Add billing info to metadata
        billing_result.metadata['billing'] = billing_metadata

        if debug:
            logger.debug(f"Billing integration completed. Usage logged: {usage_log_id}")
            logger.debug(f"Cost breakdown: {cost_breakdown}")

        return billing_result

    return quantum_with_billing


def quantum_billing_decorator(database_url: Optional[str] = None,
                             pricing_config: Optional[Dict] = None):
    """
    Decorator to add billing functionality to existing quantum functions.

    This decorator can be applied to any function that calls the quantum()
    function to add automatic billing integration.

    Args:
        database_url: Database URL for billing system
        pricing_config: Custom pricing configuration

    Returns:
        Decorator function

    Examples:
        >>> @quantum_billing_decorator()
        >>> def my_quantum_function(program, **kwargs):
        ...     return quantum(program, **kwargs)
        >>>
        >>> # Function now has billing integration
        >>> result = my_quantum_function("Create Bell state", api_key="your_key")
        >>> print(result.billing_metadata)
    """
    billing = BillingIntegration(pricing_config, database_url)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract billing parameters
            api_key = kwargs.pop('api_key', None)
            user_id = kwargs.pop('user_id', None)
            session_id = kwargs.pop('session_id', None)
            client_ip = kwargs.pop('client_ip', None)
            user_agent = kwargs.pop('user_agent', None)

            # Create billing-enabled quantum function
            billing_quantum = create_billing_quantum_function(database_url, pricing_config)

            # Execute with billing
            return billing_quantum(
                *args, **kwargs,
                api_key=api_key,
                user_id=user_id,
                session_id=session_id,
                client_ip=client_ip,
                user_agent=user_agent
            )
        return wrapper
    return decorator


# Convenience function for backward compatibility
def quantum_with_billing(*args, **kwargs) -> BillingResult:
    """
    Direct billing-enabled quantum function for immediate use.

    This is a convenience function that creates a billing integration
    and executes the quantum program in one call.
    """
    billing_quantum = create_billing_quantum_function()
    return billing_quantum(*args, **kwargs)


# Module-level configuration functions
def configure_billing(database_url: Optional[str] = None,
                     pricing_config: Optional[Dict] = None,
                     enabled: Optional[bool] = None) -> Dict[str, Any]:
    """
    Configure billing system settings.

    Args:
        database_url: Database URL for billing system
        pricing_config: Custom pricing configuration
        enabled: Enable/disable billing

    Returns:
        Dictionary with configuration status
    """
    global BILLING_ENABLED, BILLING_DATABASE_URL

    config_status = {
        'success': True,
        'changes': [],
        'current_config': {}
    }

    if enabled is not None:
        BILLING_ENABLED = enabled
        config_status['changes'].append(f"Billing enabled: {enabled}")

    if database_url:
        BILLING_DATABASE_URL = database_url
        config_status['changes'].append(f"Database URL updated")

    if pricing_config:
        try:
            import json
            os.makedirs(os.path.dirname(BILLING_CONFIG_PATH), exist_ok=True)
            with open(BILLING_CONFIG_PATH, 'w') as f:
                json.dump(pricing_config, f, indent=2)
            config_status['changes'].append(f"Pricing config saved to {BILLING_CONFIG_PATH}")
        except Exception as e:
            config_status['success'] = False
            config_status['error'] = f"Failed to save pricing config: {e}"

    config_status['current_config'] = {
        'billing_enabled': BILLING_ENABLED,
        'database_url': BILLING_DATABASE_URL,
        'config_path': BILLING_CONFIG_PATH
    }

    return config_status


def get_billing_status() -> Dict[str, Any]:
    """
    Get current billing system status and configuration.

    Returns:
        Dictionary with billing system status
    """
    status = {
        'billing_enabled': BILLING_ENABLED,
        'database_configured': BILLING_DATABASE_URL is not None,
        'config_file_exists': os.path.exists(BILLING_CONFIG_PATH),
        'dependencies_available': False,
        'bp_pl_available': False
    }

    # Check SQLAlchemy availability
    try:
        import sqlalchemy
        status['dependencies_available'] = True
    except ImportError:
        status['sqlalchemy_missing'] = True

    # Check BP&PL availability
    try:
        from ..BP.services.usage_tracker import UsageTracker
        status['bp_pl_available'] = True
    except ImportError:
        status['bp_pl_missing'] = True

    # Test database connection if configured
    if BILLING_DATABASE_URL and status['dependencies_available']:
        try:
            db_manager = BillingConnectionManager(BILLING_DATABASE_URL)
            session = db_manager.get_session()
            if session:
                status['database_connection'] = True
                db_manager.close_session()
            else:
                status['database_connection'] = False
        except Exception as e:
            status['database_connection'] = False
            status['database_error'] = str(e)

    return status


if __name__ == "__main__":
    # Command-line interface for billing integration
    import argparse

    parser = argparse.ArgumentParser(description='BioQL Billing Integration')
    parser.add_argument('--status', action='store_true', help='Show billing status')
    parser.add_argument('--configure', action='store_true', help='Configure billing')
    parser.add_argument('--database-url', help='Set database URL')
    parser.add_argument('--enable', action='store_true', help='Enable billing')
    parser.add_argument('--disable', action='store_true', help='Disable billing')

    args = parser.parse_args()

    if args.status:
        status = get_billing_status()
        print("\n=== BioQL Billing System Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")

    if args.configure:
        config_changes = {}
        if args.database_url:
            config_changes['database_url'] = args.database_url
        if args.enable:
            config_changes['enabled'] = True
        if args.disable:
            config_changes['enabled'] = False

        if config_changes:
            result = configure_billing(**config_changes)
            print("\n=== Configuration Result ===")
            print(f"Success: {result['success']}")
            for change in result['changes']:
                print(f"- {change}")
        else:
            print("No configuration changes specified.")