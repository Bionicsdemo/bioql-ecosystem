# 🎉 Monitoreo BioQL - Instalación Completa

**Fecha**: 29 de Octubre 2025
**Servidor**: api.bioql.bio (167.71.86.90)
**Estado**: ✅ OPERATIVO

---

## ✅ Servicios Instalados

### 1. Prometheus
- **Puerto**: 9090
- **Status**: `active`
- **Acceso**: http://localhost:9090 (vía túnel SSH)
- **Función**: Base de datos de métricas time-series
- **Scraping Interval**: 15-30 segundos

### 2. Node Exporter
- **Puerto**: 9100
- **Status**: `active`
- **Función**: Exportador de métricas del sistema
- **Métricas**: CPU, RAM, Disco, Network, Procesos

### 3. Grafana
- **Puerto**: 3000
- **Status**: `active`
- **Acceso**: http://localhost:3000 (vía túnel SSH)
- **Usuario**: `admin`
- **Password**: `admin` (cambiar en primer login)
- **Función**: Dashboard de visualización

---

## 📊 Servicios BioQL Monitoreados

Prometheus está configurado para monitorear los siguientes endpoints:

```yaml
scrape_configs:
  - job_name: 'bioql_services'
    static_configs:
      - targets:
          - 'localhost:5001'  # Workflows
          - 'localhost:5002'  # Quantum Graphs
          - 'localhost:5003'  # Lab Notebook (local)
          - 'localhost:8100'  # Quantum Docking
          - 'localhost:9000'  # Quantum Execution
    scrape_interval: 30s
```

---

## 🚀 Acceso a Monitoreo

### A) Prometheus

```bash
# 1. Crear túnel SSH
ssh -L 9090:localhost:9090 root@167.71.86.90
# Password: P31e27r12u1@HJG

# 2. Abrir en navegador
open http://localhost:9090
```

**Endpoints útiles:**
- http://localhost:9090 → Interfaz principal
- http://localhost:9090/targets → Ver estado de servicios monitoreados
- http://localhost:9090/graph → Crear gráficos de métricas

### B) Grafana

```bash
# 1. Crear túnel SSH
ssh -L 3000:localhost:3000 root@167.71.86.90
# Password: P31e27r12u1@HJG

# 2. Abrir en navegador
open http://localhost:3000
```

**Login inicial:**
- Usuario: `admin`
- Password: `admin`
- Te pedirá cambiar la contraseña en el primer login

---

## 📝 Configurar Grafana (Primera vez)

### 1. Agregar Prometheus como Data Source

1. En Grafana: **Configuration** (⚙️) → **Data Sources**
2. Click **Add data source**
3. Seleccionar **Prometheus**
4. Configuración:
   - **Name**: `Prometheus`
   - **URL**: `http://localhost:9090`
   - **Access**: `Server (default)`
5. Click **Save & Test** → Debe mostrar "Data source is working"

### 2. Importar Dashboard de Node Exporter

1. Click **+** (Create) → **Import**
2. **Dashboard ID**: `1860` (Node Exporter Full)
3. **Name**: `BioQL Server Metrics`
4. **Prometheus**: Seleccionar `Prometheus`
5. Click **Import**

**Métricas que verás:**
- CPU Usage (%)
- Memory Usage (%)
- Disk I/O
- Network Traffic
- System Load
- Procesos corriendo

### 3. Crear Dashboard Personalizado para BioQL

1. Click **+** → **Dashboard**
2. Click **Add panel**
3. En **Metrics**, usar queries como:
   ```promql
   up{job="bioql_services"}
   ```

**Queries útiles:**
```promql
# Servicios activos
up{job="bioql_services"}

# CPU del servidor
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memoria disponible
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100

# Requests HTTP (si tienes metrics endpoint en tus servicios)
rate(http_requests_total[5m])
```

---

## 🔍 Verificar Estado de Servicios

### Desde el servidor:

```bash
ssh root@167.71.86.90

# Ver status de Prometheus
systemctl status prometheus

# Ver status de Node Exporter
systemctl status prometheus-node-exporter

# Ver status de Grafana
systemctl status grafana-server

# Ver logs
journalctl -u prometheus -f
journalctl -u grafana-server -f
```

### Desde Prometheus (Web UI):

1. Abrir http://localhost:9090/targets
2. Verificar que todos los targets estén **UP** (verde)
3. Si alguno está **DOWN** (rojo), revisar logs del servicio

---

## 📈 Dashboards Recomendados

### Para importar desde Grafana:

| Dashboard | ID | Descripción |
|-----------|----|----|
| Node Exporter Full | 1860 | Métricas completas del servidor |
| Prometheus 2.0 Stats | 3662 | Estadísticas de Prometheus |
| Node Exporter for Prometheus Dashboard | 11074 | Dashboard alternativo |

**Cómo importar:**
1. Grafana → **+** → **Import**
2. Ingresar Dashboard ID
3. Seleccionar Data Source: `Prometheus`
4. Click **Import**

---

## 🎯 Próximos Pasos

### 1. Agregar Endpoints de Métricas a Servicios BioQL

Para que Prometheus pueda recolectar métricas detalladas de tus servicios, debes agregar un endpoint `/metrics` en cada uno:

**Ejemplo en Flask:**
```python
from prometheus_client import Counter, generate_latest
from flask import Response

# Contador de requests
REQUEST_COUNT = Counter('app_requests_total', 'Total de requests')

@app.route('/metrics')
def metrics():
    REQUEST_COUNT.inc()
    return Response(generate_latest(), mimetype='text/plain')
```

**Ejemplo en FastAPI:**
```python
from prometheus_client import Counter, generate_latest
from starlette.responses import Response

REQUEST_COUNT = Counter('app_requests_total', 'Total de requests')

@app.get('/metrics')
async def metrics():
    REQUEST_COUNT.inc()
    return Response(generate_latest(), media_type='text/plain')
```

### 2. Configurar Alertas en Prometheus

Editar `/etc/prometheus/prometheus.yml` para agregar alertas:

```yaml
rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093
```

Crear `/etc/prometheus/alerts.yml`:

```yaml
groups:
  - name: bioql_alerts
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up{job="bioql_services"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "BioQL service {{ $labels.instance }} is down"

      - alert: HighCPU
        expr: 100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU usage above 80%"
```

### 3. Configurar Alertmanager (Notificaciones)

```bash
apt-get install -y prometheus-alertmanager

# Configurar en /etc/prometheus/alertmanager.yml
systemctl start prometheus-alertmanager
systemctl enable prometheus-alertmanager
```

---

## 📁 Archivos de Configuración

### Prometheus
- **Config**: `/etc/prometheus/prometheus.yml`
- **Data**: `/var/lib/prometheus/`
- **Logs**: `journalctl -u prometheus`

### Grafana
- **Config**: `/etc/grafana/grafana.ini`
- **Data**: `/var/lib/grafana/`
- **Logs**: `journalctl -u grafana-server`

### Node Exporter
- **Config**: `/etc/default/prometheus-node-exporter`
- **Logs**: `journalctl -u prometheus-node-exporter`

---

## 🛠️ Scripts de Instalación

Todos los scripts están en:
```
/Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/deployment/scripts/
```

### Scripts disponibles:

1. **install_monitoring_simple.sh** ✅ (Ejecutado exitosamente)
   - Instala Prometheus + Grafana
   - No modifica Nginx
   - Instalación limpia y verificada

2. **configuracion_final_completa.sh** (Con confirmación)
   - Instala monitoreo + configura Lab Notebook en Nginx
   - Pide confirmación antes de ejecutar

3. **configuracion_final_auto.sh** (Automático - NO USAR)
   - Tiene bug en la inserción de Nginx
   - Mantener para referencia histórica

---

## 🔒 Seguridad

### Cambiar password de Grafana:

1. Login inicial con `admin`/`admin`
2. Grafana pedirá cambiar password
3. Usar password seguro

### Configurar HTTPS para Grafana (Opcional):

```bash
# Editar /etc/grafana/grafana.ini
[server]
protocol = https
cert_file = /etc/letsencrypt/live/api.bioql.bio/fullchain.pem
cert_key = /etc/letsencrypt/live/api.bioql.bio/privkey.pem
```

### Restringir acceso por IP:

```bash
# Usar UFW firewall
ufw allow from TU_IP to any port 3000
ufw allow from TU_IP to any port 9090
```

---

## 📊 Métricas Actuales del Sistema

### Estado de Servicios BioQL:

| Servicio | Puerto | Status | URL Pública |
|----------|--------|--------|-------------|
| BioQL Core | - | ✅ | https://api.bioql.bio/health |
| Workflows | 5001 | ✅ | https://api.bioql.bio/workflow/health |
| Quantum Graphs | 5002 | ✅ | https://api.bioql.bio/quantum-graph/health |
| Lab Notebook | 5003 | ✅ Local | (No en Nginx aún) |
| Quantum Docking | 8100 | ✅ | https://api.bioql.bio/health/quantum-docking |
| Quantum Execution | 9000 | ✅ | https://api.bioql.bio/api/quantum/execute |

### Estado de Monitoreo:

| Servicio | Puerto | Status |
|----------|--------|--------|
| Prometheus | 9090 | ✅ active |
| Node Exporter | 9100 | ✅ active |
| Grafana | 3000 | ✅ active |

---

## 🎉 Resumen

✅ **Instalación Completa**: 3/3 servicios de monitoreo instalados
✅ **Configuración**: Prometheus monitoreando 5 servicios BioQL
✅ **Acceso**: Túneles SSH configurados para Grafana y Prometheus
✅ **Seguridad**: Servicios corriendo en localhost, acceso vía SSH
✅ **Documentación**: Guías completas de uso y configuración

**Próximos pasos opcionales:**
- [ ] Configurar Lab Notebook en Nginx
- [ ] Agregar endpoints `/metrics` a servicios BioQL
- [ ] Configurar alertas en Prometheus
- [ ] Instalar Alertmanager para notificaciones

---

**Script ejecutado exitosamente el**: 29/10/2025 09:06
**Tiempo de instalación**: ~15 minutos
**Sin errores**: ✅
