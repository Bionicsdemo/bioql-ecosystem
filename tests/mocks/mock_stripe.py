# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Mock Stripe Client for testing billing
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MockStripeCustomer:
    """Mock Stripe customer"""

    id: str
    email: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    balance: int = 0


@dataclass
class MockStripeCharge:
    """Mock Stripe charge"""

    id: str
    amount: int
    currency: str
    customer: str
    status: str = "succeeded"
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))


@dataclass
class MockStripeInvoice:
    """Mock Stripe invoice"""

    id: str
    customer: str
    amount_due: int
    amount_paid: int
    status: str
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))


class MockStripeClient:
    """Mock Stripe API client"""

    def __init__(self, api_key: str = "sk_test_mock"):
        self.api_key = api_key
        self.customers = {}
        self.charges = {}
        self.invoices = {}
        self.webhook_events = []

    class Customer:
        """Mock Customer API"""

        def __init__(self, parent):
            self.parent = parent

        def create(self, email: str, metadata: Dict = None) -> MockStripeCustomer:
            """Create customer"""
            customer_id = f"cus_{uuid.uuid4().hex[:14]}"
            customer = MockStripeCustomer(id=customer_id, email=email, metadata=metadata or {})
            self.parent.customers[customer_id] = customer
            return customer

        def retrieve(self, customer_id: str) -> MockStripeCustomer:
            """Retrieve customer"""
            return self.parent.customers.get(customer_id)

        def list(self, limit: int = 10) -> Dict[str, Any]:
            """List customers"""
            customers = list(self.parent.customers.values())[:limit]
            return {"data": customers, "has_more": len(self.parent.customers) > limit}

    class Charge:
        """Mock Charge API"""

        def __init__(self, parent):
            self.parent = parent

        def create(self, amount: int, currency: str, customer: str, **kwargs) -> MockStripeCharge:
            """Create charge"""
            charge_id = f"ch_{uuid.uuid4().hex[:14]}"
            charge = MockStripeCharge(
                id=charge_id, amount=amount, currency=currency, customer=customer
            )
            self.parent.charges[charge_id] = charge
            return charge

        def retrieve(self, charge_id: str) -> MockStripeCharge:
            """Retrieve charge"""
            return self.parent.charges.get(charge_id)

    class Invoice:
        """Mock Invoice API"""

        def __init__(self, parent):
            self.parent = parent

        def create(self, customer: str, **kwargs) -> MockStripeInvoice:
            """Create invoice"""
            invoice_id = f"in_{uuid.uuid4().hex[:14]}"
            invoice = MockStripeInvoice(
                id=invoice_id,
                customer=customer,
                amount_due=kwargs.get("amount_due", 0),
                amount_paid=0,
                status="draft",
            )
            self.parent.invoices[invoice_id] = invoice
            return invoice

        def finalize(self, invoice_id: str) -> MockStripeInvoice:
            """Finalize invoice"""
            invoice = self.parent.invoices.get(invoice_id)
            if invoice:
                invoice.status = "open"
            return invoice

        def pay(self, invoice_id: str) -> MockStripeInvoice:
            """Pay invoice"""
            invoice = self.parent.invoices.get(invoice_id)
            if invoice:
                invoice.status = "paid"
                invoice.amount_paid = invoice.amount_due
            return invoice

        def list(self, customer: str = None, limit: int = 10) -> Dict[str, Any]:
            """List invoices"""
            invoices = list(self.parent.invoices.values())
            if customer:
                invoices = [inv for inv in invoices if inv.customer == customer]
            invoices = invoices[:limit]
            return {"data": invoices, "has_more": len(invoices) > limit}

    def __init__(self, api_key: str = "sk_test_mock"):
        self.api_key = api_key
        self.customers = {}
        self.charges = {}
        self.invoices = {}
        self.webhook_events = []

        # Initialize nested APIs
        self.Customer = self.Customer(self)
        self.Charge = self.Charge(self)
        self.Invoice = self.Invoice(self)

    def construct_event(self, payload: str, sig_header: str, secret: str) -> Dict[str, Any]:
        """Mock webhook event construction"""
        import json

        event_id = f"evt_{uuid.uuid4().hex[:14]}"
        event = {
            "id": event_id,
            "type": "invoice.payment_succeeded",
            "data": json.loads(payload) if isinstance(payload, str) else payload,
        }
        self.webhook_events.append(event)
        return event

    def reset(self):
        """Reset all mock data"""
        self.customers.clear()
        self.charges.clear()
        self.invoices.clear()
        self.webhook_events.clear()
