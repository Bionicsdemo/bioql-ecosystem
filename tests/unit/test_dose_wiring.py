"""The pipeline publishes a derived dose, or none. Never a sampled one.

`recommended_dose_mg` used to come from a generative QNN head with a 5-1000 mg
range and a 200 mg fallback. It now comes from potency -> target exposure ->
PBPK inverse solve, or it is absent with a reason. These tests hold the wiring
to that, and to one more thing the measurements forced: the dose must not
change between runs of the same molecule.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import pipeline_finalize as PF  # noqa: E402
import efficacious_dose as ED  # noqa: E402


class FakeModeler:
    def __init__(self, dose=125.0):
        self.dose = dose

    def optimize_dosing(self, smiles, target_cmin, target_cmax,
                        weight_kg=70.0, optimizer=None):
        assert optimizer == "classical", "the pipeline must ask for the deterministic solve"
        return {"dose_mg": self.dose, "interval_h": 12.0}


COMPLETE = {
    "name": "C-1", "smiles": "CCO", "mw": 400.0,
    "pharmacology": {
        "pharmacodynamics": {"potency": {"ic50": 50.0}},
        "pharmacokinetics": {"distribution": {"ppb": 90.0}},
    },
}
INCOMPLETE = {"name": "C-2", "smiles": "CCC", "mw": 300.0}  # no potency, no PPB


@pytest.fixture(autouse=True)
def _fake_pbpk(monkeypatch):
    """Never touch the real PBPK (or a provider) from a unit test."""
    real = ED.efficacious_dose

    def patched(candidate, **kw):
        kw.setdefault("modeler", FakeModeler())
        return real(candidate, **kw)

    monkeypatch.setattr(ED, "efficacious_dose", patched)


def test_a_complete_candidate_gets_a_derived_dose():
    r = PF._attach_efficacious_dose({"candidates": [dict(COMPLETE)]})
    c = r["candidates"][0]
    assert c["recommended_dose_mg"] == 125.0
    assert c["efficacious_dose"]["available"] is True
    assert "PBPK" in c["efficacious_dose"]["method"]


def test_an_incomplete_candidate_gets_no_dose_and_a_reason():
    r = PF._attach_efficacious_dose({"candidates": [dict(INCOMPLETE)]})
    c = r["candidates"][0]
    assert c["recommended_dose_mg"] is None, "absent, not zero and not a default"
    assert c["efficacious_dose"]["available"] is False
    assert c["efficacious_dose"]["reason"]


def test_no_candidate_ever_receives_the_old_default():
    r = PF._attach_efficacious_dose(
        {"candidates": [dict(COMPLETE), dict(INCOMPLETE)]})
    for c in r["candidates"]:
        assert c["recommended_dose_mg"] != 200, "the 200 mg fallback came back"


def test_every_candidate_list_key_is_covered():
    r = PF._attach_efficacious_dose({
        "candidates": [dict(COMPLETE)],
        "lead_compounds": [dict(COMPLETE)],
        "drug_candidates": [dict(COMPLETE)],
    })
    for key in ("candidates", "lead_compounds", "drug_candidates"):
        assert r[key][0]["recommended_dose_mg"] == 125.0


def test_the_summary_separates_derived_from_absent():
    r = PF._attach_efficacious_dose(
        {"candidates": [dict(COMPLETE), dict(INCOMPLETE)]})
    s = r["efficacious_dose_summary"]
    assert s["candidates_seen"] == 2
    assert s["doses_derived"] == 1 and s["doses_absent"] == 1
    assert "not zero" in s["note"]


def test_the_same_candidate_twice_gives_the_same_dose():
    a = PF._attach_efficacious_dose({"candidates": [dict(COMPLETE)]})
    b = PF._attach_efficacious_dose({"candidates": [dict(COMPLETE)]})
    assert (a["candidates"][0]["recommended_dose_mg"]
            == b["candidates"][0]["recommended_dose_mg"])


def test_a_derivation_failure_never_takes_the_pipeline_down(monkeypatch):
    def boom(candidate, **kw):
        raise RuntimeError("derivation exploded")
    monkeypatch.setattr(ED, "efficacious_dose", boom)
    r = PF._attach_efficacious_dose({"candidates": [dict(COMPLETE)]})
    c = r["candidates"][0]
    assert c["recommended_dose_mg"] is None
    assert "failed" in c["efficacious_dose"]["reason"]


@pytest.mark.parametrize("payload", [
    {}, {"candidates": None}, {"candidates": [None, 7, "x"]}, "not a dict",
])
def test_malformed_input_is_survived(payload):
    out = PF._attach_efficacious_dose(payload)
    assert out is not None


def test_finalize_actually_calls_it():
    """A helper nobody calls is a helper that fixes nothing."""
    src = open(os.path.join(BACKEND, "pipeline_finalize.py"), encoding="utf-8").read()
    i = src.index("def finalize(")
    assert "_attach_efficacious_dose(result)" in src[i:], (
        "finalize no longer attaches the derived dose")
