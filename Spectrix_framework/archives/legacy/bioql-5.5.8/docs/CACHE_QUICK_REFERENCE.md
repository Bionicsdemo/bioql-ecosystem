# BioQL Circuit Cache - Quick Reference

## Import
```python
from bioql.cache import CircuitCache, CacheKey, get_global_cache
```

## Create Cache
```python
# Custom cache
cache = CircuitCache(max_size=100, ttl_hours=24)

# Global cache (singleton)
cache = get_global_cache()
```

## Basic Operations

### Cache Circuit
```python
key = CacheKey.from_ir(ir_program, "qiskit", 1)
cache.put(key, circuit, {"compile_time_ms": 125})
```

### Retrieve Circuit
```python
cached = cache.get(key)
if cached:
    circuit = cached.circuit
    metadata = cached.metadata
    print(f"Accessed {cached.access_count} times")
```

### Create Key
```python
# From string
key = CacheKey.from_ir("LOAD protein.pdb", "qiskit", 1)

# From BioQL program
key = CacheKey.from_ir(program_object, "qiskit", 2)

# With parameters
key = CacheKey.from_ir(ir, "qiskit", 1, parameters={"p1": 0.5})
```

## Cache Management

### Invalidation
```python
# By pattern
cache.invalidate(r".*:qiskit:.*")

# By backend
cache.invalidate_backend("qiskit")

# All entries
cache.invalidate_all()
```

### Statistics
```python
# Hit rate
hit_rate = cache.get_hit_rate()  # 0.0 to 1.0

# Full stats
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Size: {stats['current_size']}/{stats['max_size']}")
```

### Optimization
```python
report = cache.optimize_cache()
print(f"Removed {report['expired_removed']} expired entries")
print(f"Recommendations: {report['recommendations']}")
```

## Advanced Features

### Cache Warming
```python
circuits = [
    (ir_prog1, circuit1, meta1),
    (ir_prog2, circuit2, meta2),
]
cache.warm_cache(circuits, "qiskit", 1)
```

### Thread Safety
```python
# Cache is automatically thread-safe
import threading

def worker():
    key = CacheKey.from_ir("program", "qiskit", 1)
    cache.put(key, "circuit", {})
    cached = cache.get(key)

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
```

## Common Patterns

### Compilation with Cache
```python
def compile_with_cache(ir_program, backend="qiskit", opt_level=1):
    cache = get_global_cache()
    key = CacheKey.from_ir(ir_program, backend, opt_level)
    
    # Check cache
    cached = cache.get(key)
    if cached:
        return cached.circuit
    
    # Compile and cache
    circuit = compile_circuit(ir_program, backend, opt_level)
    cache.put(key, circuit, {"backend": backend})
    return circuit
```

### Monitor Performance
```python
import time

start = time.time()
result = compile_with_cache(ir_program)
duration = time.time() - start

print(f"Compiled in {duration:.2f}s")
print(f"Cache hit rate: {cache.get_hit_rate():.2%}")
```

### Periodic Optimization
```python
import schedule

def optimize():
    report = cache.optimize_cache()
    print(f"Cache optimized: {report}")

schedule.every(1).hours.do(optimize)
```

## File Locations

- **Implementation**: `/Users/heinzjungbluth/Desktop/bioql/bioql/cache.py`
- **Tests**: `/Users/heinzjungbluth/Desktop/bioql/tests/test_cache.py`
- **Examples**: `/Users/heinzjungbluth/Desktop/bioql/examples/cache_usage_example.py`
- **Full Docs**: `/Users/heinzjungbluth/Desktop/bioql/bioql/CACHE_README.md`

## Troubleshooting

### Low Hit Rate
```python
stats = cache.get_stats()
if stats['hit_rate'] < 0.5:
    # Increase max_size or ttl_hours
    cache = CircuitCache(max_size=200, ttl_hours=48)
```

### High Memory
```python
# Reduce size or TTL
cache = CircuitCache(max_size=50, ttl_hours=6)

# Run optimization
cache.optimize_cache()
```

### Check Cache State
```python
print(cache)  # CircuitCache(size=42/100, hit_rate=87.50%)
info = cache.get_cache_info()
```

## Quick Test
```bash
cd /Users/heinzjungbluth/Desktop/bioql
python bioql/cache.py  # Runs demo
python -m pytest tests/test_cache.py  # Runs tests
```

---
**Version**: 1.0.0 | **Date**: 2025-10-03
