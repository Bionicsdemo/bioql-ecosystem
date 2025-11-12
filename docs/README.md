# BioQL Quantum Computing Platform

## 📚 Descripción

BioQL es una plataforma de computación cuántica diseñada específicamente para aplicaciones en bioquímica y descubrimiento de fármacos. Combina algoritmos cuánticos avanzados con corrección de errores cuánticos (QEC) usando el framework Quillow.

## 🚀 Componentes Principales

### 1. **Spectrix Framework** ([Spectrix_framework/](./Spectrix_framework/))
Framework core de BioQL con:
- Compilador cuántico con reconocimiento de patrones (1B+ patrones)
- Integración con IBM Quantum, Qiskit, y simuladores
- Sistema de autenticación y billing con Stripe
- Corrección de errores cuánticos (Surface Code)

### 2. **Server BioQL** ([Server_bioql/](./Server_bioql/))
Servidor de ejecución cuántica remota:
- API REST para ejecución de circuitos cuánticos
- Autenticación y billing
- Métricas y monitoreo

### 3. **QPHAROS** ([QPHAROS/](./QPHAROS/))
Sistema de docking molecular cuántico con:
- Integración con Quillow QEC
- Análisis de interacciones proteína-ligando
- Optimización de estructuras moleculares

## 📖 Documentación

### Deployment
- [DEPLOYMENT_INSTRUCTIONS.md](./documentation/DEPLOYMENT_INSTRUCTIONS.md) - Instrucciones completas de deployment
- [QPHAROS_DEPLOYMENT_SUCCESS.md](./documentation/QPHAROS_DEPLOYMENT_SUCCESS.md) - Deployment exitoso de QPHAROS
- [TROUBLESHOOTING_2025-11-03.md](./documentation/TROUBLESHOOTING_2025-11-03.md) - Resolución de problemas (Nov 2025)

### Scripts de Deployment
- [deploy_bioql_quantum_complete.sh](./deployment_scripts/deploy_bioql_quantum_complete.sh) - Deployment completo del servidor
- [configure_nginx_quantum.sh](./deployment_scripts/configure_nginx_quantum.sh) - Configuración de Nginx
- [fix_bioql_api_service.sh](./deployment_scripts/fix_bioql_api_service.sh) - Script de diagnóstico

### Resultados y Tests
- [TEST_RESULTS_FINAL.md](./documentation/TEST_RESULTS_FINAL.md) - Resultados de tests finales

## 🔧 Configuración Rápida

### Instalación Local (macOS)

```bash
# 1. Clonar repositorio
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework

# 2. Instalar con conda (recomendado)
conda activate base
pip install -e .

# 3. O instalar con pyenv
~/.pyenv/versions/3.12.7/bin/pip install -e .

# 4. Verificar instalación
python -c "import bioql; print(f'BioQL v{bioql.__version__}')"
```

### Ejecución de Tests

```bash
# Test básico con simulador
cd ~/Test
python testing1.py

# O ejecutar directamente
python -c "
from bioql import quantum
result = quantum(
    'Create a Bell state with 2 qubits',
    backend='simulator',
    shots=1024,
    api_key='your_api_key_here'
)
print(f'Success: {result.success}')
"
```

### Test con curl

```bash
curl https://api.bioql.bio/api/quantum/execute \
  -H 'Content-Type: application/json' \
  -d '{
        "program": "Create a Bell state with 2 qubits",
        "backend": "simulator",
        "shots": 1024,
        "api_key": "your_api_key_here"
      }'
```

## 🌐 Servidor de Producción

**URL:** https://api.bioql.bio
**IP:** 167.71.86.90

### Servicios Activos

| Servicio | Puerto | Endpoint | Estado |
|----------|--------|----------|--------|
| Auth/Billing | 5001 | `/auth/*`, `/billing/*` | ✅ Running |
| Quantum Execution | 5002 | `/api/quantum/*` | ✅ Running |
| Docking API | 8100 | `/api/execute` | ✅ Running |
| Nginx | 80/443 | HTTPS Proxy | ✅ Running |

### Endpoints Principales

- `GET /health` - Health check del servidor
- `POST /auth/validate` - Validar API key
- `POST /billing/record-usage` - Registrar uso para billing
- `POST /api/quantum/execute` - Ejecutar circuito cuántico

## 🔑 Autenticación

Obtén tu API key en: https://bioql.com/signup

```python
from bioql import quantum

result = quantum(
    "Your quantum program here",
    backend='ibm_torino',
    shots=2000,
    api_key='bioql_your_api_key_here'
)
```

## 📊 Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Cliente (Mac/Local)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Python     │  │    Jupyter   │  │     CLI      │      │
│  │   Scripts    │  │   Notebooks  │  │   Interface  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                     bioql package                            │
└────────────────────────────┼────────────────────────────────┘
                             │
                    HTTPS (api.bioql.bio)
                             │
┌────────────────────────────▼────────────────────────────────┐
│                  Servidor (Ubuntu VPS)                       │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Nginx (Reverse Proxy)                 │     │
│  │                  Ports 80/443                      │     │
│  └───┬──────────────────┬────────────────┬───────────┘     │
│      │                  │                │                  │
│  ┌───▼────┐      ┌──────▼──────┐    ┌───▼──────────┐      │
│  │ Auth/  │      │  Quantum    │    │   Docking    │      │
│  │ Billing│      │  Execution  │    │     API      │      │
│  │ (5001) │      │   (5002)    │    │   (8100)     │      │
│  └───┬────┘      └──────┬──────┘    └───┬──────────┘      │
│      │                  │                │                  │
│  ┌───▼──────────────────▼────────────────▼──────────┐      │
│  │              BioQL Framework                      │      │
│  │         (Compiler, QEC, Connectors)               │      │
│  └───┬──────────────────┬────────────────┬───────────┘     │
│      │                  │                │                  │
│  ┌───▼────┐      ┌──────▼──────┐    ┌───▼──────────┐      │
│  │ Stripe │      │ IBM Quantum │    │   Quillow    │      │
│  │  API   │      │   Runtime   │    │  QEC Engine  │      │
│  └────────┘      └─────────────┘    └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 🛡️ Corrección de Errores Cuánticos (QEC)

BioQL integra Quillow para QEC a nivel de circuito:

```python
result = quantum(
    "Your program",
    backend='ibm_torino',
    error_correction='surface_code',
    correction_level='low',  # 'low', 'medium', 'high'
    num_logical_qubits=2
)
```

### Parámetros QEC:
- **surface_code**: Surface code con distancia d=3, 5, 7
- **correction_level**: 'low' (d=3), 'medium' (d=5), 'high' (d=7)
- **num_logical_qubits**: Número de qubits lógicos protegidos

## 💰 Billing y Costos

- **Simulador**: $0.01 por shot
- **Hardware IBM**: $3.00 por shot
- **Billing automático**: Integrado con Stripe
- **Balance en tiempo real**: Tracking de uso y costos

## 🔧 Troubleshooting

### Problema: "Unable to connect to BioQL authentication service"

**Solución:**
```bash
# Verificar que estás usando el Python correcto
which python
python -c "import bioql; print(bioql.__file__)"

# Reinstalar en el entorno correcto
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework
pip install -e .
```

### Problema: Servicio no inicia en el servidor

**Solución:**
```bash
# Verificar directorios necesarios
mkdir -p /var/run/bioql /var/log/bioql

# Ver logs del servicio
journalctl -u bioql-api.service -n 50

# Intentar inicio manual
cd /root/bioql_apps/bioql_quillow_docking/web_interface/
./venv/bin/gunicorn --config gunicorn_config.py wsgi:app
```

Ver [TROUBLESHOOTING_2025-11-03.md](./documentation/TROUBLESHOOTING_2025-11-03.md) para más detalles.

## 📞 Soporte

- **Email:** support@bioql.com
- **Documentación:** https://spectrixrd.com/docs
- **API Docs:** https://api.bioql.bio/docs

## 📝 Licencia

Propietario - Spectrix RD LLC

---

**Última actualización:** 2025-11-03
**Versión:** 6.0.0
**Mantenedor:** Heinz Jungbluth
