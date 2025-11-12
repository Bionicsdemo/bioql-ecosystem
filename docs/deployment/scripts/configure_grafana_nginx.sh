#!/bin/bash

echo "=========================================="
echo "🎨 CONFIGURANDO GRAFANA EN NGINX"
echo "=========================================="
echo ""

# 1. Backup de Nginx
BACKUP_FILE="/etc/nginx/sites-available/bioql.backup_grafana_$(date +%Y%m%d_%H%M%S)"
cp /etc/nginx/sites-available/bioql "$BACKUP_FILE"
echo "✅ Backup: $BACKUP_FILE"

# 2. Configurar Grafana para root_url
echo "📝 Configurando Grafana..."
if ! grep -q "root_url = %(protocol)s://%(domain)s:%(http_port)s/grafana/" /etc/grafana/grafana.ini; then
    sed -i 's|;root_url = %(protocol)s://%(domain)s:%(http_port)s/|root_url = %(protocol)s://%(domain)s:%(http_port)s/grafana/|' /etc/grafana/grafana.ini
    sed -i 's|;serve_from_sub_path = false|serve_from_sub_path = true|' /etc/grafana/grafana.ini
    echo "✅ Grafana configurado"
else
    echo "✅ Grafana ya configurado"
fi

# 3. Verificar si Grafana ya está en Nginx
if grep -q "location /grafana/" /etc/nginx/sites-available/bioql; then
    echo "⚠️  Grafana ya está en Nginx"
    echo ""
    echo "🌐 Acceso: https://api.bioql.bio/grafana/"
    echo "🔐 Login: admin / admin"
    exit 0
fi

# 4. Agregar location de Grafana DENTRO del bloque server para HTTPS (puerto 443)
# Buscar la última línea del bloque server de HTTPS (antes del } final de ese bloque)
# Insertamos justo antes del cierre del bloque location /

echo "📍 Agregando configuración de Grafana..."

# Crear el bloque de configuración
cat > /tmp/grafana_block.conf << 'EOF'
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
EOF

# Encontrar el último bloque location dentro del server HTTPS y agregar Grafana después
# Buscar la línea que contiene "location /" (el último location block)
LAST_LOCATION_LINE=$(grep -n "location /health/quantum-docking" /etc/nginx/sites-available/bioql | tail -1 | cut -d: -f1)

if [ -z "$LAST_LOCATION_LINE" ]; then
    # Si no encuentra quantum-docking, buscar cualquier location
    LAST_LOCATION_LINE=$(grep -n "location /" /etc/nginx/sites-available/bioql | tail -1 | cut -d: -f1)
fi

# Buscar el cierre de ese bloque (siguiente } después de esa línea)
CLOSE_BRACE_LINE=$(tail -n +$((LAST_LOCATION_LINE + 1)) /etc/nginx/sites-available/bioql | grep -n "^    }" | head -1 | cut -d: -f1)
INSERT_LINE=$((LAST_LOCATION_LINE + CLOSE_BRACE_LINE))

echo "📌 Insertando después de línea $INSERT_LINE..."

# Insertar el bloque
sed -i "${INSERT_LINE}r /tmp/grafana_block.conf" /etc/nginx/sites-available/bioql

# 5. Verificar sintaxis
echo "🔍 Verificando sintaxis..."
NGINX_TEST=$(nginx -t 2>&1)
if echo "$NGINX_TEST" | grep -q "test is successful"; then
    echo "✅ Sintaxis OK"

    # 6. Reiniciar servicios
    echo "🔄 Reiniciando servicios..."
    systemctl restart grafana-server > /dev/null 2>&1
    systemctl reload nginx > /dev/null 2>&1

    echo ""
    echo "=========================================="
    echo "✅ GRAFANA CONFIGURADO"
    echo "=========================================="
    echo ""
    echo "🌐 URL: https://api.bioql.bio/grafana/"
    echo "🔐 Login: admin / admin"
    echo ""

else
    echo "❌ Error en Nginx"
    echo "$NGINX_TEST"
    echo ""
    echo "🔄 Restaurando backup..."
    cp "$BACKUP_FILE" /etc/nginx/sites-available/bioql
    echo "✅ Backup restaurado"
    exit 1
fi

rm -f /tmp/grafana_block.conf
