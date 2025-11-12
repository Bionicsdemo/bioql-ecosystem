# 🔍 BioQL Service Monitor - Complete Guide

## Overview

Sistema de monitoreo automático que revisa cada 24 horas el estado de:
- ✅ Servidor Python (bioql_auth_server.py)
- ✅ Túnel ngrok
- ✅ Configuración de Firebase
- ✅ Recursos del sistema

**Características:**
- 🔄 Auto-restart de servicios caídos
- 📊 Logging detallado
- 🚨 Sistema de alertas
- 🧹 Limpieza automática de logs
- 📧 Notificaciones por email (opcional)

---

## 🚀 Quick Start

### Opción 1: Inicio Rápido (Recomendado)
```bash
cd /Users/heinzjungbluth/Desktop/bioql

# Iniciar todos los servicios + monitor
./start_services.sh
```

### Opción 2: Solo Monitor (si servicios ya están corriendo)
```bash
nohup ./monitor_services.sh > logs/monitor_nohup.log 2>&1 &
```

---

## 📋 Scripts Disponibles

### 1. `start_services.sh` - Iniciar Todo
```bash
./start_services.sh
```

**Inicia:**
- Python server (puerto 5001)
- ngrok tunnel
- Service monitor (check cada 24h)

**Output:**
```
=========================================
All services started!
=========================================
Server PID:    12345
ngrok PID:     12346
Monitor PID:   12347

Tunnel URL:    https://abc123.ngrok-free.app

Logs:
  Server:  tail -f logs/server_nohup.log
  ngrok:   tail -f logs/ngrok_nohup.log
  Monitor: tail -f logs/monitor.log
```

---

### 2. `stop_services.sh` - Detener Todo
```bash
./stop_services.sh
```

**Detiene:**
- Monitor
- ngrok
- Python server

---

### 3. `check_services.sh` - Verificar Estado
```bash
./check_services.sh
```

**Muestra:**
- Estado de cada servicio
- PIDs activos
- Salud de endpoints
- URL del túnel ngrok
- Uso de recursos
- Logs recientes

**Output:**
```
=========================================
BioQL Services Status
=========================================

1. Python Server:
   ✓ Running (PID: 12345)
   ✓ Listening on port 5001
   ✓ Health check passed

2. ngrok Tunnel:
   ✓ Running (PID: 12346)
   ✓ Tunnel active
   URL: https://abc123.ngrok-free.app
   ✓ Tunnel accessible (HTTP 200)

3. Service Monitor:
   ✓ Running (PID: 12347)
   Last check: [2025-10-02 15:30:00] All services healthy

4. System Resources:
   Memory: 45.3%
   Disk: 62%
   Logs: 125M
```

---

### 4. `monitor_services.sh` - Monitor Principal
```bash
# Ejecutar en background con nohup
nohup ./monitor_services.sh > logs/monitor_nohup.log 2>&1 &

# Ver logs en tiempo real
tail -f logs/monitor.log
```

**Funciones:**
- Check cada 24 horas
- Auto-restart servicios caídos
- Health checks HTTP
- Logging estructurado
- Limpieza de logs

---

## 📁 Estructura de Logs

```
bioql/
├── logs/
│   ├── monitor.log              # Monitor principal
│   ├── monitor_nohup.log        # nohup output del monitor
│   ├── server_nohup.log         # Server output
│   ├── ngrok_nohup.log          # ngrok output
│   ├── firebase_deploy.log      # Firebase deployments
│   ├── current_tunnel_url.txt   # URL actual de ngrok
│   └── *.log.gz                 # Logs comprimidos (>7 días)
```

---

## 🔧 Configuración

### Variables en `monitor_services.sh`

```bash
# Editar líneas 8-15:
PROJECT_DIR="/Users/heinzjungbluth/Desktop/bioql"
SERVER_SCRIPT="scripts/admin/bioql_auth_server.py"
SERVER_PORT=5001
NGROK_PORT=5001
CHECK_INTERVAL=86400  # 24 horas en segundos
ALERT_EMAIL=""  # Tu email para alertas
```

### Cambiar Intervalo de Monitoreo

```bash
# Para 12 horas:
CHECK_INTERVAL=43200

# Para 6 horas:
CHECK_INTERVAL=21600

# Para 1 hora (testing):
CHECK_INTERVAL=3600
```

---

## 🔥 Firebase Deployment

### Setup Inicial de Firebase

```bash
# 1. Instalar Firebase CLI
npm install -g firebase-tools

# 2. Login
firebase login

# 3. Inicializar proyecto
cd /Users/heinzjungbluth/Desktop/bioql
firebase init hosting
```

### Configuración `firebase.json`

```json
{
  "hosting": {
    "public": "public",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

### Deploy Manual

```bash
firebase deploy --only hosting
```

### Deploy Automático con Monitor

El monitor puede deployar automáticamente si descomentas:

```bash
# En monitor_services.sh, línea ~280
# Descomentar para auto-deploy:
# deploy_to_firebase
```

---

## 📊 Health Checks Realizados

### 1. Python Server
```bash
✓ Proceso corriendo (pgrep)
✓ Puerto escuchando (lsof)
✓ HTTP health endpoint (/health)
```

### 2. ngrok Tunnel
```bash
✓ Proceso corriendo
✓ Túnel activo (API ngrok)
✓ URL accesible (curl)
✓ HTTP status code válido
```

### 3. Sistema
```bash
✓ Uso de memoria
✓ Uso de disco
✓ Tamaño de logs
```

---

## 🚨 Sistema de Alertas

### Configurar Email

1. Editar `monitor_services.sh`:
   ```bash
   ALERT_EMAIL="tu@email.com"
   ```

2. Configurar `mail` en macOS:
   ```bash
   # Instalar mailutils si no está
   brew install mailutils
   ```

### Tipos de Alertas

- ⚠️ **WARNING:** Disco >90%, logs grandes
- 🚨 **CRITICAL:** Servicio no inicia, túnel caído

---

## 📝 Logs y Debugging

### Ver Logs en Tiempo Real

```bash
# Monitor principal
tail -f logs/monitor.log

# Servidor
tail -f logs/server_nohup.log

# ngrok
tail -f logs/ngrok_nohup.log

# Todos juntos
tail -f logs/*.log
```

### Buscar Errores

```bash
# Errores en monitor
grep ERROR logs/monitor.log

# Últimas 50 líneas del servidor
tail -50 logs/server_nohup.log

# Logs de hoy
grep "$(date +%Y-%m-%d)" logs/monitor.log
```

### Limpiar Logs Manualmente

```bash
# Comprimir logs viejos
find logs -name "*.log" -mtime +7 -exec gzip {} \;

# Eliminar logs >30 días
find logs -name "*.log.gz" -mtime +30 -delete

# Ver tamaño de logs
du -sh logs/
```

---

## 🔄 Auto-Recovery

### Servicios Se Auto-Reinician

Si el monitor detecta un servicio caído:

1. **Intenta reiniciar** automáticamente
2. **Espera 5 segundos** para verificar
3. **Confirma** que el servicio está funcionando
4. **Registra** el evento en logs
5. **Envía alerta** si falla el reinicio

### Ejemplo de Recovery

```
[2025-10-02 15:30:00] Python server check failed
[2025-10-02 15:30:01] Attempting restart...
[2025-10-02 15:30:06] Server started with PID: 12345
[2025-10-02 15:30:07] Server recovery successful
```

---

## 🛠️ Troubleshooting

### Monitor No Inicia

```bash
# Verificar permisos
ls -l monitor_services.sh
# Debe mostrar: -rwxr-xr-x

# Dar permisos si falta
chmod +x monitor_services.sh

# Ver errores
cat logs/monitor_nohup.log
```

### ngrok No Se Conecta

```bash
# Verificar ngrok
ngrok version

# Test manual
ngrok http 5001

# Ver API de ngrok
curl http://localhost:4040/api/tunnels
```

### Servidor No Responde

```bash
# Verificar puerto
lsof -i :5001

# Test health endpoint
curl http://localhost:5001/health

# Ver logs del servidor
tail -50 logs/server_nohup.log
```

### Monitor No Hace Checks

```bash
# Verificar si está corriendo
ps aux | grep monitor_services.sh

# Ver último log
tail logs/monitor.log

# Forzar check manual
./check_services.sh
```

---

## 📈 Métricas y Estadísticas

### Ver Uptime

```bash
# Cuánto tiempo lleva corriendo el monitor
ps -p $(pgrep -f monitor_services.sh) -o etime=
```

### Contar Checks Realizados

```bash
grep "Starting 24-Hour Health Check" logs/monitor.log | wc -l
```

### Ver Histórico de Errores

```bash
grep ERROR logs/monitor.log | tail -20
```

### Estadísticas de Recovery

```bash
grep "recovery successful" logs/monitor.log | wc -l
```

---

## 🔒 Seguridad

### Mejores Prácticas

1. **No commitear logs:**
   ```bash
   echo "logs/" >> .gitignore
   ```

2. **Rotar logs regularmente:**
   - Automático: cada 30 días
   - Manual: `find logs -name "*.log" -mtime +30 -delete`

3. **Proteger túnel ngrok:**
   ```bash
   # Agregar auth a ngrok
   ngrok http 5001 --auth="user:password"
   ```

4. **Usar HTTPS siempre:**
   - ngrok provee HTTPS por defecto

---

## 🚀 Producción

### Recomendaciones para Prod

1. **Usar systemd en lugar de nohup:**
   ```bash
   # Crear /etc/systemd/system/bioql-monitor.service
   # (Ver ejemplo abajo)
   ```

2. **Monitoreo externo:**
   - UptimeRobot
   - Pingdom
   - StatusCake

3. **Logs centralizados:**
   - Papertrail
   - Loggly
   - ELK Stack

4. **ngrok alternativas para prod:**
   - Usar dominio propio
   - Nginx reverse proxy
   - Cloudflare Tunnel

---

## 📦 systemd Service Example

```ini
# /etc/systemd/system/bioql-monitor.service
[Unit]
Description=BioQL Service Monitor
After=network.target

[Service]
Type=simple
User=heinzjungbluth
WorkingDirectory=/Users/heinzjungbluth/Desktop/bioql
ExecStart=/Users/heinzjungbluth/Desktop/bioql/monitor_services.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar
sudo systemctl enable bioql-monitor

# Iniciar
sudo systemctl start bioql-monitor

# Ver status
sudo systemctl status bioql-monitor
```

---

## ✅ Checklist de Setup

- [ ] Scripts creados y ejecutables
- [ ] Probado `./start_services.sh`
- [ ] Verificado con `./check_services.sh`
- [ ] Logs en `logs/` funcionando
- [ ] ngrok conectado y URL disponible
- [ ] Firebase configurado (opcional)
- [ ] Email alerts configurado (opcional)
- [ ] Monitor corriendo en background
- [ ] Todo funcionando 24h sin problemas

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisa logs:** `tail -f logs/monitor.log`
2. **Verifica estado:** `./check_services.sh`
3. **Reinicia servicios:** `./stop_services.sh && ./start_services.sh`
4. **Contacta soporte:** support@bioql.com

---

## 🎉 Quick Commands Reference

```bash
# Iniciar todo
./start_services.sh

# Ver estado
./check_services.sh

# Ver logs
tail -f logs/monitor.log

# Detener todo
./stop_services.sh

# Reiniciar
./stop_services.sh && ./start_services.sh

# Ver URL de ngrok
cat logs/current_tunnel_url.txt
```

---

**¡Todo listo para correr 24/7!** 🚀

*Last Updated: October 2, 2025*
