# 🚀 Quick Start - Monitor de Servicios (5 Minutos)

## ✅ Estado Actual

**Servicios Detectados:**
- ✅ Python Server (PID: 1174) - Puerto 5001
- ✅ ngrok Tunnel - https://aae99709f69d.ngrok-free.app
- ⏸️ Monitor - No corriendo (vamos a iniciarlo)

---

## 🎯 Inicio Rápido (3 Comandos)

```bash
cd /Users/heinzjungbluth/Desktop/bioql

# 1. Verificar estado actual
./check_services.sh

# 2. Iniciar monitor en background
nohup ./monitor_services.sh > logs/monitor_nohup.log 2>&1 &

# 3. Verificar que inició
sleep 3 && tail -20 logs/monitor.log
```

**¡Listo!** El monitor ya está corriendo y revisará cada 24 horas.

---

## 📋 Opción Alternativa: Reiniciar Todo Limpio

```bash
# 1. Detener servicios actuales
./stop_services.sh

# 2. Iniciar todo desde cero (Server + ngrok + Monitor)
./start_services.sh

# 3. Ver estado
./check_services.sh
```

---

## 🔍 Ver Logs en Tiempo Real

```bash
# Monitor principal
tail -f logs/monitor.log

# Todos los logs
tail -f logs/*.log

# Solo errores
tail -f logs/monitor.log | grep ERROR
```

---

## 📊 Verificar Funcionamiento

### Test Manual del Monitor

```bash
# Ver si está corriendo
ps aux | grep monitor_services.sh | grep -v grep

# Si NO está corriendo, iniciarlo
nohup ./monitor_services.sh > logs/monitor_nohup.log 2>&1 &

# Verificar PID
echo "Monitor PID: $(pgrep -f monitor_services.sh)"
```

### Ver Último Check

```bash
tail -50 logs/monitor.log
```

### Forzar Check Inmediato (para testing)

```bash
# Modificar intervalo temporalmente (en monitor_services.sh línea 15)
# CHECK_INTERVAL=300  # 5 minutos en lugar de 24 horas

# O ejecutar manualmente las funciones de check
./check_services.sh
```

---

## 🔧 Configuración del Monitor

### Cambiar Intervalo de Revisión

**Editar:** `monitor_services.sh` línea 15

```bash
CHECK_INTERVAL=86400   # 24 horas (default)
CHECK_INTERVAL=43200   # 12 horas
CHECK_INTERVAL=21600   # 6 horas
CHECK_INTERVAL=3600    # 1 hora
CHECK_INTERVAL=300     # 5 minutos (testing)
```

### Activar Alertas por Email

**Editar:** `monitor_services.sh` línea 16

```bash
ALERT_EMAIL="tu@email.com"
```

---

## 📁 Archivos Creados

```
bioql/
├── monitor_services.sh          ← Monitor principal (corre en nohup)
├── start_services.sh            ← Inicia todo
├── stop_services.sh             ← Detiene todo
├── check_services.sh            ← Verifica estado
├── SERVICE_MONITOR_GUIDE.md     ← Guía completa
├── QUICK_START_MONITOR.md       ← Esta guía
└── logs/
    ├── monitor.log              ← Log principal del monitor
    ├── monitor_nohup.log        ← Output de nohup
    ├── server_nohup.log         ← Logs del servidor
    ├── ngrok_nohup.log          ← Logs de ngrok
    └── current_tunnel_url.txt   ← URL actual de ngrok
```

---

## ✅ Checklist de Verificación

### 1. Scripts Ejecutables
```bash
ls -l *.sh | grep rwx
# Deben tener permisos -rwxr-xr-x
```

### 2. Servicios Corriendo
```bash
./check_services.sh
# Todos deben mostrar ✓
```

### 3. Monitor Activo
```bash
ps aux | grep monitor_services.sh | grep -v grep
# Debe mostrar un proceso
```

### 4. Logs Generándose
```bash
tail -f logs/monitor.log
# Debe mostrar actividad
```

### 5. ngrok URL Disponible
```bash
cat logs/current_tunnel_url.txt
# Debe mostrar URL https://
```

---

## 🚨 Troubleshooting Rápido

### Monitor no inicia

```bash
# Dar permisos
chmod +x monitor_services.sh

# Ver errores
cat logs/monitor_nohup.log

# Iniciar manualmente para ver errores
./monitor_services.sh
```

### Servicios caídos

```bash
# Reiniciar todo
./stop_services.sh
sleep 2
./start_services.sh
```

### Logs no se crean

```bash
# Crear directorio de logs
mkdir -p logs

# Verificar permisos
ls -ld logs
```

---

## 📊 Lo Que Hace el Monitor Cada 24 Horas

1. ✅ **Verifica servidor Python**
   - Proceso corriendo
   - Puerto escuchando
   - Health endpoint (/health)

2. ✅ **Verifica ngrok**
   - Proceso corriendo
   - Túnel activo
   - URL accesible

3. ✅ **Verifica recursos**
   - Uso de memoria
   - Uso de disco
   - Tamaño de logs

4. 🔄 **Auto-restart**
   - Reinicia servicios caídos
   - Verifica que iniciaron correctamente
   - Registra en logs

5. 🧹 **Limpieza**
   - Comprime logs >7 días
   - Elimina logs >30 días

---

## 🎯 Comandos de Un Vistazo

```bash
# Estado
./check_services.sh

# Iniciar todo
./start_services.sh

# Detener todo
./stop_services.sh

# Ver logs
tail -f logs/monitor.log

# Reiniciar
./stop_services.sh && ./start_services.sh

# PID del monitor
pgrep -f monitor_services.sh

# Matar monitor
pkill -f monitor_services.sh
```

---

## 🔥 Firebase (Opcional)

### Si quieres auto-deploy a Firebase

```bash
# 1. Instalar Firebase CLI
npm install -g firebase-tools

# 2. Login
firebase login

# 3. Init
firebase init hosting

# 4. Descomentar en monitor_services.sh línea ~290
# deploy_to_firebase

# 5. Reiniciar monitor
pkill -f monitor_services.sh
nohup ./monitor_services.sh > logs/monitor_nohup.log 2>&1 &
```

---

## 📞 Próximos Pasos

1. **Ahora mismo:**
   ```bash
   nohup ./monitor_services.sh > logs/monitor_nohup.log 2>&1 &
   ```

2. **En 5 minutos:**
   ```bash
   tail logs/monitor.log
   # Verificar que hay actividad
   ```

3. **En 24 horas:**
   ```bash
   tail logs/monitor.log
   # Debe haber un nuevo check completo
   ```

4. **Opcional:**
   - Configurar email alerts
   - Ajustar intervalo de checks
   - Integrar con Firebase

---

## 🎉 ¡Ya Está Listo!

**El monitor ahora:**
- ✅ Corre en background con nohup
- ✅ Revisa servicios cada 24 horas
- ✅ Auto-reinicia si algo falla
- ✅ Guarda logs detallados
- ✅ Limpia logs viejos automáticamente

**Para verificar:**
```bash
./check_services.sh
```

**Debería mostrar todo en verde (✓)**

---

*Creado: 2 de Octubre, 2025*
*Status: ✅ Listo para Producción*
