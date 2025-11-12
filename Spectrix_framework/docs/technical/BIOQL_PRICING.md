# BioQL Code Generation API - Pricing

**Last Updated**: October 2, 2025

---

## 💰 Pricing Model

### Pay-Per-Use Inference
BioQL charges based on actual GPU compute time used for code generation.

**Base Rate**: **$0.000428 per second** of inference time

---

## 📊 Typical Costs

### Average Request Costs

| Request Type | Typical Time | Estimated Cost |
|-------------|-------------|----------------|
| Simple (Bell state) | 2-3 seconds | $0.0009 - $0.0013 |
| Medium (QFT 4 qubits) | 3-4 seconds | $0.0013 - $0.0017 |
| Complex (Full algorithm) | 4-6 seconds | $0.0017 - $0.0026 |

### Monthly Estimates

| Usage Level | Requests/Month | Estimated Cost |
|------------|----------------|----------------|
| **Free Tier** | 100 requests | **$0.10 - $0.15** |
| **Light** | 1,000 requests | $1.00 - $1.50 |
| **Professional** | 10,000 requests | $10.00 - $15.00 |
| **Enterprise** | 100,000 requests | $100.00 - $150.00 |

---

## 💡 Cost Breakdown

### What You Pay For

```
User Price = Base Cost × 1.40
```

**Components**:
- **Modal GPU Time** (A10G): $1.10/hour base
- **Profit Margin**: 40%
- **Final Rate**: ~$1.54/hour or $0.000428/second

### Example Calculation

**3-second request**:
- Base Cost: 3s × $0.000306 = $0.000918
- User Price: 3s × $0.000428 = $0.001284
- Profit: $0.000366 (40% margin)

---

## 🎯 Cost Optimization Tips

### 1. Use Template Mode for Simple Queries
For basic patterns (Bell states, simple circuits), use `template` mode (free):
```json
{
  "bioql.mode": "template"
}
```

### 2. Batch Similar Requests
Group related code generation tasks together to minimize cold starts.

### 3. Cache Results Locally
Store frequently used code snippets in your project to avoid regeneration.

### 4. Set Appropriate `max_length`
Shorter `max_length` values = faster generation = lower cost:
```javascript
{
  "prompt": "Create a Bell state",
  "max_length": 150  // vs default 300
}
```

---

## 📈 Pricing Transparency

### Cost Tracking in Response

Every API response includes detailed cost information:

```json
{
  "code": "from bioql import quantum...",
  "timing": {
    "total_seconds": 2.345,
    "generation_seconds": 2.1,
    "overhead_seconds": 0.245
  },
  "cost": {
    "base_cost_usd": 0.000716,
    "user_cost_usd": 0.001003,
    "profit_usd": 0.000287,
    "profit_margin_percent": 40.0
  }
}
```

### VS Code Extension Display

When using modal mode, costs are automatically logged in the **BioQL Assistant** output channel:

```
💰 Cost Information:
   User Cost: $0.001003
   Generation Time: 2.1s
   Profit Margin: 40%
```

---

## 🆓 Free Options

### 1. Template Mode (Free)
- Pre-built code templates
- Instant responses
- No ML inference
- Limited to common patterns

### 2. Local Mode (Free, but requires resources)
- Run model on your machine
- Requires: 16GB RAM, GPU optional
- One-time setup cost
- No per-request charges

### 3. Monthly Free Tier
- **100 free requests/month** on modal mode
- Perfect for learning and experimentation
- Auto-resets monthly

---

## 💳 Billing

### How Billing Works

1. **Real-time Cost Calculation**: Each request calculates exact cost
2. **Transparent Reporting**: Costs shown in API response
3. **Usage Tracking**: Monitor in Modal dashboard
4. **Monthly Invoicing**: Consolidated bill at month end

### Payment Methods

- Credit/Debit Card
- Bank Transfer (Enterprise)
- Monthly Subscription (coming soon)

---

## 🔒 Enterprise Pricing

For high-volume users (>100K requests/month), we offer:

- **Volume Discounts**: Up to 30% off
- **Dedicated Instances**: Reserved GPU capacity
- **Custom SLAs**: Guaranteed uptime
- **Priority Support**: 24/7 assistance

**Contact**: enterprise@bioql.com

---

## 📞 Support

- **General Questions**: support@bioql.com
- **Billing Inquiries**: billing@bioql.com
- **Technical Issues**: https://github.com/bioql/bioql/issues

---

## 🔄 Price Updates

We commit to:
- ✅ 30-day notice before price changes
- ✅ Grandfathering existing contracts
- ✅ Transparent cost breakdowns
- ✅ Annual price lock for enterprise

**Current pricing valid through**: December 31, 2025

---

## 🧮 Cost Calculator

Use our interactive calculator to estimate your monthly costs:

```python
# Example: Calculate monthly cost
requests_per_month = 1000
avg_time_per_request = 3  # seconds

estimated_cost = requests_per_month * avg_time_per_request * 0.000428
print(f"Estimated Monthly Cost: ${estimated_cost:.2f}")
# Output: Estimated Monthly Cost: $1.28
```

---

## 📊 Competitor Comparison

| Provider | Cost per Request | Model Quality | Speed |
|----------|-----------------|---------------|-------|
| **BioQL** | **$0.0009 - $0.0026** | ⭐⭐⭐⭐⭐ | 2-6s |
| OpenAI Codex | $0.002 - $0.004 | ⭐⭐⭐⭐ | 3-8s |
| GitHub Copilot | $10/month (unlimited) | ⭐⭐⭐ | Variable |
| Tabnine | $12/month (unlimited) | ⭐⭐⭐ | Variable |

**BioQL Advantage**:
- Specialized for quantum computing
- Transparent, usage-based pricing
- No monthly fees (pay-as-you-go)

---

## ✅ Getting Started

1. **Sign up** at https://bioql.com
2. **Get your API key** from dashboard
3. **Configure VS Code** extension with modal mode
4. **Start generating code** - costs automatically tracked!

**First 100 requests FREE!** 🎉

---

**Questions?** Contact us at pricing@bioql.com
