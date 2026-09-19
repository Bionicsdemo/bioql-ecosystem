"""TypeSafe System One client — typed judgments over TEXT, never over molecules.

TypeSafe returns calibrated probabilities for semantic questions. Its own skill
is explicit about the limit: "Typed output guarantees the interface, not truth.
System One models are trained for calibrated decisions; validate their
performance in the target domain."

That line draws the boundary this module enforces. A TypeSafe probability looks
exactly like an ensemble toxicology score once it lands in a report -- both are
numbers between 0 and 1 -- and this platform has already shipped a candidate
labelled "Good" whose own internals said Category 1 (Fatal) because one layer's
number was read as another's measurement.

So the rule here, enforced by `assert_text_only_state` and by
tests/unit/test_typesafe_boundary.py:

    TypeSafe judges text. Trained models measure molecules.

Credentials are read from the environment or from ~/.bioql/, following the same
convention as the Gosset integration. Nothing is read from the repository.

Stdlib only, same as gosset_mcp_client.py.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
TOKEN_FILE = os.path.expanduser("~/.bioql/typesafe_tokens.json")

# Field names that carry a scientific measurement. A TypeSafe answer must never
# be written into one of these, and a question must never be asked as if the
# model could supply one.
FORBIDDEN_TARGETS = frozenset({
    "ld50_mg_kg", "ld50_oral", "ld50_predicted", "ghs_class", "toxicity_class",
    "binding_affinity", "binding_affinity_kcal", "binding_affinity_kcal_mol",
    "predicted_binding_kd_nm", "kd_nm", "iptm", "ptm", "plddt",
    "composite_score", "drug_candidate_class", "safety_gate", "safety_flags",
    "noael", "loael", "herg_pic50", "herg_ic50_um", "dili_score",
    "nephrotoxicity", "hepatotoxicity", "cardiotoxicity", "neurotoxicity",
    "ames_mutagenicity", "micronucleus", "chromosome_aberration",
    "carcinogenicity", "qed_score", "logp", "tpsa", "overall_admet_score",
})


class TypeSafeError(RuntimeError):
    pass


class TypeSafeNotConfigured(TypeSafeError):
    """No credential available. Callers should degrade, not fabricate."""


def _read_api_key() -> Optional[str]:
    key = os.environ.get("TYPESAFE_API_KEY")
    if key and key.strip():
        return key.strip()
    try:
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    for field in ("api_key", "apiKey", "key", "token"):
        v = data.get(field)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def is_configured() -> bool:
    return _read_api_key() is not None


def assert_text_only_target(question_id: str) -> None:
    """Refuse a question whose id claims a measured scientific field.

    Naming a question `ld50_mg_kg` is how a judgment quietly becomes a
    measurement three layers downstream, so it is refused at the door.
    """
    qid = str(question_id or "").strip().lower()
    if qid in FORBIDDEN_TARGETS:
        raise TypeSafeError(
            "question id %r names a measured scientific field. TypeSafe judges "
            "text; this value must come from the trained model that measures it."
            % question_id
        )


def ask(state: Any,
        questions: Dict[str, Dict[str, Any]],
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        retries: int = 2) -> Dict[str, Any]:
    """POST one System One request. Returns the parsed `answers` mapping.

    `state` is the evidence (a string, or a JSON-serialisable object of named
    fields). `questions` maps an id to {type, instructions, criteria}.

    Raises TypeSafeNotConfigured when no credential is present: a caller must
    then say the check did not run, never assume it passed.
    """
    key = _read_api_key()
    if not key:
        raise TypeSafeNotConfigured(
            "No TypeSafe credential. Set TYPESAFE_API_KEY or create %s with "
            '{"api_key": "..."}.' % TOKEN_FILE
        )
    for qid in questions:
        assert_text_only_target(qid)

    body = json.dumps({
        "state": state,
        "model": model,
        "questions": questions,
    }).encode("utf-8")

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            API_URL, data=body, method="POST",
            headers={
                "Authorization": "Bearer %s" % key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            answers = payload.get("answers")
            if not isinstance(answers, dict):
                raise TypeSafeError("response carried no answers: %r" % payload)
            return {
                "answers": answers,
                "model": payload.get("model"),
                "usage": payload.get("usage") or {},
            }
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:300]
            except Exception:
                pass
            # 4xx will not fix itself on retry.
            if 400 <= exc.code < 500:
                raise TypeSafeError("HTTP %s: %s" % (exc.code, detail)) from exc
            last_err = TypeSafeError("HTTP %s: %s" % (exc.code, detail))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_err = exc
        if attempt < retries:
            time.sleep(0.6 * (2 ** attempt))
    raise TypeSafeError("TypeSafe request failed: %s" % last_err)


def noul(answers: Dict[str, Any], qid: str) -> Optional[float]:
    """Probability of yes, or None when the question was not answered."""
    a = answers.get(qid)
    if not isinstance(a, dict):
        return None
    v = a.get("noul")
    return float(v) if isinstance(v, (int, float)) else None


def score(answers: Dict[str, Any], qid: str) -> Optional[Dict[str, Any]]:
    """Score with its legend, distribution and confidence, or None."""
    a = answers.get(qid)
    if not isinstance(a, dict) or not isinstance(a.get("score"), (int, float)):
        return None
    return {
        "score": float(a["score"]),
        "legend": a.get("legend") or {},
        "probabilities": a.get("probabilities") or {},
        "confidence": a.get("confidence"),
    }
