# Previous experience in protein design, including prior competitions

> Anthropic × Adaptyv Protein Design Competition — Track 2
> Respuesta lista para pegar. Toda cifra procede de `src/backend/validation_metrics.json`, con su fecha de registro.

---

## De novo binder design

*Benchmarked in-house against live NVIDIA BioNeMo endpoints, recorded 2026-06-27 — not a paper reproduction.*

RFdiffusion → ProteinMPNN → ESMFold self-consistency pipeline. 10 backbones (length 100, 50 diffusion steps) × 8 sequences = 80 designs, scored by Kabsch scRMSD between the generated backbone and the refolded sequence. **8/10 backbones self-consistent at the canonical scRMSD < 2.0 Å threshold (80%); median best scRMSD 0.757 Å.** Target-conditioned design via RFdiffusion contigs and hotspot residues is implemented and in production use.

## Antibody–antigen ΔΔG — AB-Bind, single→Ala, RDE-Network supervised head

**Pearson r = 0.621, Spearman ρ = 0.55, sign accuracy 0.872** on the held-out split. The leaked all-fold average (r = 0.812) is recorded in the same metrics file and explicitly labelled as not the honest number, because 23 of 24 AB-Bind complexes appear in SKEMPI2 and two of three averaged CV models saw each one. Head-to-head on identical mutations: ESM-IF1 r = 0.475 vs restrained MM-GBSA r = 0.113.

## Antibody–antigen cognate-pair discrimination — SAbDab, 3,064 complexes

AntiBERTa2 VH/VL + ESM-2 antigen embeddings, bilinear probe. **AUROC 0.6925 generic, 0.7159 SARS-CoV-2**, evaluated over 954 held-out antigen groups to control sequence leakage.

## Structure prediction QC

Boltz-2 mean pLDDT 0.962 across chignolin, Trp-cage and villin HP35.

## Prior competitions

Anthropic hackathon, February 2026 — TargetRadar, a target-discovery tool (github.com/Bionicsdemo/targetradar). Not a protein design competition. I have entered no protein design competition before this one.

## Related methodological work

*Unpublished manuscripts; small-molecule binding free energy, not protein design. Listed as evidence of the standard of proof I work to, not as protein design credentials.*

- **"A unified quantum–classical platform for relative binding free energies: 2.0× lower error than the reference commercial engine on identical edges"** — TYK2 edges, head-to-head against a commercial FEP engine.
- **"Measured Applicability Domains for a Multi-Physics Binding-Affinity Pipeline"** — each method's validity boundary measured rather than assumed.
- **"A Two-Algorithm Quantum Core for Drug Discovery: Combinatorial Sequence Optimization and Variational Cell-State Simulation"**

---

I have no peer-reviewed or preprint publication in protein design, and the manuscripts above are unpublished and address small-molecule binding, not design. A platform preprint is in preparation. My protein design record is measured, versioned and leakage-audited rather than published: the numbers above come from a metrics file in the repository, each with its recording date.
