#!/bin/bash
# Deploy Quantum_graph to Ubuntu Server
# =====================================
# Server: ubuntu-s-1vcpu-1gb-nyc3-01
# IP: 167.71.86.90
# User: root

set -e

SERVER_IP="167.71.86.90"
SERVER_USER="root"
REMOTE_PATH="/opt/bioql/quantum_graph"
LOCAL_PATH="/Users/heinzjungbluth/Desktop/Quantum_graph"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         QUANTUM_GRAPH DEPLOYMENT                                 ║"
echo "║         Server: $SERVER_IP                                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check sshpass
if ! command -v /Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass &> /dev/null; then
    echo "❌ sshpass not found"
    exit 1
fi

echo "📦 Step 1: Creating remote directory..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP \
    "mkdir -p $REMOTE_PATH/{backend,frontend,quantum_core,visualization,examples,data,logs}"

echo "✅ Remote directory created"

echo ""
echo "📤 Step 2: Uploading Quantum_graph files..."

# Upload core modules
echo "  ⚛️  Uploading quantum_core..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp scp -r \
    $LOCAL_PATH/quantum_core/* \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/quantum_core/

echo "  🎨 Uploading visualization..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp scp -r \
    $LOCAL_PATH/visualization/* \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/visualization/

echo "  🌐 Uploading backend..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp scp -r \
    $LOCAL_PATH/backend/* \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/backend/

echo "  📖 Uploading examples..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp scp -r \
    $LOCAL_PATH/examples/* \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/examples/

# Upload configuration files
echo "  ⚙️  Uploading configuration..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp scp \
    $LOCAL_PATH/requirements.txt \
    $LOCAL_PATH/setup.py \
    $LOCAL_PATH/README.md \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/

echo "✅ Files uploaded"

echo ""
echo "🐍 Step 3: Installing Python dependencies..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP << 'EOF'
cd /opt/bioql/quantum_graph

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
source venv/bin/activate

echo "  Installing core dependencies..."
pip install --upgrade pip wheel setuptools

echo "  Installing numpy, scipy, matplotlib..."
pip install numpy scipy matplotlib

echo "  Installing FastAPI and uvicorn..."
pip install fastapi uvicorn pydantic python-multipart

echo "  Installing networkx for metabolomics..."
pip install networkx

echo "  Installing from requirements.txt..."
pip install -r requirements.txt || echo "⚠️  Some optional dependencies may have failed"

echo "✅ Dependencies installed"
EOF

echo ""
echo "🔧 Step 4: Creating systemd service..."

# Create systemd service file
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP << 'EOF'
cat > /etc/systemd/system/quantum-graph.service << 'SERVICE'
[Unit]
Description=Quantum_graph Visualization API
After=network.target

[Service]
Type=simple
User=bioql
Group=bioql
WorkingDirectory=/opt/bioql/quantum_graph
Environment="PATH=/opt/bioql/quantum_graph/venv/bin"
Environment="PYTHONPATH=/opt/bioql/quantum_graph"
ExecStart=/opt/bioql/quantum_graph/venv/bin/python backend/api/quantum_viz_api.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/bioql/logs/quantum_graph.log
StandardError=append:/opt/bioql/logs/quantum_graph_error.log

[Install]
WantedBy=multi-user.target
SERVICE

echo "✅ Systemd service created"
EOF

echo ""
echo "👤 Step 5: Setting permissions..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP \
    "chown -R bioql:bioql /opt/bioql/quantum_graph"

echo "✅ Permissions set"

echo ""
echo "🚀 Step 6: Starting Quantum_graph service..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP << 'EOF'
systemctl daemon-reload
systemctl enable quantum-graph
systemctl restart quantum-graph
sleep 3
systemctl status quantum-graph --no-pager | head -20
EOF

echo ""
echo "🔥 Step 7: Configuring firewall..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP \
    "ufw allow 9000/tcp && ufw status | grep 9000"

echo "✅ Port 9000 opened"

echo ""
echo "🌐 Step 8: Configuring nginx reverse proxy..."

# Create nginx config for Quantum_graph
cat > /tmp/quantum-graph-nginx.conf << 'NGINX'
# Quantum_graph API proxy
location /api/quantum/ {
    proxy_pass http://127.0.0.1:9000/api/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
}

# Quantum_graph frontend (future)
location /quantum-graph/ {
    proxy_pass http://127.0.0.1:9000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
NGINX

# Upload and apply nginx config
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp scp \
    /tmp/quantum-graph-nginx.conf \
    $SERVER_USER@$SERVER_IP:/tmp/

/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP << 'EOF'
# Backup existing nginx config
cp /etc/nginx/sites-available/api.bioql.bio /etc/nginx/sites-available/api.bioql.bio.backup

# Insert Quantum_graph config into existing api.bioql.bio config
# Find the last location block and add our config before the closing brace
sed -i '/^}/i \
\
    # Quantum_graph API\
    location /api/quantum/ {\
        proxy_pass http://127.0.0.1:9000/api/;\
        proxy_http_version 1.1;\
        proxy_set_header Upgrade $http_upgrade;\
        proxy_set_header Connection '"'"'upgrade'"'"';\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_set_header X-Forwarded-Proto $scheme;\
        proxy_cache_bypass $http_upgrade;\
        proxy_read_timeout 300;\
        proxy_connect_timeout 300;\
        proxy_send_timeout 300;\
    }\
\
    location /quantum-graph/ {\
        proxy_pass http://127.0.0.1:9000/;\
        proxy_http_version 1.1;\
        proxy_set_header Upgrade $http_upgrade;\
        proxy_set_header Connection '"'"'upgrade'"'"';\
        proxy_set_header Host $host;\
        proxy_cache_bypass $http_upgrade;\
    }' /etc/nginx/sites-available/api.bioql.bio

# Test nginx config
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx config valid, reloading..."
    systemctl reload nginx
    echo "✅ Nginx reloaded"
else
    echo "❌ Nginx config invalid, restoring backup..."
    mv /etc/nginx/sites-available/api.bioql.bio.backup /etc/nginx/sites-available/api.bioql.bio
    exit 1
fi
EOF

echo ""
echo "🧪 Step 9: Testing deployment..."
echo "  Testing local API..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP \
    "curl -I http://127.0.0.1:9000/ 2>&1 | head -10"

echo ""
echo "  Testing via nginx..."
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP \
    "curl -I https://api.bioql.bio/api/quantum/health 2>&1 | head -10"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         ✅ QUANTUM_GRAPH DEPLOYED SUCCESSFULLY!                  ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 API Endpoints:"
echo "   https://api.bioql.bio/api/quantum/                  - API root"
echo "   https://api.bioql.bio/api/quantum/health            - Health check"
echo "   https://api.bioql.bio/api/quantum/optimize/quantum  - Optimize parameters"
echo "   https://api.bioql.bio/api/quantum/visualize/protein - Protein viz"
echo "   https://api.bioql.bio/quantum-graph/                - Web interface (future)"
echo ""
echo "📚 API Documentation:"
echo "   https://api.bioql.bio/quantum-graph/docs"
echo ""
echo "📊 Service Status:"
/Users/heinzjungbluth/Desktop/sshpass-1.09/sshpass -f /tmp/.sshpass_temp ssh $SERVER_USER@$SERVER_IP \
    "systemctl status quantum-graph --no-pager | head -10"
echo ""
echo "📝 Logs:"
echo "   sudo journalctl -u quantum-graph -f"
echo "   tail -f /opt/bioql/logs/quantum_graph.log"
echo ""
echo "🎉 Deployment complete!"
