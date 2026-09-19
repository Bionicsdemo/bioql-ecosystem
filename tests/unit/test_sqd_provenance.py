"""A record may not claim a quantum solve that did not happen.

Audited 2026-09-18: all 24 historical `ewf_sqd` records reported
`quantum_hard_fragments: 8..14` and a method string naming CUDA-Q SQD, while the
function that produced them never imported cudaq. The count was a count of
LABELS. These tests pin the three properties that made that possible.

The module itself only imports pyscf/vayesta/cudaq inside function bodies (they
live in the Modal image, not here), so the source is checked as source.

-- MOLEVERA / BIOQL
"""
import ast
import os
import re

import pytest

SRC = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src", "backend", "modal_ewf_sqd.py")

with open(SRC, encoding="utf-8") as _fh:
    TEXT = _fh.read()
TREE = ast.parse(TEXT)


def _func(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("function %r not found in modal_ewf_sqd.py" % name)


def _body_text(name):
    """Source of the function WITHOUT its docstring.

    A guard that reads the docstring fires on its own explanation -- the
    docstring here says "nothing here imports cudaq", which a naive substring
    check reads as an import. That exact mistake was made twice today.
    """
    node = _func(name)
    body = node.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return "\n".join(ast.get_source_segment(TEXT, st) or "" for st in body)


# ───── the classical function must not describe itself as quantum ─────

def test_the_classical_function_imports_no_quantum_stack():
    """`ewf_sqd_protein` claimed CUDA-Q SQD and never imported it."""
    body = _body_text("ewf_sqd_protein")
    for mod in ("cudaq", "ffsim", "qiskit_addon_sqd", "solve_fermion"):
        assert mod not in body, (
            "%s appears in ewf_sqd_protein; if it now really solves, update this "
            "test and its docstring together" % mod)


def test_the_classical_function_does_not_claim_a_quantum_solve():
    body = _body_text("ewf_sqd_protein")
    m = re.search(r'"method":\s*(".*?")', body, re.S)
    assert m, "no method string found"
    method = m.group(1).lower()
    assert "classical" in method
    assert "no quantum solve" in method


def test_the_classical_function_reports_zero_quantum_fragments():
    body = _body_text("ewf_sqd_protein")
    assert '"quantum_solved_fragments": 0' in body
    assert '"quantum_achieved": False' in body


def test_a_label_count_is_not_named_like_a_solve_count():
    """`quantum_hard_fragments` read as "solved on a quantum backend"."""
    body = _body_text("ewf_sqd_protein")
    assert "sqd_eligible_fragments_labelled" in body
    assert '"quantum_hard_fragments"' not in body


def test_the_docstring_says_the_unused_arguments_are_unused():
    doc = ast.get_docstring(_func("ewf_sqd_protein")) or ""
    assert "NO quantum solve" in doc
    for arg in ("sqd_on_hardest", "shots", "n_reps"):
        assert arg in doc, "%s is accepted and ignored; say so" % arg


# ───────── the real solver must report what ran, not what was asked ────────

def test_mode_is_derived_from_what_solved_not_from_the_request():
    body = _body_text("_run_multifragment")
    # The old form asserted quantum purely from the flag.
    assert '"quantum (SQD on hard fragments)" if use_quantum' not in body
    assert "n_quantum > 0" in body, "mode must consult the actual solve count"


def test_a_run_that_solved_nothing_quantum_is_not_a_success():
    body = _body_text("_run_multifragment")
    assert '"success": True,' not in body, (
        "unconditional success is how a total SQD fallback got filed as a "
        "quantum result")
    assert "n_quantum == 0" in body


def test_the_fallback_count_is_reported():
    body = _body_text("_run_multifragment")
    assert "fci_fallback_fragments" in body


def test_the_active_space_electron_count_is_actually_recorded():
    """All 24 historical records had nelec null: `nelec_active` is not a Vayesta
    cluster attribute, so getattr returned None without complaint."""
    body = _body_text("_run_multifragment")
    assert "mf_clus.mol.nelec" in body, (
        "nelec must come from the molecule, not from a getattr that can miss")
    assert '"nelec": [int(nele[0]), int(nele[1])]' in body


def test_a_failed_fragment_records_why():
    body = _body_text("_run_multifragment")
    for key in ("sqd_error", "sqd_traceback", "fci_fallback"):
        assert key in body


# ──────── a dropped gate would sample a different circuit, silently ───────

def test_an_untranslatable_gate_stops_the_sample():
    body = _body_text("_sample_cudaq_local")
    assert "raise RuntimeError" in body, (
        "an unhandled gate used to be skipped, which samples a circuit that is "
        "not the transpiled one and returns a plausible wrong energy")
    assert "not be the transpiled circuit" in body


def test_the_real_solver_still_runs_the_real_sqd_pipeline():
    """Guard against gutting the quantum path while making it honest."""
    body = _body_text("_sqd_fragment_rdms")
    for step in ("ffsim", "UCJOpSpinBalanced", "_sample_cudaq_local",
                 "counts_to_arrays", "recover_configurations",
                 "postselect_and_subsample", "solve_fermion"):
        assert step in body, "%s is part of the SQD solve" % step


def test_the_real_solver_refuses_to_return_without_a_valid_state():
    body = _body_text("_sqd_fragment_rdms")
    assert "SQD produced no valid fragment state" in body


def test_the_hamming_weight_diagnostic_is_recorded():
    """The number that says whether the quantum arm can reach a subspace at all."""
    body = _body_text("_sqd_fragment_rdms")
    assert "quantum_valid_unique" in body
