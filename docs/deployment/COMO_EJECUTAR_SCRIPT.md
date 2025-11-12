# 🚀 CÓMO EJECUTAR EL SCRIPT DE CONFIGURACIÓN FINAL

## 📋 Archivo creado

**Ubicación**: `/Users/heinzjungbluth/Desktop/configuracion_final_completa.sh`

**Tamaño**: 11 KB

**Permisos**: Ejecutable ✅

---

## 🎯 QUÉ HACE EL SCRIPT

El script automatiza 3 tareas:

1. ✅ **Configura Lab Notebook en Nginx** (5 min)
   - Agrega configuración al archivo de Nginx
   - Hace backup automático
   - Test de sintaxis con timeout
   - Reload de Nginx
   - Verifica que funciona

2. ✅ **Instala Prometheus + Grafana** (15 min)
   - Instala Prometheus y Node Exporter
   - Configura monitoreo de 6 servicios BioQL
   - Instala Grafana
   - Configura repositorio y dependencias

3. ✅ **Verificación completa** (1 min)
   - Test de todos los servicios
   - Test de todos los endpoints
   - Muestra información de acceso

**Tiempo total**: ~20 minutos

---

## 🔧 OPCIÓN 1: Copiar al servidor via SCP

### Paso 1: Copiar el script

```bash
# Desde tu computadora
scp /Users/heinzjungbluth/Desktop/configuracion_final_completa.sh root@167.71.86.90:/tmp/
```

### Paso 2: Conectar al servidor

```bash
ssh root@167.71.86.90
# Password: P31e27r12u1@HJG
```

### Paso 3: Ejecutar el script

```bash
cd /tmp
bash configuracion_final_completa.sh
```

**El script pedirá confirmación antes de empezar.**

---

## 🔧 OPCIÓN 2: Copiar manualmente (Copy-Paste)

### Paso 1: Conectar al servidor

```bash
ssh root@167.71.86.90
# Password: P31e27r12u1@HJG
```

### Paso 2: Crear el script en el servidor

```bash
cat > /tmp/configuracion_final_completa.sh << 'ENDOFSCRIPT'
```

### Paso 3: Copiar TODO el contenido del script

Abre el archivo:
```bash
open /Users/heinzjungbluth/Desktop/configuracion_final_completa.sh
```

Copia TODO el contenido (Cmd+A, Cmd+C)

Pega en la terminal SSH

### Paso 4: Cerrar el heredoc

Presiona Enter y escribe:
```bash
ENDOFSCRIPT
```

### Paso 5: Hacer ejecutable y ejecutar

```bash
chmod +x /tmp/configuracion_final_completa.sh
bash /tmp/configuracion_final_completa.sh
```

---

## 📊 QUÉ VERÁS DURANTE LA EJECUCIÓN

### Inicio
```
==========================================
🚀 CONFIGURACIÓN FINAL COMPLETA - BioQL
==========================================

Este script va a:
  1. Configurar Lab Notebook en Nginx
  2. Instalar Prometheus + Grafana
  3. Configurar monitoreo de servicios BioQL

Tiempo estimado: 20 minutos

¿Continuar? (y/n)
```

**Presiona `y` y Enter para continuar**

### Durante la ejecución verás:

```
==========================================
📓 PASO 1/3: CONFIGURAR LAB NOTEBOOK
==========================================

🔍 Verificando Lab Notebook en puerto 5003...
✅ Lab Notebook está corriendo

📦 Creando backup de Nginx...
✅ Backup creado

📝 Creando configuración de Lab Notebook...
   Insertando en línea 38...

🔍 Verificando inserción...
✅ Configuración insertada correctamente

🧪 Testing sintaxis de Nginx (timeout 10s)...
✅ Sintaxis correcta
✅ Nginx recargado exitosamente

🧪 Testing endpoint...
{"service":"BioQL Lab Notebook API","status":"healthy",...}

✅ LAB NOTEBOOK CONFIGURADO EXITOSAMENTE
```

```
==========================================
📊 PASO 2/3: INSTALAR PROMETHEUS + GRAFANA
==========================================

📦 Actualizando sistema...
📥 Instalando Prometheus y Node Exporter...
✅ Prometheus y Node Exporter instalados

📝 Configurando Prometheus para monitorear BioQL...
🔄 Iniciando Prometheus...
✅ Prometheus iniciado y funcionando
✅ Node Exporter funcionando

📥 Instalando Grafana...
✅ Grafana instalado

🔄 Iniciando Grafana...
✅ Grafana iniciado y funcionando
```

```
==========================================
✅ PASO 3/3: VERIFICACIÓN FINAL
==========================================

🔍 Verificando servicios instalados...

  ✅ prometheus
  ✅ prometheus-node-exporter
  ✅ grafana-server
  ✅ nginx

🔍 Verificando endpoints BioQL...

  ✅ BioQL Core
  ✅ Workflows
  ✅ Lab Notebook
  ✅ Quantum Docking
  ✅ Quantum Graphs

==========================================
🎉 CONFIGURACIÓN COMPLETA
==========================================

📊 Resultados:
  - Servicios del sistema: 4/4 activos
  - Endpoints BioQL: 5/5 online
```

### Al final verás toda la información de acceso:

```
==========================================
📝 INFORMACIÓN DE ACCESO
==========================================

Lab Notebook:
  ✅ https://api.bioql.bio/lab-notebook/health
  ✅ https://api.bioql.bio/lab-notebook/

Prometheus:
  📊 http://localhost:9090
  🔐 Acceso: ssh -L 9090:localhost:9090 root@167.71.86.90

Grafana:
  📊 http://localhost:3000
  🔐 Acceso: ssh -L 3000:localhost:3000 root@167.71.86.90
  👤 Usuario: admin
  🔑 Password: admin (cambiar en primer login)

==========================================
📝 PRÓXIMOS PASOS
==========================================

1. Crear túnel SSH desde tu computadora:
   ssh -L 3000:localhost:3000 -L 9090:localhost:9090 root@167.71.86.90

2. Abrir Grafana en tu navegador:
   http://localhost:3000

3. Login con admin/admin y cambiar password

4. Agregar Prometheus como Data Source:
   Configuration → Data Sources → Add → Prometheus
   URL: http://localhost:9090

5. Importar Dashboard:
   + → Import → Dashboard ID: 1860

🎉 ¡Sistema BioQL al 100% configurado!
```

---

## ✅ RESULTADO FINAL

Después de ejecutar el script tendrás:

```
✅ 6/6 Servicios BioQL Online
   - BioQL Core
   - Quantum Execution
   - Workflows
   - Lab Notebook        ← NUEVO
   - Quantum Docking
   - Quantum Graphs

✅ Monitoreo Completo
   - Prometheus          ← NUEVO
   - Node Exporter       ← NUEVO
   - Grafana            ← NUEVO
```

**Sistema BioQL al 100%** 🎉

---

## 🆘 SI ALGO FALLA

### El script se detiene con error

```bash
# Ver últimos logs
tail -50 /tmp/configuracion_final_completa.log

# Restaurar backup de Nginx si es necesario
ls -lt /etc/nginx/sites-available/bioql.backup_final_*
cp /etc/nginx/sites-available/bioql.backup_final_XXXXXX /etc/nginx/sites-available/bioql
systemctl reload nginx
```

### Lab Notebook no responde

El script verificará esto al inicio. Si falla:

```bash
# Verificar que Lab Notebook esté corriendo
ps aux | grep notebook | grep 5003

# Ver puerto
netstat -tulpn | grep 5003

# Reiniciar si es necesario
# (buscar el comando de inicio en el servidor)
```

### Prometheus no instala

```bash
# Actualizar repos
apt-get update

# Intentar instalación manual
apt-get install prometheus prometheus-node-exporter

# Ver logs
journalctl -xeu prometheus
```

### Grafana no instala

```bash
# Intentar instalación manual
apt-get update
apt-get install grafana

# Ver logs
journalctl -xeu grafana-server
```

---

## 📝 ARCHIVOS CREADOS POR EL SCRIPT

```
/etc/nginx/sites-available/bioql.backup_final_YYYYMMDD_HHMMSS  # Backup de Nginx
/etc/prometheus/prometheus.yml                                  # Config de Prometheus
/tmp/lab_notebook_config.txt                                   # Config temporal
```

---

## 🔍 VERIFICAR DESPUÉS DE LA EJECUCIÓN

### En el servidor:

```bash
# Verificar todos los servicios
systemctl status prometheus
systemctl status prometheus-node-exporter
systemctl status grafana-server
systemctl status nginx

# Test endpoints
curl -s https://api.bioql.bio/lab-notebook/health
curl -s http://localhost:9090/metrics | head -5
curl -s http://localhost:9100/metrics | head -5
```

### Desde tu computadora:

```bash
# Crear túnel SSH
ssh -L 3000:localhost:3000 root@167.71.86.90

# Abrir Grafana
open http://localhost:3000
```

---

## ⏱️ TIEMPO ESTIMADO

- Copiar script al servidor: 30 segundos
- Ejecutar script: 20 minutos
- Configurar Grafana: 5 minutos
- **Total: 25-26 minutos**

---

## 🎯 RECOMENDACIÓN

**Usa la OPCIÓN 1 (SCP)** - Es más rápida y confiable:

```bash
# Un solo comando desde tu Mac
scp /Users/heinzjungbluth/Desktop/configuracion_final_completa.sh root@167.71.86.90:/tmp/ && ssh root@167.71.86.90 "bash /tmp/configuracion_final_completa.sh"
```

Este comando:
1. Copia el script al servidor
2. Se conecta via SSH
3. Ejecuta el script automáticamente

**Solo necesitas escribir:**
- Password SSH: `P31e27r12u1@HJG`
- Confirmación: `y` (cuando el script pregunte)

¡Y listo! El script hará todo el resto.

---

**¿Listo para ejecutar?** 🚀
