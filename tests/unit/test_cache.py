# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Unit Tests for BioQL Cache Module

Tests the following functionality:
- bioql/cache.py (circuit caching system)
- Cache key generation
- LRU eviction policy
- TTL expiration
- Cache hits and misses
- Memory limits
- Pattern-based invalidation

All tests use mocking to avoid external dependencies.
"""

# Add project to path
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Spectrix_framework"))

from bioql.cache import (
    CachedCircuit,
    CacheKey,
    CacheStats,
    CircuitCache,
    get_global_cache,
    reset_global_cache,
)

# ============================================================================
# CACHE KEY TESTS
# ============================================================================


class TestCacheKey:
    """Test suite for cache key generation and comparison."""

    def test_cache_key_creation(self):
        """Test basic cache key creation."""
        key = CacheKey(
            program_fingerprint="abc123",
            backend_target="qiskit",
            optimization_level=1,
            parameters_hash="params1",
        )

        assert key.program_fingerprint == "abc123"
        assert key.backend_target == "qiskit"
        assert key.optimization_level == 1
        assert key.parameters_hash == "params1"

    def test_cache_key_equality(self):
        """Test cache key equality comparison."""
        key1 = CacheKey("abc", "qiskit", 1, "params")
        key2 = CacheKey("abc", "qiskit", 1, "params")
        key3 = CacheKey("xyz", "qiskit", 1, "params")

        assert key1 == key2
        assert key1 != key3

    def test_cache_key_hashing(self):
        """Test cache key can be used as dict key."""
        key1 = CacheKey("abc", "qiskit", 1, "params")
        key2 = CacheKey("abc", "qiskit", 1, "params")

        cache_dict = {key1: "value"}
        assert cache_dict[key2] == "value"

    def test_cache_key_from_ir_string(self):
        """Test cache key creation from IR string."""
        ir_program = "OPENQASM 2.0; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1];"

        key = CacheKey.from_ir(ir_program, "qiskit", 1)

        assert len(key.program_fingerprint) == 64  # SHA-256 hex digest
        assert key.backend_target == "qiskit"
        assert key.optimization_level == 1

    def test_cache_key_from_ir_dict(self):
        """Test cache key creation from IR dictionary."""
        ir_program = {"gates": ["h", "cx"], "qubits": 2}

        key = CacheKey.from_ir(ir_program, "cirq", 2)

        assert key.backend_target == "cirq"
        assert key.optimization_level == 2

    def test_cache_key_with_parameters(self):
        """Test cache key includes parameters in hash."""
        ir_program = "test_circuit"
        params1 = {"theta": 0.5, "phi": 1.0}
        params2 = {"theta": 0.6, "phi": 1.0}

        key1 = CacheKey.from_ir(ir_program, "qiskit", 1, params1)
        key2 = CacheKey.from_ir(ir_program, "qiskit", 1, params2)

        assert key1 != key2  # Different parameters -> different keys

    def test_cache_key_to_string(self):
        """Test cache key string representation."""
        key = CacheKey("abc123", "qiskit", 1, "params1")
        key_str = key.to_string()

        assert "abc123" in key_str
        assert "qiskit" in key_str
        assert "1" in key_str
        assert "params1" in key_str


# ============================================================================
# CACHED CIRCUIT TESTS
# ============================================================================


class TestCachedCircuit:
    """Test suite for cached circuit metadata."""

    def test_cached_circuit_creation(self):
        """Test cached circuit creation."""
        mock_circuit = MagicMock()
        cached = CachedCircuit(circuit=mock_circuit, metadata={"backend": "qiskit"})

        assert cached.circuit == mock_circuit
        assert cached.metadata["backend"] == "qiskit"
        assert cached.access_count == 0

    def test_record_access(self):
        """Test access recording."""
        cached = CachedCircuit(circuit="mock_circuit")

        cached.record_access()
        assert cached.access_count == 1

        cached.record_access()
        assert cached.access_count == 2

    def test_age_calculation(self):
        """Test age calculation."""
        cached = CachedCircuit(circuit="mock_circuit")
        time.sleep(0.1)

        age = cached.age_seconds()
        assert age >= 0.1

    def test_time_since_access(self):
        """Test time since last access."""
        cached = CachedCircuit(circuit="mock_circuit")
        cached.record_access()
        time.sleep(0.1)

        time_since = cached.time_since_access_seconds()
        assert time_since >= 0.1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        mock_circuit = MagicMock()
        mock_circuit.num_qubits = 3
        mock_circuit.depth.return_value = 5
        mock_circuit.data = [1, 2, 3]

        cached = CachedCircuit(circuit=mock_circuit)
        cached.record_access()

        data = cached.to_dict()

        assert data["access_count"] == 1
        assert "created_at" in data
        assert "circuit_info" in data


# ============================================================================
# CACHE STATS TESTS
# ============================================================================


class TestCacheStats:
    """Test suite for cache statistics."""

    def test_cache_stats_initialization(self):
        """Test cache stats initialization."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats()
        stats.hits = 75
        stats.misses = 25

        assert stats.hit_rate() == 0.75
        assert stats.miss_rate() == 0.25

    def test_hit_rate_with_no_requests(self):
        """Test hit rate with no requests."""
        stats = CacheStats()

        assert stats.hit_rate() == 0.0
        assert stats.miss_rate() == 1.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = CacheStats(hits=80, misses=20, evictions=5)
        data = stats.to_dict()

        assert data["hits"] == 80
        assert data["misses"] == 20
        assert data["hit_rate"] == 0.8


# ============================================================================
# CIRCUIT CACHE TESTS
# ============================================================================


class TestCircuitCache:
    """Test suite for the main circuit cache."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = CircuitCache(max_size=50, ttl_hours=12)

        assert cache.max_size == 50
        assert cache.ttl_seconds == 12 * 3600
        assert len(cache) == 0

    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        cache = CircuitCache(max_size=10)
        key = CacheKey("test", "qiskit", 1, "params")

        cache.put(key, "test_circuit", {"info": "test"})
        cached = cache.get(key)

        assert cached is not None
        assert cached.circuit == "test_circuit"
        assert cached.metadata["info"] == "test"

    def test_cache_miss(self):
        """Test cache miss."""
        cache = CircuitCache()
        key = CacheKey("nonexistent", "qiskit", 1, "params")

        cached = cache.get(key)

        assert cached is None
        assert cache._stats.misses == 1

    def test_cache_hit_increments_access(self):
        """Test cache hit increments access count."""
        cache = CircuitCache()
        key = CacheKey("test", "qiskit", 1, "params")

        cache.put(key, "circuit")
        cache.get(key)
        cache.get(key)

        cached = cache.get(key)
        assert cached.access_count == 3
        assert cache._stats.hits == 3

    def test_lru_eviction(self):
        """Test LRU eviction policy."""
        cache = CircuitCache(max_size=3)

        # Add 4 items to trigger eviction
        key1 = CacheKey("prog1", "qiskit", 1, "p1")
        key2 = CacheKey("prog2", "qiskit", 1, "p2")
        key3 = CacheKey("prog3", "qiskit", 1, "p3")
        key4 = CacheKey("prog4", "qiskit", 1, "p4")

        cache.put(key1, "circuit1")
        cache.put(key2, "circuit2")
        cache.put(key3, "circuit3")
        cache.put(key4, "circuit4")  # Should evict key1

        assert len(cache) == 3
        assert cache.get(key1) is None  # Evicted
        assert cache.get(key2) is not None
        assert cache._stats.evictions == 1

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = CircuitCache(max_size=10, ttl_hours=0.0001)  # Very short TTL
        key = CacheKey("test", "qiskit", 1, "params")

        cache.put(key, "circuit")
        time.sleep(0.5)  # Wait for expiration

        cached = cache.get(key)
        assert cached is None
        assert cache._stats.expirations >= 1

    def test_invalidate_pattern(self):
        """Test pattern-based invalidation."""
        cache = CircuitCache()

        key1 = CacheKey("prog1", "qiskit", 1, "p1")
        key2 = CacheKey("prog2", "qiskit", 2, "p2")
        key3 = CacheKey("prog3", "cirq", 1, "p3")

        cache.put(key1, "circuit1")
        cache.put(key2, "circuit2")
        cache.put(key3, "circuit3")

        # Invalidate all qiskit circuits
        invalidated = cache.invalidate_backend("qiskit")

        assert invalidated == 2
        assert len(cache) == 1
        assert cache.get(key3) is not None

    def test_invalidate_all(self):
        """Test clearing entire cache."""
        cache = CircuitCache()

        for i in range(5):
            key = CacheKey(f"prog{i}", "qiskit", 1, f"p{i}")
            cache.put(key, f"circuit{i}")

        invalidated = cache.invalidate_all()

        assert invalidated == 5
        assert len(cache) == 0

    def test_get_hit_rate(self):
        """Test getting cache hit rate."""
        cache = CircuitCache()
        key = CacheKey("test", "qiskit", 1, "params")

        cache.put(key, "circuit")
        cache.get(key)  # Hit
        cache.get(CacheKey("miss", "qiskit", 1, "p"))  # Miss

        hit_rate = cache.get_hit_rate()
        assert hit_rate == 0.5

    def test_optimize_cache(self):
        """Test cache optimization."""
        cache = CircuitCache(max_size=10, ttl_hours=0.0001)

        # Add some circuits
        for i in range(5):
            key = CacheKey(f"prog{i}", "qiskit", 1, f"p{i}")
            cache.put(key, f"circuit{i}")

        time.sleep(0.5)  # Wait for expiration

        report = cache.optimize_cache()

        assert "expired_removed" in report
        assert report["expired_removed"] >= 0

    def test_warm_cache(self):
        """Test cache warming."""
        cache = CircuitCache()

        circuits = [
            ("prog1", "circuit1", {"info": "test1"}),
            ("prog2", "circuit2", {"info": "test2"}),
        ]

        count = cache.warm_cache(circuits, "qiskit", 1)

        assert count == 2
        assert len(cache) == 2

    def test_thread_safety(self):
        """Test thread-safe operations."""
        cache = CircuitCache(max_size=100)
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    key = CacheKey(f"prog_{thread_id}_{i}", "qiskit", 1, "params")
                    cache.put(key, f"circuit_{thread_id}_{i}")
                    cached = cache.get(key)
                    assert cached is not None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(cache) >= 10

    def test_contains(self):
        """Test __contains__ operator."""
        cache = CircuitCache()
        key = CacheKey("test", "qiskit", 1, "params")

        assert key not in cache

        cache.put(key, "circuit")

        assert key in cache

    def test_repr(self):
        """Test string representation."""
        cache = CircuitCache(max_size=10)
        key = CacheKey("test", "qiskit", 1, "params")
        cache.put(key, "circuit")
        cache.get(key)

        repr_str = repr(cache)

        assert "CircuitCache" in repr_str
        assert "1/10" in repr_str


# ============================================================================
# GLOBAL CACHE TESTS
# ============================================================================


class TestGlobalCache:
    """Test suite for global cache management."""

    def test_get_global_cache(self):
        """Test getting global cache instance."""
        reset_global_cache()
        cache = get_global_cache()

        assert cache is not None
        assert isinstance(cache, CircuitCache)

    def test_global_cache_singleton(self):
        """Test global cache is singleton."""
        reset_global_cache()
        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2

    def test_reset_global_cache(self):
        """Test resetting global cache."""
        cache1 = get_global_cache()
        reset_global_cache()
        cache2 = get_global_cache()

        assert cache1 is not cache2


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestCacheErrorHandling:
    """Test suite for cache error handling."""

    def test_cache_with_disabled_stats(self):
        """Test cache with statistics disabled."""
        cache = CircuitCache(enable_stats=False)
        key = CacheKey("test", "qiskit", 1, "params")

        cache.put(key, "circuit")
        cache.get(key)

        hit_rate = cache.get_hit_rate()
        assert hit_rate == 0.0

    def test_export_circuit_not_found(self):
        """Test exporting non-existent circuit."""
        cache = CircuitCache()
        key = CacheKey("nonexistent", "qiskit", 1, "params")

        result = cache.export_circuit(key)

        assert result is None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
