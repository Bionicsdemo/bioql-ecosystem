"""Route a request in words to one registered tool. Select from the registry.

WHY THIS IS A SELECTION PROBLEM AND NOT A GENERATION ONE
    The MCP server registers 130 tools. A request in plain language has to
    reach exactly one of them. A model that WRITES a tool name can write one
    that does not exist, or -- worse -- one that does exist and costs GPU
    hours. `full_drug_development` and `bioql_status` are one token apart in
    an embedding and four orders of magnitude apart in cost.

    So the model never writes a name. Code hands it the registry, the model
    returns an index, and code looks the tool up. A name that is not in the
    registry cannot come out of this module -- the same invariant, enforced
    the same way, as in `literature_value_extraction`.

COST IS A GATE, NOT A HINT
    Confidence alone must not launch an expensive run. Each tool carries a
    cost tier, and a tier above `cheap` requires both a higher confidence
    floor AND explicit human confirmation. The router's job is to propose;
    spending is the user's decision. This is the same standing rule that keeps
    QPU submission off by default.

WHAT IT REFUSES
    Below the floor, it returns `none` with the shortlist it considered and
    what it would need to disambiguate. An honest "I am not sure which of
    these three you meant" is worth more than a confident wrong pipeline.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import typesafe_client as TS

# What running the tool costs. The router may auto-dispatch only `cheap`.
COST_TIERS = ("cheap", "cpu_heavy", "gpu", "quantum", "irreversible")

# Confidence a selection must clear before it may be acted on, per tier.
CONFIDENCE_FLOOR = {
    "cheap": 0.60,
    "cpu_heavy": 0.80,
    "gpu": 0.90,
    "quantum": 0.90,
    "irreversible": 0.95,
}

# Tiers that never dispatch without a human saying so, however confident.
REQUIRES_CONFIRMATION = frozenset({"gpu", "quantum", "irreversible"})

# Generic executors: the cost lives in the PAYLOAD, not in the name. A name
# like `bioql_execute` reads as cheap and can carry a 51-stage quantum run, so
# no name-based tier can be trusted for it. Always confirmed, whatever tier.
_PAYLOAD_COST_SHAPES = ("execute", "run_script", "submit", "eval", "dispatch")


def cost_is_in_the_payload(name: str, description: str = "") -> bool:
    """True when the tool is a generic executor and its name says nothing."""
    hay = ("%s %s" % (name, description)).lower()
    return any(s in hay for s in _PAYLOAD_COST_SHAPES)

# Substrings that place a tool in a tier when the registry does not say.
_TIER_HINTS = (
    ("irreversible", ("delete", "purge", "reset", "submit_job", "deploy")),
    ("quantum", ("qpu", "quantum", "vqe", "qaoa", "sqd", "qec")),
    # A multi-stage pipeline reaches GPU stages whichever way it branches, so
    # it belongs here and not below: `full_drug_development` runs 51 stages and
    # is the most expensive thing on the platform. Classified `cpu_heavy` it
    # cleared its floor at 0.88 and dispatched itself, which is exactly the
    # mistake this module exists to prevent.
    ("gpu", ("protenix", "complexa", "alphagen", "fold", "docking", "md_",
             "engineering", "protein_", "antibody", "binder",
             "pipeline", "full_", "complete_", "discovery")),
    ("cpu_heavy", ("design", "optimization", "benchmark", "simulat",
                   "multipose", "pareto", "screen")),
)

# Names that read as a plain lookup. Anything else with no hint at all is
# assumed to cost something: an unknown tool classified `cheap` is a tool the
# router may dispatch on its own, which is the wrong way to be wrong.
_CHEAP_SHAPES = ("status", "list_", "get_", "fetch", "help", "info", "check_",
                 "report", "read_", "search", "query", "show", "results")
_UNKNOWN_TIER = "cpu_heavy"


class NotInRegistry(TS.TypeSafeError):
    """The model returned a tool that is not registered. Refused."""


def infer_cost_tier(name: str, description: str = "") -> str:
    """Classify a tool by cost. Pure string matching -- no judgment involved.

    Takes the MOST expensive tier any hint suggests, never the first one
    matched: a tool that is both a pipeline and a QPU job is a QPU job. With
    no hint at all it is assumed to cost something unless its name reads as a
    plain lookup -- being wrong towards caution costs a confirmation prompt,
    being wrong the other way costs GPU hours.
    """
    hay = ("%s %s" % (name, description)).lower()
    for tier, hints in _TIER_HINTS:          # ordered most expensive first
        if any(h in hay for h in hints):
            return tier
    if any(s in hay for s in _CHEAP_SHAPES):
        return "cheap"
    return _UNKNOWN_TIER


def build_registry(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise a tool list into the closed set the model chooses from."""
    out = []
    for t in tools or []:
        name = str((t or {}).get("name") or "").strip()
        if not name:
            continue
        desc = str(t.get("description") or "").strip()
        out.append({
            "name": name,
            "description": desc[:200],
            "cost_tier": t.get("cost_tier") or infer_cost_tier(name, desc),
        })
    return out


def route(request: str,
          registry: List[Dict[str, Any]],
          *,
          shortlist: int = 25,
          timeout: float = 25.0) -> Dict[str, Any]:
    """Choose one registered tool for `request`, or decline and say why.

    Never returns a name absent from `registry`. Never marks an expensive tool
    ready to dispatch without confirmation.
    """
    reg = build_registry(registry)
    if not reg:
        return _decline("No tools are registered; there is nothing to route to.", [])
    if not (request or "").strip():
        return _decline("Empty request; nothing to route.", [])

    # Keyword pre-filter so the model sees a short, relevant set rather than
    # 130 options. A tool filtered out here simply cannot be selected -- which
    # is why the filter is generous and falls back to the whole registry.
    words = {w for w in _tokens(request) if len(w) > 3}
    scored = sorted(
        reg,
        key=lambda t: -len(words & _tokens("%s %s" % (t["name"], t["description"]))))
    top = scored[:shortlist] if words else reg[:shortlist]
    if not any(words & _tokens("%s %s" % (t["name"], t["description"])) for t in top):
        top = reg[:shortlist]

    # Keyed by NAME, never by position. A positional index depends on an
    # ordering the caller cannot see, so any perturbation between building the
    # options and looking the choice up dispatches a different tool -- and the
    # tool one row over may cost GPU hours.
    by_name = {t["name"]: t for t in top}
    options = {
        t["name"]: "[%s] %s" % (t["cost_tier"], t["description"] or "no description")
        for t in top
    }
    options["none"] = ("No registered tool clearly matches this request, or more "
                       "than one matches and the request does not distinguish them.")

    questions = {
        "which_tool": {
            "type": "choice",
            "instructions": (
                "Which single registered tool does this request ask for? Choose "
                "'none' if no option clearly matches or if several match equally "
                "well. Prefer 'none' over a costly guess: the options marked gpu, "
                "quantum or irreversible consume real budget when run."
            ),
            "criteria": options,
        },
    }

    try:
        res = TS.ask({"request": request[:2000]}, questions, timeout=timeout)
    except TS.TypeSafeNotConfigured as exc:
        return _decline("Routing unavailable: %s" % exc, top)
    except TS.TypeSafeError as exc:
        return _decline("Routing unavailable: %s" % exc, top)

    ans = (res.get("answers") or {}).get("which_tool") or {}
    choice = str(ans.get("choice", ans.get("value", ""))).strip()
    confidence = ans.get("confidence")

    if choice == "none" or choice == "":
        return _decline(
            "No registered tool clearly matches. These were considered.", top,
            confidence=confidence)

    if choice not in options:
        raise NotInRegistry(
            "model returned %r, which is not one of the %d registered tools it "
            "was shown. Refusing: a tool name that is not in the registry cannot "
            "come out of this module." % (choice, len(top)))

    tool = by_name[choice]
    tier = tool["cost_tier"]
    floor = CONFIDENCE_FLOOR.get(tier, 0.90)
    conf = float(confidence) if isinstance(confidence, (int, float)) else 0.0

    payload_cost = cost_is_in_the_payload(tool["name"], tool["description"])
    below_floor = conf < floor
    needs_ok = tier in REQUIRES_CONFIRMATION or payload_cost

    return {
        "available": True,
        "tool": tool["name"],
        "cost_tier": tier,
        "confidence": confidence,
        "confidence_floor": floor,
        "ready_to_dispatch": (not below_floor) and (not needs_ok),
        "requires_confirmation": needs_ok,
        "cost_is_in_the_payload": payload_cost,
        "reason": (
            "Below the %.2f confidence floor for a %s tool; ask rather than run."
            % (floor, tier) if below_floor else
            "This is a generic executor: its cost is in the payload, not the "
            "name, so no name-based tier can clear it. Confirmation required."
            if payload_cost else
            "A %s tool is never dispatched without explicit confirmation, however "
            "confident the match." % tier if needs_ok else
            "Cheap tool above its confidence floor; safe to dispatch."
        ),
        "considered": [t["name"] for t in top[:10]],
        "method": "closed-registry selection; the name is looked up, never written",
    }


def _tokens(s: str) -> set:
    out, cur = set(), []
    for ch in str(s).lower():
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.add("".join(cur))
            cur = []
    if cur:
        out.add("".join(cur))
    return out


def _decline(reason: str, considered: List[Dict[str, Any]],
             confidence: Optional[float] = None) -> Dict[str, Any]:
    return {
        "available": False,
        "tool": None,
        "ready_to_dispatch": False,
        "confidence": confidence,
        "reason": reason,
        "considered": [t["name"] for t in (considered or [])[:10]],
        "next_step": (
            "Name the tool directly, or say which of the considered tools you "
            "meant. Nothing was run."
        ),
    }
