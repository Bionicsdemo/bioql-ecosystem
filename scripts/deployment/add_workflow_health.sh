#!/bin/bash
# Script para agregar endpoint /workflow/health a Nginx

echo "=========================================="
echo "🔧 AGREGANDO /workflow/health A NGINX"
echo "=========================================="

# Backup
echo ""
echo "📦 Backup..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_add_health_$(date +%Y%m%d_%H%M%S)

# Crear archivo temporal con la nueva configuración
cat > /tmp/workflow_config.txt << 'EOF'
    # Workflows Health endpoint
    location /workflow/health {
        proxy_pass http://127.0.0.1:5002/health;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

EOF

# Insertar ANTES de la línea que contiene "location /workflow/ {"
sed -i '/location \/workflow\/ {/e cat /tmp/workflow_config.txt' /etc/nginx/sites-available/bioql

echo "✅ Configuración agregada"

# Verificar
echo ""
echo "🔍 Verificando..."
grep -A20 "Workflows" /etc/nginx/sites-available/bioql | head -30

# Test sintaxis
echo ""
echo "🧪 Testing sintaxis..."
nginx -t

# Reload
if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 Recargando Nginx..."
    systemctl reload nginx
    sleep 2

    echo ""
    echo "✅ Testing endpoints..."
    echo ""
    echo "Local test:"
    curl -s http://127.0.0.1:5002/health
    echo ""
    echo ""
    echo "A través de Nginx local:"
    curl -s http://127.0.0.1/workflow/health
    echo ""
fi

echo ""
echo "=========================================="
echo "✅ LISTO"
echo "=========================================="
echo ""
echo "Test público:"
echo "  curl -s https://api.bioql.bio/workflow/health"
