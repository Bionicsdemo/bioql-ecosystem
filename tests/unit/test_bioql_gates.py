"""The gate layer fails open, so it must never claim a check that did not run.

A gate that raises would take a 51-stage pipeline down with it, so these
wrappers swallow. The risk that buys is a silent "pass" -- so every wrapper
carries `checked`, and a failure says so in words.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import bioql_gates as G  # noqa: E402
import stage_audit as SA  # noqa: E402


# ───────────────────── failing open, but never silently ───────────────────

def test_a_broken_audit_does_not_take_the_pipeline_down(monkeypatch):
    monkeypatch.setattr(SA, "audit_stage",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = G.audit("3_toxicology", {"x": 1})
    assert r["verdict"] == "pass", "the pipeline must keep running"
    assert r["checked"] is False, "but it must not claim to have checked"
    assert "boom" in r["gate_error"]


def test_a_failed_gate_says_unchecked_is_not_passed(monkeypatch):
    monkeypatch.setattr(SA, "audit_stage",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = G.audit("3_toxicology", {})
    assert "Unchecked is not the same as passed" in r["note"]


def test_a_successful_audit_is_marked_checked():
    r = G.audit("3_toxicology", {"tox": {"ld50": 1.0, "ld50_unit": "mg/kg"}})
    assert r["checked"] is True


def test_broken_routing_never_reports_ready_to_dispatch(monkeypatch):
    import intent_router
    monkeypatch.setattr(intent_router, "route",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = G.route_request("do something", [{"name": "t"}])
    assert r["ready_to_dispatch"] is False and r["tool"] is None
    assert "Nothing was run" in r["next_step"]


def test_broken_extraction_yields_no_value(monkeypatch):
    import literature_value_extraction as LX
    monkeypatch.setattr(LX, "potency_for_candidate",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = G.potency_from_text({"target": "KRAS"}, "IC50 of 5 nM")
    assert r["available"] is False and r["value_nm"] is None


# ────────────────── the audit rides along with the output ─────────────────

def test_the_audit_is_attached_to_what_flows_downstream():
    out = G.audited("8_scoring", {"drug_candidate_class": "Good"},
                    prior={"tox": {"acute": "GHS Category 1 (Fatal)"}})
    assert out["_stage_audit"]["verdict"] == "quarantine"


def test_shadow_mode_attaches_the_verdict_but_withholds_nothing(monkeypatch):
    monkeypatch.setenv("BIOQL_STAGE_AUDIT", "shadow")
    out = G.audited("8_scoring", {"drug_candidate_class": "Good"},
                    prior={"tox": {"acute": "GHS Category 1 (Fatal)"}})
    assert out["drug_candidate_class"] == "Good", "shadow withholds nothing"
    assert out["_stage_audit"]["withheld"] == ["drug_candidate_class"]


def test_enforce_mode_actually_withholds(monkeypatch):
    monkeypatch.setenv("BIOQL_STAGE_AUDIT", "enforce")
    out = G.audited("8_scoring", {"drug_candidate_class": "Good", "rank": 3},
                    prior={"tox": {"acute": "GHS Category 1 (Fatal)"}})
    assert "drug_candidate_class" not in out, "the contradicted verdict is withheld"
    assert out["rank"] == 3, "everything else still flows"
    assert "drug_candidate_class" in out["_quarantined"]


def test_the_caller_s_dict_is_never_mutated():
    src = {"drug_candidate_class": "Good"}
    G.audited("8_scoring", src, prior={"tox": {"acute": "GHS Category 1"}})
    assert src == {"drug_candidate_class": "Good"}


# ─────────────────── the model half is opt-in, it costs ───────────────────

def test_the_model_is_not_consulted_by_default(monkeypatch):
    monkeypatch.delenv("BIOQL_STAGE_AUDIT_MODEL", raising=False)
    assert G._consult_model() is False


def test_the_model_can_be_turned_on(monkeypatch):
    monkeypatch.setenv("BIOQL_STAGE_AUDIT_MODEL", "1")
    assert G._consult_model() is True


# ──────────────────────────────── status ──────────────────────────────────

def test_status_reports_every_gate_module():
    s = G.status()
    for name in ("stage_audit", "intent_router", "literature_value_extraction",
                 "efficacious_dose"):
        assert s["modules"][name]["loaded"] is True, name
    assert "stage_audit" in s["modes"]


def test_status_reports_a_module_it_cannot_load(monkeypatch):
    """A gate that is not reachable must show as not reachable."""
    real = __import__

    def _fake(name, *a, **k):
        if name == "intent_router":
            raise ImportError("no such module")
        return real(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", _fake)
    s = G.status()
    assert s["modules"]["intent_router"]["loaded"] is False


# ───── the evidenced composite rides beside the published one ─────

def test_the_evidenced_composite_is_attached_beside_the_published_score():
    cand = {"drug_candidate_class": "Good", "composite_score": 0.7,
            "analyses": {"admet": {"status": "skipped"},
                         "toxicology": {"status": "completed", "x": 1},
                         "scoring": {"composite_score": 0.7, "score_breakdown": {
                             "admet": {"score": 0.5, "weight": 0.5},
                             "toxicology": {"score": 0.9, "weight": 0.5}}}}}
    out = G.audited("report_assembly", cand, candidate=cand)
    rc = out["_composite_evidenced"]
    assert rc["composite_published"] == 0.7
    assert rc["composite_evidenced"] == 0.9, "admet did not run; only tox counts"
    assert out["composite_score"] == 0.7, "the published score is never replaced"


def test_a_record_with_nothing_to_weigh_gets_no_recompute_block():
    out = G.audited("report_assembly", {"drug_candidate_class": "Good"})
    assert "_composite_evidenced" not in out


def test_a_failed_recompute_says_it_did_not_run(monkeypatch):
    import composite_recompute as CR
    monkeypatch.setattr(CR, "recompute",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    rc = G.composite_beside({"score_breakdown": {"a": 0.5, "b": 0.6}})
    assert rc["checked"] is False and "did not run" in rc["reason"]
