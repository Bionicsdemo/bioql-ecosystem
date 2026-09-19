"""A value that is not in the text cannot come out of this module.

That is the whole safety argument for letting a model near a measurement. The
model chooses among spans a regex found; code copies the chosen span unchanged.
If the model ever returns something else, the module raises rather than pass it
on -- because a fabricated potency would flow straight into a dose.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import literature_value_extraction as LX  # noqa: E402
import typesafe_client as TS  # noqa: E402

PAPER = (
    "Compound 7a inhibited KRAS G12D with an IC50 of 12.4 nM in the biochemical "
    "assay. Against the off-target HRAS the IC50 was 3.2 uM. Cell viability was "
    "unaffected below 50 uM. The reference inhibitor showed 890 pM potency."
)


def _pick(monkeypatch, choice, confidence=0.95):
    def _ask(state, questions, **kw):
        return {"answers": {"which_value": {"type": "choice",
                                            "choice": choice,
                                            "confidence": confidence}},
                "model": "jev-test", "usage": {}}
    monkeypatch.setattr(TS, "ask", _ask)


# ─────────────────────── the regex over-finds on purpose ──────────────────

def test_every_concentration_in_the_text_becomes_a_candidate():
    """A missed candidate can never be selected; a spurious one is just rejected."""
    c = LX.find_candidates(PAPER)
    spans = [x["span"] for x in c]
    assert any("12.4" in s for s in spans)
    assert any("3.2" in s for s in spans)
    assert any("50" in s for s in spans)
    assert any("890" in s for s in spans)
    assert len(c) >= 4


def test_each_candidate_carries_its_context_and_offsets():
    c = LX.find_candidates(PAPER)[0]
    assert c["context"] and c["start"] < c["end"]
    assert PAPER[c["start"]:c["end"]] == c["span"], "offsets must locate the span"


# ───────────────────────────── unit handling ──────────────────────────────

@pytest.mark.parametrize("value,unit,expected", [
    ("12.4", "nM", 12.4),
    ("3.2", "uM", 3200.0),
    ("890", "pM", 0.89),
    ("1", "mM", 1e6),
    ("1,5", "nM", 1.5),          # comma decimal, as papers often print it
])
def test_units_convert_to_nanomolar(value, unit, expected):
    assert LX.to_nanomolar(value, unit) == pytest.approx(expected)


def test_an_unresolvable_unit_returns_none_not_a_guess():
    assert LX.to_nanomolar("12.4", "furlongs") is None


# ─────────── the invariant: nothing comes out that was not in ─────────────

def test_a_value_the_regex_never_found_is_refused(monkeypatch):
    """The guarantee is enforced, not assumed."""
    _pick(monkeypatch, "999")           # not a valid option index
    with pytest.raises(LX.NotInText) as exc:
        LX.select_value(PAPER, "KRAS G12D")
    assert "not in the text" in str(exc.value)


def test_the_returned_span_is_character_for_character_from_the_source(monkeypatch):
    cands = LX.find_candidates(PAPER)
    idx = next(i for i, c in enumerate(cands) if "12.4" in c["span"])
    _pick(monkeypatch, str(idx))
    r = LX.select_value(PAPER, "KRAS G12D", candidates=cands)
    assert r["available"] is True
    lo, hi = r["source_offsets"]
    assert PAPER[lo:hi] == r["selected_span"], (
        "the span must be locatable, verbatim, in the source")
    assert r["value_nm"] == pytest.approx(12.4)


def test_the_result_states_it_was_read_not_computed(monkeypatch):
    _pick(monkeypatch, "0")
    r = LX.select_value(PAPER, "KRAS G12D")
    assert "READ from supplied text" in r["provenance"]
    assert "not computed or estimated" in r["provenance"]


# ──────────────────── a no-match must be possible ─────────────────────────

def test_none_is_always_an_option(monkeypatch):
    """Without a no-match the model is forced to pick even when nothing fits."""
    seen = {}

    def _ask(state, questions, **kw):
        seen["criteria"] = questions["which_value"]["criteria"]
        return {"answers": {"which_value": {"choice": "none"}}, "usage": {}}

    monkeypatch.setattr(TS, "ask", _ask)
    r = LX.select_value(PAPER, "EGFR")
    assert "none" in seen["criteria"]
    assert r["available"] is False and r["value_nm"] is None


def test_text_without_any_concentration_yields_nothing():
    r = LX.select_value("This paper reports no binding data whatsoever.", "KRAS")
    assert r["available"] is False and r["value_nm"] is None
    assert "Nothing to select from" in r["reason"]


# ──────────────────── degrading, never fabricating ────────────────────────

def test_an_unconfigured_service_extracts_nothing(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(TS, "TOKEN_FILE", str(tmp_path / "absent.json"))
    r = LX.select_value(PAPER, "KRAS G12D")
    assert r["available"] is False and r["value_nm"] is None


def test_a_service_failure_extracts_nothing(monkeypatch):
    def _fail(*a, **k):
        raise TS.TypeSafeError("down")
    monkeypatch.setattr(TS, "ask", _fail)
    r = LX.select_value(PAPER, "KRAS G12D")
    assert r["available"] is False and r["value_nm"] is None


def test_a_candidate_without_a_target_gets_no_potency():
    """A potency is meaningless without saying what it is against."""
    r = LX.potency_for_candidate({"name": "X"}, PAPER)
    assert r["available"] is False
    assert "target" in r["reason"].lower()


# ───────────────────────── boundary still holds ───────────────────────────

def test_the_question_id_clears_the_text_only_boundary():
    """Even here, the question must not be named after a measured field."""
    TS.assert_text_only_target("which_value")
