"""AVAS sobre "2pz" y la orientacion del plano conjugado (MEDIDO 2026-09-24).

"C 2pz" en PySCF es el p del eje z GLOBAL. Un cromoforo en el marco de un
cristal llega inclinado, y el bloque "pi" de AVAS deja de ser pi: en LBV/4E04 la
ventana CAS(8,8) contenia el 0.8 % del HOMO y daba S1 = 14.35 eV. Estos tests
fijan la correccion (pi_orientation) sobre butadieno, que es rapido y cuyo HOMO
y LUMO no son degenerados.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend"))

from pi_orientation import orient_atom_string, orient_pi_plane  # noqa: E402

# trans-1,3-butadieno en el plano xy
BUTADIENO = [
    ("C", (0.0, 0.0, 0.0)),
    ("C", (1.34, 0.0, 0.0)),
    ("C", (2.07, 1.26, 0.0)),
    ("C", (3.41, 1.26, 0.0)),
    ("H", (-0.55, -0.93, 0.0)),
    ("H", (-0.55, 0.93, 0.0)),
    ("H", (1.89, -0.93, 0.0)),
    ("H", (1.52, 2.19, 0.0)),
    ("H", (3.96, 0.33, 0.0)),
    ("H", (3.96, 2.19, 0.0)),
]
SYM = [s for s, _ in BUTADIENO]
X0 = np.array([c for _, c in BUTADIENO])


def _rot(axis, deg):
    a = np.radians(deg)
    k = np.array(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


INCLINADO = X0 @ _rot([1, 1, 0], 90).T + np.array([4.0, -2.0, 7.0])


def _dist(A, B=None):
    B = A if B is None else B
    return np.linalg.norm(A[:, None] - B[None], axis=-1)


def test_la_rotacion_es_rigida_y_deja_el_plano_conjugado_en_xy():
    cargas = np.array([[10.0, 3.0, -2.0], [-5.0, 8.0, 1.0], [2.0, -7.0, 9.0]])
    X, E, info = orient_pi_plane(SYM, INCLINADO, cargas)
    carbonos = X[[i for i, s in enumerate(SYM) if s == "C"]]
    assert np.ptp(carbonos[:, 2]) < 1e-8, "los carbonos conjugados deben quedar en un plano z = cte"
    assert np.allclose(_dist(X), _dist(INCLINADO), atol=1e-10), "la rotacion debe ser rigida"
    assert np.allclose(
        _dist(X, E), _dist(INCLINADO, cargas), atol=1e-10
    ), "las cargas deben rotar con la molecula"
    assert info["from_conjugated_cluster"] and info["n_plane_atoms"] == 4
    assert abs(info["tilt_before_deg"] - 90.0) < 1e-6


def test_el_formato_de_geometria_se_conserva():
    geom = "; ".join(f"{s} {x} {y} {z}" for s, (x, y, z) in zip(SYM, INCLINADO))
    out, _, _ = orient_atom_string(geom)
    partes = [t.split() for t in out.split(";")]
    assert [p[0] for p in partes] == SYM
    X = np.array([[float(v) for v in p[1:4]] for p in partes])
    assert np.allclose(_dist(X), _dist(INCLINADO), atol=1e-5)


def _ventana_avas(Y, k=1):
    """AVAS 'C 2pz' (umbral 0.2) + ventana de frontera k; devuelve el tamano de AVAS,
    la fraccion del HOMO y del LUMO de RHF dentro de la ventana, y la energia RHF."""
    from pyscf import gto, scf
    from pyscf.mcscf import avas

    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(SYM, Y)], basis="sto-3g", verbose=0)
    mf = scf.RHF(mol).run()
    nocc = mol.nelectron // 2
    norb, ne, orbs = avas.avas(mf, ["C 2pz"], threshold=0.2, minao="minao", verbose=0)
    ne = int(ne if np.isscalar(ne) else sum(ne))
    nc = (mol.nelectron - ne) // 2 + ne // 2 - k
    Cw = orbs[:, nc : nc + 2 * k]
    S = mf.get_ovlp()
    P = Cw @ Cw.T @ S

    def dentro(mo):
        return float(mo @ S @ (P @ mo))

    return (
        int(norb),
        ne,
        dentro(mf.mo_coeff[:, nocc - 1]),
        dentro(mf.mo_coeff[:, nocc]),
        float(mf.e_tot),
    )


def test_sin_orientar_avas_2pz_pierde_el_homo_y_orientado_lo_recupera():
    pytest.importorskip("pyscf")
    crudo = _ventana_avas(INCLINADO)
    Xo, _, _ = orient_pi_plane(SYM, INCLINADO)
    orientado = _ventana_avas(Xo)
    # el fallo que se corrige: en el marco inclinado el HOMO no esta en la ventana
    assert (
        crudo[2] < 0.5
    ), f"se esperaba el fallo en el marco inclinado, HOMO dentro = {crudo[2]:.3f}"
    # la correccion: el sistema pi del butadieno son 4 orbitales y 4 electrones
    assert orientado[:2] == (4, 4)
    assert orientado[2] > 0.99 and orientado[3] > 0.99
    # y la fisica no cambia: misma energia RHF
    assert abs(crudo[4] - orientado[4]) < 1e-8


def test_la_plantilla_casci_del_diferencial_orienta_antes_de_avas():
    """Corre la plantilla real _QUANTUM en su subproceso con la ruta CASCI+AVAS."""
    pytest.importorskip("pyscf")
    import nir_differential as D
    from pyscf import fci, gto, mcscf, scf
    from pyscf.mcscf import avas

    geom = "; ".join(f"{s} {x} {y} {z}" for s, (x, y, z) in zip(SYM, INCLINADO))
    payload = {
        "geom": geom,
        "basis": "sto-3g",
        "charge": 0,
        "coords": [[60.0, 60.0, 60.0]],
        "charges": [0.0],
        "method": "casci",
        "frontier_k": 1,
        "sites": [],
        "sel": {},
    }
    r = D._run(D._QUANTUM, payload, timeout=600)
    assert r.get("ok"), r

    def s1(Y):
        mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(SYM, Y)], basis="sto-3g", verbose=0)
        mf = scf.RHF(mol).run()
        norb, ne, orbs = avas.avas(mf, ["C 2pz"], threshold=0.2, minao="minao", verbose=0)
        ne = int(ne if np.isscalar(ne) else sum(ne))
        mc = mcscf.CASCI(mf, 2, 2)
        mc.mo_coeff = orbs
        mc.ncore = (mol.nelectron - ne) // 2 + ne // 2 - 1
        mc.fcisolver = fci.direct_spin1.FCI()
        fci.addons.fix_spin_(mc.fcisolver, shift=0.5, ss=0)
        mc.fcisolver.nroots = 2
        mc.verbose = 0
        e = mc.kernel()[0]
        return float((e[1] - e[0]) * 27.211386245988)

    Xo, _, _ = orient_pi_plane(SYM, INCLINADO)
    assert (
        abs(r["s1_wt_ev"] - s1(Xo)) < 1e-4
    ), "la plantilla debe calcular sobre la geometria orientada"
    assert abs(r["s1_wt_ev"] - s1(INCLINADO)) > 0.1, "y el marco inclinado debe dar otro numero"


def test_la_cascada_entrega_a_avas_la_geometria_orientada(monkeypatch):
    import excited_state_pipeline as ESP
    import nir_electronic_cascade as C

    visto = {}

    def falso(**kw):
        visto["atom"] = kw["designs"][0]["atom"]
        return {"error": "stub: solo se inspecciona la geometria"}

    monkeypatch.setattr(ESP, "run_pipeline_isolated", falso)
    geom = "; ".join(f"{s} {x} {y} {z}" for s, (x, y, z) in zip(SYM, INCLINADO))
    out = C.electronic_cascade(geom, allow_qpu=False, budget_s=5)
    X = np.array([[float(v) for v in t.split()[1:4]] for t in visto["atom"].split(";")])
    carbonos = X[[i for i, s in enumerate(SYM) if s == "C"]]
    assert np.ptp(carbonos[:, 2]) < 1e-5
    assert out["pi_orientation"]["from_conjugated_cluster"]
