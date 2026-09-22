# Anthropic × Adaptyv Protein Design Competition — respuestas listas
2026-09-21 · Track 2 · solicitante individual
Toda cifra sale de `src/backend/validation_metrics.json` con su fecha de registro.
Los **[CORCHETES]** son lo único que falta completar.

---

## Track
**Track 2 únicamente.** Track 1 exige postular como equipo; siendo solo, marcarlo
sería reclamar algo que no se sostiene en revisión.

---

## Q: Previous experience in protein design, including prior competitions

DE NOVO BINDER DESIGN (benchmarked in-house against live NVIDIA BioNeMo
endpoints, recorded 2026-06-27 — not a paper reproduction)

RFdiffusion → ProteinMPNN → ESMFold self-consistency pipeline. 10 backbones
(length 100, 50 diffusion steps) × 8 sequences = 80 designs, scored by Kabsch
scRMSD between the generated backbone and the refolded sequence. 8/10 backbones
self-consistent at the canonical scRMSD < 2.0 Å threshold (80%); median best
scRMSD 0.757 Å. Target-conditioned design via RFdiffusion contigs and hotspot
residues is implemented and in production use.

ANTIBODY–ANTIGEN ΔΔG — AB-Bind, single→Ala, RDE-Network supervised head
Pearson r = 0.621, Spearman ρ = 0.55, sign accuracy 0.872 on the held-out split.
The leaked all-fold average (r = 0.812) is recorded in the same metrics file and
explicitly labelled as not the honest number, because 23 of 24 AB-Bind complexes
appear in SKEMPI2 and two of three averaged CV models saw each one. Head-to-head
on identical mutations: ESM-IF1 r = 0.475 vs restrained MM-GBSA r = 0.113.

ANTIBODY–ANTIGEN COGNATE-PAIR DISCRIMINATION — SAbDab, 3,064 complexes
AntiBERTa2 VH/VL + ESM-2 antigen embeddings, bilinear probe. AUROC 0.6925
generic, 0.7159 SARS-CoV-2, evaluated over 954 held-out antigen groups to
control sequence leakage.

STRUCTURE PREDICTION QC
Boltz-2 mean pLDDT 0.962 across chignolin, Trp-cage and villin HP35.

PRIOR COMPETITIONS
Anthropic hackathon, February 2026 — TargetRadar, a target-discovery tool
(github.com/Bionicsdemo/targetradar). Not a protein design competition. I have
entered no protein design competition before this one.

RELATED METHODOLOGICAL WORK (unpublished manuscripts; small-molecule binding
free energy, not protein design). Listed as evidence of the standard of proof I
work to, not as protein design credentials:
• "A unified quantum–classical platform for relative binding free energies:
  2.0× lower error than the reference commercial engine on identical edges"
  (TYK2 edges, head-to-head against a commercial FEP engine)
• "Measured Applicability Domains for a Multi-Physics Binding-Affinity Pipeline"
  (each method's validity boundary measured rather than assumed)
• "A Two-Algorithm Quantum Core for Drug Discovery: Combinatorial Sequence
  Optimization and Variational Cell-State Simulation"

I have no peer-reviewed or preprint publication in protein design, and the
manuscripts above are unpublished and address small-molecule binding, not
design. A platform preprint is in preparation. My protein design record is
measured, versioned and leakage-audited rather than published: the numbers
above come from a metrics file in the repository, each with its recording date.

---

## Q: Lab website / Google Scholar / GitHub

https://github.com/Bionicsdemo — BioQL ecosystem, TargetRadar, Spectrix.
[+ web corporativa si la hay]

---

## Q: Research team description  (145 words)

I am the sole researcher. I founded [COMPANY] and build BioQL, a computational
discovery platform covering protein design, structural modelling and binding free
energy. Scientific domain: de novo binder design with RFdiffusion, ProteinMPNN and
ESMFold self-consistency filtering, benchmarked in-house at 80% self-consistency
(scRMSD < 2 Å, median 0.76 Å); antibody engineering (AB-Bind ΔΔG, SAbDab
cognate-pair discrimination, humanness, developability); MM-GBSA and alchemical
free-energy calculation; quantum chemistry with SQD and DMRG benchmarked against
CCSD(T). AI/ML: production deployment of protein language models (ESM-2,
AntiBERTa2, ESM-IF1), diffusion models for backbone generation, and GPU inference
on Modal and NVIDIA BioNeMo, under a suite of 1,489 automated tests.
**[CREDENCIALES: título y años en biología computacional]**. Every result carries
provenance — cryptographic manifests, explicit leakage audits, recorded negative
results — because a design claim nobody can trace is not a claim. That is why I
want these designs measured by someone else.

---

## Q: How Claude will be used  (144 words)

Today our triage is fixed thresholds — scRMSD < 2 Å, ipTM > 0.8 — applied
independently to each candidate. They cannot weigh a design that folds cleanly but
buries a charged hotspot, and they know nothing about the target. Claude reads those
signals jointly, alongside the literature on each epitope, and proposes ranked
hypotheses with stated reasoning that we then try to falsify computationally before
spending a synthesis slot. Second, Claude audits the pipeline itself: this month it
found two silent failures our 1,489 tests missed — a status layer reporting GPU
services as live when they were unreachable, and a refold endpoint failing open, so
designs disappeared with no error. Both had been wrong for days. Third, it drafts
the provenance record for every submitted design so a third party can reproduce it,
which is the point of publishing negative results openly.

---

## Pendientes antes de enviar

1. **[COMPANY]** — nombre legal exacto ligado al correo corporativo.
2. **[CREDENCIALES]** — título y años en biología computacional.
3. **Competencias previas** — ¿cuenta el hackathon de Anthropic (TargetRadar)?
   Hace falta fecha y resultado, o se elimina la línea.
4. **Workspace de Modal deshabilitado** (`ac-zVHXKkD32vUUIhyl2OGFgJ`): los créditos
   de la competencia aterrizan en un workspace; conviene reactivarlo antes.
