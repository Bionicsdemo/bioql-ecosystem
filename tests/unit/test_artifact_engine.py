"""The interactive report may not say anything the run does not contain.

Three promises are checked here:
  * every value of the result JSON is accounted for -- shown in a chapter or
    listed in the data annex, never dropped;
  * no sentence carries a number that is not in the run, and no sentence claims
    a picture or a verification that did not happen;
  * what the run could not measure is stated as a gap, in the pipeline's own
    words.

No network, no PyMOL: the mesh builder is replaced by a stub, so these run
anywhere.
"""

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2] / "src" / "backend"
sys.path.insert(0, str(BACKEND))

from artifact_engine import build, facts, narrate  # noqa: E402
from artifact_engine.models import mrna  # noqa: E402

PDB = "\n".join(
    f"ATOM  {i:5d}  CA  ALA A{i:4d}    {i * 3.8:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 {70 + i % 20:5.2f}           C"
    for i in range(1, 9)
)


def fake_mesh(pdb):
    res, kind = __import__("artifact_engine.mesh", fromlist=["x"]).residues(pdb)
    return {
        "scale": 0.01,
        "nv": 6,
        "nt": 2,
        "b64": "",
        "kind": kind,
        "n_res": len(res),
        "center": [0, 0, 0],
        "gz_bytes": 0,
        "resEnd": {i: i + 1 for i in range(len(res))},
        "res": [
            {
                "chain": r["chain"],
                "resi": r["resi"],
                "resn": r["resn"],
                "ss": "L",
                "b": r["b"],
                "p": r["p"],
            }
            for r in res
        ],
    }


def run_json(**over):
    r = {
        "pipeline": "mrna_therapeutic_v1",
        "timestamp": "2026-09-25T00:00:00Z",
        "construct_mode": "monomer",
        "input": {"construct_mode": "monomer", "target_receptors": ["TESTR"], "n_seeds": 1},
        "stages": {
            "1_protein_design": {
                "protein_with_signal_fasta": "MKWVTFISLLFLFSSAYSQVQLVQSGAEVKK",
                "protein_mature_fasta": "QVQLVQSGAEVKK",
                "mature_length_aa": 13,
                "signal_length_aa": 18,
                "monomer_mw_kda": 3.4,
                "mw_method": "Biopython ProtParam",
                "signal_peptide": "MKWVTFISLLFLFSSAYS",
                "signal_type": "albumin",
                "domain_map": {"payload": {"start": 0, "end": 13, "length": 13}},
                "domain_sequences": {"payload": "QVQLVQSGAEVKK"},
            },
            "4_mrna_optimization": {
                "best_cds_sequence": "AUGAAAUGGGUGACCUUCAUCAGCCUGCUGUUCCUGUUCAGCAGCGCCUACAGCCAGGUGCAGCUGGUGCAGAGCGGCGCCGAGGUGAAGAAG",
                "full_mrna_sequence": "",  # filled below
                "utr5": "GGGAAAUAAGAGAGAAAAGAAGAGUAAGAAGAAAUAUAAGAGCCACC",
                "utr3": "GCUGCCUUCUGCUUUGCUGCUGCU",
                "polya_length": 12,
                "cds_length_nt": 93,
                "expression_system": "human",
                "best_cai": 0.88,
                "best_gc": 0.55,
                "best_homopolymer": 4,
                "n_candidates_passing": 1,
                "all_candidates": [{"candidate_id": "CDS-000", "cai": 0.88}],
                "modifications": "Cap1 + m1Psi",
                "length_breakdown_nt": {
                    "utr5": 47,
                    "orf": 93,
                    "utr3": 24,
                    "polya": 12,
                    "sum_check": 176,
                },
            },
            "7_safety_verdict": {
                "verdict": "computational only",
                "immunogenicity": {
                    "mhc_epitope_count": 3,
                    "risk_level": "low",
                    "method": "HistGBM",
                },
            },
        },
        "structure_3d": {"method": "TestFolder", "plddt": 82.5, "pdb": PDB},
        "optimization": {
            "iterations_run": 1,
            "converged_reason": "criteria_met",
            "all_criteria_met": True,
            "final_metrics": {"cai": 0.88},
        },
    }
    s4 = r["stages"]["4_mrna_optimization"]
    s4["full_mrna_sequence"] = (
        s4["utr5"] + s4["best_cds_sequence"] + s4["utr3"] + "A" * s4["polya_length"]
    )
    s4["full_mrna_length_nt"] = len(s4["full_mrna_sequence"])
    for k, v in over.items():
        r[k] = v
    return r


def report(**over):
    return build.build(run_json(**over), mesh_fn=fake_mesh)


# -- the coverage promise --------------------------------------------------------
def test_every_value_of_the_run_is_shown_or_annexed():
    r = run_json()
    p = build.build(r, mesh_fn=fake_mesh)
    assert p["coverage"]["leaves"] == len(facts.flatten(r))
    assert sum(p["coverage"]["per_chapter"].values()) == p["coverage"]["leaves"]


def test_a_value_no_chapter_claims_lands_in_the_annex():
    p = report(surprise_field={"not_claimed_by_anyone": 7})
    paths = [a["path"] for a in p["annex"]]
    assert "surprise_field.not_claimed_by_anyone" in paths
    assert any(a["value"] == 7 for a in p["annex"])


def test_prefix_matching_is_by_token_not_substring():
    assert facts.under("stages.4_mrna_optimization.best_cai", "stages.4_mrna_optimization")
    assert not facts.under("stages.4_mrna_optimization_extra.x", "stages.4_mrna_optimization")
    assert facts.under("a.b[2].c", "a.b[2]")


# -- the honesty promise ---------------------------------------------------------
def test_a_sentence_cannot_carry_a_number_the_run_does_not_have():
    r = run_json()
    del r["stages"]["1_protein_design"]["monomer_mw_kda"]
    p = build.build(r, mesh_fn=fake_mesh)
    said = " ".join(b["es"] for ch in p["chapters"] for b in ch["beats"])
    assert "kDa" not in said, "the mass sentence must disappear with its value"


def test_every_number_in_every_sentence_is_in_the_run():
    r = run_json()
    p = build.build(r, mesh_fn=fake_mesh)
    present = {str(v) for _, v in facts.flatten(r)}
    for ch in p["chapters"]:
        for b in ch["beats"]:
            for path in b["paths"]:
                assert (
                    facts.get(r, path) is not None
                ), f"{ch['id']}: quoted a path that is empty: {path}"
            assert b["paths"] or b["kind"] in (
                "note",
                "check",
                "gap",
            ), f"{ch['id']}: a fact with no source: {b['es'][:60]}"
    assert present  # the run really did have values to quote


def test_a_missing_structure_becomes_a_declared_gap_not_a_description():
    r = run_json()
    r["structure_3d"] = {
        "method": "TestFolder",
        "status": "unavailable",
        "reason": "the folder was offline for this run",
    }
    p = build.build(r, mesh_fn=fake_mesh)
    ch = next(c for c in p["chapters"] if c["id"] == "structure")
    assert ch["status"] == "gap"
    assert all(b["kind"] == "gap" for b in ch["beats"])
    assert "offline" in ch["beats"][0]["es"]
    assert "PyMOL" not in " ".join(b["es"] for b in ch["beats"])


def test_a_verification_is_only_claimed_when_it_actually_passed():
    r = run_json()
    r["stages"]["4_mrna_optimization"][
        "best_cds_sequence"
    ] = "AUGAAAUAA"  # no longer the designed protein
    p = build.build(r, mesh_fn=fake_mesh)
    said = " ".join(b["es"] for ch in p["chapters"] for b in ch["beats"])
    assert "devuelve exactamente la proteína diseñada" not in said
    assert next(c for c in p["checks"] if c["id"] == "translation")["ok"] is False


def test_the_length_arithmetic_is_recomputed_not_trusted():
    r = run_json()
    r["stages"]["4_mrna_optimization"]["length_breakdown_nt"]["orf"] = 999
    p = build.build(r, mesh_fn=fake_mesh)
    assert next(c for c in p["checks"] if c["id"] == "lengths")["ok"] is False
    said = " ".join(b["es"] for ch in p["chapters"] for b in ch["beats"])
    assert "suman exactamente" not in said


def test_gaps_quote_the_pipelines_own_reason():
    r = run_json()
    r["rna_3d"] = {
        "n_folded": 0,
        "skipped": [{"name": "5'UTR", "reason": "backend unavailable"}],
        "honest_note": "RNAPro backend unavailable; no structure fabricated.",
    }
    p = build.build(r, mesh_fn=fake_mesh)
    ch = next(c for c in p["chapters"] if c["id"] == "rna3d")
    assert any("fabricated" in b["es"] or "unavailable" in b["es"] for b in ch["beats"])


# -- the scenes are made of the run's own data --------------------------------------
def test_the_transcript_scene_finds_the_real_regions():
    r = run_json()
    sc = mrna.scene_transcript(r)
    names = [x["name"] for x in sc["regions"]]
    assert names == ["5'UTR", "CDS", "3'UTR", "poly(A)"]
    assert sc["seq"][sc["regions"][1]["start"] :][:3] == "AUG"
    assert sc["regions"][-1]["end"] == len(sc["seq"])


def test_translation_is_derived_from_the_runs_own_cds():
    sc = mrna.scene_translation(run_json())
    assert sc["identical"] is True
    assert sc["protein"] == "MKWVTFISLLFLFSSAYSQVQLVQSGAEVKK"
    assert sc["n_codons"] == 31


def test_the_report_refuses_a_pipeline_it_has_no_model_for():
    with pytest.raises(ValueError, match="no artifact model"):
        build.build({"pipeline": "something_else", "data": 1}, mesh_fn=fake_mesh)


def test_the_payload_is_json_and_carries_the_whole_result():
    p = report()
    s = json.dumps(p, default=str)
    assert json.loads(s)["result"] == run_json()
    assert p["digest"] and len(p["digest"]) == 16


# -- the small-molecule model ---------------------------------------------------------
from artifact_engine import molecule as MOL  # noqa: E402
from artifact_engine.models import small_molecule as SM  # noqa: E402

MOLBLOCK = """water
  test

  3  2  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 O   0  0
    0.7570    0.5860    0.0000 H   0  0
   -0.7570    0.5860    0.0000 H   0  0
  1  2  1  0
  1  3  1  0
M  END
"""


def test_a_mol_block_is_read_as_real_atoms_and_bonds():
    m = MOL.parse(MOLBLOCK)
    assert m["n_atoms"] == 3 and m["n_bonds"] == 2
    assert m["counts"] == {"O": 1, "H": 2} and m["heavy"] == 1
    assert all(len(a["p"]) == 3 for a in m["atoms"])
    assert MOL.parse("not a mol block") is None


def small_molecule_run(**over):
    r = {
        "pipeline": "CUSTOM_MOLECULE",
        "timestamp": "2026-09-25T00:00:00Z",
        "target_name": "TESTR",
        "molecule": {"smiles": "O"},
        "stages": {
            "0_molecule_analysis": {
                "properties": {
                    "formula": "H2O",
                    "molecular_weight": 18.02,
                    "num_heavy_atoms": 1,
                    "num_rings": 0,
                    "num_aromatic_rings": 0,
                    "num_stereocenters": 0,
                    "num_rotatable_bonds": 0,
                    "tpsa": 20.2,
                    "logp": -0.6,
                },
                "drug_likeness": {"lipinski_violations": 0, "brenk_alerts": 0, "pains_alerts": 0},
                "detected_motifs": ["hydroxyl"],
            },
            "7_3d_structure": {"mol_block": MOLBLOCK, "method": "RDKit MMFF94"},
            "8_scoring": {
                "composite_score": 0.5,
                "score_breakdown": {
                    "admet": {"score": 0.5, "weight": 0.6, "weighted": 0.3},
                    "tox": {"score": 0.5, "weight": 0.4, "weighted": 0.2},
                },
                "drug_candidate_class": "Good",
            },
        },
    }
    for k, v in over.items():
        r[k] = v
    return r


def test_the_formula_is_checked_against_the_3d_block():
    p = build.build(small_molecule_run(), mesh_fn=fake_mesh)
    assert next(c for c in p["checks"] if c["id"] == "formula")["ok"] is True
    r = small_molecule_run()
    r["stages"]["0_molecule_analysis"]["properties"]["formula"] = "C6H6"
    p2 = build.build(r, mesh_fn=fake_mesh)
    assert next(c for c in p2["checks"] if c["id"] == "formula")["ok"] is False


def test_a_composite_that_does_not_match_its_parts_is_said_out_loud():
    ok = build.build(small_molecule_run(), mesh_fn=fake_mesh)
    said = " ".join(b["es"] for ch in ok["chapters"] for b in ch["beats"])
    assert "la suma ponderada de las partes da exactamente" in said
    assert "no suman esa nota" not in said

    r = small_molecule_run()
    r["stages"]["8_scoring"]["composite_score"] = 0.42  # parts still add to 0.5
    bad = build.build(r, mesh_fn=fake_mesh)
    said = " ".join(b["es"] for ch in bad["chapters"] for b in ch["beats"])
    assert "no suman esa nota" in said, "the page must state the discrepancy"
    assert "la suma ponderada de las partes da exactamente" not in said
    assert next(c for c in bad["checks"] if c["id"] == "composite")["ok"] is False


def test_each_pipeline_gets_its_own_model():
    assert SM.matches(small_molecule_run()) and not mrna.matches(small_molecule_run())
    assert mrna.matches(run_json()) and not SM.matches(run_json())


# -- the peptide model ------------------------------------------------------------------
from artifact_engine.models import peptide as PEP  # noqa: E402


def peptide_run(**over):
    r = {
        "pipeline": "PEPTIDE_DISCOVERY",
        "timestamp": "2026-09-25T00:00:00Z",
        "target": "TESTR",
        "indication": "test",
        "n_candidates": 1,
        "optimize_for": "binding",
        "quantum_backend": "AerSimulator",
        "on_real_quantum_hardware": False,
        "pipeline_architecture": "Generate -> Evaluate -> Optimize",
        "stages": {
            "2_quantum_generation": {
                "candidates_generated": 1,
                "peptides": [{"sequence": "ACDKFG", "source": "test"}],
            },
            "3_variant_optimization": {
                "total_variants": 1,
                "variants": [{"original": "ACDKFG", "optimized": "ACDRFG", "score": 0.7}],
            },
            "11_scoring": {
                "composite_score": 0.6,
                "peptide_bonus": 0.1,
                "drug_candidate_class": "Good",
                "score_breakdown": {
                    "admet": {"score": 0.5, "weight": 0.6, "weighted": 0.3},
                    "tox": {"score": 0.5, "weight": 0.4, "weighted": 0.2},
                },
            },
        },
        "candidates": [
            {
                "rank": 1,
                "sequence": "ACDRFG",
                "original_sequence": "ACDKFG",
                "optimization_score": 0.7,
                "mutations": ["K4R"],
                "molecular_weight_da": 650.7,
                "net_charge": 1,
                "serum_half_life_hours": 5.0,
                "protease_resistance": "HIGH",
                "aggregation_risk": "LOW",
            }
        ],
        "optimization": {"iterations": 1, "converged": True, "improvement_pct": 0.0},
    }
    r["best_candidate"] = dict(r["candidates"][0])
    for k, v in over.items():
        r[k] = v
    return r


def test_mutations_are_rederived_from_the_sequences_not_trusted():
    assert [c["label"] for c in PEP.diff("ACDKFG", "ACDRFG")] == ["K4R"]
    p = build.build(peptide_run(), mesh_fn=fake_mesh)
    assert next(c for c in p["checks"] if c["id"] == "mutations")["ok"] is True

    r = peptide_run()
    r["best_candidate"]["mutations"] = ["K9W"]  # a label that does not match the sequences
    p2 = build.build(r, mesh_fn=fake_mesh)
    assert next(c for c in p2["checks"] if c["id"] == "mutations")["ok"] is False
    said = " ".join(b["es"] for ch in p2["chapters"] for b in ch["beats"])
    assert "recalculados comparando" not in said


def test_the_peptide_bonus_is_part_of_the_composite_check():
    p = build.build(peptide_run(), mesh_fn=fake_mesh)  # 0.3 + 0.2 + 0.1 == 0.6
    assert next(c for c in p["checks"] if c["id"] == "composite")["ok"] is True
    r = peptide_run()
    r["stages"]["11_scoring"]["peptide_bonus"] = 0.0
    p2 = build.build(r, mesh_fn=fake_mesh)
    assert next(c for c in p2["checks"] if c["id"] == "composite")["ok"] is False


def test_three_models_each_match_only_their_own_pipeline():
    runs = {"mrna": run_json(), "sm": small_molecule_run(), "pep": peptide_run()}
    models = {"mrna": mrna, "sm": SM, "pep": PEP}
    for name, run in runs.items():
        hit = [n for n, m in models.items() if m.matches(run)]
        assert hit == [name], f"{name} matched {hit}"


# -- the contract every model must keep, including ones added later ----------------------
import re  # noqa: E402

ARTIFACTS = Path("~/.bioql/artifacts").expanduser()

# What an unresolved template reference looks like, as opposed to a brace the data
# itself carries: a conformal prediction set written "{0,1}" is a value, not a field.
_UNRESOLVED = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*[.:\[\]0-9A-Za-z_]*(?:\|[a-z0-9]+)?\??\}")


def test_every_discovered_model_declares_the_whole_contract():
    assert build.MODELS, "no models discovered"
    for m in build.MODELS:
        assert isinstance(m.PIPELINE, str) and m.PIPELINE
        assert set(m.TITLE) >= {"es", "en"}
        for fn in ("matches", "unwrap", "subject", "chapters", "mesh_targets"):
            assert callable(getattr(m, fn)), f"{m.PIPELINE}: {fn} is not callable"
        assert isinstance(getattr(m, "ALIASES", {}), dict)
    assert not build.discover.skipped, f"a model file failed to load: {build.discover.skipped}"


def _reference_runs():
    """One saved run per discovered pipeline, when this machine has them."""
    if not ARTIFACTS.is_dir():
        return {}
    by_pipeline = {}
    for d in sorted(ARTIFACTS.iterdir()):
        f = d / "result.json"
        if not f.is_file() or f.stat().st_size > 8_000_000:
            continue
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        for m in build.MODELS:
            try:
                if m.matches(r):
                    prev = by_pipeline.get(m.PIPELINE)
                    if prev is None or f.stat().st_size > prev[1]:
                        by_pipeline[m.PIPELINE] = (r, f.stat().st_size)
                    break
            except Exception:
                continue
    return {k: v[0] for k, v in by_pipeline.items()}


REFERENCE = _reference_runs()


@pytest.mark.skipif(not REFERENCE, reason="no saved runs on this machine")
def test_no_two_models_claim_the_same_run():
    for pipeline, run in REFERENCE.items():
        hits = [m.PIPELINE for m in build.MODELS if m.matches(run)]
        assert hits == [pipeline], f"{pipeline} also matched {hits}"


@pytest.mark.skipif(not REFERENCE, reason="no saved runs on this machine")
def test_every_model_renders_its_run_without_overclaiming():
    """The rules, checked against every pipeline this machine has data for."""
    for pipeline, run in REFERENCE.items():
        p = build.build(run, mesh_fn=fake_mesh)
        r = p["result"]
        drawn = set(p["meshes"])
        passed = {c["id"] for c in p["checks"] if c.get("ok")}
        for ch in p["chapters"]:
            for b in ch["beats"]:
                where = f"{pipeline}/{ch['id']}"
                for path in b["paths"]:
                    assert facts.get(r, path) is not None, f"{where}: quoted an empty path {path}"
                assert b["paths"] or b["kind"] in (
                    "note",
                    "check",
                    "gap",
                ), f"{where}: a fact with no source: {b['es'][:70]}"
                assert b["es"] and b["en"], f"{where}: a beat missing a language"
                for text in (b["es"], b["en"], *(b.get("tech") or {}).values()):
                    left = _UNRESOLVED.search(text)
                    assert (
                        not left
                    ), f"{where}: an unresolved field reached the page: {left.group(0) if left else ''}"
                for note in ch["scene"].get("annotations") or []:
                    assert ch["scene"].get("mesh") in drawn or note.get(
                        "pos"
                    ), f"{where}: an annotation with no structure behind it"
        assert p["coverage"]["leaves"] == len(facts.flatten(r))
        assert sum(p["coverage"]["per_chapter"].values()) == p["coverage"]["leaves"]
        # a sentence may only say "checked" when a check of that name really passed
        for ch in p["chapters"]:
            for b in ch["beats"]:
                if b["kind"] == "check":
                    assert passed, f"{pipeline}/{ch['id']}: a check sentence with no passing check"


def test_a_non_finite_number_cannot_blank_the_page():
    """A NaN in the run must not reach the page as the bare token `NaN`.

    `json.dumps` writes NaN and Infinity unquoted by default; no browser's JSON.parse
    accepts them, so one of them anywhere in a result threw before the first line of
    the renderer ran and the reader got a blank screen. The modality comparison run
    carries exactly that, and its report was unreadable for it.
    """
    import json as _json

    from artifact_engine import render as _render

    payload = {
        "a": float("nan"),
        "b": [1.0, float("inf"), {"c": float("-inf")}],
        "d": {"e": 2.5},
    }
    text = _render._safe_json(payload)
    assert "NaN" not in text and "Infinity" not in text
    back = _json.loads(text)  # the browser's parser is this strict too
    assert back["a"] is None
    assert back["b"] == [1.0, None, {"c": None}]
    assert back["d"]["e"] == 2.5
