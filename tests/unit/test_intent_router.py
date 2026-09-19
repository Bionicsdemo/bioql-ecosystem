"""A tool name that is not in the registry cannot come out of the router.

And confidence alone never launches a GPU run: cost is a gate, not a hint.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import intent_router as IR  # noqa: E402
import typesafe_client as TS  # noqa: E402

REGISTRY = [
    {"name": "bioql_status", "description": "Report the status of a running job."},
    {"name": "bioql_results", "description": "Fetch results for a finished job."},
    {"name": "full_drug_development", "description": "Run the complete 51-stage pipeline."},
    {"name": "quantum_fast_discovery", "description": "SQD discovery on QPU or simulator."},
    {"name": "protein_engineering_pipeline", "description": "Protenix folding and design."},
]


def _picks(monkeypatch, choice, confidence=0.99):
    monkeypatch.setattr(TS, "ask", lambda *a, **k: {
        "answers": {"which_tool": {"choice": choice, "confidence": confidence}},
        "usage": {}})


# ──────────────────────────── cost classification ─────────────────────────

@pytest.mark.parametrize("name,expected", [
    ("bioql_status", "cheap"),
    ("bioql_results", "cheap"),
    ("full_drug_development", "gpu"),
    ("quantum_fast_discovery", "quantum"),
    ("protein_engineering_pipeline", "gpu"),
    ("delete_session", "irreversible"),
])
def test_tools_are_placed_in_a_cost_tier(name, expected):
    assert IR.infer_cost_tier(name) == expected


def test_a_plain_lookup_is_cheap():
    assert IR.infer_cost_tier("list_targets", "Return known targets.") == "cheap"


def test_a_tool_with_no_hint_at_all_is_assumed_to_cost_something():
    """Being wrong towards caution costs a prompt; the other way costs GPU hours."""
    assert IR.infer_cost_tier("wibble_frobnicate", "") != "cheap"


def test_a_multi_stage_pipeline_is_never_cheap_enough_to_self_dispatch():
    """It cleared a 0.80 floor as cpu_heavy and launched 51 stages unasked."""
    assert IR.infer_cost_tier("full_drug_development") in IR.REQUIRES_CONFIRMATION


def test_the_most_expensive_matching_tier_wins():
    """A QPU job that is also a pipeline is a QPU job."""
    assert IR.infer_cost_tier("quantum_discovery_pipeline") == "quantum"


# ────────────── the invariant: nothing comes out that was not in ──────────

def test_a_tool_outside_the_registry_is_refused(monkeypatch):
    _picks(monkeypatch, "bioql_delete_everything")
    with pytest.raises(IR.NotInRegistry) as exc:
        IR.route("check my job", REGISTRY)
    assert "not in the registry" in str(exc.value)


def test_a_plausible_but_unregistered_name_is_refused(monkeypatch):
    """Options are keyed by name, so a near-miss name must still be refused."""
    _picks(monkeypatch, "bioql_statuses")
    with pytest.raises(IR.NotInRegistry):
        IR.route("check my job", REGISTRY)


# ─────────────────────────── cost gates dispatch ──────────────────────────

def test_a_cheap_tool_above_its_floor_is_ready_to_dispatch(monkeypatch):
    _picks(monkeypatch, "bioql_status", 0.97)
    r = IR.route("what is the status of my job", REGISTRY)
    assert r["tool"] == "bioql_status"
    assert r["ready_to_dispatch"] is True


def test_a_gpu_tool_is_never_ready_to_dispatch_however_confident(monkeypatch):
    """Certainty about WHAT to run is not permission to SPEND."""
    _picks(monkeypatch, "protein_engineering_pipeline", 1.0)
    r = IR.route("fold this protein", REGISTRY)
    assert r["tool"] == "protein_engineering_pipeline"
    assert r["ready_to_dispatch"] is False
    assert r["requires_confirmation"] is True


def test_a_quantum_tool_is_never_ready_to_dispatch(monkeypatch):
    _picks(monkeypatch, "quantum_fast_discovery", 1.0)
    r = IR.route("run the SQD discovery", REGISTRY)
    assert r["ready_to_dispatch"] is False
    assert r["cost_tier"] == "quantum"


def test_a_low_confidence_cheap_match_is_not_dispatched(monkeypatch):
    _picks(monkeypatch, "bioql_status", 0.40)
    r = IR.route("do the thing", REGISTRY)
    assert r["ready_to_dispatch"] is False
    assert "confidence floor" in r["reason"]


def test_an_expensive_tool_needs_a_higher_floor_than_a_cheap_one():
    assert IR.CONFIDENCE_FLOOR["cheap"] < IR.CONFIDENCE_FLOOR["gpu"]
    assert IR.CONFIDENCE_FLOOR["gpu"] <= IR.CONFIDENCE_FLOOR["irreversible"]


# ───────────────────── declining is a first-class answer ──────────────────

def test_none_is_offered_and_honoured(monkeypatch):
    seen = {}

    def _ask(state, questions, **k):
        seen["criteria"] = questions["which_tool"]["criteria"]
        return {"answers": {"which_tool": {"choice": "none"}}, "usage": {}}

    monkeypatch.setattr(TS, "ask", _ask)
    r = IR.route("something completely unrelated to this platform", REGISTRY)
    assert "none" in seen["criteria"]
    assert r["available"] is False and r["tool"] is None
    assert r["considered"], "a decline must still show what it weighed"


def test_the_options_carry_their_cost_so_the_choice_is_informed(monkeypatch):
    seen = {}

    def _ask(state, questions, **k):
        seen["criteria"] = questions["which_tool"]["criteria"]
        return {"answers": {"which_tool": {"choice": "none"}}, "usage": {}}

    monkeypatch.setattr(TS, "ask", _ask)
    IR.route("run a pipeline", REGISTRY)
    assert any("[quantum]" in v for v in seen["criteria"].values())


def test_an_empty_request_routes_nowhere():
    r = IR.route("   ", REGISTRY)
    assert r["available"] is False


def test_an_empty_registry_routes_nowhere():
    r = IR.route("check status", [])
    assert r["available"] is False


# ──────────────────── degrading, and never fabricating ────────────────────

def test_an_unconfigured_service_routes_nowhere(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(TS, "TOKEN_FILE", str(tmp_path / "absent.json"))
    r = IR.route("check my job status", REGISTRY)
    assert r["available"] is False and r["ready_to_dispatch"] is False


def test_a_service_failure_routes_nowhere(monkeypatch):
    def _fail(*a, **k):
        raise TS.TypeSafeError("down")
    monkeypatch.setattr(TS, "ask", _fail)
    r = IR.route("check my job status", REGISTRY)
    assert r["available"] is False
    assert "Nothing was run" in r["next_step"]


def test_the_question_id_clears_the_text_only_boundary():
    TS.assert_text_only_target("which_tool")


# ───────────── a generic executor carries its cost in its payload ─────────

def test_a_generic_executor_is_never_auto_dispatched(monkeypatch):
    """`bioql_execute` reads as cheap and can carry a 51-stage quantum run."""
    reg = [{"name": "bioql_execute", "description": "Execute a BioQL script."}]
    _picks(monkeypatch, "bioql_execute", 1.0)
    r = IR.route("execute this script", reg)
    assert r["tool"] == "bioql_execute"
    assert r["ready_to_dispatch"] is False
    assert r["cost_is_in_the_payload"] is True


def test_a_plain_lookup_is_still_auto_dispatched(monkeypatch):
    """The executor rule must not swallow every cheap tool."""
    _picks(monkeypatch, "bioql_status", 0.97)
    r = IR.route("status", REGISTRY)
    assert r["ready_to_dispatch"] is True
