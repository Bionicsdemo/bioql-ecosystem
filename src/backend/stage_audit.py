"""Check a stage's output before it flows downstream. Quarantine, never repair.

WHY THIS EXISTS
    KRAS-005 shipped labelled "Good" while its own toxicology block said GHS
    Category 1 (Fatal). Neither stage was wrong in isolation. The failure was
    that nothing looked at the BOUNDARY between them: stage 3 wrote a hazard,
    stage 8 wrote a verdict, and the hazard never reached the verdict.

    `stage_solver` decides whether a stage should RUN. This module decides
    whether what a stage PRODUCED may be believed by the stages after it.

THE ASYMMETRY THAT MAKES IT SAFE
    Deterministic invariants run first and own the outcome. They are arithmetic
    and identity: an ordering, a range, a marker, a contradiction with what is
    already recorded. A judgment cannot clear one. The model is consulted only
    where code genuinely cannot decide, and it may only ESCALATE -- pass to
    flag. It can never turn a failed invariant into a pass.

    That direction is the whole safety argument. A verifier that can clear its
    own alarms is not a verifier.

QUARANTINE, NOT REPAIR
    A quarantined value is marked and withheld from downstream stages. It is
    not deleted, not defaulted, not recomputed and never replaced by an
    estimate. The absence is visible and carries its reason -- the same rule
    `stage_solver` follows for a skipped stage.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import typesafe_client as TS

# pass      -> flows downstream unchanged
# flag      -> flows, carrying a warning a human should see
# quarantine-> does NOT flow; recorded with its reason
VERDICTS = ("pass", "flag", "quarantine")

_ESCALATION = {"pass": 0, "flag": 1, "quarantine": 2}

# A value repeated verbatim across this many candidates is inherited, not
# measured. 38 of 80 candidates carried the same hardcoded 1500 mg/kg.
_INHERITANCE_MIN_REPEATS = 3

# CONFIGURATION, not measurement. A scoring weight is SUPPOSED to be identical
# on every candidate -- that is what makes the score comparable. Counting one
# as an inherited default is a false positive, and it was: measured across 507
# historical candidates it inflated the inheritance rate from 45% to 94%.
_CONFIG_SUFFIXES = ("weight", "weights", "coefficient", "coefficients",
                    "threshold", "thresholds", "cutoff", "scale", "factor",
                    "version", "n_samples", "seed", "max_iter", "tolerance")


def _is_config(path: str) -> bool:
    """True when the field sets policy rather than reporting a result."""
    last = path.rsplit(".", 1)[-1].lower().rstrip("0123456789[]")
    return last in _CONFIG_SUFFIXES or last.endswith("_weight")


def _tokens(s: str) -> set:
    """Split a path into word tokens, so `kd` cannot match inside `breakdown`.

    It did. A plain substring test put every `score_breakdown.*` field into the
    inherited-constant invariant, because "brea(kd)own" contains "kd" -- which
    is why that rate sat at 94% and would not move.
    """
    out, cur = set(), []
    for ch in str(s).lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.add("".join(cur))
            cur = []
    if cur:
        out.add("".join(cur))
    # `ld50_mg_kg` should also be findable as `ld50`
    return out | {t.split("_")[0] for t in out}


def _names_a_measurement(path: str, keys) -> bool:
    """True when a path segment IS one of `keys`, not merely contains one."""
    toks = _tokens(path)
    return any(k in toks for k in keys)

# Text that marks a placeholder the platform generated for itself.
_FABRICATION_MARKERS = ("SYNTHETIC_PDB_MARKER", "PLACEHOLDER", "FALLBACK_STRUCTURE")

# Verdict words that assert a candidate is acceptable. If one of these sits in
# the same record as an unresolved hard stop, the record contradicts itself.
_POSITIVE_VERDICTS = frozenset({"good", "excellent", "pass", "passed", "apto",
                                "viable", "recommended", "promising"})

# Recorded hazards that must defeat any positive verdict.
_HARD_STOPS = ("ghs category 1", "ghs category 2", "ghs_cat_1", "ghs_cat_2",
               "fatal", "micronucleus", "chromosome aberration", "carcinogen",
               "clinically disqualified", "genotoxic")

# Fields that EXPLAIN rather than RECORD. A note saying "re-evaluated with the
# hardened gate (GHS acute class, micronucleus / chromosome aberration...)" is
# a description of what was checked, not a finding that any of it was present.
# Matching prose like that is how a guard ends up firing on its own commentary
# -- which this one did, on a real candidate, the first time it ran live.
_PROSE_FIELDS = ("note", "notes", "explanation", "description", "rationale",
                 "summary", "instructions", "method", "caveat", "provenance",
                 "derivation", "reason", "interpretation", "disclaimer",
                 "scope", "comment", "detail", "details", "message")

# A recorded classification is short. A sentence is prose, whatever it is named.
_MAX_RECORDED_VALUE_CHARS = 120


def _is_prose(path: str, value: str) -> bool:
    """True when this leaf explains something rather than recording a result."""
    last = path.rsplit(".", 1)[-1].lower().rstrip("0123456789[]")
    return last in _PROSE_FIELDS or len(value) > _MAX_RECORDED_VALUE_CHARS


class Finding(dict):
    """One invariant result. Dict so it serialises into the pipeline record."""

    @property
    def failed(self) -> bool:
        return self["verdict"] != "pass"


def _finding(name: str, verdict: str, detail: str, *,
             field: Optional[str] = None,
             decided_by: str = "rule") -> Finding:
    return Finding({"invariant": name, "verdict": verdict, "detail": detail,
                    "field": field, "decided_by": decided_by})


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


def _walk(obj: Any, path: str = "") -> List[Tuple[str, Any]]:
    """Every leaf with its dotted path, so an invariant can name what it found."""
    out: List[Tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_walk(v, "%s.%s" % (path, k) if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            out.extend(_walk(v, "%s[%d]" % (path, i)))
    else:
        out.append((path, obj))
    return out


# ───────────────────────────── the invariants ─────────────────────────────
# Each returns a list of findings. They see only recorded facts, never a model.

def _inv_no_fabrication_markers(output: Dict[str, Any], candidate, prior):
    """A placeholder the platform made for itself must not pass as a result."""
    found = []
    for path, v in _walk(output):
        if isinstance(v, str):
            for marker in _FABRICATION_MARKERS:
                if marker in v:
                    found.append(_finding(
                        "no_fabrication_markers", "quarantine",
                        "%s carries %s: this is a placeholder this platform "
                        "generated, not a measurement or a structure."
                        % (path, marker), field=path))
    return found


def _inv_noael_below_loael(output: Dict[str, Any], candidate, prior):
    """No-effect level cannot exceed lowest-effect level. Arithmetic, not opinion."""
    noael = lowest = None
    for path, v in _walk(output):
        p = path.lower()
        if "noael" in p and noael is None:
            noael = (path, _num(v))
        elif "loael" in p and lowest is None:
            lowest = (path, _num(v))
    if noael and lowest and noael[1] is not None and lowest[1] is not None:
        if noael[1] > lowest[1]:
            return [_finding(
                "noael_below_loael", "quarantine",
                "NOAEL %s (%s) exceeds LOAEL %s (%s). One of the two is wrong; "
                "neither may be used until it is resolved."
                % (noael[1], noael[0], lowest[1], lowest[0]), field=noael[0])]
    return []


def _inv_verdict_matches_hazards(output: Dict[str, Any], candidate, prior):
    """The KRAS-005 invariant: a positive verdict beside an unresolved hard stop."""
    leaves = _walk(output) + _walk(candidate or {}) + _walk(prior or {})
    verdict_at = None
    for path, v in leaves:
        p = path.lower()
        if isinstance(v, str) and str(v).strip().lower() in _POSITIVE_VERDICTS:
            if any(w in p for w in ("class", "verdict", "recommendation",
                                    "candidate_class", "status", "label")):
                verdict_at = (path, v)
                break
    if not verdict_at:
        return []
    for path, v in leaves:
        if not isinstance(v, str):
            continue
        if _is_prose(path, v):
            continue
        low = v.strip().lower()
        for stop in _HARD_STOPS:
            if stop in low:
                return [_finding(
                    "verdict_matches_hazards", "quarantine",
                    "%s asserts %r while %s records %r. A verdict may not be "
                    "more favourable than the hazards recorded beside it."
                    % (verdict_at[0], verdict_at[1], path, v[:80]),
                    field=verdict_at[0])]
    return []


def _inv_units_declared(output: Dict[str, Any], candidate, prior):
    """A toxicity value without its unit is the bug that produced 95% Cat 1."""
    findings = []
    for path, v in _walk(output):
        p = path.lower()
        if not any(k in p for k in ("ld50", "noael", "loael", "ic50", "ec50")):
            continue
        if _num(v) is None or p.endswith(("_unit", "_units", ".unit", ".units")):
            continue
        siblings = [q for q, _ in _walk(output)
                    if q.rsplit(".", 1)[0] == path.rsplit(".", 1)[0]]
        if not any(s.lower().endswith(("_unit", "_units", "unit", "units"))
                   for s in siblings):
            findings.append(_finding(
                "units_declared", "flag",
                "%s = %s carries no unit field beside it. -log10(mol/kg) and "
                "mg/kg differ by orders of magnitude and look alike."
                % (path, v), field=path))
    return findings


def _inv_no_inherited_constant(output: Dict[str, Any], candidate, prior,
                               cohort: Optional[List[Dict[str, Any]]] = None):
    """The same number on many candidates is a default, not a measurement."""
    if not cohort:
        return []
    findings = []
    for path, v in _walk(output):
        n = _num(v)
        if n is None or n == 0:
            continue
        if not _names_a_measurement(
                path, ("ld50", "noael", "loael", "kd", "ic50", "ec50", "ki")):
            continue
        if _is_config(path):
            continue
        repeats = 0
        for other in cohort:
            for opath, ov in _walk(other):
                if opath == path and _num(ov) == n:
                    repeats += 1
                    break
        if repeats >= _INHERITANCE_MIN_REPEATS:
            findings.append(_finding(
                "no_inherited_constant", "quarantine",
                "%s = %s appears identically on %d candidates. A value shared "
                "verbatim across distinct molecules is inherited from a default, "
                "not measured from any of them." % (path, n, repeats), field=path))
    return findings


def _inv_probability_in_range(output: Dict[str, Any], candidate, prior):
    """A probability outside [0,1] means two scales were mixed somewhere."""
    findings = []
    for path, v in _walk(output):
        p = path.lower()
        if not any(k in p for k in ("probability", "_prob", "confidence",
                                    "plddt", "iptm", "ptm")):
            continue
        n = _num(v)
        if n is None:
            continue
        hi = 100.0 if "plddt" in p else 1.0
        if not (0.0 <= n <= hi):
            findings.append(_finding(
                "probability_in_range", "quarantine",
                "%s = %s lies outside [0, %g]. Two different scales were mixed."
                % (path, n, hi), field=path))
    return findings


def _inv_score_without_its_analysis(output: Dict[str, Any], candidate, prior):
    """A score component whose own analysis says it never ran.

    In a run of N candidates the heavy engines execute for the lead only, so
    N-1 candidates get `admet_score = 0.5` -- the "no information" midpoint --
    while `analyses.admet.status` is honestly set to "skipped". The dict says
    skipped; the NUMBER does not, and the number is what enters the composite.
    135 of 507 historical candidates carry exactly 0.5 this way.

    This flags the pattern wherever it appears rather than any one constant:
    a component contributing to a score while its analysis reports it absent.
    """
    leaves = dict(_walk(output))
    findings = []
    for path, v in list(leaves.items()):
        if not path.endswith(".status") or not isinstance(v, str):
            continue
        if v.strip().lower() not in ("skipped", "unavailable", "error", "failed"):
            continue
        # `analyses.admet.status` -> the component is `admet`
        parts = path.split(".")
        if len(parts) < 2:
            continue
        component = parts[-2]
        for p2, v2 in leaves.items():
            if not p2.endswith("score_breakdown.%s.score" % component):
                continue
            if _num(v2) is None:
                continue
            findings.append(_finding(
                "score_without_its_analysis", "quarantine",
                "%s contributes %s to the composite while %s reports %r. A "
                "component that did not run must not carry a number that is "
                "indistinguishable from a measured one."
                % (p2, v2, path, v), field=p2))
    return findings


_INVARIANTS = (
    _inv_score_without_its_analysis,
    _inv_no_fabrication_markers,
    _inv_noael_below_loael,
    _inv_verdict_matches_hazards,
    _inv_units_declared,
    _inv_probability_in_range,
)


def check_invariants(output: Dict[str, Any],
                     candidate: Optional[Dict[str, Any]] = None,
                     prior: Optional[Dict[str, Any]] = None,
                     cohort: Optional[List[Dict[str, Any]]] = None) -> List[Finding]:
    """Every deterministic finding. No model is consulted here, ever."""
    findings: List[Finding] = []
    for inv in _INVARIANTS:
        try:
            findings.extend(inv(output or {}, candidate, prior) or [])
        except Exception as exc:                       # an invariant must not
            findings.append(_finding(                  # take the pipeline down
                inv.__name__, "flag",
                "invariant raised %s; treat as unchecked, not as passed." % exc))
    findings.extend(_inv_no_inherited_constant(
        output or {}, candidate, prior, cohort) or [])
    return findings


def _worst(findings: List[Finding]) -> str:
    return max((f["verdict"] for f in findings), key=lambda v: _ESCALATION[v],
               default="pass")


# ───────────────────────── the judgment, escalate-only ────────────────────

def _judge(stage: str, output: Dict[str, Any], current: str,
           timeout: float) -> Tuple[str, Optional[Finding]]:
    """Ask whether the stage's own narrative supports its own numbers.

    Text against text -- which is what TypeSafe is for. The answer may only
    raise the verdict. `current` is the floor, never the ceiling.
    """
    narrative = " ".join(
        str(v)[:400] for _, v in _walk(output)
        if isinstance(v, str) and len(str(v)) > 60)[:4000]
    if not narrative.strip():
        return current, None

    numbers = {p: v for p, v in _walk(output) if _num(v) is not None}
    questions = {
        "narrative_contradicts_numbers": {
            "type": "noul",
            "instructions": (
                "Does the written interpretation contradict, overstate, or omit "
                "a concern that the recorded numbers beside it establish? "
                "Answer about consistency between the two texts only. Do not "
                "assess whether any number is scientifically correct."
            ),
        },
    }
    state = {"stage": stage, "interpretation": narrative,
             "recorded_values": {k: v for k, v in list(numbers.items())[:40]}}
    try:
        res = TS.ask(state, questions, timeout=timeout)
    except TS.TypeSafeError as exc:
        return current, _finding(
            "narrative_contradicts_numbers", "flag",
            "Consistency judgment did not run (%s). Unchecked is not passed."
            % exc, decided_by="unavailable")

    p = TS.noul(res.get("answers") or {}, "narrative_contradicts_numbers")
    if p is None:
        return current, None
    if p >= 0.70:
        raised = "quarantine" if _ESCALATION[current] >= 1 else "flag"
        return raised, _finding(
            "narrative_contradicts_numbers", raised,
            "The written interpretation is judged inconsistent with the recorded "
            "values (p=%.2f). Escalated from %r." % (p, current),
            decided_by="judgment")
    return current, _finding(
        "narrative_contradicts_numbers", "pass",
        "Interpretation consistent with recorded values (p=%.2f)." % p,
        decided_by="judgment")


# ────────────────────────────── the boundary ──────────────────────────────

def mode() -> str:
    """off | shadow | enforce. Shadow records verdicts without withholding."""
    m = (os.environ.get("BIOQL_STAGE_AUDIT") or "shadow").strip().lower()
    return m if m in ("off", "shadow", "enforce") else "shadow"


def audit_stage(stage: str,
                output: Dict[str, Any],
                candidate: Optional[Dict[str, Any]] = None,
                prior: Optional[Dict[str, Any]] = None,
                *,
                cohort: Optional[List[Dict[str, Any]]] = None,
                consult_model: bool = True,
                timeout: float = 20.0) -> Dict[str, Any]:
    """Audit one stage's output at the boundary before the next stage sees it.

    Returns the verdict, every finding, and the fields withheld. The output
    itself is never modified: a caller withholds by consulting `withheld`.
    """
    if mode() == "off":
        return {"stage": stage, "verdict": "pass", "findings": [],
                "withheld": [], "mode": "off",
                "reason": "Stage audit disabled (BIOQL_STAGE_AUDIT=off)."}

    findings = check_invariants(output, candidate, prior, cohort)
    verdict = _worst(findings)

    if consult_model and TS.is_configured():
        verdict, jf = _judge(stage, output or {}, verdict, timeout)
        if jf is not None:
            findings.append(jf)

    withheld = sorted({f["field"] for f in findings
                       if f["verdict"] == "quarantine" and f.get("field")})

    return {
        "stage": stage,
        "verdict": verdict,
        "mode": mode(),
        "findings": findings,
        "withheld": withheld,
        "enforced": mode() == "enforce" and verdict == "quarantine",
        "note": (
            "Quarantined fields are withheld from downstream stages. They are "
            "not deleted, defaulted or recomputed; the absence carries its reason."
            if withheld else
            "No field was withheld."
        ),
    }


def apply_quarantine(output: Dict[str, Any], audit: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with quarantined fields absent, each replaced by its reason.

    Only acts in enforce mode. Absence is recorded under `_quarantined` so a
    downstream reader sees why a field is missing rather than inferring zero.
    """
    if not audit.get("enforced") or not audit.get("withheld"):
        return output
    import copy
    out = copy.deepcopy(output or {})
    reasons = {f["field"]: f["detail"] for f in audit["findings"]
               if f.get("field") and f["verdict"] == "quarantine"}
    for path in audit["withheld"]:
        parts = path.split(".")
        node = out
        for k in parts[:-1]:
            if not isinstance(node, dict) or k not in node:
                node = None
                break
            node = node[k]
        if isinstance(node, dict):
            node.pop(parts[-1], None)
    out["_quarantined"] = reasons
    return out
