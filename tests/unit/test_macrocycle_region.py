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
