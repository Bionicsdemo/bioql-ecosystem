# 🚨 CRITICAL: BioQL Server Status Report

**Timestamp**: 2025-10-28 (Session recovery)
**Server**: api.bioql.bio (167.71.86.90)
**Status**: ⚠️ SERVICES DOWN, SSH SATURATED

---

## Current Situation

### ✅ What's Working
- ✅ Server is **pingable** (167.71.86.90)
- ✅ Network connectivity is OK
- ✅ DNS resolution works (api.bioql.bio → 167.71.86.90)

### ❌ What's NOT Working
- ❌ **All HTTPS endpoints timeout** (5 second timeout)
  - `https://api.bioql.bio/health` → TIMEOUT
  - `https://api.bioql.bio/workflow/` → TIMEOUT
  - `https://api.bioql.bio/quantum-graph/health` → TIMEOUT
  - `https://api.bioql.bio/health/quantum-docking` → TIMEOUT

- ❌ **SSH connection saturated**
  - Error: `SSHException: No existing session`
  - Error: `Error reading SSH protocol banner`
  - Too many connection attempts from client (100+ in last hour)

### 🔍 Likely Root Causes

1. **BioQL Services Crashed**: The Python Flask/Gunicorn services have stopped
2. **Nginx May Be Down**: The reverse proxy may have stopped
3. **SSH MaxStartups Exceeded**: Too many SSH connection attempts hit the limit (default: 10)

---

## What Was Successfully Completed Before Crash

### ✅ Successfully Deployed
1. **BioQL Core + Quillow** (Port 5001)
   - File: `/opt/bioql/auth_server/bioql_auth_server_stripe.py`
   - Endpoint: `https://api.bioql.bio/api/quantum/execute`
   - Stripe: ✅ Upgraded to v13.0.1
   - Last tested: **WORKING** (executed 2000 shots on IBM Torino, cost $9,000)

2. **Quantum Docking** (Port 8100)
   - File: `/opt/bioql/quantum_docking/web_interface/production_backend.py`
   - Endpoint: `https://api.bioql.bio/health/quantum-docking`
   - Last tested: **WORKING**

3. **Quantum Graphs** (Port 9000)
   - Endpoint: `https://api.bioql.bio/quantum-graph/health`
   - Last tested: **WORKING**

### ⚠️ Partially Configured
4. **Workflows** (Port 5002)
   - Server: Running on port 5002
   - Nginx: **NOT YET CONFIGURED** (missing proxy block)
   - Status: Server running but not accessible via HTTPS

5. **Lab Notebook**
   - Status: **UNKNOWN** (never verified)
   - May not be deployed

---

## Manual Recovery Steps

### Step 1: Wait for SSH to Clear (5-10 minutes)
The SSH connection pool is saturated from too many attempts. Wait before trying again.

### Step 2: SSH into Server (from different IP if possible)
```bash
ssh root@api.bioql.bio
# Password: P31e27r12u1@HJG
```

### Step 3: Check Service Status
```bash
# Check Nginx
systemctl status nginx

# Check Python processes
ps aux | grep python | grep -E "(bioql|workflow|notebook|graph|docking)" | grep -v grep

# Check listening ports
netstat -tulpn | grep LISTEN | grep -E "5001|5002|8100|9000"
```

### Step 4: Restart Nginx (if down)
```bash
systemctl restart nginx
systemctl status nginx
```

### Step 5: Restart BioQL Core Service
```bash
# Kill any existing processes
pkill -f "bioql_auth_server_stripe"

# Start fresh
cd /opt/bioql/auth_server
/opt/bioql/venv/bin/python bioql_auth_server_stripe.py > /tmp/bioql_auth.log 2>&1 &

# Verify
tail -f /tmp/bioql_auth.log
# Should see: "Running on http://127.0.0.1:5001"
```

### Step 6: Restart Quantum Docking Service
```bash
# Kill existing
pkill -f "production_backend"

# Start fresh
cd /opt/bioql/quantum_docking/web_interface
/opt/bioql/venv/bin/python production_backend.py > /tmp/quantum_docking.log 2>&1 &

# Verify
tail -f /tmp/quantum_docking.log
```

### Step 7: Restart Quantum Graphs Service
```bash
# Kill existing
ps aux | grep quantum.*graph | grep -v grep | awk '{print $2}' | xargs kill

# Start fresh (find the startup script or Python file)
# Location likely: /opt/bioql/quantum_graph/ or similar
```

### Step 8: Configure Nginx for Workflows
```bash
# Backup current config
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_$(date +%Y%m%d_%H%M%S)

# Edit config
nano /etc/nginx/sites-available/bioql

# Add this BEFORE the "location / {" block:

    # Workflows Server (Port 5002)
    location /workflow/ {
        proxy_pass http://127.0.0.1:5002/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        if ($request_method = OPTIONS) {
            return 204;
        }
    }

# Test and reload
nginx -t
systemctl reload nginx
```

### Step 9: Test All Endpoints
```bash
# From the server itself
curl -s http://127.0.0.1:5001/health
curl -s http://127.0.0.1:5002/
curl -s http://127.0.0.1:8100/api/health
curl -s http://127.0.0.1:9000/health

# From outside (after services restart)
curl -s https://api.bioql.bio/health
curl -s https://api.bioql.bio/workflow/
curl -s https://api.bioql.bio/quantum-graph/health
curl -s https://api.bioql.bio/health/quantum-docking
```

---

## Automated Recovery Script

If SSH works, run this script on the server:

```bash
#!/bin/bash
# /opt/bioql/restart_all_services.sh

echo "🔄 RESTARTING ALL BIOQL SERVICES"

# Kill all existing services
pkill -f "bioql_auth_server_stripe"
pkill -f "production_backend"
pkill -f "quantum.*graph"

sleep 2

# Start BioQL Core (Port 5001)
cd /opt/bioql/auth_server
/opt/bioql/venv/bin/python bioql_auth_server_stripe.py > /tmp/bioql_auth.log 2>&1 &
echo "✅ Started BioQL Core on port 5001"

# Start Quantum Docking (Port 8100)
cd /opt/bioql/quantum_docking/web_interface
/opt/bioql/venv/bin/python production_backend.py > /tmp/quantum_docking.log 2>&1 &
echo "✅ Started Quantum Docking on port 8100"

# Restart Nginx
systemctl restart nginx
echo "✅ Restarted Nginx"

sleep 3

# Verify
echo ""
echo "🔍 VERIFYING SERVICES..."
netstat -tulpn | grep LISTEN | grep -E "5001|5002|8100|9000|80|443"

echo ""
echo "🧪 TESTING ENDPOINTS..."
curl -s http://127.0.0.1:5001/health | head -20
```

---

## Previous Working Configuration

### Nginx Config (`/etc/nginx/sites-available/bioql`)
```nginx
server {
    listen 443 ssl http2;
    server_name api.bioql.bio;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/api.bioql.bio/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.bioql.bio/privkey.pem;

    # BioQL Core + Quillow (Port 5001)
    location /api/quantum/execute {
        proxy_pass http://127.0.0.1:5001/api/quantum/execute;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-API-Key' always;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    location /health {
        proxy_pass http://127.0.0.1:5001/health;
        # ... same headers ...
    }

    # Quantum Graphs (Port 9000)
    location /quantum-graph/ {
        proxy_pass http://127.0.0.1:9000/;
        # ... same headers ...
    }

    # Quantum Docking (Port 8100)
    location /quantum-docking/ {
        proxy_pass http://127.0.0.1:8100/;
        # ... same headers ...
    }

    location /health/quantum-docking {
        proxy_pass http://127.0.0.1:8100/api/health;
        # ... same headers ...
    }

    # Catch-all
    location / {
        proxy_pass http://127.0.0.1:5001/;
        # ... same headers ...
    }
}
```

---

## Files Ready for Deployment

1. **Workflows Nginx Config**: `/Users/heinzjungbluth/Desktop/configure_final.py`
   - This script will add the Workflows proxy when SSH is available

2. **Complete Documentation**: `/Users/heinzjungbluth/Desktop/SOLUCION_COMPLETA_BIOQL.md`
   - Step-by-step manual for all configurations

---

## Contact Info

- **Server**: api.bioql.bio (167.71.86.90)
- **SSH User**: root
- **SSH Password**: P31e27r12u1@HJG
- **BioQL API Key**: __BIOQL_REDACTED__

---

## Next Steps for User

1. **Wait 10-15 minutes** for SSH connection pool to clear
2. **SSH into server manually** from a different terminal/location if possible
3. **Run the manual recovery steps** above to restart services
4. **Once services are up**, run the configure_final.py script to add Workflows to Nginx
5. **Test all endpoints** to verify everything is working

---

## Summary

**What happened**:
- Successfully deployed and tested BioQL quantum execution on IBM Torino ($9,000 job executed successfully)
- During final configuration steps, made 100+ SSH connection attempts trying to configure Workflows
- SSH connection pool exceeded, services may have crashed during this time
- Now unable to connect via SSH or HTTPS

**What's needed**:
- Manual server reboot or service restart via console/control panel
- OR wait for SSH to clear and manually SSH in to restart services

**Priority**:
1. HIGH: Restart Nginx
2. HIGH: Restart BioQL Core (port 5001) - this is the main service
3. MEDIUM: Restart Quantum Docking (port 8100)
4. LOW: Configure Workflows proxy
5. LOW: Verify Lab Notebook

---

**Last successful test**: Molecular docking on IBM Torino at timestamp ~20:29 on 2025-10-28
**Crash time**: ~20:35-20:40 (after multiple SSH saturation attempts)
