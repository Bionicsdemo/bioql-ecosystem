"""Watch the literature for potencies. Extract what is written; never infer.

WHY THIS SHAPE AND NOT A HYPOTHESIS AGENT
    The obvious "literature agent" reads papers and proposes ideas. That is a
    generator, and everything this codebase spent two days fixing came from a
    generated number reaching a field that readers take as measured. So this
    one does the opposite: it fetches abstracts, hands each to the
    select-don't-generate extractor, and returns only values that are
    character-for-character present in a specific abstract, each with the PMID
    that carries it.

    It proposes nothing. Every number it returns is someone else's measurement
    with a citation attached, or it returns nothing at all.

WHAT IT UNBLOCKS
    `efficacious_dose` refuses without a potency, and the platform's only
    affinity is an MM-GBSA dG that must not become one. This finds a real IC50
    for a named compound and target, with a source a reader can open.

SOURCE
    Europe PMC's public REST API. No key, no account, and it returns full
    abstracts, which is what the extractor needs. Network failure yields no
    values and says so -- it never falls back to a remembered number.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# Only formatting tags that entity-decoding can reveal. Deliberately a closed
# list: a generic <...> sweep here would eat "IC50 < 10 nM".
_MARKUP_TAG = re.compile(r"</?(?:sup|sub|i|b|em|strong|br|p|span)\s*/?>",
                         re.IGNORECASE)

# Abstracts per query. Small on purpose: each one costs a model call to read,
# and a potency stated in the tenth hit is not more true than in the first.
DEFAULT_PAGE_SIZE = 5


class LiteratureUnavailable(RuntimeError):
    """The source could not be reached. Callers report nothing, not a guess."""


def _strip_tags(s: str) -> str:
    """Europe PMC embeds HTML entities and <sup> markup in abstracts.

    The extractor works on offsets into the text it is given, so the text it is
    given must be the text the offsets are quoted against -- cleaned once, here,
    and never again afterwards.
    """
    # Order matters, in both directions. Decoding before stripping would turn
    # "IC50 &lt; 10 nM" into "IC50 < 10 nM" and then eat the rest as a tag --
    # and comparison operators are everywhere in potency statements. Stripping
    # before decoding leaves "&lt;sup&gt;" behind as visible markup. So: strip
    # real tags, decode entities, then remove only the known markup tags that
    # decoding can reveal.
    out, depth = [], 0
    for ch in s or "":
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    text = "".join(out)
    for ent, rep in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                     ("&apos;", "'"), ("&#x2009;", " "), ("&nbsp;", " "),
                     ("&amp;", "&")):
        text = text.replace(ent, rep)
    return _MARKUP_TAG.sub("", text)


def search_abstracts(query: str, page_size: int = DEFAULT_PAGE_SIZE,
                     timeout: float = 20.0) -> List[Dict[str, Any]]:
    """Abstracts matching `query`, newest-relevance first. Raises if unreachable."""
    params = urllib.parse.urlencode({
        "query": query, "format": "json",
        "resultType": "core", "pageSize": max(1, min(int(page_size), 25)),
    })
    req = urllib.request.Request(
        "%s?%s" % (EUROPEPMC, params),
        headers={"Accept": "application/json",
                 "User-Agent": "BioQL-literature-monitor"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise LiteratureUnavailable("Europe PMC unreachable: %s" % exc)

    out = []
    for r in (payload.get("resultList") or {}).get("result", []):
        abstract = _strip_tags(r.get("abstractText") or "")
        if not abstract.strip():
            continue
        out.append({
            "pmid": r.get("pmid") or r.get("id"),
            "doi": r.get("doi"),
            "title": _strip_tags(r.get("title") or ""),
            "journal": (r.get("journalInfo") or {}).get("journal", {}).get("title"),
            "year": r.get("pubYear"),
            "abstract": abstract,
            "url": ("https://europepmc.org/article/%s/%s"
                    % (r.get("source") or "MED", r.get("id") or "")),
        })
    return out


def build_query(compound: str, target: str, measure: str = "IC50") -> str:
    """A query naming all three, so an abstract that mentions none is not read."""
    parts = [p for p in (compound, target, measure) if p and str(p).strip()]
    return " AND ".join('"%s"' % str(p).strip() for p in parts)


def find_potency(compound: str, target: str, *, measure: str = "IC50",
                 page_size: int = DEFAULT_PAGE_SIZE,
                 timeout: float = 20.0) -> Dict[str, Any]:
    """Search, then extract. Returns every citation-backed value found, best first.

    A returned value is a span of a specific abstract, with that abstract's PMID
    and the offsets to locate it. Nothing is averaged, combined or inferred
    across papers: they are reported side by side, because two labs disagreeing
    is information a reader needs, not noise to smooth away.
    """
    query = build_query(compound, target, measure)
    try:
        papers = search_abstracts(query, page_size, timeout)
    except LiteratureUnavailable as exc:
        return {"available": False, "values": [], "query": query,
                "reason": str(exc),
                "note": "The search did not run. No value is reported."}

    if not papers:
        return {"available": False, "values": [], "query": query,
                "papers_read": 0,
                "reason": "No abstract matched %s." % query}

    try:
        import literature_value_extraction as LX
    except ImportError as exc:
        return {"available": False, "values": [], "query": query,
                "reason": "Extractor unavailable (%s)." % exc}

    values, refusals = [], []
    for p in papers:
        try:
            r = LX.select_value(p["abstract"], target, measure=measure)
        except LX.NotInText as exc:
            refusals.append({"pmid": p["pmid"], "reason": str(exc)[:200]})
            continue
        except Exception as exc:                       # never let one paper stop the sweep
            refusals.append({"pmid": p["pmid"], "reason": "%s" % exc})
            continue
        if not r.get("available"):
            continue
        values.append({
            "value_nm": r["value_nm"],
            "measure": measure,
            "target": target,
            "compound": compound,
            "selected_span": r["selected_span"],
            "source_offsets": r["source_offsets"],
            "confidence": r.get("confidence"),
            "pmid": p["pmid"],
            "doi": p.get("doi"),
            "title": p["title"],
            "journal": p.get("journal"),
            "year": p.get("year"),
            "url": p["url"],
            "provenance": r["provenance"],
        })

    values.sort(key=lambda v: -(v.get("confidence") or 0.0))
    return {
        "available": bool(values),
        "values": values,
        "query": query,
        "papers_read": len(papers),
        "refusals": refusals,
        "reason": None if values else (
            "%d abstracts were read and none stated a %s for %s. That is a "
            "result, not a failure." % (len(papers), measure, target)),
        "note": ("Each value is a verbatim span of the abstract under its PMID. "
                 "Values from different papers are listed separately and never "
                 "averaged: disagreement between labs is information."),
    }


def potency_for_candidate(candidate: Dict[str, Any], *, measure: str = "IC50",
                          page_size: int = DEFAULT_PAGE_SIZE) -> Dict[str, Any]:
    """Look up a candidate's potency by its own name and target."""
    name = str((candidate or {}).get("name") or "").strip()
    target = str((candidate or {}).get("target") or "").strip()
    if not name or not target:
        return {"available": False, "values": [],
                "reason": "A literature search needs both a compound name and a "
                          "target; this candidate has %s."
                          % ("no target" if name else "no name")}
    return find_potency(name, target, measure=measure, page_size=page_size)
