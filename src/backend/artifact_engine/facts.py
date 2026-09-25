"""
Every value in a pipeline result, addressable and accounted for.

The interactive report promises that ALL of the result is in it. That promise is
checked here, not hoped for: the result JSON is flattened into leaves (one per
scalar, one per empty container), each leaf gets a path such as
`stages.4_mrna_optimization.all_candidates[0].cai`, and every chapter claims the
subtrees it shows by path prefix. `coverage()` then proves each leaf belongs to
exactly one chapter -- the most specific prefix wins -- and whatever no chapter
claims goes to the data annex, so nothing is ever dropped silently.

MOLEVERA / BIOQL
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

Leaf = Tuple[str, Any]

_TOKEN = re.compile(r"[^.\[\]]+|\[\d+\]")


def flatten(obj: Any, prefix: str = "") -> List[Leaf]:
    """(path, value) for every scalar and every empty container, in document order."""
    out: List[Leaf] = []

    def walk(o: Any, p: str) -> None:
        if isinstance(o, dict):
            if not o:
                out.append((p, {}))
            for k, v in o.items():
                walk(v, f"{p}.{k}" if p else str(k))
        elif isinstance(o, list):
            if not o:
                out.append((p, []))
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
        else:
            out.append((p, o))

    walk(obj, prefix)
    return out


def tokens(path: str) -> List[str]:
    return _TOKEN.findall(path)


def under(path: str, prefix: str) -> bool:
    """True when `path` is `prefix` itself or inside it (token boundary, not substring)."""
    if not prefix:
        return True
    tp, tq = tokens(path), tokens(prefix)
    return tp[: len(tq)] == tq


def get(obj: Any, path: str, default: Any = None) -> Any:
    cur = obj
    for t in tokens(path):
        if t.startswith("["):
            i = int(t[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return default
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or t not in cur:
                return default
            cur = cur[t]
    return cur


def owner(path: str, claims: Dict[str, Iterable[str]]) -> Optional[str]:
    """The chapter whose claimed prefix is the longest match for `path`."""
    best, best_len = None, -1
    for chapter, prefixes in claims.items():
        for pre in prefixes:
            if under(path, pre):
                n = len(tokens(pre))
                if n > best_len:
                    best, best_len = chapter, n
    return best


def coverage(result: Any, claims: Dict[str, Iterable[str]], annex: str = "annex") -> Dict[str, Any]:
    """Assign every leaf to a chapter. Returns counts per chapter and the annex paths."""
    leaves = flatten(result)
    per: Dict[str, int] = {}
    annex_paths: List[str] = []
    for path, _ in leaves:
        ch = owner(path, claims)
        if ch is None:
            ch = annex
            annex_paths.append(path)
        per[ch] = per.get(ch, 0) + 1
    return {"leaves": len(leaves), "per_chapter": per, "annex_paths": annex_paths}


# -- recognising what a value is -------------------------------------------------
_AA = set("ACDEFGHIKLMNPQRSTVWYXUBZO")
_NT = set("ACGUTN")


def is_pdb(v: Any) -> bool:
    return (
        isinstance(v, str)
        and len(v) > 200
        and ("\nATOM  " in v or v.startswith("ATOM  ") or "\nHETATM" in v)
    )


def is_data_image(v: Any) -> bool:
    return isinstance(v, str) and v.startswith("data:image/")


def fasta_sequence(v: Any) -> Optional[str]:
    """Sequence from a FASTA string, or from a bare sequence -- both forms occur."""
    if not isinstance(v, str) or not v.strip():
        return None
    seq = "".join(ln.strip() for ln in v.splitlines() if ln and not ln.startswith(">"))
    if not seq:
        return None
    return seq if seq_kind(seq, min_len=4) == "protein" or v.startswith(">") else None


def seq_kind(v: Any, min_len: int = 12) -> Optional[str]:
    """'rna', 'dna' or 'protein' for a bare sequence string, else None."""
    if not isinstance(v, str) or len(v) < min_len or any(c.isspace() for c in v[:200]):
        return None
    s = set(v.upper())
    if s <= _NT:
        return "rna" if "U" in s else "dna"
    if s <= _AA and len(s) >= 8:
        return "protein"
    return None


# -- units from key names (what the pipelines already encode in their field names) --
_UNIT_SUFFIX = [
    ("_kda", "kDa"),
    ("_da", "Da"),
    ("_aa", "aa"),
    ("_nt", "nt"),
    ("_bp", "bp"),
    ("_pct", "%"),
    ("_percent", "%"),
    ("_ha", "Ha"),
    ("_ev", "eV"),
    ("_mha", "mHa"),
    ("_kcal", "kcal/mol"),
    ("_kcal_mol", "kcal/mol"),
    ("_nm", "nm"),
    ("_um", "µM"),
    ("_nM", "nM"),
    ("_s", "s"),
    ("_seconds", "s"),
    ("_ms", "ms"),
    ("_a2", "Å²"),
    ("_A2", "Å²"),
    ("_angstrom", "Å"),
    ("_mw", "Da"),
    ("_usd", "USD"),
]


def unit_for(key: str) -> Optional[str]:
    k = key.lower()
    for suf, unit in _UNIT_SUFFIX:
        if k.endswith(suf.lower()):
            return unit
    return None


def humanize(key: str) -> str:
    k = re.sub(r"^\d+_", "", str(key))
    return k.replace("_", " ").strip()


# MOLEVERA / BIOQL
