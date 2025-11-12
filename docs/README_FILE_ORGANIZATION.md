# 📁 Organización de Archivos - BioQL Project

**Fecha de organización**: 2025-10-29
**Sesión**: Post-deployment y configuración de servidores

---

## 📂 Estructura de Directorios

```
Spectrix_BioQL/
├── docs/
│   ├── deployment/          # Documentación de despliegue y configuración
│   ├── testing/            # Documentación de testing
│   └── troubleshooting/    # Guías de solución de problemas
├── scripts/
│   ├── deployment/         # Scripts de despliegue automatizado
│   ├── testing/           # Scripts de testing y validación
│   └── server_management/ # Scripts de gestión de servidores
├── test_results/          # Resultados de tests ejecutados
├── Spectrix_framework/    # Framework BioQL core
├── Server_bioql/          # Código del servidor de producción
└── ...

```

---

## 📚 Documentación (docs/deployment/)

### Documentos principales

1. **ACCION_INMEDIATA.md** ⭐
   - Guía de acción inmediata para recovery del servidor
   - Comandos copy-paste listos
   - Uso: Cuando necesites reiniciar servicios rápidamente

2. **RESUMEN_FINAL_BIOQL.md**
   - Resumen completo de todos los logros del proyecto
   - Status de servicios
   - Credenciales y endpoints
   - Tests ejecutados exitosamente

3. **CRITICAL_SERVER_STATUS.md**
   - Reporte de status crítico del servidor
   - Pasos de recovery manual
   - Configuraciones de Nginx completas

4. **DESATURAR_SSH.md**
   - Cómo resolver problemas de SSH saturado
   - 4 métodos diferentes de recovery
   - Prevención futura

5. **SOLUCION_COMPLETA_BIOQL.md**
   - Documentación técnica completa
   - Arquitectura del sistema
   - Configuración paso a paso

6. **RESUMEN_FINAL_COMPLETO.md**
   - Resumen ejecutivo del proyecto
   - KPIs y métricas
   - Lecciones aprendidas

---

## 🚀 Scripts de Deployment (scripts/deployment/)

### Scripts principales

1. **configure_final.py**
   - Script automatizado para configurar Workflows + Lab Notebook
   - Agrega configuración de Nginx
   - Verifica todos los servicios
   - Uso: `python3 configure_final.py`

2. **configure_workflows_nginx.sh**
   - Script bash para configurar proxy de Workflows
   - Backup automático de Nginx config
   - Test y reload automático

3. **add_workflow_health.sh**
   - Agrega endpoint /workflow/health a Nginx
   - Verificación automática

4. **deploy_updated_server.py**
   - Despliega código actualizado al servidor
   - Usa SSH + SCP
   - Reinicia servicios

5. **update_bioql_server.py**
   - Actualiza servidor BioQL Core
   - Maneja virtual environment
   - Backup automático

6. **download_server.py**
   - Descarga archivos del servidor para inspección
   - Útil para debugging

7. **fix_all_services_final.py**
   - Script de recovery completo
   - Reinicia todos los servicios
   - Configuración de Nginx

8. **update_nginx_quantum.py**
   - Actualiza configuración de Nginx para endpoints quantum
   - Agrega rate limiting
   - Configuración de CORS

---

## 🧪 Scripts de Testing (scripts/testing/)

### Tests principales

1. **test_bioql_docking_torino.py** ⭐
   - Test completo de molecular docking en IBM Torino
   - Incluye QEC + Quillow
   - Ejecutado exitosamente: $9,000 job
   - Resultado: -6.39 kcal/mol binding affinity

2. **test_docking_qec_FIXED.py**
   - Test de docking con parámetros QEC corregidos
   - Verifica que usa `error_correction`, `correction_level`, `num_logical_qubits`
   - NO usa `qec_config` (error antiguo)

3. **test_generator.py**
   - Genera código de test automáticamente
   - Útil para crear nuevos tests

4. **test_modal_api.py**
   - Test de Modal endpoint (antes de migrar a api.bioql.bio)
   - Histórico

5. **test_quantum_endpoint.py**
   - Test del endpoint /api/quantum/execute
   - Verifica remote execution

6. **test_stripe_reporting.py**
   - Verifica reporting a Stripe
   - Billing y metering

7. **test_vscode_simulation.py**
   - Simula generación de código desde VS Code extension
   - Verifica parámetros QEC correctos

8. **test_workflow_notebook_endpoints.py**
   - Test de endpoints de Workflows y Lab Notebook
   - Verifica conectividad

---

## 🛠️ Scripts de Server Management (scripts/server_management/)

### Verificación y diagnóstico

1. **check_all_services.py**
   - Verifica status de todos los servicios
   - BioQL Core, Workflows, Quantum Graphs, Quantum Docking, Lab Notebook
   - Test de endpoints públicos

2. **check_and_restart_servers.py**
   - Verifica servicios y reinicia si están caídos
   - Limpia procesos zombie
   - Recovery automático

3. **check_https_config.py**
   - Verifica configuración HTTPS/SSL
   - Let's Encrypt certificates
   - Nginx SSL settings

4. **check_nginx_config.py**
   - Verifica sintaxis de Nginx
   - Lee configuración actual
   - Debugging de proxies

5. **check_stripe_logs.py**
   - Lee logs de Stripe integration
   - Verifica billing events
   - Debugging de facturación

6. **check_stripe_startup.py**
   - Verifica que Stripe se inicie correctamente
   - Meter y pricing configuration
   - Webhooks

### Fixes y repairs

7. **fix_workflows_and_notebook.py**
   - Arregla configuración de Workflows y Lab Notebook
   - Agrega proxies faltantes a Nginx

8. **fix_bioql_nginx.py**
   - Arregla configuración general de Nginx para BioQL
   - Rate limiting
   - CORS headers

9. **get_bioql_api_config.py**
   - Obtiene configuración actual de la API
   - Útil para debugging

### Stripe management

10. **upgrade_stripe.py**
    - Actualiza Stripe de v7.0.0 a v13.0.1
    - Ejecutado exitosamente

11. **verify_stripe_config.py**
    - Verifica configuración de Stripe
    - Meter y pricing IDs
    - Customer IDs

### Utilidades

12. **ssh_test.sh**
    - Script para probar conectividad SSH
    - Obtiene banner de SSH
    - Debugging de conexión

---

## 📊 Test Results (test_results/)

### Resultados guardados

1. **__BIOQL_REDACTED__.json**
   - Resultado del test exitoso en IBM Torino
   - 2000 shots
   - $9,000 USD
   - Binding affinity: -6.39 kcal/mol
   - 62 quantum states
   - Datos completos del experimento

---

## 🔧 Servidor (Server_bioql/)

### Archivos principales

1. **auth_server/server_bioql_auth_server_stripe.py**
   - Servidor de autenticación y billing
   - Stripe v13.0.1
   - Endpoint: /api/quantum/execute
   - Puerto: 5001

---

## 🎯 Uso Común

### Para deployment:
```bash
# Configurar Workflows
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/scripts/deployment
python3 configure_final.py

# Actualizar servidor
python3 deploy_updated_server.py
```

### Para testing:
```bash
# Test de docking en IBM Torino
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/scripts/testing
python3 test_bioql_docking_torino.py

# Test de todos los endpoints
python3 test_workflow_notebook_endpoints.py
```

### Para verificación:
```bash
# Verificar todos los servicios
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/scripts/server_management
python3 check_all_services.py

# Verificar Stripe
python3 verify_stripe_config.py
```

### Para recovery:
```bash
# Reiniciar servicios
python3 check_and_restart_servers.py

# Arreglar Workflows
python3 fix_workflows_and_notebook.py
```

---

## 📝 Notas

- **Archivos organizados**: 2025-10-29 02:40 UTC
- **Origen**: Desktop (scripts de sesión de deployment)
- **Propósito**: Mantener proyecto organizado y facilitar mantenimiento futuro
- **Imagen**: `Captura de pantalla 2025-10-28 a la(s) 12.36.42.heic` quedó en Desktop (no se movió)

---

## 🚀 Próximos Pasos

1. ✅ Archivos organizados
2. ⏳ Terminar configuración de Workflows en Nginx
3. ⏳ Verificar Lab Notebook (puerto 5003)
4. ⏳ Crear git commit con todos los cambios
5. ⏳ Backup del servidor completo

---

## 📞 Contacto

- **Servidor**: api.bioql.bio (167.71.86.90)
- **Documentación**: `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/`
- **Scripts**: `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/scripts/`
