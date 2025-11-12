#!/bin/bash
# Deploy Quantum Execution Server to api.bioql.bio (167.71.86.90)

set -e

SERVER="root@167.71.86.90"
SERVER_DIR="/root/bioql_quantum_server"

echo "="*80
echo "🚀 Deploying Quantum Execution Server to api.bioql.bio"
echo "="*80

# Step 1: Create server directory
echo "📁 Creating server directory on remote..."
ssh $SERVER "mkdir -p $SERVER_DIR"

# Step 2: Copy quantum execution server
echo "📤 Uploading quantum_execution_server.py..."
scp /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Server_bioql/quantum_execution_server.py $SERVER:$SERVER_DIR/

# Step 3: Copy BioQL framework
echo "📤 Uploading BioQL framework..."
ssh $SERVER "mkdir -p $SERVER_DIR/bioql"
scp -r /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework/bioql/* $SERVER:$SERVER_DIR/bioql/

# Step 4: Create systemd service
echo "⚙️  Creating systemd service..."
ssh $SERVER << 'EOF'
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
ExecStart=/usr/bin/python3 /root/bioql_quantum_server/quantum_execution_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable bioql-quantum
systemctl restart bioql-quantum

# Check status
systemctl status bioql-quantum --no-pager
EOF

echo ""
echo "="*80
echo "✅ Deployment Complete!"
echo "="*80
echo "Service: bioql-quantum"
echo "Port: 5002"
echo "Health: http://167.71.86.90:5002/health"
echo "Endpoint: http://api.bioql.bio/api/quantum/execute"
echo ""
echo "Check logs: ssh $SERVER journalctl -u bioql-quantum -f"
echo "="*80
