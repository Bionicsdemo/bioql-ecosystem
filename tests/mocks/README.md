# BioQL Ecosystem Mock APIs

Comprehensive mocks for all external APIs used in the BioQL ecosystem.

## Overview

This package provides mock implementations for:

1. **IBM Quantum API (Qiskit)** - Mock quantum circuits, backends, jobs, and results
2. **Modal API** - Mock serverless functions and workflows
3. **Stripe API** - Mock payment processing, customers, and webhooks
4. **RDKit Chemistry** - Mock molecular operations and descriptors
5. **PDB Database** - Mock protein structure fetching

## Files

- `api_mocks.py` - Main comprehensive mock implementations (1,401 lines)
- `__init__.py` - Package exports and imports
- `mock_quantum_backend.py` - Legacy quantum backend mocks
- `mock_stripe.py` - Legacy Stripe mocks
- `mock_database.py` - Legacy database mocks

## Usage

### Import Mocks

```python
from tests.mocks.api_mocks import (
    MockIBMQuantum,
    MockModal,
    MockStripe,
    MockRDKit,
    MockPDB
)
```

### Use with Pytest Fixtures

The mocks are available as pytest fixtures in `tests/conftest.py`:

```python
def test_quantum_circuit(mock_ibm_quantum):
    backend = mock_ibm_quantum.get_backend('aer_simulator')
    circuit = MockQuantumCircuit(2)
    circuit.h(0).cx(0, 1).measure_all()
    job = backend.run(circuit, shots=1024)
    result = job.result()
    assert result.success
```

### Available Fixtures

#### IBM Quantum
- `mock_ibm_quantum` - Full quantum platform
- `mock_quantum_backend` - Quantum backend
- `mock_quantum_circuit` - Quantum circuit
- `mock_quantum_result` - Quantum result
- `mock_quantum_job` - Quantum job

#### Modal
- `mock_modal` - Modal platform
- `mock_modal_function` - Modal function
- `mock_modal_workflow` - Modal workflow

#### Stripe
- `mock_stripe` - Stripe API
- `mock_stripe_customer` - Customer object
- `mock_stripe_charge` - Charge object
- `mock_stripe_webhook` - Webhook event

#### RDKit
- `mock_rdkit` - RDKit library
- `mock_molecule` - Molecule object
- `mock_aspirin` - Aspirin molecule
- `mock_caffeine` - Caffeine molecule

#### PDB
- `mock_pdb` - PDB database
- `mock_protein_structure` - Protein structure
- `mock_spike_protein` - SARS-CoV-2 spike protein

### Direct Usage

```python
# IBM Quantum
quantum = MockIBMQuantum()
backend = quantum.get_backend('ibm_brisbane')
job = backend.run(circuit, shots=1024)
result = job.result()
counts = result.get_counts()

# Modal
modal = MockModal()
func = MockModalFunction("my_function")
result = func.remote(x=5)
value = result.get()

# Stripe
stripe = MockStripe()
customer = stripe.Customer.create(
    email="test@example.com",
    name="Test User"
)
charge = stripe.Charge.create(
    amount=10000,
    customer=customer.id
)

# RDKit
rdkit = MockRDKit()
mol = rdkit.Chem.MolFromSmiles("CCO")
mol_weight = rdkit.Descriptors.MolWt(mol)

# PDB
pdb = MockPDB()
structure = pdb.fetch("7BV2", format='dict')
pdb_string = pdb.fetch("7BV2", format='pdb')
```

### Use Utility Functions for Patching

```python
from unittest.mock import patch
from tests.mocks.api_mocks import create_all_mock_patches

def test_with_mocks():
    patches = create_all_mock_patches()
    with patch.dict('sys.modules', patches):
        # Your test code here
        pass
```

## Mock Statistics

- **Total Mock Classes**: 22
- **Total Utility Functions**: 6
- **Total Exports**: 28
- **Total Lines of Code**: ~1,400 lines

## Features

All mocks provide:

- Realistic return values
- Support for different test scenarios
- Easy configuration
- Full compatibility with unittest.mock and pytest-mock
- Comprehensive API coverage

## Examples

See `tests/conftest.py` for fixture examples and test usage patterns.

## License

Copyright 2024-2025 SpectrixRD  
Licensed under the Apache License, Version 2.0
