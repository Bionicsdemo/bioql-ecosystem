"""
Sentences whose numbers can only come from the result.

A beat is a short bilingual template: `"El mRNA mide {p:4.full_mrna_length_nt} nt"`.
Every `{...}` names a path into the result JSON, so `render()` fills it from the
data or drops the sentence -- a template cannot state a number the run does not
have, because there is nowhere for that number to come from. Paths marked `?`
are optional: missing, they leave an empty string; a missing required path
turns the beat into a declared gap carrying the pipeline's own reason.

Format after a `|`: `n` plain number, `n2` two decimals, `pct` percent,
`int` thousands separator, `count` length, `up`/`low` case.

A beat may carry a second `tech` line -- the method, backend, uncertainty or
provenance behind the value it just stated. It is resolved separately, so a
sentence survives a run that recorded no provenance for it, and a half-filled
technical line never reaches the page.

MOLEVERA / BIOQL
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import facts as F

_FIELD = re.compile(r"\{([^{}]+)\}")


def _fmt_number(x: float, spec: str) -> str:
    if spec == "int" or (spec in ("", "n") and float(x).is_integer()):
        return f"{int(x):,}".replace(",", " ") if abs(x) >= 10000 else str(int(x))
    if spec == "pct":
        return f"{x * 100:.1f}%"
    if spec.startswith("n") and spec[1:].isdigit():
        return f"{x:.{int(spec[1:])}f}"
    return f"{x:.4g}"


def format_value(v: Any, spec: str = "", lang: str = "es") -> str:
    if spec == "count":
        return str(len(v)) if isinstance(v, (list, tuple, dict, str)) else "1"
    if isinstance(v, bool):
        return ("sí" if v else "no") if lang == "es" else ("yes" if v else "no")
    if isinstance(v, (int, float)):
        return _fmt_number(float(v), spec)
    if isinstance(v, (list, tuple)):
        return ", ".join(format_value(x, "", lang) for x in v)
    if isinstance(v, dict):
        return ", ".join(f"{k} {format_value(x, '', lang)}" for k, x in v.items())
    s = str(v)
    return s.upper() if spec == "up" else s.lower() if spec == "low" else s


class Resolver:
    """Resolves `{path|spec}` against one result, remembering which paths were used."""

    def __init__(self, result: Any, aliases: Optional[Dict[str, str]] = None, lang: str = "es"):
        self.result = result
        self.aliases = aliases or {}
        self.lang = lang  # a boolean reads "sí"/"no" or "yes"/"no" accordingly
        self.used: List[str] = []

    def path_of(self, ref: str) -> str:
        head, _, rest = ref.partition(":")
        base = self.aliases.get(head)
        return f"{base}.{rest}" if base and rest else (base or ref)

    def value(self, ref: str) -> Tuple[Any, str]:
        path = self.path_of(ref)
        return F.get(self.result, path, None), path

    def render(self, text: str) -> Optional[str]:
        """The sentence with values filled in, or None when a required one is missing."""
        missing = False

        def sub(m: re.Match) -> str:
            nonlocal missing
            body = m.group(1)
            optional = body.endswith("?")
            body = body[:-1] if optional else body
            ref, _, spec = body.partition("|")
            v, path = self.value(ref.strip())
            if v is None or v == "" or v == [] or v == {}:
                if not optional:
                    missing = True
                return ""
            self.used.append(path)
            return format_value(v, spec.strip(), self.lang)

        out = _FIELD.sub(sub, text)
        if missing:
            return None
        return re.sub(r"\s{2,}", " ", out).replace(" .", ".").replace(" ,", ",").strip()


def gap_reason(result: Any, paths: List[str], fallback: str) -> Tuple[str, List[str]]:
    """The pipeline's own words for why something is absent, and where they came from.

    A gap beat is given several places to look; only the one that actually supplied the
    explanation is cited, so the page never points a reader at an empty path.
    """
    for p in paths:
        block = F.get(result, p)
        if isinstance(block, dict):
            for k in (
                "status_reason",
                "reason",
                "honest_note",
                "note",
                "error",
                "applicability_note",
                "plddt_note",
            ):
                v = block.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip(), [f"{p}.{k}"]
        elif isinstance(block, str) and block.strip():
            return block.strip(), [p]
    return fallback, []


def build_beats(
    result: Any,
    beats: List[Dict[str, Any]],
    aliases: Optional[Dict[str, str]] = None,
    checks: Optional[Dict[str, bool]] = None,
    meshes: Optional[Any] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Render a chapter's beats. Returns (beats kept, paths actually quoted).

    A beat with `requires_check` is dropped unless that check ran AND passed, and
    one with `requires_mesh` unless that structure was actually drawn: a sentence
    may not describe a picture that is not there, nor claim a verification that
    could not be done. Either way the beat's `gap` explanation takes its place."""
    out: List[Dict[str, Any]] = []
    used: List[str] = []
    checks = checks or {}
    meshes = set(meshes or ())
    for b in beats:
        needs_failure = b.get("requires_failed_check")
        unmet = (
            (b.get("requires_check") and not checks.get(b["requires_check"]))
            or (b.get("requires_mesh") and b["requires_mesh"] not in meshes)
            # a "these do not add up" sentence exists only while they do not add up
            or (needs_failure and checks.get(needs_failure, True))
        )
        if unmet:
            if b.get("gap"):
                why, src = gap_reason(result, b["gap"], b.get("gap_text", ""))
                if why:
                    out.append(
                        {
                            "es": f"{b.get('gap_es', 'No está en la corrida')}: {why}",
                            "en": f"{b.get('gap_en', 'Not in this run')}: {why}",
                            "kind": "gap",
                            "focus": b.get("focus", {}),
                            "paths": src,
                        }
                    )
            continue
        r = Resolver(result, aliases, "es")
        es = r.render(b["es"])
        en = Resolver(result, aliases, "en").render(b["en"])
        if es is None or en is None:
            if b.get("gap"):
                why, src = gap_reason(result, b["gap"], b.get("gap_text", ""))
                if why:
                    out.append(
                        {
                            "es": f"{b.get('gap_es', 'Este dato no está en la corrida')}: {why}",
                            "en": f"{b.get('gap_en', 'This value is not in the run')}: {why}",
                            "kind": "gap",
                            "focus": b.get("focus", {}),
                            "paths": src,
                        }
                    )
            continue
        beat = {
            "es": es,
            "en": en,
            "_check": b.get("requires_check") or "",
            "kind": b.get("kind", "fact"),
            "focus": b.get("focus", {}),
            "paths": sorted(set(r.used)),
        }
        # The technical line resolves on its own: a sentence keeps its place even when
        # the run recorded no method or backend for that value, and a half-filled
        # provenance line never appears.
        tech = b.get("tech")
        if tech:
            rt_es, rt_en = Resolver(result, aliases, "es"), Resolver(result, aliases, "en")
            t_es, t_en = rt_es.render(tech["es"]), rt_en.render(tech["en"])
            if t_es and t_en:
                beat["tech"] = {"es": t_es, "en": t_en}
                beat["paths"] = sorted(set(beat["paths"]) | set(rt_es.used))
                used += rt_es.used
        out.append(beat)
        used += r.used
    return out, sorted(set(used))


# MOLEVERA / BIOQL
