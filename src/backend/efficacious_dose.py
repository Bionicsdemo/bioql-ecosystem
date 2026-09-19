"""Efficacious dose from potency + PBPK — derived, never sampled.

WHY THIS EXISTS
    The platform already has all three pieces an efficacious-dose prediction
    needs: ADMET from trained engines, potency from MM-GBSA / Protenix / FEP,
    and a 14-compartment PBPK model with allometric scaling, CYP kinetics and
    renal clearance (`pbpk_modeler.py`, 1712 lines).

    And the dose it published came from none of them. It came from a generative
    QNN head:

        {"name": "recommended_dose_mg", "range": (5, 1000), "seed": 8005}
        rec_dose = _qnn_val(decoded, "recommended_dose_mg", 200)

    A number sampled from a 5-1000 mg range with a 200 mg fallback. The payload
    already admitted it: "NOT calibrated molecule-specific clinical predictions".

    This module supplies the missing link -- the PK/PD step that turns a potency
    into a target exposure, so the PBPK model can be asked the question it was
    built to answer: what dose reaches that exposure?

THE CHAIN, EXPLICITLY
    1. potency (IC50/EC50/Ki, nM)  ->  target FREE plasma concentration
    2. free -> total, via fraction unbound (fu = 1 - PPB)
    3. target total Cmin  ->  PBPK inverse solve  ->  dose and interval

    Every step is arithmetic or physiology. Nothing is sampled.

WHAT IT REFUSES
    No potency, no unbound fraction, no molecular weight -> no dose. An honest
    null with the reason, never a default. And it will not accept a Kd derived
    from MM-GBSA: single-structure MM-GBSA without entropy overestimates by
    3-5x, and exponentiating it into a Kd amplified that until this platform
    was reporting 0.00 nM. That number cannot drive a dose.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# Potency sources we accept, in order of preference. Each must be an actual
# measured or modelled potency, not a docking score converted into one.
_POTENCY_PATHS = (
    ("pharmacology", "pharmacodynamics", "potency", "ic50"),
    ("pharmacology", "pharmacodynamics", "potency", "ec50"),
    ("pharmacology", "potency_nm"),
)

# Fraction of the target's IC50 the free concentration must exceed at trough.
# 1.0 means "free Cmin at the IC50". Stated, not hidden, because it is the one
# pharmacological assumption in the chain and programmes set it differently.
DEFAULT_COVERAGE = 1.0


def _num(v: Any) -> Optional[float]:
    if isinstance(v, dict):
        v = v.get("value")
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _dig(d: Any, path) -> Any:
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _potency_from_literature(candidate: Dict[str, Any], text: str,
                             measure: str) -> Optional[Dict[str, Any]]:
    """A potency someone else measured, lifted verbatim from text they wrote.

    Reading a stated measurement is legitimate where estimating one is not, but
    only under the guarantee that module enforces: the value returned is
    character-for-character a span of the supplied text, with offsets that
    locate it. If extraction is unavailable, there is simply no potency.
    """
    try:
        import literature_value_extraction as LX
    except ImportError:
        return None
    try:
        r = LX.select_value(text, str(candidate.get("target") or ""), measure=measure)
    except LX.NotInText as exc:
        return {"value_nm": None, "source": None,
                "reason": "Literature extraction refused: %s" % exc}
    if not r.get("available"):
        return None
    return {
        "value_nm": r["value_nm"],
        "source": "literature_text",
        "measure": measure,
        "selected_span": r["selected_span"],
        "source_offsets": r["source_offsets"],
        "confidence": r.get("confidence"),
        "provenance": r["provenance"],
    }


def extract_potency_nm(candidate: Dict[str, Any], *,
                       literature_text: Optional[str] = None,
                       measure: str = "IC50") -> Dict[str, Any]:
    """Find a usable potency in nM, or say why there is none.

    `literature_text` is opt-in: a potency is only read from text a caller
    deliberately supplies, never from something found lying in the record.
    """
    for path in _POTENCY_PATHS:
        v = _num(_dig(candidate, path))
        if v is not None and v > 0:
            return {"value_nm": v, "source": ".".join(path)}

    if literature_text:
        lit = _potency_from_literature(candidate, literature_text, measure)
        if lit is not None:
            return lit

    # Explicitly reject the MM-GBSA-derived Kd, and say why rather than
    # silently falling through: it looks like a potency and is not one.
    kd = _num(candidate.get("predicted_binding_kd_nm"))
    basis = str(candidate.get("predicted_binding_kd_nm_basis") or "")
    if kd is not None:
        return {
            "value_nm": None,
            "source": None,
            "reason": (
                "predicted_binding_kd_nm = %s was found but not used: it is derived "
                "from MM-GBSA (%s), which overestimates binding by 3-5x without an "
                "entropy correction. Exponentiating it into a Kd amplifies that error, "
                "and a dose must not rest on it." % (kd, basis[:80] or "no basis recorded")
            ),
        }
    return {"value_nm": None, "source": None,
            "reason": "No IC50/EC50/Ki found in pharmacology.pharmacodynamics.potency."
                      + ("" if literature_text else
                         " No literature text was supplied to read one from.")}


def extract_fraction_unbound(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Fraction unbound in plasma, from PPB. Free drug is what acts."""
    for path in (("pharmacology", "pharmacokinetics", "distribution", "ppb"),
                 ("admet", "distribution", "plasma_protein_binding_percent"),
                 ("ppb",)):
        v = _num(_dig(candidate, path))
        if v is None:
            continue
        # PPB may arrive as a percent (70.4) or a fraction (0.704).
        pct = v * 100.0 if v <= 1.0 else v
        if not (0.0 <= pct < 100.0):
            continue
        fu = max(1e-4, (100.0 - pct) / 100.0)
        return {"fu": fu, "ppb_percent": round(pct, 3), "source": ".".join(path)}
    return {"fu": None, "reason": "No plasma protein binding found; free fraction unknown."}


# The highest total plasma concentration an orally dosed small molecule sustains
# at trough, in mg/L. An empirical envelope of marketed oral drugs, not a physical
# law: paracetamol runs 10-20 mg/L, valproate 50-100, and high-dose salicylate
# reaches 150-300 only at near-toxic exposure. Above ~100 there is essentially
# nothing held at trough.
#
# The exact value does not drive the outcome, which is why it is defensible. On
# the 10-drug reference set the required trough is 268 mg/L (ibuprofen) and
# 130 mg/L (metformin), then drops to 15.4 (warfarin) -- an 8x gap. Any ceiling
# between roughly 20 and 128 mg/L refuses exactly those two and passes the other
# eight, so this is not a threshold tuned until a test case fell on the right
# side of it.
ATTAINABLE_CMIN_MG_L = 100.0


# Systematic overprediction of the chain, as a single multiplicative factor.
#
# Measured 2026-09-18 on the 10-drug reference set in `dose_calibration.py`,
# after the mechanism and attainability gates remove the six drugs whose
# pharmacology the chain does not model. The four that remain are all
# overpredicted, by 4.1x / 9.7x / 10.0x / 32.9x -- one direction, so a scale
# factor and not structure. The geometric mean of those is 10.7x.
#
# Leave-one-out (fit on three, test on the fourth) gives a median fold error of
# 2.4x, worst 4.5x, two of four within 3x. That is the only number worth
# quoting, and n=4 cannot establish accuracy -- it shows the residual is a
# scale factor, nothing more.
#
# OFF BY DEFAULT. A factor fitted on four molecules must be asked for, with its
# provenance travelling on every dose that uses it.
CALIBRATION_FACTOR = 10.7
CALIBRATION_PROVENANCE = (
    "Divided by a systematic overprediction factor of 10.7x, the geometric mean "
    "bias over 4 marketed drugs (sildenafil, celecoxib, montelukast, amlodipine) "
    "that pass the mechanism and attainability gates. Leave-one-out median fold "
    "error 2.4x, worst 4.5x, n=4. Four molecules cannot establish accuracy; this "
    "corrects a measured one-directional bias and nothing more."
)


def attainability(target_cmin_mg_L: float) -> Dict[str, Any]:
    """Whether the required trough concentration is reachable at all.

    This is the failure mode the chain cannot see from inside. Ibuprofen has 99%
    protein binding and a micromolar COX IC50, so covering that IC50 as free
    drug needs ~1.3 mM total -- about 270 mg/L, two to five times what any oral
    drug sustains. The inverse solve answers anyway, 700x high. The honest
    output is a refusal, and it is COMPUTED from the record rather than
    depending on anyone labelling the molecule.
    """
    ok = target_cmin_mg_L is not None and target_cmin_mg_L <= ATTAINABLE_CMIN_MG_L
    return {
        "attainable": bool(ok),
        "required_cmin_mg_L": target_cmin_mg_L,
        "ceiling_mg_L": ATTAINABLE_CMIN_MG_L,
        "reason": None if ok else (
            "Covering this potency as free drug requires a total trough of "
            "%.4g mg/L, above the ~%.0f mg/L envelope of marketed oral drugs. "
            "The combination of this potency and this protein binding is not "
            "reachable by oral dosing, so there is no efficacious oral dose to "
            "report. A PBPK inverse solve would still return a number."
            % (target_cmin_mg_L or float("nan"), ATTAINABLE_CMIN_MG_L)),
    }


def target_exposure(potency_nm: float, fu: float, mw: float,
                    coverage: float = DEFAULT_COVERAGE,
                    cmax_over_cmin: float = 10.0) -> Dict[str, Any]:
    """Target plasma concentrations, in mg/L, from potency and protein binding.

    C[mg/L] = C[nM] * 1e-9 mol/L * MW[g/mol] * 1000 mg/g = C[nM] * MW * 1e-6
    """
    c_free_nm = potency_nm * coverage
    c_free_mgL = c_free_nm * mw * 1e-6
    c_total_mgL = c_free_mgL / fu
    return {
        "target_free_nm": round(c_free_nm, 4),
        "target_free_mg_L": round(c_free_mgL, 6),
        "target_cmin_mg_L": round(c_total_mgL, 6),
        "target_cmax_mg_L": round(c_total_mgL * cmax_over_cmin, 6),
        "coverage_multiple_of_potency": coverage,
        "attainability": attainability(c_total_mgL),
        "assumption": (
            "Free trough concentration is held at %.2gx the potency; total "
            "concentration is the free target divided by the unbound fraction."
            % coverage
        ),
    }


# Mechanisms for which "free plasma trough >= IC50" is the wrong model. Each
# breaks the chain at a different link, and measured on 10 marketed drugs the
# median fold error inside the assumption was 9.9x against 622x outside it.
_MECHANISM_REFUSALS = {
    "prodrug": ("The potency belongs to the active metabolite, not to this "
                "molecule. Dosing this one to its own IC50 is the wrong target."),
    "irreversible": ("Effect from an irreversible or covalent inhibitor depends "
                     "on the rate of target turnover, not on maintaining a "
                     "trough above the IC50."),
    "covalent": ("Effect from a covalent inhibitor depends on target turnover, "
                 "not on maintaining a trough above the IC50."),
    "intracellular_transporter": (
        "A transporter concentrates this molecule at its target, so the target "
        "site concentration is not the plasma concentration and cannot be "
        "derived from it."),
    "cumulative": ("The effect accumulates over repeated doses through a "
                   "downstream pool, so a single-dose trough does not set it."),
}

MECHANISM_ASSUMPTION = (
    "This dose assumes reversible inhibition of a plasma-accessible target, "
    "with effect set by holding the free trough at or above the potency. No "
    "mechanism was declared on the candidate, so that assumption is stated "
    "rather than verified. It does not hold for prodrugs, covalent or "
    "irreversible inhibitors, transporter-concentrated intracellular targets, "
    "or cumulative pharmacology."
)


def mechanism_gate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse when the candidate declares a mechanism the chain cannot model.

    Read from the record; nothing is inferred from structure. When no mechanism
    is declared the dose proceeds under `MECHANISM_ASSUMPTION`, carried on the
    result so a reader sees what was assumed on their behalf.
    """
    declared = str((candidate or {}).get("mechanism")
                   or (candidate or {}).get("moa") or "").strip().lower()
    if not declared:
        return {"ok": True, "declared": None, "assumption": MECHANISM_ASSUMPTION}
    for key, why in _MECHANISM_REFUSALS.items():
        if key.replace("_", " ") in declared.replace("_", " ") or key in declared:
            return {"ok": False, "declared": declared, "reason": why}
    return {"ok": True, "declared": declared,
            "assumption": MECHANISM_ASSUMPTION}


def detect_modality(candidate: Dict[str, Any]) -> str:
    """small_molecule | peptide | oligonucleotide | biologic | unknown."""
    c = candidate or {}
    seq = str(c.get("sequence") or "").strip().upper()
    declared = str(c.get("modality") or c.get("pipeline") or "").lower()

    if "mrna" in declared or "rna" in declared or "replicon" in declared:
        return "oligonucleotide"
    if seq and set(seq) <= set("AUGC") and len(seq) > 12:
        return "oligonucleotide"
    if seq and set(seq) <= set("ATGC") and len(seq) > 12:
        return "oligonucleotide"
    if c.get("is_peptide") or "peptide" in declared:
        return "peptide"
    if seq and set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") and len(seq) > 4:
        return "peptide"
    if c.get("cdr_h3") or "antibody" in declared or c.get("vh_sequence"):
        return "biologic"
    mw = _num(c.get("mw")) or _num(c.get("molecular_weight_da"))
    if mw and mw > 2000:
        return "biologic"
    if c.get("smiles"):
        return "small_molecule"
    return "unknown"


# Only this modality is inside the PBPK model's domain. The model is built on
# allometric scaling, CYP kinetics, renal clearance and RDKit logP-derived
# tissue partition coefficients -- the small-molecule framework.
SUPPORTED_MODALITIES = frozenset({"small_molecule"})

_MODALITY_REFUSAL = {
    "oligonucleotide": (
        "mRNA and oligonucleotides are not dosed by plasma coverage of a target "
        "IC50. Dose is set by delivery (LNP), transfection efficiency and protein "
        "expression kinetics, in micrograms. MEASURED 2026-09-18: fed an mRNA "
        "construct, this chain returned 43,650 mg — against real vaccine doses of "
        "30-100 ug, wrong by roughly a millionfold. The chain is not applicable "
        "and will not answer."
    ),
    "peptide": (
        "Peptide disposition is governed by proteolysis, renal filtration and, for "
        "larger constructs, FcRn recycling. The PBPK model here uses RDKit logP "
        "partition coefficients and CYP kinetics, which describe small-molecule "
        "disposition. It produces a number for a peptide, but that number has no "
        "validated basis and is withheld."
    ),
    "biologic": (
        "Antibodies and large biologics clear by target-mediated disposition and "
        "FcRn recycling, neither of which this PBPK model represents."
    ),
    "unknown": "Modality could not be determined, so domain cannot be established.",
}


def efficacious_dose(candidate: Dict[str, Any],
                     *,
                     coverage: float = DEFAULT_COVERAGE,
                     route: str = "oral",
                     weight_kg: float = 70.0,
                     literature_text: Optional[str] = None,
                     calibrated: bool = False,
                     modeler=None) -> Dict[str, Any]:
    """Derive an efficacious dose, or return an honest null explaining what is missing."""
    def _null(reason: str, **extra) -> Dict[str, Any]:
        out = {"available": False, "dose_mg": None, "reason": reason,
               "method": "potency -> target exposure -> PBPK inverse solve"}
        out.update(extra)
        return out

    # Domain gate FIRST. A number produced outside the model's domain is worse
    # than no number, because it is indistinguishable from one inside it.
    modality = detect_modality(candidate)
    if modality not in SUPPORTED_MODALITIES:
        return _null(_MODALITY_REFUSAL.get(modality, "Modality out of domain."),
                     modality=modality,
                     supported_modalities=sorted(SUPPORTED_MODALITIES))

    mech = mechanism_gate(candidate)
    if not mech["ok"]:
        return _null("Mechanism %r is outside the model: %s"
                     % (mech["declared"], mech["reason"]),
                     modality=modality, mechanism=mech)

    smiles = (candidate or {}).get("smiles") or ""
    if not smiles:
        return _null("No SMILES; the PBPK model cannot compute descriptors.",
                     modality=modality)

    mw = _num(candidate.get("mw")) or _num(candidate.get("molecular_weight_da"))
    if not mw or mw <= 0:
        return _null("No molecular weight; nM cannot be converted to mg/L.")

    pot = extract_potency_nm(candidate, literature_text=literature_text)
    if pot.get("value_nm") is None:
        return _null(pot.get("reason", "No usable potency."), potency=pot)

    fub = extract_fraction_unbound(candidate)
    if fub.get("fu") is None:
        return _null(fub.get("reason", "No unbound fraction."),
                     potency=pot, protein_binding=fub)

    tgt = target_exposure(pot["value_nm"], fub["fu"], mw, coverage=coverage)

    att = tgt["attainability"]
    if not att["attainable"]:
        return _null(att["reason"], potency=pot, protein_binding=fub,
                     target_exposure=tgt, mechanism=mech)

    if modeler is None:
        try:
            import os
            # A dose is a deterministic PK calculation. The PBPK model is
            # quantum-first at every stage and only falls back once the external
            # provider attempt has failed, which measured at over five minutes
            # per derivation. Take the classical path unless the caller has
            # deliberately asked for quantum.
            os.environ.setdefault("BIOQL_PBPK_CLASSICAL", "1")
            from pbpk_modeler import PBPKModeler
            modeler = PBPKModeler()
        except Exception as exc:
            return _null("PBPK model unavailable (%s)." % exc,
                         potency=pot, protein_binding=fub, target_exposure=tgt)

    try:
        # The dose uses the DETERMINISTIC optimizer. Measured 2026-09-17 on one
        # PK input: classical returned 169.7 mg three times out of three, while
        # QAOA-PK returned 217.7 / 218.7 / 215.9. End to end the divergence was
        # larger still -- 628.6 mg vs 3656.5 mg for the same molecule -- so the
        # answer depended on which substrate happened to respond. A recommended
        # dose cannot do that.
        kwargs = {"smiles": smiles,
                  "target_cmin": tgt["target_cmin_mg_L"],
                  "target_cmax": tgt["target_cmax_mg_L"],
                  "weight_kg": weight_kg}
        try:
            regimen = modeler.optimize_dosing(optimizer="classical", **kwargs)
            optimizer_used = "classical"
        except TypeError:
            # A modeler without the selector. This fallback used to call
            # optimize_dosing() plainly, which on the deployed copy meant
            # QAOA-PK: the code believed it was deterministic while the live
            # path returned 51.2 / 49.3 / 48.8 mg for identical input, and
            # 7.5 mg once the classical path was actually taken. Falling back
            # to the substrate we just refused is not a fallback. Record what
            # ran and let the caller see it rather than assume determinism.
            regimen = modeler.optimize_dosing(**kwargs)
            optimizer_used = "unknown_no_selector"
    except Exception as exc:
        return _null("PBPK inverse solve failed (%s)." % exc,
                     potency=pot, protein_binding=fub, target_exposure=tgt)

    dose = _num((regimen or {}).get("dose_mg"))
    if dose is not None and calibrated:
        dose = dose / CALIBRATION_FACTOR
    if dose is None or dose <= 0:
        return _null("PBPK returned no usable dose.",
                     potency=pot, protein_binding=fub, target_exposure=tgt,
                     regimen=regimen)

    return {
        "available": True,
        "dose_mg": round(dose, 2),
        "interval_h": _num((regimen or {}).get("interval_h")),
        "route": route,
        "weight_kg": weight_kg,
        "method": "potency -> target exposure -> PBPK inverse solve",
        "mechanism": mech,
        "calibrated": bool(calibrated),
        "calibration": (CALIBRATION_PROVENANCE if calibrated else
                        "Uncalibrated. Measured on 4 in-domain marketed drugs "
                        "this chain overpredicts by ~10.7x; pass calibrated=True "
                        "to divide it out."),
        "optimizer": optimizer_used,
        "deterministic": optimizer_used == "classical",
        "potency": pot,
        "protein_binding": fub,
        "target_exposure": tgt,
        "baseline_pk": (regimen or {}).get("baseline_pk"),
        "derivation": (
            "Potency %.4g nM from %s; free target %.4g nM at %.2gx coverage; "
            "unbound fraction %.4g (PPB %.3g%%) gives a total trough target of "
            "%.4g mg/L; the PBPK model was solved inversely for the dose that "
            "reaches it." % (pot["value_nm"], pot["source"], tgt["target_free_nm"],
                             coverage, fub["fu"], fub["ppb_percent"],
                             tgt["target_cmin_mg_L"])
        ),
        "caveat": (
            "This is a model-derived dose, not a clinical prediction. It inherits "
            "the uncertainty of the potency estimate and of the PBPK parameters, "
            "and it has not been calibrated against observed human doses."
        ),
    }
