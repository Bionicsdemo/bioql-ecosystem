# Pendiente: ejecutar en GPU y cuántico cuando vuelva Modal

> Anotado el 2026-09-29 a petición del usuario. Este fichero existe porque los
> almacenes de memoria de la sesión están bloqueados por permisos; el repo es el
> sitio que sí persiste.

## El bloqueo

El workspace de Modal está **deshabilitado**:

```
modal: ConflictError: workspace ac-zVHXKkD32vUUIhyl2OGFgJ is disabled
```

Brev, la segunda ruta de `modal_compute_layer`, figura como `not usable (off)`.
Entre las dos se cae todo el cómputo remoto: `admet_sota`, `fold_protein`,
`fold_complex`, `mmgbsa_ensemble`, y la ruta EWF-SQD de `modal_ewf_sqd.py`, que
es donde vive el método completo del paper de Cleveland Clinic / RIKEN
(arXiv:2512.17130).

Esto no afecta solo a macrociclos: ADMET está caído para todos los pipelines.

## La orden

**El usuario dará la orden explícita de probar todo lo pendiente y ejecutarlo en
GPU y en cuántico cuando Modal se recupere y haya cuántico disponible.** Hasta
entonces, nada de esto se ejecuta por iniciativa propia.

«De manera responsable», tal como lo pidió, significa:

- Empezar por el simulador, nunca directamente por hardware.
- Medir el coste de **una** unidad antes de lanzar el lote.
- Los minutos de IBM Heron son escasos: no se suben sin que él lo pida en esa
  corrida concreta.
- `allow_qpu` y `allow_cudaq` siguen en `False` por defecto y llegan desde la
  petición, no desde el código. Lo que se usó queda escrito en el JSON al lado
  del número, para que un resultado de simulador no pueda leerse como uno de
  hardware.

## Qué está esperando, concretamente

| Qué | Dónde | Estado hoy |
|---|---|---|
| ADMET | `stages.6_admet` | declara su razón, no da números |
| Afinidad MM-GBSA | `stages.10_docking.affinity` | el informe dice que no hay afinidad y por qué |
| Clusters duros a SQD | `ewf_embedding.hard_clusters()` | listados con sus orbitales activos; hoy resueltos con CCSD |
| EWF + SQD en A100 | `modal_ewf_sqd.ewf_multifragment` | la ruta del paper completa, sin tocar |

## EWF en CPU: lento a propósito, NO se optimiza

Corrida medida el 2026-09-29 sobre el macrociclo de 8 residuos
(`F-G-K-L-A-W-T-S`), 126 átomos, 382 funciones de base, fragmentado por
residuo:

| | |
|---|---|
| E(RHF) | −2957,739393 Ha (99 s) |
| E(EWF) | −2961,828146 Ha |
| Correlación | −4,088754 Ha = −2 566 kcal/mol |
| Fragmentos | 8, uno por residuo |
| Tiempo EWF | 4 826 s (1 h 20 min) |
| Orbitales activos por cluster | 116, 96, 91, 87, 75, 65, 57, 45 |
| Clusters duros (>6 orbitales) | **8 de 8** |

Los ocho fragmentos los resolvió CCSD emitiendo, en cada uno,
`at least one diagnostic indicates that CCSD is not adequate`. Es decir:
el propio cálculo identificó dónde hace falta cuántico, sobre esta molécula
y fragmento a fragmento. No es una conjetura del pipeline.

**DECISIÓN DEL USUARIO (2026-09-29): esa hora y veinte NO es un problema a
arreglar.** Esto no debe terminar corriendo en CPU — se va a escalar a
cuántico real y a GPU. Por ahora se deja como está.

Consecuencia práctica: **no** poner topes de átomos en `4c_ewf`, **no**
optimizar la fragmentación para CPU, **no** cambiar el solver por uno más
barato. Todo eso sería trabajo tirado, y además taparía la señal útil —
que los ocho clusters salgan marcados como duros es exactamente lo que
justifica subirlos a SQD.

Nota de tamaño para cuando llegue el momento: el cluster mayor tiene 116
orbitales activos ≈ 232 qubits, por encima de los 156 de un Heron r2. Los
de 45–65 orbitales (90–130 qubits) sí entran. Apretar el baño para bajar
los mayores será una decisión de método, no de presupuesto.

## Por qué importa no rellenarlo mientras tanto

Todo eso ya está cableado y **declarando su ausencia** con `available: False` y
la causa escrita. El día que Modal vuelva, el mismo código empieza a dar valores
sin tocar nada.

Lo que no hay que hacer es tapar esos huecos con estimaciones, valores por
defecto o números plausibles. La diferencia entre «no se midió» y «se midió y
salió bien» es justo la que un dossier no puede permitirse borrar, y es la razón
de que estos huecos estén escritos y no escondidos.

MOLEVERA / BIOQL
