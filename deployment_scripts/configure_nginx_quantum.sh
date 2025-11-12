#!/bin/bash
# Configure Nginx to route quantum execution requests

SERVER="root@167.71.86.90"

echo "="*80
echo "🔧 Configuring Nginx for Quantum Execution"
echo "="*80

ssh $SERVER << 'EOF'
# Backup existing config
cp /etc/nginx/sites-available/api.bioql.bio /etc/nginx/sites-available/api.bioql.bio.backup.$(date +%Y%m%d_%H%M%S)

# Update Nginx configuration
cat > /etc/nginx/sites-available/api.bioql.bio << 'NGINX_CONFIG'
server {
    listen 80;
    listen [::]:80;
    server_name api.bioql.bio;

    # Redirect HTTP to HTTPS
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
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # CORS headers (enabled for quantum API)
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    # Handle preflight OPTIONS requests
    if ($request_method = OPTIONS) {
        add_header Access-Control-Allow-Origin "*";
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
        return 204;
    }

    # Quantum execution endpoints (NEW - Port 5002)
    location /api/quantum/ {
        proxy_pass http://localhost:5002/api/quantum/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Longer timeout for quantum execution
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Alternative quantum execution endpoint
    location /api/execute {
        proxy_pass http://localhost:5002/api/execute;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Fallback quantum execution endpoint
    location /execute {
        proxy_pass http://localhost:5002/execute;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Authentication endpoints (Port 5001)
    location /auth/ {
        proxy_pass http://localhost:5001/auth/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Billing endpoints (Port 5001)
    location /billing/ {
        proxy_pass http://localhost:5001/billing/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhooks (Port 5001)
    location /webhooks/ {
        proxy_pass http://localhost:5001/webhooks/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health and stats endpoints
    location /health {
        proxy_pass http://localhost:5001/health;
        proxy_set_header Host $host;
    }

    location /stats {
        proxy_pass http://localhost:5001/stats;
        proxy_set_header Host $host;
    }

    # Root path
    location / {
        return 200 '{"service":"BioQL API","version":"3.0.0","endpoints":["/auth/","/billing/","/api/quantum/","/health","/stats"]}';
        add_header Content-Type application/json;
    }

    # Access and error logs
    access_log /var/log/nginx/api.bioql.bio.access.log;
    error_log /var/log/nginx/api.bioql.bio.error.log;
}
NGINX_CONFIG

# Test Nginx configuration
nginx -t

# If test passes, reload Nginx
if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration valid"
    systemctl reload nginx
    echo "✅ Nginx reloaded"
else
    echo "❌ Nginx configuration error!"
    echo "Restoring backup..."
    cp /etc/nginx/sites-available/api.bioql.bio.backup.$(date +%Y%m%d)* /etc/nginx/sites-available/api.bioql.bio
    exit 1
fi
EOF

echo ""
echo "="*80
echo "✅ Nginx Configuration Complete!"
echo "="*80
echo "Quantum endpoint: https://api.bioql.bio/api/quantum/execute"
echo "Authentication: https://api.bioql.bio/auth/validate"
echo "Health check: https://api.bioql.bio/health"
echo "="*80
