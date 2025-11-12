# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Comprehensive API Mocks for BioQL Ecosystem Testing
===================================================

This module provides mock implementations for all external APIs used in BioQL:
1. IBM Quantum API (Qiskit)
2. Modal API
3. Stripe API
4. RDKit Chemistry Operations
5. PDB Protein Structure Fetching

All mocks are designed to:
- Return realistic data
- Support different test scenarios
- Be easily configurable
- Work with unittest.mock and pytest-mock
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import MagicMock, Mock

import numpy as np

# ============================================================================
# IBM Quantum Mocks (Qiskit)
# ============================================================================


@dataclass
class MockQuantumCounts:
    """Mock quantum measurement counts with dict-like interface."""

    counts_dict: Dict[str, int] = field(default_factory=lambda: {"00": 500, "11": 500})

    def get_counts(self):
        """Return counts dictionary (Qiskit compatibility)."""
        return self.counts_dict

    def __getitem__(self, key):
        return self.counts_dict[key]

    def __iter__(self):
        return iter(self.counts_dict)

    def items(self):
        return self.counts_dict.items()

    def keys(self):
        return self.counts_dict.keys()

    def values(self):
        return self.counts_dict.values()


@dataclass
class MockQuantumResult:
    """Mock Qiskit Result object with full compatibility."""

    counts: Union[MockQuantumCounts, Dict[str, int]] = field(
        default_factory=lambda: {"00": 500, "11": 500}
    )
    shots: int = 1000
    backend: str = "aer_simulator"
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    job_id: str = "mock_job_12345"
    date: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if isinstance(self.counts, dict):
            self.counts = MockQuantumCounts(self.counts)

    def get_counts(self, circuit=0):
        """Get measurement counts (Qiskit API)."""
        return self.counts.counts_dict

    def get_statevector(self, circuit=0):
        """Get statevector for simulator results."""
        return np.array([1 / np.sqrt(2), 0, 0, 1 / np.sqrt(2)])  # Bell state

    def get_memory(self, circuit=0):
        """Get individual shot results."""
        return ["00", "11"] * (self.shots // 2)

    def data(self, circuit=0):
        """Get result data (Qiskit API)."""
        return {"counts": self.counts.counts_dict, "shots": self.shots, "success": self.success}

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "counts": self.counts.counts_dict,
            "shots": self.shots,
            "backend_name": self.backend,
            "job_id": self.job_id,
            "success": self.success,
            "date": self.date,
        }


class MockQuantumJob:
    """Mock Qiskit Job object with realistic behavior."""

    def __init__(
        self, job_id: str, circuit: Any = None, backend: str = "aer_simulator", shots: int = 1024
    ):
        self.job_id = job_id
        self.circuit = circuit
        self.backend = backend
        self.shots = shots
        self.status_val = "QUEUED"
        self._result = None

    def status(self):
        """Get job status (Qiskit API)."""

        class JobStatus:
            def __init__(self, value):
                self.value = value
                self.name = value

        return JobStatus(self.status_val)

    def result(self, timeout=None):
        """Get job result, automatically completes job."""
        self.status_val = "DONE"
        if self._result is None:
            counts = self._generate_realistic_counts()
            self._result = MockQuantumResult(
                counts=counts, shots=self.shots, backend=self.backend, job_id=self.job_id
            )
        return self._result

    def _generate_realistic_counts(self):
        """Generate realistic quantum counts based on circuit."""
        # Simulate Bell state with measurement noise
        base_counts = {
            "00": int(self.shots * 0.48),
            "11": int(self.shots * 0.48),
            "01": int(self.shots * 0.02),
            "10": int(self.shots * 0.02),
        }
        return base_counts

    def wait_for_final_state(self, timeout=None):
        """Wait for job to complete."""
        self.status_val = "DONE"

    def cancel(self):
        """Cancel job."""
        self.status_val = "CANCELLED"
        return True


class MockQuantumCircuit:
    """Mock Qiskit QuantumCircuit with common operations."""

    def __init__(self, num_qubits: int = 2, num_clbits: int = None):
        self.num_qubits = num_qubits
        self.num_clbits = num_clbits or num_qubits
        self.operations = []
        self._data = []
        self.qregs = []
        self.cregs = []

    def h(self, qubit):
        """Apply Hadamard gate."""
        self.operations.append(("h", qubit))
        return self

    def x(self, qubit):
        """Apply X gate."""
        self.operations.append(("x", qubit))
        return self

    def y(self, qubit):
        """Apply Y gate."""
        self.operations.append(("y", qubit))
        return self

    def z(self, qubit):
        """Apply Z gate."""
        self.operations.append(("z", qubit))
        return self

    def cx(self, control: int, target: int):
        """Apply CNOT gate."""
        self.operations.append(("cx", control, target))
        return self

    def ry(self, theta, qubit):
        """Apply RY rotation."""
        self.operations.append(("ry", theta, qubit))
        return self

    def rz(self, theta, qubit):
        """Apply RZ rotation."""
        self.operations.append(("rz", theta, qubit))
        return self

    def measure(self, qubit, clbit):
        """Measure qubit to classical bit."""
        self.operations.append(("measure", qubit, clbit))
        return self

    def measure_all(self):
        """Measure all qubits."""
        for i in range(self.num_qubits):
            self.measure(i, i)
        return self

    def barrier(self, *qubits):
        """Add barrier."""
        self.operations.append(("barrier", qubits))
        return self

    def draw(self, output=None):
        """Draw circuit diagram."""
        return "Mock Quantum Circuit Diagram"

    def depth(self):
        """Get circuit depth."""
        return len(self.operations)

    def size(self):
        """Get total gate count."""
        return len(self.operations)

    def num_parameters(self):
        """Get number of parameters."""
        return sum(1 for op in self.operations if len(op) > 2 and isinstance(op[1], (int, float)))


class MockBackend:
    """Mock Qiskit Backend with realistic properties."""

    def __init__(self, name: str = "aer_simulator", max_shots: int = 100000):
        self.name = name
        self.max_shots = max_shots
        self._job_counter = 0
        self._config = {
            "backend_name": name,
            "backend_version": "1.0.0",
            "n_qubits": 32,
            "basis_gates": ["id", "rz", "sx", "x", "cx", "reset"],
            "gates": [],
            "local": True,
            "simulator": "aer" in name or "simulator" in name,
            "conditional": True,
            "open_pulse": False,
            "memory": True,
            "max_shots": max_shots,
            "coupling_map": None,
        }

    def run(self, circuits, shots: int = 1024, **kwargs):
        """Run circuits on backend."""
        self._job_counter += 1
        job_id = f"{self.name}_job_{self._job_counter}"
        return MockQuantumJob(job_id=job_id, circuit=circuits, backend=self.name, shots=shots)

    def properties(self):
        """Get backend properties."""
        return self._config

    def configuration(self):
        """Get backend configuration."""
        return self._config

    def status(self):
        """Get backend status."""
        return {
            "backend_name": self.name,
            "backend_version": "1.0.0",
            "operational": True,
            "pending_jobs": 0,
            "status_msg": "active",
        }


class MockIBMQuantum:
    """Mock IBM Quantum Platform with comprehensive functionality."""

    def __init__(self, api_token: str = "mock_ibm_token"):
        self.api_token = api_token
        self.jobs = {}
        self.job_counter = 0
        self.backends_list = {
            "aer_simulator": MockBackend("aer_simulator"),
            "ibmq_qasm_simulator": MockBackend("ibmq_qasm_simulator"),
            "ibm_brisbane": MockBackend("ibm_brisbane", max_shots=10000),
            "ibm_kyoto": MockBackend("ibm_kyoto", max_shots=10000),
            "ibm_osaka": MockBackend("ibm_osaka", max_shots=10000),
        }

    def get_backend(self, name: str = "aer_simulator"):
        """Get backend by name."""
        return self.backends_list.get(name, self.backends_list["aer_simulator"])

    def backends(self, filters=None):
        """List available backends."""
        return list(self.backends_list.values())

    def run_circuit(self, circuit: Any, backend: str = "ibm_torino", shots: int = 1024):
        """Run circuit on specified backend."""
        self.job_counter += 1
        job_id = f"mock_job_{self.job_counter}"
        job = MockQuantumJob(job_id, circuit, backend, shots)
        self.jobs[job_id] = job
        return job

    def execute(self, circuits, backend=None, shots: int = 1024, **kwargs):
        """Execute circuits (compatibility with qiskit.execute)."""
        if backend is None:
            backend = self.get_backend()
        return backend.run(circuits, shots=shots, **kwargs)

    @staticmethod
    def mock_bell_state_result(shots: int = 1024):
        """Generate realistic Bell state measurement results."""
        counts = {
            "00": int(shots * 0.48),
            "11": int(shots * 0.48),
            "01": int(shots * 0.02),
            "10": int(shots * 0.02),
        }
        return MockQuantumResult(counts=counts, shots=shots)

    @staticmethod
    def mock_vqe_result(energy: float = -1.137):
        """Generate realistic VQE algorithm results."""
        return {
            "energy": energy,
            "eigenvalue": energy,
            "optimal_parameters": [0.5, 1.2, -0.3, 0.8],
            "optimizer_evals": 150,
            "optimizer_time": 12.5,
            "eigenstate": [0.707, 0.0, 0.0, 0.707],
        }

    @staticmethod
    def mock_grover_result(marked_state: str = "101", shots: int = 1024):
        """Generate realistic Grover search results."""
        counts = {marked_state: int(shots * 0.9)}
        # Add noise to other states
        for i in range(8):
            state = format(i, "03b")
            if state != marked_state:
                counts[state] = int(shots * 0.01)
        return MockQuantumResult(counts=counts, shots=shots)


# ============================================================================
# Modal API Mocks
# ============================================================================


@dataclass
class MockModalResult:
    """Mock Modal function execution result."""

    value: Any = None
    execution_id: str = "modal_exec_12345"
    status: str = "success"
    duration_ms: float = 125.5
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def get(self):
        """Get result value."""
        return self.value

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "value": self.value,
            "execution_id": self.execution_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


class MockModalFunction:
    """Mock Modal Function with remote/local execution."""

    def __init__(self, name: str = "mock_function", image: str = "python:3.10"):
        self.name = name
        self.image = image
        self.invocations = []
        self._execution_counter = 0

    def remote(self, *args, **kwargs):
        """Execute function remotely (async)."""
        self._execution_counter += 1
        exec_id = f"modal_exec_{self.name}_{self._execution_counter}"
        self.invocations.append({"args": args, "kwargs": kwargs, "exec_id": exec_id})

        # Return different results based on function name
        if "quantum" in self.name.lower():
            value = {"counts": {"00": 500, "11": 500}, "shots": 1000, "backend": "ibm_kyoto"}
        elif "protein" in self.name.lower():
            value = {"structure": "ATOM  1  CA  ALA A   1...", "format": "pdb", "pdb_id": "7BV2"}
        elif "docking" in self.name.lower():
            value = {"binding_affinity": -8.5, "pose_file": "/tmp/pose.pdbqt", "rmsd": 1.2}
        else:
            value = {"status": "completed", "result": "mock_result"}

        return MockModalResult(value=value, execution_id=exec_id)

    def local(self, *args, **kwargs):
        """Execute function locally."""
        result = self.remote(*args, **kwargs)
        return result.get()

    def map(self, *inputs):
        """Map function over multiple inputs."""
        return [self.remote(inp) for inp in inputs]

    def invoke(self, *args, **kwargs):
        """Invoke function (alias for remote)."""
        return self.remote(*args, **kwargs)


class MockModalWorkflow:
    """Mock Modal Workflow for multi-step processing."""

    def __init__(self, name: str = "mock_workflow"):
        self.name = name
        self.steps = []
        self.completed = False
        self._results = []

    def add_step(self, step_name: str, func: Callable, *args, **kwargs):
        """Add a step to the workflow."""
        self.steps.append({"name": step_name, "function": func, "args": args, "kwargs": kwargs})

    def run(self):
        """Execute the workflow."""
        self._results = []
        start_time = datetime.now()

        for step in self.steps:
            func = step["function"]
            if isinstance(func, MockModalFunction):
                result = func.remote(*step["args"], **step["kwargs"])
                self._results.append(
                    {"step": step["name"], "result": result.get(), "status": "success"}
                )
            else:
                self._results.append({"step": step["name"], "result": None, "status": "skipped"})

        self.completed = True
        duration = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "status": "completed",
            "workflow_name": self.name,
            "steps_completed": len(self.steps),
            "results": self._results,
            "duration_ms": duration,
        }


class MockModal:
    """Mock Modal serverless platform."""

    def __init__(self):
        self.functions = {}
        self.workflows = {}
        self.images = {}

    def Function(self, name: str = None, image: str = None, **kwargs):
        """Create a Modal function decorator."""

        def decorator(func):
            mock_func = MockModalFunction(name=name or func.__name__, image=image or "python:3.10")
            self.functions[name or func.__name__] = mock_func
            return mock_func

        return decorator

    def Workflow(self, name: str = None):
        """Create a Modal workflow."""
        workflow = MockModalWorkflow(name=name or "default_workflow")
        self.workflows[name or "default_workflow"] = workflow
        return workflow

    def Image(self, name: str = None):
        """Create a Modal image."""
        image = {"name": name or "default_image", "packages": [], "base_image": "python:3.10"}
        self.images[name or "default_image"] = image
        return image

    def create_function(self, name: str):
        """Create function (legacy compatibility)."""
        func = MockModalFunction(name)
        self.functions[name] = func
        return func

    @staticmethod
    def mock_function_result(value=None):
        """Create a mock function result."""
        return MockModalResult(value=value)

    @staticmethod
    def mock_workflow_result(results=None):
        """Create a mock workflow result."""
        return {"status": "completed", "results": results or [], "duration_ms": 1250.0}


# ============================================================================
# Stripe API Mocks
# ============================================================================


@dataclass
class MockStripeCustomer:
    """Mock Stripe Customer object."""

    id: str = "cus_mock12345"
    email: str = "test@example.com"
    name: str = "Test User"
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    balance: int = 0
    currency: str = "usd"
    metadata: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": "customer",
            "email": self.email,
            "name": self.name,
            "created": self.created,
            "balance": self.balance,
            "currency": self.currency,
            "metadata": self.metadata,
            "description": self.description,
        }


@dataclass
class MockStripeCharge:
    """Mock Stripe Charge object."""

    id: str = "ch_mock12345"
    amount: int = 10000  # in cents ($100.00)
    currency: str = "usd"
    customer: str = "cus_mock12345"
    customer_id: str = "cus_mock12345"  # Alias
    status: str = "succeeded"
    paid: bool = True
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    receipt_url: str = "https://pay.stripe.com/receipts/mock"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": "charge",
            "amount": self.amount,
            "currency": self.currency,
            "customer": self.customer,
            "status": self.status,
            "paid": self.paid,
            "created": self.created,
            "metadata": self.metadata,
            "description": self.description,
            "receipt_url": self.receipt_url,
        }


@dataclass
class MockStripeInvoice:
    """Mock Stripe Invoice object."""

    id: str = "in_mock12345"
    customer: str = "cus_mock12345"
    amount_due: int = 300000  # $3000 in cents
    amount_paid: int = 0
    currency: str = "usd"
    status: str = "open"
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": "invoice",
            "customer": self.customer,
            "amount_due": self.amount_due,
            "amount_paid": self.amount_paid,
            "currency": self.currency,
            "status": self.status,
            "created": self.created,
            "metadata": self.metadata,
        }


@dataclass
class MockStripeWebhook:
    """Mock Stripe Webhook Event."""

    id: str = "evt_mock12345"
    type: str = "charge.succeeded"
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    data: Dict[str, Any] = field(default_factory=dict)
    livemode: bool = False

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": "event",
            "type": self.type,
            "created": self.created,
            "data": self.data,
            "livemode": self.livemode,
        }


class MockStripe:
    """Mock Stripe API with full customer/charge/webhook support."""

    def __init__(self, api_key: str = "sk_test_mock"):
        self.api_key = api_key
        self._customer_counter = 0
        self._charge_counter = 0
        self._invoice_counter = 0
        self._event_counter = 0

    class Customer:
        """Mock Stripe Customer API."""

        _customers = {}
        _counter = 0

        @classmethod
        def create(cls, email=None, name=None, metadata=None, description="", **kwargs):
            """Create a customer."""
            cls._counter += 1
            customer = MockStripeCustomer(
                id=f"cus_mock{cls._counter:05d}",
                email=email or f"test{cls._counter}@example.com",
                name=name or f"Test User {cls._counter}",
                metadata=metadata or {},
                description=description,
            )
            cls._customers[customer.id] = customer
            return customer

        @classmethod
        def retrieve(cls, customer_id):
            """Retrieve a customer."""
            return cls._customers.get(customer_id)

        @classmethod
        def modify(cls, customer_id, **kwargs):
            """Modify a customer."""
            customer = cls._customers.get(customer_id)
            if customer:
                for key, value in kwargs.items():
                    if hasattr(customer, key):
                        setattr(customer, key, value)
            return customer

        @classmethod
        def delete(cls, customer_id):
            """Delete a customer."""
            if customer_id in cls._customers:
                del cls._customers[customer_id]
                return {"id": customer_id, "deleted": True}
            return None

        @classmethod
        def list(cls, limit=10, **kwargs):
            """List customers."""
            customers = list(cls._customers.values())[:limit]
            return {"data": customers, "has_more": len(cls._customers) > limit}

    class Charge:
        """Mock Stripe Charge API."""

        _charges = {}
        _counter = 0

        @classmethod
        def create(
            cls, amount=None, currency="usd", customer=None, metadata=None, description="", **kwargs
        ):
            """Create a charge."""
            cls._counter += 1
            charge = MockStripeCharge(
                id=f"ch_mock{cls._counter:05d}",
                amount=amount or 10000,
                currency=currency,
                customer=customer or "cus_mock00001",
                customer_id=customer or "cus_mock00001",
                metadata=metadata or {},
                description=description,
                status="succeeded" if kwargs.get("capture", True) else "pending",
            )
            cls._charges[charge.id] = charge
            return charge

        @classmethod
        def retrieve(cls, charge_id):
            """Retrieve a charge."""
            return cls._charges.get(charge_id)

        @classmethod
        def list(cls, limit=10, **kwargs):
            """List charges."""
            charges = list(cls._charges.values())[:limit]
            return {"data": charges, "has_more": len(cls._charges) > limit}

    class Invoice:
        """Mock Stripe Invoice API."""

        _invoices = {}
        _counter = 0

        @classmethod
        def create(cls, customer=None, amount=300000, metadata=None, **kwargs):
            """Create an invoice."""
            cls._counter += 1
            invoice = MockStripeInvoice(
                id=f"in_mock{cls._counter:05d}",
                customer=customer or "cus_mock00001",
                amount_due=amount,
                metadata=metadata or {},
            )
            cls._invoices[invoice.id] = invoice
            return invoice

        @classmethod
        def retrieve(cls, invoice_id):
            """Retrieve an invoice."""
            return cls._invoices.get(invoice_id)

        @classmethod
        def finalize_invoice(cls, invoice_id, **kwargs):
            """Finalize an invoice."""
            invoice = cls._invoices.get(invoice_id)
            if invoice:
                invoice.status = "open"
            return invoice

    class Webhook:
        """Mock Stripe Webhook API."""

        @staticmethod
        def construct_event(payload, sig_header, secret):
            """Construct webhook event from payload."""
            if isinstance(payload, str):
                data = json.loads(payload)
            else:
                data = payload

            return MockStripeWebhook(
                id=data.get("id", "evt_mock12345"),
                type=data.get("type", "charge.succeeded"),
                data=data.get("data", {}),
                created=data.get("created", int(datetime.now().timestamp())),
            )

    @staticmethod
    def mock_customer(email="test@example.com", name="Test User"):
        """Create a mock customer."""
        return MockStripeCustomer(email=email, name=name)

    @staticmethod
    def mock_charge(amount=10000, status="succeeded"):
        """Create a mock charge."""
        return MockStripeCharge(amount=amount, status=status)

    @staticmethod
    def mock_invoice(amount_due=300000, status="open"):
        """Create a mock invoice."""
        return MockStripeInvoice(amount_due=amount_due, status=status)

    @staticmethod
    def mock_webhook_event(event_type="charge.succeeded", data=None):
        """Create a mock webhook event."""
        return MockStripeWebhook(type=event_type, data=data or {})


# ============================================================================
# RDKit Chemistry Mocks
# ============================================================================


class MockAtom:
    """Mock RDKit Atom object."""

    def __init__(self, symbol: str = "C", idx: int = 0):
        self.symbol = symbol
        self.idx = idx
        self._formal_charge = 0
        self._num_hydrogens = 0

    def GetSymbol(self):
        return self.symbol

    def GetIdx(self):
        return self.idx

    def GetFormalCharge(self):
        return self._formal_charge

    def SetFormalCharge(self, charge):
        self._formal_charge = charge

    def GetTotalNumHs(self):
        return self._num_hydrogens

    def GetAtomicNum(self):
        symbol_to_num = {"H": 1, "C": 6, "N": 7, "O": 8, "S": 16, "P": 15, "F": 9, "Cl": 17}
        return symbol_to_num.get(self.symbol, 6)


class MockBond:
    """Mock RDKit Bond object."""

    def __init__(self, begin_idx: int = 0, end_idx: int = 1, bond_type: str = "SINGLE"):
        self.begin_idx = begin_idx
        self.end_idx = end_idx
        self.bond_type = bond_type

    def GetBeginAtomIdx(self):
        return self.begin_idx

    def GetEndAtomIdx(self):
        return self.end_idx

    def GetBondType(self):
        return self.bond_type


class MockConformer:
    """Mock RDKit Conformer object."""

    def __init__(self, num_atoms: int = 3):
        self.num_atoms = num_atoms
        # Generate simple mock positions as list of lists
        self._positions = [
            [float(i) * 3.8, 0.0, 0.0] for i in range(num_atoms)  # Simple linear arrangement
        ]

    def GetPositions(self):
        """Return positions as list (compatible with RDKit API)."""
        return self._positions

    def GetAtomPosition(self, idx):
        """Get position of specific atom."""
        return self._positions[idx]


class MockMolecule:
    """Mock RDKit Mol object with comprehensive API."""

    def __init__(self, smiles: str = "CCO", num_atoms: int = None):
        self.smiles = smiles
        self._num_atoms = num_atoms or max(3, len(smiles) // 2)
        self._atoms = [MockAtom("C", 0), MockAtom("C", 1), MockAtom("O", 2)]
        self._bonds = [MockBond(0, 1), MockBond(1, 2)]
        self._conformers = [MockConformer(self._num_atoms)]
        self._props = {}

    def GetNumAtoms(self):
        """Get number of atoms."""
        return self._num_atoms

    def get_num_atoms(self):
        """Alias for GetNumAtoms."""
        return self.GetNumAtoms()

    def GetAtoms(self):
        """Get list of atoms."""
        return self._atoms

    def GetBonds(self):
        """Get list of bonds."""
        return self._bonds

    def GetAtomWithIdx(self, idx):
        """Get atom by index."""
        if 0 <= idx < len(self._atoms):
            return self._atoms[idx]
        return None

    def GetNumConformers(self):
        """Get number of conformers."""
        return len(self._conformers)

    def GetConformer(self, idx=0):
        """Get conformer."""
        if self._conformers:
            return self._conformers[idx]
        return None

    def AddConformer(self, conf):
        """Add conformer."""
        self._conformers.append(conf)

    def SetProp(self, key, value):
        """Set molecular property."""
        self._props[key] = str(value)

    def GetProp(self, key):
        """Get molecular property."""
        return self._props.get(key, "")

    def HasProp(self, key):
        """Check if property exists."""
        return key in self._props

    def compute_properties(self):
        """Compute mock molecular properties."""
        self.properties = {
            "MW": 46.07,  # Ethanol
            "LogP": -0.14,
            "HBD": 1,
            "HBA": 1,
            "TPSA": 20.23,
            "NumRotatableBonds": 0,
            "NumAromaticRings": 0,
        }
        return self.properties


class MockRDKit:
    """Mock RDKit chemistry library with comprehensive functionality."""

    class Chem:
        """Mock RDKit Chem module."""

        @staticmethod
        def MolFromSmiles(smiles, sanitize=True):
            """Create molecule from SMILES."""
            if not smiles or smiles == "INVALID" or smiles == "":
                return None
            return MockMolecule(smiles=smiles)

        @staticmethod
        def MolToSmiles(mol):
            """Convert molecule to SMILES."""
            if isinstance(mol, MockMolecule):
                return mol.smiles
            return None

        @staticmethod
        def AddHs(mol):
            """Add hydrogens to molecule."""
            return mol

        @staticmethod
        def RemoveHs(mol):
            """Remove hydrogens from molecule."""
            return mol

        @staticmethod
        def SanitizeMol(mol):
            """Sanitize molecule."""
            return 0  # Success code

        @staticmethod
        def MolFromPDBFile(filename):
            """Load molecule from PDB file."""
            return MockMolecule(smiles="CCO")

        @staticmethod
        def MolToPDBFile(mol, filename):
            """Write molecule to PDB file."""
            with open(filename, "w") as f:
                f.write(
                    "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 20.00           C\n"
                )
            return True

        @staticmethod
        def mol_from_smiles(smiles: str):
            """Lowercase alias for MolFromSmiles."""
            return MockRDKit.Chem.MolFromSmiles(smiles)

        @staticmethod
        def mol_to_smiles(mol):
            """Lowercase alias for MolToSmiles."""
            return MockRDKit.Chem.MolToSmiles(mol)

    class AllChem:
        """Mock RDKit AllChem module."""

        @staticmethod
        def EmbedMolecule(mol, randomSeed=42, useRandomCoords=False):
            """Generate 3D coordinates."""
            return 0  # Success code

        @staticmethod
        def UFFOptimizeMolecule(mol, maxIters=200):
            """Optimize molecule geometry with UFF."""
            return 0  # Success code

        @staticmethod
        def MMFFOptimizeMolecule(mol, maxIters=200):
            """Optimize molecule geometry with MMFF."""
            return 0  # Success code

        @staticmethod
        def EmbedMultipleConfs(mol, numConfs=10):
            """Generate multiple conformers."""
            for i in range(numConfs):
                mol.AddConformer(MockConformer(mol.GetNumAtoms()))
            return list(range(numConfs))

    class Descriptors:
        """Mock RDKit Descriptors module."""

        @staticmethod
        def MolWt(mol):
            """Calculate molecular weight."""
            return 46.07  # Ethanol

        @staticmethod
        def MolLogP(mol):
            """Calculate LogP."""
            return -0.14

        @staticmethod
        def TPSA(mol):
            """Calculate topological polar surface area."""
            return 20.23

        @staticmethod
        def NumHDonors(mol):
            """Count hydrogen bond donors."""
            return 1

        @staticmethod
        def NumHAcceptors(mol):
            """Count hydrogen bond acceptors."""
            return 1

        @staticmethod
        def NumRotatableBonds(mol):
            """Count rotatable bonds."""
            return 0

        @staticmethod
        def NumAromaticRings(mol):
            """Count aromatic rings."""
            return 0

    @staticmethod
    def mock_molecule(smiles="CCO"):
        """Create a mock molecule."""
        return MockMolecule(smiles=smiles)

    @staticmethod
    def mock_aspirin():
        """Create a mock aspirin molecule."""
        return MockMolecule(smiles="CC(=O)OC1=CC=CC=C1C(=O)O", num_atoms=13)

    @staticmethod
    def mock_caffeine():
        """Create a mock caffeine molecule."""
        return MockMolecule(smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C", num_atoms=14)

    @staticmethod
    def mock_drug_candidate():
        """Create a mock drug candidate molecule."""
        return MockMolecule(smiles="CC(C)Cc1ccc(cc1)C(C)C(=O)O", num_atoms=15)


# ============================================================================
# PDB Protein Structure Mocks
# ============================================================================


@dataclass
class MockProteinStructure:
    """Mock PDB protein structure."""

    pdb_id: str = "1ABC"
    sequence: str = "ACDEFGHIKLMNPQRSTVWY"
    num_residues: int = 20
    num_chains: int = 1
    num_atoms: int = 160
    chains: List[str] = field(default_factory=lambda: ["A"])
    resolution: float = 2.0
    method: str = "X-RAY DIFFRACTION"

    def to_pdb_string(self):
        """Convert to PDB format string."""
        pdb_lines = [
            f"HEADER    MOCK PROTEIN                            {self.pdb_id}",
            f"TITLE     MOCK PROTEIN STRUCTURE FOR TESTING",
            f"EXPDTA    {self.method}",
            f"REMARK   2 RESOLUTION. {self.resolution} ANGSTROMS.",
        ]

        # Add some atoms
        for i in range(min(10, self.num_residues)):
            pdb_lines.append(
                f"ATOM   {i+1:4d}  CA  ALA A{i+1:4d}    {i*3.8:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 20.00           C"
            )

        pdb_lines.append("END")
        return "\n".join(pdb_lines)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "pdb_id": self.pdb_id,
            "sequence": self.sequence,
            "num_residues": self.num_residues,
            "num_chains": self.num_chains,
            "num_atoms": self.num_atoms,
            "chains": self.chains,
            "resolution": self.resolution,
            "method": self.method,
        }

    def get_chains(self):
        """Get chain identifiers."""
        return self.chains

    def get_residues(self):
        """Get mock residues."""
        residues = []
        residue_names = ["ALA", "CYS", "ASP", "GLU", "PHE", "GLY", "HIS", "ILE", "LYS", "LEU"]
        for i in range(self.num_residues):
            residues.append(
                {
                    "chain": self.chains[i % len(self.chains)],
                    "id": i + 1,
                    "name": residue_names[i % len(residue_names)],
                }
            )
        return residues


class MockPDB:
    """Mock PDB database operations."""

    def __init__(self):
        self.structures = {
            "1ABC": MockProteinStructure(pdb_id="1ABC"),
            "2XYZ": MockProteinStructure(
                pdb_id="2XYZ", sequence="MLKJIHGFEDCBA", num_residues=13, num_atoms=104
            ),
            "7BV2": MockProteinStructure(
                pdb_id="7BV2",
                sequence="MFVFLVLLPLVSSQCVNLTTRTQLPP",
                num_residues=26,
                num_atoms=208,
                resolution=2.9,
                method="X-RAY DIFFRACTION",
            ),
        }

    def fetch(self, pdb_id, format="pdb"):
        """Fetch PDB structure."""
        structure = self.structures.get(pdb_id.upper())
        if structure is None:
            raise ValueError(f"PDB ID {pdb_id} not found in mock database")

        if format == "pdb":
            return structure.to_pdb_string()
        elif format == "dict":
            return structure.to_dict()
        else:
            return structure

    def fetch_structure(self, pdb_id: str):
        """Fetch mock protein structure (alias)."""
        return self.fetch(pdb_id, format="object")

    def download(self, pdb_id, output_path=None):
        """Download PDB file."""
        structure = self.fetch(pdb_id, format="pdb")
        if output_path:
            with open(output_path, "w") as f:
                f.write(structure)
        return structure

    def search(self, query):
        """Search PDB database."""
        results = []
        for pdb_id, structure in self.structures.items():
            if query.lower() in pdb_id.lower() or query.lower() in structure.sequence.lower():
                results.append(structure.to_dict())
        return results

    @staticmethod
    def mock_structure(pdb_id="1ABC", sequence="ACDEFG"):
        """Create a mock protein structure."""
        return MockProteinStructure(
            pdb_id=pdb_id,
            sequence=sequence,
            num_residues=len(sequence),
            num_atoms=len(sequence) * 8,  # Approximate atoms per residue
        )

    @staticmethod
    def mock_spike_protein():
        """Create a mock SARS-CoV-2 spike protein."""
        return MockProteinStructure(
            pdb_id="7BV2",
            sequence="MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHV",
            num_residues=70,
            num_atoms=560,
            resolution=2.9,
            method="X-RAY DIFFRACTION",
        )


# ============================================================================
# Utility Functions for Creating Mock Patches
# ============================================================================


def create_quantum_mock_patches():
    """
    Create patches for quantum APIs.

    Returns:
        dict: Mapping of module paths to mock objects

    Example:
        >>> patches = create_quantum_mock_patches()
        >>> with patch.dict('sys.modules', patches):
        ...     # Your test code here
    """
    mock_ibm = MockIBMQuantum()
    mock_backend = MockBackend()

    return {
        "qiskit.execute": Mock(side_effect=lambda circuits, backend, shots: MockQuantumJob()),
        "qiskit.QuantumCircuit": MockQuantumCircuit,
        "qiskit_aer.AerSimulator": Mock(return_value=mock_backend),
        "qiskit_ibm_runtime.QiskitRuntimeService": Mock(return_value=mock_ibm),
    }


def create_modal_mock_patches():
    """
    Create patches for Modal API.

    Returns:
        dict: Mapping of module paths to mock objects
    """
    mock_modal = MockModal()
    return {
        "modal.Function": mock_modal.Function,
        "modal.Workflow": mock_modal.Workflow,
        "modal.Image": mock_modal.Image,
    }


def create_stripe_mock_patches():
    """
    Create patches for Stripe API.

    Returns:
        dict: Mapping of module paths to mock objects
    """
    return {
        "stripe.Customer": MockStripe.Customer,
        "stripe.Charge": MockStripe.Charge,
        "stripe.Invoice": MockStripe.Invoice,
        "stripe.Webhook": MockStripe.Webhook,
    }


def create_rdkit_mock_patches():
    """
    Create patches for RDKit.

    Returns:
        dict: Mapping of module paths to mock objects
    """
    mock_rdkit = MockRDKit()
    return {
        "rdkit.Chem.MolFromSmiles": mock_rdkit.Chem.MolFromSmiles,
        "rdkit.Chem.MolToSmiles": mock_rdkit.Chem.MolToSmiles,
        "rdkit.Chem.AddHs": mock_rdkit.Chem.AddHs,
        "rdkit.Chem.AllChem.EmbedMolecule": mock_rdkit.AllChem.EmbedMolecule,
        "rdkit.Chem.Descriptors.MolWt": mock_rdkit.Descriptors.MolWt,
        "rdkit.Chem.Descriptors.MolLogP": mock_rdkit.Descriptors.MolLogP,
    }


def create_pdb_mock_patches():
    """
    Create patches for PDB operations.

    Returns:
        dict: Mapping of module paths to mock objects
    """
    mock_pdb = MockPDB()
    return {
        "Bio.PDB.PDBList.retrieve_pdb_file": mock_pdb.download,
        "fetch_pdb": mock_pdb.fetch,
    }


def create_all_mock_patches():
    """
    Create all mock patches for external APIs.

    Returns:
        dict: Combined mapping of all module paths to mock objects
    """
    all_patches = {}
    all_patches.update(create_quantum_mock_patches())
    all_patches.update(create_modal_mock_patches())
    all_patches.update(create_stripe_mock_patches())
    all_patches.update(create_rdkit_mock_patches())
    all_patches.update(create_pdb_mock_patches())
    return all_patches


# Export all mock classes and utilities
__all__ = [
    # IBM Quantum
    "MockIBMQuantum",
    "MockQuantumCircuit",
    "MockQuantumJob",
    "MockQuantumResult",
    "MockQuantumCounts",
    "MockBackend",
    # Modal
    "MockModal",
    "MockModalFunction",
    "MockModalWorkflow",
    "MockModalResult",
    # Stripe
    "MockStripe",
    "MockStripeCustomer",
    "MockStripeCharge",
    "MockStripeInvoice",
    "MockStripeWebhook",
    # RDKit
    "MockRDKit",
    "MockMolecule",
    "MockAtom",
    "MockBond",
    "MockConformer",
    # PDB
    "MockPDB",
    "MockProteinStructure",
    # Utility Functions
    "create_quantum_mock_patches",
    "create_modal_mock_patches",
    "create_stripe_mock_patches",
    "create_rdkit_mock_patches",
    "create_pdb_mock_patches",
    "create_all_mock_patches",
]
