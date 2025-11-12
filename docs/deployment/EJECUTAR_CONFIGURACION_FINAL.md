# 🚀 EJECUTAR CONFIGURACIÓN FINAL - BioQL

**Copiar y pegar estos comandos en tu terminal SSH**

---

## 📋 PASO 1: Conectar al servidor

```bash
ssh root@167.71.86.90
# Password: P31e27r12u1@HJG
```

---

## 📓 PASO 2: Configurar Lab Notebook (5 minutos)

**Copia y pega este bloque completo:**

```bash
#!/bin/bash
echo "=========================================="
echo "📓 CONFIGURANDO LAB NOTEBOOK EN NGINX"
echo "=========================================="

# Verificar Lab Notebook
echo ""
echo "🔍 Verificando Lab Notebook..."
NOTEBOOK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5003/health)

if [ "$NOTEBOOK_STATUS" != "200" ]; then
    echo "❌ Lab Notebook no responde (HTTP $NOTEBOOK_STATUS)"
    exit 1
fi

echo "✅ Lab Notebook funcionando"

# Backup
echo "📦 Backup..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_notebook_final_$(date +%Y%m%d_%H%M%S)

# Crear configuración
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
sed -i "${INSERT_LINE}r /tmp/lab_notebook_config.txt" /etc/nginx/sites-available/bioql

# Verificar
if grep -q "Lab Notebook API" /etc/nginx/sites-available/bioql; then
    echo "✅ Configuración insertada"
else
    echo "❌ Error insertando configuración"
    exit 1
fi

# Test con timeout
echo "🧪 Testing sintaxis..."
if timeout 10 nginx -t 2>&1; then
    echo "✅ Sintaxis OK"
    systemctl reload nginx
    echo "✅ Nginx recargado"

    sleep 2
    echo ""
    echo "🧪 Testing endpoint..."
    curl -s https://api.bioql.bio/lab-notebook/health

    echo ""
    echo ""
    echo "✅ LAB NOTEBOOK CONFIGURADO"
    echo "   URL: https://api.bioql.bio/lab-notebook/health"
else
    echo "❌ Error en sintaxis"
    LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_notebook_final_* | head -1)
    cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
    exit 1
fi
```

**Resultado esperado:**
```
✅ LAB NOTEBOOK CONFIGURADO
   URL: https://api.bioql.bio/lab-notebook/health
```

---

## 📊 PASO 3: Instalar Prometheus + Grafana (15 minutos)

**Copia y pega este bloque completo:**

```bash
#!/bin/bash
echo "=========================================="
echo "📊 INSTALANDO PROMETHEUS + GRAFANA"
echo "=========================================="

# Actualizar sistema
echo "📦 Actualizando sistema..."
apt-get update -qq

# Instalar Prometheus y Node Exporter
echo ""
echo "📥 Instalando Prometheus..."
apt-get install -y -qq prometheus prometheus-node-exporter

if [ $? -eq 0 ]; then
    echo "✅ Prometheus instalado"
else
    echo "❌ Error instalando Prometheus"
    exit 1
fi

# Configurar Prometheus
echo ""
echo "📝 Configurando Prometheus..."
cat > /etc/prometheus/prometheus.yml << 'ENDPROM'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

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

  - job_name: 'bioql_quantum_docking'
    static_configs:
      - targets: ['localhost:8100']
    scrape_interval: 30s

  - job_name: 'bioql_quantum_graphs'
    static_configs:
      - targets: ['localhost:9000']
    scrape_interval: 30s
ENDPROM

# Reiniciar Prometheus
systemctl restart prometheus
systemctl enable prometheus

if systemctl is-active --quiet prometheus; then
    echo "✅ Prometheus iniciado"
else
    echo "❌ Error iniciando Prometheus"
    journalctl -xeu prometheus | tail -10
    exit 1
fi

# Instalar Grafana
echo ""
echo "📥 Instalando Grafana..."
apt-get install -y -qq apt-transport-https software-properties-common wget

wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list

apt-get update -qq
apt-get install -y -qq grafana

if [ $? -eq 0 ]; then
    echo "✅ Grafana instalado"
else
    echo "❌ Error instalando Grafana"
    exit 1
fi

# Iniciar Grafana
systemctl start grafana-server
systemctl enable grafana-server

if systemctl is-active --quiet grafana-server; then
    echo "✅ Grafana iniciado"
else
    echo "❌ Error iniciando Grafana"
    exit 1
fi

# Verificar
echo ""
echo "=========================================="
echo "✅ INSTALACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "Prometheus:"
echo "  URL interna: http://localhost:9090"
echo "  Acceso: ssh -L 9090:localhost:9090 root@167.71.86.90"
echo ""
echo "Node Exporter:"
echo "  Métricas: http://localhost:9100/metrics"
echo ""
echo "Grafana:"
echo "  URL interna: http://localhost:3000"
echo "  Acceso: ssh -L 3000:localhost:3000 root@167.71.86.90"
echo "  Usuario: admin"
echo "  Password: admin (cambiar en primer login)"
echo ""
echo "=========================================="
echo "📝 PRÓXIMOS PASOS"
echo "=========================================="
echo ""
echo "1. Desde tu computadora local, crear túnel SSH:"
echo "   ssh -L 3000:localhost:3000 root@167.71.86.90"
echo ""
echo "2. Abrir navegador:"
echo "   http://localhost:3000"
echo ""
echo "3. Login: admin / admin"
echo ""
echo "4. Cambiar password"
echo ""
echo "5. Agregar Data Source:"
echo "   Configuration → Data Sources → Add → Prometheus"
echo "   URL: http://localhost:9090"
echo "   Save & Test"
echo ""
echo "6. Importar Dashboard:"
echo "   + → Import → Dashboard ID: 1860 (Node Exporter Full)"
echo ""
echo "🎉 Monitoreo instalado exitosamente!"
```

**Resultado esperado:**
```
✅ INSTALACIÓN COMPLETA
Prometheus: http://localhost:9090
Grafana: http://localhost:3000
```

---

## ✅ PASO 4: Verificación Final

**En el servidor:**

```bash
# Verificar todos los servicios
systemctl status prometheus | head -3
systemctl status prometheus-node-exporter | head -3
systemctl status grafana-server | head -3
systemctl status nginx | head -3

# Test todos los endpoints
curl -s https://api.bioql.bio/health | head -3
curl -s https://api.bioql.bio/workflow/health | head -3
curl -s https://api.bioql.bio/lab-notebook/health | head -3
curl -s https://api.bioql.bio/health/quantum-docking | head -3
curl -s https://api.bioql.bio/quantum-graph/health | head -3
```

**Resultado esperado:**
```
✅ Todos los servicios activos
✅ Todos los endpoints responden HTTP 200
```

---

## 🌐 PASO 5: Acceder a Grafana

**Desde tu computadora local (nueva terminal):**

```bash
# Crear túnel SSH
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 root@167.71.86.90

# Abrir Grafana en navegador
open http://localhost:3000
```

**Login:**
- Usuario: `admin`
- Password: `admin`

**IMPORTANTE:** Cambiar password en primer login

---

## 📊 PASO 6: Configurar Grafana (5 minutos)

### A. Agregar Data Source

1. Click **⚙️ Configuration** → **Data Sources**
2. Click **Add data source**
3. Seleccionar **Prometheus**
4. Configurar:
   - **Name**: `Prometheus`
   - **URL**: `http://localhost:9090`
5. Click **Save & Test**
6. Debe decir: ✅ "Data source is working"

### B. Importar Dashboard

1. Click **+** → **Import**
2. Ingresar Dashboard ID: `1860`
3. Click **Load**
4. Seleccionar **Prometheus** data source
5. Click **Import**

Ahora verás el dashboard "Node Exporter Full" con todas las métricas del sistema.

### C. Crear Dashboard BioQL (opcional)

1. Click **+** → **Dashboard** → **Add new panel**
2. Query: `up{job=~"bioql.*"}`
3. Title: "BioQL Services Status"
4. Visualization: **Stat**
5. Click **Apply**
6. Click **💾 Save dashboard**
7. Nombre: "BioQL Monitoring"

---

## 🎉 RESULTADO FINAL

### ✅ 6/6 Servicios Online

```
✅ BioQL Core              → https://api.bioql.bio/health
✅ Quantum Execution       → https://api.bioql.bio/api/quantum/execute
✅ Workflows               → https://api.bioql.bio/workflow/health
✅ Lab Notebook            → https://api.bioql.bio/lab-notebook/health ← NUEVO
✅ Quantum Docking         → https://api.bioql.bio/health/quantum-docking
✅ Quantum Graphs          → https://api.bioql.bio/quantum-graph/health
```

### ✅ Monitoreo Activo

```
✅ Prometheus              → http://localhost:9090 (via SSH tunnel)
✅ Node Exporter           → Métricas del sistema
✅ Grafana                 → http://localhost:3000 (via SSH tunnel)
```

**SISTEMA BIOQL AL 100% COMPLETO** 🚀

---

## 📝 TIEMPO ESTIMADO

- Lab Notebook: 5 minutos
- Prometheus + Grafana: 15 minutos
- Configurar Grafana: 5 minutos
- **Total: 25 minutos**

---

## 🆘 SI ALGO FALLA

### Lab Notebook no configura

```bash
# Ver si ya está configurado
grep -n "Lab Notebook" /etc/nginx/sites-available/bioql

# Ver últimos backups
ls -lt /etc/nginx/sites-available/bioql.backup_* | head -3

# Restaurar backup
cp /etc/nginx/sites-available/bioql.backup_notebook_final_* /etc/nginx/sites-available/bioql
systemctl reload nginx
```

### Prometheus no inicia

```bash
# Ver logs
journalctl -xeu prometheus | tail -20

# Verificar config
promtool check config /etc/prometheus/prometheus.yml

# Reiniciar
systemctl restart prometheus
```

### Grafana no accesible

```bash
# Ver logs
journalctl -xeu grafana-server | tail -20

# Verificar puerto
netstat -tulpn | grep 3000

# Asegurar túnel SSH
ssh -L 3000:localhost:3000 root@167.71.86.90
```

---

**¡LISTO PARA EJECUTAR!** 🎯

Copia cada bloque y pégalo en tu terminal SSH del servidor.
