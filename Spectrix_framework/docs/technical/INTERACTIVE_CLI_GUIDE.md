# 🧬 BioQL Interactive Admin CLI - Guía Completa

## ✨ **Nueva Versión Interactiva**

¡He creado una versión completamente interactiva del CLI que te guía paso a paso en todas las tareas administrativas!

## 🚀 **Cómo Ejecutar**

```bash
# Versión interactiva con menús guiados
./bioql-admin-interactive

# O directamente:
python3 bioql_admin_interactive.py --db bioql_billing.db
```

## 🎯 **Características Principales**

### 🧭 **Navegación Intuitiva**
- **Menús jerárquicos** - Sistema de menús organizados por categorías
- **Asistentes guiados** - Wizards paso a paso para tareas complejas
- **Acciones rápidas** - Shortcuts para tareas comunes
- **Ayuda contextual** - Información detallada en cada paso

### 📋 **Sistema de Menús Principales**

#### 1. 👥 **User Management**
- Listar usuarios con filtros
- Crear usuarios con wizard guiado
- Buscar detalles de usuarios
- Desactivar usuarios
- Búsqueda rápida

#### 2. 🔑 **API Key Management**
- Listar API keys por usuario
- Crear API keys con asistente
- Ver detalles de API keys

#### 3. 💰 **Billing & Invoices**
- Listar todas las facturas
- Facturas por usuario
- Facturas pendientes
- Resumen de facturación

#### 4. 📊 **Reports & Analytics**
- Estadísticas de uso
- Analytics de usuarios
- Reportes de ingresos
- Estado del sistema

#### 5. 🔧 **System Tools**
- Crear backups
- Ejecutar consultas SQL
- Estado del sistema
- Herramientas de mantenimiento

#### 6. 🎯 **Quick Actions**
- Crear usuario + API key express
- Buscar usuario por email
- Verificar facturación
- Estadísticas del día

#### 7. 📚 **Help & Documentation**
- Ayuda completa de comandos
- Documentación integrada

## 🧙‍♂️ **Asistentes Guiados (Wizards)**

### ➕ **Create User Wizard**
Te guía paso a paso para crear usuarios:

```
📧 STEP 1: Email Address
👤 STEP 2: User Name
🏢 STEP 3: Organization
📋 STEP 4: Subscription Plan
✅ STEP 5: Confirmation
```

**Beneficios:**
- ✅ Validación automática de email
- ✅ Verificación de duplicados
- ✅ Generación automática de API key
- ✅ Confirmación antes de crear

### 🔑 **API Key Creation Wizard**
Asistente para crear API keys adicionales:
- Selecciona usuario existente
- Asigna nombre descriptivo
- Genera key segura automáticamente

## 🎯 **Acciones Rápidas**

### ⚡ **Express User Creation**
Creación ultra-rápida para usuarios simples:
```bash
Email: cliente@empresa.com
Name: Dr. Juan Pérez
Organization: BioTech Solutions
✅ Created with free plan + API key
```

### 🔍 **Quick User Search**
Búsqueda instantánea por email con todos los detalles.

### 📊 **Today's Stats**
Resumen rápido de actividad del día.

## 🎨 **Interfaz Mejorada**

### 📊 **Tablas Elegantes**
```
┌─────────┬─────────────────────┬──────────────┬─────────────┐
│ ID      │ Email               │ Name         │ Plan        │
├─────────┼─────────────────────┼──────────────┼─────────────┤
│ abc123  │ cliente@empresa.com │ Dr. Pérez    │ basic       │
│ def456  │ lab@university.edu  │ Research Lab │ pro         │
└─────────┴─────────────────────┴──────────────┴─────────────┘
```

### 🎨 **Colores y Símbolos**
- ✅ Verde para éxito
- ❌ Rojo para errores
- ⚠️ Amarillo para advertencias
- 🟢 Activo / 🔴 Inactivo
- 📧📊🔑💰 Iconos descriptivos

## 🚀 **Flujo de Trabajo Completo**

### 1. **Iniciar Sistema**
```bash
./bioql-admin-interactive
```

### 2. **Ver Menú Principal**
```
🧬 bioql> menu

🧬 BIOQL MAIN MENU
==================
1. 👥 User Management
2. 🔑 API Key Management
3. 💰 Billing & Invoices
4. 📊 Reports & Analytics
5. 🔧 System Tools
6. 🎯 Quick Actions
7. 📚 Help & Documentation
0. 🚪 Exit

Select an option (0-7):
```

### 3. **Crear Usuario (Ejemplo)**
```
Seleccionar: 1 (User Management)
Seleccionar: 2 (Create new user - Guided)

📧 STEP 1: Email Address
Enter user email: cliente@nuevaempresa.com

👤 STEP 2: User Name
Enter full name: Dr. María García

🏢 STEP 3: Organization
Enter organization name: Nueva Empresa Biotech

📋 STEP 4: Subscription Plan
Available plans:
  • free - Free tier
  • basic - Basic plan ($99/month)
  • pro - Professional plan ($499/month)
  • enterprise - Enterprise plan ($2999/month)

Select plan: basic

✅ STEP 5: Confirmation
Email: cliente@nuevaempresa.com
Name: Dr. María García
Organization: Nueva Empresa Biotech
Plan: basic

Create this user? (y/N): y

🎉 USER CREATED SUCCESSFULLY!
📧 Email: cliente@nuevaempresa.com
🔑 API Key: bioql_ABC123XYZ...
⚠️  SAVE THE API KEY!
```

## 💡 **Comandos Rápidos**

Además de los menús, puedes usar comandos directos:

```bash
🧬 bioql> menu          # Menú principal
🧬 bioql> wizard        # Asistentes de creación
🧬 bioql> quick         # Acciones rápidas
🧬 bioql> status        # Estado del sistema
🧬 bioql> help          # Ayuda completa
🧬 bioql> list_users    # Listar usuarios
🧬 bioql> user_details cliente@email.com  # Detalles de usuario
🧬 bioql> backup        # Crear backup
🧬 bioql> exit          # Salir
```

## 🔍 **Búsqueda y Detalles de Usuario**

### Vista Completa de Usuario:
```
👤 USER DETAILS
===============
🆔 User ID: abc123-def456-ghi789
📧 Email: cliente@empresa.com
👤 Name: Dr. Juan Pérez
🏢 Organization: BioTech Solutions
📋 Plan: BASIC
🔄 Status: 🟢 Active
📅 Created: 2024-09-28

📊 USAGE SUMMARY
----------------
🔑 API Keys: 2 active
⚡ Total Jobs: 147 (142 successful)
🎯 Total Shots: 234,567
💰 Total Spent: $1,247.89
🧾 Bills: 3

🔑 API KEYS:
┌──────────────────┬─────────────────┬────────────┬───────┐
│ Key Prefix       │ Name            │ Created    │ Usage │
├──────────────────┼─────────────────┼────────────┼───────┤
│ bioql_abc123...  │ Default API Key │ 2024-09-15 │ 142   │
│ bioql_def456...  │ Production Key  │ 2024-09-20 │ 5     │
└──────────────────┴─────────────────┴────────────┴───────┘

🎯 ACTIONS:
  1. Create new API key
  2. View usage details
  3. View billing details
  0. Return to menu
```

## 🛡️ **Validaciones y Seguridad**

### ✅ **Validaciones Automáticas**
- **Email format** - Verifica formato válido
- **Duplicados** - Evita usuarios duplicados
- **Campos requeridos** - Valida datos obligatorios
- **Planes válidos** - Solo permite planes existentes

### 🔒 **Seguridad**
- **API keys hasheadas** - Solo muestra prefijos
- **Confirmaciones** - Para acciones destructivas
- **Solo consultas SELECT** - En modo SQL
- **Backups seguros** - Preserva datos

## 🎁 **Características Especiales**

### 🔄 **Navegación Intuitiva**
- **Menús numerados** - Selección fácil con números
- **Breadcrumbs** - Sabes dónde estás siempre
- **Vuelta atrás** - Opción 0 para regresar
- **Cancelar** - Escape en cualquier momento

### 🎯 **User Experience**
- **Mensajes claros** - Explicaciones en español
- **Pasos numerados** - Progreso visible
- **Confirmaciones** - Evita errores accidentales
- **Tips contextuales** - Ayuda cuando la necesitas

### ⚡ **Performance**
- **Sin dependencias externas** - Solo Python estándar
- **Conexión eficiente** - Reutiliza conexiones DB
- **Carga rápida** - Inicio instantáneo

## 🎉 **¡Listo para Usar!**

El nuevo CLI interactivo está **completamente funcional** y te guiará en todas las tareas administrativas de BioQL.

### **Ejecutar ahora:**
```bash
./bioql-admin-interactive
```

### **Primeros pasos recomendados:**
1. Ejecutar `menu` para explorar opciones
2. Crear un usuario de prueba con el wizard
3. Explorar los detalles del usuario creado
4. Crear un backup de seguridad

**¡Disfruta de la experiencia administrativa mejorada de BioQL!** 🚀
