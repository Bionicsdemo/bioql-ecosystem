# 🌐 Azure Quantum - Setup desde CLI

**Guía completa para crear y configurar Azure Quantum Workspace desde la línea de comandos**

Fecha: October 3, 2025

---

## 📋 PREREQUISITOS

### 1. Azure CLI Instalado

```bash
# macOS (Homebrew)
brew update && brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Descargar desde: https://aka.ms/installazurecliwindows

# Verificar instalación
az --version
```

### 2. Extensión de Azure Quantum

```bash
# Instalar extensión de Quantum
az extension add --name quantum

# Verificar extensión
az extension list --output table
```

### 3. Login en Azure

```bash
# Login interactivo
az login

# O con service principal
az login --service-principal \
  --username <app-id> \
  --password <password-or-cert> \
  --tenant <tenant-id>

# Verificar suscripción
az account show
```

---

## 🚀 CREAR WORKSPACE DE AZURE QUANTUM

### Método 1: Comando Directo (Recomendado)

```bash
# Variables de configuración
SUBSCRIPTION_ID="your-subscription-id"
RESOURCE_GROUP="bioql-quantum-rg"
WORKSPACE_NAME="bioql-quantum-workspace"
LOCATION="eastus"  # o westus, westeurope, etc.
STORAGE_ACCOUNT="bioqlquantumstorage"

# Crear resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Crear storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Crear Quantum Workspace
az quantum workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --location $LOCATION \
  --storage-account "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
```

### Método 2: Con Archivo de Configuración JSON

```bash
# Crear archivo de configuración
cat > quantum-workspace-config.json << 'EOF'
{
  "location": "eastus",
  "properties": {
    "providers": [
      {
        "providerId": "ionq",
        "providerSku": "pay-as-you-go-cred"
      },
      {
        "providerId": "microsoft-qc",
        "providerSku": "learn-and-develop"
      },
      {
        "providerId": "quantinuum",
        "providerSku": "pay-as-you-go-cred"
      }
    ],
    "storageAccount": "/subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/Microsoft.Storage/storageAccounts/{storage-name}"
  }
}
EOF

# Crear workspace con configuración
az quantum workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --location $LOCATION \
  --provider-sku-list "ionq/pay-as-you-go-cred" "microsoft-qc/learn-and-develop"
```

---

## ⚙️ CONFIGURAR PROVIDERS

### Agregar IonQ

```bash
az quantum workspace provider add \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --provider-id "ionq" \
  --provider-sku "pay-as-you-go-cred"
```

### Agregar Quantinuum

```bash
az quantum workspace provider add \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --provider-id "quantinuum" \
  --provider-sku "pay-as-you-go-cred"
```

### Agregar Microsoft QIO

```bash
az quantum workspace provider add \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --provider-id "microsoft-qc" \
  --provider-sku "learn-and-develop"
```

### Listar Providers Disponibles

```bash
az quantum offerings list \
  --location $LOCATION \
  --output table
```

---

## 📊 GESTIONAR WORKSPACE

### Ver Workspace

```bash
# Listar workspaces
az quantum workspace list \
  --resource-group $RESOURCE_GROUP \
  --output table

# Ver detalles de workspace
az quantum workspace show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME
```

### Actualizar Workspace

```bash
az quantum workspace update \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --tags env=production project=bioql
```

### Eliminar Workspace

```bash
az quantum workspace delete \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --yes
```

---

## 🔑 CONFIGURAR CREDENCIALES

### Obtener Connection String

```bash
# Ver información de conexión
az quantum workspace show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --query "{id:id, location:location, endpoint:endpoint}" \
  --output json
```

### Guardar Credenciales

```bash
# Crear directorio de configuración
mkdir -p ~/.azure-quantum

# Guardar configuración
cat > ~/.azure-quantum/config.json << EOF
{
  "subscription_id": "$SUBSCRIPTION_ID",
  "resource_group": "$RESOURCE_GROUP",
  "workspace_name": "$WORKSPACE_NAME",
  "location": "$LOCATION"
}
EOF

# Proteger archivo
chmod 600 ~/.azure-quantum/config.json
```

---

## 🐍 INTEGRACIÓN CON PYTHON (BioQL)

### 1. Instalar Azure Quantum SDK

```bash
pip install azure-quantum
pip install qiskit-azure-quantum
```

### 2. Código de Integración BioQL

```python
# bioql/cloud_auth.py - Azure Quantum Integration

from azure.quantum import Workspace
from azure.quantum.qiskit import AzureQuantumProvider
from typing import Optional, Dict, Any
import json
from pathlib import Path

class AzureQuantumAuth:
    """Azure Quantum authentication and workspace management"""

    def __init__(
        self,
        subscription_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        workspace_name: Optional[str] = None,
        location: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        """
        Initialize Azure Quantum authentication.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            workspace_name: Workspace name
            location: Azure region
            config_file: Path to config file (JSON)
        """
        if config_file:
            self._load_config(config_file)
        else:
            self.subscription_id = subscription_id
            self.resource_group = resource_group
            self.workspace_name = workspace_name
            self.location = location

        self.workspace = None
        self.provider = None

    def _load_config(self, config_file: str):
        """Load configuration from file"""
        with open(Path(config_file).expanduser()) as f:
            config = json.load(f)

        self.subscription_id = config.get('subscription_id')
        self.resource_group = config.get('resource_group')
        self.workspace_name = config.get('workspace_name')
        self.location = config.get('location')

    def connect(self) -> Workspace:
        """Connect to Azure Quantum workspace"""
        self.workspace = Workspace(
            subscription_id=self.subscription_id,
            resource_group=self.resource_group,
            name=self.workspace_name,
            location=self.location
        )

        # Get Qiskit provider
        self.provider = AzureQuantumProvider(workspace=self.workspace)

        return self.workspace

    def list_backends(self) -> list:
        """List available backends"""
        if not self.provider:
            self.connect()

        return self.provider.backends()

    def get_backend(self, name: str):
        """Get specific backend"""
        if not self.provider:
            self.connect()

        return self.provider.get_backend(name)


# Ejemplo de uso
if __name__ == "__main__":
    # Opción 1: Desde variables
    auth = AzureQuantumAuth(
        subscription_id="your-subscription-id",
        resource_group="bioql-quantum-rg",
        workspace_name="bioql-quantum-workspace",
        location="eastus"
    )

    # Opción 2: Desde archivo
    auth = AzureQuantumAuth(config_file="~/.azure-quantum/config.json")

    # Conectar
    workspace = auth.connect()

    # Listar backends
    backends = auth.list_backends()
    for backend in backends:
        print(f"Backend: {backend.name()}")

    # Obtener backend específico
    ionq_backend = auth.get_backend("ionq.simulator")

    # Usar con BioQL
    from bioql import quantum
    from qiskit import QuantumCircuit

    # Crear circuito
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    # Ejecutar en Azure Quantum
    job = ionq_backend.run(qc, shots=1024)
    result = job.result()
    print(result.get_counts())
```

---

## 🔧 SCRIPT COMPLETO DE SETUP

### Script Automático: `setup_azure_quantum.sh`

```bash
#!/bin/bash
# setup_azure_quantum.sh - Setup completo de Azure Quantum

set -e

echo "🌐 Azure Quantum Workspace Setup"
echo "================================"

# Variables (Modificar según necesites)
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-}"
RESOURCE_GROUP="bioql-quantum-rg"
WORKSPACE_NAME="bioql-quantum-workspace"
LOCATION="eastus"
STORAGE_ACCOUNT="bioqlquantumstorage$(date +%s)"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función de log
log() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. Verificar Azure CLI
info "Verificando Azure CLI..."
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI no instalado. Instalando..."
    brew install azure-cli
fi
log "Azure CLI instalado"

# 2. Instalar extensión Quantum
info "Instalando extensión Quantum..."
az extension add --name quantum --yes 2>/dev/null || true
log "Extensión Quantum instalada"

# 3. Login
info "Verificando login..."
if ! az account show &> /dev/null; then
    echo "Por favor, haz login en Azure:"
    az login
fi

# Obtener subscription ID si no está definido
if [ -z "$SUBSCRIPTION_ID" ]; then
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
fi

log "Subscription: $SUBSCRIPTION_ID"

# 4. Crear Resource Group
info "Creando resource group..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

log "Resource group creado: $RESOURCE_GROUP"

# 5. Crear Storage Account
info "Creando storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --output none

log "Storage account creado: $STORAGE_ACCOUNT"

# 6. Crear Quantum Workspace
info "Creando Quantum Workspace..."
az quantum workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $WORKSPACE_NAME \
    --location $LOCATION \
    --storage-account "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
    --output none

log "Quantum Workspace creado: $WORKSPACE_NAME"

# 7. Agregar Providers
info "Agregando providers..."

# IonQ
az quantum workspace provider add \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $WORKSPACE_NAME \
    --provider-id "ionq" \
    --provider-sku "pay-as-you-go-cred" \
    --output none || true

# Microsoft QIO
az quantum workspace provider add \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $WORKSPACE_NAME \
    --provider-id "microsoft-qc" \
    --provider-sku "learn-and-develop" \
    --output none || true

log "Providers agregados"

# 8. Guardar configuración
info "Guardando configuración..."
mkdir -p ~/.azure-quantum

cat > ~/.azure-quantum/config.json << EOF
{
  "subscription_id": "$SUBSCRIPTION_ID",
  "resource_group": "$RESOURCE_GROUP",
  "workspace_name": "$WORKSPACE_NAME",
  "location": "$LOCATION",
  "storage_account": "$STORAGE_ACCOUNT"
}
EOF

chmod 600 ~/.azure-quantum/config.json
log "Configuración guardada en ~/.azure-quantum/config.json"

# 9. Mostrar información
echo ""
echo "================================"
echo "✅ Setup Completado!"
echo "================================"
echo "Subscription ID: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo "Workspace: $WORKSPACE_NAME"
echo "Location: $LOCATION"
echo "Storage: $STORAGE_ACCOUNT"
echo ""
echo "📋 Próximos pasos:"
echo "1. Instalar Azure Quantum SDK:"
echo "   pip install azure-quantum qiskit-azure-quantum"
echo ""
echo "2. Usar en Python:"
echo "   from azure.quantum import Workspace"
echo "   workspace = Workspace("
echo "       subscription_id='$SUBSCRIPTION_ID',"
echo "       resource_group='$RESOURCE_GROUP',"
echo "       name='$WORKSPACE_NAME',"
echo "       location='$LOCATION'"
echo "   )"
echo ""
echo "3. Listar backends disponibles:"
echo "   az quantum workspace show -g $RESOURCE_GROUP -w $WORKSPACE_NAME"
echo ""
```

### Hacer ejecutable y correr

```bash
# Hacer ejecutable
chmod +x setup_azure_quantum.sh

# Ejecutar
./setup_azure_quantum.sh
```

---

## 📝 COMANDOS ÚTILES

### Gestión de Workspace

```bash
# Listar todas las ubicaciones disponibles
az quantum workspace list-locations --output table

# Ver quotas
az quantum workspace quotas \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME

# Ver jobs
az quantum job list \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME

# Ver detalles de un job
az quantum job show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --job-id <job-id>
```

### Gestión de Costos

```bash
# Ver uso actual
az consumption usage list \
  --start-date 2025-10-01 \
  --end-date 2025-10-03

# Ver presupuesto
az consumption budget list \
  --resource-group $RESOURCE_GROUP
```

---

## 🔒 SEGURIDAD Y MEJORES PRÁCTICAS

### 1. Usar Variables de Entorno

```bash
# Agregar a ~/.bashrc o ~/.zshrc
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_RESOURCE_GROUP="bioql-quantum-rg"
export AZURE_QUANTUM_WORKSPACE="bioql-quantum-workspace"
export AZURE_QUANTUM_LOCATION="eastus"
```

### 2. Usar Service Principal (Producción)

```bash
# Crear service principal
az ad sp create-for-rbac \
  --name "bioql-quantum-sp" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP

# Guardar credenciales de forma segura
# Usar Azure Key Vault para producción
```

### 3. Limitar Permisos

```bash
# Crear role assignment específico
az role assignment create \
  --assignee <service-principal-id> \
  --role "Quantum Workspace Contributor" \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP
```

---

## 🧪 TESTING

### Test de Conexión

```bash
# Test básico
az quantum workspace show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $WORKSPACE_NAME \
  --query "provisioningState" \
  --output tsv

# Debería retornar: Succeeded
```

### Test con Python

```python
from azure.quantum import Workspace

workspace = Workspace(
    subscription_id="your-subscription-id",
    resource_group="bioql-quantum-rg",
    name="bioql-quantum-workspace",
    location="eastus"
)

# Verificar conexión
print(f"Workspace: {workspace.name}")
print(f"Location: {workspace.location}")

# Listar backends
from azure.quantum.qiskit import AzureQuantumProvider
provider = AzureQuantumProvider(workspace=workspace)

backends = provider.backends()
print(f"\nBackends disponibles: {len(backends)}")
for backend in backends:
    print(f"  - {backend.name()}")
```

---

## 📊 MONITOREO Y LOGS

### Ver Logs de Actividad

```bash
az monitor activity-log list \
  --resource-group $RESOURCE_GROUP \
  --start-time 2025-10-03T00:00:00Z \
  --query "[].{Time:eventTimestamp, Operation:operationName.localizedValue, Status:status.localizedValue}" \
  --output table
```

### Configurar Alertas

```bash
# Crear alerta de costos
az monitor metrics alert create \
  --name quantum-cost-alert \
  --resource-group $RESOURCE_GROUP \
  --scopes /subscriptions/$SUBSCRIPTION_ID \
  --condition "total cost > 100" \
  --description "Alert when quantum costs exceed $100"
```

---

## 🔗 RECURSOS ADICIONALES

- **Documentación Azure Quantum**: https://docs.microsoft.com/azure/quantum/
- **Azure CLI Reference**: https://docs.microsoft.com/cli/azure/quantum
- **Pricing Calculator**: https://azure.microsoft.com/pricing/calculator/
- **Azure Quantum Samples**: https://github.com/microsoft/quantum

---

## ✅ CHECKLIST

- [ ] Azure CLI instalado
- [ ] Extensión Quantum instalada
- [ ] Login en Azure completado
- [ ] Resource Group creado
- [ ] Storage Account creado
- [ ] Quantum Workspace creado
- [ ] Providers configurados
- [ ] Credenciales guardadas
- [ ] SDK de Python instalado
- [ ] Conexión testeada

---

**¡Azure Quantum Workspace listo para usar con BioQL!** 🚀
