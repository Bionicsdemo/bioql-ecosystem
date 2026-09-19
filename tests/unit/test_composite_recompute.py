"""Nothing in this module may be hardcoded — it exists to find hardcoded values.

Components come from the candidate's own breakdown, weights from the record, and
default values from repetition across the cohort. The tests below pin all three,
plus the distinction that `undecidable` is not a soft `absent`.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import composite_recompute as CR  # noqa: E402


def _sm(admet_status=None, admet_score=0.5, admet_content=None, composite=0.72,
        weights=True):
    """A small-molecule-shaped candidate: nested components, recorded weights."""
    admet = {}
    if admet_status:
        admet["status"] = admet_status
    if admet_content:
        admet.update(admet_content)
    w = {"admet": 0.20, "toxicology": 0.25, "pharmacology": 0.25, "docking": 0.30}
    bd = {"admet": {"score": admet_score}, "toxicology": {"score": 0.70},
          "pharmacology": {"score": 0.60}, "docking": {"score": 0.80}}
    if weights:
        for k in bd:
            bd[k]["weight"] = w[k]
    return {"analyses": {
        "admet": admet,
        "toxicology": {"status": "completed", "overall_score": 0.7},
        "pharmacology": {"status": "completed", "bioavailability": 0.4},
        "docking": {"status": "completed", "best_score": -8.1},
        "scoring": {"composite_score": composite, "score_breakdown": bd}}}


def _ab(binding=0.9, composite=0.71):
    """An antibody-shaped candidate: bare component scores, no weights, no analyses."""
    return {"score_breakdown": {"binding": binding, "developability": 0.5,
                                "immunogenicity_safety": 0.7, "structure": 0.6},
            "composite_score": composite}


# ─────────────── components come from the record, not a table ──────────────

def test_the_components_are_read_from_the_candidates_own_breakdown():
    assert set(CR.components_of(_sm())) == {
        "admet", "toxicology", "pharmacology", "docking"}
    assert set(CR.components_of(_ab())) == {
        "binding", "developability", "immunogenicity_safety", "structure"}


def test_an_unfamiliar_component_set_is_scored_not_rejected():
    """A hardcoded set reported all four as absent for 167 antibody candidates.
    Any named component set must simply be weighed on its own terms."""
    c = {"score_breakdown": {"vibes": 0.9, "aura": 0.3}, "composite_score": 0.6}
    r = CR.recompute(c)
    assert r["available"] is True
    assert set(r["components_kept"]) == {"vibes", "aura"}


def test_a_candidate_with_no_breakdown_assumes_no_components():
    r = CR.recompute({"composite_score": 0.6})
    assert r["available"] is False
    assert "no score_breakdown" in r["reason"]
    assert "Nothing is assumed" in r["reason"]


def test_a_bare_component_score_is_read_not_missed():
    """Antibody runs write {"binding": 1.0}, not {"binding": {"score": 1.0}}."""
    assert CR._component_score({"binding": 1.0}, "binding") == 1.0
    assert CR._component_score({"admet": {"score": 0.5}}, "admet") == 0.5


# ───────────────── weights come from the record, or are equal ──────────────

def test_recorded_per_component_weights_are_used():
    w, src = CR.weights_of(_sm(), CR.components_of(_sm()))
    assert w["docking"] == 0.30
    assert "score_breakdown" in src


def test_run_level_weights_are_used_when_components_carry_none():
    c = _sm(weights=False)
    c["analyses"]["scoring"]["scoring_weights"] = {
        "admet": 0.1, "toxicology": 0.2, "pharmacology": 0.3, "docking": 0.4}
    w, src = CR.weights_of(c, CR.components_of(c))
    assert w["docking"] == 0.4
    assert "scoring_weights" in src


def test_with_no_weights_recorded_the_split_is_equal_and_says_so():
    """No table of weights may stand in for weights nobody wrote down."""
    c = _ab()
    w, src = CR.weights_of(c, CR.components_of(c))
    assert set(w.values()) == {0.25}
    assert "EQUAL" in src and "none are assumed" in src


def test_the_weight_source_is_always_reported():
    assert "score_breakdown" in CR.recompute(_sm())["weight_source"]
    assert "EQUAL" in CR.recompute(_ab())["weight_source"]


# ────────── default values are derived from the cohort, not listed ─────────

def test_a_value_repeating_across_the_cohort_is_derived_as_a_default():
    cohort = [_sm(admet_score=0.5) for _ in range(4)]
    d = CR.derive_default_values(cohort)
    assert 0.5 in d["admet"]


def test_a_value_unique_in_the_cohort_is_not_a_default():
    cohort = [_sm(admet_score=v) for v in (0.11, 0.22, 0.33, 0.44)]
    d = CR.derive_default_values(cohort)
    assert d["admet"] == set()


def test_without_a_cohort_nothing_is_presumed_to_be_a_default():
    r = CR.recompute(_sm(admet_score=0.5))
    assert r["undecidable"] == []
    assert "no value presumed default" in r["default_detection"]


def test_the_threshold_is_stated_in_the_result():
    r = CR.recompute(_sm(), cohort=[_sm() for _ in range(4)])
    assert "threshold %d" % CR.DEFAULT_REPEAT_THRESHOLD in r["default_detection"]


# ───────────────────────── classifying a component ────────────────────────

def test_a_skipped_analysis_makes_its_component_absent():
    v, why = CR.classify_component(_sm(admet_status="skipped"), "admet")
    assert v == "absent" and "skipped" in why


@pytest.mark.parametrize("status", ["unavailable", "error", "failed", "not_run"])
def test_every_absent_status_is_recognised(status):
    v, _ = CR.classify_component(_sm(admet_status=status), "admet")
    assert v == "absent"


def test_a_completed_analysis_makes_its_component_evidenced():
    v, _ = CR.classify_component(_sm(admet_status="completed"), "admet")
    assert v == "evidenced"


def test_result_fields_count_as_evidence_even_with_no_status():
    v, why = CR.classify_component(
        _sm(admet_content={"hia": 0.9, "bbb": 0.2}), "admet")
    assert v == "evidenced" and "result fields" in why


def test_a_repeated_value_with_nothing_either_way_is_undecidable():
    cohort = [_sm(admet_score=0.5) for _ in range(4)]
    d = CR.derive_default_values(cohort)
    v, why = CR.classify_component(_sm(admet_score=0.5), "admet", d)
    assert v == "undecidable"
    assert "cannot be determined" in why


def test_a_score_that_does_not_repeat_is_evidenced_even_bare():
    cohort = [_sm(admet_score=0.5) for _ in range(4)]
    d = CR.derive_default_values(cohort)
    v, _ = CR.classify_component(_sm(admet_score=0.83), "admet", d)
    assert v == "evidenced"


# ──────────────────── renormalising over what is left ─────────────────────

def test_an_absent_component_is_dropped_and_the_weights_renormalise():
    r = CR.recompute(_sm(admet_status="skipped"))
    assert "admet" in r["components_dropped"]
    assert r["composite_evidenced"] == pytest.approx(
        (0.70 * 0.25 + 0.60 * 0.25 + 0.80 * 0.30) / 0.80, abs=1e-4)
    assert r["weight_covered_by_evidence"] == pytest.approx(0.80)


def test_the_published_score_is_reported_beside_the_recomputed_one():
    r = CR.recompute(_sm(admet_status="skipped", composite=0.72))
    assert r["composite_published"] == 0.72
    assert r["delta"] == pytest.approx(r["composite_evidenced"] - 0.72, abs=1e-4)


def test_nothing_is_written_back_into_the_candidate():
    c = _sm(admet_status="skipped")
    before = repr(c)
    CR.recompute(c, cohort=[_sm(), _sm(), _sm()])
    assert repr(c) == before


def test_all_components_evidenced_reproduces_the_full_weighted_sum():
    r = CR.recompute(_sm(admet_status="completed", admet_score=0.90))
    assert r["components_dropped"] == []
    assert r["composite_evidenced"] == pytest.approx(
        0.90 * 0.20 + 0.70 * 0.25 + 0.60 * 0.25 + 0.80 * 0.30, abs=1e-4)


def test_an_antibody_candidate_is_scored_on_its_own_components():
    r = CR.recompute(_ab())
    assert r["available"] is True
    assert set(r["components_kept"]) == {
        "binding", "developability", "immunogenicity_safety", "structure"}
    assert r["components_dropped"] == []


# ───────── the undecidable are kept by default, never assumed away ────────

def test_an_undecidable_component_is_kept_by_default():
    cohort = [_sm(admet_score=0.5) for _ in range(4)]
    r = CR.recompute(_sm(admet_score=0.5), cohort=cohort)
    assert "admet" in r["undecidable"]
    assert "admet" not in r["components_dropped"]


def test_the_undecidable_can_be_dropped_only_when_asked_explicitly():
    cohort = [_sm(admet_score=0.5) for _ in range(4)]
    r = CR.recompute(_sm(admet_score=0.5), cohort=cohort,
                     undecidable_counts_as_absent=True)
    assert "admet" in r["components_dropped"]
    assert r["weight_covered_by_evidence"] == pytest.approx(0.80)


# ───────────── no evidence at all is not a score of any kind ───────────────

def test_a_candidate_with_every_component_absent_yields_no_composite():
    c = _sm()
    for comp in ("admet", "toxicology", "pharmacology", "docking"):
        c["analyses"][comp] = {"status": "skipped"}
    r = CR.recompute(c)
    assert r["available"] is False
    assert "weighted sum of assumptions" in r["reason"]


def test_every_component_is_always_reported_with_its_reason():
    r = CR.recompute(_sm(admet_status="skipped"))
    assert {x["component"] for x in r["components"]} == {
        "admet", "toxicology", "pharmacology", "docking"}
    assert all(x["reason"] for x in r["components"])


# ─── the evidence effect must not be confused with a weighting effect ───

def test_delta_from_evidence_uses_the_same_weights_on_both_sides():
    """With no recorded weights the split is equal, so a delta against the
    published score also carries a weighting difference. delta_from_evidence
    holds the weights fixed and moves only the evidence."""
    c = {"score_breakdown": {"a": 0.9, "b": 0.3}, "composite_score": 0.75,
         "analyses": {"b": {"status": "skipped"}}}
    r = CR.recompute(c)
    assert r["composite_all_components_same_weights"] == pytest.approx(0.6)
    assert r["composite_evidenced"] == pytest.approx(0.9)
    assert r["delta_from_evidence"] == pytest.approx(0.3)
    # the published delta differs, because 0.75 was not an equal split
    assert r["delta"] == pytest.approx(0.15)


def test_with_nothing_dropped_the_evidence_effect_is_zero():
    """Whatever the weights, keeping every component moves nothing."""
    r = CR.recompute(_ab())
    assert r["delta_from_evidence"] == pytest.approx(0.0)
