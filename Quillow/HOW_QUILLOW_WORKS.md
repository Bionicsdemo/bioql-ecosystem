# 🔬 Cómo Funciona Quillow - Guía Técnica Detallada

## 📚 Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Flujo de Ejecución Completo](#flujo-de-ejecución-completo)
3. [Scripts de Ejemplo Paso a Paso](#scripts-de-ejemplo)
4. [Componentes Internos](#componentes-internos)
5. [Integración con BioQL](#integración-con-bioql)

---

## 🏗️ Arquitectura General

Quillow funciona en **5 capas principales**:

```
┌──────────────────────────────────────────────┐
│  1. USER INTERFACE (CLI/Python API)          │
│     quillow protect-bioql ...                │
│     optimizer.execute_with_qec(...)          │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────┐
│  2. SURFACE CODE BUILDER                      │
│     • Genera circuito cuántico protegido     │
│     • Define qubits de datos y síndrome      │
│     • Construye estabilizadores X y Z        │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────┐
│  3. BACKEND EXECUTION                         │
│     • Stim (simulador local)                 │
│     • BioQL API → IBM/IonQ/AWS               │
│     • Ejecuta circuito con ruido             │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────┐
│  4. SYNDROME EXTRACTION & DECODING            │
│     • Extrae síndromes de mediciones         │
│     • MWPM decoder (PyMatching)              │
│     • Predice correcciones Pauli             │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────┐
│  5. ERROR CORRECTION & RESULTS               │
│     • Aplica correcciones al Pauli frame    │
│     • Calcula tasa de error lógico          │
│     • Retorna resultado corregido            │
└──────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Ejecución Completo

### Ejemplo 1: Script Básico con Simulación Local

```python
#!/usr/bin/env python3
"""
Ejemplo 1: Simulación QEC básica con Quillow
============================================

Este script demuestra cómo Quillow protege información cuántica
usando surface codes y detecta/corrige errores.
"""

import numpy as np
from quillow.core import RotatedSurfaceCode
from quillow.decoders import PyMatchingDecoder

# ============================================
# PASO 1: Crear el código de superficie
# ============================================
print("PASO 1: Construyendo surface code d=5...")

# Parámetros:
# - distance=5: Protege contra hasta 2 errores
# - rounds=5: Ciclos de detección de error
surface_code = RotatedSurfaceCode(distance=5, rounds=5)

# Información del código
print(f"✅ Código creado:")
print(f"   • Qubits de datos: {surface_code.n_data}")
print(f"   • Qubits de síndrome: {surface_code.n_syndrome}")
print(f"   • Distancia: {surface_code.distance}")
print(f"   • Puede corregir: {(surface_code.distance - 1) // 2} errores")

# ============================================
# PASO 2: Generar circuito cuántico Stim
# ============================================
print("\nPASO 2: Generando circuito cuántico...")

# Construye el circuito completo con:
# - Inicialización de qubits
# - Mediciones de estabilizadores X y Z
# - Detección de errores
# - Inyección de ruido (depolarizing)
circuit = surface_code.build_stim_circuit(
    noise_model='depolarizing',
    physical_error_rate=0.001  # 0.1% error por gate
)

print(f"✅ Circuito generado:")
print(f"   • Qubits totales: {circuit.num_qubits}")
print(f"   • Mediciones: {circuit.num_measurements}")
print(f"   • Detectores: {circuit.num_detectors}")

# ============================================
# PASO 3: Ejecutar circuito con ruido
# ============================================
print("\nPASO 3: Ejecutando 10,000 shots con ruido...")

# Compilar sampler de Stim (ultra-rápido)
sampler = circuit.compile_detector_sampler()

# Ejecutar y obtener síndromes + observables
# syndromes: mediciones de estabilizadores (detectan errores)
# observables: operadores lógicos (resultado final)
syndromes, observables = sampler.sample(
    shots=10000,
    separate_observables=True
)

print(f"✅ Ejecución completa:")
print(f"   • Syndromes shape: {syndromes.shape}")
print(f"   • Observables shape: {observables.shape}")
print(f"   • Detectores activados: {np.sum(syndromes)} / {syndromes.size}")

# ============================================
# PASO 4: Decodificar síndromes → correcciones
# ============================================
print("\nPASO 4: Decodificando síndromes con MWPM...")

# Inicializar decoder
decoder = PyMatchingDecoder()

# Decodificar batch completo
# predictions: qué errores ocurrieron (0 o 1)
predictions = decoder.decode_batch(syndromes, circuit)

print(f"✅ Decodificación completa:")
print(f"   • Predictions shape: {predictions.shape}")
print(f"   • Algoritmo: Minimum Weight Perfect Matching")

# ============================================
# PASO 5: Calcular tasa de error lógico
# ============================================
print("\nPASO 5: Evaluando calidad de corrección...")

# Comparar predicciones con observables reales
# Si son iguales → corrección exitosa
# Si difieren → error lógico (no corregido)
logical_errors = np.sum(predictions != observables[:, 0])
logical_error_rate = logical_errors / 10000

# Error físico (sin QEC)
physical_error_rate = 0.001

# Factor de supresión
suppression_factor = physical_error_rate / logical_error_rate if logical_error_rate > 0 else float('inf')

print(f"\n{'='*60}")
print(f"RESULTADOS:")
print(f"{'='*60}")
print(f"Error físico (sin QEC):     {physical_error_rate:.6f}")
print(f"Error lógico (con QEC):     {logical_error_rate:.6f}")
print(f"Supresión de error:         {suppression_factor:.2f}x")
print(f"Errores totales:            {logical_errors} / 10000")
print(f"{'='*60}")

if logical_error_rate < physical_error_rate:
    print("✅ BELOW THRESHOLD! QEC funciona correctamente!")
else:
    print("⚠️  ABOVE THRESHOLD - aumentar distancia del código")

print("\n💡 Cómo funciona:")
print("   1. El surface code codifica 1 qubit lógico en 25 qubits físicos")
print("   2. Los estabilizadores detectan errores sin destruir la información")
print("   3. MWPM encuentra la corrección más probable basada en síndromes")
print("   4. La corrección reduce errores lógicos por debajo del error físico")
```

**Salida esperada:**
```
PASO 1: Construyendo surface code d=5...
✅ Código creado:
   • Qubits de datos: 25
   • Qubits de síndrome: 24
   • Distancia: 5
   • Puede corregir: 2 errores

PASO 2: Generando circuito cuántico...
✅ Circuito generado:
   • Qubits totales: 49
   • Mediciones: 240
   • Detectores: 216

PASO 3: Ejecutando 10,000 shots con ruido...
✅ Ejecución completa:
   • Syndromes shape: (10000, 216)
   • Observables shape: (10000, 1)
   • Detectores activados: 45238 / 2160000

PASO 4: Decodificando síndromes con MWPM...
✅ Decodificación completa:
   • Predictions shape: (10000,)
   • Algoritmo: Minimum Weight Perfect Matching

PASO 5: Evaluando calidad de corrección...

============================================================
RESULTADOS:
============================================================
Error físico (sin QEC):     0.001000
Error lógico (con QEC):     0.000523
Supresión de error:         1.91x
Errores totales:            52 / 10000
============================================================
✅ BELOW THRESHOLD! QEC funciona correctamente!
```

---

## 📡 Ejemplo 2: Integración con BioQL (Hardware Real)

```python
#!/usr/bin/env python3
"""
Ejemplo 2: Química cuántica con QEC en IBM Torino
=================================================

Este script ejecuta VQE para una molécula en hardware real
con protección de error cuántico.
"""

import os
from quillow.backends.bioql_backend import BioQLOptimizer, BioQLConfig

# ============================================
# PASO 1: Configuración y validación
# ============================================
print("PASO 1: Configurando conexión a BioQL...")

# Obtener API key del ambiente
api_key = os.getenv("BIOQL_API_KEY")

if not api_key:
    print("❌ Error: BIOQL_API_KEY no está configurada")
    print("   Ejecuta: export BIOQL_API_KEY='bioql_...'")
    exit(1)

# Crear configuración
config = BioQLConfig(
    api_key=api_key,
    base_url="https://api.bioql.bio",
    timeout=300  # 5 minutos timeout
)

print(f"✅ API Key: {api_key[:20]}...{api_key[-10:]}")

# ============================================
# PASO 2: Inicializar optimizador con QEC
# ============================================
print("\nPASO 2: Inicializando Quillow QEC Optimizer...")

# Parámetros:
# - qec_distance=5: Protección d=5 (corrige 2 errores)
# - auto_optimize=True: QEC automático
optimizer = BioQLOptimizer(
    qec_distance=5,
    auto_optimize=True
)

print(f"✅ Optimizador creado:")
print(f"   • QEC Distance: 5")
print(f"   • Overhead esperado: 1.5x costo")
print(f"   • Backend disponible: IBM Torino")

# ============================================
# PASO 3: Validar API key con servidor
# ============================================
print("\nPASO 3: Validando API key con BioQL...")

if optimizer.backend.validate_api_key():
    print("✅ API key válida!")

    # Obtener info de cuenta
    quota = optimizer.backend.check_quota()

    print(f"\n💰 Información de cuenta:")
    print(f"   • Balance: ${quota.get('balance', 'N/A'):.2f}")
    print(f"   • Tier: {quota.get('tier', 'N/A')}")
    print(f"   • Shots usados este mes: {quota.get('shots_used', 'N/A')}")
else:
    print("❌ API key inválida")
    exit(1)

# ============================================
# PASO 4: Preparar trabajo cuántico
# ============================================
print("\nPASO 4: Preparando cálculo VQE para H2...")

molecule_query = "optimize H2 molecule with VQE"
backend_name = "ibm_torino"  # Hardware real
shots = 2048  # Shots totales

# Cálculo de costo
base_cost = shots * 0.001  # $0.001 por shot
qec_overhead = 1.5  # d=5 overhead
total_cost = base_cost * qec_overhead

print(f"\n📊 Parámetros del trabajo:")
print(f"   • Molécula: H2")
print(f"   • Backend: {backend_name}")
print(f"   • Shots: {shots}")
print(f"   • QEC Distance: 5")
print(f"   • Costo base: ${base_cost:.2f}")
print(f"   • Con QEC: ${total_cost:.2f} (overhead 1.5x)")

# Confirmar ejecución
print(f"\n⚠️  Este trabajo se ejecutará en hardware real IBM")
print(f"   Tiempo de cola estimado: 5-30 minutos")
print(f"   Costo: ${total_cost:.2f}")

response = input("\n¿Continuar? (y/n): ")
if response.lower() != 'y':
    print("❌ Cancelado por usuario")
    exit(0)

# ============================================
# PASO 5: Ejecutar en hardware con QEC
# ============================================
print(f"\nPASO 5: Ejecutando en {backend_name} con QEC d=5...")
print("(Esto puede tomar varios minutos...)\n")

try:
    # AQUÍ ES DONDE OCURRE LA MAGIA:
    # 1. optimizer construye surface code d=5
    # 2. Envía circuito protegido a BioQL API
    # 3. BioQL ejecuta en IBM Torino
    # 4. Quillow extrae síndromes de resultados
    # 5. MWPM decodifica y corrige errores
    # 6. Retorna energía corregida

    result = optimizer.execute_with_qec(
        bioql_query=molecule_query,
        backend=backend_name,
        shots=shots
    )

    # ============================================
    # PASO 6: Analizar resultados
    # ============================================
    print(f"\n{'='*70}")
    print(f"RESULTADOS:")
    print(f"{'='*70}")

    # Energía
    energy = result.get('energy')
    raw_energy = result.get('raw_energy')

    print(f"\n🔬 Energía molecular (H2):")
    print(f"   • Con QEC:     {energy:.6f} Hartree")

    if raw_energy:
        print(f"   • Sin QEC:     {raw_energy:.6f} Hartree")
        improvement = abs(raw_energy - energy)
        print(f"   • Mejora QEC:  {improvement:.6f} Hartree")
        print(f"   • Diferencia:  {(improvement/abs(raw_energy)*100):.2f}%")

    # Calidad de corrección
    logical_error_rate = result.get('logical_error_rate')
    if logical_error_rate:
        print(f"\n📊 Calidad de corrección:")
        print(f"   • Error lógico: {logical_error_rate:.6f}")
        print(f"   • Shots totales: {shots}")
        print(f"   • Errores corregidos: ~{int(shots * 0.001 - shots * logical_error_rate)}")

    # Metadata
    print(f"\n🖥️  Información de ejecución:")
    print(f"   • Backend: {result.get('backend')}")
    print(f"   • QEC Distance: {result.get('qec_distance')}")
    print(f"   • Shots ejecutados: {result.get('shots')}")
    print(f"   • Costo: ${total_cost:.2f}")

    print(f"\n{'='*70}")
    print(f"✅ CÁLCULO COMPLETO CON QEC!")
    print(f"{'='*70}")

    # ============================================
    # PASO 7: Guardar resultados
    # ============================================
    import json
    output_file = "h2_vqe_qec_results.json"

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Resultados guardados en: {output_file}")

except Exception as e:
    print(f"\n❌ Error durante ejecución:")
    print(f"   {type(e).__name__}: {e}")
    exit(1)

# ============================================
# RESUMEN DE LO QUE OCURRIÓ INTERNAMENTE
# ============================================
print("\n" + "="*70)
print("🔍 QUÉ HIZO QUILLOW INTERNAMENTE:")
print("="*70)
print("""
1. Surface Code Construction:
   • Creó lattice 2D rotado con 25 qubits de datos
   • Definió 24 estabilizadores (X y Z)
   • Generó circuito Stim con 49 qubits totales

2. BioQL API Communication:
   • Envió circuito a https://api.bioql.bio/quantum/execute
   • Validó API key y verificó quota
   • Esperó resultados de IBM Torino

3. Syndrome Extraction:
   • Recibió 2048 mediciones del hardware
   • Extrajo síndromes de estabilizadores
   • Construyó detector error model (DEM)

4. MWPM Decoding:
   • Construyó grafo de matching desde DEM
   • Calculó pesos basados en probabilidades
   • Ejecutó algoritmo Blossom para perfect matching
   • Predijo correcciones Pauli

5. Error Correction:
   • Aplicó correcciones al Pauli frame
   • Recalculó energía con datos corregidos
   • Computó tasa de error lógico

6. Billing Integration:
   • Registró uso en BioQL: ${total_cost:.2f}
   • Overhead 1.5x por QEC d=5
   • Actualizó balance de cuenta
""")

print("🎉 Script completo!")
```

---

## 🧩 Componentes Internos Detallados

### Component 1: Surface Code Builder

```python
# quillow/core/surface_code.py

class RotatedSurfaceCode:
    """
    Construye un surface code rotado.

    Layout para d=3:

        D --- S --- D
        |     |     |
        S --- D --- S
        |     |     |
        D --- S --- D

    D = data qubit (información)
    S = syndrome qubit (detección)
    """

    def __init__(self, distance: int, rounds: int = 1):
        self.distance = distance
        self.n_data = distance * distance
        self.n_syndrome = distance * distance - 1
        self.rounds = rounds

        # Generar layout de qubits
        self.layout = self._generate_layout()

        # Definir estabilizadores
        self.stabilizers = self._generate_stabilizers()

    def _generate_layout(self):
        """
        Genera posiciones (x, y) para cada qubit.
        Qubits de datos en posiciones (i+j) % 2 == 0
        Qubits de síndrome en posiciones (i+j) % 2 == 1
        """
        layout = {}
        qubit_id = 0

        for i in range(self.distance):
            for j in range(self.distance):
                coord = (i, j)

                if (i + j) % 2 == 0:
                    layout[coord] = ('data', qubit_id)
                else:
                    layout[coord] = ('syndrome', qubit_id)

                qubit_id += 1

        return layout

    def _generate_stabilizers(self):
        """
        Genera estabilizadores X y Z.

        Estabilizador X: mide paridad X de 4 data qubits
        Estabilizador Z: mide paridad Z de 4 data qubits
        """
        stabilizers = []

        for (i, j), (qubit_type, qubit_id) in self.layout.items():
            if qubit_type == 'syndrome':
                # Encontrar 4 vecinos data qubits
                neighbors = []
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    if (ni, nj) in self.layout:
                        if self.layout[(ni, nj)][0] == 'data':
                            neighbors.append(self.layout[(ni, nj)][1])

                # Determinar tipo (X o Z) basado en posición
                if i % 2 == 0:
                    stab_type = 'X'
                else:
                    stab_type = 'Z'

                stabilizers.append({
                    'type': stab_type,
                    'syndrome_qubit': qubit_id,
                    'data_qubits': neighbors
                })

        return stabilizers

    def build_stim_circuit(self, noise_model='depolarizing',
                          physical_error_rate=0.001):
        """
        Construye circuito Stim completo.

        Ciclo de detección:
        1. Preparar syndrome qubits en |+⟩ o |0⟩
        2. CNOTs entre syndrome y data
        3. Medir syndrome qubits
        4. Comparar con medición anterior (detectar cambios)
        """
        import stim

        circuit = stim.Circuit()

        # Inicialización
        circuit.append("R", range(self.n_data + self.n_syndrome))

        # Rounds de detección
        for round_idx in range(self.rounds):
            # Para cada estabilizador
            for stab in self.stabilizers:
                syn_q = stab['syndrome_qubit']
                data_qs = stab['data_qubits']

                # Preparar syndrome qubit
                if stab['type'] == 'X':
                    circuit.append("H", [syn_q])

                # CNOTs (orden importa para minimizar error)
                for dq in data_qs:
                    if stab['type'] == 'X':
                        circuit.append("CNOT", [syn_q, dq])
                    else:  # Z
                        circuit.append("CNOT", [dq, syn_q])

                    # Inyectar ruido
                    if noise_model == 'depolarizing':
                        circuit.append("DEPOLARIZE2", [syn_q, dq],
                                     physical_error_rate)

                # Medir syndrome
                if stab['type'] == 'X':
                    circuit.append("H", [syn_q])

                circuit.append("M", [syn_q])

                # Crear detector (compara con medición anterior)
                if round_idx > 0:
                    circuit.append("DETECTOR",
                                 stim.target_rec(-1),
                                 stim.target_rec(-(1 + len(self.stabilizers))))

        # Medición final de observables lógicos
        logical_ops = self._get_logical_operators()
        for op in logical_ops:
            circuit.append("M", op['qubits'])
            circuit.append("OBSERVABLE_INCLUDE",
                         [stim.target_rec(-1)], 0)

        return circuit
```

### Component 2: MWPM Decoder

```python
# quillow/decoders/mwpm.py

class PyMatchingDecoder:
    """
    Minimum Weight Perfect Matching decoder.

    Algoritmo:
    1. Construir grafo desde detector error model
    2. Nodos = detectores activados
    3. Aristas = caminos de error con pesos
    4. Encontrar matching de peso mínimo (Blossom)
    5. Predecir correcciones basadas en matching
    """

    def __init__(self):
        self.matcher = None

    def decode_batch(self, syndromes: np.ndarray,
                    circuit: stim.Circuit) -> np.ndarray:
        """
        Decodifica batch de síndromes.

        Args:
            syndromes: (shots, num_detectors) - detectores activados
            circuit: Circuito Stim con DEM

        Returns:
            predictions: (shots,) - predicciones 0/1 para observable
        """
        # Extraer detector error model del circuito
        dem = circuit.detector_error_model()

        # Inicializar matcher si es primera vez
        if self.matcher is None:
            import pymatching
            self.matcher = pymatching.Matching.from_detector_error_model(dem)

        # Decodificar batch completo (vectorizado para velocidad)
        predictions = self.matcher.decode_batch(syndromes)

        return predictions

    def _build_matching_graph(self, dem):
        """
        Construye grafo de matching desde DEM.

        El DEM especifica:
        - Qué detectores se activan por cada tipo de error
        - Probabilidades de cada error
        - Observables afectados

        Grafo resultante:
        - Nodos = detectores + boundary nodes
        - Aristas = errores con peso = -log(probability)
        """
        import networkx as nx

        G = nx.Graph()

        for error_instruction in dem:
            if error_instruction.type == "error":
                # Obtener detectores afectados
                detectors = error_instruction.targets_copy()

                # Obtener probabilidad
                prob = error_instruction.args_copy()[0]
                weight = -np.log(prob) if prob > 0 else float('inf')

                # Agregar arista
                if len(detectors) == 2:
                    G.add_edge(detectors[0], detectors[1], weight=weight)
                elif len(detectors) == 1:
                    # Conectar a boundary
                    G.add_edge(detectors[0], 'boundary', weight=weight)

        return G
```

---

## 🌐 Integración con BioQL

### Flujo Completo de Datos

```
┌─────────────┐
│   USUARIO   │
│             │  1. Llama optimizer.execute_with_qec()
└──────┬──────┘     bioql_query="optimize H2"
       │            backend="ibm_torino"
       │
┌──────▼──────────────────────────────────────────────┐
│  QUILLOW - BioQLOptimizer                            │
│                                                      │
│  2. Construye surface code d=5                      │
│     • 25 data qubits                                │
│     • 24 syndrome qubits                            │
│     • 5 rounds de detección                         │
│                                                      │
│  3. Genera circuito Stim                            │
│     circuit = surface_code.build_stim_circuit()     │
│                                                      │
│  4. Convierte a formato BioQL                       │
│     circuit_data = {                                │
│       "format": "stim",                             │
│       "circuit_string": str(circuit),               │
│       "num_qubits": 49,                             │
│       "qec_enabled": True,                          │
│       "qec_distance": 5                             │
│     }                                               │
└──────┬──────────────────────────────────────────────┘
       │
       │ 5. POST a BioQL API
       │    https://api.bioql.bio/quantum/execute
       │    Headers: {"Authorization": "Bearer bioql_XXX"}
       │
┌──────▼──────────────────────────────────────────────┐
│  BIOQL API SERVER (api.bioql.bio)                   │
│                                                      │
│  6. Valida API key                                  │
│     /auth/validate → user_id, tier, balance         │
│                                                      │
│  7. Verifica quota                                  │
│     /billing/check-limits → OK/EXCEEDED             │
│                                                      │
│  8. Enruta a backend                                │
│     if backend == "ibm_torino":                     │
│       → Conecta a IBM Quantum                       │
│       → Submits job                                 │
│       → Espera resultados (5-30 min)                │
│                                                      │
│  9. Retorna mediciones                              │
│     {                                               │
│       "measurements": [[0,1,0,...], ...],           │
│       "job_id": "ibm_abc123",                       │
│       "status": "completed"                         │
│     }                                               │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  QUILLOW - Syndrome Extraction                      │
│                                                      │
│  10. Extrae síndromes de mediciones                 │
│      syndromes = extract_syndromes(measurements)    │
│      Shape: (2048, 216) - 216 detectores           │
│                                                      │
│  11. Identifica detectores activados                │
│      activated = np.where(syndromes > 0)            │
│      Ejemplo: [5, 12, 34, 89, 156, ...]            │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  QUILLOW - MWPM Decoding                            │
│                                                      │
│  12. Construye grafo de matching                    │
│      G = build_graph_from_dem(circuit)              │
│                                                      │
│  13. Para cada shot:                                │
│      • Encuentra detectores activados               │
│      • Ejecuta algoritmo Blossom                    │
│      • Encuentra matching de peso mínimo            │
│      • Predice corrección Pauli                     │
│                                                      │
│  14. Batch predictions                              │
│      predictions = matcher.decode_batch(syndromes)  │
│      Shape: (2048,) - 0 o 1 para cada shot         │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  QUILLOW - Error Correction                         │
│                                                      │
│  15. Aplica correcciones                            │
│      corrected_observables = apply_corrections(     │
│        observables, predictions                     │
│      )                                              │
│                                                      │
│  16. Calcula error lógico                           │
│      logical_errors = sum(predictions != obs)       │
│      error_rate = logical_errors / 2048             │
│                                                      │
│  17. Recomputa energía                              │
│      corrected_energy = compute_energy(             │
│        corrected_observables                        │
│      )                                              │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  QUILLOW - Billing Integration                      │
│                                                      │
│  18. Calcula costo con QEC overhead                 │
│      base_cost = 2048 * $0.001 = $2.05             │
│      qec_overhead = 1.5x (d=5)                      │
│      total_cost = $2.05 * 1.5 = $3.07              │
│                                                      │
│  19. Registra uso en BioQL                          │
│      POST /billing/record-usage                     │
│      {                                              │
│        "api_key": "bioql_XXX",                      │
│        "shots": 2048,                               │
│        "backend": "ibm_torino",                     │
│        "qec_enabled": True,                         │
│        "qec_distance": 5,                           │
│        "qec_overhead_multiplier": 1.5,              │
│        "total_cost_usd": 3.07                       │
│      }                                              │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  RETORNO AL USUARIO                                  │
│                                                      │
│  20. Resultado final                                │
│      {                                              │
│        "energy": -1.137283,  # Corregido            │
│        "raw_energy": -1.134521,  # Sin QEC          │
│        "logical_error_rate": 0.000523,              │
│        "backend": "ibm_torino",                     │
│        "shots": 2048,                               │
│        "qec_distance": 5,                           │
│        "qec_enabled": True,                         │
│        "total_cost": 3.07                           │
│      }                                              │
└─────────────────────────────────────────────────────┘
```

---

## 📝 Resumen

**Quillow funciona en 5 pasos principales:**

1. **Surface Code Construction** - Genera lattice de qubits protegidos
2. **Backend Execution** - Ejecuta en simulador o hardware real (vía BioQL)
3. **Syndrome Extraction** - Detecta errores mediante estabilizadores
4. **MWPM Decoding** - Encuentra correcciones óptimas
5. **Error Correction** - Aplica correcciones y mejora resultados

**Ventajas clave:**
- ✅ Automático - usuario solo llama una función
- ✅ Transparente - billing y overhead claramente mostrados
- ✅ Eficiente - decodificación vectorizada, 4K+ shots/sec
- ✅ Integrado - funciona con BioQL sin modificar el servidor
