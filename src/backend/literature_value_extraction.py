"""Read a measured value out of text. Select it; never generate it.

THE PATTERN, AND WHY IT IS THE ONLY SAFE ONE HERE
    Code finds every candidate value with a regex tuned to OVER-find. The model
    chooses which candidate answers the question. Code copies the chosen span
    verbatim. The model never emits a number.

    TypeSafe's own documentation puts the guarantee plainly: the model "only
    ever chooses among the spans the regex found... It cannot invent a value or
    transpose a digit." That is the difference between reading a measurement
    and producing one, and it is the line this codebase spent two days
    enforcing everywhere else.

WHAT THIS UNBLOCKS
    `efficacious_dose` refuses most candidates for want of a potency: the
    platform has no IC50/EC50/Ki source, and the only affinity it holds is an
    MM-GBSA dG that must not be converted into one. A potency stated in a paper
    is a real measurement made by someone else; lifting it verbatim, with its
    source span recorded, is legitimate in a way that estimating it never is.

THE INVARIANT, ENFORCED AND TESTED
    Every returned value is character-for-character one of the candidate spans
    the regex produced. `select_value` raises if the model returns anything
    else. A value that is not in the text cannot come out of this module.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import typesafe_client as TS

# Units we accept for a potency, with the multiplier to nM. A value whose unit
# we cannot resolve is reported, not guessed at.
_TO_NM = {
    "pm": 0.001, "pM": 0.001,
    "nm": 1.0, "nM": 1.0,
    "um": 1000.0, "uM": 1000.0, "μM": 1000.0, "µM": 1000.0,
    "mm": 1e6, "mM": 1e6,
    "m": 1e9, "M": 1e9,
}

# Deliberately greedy: a missed candidate cannot be selected, while a spurious
# one only costs the model a rejection.
_POTENCY_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>pM|nM|µM|μM|uM|mM|M)\b",
    re.IGNORECASE,
)


def find_candidates(text: str, pattern: re.Pattern = _POTENCY_RE,
                    window: int = 90) -> List[Dict[str, Any]]:
    """Every candidate span, with the text around it so the model can judge.

    Over-finding is intentional. The model can reject a candidate; it cannot
    select one the regex never produced.
    """
    out: List[Dict[str, Any]] = []
    for m in pattern.finditer(text or ""):
        lo = max(0, m.start() - window)
        hi = min(len(text), m.end() + window)
        out.append({
            "span": m.group(0),
            "value": m.group("value"),
            "unit": m.group("unit"),
            "start": m.start(),
            "end": m.end(),
            "context": text[lo:hi].replace("\n", " "),
        })
    return out


def to_nanomolar(value: str, unit: str) -> Optional[float]:
    """Convert a selected span to nM. Returns None rather than guess a unit."""
    mult = _TO_NM.get(unit) or _TO_NM.get(unit.lower()) or _TO_NM.get(unit.upper())
    if mult is None:
        return None
    try:
        return float(str(value).replace(",", ".")) * mult
    except (TypeError, ValueError):
        return None


class NotInText(TS.TypeSafeError):
    """The model returned something the regex never found. Refused."""


def select_value(text: str,
                 target: str,
                 *,
                 measure: str = "IC50",
                 candidates: Optional[List[Dict[str, Any]]] = None,
                 timeout: float = 30.0) -> Dict[str, Any]:
    """Pick which candidate is `measure` against `target`, or say none is.

    Returns the selected span verbatim with its offsets, so the claim can be
    checked against the source. Never returns a value absent from `candidates`.
    """
    cands = candidates if candidates is not None else find_candidates(text)
    if not cands:
        return {"available": False, "value_nm": None,
                "reason": "No numeric value with a concentration unit was found "
                          "in the text. Nothing to select from."}

    # Labelled options, plus an explicit no-match. Without a no-match the model
    # is forced to pick something even when the paper states no such value.
    options = {str(i): "%s  (context: ...%s...)" % (c["span"], c["context"])
               for i, c in enumerate(cands)}
    options["none"] = "No candidate is the %s against %s." % (measure, target)

    questions = {
        "which_value": {
            "type": "choice",
            "instructions": (
                "Which candidate is the %s of the compound against %s, as stated "
                "in this text? Choose 'none' if the text states no such value."
                % (measure, target)
            ),
            "criteria": options,
        },
    }
    state = {"target": target, "measure": measure, "text": text[:6000]}

    try:
        res = TS.ask(state, questions, timeout=timeout)
    except TS.TypeSafeNotConfigured as exc:
        return {"available": False, "value_nm": None,
                "reason": "TypeSafe not configured (%s)." % exc}
    except TS.TypeSafeError as exc:
        return {"available": False, "value_nm": None,
                "reason": "Selection unavailable (%s)." % exc}

    ans = (res.get("answers") or {}).get("which_value") or {}
    choice = str(ans.get("choice", ans.get("value", ""))).strip()
    confidence = ans.get("confidence")

    if choice == "none" or choice == "":
        return {"available": False, "value_nm": None, "confidence": confidence,
                "reason": "The model found no candidate that is the %s against %s."
                          % (measure, target)}

    if choice not in options:
        # The guarantee is enforced here, not assumed.
        raise NotInText(
            "model returned %r, which is not one of the %d candidate spans the "
            "regex produced. Refusing: a value that is not in the text cannot "
            "come out of this module." % (choice, len(cands)))

    c = cands[int(choice)]
    nm = to_nanomolar(c["value"], c["unit"])
    if nm is None:
        return {"available": False, "value_nm": None,
                "selected_span": c["span"],
                "reason": "Unit %r could not be resolved to nM." % c["unit"]}

    return {
        "available": True,
        "value_nm": nm,
        "measure": measure,
        "target": target,
        "selected_span": c["span"],          # verbatim, as it appears
        "source_offsets": [c["start"], c["end"]],
        "source_context": c["context"],
        "confidence": confidence,
        "n_candidates": len(cands),
        "method": "regex over-find + model selection + verbatim copy",
        "provenance": (
            "This value was READ from supplied text, not computed or estimated. "
            "It is one of the spans the regex found, copied unchanged, and the "
            "offsets locate it in the source."
        ),
    }


def potency_for_candidate(candidate: Dict[str, Any], text: str,
                          measure: str = "IC50") -> Dict[str, Any]:
    """Extract a potency for a candidate from a paper or assay record."""
    target = str((candidate or {}).get("target") or "").strip()
    if not target:
        return {"available": False, "value_nm": None,
                "reason": "Candidate has no target; a potency is meaningless "
                          "without saying what it is against."}
    return select_value(text, target, measure=measure)
