# AWS Braket - Instrucciones de Uso

## 🚀 Configuración Rápida

### Paso 1: Ejecutar el Script

```bash
~/setup_braket.sh
```

El script ejecutará automáticamente:

1. ✅ Limpiar configuración AWS existente (con backup)
2. ✅ Crear perfil `braket-dev` con tus credenciales
3. ✅ Verificar identidad con `aws sts get-caller-identity`
4. ✅ Listar dispositivos Braket (SV1 simulator)
5. ✅ Crear circuito de Bell (`~/braket-demo/bell.qasm`)
6. ✅ Crear bucket S3 para resultados
7. ✅ Lanzar tarea cuántica con 1000 shots
8. ✅ Monitorear estado y descargar resultados
9. ✅ Analizar mediciones y validar entrelazamiento

### Paso 2: Verificar Resultados

Los resultados estarán en:
- **Circuito**: `~/braket-demo/bell.qasm`
- **Resultados JSON**: `~/braket-demo/results/results.json`
- **Task ARN**: `~/braket-demo/task_arn.txt`

---

## 🔧 Comandos Útiles

### Verificar Credenciales
```bash
aws sts get-caller-identity --profile braket-dev
```

### Listar Tareas Cuánticas
```bash
aws braket search-quantum-tasks --profile braket-dev
```

### Ver Estado de Tarea
```bash
# Usar ARN guardado en task_arn.txt
TASK_ARN=$(cat ~/braket-demo/task_arn.txt)
aws braket get-quantum-task --quantum-task-arn $TASK_ARN --profile braket-dev
```

### Listar Dispositivos Braket
```bash
aws braket search-devices --profile braket-dev
```

### Ver Resultados
```bash
cat ~/braket-demo/results/results.json | jq '.'
```

---

## 📊 Circuito de Bell - Explicación

El circuito `bell.qasm` crea un estado de Bell (entrelazamiento cuántico):

```
|Φ+⟩ = (|00⟩ + |11⟩) / √2
```

**Pasos del circuito:**
1. **Hadamard (H)** en q[0] → Crea superposición: (|0⟩ + |1⟩)/√2
2. **CNOT** (q[0], q[1]) → Entrelaza los qubits
3. **Measure** → Mide ambos qubits

**Resultados esperados:**
- **50%** probabilidad de medir |00⟩
- **50%** probabilidad de medir |11⟩
- **0%** probabilidad de medir |01⟩ o |10⟩ (debido al entrelazamiento)

---

## 🐛 Troubleshooting

### Error: "The security token included in the request is invalid"
- **Causa**: Credenciales incorrectas o expiradas
- **Solución**: Verificar Access Key y Secret Key en el script

### Error: "AccessDeniedException"
- **Causa**: Usuario sin permisos de Braket
- **Solución**: Agregar política IAM `AmazonBraketFullAccess`

### Error: "NoSuchBucket" o "bucket does not start with 'amazon-braket-'"
- **Causa**: AWS Braket requiere que el bucket S3 empiece con `amazon-braket-`
- **Solución**: Crear bucket con prefijo correcto:
  ```bash
  aws s3 mb s3://amazon-braket-bioql-ACCOUNT_ID --profile braket-dev
  ```

### Error: "DeviceNotAvailable"
- **Causa**: Dispositivo cuántico no disponible en la región
- **Solución**: Usar SV1 (disponible en todas las regiones) o cambiar región

---

## 🎯 Próximos Pasos

### 1. Experimentar con Otros Circuitos

**GHZ State (3 qubits):**
```qasm
OPENQASM 3.0;
qubit[3] q;
bit[3] c;

h q[0];
cnot q[0], q[1];
cnot q[0], q[2];

c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
```

**Quantum Teleportation:**
```qasm
OPENQASM 3.0;
qubit[3] q;
bit[3] c;

// Bell pair entre q[1] y q[2]
h q[1];
cnot q[1], q[2];

// Alice entrelaza su qubit con q[0]
cnot q[0], q[1];
h q[0];

// Mediciones de Alice
c[0] = measure q[0];
c[1] = measure q[1];

// Corrección de Bob basada en mediciones
if (c[1] == 1) x q[2];
if (c[0] == 1) z q[2];

c[2] = measure q[2];
```

### 2. Probar Otros Simuladores

**TN1 (Tensor Network Simulator):**
```bash
TN1_ARN="arn:aws:braket:::device/quantum-simulator/amazon/tn1"
```

### 3. Dispositivos Cuánticos Reales

**IonQ Harmony:**
```bash
IONQ_ARN="arn:aws:braket:us-east-1::device/qpu/ionq/Harmony"
```

**Rigetti Aspen-M-3:**
```bash
RIGETTI_ARN="arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3"
```

⚠️ **Nota**: Los dispositivos QPU tienen costo adicional (~$0.30 por tarea + $0.01 por shot)

### 4. Integrar con BioQL 5.0.0

```python
from bioql import quantum

result = quantum(
    "Create a Bell state for molecular docking preparation",
    backend='aws_braket',
    device='sv1',
    shots=1000,
    qec_enabled=True,
    qec_type='surface_code',
    code_distance=5,
    api_key='your_api_key'
)

print(f"Entanglement fidelity: {result.qec_metrics.fidelity:.2%}")
```

---

## 📚 Recursos

- **AWS Braket Docs**: https://docs.aws.amazon.com/braket/
- **OpenQASM 3.0 Spec**: https://openqasm.com/
- **BioQL Docs**: https://docs.bioql.com/
- **Qiskit → Braket**: https://github.com/aws/amazon-braket-sdk-python

---

## 🔐 Seguridad

**Credenciales actuales:**
- Access Key: `__AWS_ID_REDACTED__`
- Region: `us-east-1`
- Profile: `braket-dev`

**⚠️ IMPORTANTE**:
- No compartir credenciales públicamente
- Rotar Access Keys cada 90 días
- Usar IAM roles en producción
- Habilitar MFA para la cuenta

---

## 💰 Costos Estimados

### SV1 Simulator (State Vector)
- **Gratis** hasta 1 hora/mes (AWS Free Tier)
- **$0.075/hora** después de Free Tier
- Bell circuit (1000 shots) ≈ $0.001

### TN1 Simulator (Tensor Network)
- **$0.275/hora**
- Mejor para circuitos grandes (>30 qubits)

### Dispositivos QPU
- **IonQ**: $0.30 por tarea + $0.01 por shot
- **Rigetti**: $0.30 por tarea + $0.00035 por shot
- **QuEra**: $0.30 por tarea + $0.01 por shot

**Ejemplo Bell circuit en IonQ:**
- 1 tarea + 1000 shots = $0.30 + (1000 × $0.01) = **$10.30**

---

**✅ Todo listo para quantum computing con AWS Braket!**
