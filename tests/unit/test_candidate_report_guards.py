"""Candidate-report guards: the 2026-09-15 failures must not come back.

Every test here comes from a failure MEASURED against the live set, not from a
hypothesis. The case that exposed all of them was KRAS-005 (id 0000243a63ed),
whose report declared the molecule "Good" while its own internals said
Category 1 (Fatal), micronucleus positive and clinically disqualified.

The rule running through this file: when something cannot be computed, the
correct answer is to say so. A fabricated number is worse than a gap, because
a gap is visible and a number is believed.

-- MOLEVERA / BIOQL
"""
import importlib.util
import os
import re
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
sys.path.insert(0, BACKEND)

MONOLITH = os.path.join(BACKEND, "script_executor_server.py")
QBP = os.path.join(BACKEND, "quantum_batch_predictor.py")


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _code_only(path):
    """Executable source only: comments and string literals removed.

    The source-level guards must look at code, not at the prose that documents
    what was removed -- the comments and docstrings quote the old formulas on
    purpose, so a future reader understands why they are gone. Without this the
    guard would fire on its own explanation.
    """
    import io
    import tokenize
    out = []
    try:
        with open(path, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                out.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):  # pragma: no cover
        # Never let a tokenizer hiccup turn into a silent pass.
        return _src(path)
    return " ".join(out)


def _without_comment_lines(path):
    """Source with `#` comment lines dropped, string literals kept.

    Needed where the guard looks for a dict literal such as
    `"ld50_mg_kg": 1500`: tokenize-based stripping would remove the key and
    leave the number orphaned, losing the pairing that matters.
    """
    return "\n".join(line for line in _src(path).splitlines()
                      if not line.lstrip().startswith("#"))


def _extract(path, name, stubs=None):
    """Pull one function out of the monolith and run it in isolation.

    The monolith is 35k lines and drags in Flask, RDKit and half the ecosystem,
    so importing it in a unit test is not viable. The function is extracted from
    source: if someone renames or deletes it, this test fails, which is exactly
    what we want.
    """
    src = _src(path)
    start = src.index("def %s(" % name)
    rest = src[start + 1:]
    nxt = re.search(r"\n(?:def |class |@app\.route)", rest)
    end = start + 1 + (nxt.start() if nxt else len(rest))
    ns = dict(stubs or {})
    exec(compile(src[start:end], name, "exec"), ns)
    return ns[name]


def _qbp():
    spec = importlib.util.spec_from_file_location("qbp_guard", QBP)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip("quantum_batch_predictor not importable here: %s" % exc)
    return mod


# ────────────────────────── unit conversion ───────────────────────────────

def test_ld50_is_converted_before_ghs_classification():
    """The root bug: a -log10(mol/kg) value compared against mg/kg thresholds.

    The `ld50_oral` head emits -log10(mol/kg) with a declared range of
    (0.911, 5.24). The GHS thresholds are mg/kg and the first one is <=5, so a
    logarithmic value ALWAYS fell into the first bucket: 95% of the model's
    output range was labelled "Category 1 (Fatal)" by construction.
    """
    m = _qbp()
    # KRAS-005: 4.9768 in log units, MW 1386.3 Da
    mg = m.ld50_log_to_mg_kg(4.9768, 1386.3)
    assert mg == pytest.approx(14.6, abs=0.2), (
        "10**(-4.9768) * 1386.3 * 1000 is 14.6 mg/kg, not 4.98")
    assert m.classify_ghs_acute_oral(mg) == "Category 2 (Fatal)"


def test_the_model_range_no_longer_lands_entirely_in_fatal():
    """With the conversion in place the output spreads across the categories."""
    m = _qbp()
    classes = {m.classify_ghs_acute_oral(m.ld50_log_to_mg_kg(
        0.911 + (5.24 - 0.911) * i / 100.0, 350.0)) for i in range(101)}
    assert len(classes) >= 4, (
        "the whole range used to be Category 1/2 (both 'Fatal'); it should now "
        "cover several classes, got: %s" % sorted(classes))
    assert any("Category 4" in c or "Category 5" in c or "Not classified" in c
               for c in classes), "no molecule could ever leave the lethal range"


def test_without_molecular_weight_no_ld50_is_invented():
    """Without MW the conversion is undefined; a silent default would fake it."""
    m = _qbp()
    assert m.ld50_log_to_mg_kg(4.9768, None) is None
    assert m.ld50_log_to_mg_kg(4.9768, 0) is None
    assert m.ld50_log_to_mg_kg(None, 350.0) is None
    assert "not classified" in m.classify_ghs_acute_oral(None).lower(), (
        "with no data the class has to say it could not be classified")


def test_the_declared_unit_carries_the_minus_sign():
    """`log10(mol/kg)` without the minus was part of what invited the error."""
    src = _src(QBP)
    assert '"-log10(mol/kg)"' in src
    assert re.search(r'"unit":\s*"log10\(mol/kg\)"', src) is None, (
        "some unit string is still missing the minus sign")


# ─────────────────────── fabricated LD50 formulas ─────────────────────────

FORBIDDEN_FORMULAS = (
    # linear, from the monolith: any large polar molecule looked harmless
    r"2000\s*-\s*200\s*\*\s*logp",
    # exponential, from quantum_batch_predictor
    r"0\.5\s*\*\s*logp\s*\+\s*0\.001\s*\*\s*mw\s*\+\s*2\.5",
)


@pytest.mark.parametrize("path", [MONOLITH, QBP])
def test_the_fabricated_ld50_formulas_do_not_return(path):
    """Two copies, two different formulas, 115x apart.

    On KRAS-005 (logP -4.324, MW 1386.44, tPSA 601.44):
        exponential ->    53.02 mg/kg -> DISQUALIFIES
        linear      ->  6106.32 mg/kg -> passes
    The verdict depended on which copy happened to run. Neither was a model,
    and unifying them would not have made them correct: they had to go.
    """
    src = _code_only(path).lower()
    for pattern in FORBIDDEN_FORMULAS:
        assert re.search(pattern, src) is None, (
            "a fabricated LD50 formula reappeared (%s) in %s"
            % (pattern, os.path.basename(path)))


@pytest.mark.parametrize("path", [MONOLITH, QBP])
def test_the_acute_tox_screen_does_not_disqualify_without_measuring(path):
    """With no LD50 from the real model, nothing is disqualified or invented."""
    fn = _extract(path, "check_acute_toxicity_disqualification", stubs={
        "_check_sequence_natural": lambda s: False,
        "_is_natural_amino_acid_peptide": lambda s: False,
    })
    disq, ld50, basis = fn("CCO", "", None)
    assert disq is False
    assert ld50 is None, "no data means no number"
    assert basis["assessed"] is False
    assert basis.get("reason"), "a gap without a reason informs nobody"


@pytest.mark.parametrize("path", [MONOLITH, QBP])
def test_the_screen_uses_the_model_ld50_when_present(path):
    fn = _extract(path, "check_acute_toxicity_disqualification", stubs={
        "_check_sequence_natural": lambda s: False,
        "_is_natural_amino_acid_peptide": lambda s: False,
    })
    tox = {"acute_toxicity": {"ld50_mg_kg": 120.0}}
    disq, ld50, basis = fn("CCO", "", tox)
    assert disq is True and ld50 == 120.0
    assert basis["assessed"] is True
    assert "toxicology.acute_toxicity" in basis["source"]

    tox_ok = {"acute_toxicity": {"ld50_mg_kg": 2500.0}}
    disq2, ld50_2, _ = fn("CCO", "", tox_ok)
    assert disq2 is False and ld50_2 == 2500.0


def test_a_natural_peptide_is_out_of_domain_not_disqualified():
    """LD50_Zhu is trained on small molecules.

    This is the same policy the platform already applies in
    `_apply_peptide_tox_adjustments` and in the biologics N/A.
    """
    fn = _extract(MONOLITH, "check_acute_toxicity_disqualification", stubs={
        "_check_sequence_natural": lambda s: True,
        "_is_natural_amino_acid_peptide": lambda s: True,
    })
    disq, ld50, basis = fn("CC(C)", "FDVRWDFSAED",
                           {"acute_toxicity": {"ld50_mg_kg": 10.0}})
    assert disq is False, "an out-of-domain endpoint cannot disqualify"
    assert ld50 is None
    assert basis["source"] == "not applicable"
    assert "out of domain" in basis["reason"].lower()


# ─────────────── the toxicology fallback does not absolve ─────────────────

def test_the_toxicology_fallback_does_not_certify_safety():
    """The worst failure of all: a crash was reported as a safe molecule.

    When both the quantum engine AND the hybrid failed, the final branch
    returned `"status": "success"` with a complete clean bill of health --
    LD50 1500, Ames negative, hERG low, DILI low, all three organs low and a
    score of 0.75 -- without having evaluated anything. MEASURED: 38 of 80
    stored records carry that `ld50_mg_kg: 1500`, so the branch was taken often.
    """
    src = _without_comment_lines(MONOLITH)
    assert '"ld50_mg_kg": 1500' not in src, (
        "the constant 1500 mg/kg LD50 came back")
    # The full clean profile must not reappear next to a success either.
    pattern = re.compile(
        r'"status":\s*"success".{0,400}?"ld50_mg_kg":\s*\d+', re.S)
    assert pattern.search(src) is None, (
        "there is a branch declaring success with a constant LD50")
    assert "both engines failed" in _src(MONOLITH), (
        "the total-failure branch has to say that it failed")


def test_there_is_no_default_pdb_for_an_unresolved_target():
    """`pdb_id or "5O3L"` attributed a real, specific structure to any target."""
    src = _code_only(MONOLITH)
    assert re.search(r'pdb_info\.get\("pdb_id"\)\s*or\s*"5O3L"', src) is None
    assert "SYNTHETIC_PDB_MARKER" in src, (
        "the poly-alanine placeholder helix has to be marked")
    assert "protein_pdb_is_synthetic" in src


# ──────────────── the safety gate looks at everything ─────────────────────

def _gate():
    return _extract(MONOLITH, "_safety_gate_check")


def test_the_gate_reads_the_ghs_class():
    """50 of 174 candidates were 'Category 1 (Fatal)' with the gate green."""
    gate = _gate()
    passed, flags, sev = gate({
        "toxicology": {"acute_toxicity": {"ghs_class": "Category 1 (Fatal)"}}})
    assert passed is False and sev == "CRITICAL"
    assert any("GHS" in f for f in flags)


def test_the_gate_reads_the_chromosome_damage_assays():
    """It only looked at Ames; micronucleus and chromosome aberration did not exist."""
    gate = _gate()
    for assay in ("micronucleus", "chromosome_aberration"):
        passed, flags, sev = gate({
            "toxicology": {"genotoxicity": {assay: {"result": "Positive",
                                                    "confidence": 0.9}}}})
        assert passed is False, "%s positive cannot pass" % assay
        assert sev == "CRITICAL"


def test_the_gate_picks_up_flags_another_layer_already_raised():
    """KRAS-005's literal failure: safety_gate.flags=[] with scoring.safety_flags full."""
    gate = _gate()
    passed, flags, sev = gate({
        "scoring": {"safety_flags": ["Chromosome aberration positive - genotoxicity risk"]}})
    assert passed is False, (
        "what one pipeline layer declared a risk cannot vanish here")
    assert any("upstream" in f for f in flags)


def test_the_gate_reads_the_clinical_disqualification():
    gate = _gate()
    passed, _, sev = gate({
        "clinical_trial": {"approval_class": "Failed/Toxic",
                           "disqualification_reason": "Fatal acute toxicity"}})
    assert passed is False and sev == "CRITICAL"


def test_the_gate_reads_organ_risk_from_the_block_not_the_flat_field():
    """The flat field can be a placeholder; the payload marks it in _admet_proxy_fields."""
    gate = _gate()
    passed, flags, _ = gate({
        "nephrotoxicity": 0.1,  # placeholder
        "_admet_proxy_fields": ["nephrotoxicity"],
        "toxicology": {"nephrotoxicity_risk": "High"}})
    assert passed is False
    assert any("nephrotox" in f.lower() for f in flags)


def test_an_out_of_domain_signal_neither_disqualifies_nor_absolves():
    """A positive from a model not validated for the modality carries no information.

    Neither for nor against. So it cannot be a hard stop, and it cannot vanish
    leaving a clean PASS behind.
    """
    gate = _gate()
    passed, flags, sev = gate({
        "toxicology": {"genotoxicity": {"micronucleus": {
            "result": "Positive", "confidence": 0.86,
            "method": "QSVM", "out_of_domain": True}}}})
    assert sev == "REVIEW_OUT_OF_DOMAIN", (
        "it cannot end up as PASS: the signal exists even if it does not inform")
    assert any("OUT OF DOMAIN" in f for f in flags)


def test_the_same_finding_is_not_counted_twice_with_opposite_criteria():
    """Micronucleus arrived as soft from the block and as hard from upstream."""
    gate = _gate()
    _, flags, sev = gate({
        "toxicology": {"genotoxicity": {"micronucleus": {
            "result": "Positive", "method": "QSVM", "out_of_domain": True}}},
        "scoring": {"safety_flags": ["Micronucleus test positive - genotoxicity risk"]}})
    assert sev == "REVIEW_OUT_OF_DOMAIN", (
        "the upstream copy cannot undo the out-of-domain marking")
    hard = [f for f in flags if "out of domain" not in f.lower()]
    assert not any("icronucleus" in f for f in hard)


def test_a_clean_candidate_still_passes():
    """A gate that fails everything is as useless as one that passes everything."""
    gate = _gate()
    passed, flags, sev = gate({
        "herg_pic50": 4.0, "dili_score": 0.1, "total_clearance": 20,
        "toxicology": {
            "acute_toxicity": {"ghs_class": "Category 4 (Harmful)"},
            "genotoxicity": {"micronucleus": {"result": "Negative"},
                             "chromosome_aberration": {"result": "Negative"},
                             "carcinogenicity": {"result": "Non-carcinogen"}},
            "nephrotoxicity_risk": "Low", "hepatotoxicity_risk": "Low",
            "cardiotoxicity_risk": "Low"},
        "scoring": {"safety_flags": []}})
    assert passed is True and sev == "PASS" and flags == []


@pytest.mark.parametrize("payload", [
    {}, {"toxicology": None}, {"toxicology": {"acute_toxicity": None}},
    {"clinical_trial": "not a dict"},
    {"toxicology": {"genotoxicity": {"micronucleus": "Positive"}}},
])
def test_the_gate_does_not_throw_on_malformed_payloads(payload):
    """A gate that crashes lets the pipeline through unevaluated."""
    passed, flags, sev = _gate()(payload)
    assert isinstance(passed, bool) and isinstance(flags, list) and sev


# ────────── the candidate class does not contradict safety ────────────────

def _disq():
    return _extract(MONOLITH, "_check_safety_disqualifiers", stubs={
        "_is_ames_positive_check": lambda t: False,
        "_get_herg_ic50": lambda t: 99.0,
        "_is_micronucleus_positive": lambda t: bool(
            str(((t.get("genotoxicity") or {}).get("micronucleus") or {})
                .get("result", "")).lower().startswith("positive")),
        "_is_natural_amino_acid_peptide": lambda s: True,
        "_check_sequence_natural": lambda s: True,
    })


def test_a_lethal_ghs_class_disqualifies_on_its_own():
    """`_check_safety_disqualifiers` never consulted the GHS class at all."""
    _score, klass, _flags, disq = _disq()(
        {"acute_toxicity": {"ghs_class": "Category 1 (Fatal)"}}, 0.9, smiles="pep")
    assert disq is True and klass == "Disqualified"


def test_the_peptide_exemption_does_not_cover_genotoxicity():
    """The waiver is for the carcinogenicity QSVMs, not for a positive assay.

    KRAS-005 was a natural peptide with EXACTLY two genotoxicity flags, and the
    3-flag threshold for peptides let it through as "Good".
    """
    fn = _disq()
    tox = {"genotoxicity": {"micronucleus": {"result": "Positive", "confidence": 0.86},
                            "chromosome_aberration": {"result": "Positive",
                                                      "confidence": 0.95}}}
    _score, klass, flags, disq = fn(tox, 0.789, smiles="pep")
    assert klass != "Good", "a peptide with positive genotoxicity is not 'Good'"
    assert disq is True, "two non-waivable stops disqualify"
    assert len(flags) >= 2


def test_a_single_non_waivable_stop_never_reaches_good():
    fn = _disq()
    tox = {"genotoxicity": {"micronucleus": {"result": "Positive", "confidence": 0.86}}}
    _score, klass, _flags, disq = fn(tox, 0.9, smiles="pep")
    assert disq is False, "one alone does not disqualify automatically"
    assert klass in ("Moderate", "Poor"), (
        "but it cannot read as Good/Excellent either: got %r" % klass)


def test_the_peptide_carcinogenicity_exemption_is_preserved():
    """The legitimate waiver stays alive: its justification is documented."""
    fn = _disq()
    tox = {"genotoxicity": {"carcinogenicity": {"result": "Positive", "confidence": 0.8}}}
    _score, klass, flags, disq = fn(tox, 0.9, smiles="pep")
    assert disq is False
    assert not any("carcinogen" in f.lower() for f in flags)
    assert klass == "Excellent", (
        "with no other stops a natural peptide is not penalised for this")


def test_with_no_toxicology_data_the_class_comes_from_the_score():
    fn = _disq()
    _score, klass, flags, disq = fn(None, 0.8)
    assert disq is False and flags == [] and klass == "Excellent"


# ────────── the structure shown belongs to the candidate ──────────────────

def test_the_structure_block_is_not_inherited_from_another_molecule():
    """4 of 6 KRAS peptides carried the rank-1 candidate's mol_3d.

    On KRAS-005 the mass gave it away: 1386.3 Da over its 11 residues is 126
    Da/residue (coherent); over the inherited peptide's 17 it would be 82,
    impossible for an amino-acid chain.
    """
    code = _code_only(MONOLITH)
    # The check must be USED, not merely defined: renaming the set to
    # `_STRUCTURE_KEYS_DISABLED` would satisfy a substring assertion while
    # silently turning the guard off.
    assert re.search(r"key\s+in\s+_STRUCTURE_KEYS\b", code), (
        "the structure-identity guard is no longer consulted")
    assert "structure_inheritance_blocked" in _src(MONOLITH), (
        "the blocked-inheritance record disappeared")
    src = _src(MONOLITH)
    # The attach loop must not go back to overwriting unconditionally.
    assert re.search(
        r'for key in \["toxicology".{0,900}?\n\s*if key in inner:\s*\n\s*detail\[key\] = inner\[key\]',
        src, re.S) is None, (
        "the loop went back to overwriting the candidate's own data")


def test_the_clinical_screen_is_evaluated_per_candidate():
    """It used to evaluate `candidates[0]` and stamp the verdict on all of them."""
    assert re.search(
        r'is_disq,\s*ld50_val\s*=\s*check_acute_toxicity_disqualification\(lead_smiles\)',
        _code_only(MONOLITH)) is None, (
        "single-molecule evaluation for the whole run came back")
    src = _src(MONOLITH)
    assert "acute_tox_screen" in src
    assert "applies_to" in src, (
        "the run-level block has to say who it describes")


def test_clinical_phases_are_not_zeroed_without_an_assessment():
    """A 0.0% reads as a computed forecast; an absence reads as an absence."""
    src = _src(MONOLITH)
    assert "phase_success_null_reason" in src
    assert re.search(r'"phase1_success":\s*0\.0,\s*\n\s*"phase2_success":\s*0\.0',
                     src) is None, "phases went back to 0.0 on disqualification"
    qsrc = _src(QBP)
    assert "_really_assessed" in qsrc, (
        "phases can only be 0.0 if the screen actually measured something")


# ───────────── a retracted finding stops disqualifying ────────────────────

def test_a_flag_the_pipeline_itself_retracted_is_not_a_hard_stop():
    """KRAS-005: scoring said "Chromosome aberration positive"; the block said Negative.

    The block is right. Clastogenicity by intercalation needs a planar
    polyaromatic system AND lipophilicity; the structure-based correction scores
    0.05 against a 0.20 threshold because logP is -4.32. The flag came from the
    raw QSVM label, before that correction ran. A value the pipeline retracted
    must not keep disqualifying candidates.
    """
    gate = _gate()
    passed, flags, sev = gate({
        "toxicology": {"genotoxicity": {
            "chromosome_aberration": {"result": "Negative", "confidence": 0.5,
                                      "method": "QSVM"}}},
        "scoring": {"safety_flags": ["Chromosome aberration positive - genotoxicity risk"]}})
    assert sev != "CRITICAL", "a retracted flag still disqualified"
    assert any("superseded" in f for f in flags), flags
    hard = [f for f in flags if "superseded" not in f and "out of domain" not in f]
    assert not any("hromosome" in f for f in hard)


def test_a_flag_the_block_still_confirms_remains_a_hard_stop():
    """Supersession must require the block to actually disagree."""
    gate = _gate()
    passed, flags, sev = gate({
        "toxicology": {"genotoxicity": {
            "chromosome_aberration": {"result": "Positive", "confidence": 0.95}}},
        "scoring": {"safety_flags": ["Chromosome aberration positive - genotoxicity risk"]}})
    assert passed is False and sev == "CRITICAL"


def test_an_upstream_flag_with_no_matching_block_stays_hard():
    """Absence of a block is not evidence of retraction."""
    gate = _gate()
    passed, flags, sev = gate({
        "scoring": {"safety_flags": ["Chromosome aberration positive - genotoxicity risk"]}})
    assert passed is False and sev == "CRITICAL"
    assert any(f.startswith("upstream:") for f in flags)
