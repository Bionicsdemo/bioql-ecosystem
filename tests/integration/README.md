# BioQL Ecosystem Integration Tests

## Overview

This directory contains comprehensive integration tests for the BioQL Ecosystem, covering all major components and their interactions.

## Test Files

### 1. `test_bioql_integration.py` (24 tests)

Tests end-to-end quantum execution with mocked backends, BioQL + Quillow integration, caching, optimization, and error handling.

**Test Categories:**
- **Quantum Execution** (7 tests)
  - Simple circuit execution
  - Noisy backend execution
  - Backend failure handling
  - Multiple circuit execution
  - IBM job submission
  - Job result retrieval
  - Backend properties

- **QEC Integration** (5 tests)
  - QEC circuit protection
  - Syndrome extraction
  - Error correction workflow
  - QEC overhead calculation
  - Multiple QEC distances

- **Caching & Optimization** (4 tests)
  - Circuit caching
  - Parameter optimization
  - Adaptive shot allocation
  - Batch execution optimization

- **Error Handling** (7 tests)
  - Invalid circuit handling
  - Quota exceeded handling
  - Backend timeout handling
  - Network error retry
  - Partial result handling
  - Concurrent execution safety
  - Error recovery workflow

- **Summary** (1 test)

### 2. `test_qpharos_integration.py` (21 tests)

Tests complete drug discovery pipeline, BioQL + QPHAROS integration, molecular docking workflow, and ADMET pipeline.

**Test Categories:**
- **Drug Discovery Pipeline** (6 tests)
  - Molecular encoding
  - Binding affinity prediction
  - Docking pose generation
  - ADMET prediction
  - Lipinski Rule of Five
  - Molecular generation

- **Molecular Docking** (5 tests)
  - Protein preparation
  - Ligand preparation
  - Docking simulation
  - Interaction analysis
  - Docking validation

- **ADMET Pipeline** (6 tests)
  - Absorption prediction
  - Distribution prediction
  - Metabolism prediction
  - Toxicity prediction
  - Drug-likeness score
  - ADMET optimization

- **BioQL Integration** (3 tests)
  - End-to-end drug design
  - Quantum backend switching
  - Multi-target optimization

- **Summary** (1 test)

### 3. `test_server_integration.py` (20 tests)

Tests Flask API endpoints, authentication flow, billing integration with mocked Stripe, and WebSocket connections.

**Test Categories:**
- **API Endpoints** (3 tests)
  - Auth validation success
  - Auth validation failure
  - Quantum execute endpoint

- **Authentication Flow** (4 tests)
  - User registration
  - Duplicate registration
  - API key lookup
  - Tier upgrade

- **Billing Integration** (6 tests)
  - Create Stripe customer
  - Record usage and charge
  - Invoice creation
  - Usage-based billing
  - Webhook handling

- **WebSocket Connections** (4 tests)
  - WebSocket connection
  - Job status updates
  - Real-time result streaming
  - Error notification

- **Concurrent Requests** (3 tests)
  - Concurrent authentications
  - Concurrent executions
  - Rate limiting

- **Summary** (1 test)

### 4. `test_workflow_integration.py` (19 tests)

Tests workflow builder, node execution, and data flow between nodes.

**Test Categories:**
- **Workflow Builder** (3 tests)
  - Create simple workflow
  - Workflow validation
  - Workflow serialization

- **Node Execution** (5 tests)
  - Input node execution
  - Processing node execution
  - Output node execution
  - Node error handling
  - Conditional node execution

- **Data Flow** (5 tests)
  - Simple data flow
  - Branching data flow
  - Parallel data flow
  - Data aggregation
  - Data transformation chain

- **Complex Workflows** (5 tests)
  - Quantum chemistry workflow
  - Drug discovery workflow
  - Multi-target optimization workflow
  - Error recovery workflow
  - Workflow monitoring

- **Summary** (1 test)

## Total Test Count

**84 Integration Tests** across 4 test files covering:
- Quantum circuit execution and QEC
- Drug discovery and molecular docking
- Server APIs and billing
- Workflow orchestration

## Mock Components

All integration tests use comprehensive mocks located in `tests/mocks/`:

- **`mock_quantum_backend.py`**: Mock quantum backends (IBM, simulator, Stim)
- **`mock_stripe.py`**: Mock Stripe API client for billing tests
- **`mock_database.py`**: Mock SQLite database for user/usage data

## Running the Tests

### Run all integration tests:
```bash
pytest tests/integration/ -v -m integration
```

### Run specific test file:
```bash
pytest tests/integration/test_bioql_integration.py -v
pytest tests/integration/test_qpharos_integration.py -v
pytest tests/integration/test_server_integration.py -v
pytest tests/integration/test_workflow_integration.py -v
```

### Run with coverage:
```bash
pytest tests/integration/ -v --cov=. --cov-report=html
```

### Run test summaries only:
```bash
pytest tests/integration/ -v -k "summary"
```

## Test Scenarios Covered

### 1. End-to-End Workflows
- Complete quantum circuit execution pipeline
- Drug discovery from molecule to candidate
- User authentication to quantum execution
- Workflow creation to result aggregation

### 2. Component Integration
- BioQL + Quillow (QEC integration)
- BioQL + QPHAROS (drug discovery)
- Flask API + Stripe (billing)
- Workflow nodes + data flow

### 3. Error Scenarios
- Backend failures and recovery
- Network timeouts and retries
- Quota limits and validation
- Invalid inputs and edge cases

### 4. Realistic User Workflows
- Register → Execute → Pay workflow
- Design → Optimize → Validate drug pipeline
- Create → Execute → Monitor workflow
- Query → Process → Aggregate data flow

## Key Features

1. **Comprehensive Coverage**: 84+ tests covering all major system components
2. **Realistic Scenarios**: Tests simulate real user workflows and use cases
3. **Mock-Based**: All external dependencies (IBM Quantum, Stripe, databases) are mocked
4. **Error Handling**: Extensive testing of failure scenarios and recovery
5. **Performance**: Tests include concurrent execution, caching, and optimization
6. **Documentation**: Each test includes clear docstrings explaining purpose

## Dependencies

Tests require the following packages (all included in project requirements):
- pytest
- numpy
- flask (for server tests)
- concurrent.futures (for parallel execution tests)

## Contributing

When adding new integration tests:

1. Use the `@pytest.mark.integration` decorator
2. Create fixtures for reusable components
3. Include both success and failure scenarios
4. Add docstrings explaining test purpose
5. Update the summary test with new test counts

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No external API dependencies (all mocked)
- Fast execution (< 2 minutes for all tests)
- Deterministic results (no flaky tests)
- Clear failure messages

## License

Copyright 2024-2025 SpectrixRD
Licensed under the Apache License, Version 2.0
