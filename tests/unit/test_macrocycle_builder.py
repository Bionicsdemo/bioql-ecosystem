"""
El constructor de macrociclos, comprobado contra la molécula y contra decoys.

Los dos modos de fallo que estos tests existen para cazar son silenciosos: un
anillo que nunca cerró sigue calculando descriptores y dockeando como si fuera un
macrociclo, y una estereoquímica perdida en el round-trip deja otra molécula con
los mismos números. Ninguno lanza excepción por su cuenta.

Ningún gate entra sin demostrar poder discriminante, así que los decoys de anillo
abierto tienen que ser rechazados al 100%: un filtro que aprueba todo no es un
filtro.

MOLEVERA / BIOQL
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend"))

mb = pytest.importorskip("macrocycle_builder")
Chem = pytest.importorskip("rdkit.Chem")


# ── la invariante geométrica sobre la que se apoya todo ───────────────────────
@pytest.mark.parametrize(
    "side,cip_L",
    [("C", "S"), ("CO", "S"), ("CS", "R"), ("[C@@H](C)O", "S")],
    ids=["Ala", "Ser", "Cys", "Thr"],
)
def test_arroba_doble_es_L_y_el_cip_depende_de_la_cadena_lateral(side, cip_L):
    """En el orden N, CA, lateral, C(=O): `@@` es L y `@` es D.

    Y el CIP NO es constante: L-Cys sale R porque el azufre gana prioridad,
    mientras Ala, Ser y Thr salen S. Por eso la configuración se declara por
    geometría y el CIP se registra como consecuencia. Si RDKit cambiara este
    convenio, todos los D-aminoácidos del pipeline se construirían al revés sin
    que nada más lo notase.
    """
    L = Chem.MolFromSmiles(f"N[C@@H]({side})C(=O)O")
    D = Chem.MolFromSmiles(f"N[C@H]({side})C(=O)O")
    for m in (L, D):
        Chem.AssignStereochemistry(m, cleanIt=True, force=True)
    assert L.GetAtomWithIdx(1).GetPropsAsDict()["_CIPCode"] == cip_L
    opuesto = "R" if cip_L == "S" else "S"
    assert D.GetAtomWithIdx(1).GetPropsAsDict()["_CIPCode"] == opuesto


# ── F-1: el anillo cerró de verdad ────────────────────────────────────────────
@pytest.mark.parametrize("n", [3, 4, 5, 6, 8])
def test_head_to_tail_mide_tres_atomos_por_residuo(n):
    """N, CA y C por residuo: el anillo de un head-to-tail mide exactamente 3n.

    Es la comprobación que distingue un macrociclo de un lineal con una etiqueta.
    """
    spec = mb.build_macrocycle("A" * n, "head_to_tail")
    ring = mb.verify_ring(spec)
    assert ring["ok"], ring
    assert ring["ring_size"] == 3 * n


def test_disulfuro_y_lactama_lateral_cierran_anillo():
    for seq, cyc in (("CAGC", "disulfide"), ("AKGF", "sidechain_to_tail")):
        ring = mb.verify_ring(mb.build_macrocycle(seq, cyc))
        assert ring["ok"], (seq, cyc, ring)
        assert ring["ring_size"] > 8


# ── F-1, control negativo: los decoys tienen que caer TODOS ───────────────────
_DECOYS_ANILLO_ABIERTO = [
    # el lineal que el constructor produce sin ciclar: misma composición, sin anillo
    ("lineal crudo", "N[C@@H](C)C(=O)NCC(=O)N[C@@H](Cc1ccccc1)C(=O)O"),
    # solo cadenas laterales aromáticas: hay anillos, pero ninguno macrocíclico
    ("solo aromáticos", "N[C@@H](Cc1ccccc1)C(=O)N[C@@H](Cc1ccccc1)C(=O)O"),
    # un anillo pequeño (prolina) que no es el macrociclo
    ("anillo pequeño", "O=C(O)[C@@H]1CCCN1"),
    ("dipéptido lineal", "NCC(=O)NCC(=O)O"),
]


@pytest.mark.parametrize(
    "nombre,smiles", _DECOYS_ANILLO_ABIERTO, ids=[d[0] for d in _DECOYS_ANILLO_ABIERTO]
)
def test_el_gate_rechaza_todo_decoy_de_anillo_abierto(nombre, smiles):
    """Tasa de rechazo exigida: 100%.

    Un filtro que no separa señal de decoy no es un filtro, y el peor resultado
    posible aquí es aprobar por construcción.
    """
    falso = mb.MacrocycleSpec(
        smiles=smiles, sequence="(decoy)", residues=[], cyclization="head_to_tail"
    )
    ring = mb.verify_ring(falso)
    assert not ring["ok"], f"el decoy {nombre!r} pasó el gate: {ring}"
    assert ring.get("reason"), "un rechazo sin razón no es accionable"


def test_el_gate_acepta_los_macrociclos_de_verdad():
    """La otra mitad del control: que no rechace por construcción."""
    for seq, cyc in (
        ("AGFK", "head_to_tail"),
        ("AAAAA", "head_to_tail"),
        ("CAGC", "disulfide"),
        ("AKGF", "sidechain_to_tail"),
    ):
        assert mb.verify_ring(mb.build_macrocycle(seq, cyc))["ok"], (seq, cyc)


# ── F-2: la estereoquímica declarada es la que sale ───────────────────────────
def test_el_d_aminoacido_sale_con_el_cip_contrario_al_l():
    """Si esto falla, se pide D-Phe y se construye L-Phe: otra molécula."""
    L = mb.build_macrocycle("AFGK", "head_to_tail")
    D = mb.build_macrocycle("A-D:F-G-K", "head_to_tail")
    cip_L = {s["atom"]: s["cip"] for s in L.stereo}
    cip_D = {s["atom"]: s["cip"] for s in D.stereo}
    assert cip_L != cip_D, "cambiar L por D no cambió ningún CIP"
    distintos = [i for i in cip_L if cip_L.get(i) != cip_D.get(i)]
    assert len(distintos) == 1, f"debería cambiar exactamente un centro, cambiaron {len(distintos)}"


def test_aib_no_aporta_centro_quiral():
    """Aib es α,α-dimetilglicina: no tiene centro, y contarlo inflaría el recuento."""
    spec = mb.build_macrocycle("A-Aib-G-K", "head_to_tail")
    assert mb.verify_stereo(spec)["declared_centers"] == 2  # A y K; Aib y G no


def test_la_n_metilacion_no_toca_la_estereoquimica():
    sin = mb.build_macrocycle("AFGK", "head_to_tail")
    con = mb.build_macrocycle("A-NMe:F-G-K", "head_to_tail")
    assert mb.verify_stereo(sin)["ok"] and mb.verify_stereo(con)["ok"]
    assert mb.verify_stereo(sin)["declared_centers"] == mb.verify_stereo(con)["declared_centers"]
    assert "N(C)" in con.smiles, "la N-metilación no llegó al SMILES"


@pytest.mark.parametrize(
    "seq,cyc",
    [
        ("AGFK", "head_to_tail"),
        ("A-D:F-Aib-K", "head_to_tail"),
        ("A-NMe:F-G-K-L", "head_to_tail"),
        ("CAGC", "disulfide"),
        ("AKGF", "sidechain_to_tail"),
    ],
)
def test_el_roundtrip_a_sdf_no_pierde_ningun_centro(seq, cyc):
    """SMILES -> mol -> SDF -> mol es el viaje que hará el pipeline al embeber en
    3D y al escribir poses. Si un centro se pierde ahí, todo lo posterior corre
    sobre una molécula que nadie pidió."""
    rt = mb.roundtrip_stereo(mb.build_macrocycle(seq, cyc))
    assert rt["ok"], rt
    assert rt["centers_before"] == rt["centers_after"]


# ── ambigüedad: se pregunta, no se adivina ────────────────────────────────────
def test_tres_cisteinas_sin_anclas_es_un_error_y_no_una_eleccion_al_azar():
    """Con tres Cys hay tres disulfuros posibles. Elegir uno en silencio sería
    inventar el compuesto que se va a evaluar."""
    with pytest.raises(ValueError, match="anchor_i"):
        mb.build_macrocycle("CACGC", "disulfide")


def test_una_sola_cisteina_no_puede_formar_disulfuro():
    with pytest.raises(ValueError, match="hacen falta dos"):
        mb.build_macrocycle("CAGA", "disulfide")


def test_la_prolina_rechaza_la_n_metilacion_en_vez_de_producir_un_smiles_falso():
    with pytest.raises(ValueError, match="prolina"):
        mb.build_macrocycle("A-NMe:P-G-K", "head_to_tail")


def test_un_residuo_desconocido_falla_al_construir_no_al_dockear():
    with pytest.raises(KeyError):
        mb.build_macrocycle("A-Xyz-K", "head_to_tail")


# ── determinismo ──────────────────────────────────────────────────────────────
def test_la_misma_secuencia_da_el_mismo_hash():
    a = mb.build_macrocycle("A-D:F-Aib-K", "head_to_tail")
    b = mb.build_macrocycle("A-D:F-Aib-K", "head_to_tail")
    assert a.content_hash == b.content_hash and a.content_hash


def test_cambiar_la_quiralidad_cambia_el_hash():
    """Si no cambiara, el cacheo por contenido serviría el enantiómero guardado."""
    L = mb.build_macrocycle("AFGK", "head_to_tail")
    D = mb.build_macrocycle("A-D:F-G-K", "head_to_tail")
    assert L.content_hash != D.content_hash


# MOLEVERA / BIOQL


# ── el guard que faltaba: una frase que se cae no deja rastro ─────────────────
def test_ninguna_frase_del_modelo_referencia_una_ruta_que_no_existe():
    """Una plantilla con una ruta inexistente no da error: la frase desaparece.

    `convergence_note()` emitía `note` mientras el modelo pedía `note_en`, y esa
    frase estuvo cayéndose del informe sin que nada lo dijera. La comprobación de
    "no queda castellano en el informe inglés" daba verde justamente porque la
    frase no estaba, no porque estuviera traducida.

    Así que aquí se resuelven TODAS las rutas que el modelo referencia contra una
    corrida real. Las marcadas opcionales con `?` pueden faltar; el resto no.
    """
    import json
    import pathlib
    import re

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.backend.artifact_engine import facts as F  # noqa: E402
    from src.backend.artifact_engine.models import macrocycle as M  # noqa: E402

    ref = pathlib.Path("~/.bioql/artifacts/macrocycle-mdm2-c1/result.json").expanduser()
    if not ref.is_file():
        pytest.skip("no hay corrida de referencia de macrociclos en esta máquina")
    r = json.loads(ref.read_text())

    campo = re.compile(r"\{([^{}]+)\}")
    faltan = []
    for ch in M.chapters(r, {}, {}):
        for b in ch["beats"]:
            for texto in (b["es"], b["en"], *(b.get("tech") or {}).values()):
                for cuerpo in campo.findall(texto):
                    if cuerpo.endswith("?"):
                        continue  # declarada opcional
                    ref_path = cuerpo.split("|")[0].strip()
                    head, _, rest = ref_path.partition(":")
                    base = (M.ALIASES or {}).get(head)
                    ruta = f"{base}.{rest}" if base and rest else (base or ref_path)
                    if F.get(r, ruta) is None:
                        faltan.append((ch["id"], ruta))
    assert not faltan, (
        "el modelo referencia rutas que la corrida no tiene, así que esas frases "
        f"desaparecen del informe sin avisar: {sorted(set(faltan))}"
    )
