"""
Putting every sentence of a report to Jev, against only the values it quotes.

The template machinery already guarantees the NUMBERS are real: a sentence cannot
name a value the run does not carry, because there is nowhere for that value to come
from. It does not guarantee the SENTENCE is supported -- a template can word a
relationship the data never establishes ("X therefore Y" when the run only records X),
name a method that is nowhere in the run, or turn a prediction into a measurement.

So each sentence goes to Jev with the values it cites and nothing else. Judging
against only the quoted values is the whole point: a sentence that needs outside
knowledge to be true is a sentence the report should not be making. Four independent
judgements, asked so they cannot all fail the same way:

    supported     can the sentence be read straight off the evidence?
    contradicted  does it CONFLICT with the evidence -- both cannot be true?
    overclaims    does it assert more than the evidence carries?
    invented      does it name a figure, unit or entity the evidence does not have?

A sentence passes when it is supported and trips none of the three faults. The
verdict vocabulary is kept honest in both directions: only a real conflict is
reported as `contradicts`. A sentence that merely says more than its values carry is
`says_nothing` -- the data is silent about the surplus, not opposed to it. Calling
that a contradiction would be the verifier committing the very sin it looks for.

A sentence that quotes nothing and rests on no recomputed arithmetic -- the page's own
meta-notes -- is not judged at all. There is no evidence to judge it against, so any
verdict would be noise, and a false "unsupported" would delete the report's own
honesty statement under BIOQL_REPORT_VERIFY=strict. Those are counted and named,
never scored.

Never raises, and degrades honestly: with no credential, `{"available": False}` and a
reason. A report must build whether or not the verifier can run.

Wordings and thresholds here are not guesses. They were fitted on 15 hand-labelled
sentences from a real mrna_therapeutic_v1 run (ps-ee68d5c59415). The wording below
agrees with 13 to 14 of the 15 on repeat runs, against 9/15 for the first draft. One
disagreement is stable -- a sentence that mixes a count derived from a subtree with a
claim about the page's own animation, which is arguable in both directions -- and the
rest sits on a threshold and is reported `borderline`.

MOLEVERA / BIOQL
"""

import concurrent.futures
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from . import facts as F

SUPPORTED, CONTRADICTED, OVERCLAIM, INVENTED = (
    "supported",
    "contradicted",
    "overclaims",
    "invented",
)

PASS_SUPPORT = 0.70  # below this the evidence does not establish the sentence
FAIL_FAULT = 0.50  # at or above this the sentence conflicts, overclaims or invents

# How close to a threshold a probability may sit before the verdict is really a coin
# toss. Measured, not chosen. Judging the same sentences three times over, Jev moves by
# 0.025 on average and never by more than 0.20; of 41 mRNA sentences one verdict
# changed between runs, and of 74 modality_comparison sentences four did. Every one of
# those five sat inside this band, and nothing outside it moved. So a verdict this
# close to its threshold is reported `borderline`: it is a real reading of the data,
# but a second run may return the other one.
MARGIN = 0.06

# Caps on a single quoted value. A path may point at a whole subtree or a 19 kB PDB;
# the sentence is still judged against what it quotes, just not against all of it.
MAX_STR = 800
MAX_ITEMS = 40
MAX_DEPTH = 6

# Named so every question refers to the same thing. The evidence is the values the
# sentence quotes, plus -- only for a sentence gated on a passing check -- that check's
# own recomputed statement. A sentence such as "checked here, the parts add up" is
# supported by the arithmetic this report redid, not by the raw values, and the first
# draft of this module mentioned that field to the `supported` question alone: the
# other three then read the recomputed evidence as absent and scored those sentences
# as inventions. Hence one preamble, shared verbatim.
#
# Saying that the check PASSED is not decoration. Described merely as "arithmetic this
# report redid", the same 13 check-gated sentences across four pipelines scored 6/13;
# named as a verification that passed, and reported in any wording, 10/13 -- support
# rose on all 13. A judge told only that a calculation exists cannot tell whether the
# sentence reporting its outcome is right.
EVIDENCE = (
    "`values` holds every value of the run that the sentence cites, keyed by its path "
    "in the run's result. `verified_by_this_report` is a check this report recomputed "
    "from the run's own data and which PASSED; a sentence reporting that check is "
    "established by it, in any wording. Whichever of the two are present are the "
    "evidence, and there is no other: treat anything not in the evidence as unknown "
    "about this run, however plausible it may be.\n\n"
)

QUESTIONS: Dict[str, Dict[str, Any]] = {
    SUPPORTED: {
        "type": "noul",
        "instructions": EVIDENCE
        + (
            "Can the sentence be read straight off the evidence? Yes when every "
            "run-specific figure, name, unit and relationship it states is there, "
            "whether quoted verbatim, reworded, or obtained by counting or simple "
            "arithmetic on it. A sentence that restates or reformats the evidence, "
            "adds a label, or frames it for a reader is a Yes.\n\n"
            "No only when the sentence makes a run-specific claim the evidence cannot "
            "supply. Common-knowledge biology that asserts nothing new about this run, "
            "and description of the page's own graphics, are not run-specific claims "
            "— ignore them when deciding."
        ),
    },
    CONTRADICTED: {
        "type": "noul",
        "instructions": EVIDENCE
        + (
            "Does the sentence CONFLICT with the evidence — a number, unit, name, "
            "direction or outcome that disagrees with what the evidence says, "
            "arithmetic that does not come out, or a pass where the evidence records a "
            "failure?\n\n"
            "This is narrower than being unsupported. Yes only when the evidence and "
            "the sentence cannot both be true. No when the sentence merely says more "
            "than the evidence covers, or speaks about something the evidence does not "
            "address."
        ),
    },
    OVERCLAIM: {
        "type": "noul",
        "instructions": EVIDENCE
        + (
            "Does the sentence claim MORE about this run than the evidence carries: an "
            "effect where the evidence has only a number, a cause where it has a "
            "correlation, a measurement where it has an estimate, a validation where it "
            "has a prediction, or certainty where it records a status, a caveat or a "
            "null?\n\n"
            "Yes when the sentence is stronger than the evidence behind it. No when it "
            "states exactly what the evidence says — including when it plainly reports "
            "an absence, a failure or a caveat, when it restates the evidence in other "
            "words or under a label, and when the stronger-sounding part is "
            "common-knowledge biology asserting nothing new about this run, or a "
            "description of the page's own graphics."
        ),
    },
    INVENTED: {
        "type": "noul",
        "instructions": EVIDENCE
        + (
            "Does the sentence attribute to THIS RUN any figure, unit, identifier, "
            "method, model, protein, gene, sequence or backend that is absent from the "
            "evidence?\n\n"
            "Yes when a run-specific claim names something with no counterpart in the "
            "evidence. No when everything it attributes to this run is there, including "
            "values reworded, reformatted, counted or arithmetically derived from it. "
            "Ordinary connecting language, common-knowledge biology that is not a "
            "result of this run, and description of the page's own graphics are not "
            "inventions."
        ),
    },
}


def configured() -> bool:
    """True when a TypeSafe credential is reachable. Never reads or prints the key."""
    try:
        import typesafe_client

        return bool(typesafe_client.is_configured())
    except Exception:  # noqa: BLE001
        return False


def _clip(v: Any, depth: int = 0) -> Any:
    """A value small enough to send, with its shape intact and its truncation declared.

    Structure matters here: the first draft flattened every container through `str()`,
    so a sentence that counts a subtree was judged against a Python repr. Dicts stay
    dicts. What is cut says so, rather than silently looking complete.
    """
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return v if len(v) <= MAX_STR else v[:MAX_STR] + f" …(+{len(v) - MAX_STR} characters)"
    if depth >= MAX_DEPTH:
        return str(v)[:MAX_STR]
    if isinstance(v, dict):
        out = {str(k): _clip(x, depth + 1) for i, (k, x) in enumerate(v.items()) if i < MAX_ITEMS}
        if len(v) > MAX_ITEMS:
            out["…"] = f"+{len(v) - MAX_ITEMS} more keys"
        return out
    if isinstance(v, (list, tuple)):
        items = [_clip(x, depth + 1) for x in list(v)[:MAX_ITEMS]]
        if len(v) > MAX_ITEMS:
            items.append(f"…(+{len(v) - MAX_ITEMS} more items)")
        return items
    return str(v)[:MAX_STR]


def _evidence(
    beat: Dict[str, Any], result: Any, checks: Optional[Dict[str, str]] = None
) -> Tuple[Dict[str, Any], Optional[str]]:
    """The values the sentence quotes, and the recomputed arithmetic behind it."""
    values: Dict[str, Any] = {}
    for p in beat.get("paths") or []:
        try:
            values[str(p)] = _clip(F.get(result, str(p)))
        except Exception:  # noqa: BLE001 -- one odd path may not lose the sentence
            continue
    ev = (checks or {}).get(beat.get("_check") or "")
    return values, (ev or None)


def _state(sentence: str, values: Dict[str, Any], recomputed: Optional[str]) -> Dict[str, Any]:
    """Exactly what Jev sees. Whatever is not here counts as unknown about this run.

    The beat's `kind` is deliberately absent: telling the judge a line is a "note"
    invites it to grade the label rather than the sentence, and measurably did.

    An empty `values` is omitted rather than sent as `{}`. A sentence resting entirely
    on a recomputed check quotes no paths, and an empty dict beside it reads as
    evidence of absence: sending it cost about 0.10 of support on every such sentence.
    """
    state: Dict[str, Any] = {"sentence": sentence}
    if values:
        state["values"] = values
    if recomputed:
        state["verified_by_this_report"] = recomputed
    return state


def _judge(client, sentence: str, state: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    ans = client.ask(state, QUESTIONS, timeout=timeout)["answers"]
    p = {q: client.noul(ans, q) for q in QUESTIONS}
    p_sup = p[SUPPORTED]
    if p_sup is None:
        return {
            "relation": "says_nothing",
            "confidence": 0.0,
            "ok": False,
            "note": "Jev returned no judgement",
        }
    p_con, p_over, p_inv = (p[CONTRADICTED] or 0.0), (p[OVERCLAIM] or 0.0), (p[INVENTED] or 0.0)

    if p_con >= FAIL_FAULT:
        # The one verdict that means the run and the sentence cannot both be right.
        rel, conf, driver = "contradicts", p_con, p_con - FAIL_FAULT
        note = f"conflicts with the values it quotes (p={p_con:.2f})"
    elif p_inv >= FAIL_FAULT:
        rel, conf, driver = "says_nothing", p_inv, p_inv - FAIL_FAULT
        note = f"names something the quoted values do not carry (p={p_inv:.2f})"
    elif p_over >= FAIL_FAULT:
        rel, conf, driver = "says_nothing", p_over, p_over - FAIL_FAULT
        note = f"claims more than the quoted values carry (p={p_over:.2f})"
    elif p_sup < PASS_SUPPORT:
        rel, conf, driver = "says_nothing", 1.0 - p_sup, PASS_SUPPORT - p_sup
        note = f"the quoted values do not establish it (support p={p_sup:.2f})"
    else:
        # Clears every threshold; how comfortably is the smallest of the four margins.
        driver = min(
            p_sup - PASS_SUPPORT, FAIL_FAULT - p_con, FAIL_FAULT - p_over, FAIL_FAULT - p_inv
        )
        rel, conf, note = "supports", p_sup, ""

    borderline = driver < MARGIN
    if borderline:
        note = (note or "supported, but only just") + " — borderline, a second run may differ"

    return {
        "relation": rel,
        "confidence": round(float(conf), 3),
        "ok": rel == "supports",
        "note": note,
        "borderline": borderline,
        "p_support": round(float(p_sup), 3),
        "p_contradicted": None if p[CONTRADICTED] is None else round(float(p_con), 3),
        "p_overclaim": None if p[OVERCLAIM] is None else round(float(p_over), 3),
        "p_invented": None if p[INVENTED] is None else round(float(p_inv), 3),
    }


def _unavailable(why: str, t0: float) -> Dict[str, Any]:
    return {
        "available": False,
        "why": why,
        "checked": 0,
        "verdicts": [],
        "n_ok": 0,
        "n_unsupported": 0,
        "elapsed_s": round(time.time() - t0, 1),
    }


def verify(
    beats: List[Dict[str, Any]],
    result: Any,
    *,
    timeout: float = 60.0,
    workers: int = 4,
    limit: Optional[int] = None,
    checks: Optional[List[Dict[str, Any]]] = None,
    tech: bool = True,
) -> Dict[str, Any]:
    """Every sentence judged against the values it quotes. Never raises.

    `beats` are rendered beats -- {"es","en","kind","paths",...}. `checks` are the
    model's recomputed checks, so a sentence gated on one is judged against that
    arithmetic as well. `tech` also judges each provenance line, reported apart from
    the sentences so an unsupported method line never removes the fact above it.

    A beat that quotes nothing and rests on no check is listed in `unjudgeable` and
    left out of `verdicts` entirely: it is not evidence against the page that a
    sentence with no numbers could not be scored against numbers.
    """
    t0 = time.time()
    try:
        import typesafe_client as client
    except Exception as e:  # noqa: BLE001
        return _unavailable(f"typesafe_client not importable: {type(e).__name__}: {e}", t0)
    try:
        if not client.is_configured():
            return _unavailable(
                "no TypeSafe credential (set TYPESAFE_API_KEY or ~/.bioql/typesafe_tokens.json)",
                t0,
            )
    except Exception as e:  # noqa: BLE001
        return _unavailable(f"credential unreadable: {type(e).__name__}: {e}", t0)

    try:
        ev: Dict[str, str] = {}
        for c in checks or []:
            if isinstance(c, dict) and c.get("ok") and c.get("id"):
                ev[str(c["id"])] = str(c.get("en") or c.get("es") or "")

        jobs: List[Tuple[int, str, str, Dict[str, Any]]] = []  # (i, line, sentence, state)
        unjudgeable: List[Dict[str, Any]] = []
        for i, b in enumerate(beats or []):
            if not isinstance(b, dict):
                continue
            sentence = b.get("en") or b.get("es")
            if not sentence:
                continue
            values, recomputed = _evidence(b, result, ev)
            if not values and not recomputed:
                unjudgeable.append(
                    {
                        "i": i,
                        "kind": b.get("kind", "fact"),
                        "sentence": str(sentence)[:220],
                        "why": "quotes no value and rests on no recomputed check",
                    }
                )
                continue
            jobs.append((i, "sentence", str(sentence), _state(str(sentence), values, recomputed)))
            t = b.get("tech") if tech else None
            if isinstance(t, dict) and (t.get("en") or t.get("es")):
                line = str(t.get("en") or t.get("es"))
                jobs.append((i, "tech", line, _state(line, values, recomputed)))

        if limit:
            keep = {i for i, _, _, _ in jobs}
            keep = set(sorted(keep)[:limit])
            jobs = [j for j in jobs if j[0] in keep]

        verdicts: List[Dict[str, Any]] = []
        tech_verdicts: List[Dict[str, Any]] = []
        failures = 0
        if jobs:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
                futures = {
                    pool.submit(_judge, client, s, st, timeout): (i, line, s)
                    for i, line, s, st in jobs
                }
                for fut in concurrent.futures.as_completed(futures):
                    i, line, s = futures[fut]
                    try:
                        v = fut.result()
                    except Exception as e:  # noqa: BLE001 -- one refusal may not lose the rest
                        failures += 1
                        v = {
                            "relation": "says_nothing",
                            "confidence": 0.0,
                            "ok": False,
                            "note": f"not judged: {type(e).__name__}: {str(e)[:120]}",
                        }
                    v["i"] = i
                    v["sentence"] = s[:220]
                    (verdicts if line == "sentence" else tech_verdicts).append(v)

        verdicts.sort(key=lambda v: v["i"])
        tech_verdicts.sort(key=lambda v: v["i"])
        n_ok = sum(1 for v in verdicts if v["ok"])
        out: Dict[str, Any] = {
            "available": True,
            "why": None,
            "checked": len(verdicts),
            "verdicts": verdicts,
            "n_ok": n_ok,
            "n_unsupported": len(verdicts) - n_ok,
            "n_contradicted": sum(1 for v in verdicts if v["relation"] == "contradicts"),
            "n_borderline": sum(1 for v in verdicts if v.get("borderline")),
            "n_errors": failures,
            "tech_verdicts": tech_verdicts,
            "n_tech_unsupported": sum(1 for v in tech_verdicts if not v["ok"]),
            "unjudgeable": unjudgeable,
            "n_unjudgeable": len(unjudgeable),
            "elapsed_s": round(time.time() - t0, 1),
            "thresholds": {"support": PASS_SUPPORT, "fault": FAIL_FAULT},
        }
        if failures and failures == len(verdicts) + len(tech_verdicts):
            out.update(available=False, why="every request to Jev failed")
        return out
    except Exception as e:  # noqa: BLE001 -- a verifier may never cost the report
        return _unavailable(f"verification failed: {type(e).__name__}: {str(e)[:200]}", t0)


def summarize(v: Optional[Dict[str, Any]]) -> str:
    """One line for a log. Like `verify`, it never raises -- a log line may not
    bring down the build that was only trying to record what happened."""
    if not v:
        return "verification: not run"
    if not isinstance(v, dict):
        return f"verification: unreadable result ({type(v).__name__})"
    if not v.get("available"):
        return f"verification: unavailable ({v.get('why')})"
    s = (
        f"verification: {v.get('n_ok', 0)}/{v.get('checked', 0)} sentences supported by the "
        f"values they quote"
    )
    if v.get("n_contradicted"):
        s += f", {v['n_contradicted']} contradicted"
    if v.get("n_borderline"):
        s += f", {v['n_borderline']} borderline"
    if v.get("n_tech_unsupported"):
        s += f", {v['n_tech_unsupported']} technical lines unsupported"
    if v.get("n_unjudgeable"):
        s += f", {v['n_unjudgeable']} quote nothing to judge"
    if v.get("n_errors"):
        s += f", {v['n_errors']} not judged"
    return s + f", {v.get('elapsed_s', 0)} s"


if __name__ == "__main__":
    # Run it as a module -- this file imports its siblings relatively, so
    # `python verify.py` cannot work:
    #   cd src/backend && ~/.bioql/venv/bin/python -m artifact_engine.verify [result.json]
    #   BIOQL_VERIFY_LIMIT=5 ... to judge only the first few sentences.
    import json
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from artifact_engine import build  # noqa: E402

    src = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.expanduser("~/.bioql/artifacts/ps-ee68d5c59415/result.json")
    )
    p = build.build(json.load(open(src)), mesh_fn=None)
    beats = [b for ch in p["chapters"] for b in ch["beats"]]
    v = verify(
        beats,
        p["result"],
        checks=p.get("checks"),
        limit=int(os.environ.get("BIOQL_VERIFY_LIMIT", "0")) or None,
    )
    print(summarize(v))
    for x in v.get("verdicts", []) + v.get("tech_verdicts", []):
        if not x["ok"]:
            print(f"  [{x['relation']}] {x['note']}\n      {x['sentence'][:150]}")

# MOLEVERA / BIOQL
