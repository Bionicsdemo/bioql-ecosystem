# 🚀 Configuración Final Completa - BioQL

**Objetivo**: Configurar Lab Notebook en Nginx e instalar monitoreo Prometheus/Grafana

---

## 📋 RESUMEN

Dos tareas finales para llegar al 100%:

1. **✅ Configurar Lab Notebook en Nginx** (5 minutos)
   - Lab Notebook ya funciona localmente en puerto 5003
   - Necesita configurarse en Nginx para acceso público

2. **✅ Instalar Prometheus + Grafana** (15 minutos)
   - Monitoreo de todos los servicios
   - Dashboards visuales
   - Alertas automáticas

---

## 1️⃣ CONFIGURAR LAB NOTEBOOK (5 minutos)

### Paso 1: Conectar al servidor

```bash
ssh root@167.71.86.90
# Password: P31e27r12u1@HJG
```

### Paso 2: Descargar el script

```bash
cd /tmp
cat > configure_lab_notebook.sh << 'ENDSCRIPT'
#!/bin/bash
# Script para configurar Lab Notebook en Nginx

echo "=========================================="
echo "📓 CONFIGURANDO LAB NOTEBOOK EN NGINX"
echo "=========================================="

# Verificar que Lab Notebook esté corriendo
echo ""
echo "🔍 Verificando Lab Notebook en puerto 5003..."
NOTEBOOK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5003/health)

if [ "$NOTEBOOK_STATUS" != "200" ]; then
    echo "❌ Lab Notebook no está respondiendo"
    exit 1
fi

echo "✅ Lab Notebook funcionando"

# Backup de Nginx
echo "📦 Creando backup..."
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_notebook_final_$(date +%Y%m%d_%H%M%S)

# Crear configuración
cat > /tmp/lab_notebook_nginx.conf << 'ENDNGINX'

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
ENDNGINX

# Insertar después del bloque de Workflows
WORKFLOW_LINE=$(grep -n "location /workflow/ {" /etc/nginx/sites-available/bioql | cut -d: -f1)
INSERT_LINE=$((WORKFLOW_LINE + 12))
sed -i "${INSERT_LINE}r /tmp/lab_notebook_nginx.conf" /etc/nginx/sites-available/bioql

# Test con timeout
echo "🧪 Testing sintaxis..."
if timeout 10 nginx -t 2>&1; then
    echo "✅ Sintaxis correcta"
    systemctl reload nginx
    echo "✅ Nginx recargado"

    # Test
    sleep 2
    curl -s https://api.bioql.bio/lab-notebook/health

    echo ""
    echo "✅ LAB NOTEBOOK CONFIGURADO"
    echo "   URL: https://api.bioql.bio/lab-notebook/health"
else
    echo "❌ Error en sintaxis"
    LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/bioql.backup_notebook_final_* | head -1)
    cp $LATEST_BACKUP /etc/nginx/sites-available/bioql
fi
ENDSCRIPT

chmod +x configure_lab_notebook.sh
```

### Paso 3: Ejecutar el script

```bash
bash configure_lab_notebook.sh
```

### Resultado Esperado

```
✅ LAB NOTEBOOK CONFIGURADO
   URL: https://api.bioql.bio/lab-notebook/health
```

### Verificación

```bash
# Desde el servidor
curl -s https://api.bioql.bio/lab-notebook/health

# Desde tu computadora
open https://api.bioql.bio/lab-notebook/health
```

---

## 2️⃣ INSTALAR PROMETHEUS + GRAFANA (15 minutos)

### Paso 1: Ya deberías estar conectado al servidor

```bash
ssh root@167.71.86.90
# (si no estás conectado ya)
```

### Paso 2: Ejecutar instalación automatizada

```bash
# Instalar Prometheus, Node Exporter y Grafana
curl -sL https://raw.githubusercontent.com/prometheus/prometheus/main/documentation/examples/prometheus-install.sh | bash

# O manualmente:
apt-get update
apt-get install -y prometheus prometheus-node-exporter grafana
```

### Paso 3: Configurar Prometheus para BioQL

```bash
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
      - targets:
        - 'localhost:5001'  # BioQL Core
        - 'localhost:5002'  # Workflows
        - 'localhost:5003'  # Lab Notebook
        - 'localhost:8100'  # Quantum Docking
        - 'localhost:9000'  # Quantum Graphs
    scrape_interval: 30s
ENDPROM

# Reiniciar Prometheus
systemctl restart prometheus
systemctl enable prometheus
```

### Paso 4: Iniciar Grafana

```bash
systemctl start grafana-server
systemctl enable grafana-server
systemctl status grafana-server
```

### Paso 5: Configurar Nginx para Grafana

```bash
# Backup
cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_grafana_$(date +%Y%m%d_%H%M%S)

# Agregar al final del primer server block (antes del último })
cat >> /etc/nginx/sites-available/bioql << 'ENDGRAFANA'

    # Grafana Dashboard
    location /grafana/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
ENDGRAFANA

# NOTA: Esto puede fallar, si falla simplemente accede a Grafana directamente:
# ssh -L 3000:localhost:3000 root@167.71.86.90
# Luego abre: http://localhost:3000
```

### Paso 6: Verificación

```bash
# Ver que Prometheus esté corriendo
systemctl status prometheus

# Ver métricas
curl -s http://localhost:9090/metrics | head -20

# Ver que Grafana esté corriendo
systemctl status grafana-server
```

---

## 3️⃣ CONFIGURAR GRAFANA (5 minutos)

### Acceder a Grafana

**Opción A: Via SSH Tunnel (RECOMENDADO)**

```bash
# Desde tu computadora local
ssh -L 3000:localhost:3000 root@167.71.86.90

# Abrir en navegador
open http://localhost:3000
```

**Opción B: Via Nginx (si configuraste el proxy)**

```bash
open https://api.bioql.bio/grafana/
```

### Login

```
Usuario: admin
Password: admin
```

**IMPORTANTE**: Cambia la contraseña en el primer login.

### Configurar Data Source

1. Click en **Configuration** (⚙️) → **Data Sources**
2. Click **Add data source**
3. Seleccionar **Prometheus**
4. Configurar:
   - **Name**: `Prometheus`
   - **URL**: `http://localhost:9090`
   - Click **Save & Test**

Debería decir: ✅ "Data source is working"

### Importar Dashboards

1. Click en **+** → **Import**
2. Importar estos dashboards:

**Dashboard 1: Node Exporter Full**
- Dashboard ID: `1860`
- Click **Load**
- Seleccionar Prometheus data source
- Click **Import**

**Dashboard 2: BioQL Services (personalizado)**
- Click **+** → **Dashboard** → **Add new panel**
- Query: `up{job=~"bioql.*"}`
- Title: "BioQL Services Status"
- Save dashboard como "BioQL Monitoring"

---

## 4️⃣ VERIFICACIÓN FINAL

### Todos los Servicios

```bash
# En el servidor
systemctl status prometheus
systemctl status prometheus-node-exporter
systemctl status grafana-server
systemctl status nginx

# Test endpoints
curl -s https://api.bioql.bio/health
curl -s https://api.bioql.bio/workflow/health
curl -s https://api.bioql.bio/lab-notebook/health  # ← NUEVO
curl -s https://api.bioql.bio/health/quantum-docking
curl -s https://api.bioql.bio/quantum-graph/health
```

### Dashboard de Grafana

1. Acceder a Grafana (http://localhost:3000 via SSH tunnel)
2. Ir a **Dashboards**
3. Abrir "Node Exporter Full"
4. Deberías ver:
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic
   - System load

---

## 📊 RESULTADO FINAL

### ✅ Servicios Configurados (6/6)

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
✅ Prometheus              → http://localhost:9090 (SSH tunnel)
✅ Node Exporter           → http://localhost:9100/metrics
✅ Grafana                 → http://localhost:3000 (SSH tunnel)
```

**PROGRESO: 100% COMPLETO** 🎉

---

## 🎯 PRÓXIMOS PASOS OPCIONALES

1. **Configurar Alertas en Grafana**
   - Alertas si CPU > 80%
   - Alertas si servicio está down
   - Notificaciones vía Email/Slack

2. **Agregar Métricas Personalizadas**
   - Shots ejecutados por hora
   - Costo promedio por job
   - Usuarios activos

3. **Backups Automáticos**
   - Script diario de backup
   - Subir a S3 o similar

---

## 📝 SCRIPTS CREADOS

Todos los scripts están en:
```
/Users/heinzjungbluth/Desktop/Spectrix_BioQL/scripts/deployment/
├── configure_lab_notebook.sh          # ← Configurar Lab Notebook
├── install_prometheus_grafana.sh      # ← Instalar monitoreo
└── ...
```

---

## 🆘 TROUBLESHOOTING

### Lab Notebook no responde

```bash
# Ver logs
journalctl -fu $(ps aux | grep 5003 | grep python | awk '{print $2}' | head -1)

# Reiniciar
pkill -f notebook_server
cd /opt/bioql && /opt/bioql/venv/bin/python notebook_server.py &
```

### Prometheus no inicia

```bash
# Ver logs
journalctl -xeu prometheus

# Verificar sintaxis del config
promtool check config /etc/prometheus/prometheus.yml

# Reiniciar
systemctl restart prometheus
```

### Grafana no accesible

```bash
# Ver logs
journalctl -xeu grafana-server

# Verificar puerto
netstat -tulpn | grep 3000

# Usar SSH tunnel
ssh -L 3000:localhost:3000 root@167.71.86.90
```

---

## ✅ CHECKLIST FINAL

- [ ] SSH al servidor
- [ ] Ejecutar configure_lab_notebook.sh
- [ ] Verificar Lab Notebook: `curl https://api.bioql.bio/lab-notebook/health`
- [ ] Instalar Prometheus y Grafana
- [ ] Configurar Prometheus para BioQL
- [ ] Acceder a Grafana via SSH tunnel
- [ ] Cambiar password de Grafana
- [ ] Agregar Prometheus como data source
- [ ] Importar dashboard Node Exporter (ID: 1860)
- [ ] Crear dashboard personalizado para BioQL
- [ ] Verificar todos los 6 servicios están online
- [ ] Crear git commit con todos los cambios

**Tiempo estimado total**: 25 minutos

---

**Última actualización**: 2025-10-29
**Scripts**: `configure_lab_notebook.sh`, `install_prometheus_grafana.sh`
