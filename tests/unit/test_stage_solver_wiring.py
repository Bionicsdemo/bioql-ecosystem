"""The solver is wired into pipelines. These guard how it is wired.

Connecting a decision layer to a running pipeline is the riskiest change in
this work: it can quietly stop doing things. So the wiring itself is tested,
not just the solver:

    1. OFF by default. An unset environment changes nothing and costs nothing.
    2. Shadow mode decides and records, and still runs everything.
    3. A broken or absent solver runs the stage.
    4. An enforced skip writes a visible stage entry, never a silent absence.

-- MOLEVERA / BIOQL
"""
import os
import re
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import stage_solver as SS  # noqa: E402
import typesafe_client as TS  # noqa: E402

MONOLITH = os.path.join(BACKEND, "script_executor_server.py")

CAND = {"name": "K-1", "smiles": "CCO", "composite_score": 0.6,
        "safety_gate": {"passed": True, "severity": "PASS", "flags": []}}


def _src():
    with open(MONOLITH, encoding="utf-8") as fh:
        return fh.read()


def _judgment(monkeypatch, worth, enough):
    def _ask(state, questions, **kw):
        return {"answers": {
            "worth_the_compute": {"type": "noul", "noul": worth},
            "evidence_sufficient": {"type": "noul", "noul": enough},
        }, "model": "jev-test", "usage": {"input_tokens": 50, "output_tokens": 5}}
    monkeypatch.setattr(TS, "ask", _ask)


# ───────────────────────── 1. off by default ──────────────────────────────

def test_the_default_is_off(monkeypatch):
    monkeypatch.delenv(SS.MODE_ENV, raising=False)
    assert SS.mode() == "off"


def test_off_changes_nothing_and_asks_nothing(monkeypatch):
    monkeypatch.delenv(SS.MODE_ENV, raising=False)

    def _explode(*a, **k):  # pragma: no cover
        raise AssertionError("the solver spent a request while switched off")

    monkeypatch.setattr(TS, "ask", _explode)
    result = {"stages": {}}
    assert SS.gate("5b_protenix", CAND, result) is True
    assert "stage_solver" not in result, "off must leave no trace"


def test_an_unrecognised_mode_falls_back_to_off(monkeypatch):
    monkeypatch.setenv(SS.MODE_ENV, "yes-please")
    assert SS.mode() == "off"


# ────────────────────────── 2. shadow mode ────────────────────────────────

def test_shadow_records_the_decision_but_still_runs(monkeypatch):
    monkeypatch.setenv(SS.MODE_ENV, "shadow")
    _judgment(monkeypatch, worth=0.02, enough=0.99)   # a clear "skip"
    result = {"stages": {}}
    assert SS.gate("5b_protenix", CAND, result) is True, (
        "shadow mode must never change what runs")
    dec = result["stage_solver"]["decisions"][0]
    assert dec["action"] == "skip" and dec["enforced"] is False
    assert result["stages"] == {}, "shadow must not write stage entries"


def test_shadow_decisions_accumulate_for_review(monkeypatch):
    monkeypatch.setenv(SS.MODE_ENV, "shadow")
    _judgment(monkeypatch, worth=0.9, enough=0.1)
    result = {"stages": {}}
    for s in ("5b_protenix", "5c_ewf_sqd", "5c_complexa"):
        SS.gate(s, CAND, result)
    decs = result["stage_solver"]["decisions"]
    assert [d["stage"] for d in decs] == ["5b_protenix", "5c_ewf_sqd", "5c_complexa"]
    assert SS.summarize(decs)["judgment_tokens_spent"] == 165


# ─────────────────── 3. failure always means "run" ────────────────────────

def test_a_solver_error_runs_the_stage(monkeypatch):
    monkeypatch.setenv(SS.MODE_ENV, "enforce")

    def _boom(*a, **k):
        raise RuntimeError("solver exploded")

    monkeypatch.setattr(SS, "decide_stage", _boom)
    result = {"stages": {}}
    assert SS.gate("5b_protenix", CAND, result) is True
    assert "Solver error" in result["stage_solver"]["decisions"][0]["reason"]


def test_the_pipeline_helper_runs_when_the_module_is_missing():
    """_solver_gate must swallow ImportError and return True."""
    src = _src()
    start = src.find("def _solver_gate(")
    assert start != -1, "_solver_gate helper not found in the pipeline"
    nxt = re.search(r"\ndef ", src[start + 1:])
    body = src[start:start + 1 + (nxt.start() if nxt else 0)]
    assert "except Exception" in body, "the helper does not catch failures"
    # The last thing the failure path does must be to allow the stage.
    tail = [ln.strip() for ln in body.strip().splitlines() if ln.strip()]
    assert tail[-1] == "return True", (
        "the failure path must run the stage, not skip it; got %r" % tail[-1])


# ──────────────────── 4. an enforced skip is visible ──────────────────────

def test_an_enforced_skip_writes_a_visible_stage_entry(monkeypatch):
    monkeypatch.setenv(SS.MODE_ENV, "enforce")
    _judgment(monkeypatch, worth=0.02, enough=0.99)
    result = {"stages": {}}
    assert SS.gate("5b_protenix", CAND, result) is False
    entry = result["stages"]["5b_protenix"]
    assert entry["status"] == "skipped_by_solver"
    assert entry["reason"]
    assert "absent" in entry["fields_left_absent"], (
        "a stage that simply vanished is indistinguishable from one that failed")


def test_enforce_still_cannot_skip_a_safety_stage(monkeypatch):
    monkeypatch.setenv(SS.MODE_ENV, "enforce")
    _judgment(monkeypatch, worth=0.01, enough=0.99)
    result = {"stages": {}}
    assert SS.gate("3_toxicology", CAND, result) is True


# ─────────────────────────── the wiring itself ────────────────────────────

WIRED = ("5b_protenix", "5c_ewf_sqd", "5c_complexa")


@pytest.mark.parametrize("stage", WIRED)
def test_the_expensive_stage_is_gated(stage):
    assert '_solver_gate(\n                "%s"' % stage in _src(), (
        "%s lost its solver gate" % stage)


@pytest.mark.parametrize("stage", WIRED)
def test_every_gated_stage_is_discretionary(stage):
    assert stage in SS.DISCRETIONARY_STAGES
    assert stage not in SS.SAFETY_STAGES


def test_no_safety_stage_was_gated():
    src = _src()
    for stage in SS.SAFETY_STAGES:
        assert '_solver_gate(\n                "%s"' % stage not in src, (
            "a safety stage was put behind the solver: %s" % stage)
