# 🎯 ACCIÓN INMEDIATA - BioQL Server Recovery

## 📊 SITUACIÓN ACTUAL (VERIFICADA)

```
✅ Servidor ONLINE: 167.71.86.90 responde a ping
✅ Puerto SSH 22: ABIERTO (nc test passed)
❌ SSH Banner: NO RESPONDE (saturado)
❌ Paramiko: FALLA (Error reading SSH protocol banner)
❌ Web services: TIMEOUT (posiblemente caídos)
```

---

## ⚡ LO QUE NECESITAS HACER AHORA

### Método más simple: Terminal SSH manual

**Abre una nueva ventana de Terminal** (Command + T) y ejecuta:

```bash
ssh root@167.71.86.90
```

**Password cuando te lo pida**:
```
P31e27r12u1@HJG
```

Si te pregunta "Are you sure you want to continue connecting?" → escribe `yes`

---

## 🔧 COMANDOS A EJECUTAR EN EL SERVIDOR

Una vez conectado via SSH, copia y pega estos comandos:

### 1. Verificar estado actual
```bash
echo "=== VERIFICANDO SERVICIOS ==="

# Ver procesos Python
echo "Procesos BioQL:"
ps aux | grep python | grep bioql | grep -v grep

# Ver Nginx
echo ""
echo "Nginx status:"
systemctl status nginx | head -5

# Ver puertos
echo ""
echo "Puertos escuchando:"
netstat -tulpn 2>/dev/null | grep LISTEN | grep -E "5001|5002|8100|9000|80|443"
```

### 2. Reiniciar servicios si están caídos
```bash
echo "=== REINICIANDO SERVICIOS ==="

# Reiniciar Nginx
systemctl restart nginx
echo "✅ Nginx reiniciado"

# Matar procesos viejos de BioQL
pkill -f "bioql_auth_server_stripe"
sleep 2

# Iniciar BioQL Core
cd /opt/bioql/auth_server
/opt/bioql/venv/bin/python bioql_auth_server_stripe.py > /tmp/bioql_restart_$(date +%H%M%S).log 2>&1 &
echo "✅ BioQL Core iniciado"

sleep 3

# Verificar que arrancó
ps aux | grep bioql_auth_server_stripe | grep -v grep
```

### 3. Limpiar SSH saturado
```bash
echo "=== LIMPIANDO SSH ==="

# Ver cuántas conexiones SSH hay
echo "Conexiones SSH actuales:"
ps aux | grep sshd | wc -l

# Reiniciar SSH service (esto NO te desconectará a ti)
systemctl restart sshd
echo "✅ SSH service reiniciado"

# Verificar
systemctl status sshd | head -3
```

### 4. Testear que todo funciona
```bash
echo "=== TESTING ENDPOINTS ==="

# Test local
curl -s http://127.0.0.1:5001/health
echo ""

# Test Nginx
curl -s http://127.0.0.1/health
echo ""

echo "✅ Si ves JSON arriba, el servidor está funcionando"
```

---

## 🔄 DESPUÉS DE REINICIAR SERVICIOS

**Regresa a tu computadora** y ejecuta:

```bash
# 1. Verificar que endpoints responden
curl -s https://api.bioql.bio/health

# 2. Ejecutar configuración final de Workflows
python3 /Users/heinzjungbluth/Desktop/configure_final.py
```

---

## 📋 COMANDOS RESUMIDOS (COPY-PASTE)

**Todo en uno** (ejecutar en el servidor):

```bash
#!/bin/bash
# BioQL Server Recovery Script

echo "🔧 REINICIANDO SERVICIOS BIOQL"
echo "================================"

# Nginx
systemctl restart nginx && echo "✅ Nginx OK"

# BioQL Core
pkill -f "bioql_auth_server_stripe"
sleep 2
cd /opt/bioql/auth_server && /opt/bioql/venv/bin/python bioql_auth_server_stripe.py > /tmp/bioql_$(date +%H%M%S).log 2>&1 &
echo "✅ BioQL Core iniciado"

# SSH cleanup
systemctl restart sshd && echo "✅ SSH service reiniciado"

sleep 3

# Verificar
echo ""
echo "🔍 VERIFICACIÓN:"
ps aux | grep bioql_auth_server_stripe | grep -v grep | head -1
systemctl is-active nginx
systemctl is-active sshd

echo ""
echo "🧪 TEST:"
curl -s http://127.0.0.1:5001/health | head -3

echo ""
echo "✅ LISTO - Puedes desconectarte"
```

---

## 🚀 ALTERNATIVA: Si SSH manual tampoco funciona

### Usar el panel de control del hosting

1. **DigitalOcean**: https://cloud.digitalocean.com/
   - Buscar droplet con IP 167.71.86.90
   - Click en "Access" → "Launch Droplet Console"

2. **AWS**: https://console.aws.amazon.com/
   - Buscar EC2 instance con IP 167.71.86.90
   - "Connect" → "EC2 Instance Connect"

3. **Otro hosting**: Buscar "Console" o "VNC" en el panel

4. **Login**: root / P31e27r12u1@HJG

5. **Ejecutar el script resumido** de arriba

---

## ⏰ LÍNEA DE TIEMPO ESTIMADA

| Acción | Tiempo |
|--------|--------|
| SSH manual al servidor | 30 segundos |
| Ejecutar comandos de reinicio | 2 minutos |
| Verificar servicios | 1 minuto |
| Ejecutar configure_final.py | 3 minutos |
| **TOTAL** | **~7 minutos** |

---

## 📞 SI ALGO FALLA

### Error: "Connection refused"
- SSH está completamente caído
- Solución: Usar consola web del hosting

### Error: "Permission denied"
- Password incorrecto
- Verificar: P31e27r12u1@HJG (copiar/pegar exacto)

### Error: Servicios no inician
- Ver logs: `tail -50 /tmp/bioql_*.log`
- Ver errors: `journalctl -xe | tail -50`

---

## ✅ CONFIRMACIÓN DE ÉXITO

Sabrás que todo funciona cuando:

```bash
# Desde tu computadora
curl -s https://api.bioql.bio/health
```

Devuelva algo como:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "..."
}
```

---

## 📚 DOCUMENTOS DE REFERENCIA

1. **`RESUMEN_FINAL_BIOQL.md`** - Resumen completo de todo lo logrado
2. **`DESATURAR_SSH.md`** - Todas las opciones para desaturar SSH
3. **`CRITICAL_SERVER_STATUS.md`** - Status crítico y recovery
4. **`SOLUCION_COMPLETA_BIOQL.md`** - Documentación técnica completa
5. **`configure_final.py`** - Script para configurar Workflows

---

## 🎯 SIGUIENTE PASO

**ABRE UNA TERMINAL NUEVA AHORA** y ejecuta:

```bash
ssh root@167.71.86.90
```

Luego sigue los comandos de "COMANDOS RESUMIDOS" arriba.

---

**Tiempo estimado hasta sistema 100% funcional: 7 minutos** ⏱️
