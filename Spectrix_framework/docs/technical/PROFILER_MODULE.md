# BioQL Profiler Module Documentation

## Overview

The BioQL Profiler Module provides comprehensive performance profiling and optimization analysis for quantum operations in BioQL. It features thread-safe context management, stage-based timing analysis, circuit metrics tracking, cost analysis, bottleneck detection, and memory profiling with minimal overhead (<5%).

## Features

- **Thread-Safe Context Management**: Safely profile concurrent quantum operations
- **Stage-Based Timing**: Track performance across different execution stages
- **Circuit Metrics**: Analyze quantum circuit complexity and optimization
- **Cost Tracking**: Monitor and project quantum computing costs
- **Bottleneck Detection**: Automatically identify performance issues with actionable recommendations
- **Memory Profiling**: Track memory usage using Python's tracemalloc
- **Export Capabilities**: Generate reports in JSON and Markdown formats
- **Backend Comparison**: Compare performance across multiple quantum backends
- **Decorator Support**: Easy profiling with `@profile_quantum` decorator

## Installation

The profiler module is included with BioQL. Ensure you have the required dependencies:

```bash
pip install psutil  # For CPU and memory monitoring
```

## Quick Start

### Basic Usage

```python
from bioql.profiler import Profiler, ProfilingMode
from bioql.enhanced_quantum import enhanced_quantum

# Create profiler
profiler = Profiler(mode=ProfilingMode.STANDARD)

# Profile a quantum function
result = profiler.profile_quantum(
    enhanced_quantum,
    program="Create a Bell state and measure",
    api_key="your_api_key",
    backend='simulator',
    shots=1024
)

# Get summary
summary = profiler.get_summary()
print(f"Total Duration: {summary['total_duration']:.3f}s")
print(f"Overhead: {summary['overhead_percentage']:.2f}%")
```

### Using the Decorator

```python
from bioql.profiler import profile_quantum, ProfilingMode

@profile_quantum(
    mode=ProfilingMode.DETAILED,
    export_path='./reports/profile.json',
    export_format='json'
)
def my_quantum_function(program, api_key, **kwargs):
    return enhanced_quantum(program, api_key, **kwargs)

# Call the function - profiling happens automatically
result = my_quantum_function(
    program="Dock ligand to protein",
    api_key="your_api_key"
)
```

## Profiling Modes

### ProfilingMode.MINIMAL
- Basic timing only
- Lowest overhead (~1%)
- Best for production environments

### ProfilingMode.STANDARD (Default)
- Timing + circuit metrics
- Moderate overhead (~2-3%)
- Recommended for most use cases

### ProfilingMode.DETAILED
- Standard + cost analysis
- Higher overhead (~3-4%)
- Best for cost optimization

### ProfilingMode.DEBUG
- All metrics + memory profiling
- Highest overhead (~4-5%)
- Best for debugging performance issues

## API Reference

### Profiler Class

#### Constructor

```python
Profiler(mode: ProfilingMode = ProfilingMode.STANDARD)
```

**Parameters:**
- `mode`: Profiling mode (MINIMAL, STANDARD, DETAILED, or DEBUG)

#### Methods

##### profile_quantum()

```python
profiler.profile_quantum(
    quantum_func: Callable,
    *args,
    extract_metrics: bool = True,
    **kwargs
) -> Dict[str, Any]
```

Profile a quantum function execution.

**Parameters:**
- `quantum_func`: The quantum function to profile
- `*args`: Positional arguments for the function
- `extract_metrics`: Extract circuit metrics from result (default: True)
- `**kwargs`: Keyword arguments for the function

**Returns:**
Dictionary containing:
- `result`: The function result
- `success`: Boolean indicating success
- `error`: Error message if failed
- `profiling`: Profiling summary

##### get_summary()

```python
profiler.get_summary() -> Dict[str, Any]
```

Get comprehensive profiling summary.

**Returns:**
Dictionary containing:
- `mode`: Profiling mode used
- `timestamp`: ISO timestamp
- `total_duration`: Total execution time
- `stages`: Stage-by-stage breakdown
- `circuit_metrics`: Circuit complexity metrics
- `cost_metrics`: Cost analysis
- `bottlenecks`: Detected performance issues
- `overhead_percentage`: Profiling overhead

##### export_report()

```python
profiler.export_report(
    filepath: Union[str, Path],
    format: str = 'json'
) -> None
```

Export profiling report to file.

**Parameters:**
- `filepath`: Path to output file
- `format`: Export format ('json' or 'markdown')

##### compare_backends()

```python
profiler.compare_backends(
    quantum_func: Callable,
    backends: List[str],
    *args,
    **kwargs
) -> Dict[str, Any]
```

Compare performance across multiple backends.

**Parameters:**
- `quantum_func`: The quantum function to profile
- `backends`: List of backend names to compare
- `*args`: Positional arguments
- `**kwargs`: Keyword arguments (backend will be overridden)

**Returns:**
Dictionary containing:
- `backends`: List of backends tested
- `comparison_timestamp`: ISO timestamp
- `results`: Results for each backend
- `winner`: Best backend for different criteria

### ProfilerContext Class

Thread-safe context manager for manual profiling stages.

#### Constructor

```python
ProfilerContext(mode: ProfilingMode = ProfilingMode.STANDARD)
```

#### Methods

##### start_stage()

```python
context.start_stage(
    name: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None
```

Start profiling a new stage.

##### end_stage()

```python
context.end_stage(name: Optional[str] = None) -> StageMetrics
```

End profiling current or specified stage.

##### get_stage()

```python
context.get_stage(name: str) -> Optional[StageMetrics]
```

Get metrics for a specific stage.

#### Example

```python
from bioql.profiler import ProfilerContext, ProfilingMode

with ProfilerContext(mode=ProfilingMode.DEBUG) as ctx:
    ctx.start_stage("data_preparation")
    # ... your code ...
    ctx.end_stage("data_preparation")

    ctx.start_stage("quantum_execution")
    # ... quantum execution ...
    ctx.end_stage("quantum_execution")

    ctx.start_stage("post_processing")
    # ... post-processing ...
    ctx.end_stage("post_processing")

print(f"Total: {ctx.get_total_duration():.3f}s")
```

## Data Classes

### StageMetrics

Metrics for a single profiling stage.

**Fields:**
- `name`: Stage name
- `start_time`: Start timestamp
- `end_time`: End timestamp
- `duration`: Duration in seconds
- `cpu_percent`: CPU usage percentage
- `memory_mb`: Memory usage in MB
- `memory_delta_mb`: Memory change from baseline
- `metadata`: Additional metadata

### CircuitMetrics

Quantum circuit complexity metrics.

**Fields:**
- `qubits`: Number of qubits
- `depth`: Circuit depth
- `gate_count`: Total gate count
- `two_qubit_gates`: Two-qubit gate count
- `single_qubit_gates`: Single-qubit gate count
- `optimization_score`: Circuit optimization score (0-100)
- `backend`: Backend used
- `shots`: Number of shots
- `entanglement_score`: Entanglement complexity
- `parallelism_score`: Gate parallelism score

### CostMetrics

Cost analysis metrics.

**Fields:**
- `total_cost`: Total cost in USD
- `backend_cost`: Backend-specific cost
- `shot_cost`: Cost from shots
- `complexity_cost`: Cost from circuit complexity
- `algorithm_cost`: Cost from algorithm complexity
- `base_cost_per_shot`: Base cost per shot
- `complexity_multiplier`: Complexity multiplier
- `algorithm_multiplier`: Algorithm multiplier
- `shots`: Number of shots
- `projected_monthly_cost`: Projected monthly cost
- `projected_annual_cost`: Projected annual cost
- `cost_per_qubit`: Cost per qubit

### Bottleneck

Detected performance bottleneck.

**Fields:**
- `severity`: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
- `type`: Bottleneck type
- `metric_value`: Current metric value
- `threshold_value`: Threshold that was exceeded
- `impact_percentage`: Estimated performance impact
- `recommendations`: List of recommendations
- `stage`: Stage where detected (optional)

## Bottleneck Types

The profiler detects the following bottleneck types:

### CIRCUIT_DEPTH
**Threshold:** 100
**Recommendations:**
- Consider circuit optimization techniques
- Use gate cancellation and commutation rules
- Apply circuit compilation with optimization level 3
- Consider breaking into smaller subcircuits

### GATE_COUNT
**Threshold:** 500
**Recommendations:**
- Reduce gate count through optimization
- Use native gates for target backend
- Consider alternative algorithm implementations

### QUBIT_COUNT
**Threshold:** 20
**Recommendations:**
- Consider qubit reduction techniques
- Use symmetry to reduce problem size
- Evaluate if all qubits are necessary
- Consider classical preprocessing

### EXECUTION_TIME
**Threshold:** 10.0 seconds
**Recommendations:**
- Consider using a faster backend
- Reduce circuit complexity
- Use caching for repeated executions
- Parallelize independent circuits

### MEMORY_USAGE
**Threshold:** 500 MB
**Recommendations:**
- Reduce shot count if possible
- Process results in batches
- Clear intermediate results
- Use streaming results processing

### COST
**Threshold:** $1.00
**Recommendations:**
- Use simulator for development/testing
- Reduce shot count if accuracy allows
- Optimize circuit to reduce complexity multiplier
- Review projected monthly costs

## Examples

### Example 1: Basic Profiling

```python
from bioql.profiler import Profiler, ProfilingMode
from bioql.enhanced_quantum import enhanced_quantum

profiler = Profiler(mode=ProfilingMode.STANDARD)

result = profiler.profile_quantum(
    enhanced_quantum,
    program="Create Bell state",
    api_key="bioql_your_key",
    backend='simulator',
    shots=1024
)

summary = profiler.get_summary()
print(f"Duration: {summary['total_duration']:.3f}s")
print(f"Overhead: {summary['overhead_percentage']:.2f}%")

# Check for bottlenecks
if summary['bottlenecks']:
    print(f"Found {len(summary['bottlenecks'])} bottlenecks")
    for b in summary['bottlenecks']:
        print(f"  - {b['type']}: {b['severity']}")
```

### Example 2: Detailed Cost Analysis

```python
profiler = Profiler(mode=ProfilingMode.DETAILED)

result = profiler.profile_quantum(
    enhanced_quantum,
    program="Run VQE for H2 molecule",
    api_key="bioql_your_key",
    backend='qiskit',
    shots=2048
)

summary = profiler.get_summary()
cost = summary['cost_metrics']

print(f"Total Cost: ${cost['total_cost']:.4f}")
print(f"Monthly Projection: ${cost['projected_monthly_cost']:.2f}")
print(f"Annual Projection: ${cost['projected_annual_cost']:.2f}")
```

### Example 3: Backend Comparison

```python
profiler = Profiler(mode=ProfilingMode.STANDARD)

comparison = profiler.compare_backends(
    enhanced_quantum,
    backends=['simulator', 'qiskit', 'cirq'],
    program="Create Bell state",
    api_key="bioql_your_key",
    shots=1024
)

print("Winners:")
for criterion, winner in comparison['winner'].items():
    print(f"  {criterion}: {winner}")
```

### Example 4: Export Reports

```python
profiler = Profiler(mode=ProfilingMode.DETAILED)

result = profiler.profile_quantum(
    enhanced_quantum,
    program="Quantum algorithm",
    api_key="bioql_your_key"
)

# Export JSON report
profiler.export_report('./reports/profile.json', format='json')

# Export Markdown report
profiler.export_report('./reports/profile.md', format='markdown')
```

### Example 5: Using the Decorator

```python
from bioql.profiler import profile_quantum, ProfilingMode

@profile_quantum(
    mode=ProfilingMode.DETAILED,
    export_path='./reports/execution.json'
)
def run_quantum_algorithm(program, api_key, **kwargs):
    return enhanced_quantum(program, api_key, **kwargs)

# Automatically profiled
result = run_quantum_algorithm(
    program="Quantum Fourier Transform on 4 qubits",
    api_key="bioql_your_key",
    backend='qiskit',
    shots=2048
)
```

## Integration with BioQL

### With enhanced_quantum()

```python
from bioql.profiler import Profiler, ProfilingMode
from bioql.enhanced_quantum import enhanced_quantum

profiler = Profiler(mode=ProfilingMode.STANDARD)

# Profile enhanced quantum execution
result = profiler.profile_quantum(
    enhanced_quantum,
    program="Dock ligand SMILES 'CCO' to protein PDB 1ABC",
    api_key="bioql_your_key",
    backend='qiskit',
    use_nlp=True,
    return_ir=True
)

# Access both quantum results and profiling data
quantum_result = result['result']
profiling_data = result['profiling']
```

### With simple_billing

The profiler automatically integrates with `bioql.simple_billing` to extract cost metrics:

```python
# Profiler uses these functions from simple_billing:
# - get_backend_cost_per_shot()
# - get_complexity_multiplier()
# - get_algorithm_multiplier()
# - estimate_qubits_from_program()
# - classify_algorithm()
```

## Performance Overhead

The profiler is designed to minimize performance impact:

| Mode | Typical Overhead |
|------|-----------------|
| MINIMAL | ~1% |
| STANDARD | ~2-3% |
| DETAILED | ~3-4% |
| DEBUG | ~4-5% |

The overhead is calculated and reported in the profiling summary:

```python
summary = profiler.get_summary()
print(f"Overhead: {summary['overhead_percentage']:.2f}%")
```

## Best Practices

1. **Use STANDARD mode for most cases**: Provides good balance of detail and overhead

2. **Use DETAILED mode for cost optimization**: Essential for understanding and optimizing costs

3. **Use DEBUG mode sparingly**: Only when diagnosing specific performance issues

4. **Export reports for documentation**: Keep profiling reports for historical analysis

5. **Compare backends regularly**: Different backends may be optimal for different workloads

6. **Act on bottleneck recommendations**: The profiler provides actionable recommendations

7. **Monitor projections**: Use cost projections to plan budgets

8. **Profile in staging first**: Test profiling in non-production environments

## Troubleshooting

### High Overhead

If profiling overhead is too high:
- Switch to MINIMAL mode
- Disable memory tracking
- Profile less frequently
- Use sampling instead of full profiling

### Missing Metrics

If circuit metrics are not captured:
- Ensure the quantum function returns compatible results
- Check that `extract_metrics=True` in `profile_quantum()`
- Verify result has `metadata` attribute

### Export Errors

If export fails:
- Check file path exists and is writable
- Verify format is 'json' or 'markdown'
- Ensure sufficient disk space

## Advanced Usage

### Custom Stages

```python
from bioql.profiler import ProfilerContext, ProfilingMode

with ProfilerContext(mode=ProfilingMode.DEBUG) as ctx:
    ctx.start_stage("custom_preprocessing")
    # Your preprocessing code
    ctx.end_stage("custom_preprocessing")

    ctx.start_stage("custom_execution")
    # Your execution code
    ctx.end_stage("custom_execution")
```

### Extending Bottleneck Detection

```python
# Add custom bottleneck checks
profiler = Profiler(mode=ProfilingMode.STANDARD)

# ... after profiling ...

# Access bottlenecks list
bottlenecks = profiler.bottlenecks

# Add custom bottleneck
from bioql.profiler import Bottleneck, BottleneckSeverity, BottleneckType

custom_bottleneck = Bottleneck(
    severity=BottleneckSeverity.MEDIUM,
    type=BottleneckType.BACKEND_OVERHEAD,
    metric_value=5.0,
    threshold_value=2.0,
    impact_percentage=15.0,
    recommendations=["Use local backend", "Enable caching"]
)

profiler.bottlenecks.append(custom_bottleneck)
```

## License

Copyright (c) 2025 BioQL. All rights reserved.

## Support

For issues, questions, or contributions, please visit:
- GitHub: https://github.com/bioql/bioql
- Documentation: https://bioql.readthedocs.io
- Email: support@bioql.com
