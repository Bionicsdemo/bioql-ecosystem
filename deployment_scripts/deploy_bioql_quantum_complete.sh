#!/bin/bash
# Complete deployment of BioQL Quantum Execution Server to api.bioql.bio

set -e

SERVER="root@167.71.86.90"

echo "████████████████████████████████████████████████████████████████████████████████"
echo "🚀 BIOQL QUANTUM SERVER - COMPLETE DEPLOYMENT"
echo "████████████████████████████████████████████████████████████████████████████████"
echo ""
echo "Target Server: api.bioql.bio (167.71.86.90)"
echo "Components:"
echo "  - Quantum Execution Server (Port 5002)"
echo "  - Nginx Reverse Proxy Configuration"
echo "  - Systemd Service Setup"
echo ""
echo "████████████████████████████████████████████████████████████████████████████████"
echo ""

# Check if we can connect to server
echo "📡 Testing connection to server..."
if ssh -o ConnectTimeout=5 $SERVER "echo 'Connection successful'" 2>/dev/null; then
    echo "✅ Connection successful"
else
    echo "❌ Cannot connect to server"
    echo "Please check:"
    echo "  1. SSH key is configured"
    echo "  2. Server is running"
    echo "  3. Firewall allows SSH"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Install Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER << 'EOF'
echo "📦 Installing Python packages..."
pip3 install flask flask-cors requests loguru --break-system-packages --quiet || true
pip3 install qiskit qiskit-aer qiskit-ibm-runtime --break-system-packages --quiet || true
echo "✅ Dependencies installed"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Create Server Directory Structure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER << 'EOF'
echo "📁 Creating directories..."
mkdir -p /root/bioql_quantum_server
mkdir -p /root/bioql_quantum_server/bioql
echo "✅ Directories created"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Upload Quantum Execution Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📤 Uploading quantum_execution_server.py..."
scp /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Server_bioql/quantum_execution_server.py $SERVER:/root/bioql_quantum_server/
echo "✅ Server file uploaded"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Upload BioQL Framework"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📤 Uploading BioQL framework (this may take a moment)..."
scp -r /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework/bioql $SERVER:/root/bioql_quantum_server/ 2>/dev/null
echo "✅ BioQL framework uploaded"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Configure Systemd Service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER << 'EOF'
echo "⚙️  Creating systemd service..."
cat > /etc/systemd/system/bioql-quantum.service << 'SERVICE'
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd
systemctl daemon-reload
echo "✅ Systemd service created"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Configure Nginx Reverse Proxy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER << 'EOF'
echo "🔧 Backing up Nginx config..."
if [ -f /etc/nginx/sites-available/api.bioql.bio ]; then
    cp /etc/nginx/sites-available/api.bioql.bio /etc/nginx/sites-available/api.bioql.bio.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup created"
fi

echo "🔧 Updating Nginx configuration..."
cat > /etc/nginx/sites-available/api.bioql.bio << 'NGINX_CONFIG'
server {
    listen 80;
    listen [::]:80;
    server_name api.bioql.bio;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.bioql.bio;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/api.bioql.bio/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.bioql.bio/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

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
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    location /execute {
        proxy_pass http://localhost:5002/execute;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_connect_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Auth/Billing endpoints (Port 5001)
    location /auth/ {
        proxy_pass http://localhost:5001/auth/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /billing/ {
        proxy_pass http://localhost:5001/billing/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /webhooks/ {
        proxy_pass http://localhost:5001/webhooks/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://localhost:5001/health;
        proxy_set_header Host $host;
    }

    location /stats {
        proxy_pass http://localhost:5001/stats;
        proxy_set_header Host $host;
    }

    location / {
        return 200 '{"service":"BioQL API","version":"3.0.0"}';
        add_header Content-Type application/json;
    }

    access_log /var/log/nginx/api.bioql.bio.access.log;
    error_log /var/log/nginx/api.bioql.bio.error.log;
}
NGINX_CONFIG

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration valid"
    systemctl reload nginx
    echo "✅ Nginx reloaded"
else
    echo "❌ Nginx configuration error!"
    exit 1
fi
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 7: Start Quantum Execution Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER << 'EOF'
echo "🚀 Starting BioQL Quantum service..."
systemctl enable bioql-quantum
systemctl restart bioql-quantum

sleep 3

# Check status
if systemctl is-active --quiet bioql-quantum; then
    echo "✅ Quantum Execution Server is running"
else
    echo "❌ Failed to start Quantum Execution Server"
    echo "Checking logs..."
    journalctl -u bioql-quantum -n 50 --no-pager
    exit 1
fi
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 8: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "🧪 Testing endpoints..."
echo ""

echo "1️⃣  Testing health endpoint..."
HEALTH=$(curl -s https://api.bioql.bio/health)
if [ $? -eq 0 ]; then
    echo "✅ Health endpoint working"
    echo "   Response: $HEALTH"
else
    echo "❌ Health endpoint failed"
fi

echo ""
echo "2️⃣  Testing auth validation..."
AUTH=$(curl -s -X POST https://api.bioql.bio/auth/validate \
    -H "Content-Type: application/json" \
    -d '{"api_key":"__BIOQL_REDACTED__"}')
if [ $? -eq 0 ]; then
    echo "✅ Auth endpoint working"
    echo "   Response: $AUTH" | head -c 200
    echo "..."
else
    echo "❌ Auth endpoint failed"
fi

echo ""
echo ""
echo "████████████████████████████████████████████████████████████████████████████████"
echo "✅ DEPLOYMENT COMPLETE!"
echo "████████████████████████████████████████████████████████████████████████████████"
echo ""
echo "📊 Service Information:"
echo "   Service Name: bioql-quantum"
echo "   Port: 5002"
echo "   Status: $(ssh $SERVER 'systemctl is-active bioql-quantum')"
echo ""
echo "🌐 Endpoints:"
echo "   Quantum Execute: https://api.bioql.bio/api/quantum/execute"
echo "   Health Check: https://api.bioql.bio/health"
echo "   Auth Validate: https://api.bioql.bio/auth/validate"
echo ""
echo "📝 Useful Commands:"
echo "   Check status: ssh $SERVER 'systemctl status bioql-quantum'"
echo "   View logs: ssh $SERVER 'journalctl -u bioql-quantum -f'"
echo "   Restart: ssh $SERVER 'systemctl restart bioql-quantum'"
echo ""
echo "🧪 Test with:"
echo "   cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/QPHAROS"
echo "   export BIOQL_API_KEY='__BIOQL_REDACTED__'"
echo "   python3 run_on_torino.py"
echo ""
echo "████████████████████████████████████████████████████████████████████████████████"
