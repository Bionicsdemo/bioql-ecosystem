# BioQL v3.0.2 - Estructura del Proyecto

Este documento describe la estructura organizada del proyecto BioQL después de la reorganización del 2025-09-30.

## 📁 Estructura de Directorios

```
bioql/
├── 📦 bioql/                      # Librería principal (para distribución en PyPI)
│   ├── __init__.py               # Exports principales
│   ├── quantum_connector.py      # Función quantum() principal
│   ├── compiler.py               # Compilador BQL con 164B patterns
│   ├── bio_interpreter.py        # Interpretador bioinformático
│   ├── billing_integration.py    # Integración de billing
│   ├── simple_billing.py         # Billing simplificado
│   ├── cloud_auth.py             # Autenticación cloud
│   ├── logger.py                 # Sistema de logging
│   ├── cli.py                    # CLI de BioQL
│   ├── enhanced_quantum.py       # DevKit features
│   ├── dynamic_bridge.py         # Bridge dinámico
│   │
│   ├── 🧬 chem/                  # Química computacional
│   │   ├── geometry.py
│   │   ├── ligand_prep.py
│   │   └── receptor_prep.py
│   │
│   ├── 🔧 compilers/             # Compiladores para backends
│   │   ├── base.py
│   │   ├── qiskit_compiler.py
│   │   ├── cirq_compiler.py
│   │   └── factory.py
│   │
│   ├── 🎯 docking/               # Molecular docking
│   │   ├── pipeline.py
│   │   ├── vina_runner.py
│   │   └── quantum_runner.py
│   │
│   ├── 📋 ir/                    # Intermediate Representation
│   │   ├── schema.py
│   │   └── validators.py
│   │
│   ├── 🗣️ parser/                # Parsers de lenguaje natural
│   │   ├── nl_parser.py          # Parser base
│   │   ├── llm_parser.py         # Parser con LLM (opcional)
│   │   ├── mega_patterns.py      # 26M patterns
│   │   └── ultra_patterns.py     # Generador 164B patterns
│   │
│   └── 👁️ visualize/             # Visualización molecular
│       ├── py3dmol_viz.py
│       └── pymol_viz.py
│
├── 📚 docs/                       # Documentación (NO en PyPI)
│   ├── BIOQL_V3_README.md        # README de v3.0
│   ├── PRICING_MODEL.md          # Modelo de precios
│   │
│   ├── admin/                    # Documentación administrativa
│   │   ├── ADMIN_MANUAL.md
│   │   └── BILLING_STATUS.md
│   │
│   └── technical/                # Documentación técnica
│       └── TECHNICAL_REFERENCE.md
│
├── 🧪 tests/                      # Tests (NO en PyPI)
│   ├── test_v3_mega_patterns.py  # Test de 164B patterns
│   ├── test_bioql.py
│   ├── test_compiler.py
│   ├── test_quantum.py
│   ├── test_bio_interpreter.py
│   ├── test_dynamic_bridge.py
│   ├── test_chem.py
│   ├── test_docking.py
│   ├── test_visualize.py
│   ├── test_integration.py
│   │
│   ├── integration/              # Tests de integración
│   │   ├── test_billing_fix.py
│   │   ├── test_docking_simple.py
│   │   ├── test_enhanced_integration.py
│   │   └── test_final_windows.py
│   │
│   └── validation/               # Tests de validación
│       └── validate_installation.py
│
├── 🎯 examples/                   # Ejemplos de uso (SÍ en PyPI)
│   ├── basic_usage.py
│   ├── advanced_features.py
│   ├── drug_discovery.py
│   ├── protein_folding.py
│   ├── dna_matching.py
│   ├── billing_integration_examples.py
│   │
│   └── glp1r_drug_discovery/     # Proyecto GLP1R completo
│       └── scripts/
│           ├── glp1r_simulator.py
│           ├── glp1r_drug_design.py
│           ├── generate_molecule_pdb.py
│           └── compare_glp1_drugs.py
│
├── 🔧 scripts/                    # Scripts de administración (NO en PyPI)
│   ├── admin/                    # Scripts administrativos
│   │   ├── bioql_auth_server.py  # Servidor de autenticación
│   │   ├── bioql_admin_simple.py # CLI administrativa
│   │   └── auth_server.py        # Servidor de auth simplificado
│   │
│   └── database/                 # Scripts de database
│
├── 💾 data/                       # Datos del proyecto (NO en PyPI)
│   └── databases/                # Bases de datos
│       ├── bioql_billing.db      # Database principal (32KB)
│       └── bioql_auth_production.db  # Database de auth
│
├── 📦 archive/                    # Archivos antiguos (NO en PyPI)
│   ├── old_configs/              # Configs duplicadas
│   │   ├── pytest 2.ini
│   │   └── requirements-dev 2.txt
│   │
│   └── old_builds/               # Build artifacts
│       ├── .coverage
│       └── htmlcov/
│
├── 🏢 BP&PL/                      # Business Plan & Product Logic (NO en PyPI)
├── 🎨 branding/                   # Assets de marca (NO en PyPI)
├── 💻 ide_extensions/             # Extensiones de IDE (NO en PyPI)
├── ⚙️ config/                     # Configuraciones (NO en PyPI)
├── 🧑‍💻 dev/                        # Desarrollo interno (NO en PyPI)
│
├── 📄 Archivos de configuración raíz:
│   ├── setup.py                  # Setup script
│   ├── pyproject.toml            # Configuración moderna de Python
│   ├── requirements.txt          # Dependencias principales
│   ├── requirements-dev.txt      # Dependencias de desarrollo
│   ├── requirements-vina.txt     # Dependencias de Vina
│   ├── requirements-viz.txt      # Dependencias de visualización
│   ├── requirements-openmm.txt   # Dependencias de OpenMM
│   ├── pytest.ini                # Configuración de pytest
│   ├── .gitignore                # Git ignore actualizado
│   │
│   ├── LICENSE                   # MIT License
│   ├── CHANGELOG.md              # Historial de cambios
│   └── PROJECT_STRUCTURE.md      # Este archivo
```

## 📦 Lo que se incluye en PyPI

El paquete distribuido en PyPI (`pip install bioql`) **SOLO** incluye:

✅ **Incluido:**
- `bioql/` - Librería completa
- `examples/` - Ejemplos de uso
- `LICENSE` - Licencia MIT
- `CHANGELOG.md` - Historial
- `setup.py` y `pyproject.toml` - Metadata

❌ **NO Incluido (excluido por .gitignore y pyproject.toml):**
- `docs/` - Documentación interna
- `tests/` - Suite de tests
- `scripts/` - Scripts administrativos
- `data/` - Bases de datos
- `archive/` - Archivos antiguos
- `BP&PL/` - Business logic
- `branding/` - Assets de marca
- `ide_extensions/` - Extensiones IDE
- `config/` - Configuraciones
- `dev/` - Desarrollo interno

## 🔗 Conexiones Importantes

### Bases de Datos

Todas las referencias a bases de datos ahora apuntan a:
```
/Users/heinzjungbluth/Desktop/bioql/data/databases/
```

**Archivos actualizados:**
- ✅ `bioql/simple_billing.py` - Usa `get_database_path()`
- ✅ `scripts/admin/bioql_auth_server.py` - Path actualizado
- ✅ `scripts/admin/auth_server.py` - Path actualizado
- ✅ `scripts/admin/bioql_admin_simple.py` - Path actualizado

### Imports de Parser

El módulo `bioql/parser/__init__.py` ahora tiene imports opcionales:
- ✅ `llm_parser` es opcional (requiere `loguru`, `httpx`)
- ✅ Si falta, las funciones LLM son `None` (no rompe la librería)

## 📊 Estadísticas

- **Librería BioQL**: ~50 archivos Python
- **Tests**: ~20 archivos de test
- **Ejemplos**: ~15 ejemplos de uso
- **Documentación**: ~10 archivos MD
- **Scripts admin**: 3 scripts
- **Bases de datos**: 2 archivos DB (32KB total)

## 🚀 Versión Actual

**BioQL v3.0.2** (2025-09-30)
- 164 BILLION natural language patterns
- API Key authentication REQUIRED
- Cloud billing integration
- PyPI: https://pypi.org/project/bioql/3.0.2/

## 🔄 Comandos Útiles

### Instalar desde PyPI
```bash
pip install --upgrade bioql
```

### Desarrollo local
```bash
pip install -e .
```

### Ejecutar tests
```bash
pytest tests/
```

### Ejecutar admin CLI
```bash
python3 scripts/admin/bioql_admin_simple.py
```

### Ejecutar auth server
```bash
python3 scripts/admin/bioql_auth_server.py
```

---

**Última actualización**: 2025-09-30 por Claude Code
**Versión del proyecto**: 3.0.2
