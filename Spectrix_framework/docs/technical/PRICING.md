# BioQL Quantum Computing Platform - Pricing Guide

Welcome to BioQL, the premier quantum computing platform designed specifically for biological and pharmaceutical research. Our transparent pricing model combines the flexibility of pay-per-use quantum computing with the predictability of subscription plans.

## 📊 Pricing Overview

BioQL uses a **hybrid pricing model** that combines:
- **Pay-per-shot** quantum execution costs
- **Subscription plans** for higher quotas and premium features
- **Complexity-based pricing** that scales with your quantum circuit requirements

### Base Pricing Structure

| Resource | Simulator | Real Hardware |
|----------|-----------|---------------|
| **Cost per shot** | $0.001 | $0.01 |
| **Minimum charge** | $0.001 | $0.01 |

### Complexity Multipliers

Your costs scale based on quantum circuit complexity:

| Circuit Size | Multiplier | Example Cost (1000 shots, simulator) |
|--------------|------------|--------------------------------------|
| **1-4 qubits** | 1.0× | $1.00 |
| **5-8 qubits** | 2.0× | $2.00 |
| **9+ qubits** | 5.0× | $5.00 |

### Algorithm Premium Pricing

Advanced quantum algorithms have premium pricing:

| Algorithm Type | Multiplier | Use Cases |
|----------------|------------|-----------|
| **Basic gates** | 1.0× | Simple quantum circuits, educational use |
| **VQE** | 3.0× | Protein folding, molecular optimization |
| **Grover's** | 3.0× | Database search, pattern matching |
| **Shor's** | 3.0× | Cryptography, factorization |
| **QAOA** | 2.0× | Optimization problems, drug discovery |
| **Custom** | 1.5× | Research algorithms, experimental methods |

## 💳 Subscription Plans

Choose the plan that fits your research needs:

### 🆓 Free Tier - $0/month

Perfect for learning and small experiments.

**Included:**
- ✅ 1,000 quantum shots per month
- ✅ Up to 4 qubits
- ✅ Simulator access only
- ✅ Basic quantum algorithms
- ✅ Community support
- ✅ 10 API calls per minute

**Limits:**
- ❌ No real hardware access
- ❌ No priority support
- ❌ No advanced analytics

### 🔬 Basic Research - $99/month

For individual researchers and small teams.

**Everything in Free, plus:**
- ✅ 50,000 quantum shots per month
- ✅ Up to 8 qubits
- ✅ Real quantum hardware access (IBM Quantum, IonQ)
- ✅ Advanced algorithms (VQE, QAOA)
- ✅ Usage analytics
- ✅ Email support
- ✅ 60 API calls per minute

**Annual savings:** $198 (save 2 months) - $990/year

### 🧬 Professional - $499/month

For professional research teams and biotech companies.

**Everything in Basic, plus:**
- ✅ 500,000 quantum shots per month
- ✅ Up to 16 qubits
- ✅ All quantum backends
- ✅ Custom algorithms support
- ✅ Advanced analytics & cost optimization
- ✅ Priority support (email + chat)
- ✅ Team management features
- ✅ 120 API calls per minute

**Annual savings:** $998 (save 2 months) - $4,990/year

### 🏢 Enterprise - $2,999/month

For large pharmaceutical companies and research institutions.

**Everything in Professional, plus:**
- ✅ **Unlimited quantum shots**
- ✅ **Unlimited qubits**
- ✅ Dedicated customer success manager
- ✅ Volume pricing discounts
- ✅ On-premise deployment options
- ✅ Custom API integration
- ✅ 99.9% SLA guarantee
- ✅ 300 API calls per minute

**Annual savings:** $5,988 (save 2 months) - $29,990/year

## 💰 Cost Examples

### Example 1: Basic Quantum Circuit (2 qubits, simulator)
```
Base cost: $0.001 per shot
Complexity: 1.0× (2 qubits)
Algorithm: 1.0× (basic gates)

1,000 shots = $0.001 × 1,000 × 1.0 × 1.0 = $1.00
```

### Example 2: Protein Folding with VQE (6 qubits, simulator)
```
Base cost: $0.001 per shot
Complexity: 2.0× (6 qubits)
Algorithm: 3.0× (VQE)

2,000 shots = $0.001 × 2,000 × 2.0 × 3.0 = $12.00
```

### Example 3: Drug Discovery on Real Hardware (8 qubits, IBM Quantum)
```
Base cost: $0.01 per shot
Complexity: 2.0× (8 qubits)
Algorithm: 2.0× (QAOA)

1,000 shots = $0.01 × 1,000 × 2.0 × 2.0 = $40.00
```

### Example 4: Large-scale Optimization (12 qubits, real hardware)
```
Base cost: $0.01 per shot
Complexity: 5.0× (12 qubits)
Algorithm: 2.0× (QAOA)

5,000 shots = $0.01 × 5,000 × 5.0 × 2.0 = $500.00
```

## 🚀 Getting Started

### 1. Sign Up and Get Your API Key

1. **Create Account**: Visit [bioql.ai/signup](https://bioql.ai/signup)
2. **Verify Email**: Check your email and verify your account
3. **Generate API Key**: Go to your dashboard and create an API key
4. **Choose Plan**: Start with Free tier or upgrade to a paid plan

### 2. Install BioQL

```bash
pip install bioql
```

### 3. Configure Environment

Create a `.env` file:

```bash
# Your BioQL API key
BIOQL_API_KEY=bioql_your_api_key_here

# Enable billing integration
BIOQL_BILLING_ENABLED=true

# Database for billing (optional - uses cloud by default)
BIOQL_BILLING_DATABASE_URL=postgresql://user:pass@localhost/bioql_billing
```

### 4. Your First Quantum Computation

```python
from bioql import quantum

# Simple example with automatic billing
result = quantum(
    "Create a Bell state and measure both qubits",
    backend="qasm_simulator",
    shots=1024,
    api_key="your_api_key_here"
)

print(f"Success: {result.success}")
print(f"Cost: ${result.cost_estimate:.4f}")
print(f"Counts: {result.counts}")
```

## 📈 Usage Monitoring

### Real-time Cost Tracking

Every quantum execution includes cost information:

```python
result = quantum(
    "Protein folding simulation using VQE",
    backend="ibm_oslo",
    shots=2048,
    api_key="your_api_key"
)

# Cost information
print(f"Total cost: ${result.cost_estimate:.4f}")
print(f"Shots executed: {result.total_shots}")
print(f"Backend used: {result.backend_name}")

# Detailed breakdown
breakdown = result.cost_breakdown
print(f"Base cost: ${breakdown['base_cost']:.4f}")
print(f"Complexity factor: {breakdown['complexity_multiplier']}")
print(f"Algorithm premium: {breakdown['algorithm_multiplier']}")
```

### Quota Management

Check your remaining quota:

```python
from bioql.billing import get_quota_status

status = get_quota_status(api_key="your_api_key")
print(f"Monthly shots used: {status['shots_used']}")
print(f"Monthly shots remaining: {status['shots_remaining']}")
print(f"Current plan: {status['plan_name']}")
```

### Monthly Billing Summary

```python
from bioql.billing import get_billing_summary

summary = get_billing_summary(
    api_key="your_api_key",
    month="2024-03"
)

print(f"Total spent: ${summary['total_cost']:.2f}")
print(f"Total shots: {summary['total_shots']:,}")
print(f"Most used backend: {summary['top_backend']}")
```

## 🔧 Advanced Features

### Session Management

Group related computations for better tracking:

```python
session_id = "drug_discovery_project_2024"

# Multiple related computations
for molecule in molecule_list:
    result = quantum(
        f"Analyze binding affinity for {molecule}",
        backend="ibm_brisbane",
        shots=1024,
        api_key="your_api_key",
        session_id=session_id
    )

    print(f"Molecule {molecule}: ${result.cost_estimate:.4f}")
```

### Cost Estimation

Preview costs before execution:

```python
from bioql.billing import estimate_cost

estimate = estimate_cost(
    program="Complex drug discovery simulation",
    backend="ibm_brisbane",
    shots=5000,
    api_key="your_api_key"
)

print(f"Estimated cost: ${estimate['total_cost']:.2f}")
print(f"Circuit complexity: {estimate['complexity_factor']}")
print(f"Algorithm type: {estimate['algorithm_type']}")

# Proceed with execution if cost is acceptable
if estimate['total_cost'] < 100.00:
    result = quantum(program, backend="ibm_brisbane", shots=5000)
```

### Batch Operations

Optimize costs with batch processing:

```python
from bioql import quantum_batch

programs = [
    "Protein folding - configuration 1",
    "Protein folding - configuration 2",
    "Protein folding - configuration 3"
]

results = quantum_batch(
    programs=programs,
    backend="qasm_simulator",
    shots=1024,
    api_key="your_api_key"
)

total_cost = sum(r.cost_estimate for r in results)
print(f"Batch total cost: ${total_cost:.4f}")
```

## 💡 Cost Optimization Tips

### 1. Use Simulators for Development
- **Simulators are 10x cheaper** than real hardware
- Perfect for algorithm development and testing
- Scale to real hardware only when needed

### 2. Optimize Shot Counts
- Start with fewer shots for testing (100-500)
- Increase shots only for final results
- Consider statistical requirements vs. cost

### 3. Circuit Optimization
- **Minimize qubit count** when possible (huge cost savings)
- Optimize circuit depth
- Use built-in optimizations

### 4. Algorithm Selection
- Use basic algorithms when possible (1x multiplier)
- Reserve premium algorithms (VQE, Grover) for specific needs
- Consider custom implementations for repeated use

### 5. Plan Selection
- **Free tier**: Perfect for learning and small experiments
- **Basic**: Good for regular research with hardware access
- **Professional**: Cost-effective for teams with high usage
- **Enterprise**: Best value for large-scale operations

## 📞 Support and Contact

### Technical Support
- **Free tier**: Community forum
- **Basic+**: Email support (24-48h response)
- **Professional+**: Priority email + chat
- **Enterprise**: Dedicated customer success manager

### Sales and Custom Pricing
- **Email**: sales@bioql.ai
- **Phone**: +1-555-QUANTUM
- **Custom solutions**: enterprise@bioql.ai

### Billing Questions
- **Email**: billing@bioql.ai
- **Self-service**: Dashboard billing section
- **Invoice history**: Available in your account

## 🔒 Security and Compliance

- **SOC 2 Type II** certified
- **HIPAA compliant** for healthcare research
- **Data encryption** at rest and in transit
- **EU GDPR** compliant
- **Regular security audits**

## 📋 Terms and Conditions

### Fair Use Policy
- Computational resources are shared fairly among users
- Excessive usage may be throttled
- Enterprise customers get dedicated resources

### Payment Terms
- **Subscriptions**: Billed monthly or annually
- **Usage charges**: Billed monthly in arrears
- **Payment methods**: Credit card, ACH, wire transfer (Enterprise)
- **Currencies**: USD (primary), EUR, GBP available

### Refund Policy
- **Subscriptions**: Pro-rated refunds for downgrades
- **Usage charges**: No refunds for successful computations
- **Failed jobs**: Automatic credits applied

---

*Ready to start your quantum computing journey? [Sign up today](https://bioql.ai/signup) and get $10 in free credits!*

**Last updated**: March 2024 | **Version**: 2.1
