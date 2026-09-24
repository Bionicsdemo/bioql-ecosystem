"""The routing table must not claim an app it cannot reach.

On 2026-09-19 `app_status()` reported 8/8 apps deployed, including one whose
Modal app had not been created yet. Cause: `Function.from_name()` is lazy in
modal >=1.x -- it builds a handle without contacting the server, so the
try/except around it could never fail. Four of five registrations also named
functions that do not exist in the modules that define those apps; every one of
them had been falling back to the local engine at call time.

These tests are static (no network, no Modal account) and guard both halves:
the names in APPS must match the source, and a lookup failure must show up as
NOT deployed.

-- MOLEVERA / BIOQL
"""

import ast
import glob
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import modal_compute_layer as MC  # noqa: E402


def _apps_defined_in_source():
    """{modal app name: (module, {function names}, {class names})} from the source."""
    found = {}
    for path in glob.glob(os.path.join(BACKEND, "modal_*.py")):
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except Exception:
            continue
        app_name = None
        functions, classes = set(), set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "App"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                app_name = node.args[0].value
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    if isinstance(target, ast.Attribute) and target.attr == "function":
                        functions.add(node.name)
            if isinstance(node, ast.ClassDef):
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    if isinstance(target, ast.Attribute) and target.attr == "cls":
                        classes.add(node.name)
        if app_name:
            found[app_name] = (os.path.basename(path), functions, classes)
    return found


SOURCE_APPS = _apps_defined_in_source()


@pytest.mark.parametrize("key", sorted(MC.APPS))
def test_every_registration_names_a_function_that_exists(key):
    spec = MC.APPS[key]
    src = SOURCE_APPS.get(spec["app"])
    if src is None:
        pytest.skip(f"no module in src/backend defines modal app {spec['app']!r}")
    module, functions, classes = src
    if spec.get("kind") == "cls":
        assert (
            spec["cls"] in classes or not classes
        ), f"{key}: {module} defines no @app.cls named {spec['cls']!r}"
        return
    assert spec["fn"] in functions, (
        f"{key}: {module} defines no @app.function named {spec['fn']!r} "
        f"(it has: {sorted(functions)}). A wrong name here does not error -- it "
        f"silently routes the pipeline to the local fallback."
    )


def test_a_lookup_failure_reads_as_not_deployed(monkeypatch):
    def boom(spec):
        raise RuntimeError("App not found in environment 'main'")

    monkeypatch.setattr(MC, "_handle", boom)
    st = MC.app_status()
    assert st["n_deployed"] == 0, "nothing resolves, so nothing may be claimed"
    for entry in st["apps"].values():
        assert entry["deployed"] is False
        assert "App not found" in entry["reason"]


def test_every_registered_app_is_actually_looked_up(monkeypatch):
    calls = []
    monkeypatch.setattr(MC, "_handle", lambda spec: calls.append(spec["app"]))
    MC.app_status()
    assert len(calls) == len(MC.APPS), "every registered app must be looked up"


def test_the_lookup_hydrates_rather_than_trusting_a_lazy_handle():
    """The regression itself: from_name alone never contacts the server.

    Checked on the AST of the real `_handle`, with the docstring stripped, so
    the guard cannot be satisfied by prose that merely mentions hydration.
    """
    import inspect

    tree = ast.parse(inspect.getsource(MC).lstrip())
    handle = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_handle")
    if (
        handle.body
        and isinstance(handle.body[0], ast.Expr)
        and isinstance(handle.body[0].value, ast.Constant)
    ):
        handle.body = handle.body[1:]
    hydrates = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "hydrate"
        for n in ast.walk(handle)
    )
    assert hydrates, "_handle must call .hydrate(); from_name() alone proves nothing"


def test_a_job_with_no_local_equivalent_never_reports_a_local_run():
    """LDDM has no honest CPU stand-in, so an unavailable GPU must say
    unavailable rather than quietly substituting something weaker."""
    spec = MC.APPS["ligand_design"]
    assert spec["fallback"] is None
    r = MC.run("ligand_design", {}, local_fn=None)
    assert r["where_it_ran"] in ("unavailable",) + MC.BACKENDS
    if r["where_it_ran"] == "unavailable":
        assert r["no_local_equivalent"] is True
        assert r["why"]


def test_an_unknown_job_is_refused_not_guessed():
    r = MC.run("no_such_job")
    assert r["available"] is False
    assert r["where_it_ran"] == "unavailable"
    assert "known" in r


# MOLEVERA / BIOQL
