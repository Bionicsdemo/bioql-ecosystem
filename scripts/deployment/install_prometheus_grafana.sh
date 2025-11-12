#!/bin/bash
# Script para instalar y configurar Prometheus + Grafana
# Ejecutar en el servidor: bash install_prometheus_grafana.sh

echo "=========================================="
echo "📊 INSTALANDO PROMETHEUS + GRAFANA"
echo "=========================================="

# Verificar que somos root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script debe ejecutarse como root"
    echo "   Usa: sudo bash install_prometheus_grafana.sh"
    exit 1
fi

echo ""
echo "📦 Actualizando sistema..."
apt-get update -qq

# ==========================================
# 1. INSTALAR PROMETHEUS
# ==========================================

echo ""
echo "=========================================="
echo "📊 INSTALANDO PROMETHEUS"
echo "=========================================="

# Crear usuario prometheus
if ! id "prometheus" &>/dev/null; then
    useradd --no-create-home --shell /bin/false prometheus
    echo "✅ Usuario prometheus creado"
fi

# Descargar Prometheus
cd /tmp
PROM_VERSION="2.47.0"
echo ""
echo "📥 Descargando Prometheus v$PROM_VERSION..."
wget -q https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.linux-amd64.tar.gz

if [ $? -ne 0 ]; then
    echo "❌ Error descargando Prometheus"
    exit 1
fi

echo "✅ Descarga completa"

# Extraer
echo "📦 Extrayendo..."
tar xzf prometheus-${PROM_VERSION}.linux-amd64.tar.gz
cd prometheus-${PROM_VERSION}.linux-amd64

# Copiar binarios
echo "📋 Instalando binarios..."
cp prometheus /usr/local/bin/
cp promtool /usr/local/bin/
chown prometheus:prometheus /usr/local/bin/prometheus
chown prometheus:prometheus /usr/local/bin/promtool

# Copiar archivos de configuración
mkdir -p /etc/prometheus
mkdir -p /var/lib/prometheus
cp -r consoles /etc/prometheus
cp -r console_libraries /etc/prometheus
chown -R prometheus:prometheus /etc/prometheus
chown prometheus:prometheus /var/lib/prometheus

echo "✅ Prometheus instalado"

# Configurar Prometheus
echo ""
echo "📝 Configurando Prometheus..."
cat > /etc/prometheus/prometheus.yml << 'PROMCONFIG'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Alertmanager configuration (opcional)
# alerting:
#   alertmanagers:
#     - static_configs:
#         - targets:
#           - localhost:9093

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (métricas del sistema)
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  # BioQL Services
  - job_name: 'bioql_core'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:5001']
    scrape_interval: 30s

  - job_name: 'bioql_workflows'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:5002']
    scrape_interval: 30s

  - job_name: 'bioql_quantum_docking'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8100']
    scrape_interval: 30s

  - job_name: 'bioql_quantum_graphs'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:9000']
    scrape_interval: 30s

  # Nginx metrics (requiere nginx-prometheus-exporter)
  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']
    scrape_interval: 30s
PROMCONFIG

chown prometheus:prometheus /etc/prometheus/prometheus.yml
echo "✅ Configuración creada"

# Crear servicio systemd
echo ""
echo "🔧 Creando servicio systemd..."
cat > /etc/systemd/system/prometheus.service << 'PROMSERVICE'
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
    --config.file /etc/prometheus/prometheus.yml \
    --storage.tsdb.path /var/lib/prometheus/ \
    --web.console.templates=/etc/prometheus/consoles \
    --web.console.libraries=/etc/prometheus/console_libraries

[Install]
WantedBy=multi-user.target
PROMSERVICE

systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus

if systemctl is-active --quiet prometheus; then
    echo "✅ Prometheus iniciado y funcionando"
else
    echo "❌ Error iniciando Prometheus"
    journalctl -xeu prometheus | tail -20
    exit 1
fi

# ==========================================
# 2. INSTALAR NODE EXPORTER
# ==========================================

echo ""
echo "=========================================="
echo "📊 INSTALANDO NODE EXPORTER"
echo "=========================================="

cd /tmp
NODE_VERSION="1.6.1"
echo "📥 Descargando Node Exporter v$NODE_VERSION..."
wget -q https://github.com/prometheus/node_exporter/releases/download/v${NODE_VERSION}/node_exporter-${NODE_VERSION}.linux-amd64.tar.gz

tar xzf node_exporter-${NODE_VERSION}.linux-amd64.tar.gz
cd node_exporter-${NODE_VERSION}.linux-amd64

cp node_exporter /usr/local/bin/
chown prometheus:prometheus /usr/local/bin/node_exporter

echo "✅ Node Exporter instalado"

# Crear servicio
cat > /etc/systemd/system/node_exporter.service << 'NODESERVICE'
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
NODESERVICE

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter

if systemctl is-active --quiet node_exporter; then
    echo "✅ Node Exporter iniciado"
else
    echo "❌ Error iniciando Node Exporter"
    exit 1
fi

# ==========================================
# 3. INSTALAR GRAFANA
# ==========================================

echo ""
echo "=========================================="
echo "📊 INSTALANDO GRAFANA"
echo "=========================================="

echo "📥 Agregando repositorio de Grafana..."
apt-get install -y -qq apt-transport-https software-properties-common wget

wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list

apt-get update -qq
echo ""
echo "📦 Instalando Grafana..."
apt-get install -y -qq grafana

echo "✅ Grafana instalado"

# Iniciar Grafana
systemctl daemon-reload
systemctl enable grafana-server
systemctl start grafana-server

if systemctl is-active --quiet grafana-server; then
    echo "✅ Grafana iniciado"
else
    echo "❌ Error iniciando Grafana"
    exit 1
fi

# ==========================================
# 4. CONFIGURAR NGINX PARA GRAFANA
# ==========================================

echo ""
echo "=========================================="
echo "🌐 CONFIGURANDO NGINX PARA GRAFANA"
echo "=========================================="

# Backup
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_grafana_$(date +%Y%m%d_%H%M%S)

# Agregar bloque de Grafana
echo "📝 Agregando configuración de Grafana a Nginx..."

# Encontrar la línea antes del último }
LINE_NUM=$(grep -n "^}" /etc/nginx/sites-available/bioql | tail -1 | cut -d: -f1)
INSERT_LINE=$((LINE_NUM - 1))

cat > /tmp/grafana_nginx.conf << 'GRAFANANGINX'

    # Grafana Monitoring Dashboard
    location /grafana/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Prometheus (protegido, solo acceso local)
    location /prometheus/ {
        proxy_pass http://127.0.0.1:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Restringir acceso solo a localhost
        allow 127.0.0.1;
        deny all;
    }
GRAFANANGINX

sed -i "${INSERT_LINE}r /tmp/grafana_nginx.conf" /etc/nginx/sites-available/bioql

# Test y reload
echo "🧪 Testing Nginx..."
if timeout 5 nginx -t; then
    echo "✅ Sintaxis correcta"
    systemctl reload nginx
    echo "✅ Nginx recargado"
else
    echo "❌ Error en sintaxis"
    echo "   Restaurando backup..."
    cp /etc/nginx/sites-available/bioql.backup_grafana_* /etc/nginx/sites-available/bioql
fi

# ==========================================
# 5. CONFIGURAR GRAFANA
# ==========================================

echo ""
echo "=========================================="
echo "⚙️  CONFIGURACIÓN POST-INSTALACIÓN"
echo "=========================================="

# Esperar a que Grafana esté listo
echo "⏳ Esperando a que Grafana esté listo..."
sleep 5

echo ""
echo "✅ INSTALACIÓN COMPLETA"
echo ""
echo "=========================================="
echo "📊 INFORMACIÓN DE ACCESO"
echo "=========================================="
echo ""
echo "Prometheus:"
echo "  URL interna: http://localhost:9090"
echo "  URL pública: https://api.bioql.bio/prometheus/ (solo localhost)"
echo ""
echo "Node Exporter:"
echo "  Métricas: http://localhost:9100/metrics"
echo ""
echo "Grafana:"
echo "  URL interna: http://localhost:3000"
echo "  URL pública: https://api.bioql.bio/grafana/"
echo "  Usuario: admin"
echo "  Password: admin (cambiar en primer login)"
echo ""
echo "=========================================="
echo "📝 PRÓXIMOS PASOS"
echo "=========================================="
echo ""
echo "1. Acceder a Grafana:"
echo "   https://api.bioql.bio/grafana/"
echo ""
echo "2. Login con admin/admin y cambiar password"
echo ""
echo "3. Agregar Prometheus como Data Source:"
echo "   Configuration → Data Sources → Add data source"
echo "   URL: http://localhost:9090"
echo ""
echo "4. Importar dashboards:"
echo "   + → Import"
echo "   Dashboard ID 1860 (Node Exporter Full)"
echo "   Dashboard ID 7362 (Linux Server Metrics)"
echo ""
echo "5. Ver métricas de servicios BioQL:"
echo "   Explore → Seleccionar job (bioql_core, bioql_workflows, etc.)"
echo ""
echo "=========================================="
echo ""
echo "Ver logs:"
echo "  journalctl -fu prometheus"
echo "  journalctl -fu node_exporter"
echo "  journalctl -fu grafana-server"
echo ""
echo "🎉 ¡Monitoreo instalado exitosamente!"
