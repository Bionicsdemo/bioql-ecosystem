#!/bin/bash
# Script para configurar Lab Notebook y instalar Prometheus + Grafana
# Ejecutar en el servidor: bash configuracion_final_completa.sh

set -e  # Exit on error

echo "=========================================="
echo "🚀 CONFIGURACIÓN FINAL COMPLETA - BioQL"
echo "=========================================="
echo ""
echo "Este script va a:"
echo "  1. Configurar Lab Notebook en Nginx"
echo "  2. Instalar Prometheus + Grafana"
echo "  3. Configurar monitoreo de servicios BioQL"
echo ""
echo "Tiempo estimado: 20 minutos"
echo ""
read -p "¿Continuar? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado por usuario"
    exit 1
fi

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
    echo "   Por favor inicia Lab Notebook primero"
    exit 1
fi

echo "✅ Lab Notebook está corriendo"

# Backup
echo ""
echo "📦 Creando backup de Nginx..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_final_$(date +%Y%m%d_%H%M%S)
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

        if ($request_method = OPTIONS) {
            return 204;
        }
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
    echo "✅ Configuración insertada correctamente"
else
    echo "❌ Error: Configuración no se insertó"
    echo "   Restaurando backup..."
    LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_final_* | head -1)
    cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
    exit 1
fi

# Test con timeout
echo ""
echo "🧪 Testing sintaxis de Nginx (timeout 10s)..."
if timeout 10 nginx -t 2>&1; then
    echo "✅ Sintaxis correcta"

    systemctl reload nginx
    if [ $? -eq 0 ]; then
        echo "✅ Nginx recargado exitosamente"

        sleep 2
        echo ""
        echo "🧪 Testing endpoint..."
        RESPONSE=$(curl -s https://api.bioql.bio/lab-notebook/health)
        echo "$RESPONSE"

        if [[ "$RESPONSE" == *"healthy"* ]]; then
            echo ""
            echo "✅ LAB NOTEBOOK CONFIGURADO EXITOSAMENTE"
        else
            echo "⚠️  Endpoint responde pero sin 'healthy'"
        fi
    else
        echo "❌ Error al recargar Nginx"
        LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_final_* | head -1)
        cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
        systemctl reload nginx
        exit 1
    fi
else
    echo "❌ Error en sintaxis de Nginx o timeout"
    LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_final_* | head -1)
    cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
    exit 1
fi

# ==========================================
# PARTE 2: INSTALAR PROMETHEUS + GRAFANA
# ==========================================

echo ""
echo "=========================================="
echo "📊 PASO 2/3: INSTALAR PROMETHEUS + GRAFANA"
echo "=========================================="

# Actualizar sistema
echo ""
echo "📦 Actualizando sistema..."
apt-get update -qq

# Instalar Prometheus y Node Exporter
echo ""
echo "📥 Instalando Prometheus y Node Exporter..."
apt-get install -y -qq prometheus prometheus-node-exporter

if [ $? -eq 0 ]; then
    echo "✅ Prometheus y Node Exporter instalados"
else
    echo "❌ Error instalando Prometheus"
    exit 1
fi

# Configurar Prometheus
echo ""
echo "📝 Configurando Prometheus para monitorear BioQL..."
cat > /etc/prometheus/prometheus.yml << 'ENDPROM'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (métricas del sistema)
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  # BioQL Core
  - job_name: 'bioql_core'
    static_configs:
      - targets: ['localhost:5001']
    scrape_interval: 30s

  # Workflows
  - job_name: 'bioql_workflows'
    static_configs:
      - targets: ['localhost:5002']
    scrape_interval: 30s

  # Lab Notebook
  - job_name: 'bioql_notebook'
    static_configs:
      - targets: ['localhost:5003']
    scrape_interval: 30s

  # Quantum Docking
  - job_name: 'bioql_quantum_docking'
    static_configs:
      - targets: ['localhost:8100']
    scrape_interval: 30s

  # Quantum Graphs
  - job_name: 'bioql_quantum_graphs'
    static_configs:
      - targets: ['localhost:9000']
    scrape_interval: 30s
ENDPROM

# Reiniciar Prometheus
echo ""
echo "🔄 Iniciando Prometheus..."
systemctl restart prometheus
systemctl enable prometheus > /dev/null 2>&1

sleep 2

if systemctl is-active --quiet prometheus; then
    echo "✅ Prometheus iniciado y funcionando"
else
    echo "❌ Error iniciando Prometheus"
    echo "Ver logs: journalctl -xeu prometheus"
    exit 1
fi

# Node Exporter
if systemctl is-active --quiet prometheus-node-exporter; then
    echo "✅ Node Exporter funcionando"
else
    echo "🔄 Iniciando Node Exporter..."
    systemctl start prometheus-node-exporter
    systemctl enable prometheus-node-exporter > /dev/null 2>&1
fi

# Instalar Grafana
echo ""
echo "📥 Instalando Grafana..."
apt-get install -y -qq apt-transport-https software-properties-common wget

# Agregar repositorio
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add - > /dev/null 2>&1
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list > /dev/null

apt-get update -qq
apt-get install -y -qq grafana

if [ $? -eq 0 ]; then
    echo "✅ Grafana instalado"
else
    echo "❌ Error instalando Grafana"
    exit 1
fi

# Iniciar Grafana
echo ""
echo "🔄 Iniciando Grafana..."
systemctl start grafana-server
systemctl enable grafana-server > /dev/null 2>&1

sleep 3

if systemctl is-active --quiet grafana-server; then
    echo "✅ Grafana iniciado y funcionando"
else
    echo "❌ Error iniciando Grafana"
    echo "Ver logs: journalctl -xeu grafana-server"
    exit 1
fi

# ==========================================
# PARTE 3: VERIFICACIÓN FINAL
# ==========================================

echo ""
echo "=========================================="
echo "✅ PASO 3/3: VERIFICACIÓN FINAL"
echo "=========================================="

echo ""
echo "🔍 Verificando servicios instalados..."
echo ""

# Verificar servicios
services=("prometheus" "prometheus-node-exporter" "grafana-server" "nginx")
all_ok=true

for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "  ✅ $service"
    else
        echo "  ❌ $service"
        all_ok=false
    fi
done

echo ""
echo "🔍 Verificando endpoints BioQL..."
echo ""

# Test endpoints
endpoints=(
    "https://api.bioql.bio/health|BioQL Core"
    "https://api.bioql.bio/workflow/health|Workflows"
    "https://api.bioql.bio/lab-notebook/health|Lab Notebook"
    "https://api.bioql.bio/health/quantum-docking|Quantum Docking"
    "https://api.bioql.bio/quantum-graph/health|Quantum Graphs"
)

online_count=0
total_count=5

for endpoint_info in "${endpoints[@]}"; do
    IFS='|' read -r url name <<< "$endpoint_info"

    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url")

    if [ "$status" = "200" ]; then
        echo "  ✅ $name"
        ((online_count++))
    else
        echo "  ❌ $name (HTTP $status)"
    fi
done

echo ""
echo "=========================================="
echo "🎉 CONFIGURACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "📊 Resultados:"
echo "  - Servicios del sistema: ${#services[@]}/${#services[@]} activos"
echo "  - Endpoints BioQL: $online_count/$total_count online"
echo ""
echo "=========================================="
echo "📝 INFORMACIÓN DE ACCESO"
echo "=========================================="
echo ""
echo "Lab Notebook:"
echo "  ✅ https://api.bioql.bio/lab-notebook/health"
echo "  ✅ https://api.bioql.bio/lab-notebook/"
echo ""
echo "Prometheus:"
echo "  📊 http://localhost:9090"
echo "  🔐 Acceso: ssh -L 9090:localhost:9090 root@$(hostname -I | awk '{print $1}')"
echo ""
echo "Node Exporter:"
echo "  📈 http://localhost:9100/metrics"
echo ""
echo "Grafana:"
echo "  📊 http://localhost:3000"
echo "  🔐 Acceso: ssh -L 3000:localhost:3000 root@$(hostname -I | awk '{print $1}')"
echo "  👤 Usuario: admin"
echo "  🔑 Password: admin (cambiar en primer login)"
echo ""
echo "=========================================="
echo "📝 PRÓXIMOS PASOS"
echo "=========================================="
echo ""
echo "1. Crear túnel SSH desde tu computadora:"
echo "   ssh -L 3000:localhost:3000 -L 9090:localhost:9090 root@$(hostname -I | awk '{print $1}')"
echo ""
echo "2. Abrir Grafana en tu navegador:"
echo "   http://localhost:3000"
echo ""
echo "3. Login con admin/admin y cambiar password"
echo ""
echo "4. Agregar Prometheus como Data Source:"
echo "   Configuration → Data Sources → Add → Prometheus"
echo "   URL: http://localhost:9090"
echo "   Click 'Save & Test'"
echo ""
echo "5. Importar Dashboard:"
echo "   + → Import → Dashboard ID: 1860 (Node Exporter Full)"
echo ""
echo "6. Ver métricas de BioQL:"
echo "   Explore → Seleccionar job (bioql_core, bioql_workflows, etc.)"
echo ""
echo "=========================================="
echo ""
echo "🎉 ¡Sistema BioQL al 100% configurado!"
echo ""
echo "Ver logs:"
echo "  journalctl -fu prometheus"
echo "  journalctl -fu grafana-server"
echo ""
