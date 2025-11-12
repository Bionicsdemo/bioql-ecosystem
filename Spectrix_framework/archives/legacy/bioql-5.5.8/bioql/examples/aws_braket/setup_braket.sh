#!/bin/bash
###############################################################################
# AWS Braket - Script de Configuración Completo
# BioQL 5.0.0 - Amazon Braket Integration
###############################################################################
# PROPÓSITO: Configurar AWS CLI con credenciales válidas y lanzar una tarea
#            cuántica de ejemplo en Amazon Braket SV1 simulator
#
# PREREQUISITOS:
#   - AWS CLI instalado (brew install awscli o pip install awscli)
#   - Credenciales AWS válidas (proporcionadas abajo)
#   - Permisos: Braket, S3, STS
#
# USO:
#   chmod +x ~/setup_braket.sh
#   ~/setup_braket.sh
###############################################################################

set -e  # Exit on error
trap 'echo "❌ Error en línea $LINENO"' ERR

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_section() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  $1${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

###############################################################################
# PASO 1: LIMPIAR CONFIGURACIÓN EXISTENTE
###############################################################################
print_section "PASO 1: Limpieza de Configuración AWS"

print_info "Creando backup de configuración existente..."

# Crear directorio .aws si no existe
mkdir -p ~/.aws

# Backup de archivos existentes
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f ~/.aws/config ]; then
    cp ~/.aws/config ~/.aws/config.backup.$TIMESTAMP
    print_success "Backup creado: ~/.aws/config.backup.$TIMESTAMP"
fi

if [ -f ~/.aws/credentials ]; then
    cp ~/.aws/credentials ~/.aws/credentials.backup.$TIMESTAMP
    print_success "Backup creado: ~/.aws/credentials.backup.$TIMESTAMP"
fi

###############################################################################
# PASO 2: CREAR PERFIL braket-dev
###############################################################################
print_section "PASO 2: Configuración de Perfil braket-dev"

print_info "Escribiendo nuevas credenciales..."

# NOTA: Reemplaza estos valores con tus credenciales reales
AWS_ACCESS_KEY_ID="__AWS_ID_REDACTED__"
AWS_SECRET_ACCESS_KEY="__AWSSEC_REDACTED__"
AWS_REGION="us-east-1"
AWS_OUTPUT_FORMAT="json"
PROFILE_NAME="braket-dev"

# Escribir credentials
cat > ~/.aws/credentials << EOF
[${PROFILE_NAME}]
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}
EOF

# Escribir config
cat > ~/.aws/config << EOF
[profile ${PROFILE_NAME}]
region = ${AWS_REGION}
output = ${AWS_OUTPUT_FORMAT}
EOF

# Asegurar permisos correctos
chmod 600 ~/.aws/credentials
chmod 600 ~/.aws/config

print_success "Perfil '${PROFILE_NAME}' creado exitosamente"

# Exportar variables de entorno
export AWS_PROFILE="${PROFILE_NAME}"
export AWS_DEFAULT_REGION="${AWS_REGION}"

print_success "Variables de entorno exportadas:"
echo "  AWS_PROFILE=${AWS_PROFILE}"
echo "  AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}"

###############################################################################
# PASO 3: VERIFICAR CREDENCIALES
###############################################################################
print_section "PASO 3: Verificación de Credenciales"

print_info "Ejecutando: aws sts get-caller-identity --profile ${PROFILE_NAME}"

if IDENTITY=$(aws sts get-caller-identity --profile ${PROFILE_NAME} 2>&1); then
    print_success "Credenciales válidas!"
    echo "$IDENTITY" | jq '.'

    # Extraer información
    ACCOUNT_ID=$(echo "$IDENTITY" | jq -r '.Account')
    USER_ID=$(echo "$IDENTITY" | jq -r '.UserId')
    ARN=$(echo "$IDENTITY" | jq -r '.Arn')

    echo ""
    print_info "Detalles de la cuenta:"
    echo "  Account ID: $ACCOUNT_ID"
    echo "  User ID: $USER_ID"
    echo "  ARN: $ARN"
else
    print_error "Credenciales inválidas o sin permisos STS"
    echo "$IDENTITY"
    exit 1
fi

###############################################################################
# PASO 4: LISTAR DISPOSITIVOS BRAKET
###############################################################################
print_section "PASO 4: Listado de Dispositivos Braket"

print_info "Buscando dispositivo SV1 (State Vector Simulator)..."

# SV1 ARN (simulador de estado vectorial)
SV1_ARN="arn:aws:braket:::device/quantum-simulator/amazon/sv1"

print_info "Ejecutando: aws braket get-device --device-arn ${SV1_ARN}"

if DEVICE_INFO=$(aws braket get-device --device-arn "${SV1_ARN}" --profile ${PROFILE_NAME} 2>&1); then
    print_success "Dispositivo SV1 encontrado!"

    # Mostrar información clave
    DEVICE_NAME=$(echo "$DEVICE_INFO" | jq -r '.deviceName')
    DEVICE_STATUS=$(echo "$DEVICE_INFO" | jq -r '.deviceStatus')
    DEVICE_TYPE=$(echo "$DEVICE_INFO" | jq -r '.deviceType')

    echo ""
    print_info "Información del dispositivo:"
    echo "  Nombre: $DEVICE_NAME"
    echo "  Estado: $DEVICE_STATUS"
    echo "  Tipo: $DEVICE_TYPE"
    echo "  ARN: $SV1_ARN"
else
    print_warning "No se pudo obtener info del dispositivo (puede ser por permisos)"
    echo "$DEVICE_INFO"
    print_info "Continuando con ARN conocido: $SV1_ARN"
fi

###############################################################################
# PASO 5: CREAR CIRCUITO DE BELL
###############################################################################
print_section "PASO 5: Creación de Circuito Cuántico de Bell"

# Crear directorio para demo
DEMO_DIR="$HOME/braket-demo"
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

print_info "Directorio de trabajo: $DEMO_DIR"

# Crear circuito de Bell en OpenQASM 3.0
cat > bell.qasm << 'EOF'
OPENQASM 3.0;

// Circuito de Bell - Crear estado entrelazado |Φ+⟩ = (|00⟩ + |11⟩)/√2
// Este es el circuito cuántico más simple que demuestra entrelazamiento

// Declarar 2 qubits
qubit[2] q;

// Declarar 2 bits clásicos para medición
bit[2] c;

// Puerta Hadamard en qubit 0 - crear superposición
h q[0];

// Puerta CNOT (Controlled-NOT) - crear entrelazamiento
// Si q[0] es |1⟩, flip q[1]
cnot q[0], q[1];

// Medir ambos qubits
c[0] = measure q[0];
c[1] = measure q[1];

// Resultado esperado:
// 50% probabilidad de |00⟩ (ambos qubits miden 0)
// 50% probabilidad de |11⟩ (ambos qubits miden 1)
// 0% probabilidad de |01⟩ o |10⟩ (debido al entrelazamiento)
EOF

print_success "Circuito de Bell creado: $DEMO_DIR/bell.qasm"
echo ""
print_info "Contenido del circuito:"
cat bell.qasm

###############################################################################
# PASO 6: CREAR/VERIFICAR BUCKET S3
###############################################################################
print_section "PASO 6: Configuración de S3 Bucket"

# Nombre del bucket (DEBE empezar con 'amazon-braket-' por requisito de AWS)
S3_BUCKET="amazon-braket-bioql-${ACCOUNT_ID}"
S3_PREFIX="quantum-tasks"

print_info "Bucket S3: s3://${S3_BUCKET}/${S3_PREFIX}/"

# Verificar si el bucket existe
if aws s3 ls "s3://${S3_BUCKET}" --profile ${PROFILE_NAME} 2>&1 | grep -q "NoSuchBucket"; then
    print_info "Bucket no existe, creando..."

    if [ "${AWS_REGION}" = "us-east-1" ]; then
        # us-east-1 no requiere LocationConstraint
        aws s3 mb "s3://${S3_BUCKET}" --profile ${PROFILE_NAME}
    else
        aws s3 mb "s3://${S3_BUCKET}" --region ${AWS_REGION} --profile ${PROFILE_NAME}
    fi

    print_success "Bucket creado: s3://${S3_BUCKET}"
else
    print_success "Bucket ya existe: s3://${S3_BUCKET}"
fi

# Verificar acceso de escritura
print_info "Verificando permisos de escritura..."
echo "test" > test.txt
aws s3 cp test.txt "s3://${S3_BUCKET}/${S3_PREFIX}/test.txt" --profile ${PROFILE_NAME}
rm test.txt

print_success "Permisos de escritura verificados"

###############################################################################
# PASO 7: LANZAR TAREA CUÁNTICA
###############################################################################
print_section "PASO 7: Lanzamiento de Tarea Cuántica en SV1"

print_info "Preparando parámetros de la tarea..."

# Leer el circuito
CIRCUIT_QASM=$(cat bell.qasm)

# Número de shots (repeticiones)
SHOTS=1000

# Crear JSON del action (debe ser string JSON serializado)
ACTION_JSON=$(cat << 'EOF_ACTION'
{
  "braketSchemaHeader": {
    "name": "braket.ir.openqasm.program",
    "version": "1"
  },
  "source": "OPENQASM 3.0;\nqubit[2] q;\nbit[2] c;\nh q[0];\ncnot q[0], q[1];\nc[0] = measure q[0];\nc[1] = measure q[1];"
}
EOF_ACTION
)

print_info "Parámetros de la tarea:"
echo "  Dispositivo: SV1 (State Vector Simulator)"
echo "  Shots: ${SHOTS}"
echo "  Bucket S3: s3://${S3_BUCKET}/${S3_PREFIX}"

print_info "Lanzando tarea cuántica..."

# Lanzar tarea usando parámetros individuales
TASK_RESPONSE=$(aws braket create-quantum-task \
  --device-arn "${SV1_ARN}" \
  --action "${ACTION_JSON}" \
  --shots ${SHOTS} \
  --output-s3-bucket "${S3_BUCKET}" \
  --output-s3-key-prefix "${S3_PREFIX}" \
  --profile ${PROFILE_NAME} 2>&1)

# Verificar si hubo error
if echo "$TASK_RESPONSE" | grep -q "error\|Error\|failed\|Failed"; then
    print_error "Error al crear tarea cuántica:"
    echo "$TASK_RESPONSE"
    exit 1
fi

# Extraer ARN de la tarea
TASK_ARN=$(echo "$TASK_RESPONSE" | jq -r '.quantumTaskArn')

if [ "$TASK_ARN" = "null" ] || [ -z "$TASK_ARN" ]; then
    print_error "No se pudo obtener Task ARN"
    echo "$TASK_RESPONSE"
    exit 1
fi

print_success "Tarea cuántica creada!"
echo ""
print_info "Task ARN: $TASK_ARN"

# Guardar ARN para referencia
echo "$TASK_ARN" > task_arn.txt

###############################################################################
# PASO 8: MONITOREAR ESTADO DE LA TAREA
###############################################################################
print_section "PASO 8: Monitoreo de Estado de la Tarea"

print_info "Consultando estado de la tarea..."

# Esperar y verificar estado
MAX_ATTEMPTS=30
ATTEMPT=0
TASK_STATUS="QUEUED"

while [ "$TASK_STATUS" != "COMPLETED" ] && [ "$TASK_STATUS" != "FAILED" ] && [ "$TASK_STATUS" != "CANCELLED" ] && [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))

    print_info "Intento $ATTEMPT/$MAX_ATTEMPTS - Consultando estado..."

    TASK_INFO=$(aws braket get-quantum-task \
      --quantum-task-arn "${TASK_ARN}" \
      --profile ${PROFILE_NAME})

    TASK_STATUS=$(echo "$TASK_INFO" | jq -r '.status')

    echo "  Estado actual: $TASK_STATUS"

    if [ "$TASK_STATUS" = "COMPLETED" ]; then
        print_success "Tarea completada exitosamente!"
        break
    elif [ "$TASK_STATUS" = "FAILED" ]; then
        print_error "Tarea falló"
        echo "$TASK_INFO" | jq '.failureReason'
        exit 1
    elif [ "$TASK_STATUS" = "CANCELLED" ]; then
        print_warning "Tarea cancelada"
        exit 1
    else
        print_info "Estado: $TASK_STATUS - Esperando 3 segundos..."
        sleep 3
    fi
done

if [ "$TASK_STATUS" != "COMPLETED" ]; then
    print_warning "Tarea no completada después de $MAX_ATTEMPTS intentos"
    print_info "Estado final: $TASK_STATUS"
    print_info "Puedes verificar manualmente con:"
    echo "  aws braket get-quantum-task --quantum-task-arn ${TASK_ARN} --profile ${PROFILE_NAME}"
    exit 0
fi

###############################################################################
# PASO 9: DESCARGAR Y ANALIZAR RESULTADOS
###############################################################################
print_section "PASO 9: Análisis de Resultados"

# Extraer ruta del resultado en S3
OUTPUT_S3_URI=$(echo "$TASK_INFO" | jq -r '.outputS3Bucket')
OUTPUT_S3_DIR=$(echo "$TASK_INFO" | jq -r '.outputS3Directory')

print_info "Resultados en: s3://${OUTPUT_S3_URI}/${OUTPUT_S3_DIR}"

# Descargar resultados
print_info "Descargando resultados..."

mkdir -p results

# Intentar descargar results.json
if aws s3 cp "s3://${OUTPUT_S3_URI}/${OUTPUT_S3_DIR}/results.json" \
  results/results.json \
  --profile ${PROFILE_NAME} 2>/dev/null; then
    print_success "Resultados descargados: $DEMO_DIR/results/results.json"
else
    # Si no existe results.json, listar contenido del directorio
    print_warning "results.json no encontrado, listando contenido S3..."
    aws s3 ls "s3://${OUTPUT_S3_URI}/${OUTPUT_S3_DIR}/" --profile ${PROFILE_NAME}

    # Intentar descargar cualquier archivo .json
    aws s3 sync "s3://${OUTPUT_S3_URI}/${OUTPUT_S3_DIR}/" results/ \
      --exclude "*" --include "*.json" \
      --profile ${PROFILE_NAME}

    print_success "Archivos descargados a: $DEMO_DIR/results/"
fi

# Analizar resultados
print_info "Analizando mediciones del circuito de Bell..."

# Buscar el archivo de resultados correcto
RESULT_FILE=""
if [ -f "results/results.json" ]; then
    RESULT_FILE="results/results.json"
else
    # Buscar cualquier .json en results/
    RESULT_FILE=$(find results/ -name "*.json" -type f | head -1)
fi

if [ -z "$RESULT_FILE" ] || [ ! -f "$RESULT_FILE" ]; then
    print_warning "No se encontraron archivos de resultados"
    print_info "Puedes verificar los resultados manualmente en:"
    echo "  s3://${OUTPUT_S3_URI}/${OUTPUT_S3_DIR}/"
    exit 0
fi

print_info "Usando archivo: $RESULT_FILE"

# Extraer measurements (puede estar en diferentes ubicaciones según el formato)
MEASUREMENTS=$(cat "$RESULT_FILE" | jq -r '.measurements // .measurementCounts // empty')
MEASURED_QUBITS=$(cat "$RESULT_FILE" | jq -r '.measuredQubits // [0,1] | @json')

if [ -z "$MEASUREMENTS" ] || [ "$MEASUREMENTS" = "null" ]; then
    print_warning "No se pudieron extraer mediciones del archivo"
    print_info "Contenido del archivo de resultados:"
    cat "$RESULT_FILE" | jq '.'
    exit 0
fi

echo ""
print_info "Qubits medidos: $MEASURED_QUBITS"
echo ""

# Contar resultados
COUNT_00=$(echo "$MEASUREMENTS" | jq -r '.[] | select(.[0] == 0 and .[1] == 0)' 2>/dev/null | wc -l | tr -d ' ')
COUNT_11=$(echo "$MEASUREMENTS" | jq -r '.[] | select(.[0] == 1 and .[1] == 1)' 2>/dev/null | wc -l | tr -d ' ')
COUNT_01=$(echo "$MEASUREMENTS" | jq -r '.[] | select(.[0] == 0 and .[1] == 1)' 2>/dev/null | wc -l | tr -d ' ')
COUNT_10=$(echo "$MEASUREMENTS" | jq -r '.[] | select(.[0] == 1 and .[1] == 0)' 2>/dev/null | wc -l | tr -d ' ')

# Asegurar que los contadores no estén vacíos
COUNT_00=${COUNT_00:-0}
COUNT_11=${COUNT_11:-0}
COUNT_01=${COUNT_01:-0}
COUNT_10=${COUNT_10:-0}

TOTAL_SHOTS=$((COUNT_00 + COUNT_11 + COUNT_01 + COUNT_10))

if [ "$TOTAL_SHOTS" -eq 0 ]; then
    print_warning "No se pudieron contar las mediciones"
    print_info "Mostrando estructura del archivo de resultados:"
    cat "$RESULT_FILE" | jq '.'
    exit 0
fi

print_success "Resultados del Circuito de Bell:"
echo ""
echo "  |00⟩: $COUNT_00 veces ($(awk "BEGIN {printf \"%.1f\", $COUNT_00*100/$TOTAL_SHOTS}")%)"
echo "  |11⟩: $COUNT_11 veces ($(awk "BEGIN {printf \"%.1f\", $COUNT_11*100/$TOTAL_SHOTS}")%)"
echo "  |01⟩: $COUNT_01 veces ($(awk "BEGIN {printf \"%.1f\", $COUNT_01*100/$TOTAL_SHOTS}")%)"
echo "  |10⟩: $COUNT_10 veces ($(awk "BEGIN {printf \"%.1f\", $COUNT_10*100/$TOTAL_SHOTS}")%)"
echo ""
echo "  Total de mediciones: $TOTAL_SHOTS"

# Validar entrelazamiento
print_info "Validación de entrelazamiento cuántico:"

ENTANGLED_STATES=$((COUNT_00 + COUNT_11))
ENTANGLED_PERCENT=$(awk "BEGIN {printf \"%.1f\", $ENTANGLED_STATES*100/$TOTAL_SHOTS}")

if [ $(echo "$ENTANGLED_PERCENT > 95" | bc) -eq 1 ]; then
    print_success "Entrelazamiento confirmado: ${ENTANGLED_PERCENT}% de estados |00⟩ y |11⟩"
    echo "  ✅ El circuito de Bell funcionó correctamente"
else
    print_warning "Entrelazamiento parcial: ${ENTANGLED_PERCENT}% de estados esperados"
    echo "  ⚠️  Se esperaba >95% de estados |00⟩ y |11⟩"
fi

###############################################################################
# RESUMEN FINAL
###############################################################################
print_section "RESUMEN FINAL"

print_success "Configuración de AWS Braket completada exitosamente!"
echo ""
echo "📋 Información de la configuración:"
echo "  • Perfil AWS: ${PROFILE_NAME}"
echo "  • Región: ${AWS_REGION}"
echo "  • Account ID: ${ACCOUNT_ID}"
echo ""
echo "🚀 Tarea cuántica ejecutada:"
echo "  • Dispositivo: SV1 (State Vector Simulator)"
echo "  • Task ARN: ${TASK_ARN}"
echo "  • Estado: ${TASK_STATUS}"
echo "  • Shots ejecutados: ${TOTAL_SHOTS}"
echo ""
echo "📁 Archivos generados:"
echo "  • Circuito: $DEMO_DIR/bell.qasm"
echo "  • Resultados: $DEMO_DIR/results/results.json"
echo "  • Task ARN: $DEMO_DIR/task_arn.txt"
echo ""
echo "🔧 Comandos útiles:"
echo ""
echo "  # Verificar identidad"
echo "  aws sts get-caller-identity --profile ${PROFILE_NAME}"
echo ""
echo "  # Listar tareas cuánticas"
echo "  aws braket search-quantum-tasks --profile ${PROFILE_NAME}"
echo ""
echo "  # Ver estado de tarea específica"
echo "  aws braket get-quantum-task --quantum-task-arn ${TASK_ARN} --profile ${PROFILE_NAME}"
echo ""
echo "  # Listar dispositivos disponibles"
echo "  aws braket search-devices --profile ${PROFILE_NAME}"
echo ""
echo "🎯 Próximos pasos:"
echo "  1. Modificar bell.qasm para experimentar con otros circuitos"
echo "  2. Probar otros simuladores: TN1 (tensor network)"
echo "  3. Explorar dispositivos cuánticos reales (IonQ, Rigetti, etc.)"
echo "  4. Integrar con BioQL para quantum computing farmacéutico"
echo ""
print_success "¡Todo listo para desarrollar aplicaciones cuánticas con AWS Braket!"

###############################################################################
# FIN DEL SCRIPT
###############################################################################
