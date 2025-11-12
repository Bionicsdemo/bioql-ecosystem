# 🧬 BioQL Admin CLI - Configuración Completa

## ✅ **Sistema Listo para Usar**

Tu CLI administrativo de BioQL está completamente configurado y funcionando. Aquí tienes todo lo que necesitas saber:

## 🚀 **Ejecución Rápida**

### Opción 1: Launcher Simple (Recomendado)
```bash
./bioql-admin-simple
```

### Opción 2: Ejecución Directa
```bash
python3 bioql_admin_simple.py --db bioql_billing.db
```

## 📋 **Archivos Creados**

### CLI Principal
- `bioql_admin_simple.py` - CLI principal (sin dependencias externas)
- `bioql-admin-simple` - Script launcher

### Scripts de Configuración
- `setup_admin_cli.sh` - Script de configuración automática
- `test_simple_cli.py` - Suite de pruebas

### Documentación
- `admin_guide.md` - Guía completa de comandos
- `ADMIN_SETUP.md` - Este archivo

## 🎯 **Comandos Principales**

Una vez dentro del CLI (prompt: `bioql-admin>`):

### 👥 **Gestión de Usuarios**
```bash
# Listar usuarios
list_users
list_users --limit 10
list_users --plan basic

# Crear usuario
create_user cliente@empresa.com "Dr. Juan Pérez" "BioTech Solutions"
create_user lab@university.edu "Research Team" "Universidad" --plan pro

# Ver detalles
user_details cliente@empresa.com

# Desactivar usuario
deactivate_user cliente@empresa.com
```

### 🔑 **API Keys**
```bash
# Crear API key
create_api_key cliente@empresa.com "Production Key"

# Listar API keys
list_api_keys cliente@empresa.com
```

### 💰 **Facturación**
```bash
# Listar facturas
list_bills
list_bills --user cliente@empresa.com
list_bills --status pending
```

### 📊 **Estadísticas**
```bash
# Estadísticas de uso
usage_stats
usage_stats --user cliente@empresa.com
usage_stats --days 30

# Estado del sistema
status
```

### 🛠️ **Utilidades**
```bash
# Consultas SQL (solo SELECT)
sql SELECT COUNT(*) FROM users
sql SELECT email, current_plan FROM users WHERE is_active = 1

# Backup
backup
backup mi_backup.db

# Ayuda
help
help create_user
```

## 📝 **Ejemplo de Sesión Completa**

```bash
# 1. Iniciar CLI
./bioql-admin-simple

# 2. Ver estado del sistema
bioql-admin> status

# 3. Crear un cliente nuevo
bioql-admin> create_user cliente@newcompany.com "Dr. Smith" "NewCompany Labs" --plan basic
# ✅ USER CREATED SUCCESSFULLY
# API Key: bioql_ABC123XYZ... (guardar este key!)

# 4. Ver detalles del cliente
bioql-admin> user_details cliente@newcompany.com

# 5. Ver estadísticas de uso
bioql-admin> usage_stats --days 30

# 6. Listar facturas pendientes
bioql-admin> list_bills --status pending

# 7. Crear backup
bioql-admin> backup cliente_backup_20240928.db

# 8. Salir
bioql-admin> exit
```

## 🔧 **Características Técnicas**

### ✅ **Lo que FUNCIONA:**
- ✅ Sin dependencias externas (solo Python estándar)
- ✅ Interfaz limpia con tablas formateadas
- ✅ Validación completa de entrada
- ✅ Manejo seguro de errores
- ✅ Consultas SQL de solo lectura
- ✅ Backups automáticos
- ✅ Generación automática de API keys
- ✅ Sistema de ayuda integrado

### 🔒 **Seguridad Implementada:**
- 🔒 Solo consultas SELECT en modo SQL
- 🔒 Validación de todos los parámetros
- 🔒 API keys hasheadas en base de datos
- 🔒 Confirmación para acciones destructivas
- 🔒 No exposición de claves completas

## 🎯 **Flujos de Trabajo Típicos**

### 1. **Onboarding Cliente Nuevo**
```bash
bioql-admin> create_user cliente@empresa.com "Nombre" "Empresa" --plan basic
bioql-admin> user_details cliente@empresa.com
# Enviar API key al cliente
```

### 2. **Monitoreo de Cliente**
```bash
bioql-admin> user_details cliente@empresa.com
bioql-admin> usage_stats --user cliente@empresa.com --days 30
bioql-admin> list_bills --user cliente@empresa.com
```

### 3. **Análisis del Sistema**
```bash
bioql-admin> status
bioql-admin> usage_stats --days 7
bioql-admin> list_bills --status pending
bioql-admin> sql SELECT current_plan, COUNT(*) FROM users GROUP BY current_plan
```

### 4. **Troubleshooting**
```bash
bioql-admin> user_details cliente@problema.com
bioql-admin> list_api_keys cliente@problema.com
bioql-admin> usage_stats --user cliente@problema.com --days 7
```

## 🚨 **Solución de Problemas**

### Error: "Database not found"
```bash
# Crear la base de datos
python3 "BP&PL/setup_billing_database.py" --database sqlite --reset
```

### Error: "ModuleNotFoundError"
```bash
# Usar la versión simple (sin dependencias)
python3 bioql_admin_simple.py --db bioql_billing.db
```

### CLI no responde
```bash
# Usar Ctrl+C para salir y reiniciar
# Verificar que la base de datos no esté corrupta
python3 bioql_admin_simple.py --db bioql_billing.db
bioql-admin> sql SELECT COUNT(*) FROM users
```

## 📊 **Base de Datos**

Tu base de datos `bioql_billing.db` contiene:
- ✅ 4 usuarios de ejemplo
- ✅ 0 suscripciones activas
- ✅ 12 logs de uso
- ✅ 0 facturas pendientes

### Usuarios Preconfigurados:
1. `researcher@university.edu` (Plan: free)
2. `lab@biotech.com` (Plan: basic)
3. `team@pharma.com` (Plan: pro)
4. `enterprise@megacorp.com` (Plan: enterprise)

## 🎉 **¡Todo Listo!**

Tu sistema administrativo de BioQL está completamente operativo. Puedes:

1. **Gestionar usuarios** - Crear, ver, desactivar
2. **Controlar API keys** - Generar y monitorear
3. **Monitorear facturación** - Ver facturas y uso
4. **Generar reportes** - Estadísticas y análisis
5. **Mantener el sistema** - Backups y consultas

**🚀 Comando para empezar:**
```bash
./bioql-admin-simple
```

**📖 Documentación completa:** Ver `admin_guide.md`
