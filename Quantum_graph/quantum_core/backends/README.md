# Quantum Executor Module - Integration Documentation

## Overview

This module provides production-ready quantum execution infrastructure for the Quantum_graph system, integrating the existing BioQL quantum connector with support for multiple quantum computing backends.

## Created Files

### 1. `quantum_executor.py` (Main Execution Module)
**Location**: `/Users/heinzjungbluth/Desktop/Quantum_graph/quantum_core/backends/quantum_executor.py`

**Purpose**: Unified interface for executing quantum circuits across multiple backends

**Key Classes**:
- `QuantumExecutor`: Main executor class
- `QuantumExecutionResult`: Standardized result container
- `BackendType`: Enum for supported backends
- `BackendConfig`: Configuration dataclass

**Supported Backends**:
- **IBM Torino** (133 qubits, $3.00/shot) - Real quantum hardware
- **IBM Brisbane** (127 qubits, $1.25/shot) - Real quantum hardware
- **IonQ Simulator** (29 qubits, $0.01/shot) - Cloud simulator
- **IonQ Forte** (36 qubits, $3.00/shot) - Trapped-ion quantum computer
- **AWS SV1** (34 qubits, $0.01/shot) - State vector simulator
- **Qiskit Simulator** (32 qubits, free) - Local simulator

### 2. `circuit_builder.py` (Circuit Generation Module)
**Location**: `/Users/heinzjungbluth/Desktop/Quantum_graph/quantum_core/backends/circuit_builder.py`

**Purpose**: Convert molecular complexity data to quantum circuits

**Key Classes**:
- `MolecularCircuitBuilder`: Circuit builder for molecular data
- `MolecularData`: Data structure for molecular information

**Supported Molecule Types**:
- **protein**: Protein folding and structure (8 qubits base)
- **drug**: Drug-target binding (6 qubits base)
- **metabolomics**: Metabolic pathway analysis (10 qubits base)
- **antibody**: Antibody-antigen interactions (12 qubits base)

**Ansatz Types**:
- TwoLocal (protein, antibody)
- EfficientSU2 (drug)
- RealAmplitudes (metabolomics)

### 3. `__init__.py` (Module Exports)
**Location**: `/Users/heinzjungbluth/Desktop/Quantum_graph/quantum_core/backends/__init__.py`

Exposes all public APIs for easy importing.

### 4. `test_quantum_integration.py` (Test Suite)
**Location**: `/Users/heinzjungbluth/Desktop/Quantum_graph/quantum_core/backends/test_quantum_integration.py`

Comprehensive integration tests covering all functionality.

## Key Methods

### QuantumExecutor

#### `execute_circuit(circuit, backend, shots=1024, job_id=None)`
Execute a quantum circuit on specified backend.

**Parameters**:
- `circuit`: QuantumCircuit or BraketCircuit
- `backend`: BackendType enum value
- `shots`: Number of measurement shots (default: 1024)
- `job_id`: Optional job identifier

**Returns**: `QuantumExecutionResult` with counts, timing, and cost

**Example**:
```python
from quantum_executor import QuantumExecutor, BackendType
from circuit_builder import build_molecular_circuit

executor = QuantumExecutor()
circuit = build_molecular_circuit(4, 'drug', 0.5)
result = executor.execute_circuit(circuit, BackendType.IONQ_SIMULATOR, shots=1024)

print(f"Cost: ${result.cost:.2f}")
print(f"Most likely outcome: {result.most_likely_outcome}")
```

#### `estimate_cost(backend, shots)`
Estimate execution cost before running.

**Example**:
```python
cost = executor.estimate_cost(BackendType.IBM_TORINO, shots=2048)
print(f"Estimated cost: ${cost:.2f}")  # Output: $6144.00
```

#### `list_backends()`
List all available backends with configurations.

#### `get_backend_info(backend)`
Get detailed information about a specific backend.

### MolecularCircuitBuilder

#### `build_circuit(mol_data, custom_qubits=None, custom_depth=None)`
Build quantum circuit from molecular data.

**Parameters**:
- `mol_data`: MolecularData object
- `custom_qubits`: Override default qubit count
- `custom_depth`: Override default circuit depth

**Returns**: Parameterized QuantumCircuit

**Example**:
```python
from circuit_builder import MolecularCircuitBuilder, MolecularData

mol_data = MolecularData(
    molecule_type='protein',
    complexity=0.7,
    num_atoms=24,
    num_bonds=26
)

builder = MolecularCircuitBuilder()
circuit = builder.build_circuit(mol_data)
```

#### `build_from_complexity(molecule_type, complexity, num_qubits=None)`
Convenience method to build from basic complexity score.

**Example**:
```python
circuit = builder.build_from_complexity('protein', 0.65, num_qubits=8)
```

### Convenience Functions

#### `execute_on_backend(circuit, backend, shots)`
Quick execution without creating executor instance.

```python
from quantum_executor import execute_on_backend, BackendType
from circuit_builder import create_protein_circuit

circuit = create_protein_circuit(num_residues=20, folding_complexity=0.8)
result = execute_on_backend(circuit, BackendType.QISKIT_SIMULATOR)
```

#### `build_molecular_circuit(num_qubits, molecule_type, complexity)`
Quick circuit creation.

```python
from circuit_builder import build_molecular_circuit

circuit = build_molecular_circuit(6, 'drug', 0.4)
```

#### `create_protein_circuit(num_residues, folding_complexity)`
Create protein-specific circuit.

```python
circuit = create_protein_circuit(num_residues=30, folding_complexity=0.75)
```

#### `create_drug_circuit(molecular_weight, binding_affinity)`
Create drug-specific circuit.

```python
circuit = create_drug_circuit(molecular_weight=450.0, binding_affinity=0.6)
```

#### `convert_molecular_data_to_circuit(mol_data)`
Convert dictionary to circuit.

```python
mol_dict = {
    'molecule_type': 'protein',
    'complexity': 0.7,
    'num_atoms': 24,
    'num_bonds': 26
}
circuit = convert_molecular_data_to_circuit(mol_dict)
```

## Results Structure

### QuantumExecutionResult

**Attributes**:
- `job_id`: Unique job identifier
- `backend`: Backend name used
- `counts`: Dictionary mapping outcomes to counts
- `execution_time`: Total execution time (seconds)
- `cost`: Execution cost (USD)
- `success`: Boolean success flag
- `error_message`: Error description (if failed)
- `metadata`: Additional execution metadata
- `statevector`: State vector (if available)

**Properties**:
- `total_shots`: Total number of shots executed
- `most_likely_outcome`: Most frequently measured outcome
- `probabilities()`: Convert counts to probabilities

**Example**:
```python
result = executor.execute_circuit(circuit, BackendType.IONQ_SIMULATOR)

if result.success:
    print(f"Total shots: {result.total_shots}")
    print(f"Most likely: {result.most_likely_outcome}")

    # Get probabilities
    probs = result.probabilities()
    for outcome, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{outcome}: {prob:.1%}")
```

## Testing

Run the integration tests:

```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph/quantum_core/backends
python test_quantum_integration.py
```

**Test Coverage**:
1. Module imports
2. Backend configurations
3. Circuit builder functionality
4. Executor initialization
5. Simulator execution
6. Convenience functions
7. Molecular data conversion

All 7 tests pass successfully.

## Dependencies

### Required
- `qiskit >= 1.0.0`
- `qiskit-aer >= 0.14.0`
- `numpy`

### Optional (for specific backends)
- `qiskit-ibm-runtime` (IBM Quantum backends)
- `qiskit-ionq` (IonQ backends)
- `amazon-braket-sdk` (AWS Braket backends)

## Configuration

Set environment variables for backend access:

```bash
export IBM_QUANTUM_TOKEN="your_ibm_token"
export IONQ_API_KEY="your_ionq_key"
export AWS_ACCESS_KEY_ID="your_aws_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret"
```

Or pass tokens directly to QuantumExecutor:

```python
executor = QuantumExecutor(
    ibm_token="your_token",
    ionq_token="your_key"
)
```

## Cost Estimates

| Backend | Qubits | Cost per Shot | 1K Shots | 10K Shots |
|---------|--------|---------------|----------|-----------|
| IBM Torino | 133 | $3.00 | $3,072 | $30,720 |
| IBM Brisbane | 127 | $1.25 | $1,280 | $12,800 |
| IonQ Forte | 36 | $3.00 | $3,072 | $30,720 |
| IonQ Simulator | 29 | $0.01 | $10.24 | $102.40 |
| AWS SV1 | 34 | $0.01 | $10.24 | $102.40 |
| Qiskit Simulator | 32 | $0.00 | $0.00 | $0.00 |

## Integration with Existing Code

The new modules integrate seamlessly with the existing `quantum_backend_connector.py`:

### Before (using existing connector):
```python
from quantum_backend_connector import QuantumBackendConnector

connector = QuantumBackendConnector()
await connector.connect_ibm_quantum()
circuit = connector.create_molecular_circuit(4, 'protein', QuantumBackendType.IBM_TORINO)
```

### After (using new quantum_executor):
```python
from quantum_executor import QuantumExecutor, BackendType
from circuit_builder import build_molecular_circuit

executor = QuantumExecutor()
circuit = build_molecular_circuit(4, 'protein', 0.7)
result = executor.execute_circuit(circuit, BackendType.IBM_TORINO)
```

## Error Handling

All errors inherit from `QuantumExecutionError`:

```python
from quantum_executor import QuantumExecutor, QuantumExecutionError, BackendType

executor = QuantumExecutor()

try:
    result = executor.execute_circuit(circuit, BackendType.IBM_TORINO)
    if not result.success:
        print(f"Execution failed: {result.error_message}")
except QuantumExecutionError as e:
    print(f"Error: {e}")
```

## Advanced Usage

### Custom Parameter Binding

Circuits are automatically bound with random parameters. For custom parameters:

```python
from circuit_builder import MolecularCircuitBuilder
import numpy as np

builder = MolecularCircuitBuilder()
circuit = builder.build_circuit(mol_data)

# Bind custom parameters
param_values = np.array([0.1, 0.2, 0.3, ...])  # Match circuit.num_parameters
bound_circuit = circuit.assign_parameters(param_values)

result = executor.execute_circuit(bound_circuit, BackendType.QISKIT_SIMULATOR)
```

### Batch Execution

Execute multiple circuits efficiently:

```python
circuits = [
    build_molecular_circuit(4, 'drug', 0.3),
    build_molecular_circuit(6, 'protein', 0.5),
    build_molecular_circuit(8, 'antibody', 0.7),
]

results = []
for circuit in circuits:
    result = executor.execute_circuit(circuit, BackendType.IONQ_SIMULATOR)
    results.append(result)

# Analyze results
total_cost = sum(r.cost for r in results)
print(f"Total cost: ${total_cost:.2f}")
```

## Issues and Troubleshooting

### Import Errors
If you see import errors, ensure all dependencies are installed:
```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime qiskit-ionq
```

### AWS Braket Not Available
AWS Braket is optional. The module gracefully falls back to local simulator if not installed.

### Parameter Binding
Parameterized circuits are automatically bound with random values. The circuits use VQE-style ansätze which require parameter values for execution.

## Future Enhancements

Potential improvements for future versions:

1. **Parameter Optimization**: Implement VQE optimization loops
2. **Result Caching**: Cache results to avoid duplicate executions
3. **Async Execution**: Add async support for parallel job submission
4. **Job Monitoring**: Real-time job status tracking
5. **Circuit Optimization**: Backend-specific circuit optimization
6. **Hamiltonian Encoding**: Add molecular Hamiltonian terms
7. **Error Mitigation**: Implement error mitigation strategies

## Summary

✅ **quantum_executor.py** created successfully
✅ **circuit_builder.py** created successfully
✅ **__init__.py** created successfully
✅ **test_quantum_integration.py** created successfully
✅ All tests passing (7/7)
✅ Integration with BioQL infrastructure complete

The module is production-ready and provides a unified, cost-aware interface for executing molecular simulation circuits across multiple quantum computing platforms.
