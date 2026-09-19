"""The dose is derived or it is absent. It is never sampled.

The platform used to publish a recommended dose drawn from a generative QNN head
with a 5-1000 mg range and a 200 mg fallback, while a 14-compartment PBPK model
sat unused next to it. These tests hold the replacement to the only standard
that matters here: every milligram it reports must be traceable to a potency, a
protein-binding fraction and a PBPK solve -- and when any of those is missing,
it must say so instead of guessing.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import efficacious_dose as ED  # noqa: E402


class FakeModeler:
    """Stands in for PBPKModeler so the chain is testable without pyscf/IBM."""

    def __init__(self, dose=125.0, interval=12.0, fail=False):
        self.dose, self.interval, self.fail = dose, interval, fail
        self.calls = []

    def optimize_dosing(self, smiles, target_cmin, target_cmax, weight_kg=70.0):
        self.calls.append({"smiles": smiles, "target_cmin": target_cmin,
                           "target_cmax": target_cmax, "weight_kg": weight_kg})
        if self.fail:
            raise RuntimeError("solver blew up")
        return {"dose_mg": self.dose, "interval_h": self.interval,
                "baseline_pk": {"t_half_h": 6.0, "CL_L_h": 12.0}}


GOOD = {
    "name": "CAND-1",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "mw": 400.0,
    "pharmacology": {
        "pharmacodynamics": {"potency": {"ic50": {"value": 50.0, "unit": "nM"}}},
        "pharmacokinetics": {"distribution": {"ppb": {"value": 90.0, "unit": "%"}}},
    },
}


# ───────────────────────── the arithmetic is right ────────────────────────

def test_the_unit_conversion_is_correct():
    """C[mg/L] = C[nM] * MW * 1e-6. Getting this wrong is how an LD50 became 'Fatal'."""
    t = ED.target_exposure(potency_nm=50.0, fu=0.10, mw=400.0, coverage=1.0)
    # 50 nM * 400 g/mol * 1e-6 = 0.02 mg/L free
    assert t["target_free_mg_L"] == pytest.approx(0.02, rel=1e-6)
    # total = free / fu = 0.02 / 0.10 = 0.2 mg/L
    assert t["target_cmin_mg_L"] == pytest.approx(0.2, rel=1e-6)


def test_free_drug_is_what_acts():
    """Halving the unbound fraction doubles the total concentration needed."""
    a = ED.target_exposure(50.0, 0.10, 400.0)["target_cmin_mg_L"]
    b = ED.target_exposure(50.0, 0.05, 400.0)["target_cmin_mg_L"]
    assert b == pytest.approx(2 * a, rel=1e-6)


def test_coverage_scales_the_target():
    a = ED.target_exposure(50.0, 0.10, 400.0, coverage=1.0)["target_cmin_mg_L"]
    b = ED.target_exposure(50.0, 0.10, 400.0, coverage=3.0)["target_cmin_mg_L"]
    assert b == pytest.approx(3 * a, rel=1e-6)


def test_the_assumption_is_stated_not_hidden():
    t = ED.target_exposure(50.0, 0.1, 400.0, coverage=2.0)
    assert "2" in t["assumption"] and "unbound" in t["assumption"]


# ───────────────── an MM-GBSA Kd is refused, and says why ─────────────────

def test_an_mmgbsa_derived_kd_is_never_used_as_potency():
    """0.00 nM from exp(dG/RT) is an underflow, not an affinity."""
    cand = {"predicted_binding_kd_nm": 0.0,
            "predicted_binding_kd_nm_basis": "Kd from real MM-GBSA dG_bind"}
    p = ED.extract_potency_nm(cand)
    assert p["value_nm"] is None
    assert "MM-GBSA" in p["reason"]
    assert "3-5x" in p["reason"]


def test_a_real_potency_is_used_and_its_source_recorded():
    p = ED.extract_potency_nm(GOOD)
    assert p["value_nm"] == 50.0
    assert p["source"].endswith("ic50")


def test_a_missing_potency_is_reported_not_defaulted():
    p = ED.extract_potency_nm({"name": "X"})
    assert p["value_nm"] is None and p["reason"]


# ─────────────────────── protein binding handling ─────────────────────────

@pytest.mark.parametrize("ppb,expected_fu", [(90.0, 0.10), (0.90, 0.10), (99.0, 0.01)])
def test_ppb_is_read_as_percent_or_fraction(ppb, expected_fu):
    cand = {"pharmacology": {"pharmacokinetics": {"distribution": {"ppb": ppb}}}}
    assert ED.extract_fraction_unbound(cand)["fu"] == pytest.approx(expected_fu, rel=1e-6)


def test_absent_protein_binding_is_reported():
    r = ED.extract_fraction_unbound({"name": "X"})
    assert r["fu"] is None and r["reason"]


# ───────────────── no input, no dose. never a default. ────────────────────

@pytest.mark.parametrize("missing,needles", [
    # With neither SMILES nor a sequence the modality itself is undeterminable,
    # so the domain gate refuses first. Either refusal is honest; both must
    # name what is missing.
    ("smiles", ("smiles", "modality")),
    ("mw", ("molecular weight",)),
])
def test_a_missing_input_yields_an_honest_null(missing, needles):
    cand = dict(GOOD)
    cand.pop(missing)
    r = ED.efficacious_dose(cand, modeler=FakeModeler())
    assert r["available"] is False and r["dose_mg"] is None
    assert any(n in r["reason"].lower() for n in needles), r["reason"]


def test_no_potency_means_no_dose():
    cand = dict(GOOD, pharmacology={"pharmacokinetics": {"distribution": {"ppb": 90.0}}})
    r = ED.efficacious_dose(cand, modeler=FakeModeler())
    assert r["available"] is False and r["dose_mg"] is None


def test_no_protein_binding_means_no_dose():
    cand = dict(GOOD, pharmacology={"pharmacodynamics": {"potency": {"ic50": 50.0}}})
    r = ED.efficacious_dose(cand, modeler=FakeModeler())
    assert r["available"] is False and r["dose_mg"] is None


def test_a_pbpk_failure_yields_a_null_not_a_guess():
    r = ED.efficacious_dose(GOOD, modeler=FakeModeler(fail=True))
    assert r["available"] is False and r["dose_mg"] is None
    assert "PBPK" in r["reason"]


def test_a_pbpk_result_without_a_dose_is_not_invented():
    class Empty(FakeModeler):
        def optimize_dosing(self, **kw):
            return {"dose_mg": None}
    r = ED.efficacious_dose(GOOD, modeler=Empty())
    assert r["available"] is False and r["dose_mg"] is None


def test_no_default_dose_appears_anywhere_in_the_module():
    """The head it replaces had a 200 mg fallback and a 5-1000 range."""
    src = open(os.path.join(BACKEND, "efficacious_dose.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "dose_mg = 200" not in code
    assert "or 200" not in code


# ──────────────────────── the happy path is traceable ─────────────────────

def test_a_derived_dose_carries_its_whole_chain():
    m = FakeModeler(dose=125.0, interval=12.0)
    r = ED.efficacious_dose(GOOD, modeler=m)
    assert r["available"] is True and r["dose_mg"] == 125.0 and r["interval_h"] == 12.0
    # every link present
    assert r["potency"]["value_nm"] == 50.0
    assert r["protein_binding"]["fu"] == pytest.approx(0.10)
    assert r["target_exposure"]["target_cmin_mg_L"] == pytest.approx(0.2, rel=1e-6)
    assert "PBPK" in r["derivation"] or "PBPK" in r["method"]
    assert "not a clinical prediction" in r["caveat"]


def test_the_pbpk_receives_the_computed_target_not_a_constant():
    m = FakeModeler()
    ED.efficacious_dose(GOOD, modeler=m)
    call = m.calls[0]
    assert call["target_cmin"] == pytest.approx(0.2, rel=1e-6)
    assert call["target_cmax"] > call["target_cmin"]


def test_a_more_potent_compound_needs_a_lower_target_exposure():
    """The direction of the chain must be right, not just its arithmetic."""
    weak = ED.target_exposure(500.0, 0.1, 400.0)["target_cmin_mg_L"]
    strong = ED.target_exposure(5.0, 0.1, 400.0)["target_cmin_mg_L"]
    assert strong < weak


# ─────────────────── the dose must not change between runs ────────────────

def test_the_dose_uses_the_deterministic_optimizer():
    """Measured: QAOA-PK returned 217.7 / 218.7 / 215.9 mg on identical input.

    A recommended dose that moves between runs of the same molecule is not
    usable, so the derivation must ask for the classical solve explicitly.
    """
    seen = {}

    class Recording(FakeModeler):
        def optimize_dosing(self, smiles, target_cmin, target_cmax,
                            weight_kg=70.0, optimizer=None):
            seen["optimizer"] = optimizer
            return {"dose_mg": self.dose, "interval_h": self.interval}

    r = ED.efficacious_dose(GOOD, modeler=Recording())
    assert r["available"] is True
    assert seen["optimizer"] == "classical", (
        "the dose asked for %r; it must ask for the deterministic solver"
        % seen["optimizer"])


def test_an_older_modeler_without_the_selector_still_works():
    """A modeler that predates the selector must not break the derivation."""
    r = ED.efficacious_dose(GOOD, modeler=FakeModeler(dose=99.0))
    assert r["available"] is True and r["dose_mg"] == 99.0


def test_the_same_candidate_gives_the_same_dose_twice():
    a = ED.efficacious_dose(GOOD, modeler=FakeModeler())
    b = ED.efficacious_dose(GOOD, modeler=FakeModeler())
    assert a["dose_mg"] == b["dose_mg"]


# ─────────────── only the modality the model actually covers ──────────────

@pytest.mark.parametrize("cand,expected", [
    ({"smiles": "CCO", "mw": 300.0}, "small_molecule"),
    ({"sequence": "FDVRWDFSAED", "is_peptide": True}, "peptide"),
    ({"sequence": "AUGGCUAGC" * 5, "modality": "mRNA"}, "oligonucleotide"),
    ({"cdr_h3": "ARDYW", "mw": 150000.0}, "biologic"),
    ({}, "unknown"),
])
def test_modality_is_detected(cand, expected):
    assert ED.detect_modality(cand) == expected


@pytest.mark.parametrize("cand", [
    {"name": "m", "sequence": "AUGGCUAGC" * 20, "modality": "mRNA",
     "mw": 250000.0, "smiles": "CCO",
     "pharmacology": {"pharmacodynamics": {"potency": {"ic50": 50.0}},
                      "pharmacokinetics": {"distribution": {"ppb": 10.0}}}},
    {"name": "p", "sequence": "FDVRWDFSAED", "is_peptide": True, "mw": 1386.3,
     "smiles": "CC(C)[C@H](N)C(=O)O",
     "pharmacology": {"pharmacodynamics": {"potency": {"ic50": 50.0}},
                      "pharmacokinetics": {"distribution": {"ppb": 70.4}}}},
    {"name": "a", "cdr_h3": "ARDYW", "mw": 150000.0, "smiles": "CCO",
     "pharmacology": {"pharmacodynamics": {"potency": {"ic50": 5.0}},
                      "pharmacokinetics": {"distribution": {"ppb": 50.0}}}},
])
def test_an_out_of_domain_modality_gets_no_dose(cand):
    """MEASURED 2026-09-18, before the gate: an mRNA construct with complete
    inputs returned 43,650 mg. Real mRNA vaccine doses are 30-100 ug -- wrong by
    about a millionfold, and delivered with the same confidence as a number
    inside the model's domain. The PBPK model is small-molecule machinery.
    """
    r = ED.efficacious_dose(cand, modeler=FakeModeler())
    assert r["available"] is False and r["dose_mg"] is None
    assert r["modality"] in ("peptide", "oligonucleotide", "biologic")
    assert len(r["reason"]) > 40, "a refusal must explain itself"


def test_the_refusal_happens_before_the_pbpk_is_called():
    """An out-of-domain candidate must not consume a PBPK solve either."""
    class Exploding(FakeModeler):
        def optimize_dosing(self, **kw):
            raise AssertionError("the PBPK ran for an out-of-domain modality")
    r = ED.efficacious_dose(
        {"name": "m", "sequence": "AUGGCUAGC" * 20, "modality": "mRNA",
         "mw": 250000.0, "smiles": "CCO"}, modeler=Exploding())
    assert r["available"] is False


def test_a_small_molecule_still_gets_its_dose():
    """The gate must narrow the domain, not close it."""
    r = ED.efficacious_dose(GOOD, modeler=FakeModeler())
    assert r["available"] is True and r["dose_mg"] == 125.0


# ───────────── a dose must not depend on which substrate answered ─────────

class _NoSelectorModeler:
    """The deployed copy: optimize_dosing with no `optimizer` parameter."""

    def optimize_dosing(self, smiles, target_cmin, target_cmax, weight_kg=70.0):
        return {"dose_mg": 50.0, "interval_h": 24.0}


class _SelectorModeler:
    def optimize_dosing(self, smiles, target_cmin, target_cmax, weight_kg=70.0,
                        optimizer="quantum_first"):
        assert optimizer == "classical", "the dose must ask for the deterministic path"
        return {"dose_mg": 7.5, "interval_h": 24.0}


def _cand():
    return {"name": "T", "target": "KRAS", "modality": "small_molecule",
            "smiles": "CC", "mw": 600.0,
            "pharmacology": {"pharmacodynamics": {"potency": {"ic50": 0.2}},
                             "pharmacokinetics": {"distribution": {"ppb": 95.0}}}}


def test_the_dose_asks_for_the_deterministic_optimizer():
    d = ED.efficacious_dose(_cand(), modeler=_SelectorModeler())
    assert d["available"] is True
    assert d["optimizer"] == "classical" and d["deterministic"] is True


def test_a_modeler_without_the_selector_is_not_reported_as_deterministic():
    """It silently ran QAOA-PK and the record claimed classical: 51.2/49.3/48.8 mg."""
    d = ED.efficacious_dose(_cand(), modeler=_NoSelectorModeler())
    assert d["available"] is True
    assert d["optimizer"] == "unknown_no_selector"
    assert d["deterministic"] is False, "it must not claim a determinism it lost"


# ───── the domain gates: a wrong mechanism is not a calibration error ─────

def test_the_attainability_gate_refuses_an_unreachable_trough():
    """Ibuprofen: 99% bound with a micromolar IC50 needs 268 mg/L at trough.
    The inverse solve answers anyway, 700x high."""
    c = {"name": "Ibuprofen", "modality": "small_molecule", "smiles": "CC(C)Cc1ccccc1",
         "mw": 206.3,
         "pharmacology": {"pharmacodynamics": {"potency": {"ic50": 13000.0}},
                          "pharmacokinetics": {"distribution": {"ppb": 99.0}}}}
    d = ED.efficacious_dose(c)
    assert d["available"] is False
    assert "not reachable by oral dosing" in d["reason"]


def test_an_attainable_trough_passes_the_gate():
    a = ED.attainability(0.5)
    assert a["attainable"] is True and a["reason"] is None


def test_the_ceiling_is_reported_with_the_requirement():
    a = ED.attainability(5000.0)
    assert a["attainable"] is False
    assert a["ceiling_mg_L"] == ED.ATTAINABLE_CMIN_MG_L
    assert a["required_cmin_mg_L"] == 5000.0


@pytest.mark.parametrize("mech", ["prodrug", "irreversible", "covalent",
                                  "intracellular_transporter", "cumulative"])
def test_a_mechanism_the_chain_cannot_model_is_refused(mech):
    c = _cand()
    c["mechanism"] = mech
    d = ED.efficacious_dose(c, modeler=_SelectorModeler())
    assert d["available"] is False
    assert "outside the model" in d["reason"]


def test_an_undeclared_mechanism_proceeds_but_states_the_assumption():
    """The assumption is stated rather than verified -- and carried on the result."""
    g = ED.mechanism_gate({})
    assert g["ok"] is True and g["declared"] is None
    assert "reversible inhibition of a plasma-accessible target" in g["assumption"]
    d = ED.efficacious_dose(_cand(), modeler=_SelectorModeler())
    assert d["mechanism"]["assumption"] == ED.MECHANISM_ASSUMPTION


def test_a_reversible_mechanism_is_allowed_through():
    c = _cand()
    c["mechanism"] = "reversible competitive inhibitor"
    d = ED.efficacious_dose(c, modeler=_SelectorModeler())
    assert d["available"] is True


# ─────────── calibration is opt-in and carries its provenance ─────────────

def test_the_dose_is_uncalibrated_by_default():
    """A factor fitted on four molecules must be asked for."""
    d = ED.efficacious_dose(_cand(), modeler=_SelectorModeler())
    assert d["calibrated"] is False
    assert "Uncalibrated" in d["calibration"]


def test_calibration_divides_out_the_measured_bias():
    raw = ED.efficacious_dose(_cand(), modeler=_SelectorModeler())
    cal = ED.efficacious_dose(_cand(), modeler=_SelectorModeler(), calibrated=True)
    assert cal["dose_mg"] == pytest.approx(
        raw["dose_mg"] / ED.CALIBRATION_FACTOR, abs=0.01)
    assert cal["calibrated"] is True


def test_the_calibration_states_its_sample_size_and_loo_error():
    cal = ED.efficacious_dose(_cand(), modeler=_SelectorModeler(), calibrated=True)
    assert "n=4" in cal["calibration"]
    assert "2.4x" in cal["calibration"]
    assert "cannot establish accuracy" in cal["calibration"]
