"""Check an Auto-Insight against the pipeline data it claims to describe.

The Auto-Insight panel renders free-form LLM markdown straight into the page.
On 2026-09-15 one of those insights was audited by hand against the pipeline
JSON and made quantitative claims the data did not support. Nothing in the
product checked; a reader had no way to tell a grounded sentence from a
confident one.

This module closes that gap with TypeSafe: the insight text and the pipeline
state go in, typed judgments come out. It judges the TEXT -- whether a sentence
is supported by the evidence given -- and never judges the molecule. No answer
here may become, replace or override a scientific value; see
`typesafe_client.FORBIDDEN_TARGETS`.

When the credential is missing or the service fails, the verdict is
"not verified". That is not the same as verified, and callers must render the
difference.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import typesafe_client as TS

# The state handed to the model is built from a small allowlist. Sending the
# whole candidate would bury the evidence and leak unrelated fields.
_STATE_FIELDS = (
    "name", "target", "pipeline", "sequence", "smiles", "formula", "mw",
    "composite_score", "drug_candidate_class", "binding_affinity",
    "safety_gate", "score_breakdown", "unit_corrections_applied",
)


def _compact_run(result: Dict[str, Any]) -> Dict[str, Any]:
    """Evidence for an insight about a whole pipeline run.

    An Auto-Insight fires on a finished pipeline, so its claims are about the
    run: which target, how many candidates, what they scored. Handing it a
    single candidate would judge the text against the wrong evidence, and the
    top-ranked candidate in particular is how this codebase has repeatedly
    leaked one molecule's data onto another.
    """
    inner = result.get("result") if isinstance(result.get("result"), dict) else result
    cands = None
    for key in ("candidates", "all_candidates", "drug_candidates"):
        v = inner.get(key)
        if isinstance(v, list) and v:
            cands = v
            break
    if cands is None:
        return {}

    out: Dict[str, Any] = {
        "target": inner.get("target") or inner.get("target_name"),
        "pipeline": inner.get("pipeline") or inner.get("pipeline_name"),
        "candidate_count": len(cands),
    }
    rows = []
    for c in cands[:25]:
        if not isinstance(c, dict):
            continue
        row = {k: c.get(k) for k in
               ("name", "composite_score", "drug_candidate_class", "sequence")
               if c.get(k) not in (None, "")}
        gate = c.get("safety_gate")
        if isinstance(gate, dict):
            row["safety_gate"] = {"passed": gate.get("passed"),
                                  "severity": gate.get("severity")}
        if row:
            rows.append(row)
    out["candidates"] = rows
    return {k: v for k, v in out.items() if v not in (None, "", [], {})}


def _compact_state(candidate: Dict[str, Any]) -> Dict[str, Any]:
    # A pipeline envelope and a single candidate are both valid evidence; the
    # caller knows which one the insight is about.
    run = _compact_run(candidate or {})
    if run:
        return run
    out: Dict[str, Any] = {}
    for f in _STATE_FIELDS:
        v = candidate.get(f)
        if v in (None, "", [], {}):
            continue
        out[f] = v
    tox = candidate.get("toxicology")
    if isinstance(tox, dict):
        acute = tox.get("acute_toxicity") if isinstance(tox.get("acute_toxicity"), dict) else {}
        out["toxicology"] = {
            "ghs_class": acute.get("ghs_class"),
            "ld50_mg_kg": acute.get("ld50_mg_kg"),
            "nephrotoxicity_risk": tox.get("nephrotoxicity_risk"),
            "hepatotoxicity_risk": tox.get("hepatotoxicity_risk"),
            "cardiotoxicity_risk": tox.get("cardiotoxicity_risk"),
            "backend": tox.get("backend"),
        }
    clin = candidate.get("clinical_trial")
    if isinstance(clin, dict):
        out["clinical_trial"] = {
            "approval_class": clin.get("approval_class"),
            "disqualification_reason": clin.get("disqualification_reason"),
            "disqualification_withdrawn": clin.get("disqualification_withdrawn"),
        }
    return out


QUESTIONS: Dict[str, Dict[str, Any]] = {
    # Every id below names a property of the TEXT, never a measured endpoint.
    "claims_grounded": {
        "type": "noul",
        "instructions": (
            "Every quantitative claim in `insight` must be traceable to a value "
            "present in `evidence`. Is that true of this insight?"
        ),
        "criteria": {
            "true": "Each number, class and verdict stated in the insight appears "
                    "in the evidence, or the insight says it is unknown.",
            "false": "The insight states at least one number, class or verdict that "
                     "the evidence does not contain.",
        },
    },
    "overstates_certainty": {
        "type": "noul",
        "instructions": (
            "Does `insight` present an estimate, a proxy or an unassessed field as "
            "if it were a measurement?"
        ),
        "criteria": {
            "true": "It asserts as measured something the evidence marks as an "
                    "estimate, a placeholder, withdrawn, or not assessed.",
            "false": "It reports estimates as estimates and gaps as gaps.",
        },
    },
    "contradicts_evidence": {
        "type": "noul",
        "instructions": (
            "Does `insight` state anything that directly conflicts with `evidence`?"
        ),
        "criteria": {
            "true": "A statement in the insight is incompatible with a value in the evidence.",
            "false": "Nothing in the insight conflicts with the evidence.",
        },
    },
    "actionability": {
        "type": "score",
        "instructions": (
            "How actionable is this insight for a medicinal chemist deciding what "
            "to do next with this candidate?"
        ),
        "criteria": [
            "Generic commentary that would apply to any molecule",
            "Specific to this candidate but proposes no next step",
            "Names a concrete, checkable next step for this candidate",
        ],
    },
}

# Above this probability the claim is treated as established for display.
_HIGH = 0.70


def verify_insight(insight_text: str,
                   candidate: Dict[str, Any],
                   timeout: float = 30.0) -> Dict[str, Any]:
    """Judge an insight against its candidate. Never raises for service failure.

    Returns a dict with `verified` (bool|None), per-question probabilities, and
    a `status` that distinguishes "checked and clean" from "not checked".
    """
    text = (insight_text or "").strip()
    if not text:
        return {"status": "skipped", "verified": None,
                "reason": "empty insight text"}

    state = {"insight": text, "evidence": _compact_state(candidate or {})}

    try:
        result = TS.ask(state, QUESTIONS, timeout=timeout)
    except TS.TypeSafeNotConfigured as exc:
        return {"status": "not_configured", "verified": None, "reason": str(exc)}
    except TS.TypeSafeError as exc:
        return {"status": "unavailable", "verified": None, "reason": str(exc)}

    answers = result["answers"]
    grounded = TS.noul(answers, "claims_grounded")
    overstates = TS.noul(answers, "overstates_certainty")
    contradicts = TS.noul(answers, "contradicts_evidence")
    action = TS.score(answers, "actionability")

    problems: List[str] = []
    if grounded is not None and grounded < _HIGH:
        problems.append("contains claims not traceable to the pipeline data")
    if overstates is not None and overstates >= _HIGH:
        problems.append("presents an estimate or an unassessed field as measured")
    if contradicts is not None and contradicts >= _HIGH:
        problems.append("states something that conflicts with the pipeline data")

    verified: Optional[bool] = None
    if grounded is not None or overstates is not None or contradicts is not None:
        verified = not problems

    return {
        "status": "checked",
        "verified": verified,
        "problems": problems,
        "probabilities": {
            "claims_grounded": grounded,
            "overstates_certainty": overstates,
            "contradicts_evidence": contradicts,
        },
        "actionability": action,
        "model": result.get("model"),
        "usage": result.get("usage"),
        # Stated on every response so a reader never mistakes this for a
        # judgement about the molecule.
        "scope": ("Judges the insight TEXT against the pipeline data. It does not "
                  "evaluate the molecule and cannot change any scientific value."),
    }
