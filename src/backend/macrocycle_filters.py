"""
bRo5: el espacio de propiedades donde viven los macrociclos.

BioQL no tenía esto. Lo único que había era `docking_screening_engine`
`_passes_lipinski(mw_range=(200, 600), logp_range=(-1, 5))`, que es la regla de
cinco de moléculas pequeñas: **descalificaría a TODOS los macrociclos**, porque
una ciclosporina A pesa 1202 Da. El resto de menciones a «beyond rule of five» en
el repo son prosa de informe, no código que evalúe nada.

Los umbrales de aquí son los de Doak/Kihlberg para el espacio bRo5 -- el que
ocupan los orales de peso alto, macrociclos incluidos. No son una invención de
este fichero, pero tampoco son una ley: se declaran, y cada candidato sale con
qué criterio incumplió y por cuánto, en vez de con un booleano sin recurso.

Y la propiedad que de verdad separa a un macrociclo permeable de uno que no lo es
NO está en esta tabla: es el ÁREA POLAR QUE EL CONFÓRMERO ESCONDE al plegarse
sobre sí mismo formando puentes de hidrógeno intramoleculares. Una TPSA calculada
sobre la fórmula plana no la ve. Por eso `conformer_psa()` la calcula sobre el
ensemble 3D y se declara aparte: es una aproximación, y se dice cuál.

MOLEVERA / BIOQL
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

    RDLogger.DisableLog("rdApp.*")
    _RDKIT = True
except Exception:  # pragma: no cover
    _RDKIT = False


# Espacio bRo5 (Doak & Kihlberg). Cada criterio con su límite y su dirección.
BRO5 = (
    ("mw", "Peso molecular", 1000.0, "<="),
    ("clogp", "cLogP", 10.0, "<="),
    ("clogp_min", "cLogP", -2.0, ">="),
    ("hbd", "Donadores de H", 6, "<="),
    ("hba", "Aceptores de H", 15, "<="),
    ("tpsa", "TPSA", 250.0, "<="),
    ("rotb", "Enlaces rotables", 20, "<="),
)

# Para contraste: la regla de cinco clásica, que se reporta pero NO se aplica como
# gate. Un macrociclo la incumple por diseño y eso no es un defecto.
RO5 = (("mw", 500.0), ("clogp", 5.0), ("hbd", 5), ("hba", 10))


def descriptors(smiles: str) -> Optional[Dict[str, Any]]:
    if not _RDKIT:
        return None
    m = Chem.MolFromSmiles(smiles or "")
    if m is None:
        return None
    return {
        "mw": round(Descriptors.MolWt(m), 2),
        "clogp": round(Crippen.MolLogP(m), 3),
        "hbd": rdMolDescriptors.CalcNumHBD(m),
        "hba": rdMolDescriptors.CalcNumHBA(m),
        "tpsa": round(rdMolDescriptors.CalcTPSA(m), 2),
        "rotb": rdMolDescriptors.CalcNumRotatableBonds(m),
        "n_heavy": m.GetNumHeavyAtoms(),
        "csp3": round(rdMolDescriptors.CalcFractionCSP3(m), 3),
    }


def bro5(smiles: str) -> Dict[str, Any]:
    """Evalúa el espacio bRo5 y dice qué incumple y por cuánto."""
    d = descriptors(smiles)
    if d is None:
        return {"ok": False, "reason": "no se pudo calcular descriptores"}
    fallos: List[Dict[str, Any]] = []
    for clave, etiqueta, limite, direccion in BRO5:
        campo = "clogp" if clave == "clogp_min" else clave
        v = d.get(campo)
        if v is None:
            continue
        pasa = v <= limite if direccion == "<=" else v >= limite
        if not pasa:
            fallos.append(
                {
                    "criterion": etiqueta,
                    "field": campo,
                    "value": v,
                    "limit": limite,
                    "direction": direccion,
                    "excess": round(abs(v - limite), 3),
                }
            )
    ro5_fallos = sum(1 for k, lim in RO5 if (d.get(k) or 0) > lim)
    return {
        "ok": not fallos,
        "descriptors": d,
        "violations": fallos,
        "n_violations": len(fallos),
        "ro5_violations": ro5_fallos,
        "note": (
            "cumple el espacio bRo5"
            if not fallos
            else "fuera del espacio bRo5 en " + ", ".join(f["criterion"] for f in fallos)
        ),
        "ro5_note": (
            f"incumple {ro5_fallos} de 4 criterios de la regla de cinco clásica, lo "
            f"que para un macrociclo es esperable y no se usa como gate"
        ),
    }


def polar_sasa(molblock: str) -> Optional[float]:
    """Área polar (N, O y sus H) accesible al disolvente, en Å², de UNA conformación."""
    if not _RDKIT or not molblock:
        return None
    m = Chem.MolFromMolBlock(molblock, removeHs=False)
    if m is None:
        return None
    try:
        from rdkit.Chem import rdFreeSASA

        rdFreeSASA.CalcSASA(m, rdFreeSASA.classifyAtoms(m))
        total = 0.0
        for at in m.GetAtoms():
            if at.GetSymbol() in ("N", "O"):
                total += float(at.GetProp("SASA")) if at.HasProp("SASA") else 0.0
                for nb in at.GetNeighbors():
                    if nb.GetSymbol() == "H" and nb.HasProp("SASA"):
                        total += float(nb.GetProp("SASA"))
        return round(total, 1)
    except Exception:  # noqa: BLE001
        return None


def psa_across_ensemble(molblocks: List[str]) -> Dict[str, Any]:
    """Cuánta área polar esconde la molécula al plegarse, medida CONTRA SÍ MISMA.

    Es lo que separa a un macrociclo permeable de uno que no lo es: el compuesto
    plegado esconde sus donadores de hidrógeno formando puentes intramoleculares,
    y el mismo compuesto estirado no pasa la membrana. La TPSA de la fórmula plana
    da el mismo número en los dos casos y por eso no sirve aquí.

    La primera versión de esto dividía la SASA polar (Å², en 3D) entre la TPSA
    (derivada de la fórmula plana) y llamaba «fracción enterrada» al cociente.
    Son magnitudes distintas: el número salió NEGATIVO en el primer macrociclo
    probado, que es como se descubrió. Lo comparable es la SASA polar de unos
    confórmeros contra la de otros de LA MISMA molécula, y eso es lo que se mide.
    """
    vals = [v for v in (polar_sasa(mb) for mb in molblocks or []) if v is not None]
    if not vals:
        return {"available": False, "reason": "ninguna conformación dio SASA"}
    lo, hi = min(vals), max(vals)
    return {
        "available": True,
        "n_conformers": len(vals),
        "polar_sasa_min_A2": lo,
        "polar_sasa_max_A2": hi,
        "spread_A2": round(hi - lo, 1),
        "buried_vs_most_open_A2": round(hi - lo, 1),
        "method": "SASA de N, O y sus H (rdFreeSASA), comparada entre confórmeros "
        "de la misma molécula",
        "caveat": (
            "proxy conformacional, NO una permeabilidad y NO un Papp. Mide cuánta "
            "área polar puede esconder este compuesto plegándose, no si lo hace en "
            "membrana ni con qué población"
        ),
    }


def sequence_liabilities(sequence: str) -> Dict[str, Any]:
    """Motivos de secuencia que dan problemas de estabilidad, sin adornos."""
    s = (sequence or "").upper().replace("-", "")
    hallazgos = []
    for motivo, que in (
        ("NG", "desamidación de Asn-Gly"),
        ("DP", "hidrólisis de Asp-Pro"),
        ("DG", "isomerización de Asp-Gly"),
    ):
        i = s.find(motivo)
        while i >= 0:
            hallazgos.append({"motif": motivo, "position": i + 1, "risk": que})
            i = s.find(motivo, i + 1)
    for res, que in (
        ("M", "oxidación de metionina"),
        ("C", "oxidación/intercambio de cisteína"),
        ("W", "oxidación de triptófano"),
    ):
        n = s.count(res)
        if n:
            hallazgos.append({"motif": res, "count": n, "risk": que})
    return {
        "n_findings": len(hallazgos),
        "findings": hallazgos,
        "note": (
            "sin motivos de riesgo conocidos en la secuencia"
            if not hallazgos
            else f"{len(hallazgos)} motivo(s) de riesgo; son banderas de "
            f"estabilidad química, no de actividad"
        ),
    }


# MOLEVERA / BIOQL
