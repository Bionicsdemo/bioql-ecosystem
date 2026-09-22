"""No pipeline stage may return a fabricated number.

THE FAILURE THIS PREVENTS
    `bioql_agent_orchestrator.ProteinEngineeringAgent` ran seven stages and
    reported {"status": "success"}. Behind six of them were `# TODO: Implement`
    bodies returning constants: hotspots [42, 89, 134], epistatic synergies of
    0.87 and 0.92, a variant with "predicted_improvement": "8.5x" and
    "confidence": 0.94, an aggregation propensity of 0.15, a binding affinity
    of "-12.4 kcal/mol", "$450" of synthesis cost. Nothing computed any of it.
    A caller -- or a report, or a slide -- could not tell that output from a
    real run.

    A crash is recoverable. A fabricated number that reports success is not:
    it propagates.

THE RULE, FOR EVERY PIPELINE IN BioQL
    A stage with no engine behind it returns `implemented: False` and None
    where the value would go. Not implemented is not the same as computed,
    exactly as unchecked is not the same as passed.

HOW THE CHECK WORKS
    AST over every module in src/backend, looking for one shape: a function
    whose entire body (docstring removed) is a single `return` of a literal
    expression, whose body also carries a TODO/placeholder comment, and whose
    literal contains numbers or claims success. Docstrings are stripped before
    any text match, so a function that merely DESCRIBES placeholders in prose
    is never flagged for its own explanation.

-- MOLEVERA / BIOQL
"""
import ast
import glob
import os

import pytest

BACKEND = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend"))

TODO_MARKERS = ("todo", "not implemented", "placeholder", "fixme", "stub",
                "will be implemented")

# Stages that are legitimately empty, with the reason they are allowed.
ALLOWED = {
    ("fda_report_layer.py", "_empty_signature_block"):
        "an unsigned signature block is the correct empty value before sign-off",
}


def _strip_docstring(fn):
    body = list(fn.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return body


def _literal_only(node):
    """True when the returned expression is built purely from literals."""
    for n in ast.walk(node):
        if isinstance(n, (ast.Call, ast.Attribute, ast.Name, ast.Subscript,
                          ast.BinOp, ast.Compare, ast.IfExp, ast.ListComp,
                          ast.DictComp, ast.GeneratorExp, ast.Await)):
            return False
    return True


def _todo_comments(lines, fn):
    """TODO-ish comments inside the function body. Never reads the docstring."""
    lo = fn.lineno
    hi = getattr(fn, "end_lineno", fn.lineno)
    found = []
    for i in range(lo - 1, min(hi, len(lines))):
        if "#" not in lines[i]:
            continue
        comment = lines[i].split("#", 1)[1].strip().lower()
        if any(m in comment for m in TODO_MARKERS):
            found.append(comment[:80])
    return found


def _scan(path):
    try:
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
    except Exception:
        return []
    lines = src.splitlines()
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = _strip_docstring(fn)
        if len(body) != 1 or not isinstance(body[0], ast.Return):
            continue
        if body[0].value is None or not _literal_only(body[0].value):
            continue
        todos = _todo_comments(lines, fn)
        if not todos:
            continue
        numbers = [n.value for n in ast.walk(body[0].value)
                   if isinstance(n, ast.Constant)
                   and isinstance(n.value, (int, float))
                   and not isinstance(n.value, bool)]
        dumped = ast.dump(body[0].value)
        claims_success = "'success'" in dumped or '"success"' in dumped
        if not numbers and not claims_success:
            continue
        out.append({"file": os.path.basename(path), "func": fn.name,
                    "line": fn.lineno, "numbers": numbers[:6],
                    "claims_success": claims_success, "todo": todos[0]})
    return out


def _all_offenders():
    hits = []
    for path in sorted(glob.glob(os.path.join(BACKEND, "*.py"))):
        for h in _scan(path):
            if (h["file"], h["func"]) in ALLOWED:
                continue
            hits.append(h)
    return hits


def test_no_stage_returns_a_fabricated_number():
    offenders = _all_offenders()
    if offenders:
        report = "\n".join(
            "  %s:%d %s -> %s%s  (%s)"
            % (o["file"], o["line"], o["func"], o["numbers"],
               " + status=success" if o["claims_success"] else "", o["todo"])
            for o in offenders)
        pytest.fail(
            "%d unimplemented stage(s) return fabricated values:\n%s\n\n"
            "Return not_implemented(...) with None instead. A number nobody "
            "computed is worse than an error, because it ships."
            % (len(offenders), report))


def test_the_scanner_still_detects_the_original_shape(tmp_path):
    """A guard that cannot fail is not a guard.

    Rebuilds the exact shape that shipped in ProteinEngineeringAgent and
    asserts the scanner catches it.
    """
    mod = tmp_path / "regression_shape.py"
    mod.write_text(
        "def _protein_admet(self, variants):\n"
        '    """Protein ADMET prediction"""\n'
        "    # TODO: Implement protein ADMET\n"
        "    return {\n"
        '        "immunogenicity": "low",\n'
        '        "aggregation_propensity": 0.15,\n'
        '        "stability_score": 8.2\n'
        "    }\n")
    hits = _scan(str(mod))
    assert len(hits) == 1, hits
    assert hits[0]["func"] == "_protein_admet"
    assert 0.15 in hits[0]["numbers"] and 8.2 in hits[0]["numbers"]


def test_prose_about_placeholders_is_not_flagged(tmp_path):
    """The docstring must be stripped before any text match, so a function that
    explains placeholders in prose is not accused of being one."""
    mod = tmp_path / "prose.py"
    mod.write_text(
        "def describe():\n"
        '    """This returns a TODO placeholder stub value of 0.87, in theory."""\n'
        "    return 1\n")
    assert _scan(str(mod)) == []


def test_the_orchestrator_contract_is_in_place():
    """bioql_agent_orchestrator must expose the not-implemented contract."""
    import sys
    sys.path.insert(0, BACKEND)
    import bioql_agent_orchestrator as O

    rec = O.not_implemented("x", "y", ("a", "b"))
    assert rec["implemented"] is False
    assert rec["value"] is None and rec["a"] is None and rec["b"] is None
    assert O.stage_ran(rec) is False
    assert O.stage_ran([]) is False, "no variants is not a computed stage"
    assert O.stage_ran({"binding_affinity": -12.4}) is True


def test_an_agent_never_reports_success_for_stages_that_did_not_run():
    """Status must track what COMPUTED. Some stages are wired to real engines
    now (ESM-2, developability) and some are not (epistasis, assembly), so the
    honest answer is 'partial' -- never 'success'."""
    import sys
    sys.path.insert(0, BACKEND)
    import bioql_agent_orchestrator as O

    out = O.BioQLOrchestrator().process(
        {"sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAV",
         "max_mutations": 3})
    res = out["results"]
    assert res["status"] in ("not_implemented", "partial"), res["status"]
    assert res["stages_not_implemented"], (
        "stages with no engine must be named, not folded into success")
    # None of the original fabricated constants may reappear.
    blob = str(res)
    for ghost in ("-12.4 kcal/mol", "8.5x", "$450", '"optimized"'):
        assert ghost not in blob, "fabricated value returned: %s" % ghost


def test_every_variant_carries_its_scorer_and_its_caveat():
    """A ranked variant with no attributable scorer is indistinguishable from
    an invented one, which is how the original `8.5x` shipped."""
    import sys
    sys.path.insert(0, BACKEND)
    import bioql_agent_orchestrator as O

    agent = O.ProteinEngineeringAgent()
    variants = agent._generate_variants(
        "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRV", {}, 3)
    for v in variants:
        assert isinstance(v.get("esm2_log_odds"), float)
        assert "ESM-2" in v.get("scorer", "")
        assert v.get("caveat"), "a triage ordering must say it is one"
    if variants:
        scores = [v["esm2_log_odds"] for v in variants]
        assert scores == sorted(scores, reverse=True), "must be ranked"

# MOLEVERA / BIOQL
