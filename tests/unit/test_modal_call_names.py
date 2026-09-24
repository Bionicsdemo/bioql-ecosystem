"""Llamadas a Modal que apuntaban a funciones inexistentes (consulta real a Modal, 2026-09-24).

`modal.Function.from_name()` es perezoso en modal>=1.x: devuelve un handle sin consultar al
servidor y nunca falla, asi que un nombre equivocado solo aparece al llamar. Estos tests fijan
los nombres que SI existen en produccion y que las sondas hidraten. No tocan la red: usan un
modulo `modal` falso o parchean la capa de computo.
"""

import ast
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "backend"))


def _fake_modal(existing):
    calls = []

    class _Fn:
        def __init__(self, app, name):
            self.app, self.name = app, name
            calls.append((app, name))

        def hydrate(self):
            if (self.app, self.name) not in existing:
                raise LookupError(f"{self.app}::{self.name} not found")
            return self

    mod = types.ModuleType("modal")
    mod.Function = types.SimpleNamespace(from_name=lambda app, name: _Fn(app, name))
    return mod, calls


def test_la_sonda_cudaq_hidrata_la_funcion_que_existe(monkeypatch):
    import sqd_cascade as S

    fake, calls = _fake_modal({("bioql-quantum-gpu", "cudaq_statevector")})
    monkeypatch.setitem(sys.modules, "cudaq", None)  # sin CUDA-Q local: fuerza la ruta Modal
    monkeypatch.setitem(sys.modules, "modal", fake)
    r = S.probe_cudaq()
    assert calls == [("bioql-quantum-gpu", "cudaq_statevector")]
    assert r["available"] is True and r["is_real_hardware"] is False


def test_la_sonda_cudaq_no_se_da_por_disponible_sin_la_app(monkeypatch):
    import sqd_cascade as S

    fake, _ = _fake_modal(set())
    monkeypatch.setitem(sys.modules, "cudaq", None)
    monkeypatch.setitem(sys.modules, "modal", fake)
    r = S.probe_cudaq()
    assert r["available"] is False and "no resoluble" in r["reason"]


def test_el_respaldo_de_plegado_llama_funciones_desplegadas(monkeypatch):
    import esmfold2_backend
    import modal_compute_layer as M
    import nir_protein_engine as N

    monkeypatch.setattr(
        esmfold2_backend,
        "predict_structure_esmfold2",
        lambda seq: {"success": False, "error": "backend caido"},
    )
    llamadas = []

    def falso_run(key, *args, **kw):
        llamadas.append((key, args))
        if key == "fold_protein":
            return {"available": False, "where_it_ran": "unavailable", "why": "sin presupuesto"}
        return {
            "available": True,
            "where_it_ran": "modal",
            "app": "bioql-boltz2",
            "function": "predict",
            "result": {
                "success": True,
                "pdb": "ATOM      1  N   MET A   1",
                "confidence": {"plddt": 0.71},
            },
        }

    monkeypatch.setattr(M, "run", falso_run)
    seq = "M" + "ACDEFGHIKLMNPQRSTVWY" * 3
    r = N.fold_sequence(seq, allow_external_msa=False)
    assert [k for k, _ in llamadas] == ["fold_protein", "fold_complex"]
    assert llamadas[0][1] == (seq,)
    assert llamadas[1][1] == ({"protein_sequence": seq, "use_msa_server": False},)
    assert r["available"] and r["backend"] == "bioql-boltz2::predict" and r["plddt"] == 0.71


def _app_names():
    names = {}
    for base in (REPO / "src" / "backend", REPO / "src" / "modal"):
        for f in base.rglob("*.py"):
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("App", "Stub")
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "modal"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    names.setdefault(node.args[0].value, set()).add(str(f.relative_to(REPO)))
    return names


def test_cada_app_modal_se_declara_en_un_solo_archivo():
    """Dos archivos con el mismo nombre de app: desplegar uno reemplaza al otro."""
    names = _app_names()
    dup = {k: sorted(v) for k, v in names.items() if len(v) > 1}
    assert not dup, f"apps de Modal declaradas en mas de un archivo: {dup}"
    assert names.get("bioql-esmfold2") == {"src/backend/modal_esmfold2.py"}
    assert names.get("bioql-esmfold2-service") == {"src/modal/esmfold2_modal.py"}


def test_parabricks_no_acepta_una_referencia_vacia(tmp_path, monkeypatch):
    pytest.importorskip("modal")
    import modal_parabricks as P

    monkeypatch.setattr(P, "_REF_DIR", str(tmp_path))
    monkeypatch.setattr(P, "_MIN_REFERENCE_BYTES", 100)
    monkeypatch.setattr(P, "ref_vol", types.SimpleNamespace(commit=lambda: None))
    monkeypatch.setattr(P, "_bwa_path", lambda: "bwa")
    monkeypatch.setattr(P, "_bwa_env", lambda: {})
    name = P._REFERENCES["GRCh38"]["fasta_name"]
    fasta = tmp_path / name
    fasta.write_bytes(b"")  # lo que habia en el volumen vivo: 0 bytes
    (tmp_path / (name + ".fai")).write_text("indice viejo")
    hechos = []

    def falso_run(cmd, **kw):
        hechos.append(cmd[0])
        if cmd[0] == "wget":
            Path(cmd[3]).write_bytes(b">chr1\n" + b"A" * 200)
        elif cmd[0] == "samtools":
            Path(cmd[2] + ".fai").write_text("chr1\t200\n")
        elif cmd[0] == "bwa":
            Path(cmd[2] + ".bwt").write_text("x")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", falso_run)
    P._ensure_reference("GRCh38")
    assert hechos[:2] == ["wget", "samtools"], hechos
    assert fasta.stat().st_size > 100
    assert (tmp_path / (name + ".fai")).read_text() == "chr1\t200\n"


def test_parabricks_rechaza_una_descarga_incompleta(tmp_path, monkeypatch):
    pytest.importorskip("modal")
    import modal_parabricks as P

    monkeypatch.setattr(P, "_REF_DIR", str(tmp_path))
    monkeypatch.setattr(P, "_MIN_REFERENCE_BYTES", 100)
    monkeypatch.setattr(P, "ref_vol", types.SimpleNamespace(commit=lambda: None))

    def falso_run(cmd, **kw):
        if cmd[0] == "wget":
            Path(cmd[3]).write_bytes(b">chr1\nAC")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", falso_run)
    with pytest.raises(RuntimeError, match="incomplete"):
        P._ensure_reference("GRCh38")
