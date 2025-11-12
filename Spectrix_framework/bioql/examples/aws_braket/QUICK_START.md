# 🚀 Quick Start - BioQL + AWS Braket

## Setup en 3 Pasos

### 1️⃣ Ejecutar Script de Configuración
```bash
~/setup_braket.sh
```

Este comando:
- ✅ Configura AWS CLI (perfil `braket-dev`)
- ✅ Verifica credenciales
- ✅ Crea bucket S3 (`amazon-braket-bioql-*`)
- ✅ Lanza circuito de Bell en SV1
- ✅ Descarga y analiza resultados

**Tiempo**: ~30 segundos

---

### 2️⃣ Verificar Resultados
```bash
cd ~/braket-demo
cat README.md
```

**Resultado esperado**:
- |00⟩: ~50%
- |11⟩: ~50%
- |01⟩: 0%
- |10⟩: 0%
- **Entrelazamiento**: 100% ✅

---

### 3️⃣ Test BioQL
```python
from bioql import quantum

result = quantum(
    "Create a Bell state",
    backend='simulator',
    shots=1000,
    api_key='bioql_dev_test_key_12345'
)

print(f"Success: {result.success}")
print(f"Counts: {result.counts}")
```

---

## Comandos Útiles

### AWS Braket

```bash
# Ver identidad
aws sts get-caller-identity --profile braket-dev

# Listar tareas
aws braket search-quantum-tasks --profile braket-dev | jq '.quantumTasks[0:3]'

# Ver dispositivos
aws braket search-devices --profile braket-dev | jq '.devices[] | {name: .deviceName, status: .deviceStatus}'
```

### BioQL

```bash
# Versión
python3 -c "from bioql import __version__; print(__version__)"

# Test simple
python3 -c "from bioql import quantum; r = quantum('test', shots=10); print(r.success)"

# Con QEC
python3 << EOF
from bioql import quantum

result = quantum(
    "Bell state with QEC",
    shots=1000,
    qec_enabled=True,
    qec_type='surface_code',
    code_distance=5,
    api_key='bioql_dev_test_key_12345'
)

print(f"Physical Qubits: {result.qec_metrics.physical_qubits}")
print(f"Fidelity: {result.qec_metrics.fidelity:.2%}")
EOF
```

---

## Archivos Importantes

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| **Script** | `~/setup_braket.sh` | Setup completo automatizado |
| **Instrucciones** | `~/braket_instructions.md` | Guía detallada |
| **Integración** | `~/bioql_braket_integration.md` | BioQL + Braket |
| **Éxito** | `~/AWS_BRAKET_SUCCESS.md` | Resultados verificados |
| **Circuito** | `~/braket-demo/bell.qasm` | Bell state QASM |
| **Resultados** | `~/braket-demo/results/results.json` | Mediciones |

---

## Troubleshooting

### Error: "bucket does not start with 'amazon-braket-'"
**Fix**:
```bash
aws s3 mb s3://amazon-braket-bioql-$(aws sts get-caller-identity --profile braket-dev --query Account --output text) --profile braket-dev
```

### Error: "Credentials invalid"
**Fix**:
```bash
aws configure --profile braket-dev
# Access Key: __AWS_ID_REDACTED__
# Secret: __AWSSEC_REDACTED__
# Region: us-east-1
# Output: json
```

### Error: "Task not found"
**Fix**: Esperar unos segundos, las tareas pueden tardar 1-3 segundos en completarse.

---

## Próximos Experimentos

### Circuito GHZ (3 qubits)
```bash
cat > ~/braket-demo/ghz.qasm << 'EOF'
OPENQASM 3.0;
qubit[3] q;
bit[3] c;

h q[0];
cnot q[0], q[1];
cnot q[0], q[2];

c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
EOF

# Ejecutar
aws braket create-quantum-task \
  --device-arn "arn:aws:braket:::device/quantum-simulator/amazon/sv1" \
  --action "{\"braketSchemaHeader\":{\"name\":\"braket.ir.openqasm.program\",\"version\":\"1\"},\"source\":\"$(cat ~/braket-demo/ghz.qasm | tr '\n' '\\n')\"}" \
  --shots 1000 \
  --output-s3-bucket "amazon-braket-bioql-013081881366" \
  --output-s3-key-prefix "quantum-tasks" \
  --profile braket-dev
```

**Esperado**: Solo |000⟩ y |111⟩ (50% cada uno)

---

## Costos Estimados

| Operación | Dispositivo | Costo |
|-----------|-------------|-------|
| Bell (1000 shots) | SV1 | Gratis (Free Tier) |
| GHZ (1000 shots) | SV1 | Gratis (Free Tier) |
| VQE H2 (5000 shots) | SV1 | ~$0.01 |
| Grover (1000 shots) | IonQ | ~$10.30 |

**Free Tier**: 1 hora/mes de SV1 gratis

---

## Recursos

- 📖 **Docs**: `~/braket_instructions.md`
- 🔗 **PyPI**: https://pypi.org/project/bioql/5.0.0/
- 🌐 **AWS Console**: https://console.aws.amazon.com/braket/
- 📊 **Resultados**: `~/braket-demo/README.md`

---

**✅ Sistema listo - Happy Quantum Computing! ⚛️**
