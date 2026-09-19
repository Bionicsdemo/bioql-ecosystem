"""Recompute a composite score over the components that actually have evidence.

THE PROBLEM
    The composite is a weighted sum over the scored components. When one did
    not run, the pipeline still supplies a number -- the "no information"
    midpoint -- and the weighted sum treats it as a measurement. The composite
    is then a blend of what was measured with what was assumed.

NOTHING HERE IS HARDCODED, AND THAT IS THE POINT
    A module whose job is to find fabricated values must not contain any. So:

    * The COMPONENTS come from the candidate's own `score_breakdown` keys.
      An earlier version carried a table of component names and reported all
      four as "absent" for 167 antibody candidates scored on a different set.
      They were not absent; they were not applicable.

    * The WEIGHTS come from the record -- the per-component `weight` the
      pipeline wrote, or the run's `scoring_weights`. If neither is present the
      weighting is equal across components and `weight_source` says so, rather
      than a table asserting numbers nobody recorded.

    * The NO-INFORMATION VALUES are derived from the cohort, not listed. A
      value that repeats verbatim across many distinct molecules is a default;
      that is an empirical fact about the set, and the threshold is stated.
      Without a cohort, nothing is presumed to be a default.

WHAT IT DELIBERATELY DOES NOT DO
    It never overwrites. A published score stays published; this sits beside it
    with the delta and what was dropped, so switching is a decision, not a
    silent rewrite of history. `stage_audit` flags the contradiction; this
    quantifies it.

THE CASE IT CANNOT FIX
    Where a score sits on a cohort-derived default and the record says nothing
    either way, the answer is `undecidable`, not `absent`. A missing value is
    recoverable; a value with no provenance is not.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# A value repeating verbatim on this many distinct candidates is a default
# rather than a measurement. Stated here because it is a judgement, and the
# only one in the module.
DEFAULT_REPEAT_THRESHOLD = 3

# A status that says the analysis behind a component produced no result. These
# are string constants the pipeline writes, not quantities.
_ABSENT_STATUS = ("skipped", "unavailable", "error", "failed", "not_run")
_PRESENT_STATUS = ("completed", "success", "ok", "done")

# Keys under a component's analysis block that describe rather than measure.
_NON_RESULT_KEYS = ("status", "reason", "note", "method", "error")


def _dig(d: Any, *path) -> Any:
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _num(v: Any) -> Optional[float]:
    if isinstance(v, dict):
        v = v.get("value")
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def breakdown_of(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """The score_breakdown, wherever this schema put it."""
    for path in (("analyses", "scoring", "score_breakdown"),
                 ("score_breakdown",),
                 ("scoring", "score_breakdown")):
        v = _dig(candidate, *path)
        if isinstance(v, dict) and v:
            return v
    return {}


def components_of(candidate: Dict[str, Any]) -> List[str]:
    """The components THIS candidate was scored on, read from its own record."""
    bd = breakdown_of(candidate)
    out = []
    for k, v in bd.items():
        if _component_score(bd, k) is not None or isinstance(v, dict):
            out.append(k)
    return out


def _component_score(breakdown: Dict[str, Any], component: str) -> Optional[float]:
    """The component's score, whichever shape this schema used.

    Nested as {"admet": {"score": 0.5, "weight": 0.2}} in small-molecule runs,
    bare as {"binding": 1.0} in antibody runs. Reading only the nested form
    reported every antibody component as having no score at all.
    """
    v = (breakdown or {}).get(component)
    if isinstance(v, dict):
        return _num(v.get("score"))
    return _num(v)


def weights_of(candidate: Dict[str, Any],
               components: List[str]) -> Tuple[Dict[str, float], str]:
    """The weights the record states, or an equal split that says it is one."""
    bd = breakdown_of(candidate)

    recorded = {}
    for c in components:
        w = _num(_dig(bd, c, "weight"))
        if w is not None and w > 0:
            recorded[c] = w
    if len(recorded) == len(components) and components:
        return recorded, "per-component `weight` recorded in score_breakdown"

    for path in (("analyses", "scoring", "scoring_weights"),
                 ("scoring_weights",), ("scoring", "scoring_weights")):
        sw = _dig(candidate, *path)
        if isinstance(sw, dict):
            got = {c: _num(sw.get(c)) for c in components}
            if all(v is not None and v > 0 for v in got.values()) and got:
                return got, "run-level `scoring_weights` recorded in the result"

    if not components:
        return {}, "no components"
    equal = round(1.0 / len(components), 6)
    return ({c: equal for c in components},
            "EQUAL across %d components -- the record states no weights, so "
            "none are assumed" % len(components))


def derive_default_values(cohort: List[Dict[str, Any]],
                          threshold: int = DEFAULT_REPEAT_THRESHOLD
                          ) -> Dict[str, set]:
    """Per component, the score values that repeat across distinct candidates.

    Empirical, not tabulated: a number identical on many different molecules is
    what gets written when nothing was measured. With no cohort this returns
    nothing, and no value is presumed to be a default.
    """
    seen: Dict[str, Counter] = {}
    for cand in cohort or []:
        bd = breakdown_of(cand)
        for comp in bd:
            s = _component_score(bd, comp)
            if s is None:
                continue
            seen.setdefault(comp, Counter())[s] += 1
    return {comp: {v for v, n in counts.items() if n >= threshold}
            for comp, counts in seen.items()}


def _analysis_status(candidate: Dict[str, Any], component: str) -> Optional[str]:
    for path in (("analyses", component, "status"), (component, "status"),
                 ("analyses", component + "_profile", "status")):
        v = _dig(candidate, *path)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return None


def _has_analysis_content(candidate: Dict[str, Any], component: str) -> bool:
    """Any substantive field under the component's own analysis block."""
    for path in (("analyses", component), (component,)):
        v = _dig(candidate, *path)
        if isinstance(v, dict):
            if {k for k in v if k not in _NON_RESULT_KEYS}:
                return True
    return False


def classify_component(candidate: Dict[str, Any], component: str,
                       defaults: Optional[Dict[str, set]] = None
                       ) -> Tuple[str, str]:
    """`evidenced` | `absent` | `undecidable`, with the reason.

    `undecidable` is not a soft `absent`: one is a fact, the other is a gap, and
    blending them is how a gap becomes a number.
    """
    score = _component_score(breakdown_of(candidate), component)
    status = _analysis_status(candidate, component)

    if status in _ABSENT_STATUS:
        return "absent", "analyses.%s.status is %r" % (component, status)
    if score is None:
        return "absent", "no score recorded for %s" % component
    if status in _PRESENT_STATUS:
        return "evidenced", "analyses.%s.status is %r" % (component, status)
    if _has_analysis_content(candidate, component):
        return "evidenced", "analyses.%s carries result fields" % component
    if score in (defaults or {}).get(component, set()):
        return "undecidable", (
            "%s = %s repeats verbatim across candidates in this set, which is "
            "what gets written when nothing was measured -- and the record "
            "carries no status and no result fields either way. Whether it was "
            "measured cannot be determined from this record."
            % (component, score))
    return "evidenced", "a score is present and does not repeat across the set"


def recompute(candidate: Dict[str, Any],
              *,
              cohort: Optional[List[Dict[str, Any]]] = None,
              weights: Optional[Dict[str, float]] = None,
              undecidable_counts_as_absent: bool = False) -> Dict[str, Any]:
    """Composite over evidenced components, weights renormalised. Never writes.

    `cohort` is what makes a repeated value detectable; without it nothing is
    presumed to be a default. `undecidable_counts_as_absent` is off by default:
    dropping an undecidable component would rewrite a published score on an
    assumption. Turn it on to see what those scores would become.
    """
    bd = breakdown_of(candidate)
    published = _num(_dig(candidate, "analyses", "scoring", "composite_score"))
    if published is None:
        published = _num(candidate.get("composite_score"))

    components = components_of(candidate)
    if not components:
        return {
            "available": False,
            "composite_published": published,
            "composite_evidenced": None,
            "reason": ("This candidate records no score_breakdown, so there are "
                       "no components to weigh. Nothing is assumed about which "
                       "ones it should have had."),
            "components": [],
        }

    w, weight_source = (dict(weights), "supplied by the caller") if weights \
        else weights_of(candidate, components)
    defaults = derive_default_values(cohort) if cohort else {}

    rows: List[Dict[str, Any]] = []
    for comp in components:
        verdict, reason = classify_component(candidate, comp, defaults)
        rows.append({"component": comp, "verdict": verdict, "reason": reason,
                     "score": _component_score(bd, comp),
                     "weight": w.get(comp)})

    def _keep(r):
        if r["verdict"] == "evidenced":
            return True
        if r["verdict"] == "undecidable":
            return not undecidable_counts_as_absent
        return False

    kept = [r for r in rows
            if _keep(r) and r["score"] is not None and r["weight"]]
    dropped = [r for r in rows if not _keep(r)]

    if not kept:
        return {
            "available": False,
            "composite_published": published,
            "composite_evidenced": None,
            "reason": ("No component has evidence behind it, so there is no "
                       "composite to recompute. The published number is a "
                       "weighted sum of assumptions."),
            "weight_source": weight_source,
            "components": rows,
        }

    total_w = sum(r["weight"] for r in kept)
    recomputed = sum(r["score"] * (r["weight"] / total_w) for r in kept)

    # The same weights over EVERY scored component. Comparing against this, not
    # against the published number, isolates the effect of dropping unevidenced
    # components. Against the published number the delta also carries any
    # difference between the recorded weights and these -- which, where the
    # record states none and the split is equal, is a weighting artefact and
    # not an evidence effect. 125 of 232 recomputable historical candidates are
    # in that case.
    scored = [r for r in rows if r["score"] is not None and r["weight"]]
    all_w = sum(r["weight"] for r in scored)
    same_weights_all = (sum(r["score"] * (r["weight"] / all_w) for r in scored)
                        if all_w else None)

    return {
        "available": True,
        "composite_published": published,
        "composite_evidenced": round(recomputed, 4),
        "delta": (round(recomputed - published, 4) if published is not None else None),
        "composite_all_components_same_weights": (
            round(same_weights_all, 4) if same_weights_all is not None else None),
        # The evidence effect alone: same weights, with and without the
        # unevidenced components. This is the number to quote.
        "delta_from_evidence": (
            round(recomputed - same_weights_all, 4)
            if same_weights_all is not None else None),
        "weight_covered_by_evidence": round(total_w, 4),
        "weight_source": weight_source,
        "components_kept": [r["component"] for r in kept],
        "components_dropped": [r["component"] for r in dropped],
        "undecidable": [r["component"] for r in rows if r["verdict"] == "undecidable"],
        "default_detection": ("cohort of %d candidates, threshold %d repeats"
                              % (len(cohort), DEFAULT_REPEAT_THRESHOLD)) if cohort
                             else "no cohort supplied; no value presumed default",
        "components": rows,
        "method": ("weighted sum over evidenced components only, weights "
                   "renormalised across them"),
        "note": ("Nothing was written back. The published composite is left as "
                 "it is; this is what it would be if only measured components "
                 "counted."),
    }
