#!/usr/bin/env python3
"""
BioQL Circuit Cache Module

This module provides comprehensive caching for compiled quantum circuits with:
- L1 (in-memory) caching with LRU eviction
- TTL-based expiration
- Thread-safe operations
- Cache statistics and optimization
- Parameterized circuit support
- Integration with existing quantum_connector.py
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Pattern, List, Union
import re
import logging

try:
    from qiskit import QuantumCircuit
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    # Dummy class for type hints
    class QuantumCircuit:
        pass

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CacheKey:
    """
    Unique key for identifying cached circuits.

    Attributes:
        program_fingerprint: Hash of the IR program
        backend_target: Target backend (qiskit, cirq, etc.)
        optimization_level: Optimization level (0-3)
        parameters_hash: Hash of circuit parameters
    """
    program_fingerprint: str
    backend_target: str
    optimization_level: int
    parameters_hash: str

    def __hash__(self) -> int:
        """Generate hash for use as dictionary key."""
        return hash((
            self.program_fingerprint,
            self.backend_target,
            self.optimization_level,
            self.parameters_hash
        ))

    def __eq__(self, other) -> bool:
        """Check equality with another CacheKey."""
        if not isinstance(other, CacheKey):
            return False
        return (
            self.program_fingerprint == other.program_fingerprint and
            self.backend_target == other.backend_target and
            self.optimization_level == other.optimization_level and
            self.parameters_hash == other.parameters_hash
        )

    def __str__(self) -> str:
        """String representation."""
        return f"CacheKey({self.program_fingerprint[:8]}..., {self.backend_target}, opt={self.optimization_level})"

    def to_string(self) -> str:
        """Convert to string for pattern matching."""
        return f"{self.program_fingerprint}:{self.backend_target}:{self.optimization_level}:{self.parameters_hash}"

    @classmethod
    def from_ir(
        cls,
        ir_program: Union[str, Dict[str, Any], Any],
        backend_target: str = "qiskit",
        optimization_level: int = 1,
        parameters: Optional[Dict[str, Any]] = None
    ) -> 'CacheKey':
        """
        Create cache key from IR program.

        Args:
            ir_program: IR program (string, dict, or BioQLProgram object)
            backend_target: Target backend
            optimization_level: Optimization level
            parameters: Circuit parameters

        Returns:
            CacheKey instance
        """
        # Convert IR to string for hashing
        if isinstance(ir_program, str):
            ir_str = ir_program
        elif isinstance(ir_program, dict):
            ir_str = json.dumps(ir_program, sort_keys=True)
        elif hasattr(ir_program, 'to_json'):
            # BioQLProgram object
            ir_str = ir_program.to_json()
        else:
            ir_str = str(ir_program)

        # Generate program fingerprint
        program_fingerprint = hashlib.sha256(ir_str.encode()).hexdigest()

        # Generate parameters hash
        if parameters:
            params_str = json.dumps(parameters, sort_keys=True)
            parameters_hash = hashlib.md5(params_str.encode()).hexdigest()
        else:
            parameters_hash = "no_params"

        return cls(
            program_fingerprint=program_fingerprint,
            backend_target=backend_target,
            optimization_level=optimization_level,
            parameters_hash=parameters_hash
        )


@dataclass
class CachedCircuit:
    """
    Cached quantum circuit with metadata.

    Attributes:
        circuit: The quantum circuit object
        metadata: Additional metadata about the circuit
        created_at: When the circuit was cached
        access_count: Number of times accessed
        last_accessed: Last access timestamp
    """
    circuit: Any  # QuantumCircuit or similar
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def record_access(self) -> None:
        """Record an access to this cached circuit."""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def age_seconds(self) -> float:
        """Get age of cached circuit in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    def time_since_access_seconds(self) -> float:
        """Get time since last access in seconds."""
        return (datetime.now() - self.last_accessed).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat(),
            'age_seconds': self.age_seconds(),
            'circuit_info': {
                'num_qubits': getattr(self.circuit, 'num_qubits', None),
                'depth': getattr(self.circuit, 'depth', lambda: None)(),
                'num_gates': len(getattr(self.circuit, 'data', []))
            }
        }


@dataclass
class CacheStats:
    """Statistics for cache performance tracking."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0
    total_size: int = 0

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'expirations': self.expirations,
            'invalidations': self.invalidations,
            'total_size': self.total_size,
            'hit_rate': self.hit_rate(),
            'miss_rate': self.miss_rate()
        }


class CircuitCache:
    """
    Thread-safe LRU cache for compiled quantum circuits.

    Features:
    - L1 (in-memory) caching with LRU eviction
    - TTL-based expiration (default 24 hours)
    - Configurable max_size (default 100)
    - Thread-safe operations using threading.Lock
    - Cache statistics tracking
    - Parameterized circuit support
    - Pattern-based invalidation
    - Cache warming capability

    Example:
        >>> cache = CircuitCache(max_size=100, ttl_hours=24)
        >>> key = CacheKey.from_ir(ir_program, "qiskit", 1)
        >>> cache.put(key, circuit, {"backend": "qiskit"})
        >>> cached = cache.get(key)
        >>> print(cache.get_hit_rate())
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_hours: float = 24.0,
        enable_stats: bool = True
    ):
        """
        Initialize circuit cache.

        Args:
            max_size: Maximum number of circuits to cache
            ttl_hours: Time-to-live for cached circuits in hours
            enable_stats: Whether to track cache statistics
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self.enable_stats = enable_stats

        # Use OrderedDict for LRU implementation
        self._cache: OrderedDict[CacheKey, CachedCircuit] = OrderedDict()

        # Thread safety
        self._lock = threading.Lock()

        # Statistics
        self._stats = CacheStats()

        logger.info(
            f"Initialized CircuitCache: max_size={max_size}, "
            f"ttl_hours={ttl_hours}, stats={enable_stats}"
        )

    def get(self, key: CacheKey) -> Optional[CachedCircuit]:
        """
        Get cached circuit by key.

        Args:
            key: Cache key

        Returns:
            CachedCircuit if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                if self.enable_stats:
                    self._stats.misses += 1
                logger.debug(f"Cache miss: {key}")
                return None

            cached = self._cache[key]

            # Check expiration
            if cached.age_seconds() > self.ttl_seconds:
                logger.debug(f"Cache entry expired: {key}")
                del self._cache[key]
                if self.enable_stats:
                    self._stats.misses += 1
                    self._stats.expirations += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            # Record access
            cached.record_access()

            if self.enable_stats:
                self._stats.hits += 1

            logger.debug(f"Cache hit: {key} (accessed {cached.access_count} times)")
            return cached

    def put(
        self,
        key: CacheKey,
        circuit: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store circuit in cache.

        Args:
            key: Cache key
            circuit: Quantum circuit to cache
            metadata: Additional metadata
        """
        with self._lock:
            # Check if we need to evict
            if len(self._cache) >= self.max_size and key not in self._cache:
                # Remove least recently used (first item)
                evicted_key, evicted_circuit = self._cache.popitem(last=False)
                if self.enable_stats:
                    self._stats.evictions += 1
                logger.debug(f"Evicted LRU entry: {evicted_key}")

            # Create cached circuit
            cached = CachedCircuit(
                circuit=circuit,
                metadata=metadata or {},
                created_at=datetime.now(),
                access_count=0,
                last_accessed=datetime.now()
            )

            # Store in cache (at end, most recently used)
            self._cache[key] = cached
            self._cache.move_to_end(key)

            if self.enable_stats:
                self._stats.total_size = len(self._cache)

            logger.debug(f"Cached circuit: {key} (size={len(self._cache)})")

    def invalidate(self, pattern: Union[str, Pattern]) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: String pattern or compiled regex

        Returns:
            Number of invalidated entries
        """
        if isinstance(pattern, str):
            # Convert string to regex pattern
            regex = re.compile(pattern)
        else:
            regex = pattern

        with self._lock:
            keys_to_remove = []

            for key in self._cache.keys():
                key_str = key.to_string()
                if regex.search(key_str):
                    keys_to_remove.append(key)

            # Remove matching keys
            for key in keys_to_remove:
                del self._cache[key]
                if self.enable_stats:
                    self._stats.invalidations += 1

            if self.enable_stats:
                self._stats.total_size = len(self._cache)

            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching: {pattern}")

            return len(keys_to_remove)

    def invalidate_backend(self, backend: str) -> int:
        """
        Invalidate all entries for a specific backend.

        Args:
            backend: Backend name

        Returns:
            Number of invalidated entries
        """
        pattern = f".*:{backend}:.*"
        return self.invalidate(pattern)

    def invalidate_all(self) -> int:
        """
        Clear entire cache.

        Returns:
            Number of invalidated entries
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            if self.enable_stats:
                self._stats.invalidations += count
                self._stats.total_size = 0
            logger.info(f"Invalidated all {count} cache entries")
            return count

    def get_hit_rate(self) -> float:
        """
        Get cache hit rate.

        Returns:
            Hit rate as a float between 0 and 1
        """
        if not self.enable_stats:
            logger.warning("Statistics not enabled for this cache")
            return 0.0
        return self._stats.hit_rate()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enable_stats:
            return {'error': 'Statistics not enabled'}

        with self._lock:
            return {
                **self._stats.to_dict(),
                'max_size': self.max_size,
                'current_size': len(self._cache),
                'ttl_hours': self.ttl_seconds / 3600,
                'utilization': len(self._cache) / self.max_size if self.max_size > 0 else 0
            }

    def optimize_cache(self) -> Dict[str, Any]:
        """
        Optimize cache by removing expired entries and analyzing performance.

        Returns:
            Dictionary with optimization report
        """
        with self._lock:
            initial_size = len(self._cache)
            expired_keys = []

            # Find expired entries
            for key, cached in self._cache.items():
                if cached.age_seconds() > self.ttl_seconds:
                    expired_keys.append(key)

            # Remove expired entries
            for key in expired_keys:
                del self._cache[key]
                if self.enable_stats:
                    self._stats.expirations += 1

            # Analyze access patterns
            access_counts = [cached.access_count for cached in self._cache.values()]
            avg_access = sum(access_counts) / len(access_counts) if access_counts else 0

            # Identify cold entries (rarely accessed)
            cold_threshold = avg_access * 0.1  # Less than 10% of average
            cold_entries = sum(1 for count in access_counts if count < cold_threshold)

            report = {
                'initial_size': initial_size,
                'final_size': len(self._cache),
                'expired_removed': len(expired_keys),
                'cold_entries': cold_entries,
                'avg_access_count': avg_access,
                'hit_rate': self._stats.hit_rate(),
                'recommendations': []
            }

            # Add recommendations
            if len(self._cache) > self.max_size * 0.9:
                report['recommendations'].append('Cache is near capacity, consider increasing max_size')

            if self._stats.hit_rate() < 0.5:
                report['recommendations'].append('Low hit rate, consider increasing TTL or cache size')

            if cold_entries > len(self._cache) * 0.5:
                report['recommendations'].append('Many cold entries, consider reducing cache size or TTL')

            if self.enable_stats:
                self._stats.total_size = len(self._cache)

            logger.info(f"Cache optimization complete: {report}")
            return report

    def warm_cache(
        self,
        circuits: List[tuple],
        backend_target: str = "qiskit",
        optimization_level: int = 1
    ) -> int:
        """
        Pre-populate cache with circuits.

        Args:
            circuits: List of (ir_program, circuit, metadata) tuples
            backend_target: Target backend
            optimization_level: Optimization level

        Returns:
            Number of circuits added to cache
        """
        count = 0
        for ir_program, circuit, metadata in circuits:
            try:
                key = CacheKey.from_ir(ir_program, backend_target, optimization_level)
                self.put(key, circuit, metadata)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache with circuit: {e}")

        logger.info(f"Warmed cache with {count} circuits")
        return count

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.

        Returns:
            Dictionary with cache details
        """
        with self._lock:
            entries = []
            for key, cached in list(self._cache.items()):
                entries.append({
                    'key': str(key),
                    'backend': key.backend_target,
                    'optimization_level': key.optimization_level,
                    'age_seconds': cached.age_seconds(),
                    'access_count': cached.access_count,
                    'time_since_access': cached.time_since_access_seconds(),
                    **cached.to_dict()
                })

            return {
                'stats': self.get_stats(),
                'entries': entries,
                'size': len(self._cache),
                'max_size': self.max_size
            }

    def export_circuit(self, key: CacheKey, format: str = "qasm") -> Optional[str]:
        """
        Export cached circuit in specified format.

        Args:
            key: Cache key
            format: Export format (qasm, json, etc.)

        Returns:
            Exported circuit string or None if not found
        """
        cached = self.get(key)
        if cached is None:
            return None

        circuit = cached.circuit

        # Handle Qiskit circuits
        if QISKIT_AVAILABLE and isinstance(circuit, QuantumCircuit):
            if format == "qasm":
                return circuit.qasm()
            elif format == "json":
                # Return circuit info as JSON
                return json.dumps({
                    'num_qubits': circuit.num_qubits,
                    'depth': circuit.depth(),
                    'num_gates': len(circuit.data),
                    'operations': [
                        {
                            'name': instr.operation.name,
                            'qubits': [q.index for q in instr.qubits]
                        }
                        for instr in circuit.data
                    ]
                }, indent=2)

        # Fallback to string representation
        return str(circuit)

    def __len__(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: CacheKey) -> bool:
        """Check if key is in cache."""
        with self._lock:
            return key in self._cache

    def __repr__(self) -> str:
        """String representation."""
        return f"CircuitCache(size={len(self._cache)}/{self.max_size}, hit_rate={self.get_hit_rate():.2%})"


# Global circuit cache instance for easy access
_global_cache: Optional[CircuitCache] = None


def get_global_cache(
    max_size: int = 100,
    ttl_hours: float = 24.0
) -> CircuitCache:
    """
    Get or create global circuit cache instance.

    Args:
        max_size: Maximum cache size
        ttl_hours: Time-to-live in hours

    Returns:
        Global CircuitCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = CircuitCache(max_size=max_size, ttl_hours=ttl_hours)
        logger.info("Created global circuit cache")

    return _global_cache


def reset_global_cache() -> None:
    """Reset the global cache instance."""
    global _global_cache
    _global_cache = None
    logger.info("Reset global circuit cache")


# Integration with quantum_connector.py
def integrate_with_quantum_connector():
    """
    Integrate this cache with the existing quantum_connector CircuitCache.

    This function patches the quantum_connector module to use this enhanced cache.
    """
    try:
        from . import quantum_connector

        # Replace the global cache in quantum_connector
        global_cache = get_global_cache()

        # Create wrapper for backward compatibility
        class CompatibilityWrapper:
            def __init__(self, cache: CircuitCache):
                self._cache = cache

            def get(self, circuit, shots: int, backend: str, max_age_hours: int = 24):
                """Backward compatible get method."""
                # Create key from circuit
                circuit_str = str(circuit) if hasattr(circuit, '__str__') else ''
                key = CacheKey(
                    program_fingerprint=hashlib.sha256(circuit_str.encode()).hexdigest(),
                    backend_target=backend,
                    optimization_level=1,
                    parameters_hash=f"shots_{shots}"
                )

                cached = self._cache.get(key)
                return cached.circuit if cached else None

            def put(self, circuit, shots: int, backend: str, result):
                """Backward compatible put method."""
                circuit_str = str(circuit) if hasattr(circuit, '__str__') else ''
                key = CacheKey(
                    program_fingerprint=hashlib.sha256(circuit_str.encode()).hexdigest(),
                    backend_target=backend,
                    optimization_level=1,
                    parameters_hash=f"shots_{shots}"
                )

                self._cache.put(key, result, {'shots': shots, 'backend': backend})

        # Replace the global cache
        quantum_connector._circuit_cache = CompatibilityWrapper(global_cache)
        logger.info("Successfully integrated with quantum_connector module")

        return True

    except ImportError as e:
        logger.warning(f"Could not integrate with quantum_connector: {e}")
        return False


# Export main classes
__all__ = [
    'CacheKey',
    'CachedCircuit',
    'CacheStats',
    'CircuitCache',
    'get_global_cache',
    'reset_global_cache',
    'integrate_with_quantum_connector'
]


if __name__ == '__main__':
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    print("=== BioQL Circuit Cache Demo ===\n")

    # Create cache
    cache = CircuitCache(max_size=10, ttl_hours=1)
    print(f"Created cache: {cache}\n")

    # Simulate caching circuits
    for i in range(15):
        key = CacheKey(
            program_fingerprint=f"program_{i}",
            backend_target="qiskit",
            optimization_level=1,
            parameters_hash="params_1"
        )
        cache.put(key, f"circuit_{i}", {"iteration": i})

    print(f"After adding 15 circuits: {cache}")
    print(f"Cache stats: {cache.get_stats()}\n")

    # Test retrieval
    key = CacheKey(
        program_fingerprint="program_10",
        backend_target="qiskit",
        optimization_level=1,
        parameters_hash="params_1"
    )

    result = cache.get(key)
    print(f"Retrieved: {result}\n")

    # Test invalidation
    invalidated = cache.invalidate_backend("qiskit")
    print(f"Invalidated {invalidated} entries\n")

    print(f"Final cache: {cache}")
    print(f"Final stats: {cache.get_stats()}")
