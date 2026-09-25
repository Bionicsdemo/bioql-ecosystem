"""
Putting every sentence of a report to Jev, against only the values it quotes.

The template machinery already guarantees the NUMBERS are real: a sentence cannot
name a value the run does not carry, because there is nowhere for that value to come
from. It does not guarantee the SENTENCE is supported -- a template can word a
relationship the data never establishes ("X therefore Y" when the run only records X).

So each sentence goes to Jev with the values it cites and nothing else. Judging
against only the quoted values is the whole point: a sentence that needs outside
knowledge to be true is a sentence the report should not be making. Three
independent judgements per sentence, asked so they cannot all fail the same way:

    supported     does the state establish exactly what the sentence says?
    overclaims    does the sentence assert more than the state carries?
    invented      does it name a number, unit or entity the state does not have?

A sentence passes when it is supported, does not overclaim, and invents nothing.

Never raises, and degrades honestly: with no credential, `{"available": False}` and
a reason. A report must build whether or not the verifier can run.

MOLEVERA / BIOQL
"""

import concurrent.futures
import os
import time
from typing import Any, Dict, List, Optional

from . import facts as F

SUPPORTED, OVERCLAIM, INVENTED = "supported", "overclaims", "invented"
PASS_SUPPORT = 0.70  # below this the state does not establish the sentence
FAIL_FAULT = 0.50  # at or above this the sentence overclaims or invents

QUESTIONS = {
    SUPPORTED: {
        "type": "noul",
        "instructions": (
            "`sentence` is one line from an automatically generated scientific report. "
            "`values` holds every value from the run that the sentence cites, keyed by its "
            "path in the run's result. Judge ONLY against `values`: treat anything not in "
            "`values` as unknown about this run, however plausible it may be. When "
            "`recomputed_and_verified` is present, it is arithmetic this report redid from "
            "the run itself and is evidence as good as `values`. Is everything "
            "the sentence asserts ABOUT THIS RUN established by `values`?\n\n"
            "Yes when each figure, name, unit and relationship it attributes to this run is "
            "in `values` or follows directly from it. No when any claim about this run would "
            "need information that is not there.\n\n"
            "Two things do NOT make it No. Textbook explanation of what a quantity or a "
            "molecule is, asserting nothing new about this run -- a signal peptide routing a "
            "protein to secretion, a ribosome reading triplets, a cap protecting the 5' end. "
            "And description of what the page itself draws or animates."
        ),
    },
    OVERCLAIM: {
        "type": "noul",
        "instructions": (
            "Judge whether `sentence` claims MORE about this run than `values` carries: an "
            "effect where the run has only a number, a cause where it has a correlation, a "
            "measurement where it has an estimate, a validation where it has a prediction, "
            "or certainty where the run records a status, a caveat or a null.\n\n"
            "Yes when the sentence is stronger than the data behind it. No when it states "
            "exactly what the data says, including when it plainly reports an absence, a "
            "failure or a caveat, and No when the stronger-sounding part is generic "
            "background or a description of the page's own animation."
        ),
    },
    INVENTED: {
        "type": "noul",
        "instructions": (
            "Judge whether `sentence` attributes to THIS RUN any figure, unit, identifier, "
            "method, model, protein, gene or backend that does NOT appear in `values`.\n\n"
            "Yes when a specific claim about this run names something with no counterpart in "
            "`values`. No when everything it attributes to this run is there. Ordinary "
            "connecting language, biological mechanisms that are common knowledge rather "
            "than results of this run, and description of the page's own animation are not "
            "inventions."
        ),
    },
}


def configured() -> bool:
    try:
        import typesafe_client

        return bool(typesafe_client.is_configured())
    except Exception:
        return False


def _state(
    beat: Dict[str, Any], result: Any, checks: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """The sentence, the values it cites, and the evidence behind any claim it makes.

    A sentence gated on a check ("checked here, the parts add up") is supported by
    that check, not by the raw values -- so the check's own recomputed statement is
    offered alongside them. Nothing else is: whatever is not here counts as unknown.
    """
    values = {}
    for p in beat.get("paths") or []:
        v = F.get(result, p)
        if isinstance(v, (dict, list)):
            v = str(v)[:400]
        values[p] = v
    # The technical line is its own claim; folding it in would make one judgement
    # answer for two sentences, and a caveat in the provenance would drag the
    # sentence down with it.
    state = {
        "sentence": beat.get("en") or beat.get("es") or "",
        "values": values,
        "kind": beat.get("kind", "fact"),
    }
    ev = (checks or {}).get(beat.get("_check") or "")
    if ev:
        state["recomputed_and_verified"] = ev
    return state


def _judge(
    client,
    beat: Dict[str, Any],
    result: Any,
    timeout: float,
    checks: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    ans = client.ask(_state(beat, result, checks), QUESTIONS, timeout=timeout)["answers"]
    p_sup = client.noul(ans, SUPPORTED)
    p_over = client.noul(ans, OVERCLAIM)
    p_inv = client.noul(ans, INVENTED)
    if p_sup is None:
        return {
            "relation": "says_nothing",
            "confidence": 0.0,
            "ok": False,
            "note": "Jev returned no judgement",
        }
    ok = p_sup >= PASS_SUPPORT and (p_over or 0) < FAIL_FAULT and (p_inv or 0) < FAIL_FAULT
    if ok:
        rel, note = "supports", ""
    elif (p_inv or 0) >= FAIL_FAULT:
        rel, note = "contradicts", f"names something the quoted values do not carry (p={p_inv:.2f})"
    elif (p_over or 0) >= FAIL_FAULT:
        rel, note = "contradicts", f"claims more than the quoted values carry (p={p_over:.2f})"
    else:
        rel, note = "says_nothing", f"the quoted values do not establish it (support p={p_sup:.2f})"
    return {
        "relation": rel,
        "confidence": round(float(p_sup), 3),
        "ok": ok,
        "note": note,
        "p_support": round(float(p_sup), 3),
        "p_overclaim": None if p_over is None else round(float(p_over), 3),
        "p_invented": None if p_inv is None else round(float(p_inv), 3),
    }


def verify(
    beats: List[Dict[str, Any]],
    result: Any,
    *,
    timeout: float = 60.0,
    workers: int = 4,
    limit: Optional[int] = None,
    checks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Every sentence judged against the values it quotes. Never raises."""
    t0 = time.time()
    try:
        import typesafe_client as client
    except Exception as e:  # noqa: BLE001
        return {
            "available": False,
            "why": f"typesafe_client not importable: {type(e).__name__}: {e}",
            "checked": 0,
            "verdicts": [],
            "n_ok": 0,
            "n_unsupported": 0,
            "elapsed_s": 0.0,
        }
    if not client.is_configured():
        return {
            "available": False,
            "why": "no TypeSafe credential (set TYPESAFE_API_KEY or ~/.bioql/typesafe_tokens.json)",
            "checked": 0,
            "verdicts": [],
            "n_ok": 0,
            "n_unsupported": 0,
            "elapsed_s": 0.0,
        }

    todo = [(i, b) for i, b in enumerate(beats) if (b.get("en") or b.get("es"))]
    if limit:
        todo = todo[:limit]
    verdicts: List[Dict[str, Any]] = []
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        ev = {c["id"]: (c.get("en") or c.get("es") or "") for c in (checks or []) if c.get("ok")}
        futures = {pool.submit(_judge, client, b, result, timeout, ev): i for i, b in todo}
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            try:
                v = fut.result()
            except Exception as e:  # noqa: BLE001 -- one refusal must not lose the rest
                failures += 1
                v = {
                    "relation": "says_nothing",
                    "confidence": 0.0,
                    "ok": False,
                    "note": f"not judged: {type(e).__name__}: {str(e)[:120]}",
                }
            v["i"] = i
            v["sentence"] = (beats[i].get("en") or beats[i].get("es"))[:220]
            verdicts.append(v)
    verdicts.sort(key=lambda v: v["i"])
    n_ok = sum(1 for v in verdicts if v["ok"])
    out = {
        "available": True,
        "why": None,
        "checked": len(verdicts),
        "verdicts": verdicts,
        "n_ok": n_ok,
        "n_unsupported": len(verdicts) - n_ok,
        "n_errors": failures,
        "elapsed_s": round(time.time() - t0, 1),
        "thresholds": {"support": PASS_SUPPORT, "fault": FAIL_FAULT},
    }
    if failures and failures == len(verdicts):
        out.update(available=False, why="every request to Jev failed")
    return out


def summarize(v: Optional[Dict[str, Any]]) -> str:
    if not v:
        return "verification: not run"
    if not v.get("available"):
        return f"verification: unavailable ({v.get('why')})"
    s = (
        f"verification: {v['n_ok']}/{v['checked']} sentences supported by the values they "
        f"quote, {v['elapsed_s']} s"
    )
    if v.get("n_errors"):
        s += f", {v['n_errors']} not judged"
    return s


if __name__ == "__main__":
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
    v = verify(beats, p["result"], limit=int(os.environ.get("BIOQL_VERIFY_LIMIT", "0")) or None)
    print(summarize(v))
    for x in v.get("verdicts", []):
        if not x["ok"]:
            print(f"  [{x['relation']}] {x['note']}\n      {x['sentence'][:150]}")

# MOLEVERA / BIOQL
