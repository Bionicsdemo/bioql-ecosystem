"""Calibrate the derived dose against drugs whose human dose is known.

WHY
    `efficacious_dose` produces a traceable number. Traceable is not the same as
    right. Beacon-2's claim is not that its chain is principled -- it is that on
    20 partner programmes it reaches Spearman 0.61, and that when two designs
    differ by 3x it picks the lower-dose one 81% of the time. Those are
    measurements against known answers. Until we have ours, "comparable
    architecture" is all we can honestly say.

WHAT THIS DOES
    Runs the chain on a reference set of marketed drugs whose approved adult
    dose, potency and plasma protein binding are public, and reports:

        fold error      -- predicted / observed, the number that matters for a dose
        Spearman rho    -- does it rank doses correctly
        pairwise 3x     -- given two drugs whose doses differ by >=3x, does it
                           pick the lower-dose one (Beacon-2's own metric)

    Whatever comes out, comes out. A calibration that only reports itself when
    flattering is not a calibration.

THE REFERENCE SET
    Small, public, and deliberately spread across potency and protein binding so
    the chain is exercised rather than fitted. Every value below is from public
    prescribing information and standard pharmacology references; none is tuned.
    This is a SANITY set, not a validation cohort -- 10 drugs cannot establish
    accuracy, and the report says so.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

# name, SMILES, MW, potency (nM), plasma protein binding (%), approved adult
# daily dose (mg), and what the potency refers to.
REFERENCE_DRUGS: List[Dict[str, Any]] = [
    {"name": "Atorvastatin", "smiles": "CC(C)c1c(C(=O)Nc2ccccc2)c(-c2ccccc2)c(-c2ccc(F)cc2)n1CC[C@@H](O)C[C@@H](O)CC(=O)O",
     "mw": 558.6, "potency_nm": 8.0, "ppb_percent": 98.0, "dose_mg": 20.0,
     "potency_basis": "HMG-CoA reductase IC50",
     # OATP1B1 carries it into hepatocytes; the liver concentration that matters is
     # not the plasma concentration and cannot be derived from it.
     "mechanism": "intracellular_transporter"},
    {"name": "Sildenafil", "smiles": "CCCc1nn(C)c2c1nc(-c1cc(S(=O)(=O)N3CCN(C)CC3)ccc1OCC)[nH]c2=O",
     "mw": 474.6, "potency_nm": 3.7, "ppb_percent": 96.0, "dose_mg": 50.0,
     "potency_basis": "PDE5 IC50",
     # reversible PDE5 inhibition of a plasma-accessible target.
     },
    {"name": "Celecoxib", "smiles": "Cc1ccc(-c2cc(C(F)(F)F)nn2-c2ccc(S(N)(=O)=O)cc2)cc1",
     "mw": 381.4, "potency_nm": 40.0, "ppb_percent": 97.0, "dose_mg": 200.0,
     "potency_basis": "COX-2 IC50",
     # reversible COX-2 inhibition.
     },
    {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
     "mw": 206.3, "potency_nm": 13000.0, "ppb_percent": 99.0, "dose_mg": 1200.0,
     "potency_basis": "COX IC50",
     # reversible COX inhibition; refused instead by the computed
     # attainability gate -- 99% bound with a micromolar IC50 needs 268 mg/L.
     },
    {"name": "Montelukast", "smiles": "CC(C)(O)c1ccccc1CC[C@H](SCC1(CC(=O)O)CC1)c1cccc(/C=C/c2ccc3ccc(Cl)cc3n2)c1",
     "mw": 586.2, "potency_nm": 1.0, "ppb_percent": 99.0, "dose_mg": 10.0,
     "potency_basis": "CysLT1 IC50",
     # reversible CysLT1 antagonism.
     },
    {"name": "Losartan", "smiles": "CCCCc1nc(Cl)c(CO)n1Cc1ccc(-c2ccccc2-c2nn[nH]n2)cc1",
     "mw": 422.9, "potency_nm": 20.0, "ppb_percent": 98.7, "dose_mg": 50.0,
     "potency_basis": "AT1 IC50",
     # the activity is carried by the EXP3174 metabolite, which is far more
     # potent; dosing losartan to the losartan IC50 targets the wrong molecule.
     "mechanism": "prodrug"},
    {"name": "Omeprazole", "smiles": "COc1ccc2[nH]c(S(=O)Cc3ncc(C)c(OC)c3C)nc2c1",
     "mw": 345.4, "potency_nm": 1000.0, "ppb_percent": 95.0, "dose_mg": 20.0,
     "potency_basis": "H+/K+-ATPase IC50",
     # acid-activated in the parietal-cell canaliculus and binds covalently;
     # effect tracks proton-pump turnover, not a trough above the IC50.
     "mechanism": "irreversible"},
    {"name": "Metformin", "smiles": "CN(C)C(=N)NC(N)=N",
     "mw": 129.2, "potency_nm": 1000000.0, "ppb_percent": 0.5, "dose_mg": 1500.0,
     "potency_basis": "AMPK activation, weak",
     # OCT1-concentrated intracellularly to millimolar; also refused by the
     # attainability gate.
     "mechanism": "intracellular_transporter"},
    {"name": "Warfarin", "smiles": "CC(=O)CC(c1ccccc1)c1c(O)c2ccccc2oc1=O",
     "mw": 308.3, "potency_nm": 500.0, "ppb_percent": 99.0, "dose_mg": 5.0,
     "potency_basis": "VKORC1 inhibition",
     # inhibits VKORC1, but the anticoagulant effect comes from clotting factors
     # depleting over days; a single-dose trough does not set it.
     "mechanism": "cumulative"},
    {"name": "Amlodipine", "smiles": "CCOC(=O)C1=C(COCCN)NC(C)=C(C(=O)OC)C1c1ccccc1Cl",
     "mw": 408.9, "potency_nm": 2.0, "ppb_percent": 93.0, "dose_mg": 5.0,
     "potency_basis": "L-type Ca channel IC50",
     # reversible L-type calcium channel blockade.
     },
]


def _as_candidate(drug: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": drug["name"],
        "smiles": drug["smiles"],
        "mw": drug["mw"],
        "pharmacology": {
            "pharmacodynamics": {"potency": {"ic50": drug["potency_nm"]}},
            "pharmacokinetics": {"distribution": {"ppb": drug["ppb_percent"]}},
        },
    }


def _spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    """Rank correlation, ties averaged. None when there is nothing to correlate."""
    n = len(xs)
    if n < 3:
        return None

    def ranks(vals: List[float]) -> List[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (num / den) if den else None


def calibrate(coverage: float = 1.0, modeler=None,
              drugs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Run the chain on the reference set and report how far off it is."""
    import efficacious_dose as ED

    drugs = drugs if drugs is not None else REFERENCE_DRUGS
    rows: List[Dict[str, Any]] = []
    for drug in drugs:
        got = ED.efficacious_dose(_as_candidate(drug), coverage=coverage,
                                  modeler=modeler)
        pred = got.get("dose_mg")
        obs = float(drug["dose_mg"])
        row = {"name": drug["name"], "observed_mg": obs, "predicted_mg": pred,
               "potency_nm": drug["potency_nm"], "ppb_percent": drug["ppb_percent"]}
        if pred is None:
            row["fold_error"] = None
            row["reason"] = got.get("reason")
        else:
            row["fold_error"] = round(max(pred / obs, obs / pred), 2)
        rows.append(row)

    ok = [r for r in rows if r["predicted_mg"] is not None]
    folds = sorted(r["fold_error"] for r in ok)
    within = lambda k: sum(1 for f in folds if f <= k)  # noqa: E731

    rho = _spearman([r["observed_mg"] for r in ok],
                    [r["predicted_mg"] for r in ok]) if len(ok) >= 3 else None

    # Beacon-2's own decision metric: given two drugs whose doses differ by >=3x,
    # is the lower-dose one predicted lower? Correlation can look respectable
    # while the decision it is used for is a coin flip.
    pairs = correct = 0
    for i in range(len(ok)):
        for j in range(i + 1, len(ok)):
            a, b = ok[i], ok[j]
            hi, lo = max(a["observed_mg"], b["observed_mg"]), min(a["observed_mg"], b["observed_mg"])
            if lo <= 0 or hi / lo < 3.0:
                continue
            pairs += 1
            lower_obs = a if a["observed_mg"] < b["observed_mg"] else b
            lower_pred = a if a["predicted_mg"] < b["predicted_mg"] else b
            correct += int(lower_obs["name"] == lower_pred["name"])

    return {
        "n_drugs": len(drugs),
        "n_predicted": len(ok),
        "n_absent": len(drugs) - len(ok),
        "median_fold_error": (folds[len(folds) // 2] if folds else None),
        "geometric_mean_fold_error": (
            round(math.exp(sum(math.log(f) for f in folds) / len(folds)), 2)
            if folds else None),
        "within_3x": within(3.0), "within_10x": within(10.0),
        "worst_fold_error": (folds[-1] if folds else None),
        "spearman_rho": (round(rho, 3) if rho is not None else None),
        "pairwise_3x_total": pairs,
        "pairwise_3x_correct": correct,
        "pairwise_3x_accuracy": (round(correct / pairs, 3) if pairs else None),
        "coverage_multiple": coverage,
        "rows": rows,
        "reference_for_comparison": {
            "beacon2_openadmet_spearman": 0.79,
            "beacon2_openadmet_fold_error": 2.4,
            "beacon2_partner_spearman": 0.61,
            "beacon2_pairwise_3x_accuracy": 0.81,
            "note": ("Published by Inductive for Beacon-2 on different sets. Not a "
                     "like-for-like comparison, and not treated as one: it is here "
                     "so the size of the gap is visible."),
        },
        "honest_limit": (
            "%d marketed drugs cannot establish accuracy. This is a sanity check on "
            "whether the chain is in the right regime, not a validation cohort. The "
            "potency values are literature IC50s against the primary target, which "
            "is not always what sets the clinical dose." % len(drugs)
        ),
    }
