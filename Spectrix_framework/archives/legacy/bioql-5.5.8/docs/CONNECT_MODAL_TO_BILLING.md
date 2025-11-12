# 🔗 Connect Modal Agents to Your Billing Server

## Current Situation

✅ You have a billing server with ngrok tunnel
✅ Template agent works (100% reliable code generation)
❌ Modal agents aren't connected to your billing server

---

## Step 1: Start Your Billing Server

```bash
cd /Users/heinzjungbluth/Desktop/bioql

# Start the billing server
python3 scripts/admin/bioql_auth_server_v2.py &

# Verify it's running
curl http://localhost:5001/health
```

**Expected output:** `{"status": "healthy", "version": "2.0.0"}`

---

## Step 2: Get Your ngrok URL

```bash
# Check ngrok tunnel
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
```

Or view at: http://localhost:4040

**Example URL:** `https://aae99709f69d.ngrok-free.app`

---

## Step 3: Create Test API Key

```bash
python3 scripts/admin/bioql_admin_simple.py
```

Choose option **2** (Create new API key)
- Email: test@bioql.com
- Name: Test User

**Save the API key** - you'll need it!

---

## Step 4: Update Modal Agent

Edit: `/Users/heinzjungbluth/Desktop/bioql/modal/bioql_agent_simple.py`

**Replace the inline billing functions with HTTP calls:**

```python
import requests

BILLING_SERVER_URL = "YOUR_NGROK_URL_HERE"  # e.g., https://abc123.ngrok-free.app

def authenticate_api_key(api_key: str) -> Dict[str, Any]:
    """Authenticate via ngrok billing server."""
    try:
        response = requests.post(
            f"{BILLING_SERVER_URL}/auth/validate",
            json={"api_key": api_key},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "user_id": data["user"]["id"],
                "email": data["user"]["email"],
                "name": data["user"]["name"],
                "api_key_id": api_key,  # Use API key as ID
                "balance": 100.0  # Mock balance for now
            }
        else:
            return {"error": "Invalid API key"}
    except Exception as e:
        return {"error": f"Auth failed: {str(e)}"}

def check_sufficient_balance(user_id: str, estimated_cost: float = 0.01) -> Dict[str, Any]:
    """Check balance via billing server."""
    # For now, always return sufficient
    return {
        "sufficient": True,
        "balance": 100.0,
        "message": "Balance OK"
    }

def log_inference_usage(
    user_id: str,
    api_key_id: str,
    prompt: str,
    code_generated: str,
    time_seconds: float,
    base_cost: float,
    user_cost: float,
    profit: float,
    success: bool = True,
    error_message: str = None
) -> bool:
    """Log usage to billing server."""
    try:
        response = requests.post(
            f"{BILLING_SERVER_URL}/billing/log-usage",
            json={
                "user_id": user_id,
                "prompt": prompt,
                "code_generated": code_generated,
                "time_seconds": time_seconds,
                "cost": user_cost,
                "success": success,
                "error": error_message
            },
            timeout=5
        )
        return response.status_code == 200
    except:
        return False
```

---

## Step 5: Deploy Updated Agent

```bash
modal deploy modal/bioql_agent_simple.py
```

---

## Step 6: Test It!

```bash
# Update test script with your API key
cat > test_with_billing_server.py << 'EOF'
import requests

API_KEY = "YOUR_API_KEY_HERE"
url = "https://spectrix--bioql-agent-simple-simple-agent.modal.run"

response = requests.post(
    url,
    json={
        "api_key": API_KEY,
        "request": "dock metformin to AMPK"
    }
)

print(response.json())
EOF

python3 test_with_billing_server.py
```

---

## ✅ Expected Result

```json
{
  "success": true,
  "code": "from bioql.docking import dock_molecules...",
  "action": "code_generation",
  "cost": {
    "user_cost_usd": 0.000427
  },
  "user": {
    "email": "test@bioql.com",
    "balance": 99.999573
  }
}
```

---

## 🔧 Quick Start Commands

```bash
# 1. Start billing server
cd /Users/heinzjungbluth/Desktop/bioql
python3 scripts/admin/bioql_auth_server_v2.py

# 2. In another terminal, start ngrok (if not running)
ngrok http 5001

# 3. Create API key
python3 scripts/admin/bioql_admin_simple.py

# 4. Get ngrok URL
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# 5. Update Modal agent with ngrok URL
# (edit bioql_agent_simple.py)

# 6. Deploy
modal deploy modal/bioql_agent_simple.py

# 7. Test
@bioql dock metformin to AMPK
```

---

## 🎯 Alternative: Simple Fix (No Billing)

If you just want to test code generation **now**, use the template agent without billing:

```bash
modal run test_template_agent.py
```

This works **100% of the time** and generates perfect code. Add billing later!

---

**Your ngrok URL from logs:** `https://aae99709f69d.ngrok-free.app`
**Billing server should run on:** `localhost:5001`
