"""
El recorte QM/MM de la región de cierre, comprobado contra la química.

Este archivo existe por un fallo concreto: `closure_region` crecía por radio y
capaba con un hidrógeno TODO enlace que cruzara la frontera. Entre esos enlaces
había un C=O y dos amidas, y capar un doble enlace con un solo H deja un radical.
La región salía con 63 electrones, pyscf la rechazaba por paridad, el `except`
del lote se tragaba la excepción, y dos de tres candidatos aparecían en el
informe como "0 de 0 confórmeros significativos" sin ninguna razón escrita.

Debajo había uno peor: la geometría llevaba solo los átomos pesados y las capas,
sin los hidrógenos de la región. El candidato que sí devolvió energías las había
calculado sobre un fragmento deshidrogenado — un número convergido y sin sentido,
que es la peor clase de resultado porque no se distingue de uno bueno.

Los tres tests de abajo son las tres condiciones bajo las que una diferencia
entre confórmeros de una región significa algo:

  1. Todo enlace cortado es C-C simple y no aromático, la única condición bajo la
     que un hidrógeno restituye la valencia sin cambiar la química de dentro.
  2. La geometría emitida lleva los hidrógenos de la región.
  3. El resultado es de capa cerrada, o se declara no disponible. Nunca se fuerza
     un espín que nadie ha medido.

MOLEVERA / BIOQL
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend"))

mq = pytest.importorskip("macrocycle_quantum")
mb = pytest.importorskip("macrocycle_builder")
Chem = pytest.importorskip("rdkit.Chem")
AllChem = pytest.importorskip("rdkit.Chem.AllChem")


def _molblocks(smiles: str, n: int = 2):
    m = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ps = AllChem.ETKDGv3()
    ps.useMacrocycleTorsions = True
    ps.randomSeed = 0xF00D
    ids = list(AllChem.EmbedMultipleConfs(m, numConfs=max(4, n * 2), params=ps))
    if not ids:
        return []
    AllChem.MMFFOptimizeMoleculeConfs(m)
    return [Chem.MolToMolBlock(m, confId=c) for c in ids[:n]]


# Un macrociclo peptídico de verdad, construido por el mismo camino que el
# pipeline: si el constructor cambia, este test se entera.
@pytest.fixture(scope="module")
def caso():
    r = mb.build_and_verify("F-G-K-L-A-W-T-S", cyclization="head_to_tail")
    smiles = (r.get("spec") or {}).get("smiles")
    # Un skip aquí sería un guard verde que no comprueba nada, que es exactamente
    # el modo de fallo que este archivo persigue. Si el constructor no da SMILES,
    # eso es el fallo, y se dice.
    assert smiles, f"el constructor no devolvió SMILES: {r}"
    blocks = _molblocks(smiles)
    assert len(blocks) >= 2, "no se pudieron embeber dos confórmeros de la secuencia de prueba"
    reg = mq.closure_region(smiles, blocks, radius=2)
    if not reg.get("available"):
        pytest.fail(f"la región no se pudo recortar: {reg.get('reason')}")
    return smiles, reg


def test_solo_se_cortan_enlaces_c_c_simples(caso):
    """Ningún enlace de frontera puede ser doble, aromático, o a heteroátomo.

    Es la regla del átomo-enlace, y es la que se estaba violando: un C=O cortado
    y capado con un H no es la misma química que había dentro.
    """
    smiles, reg = caso
    mol = Chem.MolFromSmiles(smiles)
    dentro = set(reg["atom_indices"])
    malos = []
    for i in dentro:
        for nb in mol.GetAtomWithIdx(i).GetNeighbors():
            if nb.GetIdx() in dentro:
                continue
            b = mol.GetBondBetweenAtoms(i, nb.GetIdx())
            if (
                b.GetIsAromatic()
                or b.GetBondTypeAsDouble() != 1.0
                or mol.GetAtomWithIdx(i).GetAtomicNum() != 6
                or nb.GetAtomicNum() != 6
            ):
                malos.append(
                    f"{mol.GetAtomWithIdx(i).GetSymbol()}{i}-{nb.GetSymbol()}{nb.GetIdx()} "
                    f"(orden {b.GetBondTypeAsDouble()}, aromático {b.GetIsAromatic()})"
                )
    assert not malos, "enlaces de frontera que un hidrógeno no puede capar: " + "; ".join(malos)


def test_la_geometria_lleva_los_hidrogenos_de_la_region(caso):
    """La región no es su esqueleto pesado.

    Un recorte sin hidrógenos converge igual y da un número que no significa
    nada. Se comprueba contra la cuenta esperada: los H de los átomos de dentro
    más uno por cada enlace cortado.
    """
    smiles, reg = caso
    mol = Chem.MolFromSmiles(smiles)
    esperados_h = (
        sum(mol.GetAtomWithIdx(i).GetTotalNumHs() for i in reg["atom_indices"]) + reg["n_caps"]
    )
    for k, geom in enumerate(reg["geometries"]):
        simbolos = [ln.split()[0] for ln in geom.strip().splitlines()[2:]]
        assert simbolos.count("H") == esperados_h, (
            f"confórmero {k}: {simbolos.count('H')} hidrógenos en la geometría "
            f"y {esperados_h} esperados"
        )
        assert len(simbolos) == reg["n_heavy_region"] + esperados_h


def test_la_region_es_de_capa_cerrada(caso):
    """Par de electrones, o no disponible. Nunca un espín inventado."""
    _, reg = caso
    assert reg["n_electrons"] % 2 == 0, (
        f"la región salió con {reg['n_electrons']} electrones: RHF no la describe "
        f"y debería haberse declarado no disponible en vez de emitirse"
    )


def test_todos_los_conformeros_dan_la_misma_region(caso):
    """La diferencia solo significa algo si el conjunto de átomos no cambió.

    Es la condición que hace que el error se cancele: lo único que varía entre
    geometrías es la posición, nunca qué átomos hay.
    """
    _, reg = caso
    formulas = {
        tuple(ln.split()[0] for ln in g.strip().splitlines()[2:]) for g in reg["geometries"]
    }
    assert len(formulas) == 1, (
        "los confórmeros no comparten el mismo conjunto de átomos: la diferencia "
        "de energía estaría comparando dos moléculas distintas"
    )


def test_un_recorte_de_capa_abierta_se_declara_no_disponible():
    """El guard tiene que discriminar: si la paridad falla, no se emite.

    Un filtro que aprueba todo no es un filtro, así que se comprueba con una
    molécula cuyo recorte tiene un número impar de electrones.
    """
    # Nitróxido CON amida: el ancla SÍ se encuentra, así que el rechazo tiene que
    # venir de la paridad y no de "no hay dónde anclar". Un decoy que se rechaza
    # por el motivo equivocado no demuestra nada.
    smiles = "CNC(=O)C[N]([O])C"
    blocks = _molblocks(smiles, n=1)
    assert blocks, "no se pudo embeber el decoy"
    reg = mq.closure_region(smiles, blocks, radius=2)
    assert not reg.get("available"), "un recorte de capa abierta se emitió como válido"
    assert "electrones" in (
        reg.get("reason") or ""
    ), f"se rechazó, pero no por paridad: {reg.get('reason')!r}"


# MOLEVERA / BIOQL

# ── la descomposición multi-cluster ──────────────────────────────────────────
# Todo lo que sigue protege UNA afirmación: que la suma de las energías por
# cluster es la energía de algo. Eso solo es cierto si la partición es de verdad
# una partición. En cuanto dos clusters comparten un átomo, ese átomo se cuenta
# dos veces y el total deja de ser una aproximación de nada -- sin lanzar ninguna
# excepción, sin que ningún número salga raro, y con el informe tan convencido
# como antes.
#
# Por eso el primer test es el de disyunción, y por eso no se apoya en el campo
# `disjoint: True` que la propia función escribe: comprueba los índices.


@pytest.fixture(scope="module")
def descomp(caso):
    smiles, _ = caso
    d = mq.closure_clusters(smiles, _molblocks(smiles, 3), radius=2, max_clusters=6)
    if not d.get("available"):
        pytest.fail(f"la descomposición no se pudo hacer: {d.get('reason')}")
    return smiles, d


def test_los_clusters_son_disjuntos(descomp):
    """Ningún átomo pertenece a dos clusters.

    Es la condición que hace que sumar signifique algo. Se comprueba contando
    índices, no leyendo la bandera `disjoint` que la función se pone a sí misma.
    """
    _, d = descomp
    visto: dict = {}
    choques = []
    for c in d["clusters"]:
        for a in c["atom_indices"]:
            if a in visto:
                choques.append((a, visto[a], c["index"]))
            visto[a] = c["index"]
    assert not choques, (
        "hay átomos en dos clusters, así que la suma de energías los cuenta dos "
        f"veces y no es la energía de nada: {choques[:6]}"
    )


def test_cada_cluster_corta_solo_enlaces_capables(descomp):
    """La regla del átomo-enlace vale para cada trozo, no solo para el primero."""
    smiles, d = descomp
    mol = Chem.MolFromSmiles(smiles)
    malos = []
    for c in d["clusters"]:
        dentro = set(c["atom_indices"])
        for i in dentro:
            for nb in mol.GetAtomWithIdx(i).GetNeighbors():
                if nb.GetIdx() in dentro:
                    continue
                b = mol.GetBondBetweenAtoms(i, nb.GetIdx())
                if (
                    b.GetIsAromatic()
                    or b.GetBondTypeAsDouble() != 1.0
                    or mol.GetAtomWithIdx(i).GetAtomicNum() != 6
                    or nb.GetAtomicNum() != 6
                ):
                    malos.append((c["index"], i, nb.GetIdx(), b.GetBondTypeAsDouble()))
    assert not malos, f"cortes que un hidrógeno no puede capar: {malos[:6]}"


def test_cada_cluster_es_de_capa_cerrada(descomp):
    """Un cluster con electrones impares no lo describe RHF, y no debe emitirse."""
    _, d = descomp
    impares = [(c["index"], c["n_electrons"]) for c in d["clusters"] if c["n_electrons"] % 2]
    assert not impares, f"clusters de capa abierta emitidos como válidos: {impares}"


def test_la_superficie_de_acoplamiento_esta_bien_contada(descomp):
    """El término despreciado se declara con su tamaño, y ese tamaño es correcto.

    Los enlaces que cruzan de un cluster a otro son por dónde pasa la correlación
    que esta aproximación no calcula. Declararla mal sería peor que no
    declararla: daría una falsa idea de cuánto se está dejando fuera.
    """
    smiles, d = descomp
    mol = Chem.MolFromSmiles(smiles)
    de_cluster = {a: c["index"] for c in d["clusters"] for a in c["atom_indices"]}
    esperado = sum(
        1
        for b in mol.GetBonds()
        if de_cluster.get(b.GetBeginAtomIdx()) is not None
        and de_cluster.get(b.GetEndAtomIdx()) is not None
        and de_cluster[b.GetBeginAtomIdx()] != de_cluster[b.GetEndAtomIdx()]
    )
    assert (
        d["n_coupling_bonds"] == esperado
    ), f"declara {d['n_coupling_bonds']} enlaces de acoplamiento y hay {esperado}"


def test_la_cobertura_declarada_es_la_real(descomp):
    """La fracción de molécula que ve el cuántico se cuenta, no se estima."""
    smiles, d = descomp
    mol = Chem.MolFromSmiles(smiles)
    dentro = {a for c in d["clusters"] for a in c["atom_indices"]}
    assert d["n_heavy_in_clusters"] == len(dentro)
    assert abs(d["coverage"] - len(dentro) / mol.GetNumHeavyAtoms()) < 1e-3


def test_partir_ve_mas_molecula_que_recortar_una_region(caso, descomp):
    """La descomposición tiene que APORTAR algo, o no vale lo que cuesta.

    Un método nuevo que mira lo mismo que el viejo, pero cuatro veces más caro,
    es una regresión con buena prensa. Se exige que cubra estrictamente más
    átomos pesados que el recorte de una sola región.
    """
    _, reg = caso
    _, d = descomp
    assert d["n_heavy_in_clusters"] > reg["n_heavy_region"], (
        f"partir cubre {d['n_heavy_in_clusters']} átomos pesados y recortar una "
        f"sola región cubre {reg['n_heavy_region']}: la descomposición no aporta"
    )


def test_la_suma_publicada_es_la_suma_de_los_clusters():
    """El total es la suma de las partes, comprobado con aritmética y no con fe.

    Se construye un resultado sintético para no gastar SQD: lo que se comprueba
    es la contabilidad de `rank_conformers_clusters`, que es donde un signo
    cambiado o un cluster contado dos veces pasaría inadvertido.
    """
    import macrocycle_quantum as m

    llamadas = {"n": 0}
    guardado = m.rank_conformers

    def falso(geoms, **kw):
        llamadas["n"] += 1
        base = [0.0, -0.5, 0.25][: len(geoms)]
        k = llamadas["n"]
        return {
            "method_used": "sqd",
            "energies": [
                {"conformer_id": i, "delta_ev": round(v * k, 4), "below_floor": abs(v * k) < 0.08}
                for i, v in enumerate(base)
            ],
            "degradations": [],
            "n_significant": 2,
        }

    desc = {
        "available": True,
        "coverage": 0.6,
        "n_coupling_bonds": 4,
        "clusters": [
            {
                "index": i,
                "anchor": "amida",
                "anchor_en": "amide",
                "n_heavy_region": 9,
                "n_electrons": 70,
                "charge": 0,
                "geometries": ["g0", "g1", "g2"],
            }
            for i in range(3)
        ],
    }
    m.rank_conformers = falso
    try:
        out = m.rank_conformers_clusters(desc)
    finally:
        m.rank_conformers = guardado

    assert out.get("error") is None, out.get("error")
    assert out["n_clusters_used"] == 3
    for i, e in enumerate(out["energies"]):
        esperado = round(sum(pc["deltas_ev"][i] for pc in out["per_cluster"]), 4)
        assert abs(e["delta_ev"] - esperado) < 1e-6, (
            f"confórmero {i}: publica {e['delta_ev']} y la suma de sus clusters " f"es {esperado}"
        )


def test_un_cluster_sin_energias_no_se_suma_como_cero():
    """Un cluster caído invalida la suma de ese confórmero, no vale cero.

    Sumar cero por un cluster que no respondió es decir que ese trozo de molécula
    no cambia entre confórmeros, que es una afirmación, y no la hizo nadie.
    """
    import macrocycle_quantum as m

    guardado = m.rank_conformers
    estado = {"n": 0}

    def falso(geoms, **kw):
        estado["n"] += 1
        if estado["n"] == 2:
            return {
                "method_used": "sqd",
                "energies": [],
                "error": "no convergió",
                "degradations": [],
            }
        return {
            "method_used": "sqd",
            "energies": [
                {"conformer_id": i, "delta_ev": v, "below_floor": False}
                for i, v in enumerate([0.0, -0.5])
            ],
            "degradations": [],
            "n_significant": 1,
        }

    desc = {
        "available": True,
        "coverage": 0.4,
        "n_coupling_bonds": 1,
        "clusters": [
            {
                "index": i,
                "anchor": "amida",
                "anchor_en": "amide",
                "n_heavy_region": 9,
                "n_electrons": 70,
                "charge": 0,
                "geometries": ["g0", "g1"],
            }
            for i in range(2)
        ],
    }
    m.rank_conformers = falso
    try:
        out = m.rank_conformers_clusters(desc)
    finally:
        m.rank_conformers = guardado

    assert out["n_clusters_failed"] == 1, "el cluster caído no se contabilizó"
    assert out["clusters_failed"], "cayó un cluster y no se dice cuál ni por qué"
    assert out["n_clusters_used"] == 1
