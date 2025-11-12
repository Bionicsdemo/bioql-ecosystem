#!/bin/bash
# Script para configurar Lab Notebook en Nginx
# Ejecutar en el servidor: bash configure_lab_notebook.sh

echo "=========================================="
echo "📓 CONFIGURANDO LAB NOTEBOOK EN NGINX"
echo "=========================================="

# Verificar que Lab Notebook esté corriendo
echo ""
echo "🔍 Verificando Lab Notebook en puerto 5003..."
NOTEBOOK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5003/health)

if [ "$NOTEBOOK_STATUS" != "200" ]; then
    echo "❌ Lab Notebook no está respondiendo en puerto 5003"
    echo "   Status code: $NOTEBOOK_STATUS"
    exit 1
fi

echo "✅ Lab Notebook está corriendo"

# Backup de Nginx
echo ""
echo "📦 Creando backup de Nginx..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_notebook_manual_$(date +%Y%m%d_%H%M%S)
echo "✅ Backup creado"

# Crear configuración temporal
echo ""
echo "📝 Creando configuración de Lab Notebook..."
cat > /tmp/lab_notebook_config.txt << 'ENDCONFIG'

    # Lab Notebook API
    location /lab-notebook/health {
        proxy_pass http://127.0.0.1:5003/health;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    }

    location /lab-notebook/ {
        proxy_pass http://127.0.0.1:5003/;
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
ENDCONFIG

# Encontrar dónde insertar (después del bloque de Workflows)
WORKFLOW_LINE=$(grep -n "location /workflow/ {" /etc/nginx/sites-available/bioql | cut -d: -f1)
INSERT_LINE=$((WORKFLOW_LINE + 12))

echo "   Insertando en línea $INSERT_LINE..."

# Insertar la configuración
sed -i "${INSERT_LINE}r /tmp/lab_notebook_config.txt" /etc/nginx/sites-available/bioql

# Verificar que se insertó
echo ""
echo "🔍 Verificando inserción..."
if grep -q "Lab Notebook API" /etc/nginx/sites-available/bioql; then
    echo "✅ Configuración insertada correctamente"
else
    echo "❌ Error: Configuración no se insertó"
    echo "   Restaurando backup..."
    cp /etc/nginx/sites-available/bioql.backup_notebook_manual_* /etc/nginx/sites-available/bioql
    exit 1
fi

# Test de sintaxis CON TIMEOUT
echo ""
echo "🧪 Testing sintaxis de Nginx (con timeout 10s)..."
if timeout 10 nginx -t 2>&1 | tee /tmp/nginx_test.log; then
    echo "✅ Sintaxis correcta"

    # Reload Nginx
    echo ""
    echo "🔄 Recargando Nginx..."
    systemctl reload nginx

    if [ $? -eq 0 ]; then
        echo "✅ Nginx recargado exitosamente"

        # Test endpoints
        echo ""
        echo "🧪 Testing endpoints..."
        echo ""
        echo "Local:"
        curl -s http://127.0.0.1/lab-notebook/health

        echo ""
        echo ""
        echo "Público (esperar 2 segundos)..."
        sleep 2
        curl -s https://api.bioql.bio/lab-notebook/health

        echo ""
        echo ""
        echo "=========================================="
        echo "✅ LAB NOTEBOOK CONFIGURADO EXITOSAMENTE"
        echo "=========================================="
        echo ""
        echo "Endpoints disponibles:"
        echo "  https://api.bioql.bio/lab-notebook/health"
        echo "  https://api.bioql.bio/lab-notebook/"

    else
        echo "❌ Error al recargar Nginx"
        echo "   Restaurando backup..."
        LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_notebook_manual_* | head -1)
        cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
        systemctl reload nginx
    fi

else
    echo "❌ Error en sintaxis de Nginx o timeout"
    cat /tmp/nginx_test.log
    echo ""
    echo "   Restaurando backup..."
    LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_notebook_manual_* | head -1)
    cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
    exit 1
fi
