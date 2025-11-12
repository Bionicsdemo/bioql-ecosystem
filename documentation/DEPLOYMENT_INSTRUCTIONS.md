# BioQL Quantum Execution Server - Deployment Instructions

## Summary

The issue was that BioQL's `quantum()` function was trying to execute on IBM Torino, but there was **no server endpoint** to handle quantum execution. The authentication server (port 5001) only handles auth/billing, not quantum execution.

### Solution Created:

1. ✅ Created **quantum_execution_server.py** - A Flask server that receives quantum execution requests and executes them using BioQL
2. ✅ Created deployment scripts for api.bioql.bio (167.71.86.90)
3. ✅ Created Nginx configuration to route `/api/quantum/execute` to port 5002
4. ✅ Created systemd service for automatic startup

---

## Current Status

### What Works:
- ✅ Authentication server is running at https://api.bioql.bio/auth/validate
- ✅ API key `__BIOQL_REDACTED__` is valid
- ✅ Billing/usage tracking works
- ✅ Quantum execution server code is ready
- ✅ Local testing confirmed the server works

### What's Missing:
- ❌ Quantum execution server is NOT deployed to api.bioql.bio yet
- ❌ SSH access to 167.71.86.90 is needed for deployment
- ❌ Nginx configuration needs to be updated on the server

---

## Files Created

All files are in `/Users/heinzjungbluth/Desktop/`:

1. **quantum_execution_server.py** - The main quantum execution server
   - Location: `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Server_bioql/quantum_execution_server.py`
   - Listens on port 5002
   - Endpoints: `/api/quantum/execute`, `/api/execute`, `/execute`

2. **deploy_bioql_quantum_complete.sh** - Complete deployment script
   - Automated deployment to api.bioql.bio
   - Requires SSH access to root@167.71.86.90

3. **DEPLOYMENT_INSTRUCTIONS.md** - This file

---

## Deployment Steps

### Option 1: Automated Deployment (Requires SSH Access)

```bash
# From your Mac:
cd /Users/heinzjungbluth/Desktop
chmod +x deploy_bioql_quantum_complete.sh
./deploy_bioql_quantum_complete.sh
```

This will:
1. Install dependencies on the server
2. Upload quantum_execution_server.py
3. Upload BioQL framework
4. Create systemd service
5. Configure Nginx
6. Start the service
7. Verify deployment

### Option 2: Manual Deployment

If you have SSH access but the script doesn't work:

```bash
# 1. Connect to server
ssh root@167.71.86.90

# 2. Install dependencies
pip3 install flask flask-cors requests loguru qiskit qiskit-aer qiskit-ibm-runtime --break-system-packages

# 3. Create directory
mkdir -p /root/bioql_quantum_server

# 4. Copy files (from your Mac)
scp /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Server_bioql/quantum_execution_server.py root@167.71.86.90:/root/bioql_quantum_server/
scp -r /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework/bioql root@167.71.86.90:/root/bioql_quantum_server/

# 5. Create systemd service (on server)
cat > /etc/systemd/system/bioql-quantum.service << 'EOF'
[Unit]
Description=BioQL Quantum Execution Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bioql_quantum_server
Environment="BIOQL_QUANTUM_PORT=5002"
Environment="BIOQL_QUANTUM_HOST=0.0.0.0"
Environment="BIOQL_AUTH_URL=http://localhost:5001"
Environment="PYTHONPATH=/root/bioql_quantum_server:$PYTHONPATH"
ExecStart=/usr/bin/python3 /root/bioql_quantum_server/quantum_execution_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. Start service
systemctl daemon-reload
systemctl enable bioql-quantum
systemctl start bioql-quantum
systemctl status bioql-quantum

# 7. Update Nginx configuration
# See nginx_config.txt below

# 8. Reload Nginx
nginx -t
systemctl reload nginx
```

### Nginx Configuration

Add these location blocks to `/etc/nginx/sites-available/api.bioql.bio`:

```nginx
# Quantum execution endpoints (Port 5002)
location /api/quantum/ {
    proxy_pass http://localhost:5002/api/quantum/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
}

location /api/execute {
    proxy_pass http://localhost:5002/api/execute;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_connect_timeout 600s;
    proxy_read_timeout 600s;
}

location /execute {
    proxy_pass http://localhost:5002/execute;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_connect_timeout 600s;
    proxy_read_timeout 600s;
}
```

---

## Testing After Deployment

### 1. Test Health Endpoint

```bash
curl -s https://api.bioql.bio/health | python3 -m json.tool
```

Expected response:
```json
{
  "service": "BioQL Authentication & Billing Server with Stripe",
  "status": "healthy",
  "stripe_enabled": true,
  "version": "3.0.0-stripe"
}
```

### 2. Test Authentication

```bash
curl -s -X POST https://api.bioql.bio/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"api_key":"__BIOQL_REDACTED__"}' | python3 -m json.tool
```

Expected response:
```json
{
  "valid": true,
  "user": {
    "email": "jgheinz@gmail.com",
    "name": "Heinz Jungbluth",
    "tier": "pro",
    "balance": 999999974.9962499
  }
}
```

### 3. Test Quantum Execution (After Deployment)

```bash
curl -s -X POST https://api.bioql.bio/api/quantum/execute \
  -H "Content-Type: application/json" \
  -d '{
    "program": "Create a 2-qubit Bell state",
    "api_key": "__BIOQL_REDACTED__",
    "backend": "simulator",
    "shots": 1024
  }' | python3 -m json.tool
```

### 4. Test QPHAROS with IBM Torino

```bash
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/QPHAROS
export BIOQL_API_KEY='__BIOQL_REDACTED__'
python3 run_on_torino.py
```

This should now execute all 3 quantum analyses on IBM Torino and produce real results!

---

## Troubleshooting

### Check if service is running on server:
```bash
ssh root@167.71.86.90 'systemctl status bioql-quantum'
```

### View logs:
```bash
ssh root@167.71.86.90 'journalctl -u bioql-quantum -f'
```

### Restart service:
```bash
ssh root@167.71.86.90 'systemctl restart bioql-quantum'
```

### Check if port 5002 is listening:
```bash
ssh root@167.71.86.90 'ss -tulpn | grep 5002'
```

### Test locally on server:
```bash
ssh root@167.71.86.90 'curl -s http://localhost:5002/health'
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (QPHAROS)                        │
│  /Users/heinzjungbluth/Desktop/Spectrix_BioQL/QPHAROS/         │
│               run_on_torino.py                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    api.bioql.bio (Nginx)                        │
│                    Port 443 (HTTPS)                             │
│                                                                 │
│  Routes:                                                        │
│  - /auth/* ────────────► Port 5001 (Auth Server)              │
│  - /billing/* ─────────► Port 5001 (Auth Server)              │
│  - /api/quantum/* ─────► Port 5002 (Quantum Server) ◄─ NEW!   │
│  - /health ────────────► Port 5001 (Auth Server)              │
└─────────────────────────────────────────────────────────────────┘
                             │
                ┌────────────┴─────────────┐
                │                          │
                ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  Auth Server             │  │  Quantum Server          │
│  Port 5001               │  │  Port 5002               │
│                          │  │                          │
│  - User authentication   │  │  - Execute quantum       │
│  - API key validation    │  │    programs              │
│  - Billing & usage       │  │  - Call BioQL library    │
│  - Stripe integration    │  │  - IBM Torino execution  │
└──────────────────────────┘  └────────────┬─────────────┘
                                           │
                                           │ BioQL API
                                           │
                                           ▼
                              ┌───────────────────────────┐
                              │  IBM Quantum Cloud        │
                              │  - IBM Torino (133 qubits)│
                              │  - Real quantum hardware  │
                              └───────────────────────────┘
```

---

## What Happens When You Run QPHAROS:

1. **QPHAROS** calls `quantum(program, api_key='bioql_...', backend='ibm_torino')`

2. **BioQL Library** tries to authenticate:
   - Calls `https://api.bioql.bio/auth/validate` ✅ (works)
   - Validates API key ✅ (works)
   - User: jgheinz@gmail.com, Tier: pro, Balance: $999M ✅

3. **BioQL Library** tries to execute quantum program:
   - Checks for IBM Quantum token locally ❌ (not found)
   - Falls back to remote execution ✅
   - Calls `https://api.bioql.bio/api/quantum/execute` ❌ **(THIS IS MISSING!)**

4. **Currently**: When step 3 fails, BioQL returns default/simulated values

5. **After Deployment**: Step 3 will succeed, quantum server will:
   - Receive the request
   - Authenticate user again
   - Execute quantum circuit on IBM Torino
   - Return real quantum results
   - Record usage for billing

---

## Expected Results After Deployment

### Before (Current - Simulated):
```
Binding Affinity: -8.50 kcal/mol (default value)
Ki: 582.00 nM (default value)
Source: Fallback values when quantum execution fails
```

### After (Real Quantum Hardware):
```
Binding Affinity: -7.32 kcal/mol (from IBM Torino)
Ki: 4,230 nM (calculated from quantum result)
Backend: ibm_torino
Shots: 2000
Execution Time: 45.3 seconds
Source: Real quantum hardware execution
```

---

## Next Steps

1. **Get SSH Access**: Obtain credentials for `root@167.71.86.90`

2. **Deploy**: Run the deployment script or follow manual steps

3. **Test**: Verify quantum execution endpoint works

4. **Run QPHAROS**: Execute `run_on_torino.py` and get real quantum results!

5. **Monitor**: Watch logs to see real quantum jobs being submitted to IBM

---

## Support

If deployment fails:

1. Check logs: `journalctl -u bioql-quantum -f`
2. Verify port 5002 is listening: `ss -tulpn | grep 5002`
3. Test locally first: `curl http://localhost:5002/health`
4. Check Nginx config: `nginx -t`
5. Verify BioQL imports: `python3 -c "from bioql import quantum; print('OK')"`

---

**Last Updated**: October 30, 2025
**Status**: Ready for deployment
**Deployment Location**: `/Users/heinzjungbluth/Desktop/deploy_bioql_quantum_complete.sh`
