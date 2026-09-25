"""
Artifact model for the CRISPR editor design pipeline (`crispr_editor_design`).

This pipeline does not fold a complex and does not dock anything, so the report
follows what it actually does: it picks a nuclease and says where that sequence
came from, it adds up whether the cassette fits in an AAV, it optimises the
codons, it tries to design guide RNAs, it reads the target locus against a
regulatory model of the tissue, and it runs a quantum cell simulation to guess
what the edit does to the gene network.

Several of those steps can come back empty, and this run is one where they do.
The page therefore spends as much text on what was NOT measured as on what was,
always in the pipeline's own words, and the checks below recompute the run's own
arithmetic -- which is how four internal contradictions in the reference run
surfaced: guides that do not exist but are counted by the regulatory module, a
structure that "failed to fold" yet reports 422 folded residues, a gene listed
as up-regulated whose own change is -1.0, and small-molecule ADMET scored for a
gene-editing payload with an empty SMILES.

There is no PDB in this result, so there is no cartoon: that absence is a
declared gap, not a placeholder picture.

MOLEVERA / BIOQL
"""

from typing import Any, Dict, List, Optional

from .. import facts as F

PIPELINE = "crispr_editor_design"
TITLE = {"es": "Editor CRISPR", "en": "CRISPR editor"}

SP = "sequence_provenance"
AV = "aav_fit"
ST = "structure"
CM = "codon_metrics"
OT = "offtarget"
MX = "mechanism"
SITE = "edit_site"
DS = "delivery_safety"
PX = "pharmacology_context"
CC = "clinical_context"
VD = "validation"
RG = "regulatory"
Q = "quantum_cell_validation"
CS = f"{Q}.cell_simulation"
QC = f"{CS}.quantum_compute"
QM = f"{CS}.quantum_metadata"
VS = f"{Q}.validations"
BIO = f"{VS}.biological_activity"
GEN = f"{VS}.genomics"
MET = f"{VS}.metabolic_route"
TOX = f"{VS}.toxicology"
PHA = f"{VS}.pharmacology"

ALIASES = {
    "sp": SP,
    "av": AV,
    "st": ST,
    "cm": CM,
    "ot": OT,
    "mx": MX,
    "site": SITE,
    "ds": DS,
    "px": PX,
    "cc": CC,
    "vd": VD,
    "rg": RG,
    "q": Q,
    "cs": CS,
    "qc": QC,
    "qm": QM,
    "bio": BIO,
    "gen": GEN,
    "met": MET,
    "tox": TOX,
    "pha": PHA,
}

# Keys a guide record may use for its spacer, and keys a run may use for the
# genomic window the guides were cut from. Both lists exist so the locus check
# below works on runs richer than this one without guessing a schema.
_SPACER_KEYS = ("spacer", "protospacer", "sequence", "seq", "guide_seq", "guide_sequence")
_LOCUS_PATHS = (
    "target_locus_sequence",
    "locus_sequence",
    "edit_site.locus_sequence",
    "edit_site.target_locus_sequence",
    "edit_site.sequence",
    "input.target_locus_sequence",
    "offtarget.target_sequence",
)
_PDB_PATHS = ("structure.pdb", "structure.pdb_string", "structure.cif", "structure.structure_pdb")

_COMPL = str.maketrans("ACGTU", "TGCAA")


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    if not isinstance(r, dict):
        return False
    if str(r.get("pipeline", "")).startswith("crispr"):
        return True
    # A run that lost its pipeline id is still this one if it carries the three
    # blocks only this pipeline writes.
    return (
        isinstance(r.get(AV), dict)
        and isinstance(r.get(MX), dict)
        and ("guides" in r or "guide_note" in r)
        and "editor" in r
    )


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        inner = result["result"]
        if "editor" in inner or str(inner.get("pipeline", "")).startswith("crispr"):
            return inner
    return result


def subject(r: Dict[str, Any]) -> str:
    bits = [str(r.get("editor") or "").strip(), str(r.get("target_gene") or "").strip()]
    head = " → ".join(b for b in bits if b)
    delivery = str(r.get("delivery") or "").strip()
    return f"{head} · {delivery}" if head and delivery else (head or delivery)


# ── things recomputed from the run, used by both scenes and checks ────────────────
def _num(x: Any) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def spacers(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every designed guide with a readable spacer, and where it came from."""
    out = []
    for i, g in enumerate(r.get("guides") or []):
        if not isinstance(g, dict):
            continue
        for k in _SPACER_KEYS:
            v = g.get(k)
            if isinstance(v, str) and len(v) >= 12 and F.seq_kind(v, min_len=12) in ("dna", "rna"):
                out.append({"i": i, "key": k, "seq": v.upper().replace("U", "T"), "guide": g})
                break
    return out


def locus(r: Dict[str, Any]) -> Optional[str]:
    for p in _LOCUS_PATHS:
        v = F.get(r, p)
        if isinstance(v, str) and F.seq_kind(v, min_len=30) in ("dna", "rna"):
            return v.upper().replace("U", "T")
    return None


def revcomp(s: str) -> str:
    return s.translate(_COMPL)[::-1]


def track_rows(r: Dict[str, Any], i: int) -> List[Dict[str, Any]]:
    """The regulatory track families scored at locus `i`, with their own numbers."""
    rows = []
    for name, t in (F.get(r, f"{RG}.guides[{i}].tracks") or {}).items():
        if not isinstance(t, dict):
            continue
        rows.append(
            {
                "name": str(name),
                "ratio": _num(t.get("enrichment_ratio")),
                "signal": _num(t.get("signal_at_site")),
                "window": _num(t.get("window_mean")),
                "n_tracks": t.get("n_tracks"),
                "named": len(t.get("track_names") or []),
                "resolution": t.get("resolution_bp"),
            }
        )
    return rows


def domain_sources(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Each headline domain score next to the raw signal it is supposed to restate."""
    tox_risk = _num(F.get(r, f"{Q}.toxicity_risk_honest.value"))
    met_dis = _num(F.get(r, f"{MET}.metabolic_disruption_score"))
    return [
        {
            "name": "activity",
            "score": _num(F.get(r, f"{Q}.domain_scores.activity")),
            "from": _num(F.get(r, f"{BIO}.activity_score")),
            "path": f"{BIO}.activity_score",
        },
        {
            "name": "metabolic_safety",
            "score": _num(F.get(r, f"{Q}.domain_scores.metabolic_safety")),
            "from": None if met_dis is None else 1.0 - met_dis,
            "path": f"{MET}.metabolic_disruption_score",
        },
        {
            "name": "genomic_stability",
            "score": _num(F.get(r, f"{Q}.domain_scores.genomic_stability")),
            "from": _num(F.get(r, f"{GEN}.network_stability")),
            "path": f"{GEN}.network_stability",
        },
        {
            "name": "toxicology_safe",
            "score": _num(F.get(r, f"{Q}.domain_scores.toxicology_safe")),
            "from": None if tox_risk is None else 1.0 - tox_risk,
            "path": f"{Q}.toxicity_risk_honest.value",
        },
    ]


def contradicted_directions(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Genes the run files under one direction while its own change says the other."""
    changes = F.get(r, f"{CS}.gene_expression_changes") or {}
    dirs = F.get(r, f"{CS}.gene_expression_directions") or {}
    bad = []
    for listed, want in (("genes_upregulated", 1), ("genes_downregulated", -1)):
        for gene in F.get(r, f"{CS}.{listed}") or []:
            if not isinstance(gene, str) or "." in gene or "[" in gene:
                continue
            ch = _num(changes.get(gene))
            d = dirs.get(gene)
            if ch is None:
                continue
            said = "up" if want > 0 else "down"
            if (ch > 0) != (want > 0) or (isinstance(d, str) and d not in ("none", said)):
                bad.append({"gene": gene, "listed": listed, "said": said, "change": ch, "dir": d})
    return bad


# ── scenes ────────────────────────────────────────────────────────────────────────
def scene_cover(r: Dict[str, Any]) -> Dict[str, Any]:
    stats = []

    def stat(es: str, en: str, value: Any, unit: str, path: str) -> None:
        if value is not None:
            stats.append({"es": es, "en": en, "value": value, "unit": unit, "path": path})

    stat(
        "editor",
        "editor",
        F.get(r, f"{AV}.editor_aa_length"),
        "aa",
        f"{AV}.editor_aa_length",
    )
    stat(
        "carga AAV",
        "AAV payload",
        F.get(r, f"{AV}.estimated_total_payload_bp"),
        "bp",
        f"{AV}.estimated_total_payload_bp",
    )
    stat("guías diseñadas", "guides designed", len(r.get("guides") or []), "", "guides")
    stat("loci puntuados", "loci scored", F.get(r, f"{RG}.n_scored"), "", f"{RG}.n_scored")
    stat(
        "puntuación global",
        "overall score",
        F.get(r, f"{Q}.overall_score"),
        "",
        f"{Q}.overall_score",
    )
    return {
        "type": "cover",
        "stats": stats,
        "images": [
            {"title": v.get("title"), "key": k}
            for k, v in (r.get("visualizations") or {}).items()
            if isinstance(v, dict)
        ],
    }


def scene_payload(r: Dict[str, Any]) -> Dict[str, Any]:
    """Every cassette component against the one real limit the run declares."""
    limit = _num(F.get(r, f"{AV}.aav_packaging_limit_bp"))
    rules = []
    if limit:
        for name, v in (F.get(r, f"{AV}.components_bp") or {}).items():
            n = _num(v)
            if n is not None:
                rules.append(
                    {
                        "name": str(name).replace("_bp_est", "").replace("_bp", ""),
                        "value": n,
                        "limit": limit,
                        "op": "<=",
                        "pass": n <= limit,
                    }
                )
        total = _num(F.get(r, f"{AV}.estimated_total_payload_bp"))
        if total is not None:
            rules.append(
                {
                    "name": "total",
                    "value": total,
                    "limit": limit,
                    "op": "<=",
                    "pass": total <= limit,
                }
            )
    return {
        "type": "rules",
        "rules": rules,
        "violations": [x["name"] for x in rules if not x["pass"]],
    }


def scene_codons(r: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    cai, gc = _num(F.get(r, f"{CM}.cai_estimate")), _num(F.get(r, f"{CM}.gc_fraction"))
    if cai is not None:
        items.append(
            {
                "group": "codons",
                "name": f"CAI {cai:.3f}",
                "value": cai,
                "label": "codon adaptation index",
                "unit": "",
                "note": "1.0 = always the most frequent synonymous codon",
            }
        )
    if gc is not None:
        items.append(
            {
                "group": "codons",
                "name": f"GC {gc * 100:.1f}%",
                "value": gc,
                "label": "GC fraction",
                "unit": "",
                "note": "fraction of G or C bases in the coding sequence",
            }
        )
    stats = []
    for es, en, path, unit in (
        ("CDS", "CDS", f"{CM}.cds_length_nt", "nt"),
        ("homopolímero", "homopolymer", f"{CM}.max_homopolymer", "nt"),
    ):
        v = F.get(r, path)
        if v is not None:
            stats.append({"es": es, "en": en, "value": v, "unit": unit, "path": path})
    return {
        "type": "endpoints",
        "model": F.get(r, f"{CM}.method"),
        "n": len(items),
        "items": items,
        "stats": stats,
    }


def scene_guides(r: Dict[str, Any]) -> Dict[str, Any]:
    """What the guide designer returned. On an empty run this draws the gap figure."""
    items = [{"seq": s["seq"], "source": f"guides[{s['i']}].{s['key']}"} for s in spacers(r)]
    stats = [
        {
            "es": "guías diseñadas",
            "en": "guides designed",
            "value": len(r.get("guides") or []),
            "unit": "",
            "path": "guides",
        },
        {
            "es": "loci puntuados como guía",
            "en": "loci scored as a guide",
            "value": len(F.get(r, f"{RG}.guides") or []),
            "unit": "",
            "path": f"{RG}.guides",
        },
    ]
    return {"type": "sequences", "items": items, "n": len(items), "jobs": [], "stats": stats}


def scene_regulatory(r: Dict[str, Any]) -> Dict[str, Any]:
    """Enrichment per track family, against 1.0 -- the point where the site equals
    the mean of its own window. That reference is the definition of the ratio, not
    a threshold invented here."""
    rules = []
    for i, _ in enumerate(F.get(r, f"{RG}.guides") or []):
        for t in track_rows(r, i):
            if t["ratio"] is None:
                continue
            rules.append(
                {
                    "name": t["name"],
                    "value": round(t["ratio"], 3),
                    "limit": 1.0,
                    "op": ">=",
                    "pass": t["ratio"] >= 1.0,
                }
            )
    return {
        "type": "rules",
        "rules": rules,
        "violations": [x["name"] for x in rules if not x["pass"]],
        "brenk": [],
        "pains": [],
    }


def scene_genes(r: Dict[str, Any]) -> Dict[str, Any]:
    dirs = F.get(r, f"{CS}.gene_expression_directions") or {}
    items = []
    for n, g in enumerate(F.get(r, f"{CS}.gene_expression_magnitude_relative.ranked") or []):
        if isinstance(g, dict) and g.get("gene"):
            items.append(
                {
                    "rank": n + 1,
                    "seq": str(g["gene"]),
                    "score": _num(g.get("magnitude")) or 0.0,
                    "changes": dirs.get(g["gene"]),
                }
            )
    stats = []
    for es, en, path, unit in (
        ("red perturbada", "network disruption", f"{CS}.network_disruption_score", ""),
        ("genes en la red", "genes in the network", f"{CS}.grn.n_nodes", ""),
        ("aristas reales", "real edges", f"{CS}.grn.n_edges", ""),
    ):
        v = F.get(r, path)
        if v is not None:
            stats.append({"es": es, "en": en, "value": v, "unit": unit, "path": path})
    return {"type": "ranking", "items": items, "stats": stats}


def scene_quantum(r: Dict[str, Any]) -> Dict[str, Any]:
    """A panel, not the qubit register: this run records no register size, and the
    report will not draw a number the run does not have."""
    stats = []
    for es, en, path, unit in (
        ("ΔE (VQE)", "ΔE (VQE)", f"{QM}.qgr_energy_change", ""),
        ("estabilidad", "stability", f"{QM}.qgr_stability", ""),
        ("objetivo metabólico", "metabolic objective", f"{QM}.metabolic_objective", ""),
        ("campos basales reales", "real basal fields", f"{CS}.n_genes_expression_derived", ""),
        ("segundos", "seconds", f"{CS}.elapsed_s", "s"),
    ):
        v = F.get(r, path)
        if v is not None:
            stats.append({"es": es, "en": en, "value": v, "unit": unit, "path": path})
    return {"type": "panel", "root": QC, "stats": stats}


def scene_admet(r: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for name, e in (F.get(r, f"{TOX}.admet_toxicity") or {}).items():
        if not isinstance(e, dict):
            continue
        v = _num(e.get("value"))
        if v is None:
            continue
        items.append(
            {
                "group": "toxicology",
                "name": f"{name} {v:.3f}",
                "value": v,
                "label": e.get("label"),
                "unit": "",
                "note": e.get("interpretation"),
            }
        )
    return {
        "type": "endpoints",
        "model": F.get(r, f"{Q}.engine"),
        "n": len(items),
        "score": _num(F.get(r, f"{Q}.toxicity_risk_honest.value")),
        "items": items,
    }


def scene_score(r: Dict[str, Any]) -> Dict[str, Any]:
    """The headline score as the mean it declares itself to be: each domain carries
    an equal share, and the shares stack up to the composite."""
    ds = F.get(r, f"{Q}.domain_scores") or {}
    vals = {k: _num(v) for k, v in ds.items() if _num(v) is not None}
    w = 1.0 / len(vals) if vals else 0.0
    return {
        "type": "score",
        "composite": _num(F.get(r, f"{Q}.overall_score")),
        "parts": [
            {"name": k, "score": v, "weight": round(w, 4), "weighted": round(v * w, 4)}
            for k, v in vals.items()
        ],
        "klass": F.get(r, f"{Q}.recommendation"),
        "flags": [] if F.get(r, f"{Q}.all_domains_pass") else ["all_domains_pass=false"],
        "gate": F.get(r, f"{Q}.all_domains_pass"),
    }


def scene_editor(r: Dict[str, Any]) -> Dict[str, Any]:
    stats = []
    for es, en, path, unit in (
        ("longitud", "length", f"{AV}.editor_aa_length", "aa"),
        ("residuos declarados plegados", "residues declared folded", f"{ST}.residues_folded", ""),
    ):
        v = F.get(r, path)
        if v is not None:
            stats.append({"es": es, "en": en, "value": v, "unit": unit, "path": path})
    return {"type": "panel", "root": MX, "stats": stats}


# ── generated beats ───────────────────────────────────────────────────────────────
def locus_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One sentence per locus the regulatory model actually scored, generated from
    the run, so a locus it never looked at can never get a sentence."""
    out: List[Dict[str, Any]] = []
    for i, g in enumerate(F.get(r, f"{RG}.guides") or []):
        if not isinstance(g, dict):
            continue
        out.append(
            {
                "es": f"Locus {{rg:guides[{i}].label}} en {{rg:guides[{i}].chrom}}:{{rg:guides[{i}].position|int}}, "
                f"tomado como sitio {{rg:guides[{i}].intent}}: el enriquecimiento máximo sobre la ventana es "
                f"{{rg:guides[{i}].max_enrichment|n2}}×.",
                "en": f"Locus {{rg:guides[{i}].label}} at {{rg:guides[{i}].chrom}}:{{rg:guides[{i}].position|int}}, "
                f"taken as an {{rg:guides[{i}].intent}} site: the highest enrichment over the window is "
                f"{{rg:guides[{i}].max_enrichment|n2}}×.",
                "tech": {
                    "es": f"el punto de anclaje no es una guía sino {{rg:guides[{i}].anchor_source}}; "
                    f"activo según el modelo: {{rg:guides[{i}].regulatorily_active}}",
                    "en": f"the anchor is not a guide but {{rg:guides[{i}].anchor_source}}; "
                    f"model calls it active: {{rg:guides[{i}].regulatorily_active}}",
                },
                "focus": {"locus": i},
                "gap": [f"{RG}.guides[{i}]"],
                "gap_es": f"Locus {i}, sin enriquecimiento",
                "gap_en": f"Locus {i}, no enrichment",
            }
        )
        for n, t in enumerate(track_rows(r, i)):
            if t["ratio"] is None:
                continue
            k = t["name"]
            # The scale is explained once, on the first family, and not repeated.
            tail_es = (
                "; la escala es esa razón, donde 1 sería un sitio idéntico al promedio de su entorno"
                if n == 0
                else ""
            )
            tail_en = (
                "; the scale is that ratio, where 1 would be a site identical to the average of its surroundings"
                if n == 0
                else ""
            )
            out.append(
                {
                    "es": f"{k}: la señal en el sitio es {{rg:guides[{i}].tracks.{k}.signal_at_site|n3}} frente a "
                    f"{{rg:guides[{i}].tracks.{k}.window_mean|n3}} de media en la ventana, es decir "
                    f"{{rg:guides[{i}].tracks.{k}.enrichment_ratio|n3}}×{tail_es}.",
                    "en": f"{k}: signal at the site is {{rg:guides[{i}].tracks.{k}.signal_at_site|n3}} against a window mean of "
                    f"{{rg:guides[{i}].tracks.{k}.window_mean|n3}}, that is "
                    f"{{rg:guides[{i}].tracks.{k}.enrichment_ratio|n3}}×{tail_en}.",
                    "tech": {
                        "es": f"{{rg:guides[{i}].tracks.{k}.n_tracks}} pista(s) a {{rg:guides[{i}].tracks.{k}.resolution_bp}} bp "
                        f"de resolución; la corrida nombra {{rg:guides[{i}].tracks.{k}.track_names|count}}",
                        "en": f"{{rg:guides[{i}].tracks.{k}.n_tracks}} track(s) at {{rg:guides[{i}].tracks.{k}.resolution_bp}} bp "
                        f"resolution; the run names {{rg:guides[{i}].tracks.{k}.track_names|count}}",
                    },
                    "focus": {"group": k},
                }
            )
    return out


def precedent_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One sentence per clinical precedent the run actually stored, so the list is
    read as separate facts instead of one run-on paragraph."""
    out = []
    for i, p in enumerate(F.get(r, f"{CC}.precedents") or []):
        if not isinstance(p, str) or not p.strip():
            continue
        lead_es = "Ya hay precedente clínico" if i == 0 else "Y también"
        lead_en = "There is clinical precedent already" if i == 0 else "And also"
        out.append(
            {
                "es": f"{lead_es}: {{cc:precedents[{i}]}}",
                "en": f"{lead_en}: {{cc:precedents[{i}]}}",
                "kind": "note",
                "focus": {"precedent": i},
            }
        )
    return out


def direction_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A sentence for each gene the run files under a direction its own numbers
    contradict. Generated from the run, so on a consistent run there are none."""
    out = []
    for b in contradicted_directions(r):
        g = b["gene"]
        out.append(
            {
                "es": f"La corrida lista {g} en {b['listed']}, pero su propio cambio para {g} es "
                f"{{cs:gene_expression_changes.{g}|n2}} y la dirección que registra es "
                f"{{cs:gene_expression_directions.{g}}}: las dos listas no dicen lo mismo.",
                "en": f"The run lists {g} under {b['listed']}, yet its own change for {g} is "
                f"{{cs:gene_expression_changes.{g}|n2}} and the direction it records is "
                f"{{cs:gene_expression_directions.{g}}}: the two do not agree.",
                "kind": "check",
                "requires_failed_check": "gene_directions",
                "focus": {"gene": g},
            }
        )
    return out


# ── chapters ──────────────────────────────────────────────────────────────────────
def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "overview",
            "title": {"es": "La corrida", "en": "The run"},
            "claims": [
                "pipeline",
                "status",
                "editor",
                "target_gene",
                "delivery",
                "disclaimer",
                "visualizations",
            ],
            "scene": scene_cover(r),
            "beats": [
                {
                    "es": "Esta página explica una corrida del pipeline {pipeline}: diseñar un editor {editor} contra el gen {target_gene} y entregarlo por {delivery}.",
                    "en": "This page explains one run of the {pipeline} pipeline: design a {editor} editor against the {target_gene} gene and deliver it by {delivery}.",
                    "tech": {
                        "es": "estado de la corrida: {status}",
                        "en": "run status: {status}",
                    },
                },
                {
                    "es": "El editor mide {av:editor_aa_length} aminoácidos y el casete completo que habría que empaquetar suma {av:estimated_total_payload_bp} pares de bases.",
                    "en": "The editor is {av:editor_aa_length} amino acids long and the whole cassette that would have to be packaged adds up to {av:estimated_total_payload_bp} base pairs.",
                    "tech": {
                        "es": "longitud tomada de {av:editor_aa_length_source}",
                        "en": "length taken from {av:editor_aa_length_source}",
                    },
                },
                {
                    "es": "Lo que el pipeline declara de sí mismo: {disclaimer}",
                    "en": "What the pipeline declares about itself: {disclaimer}",
                    "kind": "note",
                },
                {
                    "es": "La corrida guarda dos figuras propias, «{visualizations.aav_payload_budget.title}» y «{visualizations.codon_metrics.title}», que repiten en imagen lo que los capítulos siguientes cuentan con los números.",
                    "en": "The run stores two figures of its own, “{visualizations.aav_payload_budget.title}” and “{visualizations.codon_metrics.title}”, which repeat as pictures what the next chapters tell with the numbers.",
                    "kind": "note",
                },
                {
                    "es": "Cada número de esta página se lee del resultado de la corrida; cada valor del resultado aparece en algún capítulo o en el anexo. Cuando algo no se midió, la página cita la razón que da el propio pipeline.",
                    "en": "Every number on this page is read from the run's result; every value in that result appears in some chapter or in the annex. When something was not measured, the page quotes the pipeline's own reason.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "editor",
            "title": {
                "es": "La nucleasa y de dónde sale",
                "en": "The nuclease and where it comes from",
            },
            "claims": [SP, ST, MX],
            "scene": scene_editor(r),
            "beats": [
                {
                    "es": "La familia de la que sale el editor: {mx:nuclease_class}. {mx:architecture}",
                    "en": "The family the editor comes from: {mx:nuclease_class}. {mx:architecture}",
                    "focus": {"architecture": True},
                },
                {
                    "es": "Cómo encuentra su sitio: {mx:guide}",
                    "en": "How it finds its site: {mx:guide}",
                    "focus": {"guide": True},
                },
                {
                    "es": "Qué tiene que haber junto al sitio para que corte: {mx:pam}",
                    "en": "What has to sit next to the site before it will cut: {mx:pam}",
                    "focus": {"pam": True},
                },
                {
                    "es": "Cómo corta: {mx:catalysis}",
                    "en": "How it cuts: {mx:catalysis}",
                    "focus": {"catalysis": True},
                },
                {
                    "es": "Qué hace la célula con ese corte: {mx:outcome_biology}",
                    "en": "What the cell does with that cut: {mx:outcome_biology}",
                    "tech": {"es": "{mx:label}", "en": "{mx:label}"},
                    "focus": {"repair": True},
                },
                {
                    "es": "Lo que se plegó no es el ortólogo exacto del nombre pedido —el campo exact_named_ortholog dice {sp:exact_named_ortholog}— sino una referencia publicada: {sp:source}",
                    "en": "What was folded is not the exact ortholog of the name requested —the field exact_named_ortholog says {sp:exact_named_ortholog}— but a published reference: {sp:source}",
                    "tech": {"es": "{sp:note}", "en": "{sp:note}"},
                    "focus": {"provenance": True},
                },
                {
                    "es": "El plegado del editor se dibujaría aquí residuo a residuo.",
                    "en": "The editor's fold would be drawn here residue by residue.",
                    "requires_mesh": "editor",
                    "gap": [ST],
                    "gap_es": "Esta corrida no trae estructura: no hay cartoon que dibujar",
                    "gap_en": "This run carries no structure, so there is no cartoon to draw",
                    "focus": {"fold": True},
                },
                {
                    "es": "Sin estructura tampoco hay confianza del modelo: pLDDT {st:plddt} y pTM {st:ptm}.",
                    "en": "With no structure there is no model confidence either: pLDDT {st:plddt} and pTM {st:ptm}.",
                    "kind": "gap",
                    "tech": {
                        "es": "ipTM: {st:iptm}",
                        "en": "ipTM: {st:iptm}",
                    },
                },
                {
                    "es": "El bloque de estructura se contradice a sí mismo, y esta página lo dice en vez de elegir una de las dos versiones.",
                    "en": "The structure block contradicts itself, and this page says so rather than picking one of the two versions.",
                    "kind": "check",
                    "requires_failed_check": "structure_claim",
                },
            ],
        },
        {
            "id": "cassette",
            "title": {"es": "¿Cabe en un solo AAV?", "en": "Does it fit in a single AAV?"},
            "claims": [AV],
            "scene": scene_payload(r),
            "beats": [
                {
                    "es": "Un AAV sólo admite un genoma de {av:aav_packaging_limit_bp} pares de bases; todo lo que va dentro tiene que caber en ese presupuesto.",
                    "en": "An AAV only takes a genome of {av:aav_packaging_limit_bp} base pairs; everything that goes inside has to fit that budget.",
                    "focus": {"limit": True},
                },
                {
                    "es": "El casete son {av:components_bp|count} piezas: la nucleasa {av:components_bp.nuclease_cds_bp} bp, el promotor {av:components_bp.promoter_bp_est} bp, el casete de la guía {av:components_bp.guide_cassette_bp_est} bp, la señal de poliadenilación {av:components_bp.polyA_terminator_bp_est} bp y las ITR {av:components_bp.itr_overhead_bp_est} bp.",
                    "en": "The cassette is {av:components_bp|count} pieces: the nuclease {av:components_bp.nuclease_cds_bp} bp, the promoter {av:components_bp.promoter_bp_est} bp, the guide cassette {av:components_bp.guide_cassette_bp_est} bp, the polyadenylation signal {av:components_bp.polyA_terminator_bp_est} bp and the ITRs {av:components_bp.itr_overhead_bp_est} bp.",
                    "focus": {"components": True},
                },
                {
                    "es": "Las {av:components_bp|count} piezas suman exactamente la carga que declara la corrida, y el margen que queda es el límite menos esa suma.",
                    "en": "The {av:components_bp|count} pieces add up to exactly the payload the run declares, and the headroom is the limit minus that sum.",
                    "kind": "check",
                    "requires_check": "payload_budget",
                    "focus": {"components": True},
                },
                {
                    "es": "Quedan {av:headroom_bp} bp libres, así que la corrida concluye: {av:recommendation}.",
                    "en": "That leaves {av:headroom_bp} bp free, so the run concludes: {av:recommendation}.",
                    "tech": {"es": "{av:method}", "en": "{av:method}"},
                    "focus": {"headroom": True},
                },
                {
                    "es": "Sólo la nucleasa se midió; las piezas cuyo nombre acaba en «_est» son rangos de literatura, y por eso el resultado es una estimación y no un ensayo de empaquetamiento.",
                    "en": "Only the nuclease was measured; the pieces whose name ends in “_est” are literature ranges, which is why the result is an estimate and not a packaging assay.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "codons",
            "title": {
                "es": "La secuencia que se transcribe",
                "en": "The sequence that gets transcribed",
            },
            "claims": [CM],
            "scene": scene_codons(r),
            "beats": [
                {
                    "es": "La región codificante de la nucleasa mide {cm:cds_length_nt} nucleótidos, que es exactamente un triplete por aminoácido.",
                    "en": "The nuclease's coding region is {cm:cds_length_nt} nucleotides, which is exactly one triplet per amino acid.",
                    "kind": "check",
                    "requires_check": "cds_triplets",
                    "focus": {"group": "codons"},
                },
                {
                    "es": "El índice de adaptación de codones es {cm:cai_estimate|n4}: mide cuánto se parece la elección de codones sinónimos a la que el huésped usa con más frecuencia, y 1 sería copiarla siempre.",
                    "en": "The codon adaptation index is {cm:cai_estimate|n4}: it measures how close the synonymous-codon choice is to the one the host uses most often, and 1 would mean copying it every time.",
                    "focus": {"group": "codons"},
                },
                {
                    "es": "El contenido de G y C es {cm:gc_fraction|pct}, y la tirada más larga de una misma base es de {cm:max_homopolymer} nucleótidos — las tiradas largas complican la síntesis y la lectura del constructo.",
                    "en": "G and C content is {cm:gc_fraction|pct}, and the longest run of one repeated base is {cm:max_homopolymer} nucleotides — long runs make the construct harder to synthesise and to read.",
                    "tech": {"es": "{cm:method}", "en": "{cm:method}"},
                    "focus": {"group": "codons"},
                },
                {
                    "es": "La corrida no guarda la secuencia optimizada, sólo estas métricas suyas (estado {cm:status}), así que esta página no puede mostrarla base por base ni volver a medirlas sobre ella.",
                    "en": "The run does not store the optimised sequence, only these metrics of it (status {cm:status}), so this page can neither show it base by base nor re-measure them against it.",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "guides",
            "title": {
                "es": "Las guías que no llegaron a existir",
                "en": "The guides that never came to exist",
            },
            "claims": ["guides", "guide_note", SITE, OT],
            "scene": scene_guides(r),
            "beats": [
                {
                    "es": "El diseñador de guías no entregó ninguna, y da su razón: {guide_note}",
                    "en": "The guide designer returned none, and gives its reason: {guide_note}",
                    "kind": "gap",
                    "focus": {"guides": True},
                },
                {
                    "es": "Sin guías tampoco hay sitio de edición que mapear — estado {site:status}: {site:note}",
                    "en": "With no guides there is no edit site to map either — status {site:status}: {site:note}",
                    "kind": "gap",
                    "focus": {"site": True},
                },
                {
                    "es": "Cada espaciador se buscaría dentro de la secuencia del locus, en las dos hebras, para comprobar que la guía cae donde dice.",
                    "en": "Each spacer would be searched inside the locus sequence, on both strands, to check the guide lands where it claims.",
                    "kind": "check",
                    "requires_check": "guides_in_locus",
                    # The short status, not the long note again: the two beats above
                    # already carry the pipeline's full reason.
                    "gap": [f"{SITE}.status"],
                    "gap_es": "Ninguna guía puede localizarse en el locus, porque no hay locus",
                    "gap_en": "No guide can be located in the locus, because there is no locus",
                },
                {
                    "es": "El barrido de sitios fuera de blanco quedó en {ot:status}: {ot:reason}",
                    "en": "The off-target scan ended as {ot:status}: {ot:reason}",
                    "kind": "gap",
                    "tech": {"es": "{ot:note}", "en": "{ot:note}"},
                    "focus": {"offtarget": True},
                },
                {
                    "es": "Y la corrida etiqueta ese vacío sin suavizarlo: {ot:result_label}",
                    "en": "And the run labels that emptiness without softening it: {ot:result_label}",
                    "kind": "note",
                },
                {
                    "es": "Aun así otro módulo de esta misma corrida cuenta un locus como si fuera una guía; eso hace que dos partes del resultado no digan lo mismo.",
                    "en": "Even so another module of this same run counts a locus as if it were a guide, which makes two parts of the result disagree.",
                    "kind": "check",
                    "requires_failed_check": "guide_inventory",
                },
            ],
        },
        {
            "id": "regulatory",
            "title": {
                "es": "El locus en el paisaje del hígado",
                "en": "The locus in the liver's landscape",
            },
            "claims": [RG],
            "scene": scene_regulatory(r),
            "beats": [
                {
                    "es": "{rg:model} lee una ventana de {rg:window_bp|int} pares de bases alrededor del sitio y predice qué señales reguladoras habría allí en {rg:tissue} ({rg:ontology_term}).",
                    "en": "{rg:model} reads a {rg:window_bp|int}-base-pair window around the site and predicts which regulatory signals would be there in {rg:tissue} ({rg:ontology_term}).",
                    "tech": {
                        "es": "calculado en {rg:elapsed_s|n1} s",
                        "en": "computed in {rg:elapsed_s|n1} s",
                    },
                    "focus": {"window": True},
                },
            ]
            + locus_beats(r)
            + [
                {
                    "es": "Las cuentas del módulo cuadran: los sitios dentro y fuera de blanco suman los que se puntuaron, y los marcados como activos son los que el modelo marcó.",
                    "en": "The module's tallies add up: on-target and off-target sites sum to the ones scored, and the ones marked active are the ones the model marked.",
                    "kind": "check",
                    "requires_check": "regulatory_tally",
                },
                {
                    "es": "Cada razón de enriquecimiento es la señal del sitio dividida por la media de su ventana, recalculada aquí sobre los números de la propia corrida.",
                    "en": "Each enrichment ratio is the site's signal divided by its window mean, recomputed here from the run's own numbers.",
                    "kind": "check",
                    "requires_check": "enrichment",
                },
                {
                    "es": "Veredicto del módulo: {rg:verdict}. Ningún locus quedó como carga muerta ({rg:n_dead_payload}) ni como sitio activo fuera de blanco ({rg:n_active_offtarget}).",
                    "en": "Module verdict: {rg:verdict}. No locus came out as dead payload ({rg:n_dead_payload}) or as an active off-target site ({rg:n_active_offtarget}).",
                    "focus": {"verdict": True},
                },
                {
                    "es": "Lo que esto no dice: {rg:caveat}",
                    "en": "What this does not say: {rg:caveat}",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "cell",
            "title": {"es": "Qué le pasaría a la célula", "en": "What would happen to the cell"},
            "claims": [
                CS,
                BIO,
                GEN,
                MET,
                f"{Q}.modality",
                f"{Q}.molecule_target_link",
                f"{Q}.cell_type",
                f"{Q}.targets",
                f"{Q}.smiles",
                f"{Q}.engine",
                f"{Q}.backend",
                f"{Q}.elapsed_s",
                f"{Q}.success",
                f"{Q}.validation_status",
            ],
            "scene": scene_genes(r),
            "beats": [
                {
                    "es": "La simulación pone el editor a actuar sobre un {q:cell_type} y sigue el efecto por la red de regulación génica: {q:molecule_target_link}.",
                    "en": "The simulation puts the editor to work on a {q:cell_type} and follows the effect through the gene regulatory network: {q:molecule_target_link}.",
                    "tech": {
                        "es": "{q:engine} · {q:backend} · {q:elapsed_s|n1} s · modalidad {q:modality}",
                        "en": "{q:engine} · {q:backend} · {q:elapsed_s|n1} s · modality {q:modality}",
                    },
                    "focus": {"network": True},
                },
                {
                    "es": "La red son {cs:grn.n_nodes} genes unidos por {cs:grn.n_edges} arista(s) reales; las aristas vienen de {cs:grn.data_source} y no de esta corrida.",
                    "en": "The network is {cs:grn.n_nodes} genes joined by {cs:grn.n_edges} real edge(s); the edges come from {cs:grn.data_source}, not from this run.",
                    "tech": {"es": "{cs:grn.disclaimer}", "en": "{cs:grn.disclaimer}"},
                    "focus": {"network": True},
                },
                {
                    "es": "De esos genes, {gen:n_genes_affected} cambian de estado, lo que da una perturbación de red de {cs:network_disruption_score|n4}.",
                    "en": "Of those genes, {gen:n_genes_affected} change state, giving a network disruption of {cs:network_disruption_score|n4}.",
                    "kind": "check",
                    "requires_check": "network_disruption",
                    "focus": {"disruption": True},
                },
                {
                    "es": "Las magnitudes son relativas, no cambios de expresión absolutos: {cs:gene_expression_magnitude}.",
                    "en": "The magnitudes are relative, not absolute expression changes: {cs:gene_expression_magnitude}.",
                    "tech": {
                        "es": "{cs:gene_expression_magnitude_relative.method}",
                        "en": "{cs:gene_expression_magnitude_relative.method}",
                    },
                    "focus": {"magnitudes": True},
                },
            ]
            + direction_beats(r)
            + [
                {
                    "es": "El resultado que la corrida resume es un cambio de identidad celular: {cs:cell_state_transition}.",
                    "en": "What the run sums up is a change of cell identity: {cs:cell_state_transition}.",
                    "tech": {
                        "es": "base: {cs:cell_state_transition_detail.basis} · {cs:cell_state_transition_detail.method}",
                        "en": "basis: {cs:cell_state_transition_detail.basis} · {cs:cell_state_transition_detail.method}",
                    },
                    "focus": {"transition": True},
                },
                {
                    "es": "El modelo metabólico deja {met:active_reactions|count} reacciones activas y {met:blocked_reactions|count} bloqueadas, de donde sale una disrupción metabólica de {met:metabolic_disruption_score|n4}.",
                    "en": "The metabolic model leaves {met:active_reactions|count} reactions active and {met:blocked_reactions|count} blocked, which is where a metabolic disruption of {met:metabolic_disruption_score|n4} comes from.",
                    "kind": "check",
                    "requires_check": "metabolic_disruption",
                    "focus": {"metabolic": True},
                },
                {
                    "es": "La actividad biológica queda en {bio:activity_score|n4}, con un cambio de energía de {bio:energy_change|n4} y una estabilidad de {bio:stability_score|n4}; el módulo anota on_target_effect = {bio:on_target_effect}, es decir que no registró efecto sobre el blanco.",
                    "en": "Biological activity comes out at {bio:activity_score|n4}, with an energy change of {bio:energy_change|n4} and a stability of {bio:stability_score|n4}; the module records on_target_effect = {bio:on_target_effect}, that is, it recorded no on-target effect.",
                    "focus": {"activity": True},
                },
                {
                    "es": "La viabilidad celular no se calcula, y la corrida explica por qué: {cs:cell_viability_honest.null_reason}",
                    "en": "Cell viability is not computed, and the run explains why: {cs:cell_viability_honest.null_reason}",
                    "kind": "gap",
                    "focus": {"viability": True},
                },
                {
                    "es": "El proxy de esencialidad tampoco da número: {cs:cell_viability_proxy.null_reason}",
                    "en": "The essentiality proxy gives no number either: {cs:cell_viability_proxy.null_reason}",
                    "kind": "gap",
                    "tech": {
                        "es": "{cs:cell_viability_proxy.depmap_source}, {cs:cell_viability_proxy.depmap_n_cell_lines} líneas celulares",
                        "en": "{cs:cell_viability_proxy.depmap_source}, {cs:cell_viability_proxy.depmap_n_cell_lines} cell lines",
                    },
                },
                {
                    "es": "Y el enlace entre el editor y su blanco no está validado: {cs:molecule_target_link}",
                    "en": "And the link between the editor and its target is not validated: {cs:molecule_target_link}",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "La parte cuántica", "en": "The quantum part"},
            "claims": [QC, QM, f"{CS}.quantum_backend"],
            "scene": scene_quantum(r),
            "beats": [
                {
                    "es": "El núcleo cuántico resuelve la red génica como un problema de energía: {qm:qgr_note}",
                    "en": "The quantum core solves the gene network as an energy problem: {qm:qgr_note}",
                    "focus": {"energy": True},
                },
                {
                    "es": "El cambio de energía del estado variacional es {qm:qgr_energy_change|n4} y la estabilidad que devuelve es {qm:qgr_stability|n4}.",
                    "en": "The variational state's energy change is {qm:qgr_energy_change|n4} and the stability it returns is {qm:qgr_stability|n4}.",
                    "focus": {"energy": True},
                },
                {
                    "es": "Los campos de partida no son inventados: {qm:baseline_expression_note}",
                    "en": "The starting fields are not invented: {qm:baseline_expression_note}",
                    "tech": {
                        "es": "{qm:expression_source} para {qm:expression_cell_type_label} · {qm:n_genes_expression_derived} gen(es) con expresión real y {qm:n_genes_scaffold_default} con valor por defecto",
                        "en": "{qm:expression_source} for {qm:expression_cell_type_label} · {qm:n_genes_expression_derived} gene(s) with real expression and {qm:n_genes_scaffold_default} on a default value",
                    },
                    "focus": {"fields": True},
                },
                {
                    "es": "La cascada no es libre: parte de {qm:grn_cascade_seed_targets} y recorre regulones reales de {qm:grn_data_source}.",
                    "en": "The cascade is not free-running: it starts from {qm:grn_cascade_seed_targets} and walks real regulons from {qm:grn_data_source}.",
                    "tech": {"es": "{qm:grn_cascade_note}", "en": "{qm:grn_cascade_note}"},
                    "focus": {"cascade": True},
                },
                {
                    "es": "El plan era GPU: {qc:software} sobre {qc:target}.",
                    "en": "The plan was GPU: {qc:software} on {qc:target}.",
                    "tech": {
                        "es": "híbrido: {qc:hybrid} · {qc:provenance}",
                        "en": "hybrid: {qc:hybrid} · {qc:provenance}",
                    },
                    "focus": {"backend": True},
                },
                {
                    "es": "No ocurrió así: los dos núcleos cayeron al simulador local ({qc:qgr_vqe_gpu.backend} y {qc:qmf_qaoa_gpu.backend}), y la corrida guarda el error en vez de ocultarlo: {qc:error}",
                    "en": "That is not what happened: both kernels fell back to the local simulator ({qc:qgr_vqe_gpu.backend} and {qc:qmf_qaoa_gpu.backend}), and the run keeps the error rather than hiding it: {qc:error}",
                    "kind": "note",
                    "tech": {"es": "{qc:hint}", "en": "{qc:hint}"},
                    "focus": {"backend": True},
                },
                {
                    "es": "El simulador que acabó corriendo es {cs:quantum_backend}. La corrida no registra cuántos cúbits ni cuántos términos tenía el registro, así que esta página no los dibuja.",
                    "en": "The simulator that ended up running is {cs:quantum_backend}. The run records neither the number of qubits nor the number of terms in the register, so this page does not draw them.",
                    "kind": "gap",
                    "focus": {"backend": True},
                },
                {
                    "es": "Y el grafo de señalización no contiene el blanco, que es la razón de que el compromiso con la diana quede sin medir: {qm:qsn_error}",
                    "en": "And the signalling graph does not contain the target, which is why target engagement goes unmeasured: {qm:qsn_error}",
                    "kind": "gap",
                    "focus": {"cascade": True},
                },
            ],
        },
        {
            "id": "safety",
            "title": {
                "es": "Seguridad, y qué clase de seguridad",
                "en": "Safety, and what kind of safety",
            },
            "claims": [TOX, PHA, DS, PX],
            "scene": scene_admet(r),
            "beats": [
                {
                    "es": "Lo que se está evaluando es {ds:modality}, no una molécula pequeña.",
                    "en": "What is being assessed is {ds:modality}, not a small molecule.",
                    "tech": {"es": "{ds:label}", "en": "{ds:label}"},
                    "focus": {"modality": True},
                },
                {
                    "es": "Por eso el propio bloque de seguridad descarta el ADMET clásico: {ds:small_molecule_admet}",
                    "en": "That is why the safety block itself rules out classical ADMET: {ds:small_molecule_admet}",
                    "kind": "note",
                    "focus": {"group": "toxicology"},
                },
                {
                    "es": "Los {tox:admet_toxicity|count} modelos ADMET se ejecutaron igualmente y devolvieron Ames {tox:admet_toxicity.ames.value|n4} ({tox:admet_toxicity.ames.interpretation}), daño hepático {tox:admet_toxicity.dili.value|n4} ({tox:admet_toxicity.dili.interpretation}) y hERG {tox:admet_toxicity.herg.value|n4} ({tox:admet_toxicity.herg.interpretation}).",
                    "en": "The {tox:admet_toxicity|count} ADMET models ran anyway and returned Ames {tox:admet_toxicity.ames.value|n4} ({tox:admet_toxicity.ames.interpretation}), liver injury {tox:admet_toxicity.dili.value|n4} ({tox:admet_toxicity.dili.interpretation}) and hERG {tox:admet_toxicity.herg.value|n4} ({tox:admet_toxicity.herg.interpretation}).",
                    "tech": {
                        "es": "ROC-AUC medido: Ames {tox:admet_toxicity.ames.validation.measured.value|n3} sobre {tox:admet_toxicity.ames.validation.measured.n_test} moléculas · DILI {tox:admet_toxicity.dili.validation.measured.value|n3} sobre {tox:admet_toxicity.dili.validation.measured.n_test} · hERG {tox:admet_toxicity.herg.validation.measured.value|n3} sobre {tox:admet_toxicity.herg.validation.measured.n_test}, todos de {tox:admet_toxicity.ames.validation.measured.source}",
                        "en": "Measured ROC-AUC: Ames {tox:admet_toxicity.ames.validation.measured.value|n3} over {tox:admet_toxicity.ames.validation.measured.n_test} molecules · DILI {tox:admet_toxicity.dili.validation.measured.value|n3} over {tox:admet_toxicity.dili.validation.measured.n_test} · hERG {tox:admet_toxicity.herg.validation.measured.value|n3} over {tox:admet_toxicity.herg.validation.measured.n_test}, all from {tox:admet_toxicity.ames.validation.measured.source}",
                    },
                    "focus": {"group": "toxicology"},
                },
                {
                    "es": "El conjunto conforme dice cuánta confianza hay detrás de cada número: con una cobertura objetivo del {tox:admet_toxicity.ames.validation.conformal.target_coverage|pct}, Ames queda como {tox:admet_toxicity.ames.validation.conformal.interpretation}, DILI como {tox:admet_toxicity.dili.validation.conformal.interpretation} y hERG como {tox:admet_toxicity.herg.validation.conformal.interpretation}.",
                    "en": "The conformal set says how much confidence sits behind each number: at a target coverage of {tox:admet_toxicity.ames.validation.conformal.target_coverage|pct}, Ames comes out {tox:admet_toxicity.ames.validation.conformal.interpretation}, DILI {tox:admet_toxicity.dili.validation.conformal.interpretation} and hERG {tox:admet_toxicity.herg.validation.conformal.interpretation}.",
                    "tech": {
                        "es": "{tox:admet_toxicity.ames.validation.conformal.method}; cobertura empírica {tox:admet_toxicity.ames.validation.conformal.empirical_coverage_test|pct}",
                        "en": "{tox:admet_toxicity.ames.validation.conformal.method}; empirical coverage {tox:admet_toxicity.ames.validation.conformal.empirical_coverage_test|pct}",
                    },
                    "focus": {"group": "toxicology"},
                },
                {
                    "es": "Ninguno de los {tox:admet_toxicity|count} pasa del umbral que el propio método fija, así que el riesgo tóxico declarado es {q:toxicity_risk_honest.value|n2}.",
                    "en": "None of the {tox:admet_toxicity|count} crosses the threshold the method itself sets, so the declared toxic risk is {q:toxicity_risk_honest.value|n2}.",
                    "kind": "check",
                    "requires_check": "admet_fraction",
                    "tech": {
                        "es": "{q:toxicity_risk_honest.method} · {q:toxicity_risk_honest.provenance}",
                        "en": "{q:toxicity_risk_honest.method} · {q:toxicity_risk_honest.provenance}",
                    },
                    "focus": {"group": "toxicology"},
                },
                {
                    "es": "Ese cero está calculado sobre una molécula que no existe en esta corrida, y sin embargo alimenta la puntuación final.",
                    "en": "That zero is computed over a molecule that does not exist in this run, and it still feeds the final score.",
                    "kind": "check",
                    "requires_failed_check": "admet_applicability",
                    "focus": {"group": "toxicology"},
                },
                {
                    "es": "El riesgo que sí importa aquí no se calculó: {ds:offtarget_genomic_risk}",
                    "en": "The risk that actually matters here was not computed: {ds:offtarget_genomic_risk}",
                    "kind": "gap",
                    "focus": {"offtarget": True},
                },
                {
                    "es": "El otro riesgo propio del formato es inmunológico: {ds:immunogenicity}",
                    "en": "The other risk specific to this format is immunological: {ds:immunogenicity}",
                    "focus": {"immunogenicity": True},
                },
                {
                    "es": "Elegir vector es elegir ventana de exposición. AAV: {ds:delivery_tradeoffs.AAV} mRNA-LNP: {ds:delivery_tradeoffs.mRNA_LNP}",
                    "en": "Choosing a vector is choosing an exposure window. AAV: {ds:delivery_tradeoffs.AAV} mRNA-LNP: {ds:delivery_tradeoffs.mRNA_LNP}",
                    "tech": {
                        "es": "{ds:delivery_tradeoffs.note}",
                        "en": "{ds:delivery_tradeoffs.note}",
                    },
                    "focus": {"delivery": True},
                },
                {
                    "es": "La farmacología de un editor no se parece a la de un fármaco: {px:exposure_paradigm}",
                    "en": "An editor's pharmacology is not like a drug's: {px:exposure_paradigm}",
                    "tech": {"es": "{px:label}", "en": "{px:label}"},
                    "focus": {"pharmacology": True},
                },
                {
                    "es": "El módulo de farmacología lo dice con su propio veredicto: {pha:recommendation}",
                    "en": "The pharmacology module says as much in its own verdict: {pha:recommendation}",
                    "kind": "gap",
                    "tech": {
                        "es": "compromiso con la diana: {pha:target_engagement.null_reason}",
                        "en": "target engagement: {pha:target_engagement.null_reason}",
                    },
                    "focus": {"pharmacology": True},
                },
            ],
        },
        {
            "id": "verdict",
            "title": {
                "es": "La nota final y de qué está hecha",
                "en": "The final mark and what it is made of",
            },
            "claims": [
                f"{Q}.overall_score",
                f"{Q}.overall_score_note",
                f"{Q}.all_domains_pass",
                f"{Q}.toxicology_assessed",
                f"{Q}.toxicity_risk",
                f"{Q}.toxicity_risk_honest",
                f"{Q}.recommendation",
                f"{Q}.domain_scores",
                f"{Q}.tangential_validation",
                f"{Q}.geneformer_xcheck",
                f"{Q}.singlecell_xcheck",
                VD,
                CC,
            ],
            "scene": scene_score(r),
            "beats": [
                {
                    "es": "La puntuación global es {q:overall_score|n3} y la recomendación que sale de ella es «{q:recommendation}»; el campo all_domains_pass dice {q:all_domains_pass}.",
                    "en": "The overall score is {q:overall_score|n3} and the recommendation that comes out of it is “{q:recommendation}”; the field all_domains_pass says {q:all_domains_pass}.",
                    "focus": {"composite": True},
                },
                {
                    "es": "Es la media simple de {q:domain_scores|count} dominios: actividad {q:domain_scores.activity|n4}, seguridad metabólica {q:domain_scores.metabolic_safety|n4}, estabilidad genómica {q:domain_scores.genomic_stability|n4} y toxicología {q:domain_scores.toxicology_safe|n4}.",
                    "en": "It is the plain mean of {q:domain_scores|count} domains: activity {q:domain_scores.activity|n4}, metabolic safety {q:domain_scores.metabolic_safety|n4}, genomic stability {q:domain_scores.genomic_stability|n4} and toxicology {q:domain_scores.toxicology_safe|n4}.",
                    "kind": "check",
                    "requires_check": "domain_mean",
                    "focus": {"parts": True},
                },
                {
                    "es": "Cada uno de esos {q:domain_scores|count} repite un número que ya estaba en otra parte de la corrida, y aquí se ha vuelto a seguir hasta su origen.",
                    "en": "Each of those {q:domain_scores|count} restates a number that was already elsewhere in the run, and here each one has been traced back to its source.",
                    "kind": "check",
                    "requires_check": "domain_sources",
                    "focus": {"parts": True},
                },
                {
                    "es": "El dominio que más sube la media es el de toxicología, con {q:domain_scores.toxicology_safe|n2}; el que más la baja es la actividad, con {q:domain_scores.activity|n4}, porque el módulo no registró efecto sobre el blanco.",
                    "en": "The domain that lifts the mean most is toxicology, at {q:domain_scores.toxicology_safe|n2}; the one that pulls it down most is activity, at {q:domain_scores.activity|n4}, because the module recorded no on-target effect.",
                    "focus": {"parts": True},
                },
                {
                    "es": "La propia corrida acota qué entra en la media: {q:overall_score_note}",
                    "en": "The run itself bounds what goes into the mean: {q:overall_score_note}",
                    "kind": "note",
                },
                {
                    "es": "La validación tangencial no encontró referencia con la que comparar: {q:tangential_validation.overall_concordance_na_reason}",
                    "en": "The tangential validation found no reference to compare against: {q:tangential_validation.overall_concordance_na_reason}",
                    "kind": "gap",
                    "tech": {
                        "es": "{q:tangential_validation.data_sources.molecule}; LINCS/GDSC: {q:tangential_validation.data_sources.lincs_gdsc}",
                        "en": "{q:tangential_validation.data_sources.molecule}; LINCS/GDSC: {q:tangential_validation.data_sources.lincs_gdsc}",
                    },
                },
                {
                    "es": "Lo único que sí se pudo contrastar fue la concordancia de perturbación, y dio {q:tangential_validation.perturbation_concordance.value|n2}: {q:tangential_validation.perturbation_concordance.provenance}",
                    "en": "The one thing that could be contrasted was perturbation concordance, and it came out at {q:tangential_validation.perturbation_concordance.value|n2}: {q:tangential_validation.perturbation_concordance.provenance}",
                    "tech": {
                        "es": "{q:tangential_validation.perturbation_concordance.disclaimer}",
                        "en": "{q:tangential_validation.perturbation_concordance.disclaimer}",
                    },
                    "focus": {"concordance": True},
                },
                {
                    "es": "La segunda opinión independiente tampoco llegó: {q:geneformer_xcheck.engine} quedó en {q:geneformer_xcheck.verdict}",
                    "en": "The independent second opinion did not arrive either: {q:geneformer_xcheck.engine} ended as {q:geneformer_xcheck.verdict}",
                    "kind": "gap",
                    "tech": {
                        "es": "{q:geneformer_xcheck.error}",
                        "en": "{q:geneformer_xcheck.error}",
                    },
                },
                {
                    "es": "Las heurísticas de guías siguen sin contrastarse contra datos experimentales: dentro de blanco, {vd:ontarget.note}; fuera de blanco, {vd:offtarget.note}.",
                    "en": "The guide heuristics are still untested against experimental data: on-target, {vd:ontarget.note}; off-target, {vd:offtarget.note}.",
                    "kind": "gap",
                    "tech": {
                        "es": "cómo se validaría: {vd:how_to_validate}",
                        "en": "how it would be validated: {vd:how_to_validate}",
                    },
                },
            ]
            + precedent_beats(r)
            + [
                {
                    "es": "Sobre este blanco en concreto: {cc:target_specific}",
                    "en": "On this target in particular: {cc:target_specific}",
                    "tech": {"es": "{cc:relevance}", "en": "{cc:relevance}"},
                },
                {
                    "es": "Nada de eso es una predicción de esta corrida: {cc:label}",
                    "en": "None of that is a prediction from this run: {cc:label}",
                    "kind": "note",
                },
            ],
        },
    ]


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Which structures in this result deserve a PyMOL cartoon.

    This pipeline stores the fold under `structure`, and when the fold backend
    fails there is no PDB text at all -- then this returns nothing and every
    sentence that would have described a picture becomes a declared gap."""
    out = []
    for p in _PDB_PATHS:
        v = F.get(r, p)
        if F.is_pdb(v):
            out.append({"key": "editor", "pdb": v, "label": p})
            break
    return out


# ── checks: arithmetic recomputed from the run's own data ─────────────────────────
def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add(cid: str, ok: bool, es: str, en: str, paths: List[str]) -> None:
        out.append({"id": cid, "ok": bool(ok), "es": es, "en": en, "paths": paths})

    # 1 -- the AAV budget: the parts, the total and the headroom.
    comp = F.get(r, f"{AV}.components_bp") or {}
    parts = {k: _num(v) for k, v in comp.items() if _num(v) is not None}
    total = _num(F.get(r, f"{AV}.estimated_total_payload_bp"))
    limit = _num(F.get(r, f"{AV}.aav_packaging_limit_bp"))
    head = _num(F.get(r, f"{AV}.headroom_bp"))
    if parts and total is not None and limit is not None:
        s = sum(parts.values())
        ok = abs(s - total) < 0.5 and (head is None or abs((limit - total) - head) < 0.5)
        add(
            "payload_budget",
            ok,
            f"{' + '.join(str(int(v)) for v in parts.values())} = {int(s)} bp"
            + (
                f", la carga declarada es {int(total)} bp y el margen {int(limit)} − {int(total)} = {int(limit - total)} bp"
                if ok
                else f", pero la corrida declara {int(total)} bp de carga y {head} bp de margen"
            ),
            f"{' + '.join(str(int(v)) for v in parts.values())} = {int(s)} bp"
            + (
                f", the declared payload is {int(total)} bp and the headroom {int(limit)} − {int(total)} = {int(limit - total)} bp"
                if ok
                else f", but the run declares {int(total)} bp of payload and {head} bp of headroom"
            ),
            [f"{AV}.components_bp", f"{AV}.estimated_total_payload_bp", f"{AV}.headroom_bp"],
        )

    # 2 -- one triplet per amino acid, and the stop codon the AAV estimate adds.
    aa = _num(F.get(r, f"{AV}.editor_aa_length"))
    cds = _num(F.get(r, f"{CM}.cds_length_nt"))
    est = _num(F.get(r, f"{AV}.estimated_cds_bp"))
    if aa and cds:
        ok = abs(aa * 3 - cds) < 0.5
        tail = ""
        if est is not None:
            extra = int(est - cds)
            tail = (
                f"; el presupuesto AAV usa {int(est)} bp, {extra} nt más — el codón de parada"
                if extra == 3
                else f"; el presupuesto AAV usa {int(est)} bp, {extra} nt de diferencia"
            )
            tail_en = (
                f"; the AAV budget uses {int(est)} bp, {extra} nt more — the stop codon"
                if extra == 3
                else f"; the AAV budget uses {int(est)} bp, a difference of {extra} nt"
            )
        else:
            tail_en = ""
        add(
            "cds_triplets",
            ok,
            f"{int(aa)} aminoácidos × 3 = {int(aa * 3)} nt"
            + (f" y el CDS mide {int(cds)} nt{tail}" if ok else f" pero el CDS mide {int(cds)} nt"),
            f"{int(aa)} amino acids × 3 = {int(aa * 3)} nt"
            + (
                f" and the CDS is {int(cds)} nt{tail_en}"
                if ok
                else f" but the CDS is {int(cds)} nt"
            ),
            [f"{AV}.editor_aa_length", f"{CM}.cds_length_nt", f"{AV}.estimated_cds_bp"],
        )

    # 3 -- what the guide designer produced against what the rest of the run counts.
    guides = r.get("guides")
    reg_guides = F.get(r, f"{RG}.guides")
    if isinstance(guides, list) and isinstance(reg_guides, list):
        ng, nr = len(guides), len(reg_guides)
        anchors = sorted(
            {
                str(g.get("anchor_source"))
                for g in reg_guides
                if isinstance(g, dict) and g.get("anchor_source")
            }
        )
        via = f" ({'; '.join(anchors)})" if anchors else ""
        add(
            "guide_inventory",
            ng == nr,
            f"el diseñador entregó {ng} guía(s) y el módulo regulador puntuó {nr} locus/loci bajo la clave «guides»"
            + (
                ""
                if ng == nr
                else f"{via}: lo que se puntuó no son guías diseñadas sino el punto de anclaje del gen"
            ),
            f"the designer returned {ng} guide(s) while the regulatory module scored {nr} locus/loci under the key “guides”"
            + (
                ""
                if ng == nr
                else f"{via}: what was scored is not a designed guide but the gene's anchor point"
            ),
            ["guides", f"{RG}.guides", f"{RG}.n_scored"],
        )

    # 4 -- the structure block against itself.
    has = F.get(r, f"{ST}.has_structure")
    res = _num(F.get(r, f"{ST}.residues_folded"))
    full = F.get(r, f"{ST}.folded_full_length")
    status = F.get(r, f"{ST}.status")
    if has is not None or status is not None:
        claims_fold = bool(res) or full is True
        no_fold = has is False or (isinstance(status, str) and "fail" in status.lower())
        ok = not (no_fold and claims_fold)
        add(
            "structure_claim",
            ok,
            f"structure.status = «{status}» y has_structure = {has}"
            + (
                f", pero la misma corrida declara {int(res or 0)} residuos plegados y folded_full_length = {full}"
                if not ok
                else "; nada más en el bloque afirma un plegado"
            ),
            f"structure.status = “{status}” and has_structure = {has}"
            + (
                f", yet the same run declares {int(res or 0)} folded residues and folded_full_length = {full}"
                if not ok
                else "; nothing else in the block claims a fold"
            ),
            [
                f"{ST}.status",
                f"{ST}.has_structure",
                f"{ST}.residues_folded",
                f"{ST}.folded_full_length",
            ],
        )

    # 5 -- the regulatory module's own tallies.
    if isinstance(reg_guides, list) and reg_guides:
        n_scored = _num(F.get(r, f"{RG}.n_scored"))
        on = _num(F.get(r, f"{RG}.n_on_target"))
        off = _num(F.get(r, f"{RG}.n_off_target"))
        act = _num(F.get(r, f"{RG}.n_regulatorily_active"))
        act_real = sum(
            1 for g in reg_guides if isinstance(g, dict) and g.get("regulatorily_active")
        )
        ok = (
            n_scored == len(reg_guides)
            and (on is None or off is None or on + off == n_scored)
            and (act is None or act == act_real)
        )
        add(
            "regulatory_tally",
            ok,
            f"{len(reg_guides)} locus/loci puntuados, {int(on or 0)} dentro de blanco + {int(off or 0)} fuera = {int((on or 0) + (off or 0))}, "
            f"y {act_real} marcado(s) como regulatoriamente activo(s) frente a {int(act or 0)} declarado(s)",
            f"{len(reg_guides)} locus/loci scored, {int(on or 0)} on-target + {int(off or 0)} off-target = {int((on or 0) + (off or 0))}, "
            f"and {act_real} marked regulatorily active against {int(act or 0)} declared",
            [
                f"{RG}.n_scored",
                f"{RG}.n_on_target",
                f"{RG}.n_off_target",
                f"{RG}.n_regulatorily_active",
            ],
        )

        # 6 -- every enrichment ratio, and the maximum the run reports.
        bad, n = [], 0
        worst_max = None
        for i, _g in enumerate(reg_guides):  # the index is what track_rows needs
            rows = [t for t in track_rows(r, i) if t["ratio"] is not None and t["window"]]
            for t in rows:
                n += 1
                calc = t["signal"] / t["window"]
                if abs(calc - t["ratio"]) > max(0.01, 0.01 * abs(t["ratio"])):
                    bad.append(f"{t['name']} {calc:.3f}≠{t['ratio']}")
            declared = _num(F.get(r, f"{RG}.guides[{i}].max_enrichment"))
            if rows and declared is not None:
                top = max(t["ratio"] for t in rows)
                if abs(top - declared) > 0.01:
                    worst_max = f"{top:.3f}≠{declared}"
        if n:
            ok = not bad and worst_max is None
            add(
                "enrichment",
                ok,
                f"las {n} razones de enriquecimiento son señal/media de ventana"
                + (
                    " (dentro del redondeo que guarda la corrida), y el máximo por locus es el mayor de ellas"
                    if ok
                    else f"; no cuadran: {', '.join(bad) or worst_max}"
                ),
                f"the {n} enrichment ratios are signal over window mean"
                + (
                    " (within the rounding the run stores), and each locus's maximum is the largest of them"
                    if ok
                    else f"; they do not add up: {', '.join(bad) or worst_max}"
                ),
                [f"{RG}.guides"],
            )

    # 7 -- the headline score as the mean it says it is.
    ds = {k: _num(v) for k, v in (F.get(r, f"{Q}.domain_scores") or {}).items()}
    ds = {k: v for k, v in ds.items() if v is not None}
    overall = _num(F.get(r, f"{Q}.overall_score"))
    if ds and overall is not None:
        mean = sum(ds.values()) / len(ds)
        ok = abs(mean - overall) <= 0.001
        add(
            "domain_mean",
            ok,
            f"({' + '.join(f'{v:g}' for v in ds.values())}) / {len(ds)} = {mean:.4f}"
            + (f" y la puntuación global es {overall}" if ok else f" pero la global es {overall}"),
            f"({' + '.join(f'{v:g}' for v in ds.values())}) / {len(ds)} = {mean:.4f}"
            + (f" and the overall score is {overall}" if ok else f" but the overall is {overall}"),
            [f"{Q}.domain_scores", f"{Q}.overall_score"],
        )

    # 8 -- each domain score traced back to the raw signal it restates.
    rows = [d for d in domain_sources(r) if d["score"] is not None and d["from"] is not None]
    if rows:
        bad = [
            f"{d['name']} {d['score']}≠{d['from']:.4f}"
            for d in rows
            if abs(d["score"] - d["from"]) > 0.001
        ]
        add(
            "domain_sources",
            not bad,
            f"los {len(rows)} dominios repiten su señal de origen"
            + ("" if not bad else f", salvo {', '.join(bad)}"),
            f"the {len(rows)} domains restate their source signal"
            + ("" if not bad else f", except {', '.join(bad)}"),
            [f"{Q}.domain_scores"] + [d["path"] for d in rows],
        )

    # 9 -- the toxic-risk fraction over the endpoints it is drawn from.
    ends = {
        k: _num(v.get("value"))
        for k, v in (F.get(r, f"{TOX}.admet_toxicity") or {}).items()
        if isinstance(v, dict) and _num(v.get("value")) is not None
    }
    risk = _num(F.get(r, f"{Q}.toxicity_risk_honest.value"))
    if ends and risk is not None:
        flagged = sum(1 for v in ends.values() if v > 0.5)
        frac = flagged / len(ends)
        add(
            "admet_fraction",
            abs(frac - risk) <= 0.001,
            f"{flagged} de {len(ends)} endpoints ADMET pasan de 0,5 → {frac:.4f}, y el riesgo declarado es {risk}",
            f"{flagged} of {len(ends)} ADMET endpoints go above 0.5 → {frac:.4f}, and the declared risk is {risk}",
            [f"{TOX}.admet_toxicity", f"{Q}.toxicity_risk_honest.value"],
        )

    # 10 -- whether those endpoints had a molecule to score at all.
    smiles = F.get(r, f"{Q}.smiles")
    available = F.get(r, f"{TOX}.admet_available")
    if ends and available is not None:
        empty = not (isinstance(smiles, str) and smiles.strip())
        ok = not (available and empty)
        add(
            "admet_applicability",
            ok,
            f"admet_available = {available} con {len(ends)} endpoint(s) puntuados"
            + (
                ""
                if ok
                else f" y smiles = «{smiles}» (vacío): no hay molécula que puntuar en una carga de edición génica, "
                f"y aun así ese resultado se convierte en el dominio toxicology_safe de la nota final"
            ),
            f"admet_available = {available} with {len(ends)} endpoint(s) scored"
            + (
                ""
                if ok
                else f" and smiles = “{smiles}” (empty): there is no molecule to score in a gene-editing payload, "
                f"and that result still becomes the toxicology_safe domain of the final mark"
            ),
            [
                f"{Q}.smiles",
                f"{TOX}.admet_available",
                f"{TOX}.admet_toxicity",
                f"{Q}.domain_scores.toxicology_safe",
            ],
        )

    # 11 -- network disruption as the fraction of genes that moved.
    nd = _num(F.get(r, f"{CS}.network_disruption_score"))
    changes = F.get(r, f"{CS}.gene_expression_changes") or {}
    if nd is not None and changes:
        moved = sum(1 for v in changes.values() if _num(v) not in (None, 0.0))
        frac = moved / len(changes)
        add(
            "network_disruption",
            abs(frac - nd) <= 0.001,
            f"{moved} de {len(changes)} genes de la red cambian → {frac:.4f}, y la corrida declara {nd}",
            f"{moved} of {len(changes)} genes in the network move → {frac:.4f}, and the run declares {nd}",
            [f"{CS}.gene_expression_changes", f"{CS}.network_disruption_score"],
        )

    # 12 -- metabolic disruption as the fraction of reactions that went dark.
    act_rx = F.get(r, f"{MET}.active_reactions")
    blk_rx = F.get(r, f"{MET}.blocked_reactions")
    md = _num(F.get(r, f"{MET}.metabolic_disruption_score"))
    if (
        isinstance(act_rx, list)
        and isinstance(blk_rx, list)
        and md is not None
        and (act_rx or blk_rx)
    ):
        frac = len(blk_rx) / (len(act_rx) + len(blk_rx))
        add(
            "metabolic_disruption",
            abs(frac - md) <= 0.001,
            f"{len(blk_rx)} reacciones bloqueadas de {len(act_rx) + len(blk_rx)} → {frac:.4f}, y la corrida declara {md}",
            f"{len(blk_rx)} blocked reactions out of {len(act_rx) + len(blk_rx)} → {frac:.4f}, and the run declares {md}",
            [
                f"{MET}.active_reactions",
                f"{MET}.blocked_reactions",
                f"{MET}.metabolic_disruption_score",
            ],
        )

    # 13 -- the up/down lists against the changes they are supposed to summarise.
    bad_dirs = contradicted_directions(r)
    if changes and (F.get(r, f"{CS}.genes_upregulated") or F.get(r, f"{CS}.genes_downregulated")):
        detail = "; ".join(
            f"{b['gene']} en {b['listed']} con cambio {b['change']:g} y dirección {b['dir']}"
            for b in bad_dirs
        )
        detail_en = "; ".join(
            f"{b['gene']} under {b['listed']} with change {b['change']:g} and direction {b['dir']}"
            for b in bad_dirs
        )
        add(
            "gene_directions",
            not bad_dirs,
            (
                "las listas de genes al alza y a la baja coinciden con los cambios que la corrida registra"
                if not bad_dirs
                else f"las listas no coinciden con los cambios: {detail}"
            ),
            (
                "the up- and down-regulated lists agree with the changes the run records"
                if not bad_dirs
                else f"the lists do not agree with the changes: {detail_en}"
            ),
            [
                f"{CS}.genes_upregulated",
                f"{CS}.genes_downregulated",
                f"{CS}.gene_expression_changes",
                f"{CS}.gene_expression_directions",
            ],
        )

    # 14 -- can each designed spacer actually be found in the locus it targets?
    sp, loc = spacers(r), locus(r)
    if sp and loc:
        missing = [s for s in sp if loc.find(s["seq"]) < 0 and loc.find(revcomp(s["seq"])) < 0]
        add(
            "guides_in_locus",
            not missing,
            f"{len(sp) - len(missing)} de {len(sp)} espaciadores aparecen dentro de la secuencia del locus ({len(loc)} nt), en una de las dos hebras"
            + (
                "" if not missing else f"; no se encuentran: {', '.join(s['seq'] for s in missing)}"
            ),
            f"{len(sp) - len(missing)} of {len(sp)} spacers are found inside the locus sequence ({len(loc)} nt), on one of the two strands"
            + ("" if not missing else f"; not found: {', '.join(s['seq'] for s in missing)}"),
            ["guides"] + [p for p in _LOCUS_PATHS if F.get(r, p)],
        )

    return out


# MOLEVERA / BIOQL
