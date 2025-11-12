#!/bin/bash
# Script para configurar Workflows en Nginx
# Ejecutar en el servidor: bash configure_workflows_nginx.sh

echo "=========================================="
echo "🔧 CONFIGURANDO NGINX PARA WORKFLOWS"
echo "=========================================="

# 1. Backup
echo ""
echo "📦 Creando backup..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_workflows_$(date +%Y%m%d_%H%M%S)
echo "✅ Backup creado"

# 2. Cambiar /workflow a /workflow/
echo ""
echo "✏️  Actualizando configuración..."
sed -i 's|location /workflow {|location /workflow/ {|g' /etc/nginx/sites-available/bioql
sed -i 's|proxy_pass http://127.0.0.1:5002;|proxy_pass http://127.0.0.1:5002/;|g' /etc/nginx/sites-available/bioql
echo "✅ Configuración actualizada"

# 3. Verificar el cambio
echo ""
echo "🔍 Verificando cambio..."
grep -A5 "location /workflow" /etc/nginx/sites-available/bioql

# 4. Test de sintaxis
echo ""
echo "🧪 Testing sintaxis de Nginx..."
nginx -t

# 5. Si el test pasa, reload
if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 Recargando Nginx..."
    systemctl reload nginx

    # Verificar
    if systemctl is-active --quiet nginx; then
        echo "✅ Nginx recargado exitosamente"
    else
        echo "❌ Nginx no está activo"
        systemctl status nginx
    fi

    # Test endpoint
    echo ""
    echo "🧪 Testing endpoint /workflow/..."
    sleep 2
    curl -s http://127.0.0.1/workflow/ | head -10

    echo ""
    echo "=========================================="
    echo "✅ CONFIGURACIÓN COMPLETA"
    echo "=========================================="
    echo ""
    echo "Prueba desde fuera:"
    echo "  curl -s https://api.bioql.bio/workflow/"

else
    echo ""
    echo "❌ Error en sintaxis de Nginx"
    echo "Revisa el archivo: /etc/nginx/sites-available/bioql"
fi
