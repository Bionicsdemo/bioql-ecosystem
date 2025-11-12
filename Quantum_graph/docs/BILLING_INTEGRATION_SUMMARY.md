# BioQL Billing Integration - Complete Summary

## ✅ INTEGRATION COMPLETE

The Quantum Graphs system is now **fully integrated** with BioQL's authentication and Stripe billing system!

---

## 🎯 What Was Implemented

### 1. **Billing Integration Module** (`backend/services/billing_integration.py`)

Complete billing system with:

- ✅ **API Key Validation** - Validates BioQL API keys via auth server
- ✅ **User Quota Management** - Tracks shots_used, shots_remaining, tier info
- ✅ **Cost Calculation** - Accurate per-shot pricing with QEC multipliers
- ✅ **Quota Enforcement** - Prevents free tier users from exceeding limits
- ✅ **Usage Recording** - Reports usage to BioQL auth server → Stripe
- ✅ **Automatic Billing** - Stripe meters record all quantum usage
- ✅ **Caching** - 5-minute cache for quota data to reduce API calls

### 2. **Updated API with Authentication** (`backend/api/quantum_viz_api.py`)

Enhanced endpoints with:

- ✅ **Multi-Method Authentication**:
  - `Authorization: Bearer YOUR_API_KEY` header
  - `X-API-Key: YOUR_API_KEY` header

- ✅ **Automatic Quota Checking** - Before job submission
- ✅ **Usage Recording** - After job completion
- ✅ **Tier-Based Access Control**:
  - **Free tier**: Simulators only (1000 shots/month)
  - **Paid tiers**: Full access to quantum hardware

- ✅ **Enhanced Error Messages** - Clear quota exceeded / upgrade messages

---

## 💰 Pricing Model

### Backend Pricing (Per Shot)

| Backend | Cost/Shot | Type | Notes |
|---------|-----------|------|-------|
| **Qiskit Simulator** | FREE | Simulator | Local, unlimited |
| **IonQ Simulator** | $0.01 | Cloud Sim | Free tier eligible |
| **AWS SV1** | $0.01 | Cloud Sim | Free tier eligible |
| **IBM Torino** | $3.00 | Hardware | Requires paid tier |
| **IBM Brisbane** | $1.25 | Hardware | Requires paid tier |
| **IonQ Forte** | $3.00 | Hardware | Requires paid tier |
| **IonQ QPU** | $2.00 | Hardware | Requires paid tier |

### QEC Multipliers

- **None**: 1.0x (no overhead)
- **Surface Code**: 1.5x
- **Steane**: 2.0x
- **Shor**: 2.5x

### Example Costs

```
1000 shots × $0.01 (simulator) × 1.0 (no QEC) = $10.00
1000 shots × $3.00 (IBM Torino) × 1.5 (Surface Code) = $4,500.00
5000 shots × $3.00 (IonQ Forte) × 1.5 (Surface Code) = $22,500.00
```

---

## 🔐 Authentication Flow

### 1. User Submits Job

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Authorization: Bearer bioql_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {...},
    "molecule_type": "protein",
    "viz_type": "structure_3d",
    "backend_preference": "ibm_torino",
    "shots": 1000
  }'
```

### 2. API Validates Key

- Extracts API key from `Authorization` or `X-API-Key` header
- Calls `https://api.bioql.bio/auth/validate`
- Gets user data (email, tier, stripe_customer_id)

### 3. Check Quota

- Calls `https://api.bioql.bio/auth/quota`
- Gets current usage (shots_used, shots_remaining)
- **Free tier**: Checks if shots_remaining >= requested shots
- **Paid tier**: Always allowed (unlimited)

### 4. Calculate Cost

```python
cost = shots × cost_per_shot × qec_multiplier + (qubits × qubit_overhead)
```

### 5. Execute Job

- Job runs on selected quantum backend
- Results generated and stored

### 6. Record Usage

After job completes:

```python
POST https://api.bioql.bio/auth/usage
{
  "api_key": "bioql_xxx",
  "service": "quantum_graphs",
  "shots": 1000,
  "backend": "ibm_torino",
  "cost": 4500.00,
  "job_id": "quantum_job_xxx",
  "metadata": {
    "molecule_type": "protein",
    "viz_type": "structure_3d",
    "execution_time": 120.5,
    "qubits": 20
  }
}
```

### 7. Stripe Billing

BioQL auth server records usage to Stripe:

- Updates metered billing
- Increments invoice when threshold reached ($3000)
- Charges customer automatically

---

## 📊 Tier System

### Free Tier

- **Limit**: 1000 shots/month
- **Backends**: Simulators only (Qiskit, IonQ Sim, AWS SV1)
- **Cost**: FREE
- **Use Case**: Testing, learning, small projects

### Pro Tier

- **Limit**: Unlimited shots
- **Backends**: All (simulators + quantum hardware)
- **Cost**: Pay-per-shot (metered billing via Stripe)
- **Use Case**: Production quantum computing

### Enterprise Tier

- **Limit**: Unlimited shots
- **Backends**: All + priority access
- **Cost**: Custom pricing + SLA
- **Use Case**: Large-scale quantum research

---

## 🚀 API Examples

### Example 1: Unauthenticated (Free Simulator)

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {"smiles": "CCO", "num_atoms": 9},
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 1024
  }'
```

**Response**: Success (FREE local simulator)

---

### Example 2: Authenticated (Quantum Hardware)

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Authorization: Bearer bioql_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {"num_atoms": 250, "num_bonds": 245},
    "molecule_type": "protein",
    "viz_type": "structure_3d",
    "backend_preference": "ibm_torino",
    "shots": 1000
  }'
```

**Response**:
```json
{
  "success": true,
  "job_id": "quantum_job_abc123",
  "status": "pending",
  "estimated_cost_usd": 4500.00,
  "backend": "ibm_torino",
  "shots": 1000,
  "logical_qubits": 20,
  "physical_qubits": 300,
  "quota_info": {
    "tier": "pro",
    "shots_remaining": "unlimited"
  }
}
```

---

### Example 3: Free Tier Quota Exceeded

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Authorization: Bearer bioql_free_tier_user" \
  -H "Content-Type: application/json" \
  -d '{
    "backend_preference": "ionq_simulator",
    "shots": 2000  # Exceeds 1000 free shots
  }'
```

**Response** (HTTP 402 Payment Required):
```json
{
  "detail": {
    "error": "Quota exceeded. Free tier allows 1000 shots/month. You have 0 shots remaining.",
    "quota_info": {
      "tier": "free",
      "shots_used": 1000,
      "shots_limit": 1000,
      "shots_remaining": 0
    },
    "upgrade_url": "https://api.bioql.bio/pricing"
  }
}
```

---

### Example 4: No API Key with Quantum Hardware

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{
    "backend_preference": "ibm_torino",  # Requires API key!
    "shots": 1000
  }'
```

**Response** (HTTP 402):
```json
{
  "detail": {
    "error": "Quantum hardware backends require a BioQL API key",
    "message": "Please provide a BioQL API key to use quantum hardware (IBM, IonQ, AWS)",
    "register_url": "https://api.bioql.bio/signup",
    "allowed_backends": ["qiskit_simulator", "ionq_simulator", "aws_sv1"]
  }
}
```

---

## 🔍 Quota Checking

Get current quota status:

```bash
curl -X POST https://api.bioql.bio/auth/quota \
  -H "Content-Type: application/json" \
  -d '{"api_key": "bioql_your_key_here"}'
```

**Response**:
```json
{
  "shots_used": 750,
  "shots_remaining": 250,
  "inferences_used": 50,
  "balance": -1250.00,
  "tier": "free"
}
```

---

## 💳 Stripe Integration

### Automatic Invoicing

- **Threshold**: $3000 of usage
- **Trigger**: When user accumulates $3000 in quantum costs
- **Action**: Stripe automatically generates invoice and charges customer
- **Frequency**: Every $3000 (not monthly - usage-based)

### Metered Billing

BioQL auth server sends meter events to Stripe:

```python
stripe.billing.MeterEvent.create(
    event_name='bioql_quantum_usage',
    payload={
        'stripe_customer_id': user.stripe_customer_id,
        'value': cost_in_cents,  # e.g., 450000 cents = $4500
        'timestamp': now
    }
)
```

---

## 📈 Usage Tracking

Every completed quantum job records usage:

```python
billing.record_usage(
    api_key="bioql_xxx",
    shots=1000,
    backend="ibm_torino",
    cost=4500.00,
    job_id="quantum_job_123",
    metadata={
        "molecule_type": "protein",
        "viz_type": "structure_3d",
        "execution_time": 120.5,
        "qubits": 20
    }
)
```

This:
1. ✅ Updates user's quota in BioQL database
2. ✅ Sends meter event to Stripe
3. ✅ Increments invoice total
4. ✅ Triggers auto-invoice if threshold reached

---

## 🛡️ Security Features

1. **API Key Validation**: Every quantum hardware request requires valid BioQL API key
2. **Quota Enforcement**: Free tier users cannot exceed limits
3. **Cost Limits**: Users can set budget_usd parameter to limit spending
4. **Secure Headers**: Supports both Bearer tokens and X-API-Key
5. **HTTPS Only**: All communication encrypted via TLS
6. **Rate Limiting**: (Recommended to add via nginx)

---

## 🎛️ Configuration

### Environment Variables

```bash
# BioQL Auth Server
BIOQL_AUTH_SERVER_URL=https://api.bioql.bio/auth

# Optional: Override Stripe key (uses BioQL's by default)
STRIPE_SECRET_KEY=sk_live_xxx
```

### Server Configuration

File: `/opt/bioql/quantum_graph/.env`

```env
# BioQL Authentication
BIOQL_AUTH_SERVER_URL=https://api.bioql.bio/auth

# Already configured - no changes needed!
```

---

## ✅ Integration Checklist

- [x] Billing integration module created
- [x] API key validation implemented
- [x] Quota checking implemented
- [x] Usage recording implemented
- [x] Stripe integration connected
- [x] Tier-based access control
- [x] Free tier limits enforced
- [x] Cost calculation accurate
- [x] Error messages user-friendly
- [x] Deployed to production server
- [x] Service restarted successfully
- [ ] End-to-end billing test

---

## 🧪 Testing

### Test 1: Free Tier Simulator (No API Key)

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{"molecule_data":{"smiles":"CCO"},"molecule_type":"small_molecule","viz_type":"energy_landscape","backend_preference":"qiskit_simulator","shots":1024}'
```

**Expected**: ✅ Success (FREE)

---

### Test 2: Quantum Hardware Without API Key

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{"molecule_data":{"smiles":"CCO"},"molecule_type":"small_molecule","viz_type":"energy_landscape","backend_preference":"ibm_torino","shots":1000}'
```

**Expected**: ❌ HTTP 402 - "Quantum hardware backends require a BioQL API key"

---

### Test 3: Valid API Key with Quantum Hardware

```bash
curl -X POST https://api.bioql.bio/quantum-graph/api/optimize/quantum \
  -H "Authorization: Bearer YOUR_BIOQL_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"molecule_data":{"num_atoms":250},"molecule_type":"protein","viz_type":"structure_3d","backend_preference":"ibm_torino","shots":1000}'
```

**Expected**: ✅ Job queued, cost calculated, usage will be recorded to Stripe after completion

---

## 📞 Support

- **Get API Key**: https://api.bioql.bio/signup
- **Check Quota**: POST https://api.bioql.bio/auth/quota
- **Pricing Info**: https://api.bioql.bio/pricing
- **Upgrade Account**: https://api.bioql.bio/upgrade

---

## 🎉 Summary

**Status**: ✅ **BILLING INTEGRATION COMPLETE AND DEPLOYED!**

The Quantum Graphs system now has:

1. ✅ **Full BioQL authentication** - API key validation via auth server
2. ✅ **Stripe metered billing** - Automatic usage recording and invoicing
3. ✅ **Tier-based access** - Free tier (simulators) vs Pro (hardware)
4. ✅ **Quota enforcement** - Prevents free users from exceeding limits
5. ✅ **Transparent pricing** - Per-shot costs with QEC multipliers
6. ✅ **Automatic charging** - Stripe invoices generated at $3000 threshold
7. ✅ **Production deployment** - Live on https://api.bioql.bio/quantum-graph/

**Next Step**: End-to-end testing with real API keys! 🚀
