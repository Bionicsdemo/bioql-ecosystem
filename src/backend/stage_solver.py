"""Decide what to run next as evidence accumulates — never what the answer is.

A pipeline today runs a fixed sequence of 51 possible stages. Several are
expensive: Protenix folding on GPU, MM-GBSA under OpenMM, Complexa binder
design, real QPU jobs. They run for every candidate whether or not the result
could still change anything, and that is where the compute budget goes.

This module puts a decision at each stage boundary: given everything known so
far about this candidate, is running the next expensive stage worth it?

WHAT IT DECIDES AND WHAT IT MUST NOT
    It chooses an ACTION: run, run a cheaper proxy, skip, or stop early.
    It never produces a scientific VALUE. When it skips a stage, the fields
    that stage would have filled stay ABSENT with a recorded reason. A skip
    must never become a guess -- that is the single property that makes an
    adaptive solver safe here, and `test_stage_solver.py` enforces it.

WHAT CODE OWNS, NOT THE MODEL
    Safety stages always run. Budget ceilings are arithmetic. Missing
    prerequisites are a fact, not a judgment. Those are decided before the
    model is consulted, and the model cannot override them. A judgment that
    could skip a toxicology stage would be a judgment that could hide a hazard.

Every decision records the state it saw, the action taken and the probability
behind it, so a run can be audited afterwards and the thresholds tuned against
real outcomes rather than guessed.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import typesafe_client as TS

# Stages that produce or gate safety information. Never skippable, at any
# budget, by any judgment.
SAFETY_STAGES = frozenset({
    "2_admet", "5_admet", "6_admet",
    "3_toxicology", "6_toxicology", "7_toxicology",
    "4_scoring", "8_scoring", "11_scoring",
    "5_clinical_trial", "8_clinical_trial", "9_clinical_trial",
})

# Stages worth deciding about: expensive, and their absence is survivable.
DISCRETIONARY_STAGES: Dict[str, Dict[str, Any]] = {
    "5b_protenix":          {"cost": "gpu",     "proxy": None},
    "5c_protenix":          {"cost": "gpu",     "proxy": None},
    "7b_protenix_structure": {"cost": "gpu",    "proxy": None},
    "5c_complexa":          {"cost": "gpu",     "proxy": None},
    "7c_complexa":          {"cost": "gpu",     "proxy": None},
    "5d_complexa":          {"cost": "gpu",     "proxy": None},
    "5c_ewf_sqd":           {"cost": "quantum", "proxy": "simulator"},
    "7c_quantum_chemistry": {"cost": "quantum", "proxy": "simulator"},
    "1_quantum_78_algorithms": {"cost": "quantum", "proxy": "simulator"},
    "3_quantum_optimization": {"cost": "quantum", "proxy": "simulator"},
    "7d_qaoa_weights":      {"cost": "quantum", "proxy": "simulator"},
    "9_docking":            {"cost": "cpu_heavy", "proxy": None},
    "6_docking":            {"cost": "cpu_heavy", "proxy": None},
    "3b_quillow_multipose": {"cost": "cpu_heavy", "proxy": None},
    "4b_qpharos_pareto":    {"cost": "cpu_heavy", "proxy": None},
}

ACTIONS = ("run", "run_proxy", "skip", "stop_pipeline")


class Decision(dict):
    """A recorded decision. Dict so it serialises into the pipeline result."""

    @property
    def action(self) -> str:
        return self["action"]

    @property
    def runs(self) -> bool:
        return self["action"] in ("run", "run_proxy")


def _decide(action: str, reason: str, *, forced: bool,
            stage: str, probability: Optional[float] = None,
            state: Optional[Dict[str, Any]] = None,
            extra: Optional[Dict[str, Any]] = None) -> Decision:
    d = Decision({
        "stage": stage,
        "action": action,
        "reason": reason,
        "decided_by": "rule" if forced else "judgment",
        "probability": probability,
        "state_seen": state,
    })
    if action in ("skip", "stop_pipeline"):
        d["fields_left_absent"] = (
            "This stage did not run, so the values it produces are absent. "
            "They are not zero, not defaults and not estimated."
        )
    if extra:
        d.update(extra)
    return d


def _observed(candidate: Dict[str, Any],
              stages_done: Dict[str, Any]) -> Dict[str, Any]:
    """Small, named evidence for the judgment. Not the whole record."""
    out: Dict[str, Any] = {}
    for f in ("name", "target", "composite_score", "drug_candidate_class",
              "sequence", "smiles", "mw", "rank"):
        v = candidate.get(f)
        if v not in (None, "", [], {}):
            out[f] = v
    gate = candidate.get("safety_gate")
    if isinstance(gate, dict):
        out["safety_gate"] = {"passed": gate.get("passed"),
                              "severity": gate.get("severity"),
                              "flags": (gate.get("flags") or [])[:4]}
    if isinstance(stages_done, dict):
        out["stages_already_run"] = sorted(stages_done.keys())[:30]
    return out


def decide_stage(stage: str,
                 candidate: Dict[str, Any],
                 stages_done: Optional[Dict[str, Any]] = None,
                 *,
                 goal: str = "identify candidates worth experimental follow-up",
                 budget_remaining: Optional[float] = None,
                 requires: Optional[List[str]] = None,
                 timeout: float = 20.0) -> Decision:
    """Decide whether to run `stage` for `candidate`.

    Deterministic rules resolve first and cannot be overridden. Only a genuinely
    discretionary call reaches the model, and if the model is unavailable the
    answer is to RUN: degrading into skipping work would silently shrink the
    analysis, and an absent judgment must never look like a decision to skip.
    """
    stages_done = stages_done or {}
    state = _observed(candidate, stages_done)

    # ── Rules. Code owns these. ──
    if stage in SAFETY_STAGES:
        return _decide("run", "Safety stage: always runs.", forced=True,
                       stage=stage, state=state)

    missing = [r for r in (requires or []) if r not in stages_done]
    if missing:
        return _decide("skip", "Prerequisite stage(s) did not run: %s."
                       % ", ".join(missing), forced=True, stage=stage, state=state)

    if stage not in DISCRETIONARY_STAGES:
        return _decide("run", "Not a discretionary stage.", forced=True,
                       stage=stage, state=state)

    spec = DISCRETIONARY_STAGES[stage]

    if budget_remaining is not None and budget_remaining <= 0:
        return _decide("skip", "Budget exhausted.", forced=True,
                       stage=stage, state=state)

    gate = candidate.get("safety_gate")
    if isinstance(gate, dict) and gate.get("passed") is False:
        # Already failed on safety: expensive structure work cannot revive it.
        # Recorded as a rule, not a judgment, so it is obvious why it stopped.
        return _decide("skip",
                       "Candidate already failed the safety gate (%s); expensive "
                       "%s work would not change its disposition."
                       % (gate.get("severity"), spec["cost"]),
                       forced=True, stage=stage, state=state)

    # ── Judgment. Only what is genuinely discretionary. ──
    questions = {
        "worth_the_compute": {
            "type": "noul",
            "instructions": (
                "Given `goal` and what `observed` already establishes about this "
                "candidate, would running `stage` change what happens to it?"
            ),
            "criteria": {
                "true": "The stage would produce evidence that could change whether "
                        "this candidate is advanced, dropped or ranked differently.",
                "false": "The outcome is already determined by what is known; the "
                         "stage would add detail without changing any decision.",
            },
        },
        "evidence_sufficient": {
            "type": "noul",
            "instructions": (
                "Is there already enough evidence in `observed` to decide this "
                "candidate's disposition without further computation?"
            ),
            "criteria": {
                "true": "The accumulated evidence settles the candidate's disposition.",
                "false": "A material question about this candidate is still open.",
            },
        },
    }
    if spec.get("proxy"):
        questions["proxy_suffices"] = {
            "type": "noul",
            "instructions": (
                "Would the cheaper `%s` variant of `stage` answer the open question "
                "as well as the full run, for this candidate?" % spec["proxy"]
            ),
            "criteria": {
                "true": "The cheaper variant would support the same decision.",
                "false": "Only the full run would settle it.",
            },
        }

    payload = {"goal": goal, "stage": stage,
               "stage_cost": spec["cost"], "observed": state}

    try:
        res = TS.ask(payload, questions, timeout=timeout)
    except TS.TypeSafeError as exc:
        # Unavailable judgment must not become a decision to skip.
        return _decide("run",
                       "Judgment unavailable (%s); running rather than silently "
                       "reducing the analysis." % exc,
                       forced=True, stage=stage, state=state)

    answers = res["answers"]
    worth = TS.noul(answers, "worth_the_compute")
    enough = TS.noul(answers, "evidence_sufficient")
    proxy_ok = TS.noul(answers, "proxy_suffices")

    extra = {"usage": res.get("usage"), "model": res.get("model"),
             "probabilities": {"worth_the_compute": worth,
                               "evidence_sufficient": enough,
                               "proxy_suffices": proxy_ok}}

    # Only a clear judgment skips work. Uncertainty runs the stage: the cost of
    # an unnecessary run is compute, the cost of a wrong skip is a blind spot.
    if worth is not None and worth < 0.25 and (enough is None or enough > 0.70):
        return _decide("skip",
                       "Outcome already determined by existing evidence "
                       "(worth=%.2f, sufficient=%s)." % (worth, enough),
                       forced=False, stage=stage, probability=worth,
                       state=state, extra=extra)

    if proxy_ok is not None and proxy_ok >= 0.75:
        return _decide("run_proxy",
                       "Cheaper %s variant judged sufficient (%.2f)."
                       % (spec["proxy"], proxy_ok),
                       forced=False, stage=stage, probability=proxy_ok,
                       state=state, extra=extra)

    return _decide("run",
                   "Stage could still change this candidate's disposition"
                   + ("" if worth is None else " (worth=%.2f)" % worth) + ".",
                   forced=False, stage=stage, probability=worth,
                   state=state, extra=extra)


MODE_ENV = "BIOQL_STAGE_SOLVER"


def mode() -> str:
    """off (default) | shadow | enforce.

    Default off: turning this on costs tokens and changes what runs, and a
    cost-constrained project should opt in deliberately. `shadow` is the way
    to find out whether it does a good job -- it decides and records against
    real runs while changing nothing.
    """
    import os
    v = (os.environ.get(MODE_ENV) or "off").strip().lower()
    return v if v in ("off", "shadow", "enforce") else "off"


def gate(stage: str,
         candidate: Dict[str, Any],
         result: Dict[str, Any],
         **kw) -> bool:
    """Call from a pipeline before an expensive stage. Returns whether to run.

    The decision is appended to `result["stage_solver"]["decisions"]` so it
    lands in the stored pipeline JSON and can be reviewed afterwards against
    what the stage would have produced.

    In `shadow` mode the answer is always True: the decision is recorded but
    not applied. That is the review mechanism -- real decisions on real runs
    with nothing at risk.
    """
    m = mode()
    if m == "off":
        return True

    try:
        stages_done = (result or {}).get("stages") or {}
        d = decide_stage(stage, candidate or {}, stages_done, **kw)
    except Exception as exc:  # a broken solver must not break a pipeline
        d = _decide("run", "Solver error (%s); running." % exc,
                    forced=True, stage=stage)

    d["mode"] = m
    d["enforced"] = (m == "enforce")

    if isinstance(result, dict):
        blk = result.setdefault("stage_solver", {})
        blk.setdefault("mode", m)
        blk.setdefault("decisions", []).append(dict(d))

    if m == "shadow":
        # Recorded, deliberately not applied.
        d["would_have"] = d["action"]
        return True

    if not d.runs and isinstance(result, dict):
        # An enforced skip leaves an explicit, honest stage entry. A stage that
        # simply vanished would be indistinguishable from one that failed.
        result.setdefault("stages", {})[stage] = {
            "stage": stage,
            "status": "skipped_by_solver",
            "reason": d["reason"],
            "decided_by": d["decided_by"],
            "fields_left_absent": d.get("fields_left_absent"),
        }
    return d.runs


def summarize(decisions: List[Decision]) -> Dict[str, Any]:
    """What the solver did over a run, for the record and for tuning."""
    by_action: Dict[str, int] = {}
    skipped: List[str] = []
    tokens = 0
    for d in decisions:
        by_action[d["action"]] = by_action.get(d["action"], 0) + 1
        if d["action"] in ("skip", "stop_pipeline"):
            skipped.append(d["stage"])
        u = d.get("usage") or {}
        tokens += int(u.get("input_tokens") or 0) + int(u.get("output_tokens") or 0)
    return {
        "decisions": len(decisions),
        "by_action": by_action,
        "stages_skipped": skipped,
        "judgment_tokens_spent": tokens,
        "note": ("Skipped stages left their fields absent, with the reason recorded "
                 "on each decision. No value was estimated in their place."),
    }
