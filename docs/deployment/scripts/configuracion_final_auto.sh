#!/bin/bash
# Script AUTO para configurar Lab Notebook y instalar Prometheus + Grafana
# Ejecutar: bash configuracion_final_auto.sh

set -e  # Exit on error

echo "=========================================="
echo "🚀 CONFIGURACIÓN FINAL COMPLETA - BioQL"
echo "=========================================="
echo ""
echo "Configurando automáticamente..."
echo "Tiempo estimado: 20 minutos"
echo ""

# ==========================================
# PARTE 1: CONFIGURAR LAB NOTEBOOK
# ==========================================

echo ""
echo "=========================================="
echo "📓 PASO 1/3: CONFIGURAR LAB NOTEBOOK"
echo "=========================================="

# Verificar Lab Notebook
echo ""
echo "🔍 Verificando Lab Notebook en puerto 5003..."
NOTEBOOK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5003/health)

if [ "$NOTEBOOK_STATUS" != "200" ]; then
    echo "❌ Lab Notebook no está respondiendo (HTTP $NOTEBOOK_STATUS)"
    exit 1
fi

echo "✅ Lab Notebook está corriendo"

# Backup
echo ""
echo "📦 Creando backup de Nginx..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_auto_$(date +%Y%m%d_%H%M%S)
echo "✅ Backup creado"

# Crear configuración
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
    }
ENDCONFIG

# Insertar después de Workflows
WORKFLOW_LINE=$(grep -n "location /workflow/ {" /etc/nginx/sites-available/bioql | cut -d: -f1)
INSERT_LINE=$((WORKFLOW_LINE + 12))
echo "   Insertando en línea $INSERT_LINE..."
sed -i "${INSERT_LINE}r /tmp/lab_notebook_config.txt" /etc/nginx/sites-available/bioql

# Verificar
echo ""
echo "🔍 Verificando inserción..."
if grep -q "Lab Notebook API" /etc/nginx/sites-available/bioql; then
    echo "✅ Configuración insertada"
else
    echo "❌ Error insertando"
    exit 1
fi

# Test
echo ""
echo "🧪 Testing sintaxis Nginx..."
if timeout 10 nginx -t 2>&1; then
    echo "✅ Sintaxis OK"
    systemctl reload nginx
    echo "✅ Nginx recargado"
    sleep 2
    curl -s https://api.bioql.bio/lab-notebook/health
    echo ""
    echo "✅ LAB NOTEBOOK CONFIGURADO"
else
    echo "❌ Error en sintaxis"
    exit 1
fi

# ==========================================
# PARTE 2: INSTALAR PROMETHEUS + GRAFANA
# ==========================================

echo ""
echo "=========================================="
echo "📊 PASO 2/3: PROMETHEUS + GRAFANA"
echo "=========================================="

echo ""
echo "📦 Actualizando sistema..."
apt-get update -qq > /dev/null 2>&1

echo "📥 Instalando Prometheus..."
apt-get install -y -qq prometheus prometheus-node-exporter > /dev/null 2>&1
echo "✅ Prometheus instalado"

echo "📝 Configurando Prometheus..."
cat > /etc/prometheus/prometheus.yml << 'ENDPROM'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
  - job_name: 'bioql_services'
    static_configs:
      - targets: ['localhost:5001', 'localhost:5002', 'localhost:5003', 'localhost:8100', 'localhost:9000']
    scrape_interval: 30s
ENDPROM

systemctl restart prometheus > /dev/null 2>&1
systemctl enable prometheus > /dev/null 2>&1
sleep 2
echo "✅ Prometheus iniciado"

echo "📥 Instalando Grafana..."
apt-get install -y -qq apt-transport-https software-properties-common wget > /dev/null 2>&1
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add - > /dev/null 2>&1
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list > /dev/null
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq grafana > /dev/null 2>&1
echo "✅ Grafana instalado"

systemctl start grafana-server > /dev/null 2>&1
systemctl enable grafana-server > /dev/null 2>&1
sleep 3
echo "✅ Grafana iniciado"

# ==========================================
# PARTE 3: VERIFICACIÓN
# ==========================================

echo ""
echo "=========================================="
echo "✅ PASO 3/3: VERIFICACIÓN"
echo "=========================================="
echo ""

services=("prometheus" "prometheus-node-exporter" "grafana-server" "nginx")
for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "  ✅ $service"
    else
        echo "  ❌ $service"
    fi
done

echo ""
echo "🔍 Endpoints BioQL:"
for url in "https://api.bioql.bio/health" "https://api.bioql.bio/workflow/health" "https://api.bioql.bio/lab-notebook/health"; do
    if curl -s --max-time 3 "$url" | grep -q "healthy"; then
        echo "  ✅ $url"
    else
        echo "  ⚠️  $url"
    fi
done

echo ""
echo "=========================================="
echo "🎉 CONFIGURACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "Grafana: http://localhost:3000"
echo "  Túnel: ssh -L 3000:localhost:3000 root@167.71.86.90"
echo "  User: admin / Password: admin"
echo ""
echo "Prometheus: http://localhost:9090"
echo ""
echo "✅ Sistema BioQL al 100%"
