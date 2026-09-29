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

## Por qué importa no rellenarlo mientras tanto

Todo eso ya está cableado y **declarando su ausencia** con `available: False` y
la causa escrita. El día que Modal vuelva, el mismo código empieza a dar valores
sin tocar nada.

Lo que no hay que hacer es tapar esos huecos con estimaciones, valores por
defecto o números plausibles. La diferencia entre «no se midió» y «se midió y
salió bien» es justo la que un dossier no puede permitirse borrar, y es la razón
de que estos huecos estén escritos y no escondidos.

MOLEVERA / BIOQL
