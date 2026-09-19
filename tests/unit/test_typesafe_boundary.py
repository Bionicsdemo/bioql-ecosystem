"""TypeSafe judges text. Trained models measure molecules.

That boundary is the whole reason this integration is safe to have. A TypeSafe
probability and an ensemble toxicology score are both numbers between 0 and 1;
once one is written where the other belongs, no reader can tell them apart.
This platform has already shipped a candidate labelled "Good" whose own
internals said Category 1 (Fatal) because one layer's number was read as
another layer's measurement.

So the rule is enforced, not merely documented.

-- MOLEVERA / BIOQL
"""
import json
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import typesafe_client as TS  # noqa: E402
import insight_verifier as IV  # noqa: E402


# ───────────────────────────── the boundary ───────────────────────────────

@pytest.mark.parametrize("field", [
    "ld50_mg_kg", "ghs_class", "binding_affinity", "composite_score",
    "drug_candidate_class", "safety_gate", "iptm", "noael", "herg_pic50",
    "micronucleus", "chromosome_aberration", "qed_score", "logp",
])
def test_a_question_cannot_name_a_measured_field(field):
    """Naming a question `ld50_mg_kg` is how a judgment becomes a measurement."""
    with pytest.raises(TS.TypeSafeError) as exc:
        TS.assert_text_only_target(field)
    assert "judges text" in str(exc.value).lower()


def test_ask_refuses_before_spending_a_request(monkeypatch):
    """The refusal happens at the door, not after the tokens are paid for."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    def _explode(*a, **k):  # pragma: no cover - must never be reached
        raise AssertionError("a request was sent for a forbidden question")

    monkeypatch.setattr(TS.urllib.request, "urlopen", _explode)
    with pytest.raises(TS.TypeSafeError):
        TS.ask("some text", {"ld50_mg_kg": {"type": "noul",
                                            "instructions": "?", "criteria": {}}})


def test_text_questions_are_allowed():
    """A guard that refuses everything would just mean no integration."""
    for ok in ("claims_grounded", "overstates_certainty", "actionability",
               "is_urgent", "report_completeness"):
        TS.assert_text_only_target(ok)


def test_the_shipped_questions_all_clear_the_boundary():
    for qid in IV.QUESTIONS:
        TS.assert_text_only_target(qid)


# ──────────────────────── credentials stay outside ────────────────────────

def test_the_key_is_never_read_from_the_repository():
    assert TS.TOKEN_FILE.startswith(os.path.expanduser("~"))
    assert "Spectrix_BioQL" not in TS.TOKEN_FILE
    assert TS.TOKEN_FILE.endswith(".json")


def test_no_credential_is_hardcoded_in_the_client():
    src = open(os.path.join(BACKEND, "typesafe_client.py"), encoding="utf-8").read()
    assert "apikey_" not in src, "an API key was pasted into the source"
    assert "Bearer %s" in src, "the key must come from a variable, not a literal"


def test_missing_credential_raises_its_own_error(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(TS, "TOKEN_FILE", str(tmp_path / "absent.json"))
    assert TS.is_configured() is False
    with pytest.raises(TS.TypeSafeNotConfigured):
        TS.ask("x", {"q": {"type": "noul", "instructions": "?", "criteria": {}}})


# ───────────────────── absence is never a pass ────────────────────────────

def test_an_unconfigured_service_does_not_verify_anything(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(TS, "TOKEN_FILE", str(tmp_path / "absent.json"))
    r = IV.verify_insight("The candidate looks excellent.", {"name": "X"})
    assert r["status"] == "not_configured"
    assert r["verified"] is None, "not checked must never render as checked"


def test_a_service_failure_does_not_verify_anything(monkeypatch):
    def _fail(*a, **k):
        raise TS.TypeSafeError("boom")
    monkeypatch.setattr(TS, "ask", _fail)
    r = IV.verify_insight("Anything at all.", {"name": "X"})
    assert r["status"] == "unavailable"
    assert r["verified"] is None


def test_an_empty_insight_is_skipped_not_approved():
    r = IV.verify_insight("   ", {"name": "X"})
    assert r["status"] == "skipped" and r["verified"] is None


# ─────────────────────────── the verdict itself ───────────────────────────

def _fake_answers(monkeypatch, grounded, overstates, contradicts):
    def _ask(state, questions, **kw):
        return {"answers": {
            "claims_grounded": {"type": "noul", "noul": grounded},
            "overstates_certainty": {"type": "noul", "noul": overstates},
            "contradicts_evidence": {"type": "noul", "noul": contradicts},
            "actionability": {"type": "score", "score": 1.4,
                              "legend": {"0": "a", "1": "b", "2": "c"},
                              "probabilities": {"0": .1, "1": .4, "2": .5},
                              "confidence": 0.8},
        }, "model": "jev-latest", "usage": {}}
    monkeypatch.setattr(TS, "ask", _ask)


def test_a_grounded_insight_verifies(monkeypatch):
    _fake_answers(monkeypatch, grounded=0.95, overstates=0.05, contradicts=0.03)
    r = IV.verify_insight("ipTM is 0.74.", {"name": "X"})
    assert r["status"] == "checked" and r["verified"] is True and r["problems"] == []


@pytest.mark.parametrize("g,o,c,needle", [
    (0.20, 0.05, 0.05, "not traceable"),
    (0.95, 0.90, 0.05, "as measured"),
    (0.95, 0.05, 0.88, "conflicts"),
])
def test_each_failure_mode_is_caught_and_named(monkeypatch, g, o, c, needle):
    _fake_answers(monkeypatch, g, o, c)
    r = IV.verify_insight("Some claim.", {"name": "X"})
    assert r["verified"] is False
    assert any(needle in p for p in r["problems"]), r["problems"]


def test_every_response_states_that_it_did_not_judge_the_molecule(monkeypatch):
    _fake_answers(monkeypatch, 0.95, 0.05, 0.05)
    r = IV.verify_insight("x", {"name": "X"})
    assert "does not evaluate the molecule" in r["scope"]


# ──────────────────── the evidence sent is bounded ────────────────────────

def test_the_state_sent_is_an_allowlist_not_the_whole_candidate(monkeypatch):
    captured = {}

    def _ask(state, questions, **kw):
        captured["state"] = state
        return {"answers": {}, "model": "jev-latest", "usage": {}}

    monkeypatch.setattr(TS, "ask", _ask)
    IV.verify_insight("x", {
        "name": "KRAS-005", "composite_score": 0.59,
        "structure_cif": "HEADER..." * 5000,
        "structure_png_b64": "iVBORw0KGgo" * 5000,
        "_internal_secret": "should not travel",
    })
    ev = captured["state"]["evidence"]
    assert "name" in ev and "composite_score" in ev
    assert "structure_cif" not in ev, "a whole structure file would bury the evidence"
    assert "structure_png_b64" not in ev
    assert "_internal_secret" not in ev
    # And the payload must stay small enough to be an argument, not a dump.
    assert len(json.dumps(captured["state"])) < 20000
