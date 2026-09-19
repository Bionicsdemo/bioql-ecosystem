"""A verifier that can clear its own alarms is not a verifier.

The central test here is `test_the_model_cannot_clear_a_failed_invariant`.
Everything else is the invariant set that caught KRAS-005.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import stage_audit as SA  # noqa: E402
import typesafe_client as TS  # noqa: E402


@pytest.fixture(autouse=True)
def enforce(monkeypatch):
    monkeypatch.setenv("BIOQL_STAGE_AUDIT", "enforce")


def _model_says(monkeypatch, p):
    monkeypatch.setattr(TS, "is_configured", lambda: True)
    monkeypatch.setattr(TS, "ask", lambda *a, **k: {
        "answers": {"narrative_contradicts_numbers": {"noul": p}}, "usage": {}})


# ───────────────── the asymmetry: escalate only, never clear ──────────────

def test_the_model_cannot_clear_a_failed_invariant(monkeypatch):
    """The whole safety argument. Judgment may raise a verdict, never lower it."""
    _model_says(monkeypatch, 0.01)          # model is maximally reassuring
    out = {"toxicology": {"noael_mg_kg": 500, "loael_mg_kg": 50,
                          "interpretation": "A wide and comfortable safety "
                          "margin was observed across all dose groups tested."}}
    a = SA.audit_stage("3_toxicology", out)
    assert a["verdict"] == "quarantine", "a reassuring model must not clear arithmetic"
    assert any(f["invariant"] == "noael_below_loael" for f in a["findings"])


def test_the_model_can_raise_a_clean_stage_to_flag(monkeypatch):
    _model_says(monkeypatch, 0.95)
    out = {"result": {"value_nm": 4.0, "value_nm_unit": "nM",
                      "interpretation": "This compound is entirely without risk "
                      "and requires no further characterisation whatsoever."}}
    a = SA.audit_stage("9_docking", out)
    assert a["verdict"] == "flag"


def test_a_judgment_on_an_already_flagged_stage_escalates_to_quarantine(monkeypatch):
    _model_says(monkeypatch, 0.9)
    out = {"tox": {"ld50": 1500,                      # flagged: no unit sibling
                   "interpretation": "The margin observed here is very wide "
                   "and no further toxicological work appears warranted."}}
    a = SA.audit_stage("3_toxicology", out)
    assert a["verdict"] == "quarantine"


# ───────────────────────── the KRAS-005 invariant ─────────────────────────

def test_a_good_verdict_beside_a_fatal_hazard_is_quarantined():
    out = {"drug_candidate_class": "Good"}
    prior = {"toxicology": {"acute": "GHS Category 1 (Fatal if swallowed)"}}
    a = SA.audit_stage("8_scoring", out, prior=prior, consult_model=False)
    assert a["verdict"] == "quarantine"
    assert "drug_candidate_class" in a["withheld"]


def test_a_good_verdict_with_no_hazard_recorded_passes():
    a = SA.audit_stage("8_scoring", {"drug_candidate_class": "Good"},
                       prior={"toxicology": {"acute": "GHS Category 5"}},
                       consult_model=False)
    assert a["verdict"] == "pass"


def test_genotoxicity_defeats_a_positive_verdict():
    a = SA.audit_stage("8_scoring", {"status": "viable"},
                       prior={"genotox": {"result": "micronucleus positive"}},
                       consult_model=False)
    assert a["verdict"] == "quarantine"


# ──────────────────────── the rest of the invariants ──────────────────────

def test_a_synthetic_placeholder_never_passes_as_a_structure():
    a = SA.audit_stage("5b_protenix",
                       {"structure": {"pdb": "HEADER SYNTHETIC_PDB_MARKER\nATOM..."}},
                       consult_model=False)
    assert a["verdict"] == "quarantine"
    assert "structure.pdb" in a["withheld"]


def test_a_toxicity_value_without_a_unit_is_flagged():
    a = SA.audit_stage("3_toxicology", {"tox": {"ld50": 2.1}}, consult_model=False)
    assert a["verdict"] == "flag"
    assert any(f["invariant"] == "units_declared" for f in a["findings"])


def test_a_toxicity_value_with_its_unit_beside_it_passes():
    a = SA.audit_stage("3_toxicology",
                       {"tox": {"ld50": 2.1, "ld50_unit": "-log10(mol/kg)"}},
                       consult_model=False)
    assert a["verdict"] == "pass"


def test_a_probability_outside_its_scale_is_quarantined():
    a = SA.audit_stage("5c", {"binding": {"confidence": 87.0}}, consult_model=False)
    assert a["verdict"] == "quarantine"


def test_plddt_is_judged_on_its_own_0_to_100_scale():
    a = SA.audit_stage("5b", {"fold": {"plddt": 87.0}}, consult_model=False)
    assert a["verdict"] == "pass"


def test_the_same_number_on_many_candidates_is_treated_as_inherited():
    """38 of 80 candidates carried the same hardcoded 1500 mg/kg."""
    out = {"tox": {"ld50_mg_kg": 1500.0, "ld50_mg_kg_unit": "mg/kg"}}
    cohort = [out, out, out]
    a = SA.audit_stage("3_toxicology", out, cohort=cohort, consult_model=False)
    assert a["verdict"] == "quarantine"
    assert any(f["invariant"] == "no_inherited_constant" for f in a["findings"])


def test_a_value_unique_to_this_candidate_is_not_treated_as_inherited():
    out = {"tox": {"ld50_mg_kg": 1500.0, "ld50_mg_kg_unit": "mg/kg"}}
    cohort = [{"tox": {"ld50_mg_kg": 220.0}}, {"tox": {"ld50_mg_kg": 3100.0}}]
    a = SA.audit_stage("3_toxicology", out, cohort=cohort, consult_model=False)
    assert a["verdict"] == "pass"


# ──────────────────── degrading, and never fabricating ────────────────────

def test_an_unavailable_judgment_is_unchecked_not_passed(monkeypatch):
    monkeypatch.setattr(TS, "is_configured", lambda: True)

    def _fail(*a, **k):
        raise TS.TypeSafeError("service down")
    monkeypatch.setattr(TS, "ask", _fail)
    out = {"r": {"interpretation": "x" * 100, "value": 1.0}}
    a = SA.audit_stage("9_docking", out)
    f = next(f for f in a["findings"]
             if f["invariant"] == "narrative_contradicts_numbers")
    assert f["decided_by"] == "unavailable"
    assert "Unchecked is not passed" in f["detail"]


def test_an_invariant_that_raises_does_not_take_the_pipeline_down(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("bad input")
    monkeypatch.setattr(SA, "_INVARIANTS", (_boom,))
    a = SA.audit_stage("3_toxicology", {"x": 1}, consult_model=False)
    assert a["verdict"] == "flag"
    assert "treat as unchecked" in a["findings"][0]["detail"]


# ───────────────── quarantine withholds; it does not repair ───────────────

def test_a_quarantined_field_is_absent_not_replaced():
    out = {"structure": {"pdb": "SYNTHETIC_PDB_MARKER", "chains": 1}}
    a = SA.audit_stage("5b_protenix", out, consult_model=False)
    clean = SA.apply_quarantine(out, a)
    assert "pdb" not in clean["structure"], "the field must be absent"
    assert clean["structure"]["chains"] == 1, "siblings are untouched"
    assert "structure.pdb" in clean["_quarantined"], "the absence carries its reason"


def test_the_original_output_is_never_mutated():
    out = {"structure": {"pdb": "SYNTHETIC_PDB_MARKER"}}
    a = SA.audit_stage("5b_protenix", out, consult_model=False)
    SA.apply_quarantine(out, a)
    assert out["structure"]["pdb"] == "SYNTHETIC_PDB_MARKER"


def test_shadow_mode_records_the_verdict_but_withholds_nothing(monkeypatch):
    monkeypatch.setenv("BIOQL_STAGE_AUDIT", "shadow")
    out = {"structure": {"pdb": "SYNTHETIC_PDB_MARKER"}}
    a = SA.audit_stage("5b_protenix", out, consult_model=False)
    assert a["verdict"] == "quarantine" and a["enforced"] is False
    assert SA.apply_quarantine(out, a) == out


def test_off_disables_the_audit_entirely(monkeypatch):
    monkeypatch.setenv("BIOQL_STAGE_AUDIT", "off")
    a = SA.audit_stage("5b", {"structure": {"pdb": "SYNTHETIC_PDB_MARKER"}})
    assert a["verdict"] == "pass" and a["mode"] == "off"


def test_the_default_mode_is_shadow(monkeypatch):
    """A new gate must not start withholding fields on its first run."""
    monkeypatch.delenv("BIOQL_STAGE_AUDIT", raising=False)
    assert SA.mode() == "shadow"


# ─────────────────────── the text-only boundary holds ─────────────────────

def test_the_question_asked_is_about_text_not_about_a_measurement():
    TS.assert_text_only_target("narrative_contradicts_numbers")


# ────── a guard must not fire on its own explanatory prose ───────

def test_a_note_describing_what_was_checked_is_not_a_recorded_hazard():
    """It fired on a real candidate the first time it ran live.

    The matched text was the gate's own note listing what it looks for --
    "GHS acute class, micronucleus / chromosome aberration" -- not a finding
    that any of those were present.
    """
    out = {"drug_candidate_class": "Excellent",
           "safety_gate_reevaluated": {
               "passed": True,
               "note": "Re-evaluated with the hardened gate (GHS acute class, "
                       "micronucleus / chromosome aberration, carcinogenicity)."}}
    a = SA.audit_stage("report_assembly", out, consult_model=False)
    assert a["verdict"] == "pass", "a description of the check is not a finding"


def test_a_hazard_actually_recorded_in_a_short_field_still_fires():
    """The fix must not blind the invariant to a real hazard."""
    out = {"drug_candidate_class": "Excellent",
           "toxicology": {"genotoxicity": {"micronucleus": "positive"},
                          "acute": "GHS Category 1"}}
    a = SA.audit_stage("report_assembly", out, consult_model=False)
    assert a["verdict"] == "quarantine"


def test_a_long_sentence_is_prose_whatever_the_field_is_called():
    out = {"drug_candidate_class": "Good",
           "toxicology": {"acute_finding":
                          "The assay panel screened for GHS Category 1 acute "
                          "oral toxicity and none of the tested concentrations "
                          "produced an effect at or near that threshold."}}
    a = SA.audit_stage("report_assembly", out, consult_model=False)
    assert a["verdict"] == "pass"


# ───── configuration is meant to be identical; a measurement is not ──────

def test_a_scoring_weight_repeated_on_every_candidate_is_not_a_finding():
    """It is SUPPOSED to be identical -- that is what makes scores comparable.

    Counting it inflated the historical inheritance rate from 45% to 94%.
    """
    out = {"scoring": {"score_breakdown": {"kd_weight": 0.16}}}
    a = SA.audit_stage("8_scoring", out, cohort=[out, out, out], consult_model=False)
    assert a["verdict"] == "pass"


def test_a_measurement_repeated_on_every_candidate_is_still_a_finding():
    """The fix must not excuse the 1500 mg/kg it was built to catch."""
    out = {"tox": {"ld50_mg_kg": 1500.0, "ld50_mg_kg_unit": "mg/kg"}}
    a = SA.audit_stage("3_toxicology", out, cohort=[out, out, out],
                       consult_model=False)
    assert a["verdict"] == "quarantine"


@pytest.mark.parametrize("field", ["weight", "threshold", "coefficient",
                                   "admet_weight", "cutoff", "seed"])
def test_config_shaped_fields_are_recognised(field):
    assert SA._is_config("scoring.%s" % field) is True


@pytest.mark.parametrize("field", ["ld50_mg_kg", "kd_nm", "ic50", "noael"])
def test_measurement_shaped_fields_are_not_config(field):
    assert SA._is_config("tox.%s" % field) is False


# ───── a component that did not run must not carry a number ──────

def test_a_score_whose_analysis_was_skipped_is_quarantined():
    """The dict says "skipped"; the 0.5 beside it does not, and 0.5 is what scores."""
    out = {"analyses": {"admet": {"status": "skipped",
                                  "reason": "computed for lead candidate only"}},
           "score_breakdown": {"admet": {"score": 0.5, "weight": 0.2}}}
    a = SA.audit_stage("8_scoring", out, consult_model=False)
    assert a["verdict"] == "quarantine"
    assert any(f["invariant"] == "score_without_its_analysis" for f in a["findings"])


@pytest.mark.parametrize("status", ["skipped", "unavailable", "error", "failed"])
def test_every_way_an_analysis_can_be_absent_is_caught(status):
    out = {"analyses": {"docking": {"status": status}},
           "score_breakdown": {"docking": {"score": 0.62}}}
    a = SA.audit_stage("8_scoring", out, consult_model=False)
    assert a["verdict"] == "quarantine"


def test_a_score_whose_analysis_completed_is_not_flagged():
    out = {"analyses": {"admet": {"status": "completed"}},
           "score_breakdown": {"admet": {"score": 0.5, "weight": 0.2}}}
    a = SA.audit_stage("8_scoring", out, consult_model=False)
    assert a["verdict"] == "pass"


def test_a_skipped_analysis_that_contributes_no_score_is_not_flagged():
    """Skipping is fine. Skipping and still scoring is not."""
    out = {"analyses": {"admet": {"status": "skipped"}},
           "score_breakdown": {"toxicology": {"score": 0.6}}}
    a = SA.audit_stage("8_scoring", out, consult_model=False)
    assert a["verdict"] == "pass"


# ───── a path segment must BE the key, not merely contain it ─────

def test_kd_does_not_match_inside_breakdown():
    """It did. "brea(kd)own" put every score component into the constant check,
    which is why the historical inheritance rate sat at 94% and would not move.
    """
    keys = ("ld50", "noael", "loael", "kd", "ic50")
    assert SA._names_a_measurement("scoring.score_breakdown.admet.score", keys) is False
    assert SA._names_a_measurement("scores.kd_nm", keys) is True


def test_a_repeated_score_component_is_not_an_inherited_constant():
    out = {"scoring": {"score_breakdown": {"admet": {"score": 0.5}}},
           "analyses": {"admet": {"status": "completed"}}}
    a = SA.audit_stage("8_scoring", out, cohort=[out, out, out], consult_model=False)
    assert not any(f["invariant"] == "no_inherited_constant" for f in a["findings"])


def test_a_repeated_ld50_is_still_an_inherited_constant():
    out = {"tox": {"ld50_mg_kg": 1500.0, "ld50_mg_kg_unit": "mg/kg"}}
    a = SA.audit_stage("3_toxicology", out, cohort=[out, out, out],
                       consult_model=False)
    assert any(f["invariant"] == "no_inherited_constant" for f in a["findings"])
