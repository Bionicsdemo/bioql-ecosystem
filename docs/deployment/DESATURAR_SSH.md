# 🔓 Cómo Desaturar SSH en api.bioql.bio

## Problema Actual

SSH está bloqueado por **demasiadas conexiones simultáneas** desde tu IP.

**Error**:
```
SSHException: Error reading SSH protocol banner
socket.timeout
```

**Causa**: El servidor SSH tiene un límite de conexiones concurrentes:
- `MaxStartups 10:30:60` (default)
- Tu cliente hizo ~100 intentos en 1 hora
- SSH rechaza nuevas conexiones hasta que se limpien las antiguas

---

## ⚡ SOLUCIÓN MÁS RÁPIDA (5 minutos)

### Opción 1: Reiniciar servicio SSH desde el panel web

Si tienes acceso al panel de control del hosting (DigitalOcean, AWS, etc.):

1. **Ir al panel de control**
   - DigitalOcean: https://cloud.digitalocean.com/
   - AWS: https://console.aws.amazon.com/
   - Otro hosting: Login a tu panel

2. **Buscar el droplet/servidor**
   - Nombre: api.bioql.bio
   - IP: 167.71.86.90

3. **Abrir consola web (VNC/Console)**
   - DigitalOcean: Click en "Access" → "Launch Droplet Console"
   - AWS: "Connect" → "EC2 Instance Connect"
   - Esto te da acceso directo sin SSH

4. **Login como root**
   ```bash
   login: root
   password: P31e27r12u1@HJG
   ```

5. **Reiniciar SSH**
   ```bash
   systemctl restart sshd
   ```

6. **Verificar**
   ```bash
   systemctl status sshd
   ```

✅ **Ahora podrás conectarte via SSH desde tu computadora**

---

## ⏰ SOLUCIÓN AUTOMÁTICA (2-4 horas)

### Opción 2: Esperar que se limpie solo

El servidor SSH limpia conexiones viejas automáticamente:

**Timeouts configurados**:
- `ClientAliveInterval 300` (5 minutos)
- `ClientAliveCountMax 2` (10 minutos total)
- Las conexiones viejas mueren después de 10-20 minutos

**Cuánto esperar**:
- **30 minutos**: La mayoría se limpiarán
- **2 horas**: Limpieza completa garantizada
- **4 horas**: Segurísimo que funcionará

**Mientras esperas**:
```bash
# Probar cada 30 minutos
ssh root@167.71.86.90
```

---

## 🔥 SOLUCIÓN EXTREMA (30 segundos)

### Opción 3: Reiniciar el servidor completo

⚠️ **ADVERTENCIA**: Esto cortará todos los servicios por 1-2 minutos.

**Desde el panel de control del hosting**:
1. Buscar el servidor (167.71.86.90)
2. Click en "Power" → "Reboot"
3. Esperar 2 minutos
4. Intentar SSH

**Efecto**:
- ✅ SSH se limpiará completamente
- ✅ Todos los servicios reiniciarán
- ⚠️  Algunos procesos Python pueden no reiniciar automáticamente

**Después del reboot**, necesitarás reiniciar servicios manualmente:
```bash
ssh root@167.71.86.90

# Reiniciar BioQL Core
cd /opt/bioql/auth_server
/opt/bioql/venv/bin/python bioql_auth_server_stripe.py > /tmp/bioql_auth.log 2>&1 &

# Verificar
ps aux | grep bioql_auth_server_stripe | grep -v grep
curl -s http://127.0.0.1:5001/health
```

---

## 🌐 SOLUCIÓN DESDE OTRA COMPUTADORA (5 minutos)

### Opción 4: SSH desde otra IP

El bloqueo es **por IP de origen**, no global.

**Opciones**:
1. Usar otra computadora en tu red
2. Usar tu celular con hotspot 4G/5G
3. Usar una VPN
4. Usar un servidor intermedio

**Ejemplo con otra computadora**:
```bash
# Desde otra laptop/desktop
ssh root@167.71.86.90
# Password: P31e27r12u1@HJG

# Limpiar conexiones viejas
who
# Esto muestra todas las sesiones SSH activas

# Ver procesos SSH
ps aux | grep sshd | wc -l
# Si hay muchos (>50), hacer:
killall sshd
systemctl restart sshd

# Ahora tu computadora principal podrá conectarse
```

**Ejemplo con VPN**:
```bash
# 1. Activar VPN (cambia tu IP)
# 2. Intentar SSH
ssh root@167.71.86.90
```

---

## 🔍 VERIFICAR SI SSH ESTÁ FUNCIONANDO

Desde tu computadora actual:

```bash
# Test 1: ¿SSH responde?
nc -zv 167.71.86.90 22
# Debe decir: "Connection to 167.71.86.90 port 22 [tcp/ssh] succeeded!"

# Test 2: ¿Puedes ver el banner?
telnet 167.71.86.90 22
# Debe mostrar: "SSH-2.0-OpenSSH_..."
# Ctrl+C para salir

# Test 3: Ping sigue funcionando
ping -c 3 167.71.86.90
# Debe responder (ya verificamos que funciona)
```

Si **Test 1 y 2 fallan** → SSH service está caído (necesitas consola web)
Si **Test 1 y 2 pasan** → Tu IP está bloqueada (usa VPN o espera)

---

## 📋 SOLUCIÓN RECOMENDADA (paso a paso)

### Plan A: Usar consola web del hosting (RECOMENDADO)

```
1. Ir a panel de control del hosting
   ↓
2. Abrir consola web/VNC del servidor
   ↓
3. Login: root / P31e27r12u1@HJG
   ↓
4. Ejecutar: systemctl restart sshd
   ↓
5. Desde tu computadora: ssh root@167.71.86.90
   ↓
6. ✅ Ejecutar: python3 /Users/heinzjungbluth/Desktop/configure_final.py
```

### Plan B: Esperar 30 minutos

```
1. Esperar 30 minutos (tomar café ☕)
   ↓
2. Intentar: ssh root@167.71.86.90
   ↓
3. Si falla, esperar otros 30 minutos
   ↓
4. Intentar nuevamente
   ↓
5. ✅ Cuando funcione: python3 /Users/heinzjungbluth/Desktop/configure_final.py
```

### Plan C: Usar VPN o celular

```
1. Activar VPN o hotspot de celular
   ↓
2. Intentar: ssh root@167.71.86.90
   ↓
3. Si falla, reiniciar sshd desde consola web
   ↓
4. ✅ Ejecutar: python3 /Users/heinzjungbluth/Desktop/configure_final.py
```

---

## 🛠️ PREVENIR ESTO EN EL FUTURO

### Configurar SSH para más conexiones

En el servidor, editar `/etc/ssh/sshd_config`:

```bash
nano /etc/ssh/sshd_config

# Agregar o modificar:
MaxStartups 50:30:100    # Permite hasta 50 conexiones concurrentes
ClientAliveInterval 60    # Ping cada 60 segundos
ClientAliveCountMax 3     # 3 intentos (180 seg total)
MaxSessions 50            # 50 sesiones por conexión

# Guardar y reiniciar
systemctl restart sshd
```

### Usar SSH connection multiplexing

En tu computadora, editar `~/.ssh/config`:

```bash
nano ~/.ssh/config

# Agregar:
Host api.bioql.bio
    HostName 167.71.86.90
    User root
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600

# Crear directorio
mkdir -p ~/.ssh/sockets
```

Esto **reutiliza una sola conexión SSH** para múltiples comandos, evitando saturación.

---

## 📊 DIAGNÓSTICO ACTUAL

```
✅ Servidor: ONLINE (ping responde)
✅ IP: 167.71.86.90
✅ DNS: api.bioql.bio → 167.71.86.90
❌ SSH: Saturado (demasiadas conexiones desde tu IP)
❓ Servicios web: Status desconocido (no podemos verificar sin SSH)
```

**Causa raíz**:
- Hicimos ~100 intentos de SSH en la última hora
- Cada intento con paramiko abre una conexión nueva
- SSH service colapsó por demasiadas conexiones concurrentes

**Solución inmediata**:
- Reiniciar SSH via consola web (5 min)
- O esperar 30-120 minutos para limpieza automática

---

## 🎯 ACCIÓN INMEDIATA RECOMENDADA

**HAZLO AHORA** (5 minutos):

1. **Ir a tu panel de control del hosting**
   - DigitalOcean, AWS, Linode, Vultr, etc.

2. **Abrir consola web del servidor**
   - Buscar "Console", "VNC", "Terminal"

3. **Ejecutar estos comandos**:
   ```bash
   # Login
   root / P31e27r12u1@HJG

   # Ver cuántas conexiones SSH hay
   ps aux | grep sshd | wc -l

   # Reiniciar SSH
   systemctl restart sshd

   # Verificar que arrancó
   systemctl status sshd

   # Limpiar conexiones muertas
   who
   ```

4. **Desde tu computadora**:
   ```bash
   ssh root@167.71.86.90
   # Debería funcionar ahora
   ```

5. **Ejecutar configuración final**:
   ```bash
   python3 /Users/heinzjungbluth/Desktop/configure_final.py
   ```

---

## ✅ RESUMEN

| Método | Tiempo | Dificultad | Efectividad |
|--------|--------|------------|-------------|
| **Consola web + restart sshd** | 5 min | Fácil | 100% ✅ |
| **Esperar limpieza automática** | 30-120 min | Muy fácil | 90% ✅ |
| **Usar VPN/otra IP** | 10 min | Media | 80% ✅ |
| **Reboot completo del servidor** | 5 min | Fácil | 100% ⚠️ |

**Recomendación**: Usar consola web para reiniciar sshd (Método 1) ⭐
