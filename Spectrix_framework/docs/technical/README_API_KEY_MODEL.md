# BioQL - Quantum Computing for Bioinformatics

## 🔑 API Key Required Model

BioQL is now a cloud-based quantum computing platform where **every execution requires a valid API key** from bioql.com.

## 📦 Installation

```bash
pip install bioql
```

## 🚀 Quick Start

```python
from bioql import quantum

# ❌ This will FAIL - API key required
result = quantum("Create a Bell state")  # TypeError

# ✅ This will work - with valid API key
result = quantum(
    program="Create a 2-qubit Bell state circuit",
    backend="simulator",
    shots=100,
    api_key="bioql_your_api_key_here"  # Required!
)

print(f"Results: {result.counts}")
print(f"Cost: ${result.cost_estimate:.4f}")
```

## 🔐 Authentication

### Get Your API Key
1. Sign up at **https://bioql.com/signup**
2. Choose your plan (Free, Pro, Enterprise)
3. Get your API key from the dashboard
4. Use it in every `quantum()` call

### API Key Verification
Every call to `quantum()` performs:
- ✅ **Authentication**: Validates your API key with bioql.com
- ✅ **Usage Limits**: Checks your plan limits (shots/month, backends)
- ✅ **Billing Tracking**: Records usage for accurate billing
- ✅ **Rate Limiting**: Prevents abuse (60 calls/minute)

## 💰 Pricing Plans

| Plan | Price | Monthly Shots | Backends | Max Qubits |
|------|-------|---------------|----------|------------|
| 🆓 **Free** | $0 | 1,000 | Simulator only | 5 |
| 💰 **Pro** | $29 | 50,000 | + IBM, IonQ | 20 |
| 🏢 **Enterprise** | $299 | Unlimited | All hardware | 127 |

## 📝 Examples

### Basic Usage
```python
from bioql import quantum

# Simple quantum circuit
result = quantum(
    program="Create a Bell state and measure both qubits",
    backend="simulator",
    shots=1000,
    api_key="bioql_xyz123"
)

print(result.counts)  # {'00': 502, '11': 498}
print(result.cost_estimate)  # 0.0 (simulator is free)
```

### Premium Hardware
```python
# Real quantum hardware (Pro/Enterprise plans only)
result = quantum(
    program="Create a 4-qubit quantum Fourier transform",
    backend="ibm_quantum",
    shots=2000,
    api_key="bioql_your_pro_key"
)

print(result.cost_estimate)  # 0.70 (real hardware has cost)
```

### Error Handling
```python
try:
    result = quantum(
        program="Complex quantum algorithm",
        backend="ibm_quantum",
        shots=10000,
        api_key="bioql_free_plan_key"
    )
except Exception as e:
    if "Usage limit exceeded" in str(e):
        print("Upgrade to Pro: https://bioql.com/pricing")
    elif "Invalid API key" in str(e):
        print("Get API key: https://bioql.com/signup")
```

## 🏗️ Architecture

### User Experience
1. **Install**: `pip install bioql`
2. **Register**: Get API key at bioql.com
3. **Use**: Every quantum() call requires API key
4. **Scale**: Upgrade plan for more usage/features

### Technical Flow
```
User Code → quantum(api_key=...) → Authentication Server → Usage Check → Quantum Execution → Billing Record
```

### What's Open Source vs Proprietary
- **Open Source (GitHub/PyPI)**: Core framework, compiler, simulators
- **Proprietary (Your servers)**: Authentication, billing, usage tracking

## 🛡️ Security Features

- **API Key Hashing**: Keys are hashed before storage
- **Rate Limiting**: 60 requests/minute per user
- **Usage Validation**: Real-time limit checking
- **Secure Communication**: All auth calls over HTTPS

## 🚨 Important Changes

### Breaking Changes
- **API key is now REQUIRED** for all executions
- No default/optional API key parameter
- Local-only execution removed

### Migration Guide
```python
# OLD (will break)
result = quantum("Create Bell state")

# NEW (required)
result = quantum("Create Bell state", api_key="bioql_xxx")
```

## 📊 Usage Tracking

Every quantum execution is tracked:
- User identification
- Shots used
- Backend accessed
- Cost calculation
- Success/failure status

Users can monitor usage at: **https://bioql.com/dashboard**

## 🆘 Support

- **Get API Key**: https://bioql.com/signup
- **Pricing Info**: https://bioql.com/pricing
- **Documentation**: https://docs.bioql.com
- **Support**: support@bioql.com

## 🎯 Business Model Summary

✅ **Users get**: Easy `pip install`, powerful quantum computing, natural language interface

✅ **You control**: Authentication, billing, usage limits, access to premium hardware

✅ **Revenue streams**: Monthly subscriptions, pay-per-shot pricing, enterprise licensing

This model ensures you maintain complete control over monetization while providing a great developer experience!
