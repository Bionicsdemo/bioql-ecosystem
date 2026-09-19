"""An adaptive solver is safe here only if a skip stays a gap.

The solver decides what to RUN as evidence accumulates. The danger is obvious:
a system that decides to skip work could quietly shrink an analysis, or worse,
leave something behind that looks like a result. So three properties are
enforced rather than documented:

    1. Safety stages always run. No judgment, no budget, can skip them.
    2. A skip leaves the fields ABSENT, with a reason. Never a default.
    3. An unavailable judgment runs the stage. Silence never saves money.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import stage_solver as SS  # noqa: E402
import typesafe_client as TS  # noqa: E402


def _answers(monkeypatch, worth=None, enough=None, proxy=None):
    def _ask(state, questions, **kw):
        a = {}
        if worth is not None:
            a["worth_the_compute"] = {"type": "noul", "noul": worth}
        if enough is not None:
            a["evidence_sufficient"] = {"type": "noul", "noul": enough}
        if proxy is not None and "proxy_suffices" in questions:
            a["proxy_suffices"] = {"type": "noul", "noul": proxy}
        return {"answers": a, "model": "jev-test",
                "usage": {"input_tokens": 100, "output_tokens": 10}}
    monkeypatch.setattr(TS, "ask", _ask)


CAND = {"name": "KRAS-007", "target": "KRAS", "composite_score": 0.62,
        "safety_gate": {"passed": True, "severity": "PASS", "flags": []}}


# ───────────────── 1. safety is not negotiable ────────────────────────────

@pytest.mark.parametrize("stage", sorted(SS.SAFETY_STAGES))
def test_a_safety_stage_always_runs(monkeypatch, stage):
    """Even told it is pointless, even with no budget left."""
    _answers(monkeypatch, worth=0.01, enough=0.99)
    d = SS.decide_stage(stage, CAND, {}, budget_remaining=0)
    assert d.action == "run" and d["decided_by"] == "rule"


def test_no_safety_stage_is_listed_as_discretionary():
    assert not (SS.SAFETY_STAGES & set(SS.DISCRETIONARY_STAGES)), (
        "a safety stage became skippable")


def test_the_model_is_never_consulted_for_a_safety_stage(monkeypatch):
    def _explode(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("a judgment was requested for a safety stage")
    monkeypatch.setattr(TS, "ask", _explode)
    for stage in sorted(SS.SAFETY_STAGES)[:4]:
        assert SS.decide_stage(stage, CAND, {}).action == "run"


# ───────────────── 2. a skip is a gap, never a value ──────────────────────

def test_a_skip_records_that_the_fields_are_absent(monkeypatch):
    _answers(monkeypatch, worth=0.05, enough=0.95)
    d = SS.decide_stage("5b_protenix", CAND, {})
    assert d.action == "skip"
    assert "absent" in d["fields_left_absent"]
    assert "not zero" in d["fields_left_absent"]
    assert "not estimated" in d["fields_left_absent"]


def test_no_decision_ever_carries_a_scientific_value(monkeypatch):
    """The solver returns actions. A value here would be a fabricated result."""
    _answers(monkeypatch, worth=0.05, enough=0.95)
    for stage in ("5b_protenix", "5c_ewf_sqd", "9_docking"):
        d = SS.decide_stage(stage, CAND, {})
        leaked = set(k.lower() for k in d) & TS.FORBIDDEN_TARGETS
        assert not leaked, "decision leaked scientific field(s): %s" % leaked


def test_the_questions_asked_clear_the_text_only_boundary(monkeypatch):
    captured = {}

    def _ask(state, questions, **kw):
        captured["q"] = list(questions)
        return {"answers": {}, "model": "t", "usage": {}}

    monkeypatch.setattr(TS, "ask", _ask)
    SS.decide_stage("5c_ewf_sqd", CAND, {})
    for qid in captured["q"]:
        TS.assert_text_only_target(qid)


# ─────────── 3. an absent judgment never reduces the analysis ─────────────

def test_an_unavailable_judgment_runs_the_stage(monkeypatch):
    def _fail(*a, **k):
        raise TS.TypeSafeError("service down")
    monkeypatch.setattr(TS, "ask", _fail)
    d = SS.decide_stage("5b_protenix", CAND, {})
    assert d.action == "run", "silence must not become a decision to skip"
    assert d["decided_by"] == "rule"


def test_an_unconfigured_service_runs_the_stage(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(TS, "TOKEN_FILE", str(tmp_path / "none.json"))
    assert SS.decide_stage("9_docking", CAND, {}).action == "run"


def test_uncertainty_runs_the_stage(monkeypatch):
    """An unnecessary run costs compute; a wrong skip costs a blind spot."""
    _answers(monkeypatch, worth=0.50, enough=0.50)
    assert SS.decide_stage("5b_protenix", CAND, {}).action == "run"


def test_only_a_clear_judgment_skips(monkeypatch):
    # Not worth it, but evidence not settled -> still runs.
    _answers(monkeypatch, worth=0.10, enough=0.30)
    assert SS.decide_stage("5b_protenix", CAND, {}).action == "run"
    # Not worth it AND settled -> skips.
    _answers(monkeypatch, worth=0.10, enough=0.90)
    assert SS.decide_stage("5b_protenix", CAND, {}).action == "skip"


# ─────────────────────── the deterministic rules ──────────────────────────

def test_budget_exhaustion_is_arithmetic_not_judgment(monkeypatch):
    def _explode(*a, **k):  # pragma: no cover
        raise AssertionError("consulted the model about arithmetic")
    monkeypatch.setattr(TS, "ask", _explode)
    d = SS.decide_stage("5b_protenix", CAND, {}, budget_remaining=0)
    assert d.action == "skip" and d["decided_by"] == "rule"


def test_a_missing_prerequisite_is_a_fact_not_a_judgment(monkeypatch):
    def _explode(*a, **k):  # pragma: no cover
        raise AssertionError("consulted the model about a missing input")
    monkeypatch.setattr(TS, "ask", _explode)
    d = SS.decide_stage("9_docking", CAND, {}, requires=["7b_protenix_structure"])
    assert d.action == "skip" and d["decided_by"] == "rule"
    assert "7b_protenix_structure" in d["reason"]


def test_a_candidate_that_failed_safety_does_not_get_gpu_time(monkeypatch):
    def _explode(*a, **k):  # pragma: no cover
        raise AssertionError("consulted the model about an already-failed candidate")
    monkeypatch.setattr(TS, "ask", _explode)
    failed = dict(CAND, safety_gate={"passed": False, "severity": "CRITICAL",
                                     "flags": ["GHS acute toxicity"]})
    d = SS.decide_stage("5b_protenix", failed, {})
    assert d.action == "skip" and d["decided_by"] == "rule"


def test_a_non_discretionary_stage_just_runs(monkeypatch):
    def _explode(*a, **k):  # pragma: no cover
        raise AssertionError("consulted the model about a stage it does not own")
    monkeypatch.setattr(TS, "ask", _explode)
    assert SS.decide_stage("1_target_analysis", CAND, {}).action == "run"


# ──────────────────────────── proxy routing ───────────────────────────────

def test_a_cheaper_proxy_is_chosen_when_it_suffices(monkeypatch):
    _answers(monkeypatch, worth=0.80, enough=0.20, proxy=0.90)
    d = SS.decide_stage("5c_ewf_sqd", CAND, {})
    assert d.action == "run_proxy" and "simulator" in d["reason"]


def test_no_proxy_is_offered_where_none_exists(monkeypatch):
    captured = {}

    def _ask(state, questions, **kw):
        captured["q"] = list(questions)
        return {"answers": {}, "model": "t", "usage": {}}

    monkeypatch.setattr(TS, "ask", _ask)
    SS.decide_stage("5b_protenix", CAND, {})  # GPU folding has no proxy
    assert "proxy_suffices" not in captured["q"]


# ───────────────────────────── the audit trail ────────────────────────────

def test_every_decision_records_what_it_saw_and_why(monkeypatch):
    _answers(monkeypatch, worth=0.9, enough=0.1)
    d = SS.decide_stage("9_docking", CAND, {"1_target_analysis": {}})
    assert d["stage"] == "9_docking"
    assert d["reason"]
    assert d["decided_by"] in ("rule", "judgment")
    assert d["state_seen"]["name"] == "KRAS-007"
    assert "1_target_analysis" in d["state_seen"]["stages_already_run"]


def test_the_summary_reports_what_was_skipped_and_what_it_cost(monkeypatch):
    _answers(monkeypatch, worth=0.05, enough=0.95)
    ds = [SS.decide_stage(s, CAND, {}) for s in ("5b_protenix", "9_docking")]
    ds.append(SS.decide_stage("3_toxicology", CAND, {}))
    s = SS.summarize(ds)
    assert s["decisions"] == 3
    assert s["by_action"]["skip"] == 2 and s["by_action"]["run"] == 1
    assert set(s["stages_skipped"]) == {"5b_protenix", "9_docking"}
    assert s["judgment_tokens_spent"] == 220
    assert "No value was estimated" in s["note"]
