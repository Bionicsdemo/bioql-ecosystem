# F0 — Macrociclos como pipeline nº 9 de BioQL

Propuesta para revisión. **Sin código todavía.** Anula el F0 anterior (repo aparte).

---

## 1. Lo que se verificó, no se supuso

### Cómputo disponible — medido hoy

| Ruta | Estado | Verificado con |
|---|---|---|
| **Modal GPU** `fold_complex` (Boltz-2) | **VIVO** | `Cls.from_name(...).hydrate()` |
| **Modal GPU** `fold_protein` (ESMFold2) | **VIVO** | ídem |
| **Modal GPU** `quantum_gpu` → `cudaq_statevector` | **VIVO** | ídem — **aquí corre el cuántico** |
| **Modal GPU** `mmgbsa_ensemble` | **VIVO** | ídem |
| **Modal GPU** `admet_sota` | **VIVO** | ídem |
| Modal `bioql-lddm` (diseño 3D en bolsillo) | **MUERTO** | app no existe en `main` |
| Protenix / Complexa | **MUERTO como los llama el backend** | el endpoint HTTP da 404 «workspace disabled» |
| Brev | **APAGADO** | `BIOQL_BREV_URL` sin definir |
| Local | M1 Pro · 8 cores · 16 GB · **sin CUDA** | `sysctl`, `torch` |
| Cuántico local | qiskit 2.4.1 · Aer 0.17.2 · IBM runtime 0.47 · credencial presente · **cudaq ausente** | `importlib.metadata` |
| xtb 6.7.1 · pyscf 2.13 · block2 | **operativos** | `xtb_engine.capabilities()` |

**Matiz que importa sobre Protenix:** la *clase* Modal hidrata, pero el backend la llama por su
URL HTTP, y esa URL vive en un workspace deshabilitado. Así que está muerta *como se usa*.
Boltz-2 (`fold_complex`, vivo) es el sustituto natural.

### Química de macrociclos en BioQL: **cero**

Busqué en los 734 ficheros de `src/backend/`. No existe ninguna función que cierre un anillo:
ni head-to-tail, ni lactama sidechain→backbone, ni staple RCM, ni disulfuro, ni tioéter, ni triazol.

- `mutation_operators.py:165` `'lactam_cyclization'` — entrada de diccionario **sin
  `smarts_match`/`smarts_replace`**, a diferencia de sus vecinos. Declarada, no implementada.
- `iterative_optimizer.py:1125` `strategy == "staple"` — **no hace un staple**: inserta una `K`
  y una `E` en posiciones i, i+4 de la cadena de texto.
- El resto de menciones a «macrocycle» son **clasificadores por descriptores**
  (`MW>800 y ≥3 anillos`), no constructores.

Conviene decirlo por delante: **no estamos envolviendo código existente, estamos escribiendo la
química que falta.**

---

## 2. Los cinco huecos que definen el trabajo

| # | Hueco | Estado actual | Tamaño |
|---|---|---|---|
| H1 | **Ciclación** | inexistente | grande — es el corazón |
| H2 | **Secuencia → estructura química** | todo usa `Chem.MolFromSequence`, que **no puede** expresar macrociclo, N-metilación, D-aa ni residuos no naturales | grande — constructor propio por residuos/HELM |
| H3 | **Confórmeros de macrociclo** | `generate_conformers` usa ETKDGv3 plano; el gancho `_is_peptide`/`_cap_conformers` existe, la lógica no | medio — `useMacrocycleTorsions=True` + xtb |
| H4 | **bRo5** | **no existe como filtro**, solo prosa de informe. El único Lipinski real es `MW 200–600` — **descalificaría todos tus macrociclos** | pequeño pero crítico |
| H5 | **Co-plegado péptido:proteína** | Protenix/Complexa caídos | medio — migrar a Boltz-2 |

---

## 3. Lo que se reutiliza tal cual (es mucho)

`docking_screening_engine` (Vina con escritura propia de PDBQT, sin AutoDockTools) ·
`induced_fit_docking` (ensemble de receptores, bolsillos crípticos vía fpocket) ·
`mmgbsa_ligand_engine` + `modal_mmgbsa_ensemble` (local y GPU) ·
`peptide_developability_suite` (carga, momento hidrofóbico, CPP, hemólisis, vida media) ·
`structural_alerts` (PAINS) · `synthesizability` (SA/NP/SC + retrosíntesis AiZynth real) ·
`xtb_engine` · `disease_target_resolver` (enfermedad→UniProt→PDB con filtro de bolsillo) ·
`optimization_scoring` — **que ya tiene rama `compound_class == 'macrocycle'`** ·
`quantum_weight_optimizer` — que ya define pesos para `'macrocycle'`.

El patrón a copiar es `affinity_funnel.run_funnel()`: QED → Vina → MM-GBSA → ADMET → decisión.

---

## 4. El 60 / 40 — dónde el cuántico hace falta de verdad

Este proyecto tiene historial documentado de *quantum-washing* (19 fabricaciones corregidas).
Así que lo planteo al revés de como se suele: **primero dónde el cuántico NO pinta nada.**

### Donde sería decoración — y no se usa

Scores de docking (empíricos, clásicos) · descriptores TPSA/cLogP/PAINS · generación de
secuencia · detección de bolsillo · filtros bRo5. Meter cuántico ahí es teatro.

### Donde el cuántico sí decide — las cuatro plazas

**Q1 · Ranking energético de confórmeros — la plaza fuerte, y además el cuello de botella.**
Lo que decide si un macrociclo funciona es la *población de confórmeros*: red de puentes de H
intramoleculares (que gobierna la permeabilidad), equilibrio cis/trans de amidas N-metiladas,
tensión transanular. MMFF94s es malo en las tres. Espacio activo alrededor de la región
amida/puente-H → SQD/VQE en `quantum_gpu`.

> **El encuadre honesto ya está probado en este repo, en NIR:** el error absoluto fue 1,348 eV
> contra una puerta de 0,059 eV (23× demasiado), pero el **diferencial** entre sistemas
> emparentados bajó a 0,08 eV — factor de cancelación 16,8. El ranking de confórmeros es el
> régimen diferencial ideal: misma molécula, mismos átomos, mismo espacio activo, solo cambia la
> geometría. **Solo se emiten diferencias. Nunca energías absolutas.**

**Q2 · Barrera cis/trans de amida N-metilada.** La N-metilación es la herramienta principal de
permeabilidad en macrociclos, y el estado de transición tiene carácter multireferencial.
`quantum_reactivity_gate.py` ya calcula ese carácter — **es el que decide qué pares de
confórmeros se ganan el cuántico.** Eso es «ahí donde se necesitan» hecho ejecutable, no una cuota.

**Q3 · Química de la ciclación por disulfuro y tioéter.** El propio gate ya declara
*«disulfide — quantum-relevant in the S–S redox cleavage TS, not at rest»*. Para ciclación por
S–S o tioéter, y para la responsabilidad de oxidación de Cys, el TS es genuinamente
multireferencial.

**Q4 · QAOA/QUBO para selección de subconjunto diverso.** Ya existe el precedente
(`quantum_peptide_design_complete`, `qsurface_dock` con QAP). **Etiqueta obligatoria:
combinatorio, no ventaja cuántica** — a estos tamaños un solver clásico empata o gana.

### El 60/40 como presupuesto medido, no como adorno

El `ExecutionPlan` estima `gpu_seconds` y `quantum_seconds`; el `dry-run` enseña el reparto; el
manifiesto registra **planeado vs conseguido**. Si para una petición concreta el cuántico no
llega al 40% honestamente —porque ningún par de confórmeros pasa el gate de multireferencia—
**el plan lo dice en vez de rellenar con cálculos decorativos**. Un 40% alcanzado metiendo VQE
donde no hace falta sería exactamente el fallo que este repo ya pagó una vez.

Triaje, porque no se puede correr SQD sobre 1000 × 500 confórmeros: lo clásico/GPU hace el
grueso (generar, embeber, ensemble, dock, score) y el cuántico entra solo en el top-K de
candidatos × sus confórmeros competidores, y solo donde el gate MR lo justifica.

---

## 5. Arquitectura de integración

```
src/backend/
├── macrocycle_pipeline.py        run_macrocycle(data) -> dict
│                                 register_macrocycle_routes(app)   ← /api/pipeline/macrocycle
├── macrocycle_builder.py     H1+H2  ciclación real + secuencia→SMILES/HELM por residuos
├── macrocycle_conformers.py  H3     ETKDGv3(useMacrocycleTorsions) + xtb + convergencia
├── macrocycle_filters.py     H4     bRo5 de verdad + PSA dependiente de confórmero
├── macrocycle_quantum.py     Q1-Q4  triaje por gate MR → SQD/VQE diferencial en quantum_gpu
└── artifact_engine/models/macrocycle.py            ← el modelo nº 9
```

Reutiliza por import: `induced_fit_docking`, `docking_screening_engine`, `mmgbsa_ligand_engine`,
`peptide_developability_suite`, `structural_alerts`, `synthesizability`, `xtb_engine`,
`quantum_reactivity_gate`, `disease_target_resolver`, `modal_compute_layer`.

### Alta en la plataforma — 10 pasos verificados

| # | Fichero | Qué |
|---|---|---|
| 1 | `macrocycle_pipeline.py` | `register_macrocycle_routes(app)` que llame a **`streaming_pipeline_response`** (obligatorio: da el `ps-<12hex>`, audit 21 CFR, post-etapas) |
| 2 | `script_executor_server.py` ~32394 | añadir al bucle `for _mod, _fn, _label in [...]` |
| 3 | `script_executor_server.py:33115` | `direct_map` → aparece en `/api/tools/registry` |
| 4 | `marie_pipeline_contracts.py` | `_contract(...)` con `required`/`optional`/`intent_terms` → enrutado determinista del chat |
| 5 | `quantum_pipeline_budget_catalog.py` | entrada si usa QPU real |
| 6 | `artifact_engine/models/macrocycle.py` | el contrato de 7 nombres — **soltarlo ahí es todo lo que hace falta para tener informe** |
| 7 | `MCPClient.ts` | `BIOQL_MCP_TOOLS` **y** `pipelineTools` |
| 8 | `VSIXService.ts` | `PIPELINE_ROUTES` — **si falta, 404** |
| 9 | `MacrocycleCard.tsx` + `ChatMessage.tsx:541` y ~3400 | detección + render |
| 10 | `cardRegistry.ts` | entrada espejo (tiene test de regresión) |

**El `result` debe traer**: `pipeline` (universal), `status`, `timestamp`, `target` **string**
(si es dict el wrapper lo aplana), `stages` dict. Y `result.json` en
`~/.bioql/artifacts/<session>/` **lo escribe el pipeline** vía `save_pipeline_artifacts` — el
wrapper genérico no lo hace.

---

## 6. Modos de fallo silencioso

Los cinco de química siguen en pie, más uno de integración que **ya está vivo en el repo**.

**F-0 · El docking que no dockea** *(real, hoy, en producción)*
`docking_screening_engine.py:50` → `VINA_PATH = os.environ.get("BIOQL_VINA_PATH", "/usr/bin/vina")`.
En este Mac vina está en `/opt/homebrew/bin/vina`. Si nadie importó `induced_fit_docking` antes
(que parchea el global en caliente) ni exportó la variable, el docking cae al
`_estimate_binding_score` de `conformer_engine` — **un heurístico MMFF, no docking**, y el
resultado sale con pinta de score de Vina.
> **Test:** aserción de arranque de que `VINA_PATH` existe y es ejecutable; y que todo score de
> docking lleve `engine` + versión, de modo que un score estimado nunca pueda pasar por Vina.

**F-1 · El anillo que nunca cerró** — RDKit sanea el cierre y sigues con un lineal etiquetado
como macrociclo.
> Percepción de anillos: debe existir un anillo que contenga los `ring_atoms` declarados, del
> tamaño declarado, incluyendo el enlace de ciclación. Decoys con anillo abierto: rechazo 100%.

**F-2 · La estereoquímica perdida en el round-trip** — D-aa, N-Me, Aib. Otra molécula, mismos
números.
> Códigos CIP preservados a través de `SMILES→3D→SDF→re-parse`; cero centros sin asignar entre
> los declarados.

**F-3 · El sesgo del superviviente** — ETKDG falla en los anillos grandes y tensionados, *justo
los interesantes*; rankeas 500 y en realidad son 120. Gemelo: ensembles sin converger, donde el
confórmero bioactivo nunca estuvo en la caja.
> Conservación `N_entrada == N_salida + N_descartados` con razón; tasa de fallo por ciclación ×
> tamaño de anillo con umbral; curva de convergencia obligatoria.

**F-4 · El bolsillo que no existe** — pLDDT<70, surco de cristalización, o interfaz PPI que es
contacto cristalográfico.
> pLDDT medio/mínimo del bolsillo con gate y override explícito; ambigüedad de fpocket fuerza
> confirmación.

**F-5 · El score que no ve al target** — los scores de macrociclos correlacionan con tamaño y
lipofilia: ranking estable, reproducible y **target-independiente**.
> Doble: control de target cruzado (solape top-N bajo umbral) **y** `|Spearman(score, MW)|`,
> `|Spearman(score, cLogP)|` bajo umbral. Si no pasa, el informe declara *«ranking dominado por
> tamaño»* y no lo presenta como priorización.

---

## 7. Lo que necesito de ti antes de F1

1. **¿OK a la arquitectura** (pipeline nº 9, 6 módulos nuevos, 10 pasos de alta)?
2. **¿OK al encuadre del 60/40** — cuántico solo en Q1–Q4, presupuesto medido y reportado, y el
   plan diciendo la verdad cuando el 40% no se alcanza honestamente?
3. **¿Arreglo F-0 (el `VINA_PATH` roto) ya**, como parche aparte? Afecta a pipelines que ya
   corren hoy, no solo al nuevo.
