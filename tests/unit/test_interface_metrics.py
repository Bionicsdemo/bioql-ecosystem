"""ipTM is not iPAE. Different units, opposite direction.

  ipTM  0-1, dimensionless, HIGHER is better  (interface predicted TM-score)
  iPAE  Angstroms,          LOWER  is better  (interface predicted aligned error)

One site assigned `best_ipae = best_iptm`, and both consumers acted on it:
`min(best_ipaes)` selects the lowest value -- correct for an error metric, so it
picked the WORST binder -- and the UI colours the figure green below 10 A while
labelling it "Lower = better", so an ipTM of ~0.8 rendered every binder as good.

Source-level guards, because the writer lives in a 36k-line module that cannot
be imported without starting a Flask app.

-- MOLEVERA / BIOQL
"""
import os
import re

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
SERVER = os.path.join(BACKEND, "script_executor_server.py")
FRONTEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "frontend", "src")
PANEL = os.path.join(FRONTEND, "components", "panels", "ResultsPanel.tsx")

with open(SERVER, encoding="utf-8") as _fh:
    SERVER_TEXT = _fh.read()


# ───────────────── the two metrics must not be interchanged ────────────────

def test_no_iptm_value_is_assigned_to_an_ipae_field():
    """The bug, pinned by shape rather than by one literal line."""
    bad = re.findall(r'["\']([a-z_]*ipae[a-z_]*)["\']\s*:\s*([a-z_]*iptm[a-z_]*)\b',
                     SERVER_TEXT, re.IGNORECASE)
    assert bad == [], (
        "an ipTM value is being written into an iPAE field: %r. ipTM is 0-1 and "
        "higher is better; iPAE is in Angstroms and lower is better." % bad)


def test_no_ipae_value_is_assigned_to_an_iptm_field():
    """The same confusion in the other direction."""
    bad = re.findall(r'["\']([a-z_]*iptm[a-z_]*)["\']\s*:\s*([a-z_]*ipae[a-z_]*)\b',
                     SERVER_TEXT, re.IGNORECASE)
    assert bad == []


def test_the_binder_path_reports_iptm_under_its_own_name():
    """Nothing is lost by the fix: the ipTM is still reported, correctly named."""
    assert '"best_iptm": best_iptm' in SERVER_TEXT


def test_the_binder_path_declares_ipae_absent_with_a_reason():
    i = SERVER_TEXT.find('"best_iptm": best_iptm')
    assert i > 0
    window = SERVER_TEXT[max(0, i - 1200):i]
    assert "iPAE is not ipTM" in window, (
        "the absent iPAE must say why it is absent")
    assert 'units="A"' in window, "iPAE is in Angstroms; the unit must travel"


def test_every_ipae_null_declares_angstroms():
    """A unitless error metric is how one gets compared against the wrong scale."""
    for m in re.finditer(r'"best_ipae":\s*_null\((.{0,400}?)\)\.to_dict\(\)',
                         SERVER_TEXT, re.S):
        assert 'units="A"' in m.group(1), m.group(1)[:120]


# ──────────── the consumers assume a direction; state it in code ───────────

def test_the_aggregator_still_takes_the_minimum():
    """min() is RIGHT for iPAE -- lower is better. It was only wrong because the
    value was not an iPAE. The fix must not flip the aggregation."""
    assert "min(best_ipaes)" in SERVER_TEXT


def test_the_ui_threshold_is_documented_as_angstroms():
    with open(PANEL, encoding="utf-8") as fh:
        panel = fh.read()
    i = panel.find("Lower = better")
    assert i > 0, "the iPAE card should state its direction"
    window = panel[max(0, i - 1400):i]
    assert "10" in window and "20" in window, (
        "the green/yellow/red thresholds are Angstrom cutoffs")
    assert "Å" in window or "Angstrom" in window or "A)" in window, (
        "the card must name its unit, or a dimensionless score will be judged "
        "against an Angstrom threshold again")
