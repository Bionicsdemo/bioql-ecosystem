# 🔧 Final Fix: Billing Integration Issue

## ❌ Root Cause

```
ModuleNotFoundError: No module named 'billing_integration'
```

**Problem:** Modal volumes aren't loaded at Python import time. When the agent tries to:
```python
sys.path.insert(0, "/billing")
from billing_integration import authenticate_api_key
```

The `/billing` directory from the volume doesn't exist yet, causing import failure.

---

## ✅ Solution: Use Modal Mount

Instead of loading `billing_integration.py` from a Volume, we should use a **Modal Mount** which is available at import time.

### Quick Fix (5 minutes):

**Edit: `/Users/heinzjungbluth/Desktop/bioql/modal/bioql_agent_simple.py`**

Change this:
```python
@app.function(volumes={"/billing": billing_volume, "/model": model_volume})
@modal.fastapi_endpoint(method="POST")
def simple_agent(request: dict) -> dict:
    import sys
    sys.path.insert(0, "/billing")
    from billing_integration import ...  # ❌ FAILS
```

To this:
```python
# At the top of the file, create mount
billing_mount = modal.Mount.from_local_dir(
    "/Users/heinzjungbluth/Desktop/bioql/modal",
    remote_path="/root/billing"
)

@app.function(
    volumes={"/billing": billing_volume, "/model": model_volume},
    mounts=[billing_mount]  # ✅ Add mount
)
@modal.fastapi_endpoint(method="POST")
def simple_agent(request: dict) -> dict:
    import sys
    sys.path.insert(0, "/root/billing")
    from billing_integration import ...  # ✅ WORKS
```

---

## 🚀 Alternative: Inline the Code

Copy the billing functions directly into the agent file (simpler but less maintainable):

```python
# At top of bioql_agent_simple.py
import hashlib
import sqlite3
from typing import Dict, Any

DATABASE_PATH = "/billing/bioql_billing.db"

def authenticate_api_key(api_key: str) -> Dict[str, Any]:
    # ... copy function from billing_integration.py ...

def check_sufficient_balance(user_id: str, estimated_cost: float = 0.01) -> Dict[str, Any]:
    # ... copy function ...

def log_inference_usage(...):
    # ... copy function ...
```

---

## 🎯 Recommended Approach

**Use Modal Mount** - it's cleaner and allows code reuse.

**Steps:**
1. Add mount to both agents (simple + template)
2. Redeploy both agents
3. Test with API key
4. ✅ Should work!

---

## 📝 Your API Key (Ready to Use)

```
bioql_test_710344a04088413d8778d6f3
```

Once the fix is applied, add this to VSCode settings and you're good to go!
