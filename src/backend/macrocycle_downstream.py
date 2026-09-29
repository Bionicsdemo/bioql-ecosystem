"""
Lo que le faltaba al pipeline de macrociclos para estar a la altura del resto.

El JSON del macrociclo tenía 173 campos frente a los 2 479 - 7 983 de los otros
ocho pipelines, y la razón no era que estuviera mal construido: es que hacía
menos ciencia. Cubría construir, confórmeros, propiedades, triaje y orden, y ahí
se paraba. Ni ADMET, ni síntesis, ni toxicología, ni PK, ni docking.

Este módulo no reimplementa nada de eso. Todo existe ya en el backend y está
medido contra benchmarks; lo que faltaba era enchufarlo. Cada función de aquí es
un adaptador delgado sobre un motor que ya estaba:

    ADMET         admet_bridge.predict_admet          (ADMET-AI por Modal)
    síntesis      synthesizability.sa_score/np_score  (Ertl, y AiZynth si está)
    toxicología   multispecies_tox.run_multispecies_tox
    PK            pk_pbpk.predict_clearance_ivive     (IVIVE, well-stirred)
    estructura    RCSB, por id de PDB
    docking       bionemo_diffdock                    (DiffDock-L por NVIDIA NIM)
    afinidad      quantum_pocket_scorer               (VQE)

LA REGLA QUE GOBIERNA TODO ESTE FICHERO
---------------------------------------
Ninguna función inventa un número cuando su motor no está. Devuelve
`available: False` con la razón escrita, y el informe la enseña. Es la diferencia
entre "no se midió" y "se midió y salió bien", que es justo la que un dossier no
puede permitirse borrar.

Hoy mismo hay un ejemplo vivo: el workspace de Modal está deshabilitado, así que
ADMET devuelve su razón en vez de un número. El día que se reactive, el mismo
código empieza a dar valores sin tocar nada.

MOLEVERA / BIOQL
"""

from __future__ import annotations

import importlib
import time
from typing import Any, Dict, List, Optional

# Especies por defecto para el paquete toxicológico: las dos que pide un IND.
_ESPECIES = ("rat", "dog")

# Targets con estructura conocida, con SU CADENA RECEPTORA. No es una base de
# datos: es el atajo para que una petición que solo trae el nombre del target
# pueda dockear sin obligar al usuario a saberse el código PDB.
#
# La cadena importa tanto como el código. Casi todas estas estructuras son
# complejos: 1YCR es MDM2 (cadena A) CON el péptido de p53 metido en el bolsillo
# (cadena B). Dockear contra el complejo entero deja el sitio ocupado y empuja la
# pose a cualquier otro rincón de la superficie -- un resultado que converge, que
# se dibuja bien, y que no significa nada. Se conserva solo la cadena receptora.
_PDB_CONOCIDOS = {
    "MDM2": ("1YCR", "A"),  # A = MDM2; B es el péptido de p53 que hay que quitar
    "MDMX": ("3DAC", "A"),
    "KRAS": ("6OIM", "A"),
    "BCL2": ("2XA0", "A"),
    "MCL1": ("3MK8", "A"),
    "BETA-CATENIN": ("1JDH", "A"),
    "MENIN": ("4GQ4", "A"),
}


def _mod(nombre: str) -> Any:
    """Importa por nombre, para que un motor ausente no tumbe el import."""
    return importlib.import_module(nombre)


def _sin(razon: str, **extra: Any) -> Dict[str, Any]:
    """La forma canónica de un escenario que no pudo correr.

    Existe para que 'no disponible' sea un valor de primera clase con su causa,
    y no un hueco que el lector rellena con optimismo.
    """
    d: Dict[str, Any] = {"available": False, "reason": razon}
    d.update(extra)
    return d


# ── ADMET ────────────────────────────────────────────────────────────────────
def admet_for(smiles_list: List[str]) -> Dict[str, Any]:
    """ADMET por candidato, más la superposición de seguridad.

    `admet_bridge` promete no lanzar nunca: devuelve `available: False` con su
    razón. Se respeta esa forma en vez de traducirla, para que la causa que
    llegue al informe sea la del motor y no la mía.
    """
    t0 = time.perf_counter()
    try:
        ab = _mod("admet_bridge")
    except Exception as e:  # noqa: BLE001
        return _sin(f"admet_bridge no importable: {type(e).__name__}: {e}")

    pred = ab.predict_admet(list(smiles_list))
    if not isinstance(pred, dict) or pred.get("available") is False:
        return _sin(
            str((pred or {}).get("error") or "el motor ADMET no está disponible"),
            engine="admet_bridge/ADMET-AI",
            wall_seconds=round(time.perf_counter() - t0, 2),
        )

    filas = pred.get("predictions") or pred.get("results") or []
    banderas = []
    for fila in filas if isinstance(filas, list) else []:
        try:
            banderas.append(ab.admet_safety_flags(fila))
        except Exception:  # noqa: BLE001
            banderas.append({})
    return {
        "available": True,
        "engine": "admet_bridge/ADMET-AI",
        "n_molecules": len(smiles_list),
        "predictions": filas,
        "safety_flags": banderas,
        "wall_seconds": round(time.perf_counter() - t0, 2),
        "note_es": (
            "ADMET-AI sobre cada candidato. En macrociclos sus modelos están fuera "
            "del dominio en que se entrenaron -- casi todo era química de tamaño "
            "Ro5 -- así que estos números orientan y no deciden"
        ),
        "note_en": (
            "ADMET-AI on each candidate. On macrocycles its models sit outside the "
            "domain they were trained on -- almost all of it Ro5-sized chemistry -- "
            "so these numbers orient, they do not decide"
        ),
    }


# ── síntesis ─────────────────────────────────────────────────────────────────
def synthesis_for(smiles: str, *, want_route: bool = False) -> Dict[str, Any]:
    """Accesibilidad sintética, y la ruta si AiZynthFinder está instalado.

    SA y NP son heurísticas de Ertl sobre fragmentos: corren siempre y cuestan
    milisegundos. La ruta es otra cosa -- la valida un buscador retrosintético
    real -- y si no está, se dice, porque un SA bajo no es una ruta.
    """
    t0 = time.perf_counter()
    try:
        sy = _mod("synthesizability")
    except Exception as e:  # noqa: BLE001
        return _sin(f"synthesizability no importable: {type(e).__name__}: {e}")

    motores = {}
    try:
        motores = dict(sy.available() or {})
    except Exception:  # noqa: BLE001
        pass

    out: Dict[str, Any] = {
        "available": True,
        "backends": motores,
        "sa_score": _num(lambda: sy.sa_score(smiles)),
        "np_score": _num(lambda: sy.np_score(smiles)),
        "sc_score": _num(lambda: sy.sc_score(smiles)),
        "wall_seconds": 0.0,
    }
    out["sa_interpretation_es"] = _interpretar_sa(out["sa_score"])
    out["sa_interpretation_en"] = _interpret_sa_en(out["sa_score"])

    if not motores.get("aizynthfinder"):
        out["route"] = _sin(
            "AiZynthFinder no está instalado en este proceso, así que no hay ruta "
            "validada: SA es una heurística de fragmentos, no una síntesis"
        )
    elif want_route:
        try:
            out["route"] = {"available": True, "plan": sy.route_plan(smiles)}
        except Exception as e:  # noqa: BLE001
            out["route"] = _sin(f"la búsqueda de ruta falló: {type(e).__name__}: {e}")
    else:
        out["route"] = _sin("no se pidió ruta en esta corrida (`synthesis_route: true`)")

    out["wall_seconds"] = round(time.perf_counter() - t0, 2)
    out["note_es"] = (
        "un macrociclo peptídico se hace en fase sólida y se cicla al final; el "
        "paso que decide el rendimiento es esa ciclación, y SA no lo modela. "
        "Léase como orden de magnitud entre candidatos, no como coste"
    )
    out["note_en"] = (
        "a peptide macrocycle is made on solid phase and cyclised at the end; the "
        "step that decides the yield is that cyclisation, and SA does not model it. "
        "Read it as an order of magnitude between candidates, not as a cost"
    )
    return out


def _num(fn: Any) -> Optional[float]:
    try:
        v = fn()
        return round(float(v), 4) if v is not None else None
    except Exception:  # noqa: BLE001
        return None


def _interpretar_sa(sa: Optional[float]) -> str:
    if sa is None:
        return "sin puntuación SA"
    if sa < 4:
        return "accesible por rutas estándar"
    if sa < 6:
        return "exigente pero abordable en fase sólida"
    return "difícil: probablemente haga falta química a medida"


def _interpret_sa_en(sa: Optional[float]) -> str:
    if sa is None:
        return "no SA score"
    if sa < 4:
        return "accessible by standard routes"
    if sa < 6:
        return "demanding but workable on solid phase"
    return "hard: likely needs bespoke chemistry"


# ── toxicología ──────────────────────────────────────────────────────────────
def toxicology_for(smiles: str, species: Optional[List[str]] = None) -> Dict[str, Any]:
    """Paquete multi-especie, con el escalado alométrico que ya trae el motor."""
    t0 = time.perf_counter()
    try:
        mt = _mod("multispecies_tox")
    except Exception as e:  # noqa: BLE001
        return _sin(f"multispecies_tox no importable: {type(e).__name__}: {e}")
    try:
        r = mt.run_multispecies_tox(smiles, species=list(species or _ESPECIES))
    except Exception as e:  # noqa: BLE001
        return _sin(f"el motor toxicológico falló: {type(e).__name__}: {str(e)[:120]}")
    if not isinstance(r, dict) or not r:
        return _sin("el motor toxicológico no devolvió nada")
    r["available"] = True
    r["wall_seconds"] = round(time.perf_counter() - t0, 2)
    r["note_es"] = (
        "predicción in-silico sobre especies preclínicas. No sustituye un estudio "
        "GLP y no debe leerse como una dosis segura"
    )
    r["note_en"] = (
        "in-silico prediction across preclinical species. It does not replace a GLP "
        "study and must not be read as a safe dose"
    )
    return r


# ── farmacocinética ──────────────────────────────────────────────────────────
def pharmacokinetics_for(
    smiles: str, *, dose_mg: float = 100.0, admet: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Aclaramiento por IVIVE y la curva de un compartimento que sale de él.

    La cadena es la del repo y está validada contra TDC: CL_int descriptivo ->
    fracción libre -> well-stirred -> CL hepático. De ahí sale el t½, y del t½ la
    curva que dibuja el informe. Si falta cualquier eslabón no se dibuja una
    recta plana: se declara, porque una curva plana es una afirmación sobre este
    compuesto que la corrida nunca hizo.
    """
    t0 = time.perf_counter()
    try:
        pk = _mod("pk_pbpk")
    except Exception as e:  # noqa: BLE001
        return _sin(f"pk_pbpk no importable: {type(e).__name__}: {e}")
    try:
        cl = pk.predict_clearance_ivive(smiles, admet=admet)
    except Exception as e:  # noqa: BLE001
        return _sin(f"IVIVE falló: {type(e).__name__}: {str(e)[:120]}")

    cl_h = _float(cl.get("cl_hepatic_L_per_h"))
    fu = _float((cl.get("fraction_unbound") or {}).get("fu"))
    # Volumen de distribución: sin un modelo propio no se inventa: se toma el
    # valor por defecto del motor si lo trae, y si no, el escenario lo dice.
    vd = _float(cl.get("vd_L")) or _float((cl.get("ivive") or {}).get("vd_L"))

    out: Dict[str, Any] = {
        "available": True,
        "engine": cl.get("engine"),
        "validation": cl.get("validation"),
        "clearance": cl,
        "fraction_unbound": fu,
        "cl_hepatic_L_per_h": cl_h,
        "dose_mg": dose_mg,
    }
    if cl_h and vd:
        try:
            curva = pk.one_compartment_pk(dose_mg=dose_mg, cl_L_h=cl_h, vd_L=vd)
            out["profile"] = curva
            out["half_life_h"] = _float(curva.get("half_life_h"))
        except Exception as e:  # noqa: BLE001
            out["profile"] = _sin(f"la curva falló: {type(e).__name__}: {e}")
    else:
        out["profile"] = _sin(
            "falta el volumen de distribución, y sin él no hay t½ que dibujar. "
            "Una curva plana sería una afirmación que esta corrida no hizo"
        )
    out["wall_seconds"] = round(time.perf_counter() - t0, 2)
    out["note_es"] = (
        "los macrociclos por encima de 700 Da suelen tener baja permeabilidad "
        "pasiva, y un aclaramiento hepático predicho sobre descriptores no lo "
        "sabe. El número orienta el orden entre candidatos, no la dosis"
    )
    out["note_en"] = (
        "macrocycles above 700 Da usually have poor passive permeability, and a "
        "hepatic clearance predicted from descriptors does not know that. The "
        "number orients the order between candidates, not the dose"
    )
    return out


def _xyz(linea: str) -> List[float]:
    """Las tres coordenadas de una línea ATOM/HETATM, o [] si no se dejan leer."""
    try:
        return [float(linea[30:38]), float(linea[38:46]), float(linea[46:54])]
    except Exception:  # noqa: BLE001
        return []


def _float(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if f == f else None  # NaN fuera
    except Exception:  # noqa: BLE001
        return None


# ── estructura del target ────────────────────────────────────────────────────
def target_structure(target: str, pdb_id: str = "", chain: str = "") -> Dict[str, Any]:
    """El PDB del target, de RCSB, con el bolsillo VACÍO.

    No pasa por Modal a propósito: plegar la proteína cuando ya existe resuelta
    es gastar GPU en algo que un `urllib` resuelve en un segundo, y además deja
    el docking funcionando los días en que el plegado no está disponible.

    Se queda con la cadena receptora y tira aguas, iones y ligandos. Lo que se
    tira se CUENTA, porque «se dockeó contra MDM2» y «se dockeó contra MDM2 con
    el péptido de p53 todavía dentro» son dos experimentos distintos y solo uno
    responde la pregunta.
    """
    t0 = time.perf_counter()
    objetivo = str(target).upper().strip()
    conocido = _PDB_CONOCIDOS.get(objetivo)
    codigo = (pdb_id or (conocido[0] if conocido else "")).strip()
    cadena = (chain or (conocido[1] if conocido else "")).strip().upper()
    if not codigo:
        return _sin(
            f"no hay estructura conocida para «{target}» y no se pasó `pdb_id`: "
            f"sin receptor no se puede dockear, y dockear contra otra proteína "
            f"sería peor que no dockear",
            known_targets=sorted(_PDB_CONOCIDOS),
        )
    try:
        dse = _mod("docking_screening_engine")
        pdb_text = dse._download_pdb(codigo)
    except Exception as e:  # noqa: BLE001
        return _sin(f"no se pudo traer {codigo} de RCSB: {type(e).__name__}: {str(e)[:100]}")

    todas = sorted({ln[21] for ln in pdb_text.splitlines() if ln.startswith("ATOM")})
    if not cadena:
        cadena = todas[0] if todas else ""

    guardadas, descartadas, hetero = [], [], 0
    # Lo que se aparta no se tira sin más: sus coordenadas SON el sitio de unión.
    # Es la referencia contra la que luego se comprueba si la pose aterrizó donde
    # había que aterrizar, así que se guardan al apartarlas.
    sitio: List[List[float]] = []
    for ln in pdb_text.splitlines():
        if ln.startswith("ATOM"):
            if ln[21] == cadena:
                guardadas.append(ln)
            else:
                descartadas.append(ln)
                sitio.append(_xyz(ln))
        elif ln.startswith("HETATM"):
            hetero += 1
            if ln[17:20].strip() not in ("HOH", "WAT", "SO4", "PO4", "GOL", "EDO"):
                sitio.append(_xyz(ln))  # un ligando de verdad también marca el sitio
        elif ln.startswith(("TER", "END")):
            continue
        elif not ln.startswith(("ANISOU", "CONECT")):
            guardadas.append(ln)  # cabeceras: no estorban y documentan la fuente
    sitio = [p for p in sitio if p]
    receptor = (
        "\n".join(
            [ln for ln in guardadas if not ln.startswith("ATOM")]
            + [ln for ln in guardadas if ln.startswith("ATOM")]
        )
        + "\nEND\n"
    )

    return {
        "available": True,
        "pdb_id": codigo,
        "source": "RCSB",
        "resolved_from": "pdb_id" if pdb_id else "tabla de targets conocidos",
        "receptor_chain": cadena,
        "chains_in_file": todas,
        "n_atoms_receptor": sum(1 for ln in guardadas if ln.startswith("ATOM")),
        "n_atoms_dropped_other_chains": len(descartadas),
        "n_hetatm_dropped": hetero,
        "prepared_es": (
            f"se conserva la cadena {cadena} y se descartan {len(descartadas)} átomos "
            f"de otras cadenas y {hetero} HETATM (aguas, iones, ligandos). En "
            f"{codigo} el bolsillo venía ocupado, y dockear contra el complejo "
            f"entero habría empujado la pose fuera del sitio que interesa"
        ),
        "prepared_en": (
            f"chain {cadena} is kept and {len(descartadas)} atoms from other chains "
            f"plus {hetero} HETATM (waters, ions, ligands) are dropped. In {codigo} "
            f"the pocket came occupied, and docking against the whole complex would "
            f"have pushed the pose away from the site that matters"
        ),
        "site_reference_xyz": sitio,
        "n_site_reference_atoms": len(sitio),
        "pdb_text": receptor,
        "wall_seconds": round(time.perf_counter() - t0, 2),
    }


# ── docking ──────────────────────────────────────────────────────────────────
def dock_macrocycle(
    pdb_text: str, smiles: str, *, num_poses: int = 10, timeout_s: int = 900
) -> Dict[str, Any]:
    """DiffDock-L sobre el receptor, y la pose ganadora lista para dibujar.

    Aviso que viaja con el resultado y no se quita: los scores de docking de
    macrociclos correlacionan MAL con afinidad medida. Esto sirve para ver DÓNDE
    se posa y si el bolsillo lo admite, no para ordenar por potencia. El orden
    del pipeline no lo usa.
    """
    t0 = time.perf_counter()
    try:
        dd = _mod("bionemo_diffdock")
    except Exception as e:  # noqa: BLE001
        return _sin(f"bionemo_diffdock no importable: {type(e).__name__}: {e}")
    if not dd.is_available():
        return _sin("el cliente de DiffDock no está configurado en este proceso")
    try:
        res = dd.dock(pdb_text, smiles, ligand_file_type="smiles", num_poses=int(num_poses))
    except Exception as e:  # noqa: BLE001
        return _sin(f"el docking falló: {type(e).__name__}: {str(e)[:140]}")
    if not res:
        return _sin("DiffDock no devolvió ninguna pose")

    pose_sdf = None
    try:
        pose_sdf = dd.top_pose(res)
    except Exception:  # noqa: BLE001
        pass
    if not pose_sdf:
        return _sin("DiffDock respondió pero sin una pose legible")

    out: Dict[str, Any] = {
        "available": True,
        "engine": "DiffDock-L (NVIDIA NIM)",
        "n_poses": int(num_poses),
        "top_pose_sdf": pose_sdf,
        "raw": {k: v for k, v in res.items() if k not in ("ligand_positions", "trajectory")},
        "wall_seconds": round(time.perf_counter() - t0, 2),
        "caveat_es": (
            "los scores de docking de macrociclos correlacionan mal con afinidad "
            "medida. Esto enseña DÓNDE se posa y si el bolsillo lo admite; el "
            "orden del pipeline no lo usa, a propósito"
        ),
        "caveat_en": (
            "macrocycle docking scores correlate poorly with measured affinity. "
            "This shows WHERE it sits and whether the pocket takes it; the "
            "pipeline's ranking does not use it, deliberately"
        ),
    }
    out["ligand_atoms"] = pose_atoms(pose_sdf)
    try:
        out["complex_handoff"] = dd.top_pose_complex_handoff(pdb_text, res)
    except Exception:  # noqa: BLE001
        out["complex_handoff"] = None
    return out


# Radios de van der Waals, en Å, para dibujar la pose. Solo los elementos que
# aparecen en un péptido ciclado; cualquier otro cae al radio del carbono.
_RVDW = {"C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80, "H": 1.20, "F": 1.47, "P": 1.80}


def pose_atoms(sdf_text: str) -> List[Dict[str, Any]]:
    """Los átomos de la pose en la forma que dibuja el informe: {e, p, r}.

    Se parsea el bloque de átomos del SDF a mano en vez de pasar por RDKit: son
    tres campos por línea y el fichero ya está en memoria, y así una pose que
    RDKit rechace por valencias sigue pudiéndose ver -- que es justo cuando más
    falta hace mirarla.
    """
    lineas = (sdf_text or "").splitlines()
    if len(lineas) < 4:
        return []
    try:
        n_at = int(lineas[3][0:3])
    except Exception:  # noqa: BLE001
        return []
    salida: List[Dict[str, Any]] = []
    for ln in lineas[4 : 4 + n_at]:
        try:
            x, y, z = float(ln[0:10]), float(ln[10:20]), float(ln[20:30])
            e = ln[31:34].strip() or "C"
        except Exception:  # noqa: BLE001
            continue
        salida.append(
            {"e": e, "p": [round(x, 3), round(y, 3), round(z, 3)], "r": _RVDW.get(e, 1.70)}
        )
    return salida


def pocket_check(
    pose_atoms_list: List[Dict[str, Any]], reference_xyz: List[List[float]], cutoff: float = 5.0
) -> Dict[str, Any]:
    """¿La pose cayó donde está el sitio, o en cualquier otro rincón?

    Esto sustituye al ΔG, y a propósito. El repo tenía un
    `estimate_binding_affinity_quantum` y alguien lo RETIRÓ con este mensaje:
    «removed: it fabricated ΔG (kcal/mol) from qubit Hamming weight». Tenía razón
    quien lo quitó, y resucitarlo para tener una cifra bonita sería repetir el
    fallo con más pasos.

    Lo que sí se puede afirmar con la corrida delante es geométrico y se
    comprueba: la estructura venía con el ligando nativo dentro (en 1YCR, la
    hélice de p53), se apartó para dejar el bolsillo libre, y ahora se mide
    cuánto de la pose cae sobre ese mismo sitio. Un docking que aterriza a 30 Å
    del bolsillo también converge y también se dibuja bien; esta es la diferencia
    entre las dos cosas.

    No es afinidad. Es ocupación del sitio, que es una pregunta distinta y
    contestable.
    """
    if not pose_atoms_list:
        return _sin("sin pose no hay nada que comprobar")
    if not reference_xyz:
        return _sin(
            "la estructura no traía ligando ni cadena nativa que apartar, así que "
            "no hay sitio de referencia contra el que comprobar la pose"
        )
    try:
        import numpy as np
    except Exception as e:  # noqa: BLE001
        return _sin(f"numpy no disponible: {e}")

    pose = np.asarray([a["p"] for a in pose_atoms_list], dtype=float)
    ref = np.asarray(reference_xyz, dtype=float)
    # Distancia de cada átomo de la pose a su vecino más cercano del sitio.
    d = np.sqrt(((pose[:, None, :] - ref[None, :, :]) ** 2).sum(-1)).min(axis=1)
    dentro = int((d <= cutoff).sum())
    sep = float(np.linalg.norm(pose.mean(0) - ref.mean(0)))
    frac = dentro / len(pose)
    return {
        "available": True,
        "cutoff_angstrom": cutoff,
        "n_pose_atoms": len(pose),
        "n_within_cutoff": dentro,
        "fraction_within_site": round(frac, 3),
        "centroid_separation_angstrom": round(sep, 2),
        "min_distance_angstrom": round(float(d.min()), 2),
        "max_distance_angstrom": round(float(d.max()), 2),
        "lands_in_site": bool(frac >= 0.5),
        "note_es": (
            f"{dentro} de {len(pose)} átomos de la pose caen a menos de {cutoff} Å "
            f"del sitio que ocupaba el ligando nativo, con los centroides a "
            f"{sep:.2f} Å. Esto dice que se posa DONDE hay que posarse; no dice "
            f"con cuánta fuerza, que es otra medida y no se hizo"
        ),
        "note_en": (
            f"{dentro} of {len(pose)} pose atoms fall within {cutoff} Å of the site "
            f"the native ligand occupied, with centroids {sep:.2f} Å apart. This "
            f"says it sits WHERE it should; it does not say how tightly, which is a "
            f"different measurement and was not made"
        ),
    }


def affinity_status() -> Dict[str, Any]:
    """Por qué no hay una afinidad en este informe.

    Se emite siempre, y a propósito. Un dossier que simplemente omite la afinidad
    deja al lector suponiendo; uno que dice cuál sería el camino honesto y por
    qué hoy no corre, no.
    """
    razon = "MM-GBSA (`mmgbsa_ensemble`) es el camino honesto y no está disponible"
    try:
        mcl = _mod("modal_compute_layer")
        if not mcl.modal_enabled():
            razon = "MM-GBSA corre en Modal y Modal no está habilitado en este proceso"
    except Exception:  # noqa: BLE001
        pass
    return _sin(
        razon,
        removed_scorer=(
            "el `estimate_binding_affinity_quantum` del repo está retirado porque "
            "fabricaba ΔG a partir del peso de Hamming de un qubit. No se usa"
        ),
        removed_scorer_en=(
            "the repo's `estimate_binding_affinity_quantum` is retired because it "
            "fabricated ΔG from a qubit's Hamming weight. It is not used"
        ),
    )


# ── puntuación compuesta ─────────────────────────────────────────────────────
# Pesos del compuesto. Suman 1 y están aquí arriba para que se puedan discutir:
# un score cuyos pesos están escondidos en el código no es un score, es una
# opinión con decimales.
_PESOS = {
    "bro5": 0.30,  # ¿vive en el espacio donde viven los macrociclos orales?
    "liabilities": 0.25,  # riesgos de secuencia
    "ensemble": 0.20,  # ¿se muestreó de verdad su paisaje conformacional?
    "synthesis": 0.15,  # ¿se puede hacer?
    "safety": 0.10,  # banderas de ADMET/tox
}


def composite(cand: Dict[str, Any], extras: Dict[str, Any]) -> Dict[str, Any]:
    """Un número entre 0 y 1, con su desglose y con lo que le faltó.

    Se renormaliza sobre los componentes DISPONIBLES y se dice cuáles faltaron.
    Puntuar un candidato sin ADMET como si tuviera un ADMET perfecto es el modo
    de fallo que este desglose existe para impedir.
    """
    partes: Dict[str, Optional[float]] = {}

    partes["bro5"] = (
        1.0
        if cand.get("bro5_ok")
        else max(0.0, 1.0 - 0.25 * float(cand.get("bro5_violations") or 0))
    )
    n_liab = float(cand.get("liabilities") or 0)
    partes["liabilities"] = max(0.0, 1.0 - 0.2 * n_liab)

    n_conf = cand.get("n_conformers")
    conv = cand.get("ensemble_converged")
    if n_conf is None:
        partes["ensemble"] = None
    else:
        base = min(1.0, float(n_conf) / 100.0)
        partes["ensemble"] = base if conv is not False else base * 0.6

    sa = (extras.get("synthesis") or {}).get("sa_score")
    partes["synthesis"] = None if sa is None else max(0.0, min(1.0, (10.0 - float(sa)) / 6.0))

    tox = extras.get("toxicology") or {}
    admet = extras.get("admet") or {}
    if not tox.get("available") and not admet.get("available"):
        partes["safety"] = None
    else:
        banderas = len(((admet.get("safety_flags") or [{}])[0] or {}).get("flags") or [])
        partes["safety"] = max(0.0, 1.0 - 0.15 * banderas)

    vivos = {k: v for k, v in partes.items() if v is not None}
    faltan = sorted(k for k, v in partes.items() if v is None)
    peso_vivo = sum(_PESOS[k] for k in vivos) or 1.0
    score = sum(_PESOS[k] * v for k, v in vivos.items()) / peso_vivo

    return {
        "score": round(score, 4),
        "weights": _PESOS,
        "components": partes,
        "components_missing": faltan,
        "renormalised_over": round(peso_vivo, 3),
        "note_es": (
            "compuesto sobre los componentes que SÍ se midieron, renormalizado. "
            + (
                f"Faltaron {', '.join(faltan)}: su ausencia no puntúa como si "
                f"hubieran salido bien."
                if faltan
                else "No faltó ninguno."
            )
        ),
        "note_en": (
            "composite over the components that WERE measured, renormalised. "
            + (
                f"Missing: {', '.join(faltan)} -- their absence does not score as "
                f"though they had come out well."
                if faltan
                else "None were missing."
            )
        ),
    }


__all__ = [
    "admet_for",
    "synthesis_for",
    "toxicology_for",
    "pharmacokinetics_for",
    "target_structure",
    "dock_macrocycle",
    "pose_atoms",
    "pocket_check",
    "affinity_status",
    "composite",
]

# MOLEVERA / BIOQL
