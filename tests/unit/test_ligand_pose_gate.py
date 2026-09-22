"""The pose gate must discriminate, and must never silently discard molecules.

Two ways this gate could be worthless and still look fine: passing everything
(then it filters nothing and the GPU bill stays), or dropping molecules when it
failed to run (then a real candidate disappears with no record). Both are
tested here against a deliberately corrupted pose set built from the upstream
LDDM KRAS example.

-- MOLEVERA / BIOQL
"""
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

import ligand_pose_gate as PG  # noqa: E402

pytestmark = pytest.mark.skipif(
    not PG.available().get("ready"),
    reason="PoseBusters/RDKit not installed in this interpreter",
)

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures", "poses")
RECEPTOR = os.path.join(FIXTURES, "kras.pdb")
GOOD = os.path.join(FIXTURES, "kras_ref_ligand.sdf")
MIXED = os.path.join(FIXTURES, "kras_mixed_poses.sdf")

needs_fixtures = pytest.mark.skipif(
    not os.path.exists(MIXED), reason="pose fixtures not present")


@needs_fixtures
def test_a_crystal_pose_passes_the_full_receptor_battery():
    r = PG.check_poses(GOOD, RECEPTOR, source="test")
    assert r["checked"] is True
    assert r["battery"] == "dock", "a receptor was given, so clashes must be checked"
    assert r["n_valid"] == 1, r["poses"]


@needs_fixtures
def test_the_gate_actually_rejects_broken_poses():
    """A gate that passes everything is worse than no gate: it buys false
    confidence. The fixture holds one good pose, one translated 40 A out of the
    pocket, and one with collapsed bond lengths."""
    r = PG.check_poses(MIXED, RECEPTOR, source="test")
    assert r["n_poses"] == 3
    assert r["n_valid"] == 1, "only the crystal pose is valid"
    by_index = {p["index"]: p for p in r["poses"]}
    assert "protein-ligand_maximum_distance" in by_index[1]["failed_checks"], \
        "a ligand outside the pocket must fail on distance, not on something else"
    assert "bond_lengths" in by_index[2]["failed_checks"], \
        "collapsed geometry must fail on bond lengths"


@needs_fixtures
def test_without_a_receptor_the_record_says_what_went_unchecked():
    r = PG.check_poses(MIXED, None)
    assert r["battery"] == "mol"
    assert r["receptor_aware"] is False
    assert "NOT checked" in r["battery_note"]
    # The out-of-pocket pose is intramolecularly fine, so it passes here --
    # which is exactly why the note above has to be in the record.
    assert r["n_valid"] == 2


def test_an_unreadable_input_is_unchecked_not_clean():
    r = PG.check_poses("/nonexistent/path/ligands.sdf", None)
    assert r["checked"] is False
    assert r["verdict"] == "unchecked"
    assert r["n_valid"] is None, "0 valid would read as 'checked and all bad'"
    assert r["gate_error"]


def test_a_failed_gate_drops_nothing(monkeypatch, tmp_path):
    """If the check could not run, filtering must pass everything through and
    say so -- discarding molecules on an unchecked gate loses real candidates."""
    monkeypatch.setattr(PG, "check_poses",
                        lambda *a, **k: {"checked": False, "verdict": "unchecked",
                                         "gate_error": "boom", "poses": []})
    out = PG.filter_sdf("whatever.sdf", None, str(tmp_path / "out.sdf"))
    assert out["passthrough"] is True
    assert out["n_written"] is None and out["n_dropped"] is None
    assert "UNFILTERED" in out["passthrough_reason"]


@needs_fixtures
def test_filtering_writes_only_survivors_and_counts_the_drops(tmp_path):
    dest = str(tmp_path / "kept.sdf")
    out = PG.filter_sdf(MIXED, RECEPTOR, dest, source="test")
    assert out["passthrough"] is False
    assert out["n_written"] == 1
    assert out["n_dropped"] == 2
    assert os.path.exists(dest)
    from rdkit import Chem
    kept = [m for m in Chem.SDMolSupplier(dest, sanitize=False) if m is not None]
    assert len(kept) == 1

# MOLEVERA / BIOQL
