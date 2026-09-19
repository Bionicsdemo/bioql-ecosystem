"""A literature monitor that proposes nothing.

Every number it returns is a verbatim span of a named abstract with its PMID.
It never averages across papers, never infers, and when the source is
unreachable it reports nothing rather than a remembered value.

Network is mocked throughout; one live check lives outside the suite.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import literature_monitor as LM  # noqa: E402
import literature_value_extraction as LX  # noqa: E402
import typesafe_client as TS  # noqa: E402

ABSTRACT_A = ("MRTX1133 inhibited KRAS G12D with a biochemical IC50 of 0.2 nM "
              "and wild-type KRAS with an IC50 of 140 nM.")
ABSTRACT_B = ("In our hands the same compound showed a KRAS G12D IC50 of 1.4 nM "
              "under identical assay conditions.")


def _papers(*abstracts):
    return [{"pmid": "PM%d" % i, "doi": "10.0/%d" % i, "title": "t%d" % i,
             "journal": "J", "year": "2026", "abstract": a,
             "url": "https://europepmc.org/article/MED/%d" % i}
            for i, a in enumerate(abstracts)]


def _pick_first(monkeypatch):
    """The model always selects candidate span 0 of whatever it is shown."""
    monkeypatch.setattr(TS, "ask", lambda *a, **k: {
        "answers": {"which_value": {"choice": "0", "confidence": 0.9}}, "usage": {}})


# ─────────────────── every value carries its citation ─────────────────────

def test_each_value_names_the_paper_it_came_from(monkeypatch):
    monkeypatch.setattr(LM, "search_abstracts", lambda *a, **k: _papers(ABSTRACT_A))
    _pick_first(monkeypatch)
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    assert r["available"] is True
    v = r["values"][0]
    assert v["pmid"] == "PM0"
    assert v["url"].startswith("https://europepmc.org/")
    assert v["value_nm"] == pytest.approx(0.2)


def test_the_span_is_locatable_in_the_abstract_it_cites(monkeypatch):
    papers = _papers(ABSTRACT_A)
    monkeypatch.setattr(LM, "search_abstracts", lambda *a, **k: papers)
    _pick_first(monkeypatch)
    v = LM.find_potency("MRTX1133", "KRAS G12D")["values"][0]
    lo, hi = v["source_offsets"]
    assert papers[0]["abstract"][lo:hi] == v["selected_span"]


def test_the_result_states_it_was_read_not_computed(monkeypatch):
    monkeypatch.setattr(LM, "search_abstracts", lambda *a, **k: _papers(ABSTRACT_A))
    _pick_first(monkeypatch)
    v = LM.find_potency("MRTX1133", "KRAS G12D")["values"][0]
    assert "READ from supplied text" in v["provenance"]


# ───────────────── disagreement is reported, never averaged ───────────────

def test_two_papers_give_two_values_side_by_side(monkeypatch):
    monkeypatch.setattr(LM, "search_abstracts",
                        lambda *a, **k: _papers(ABSTRACT_A, ABSTRACT_B))
    _pick_first(monkeypatch)
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    assert len(r["values"]) == 2
    got = sorted(v["value_nm"] for v in r["values"])
    assert got == pytest.approx([0.2, 1.4])
    assert {v["pmid"] for v in r["values"]} == {"PM0", "PM1"}
    assert "never averaged" in r["note"]


def test_no_aggregate_value_is_produced(monkeypatch):
    """There must be no single "the potency" field to mistake for a consensus."""
    monkeypatch.setattr(LM, "search_abstracts",
                        lambda *a, **k: _papers(ABSTRACT_A, ABSTRACT_B))
    _pick_first(monkeypatch)
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    for forbidden in ("value_nm", "mean_nm", "median_nm", "consensus_nm"):
        assert forbidden not in r


# ──────────────────── nothing found is a result, not a bug ────────────────

def test_abstracts_with_no_stated_potency_yield_nothing(monkeypatch):
    monkeypatch.setattr(LM, "search_abstracts",
                        lambda *a, **k: _papers("This review discusses KRAS biology."))
    monkeypatch.setattr(TS, "ask", lambda *a, **k: {
        "answers": {"which_value": {"choice": "none"}}, "usage": {}})
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    assert r["available"] is False and r["values"] == []
    assert "That is a result, not a failure" in r["reason"]


def test_no_matching_abstract_is_reported_plainly(monkeypatch):
    monkeypatch.setattr(LM, "search_abstracts", lambda *a, **k: [])
    r = LM.find_potency("Nonexistol", "NOTAREALTARGET")
    assert r["available"] is False and r["papers_read"] == 0


# ────────────── an unreachable source reports nothing at all ──────────────

def test_an_unreachable_source_yields_no_value(monkeypatch):
    def _down(*a, **k):
        raise LM.LiteratureUnavailable("Europe PMC unreachable: timed out")
    monkeypatch.setattr(LM, "search_abstracts", _down)
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    assert r["available"] is False and r["values"] == []
    assert "did not run" in r["note"]


def test_one_bad_paper_does_not_stop_the_sweep(monkeypatch):
    papers = _papers(ABSTRACT_A, ABSTRACT_B)
    monkeypatch.setattr(LM, "search_abstracts", lambda *a, **k: papers)
    calls = {"n": 0}

    def _ask(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TS.TypeSafeError("transient")
        return {"answers": {"which_value": {"choice": "0", "confidence": 0.9}}}

    monkeypatch.setattr(TS, "ask", _ask)
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    assert len(r["values"]) == 1, "the second paper is still read"


def test_a_model_answer_outside_the_text_is_refused_and_recorded(monkeypatch):
    monkeypatch.setattr(LM, "search_abstracts", lambda *a, **k: _papers(ABSTRACT_A))
    monkeypatch.setattr(TS, "ask", lambda *a, **k: {
        "answers": {"which_value": {"choice": "9999"}}, "usage": {}})
    r = LM.find_potency("MRTX1133", "KRAS G12D")
    assert r["values"] == []
    assert r["refusals"] and "not in the text" in r["refusals"][0]["reason"]


# ─────────────────────────── query and cleaning ───────────────────────────

def test_the_query_names_compound_target_and_measure():
    q = LM.build_query("MRTX1133", "KRAS G12D", "IC50")
    for part in ("MRTX1133", "KRAS G12D", "IC50"):
        assert '"%s"' % part in q
    assert " AND " in q


def test_markup_is_stripped_before_offsets_are_taken():
    """Offsets must index the text the extractor was given, not the raw HTML."""
    raw = "KRAS&lt;sup&gt;G12D&lt;/sup&gt; IC50 was 5 nM"
    clean = LM._strip_tags(raw)
    assert clean == "KRASG12D IC50 was 5 nM"
    assert "&lt;" not in clean


def test_a_candidate_without_a_target_is_not_searched():
    r = LM.potency_for_candidate({"name": "X"})
    assert r["available"] is False and "no target" in r["reason"]


def test_a_candidate_without_a_name_is_not_searched():
    r = LM.potency_for_candidate({"target": "KRAS"})
    assert r["available"] is False and "no name" in r["reason"]


def test_the_question_id_clears_the_text_only_boundary():
    TS.assert_text_only_target("which_value")


def test_a_comparison_operator_survives_cleaning():
    """"IC50 &lt; 10 nM" is a normal way to state a potency bound. Decoding
    before stripping would turn it into a tag and eat the rest of the sentence."""
    clean = LM._strip_tags("The IC50 was &lt; 10 nM and the Ki &gt; 5 uM")
    assert clean == "The IC50 was < 10 nM and the Ki > 5 uM"


def test_a_real_html_tag_is_still_removed():
    assert LM._strip_tags("KRAS<sup>G12D</sup> IC50 5 nM") == "KRASG12D IC50 5 nM"
