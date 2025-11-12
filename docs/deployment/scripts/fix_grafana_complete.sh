#!/bin/bash

echo "=========================================="
echo "🔧 REPARANDO GRAFANA COMPLETO"
echo "=========================================="
echo ""

# 1. Detener Grafana
echo "🛑 Deteniendo Grafana..."
systemctl stop grafana-server
sleep 2

# 2. Hacer backup de la configuración actual
echo "💾 Backup de configuración..."
cp /etc/grafana/grafana.ini /etc/grafana/grafana.ini.backup_$(date +%Y%m%d_%H%M%S)

# 3. Reinstalar Grafana
echo "📦 Reinstalando Grafana..."
apt-get remove --purge grafana -y > /dev/null 2>&1
apt-get install -y grafana > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Error instalando Grafana"
    exit 1
fi

echo "✅ Grafana reinstalado"

# 4. Configurar Grafana SIN subpath (configuración básica)
echo "📝 Configurando Grafana..."

# Descomentar y configurar http_addr
sed -i 's|;http_addr =|http_addr = 0.0.0.0|' /etc/grafana/grafana.ini

# Descomentar y configurar http_port
sed -i 's|;http_port = 3000|http_port = 3000|' /etc/grafana/grafana.ini

# Descomentar protocol
sed -i 's|;protocol = http|protocol = http|' /etc/grafana/grafana.ini

echo "✅ Configuración básica aplicada"

# 5. Iniciar Grafana
echo "🚀 Iniciando Grafana..."
systemctl start grafana-server

# 6. Esperar 20 segundos para que inicie completamente
echo "⏳ Esperando 20 segundos para que Grafana inicie..."
for i in {20..1}; do
    echo -n "$i... "
    sleep 1
done
echo ""

# 7. Verificar que el puerto 3000 esté escuchando
echo ""
echo "🔍 Verificando puerto 3000..."
PORT_CHECK=$(ss -tulpn | grep :3000)

if [ -z "$PORT_CHECK" ]; then
    echo "❌ ERROR: Grafana NO está escuchando en puerto 3000"
    echo ""
    echo "Ver logs:"
    tail -30 /var/log/grafana/grafana.log
    echo ""
    echo "Ver status:"
    systemctl status grafana-server
    exit 1
fi

echo "✅ Puerto 3000 escuchando"

# 8. Probar conexión HTTP
echo "🔍 Probando conexión HTTP..."
HTTP_TEST=$(curl -I http://localhost:3000/ 2>&1 | head -1)

if echo "$HTTP_TEST" | grep -q "HTTP"; then
    echo "✅ Grafana respondiendo en HTTP"
else
    echo "⚠️  Grafana no responde correctamente"
    echo "Respuesta: $HTTP_TEST"
fi

# 9. Configurar Nginx para Grafana
echo ""
echo "📝 Configurando Nginx..."

# Verificar si ya existe la configuración de Grafana
if grep -q "location /grafana/" /etc/nginx/sites-available/bioql; then
    echo "⚠️  Grafana ya está configurado en Nginx"
else
    # Crear configuración de Nginx
    cat > /tmp/grafana_nginx.conf << 'ENDNGINX'
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
ENDNGINX

    # Encontrar el último location block y agregar Grafana después
    LAST_LOCATION=$(grep -n "location /health/quantum-docking" /etc/nginx/sites-available/bioql | tail -1 | cut -d: -f1)

    if [ -n "$LAST_LOCATION" ]; then
        # Buscar el cierre de ese bloque
        CLOSE_LINE=$(tail -n +$((LAST_LOCATION + 1)) /etc/nginx/sites-available/bioql | grep -n "^    }" | head -1 | cut -d: -f1)
        INSERT_LINE=$((LAST_LOCATION + CLOSE_LINE))

        # Insertar configuración
        sed -i "${INSERT_LINE}r /tmp/grafana_nginx.conf" /etc/nginx/sites-available/bioql

        echo "✅ Configuración agregada a Nginx"
    else
        echo "⚠️  No se pudo encontrar ubicación para insertar en Nginx"
    fi

    rm -f /tmp/grafana_nginx.conf
fi

# 10. Verificar sintaxis de Nginx
echo "🔍 Verificando Nginx..."
NGINX_TEST=$(nginx -t 2>&1)

if echo "$NGINX_TEST" | grep -q "test is successful"; then
    echo "✅ Sintaxis de Nginx correcta"

    # Recargar Nginx
    systemctl reload nginx
    echo "✅ Nginx recargado"
else
    echo "❌ Error en Nginx:"
    echo "$NGINX_TEST"
    exit 1
fi

# 11. Configurar Grafana para subpath /grafana/
echo ""
echo "📝 Configurando subpath /grafana/..."
sed -i 's|;root_url = %(protocol)s://%(domain)s:%(http_port)s/|root_url = %(protocol)s://%(domain)s:%(http_port)s/grafana/|' /etc/grafana/grafana.ini
sed -i 's|;serve_from_sub_path = false|serve_from_sub_path = true|' /etc/grafana/grafana.ini

# 12. Reiniciar Grafana con nueva configuración
echo "🔄 Reiniciando Grafana con subpath..."
systemctl restart grafana-server

echo "⏳ Esperando 15 segundos..."
sleep 15

# 13. Verificar acceso final
echo ""
echo "🔍 Verificando acceso final..."
FINAL_TEST=$(curl -I https://localhost/grafana/ -k 2>&1 | head -1)

if echo "$FINAL_TEST" | grep -q "HTTP"; then
    echo "✅ Grafana accesible vía Nginx"
else
    echo "⚠️  Verificar manualmente"
fi

echo ""
echo "=========================================="
echo "✅ REPARACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "🌐 Acceso:"
echo "   https://api.bioql.bio/grafana/"
echo ""
echo "🔐 Login:"
echo "   Usuario: admin"
echo "   Password: admin"
echo ""
echo "📊 Status de servicios:"
systemctl status grafana-server --no-pager | head -5
echo ""
ss -tulpn | grep 3000
echo ""
echo "✅ Script completado"
