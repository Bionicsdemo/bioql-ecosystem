// ============================================================================
// cardRegistry.ts — explicit manifest of the chat card dispatch convention.
//
// WHAT THIS IS: BioQL Workbench 3.0 has ~40 result-card components under
// src/components/chat/ but no shared data contract. Two hand-wired
// switchboards decide which card renders for a given tool result:
//
//   1. ChatMessage.tsx `extractPipelineData()` (~line 487-984) walks every
//      completed tool's output, recognizes known result shapes, and sets
//      `enrichment.<key> = ...`. The memoized result (`pipelineData`, ~line
//      994) is then read by a long list of `{pipelineData.<key> && <Card .../>}`
//      JSX conditionals (~line 2983-3413). Most — but not all — of those
//      conditionals render a dedicated <XCard> component; a few render
//      inline JSX via local `renderXxx()` helper functions instead of a
//      component (documented below as `cardComponent: '(inline JSX)'`).
//
//   2. ToolExecutionCard.tsx dispatches a *second*, independent way: by
//      `tool.name` directly (not by enrichment key), for a handful of tools
//      that render outside the ChatMessage pipelineData path entirely
//      (e.g. `mrna_therapeutic_design` -> MrnaTherapeuticCard, the
//      `v11_*` tools -> renderV11Results, `quantum_mps_*`/`quantum_gpu_*`
//      -> QuantumResultCard). This file documents those too so the
//      registry reflects the REAL dispatch surface, not an idealized one.
//
// THIS FILE IS ADDITIVE, DESCRIPTIVE TOOLING. It does not change dispatch
// behavior, is not imported by ChatMessage.tsx or ToolExecutionCard.tsx, and
// must never be treated as the source of truth for what actually renders —
// only as a manually-maintained mirror of it for regression testing. When
// the real switchboards change, this file must be updated to match (and a
// stale entry here is a registry bug, not a switchboard bug).
//
// `requiredKeys` per entry are the minimal fields whose presence the real
// switchboard already gates on (i.e. the same conditions that decide whether
// `enrichment.<key>` gets set / whether the card's own internal reads would
// produce a non-empty section) — see the `notes` field on each entry for the
// exact ChatMessage.tsx / card-component line(s) the spec was read from.
// ============================================================================

/** One required field for a card to be considered "successfully rendered". */
export interface RequiredKeySpec {
  /** Dot-path resolved against the pipeline's top-level `result` object. */
  path: string;
  /** Alternate dot-paths; ANY one of (path, ...alsoPaths) being present/positive satisfies this spec. */
  alsoPaths?: string[];
  /**
   * When true, a value of 0 (or NaN) counts as MISSING, not present.
   * Use this for count/length fields where 0 is a real historical bug
   * signature (e.g. structure_3d.length_aa, mature_length_aa) rather than
   * a legitimate measurement of zero.
   */
  mustBePositive?: boolean;
  /** Human-readable explanation of what this field represents / why it's required. */
  description?: string;
}

export type DispatchSource =
  | 'ChatMessage.extractPipelineData' // enrichment.<enrichmentKey>, ~ChatMessage.tsx:487-984, rendered ~2983-3413
  | 'ToolExecutionCard.tool.name';    // tool.name switchboard, ToolExecutionCard.tsx:180-360

export interface CardRegistryEntry {
  /** Stable id for this registry entry (not necessarily unique per component — some components appear once). */
  id: string;
  /**
   * `root.pipeline` value this entry is scoped to, or null if the card is
   * NOT gated by a specific pipeline name (i.e. it can appear for many
   * different pipelines whenever the relevant shape is found anywhere in
   * the result, per extractPipelineData's shape-sniffing / deepFind calls).
   */
  pipeline: string | null;
  dispatchedFrom: DispatchSource;
  /** Key on ChatMessage's `pipelineData` object (the `extractPipelineData()` return value), or null if dispatched by tool.name instead. */
  enrichmentKey: string | null;
  /** tool.name this entry matches, only set for ToolExecutionCard.tool.name-dispatched entries. */
  toolName?: string;
  /** Name of the component that actually renders (for reference only — not imported here). */
  cardComponent: string;
  requiredKeys: RequiredKeySpec[];
  /** Where in the real source this convention was read from, and any caveats. */
  notes: string;
}

export const CARD_REGISTRY: CardRegistryEntry[] = [
  {
    id: 'macrocycle',
    pipeline: 'macrocycle_design',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'macrocycle',
    cardComponent: 'MacrocycleCard',
    requiredKeys: [
      { path: 'stages.1_build', description: 'contabilidad de cierre de anillo' },
      { path: 'candidates', description: 'la priorización' },
    ],
    notes:
      'Ensena primero la integridad (anillos cerrados, poblacion conservada, ' +
      'ensembles sin converger) porque los fallos de este pipeline son silenciosos: ' +
      'un anillo que no cerro sigue calculando descriptores como si fuera un macrociclo.',
  },
  {
    id: 'consistencyAudit',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'consistencyAudit',
    cardComponent: 'ConsistencyAuditCard',
    requiredKeys: [
      { path: 'consistency_audit.status' },
    ],
    notes: 'Final enriched-result modality, range and contradiction gate. MOLVERA / BIOQL.',
  },
  {
    id: 'generativeModel',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'generativeModel',
    cardComponent: 'GenerativeModelCard',
    requiredKeys: [
      {
        path: 'trained_generator',
        alsoPaths: ['stages.iglm_proposer'],
        description: 'Real promoted ESM-2 checkpoint or IgLM proposal provenance.',
      },
    ],
    notes: 'Surfaces checkpoint identity, disjoint held-out loss, dataset hash, proposal diversity and honest proposal-only scope. MOLVERA / BIOQL.',
  },
  {
    id: 'qdiffvision',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'qdiffvision',
    cardComponent: 'QDiffVisionCard',
    requiredKeys: [
      { path: 'qdiffvision', alsoPaths: ['pipeline'], description: 'Direct qdiffvision_v1 result or automatic nested qdiffvision stage.' },
    ],
    notes: "ChatMessage.tsx detects root.pipeline === 'qdiffvision_v1' or deepFind(root, 'qdiffvision') in every pipeline; the card also renders GenMol topology and multipocket validation gates.",
  },
  // ── Pipeline-specific: MOLEVERA veterinary antibody drug design ────────────
  {
    id: 'moleveraVeterinaryAntibodyDesign',
    pipeline: 'molevera_veterinary_antibody_design_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'moleveraVeterinaryAntibodyDesign',
    cardComponent: 'MoleveraVeterinaryAntibodyDesignCard',
    requiredKeys: [
      { path: 'antigen_identity.status' },
      { path: 'stages' },
      { path: 'candidates', alsoPaths: ['antigen_identity.reason'] },
    ],
    notes: 'Renders all 12 animal-adapted antibody-design stages, antigen/framework provenance, every VH/VL candidate, relative binding, developability, structure and compute truth. MOLEVERA / BIOQL.',
  },
  {
    id: 'moleveraVeterinaryDrugProduct',
    pipeline: 'molevera_veterinary_antibody_design_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'moleveraVeterinaryAntibodyDesign',
    cardComponent: 'MoleveraVeterinaryDrugProductCard',
    requiredKeys: [
      { path: 'veterinary_product_profile' },
      { path: 'species_immunogenicity.status' },
      { path: 'development_plan.work_packages' },
    ],
    notes: 'Renders the veterinary target product profile, dose arithmetic, species-immunogenicity gap/results, experimental work packages and downloadable design artifacts. MOLEVERA / BIOQL.',
  },
  {
    id: 'moleveraVeterinaryQuantumContribution',
    pipeline: 'molevera_veterinary_antibody_design_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'moleveraVeterinaryAntibodyDesign',
    cardComponent: 'MoleveraVeterinaryQuantumCard',
    requiredKeys: [
      { path: 'quantum_contribution.standing_goal_pct' },
      { path: 'quantum_contribution.measured_quantum_pct', alsoPaths: ['quantum_contribution.status'] },
      { path: 'quantum_contribution.stage_ledger' },
    ],
    notes: 'Renders the measured per-run quantum share, the standing 58% floor, executed-stage ledger, backend and hardware truth. The result is measured and can be N/A or below the floor; it is never forced. MOLEVERA / BIOQL.',
  },

  // ── Pipeline-specific: configuration-driven veterinary antibodies ────────
  {
    id: 'veterinaryAntibodyProgram',
    pipeline: 'veterinary_antibody_program_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'veterinaryAntibodyProgram',
    cardComponent: 'VeterinaryAntibodyProgramCard',
    requiredKeys: [
      { path: 'program_id' },
      { path: 'phase_statuses' },
      { path: 'artifact_bundle.manifest_path', alsoPaths: ['summary.decision'] },
    ],
    notes: 'ChatMessage extracts the full pipeline root; ProgramCard renders the request-defined species, targets, phases, decision, and every artifact path. MOLEVERA / BIOQL.',
  },
  {
    id: 'veterinaryAntibodyEvidence',
    pipeline: 'veterinary_antibody_program_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'veterinaryAntibodyProgram',
    cardComponent: 'VeterinaryAntibodyEvidenceCard',
    requiredKeys: [
      { path: 'sources.literature' },
      { path: 'sources.targets' },
      { path: 'evidence_matrix' },
    ],
    notes: 'EvidenceCard renders every configured query, Europe PMC record, UniProt entry/sequence, Ensembl transcript, source error, and evidence row. MOLEVERA / BIOQL.',
  },
  {
    id: 'veterinaryAntibodyGates',
    pipeline: 'veterinary_antibody_program_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'veterinaryAntibodyProgram',
    cardComponent: 'VeterinaryAntibodyGatesCard',
    requiredKeys: [
      { path: 'gate_assessment.gates' },
      { path: 'program_state.status' },
      { path: 'compute.status' },
    ],
    notes: 'GatesCard renders every request-defined gate, prerequisites, criteria, next action, program state, and compute attribution. MOLEVERA / BIOQL.',
  },

  // ── Pipeline-specific: replicon workbench ────────────────────────────────
  {
    id: 'replicon',
    pipeline: 'replicon_workbench_v1',
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'replicon',
    cardComponent: 'RepliconCard',
    requiredKeys: [
      { path: 'genome.organism', description: 'resolved virus/organism name; genome.resolved should also be true' },
      { path: 'genome.resolved' },
      { path: 'replicon_design.construct', description: 'the designed replicon construct object (RepliconCard reads data.replicon_design.construct)' },
      { path: 'summary.measured_quantum_pct', description: 'RepliconCard KPI row; also the 58%-floor "STANDING /goal" metric' },
    ],
    notes:
      "ChatMessage.tsx ~936-956: when root.pipeline === 'replicon_workbench_v1' the ENTIRE root object " +
      "is passed through as enrichment.replicon (no reshaping) — the non-pipeline-name branch (deepFind-based, " +
      "used for older/non-tagged results) reshapes into {genome, replicon_design, antiviral_discovery, compute_stack, " +
      "llm_analysis, summary, virus_query, branch} instead. RepliconCard.tsx:160-166 reads " +
      "data.genome / data.replicon_design / data.summary directly (antiviral_discovery is optional, defaults to {}).",
  },

  // ── Tool-name-specific: mRNA therapeutic design (NOT part of ChatMessage's enrichment path) ──
  {
    id: 'mrna_therapeutic',
    pipeline: 'mrna_therapeutic_v1',
    dispatchedFrom: 'ToolExecutionCard.tool.name',
    enrichmentKey: null,
    toolName: 'mrna_therapeutic_design',
    cardComponent: 'MrnaTherapeuticCard',
    requiredKeys: [
      {
        path: 'stages.1_protein_design.mature_length_aa',
        mustBePositive: true,
        description:
          'Length of the designed mature protein payload. Historical "0 AA" bug: protein design can fail ' +
          '(empty mature_length_aa=0) while a later stage still folds a leftover placeholder sequence and ' +
          'renders a plausible-looking (but meaningless) structure card.',
      },
      {
        path: 'structure_3d.length_aa',
        mustBePositive: true,
        alsoPaths: ['structure_3d.sequence'],
        description:
          'Length of the sequence actually folded for the 3D viewer. Should track ' +
          'stages.1_protein_design.mature_length_aa; a mismatch (structure folded from a tiny placeholder ' +
          'like "GG" while mature_length_aa=0) is the same historical bug class from the other direction.',
      },
    ],
    notes:
      "MrnaTherapeuticCard is NOT rendered via ChatMessage's extractPipelineData/pipelineData mechanism at all. " +
      "It is dispatched directly from ToolExecutionCard.tsx:313-314 by tool.name === 'mrna_therapeutic_design', " +
      "receiving the raw parsed tool output (ToolExecutionCard.tsx has its own PIPELINE_TOOLS/QUANTUM_SIM_TOOLS/ " +
      "QUANTUM_MANYBODY_TOOLS switchboard, a second, independent dispatch mechanism from ChatMessage's). " +
      "MrnaTherapeuticCard.tsx:190-205 normalizes data.result vs data, then reads stages['1_protein_design'] " +
      "and structure_3d directly.",
  },

  // ── Generic (pipeline-agnostic) enrichment-key cards, ChatMessage.tsx extractPipelineData ──
  {
    id: 'protenix',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'protenix',
    cardComponent: 'ProtenixConfidencePanel',
    requiredKeys: [
      { path: 'confidence.plddt', alsoPaths: ['confidence.ptm', 'confidence.iptm', 'plddt', 'iptm'] },
    ],
    notes: 'ChatMessage.tsx:508-536 — gated on protenixStage && !error && (confidence || iptm != null). Rendered ~3067-3068.',
  },
  {
    id: 'mol3d',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'mol3d',
    cardComponent: '(inline: InteractiveMoleculeViewer / MoleculeViewer3D)',
    requiredKeys: [{ path: 'mol_3d', alsoPaths: ['stages.10_3d_structure.mol_block', 'best_candidate.mol_3d', 'candidates.0.mol_3d'] }],
    notes: 'ChatMessage.tsx:539-543. Rendered inline ~3140-3230, not a dedicated <Card/>.',
  },
  {
    id: 'docking',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'docking',
    cardComponent: '(inline JSX block)',
    requiredKeys: [
      {
        // Root-relative: the container object holding docking data must exist
        // at one of these locations (mirrors ChatMessage.tsx:544-550's lookup chain).
        path: 'docking',
        alsoPaths: [
          'stages.9_docking', 'stages.6_docking', 'analyses.docking',
          'best_candidate.analyses.docking', 'best_candidate.docking',
          'candidates.0.analyses.docking', 'candidates.0.docking',
        ],
        description: 'Container presence only — the real gate also requires status===completed OR a numeric binding_affinity_kcal/poses/poses_generated field inside it (ChatMessage.tsx:551), not replicated here.',
      },
    ],
    notes: 'ChatMessage.tsx:544-569 (also has an antibody-pipeline fallback path deriving docking from kd_nM/binding_affinity_kcal, not modeled by this spec). Rendered inline ~3083-3140.',
  },
  {
    id: 'admet',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'admet',
    cardComponent: 'ADMETRadarChart',
    requiredKeys: [
      {
        // Root-relative container lookup, mirrors ChatMessage.tsx:574-580's chain.
        path: 'admet',
        alsoPaths: [
          'stages.2_admet.data', 'analyses.admet',
          'best_candidate.analyses.admet', 'best_candidate.admet',
          'candidates.0.analyses.admet', 'candidates.0.admet',
        ],
        description: 'Container presence only — the deepFind fallback (not modeled here) additionally requires absorption/distribution/metabolism/parameters_count keys to avoid matching a bare scoring.admet weight (ChatMessage.tsx:582-589).',
      },
    ],
    notes: 'ChatMessage.tsx:574-593. Rendered ~3075-3080.',
  },
  {
    id: 'candidates',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'candidates',
    cardComponent: 'PipelineResultsChart',
    requiredKeys: [{ path: 'candidates', alsoPaths: ['discovery.candidates', 'candidates_generated.small_molecules', 'candidates_generated.peptides', 'candidates_generated.nanobodies'] }],
    notes: 'ChatMessage.tsx:596-610, requires a non-empty array. Rendered ~3062-3064.',
  },
  {
    id: 'toxicology',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'toxicology',
    cardComponent: '(inline: renderToxicology helper)',
    requiredKeys: [
      {
        // Root-relative container lookup, mirrors ChatMessage.tsx:629-643's chain
        // (candidates.0.admet.toxicology is how the antibody-pipeline shape surfaces this).
        path: 'toxicology',
        alsoPaths: [
          'stages.3_toxicology.data', 'toxicology_study', 'admet.toxicology', 'analyses.toxicology',
          'best_candidate.analyses.toxicology', 'best_candidate.toxicology', 'best_candidate.admet.toxicology',
          'candidates.0.analyses.toxicology', 'candidates.0.toxicology', 'candidates.0.admet.toxicology',
          'discovery.toxicology', 'stages.7_toxicology.data', 'acute_toxicity', 'ada_risk',
        ],
      },
    ],
    notes: 'ChatMessage.tsx:628-647. Rendered ~3235.',
  },
  {
    id: 'pharmacology',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'pharmacology',
    cardComponent: '(inline: renderPharmacology helper)',
    requiredKeys: [
      {
        path: 'pharmacology',
        alsoPaths: [
          'stages.4_pharmacology.data', 'pharmacology_study', 'analyses.pharmacology',
          'best_candidate.analyses.pharmacology', 'best_candidate.pharmacology',
          'candidates.0.analyses.pharmacology', 'candidates.0.pharmacology', 'discovery.pharmacology',
          'pharmacokinetics', 'admet.excretion.half_life_days',
        ],
      },
    ],
    notes: 'ChatMessage.tsx:650-685 (antibody-pipeline fallback derives from admet.excretion.half_life_days). Rendered ~3238.',
  },
  {
    id: 'clinical',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'clinical',
    cardComponent: '(inline: renderClinicalTrial helper)',
    requiredKeys: [
      {
        path: 'clinical_trial',
        alsoPaths: [
          'stages.5_clinical_trial.data', 'stages.clinical_trial_simulation.trials.0', 'clinical_trials',
          'analyses.clinical_trial', 'best_candidate.analyses.clinical_trial', 'best_candidate.clinical_trial',
          'candidates.0.analyses.clinical_trial', 'candidates.0.clinical_trial', 'phase_I', 'phase_1',
        ],
      },
    ],
    notes: 'ChatMessage.tsx:688-702. Rendered ~3241.',
  },
  {
    id: 'quantumCell',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'quantumCell',
    cardComponent: 'QuantumCellCard',
    requiredKeys: [{ path: 'success' }],
    notes: "ChatMessage.tsx:790-797 — gated on qcellData.success !== false (i.e. absent success also passes). Rendered ~3248.",
  },
  {
    id: 'biomolecules',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'biomolecules',
    cardComponent: '(inline: renderBiomolecules helper)',
    requiredKeys: [{ path: 'therapeutic_peptides.candidates', alsoPaths: ['antibody_fragments.candidates', 'enzyme_mimetics.candidates'] }],
    notes: 'ChatMessage.tsx:771-787 — only keeps sub-keys whose .candidates is a non-empty array. Rendered ~3253-3258.',
  },
  {
    id: 'structure3dPdb',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'structure3dPdb',
    cardComponent: '(inline: InteractiveMoleculeViewer, via structure3dPdb + structure3dMeta)',
    requiredKeys: [
      { path: 'structure_3d.pdb', alsoPaths: ['structure_3d.pdb_data', 'pdb_data', 'complex_pdb'] },
      {
        path: 'structure_3d.length_aa',
        mustBePositive: true,
        description: 'Same historical "0 AA" bug field as the mrna_therapeutic entry above, but reachable from ANY pipeline via this generic key (ChatMessage.tsx:830-837 deepFinds structure_3d for every pipeline, not just mRNA).',
      },
    ],
    notes: "ChatMessage.tsx:829-837 — requires the resolved pdb string to literally contain 'ATOM'. structure3dMeta carries {plddt, length_aa, method} alongside it. Rendered ~2988-3007.",
  },
  {
    id: 'complexPdb',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'complexPdb',
    cardComponent: '(inline: InteractiveMoleculeViewer, via complexPdb + complexMeta)',
    requiredKeys: [{ path: 'complex_structure_3d.pdb' }],
    notes: "ChatMessage.tsx:840-845 — requires complex_structure_3d.pdb to contain 'ATOM'. Rendered ~3009-3024.",
  },
  {
    id: 'fep',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'fep',
    cardComponent: 'FEPResultsCard',
    requiredKeys: [{ path: 'fep_rbfe_alchemical', alsoPaths: ['fep_rbfe'] }],
    notes: 'ChatMessage.tsx:856-859 (deepFind). Rendered ~3385.',
  },
  {
    id: 'diffdock',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'diffdock',
    cardComponent: 'DiffDockCard',
    requiredKeys: [{ path: 'engine', alsoPaths: ['docking.engine', 'diffdock'] }],
    notes: "ChatMessage.tsx:860-865 — matches root.engine === 'diffdock-l-nim' OR root.docking.engine === same, OR a deepFind('diffdock'). Rendered ~3386.",
  },
  {
    id: 'genmol',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'genmol',
    cardComponent: 'GenMolCard',
    requiredKeys: [{ path: 'generative_genmol', alsoPaths: ['genmol'] }],
    notes: 'ChatMessage.tsx:866-869 (deepFind). Rendered ~3387.',
  },
  {
    id: 'binder',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'binder',
    cardComponent: 'BinderDesignCard',
    requiredKeys: [{ path: 'denovo_scaffold', alsoPaths: ['denovo_binder_design'] }],
    notes: 'ChatMessage.tsx:870-873 (deepFind). Rendered ~3388.',
  },
  {
    id: 'crispr',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'crispr',
    cardComponent: 'CrisprOfftargetCard',
    requiredKeys: [{ path: 'offtarget', alsoPaths: ['guides'] }],
    notes: "ChatMessage.tsx:874-876 — deepFind('offtarget') or deepFind('guides'); when matched, the ENTIRE root object is passed as data (not a reshaped sub-object). Rendered ~3389.",
  },
  {
    id: 'metabolism',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'metabolism',
    cardComponent: 'MetabolismCard',
    requiredKeys: [{ path: 'site_of_metabolism', alsoPaths: ['pk_clearance', 'pk_half_life'] }],
    notes: 'ChatMessage.tsx:877-882 (three independent deepFinds combined into one object). Rendered ~3390.',
  },
  {
    id: 'qchem',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'qchem',
    cardComponent: 'QuantumChemBoundaryCard',
    requiredKeys: [{ path: 'quantum_chem_advantage_boundary' }],
    notes: 'ChatMessage.tsx:883-886 (deepFind). Rendered ~3391.',
  },
  {
    id: 'trustBadges',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'trustBadges',
    cardComponent: 'TrustBadgesCard',
    requiredKeys: [{ path: 'validated', alsoPaths: ['component', 'badge'] }],
    notes: "ChatMessage.tsx:887-899 — recursive 5-deep walk collecting objects that look like a trust badge (has 'validated'/'component'/'badge' but is NOT a {status, messages[]} banner). Requires at least one match. Rendered ~3392.",
  },
  {
    id: 'selectivity',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'selectivity',
    cardComponent: 'SelectivityCard',
    requiredKeys: [{ path: 'selectivity_panel.selectivity_score', alsoPaths: ['selectivity.selectivity_score', 'selectivity_panel.n_tested', 'selectivity_panel.targets', 'selectivity_panel.matrix', 'selectivity_panel.off_targets'] }],
    notes: 'ChatMessage.tsx:900-918 — three accepted shapes (profile_compound / build_selectivity_matrix / quantum-proxy off_targets). Rendered ~3393.',
  },
  {
    id: 'translational',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'translational',
    cardComponent: 'TranslationalSafetyCard',
    requiredKeys: [{ path: 'structural_alerts', alsoPaths: ['dose_response_model', 'pharmacogenomics', 'functional_engagement'] }],
    notes: 'ChatMessage.tsx:921-935 (four independent deepFinds combined). Rendered ~3394.',
  },
  {
    id: 'bionemoAug',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'bionemoAug',
    cardComponent: 'BioNeMoAugCard',
    requiredKeys: [{ path: 'bionemo_msa', alsoPaths: ['msa_folding_uplift', 'bionemo_singlecell', 'quantum_cell_singlecell_xcheck'] }],
    notes: 'ChatMessage.tsx:960-967. Rendered ~3397.',
  },
  {
    id: 'antibodyBench',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'antibodyBench',
    cardComponent: 'AntibodyBenchmarkCard',
    requiredKeys: [{ path: 'biophi_humanness', alsoPaths: ['abbibench_zeroshot', 'abbind_ddg', 'abag_interaction', 'flab_developability', 'denovo_binder_design'] }],
    notes: 'ChatMessage.tsx:968-975 (deepFind over a fixed list of 6 sub-keys). Rendered ~3398.',
  },
  {
    id: 'audit',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'audit',
    cardComponent: 'AuditPanel',
    requiredKeys: [{ path: 'audit' }],
    notes: 'ChatMessage.tsx:977-979. Rendered ~3399.',
  },
  {
    id: 'insights',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'insights',
    cardComponent: 'InsightCard',
    requiredKeys: [{ path: 'insights', alsoPaths: ['best_candidate_full.insights'] }],
    notes: 'ChatMessage.tsx:710-713, must be a non-empty array (checked again at render time, ~3377-3380).',
  },
  {
    id: 'validation',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'validation',
    cardComponent: 'ValidationBanner',
    requiredKeys: [{ path: 'validation' }],
    notes: 'ChatMessage.tsx:705. Rendered ~3333-3335.',
  },
  {
    id: 'provenance',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'provenance',
    cardComponent: 'ProvenancePanel',
    requiredKeys: [{ path: 'provenance', alsoPaths: ['best_candidate_full.provenance'] }],
    notes: 'ChatMessage.tsx:706-709. Rendered ~3407-3409.',
  },
  {
    id: 'molecularRelationships',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'molecularRelationships',
    cardComponent: 'MolecularRelationshipGraph',
    requiredKeys: [{ path: 'molecular_relationships', alsoPaths: ['best_candidate_full.molecular_relationships'] }],
    notes: 'ChatMessage.tsx:717-720. Rendered ~3402-3404.',
  },
  {
    id: 'externalValidation',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'externalValidation',
    cardComponent: 'ClinicalValidationPanel',
    requiredKeys: [{ path: 'external_validation' }],
    notes: 'ChatMessage.tsx:721. Rendered ~3412-3414.',
  },
  {
    id: 'visualization',
    pipeline: null,
    dispatchedFrom: 'ChatMessage.extractPipelineData',
    enrichmentKey: 'visualization',
    cardComponent: 'PipelineVisualization',
    requiredKeys: [{ path: 'visualization' }],
    notes: 'ChatMessage.tsx:821-827 — the "universal visualization envelope", emitted by _attach_visualizations across all pipeline types. Rendered ~2983-2986.',
  },
];

/** Result of resolveKey(): whether the spec's value was found, and where. */
interface ResolveResult {
  present: boolean;
  resolvedPath?: string;
  value?: unknown;
}

/** Resolves a dot-path (e.g. "stages.1_protein_design.mature_length_aa") against a plain object. */
export function getPath(obj: unknown, path: string): unknown {
  if (obj == null) return undefined;
  const parts = path.split('.');
  let cur: any = obj;
  for (const part of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[part];
  }
  return cur;
}

function isNonEmpty(value: unknown): boolean {
  if (value === undefined || value === null || value === '') return false;
  if (Array.isArray(value) && value.length === 0) return false;
  if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value as object).length === 0) return false;
  return true;
}

/** Evaluates one RequiredKeySpec against a pipeline result root. */
export function resolveRequiredKey(root: unknown, spec: RequiredKeySpec): ResolveResult {
  const candidates = [spec.path, ...(spec.alsoPaths ?? [])];
  for (const path of candidates) {
    const value = getPath(root, path);
    if (spec.mustBePositive) {
      const n = typeof value === 'number' ? value : NaN;
      if (Number.isFinite(n) && n > 0) return { present: true, resolvedPath: path, value };
      continue;
    }
    if (isNonEmpty(value)) return { present: true, resolvedPath: path, value };
  }
  return { present: false };
}

export interface CardEvaluation {
  entry: CardRegistryEntry;
  renderable: boolean;
  missing: RequiredKeySpec[];
  resolved: Record<string, unknown>;
}

/**
 * Evaluates a single registry entry against a real pipeline result's `result`
 * object (i.e. the value the frontend receives as `tool.output.result` /
 * JSON.parse(tool.output).result). Returns whether every requiredKey
 * resolved to a present (or, when `mustBePositive`, positive) value.
 */
export function evaluateCard(entry: CardRegistryEntry, root: unknown): CardEvaluation {
  const missing: RequiredKeySpec[] = [];
  const resolved: Record<string, unknown> = {};
  for (const spec of entry.requiredKeys) {
    const r = resolveRequiredKey(root, spec);
    if (!r.present) missing.push(spec);
    else resolved[spec.path] = r.value;
  }
  return { entry, renderable: missing.length === 0, resolved, missing };
}

/** Returns the registry entries whose `pipeline` matches root.pipeline (or is pipeline-agnostic, i.e. null). */
export function entriesForPipeline(pipelineName: string | undefined | null): CardRegistryEntry[] {
  return CARD_REGISTRY.filter((e) => e.pipeline === null || e.pipeline === pipelineName);
}

/** Evaluates every registry entry applicable to this result's pipeline against the result itself. */
export function evaluateAllForResult(root: any): CardEvaluation[] {
  const pipelineName = root?.pipeline as string | undefined;
  return entriesForPipeline(pipelineName).map((entry) => evaluateCard(entry, root));
}
