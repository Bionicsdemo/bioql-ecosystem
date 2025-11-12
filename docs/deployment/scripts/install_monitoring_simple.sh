#!/bin/bash
# Script SIMPLE para instalar Prometheus + Grafana
# NO toca Nginx (Lab Notebook se configurará después)

echo "=========================================="
echo "📊 INSTALANDO PROMETHEUS + GRAFANA"
echo "=========================================="
echo ""
echo "Este script SOLO instala monitoreo"
echo "NO modifica Nginx"
echo ""

# Instalar Prometheus
echo "📥 Instalando Prometheus..."
apt-get install -y prometheus prometheus-node-exporter > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Prometheus instalado"
else
    echo "❌ Error instalando Prometheus"
    exit 1
fi

# Configurar Prometheus
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

  - job_name: 'bioql_core'
    static_configs:
      - targets: ['localhost:5001']
    scrape_interval: 30s

  - job_name: 'bioql_workflows'
    static_configs:
      - targets: ['localhost:5002']
    scrape_interval: 30s

  - job_name: 'bioql_notebook'
    static_configs:
      - targets: ['localhost:5003']
    scrape_interval: 30s

  - job_name: 'bioql_docking'
    static_configs:
      - targets: ['localhost:8100']
    scrape_interval: 30s

  - job_name: 'bioql_graphs'
    static_configs:
      - targets: ['localhost:9000']
    scrape_interval: 30s
ENDPROM

# Reiniciar Prometheus
echo "🔄 Iniciando Prometheus..."
systemctl restart prometheus > /dev/null 2>&1
systemctl enable prometheus > /dev/null 2>&1
sleep 2

if systemctl is-active --quiet prometheus; then
    echo "✅ Prometheus funcionando"
else
    echo "⚠️  Prometheus no inició"
fi

# Instalar Grafana
echo ""
echo "📥 Instalando Grafana..."
apt-get install -y apt-transport-https software-properties-common wget > /dev/null 2>&1
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add - > /dev/null 2>&1
echo "deb https://packages.grafana.com/oss/deb stable main" > /etc/apt/sources.list.d/grafana.list
apt-get update -qq > /dev/null 2>&1
apt-get install -y grafana > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Grafana instalado"
else
    echo "❌ Error instalando Grafana"
    exit 1
fi

# Iniciar Grafana
echo "🔄 Iniciando Grafana..."
systemctl start grafana-server > /dev/null 2>&1
systemctl enable grafana-server > /dev/null 2>&1
sleep 3

if systemctl is-active --quiet grafana-server; then
    echo "✅ Grafana funcionando"
else
    echo "⚠️  Grafana no inició"
fi

# Verificar
echo ""
echo "=========================================="
echo "✅ INSTALACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "Servicios instalados:"
systemctl is-active prometheus && echo "  ✅ Prometheus" || echo "  ❌ Prometheus"
systemctl is-active prometheus-node-exporter && echo "  ✅ Node Exporter" || echo "  ❌ Node Exporter"
systemctl is-active grafana-server && echo "  ✅ Grafana" || echo "  ❌ Grafana"

echo ""
echo "=========================================="
echo "📝 ACCESO A SERVICIOS"
echo "=========================================="
echo ""
echo "Prometheus:"
echo "  📊 http://localhost:9090"
echo "  🔐 Túnel SSH: ssh -L 9090:localhost:9090 root@167.71.86.90"
echo ""
echo "Grafana:"
echo "  📊 http://localhost:3000"
echo "  🔐 Túnel SSH: ssh -L 3000:localhost:3000 root@167.71.86.90"
echo "  👤 Usuario: admin"
echo "  🔑 Password: admin (cambiar en primer login)"
echo ""
echo "=========================================="
echo "📝 PRÓXIMOS PASOS"
echo "=========================================="
echo ""
echo "1. Desde tu Mac, crear túnel SSH:"
echo "   ssh -L 3000:localhost:3000 root@167.71.86.90"
echo ""
echo "2. Abrir Grafana:"
echo "   open http://localhost:3000"
echo ""
echo "3. Login: admin / admin"
echo ""
echo "4. Agregar Data Source:"
echo "   Configuration → Data Sources → Add → Prometheus"
echo "   URL: http://localhost:9090"
echo "   Click 'Save & Test'"
echo ""
echo "5. Importar Dashboard:"
echo "   + → Import → Dashboard ID: 1860"
echo ""
echo "🎉 Monitoreo instalado!"
