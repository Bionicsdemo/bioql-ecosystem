"""Audit the runs already paid for, and say which are still usable.

There is no budget to regenerate the set, so the question is not "are these
runs perfect" -- they are not -- but "which of them can still be believed, and
for what". That is a triage, and it has to be done by the same invariants that
gate new runs, or it is just another opinion.

It reads. It writes nothing back into any result.

Usage:
    python audit_historical_runs.py [--dir /opt/bioql/job_results] [--json out.json]

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stage_audit as SA  # noqa: E402

DEFAULT_DIR = os.path.join(os.environ.get("BIOQL_DATA", "/opt/bioql"), "job_results")


def _candidates(blob: Dict[str, Any]) -> List[Dict[str, Any]]:
    inner = blob.get("result") if isinstance(blob.get("result"), dict) else blob
    for key in ("candidates", "all_candidates", "drug_candidates"):
        v = inner.get(key)
        if isinstance(v, list):
            return [c for c in v if isinstance(c, dict)]
    return []


def _flatten_for_audit(cand: Dict[str, Any]) -> Dict[str, Any]:
    """The candidate plus its `analyses` subtree, which is where toxicology lives.

    An invariant that never sees the hazard cannot catch a verdict that
    contradicts it, and in this schema the hazard is one level deeper than the
    verdict -- which is precisely how the two stopped being compared.
    """
    out = {k: v for k, v in cand.items()
           if k not in ("mol_3d", "structure_svg", "structure_png_b64",
                        "target_structure", "sequence", "original_sequence")}
    analyses = cand.get("analyses")
    if isinstance(analyses, dict):
        out["analyses"] = {k: v for k, v in analyses.items()
                           if k not in ("protenix_structure", "chai1_structure",
                                        "3d_structure")}
    return out


def audit_file(path: str, cohort: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            blob = json.load(fh)
    except (OSError, ValueError) as exc:
        return {"file": os.path.basename(path), "readable": False, "error": str(exc)}

    cands = _candidates(blob)
    rows = []
    for c in cands:
        flat = _flatten_for_audit(c)
        a = SA.audit_stage("historical_candidate", flat, candidate=flat,
                           cohort=cohort, consult_model=False)
        rows.append({
            "name": c.get("name"),
            "class": c.get("drug_candidate_class"),
            "verdict": a["verdict"],
            "invariants_failed": sorted({f["invariant"] for f in a["findings"]
                                         if f["verdict"] != "pass"}),
            "details": [f["detail"][:200] for f in a["findings"]
                        if f["verdict"] == "quarantine"][:3],
        })

    worst = "pass"
    for r in rows:
        if SA._ESCALATION[r["verdict"]] > SA._ESCALATION[worst]:
            worst = r["verdict"]
    return {
        "file": os.path.basename(path),
        "readable": True,
        "candidates": len(rows),
        "verdict": worst if rows else "empty",
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--json", default=None, help="write the full report here")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    if not os.path.isdir(args.dir):
        print("no such directory: %s" % args.dir)
        return 2

    files = sorted(f for f in os.listdir(args.dir) if f.endswith(".json"))
    if args.limit:
        files = files[:args.limit]
    if not files:
        print("no result files in %s" % args.dir)
        return 1

    # The cohort is every candidate in the set, so a value repeated across
    # molecules shows up as the default it is.
    cohort: List[Dict[str, Any]] = []
    for f in files:
        try:
            with open(os.path.join(args.dir, f), encoding="utf-8") as fh:
                cohort.extend(_flatten_for_audit(c) for c in _candidates(json.load(fh)))
        except (OSError, ValueError):
            continue

    reports = [audit_file(os.path.join(args.dir, f), cohort) for f in files]

    verdicts = Counter(r.get("verdict") for r in reports)
    failed = Counter()
    total_cands = 0
    for r in reports:
        for row in r.get("rows", []):
            total_cands += 1
            for inv in row["invariants_failed"]:
                failed[inv] += 1

    print("\n  runs read           : %d" % sum(1 for r in reports if r.get("readable")))
    print("  unreadable          : %d" % sum(1 for r in reports if not r.get("readable")))
    print("  candidates audited  : %d" % total_cands)
    print("\n  verdict per run:")
    for v, n in verdicts.most_common():
        print("    %-12s %4d" % (v, n))
    print("\n  invariant failures across candidates:")
    for inv, n in failed.most_common():
        pct = (100.0 * n / total_cands) if total_cands else 0.0
        print("    %-28s %5d  (%.0f%%)" % (inv, n, pct))

    usable = verdicts.get("pass", 0)
    print("\n  %d of %d runs carry no invariant failure and are usable as they stand."
          % (usable, len(reports)))
    print("  The rest are not worthless -- the failures name which FIELD is not to")
    print("  be believed, not which run to discard. Nothing was written back.\n")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"reports": reports,
                       "summary": {"verdicts": dict(verdicts),
                                   "invariant_failures": dict(failed),
                                   "candidates": total_cands}}, fh, indent=2)
        print("  full report: %s\n" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
