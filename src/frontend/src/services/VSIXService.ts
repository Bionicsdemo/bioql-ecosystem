// ============================================
// VSIX SERVICE - DeepSeek LLM Integration with MCP Tool Execution
// ============================================
// Uses OpenRouter/DeepSeek and actively executes MCP tools
// This allows the UI to use DeepSeek for quantum drug discovery with REAL tool execution

import { mcpClient, MCPToolResult, BIOQL_MCP_TOOLS } from './MCPClient';
import { quantumJobManager, QuantumJobManager } from './QuantumJobManager';
import { parseMultipleTargets, formatTargetsForWorkflow, extractTargetsDynamically } from './targetParser';
import { applyToolRouting, shouldDirectRouteVeterinaryAntibodyDesign } from './chatToolRouting';
import { QuantumJob, QuantumJobProgressUpdate, QuantumJobSubmission } from '../types/quantum';
import { renderDeterministicReport } from './deterministicReport';

// Helper for UUID (crypto.randomUUID not available in non-secure contexts)
const generateUUID = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export interface VSIXConfig {
  openRouterKey?: string;
  bioqlApiKey?: string;
  model?: string;
}

export interface VSIXMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  toolCalls?: VSIXToolCall[];
}

export interface VSIXToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  output?: unknown;
  error?: string;
  /** Backend pipeline session id (X-Pipeline-Session), when this tool call
   * hit a streaming_pipeline_response()-wrapped route. */
  pipelineSessionId?: string;
}

// Build dynamic system prompt - QUANTUM ONLY, STRICT FORMAT
const buildSystemPrompt = () => {
  return `You are BioQL Quantum AI. Backend: IBM Boston 156Q (156 qubits).

═══════════════════════════════════════════════════════════════
                    HOW TO EXTRACT TARGET PROTEIN
═══════════════════════════════════════════════════════════════

The TARGET is the protein/enzyme/receptor the user mentions. Extract it EXACTLY as written. If the user specifies multiple targets (e.g. "GLP1R, GIP, GCGR" or co-agonists), preserve all of them comma-separated or space-separated so they are passed intact. Do NOT pick only one or discard others.

PATTERN RECOGNITION:
- "drugs for X" → target = "X"
- "inhibitor for X" → target = "X"
- "against X" → target = "X"
- "targeting X" → target = "X"
- "X inhibitors" → target = "X"
- "treat Y disease" → target = main protein for Y disease
- "peptides for X" → target = "X"
- "antibody against X" → target = "X"
- "nanobody for X" → target = "X"

═══════════════════════════════════════════════════════════════
          TOOL SELECTION RULES (READ FIRST! CRITICAL!)
🚨 HIGHEST PRIORITY — PEPTIDES/PROTEINS/ANTIBODIES (overrides ALL other rules):
If the request involves peptides, proteins, antibodies, or amino acid sequences:
→ NEVER convert peptides/proteins to SMILES
→ NEVER use multi_pipeline or full_drug_development for peptides/proteins
→ ALWAYS use peptide_discovery — it handles BOTH de novo design AND scaffold-based optimization
→ NEVER hallucinate or invent amino acid sequences that the user did not explicitly provide
→ The design pipeline (antibody_cdr_design / peptide_discovery) ALREADY computes docking, MM-GBSA binding free energy, ADMET, immunogenicity, PK and toxicology INTERNALLY. For a design request, emit EXACTLY ONE pipeline tool call. NEVER emit separate binding_free_energy, docking, admet, toxicology or pharmacology tool calls for it — those are sub-steps of the pipeline, not standalone tools here.

TOOL: peptide_discovery (TOOL 3)
   Arguments: {"target": "<receptor from user message>", "indication": "<disease from user message>", "peptide_length": <infer from context or omit>}
   - target = extract the receptor/protein target from user's message
   - indication = extract disease/condition from user's message
   - peptide_length = only set if user specifies length, otherwise omit

ONLY use protein_engineering_pipeline if the user provides an EXPLICIT amino acid sequence (uppercase letters ≥8 chars) in their message. Mentioning a protein by NAME is NOT a sequence — use peptide_discovery.

⚠️ PRIORITY RULE: If user provides a SMILES (contains brackets [], rings, =O, etc.) + asks for "all pipelines", "comprehensive", "complete", "multi-pipeline", or lists 3+ pipeline names → ALWAYS use multi_pipeline (TOOL 42), NEVER full_drug_development.
⚠️ PRIORITY RULE: If user mentions "patent_analysis", "retrosynthesis_planning", "pbpk_modeling", "manufacturing_analysis", "cdx_design", "rwe_analysis", "pharmacovigilance", "regulatory_analysis", "multispecies_tox", or "formulation_optimization" → ALWAYS use multi_pipeline (TOOL 42).
⚠️ PRIORITY RULE: If user sends patient data (age + conditions/medications/labs/vitals/genomics, OR a clinical narrative like "Patient is a 62 y/o...", OR an EHR/FHIR/HL7/VCF block) WITHOUT a SMILES target molecule → ALWAYS use patient_future_health (TOOL 43), NEVER full_drug_development or custom_molecule.
🧬 PRIORITY RULE (mRNA — overrides fusion_protein_design): If the request mentions mRNA, mRNA vaccine, mRNA-encoded protein, codon optimization, LNP / lipid nanoparticle delivery, neoantigen, or a polyepitope cassette → ALWAYS use mrna_therapeutic_design, NEVER fusion_protein_design or generate_biomolecule. Set target_receptors to the REAL target(s) named in the message (e.g. KRAS, EGFR, HER2) — NEVER default to tau. Put any encoded peptide/epitope sequence in pharmacophore.
⚛️ PRIORITY RULE (QUANTUM SIMULATION): If the request mentions "simulate circuit", "quantum simulation", "GHZ", a number of "qubits", "statevector", "VQE", "ground state energy", or "tensor network" → route to the local/GPU quantum simulators, NEVER to drug-discovery pipelines:
   • Local simulation / a provided circuit (or QASM) / large qubit counts → quantum_mps_simulate (method="matrix_product_state" for large/low-entanglement, "statevector" for exact ≤29 qubits).
   • GHZ benchmark / GHZ state of N qubits → quantum_mps_ghz.
   • Exact statevector in the 30-40 qubit range / "GPU statevector" / cuStateVec → quantum_gpu_statevector.
   • Tensor-network / thousands of qubits on GPU → quantum_gpu_tensornet.
   • VQE ground-state energy from Pauli Hamiltonian terms → quantum_gpu_vqe.
   Gate format everywhere: {"gate":"h|x|y|z|rx|ry|rz|cx|cz","qubits":[...],"param":<float, only for rx/ry/rz>}. For cx/cz, qubits=[control,target].
═══════════════════════════════════════════════════════════════

STEP 1 - Identify request type from user's message:

| User asks about... | USE THIS TOOL |
|---|---|
| Drug discovery, design drugs, find molecules, novel compounds, full pipeline | full_drug_development |
| Quick lookup, simple target query (NO full pipeline) | quantum_fast_discovery |
| Peptide design, therapeutic peptide, cyclic peptide, PPI disruption | peptide_discovery |
| Antibody, nanobody, CDR design, VHH, scFv, bispecific | antibody_cdr_design |
| Protein engineering, stability, optimization | protein_engineering_pipeline |
| Enzyme optimization, catalytic activity | enzyme_activity_optimization |
| mRNA vaccine/therapeutic, mRNA-encoded protein, codon optimization, LNP delivery, neoantigen, polyepitope | mrna_therapeutic_design |
| Fusion protein, bispecific, Fc fusion (recombinant/CHO-expressed, NOT mRNA) | fusion_protein_design |
| Protein stability, thermal stability, aggregation | protein_stability_engineering |
| ADMET analysis (needs SMILES) | admet_standalone |
| Toxicology (needs SMILES) | toxicology_study |
| PK/PD, pharmacology (needs SMILES) | pharmacology_study |
| Clinical trial simulation (needs SMILES) | clinical_trial_simulation |
| 3D structure prediction, folding (ONLY after discovery) | protenix_structure_prediction |
| Off-target, selectivity, safety panel | quantum_offtarget_analysis |
| Drug combination, combination therapy, synergy, polypharmacology, drug-drug interaction (DDI), dose ratio/dose-response surface, resistance escape, multi-target pathway | combination_therapy |
| Rejuvenate/reverse aging of a tissue, epigenetic reprogramming, partial reprogramming, OSK/Yamanaka, epigenetic clock, methylation age, senescence reversal, "rejuvenecer", "revertir el envejecimiento", "reloj epigenetico" | rejuvenation_therapy |
| NOTE for rejuvenation_therapy: the prompt argument MUST repeat the user's request verbatim in THEIR language. The disease, tissue and function arguments MUST always be in ENGLISH (they are resolved against Open Targets, HPA and Gene Ontology, which are English-only). Example tissues: brain, pancreas, liver, kidney. Example functions: dopamine secretion, insulin secretion, learning or memory. | |
| Does the rejuvenation/epigenetic approach APPLY to this disease, mechanism fit, "aplica", "sirve para", "tiene sentido" + aging/rejuvenation | mechanism_fit_gate |
| CRISPR, gene editing, base editor, prime editor, Cas9/Cas12/Cas12f, knockout/knock-in, guide RNA design | crispr_editor_design |
| Compare modalities, peptide vs antibody, modality head-to-head, which modality is best | modality_comparison |
| Pocket-conditioned / structure-based de novo design, design molecules for a binding pocket | pocket_design |
| Personalized medicine, PGx, patient dosing | personalized_medicine |
| Retrosynthesis, synthetic route | retrosynthesis_planning |
| PBPK, tissue distribution | pbpk_modeling |
| Formulation, excipients | formulation_optimization |
| Patent, IP, freedom-to-operate | patent_analysis |
| Regulatory, FDA pathway | regulatory_analysis |
| Multi-species toxicology | multispecies_tox |
| Pharmacovigilance, adverse events | pharmacovigilance |
| Real-world evidence | rwe_analysis |
| Companion diagnostics, biomarker | cdx_design |
| Manufacturing, scale-up, GMP | manufacturing_analysis |
| Molecular glue, ternary complex, degrader, DC50 | molecular_glue_discovery |
| Quantum VQE calculation | bioql_fmo_vqe |
| Quantum QAOA docking | bioql_dc_qaoa |
| Quantum benchmarking | bioql_benchmark_quantum_advantage |
| Simulate a quantum circuit, local quantum simulation, many/thousands of qubits, MPS | quantum_mps_simulate |
| GHZ state, GHZ benchmark, MPS scaling test | quantum_mps_ghz |
| GPU statevector (30-40 qubits exact), GPU quantum simulation, cuStateVec | quantum_gpu_statevector |
| Tensor-network simulation, thousands of qubits on GPU, cuTensorNet | quantum_gpu_tensornet |
| VQE ground-state energy from a Pauli Hamiltonian (on GPU) | quantum_gpu_vqe |
| Quantum-chemistry / electronic / ground-state energy of a MOLECULE (a SMILES or named small molecule); "is the energy right vs FCI"; SQD | quantum_chemistry |

STEP 2 - CRITICAL RULES:
- NEVER use protenix_structure_prediction as the FIRST tool
- For peptides/proteins → use peptide_discovery or protein_engineering_pipeline FIRST
- For antibodies/nanobodies → use antibody_cdr_design FIRST
- Only call ONE tool per response (never multiple)
- If a tool needs SMILES but you don't have one, run quantum_fast_discovery FIRST

═══════════════════════════════════════════════════════════════
                    ALL AVAILABLE TOOLS
═══════════════════════════════════════════════════════════════

--- DRUG DISCOVERY PIPELINES ---

TOOL 1: full_drug_development  ⭐ DEFAULT for SIMPLE drug discovery
- Use for: SIMPLE drug discovery from scratch with just a target. Runs: discovery + 78 quantum algos + ADMET + tox + pharma + clinical.
- Arguments: {"target": "PROTEIN_NAME", "start_from": "discovery"}
- NOTE: Use this when user provides ONLY a target with no existing SMILES and wants basic discovery.
- DO NOT USE if user mentions: "multi-pipeline", "all pipelines", "complete analysis", "patent analysis", "retrosynthesis", "PBPK", "manufacturing", "regulatory", "CDx", "RWE", "pharmacovigilance", "formulation", "personalized medicine" — use TOOL 42 multi_pipeline instead.

TOOL 42: multi_pipeline  ⭐⭐ USE FOR COMPLETE/COMPREHENSIVE ANALYSIS
- Use for: comprehensive analysis, ALL pipelines, complete drug development, chains 17+ pipelines sequentially on a SPECIFIC molecule (SMILES required).
- Runs: run_78_algorithms + admet_standalone + toxicology_study + pharmacology_study + clinical_trial_simulation + retrosynthesis_planning + pbpk_modeling + formulation_optimization + patent_analysis + regulatory_analysis + multispecies_tox + pharmacovigilance + rwe_analysis + cdx_design + manufacturing_analysis + quantum_offtarget_analysis + personalized_medicine
- Arguments: {"smiles": "REQUIRED_SMILES", "target": "PROTEIN_NAME", "indication": "DISEASE", "pipelines": ["run_78_algorithms","admet_standalone","toxicology_study","pharmacology_study","clinical_trial_simulation","retrosynthesis_planning","pbpk_modeling","formulation_optimization","patent_analysis","regulatory_analysis","multispecies_tox","pharmacovigilance","rwe_analysis","cdx_design","manufacturing_analysis","quantum_offtarget_analysis","personalized_medicine"]}
- THIS IS THE PRIMARY TOOL when user requests: "all pipelines", "complete", "comprehensive", "full analysis", "multi-pipeline", "run all", "every pipeline", "entire pipeline", or explicitly mentions multi_pipeline.
- REQUIRES: smiles field (concrete molecule). If user gives a SMILES, ALWAYS use multi_pipeline for comprehensive analysis.

TOOL 2: quantum_fast_discovery (LEGACY - only for quick lookups)
- Use for: quick target query, simple lookup, when user explicitly says "quick" or "fast"
- Arguments: {"target": "PROTEIN_NAME"}
- NOTE: For full drug discovery, use full_drug_development instead

TOOL 7: peptide_discovery
- Use for: therapeutic peptides, cyclic peptides, PPI disruption, peptide design, de novo peptide, stapled peptide
- Arguments: {"target": "PROTEIN_NAME", "indication": "DISEASE"}
- NOTE: Use this for ANY peptide-related request. Both target and indication must
  be explicitly supplied by the user. Add pdb_id only when the user supplied
  that exact PDB; never infer one from a target or copy one from an example.

TOOL 8: custom_molecule_pipeline
- Use for: custom molecule from SMILES or motifs through full pipeline
- Arguments: {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "target": "PROTEIN_NAME"}

--- PROTEIN ENGINEERING ---

TOOL 9: protein_engineering_pipeline
- Use for: protein/peptide/antibody optimization, multi-agent design pipeline
- Arguments: {"sequence": "MKVLW...", "target_functions": ["binding_affinity"], "optimization_goals": ["improve stability"], "n_variants": 10}

TOOL 10: antibody_cdr_design
- Use for: antibody CDR loop design, antigen binding, humanization, affinity maturation
- Arguments: {"antigen": "PD-L1", "cdr_loops": ["H1", "H3"], "framework": "IgG1", "n_designs": 5}

TOOL 11: enzyme_activity_optimization
- Use for: enzyme improvement, catalytic activity, substrate specificity, kcat/Km
- Arguments: {"enzyme_sequence": "MVKKL...", "enzyme_class": "hydrolase", "substrate": "CC(=O)O", "optimization_target": "kcat/Km"}

TOOL 12: protein_stability_engineering
- Use for: thermal stability, aggregation resistance, pH tolerance
- Arguments: {"sequence": "MKVLW...", "stability_type": "thermal", "target_tm_increase": 10, "n_variants": 10}

TOOL 14: fusion_protein_design
- Use for: fusion proteins, bispecifics, Fc fusions, chimeric designs, linker optimization
- Arguments: {"domain1": "GLP-1", "domain2": "GIP", "target_functions": ["dual agonism"], "n_designs": 5}

TOOL 15: pdc_design
- Use for: peptide-drug conjugate (PDC) design — joint peptide carrier + linker + cytotoxic payload
  (e.g. "design a PDC", "conjugate this peptide to MMAE", "ADC-style peptide conjugate")
- Arguments: {"peptide_sequence": "DWLKAFYDKVAEKLKEAFC", "payload_key": "mmae", "indication": "solid tumor"}
  (payload_key is OPTIONAL — omit it to rank all compatible payload x linker combinations.
  Valid payload_key values: mmae, mmaf, dm1, sn38, exatecan_derivative)

TOOL 16: adar_sensor_design
- Use for: ADAR-editing RNA sensor / translational switch design (conditional/cell-signature-gated
  mRNA payload expression — e.g. "design an ADAR sensor switch", "RNA editing translational control")
- Arguments: {"payload_sequence": "AUG...", "ecs_sequence": "OPTIONAL editing-complementary sequence"}

--- ADMET / SAFETY / PK (require SMILES) ---

TOOL 3: toxicology_study
- Use for: toxicity, safety, LD50, AMES, hERG, genotoxicity
- Arguments: {"smiles": "VALID_SMILES_STRING"}

TOOL 4: pharmacology_study
- Use for: PK/PD, pharmacokinetics, dose-response, mechanism
- Arguments: {"smiles": "VALID_SMILES_STRING", "target": "PROTEIN_NAME"}

TOOL 5: clinical_trial_simulation
- Use for: clinical trials Phase I/II/III, FDA approval prediction
- Arguments: {"smiles": "VALID_SMILES_STRING", "indication": "DISEASE"}

TOOL 6: admet_standalone
- Use for: ADMET (92 parameters), absorption, distribution, metabolism, excretion, toxicity
- Arguments: {"smiles": "VALID_SMILES_STRING"}

--- STRUCTURE PREDICTION (use AFTER discovery) ---

TOOL 13: protenix_structure_prediction
- Use for: 3D protein structure, protein-ligand complex, protein-peptide complex (AlphaFold3-equivalent)
- NEVER use as first tool. Use AFTER a discovery pipeline.
- Arguments: {"target": "PROTEIN_NAME"} or {"target_sequence": "SEQUENCE", "ligand_smiles": "SMILES"}

--- ADVANCED PIPELINES (require SMILES) ---

TOOL 29: quantum_offtarget_analysis
- Use for: off-target, selectivity, safety panel, hERG/CYP screening
- Arguments: {"smiles": "VALID_SMILES_STRING", "target_uniprot": "P00533"}

TOOL 30: personalized_medicine
- Use for: personalized medicine, PGx, patient dosing, CYP genotype
- Arguments: {"smiles": "VALID_SMILES_STRING", "consent_obtained": true, "patient_data": {"age": 55, "weight_kg": 70, "sex": "male", "genotypes": {"CYP2D6": "*1/*4"}}}

TOOL 31: retrosynthesis_planning
- Use for: retrosynthesis, synthetic route, how to make a molecule
- Arguments: {"smiles": "VALID_SMILES_STRING", "max_steps": 5}

TOOL 32: pbpk_modeling
- Use for: PBPK, tissue distribution, multi-compartment PK
- Arguments: {"smiles": "VALID_SMILES_STRING", "dose_mg": 100, "route": "oral"}

TOOL 33: formulation_optimization
- Use for: formulation, excipients, drug delivery, dissolution
- Arguments: {"smiles": "VALID_SMILES_STRING", "route": "oral", "target_release": "immediate"}

TOOL 34: patent_analysis
- Use for: patent landscape, IP, freedom-to-operate, novelty
- Arguments: {"smiles": "VALID_SMILES_STRING", "target": "PROTEIN_NAME"}

TOOL 35: regulatory_analysis
- Use for: FDA pathway, eCTD, breakthrough, fast track, 505(b)
- Arguments: {"smiles": "VALID_SMILES_STRING", "indication": "DISEASE", "target": "PROTEIN_NAME"}

TOOL 36: multispecies_tox
- Use for: multi-species toxicology, allometric scaling, HED
- Arguments: {"smiles": "VALID_SMILES_STRING", "species": ["rat", "dog", "monkey"]}

TOOL 37: pharmacovigilance
- Use for: adverse events, post-market safety, signal detection, FAERS
- Arguments: {"smiles": "VALID_SMILES_STRING", "indication": "DISEASE"}

TOOL 38: rwe_analysis
- Use for: real-world evidence, treatment outcomes, comparative effectiveness
- Arguments: {"smiles": "VALID_SMILES_STRING", "indication": "DISEASE"}

TOOL 39: cdx_design
- Use for: companion diagnostics, biomarker, patient stratification
- Arguments: {"smiles": "VALID_SMILES_STRING", "target": "PROTEIN_NAME", "indication": "DISEASE"}

TOOL 40: manufacturing_analysis
- Use for: manufacturing, scale-up, GMP, green chemistry, COGS
- Arguments: {"smiles": "VALID_SMILES_STRING", "target_scale_kg": 1.0}

TOOL 41: molecular_glue_discovery
- Use for: molecular glue, ternary complex, degrader, DC50, Dmax, neo-substrate, cooperativity, CRBN, VHL
- Arguments: {"smiles": "VALID_SMILES_STRING", "target": "PROTEIN_NAME", "e3_ligase": "CRBN", "mode": "full"}

TOOL 43: patient_future_health  ⭐ PATIENT CLINICAL TWIN ORACLE
- Use for: patient future health prediction, clinical trajectory forecasting, future disease risk, personalized drug development based on patient EHR / history. ANY prompt that contains patient clinical data (age + conditions + medications + labs, OR free clinical narrative, OR FHIR/HL7/VCF input).
- ⚠️ PRIORITY RULE: If the user sends patient medical data (age, conditions, medications, labs, vitals, genomics, family history, clinical notes, or a case starting with "Patient" / "paciente" / "case" / "historia clinica") → ALWAYS use TOOL 43, NEVER full_drug_development or custom_molecule.
- Runs: patient_data_ingestion → OpenMed NER/PII/GWAS enrichment → quantum_clinical_oracle (4 real IBM Boston jobs: QFT-Time + Q-Markov + QBayes-Clinical + Q-Survival) → PGx-adjusted ADMET on current meds (quantum_batch_predictor with QFE) → disease atlas lookup → recommended actions → optional de novo drug design.
- Arguments: {"json": {"patient_id": "anonymous", "age": N, "sex": "M/F", "ethnicity": "...", "conditions": [...], "medications": [...], "labs": [...], "vitals": {...}, "family_history": [...], "social_history": {...}, "genomics": [...]}, "text": "optional_clinical_narrative", "include_drug_design": false, "time_horizons_years": [1, 3, 5, 10]}
- Minimum: at least ONE of json/text/fhir_bundle/hl7/vcf keys must be present.
- Returns: disease probability timeline per horizon, quantum-predicted survival curve, PGx-adjusted drug plan, medication recommendations, dominant future disease risk, and 10+ real IBM Boston job IDs.

--- QUANTUM TOOLS (advanced) ---

TOOL 15: bioql_fmo_vqe
- Use for: Fragment Molecular Orbital VQE energy calculation
- Arguments: {"molecule_smiles": "VALID_SMILES_STRING", "num_qubits": 8, "backend": "ibm_boston"}

TOOL quantum_chemistry: quantum_chemistry
- Use for: the REAL quantum-chemistry electronic / ground-state energy of a MOLECULE (a SMILES or a small named molecule), validated against exact FCI via SQD. Use when the user asks "the quantum energy of X", "ground-state energy of this molecule", "is the energy right / vs FCI", or mentions SQD on a molecule. Best for SMALL molecules (it returns an honest "too large" if the active space is too big).
- Arguments: {"smiles": "VALID_SMILES_STRING"}   (or {"atom": "H 0 0 0; H 0 0 0.74"})
- Returns a real electronic energy in Hartree + the error vs exact FCI (NOT a binding affinity).

TOOL 16: bioql_dc_qaoa
- Use for: Divide-and-Conquer QAOA molecular docking
- Arguments: {"protein_pdb": "5C7N", "ligand_smiles": "VALID_SMILES_STRING", "backend": "ibm_boston"}

TOOL 17: bioql_benchmark_quantum_advantage
- Use for: quantum benchmarking, advantage demonstration
- Arguments: {"test_type": "vqe", "num_qubits": 12, "backends": ["ibm_boston"]}

--- QUANTUM SIMULATORS (local MPS + Modal GPU CUDA-Q) ---

TOOL 44: quantum_mps_simulate
- Use for: "simulate this circuit", local quantum simulation, large qubit counts (MPS scales to THOUSANDS of qubits), or when the user supplies a circuit / QASM.
- Arguments: {"circuit_spec": {"n_qubits": 2, "gates": [{"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]}]}, "method": "matrix_product_state", "shots": 1024}
- method = "statevector" for exact simulation ≤29 qubits, "matrix_product_state" for large/low-entanglement circuits. Optional: max_bond_dimension. Alternative to circuit_spec: pass "qasm".

TOOL 45: quantum_mps_ghz
- Use for: GHZ benchmark, GHZ state, MPS scaling tests with many qubits.
- Arguments: {"n_qubits": 50, "shots": 1024}

TOOL 46: quantum_gpu_statevector
- Use for: exact statevector simulation in the 30-40 qubit range on a Modal A100 GPU (NVIDIA cuStateVec).
- Arguments: {"spec": {"n_qubits": 2, "gates": [{"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]}]}, "shots": 1024}

TOOL 47: quantum_gpu_tensornet
- Use for: tensor-network simulation of THOUSANDS of qubits on GPU (CUDA-Q cuTensorNet).
- Arguments: {"spec": {"n_qubits": 1000, "gates": [...]}, "shots": 1024, "max_bond": 64}  (or {"n_qubits": 1000, "shots": 1024})

TOOL 48: quantum_gpu_vqe
- Use for: VQE ground-state energy from a Pauli Hamiltonian on GPU.
- Arguments: {"hamiltonian_terms": [{"coeff": -1.05, "paulis": [["z", 0]]}, {"coeff": 0.39, "paulis": [["z", 0], ["z", 1]]}]}

Gate format for all simulator tools: {"gate": "h|x|y|z|rx|ry|rz|cx|cz", "qubits": [...], "param": <float, only for rx/ry/rz>}. For cx/cz, qubits = [control, target].

═══════════════════════════════════════════════════════════════
                    EXACT FORMAT REQUIRED
═══════════════════════════════════════════════════════════════

[TOOL_CALL]
{"tool": "TOOL_NAME", "arguments": {"key": "value"}}
[/TOOL_CALL]

═══════════════════════════════════════════════════════════════
                    STRICT RULES
═══════════════════════════════════════════════════════════════

1. EXTRACT target protein from user's message
0. DEFAULT: When in doubt about which discovery tool to use, ALWAYS choose full_drug_development
2. ONLY use the 25 tools listed above
3. ONLY use arguments shown for each tool
4. For full_drug_development ALWAYS include start_from="discovery"
5. MULTIPLE PIPELINES PER MESSAGE: If the user asks for SEVERAL distinct modalities/analyses in ONE message — e.g. "design an antibody AND an mRNA AND a CRISPR editor for HER2", or "(1) an antibody (2) a small molecule (3) compare them" — emit a SEPARATE [TOOL_CALL] block for EACH requested pipeline (one antibody_cdr_design, one mrna_therapeutic_design, one crispr_editor_design, etc.), up to 5 tool calls. Do NOT collapse a multi-modality request into a single pipeline and do NOT drop the others. For a SINGLE-modality request, use exactly ONE tool. Never call the SAME tool twice.
6. NEVER use protenix_structure_prediction as FIRST tool
7. For peptide requests → ALWAYS use peptide_discovery
8. For antibody/nanobody requests → ALWAYS use antibody_cdr_design
9. For enzyme requests → ALWAYS use enzyme_activity_optimization

❌ FORBIDDEN ARGUMENTS (NEVER USE):
   quantum_methods, disease, exclude_empirical_heuristics, quantum_uncertainty_analysis,
   mutation, optimization_level, or any parameter not listed above

⚠️ SMILES REQUIREMENT: Tools 3-6 and 29-40 need valid SMILES. If you don't have one, run quantum_fast_discovery FIRST.
⚠️ NEVER pass empty strings, "MOLECULE_SMILES", "TOP_CANDIDATE_SMILES", or English text as SMILES.
✅ Valid SMILES: "CC(=O)Oc1ccccc1C(=O)O" (aspirin), "c1ccc2ncnc(Nc3cccc(Br)c3)c2c1" (kinase inh)

═══════════════════════════════════════════════════════════════
                    EXAMPLES
═══════════════════════════════════════════════════════════════

User: "Find inhibitors for KRAS G12C"
[TOOL_CALL]
{"tool": "full_drug_development", "arguments": {"target": "KRAS G12C", "start_from": "discovery"}}
[/TOOL_CALL]

User: "Design therapeutic peptides targeting PD-L2 for melanoma"
[TOOL_CALL]
{"tool": "peptide_discovery", "arguments": {"target": "PDCD1LG2", "indication": "melanoma"}}
[/TOOL_CALL]

User: "Design a nanobody against TNF-alpha"
[TOOL_CALL]
{"tool": "antibody_cdr_design", "arguments": {"antigen": "TNF-alpha", "cdr_loops": ["H1", "H2", "H3"], "framework": "VHH", "n_designs": 8}}
[/TOOL_CALL]

User: "Full drug development for CDK4"
[TOOL_CALL]
{"tool": "full_drug_development", "arguments": {"target": "CDK4", "start_from": "discovery"}}
[/TOOL_CALL]

User: "Design 5 drug candidates for ALK neuroblastoma"
[TOOL_CALL]
{"tool": "full_drug_development", "arguments": {"target": "ALK", "start_from": "discovery"}}
[/TOOL_CALL]

User: "Optimize enzyme activity for lipase"
[TOOL_CALL]
{"tool": "enzyme_activity_optimization", "arguments": {"enzyme_sequence": "LIPASE", "enzyme_class": "hydrolase", "optimization_target": "kcat/Km"}}
[/TOOL_CALL]

User: "ADMET for aspirin"
[TOOL_CALL]
{"tool": "admet_standalone", "arguments": {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}}
[/TOOL_CALL]

User: "Analyze quantum combination therapy for TP53 in Li-Fraumeni syndrome, evaluate 5 combinations" (combination/synergy/polypharmacology/DDI/dose-ratio/resistance requests — the pipeline DESIGNS the drug combinations itself from the target; do NOT pass PDB IDs or call find_binding_pocket)
[TOOL_CALL]
{"tool": "combination_therapy", "arguments": {"target": "TP53", "indication": "Li-Fraumeni syndrome", "num_combinations": 5}}
{"tool": "rejuvenation_therapy", "arguments": {"prompt": "<echo the user's own request VERBATIM, in the user's language>", "disease": "Parkinson disease", "tissue": "brain", "function": "dopamine secretion"}}
{"tool": "mechanism_fit_gate", "arguments": {"disease": "breast carcinoma"}}
[/TOOL_CALL]

User: "Design a CRISPR base editor for PCSK9 in hypercholesterolemia"
[TOOL_CALL]
{"tool": "crispr_editor_design", "arguments": {"target": "PCSK9", "indication": "hypercholesterolemia"}}
[/TOOL_CALL]

User: "Compare peptide vs antibody modality for GLP1R in obesity"
[TOOL_CALL]
{"tool": "modality_comparison", "arguments": {"target": "GLP1R", "indication": "obesity"}}
[/TOOL_CALL]

User: "Design molecules for the EGFR binding pocket (structure-based)"
[TOOL_CALL]
{"tool": "pocket_design", "arguments": {"target": "EGFR", "n_candidates": 5}}
[/TOOL_CALL]

User: "Improve thermal stability of my protein MKVLWAALLV..."
[TOOL_CALL]
{"tool": "protein_stability_engineering", "arguments": {"sequence": "MKVLWAALLV...", "stability_type": "thermal", "target_tm_increase": 10, "n_variants": 10}}
[/TOOL_CALL]

User: "Design fusion protein combining GLP-1 and GIP"
[TOOL_CALL]
{"tool": "fusion_protein_design", "arguments": {"domain1": "GLP-1", "domain2": "GIP", "target_functions": ["dual agonism"], "n_designs": 5}}
[/TOOL_CALL]

═══════════════════════════════════════════════════════════════
`;
};

class VSIXService {
  private config: VSIXConfig = {
    openRouterKey: '',
    // La clave viene del entorno, nunca del código fuente.
    //
    // Aquí había una clave de API literal. Un secreto en el fuente no es un
    // secreto: viaja en cada clon, queda en el histórico de git para siempre, y
    // en un frontend acaba además dentro del bundle que se sirve al navegador,
    // donde cualquiera lo lee. Borrarlo después con un commit no lo quita del
    // historial; hay que reescribirlo y rotar la clave igual.
    //
    // Se sigue el mismo patrón que `openRouterKey`: vacío por defecto, y quien
    // arranca la app la inyecta. Si falta, las llamadas fallan con un 401 que se
    // ve — que es lo correcto — en vez de funcionar con una credencial que nadie
    // sabía que estaba ahí.
    bioqlApiKey: (import.meta as any).env?.VITE_BIOQL_API_KEY || '',
    model: 'deepseek/deepseek-chat',
  };
  private conversationHistory: Array<{ role: 'user' | 'assistant' | 'system'; content: string }> = [];
  private isConfiguredState: boolean = false;

  // ===== Tool routing (WS-9: pipeline_registry) =====
  // Hardcoded fallback — a COPY of the map this file used to hand-maintain
  // inline in executePipelineJob(). Kept verbatim so the app still works if
  // GET /api/tools/registry is unreachable (network/backend down): fail-open,
  // additive. The LIVE source of truth is now the backend's pipeline_registry
  // (src/backend/pipeline_registry.py) via fetchToolRoutesFromRegistry() below
  // — this is the actual fix for the host-drift bug class already confirmed
  // live in MCP's server.py (stale hardcoded PIPELINE_BACKEND_URL IP while the
  // backend itself moved on).
  private static readonly FALLBACK_TOOL_ROUTES: Record<string, string> = {
    'macrocycle_design': '/api/pipeline/macrocycle',
    'quantum_fast_discovery': '/api/quantum/fast_discovery',
    'full_drug_development': '/api/pipeline/full_development',
    'toxicology_study': '/api/pipeline/toxicology',
    'pharmacology_study': '/api/pipeline/pharmacology',
    'clinical_trial_simulation': '/api/pipeline/clinical_trial',
    'admet_standalone': '/api/pipeline/admet_standalone',
    'protenix_structure_prediction': '/api/protenix/predict/structure',
    'personalized_medicine': '/api/pipeline/personalized_medicine',
    'patient_future_health': '/api/pipeline/patient_future_health',
    'retrosynthesis_planning': '/api/pipeline/retrosynthesis',
    'pbpk_modeling': '/api/pipeline/pbpk',
    'formulation_optimization': '/api/pipeline/formulation',
    'patent_analysis': '/api/pipeline/patent_analysis',
    'regulatory_analysis': '/api/pipeline/regulatory',
    'multispecies_tox': '/api/pipeline/multispecies_tox',
    'veterinary_assessment': '/api/pipeline/veterinary',
    'veterinary_discovery': '/api/pipeline/veterinary_discovery',
    'veterinary_antibody_research': '/api/pipeline/veterinary_antibody',
    'molevera_veterinary_antibody_design': '/api/quantum/veterinary_antibody_design',
    'pharmacovigilance': '/api/pipeline/pharmacovigilance',
    'rwe_analysis': '/api/pipeline/rwe',
    'cdx_design': '/api/pipeline/cdx_design',
    'manufacturing_analysis': '/api/pipeline/manufacturing',
    'molecular_glue_discovery': '/api/pipeline/molecular_glue',
    'mrna_therapeutic_design': '/api/pipeline/mrna_therapeutic',
    'quantum_offtarget_analysis': '/api/quantum/offtarget/run',
    'combination_therapy': '/api/quantum/combination/full_pipeline',
    'crispr_editor_design': '/api/quantum/crispr_editor_design',
    'replicon_pipeline': '/api/quantum/replicon',
    'rejuvenation_therapy': '/api/aging/design',
    'mechanism_fit_gate': '/api/aging/gate',
    'quantum_antibody_cdr': '/api/quantum/antibody_cdr',
    'quantum_peptide_design': '/api/quantum/peptide_design',
    'biologic_complete': '/api/casestudy/biologic_complete',
    'bioql_gqe': '/api/quantum/gqe',
    'qdiffvision': '/api/quantum/qdiffvision',
    'modality_comparison': '/api/quantum/modality_comparison',
    'pocket_design': '/api/quantum/pocket_design',
    'peptide_discovery': '/api/quantum/peptide_discovery',
    'custom_molecule_pipeline': '/api/quantum/custom_molecule',
    'run_78_algorithms': '/api/quantum/run_78_pipeline',
    'multi_pipeline': '/api/quantum/multi_pipeline',
    'antibody_cdr_design': '/api/quantum/antibody_discovery',
    'enzyme_activity_optimization': '/api/quantum/generate_biomolecule',
    'protein_stability_engineering': '/api/quantum/generate_biomolecule',
    'fusion_protein_design': '/api/quantum/generate_biomolecule',
    'protein_engineering_pipeline': '/api/quantum/generate_biomolecule',
    'ewf_sqd': '/api/quantum/ewf_sqd',
    'quantum_chemistry': '/api/quantum/adapt_vqe',
    'proteina_complexa_design': '/api/complexa/design',
    'pdc_design': '/api/quantum/pdc_design',
    'adar_sensor_design': '/api/quantum/adar_sensor_design',
  };

  // Cache: populated once per session (first call wins; concurrent callers
  // await the same in-flight fetch instead of firing duplicate requests).
  private cachedToolRoutes: Record<string, string> | null = null;
  private toolRoutesFetchPromise: Promise<Record<string, string>> | null = null;

  /** Live registry (fail-open, cached) merged over the hardcoded fallback.
   * Registry entries only override routes for kind === 'http' pipelines
   * (the only kind with a real, addressable URL) — 'direct'/'smiles'/
   * 'proteomic' entries have no client-facing endpoint of their own today,
   * so those names keep resolving via the fallback dict / the generic
   * `/api/quantum/${toolName}` default in executePipelineJob(). */
  private async getToolRoutes(): Promise<Record<string, string>> {
    if (this.cachedToolRoutes) return this.cachedToolRoutes;
    if (!this.toolRoutesFetchPromise) {
      this.toolRoutesFetchPromise = this.fetchToolRoutesFromRegistry();
    }
    return this.toolRoutesFetchPromise;
  }

  private async fetchToolRoutesFromRegistry(): Promise<Record<string, string>> {
    const merged: Record<string, string> = { ...VSIXService.FALLBACK_TOOL_ROUTES };
    try {
      const res = await fetch('/api/tools/registry', { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        const tools: Array<{ name: string; kind: string; endpoint: string | null }> = data?.tools || [];
        for (const t of tools) {
          if (t && t.kind === 'http' && t.endpoint) {
            merged[t.name] = t.endpoint;
          }
        }
      } else {
        console.warn(`[VSIXService] /api/tools/registry returned HTTP ${res.status}; using hardcoded fallback routes`);
      }
    } catch (e) {
      console.warn('[VSIXService] /api/tools/registry fetch failed, using hardcoded fallback routes only:', e);
    }
    this.cachedToolRoutes = merged;
    return merged;
  }

  // ===== LOCAL MODE (LM Studio / OpenAI-compatible local server) =====
  // When enabled, the same tool-routing pipeline talks to a local model
  // (e.g. Qwen2.5-Coder) at /api/localllm (vite-proxied to 127.0.0.1:8001)
  // instead of OpenRouter. No API key required.
  private useLocal: boolean = false;
  private localBaseUrl: string = '/api/localllm';
  private localModel: string = 'lmstudio-community/Qwen2.5-Coder-7B-Instruct-MLX-4bit';

  enableLocalMode(model?: string) {
    this.useLocal = true;
    if (model) this.localModel = model;
    this.isConfiguredState = true;
  }
  disableLocalMode() {
    this.useLocal = false;
  }
  isLocalMode(): boolean {
    return this.useLocal;
  }
  getLocalModel(): string {
    return this.localModel;
  }

  // Validate the local model server is reachable (lists loaded models).
  async connectLocal(): Promise<boolean> {
    try {
      const res = await fetch(`${this.localBaseUrl}/v1/models`, { method: 'GET' });
      if (!res.ok) return false;
      const data = await res.json();
      const ids: string[] = Array.isArray(data?.data) ? data.data.map((m: any) => m.id) : [];
      if (ids.length > 0) this.localModel = ids[0]; // use whatever model is loaded
      console.log('✅ Local LLM connected:', this.localModel);
      this.useLocal = true;
      this.isConfiguredState = true;
      // WS-9: warm the tool-routes cache at connect time (fire-and-forget,
      // fail-open — see getToolRoutes()/fetchToolRoutesFromRegistry()).
      this.getToolRoutes().catch(() => {});
      return true;
    } catch (e) {
      console.error('Local LLM connection error:', e);
      return false;
    }
  }

  // Endpoint / headers / model resolve based on active mode (local vs OpenRouter).
  private chatUrl(): string {
    return this.useLocal
      ? `${this.localBaseUrl}/v1/chat/completions`
      : 'https://openrouter.ai/api/v1/chat/completions';
  }
  private chatHeaders(): Record<string, string> {
    if (this.useLocal) {
      // LM Studio ignores auth; send a placeholder to satisfy any middleware.
      return { 'Content-Type': 'application/json', 'Authorization': 'Bearer lm-studio' };
    }
    return {
      'Authorization': `Bearer ${this.config.openRouterKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://bioql.spectrix.io',
      'X-Title': 'BioQL Quantum UI',
    };
  }
  private chatModel(): string {
    return this.useLocal ? this.localModel : (this.config.model || 'deepseek/deepseek-chat');
  }

  configure(config: VSIXConfig) {
    this.config = { ...this.config, ...config };
    this.isConfiguredState = !!this.config.openRouterKey;
  }

  isConfigured(): boolean {
    if (this.useLocal) return true;
    return this.isConfiguredState && !!this.config.openRouterKey;
  }

  setOpenRouterKey(key: string) {
    this.config.openRouterKey = key;
    this.isConfiguredState = !!key;
  }

  getOpenRouterKey(): string {
    return this.config.openRouterKey || '';
  }

  // Connect - just validates the API key
  async connect(): Promise<boolean> {
    if (!this.config.openRouterKey) {
      console.log('DeepSeek: No OpenRouter key configured');
      return false;
    }

    try {
      // Test the API key with a simple request
      const response = await fetch('https://openrouter.ai/api/v1/models', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.config.openRouterKey}`,
        },
      });

      if (response.ok) {
        console.log('✅ DeepSeek/OpenRouter connected successfully');
        this.isConfiguredState = true;
        // WS-9: warm the tool-routes cache at connect time (fire-and-forget,
        // fail-open — see getToolRoutes()/fetchToolRoutesFromRegistry()).
        this.getToolRoutes().catch(() => {});
        return true;
      } else {
        console.error('DeepSeek: Invalid API key');
        this.isConfiguredState = false;
        return false;
      }
    } catch (error) {
      console.error('DeepSeek connection error:', error);
      this.isConfiguredState = false;
      return false;
    }
  }

  async disconnect() {
    this.conversationHistory = [];
    this.isConfiguredState = false;
  }

  // Clear conversation history
  clearHistory() {
    this.conversationHistory = [];
  }

  private extractTargetFromMessage(message: string): string {
    const targets = extractTargetsDynamically(message);
    if (targets.length > 0) {
      return formatTargetsForWorkflow(targets);
    }

    // Fallback: If no dynamic targets are found, try matching standard ones
    const lower = message.toLowerCase();
    const fallbackTargets: Record<string, string> = {
      'glp-1': 'GLP-1_receptor',
      'glp1': 'GLP-1_receptor',
      'egfr': 'EGFR_kinase',
      'her2': 'HER2_receptor',
      'bcr-abl': 'BCR-ABL_kinase',
      'cox-2': 'COX-2_cyclooxygenase',
      'cox2': 'COX-2_cyclooxygenase',
      'ace2': 'ACE2_receptor',
      'jak2': 'JAK2_kinase',
      'braf': 'BRAF_kinase',
      'kras': 'KRAS_GTPase',
      'pd-1': 'PD-1_checkpoint',
      'pd-l1': 'PD-L1_checkpoint',
      'vegfr': 'VEGFR_kinase',
      'ache': 'AChE_cholinesterase',
      'alzheimer': 'DUAL_AChE_TAU',
      'diabetes': 'GLP-1_receptor',
      'cancer': 'Oncology_multi',
      'inflammation': 'COX-2_cyclooxygenase',
      'pain': 'COX-2_cyclooxygenase'
    };

    for (const [key, value] of Object.entries(fallbackTargets)) {
      if (lower.includes(key)) {
        return value;
      }
    }

    const symbol = message.match(/\b[A-Z0-9]{2,12}\b/);
    return symbol?.[0] || '';
  }

  private extractIndicationFromMessage(message: string): string {
    const explicit = message.match(/Indication:\s*([^\n]+)/i)?.[1];
    if (explicit) return explicit.trim().replace(/[.;]+$/, '');
    return message.match(/\b(autoimmune|metabolic|oncology|cancer|inflammatory|neurologic|cardiovascular|infectious)\s+disease\b/i)?.[0] || '';
  }

  private extractPdbIdFromMessage(message: string): string | undefined {
    return message.match(/(?:pdb_id|Reference PDB|USE pdb_id|PDB):?\s*["']?([0-9][A-Za-z0-9]{3})/i)?.[1]?.toUpperCase();
  }

  private extractDesignCountFromMessage(message: string): number {
    const parsed = Number(message.match(/\b(?:design|generate|create)\s+(\d{1,2})\b/i)?.[1]);
    if (Number.isFinite(parsed) && parsed > 0) return Math.min(parsed, 20);
    return 5;
  }

  private getIntentSegment(message: string): string {
    const marker = message.search(/\n\s*(Target:|TargetRadar Score:|Chemical Tractability:|Binding Pocket Context:|Pipeline Instructions:|Tractability:)/i);
    return (marker > 0 ? message.slice(0, marker) : message).slice(0, 1500);
  }

  private detectBiologicToolFromPrompt(message: string): 'peptide_discovery' | 'antibody_cdr_design' | null {
    const intent = this.getIntentSegment(message).toLowerCase();
    const peptideMatch = intent.search(/therapeutic peptide|peptide candidates?|cyclic peptide|de novo\s+peptide|peptide\s+design|ppi disruption|protein-peptide/);
    const antibodyMatch = intent.search(/antibod|nanobod|vhh|scfv|bispecific|immunoglobulin|cdr(?:-| )?h?[123]?/);

    if (peptideMatch >= 0 && (antibodyMatch < 0 || peptideMatch < antibodyMatch)) return 'peptide_discovery';
    if (antibodyMatch >= 0 && (peptideMatch < 0 || antibodyMatch < peptideMatch)) return 'antibody_cdr_design';

    // Fallback for short prompts without TargetRadar context.
    const lower = message.toLowerCase();
    if (/therapeutic peptide|peptide candidates?|cyclic peptide|de novo\s+peptide|peptide\s+design|ppi disruption/.test(lower)) return 'peptide_discovery';
    if (/antibod|nanobod|vhh|scfv|bispecific|immunoglobulin|cdr/.test(lower)) return 'antibody_cdr_design';
    return null;
  }

  private buildForcedBiologicToolCall(message: string): { tool: string; arguments: Record<string, unknown> } | null {
    const requestedTool = this.detectBiologicToolFromPrompt(message);
    const target = this.extractTargetFromMessage(message);
    const pdb_id = this.extractPdbIdFromMessage(message);
    const indication = this.extractIndicationFromMessage(message);
    const n_designs = this.extractDesignCountFromMessage(message);

    if (requestedTool === 'peptide_discovery') {
      return {
        tool: 'peptide_discovery',
        arguments: {
          target,
          indication,
          n_designs,
          n_candidates: n_designs,
          ...(pdb_id ? { pdb_id } : {}),
        },
      };
    }

    if (requestedTool === 'antibody_cdr_design') {
      const intent = this.getIntentSegment(message).toLowerCase();
      return {
        tool: 'antibody_cdr_design',
        arguments: {
          antigen: target,
          target,
          indication,
          cdr_loops: ['H1', 'H2', 'H3'],
          framework: /nanobod|vhh/.test(intent) ? 'VHH' : 'IgG1',
          n_designs,
          ...(pdb_id ? { pdb_id } : {}),
        },
      };
    }

    return null;
  }

  // Deterministic small-molecule fallback: when the weak local router mis-routes a
  // SMILES + small-molecule request (e.g. to an orphan RBFE/mutation tool), force the
  // correct full small-molecule pipeline. Mirrors buildForcedBiologicToolCall.
  private buildForcedSmallMoleculeToolCall(message: string): { tool: string; arguments: Record<string, unknown> } | null {
    let smiles = '';
    const m = message.match(/SMILES[:\s]+([^\s\n]+)/i);
    if (m) smiles = m[1].trim();
    if (!smiles) {
      const toks = message.split(/\s+/);
      smiles = toks.find(t => t.length >= 10 && /[=#)\]]/.test(t) &&
        /^[A-Za-z0-9@+\-\[\]()=#%\/\\.]+$/.test(t) && /[cnospfCNOSPF]/.test(t)) || '';
    }
    if (!smiles || smiles.length < 8) return null;
    const target = this.extractTargetFromMessage(message);
    const indication = this.extractIndicationFromMessage(message);
    const pdb_id = this.extractPdbIdFromMessage(message);
    return {
      tool: 'custom_molecule_pipeline',
      arguments: {
        smiles,
        ...(target ? { target } : {}),
        ...(indication ? { indication } : {}),
        ...(pdb_id ? { pdb_id } : {}),
      },
    };
  }

  private shouldBypassLlmReport(toolName: string): boolean {
    return ['peptide_discovery', 'antibody_cdr_design'].some(name => toolName.includes(name));
  }

  private fmt(value: unknown, digits = 3): string {
    if (value === null || value === undefined || value === '') return 'N/A';
    if (typeof value === 'number') return Number.isFinite(value) ? value.toFixed(digits).replace(/\.?0+$/, '') : 'N/A';
    if (typeof value === 'object') {
      const obj = value as Record<string, unknown>;
      if (obj.value !== undefined) {
        const unit = obj.unit ? ` ${obj.unit}` : '';
        return `${this.fmt(obj.value, digits)}${unit}`;
      }
      if (obj.label) return String(obj.label);
      if (obj.class) return String(obj.class);
      return JSON.stringify(obj).slice(0, 120);
    }
    return String(value);
  }

  private collectCandidates(root: any): any[] {
    const discovery = root?.discovery || {};
    const direct = root?.candidates || root?.all_candidates || discovery?.candidates || discovery?.all_candidates;
    if (Array.isArray(direct)) return direct;
    const generated = root?.candidates_generated || discovery?.candidates_generated || {};
    return [
      ...(Array.isArray(generated.small_molecules) ? generated.small_molecules : []),
      ...(Array.isArray(generated.peptides) ? generated.peptides : []),
      ...(Array.isArray(generated.nanobodies) ? generated.nanobodies : []),
      ...(Array.isArray(generated.antibodies) ? generated.antibodies : []),
    ];
  }

  private countAdmetParameters(admet: any): number {
    if (!admet || typeof admet !== 'object') return 0;
    if (Number.isFinite(Number(admet.parameters_count))) return Number(admet.parameters_count);
    return ['absorption', 'distribution', 'metabolism', 'excretion', 'toxicity']
      .reduce((sum, key) => sum + (admet[key] && typeof admet[key] === 'object' ? Object.keys(admet[key]).length : 0), 0);
  }

  private buildDeterministicPipelineSummary(tools: VSIXToolCall[]): string {
    return tools.map(tool => {
      const output: any = tool.output || {};
      const root = output?.result || output;
      const candidates = this.collectCandidates(root);
      const count = Array.isArray(candidates) ? candidates.length : 0;
      const target = root?.target || root?.antigen || root?.target_name || (tool.input as any)?.target || (tool.input as any)?.antigen || 'target';
      const best = root?.best_candidate || root?.best_candidate_full || candidates[0] || {};
      const bestAdmet = best?.admet || best?.analyses?.admet || root?.admet || {};
      const admetCount = this.countAdmetParameters(bestAdmet);
      const reportRanking = Array.isArray(root?.report?.ranking) ? root.report.ranking : [];
      const ranking = reportRanking.length ? reportRanking : candidates.slice(0, 8).map((candidate: any, idx: number) => ({
        rank: candidate.rank || idx + 1,
        candidate_id: candidate.candidate_id || candidate.name || candidate.id || `Candidate ${idx + 1}`,
        composite_score: candidate.composite_score || candidate.score || candidate.scores?.composite_score,
        kd_nm: candidate.kd_nM || candidate.kd_nm || candidate.scores?.kd_nm || candidate.scores?.kd_nM,
        binding_affinity_kcal: candidate.binding_affinity_kcal || candidate.affinity || candidate.analyses?.docking?.binding_affinity_kcal,
        clinical_success: candidate.clinical_success_prob || candidate.scores?.clinical_success_prob || candidate.clinical_trial?.regulatory?.overall_success_probability,
        immunogenicity_risk: candidate.immunogenicity_risk || candidate.scores?.immunogenicity_risk || candidate.developability?.immunogenicity_risk,
      }));
      const stageNames = root?.stages && typeof root.stages === 'object'
        ? Object.values(root.stages).map((stage: any) => stage?.stage || '').filter(Boolean).slice(0, 16)
        : [];
      const jobIds = [
        ...(Array.isArray(root?.ibm_job_ids) ? root.ibm_job_ids : []),
        ...(Array.isArray(root?.simulator_job_ids) ? root.simulator_job_ids : []),
        ...(Array.isArray(root?.report?.simulator_job_ids) ? root.report.simulator_job_ids : []),
      ].filter(Boolean);
      const isAntibody = String(tool.name).includes('antibody') || String(root?.pipeline || '').toLowerCase().includes('antibody');
      const title = isAntibody ? 'Quantum Antibody Discovery Report' : 'Quantum Peptide Discovery Report';

      const candidateHeader = isAntibody
        ? '| Rank | Candidate | Format | CDR-H3 | KD nM | Humanization | Developability | Immunogenicity | Composite |\n|---|---|---|---|---:|---:|---:|---|---:|'
        : '| Rank | Candidate | Sequence | Length | KD nM | Binding kcal/mol | ADMET | Toxicology | Composite |\n|---|---|---|---:|---:|---:|---:|---:|---:|';
      const candidateRows = candidates.slice(0, 10).map((candidate: any, idx: number) => {
        if (isAntibody) {
          return `| ${candidate.rank || idx + 1} | ${candidate.candidate_id || candidate.name || candidate.id || 'N/A'} | ${candidate.format || root?.antibody_type || 'N/A'} | ${candidate.cdr_h3 || candidate.antibody_properties?.cdr_h3 || 'N/A'} | ${this.fmt(candidate.kd_nM || candidate.kd_nm || candidate.scores?.kd_nm)} | ${this.fmt(candidate.humanization_score || candidate.scores?.humanization_score)} | ${this.fmt(candidate.developability_score || candidate.developability?.developability_score || candidate.scores?.developability_score)} | ${this.fmt(candidate.immunogenicity_risk || candidate.scores?.immunogenicity_risk)} | ${this.fmt(candidate.composite_score || candidate.score || candidate.scores?.composite_score)} |`;
        }
        const sequence = candidate.sequence || candidate.peptide_sequence || candidate.name || 'N/A';
        return `| ${candidate.rank || idx + 1} | ${candidate.candidate_id || candidate.name || candidate.id || 'N/A'} | ${String(sequence).slice(0, 36)} | ${candidate.length || candidate.peptide_properties?.length || String(sequence).length || 'N/A'} | ${this.fmt(candidate.kd_nM || candidate.kd_nm || candidate.analyses?.docking?.kd_nM)} | ${this.fmt(candidate.binding_affinity_kcal || candidate.affinity || candidate.analyses?.docking?.binding_affinity_kcal)} | ${this.fmt(candidate.admet_score || candidate.analyses?.admet?.overall_admet_score)} | ${this.fmt(candidate.tox_score || candidate.analyses?.toxicology?.overall_score)} | ${this.fmt(candidate.composite_score || candidate.score)} |`;
      });

      const rankingRows = ranking.slice(0, 8).map((row: any, idx: number) =>
        `| ${row.rank || idx + 1} | ${row.candidate_id || row.name || 'N/A'} | ${this.fmt(row.composite_score)} | ${this.fmt(row.kd_nm)} | ${this.fmt(row.binding_affinity_kcal)} | ${this.fmt(row.clinical_success)} | ${this.fmt(row.immunogenicity_risk)} |`
      );

      const admetLines = ['absorption', 'distribution', 'metabolism', 'excretion', 'toxicity']
        .map(key => {
          const section = bestAdmet?.[key];
          if (!section || typeof section !== 'object') return '';
          const sample = Object.entries(section).slice(0, 6).map(([k, v]) => `${k}: ${this.fmt(v)}`).join('; ');
          return `- ${key}: ${sample}`;
        })
        .filter(Boolean);

      return [
        `# ${title}: ${target}`,
        '',
        '## Execution Summary',
        `- Pipeline: ${root?.pipeline || tool.name}`,
        `- Backend: ${root?.quantum_backend || root?.metadata?.quantum_backend || root?.quantum_hardware || 'N/A'}`,
        `- Candidates returned: ${count}`,
        `- Best candidate: ${best?.candidate_id || best?.name || root?.report?.lead_candidate || 'N/A'}`,
        `- ADMET parameters exposed: ${admetCount || 'N/A'}`,
        jobIds.length ? `- Quantum/simulator jobs: ${jobIds.slice(0, 8).join(', ')}${jobIds.length > 8 ? ` (+${jobIds.length - 8} more)` : ''}` : '',
        '',
        stageNames.length ? '## Pipeline Stages' : '',
        stageNames.length ? stageNames.map((name: string, idx: number) => `${idx + 1}. ${name}`).join('\n') : '',
        '',
        '## Candidate Table',
        candidateHeader,
        ...candidateRows,
        '',
        rankingRows.length ? '## Ranking / Score Breakdown' : '',
        rankingRows.length ? '| Rank | Candidate | Composite | KD nM | Binding kcal/mol | Clinical success | Immunogenicity |\n|---|---|---:|---:|---:|---:|---|' : '',
        ...rankingRows,
        '',
        admetLines.length ? `## ADMET Profile (${admetCount || admetLines.length} parameters)` : '',
        ...admetLines,
        '',
        'Full backend JSON is attached to the tool card below and saved for the Candidates page.',
      ].filter(line => line !== '').join('\n');
    }).join('\n\n');
  }

  // Extract key data from tool results for report generation
  private extractReportData(output: unknown, toolName: string): Record<string, unknown> {
    const data = output as Record<string, unknown>;
    if (!data) return {};
    const metadata = (data.metadata || {}) as Record<string, unknown>;
    const defaultQuantumBackend = toolName === 'antibody_cdr_design'
      ? 'Qiskit AerSimulator (local quantum mode)'
      : 'IBM_BOSTON_156Q';

    const extracted: Record<string, unknown> = {
      toolName,
      status: data.status || 'COMPLETED',
      target: data.target || data.antigen || data.target_name || data.target_protein || '',
      smiles: data.smiles || data.molecule_smiles || '',
      quantumBackend: data.quantum_backend || metadata.quantum_backend || defaultQuantumBackend,
    };

    // Extract based on study type
    if (toolName === 'pharmacology_study' && data.pharmacology) {
      const pharma = data.pharmacology as Record<string, unknown>;

      // Pharmacokinetics
      if (pharma.pharmacokinetics) {
        const pk = pharma.pharmacokinetics as Record<string, unknown>;
        extracted.absorption = pk.absorption;
        extracted.distribution = pk.distribution;
        extracted.metabolism = pk.metabolism;
        extracted.excretion = pk.excretion;
      }

      // Pharmacodynamics
      if (pharma.pharmacodynamics) {
        extracted.pharmacodynamics = pharma.pharmacodynamics;
      }

      // Efficacy
      if (pharma.efficacy_prediction) {
        extracted.efficacy = pharma.efficacy_prediction;
      }

      // DDI
      if (pharma.drug_drug_interactions) {
        extracted.ddi = pharma.drug_drug_interactions;
      }
    }

    if (toolName === 'toxicology_study' && data.toxicology) {
      const tox = data.toxicology as Record<string, unknown>;
      extracted.acuteToxicity = tox.acute_toxicity;
      extracted.genotoxicity = tox.genotoxicity;
      extracted.carcinogenicity = tox.carcinogenicity;
      extracted.organToxicity = tox.organ_toxicity;
      extracted.immunotoxicity = tox.immunotoxicity;
      extracted.reproductiveToxicity = tox.reproductive_toxicity;
      extracted.overallRisk = tox.overall_risk_assessment;
    }

    // ===== MULTI_PIPELINE specific extraction =====
    if (toolName === 'multi_pipeline' && Array.isArray(data.results)) {
      const mpResults = data.results as Array<Record<string, unknown>>;
      const stepsCompleted = (data.steps_completed as string[]) || [];
      const stepsFailed = (data.steps_failed as unknown[]) || [];
      extracted.finalSmiles = data.final_smiles || data.smiles;
      extracted.totalSteps = data.total_steps;
      extracted.stepsCompleted = stepsCompleted;
      extracted.stepsFailed = stepsFailed;
      extracted.executionTime = data.execution_time_seconds;
      extracted.ibmJobIds = data.ibm_job_ids || [];
      extracted.totalIbmJobs = (data.ibm_job_ids as unknown[])?.length || 0;

      // Group results by pipeline name
      const byPipeline: Record<string, unknown> = {};
      for (const item of mpResults) {
        const pname = item.pipeline as string;
        if (pname) byPipeline[pname] = item.result || item;
      }
      extracted.pipelineResults = byPipeline;

      // Map specific sections for the LLM to find easily
      extracted.run_78_algorithms = byPipeline['run_78_algorithms'];
      extracted.admet = byPipeline['admet_standalone'];
      extracted.toxicology = byPipeline['toxicology_study'];
      extracted.pharmacology = byPipeline['pharmacology_study'];
      extracted.clinicalTrial = byPipeline['clinical_trial_simulation'];
      extracted.retrosynthesis = byPipeline['retrosynthesis_planning'];
      extracted.pbpk = byPipeline['pbpk_modeling'];
      extracted.formulation = byPipeline['formulation_optimization'];
      extracted.patentAnalysis = byPipeline['patent_analysis'];
      extracted.regulatory = byPipeline['regulatory_analysis'];
      extracted.multispeciesTox = byPipeline['multispecies_tox'];
      extracted.pharmacovigilance = byPipeline['pharmacovigilance'];
      extracted.rwe = byPipeline['rwe_analysis'];
      extracted.cdxDesign = byPipeline['cdx_design'];
      extracted.manufacturing = byPipeline['manufacturing_analysis'];
      extracted.offTarget = byPipeline['quantum_offtarget_analysis'];
      extracted.personalizedMedicine = byPipeline['personalized_medicine'];
      return extracted;
    }

    if (toolName === 'quantum_fast_discovery' || toolName === 'full_drug_development' ||
        toolName === 'peptide_discovery' || toolName === 'custom_molecule_pipeline' ||
        toolName === 'run_78_algorithms' || toolName === 'multi_pipeline') {
      // Unwrap discovery envelope (full_drug_development wraps data in 'discovery')
      const disc = (data.discovery || {}) as Record<string, unknown>;
      extracted.bestCandidate = data.best_candidate || disc.best_candidate;
      extracted.allCandidates = data.candidates || data.all_candidates || disc.all_candidates;
      extracted.quantumMetrics = data.quantum_metrics || disc.quantum_metrics;
      extracted.paretoFront = data.pareto_front || disc.qpharos_pareto_results;
      extracted.totalIbmJobs = disc.total_ibm_jobs || data.total_ibm_jobs;
      extracted.totalTimeSeconds = disc.total_time_seconds || data.total_time_seconds;
      extracted.ibmJobIds = disc.ibm_job_ids || data.ibm_job_ids;
      if (!extracted.target && disc.target) extracted.target = disc.target;
      if (data.toxicology) extracted.toxicology = data.toxicology;
      if (data.pharmacology) extracted.pharmacology = data.pharmacology;
      if (data.clinical_trial) extracted.clinicalTrial = data.clinical_trial;
      if (data.clinical_trials) extracted.clinicalTrial = data.clinical_trials;
      if (data.protenix_structure) extracted.protenix = data.protenix_structure;
      if (data.alphagenomic) extracted.alphagenomic = data.alphagenomic;
    }

    if (toolName === 'antibody_cdr_design') {
      const candidates = Array.isArray(data.candidates)
        ? data.candidates as Array<Record<string, unknown>>
        : [];
      const best = (data.best_candidate || candidates[0] || {}) as Record<string, unknown>;
      const stages = (data.stages || {}) as Record<string, Record<string, unknown>>;
      const stageEntries = Object.entries(stages);
      const stageJobIds = stageEntries.flatMap(([, stage]) => {
        const ids = stage?.ibm_job_ids;
        return Array.isArray(ids) ? ids.map(String) : [];
      });
      const report = (data.report || {}) as Record<string, unknown>;
      const metadata = (data.metadata || {}) as Record<string, unknown>;
      const topLevelJobIds = Array.isArray(data.ibm_job_ids)
        ? (data.ibm_job_ids as unknown[]).map(String)
        : [];
      const topLevelSimulatorIds = Array.isArray(data.simulator_job_ids)
        ? (data.simulator_job_ids as unknown[]).map(String)
        : [];
      const reportJobIds = Array.isArray(report.ibm_job_ids)
        ? (report.ibm_job_ids as unknown[]).map(String)
        : [];
      const reportSimulatorIds = Array.isArray(report.simulator_job_ids)
        ? (report.simulator_job_ids as unknown[]).map(String)
        : [];
      const allJobIds = Array.from(new Set([
        ...topLevelJobIds,
        ...topLevelSimulatorIds,
        ...reportJobIds,
        ...reportSimulatorIds,
        ...stageJobIds,
      ]));

      extracted.target = data.target || best.target || extracted.target;
      extracted.sequence = best.sequence || best.vh_sequence || '';
      extracted.bestCandidate = {
        candidate_id: best.candidate_id,
        name: best.name,
        rank: best.rank,
        format: best.format || data.antibody_type,
        vh_germline: best.vh_germline,
        vl_germline: best.vl_germline,
        vh_length: best.vh_length,
        vl_length: best.vl_length,
        cdr_h1: best.cdr_h1,
        cdr_h2: best.cdr_h2,
        cdr_h3: best.cdr_h3,
        cdr_l1: best.cdr_l1,
        cdr_l2: best.cdr_l2,
        cdr_l3: best.cdr_l3,
        scores: best.scores || best.score_breakdown,
        binding_affinity_kcal: best.binding_affinity_kcal || best.binding_affinity || (best.docking as Record<string, unknown> | undefined)?.binding_affinity_kcal,
        kd_nM: best.kd_nM || (best.docking as Record<string, unknown> | undefined)?.kd_nM,
        humanization_score: best.humanization_score,
        developability_score: best.developability_score,
        immunogenicity_score: best.immunogenicity_score,
        admet: best.admet,
        toxicology: best.toxicology,
        pharmacology: best.pharmacology,
        clinical_trial: best.clinical_trial,
      };
      extracted.allCandidates = candidates.map((candidate) => ({
        rank: candidate.rank,
        candidate_id: candidate.candidate_id,
        format: candidate.format,
        cdr_h1: candidate.cdr_h1,
        cdr_h2: candidate.cdr_h2,
        cdr_h3: candidate.cdr_h3,
        cdr_h3_length: candidate.cdr_h3_length,
        kd_nM: candidate.kd_nM || (candidate.scores as Record<string, unknown> | undefined)?.kd_nm,
        binding_energy: (candidate.scores as Record<string, unknown> | undefined)?.binding_energy,
        humanization_score: candidate.humanization_score || (candidate.scores as Record<string, unknown> | undefined)?.humanization_score,
        immunogenicity_risk: (candidate.scores as Record<string, unknown> | undefined)?.immunogenicity_risk,
        clinical_success_prob: candidate.clinical_success_prob || (candidate.scores as Record<string, unknown> | undefined)?.clinical_success_prob,
        composite_score: candidate.composite_score || (candidate.scores as Record<string, unknown> | undefined)?.composite_score,
      }));
      extracted.stageSummary = stageEntries.map(([name, stage]) => ({
        name,
        stage: stage?.stage,
        ibm_job_ids: stage?.ibm_job_ids,
        total_evaluated: stage?.total_evaluated,
        top_cdr_h3_sequences: stage?.top_cdr_h3_sequences,
        vqe_energies: stage?.vqe_energies,
        humanization_scores: stage?.humanization_scores,
        kd_estimates_nm: stage?.kd_estimates_nm,
        scores: stage?.scores,
        status: stage?.status,
        method: stage?.method,
      }));
      extracted.ibmJobIds = allJobIds;
      extracted.quantumExecution = {
        backend: metadata.quantum_backend || report.quantum_backend || data.quantum_hardware,
        executionMode: metadata.execution_mode || report.execution_mode,
        hardwareJobIds: allJobIds.filter((id) => id && !id.includes('classical_fallback') && !id.startsWith('aer-sim') && !id.startsWith('sim-ab')),
        simulatorJobIds: allJobIds.filter((id) => id.startsWith('aer-sim')),
        fallbackStages: stageEntries
          .filter(([, stage]) => Array.isArray(stage?.ibm_job_ids) && (stage.ibm_job_ids as unknown[]).includes('classical_fallback'))
          .map(([name]) => name),
        fallbackCount: data.fallback_count || report.fallback_count,
      };
      extracted.admet = data.admet || best.admet;
      extracted.toxicology = data.toxicology || best.toxicology;
      extracted.pharmacology = data.pharmacology || best.pharmacology;
      extracted.clinicalTrial = data.clinical_trial || best.clinical_trial;
      extracted.report = report;
    }

    if (toolName === 'clinical_trial_simulation' && data.clinical_trial) {
      const ct = data.clinical_trial as Record<string, unknown>;
      extracted.phaseI = ct.phase_i;
      extracted.phaseII = ct.phase_ii;
      extracted.phaseIII = ct.phase_iii;
      extracted.approvalProbability = ct.approval_probability;
      extracted.regulatoryPathway = ct.regulatory_pathway;
    }

    if (toolName === 'admet_standalone') {
      if (data.admet) extracted.admet = data.admet;
      // admet_standalone's real response shape (src/backend script_executor_server.py
      // admet_standalone()) reports provenance via ibm_job_ids / quantum_execution /
      // quantum_backend at top level, NOT is_real_hardware — capture it here so
      // buildReportPrompt can hand the model real ground truth instead of letting it
      // guess (that gap is what let the LLM invent "real quantum hardware" for a
      // simulator run).
      extracted.ibmJobIds = Array.isArray(data.ibm_job_ids) ? data.ibm_job_ids : [];
      extracted.quantumExecutionStatus = data.quantum_execution || 'CLASSICAL_FALLBACK';
    }

    return extracted;
  }

  // Ground truth for whether a run actually touched real IBM quantum hardware, derived
  // from whatever provenance fields the backend actually returned for this tool — never
  // trust LLM-authored prose for this, only the tool JSON. Backends vary in field naming
  // (honest_backend_label() emits is_real_hardware/ibm_job_id/backend; admet_standalone
  // emits ibm_job_ids/quantum_execution/quantum_backend) so this checks both shapes.
  private computeHardwareTruth(extractedData: Record<string, unknown>): { isRealHardware: boolean; backendLabel: string } {
    const jobIds = Array.isArray(extractedData.ibmJobIds) ? extractedData.ibmJobIds as unknown[] : [];
    const backendLabel = String(
      extractedData.quantumBackend || extractedData.backend || 'unspecified backend'
    );
    const explicitReal = extractedData.is_real_hardware === true;
    const executionSaysReal = extractedData.quantumExecutionStatus === 'REAL_HARDWARE';
    const backendLooksLikeIbm = /^ibm[_-]/i.test(backendLabel) && backendLabel.toUpperCase() !== 'NONE';
    const isRealHardware = (explicitReal || executionSaysReal) && jobIds.length > 0 && backendLooksLikeIbm;
    return { isRealHardware, backendLabel };
  }

  // Deterministic backstop: a weak local LLM can ignore prompt instructions entirely, so
  // after the report is generated, strip/rewrite any "real (quantum) hardware" claim that
  // isn't backed by computeHardwareTruth(). Additive safety net, not a replacement for the
  // prompt-level fix above — catches whatever the prompt fix misses.
  private sanitizeHardwareClaims(report: string, groundTruth: { isRealHardware: boolean; backendLabel: string }): string {
    if (groundTruth.isRealHardware || !report) return report;
    const claimPattern = /\b(real|actual)\s+(ibm\s+)?quantum\s+hardware\b/gi;
    if (!claimPattern.test(report)) return report;
    return report.replace(
      claimPattern,
      `simulated quantum hardware (${groundTruth.backendLabel})`
    );
  }

  // Build focused report prompt with pre-extracted data
  private buildReportPrompt(toolName: string, extractedData: Record<string, unknown>, rawResults: string): string {
    const target = extractedData.target || 'Unknown';
    const smiles = extractedData.smiles || 'N/A';

    // Find dossier link in raw results
    const dossierMatch = rawResults.match(/Download: (http[^\s\n]+)/);
    const dossierLink = dossierMatch ? dossierMatch[1] : null;

    let prompt = `Generate a professional pharmaceutical report in markdown format.

**STUDY TYPE:** ${toolName}
**TARGET:** ${target}
**MOLECULE:** ${smiles}
**QUANTUM BACKEND:** ${extractedData.quantumBackend || 'IBM Boston 156Q'}
`;

    if (dossierLink) {
      prompt += `**DOSSIER DOWNLOAD:** ${dossierLink}\n`;
    }

    prompt += `\n**RAW DATA TO FORMAT:**\n`;

    // Add specific data based on study type with explicit instructions
    if (toolName === 'pharmacology_study') {
      prompt += `
## DATA FOR PHARMACOLOGY REPORT:

### ABSORPTION DATA:
${JSON.stringify(extractedData.absorption || {}, null, 2)}

### DISTRIBUTION DATA:
${JSON.stringify(extractedData.distribution || {}, null, 2)}

### METABOLISM DATA:
${JSON.stringify(extractedData.metabolism || {}, null, 2)}

### EXCRETION DATA:
${JSON.stringify(extractedData.excretion || {}, null, 2)}

### PHARMACODYNAMICS:
${JSON.stringify(extractedData.pharmacodynamics || {}, null, 2)}

### EFFICACY PREDICTION:
${JSON.stringify(extractedData.efficacy || {}, null, 2)}

### DRUG-DRUG INTERACTIONS:
${JSON.stringify(extractedData.ddi || {}, null, 2)}

---
**REQUIRED FORMAT:**

# Pharmacology Report: ${target}

## Executive Summary
[Write 2-3 sentences summarizing the key findings]

## 1. Pharmacokinetics

### 1.1 Absorption
| Parameter | Value | Unit | Confidence |
|-----------|-------|------|------------|
[Fill with data from ABSORPTION DATA - extract Caco2, intestinal_absorption, bioavailability, Pgp_substrate, etc.]

### 1.2 Distribution
| Parameter | Value | Unit | Confidence |
|-----------|-------|------|------------|
[Fill with data from DISTRIBUTION DATA - extract BBB_penetration, plasma_protein_binding, volume_of_distribution, etc.]

### 1.3 Metabolism
| Parameter | Value | Prediction | Confidence |
|-----------|-------|------------|------------|
[Fill with data from METABOLISM DATA - extract CYP inhibition/substrate values]

### 1.4 Excretion
| Parameter | Value | Unit | Confidence |
|-----------|-------|------|------------|
[Fill with data from EXCRETION DATA - extract clearance, half_life, etc.]

## 2. Pharmacodynamics
[Format the pharmacodynamics data into a readable section with mechanism, dose-response, etc.]

## 3. Efficacy Prediction
[Format efficacy data with predicted_efficacy, therapeutic_index, etc.]

## 4. Drug-Drug Interactions
[List any DDI warnings or interactions]

## 5. Dosing Recommendations
[Based on the PK data, suggest dosing]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}

**IMPORTANT:** Fill ALL table cells with actual values from the data. Do NOT leave empty cells. Use "N/A" only if the value is truly not present.
`;
    } else if (toolName === 'toxicology_study') {
      prompt += `
## DATA FOR TOXICOLOGY REPORT:

### ACUTE TOXICITY:
${JSON.stringify(extractedData.acuteToxicity || {}, null, 2)}

### GENOTOXICITY:
${JSON.stringify(extractedData.genotoxicity || {}, null, 2)}

### CARCINOGENICITY:
${JSON.stringify(extractedData.carcinogenicity || {}, null, 2)}

### ORGAN TOXICITY:
${JSON.stringify(extractedData.organToxicity || {}, null, 2)}

### IMMUNOTOXICITY:
${JSON.stringify(extractedData.immunotoxicity || {}, null, 2)}

### REPRODUCTIVE TOXICITY:
${JSON.stringify(extractedData.reproductiveToxicity || {}, null, 2)}

### OVERALL RISK:
${JSON.stringify(extractedData.overallRisk || {}, null, 2)}

---
**REQUIRED FORMAT:**

# Toxicology Report

## Executive Summary
[Write 2-3 sentences about overall safety profile]

## 1. Acute Toxicity
| Parameter | Value | Unit | Risk Level |
|-----------|-------|------|------------|
[Fill with LD50, NOAEL, LOAEL, MTD values]

## 2. Genotoxicity
| Test | Result | Confidence |
|------|--------|------------|
[Fill with Ames test, micronucleus, chromosomal aberration results]

## 3. Carcinogenicity Assessment
[Format carcinogenicity data]

## 4. Organ Toxicity
| Organ | Risk Level | Key Finding | Confidence |
|-------|------------|-------------|------------|
[Fill with hepatotoxicity, cardiotoxicity, nephrotoxicity, neurotoxicity]

## 5. Immunotoxicity
[Format immunotoxicity data]

## 6. Reproductive Toxicity
[Format reproductive toxicity data]

## 7. Overall Risk Assessment
[Summarize overall risk]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}

**IMPORTANT:** Fill ALL table cells with actual values from the data.
`;
    } else if (toolName === 'antibody_cdr_design') {
      prompt += `
## DATA FOR ANTIBODY CDR DESIGN REPORT:

### BEST ANTIBODY CANDIDATE:
${JSON.stringify(extractedData.bestCandidate || {}, null, 2)}

### ALL ANTIBODY CANDIDATES:
${JSON.stringify(extractedData.allCandidates || [], null, 2)}

### QUANTUM / AI EXECUTION TRACE:
${JSON.stringify(extractedData.quantumExecution || {}, null, 2)}

### STAGE SUMMARY:
${JSON.stringify(extractedData.stageSummary || [], null, 2)}

### ADMET:
${JSON.stringify(extractedData.admet || {}, null, 2)}

### TOXICOLOGY:
${JSON.stringify(extractedData.toxicology || {}, null, 2)}

### PHARMACOLOGY:
${JSON.stringify(extractedData.pharmacology || {}, null, 2)}

### CLINICAL TRIAL:
${JSON.stringify(extractedData.clinicalTrial || {}, null, 2)}

---
**REQUIRED FORMAT:**

# Quantum Antibody Discovery Report: ${target}

## Executive Summary
[Summarize the real pipeline outcome using only the data above. If hardwareJobIds is empty, explicitly state that no IBM hardware job ID was returned and do not claim hardware execution.]

## 1. Execution Path
| Layer | Evidence | Result |
|-------|----------|--------|
| AI Input Layer | Target, framework, epitope/sequence inputs | [fill from data] |
| Quantum Layer | IBM/Aer job IDs and stages | [list hardwareJobIds/simulatorJobIds/fallbackStages exactly] |
| AI Output Layer | Protenix/ADMET/tox/pharmacology/clinical scoring | [fill from data] |

## 2. CDR Design
| Rank | Candidate | Format | CDR-H1 | CDR-H2 | CDR-H3 | CDR-H3 Length |
|------|-----------|--------|--------|--------|--------|----------------|
[Fill with ALL ANTIBODY CANDIDATES. Do not invent CDRs.]

## 3. Binding and Developability
| Rank | Candidate | KD nM | Binding Energy | Humanization | Immunogenicity Risk | Composite Score |
|------|-----------|-------|----------------|--------------|---------------------|-----------------|
[Fill from ALL ANTIBODY CANDIDATES and BEST ANTIBODY CANDIDATE.]

## 4. ADMET / Safety / Pharmacology
[Use the ADMET, TOXICOLOGY, and PHARMACOLOGY sections. Keep biologics-specific route/half-life/ADA/cytokine-release details.]

## 5. Clinical Readiness
[Use CLINICAL TRIAL data. Include phase probabilities only if present.]

## 6. IBM Job IDs and Fallbacks
[List every job ID exactly. If fallbackStages is non-empty, list those stages and state that those values were fallback-derived.]

## 7. Recommendations
[Give 3-5 next steps based on the actual CDR, KD, humanization, immunogenicity, and developability data.]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}

**IMPORTANT:** This is an antibody/biologics report, not a small-molecule report. Do not use SMILES as the lead identity unless the backend explicitly returned one. Do not mention sim-ab IDs as real IBM jobs. Do not fabricate missing values.
`;
    } else if (toolName === 'multi_pipeline') {
      prompt += `
## DATA FOR MULTI-PIPELINE COMPREHENSIVE REPORT:

### ANALYZED MOLECULE:
- SMILES: ${extractedData.finalSmiles || 'N/A'}
- Target: ${target}

### EXECUTION SUMMARY:
- Total pipelines executed: ${extractedData.totalSteps || 0}
- Steps completed: ${JSON.stringify(extractedData.stepsCompleted || [])}
- Steps failed: ${JSON.stringify(extractedData.stepsFailed || [])}
- Execution time: ${extractedData.executionTime || 0} seconds
- Total IBM Jobs: ${extractedData.totalIbmJobs || 0}
- IBM Job IDs: ${JSON.stringify(extractedData.ibmJobIds || [])}

### PIPELINE RESULTS (ALL 17):

#### 1. run_78_algorithms:
${JSON.stringify(extractedData.run_78_algorithms || {}, null, 2)}

#### 2. admet_standalone:
${JSON.stringify(extractedData.admet || {}, null, 2)}

#### 3. toxicology_study:
${JSON.stringify(extractedData.toxicology || {}, null, 2)}

#### 4. pharmacology_study:
${JSON.stringify(extractedData.pharmacology || {}, null, 2)}

#### 5. clinical_trial_simulation:
${JSON.stringify(extractedData.clinicalTrial || {}, null, 2)}

#### 6. retrosynthesis_planning:
${JSON.stringify(extractedData.retrosynthesis || {}, null, 2)}

#### 7. pbpk_modeling:
${JSON.stringify(extractedData.pbpk || {}, null, 2)}

#### 8. formulation_optimization:
${JSON.stringify(extractedData.formulation || {}, null, 2)}

#### 9. patent_analysis:
${JSON.stringify(extractedData.patentAnalysis || {}, null, 2)}

#### 10. regulatory_analysis:
${JSON.stringify(extractedData.regulatory || {}, null, 2)}

#### 11. multispecies_tox:
${JSON.stringify(extractedData.multispeciesTox || {}, null, 2)}

#### 12. pharmacovigilance:
${JSON.stringify(extractedData.pharmacovigilance || {}, null, 2)}

#### 13. rwe_analysis:
${JSON.stringify(extractedData.rwe || {}, null, 2)}

#### 14. cdx_design:
${JSON.stringify(extractedData.cdxDesign || {}, null, 2)}

#### 15. manufacturing_analysis:
${JSON.stringify(extractedData.manufacturing || {}, null, 2)}

#### 16. quantum_offtarget_analysis:
${JSON.stringify(extractedData.offTarget || {}, null, 2)}

#### 17. personalized_medicine:
${JSON.stringify(extractedData.personalizedMedicine || {}, null, 2)}

---
**REQUIRED FORMAT:**

# Comprehensive Multi-Pipeline Analysis: ${target}

## Executive Summary
[Write 5-7 sentences highlighting: molecule analyzed, total pipelines completed, total IBM quantum jobs, key findings across all 17 pipelines, most significant results]

## 1. Target & Molecule
- **Target:** ${target}
- **Molecule SMILES:** ${extractedData.finalSmiles || 'N/A'}
- **Pipelines Executed:** ${extractedData.totalSteps || 0}

## 2. Quantum Execution Summary
| Metric | Value |
|--------|-------|
| Total IBM Jobs | ${extractedData.totalIbmJobs || 0} |
| Execution Time | ${extractedData.executionTime || 0}s |
| Pipelines Completed | ${(extractedData.stepsCompleted as unknown[])?.length || 0}/${extractedData.totalSteps || 0} |
| Pipelines Failed | ${(extractedData.stepsFailed as unknown[])?.length || 0} |
| Backend | IBM Boston 156Q |

## 3. Quantum Algorithms (run_78_algorithms)
[Extract from run_78_algorithms data]

## 4. ADMET Profile (admet_standalone)
| Parameter | Value | Unit |
|-----------|-------|------|
[Fill from admet data: oral_bioavailability, hia, bbb_penetration, caco2, half_life, clearance, cyp inhibition, hERG, ames]

## 5. Toxicology (toxicology_study)
| Category | Result | Risk |
|----------|--------|------|
[Fill from toxicology: acute, genotoxicity, carcinogenicity, organ toxicity, immunotoxicity]

## 6. Pharmacology (pharmacology_study)
| Parameter | Value | Unit |
|-----------|-------|------|
[Fill from pharmacology: PK/PD, Cmax, AUC, t1/2, clearance, bioavailability]

## 7. Clinical Trial Simulation
| Phase | Success Probability | Decision |
|-------|---------------------|----------|
[Fill from clinical_trial: phase_1, phase_2, phase_3 success probabilities and GO/NO-GO]

## 8. Retrosynthesis Planning
[Extract synthetic routes, cost estimates, number of steps]

## 9. PBPK Modeling
| Tissue | Concentration | Brain/Plasma Ratio |
|--------|---------------|---------------------|
[Fill from pbpk: 14-compartment distribution]

## 10. Formulation Optimization
[Extract excipients, stability, osmolarity]

## 11. Patent Analysis
[Extract IP landscape, freedom-to-operate conclusion]

## 12. Regulatory Pathway
[Extract FDA pathway, timeline, key study requirements]

## 13. Multi-Species Toxicology
| Species | NOAEL | LD50 | Key Finding |
|---------|-------|------|-------------|
[Fill from multispecies_tox: rat, mouse, dog, monkey, rabbit, zebrafish]

## 14. Pharmacovigilance
[Extract FAERS signals, MedDRA events]

## 15. Real-World Evidence
[Extract RWE findings]

## 16. Companion Diagnostic Design
[Extract CDx biomarkers, positioning]

## 17. Manufacturing
[Extract scale-up, yield, GMP feasibility]

## 18. Off-Target Safety Panel
| Protein | Binding | Risk |
|---------|---------|------|
[Fill from off_target: 10-protein panel]

## 19. Personalized Medicine
[Extract PGx recommendations, genotype-based dosing]

## 20. IBM Quantum Job IDs
[List ALL job IDs from the data]

## 21. Recommendations
[Based on aggregated results, provide 3-5 actionable recommendations]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}

**CRITICAL:** Fill ALL tables with actual values from the pipeline data above. This molecule has been analyzed across 17 pipelines — do NOT say "pipeline failed" or "no data". Extract every numerical value present.
`;
    } else if (toolName === 'quantum_fast_discovery' || toolName === 'full_drug_development') {
      prompt += `
## DATA FOR DRUG DISCOVERY REPORT:

### BEST CANDIDATE:
${JSON.stringify(extractedData.bestCandidate || {}, null, 2)}

### ALL CANDIDATES:
${JSON.stringify(extractedData.allCandidates || [], null, 2)}

### QUANTUM EXECUTION:
- Total IBM Jobs: ${extractedData.totalIbmJobs || 'see data'}
- Total Time: ${extractedData.totalTimeSeconds || 'see data'} seconds
- IBM Job IDs: ${JSON.stringify(extractedData.ibmJobIds || [], null, 2)}

### TOXICOLOGY SUMMARY:
${JSON.stringify(extractedData.toxicology || {}, null, 2)}

### PHARMACOLOGY SUMMARY:
${JSON.stringify(extractedData.pharmacology || {}, null, 2)}

### CLINICAL TRIAL SUMMARY:
${JSON.stringify(extractedData.clinicalTrial || {}, null, 2)}

### PROTENIX STRUCTURE:
${JSON.stringify(extractedData.protenix || {}, null, 2)}

### QUANTUM METRICS:
${JSON.stringify(extractedData.quantumMetrics || {}, null, 2)}

### PARETO FRONT:
${JSON.stringify(extractedData.paretoFront || {}, null, 2)}

---
**REQUIRED FORMAT:**

# Quantum Drug Discovery Report: ${target}

## Executive Summary
[Write summary with best candidate SMILES, binding affinity, and key achievements]

## 1. Target Analysis
- **Target Protein:** ${target}
- **Binding Site:** [from data]

## 2. Lead Candidates

### Best Candidate
- **SMILES:** [from best_candidate.smiles]
- **Binding Affinity:** [from best_candidate.predicted_binding_affinity_kcal_mol] kcal/mol
- **Composite Score:** [from best_candidate.composite_score]

### All Candidates Table
| Rank | SMILES | Binding Affinity | Composite Score |
|------|--------|------------------|-----------------|
[Fill with candidate data]

## 3. Quantum Metrics
| Metric | Value | Unit |
|--------|-------|------|
[Fill with VQE energy, QSVM confidence, QEC improvement, etc.]

## 4. Pareto Optimization
[Format pareto front results]

## 5. Recommendations
[Based on results, recommend next steps]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}
`;
    } else if (toolName === 'clinical_trial_simulation') {
      prompt += `
## DATA FOR CLINICAL TRIAL REPORT:

### PHASE I:
${JSON.stringify(extractedData.phaseI || {}, null, 2)}

### PHASE II:
${JSON.stringify(extractedData.phaseII || {}, null, 2)}

### PHASE III:
${JSON.stringify(extractedData.phaseIII || {}, null, 2)}

### APPROVAL PROBABILITY:
${JSON.stringify(extractedData.approvalProbability || {}, null, 2)}

### REGULATORY PATHWAY:
${JSON.stringify(extractedData.regulatoryPathway || {}, null, 2)}

---
**REQUIRED FORMAT:**

# Clinical Trial Simulation Report

## Executive Summary
[Summarize approval probability and key findings]

## 1. Phase I Results
| Parameter | Value | Status |
|-----------|-------|--------|
[Fill with safety, MTD, PK data]

## 2. Phase II Results
| Parameter | Value | Status |
|-----------|-------|--------|
[Fill with efficacy, dose-response data]

## 3. Phase III Results
| Endpoint | Result | P-value | Status |
|----------|--------|---------|--------|
[Fill with primary/secondary endpoints]

## 4. Approval Probability
[Format approval probability comparison vs industry average]

## 5. Regulatory Pathway
[Format regulatory recommendations]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}
`;
    } else if (toolName === 'admet_standalone') {
      const jobIds = Array.isArray(extractedData.ibmJobIds) ? extractedData.ibmJobIds as unknown[] : [];
      const execStatus = extractedData.quantumExecutionStatus || 'CLASSICAL_FALLBACK';
      prompt += `
## DATA FOR ADMET REPORT:

### ADMET DATA:
${JSON.stringify(extractedData.admet || {}, null, 2)}

### QUANTUM/HARDWARE PROVENANCE (ground truth — do not contradict this):
- quantum_backend: ${extractedData.quantumBackend || 'NONE'}
- quantum_execution: ${execStatus}
- ibm_job_ids: ${jobIds.length ? JSON.stringify(jobIds) : '[] (none)'}
[If quantum_execution is not exactly "REAL_HARDWARE" or ibm_job_ids is empty, this run used a classical/simulator backend — say so plainly in the report and do NOT claim "real quantum hardware" anywhere.]

---
**REQUIRED FORMAT:**

# ADMET Analysis Report

## Executive Summary
[Summarize ADMET profile]

## 1. Absorption
| Parameter | Value | Unit | Status |
|-----------|-------|------|--------|
[Fill with Caco-2, intestinal absorption, bioavailability]

## 2. Distribution
| Parameter | Value | Unit | Status |
|-----------|-------|------|--------|
[Fill with BBB, PPB, Vd]

## 3. Metabolism
| CYP Enzyme | Inhibitor | Substrate | Confidence |
|------------|-----------|-----------|------------|
[Fill with CYP data]

## 4. Excretion
| Parameter | Value | Unit |
|-----------|-------|------|
[Fill with clearance, half-life]

## 5. Toxicity Alerts
[List any toxicity flags]

## 6. Drug-likeness
| Rule | Status | Details |
|------|--------|---------|
[Fill with Lipinski, Veber, QED]

${dossierLink ? `\n## Download Complete Dossier\n📥 **[Download Full Report (DOCX)](${dossierLink})**\n` : ''}
`;
    } else {
      // Generic format
      prompt += `
${rawResults}

Generate a professional report with:
1. Executive Summary
2. Key findings in tables
3. Recommendations
${dossierLink ? `4. Download link: ${dossierLink}` : ''}
`;
      // A pipeline that ships an `llm_brief` has ALREADY written its own
      // verdict. Observed 2026-09-09 on the rejuvenation designer: left to
      // interpret the raw JSON, the model called the disease being polygenic
      // a "negative" (it is the very reason the gate passes), presented the
      // chemical arm's docking pocket as the therapeutic target, and proposed
      // a CRISPR knockdown — which contradicts a catalytically DEAD editor.
      // The numbers were right and the story was wrong. Where the pipeline
      // states the meaning, the model reproduces it; it does not re-derive it.
      if (/"llm_brief"\s*:/.test(rawResults)) {
        prompt += `
CRITICAL — this result carries an \`llm_brief\` block written by the pipeline itself.
* Use \`llm_brief.headline\` as your one-line verdict, preserving its meaning.
* Build "Key findings" from \`llm_brief.key_points\` — do not substitute your own reading.
* Reproduce \`llm_brief.honest_limits\` verbatim; never soften or omit them.
* Obey every entry in \`llm_brief.must_not_say\`. These are not stylistic
  preferences: each one marks a scientific error the model has actually made
  on this pipeline before.
* Recommend ONLY what appears in \`llm_brief.valid_next_steps\`. Do not invent
  experiments, mechanisms or modalities the pipeline did not compute.
`;
      }
    }

    return prompt;
  }

  // Fetch the LIVE BioQL knowledge block (identity + honest-framing + RAG over the
  // platform's own catalogs) from the backend and PREPEND it to the static routing
  // contract. Makes the model BioQL-aware without touching its weights. Fail-open:
  // on ANY error/timeout it returns '' and chat falls back to today's exact prompt.
  // Per-send (not per-keystroke), hard 2.5s timeout so it can never stall the chat.
  // Last honesty rules fetched from the backend knowledge layer. Reused to keep the
  // report-generation pass honest (label simulation, don't oversell, never fabricate)
  // without a second round-trip. '' until the first successful knowledge fetch.
  private lastHonestyRules: string = '';

  private async fetchBioQLKnowledge(userMessage: string): Promise<string> {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2500);
      const res = await fetch('/api/llm/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) return '';
      const data = await res.json();
      const prompt = typeof data?.system_prompt === 'string' ? data.system_prompt : '';
      if (Array.isArray(data?.honesty_rules) && data.honesty_rules.length) {
        this.lastHonestyRules = data.honesty_rules.map((r: string) => `- ${r}`).join('\n');
      }
      if (prompt && Array.isArray(data?.sources) && data.sources.length) {
        console.log('[BioQL knowledge] injected', data.sources.length, 'catalog sources:',
          data.sources.map((s: any) => s.breadcrumb).join(' | '));
      }
      return prompt;
    } catch {
      return ''; // fail-open: chat keeps working exactly as before
    }
  }

  // Send message to DeepSeek via OpenRouter with automatic MCP tool execution
  async sendMessage(
    content: string,
    onToolCall?: (toolCall: VSIXToolCall) => void,
    onStream?: (text: string) => void
  ): Promise<VSIXMessage> {
    const messageId = generateUUID();

    // Local mode (LM Studio :8001) needs NO API key — only OpenRouter mode does.
    if (!this.useLocal && !this.config.openRouterKey) {
      throw new Error('OpenRouter API key not configured. Please add your key in the settings.');
    }

    // Add user message to history
    this.conversationHistory.push({
      role: 'user',
      content,
    });

    try {
      let assistantContent = '';
      const toolCallPayloads: string[] = [];

      // Explicit veterinary-antibody design requests already contain a complete
      // deterministic routing contract. Execute the real pipeline directly so a
      // 7K+ tool-selection prompt cannot exhaust the local model's 300 s timeout.
      // The normal tool execution, result cards, provenance and deterministic
      // report path below remain unchanged.
      // MOLEVERA / BIOQL
      if (shouldDirectRouteVeterinaryAntibodyDesign(content)) {
        const routed = applyToolRouting(content, 'molevera_veterinary_antibody_design', {}, {
          isFirstTool: true,
          provider: 'vsix',
          helpers: {
            extractTargetFromMessage: (m) => this.extractTargetFromMessage(m),
            extractIndicationFromMessage: (m) => this.extractIndicationFromMessage(m),
            extractPdbIdFromMessage: (m) => this.extractPdbIdFromMessage(m),
            extractDesignCountFromMessage: (m) => this.extractDesignCountFromMessage(m),
            detectBiologicToolFromPrompt: (m) => this.detectBiologicToolFromPrompt(m),
          },
        });
        toolCallPayloads.push(JSON.stringify({ tool: routed.toolName, arguments: routed.args }));
        assistantContent = `Executing ${routed.toolName} with backend pipeline results.`;
        console.log('[ROUTING] Veterinary antibody design bypassed local LLM tool selection.');
      } else {
        // Prepare messages with dynamic system prompt (includes MCP tools).
        // Prepend the LIVE BioQL knowledge block (from the backend catalogs) so the
        // model can converse accurately about the platform; the static routing
        // contract below it stays the authority the [TOOL_CALL] parser depends on.
        const routingContract = buildSystemPrompt();
        const knowledge = await this.fetchBioQLKnowledge(content);
        const systemContent = knowledge
          ? `${knowledge}\n\n══════════════════════════════════════════\n\n${routingContract}`
          : routingContract;
        const messages = [
          { role: 'system' as const, content: systemContent },
          ...this.conversationHistory,
        ];

        // Call the active LLM endpoint (OpenRouter or local LM Studio)
        const response = await fetch(this.chatUrl(), {
          method: 'POST',
          headers: this.chatHeaders(),
          body: JSON.stringify({
            model: this.chatModel(),
            messages,
            temperature: 0.7,
            max_tokens: 4000,
            stream: false,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`${this.useLocal ? 'Local LLM' : 'OpenRouter'} API error: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        assistantContent = data.choices?.[0]?.message?.content || '';

        // Extract and execute tool calls from the response.
        // Biologic design requests must run backend tools; do not accept a free-form LLM report as a result.
        toolCallPayloads.push(...Array.from(
          assistantContent.matchAll(/\[TOOL_CALL\]\s*([\s\S]*?)\s*\[\/TOOL_CALL\]/g),
        ).map(match => match[1]));
        assistantContent = assistantContent.replace(/\[TOOL_CALL\][\s\S]*?\[\/TOOL_CALL\]/g, '').trim();
      }
      const forcedToolCall = toolCallPayloads.length === 0 ? this.buildForcedBiologicToolCall(content) : null;
      if (forcedToolCall) {
        console.warn('[ROUTING] Forced backend tool execution for biologic request:', forcedToolCall.tool, forcedToolCall.arguments);
        toolCallPayloads.push(JSON.stringify(forcedToolCall));
        assistantContent = `Executing ${forcedToolCall.tool} with backend pipeline results.`;
      }
      // ── Deterministic small-molecule override ────────────────────────────────
      // A SMILES + comprehensive request ("full pipeline", "all cards", "comprehensive")
      // must run the full molecule pipeline. The weak local router otherwise mis-routes
      // it to an orphan RBFE/mutation tool (which then errors on missing mutation fields).
      // This bypasses the model's tool choice entirely, regardless of payload shape.
      {
        const wantsComprehensive = /\b(full\s+pipeline|all\s+cards|comprehensive|complete\b|full\s+development|entire\s+pipeline|every\s+card|todas\s+las\s+cards|pipeline\s+completo|full\s+drug)\b/i.test(content);
        const looksBiologic = /\b(antibod|nanobod|vhh|peptide|mrna|intrabody|protein\s+design|de-?immuniz|codon)\b/i.test(content);
        if (wantsComprehensive && !looksBiologic) {
          const sm = this.buildForcedSmallMoleculeToolCall(content);
          if (sm) {
            console.warn('[ROUTING] SMILES + comprehensive request → forcing custom_molecule_pipeline (override). Was:', toolCallPayloads);
            toolCallPayloads.length = 0;
            toolCallPayloads.push(JSON.stringify(sm));
            assistantContent = `Executing ${sm.tool} (full small-molecule pipeline) with backend results.`;
          }
        }
      }
      // ── Drop ORPHAN comp-chem sub-step tool calls ────────────────────────────
      // The local router sometimes decomposes a design prompt ("…compute the MM-GBSA
      // binding free energy for the lead…") into standalone binding_free_energy /
      // RBFE / interaction tool calls. Those need a `complex_pdb` the chat does not
      // have → they execute with an empty structure and render empty cards (the 3
      // blank "Binding Free Energy" cards). The DESIGN pipelines (antibody/peptide/
      // mRNA) already compute MM-GBSA, docking, ADMET, tox internally, so:
      //   (a) if a pipeline tool is present, drop the redundant sub-step tools;
      //   (b) always drop a comp-chem tool that lacks a real complex_pdb;
      //   (c) de-duplicate identical tool calls.
      {
        const PIPELINE_TOOLS = new Set(['antibody_cdr_design', 'peptide_discovery',
          'mrna_therapeutic_design', 'protein_engineering_pipeline', 'fusion_protein_design',
          'full_drug_development', 'unified_drug_development', 'custom_molecule_pipeline',
          'master_discovery', 'modality_comparison', 'proteina_complexa_design']);
        const SUBSTEP_TOOLS = new Set(['binding_free_energy', 'relative_binding_free_energy',
          'protein_ligand_interactions', 'pocket_detection', 'lead_optimization', 'metallodrug']);
        const parsed = toolCallPayloads.map(p => { try { return { p, j: JSON.parse(p) }; } catch { return { p, j: null }; } });
        const hasPipeline = parsed.some(x => x.j && PIPELINE_TOOLS.has(x.j.tool));
        const seen = new Set<string>();
        const kept: string[] = [];
        let dropped = 0;
        for (const { p, j } of parsed) {
          if (!j || !j.tool) { kept.push(p); continue; }
          const args = j.arguments || j.payload || {};
          const toolKey = String(j.tool || '').toLowerCase();
          const isSubstep = SUBSTEP_TOOLS.has(j.tool) ||
            /binding_free_energy|rbfe|relative_binding|protein_ligand_interaction|atom[-_]?openmm/.test(toolKey);
          const cpx = (args && args.complex_pdb) || j.complex_pdb || (j.payload && j.payload.complex_pdb);
          const noStruct = isSubstep &&
            !(typeof cpx === 'string' && cpx.trim().length > 20);
          if (isSubstep && (hasPipeline || noStruct)) { dropped++; continue; }
          const sig = j.tool + '|' + JSON.stringify(args);
          if (seen.has(sig)) { dropped++; continue; }   // de-dup
          seen.add(sig);
          kept.push(p);
        }
        if (dropped > 0) {
          console.warn(`[ROUTING] dropped ${dropped} orphan/duplicate sub-step tool call(s) (e.g. binding_free_energy without a complex)`);
          toolCallPayloads.length = 0;
          toolCallPayloads.push(...kept);
        }
      }

      // If the router emitted ONLY orphan sub-step tools (e.g. 3× binding_free_energy
      // for an antibody-design prompt) and they were all dropped, force the correct
      // design pipeline so the request actually runs instead of returning nothing.
      if (toolCallPayloads.length === 0) {
        const forcedAfterFilter = this.buildForcedBiologicToolCall(content)
          || this.buildForcedSmallMoleculeToolCall(content);
        if (forcedAfterFilter) {
          console.warn('[ROUTING] all tool calls were orphan sub-steps; forcing pipeline:', forcedAfterFilter.tool);
          toolCallPayloads.push(JSON.stringify(forcedAfterFilter));
          assistantContent = `Executing ${forcedAfterFilter.tool} with backend pipeline results.`;
        }
      }

      const executedTools: VSIXToolCall[] = [];
      // Filled in ORIGINAL payload order after the concurrent execution phase
      // below, so the assembled report text reads the same as before even
      // though the underlying tool calls now run in parallel.
      const toolResultTexts: string[] = [];

      let toolCallCount = 0;
      // Raised 2 -> 5 so a multi-modality request ("antibody AND mRNA AND CRISPR")
      // fans out to one pipeline per modality on DeepSeek/VSIX too (parity with Claude).
      const MAX_TOOL_CALLS = 5;
      // Phase 1 (SEQUENTIAL): parse + route every tool call. Routing rules read
      // `toolCallCount === 1` (isFirstTool), so this ordering must stay serial.
      // Phase 2 (CONCURRENT, below): actually execute them — the slow part
      // (real pipeline runs / quantum job polling) — via Promise.all so
      // independent tool calls in the same turn run at the same time instead
      // of one after another.
      const pendingCalls: Array<{
        index: number;
        toolCall: VSIXToolCall;
        finalToolName: string;
        finalToolArgs: Record<string, unknown>;
        isQuantumJob: boolean;
        originalToolName: string;
      }> = [];
      const seenRoutedCalls = new Set<string>();
      for (const toolCallPayload of toolCallPayloads) {
        if (toolCallCount >= MAX_TOOL_CALLS) { console.log('[LIMIT] Max tool calls reached'); break; }
        const _thisIndex = toolCallCount;
        toolCallCount++;
        try {
          const toolCallJson = JSON.parse(toolCallPayload);
          const toolName = toolCallJson.tool;
          const toolArgs = toolCallJson.arguments || {};

          // Create tool call object
          const toolCall: VSIXToolCall = {
            id: generateUUID(),
            name: toolName,
            input: toolArgs,
            status: 'running',
          };

          // SMART ROUTING: Override wrong tool selections.
          // The routing rules (mRNA Rule 0, quantum_fast_discovery upgrade,
          // protenix-never-first with enzyme branch, peptide/antibody overrides)
          // are centralized in chatToolRouting.applyToolRouting so this provider
          // and ClaudeService share ONE implementation. VSIX-specific arg shapes
          // (n_designs/n_candidates, framework, antigen, enzyme branch) are
          // reproduced via the `helpers` extractors below; the antibody intent
          // still routes to antibody_cdr_design (VSIX) — see module docs.
          const routedVsix = applyToolRouting(content, toolCallJson.tool, toolArgs, {
            isFirstTool: toolCallCount === 1,
            provider: 'vsix',
            helpers: {
              extractTargetFromMessage: (m) => this.extractTargetFromMessage(m),
              extractIndicationFromMessage: (m) => this.extractIndicationFromMessage(m),
              extractPdbIdFromMessage: (m) => this.extractPdbIdFromMessage(m),
              extractDesignCountFromMessage: (m) => this.extractDesignCountFromMessage(m),
              detectBiologicToolFromPrompt: (m) => this.detectBiologicToolFromPrompt(m),
            },
          });
          // Reflect routing decision back onto the structures the downstream
          // code reads (toolCallJson.tool / toolCallJson.arguments). The shared
          // function already Object.assign'd the new args into `toolArgs`.
          toolCallJson.tool = routedVsix.toolName;
          toolCallJson.arguments = routedVsix.args;

          // Update toolName after routing
          const finalToolName = toolCallJson.tool;
          const finalToolArgs = toolCallJson.arguments || toolArgs;
          // Update toolCall with routed name/args
          toolCall.name = finalToolName;
          toolCall.input = finalToolArgs;

          // Different weak-router payloads can converge to the same full
          // pipeline only AFTER deterministic routing. De-duplicate here,
          // before execution/UI notification, so one user request creates one
          // scientific run and one result card set.
          const routedSignature = `${finalToolName}|${JSON.stringify(finalToolArgs)}`;
          if (seenRoutedCalls.has(routedSignature)) {
            console.warn(`[ROUTING] dropped duplicate routed tool call: ${finalToolName}`);
            continue;
          }
          seenRoutedCalls.add(routedSignature);
          executedTools.push(toolCall);
          if (onToolCall) onToolCall(toolCall);

          // Forward the RAW user prompt so peptide-panel / HLA pipelines (e.g. the
          // polyclonal antibody + docking branch) can self-parse the peptide list,
          // HLA, and docking intent that the structured router args drop. The LLM
          // router only emits {antigen, cdr_loops, n_designs}, losing the panel;
          // the backend parser recovers everything from this prompt. Harmless for
          // other tools (unknown key ignored); only set when absent.
          if (finalToolArgs && typeof finalToolArgs === 'object'
              && /antibod|peptide|cdr|epitope|immunogen|hla/i.test(finalToolName + ' ' + content)
              && (finalToolArgs as Record<string, unknown>).prompt === undefined) {
            (finalToolArgs as Record<string, unknown>).prompt = content;
          }

          console.log(`🔧 Queued MCP tool: ${finalToolName}`, finalToolArgs);

          // Check if this is a quantum job that requires polling
          const isQuantumJob = this.isQuantumJobTool(finalToolName);

          pendingCalls.push({
            index: _thisIndex,
            toolCall,
            finalToolName,
            finalToolArgs: finalToolArgs as Record<string, unknown>,
            isQuantumJob,
            originalToolName: toolName,
          });

        } catch (parseError) {
          console.error('Failed to parse tool call:', parseError);
        }
      }

      // Phase 2 (CONCURRENT): actually run every queued tool call. Each entry
      // updates its own toolCall/toolResultTexts slot independently, so a
      // slow or failing call never blocks the others.
      await Promise.all(pendingCalls.map(async (pc) => {
        const { toolCall, finalToolName, finalToolArgs, isQuantumJob, originalToolName, index } = pc;
        try {
          console.log(`🔧 Executing MCP tool: ${finalToolName}`, finalToolArgs);

          if (isQuantumJob) {
            // Handle quantum job with polling
            const result = await this.executeQuantumJob(finalToolName, finalToolArgs, onStream);

            // Update tool call with result
            toolCall.status = result.success ? 'completed' : 'failed';
            toolCall.output = result.content;
            toolCall.error = result.error;

            // Notify UI of completion
            if (onToolCall) {
              onToolCall(toolCall);
            }

            // Store result for follow-up (slotted by original payload order)
            toolResultTexts[index] = `\n\nTool: ${finalToolName}\nResult:\n${(() => { const _r = JSON.stringify(result.content || result.error, null, 2); return _r.length > 8000 ? _r.substring(0, 8000) + "\n... [TRUNCATED: " + Math.round(_r.length/1024) + "KB — full result saved to session]" : _r; })()}\n`;

            // Generate DOCX dossier for quantum jobs
            if (result.success && result.content) {
              try {
                const _dKey = sessionStorage.getItem('bioql_api_key') || localStorage.getItem('bioql_api_key') || '';
                const dossierResponse = await fetch('/api/reports/generate_dossier', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', ...(_dKey ? { 'X-API-Key': _dKey } : {}) },
                  body: JSON.stringify(result.content),
                });
                if (dossierResponse.ok) {
                  const dossierResult = await dossierResponse.json();
                  console.log(`📄 Dossier generated: ${dossierResult.filename}`);
                  toolResultTexts[index] += `\n\n**DOSSIER GENERATED:**\n- File: ${dossierResult.filename}\n- Download: ${dossierResult.download_url}\n`;
                }
              } catch (dossierError) {
                console.warn('Dossier generation failed:', dossierError);
              }
            }

            console.log(`✅ Quantum job ${originalToolName} completed:`, result);
          } else {
            // Execute regular MCP tool
            const result = await mcpClient.callTool(finalToolName, finalToolArgs);

            // Update tool call with result
            toolCall.status = result.success ? 'completed' : 'failed';
            toolCall.output = result.content;
            toolCall.error = result.error;
            toolCall.pipelineSessionId = result.pipelineSessionId;

            // Notify UI of completion
            if (onToolCall) {
              onToolCall(toolCall);
            }

            // Store result for follow-up (slotted by original payload order)
            toolResultTexts[index] = `\n\nTool: ${finalToolName}\nResult:\n${(() => { const _r = JSON.stringify(result.content || result.error, null, 2); return _r.length > 8000 ? _r.substring(0, 8000) + "\n... [TRUNCATED: " + Math.round(_r.length/1024) + "KB — full result saved to session]" : _r; })()}\n`;

            console.log(`✅ Tool ${originalToolName} completed:`, result);
          }
        } catch (execError) {
          console.error(`Tool execution failed for ${finalToolName}:`, execError);
          toolCall.status = 'failed';
          toolCall.error = execError instanceof Error ? execError.message : String(execError);
          if (onToolCall) onToolCall(toolCall);
        }
      }));

      const toolResults = toolResultTexts.join('');

      // If tools were executed, make a follow-up call to format the report
      const bypassLlmReport = executedTools.some(tool => this.shouldBypassLlmReport(tool.name));
      if (toolResults && bypassLlmReport) {
        assistantContent = this.buildDeterministicPipelineSummary(executedTools);
      }

      if (toolResults && executedTools.length > 0 && !bypassLlmReport) {
        // Phase A of the report-builder plan (see project plan doc): reports are
        // rendered DETERMINISTICALLY from the real result JSON — no LLM call, so
        // nothing can be fabricated structurally, not just filtered post-hoc.
        // This replaces the previous free-text LLM report generator entirely
        // (buildReportPrompt/extractReportData/sanitizeHardwareClaims below are
        // kept in the file, unused, rather than deleted, in case of rollback).
        // Notably this also covers tool types (e.g. mrna_therapeutic_v1) that
        // previously had NO bespoke template at all and fell through to the
        // least-constrained "generic" LLM branch.
        const toolName = executedTools[0]?.name || '';
        const rawOutput = executedTools[0]?.output as any;
        const rootData = (rawOutput && typeof rawOutput === 'object' && rawOutput.result && typeof rawOutput.result === 'object')
          ? rawOutput.result : rawOutput;
        const reportTarget = (executedTools[0]?.input as any)?.target
          || rootData?.target || rootData?.antigen || rootData?.target_name || undefined;
        assistantContent = renderDeterministicReport(toolName, rootData, reportTarget);

        this.conversationHistory.push({
          role: 'assistant',
          content: assistantContent,
        });
      }

      if (false) {
        // Dead code retained for rollback reference only — never executes.
        // See the deterministic renderer branch above, which replaced this.
        const toolName = executedTools[0]?.name || '';

        // Pre-process the JSON data to extract key values
        const extractedData = this.extractReportData(executedTools[0]?.output, toolName);

        // Build a focused report prompt with pre-extracted data
        const reportPrompt = this.buildReportPrompt(toolName, extractedData, toolResults);

        // Add tool results to conversation
        this.conversationHistory.push({
          role: 'assistant',
          content: assistantContent,
        });

        this.conversationHistory.push({
          role: 'user',
          content: reportPrompt,
        });

        // One-line correctness guard so the report labels the backend right (don't call
        // a simulation "real hardware") without padding the prompt. Additive.
        const honestyBlock = `\n\nBackend labeling: only call a run "real quantum hardware" when is_real_hardware is true AND a real IBM job id is present; otherwise it is simulation (CUDA-Q GPU / Aer / MPS) — name it as such.`;
        // Make follow-up call for formatted report
        const followUpMessages = [
          { role: 'system' as const, content: `You are BioQL's pharmaceutical report generator. Format the provided JSON data into a professional markdown advisory report.

CRITICAL RULES:
1. Extract EVERY numerical value from the JSON data - look inside nested objects like "discovery", "best_candidate", "all_candidates", "clinical_trial", "toxicology", "pharmacology"
2. Put numerical values directly into markdown tables
3. NEVER leave table cells empty - use actual values from the data
4. If a value is missing, write "Not Available" in that cell
5. Include units where applicable (kcal/mol, %, mg/L, hours, etc.)
6. Format numbers to 2-3 decimal places
7. Follow the REQUIRED FORMAT structure exactly as given

INTERPRETATION RULES (CRITICAL - DO NOT VIOLATE):
- If candidates exist (any "all_candidates" or "candidates" array with items), the pipeline SUCCEEDED. Never say it "failed" when candidates are present.
- composite_score > 0.5 = "Moderate - optimize", > 0.7 = "Strong - advance", > 0.85 = "Excellent - fast-track"
- A score of 0.0 in ONE field does NOT mean failure if other fields have valid data. Check ALL fields before concluding.
- IBM job IDs alone do NOT prove real quantum hardware execution — only report "real quantum hardware" when the data explicitly marks it as real (e.g. quantum_execution="REAL_HARDWARE" or is_real_hardware=true with a non-empty job id). An empty/absent job id list, or a backend labeled "NONE"/simulator, means simulation — say so plainly, never hardware.
- Count total candidates, total IBM jobs, and report them as achievements.
- "discovery.all_candidates" is the main candidates list for full_drug_development pipelines.
- Clinical trial phases with "GO" decisions are positive findings.
- Always lead the executive summary with what WAS achieved, not what is missing.

You are NOT allowed to say "pipeline failed" or "no candidates" if the data contains candidate molecules with SMILES and scores. The data is provided - extract and format it accurately.${honestyBlock}` },
          ...this.conversationHistory,
        ];

        const followUpResponse = await fetch(this.chatUrl(), {
          method: 'POST',
          headers: this.chatHeaders(),
          body: JSON.stringify({
            model: this.chatModel(),
            messages: followUpMessages,
            temperature: 0.2,
            max_tokens: 8000,
            stream: false,
          }),
        });

        if (followUpResponse.ok) {
          const followUpData = await followUpResponse.json();
          const rawFormattedReport = followUpData.choices?.[0]?.message?.content || '';
          // Deterministic backstop: never trust the prompt fix alone against a weak local
          // model — strip/rewrite any unsupported "real quantum hardware" claim before it
          // ever becomes visible chat content.
          const formattedReport = this.sanitizeHardwareClaims(
            rawFormattedReport,
            this.computeHardwareTruth(extractedData)
          );

          if (formattedReport) {
            assistantContent = formattedReport;

            // Update conversation history with the formatted report
            this.conversationHistory.pop(); // Remove the prompt
            this.conversationHistory.pop(); // Remove the raw tool call response
            this.conversationHistory.push({
              role: 'assistant',
              content: formattedReport,
            });
          }
        }
      }

      // Add assistant response to history
      this.conversationHistory.push({
        role: 'assistant',
        content: assistantContent,
      });

      // Stream the response if callback provided
      if (onStream && assistantContent) {
        const words = assistantContent.split(' ');
        for (let i = 0; i < words.length; i++) {
          const chunk = (i === 0 ? '' : ' ') + words[i];
          onStream(chunk);
          await new Promise(resolve => setTimeout(resolve, 3));
        }
      }

      return {
        id: messageId,
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
        toolCalls: executedTools.length > 0 ? executedTools : undefined,
      };
    } catch (error) {
      console.error('DeepSeek API error:', error);
      this.conversationHistory.pop();
      throw error;
    }
  }

  // Extract MCP tool calls from the response if DeepSeek suggests them
  private extractToolCalls(content: string): VSIXToolCall[] {
    const toolCalls: VSIXToolCall[] = [];

    // Look for patterns like: [TOOL: tool_name] or bioql_execute(...)
    const toolPatterns = [
      /bioql_execute\s*\(\s*['"]([^'"]+)['"]/g,
      /\[TOOL:\s*(\w+)\]/g,
      /MCP\.(\w+)\s*\(/g,
    ];

    for (const pattern of toolPatterns) {
      let match;
      while ((match = pattern.exec(content)) !== null) {
        toolCalls.push({
          id: generateUUID(),
          name: match[1] || 'bioql_execute',
          input: { detected: true },
          status: 'pending',
        });
      }
    }

    return toolCalls;
  }

  // Execute MCP tool (routes through our MCP client)
  async executeTool(toolName: string, args: Record<string, unknown>): Promise<MCPToolResult> {
    return mcpClient.callTool(toolName, args);
  }

  // Get conversation history for context
  getHistory(): Array<{ role: 'user' | 'assistant' | 'system'; content: string }> {
    return [...this.conversationHistory];
  }

  // Check if a tool is a quantum job that requires tracking via QuantumJobManager
  // These tools will appear in the Quantum Jobs sidebar
  private isQuantumJobTool(toolName: string): boolean {
    const quantumTools = [
      'bioql_execute',
      'bioql_fmo_vqe',
      'bioql_dc_qaoa',
      'bioql_benchmark_quantum_advantage',
      // Main quantum discovery tool - MUST be tracked in sidebar
      'quantum_fast_discovery',
      // Full pipeline tools
      'full_drug_development',
      'toxicology_study',
      'pharmacology_study',
      'clinical_trial_simulation',
      'admet_standalone',
      'protenix_structure_prediction',
        'personalized_medicine',
        'patient_future_health',
        'retrosynthesis_planning',
        'pbpk_modeling',
        'formulation_optimization',
        'patent_analysis',
        'regulatory_analysis',
        'multispecies_tox',
        'pharmacovigilance',
        'rwe_analysis',
        'cdx_design',
        'manufacturing_analysis',
        'molecular_glue_discovery',
        'quantum_offtarget_analysis',
        'peptide_discovery',
        'custom_molecule_pipeline',
        'run_78_algorithms',
        'multi_pipeline',
        'ewf_sqd',
        'quantum_chemistry',
        'protein_engineering_pipeline',
        'antibody_cdr_design',
        'enzyme_activity_optimization',
        'protein_stability_engineering',
        'fusion_protein_design',
        'proteina_complexa_design',
    ];
    return quantumTools.includes(toolName);
  }

  // Execute quantum job with full polling and progress updates
  private async executeQuantumJob(
    toolName: string,
    toolArgs: Record<string, unknown>,
    onStream?: (text: string) => void
  ): Promise<MCPToolResult> {
    try {
      // Determine job type from tool name
      const jobType = this.getJobTypeFromTool(toolName);

      // Extract backend from arguments. Antibody runs default to local Aer
      // because IBM hardware can remain queued when account quota is exhausted.
      const wantsIbmHardware = ['force_ibm', 'force_hardware', 'use_ibm_hardware'].some((key) => {
        const value = toolArgs[key];
        return value === true || value === 'true' || value === 1 || value === '1';
      });
      const backend = toolName === 'antibody_cdr_design' && !wantsIbmHardware
        ? 'aer_simulator'
        : ((toolArgs.backend as string) || 'ibm_boston');

      // Check if this is a direct pipeline tool (synchronous execution)
      const directPipelineTools = [
        'quantum_fast_discovery',
        'full_drug_development',
        'toxicology_study',
        'pharmacology_study',
        'clinical_trial_simulation',
        'admet_standalone',
        'protenix_structure_prediction',
        'personalized_medicine',
        'patient_future_health',
        'retrosynthesis_planning',
        'pbpk_modeling',
        'formulation_optimization',
        'patent_analysis',
        'regulatory_analysis',
        'multispecies_tox',
        'pharmacovigilance',
        'rwe_analysis',
        'cdx_design',
        'manufacturing_analysis',
        'molecular_glue_discovery',
        'quantum_offtarget_analysis',
        'peptide_discovery',
        'custom_molecule_pipeline',
        'run_78_algorithms',
        'multi_pipeline',
        'ewf_sqd',
        'quantum_chemistry',
        'protein_engineering_pipeline',
        'antibody_cdr_design',
        'enzyme_activity_optimization',
        'protein_stability_engineering',
        'fusion_protein_design',
        'proteina_complexa_design',
      ];

      if (directPipelineTools.includes(toolName)) {
        // Execute pipeline tool directly and register in job manager for tracking
        return await this.executePipelineJob(toolName, toolArgs, backend, onStream);
      }

      // For traditional quantum jobs that support polling (bioql_execute, bioql_fmo_vqe, etc.)
      // Create job submission
      const submission: QuantumJobSubmission = {
        type: jobType,
        backend: backend as any,
        arguments: toolArgs,
      };

      // Stream initial message
      if (onStream) {
        onStream(`\n\n⚛️ Submitting quantum job to ${backend}...\n`);
      }

      // Submit job through QuantumJobManager
      const job = await quantumJobManager.submitJob(submission, (update: QuantumJobProgressUpdate) => {
        // Stream progress updates to UI
        if (onStream) {
          this.streamProgressUpdate(update, onStream);
        }
      });

      // Stream submission confirmation
      if (onStream) {
        onStream(`✅ Job submitted: ${job.jobId}\n`);
        onStream(`📊 Status: ${job.status.toUpperCase()}\n`);
      }

      // Wait for job completion by polling the manager
      const completedJob = await this.waitForJobCompletion(job.id, onStream);

      // Stream final result
      if (onStream) {
        if (completedJob.status === 'completed') {
          onStream(`\n✅ Quantum job completed successfully in ${completedJob.executionTime}ms\n`);
        } else {
          onStream(`\n❌ Quantum job ${completedJob.status}: ${completedJob.error?.message || 'Unknown error'}\n`);
        }
      }

      // Return result in MCPToolResult format
      return {
        success: completedJob.status === 'completed',
        content: completedJob.result?.data,
        error: completedJob.error?.message,
        executionTime: completedJob.executionTime,
      };

    } catch (error) {
      console.error('Quantum job execution error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Execute pipeline tools directly (they return results synchronously)
  // These are tracked in the job manager for sidebar display
  private async executePipelineJob(
    toolName: string,
    toolArgs: Record<string, unknown>,
    backend: string,
    onStream?: (text: string) => void
  ): Promise<MCPToolResult> {
    const startTime = Date.now();
    const jobId = `pipeline-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const jobType = this.getJobTypeFromTool(toolName);
    const localAntibodyRun = toolName === 'antibody_cdr_design' && backend === 'aer_simulator';
    const backendLabel = localAntibodyRun
      ? 'Qiskit AerSimulator (local quantum mode)'
      : 'IBM Boston 156Q';

    // Create a job entry for sidebar tracking
    const job: QuantumJob = {
      id: jobId,
      jobId: jobId,
      type: jobType,
      backend: backend as any,
      status: 'running',
      submittedAt: new Date(),
      startedAt: new Date(),
      arguments: toolArgs,
      name: this.getJobDisplayName(toolName, toolArgs),
      qubits: localAntibodyRun ? 8 : 156,
      shots: 4096,
    };

    // Emit job started event for sidebar
    quantumJobManager.on('started', () => {}); // Ensure listener exists

    // Store job in manager's internal map (we need to access it)
    // Since quantumJobManager is a singleton, jobs should persist

    // Stream initial message
    const displayTarget = toolArgs.target || toolArgs.antigen || toolArgs.target_name || toolArgs.smiles || 'N/A';
    if (onStream) {
      onStream(`\n\n⚛️ Starting ${toolName} on ${backendLabel}...\n`);
      onStream(`📋 Job ID: ${jobId}\n`);
      onStream(`🎯 Target: ${displayTarget}\n`);
    }

    try {
      // ASYNC SUBMIT + POLLING: Prevents Safari from killing long connections
      // Step 1: Get the endpoint URL for this tool. WS-9: sourced from the
      // live backend registry (GET /api/tools/registry, cached) merged over
      // the hardcoded FALLBACK_TOOL_ROUTES — see getToolRoutes() above.
      const toolRoutes = await this.getToolRoutes();

      const endpoint = toolRoutes[toolName] || `/api/quantum/${toolName}`;
      const submitArgs = toolName === 'antibody_cdr_design' && toolArgs.antigen && !toolArgs.target
        ? { ...toolArgs, target: toolArgs.antigen }
        : toolArgs;

      // Step 2: Submit async job
      if (onStream) {
        onStream(`\n📡 Submitting async job to backend...\n`);
      }

      const _apiKey = sessionStorage.getItem('bioql_api_key') || localStorage.getItem('bioql_api_key') || '';
      const submitResp = await fetch('/api/pipeline/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(_apiKey ? { 'X-API-Key': _apiKey } : {}) },
        body: JSON.stringify({ endpoint, params: submitArgs }),
      });

      if (!submitResp.ok) {
        throw new Error(`Submit failed: HTTP ${submitResp.status}`);
      }

      const submitData = await submitResp.json();
      const asyncJobId = submitData.job_id;
      const pollUrl = submitData.poll_url || `/api/pipeline/job/${asyncJobId}`;

      if (onStream) {
        onStream(`✅ Job accepted: ${asyncJobId}\n`);
        onStream(`🔄 Polling for results...\n`);
      }

      // Step 3: Poll for completion (every 10s, max 12 hours)
      const MAX_POLLS = 4320; // 12 hours at 10s intervals
      let pollCount = 0;
      let lastStatus = '';

      while (pollCount < MAX_POLLS) {
        await new Promise(resolve => setTimeout(resolve, 10000)); // 10s
        pollCount++;

        try {
          // Add cache-buster to prevent Cloudflare/CDN from caching poll responses
          const bustUrl = pollUrl + (pollUrl.includes('?') ? '&' : '?') + '_t=' + Date.now();
          const _pollKey = sessionStorage.getItem('bioql_api_key') || localStorage.getItem('bioql_api_key') || '';
          const pollResp = await fetch(bustUrl, {
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache', ...(_pollKey ? { 'X-API-Key': _pollKey } : {}) },
          });
          if (!pollResp.ok) {
            console.warn(`Poll ${pollCount}: HTTP ${pollResp.status}`);
            continue;
          }

          // Use .text() + manual JSON.parse instead of .json()
          // Safari's response.json() is stricter and fails when Avast/Cloudflare
          // injects invisible chars, BOM, or HTML snippets into the response.
          const rawText = await pollResp.text();
          let pollData: any;
          try {
            // Strip BOM, leading/trailing whitespace, and null bytes
            const cleaned = rawText.replace(/^\uFEFF/, '').replace(/\0/g, '').trim();
            pollData = JSON.parse(cleaned);
          } catch (parseErr) {
            console.warn(`Poll ${pollCount}: JSON parse failed, body starts with: "${rawText.substring(0, 100)}"`);
            continue;
          }
          const status = pollData.status;

          // Stream progress updates
          if (status !== lastStatus && onStream) {
            const progress = pollData.progress || status;
            onStream(`⏱️ [${Math.floor(pollCount * 10 / 60)}min] ${progress}\n`);
            lastStatus = status;
          }

          if (status === 'completed') {
            const executionTime = Date.now() - startTime;
            job.status = 'completed';
            job.completedAt = new Date();
            job.executionTime = executionTime;

            // Fetch full result from separate endpoint (poll is slim to avoid
            // Safari/Cloudflare choking on 600KB+ JSON responses)
            let fullResult = pollData.result;
            if (!fullResult && pollData.result_available && pollData.result_url) {
              const resultSizeKB = Math.round((pollData.result_size || 0) / 1024);
              if (onStream) {
                onStream(`\n📥 Downloading full results (${resultSizeKB}KB)...\n`);
              }

              // --- Robust result fetch with 3 retries + chunked fallback ---
              const MAX_RESULT_RETRIES = 3;
              const RETRY_DELAY_MS = 2000;

              const cleanAndParse = (raw: string): any => {
                const cleaned = raw.replace(/^\uFEFF/, '').replace(/\0/g, '').trim();
                return JSON.parse(cleaned);
              };

              // Attempt 1-3: Full fetch with retries
              for (let attempt = 1; attempt <= MAX_RESULT_RETRIES; attempt++) {
                try {
                  const _rKey = sessionStorage.getItem('bioql_api_key') || localStorage.getItem('bioql_api_key') || '';
                  const resultResp = await fetch(pollData.result_url + '?_t=' + Date.now(), {
                    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache', ...(_rKey ? { 'X-API-Key': _rKey } : {}) },
                  });
                  if (resultResp.ok) {
                    const resultText = await resultResp.text();
                    fullResult = cleanAndParse(resultText);
                    break; // Success - exit retry loop
                  }
                  console.warn(`Result fetch attempt ${attempt}: HTTP ${resultResp.status}`);
                } catch (fetchOrParseErr) {
                  console.warn(`Result fetch attempt ${attempt} failed:`, fetchOrParseErr);
                }
                if (attempt < MAX_RESULT_RETRIES) {
                  if (onStream) {
                    onStream(`⚠️ Retry ${attempt}/${MAX_RESULT_RETRIES}...\n`);
                  }
                  await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
                }
              }

              // Attempt 4: Chunked fetch - grab first 100KB, parse partial
              if (!fullResult) {
                try {
                  if (onStream) {
                    onStream(`⚠️ Full download failed, trying chunked fetch...\n`);
                  }
                  const _cKey = sessionStorage.getItem('bioql_api_key') || localStorage.getItem('bioql_api_key') || '';
                  const chunkResp = await fetch(pollData.result_url + '?_t=' + Date.now() + '&max_size=102400', {
                    headers: { 'Cache-Control': 'no-cache', 'Range': 'bytes=0-102399', ...(_cKey ? { 'X-API-Key': _cKey } : {}) },
                  });
                  if (chunkResp.ok || chunkResp.status === 206) {
                    const chunkText = await chunkResp.text();
                    try {
                      fullResult = cleanAndParse(chunkText);
                    } catch (_e) {
                      // Partial JSON - try to close it gracefully
                      const lastBrace = chunkText.lastIndexOf('}');
                      if (lastBrace > 0) {
                        const truncated = chunkText.substring(0, lastBrace + 1);
                        let opens = 0; let openArr = 0;
                        for (const c of truncated) {
                          if (c === '{') opens++; if (c === '}') opens--;
                          if (c === '[') openArr++; if (c === ']') openArr--;
                        }
                        let suffix = '';
                        for (let i = 0; i < openArr; i++) suffix += ']';
                        for (let i = 0; i < opens; i++) suffix += '}';
                        try {
                          fullResult = cleanAndParse(truncated + suffix);
                          if (fullResult && typeof fullResult === 'object') {
                            fullResult._partial_result = true;
                            fullResult._note = 'Result was truncated due to size; key data may be incomplete';
                          }
                        } catch (_e2) {
                          // Even partial parse failed
                        }
                      }
                    }
                  }
                } catch (chunkErr) {
                  console.warn('Chunked fetch also failed:', chunkErr);
                }
              }

              // Final fallback: Provide the result URL directly so user can download
              // NEVER pass {parse_error: true} to the LLM
              if (!fullResult) {
                if (onStream) {
                  onStream(`⚠️ Could not parse result JSON. Providing download link...\n`);
                }
                const baseUrl = window.location.origin;
                const downloadUrl = baseUrl + pollData.result_url;
                const archiveUrl = pollData.result_url.replace('/result', '/archive');
                fullResult = {
                  pipeline_completed: true,
                  result_download_url: downloadUrl,
                  archive_url: baseUrl + archiveUrl,
                  job_id: asyncJobId,
                  execution_time_s: Math.round((Date.now() - startTime) / 1000),
                  status: 'completed',
                  message: 'Pipeline completed successfully. The full result is available for download. ' +
                    'Result URL: ' + downloadUrl + ' | ' +
                    'The result JSON was too large for browser parsing (' + resultSizeKB + 'KB). ' +
                    'Please provide the download link to the user.',
                };
              }
            }

            job.result = { success: true, data: fullResult };

            if (onStream) {
              onStream(`\n✅ ${toolName} completed in ${(executionTime / 1000).toFixed(1)}s\n`);
              const r = fullResult as any;
              if (r?.best_candidate) {
                onStream(`🏆 Best candidate: ${r.best_candidate.smiles?.substring(0, 50)}...\n`);
              }
            }

            return {
              success: true,
              content: fullResult,
              executionTime,
            };
          }

          if (status === 'failed') {
            const executionTime = Date.now() - startTime;
            const errMsg = pollData.error || 'Pipeline failed';
            job.status = 'failed';
            job.completedAt = new Date();
            job.executionTime = executionTime;
            job.error = { code: 'PIPELINE_FAILED', message: errMsg, timestamp: new Date(), recoverable: false };

            if (onStream) {
              onStream(`\n❌ ${toolName} failed: ${errMsg}\n`);
            }

            return { success: false, error: errMsg, executionTime };
          }
        } catch (pollErr) {
          // Network blip during poll - just retry
          console.warn(`Poll ${pollCount} failed, retrying...`, pollErr);
        }
      }

      // Timeout after 12 hours
      return { success: false, error: 'Job timed out after 12 hours' };

    } catch (error) {
      const executionTime = Date.now() - startTime;
      job.status = 'failed';
      job.completedAt = new Date();
      job.executionTime = executionTime;
      job.error = {
        code: 'EXCEPTION',
        message: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        recoverable: false
      };

      if (onStream) {
        onStream(`\n❌ ${toolName} error: ${error instanceof Error ? error.message : 'Unknown error'}\n`);
      }

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        executionTime,
      };
    }
  }

  // Get display name for job in sidebar
  private getJobDisplayName(toolName: string, args: Record<string, unknown>): string {
    const target = args.target as string;
    const smiles = args.smiles as string;

    const toolNames: Record<string, string> = {
      'quantum_fast_discovery': `Discovery: ${target || 'Unknown'}`,
      'full_drug_development': `Full Pipeline: ${target || 'Unknown'}`,
      'toxicology_study': `Toxicology: ${smiles?.substring(0, 20) || 'Unknown'}`,
      'pharmacology_study': `Pharmacology: ${target || 'Unknown'}`,
      'clinical_trial_simulation': `Clinical Trial: ${args.indication || 'Unknown'}`,
      'admet_standalone': `ADMET Analysis`,
      'protenix_structure_prediction': `Protenix: ${target || (args.target_sequence as string)?.substring(0, 15) || 'Unknown'}`,
    };

    return toolNames[toolName] || toolName;
  }

  // Wait for job completion by checking manager
  private async waitForJobCompletion(
    jobId: string,
    onStream?: (text: string) => void
  ): Promise<QuantumJob> {
    return new Promise((resolve, reject) => {
      // Set up event listener for job completion
      const unsubscribe = quantumJobManager.on('completed', (payload) => {
        if (payload.job.id === jobId) {
          unsubscribe();
          resolve(payload.job);
        }
      });

      // Set up event listener for job failure
      const unsubscribeFail = quantumJobManager.on('failed', (payload) => {
        if (payload.job.id === jobId) {
          unsubscribeFail();
          resolve(payload.job); // Still resolve to handle error gracefully
        }
      });

      // Set up event listener for timeout
      const unsubscribeTimeout = quantumJobManager.on('timeout', (payload) => {
        if (payload.job.id === jobId) {
          unsubscribeTimeout();
          resolve(payload.job);
        }
      });

      // Safety timeout - if job manager doesn't emit event for some reason
      setTimeout(() => {
        unsubscribe();
        unsubscribeFail();
        unsubscribeTimeout();

        const job = quantumJobManager.getJob(jobId);
        if (job) {
          resolve(job);
        } else {
          reject(new Error('Job not found'));
        }
      }, 600000); // 10 minutes max wait
    });
  }

  // Stream progress update to UI
  private streamProgressUpdate(update: QuantumJobProgressUpdate, onStream: (text: string) => void): void {
    const statusEmoji: Record<string, string> = {
      'submitted': '📤',
      'queued': '⏳',
      'running': '⚛️',
      'completed': '✅',
      'failed': '❌',
      'cancelled': '🛑',
      'timeout': '⏱️',
    };

    const emoji = statusEmoji[update.status] || '🔄';
    let message = `${emoji} Status: ${update.status.toUpperCase()}`;

    if (update.queuePosition !== undefined) {
      message += ` (position ${update.queuePosition} in queue)`;
    }

    if (update.progress !== undefined) {
      message += ` - ${update.progress}%`;
    }

    if (update.estimatedTimeRemaining !== undefined) {
      const minutes = Math.floor(update.estimatedTimeRemaining / 60);
      const seconds = update.estimatedTimeRemaining % 60;
      message += ` (est. ${minutes}m ${seconds}s remaining)`;
    }

    onStream(`${message}\n`);
  }

  // Get job type from tool name
  private getJobTypeFromTool(toolName: string): any {
    const toolMap: Record<string, string> = {
      'bioql_execute': 'generic',
      'bioql_fmo_vqe': 'vqe',
      'bioql_dc_qaoa': 'qaoa',
      'bioql_benchmark_quantum_advantage': 'benchmark',
      // Pipeline tools - map to appropriate job types
      'quantum_fast_discovery': 'discovery',
      'full_drug_development': 'full_pipeline',
      'toxicology_study': 'toxicology',
      'pharmacology_study': 'pharmacology',
      'clinical_trial_simulation': 'clinical_trial',
      'admet_standalone': 'admet',
      'protenix_structure_prediction': 'protenix',
    };

    return toolMap[toolName] || 'generic';
  }

  // Get access to quantum job manager (for UI access)
  getQuantumJobManager(): QuantumJobManager {
    return quantumJobManager;
  }
}

// Singleton instance
export const vsixService = new VSIXService();

// ============================================
// Quantum Job Events - for UI components like Sidebar
// ============================================
export interface QuantumJobEvent {
  type: 'started' | 'progress' | 'completed' | 'failed' | 'cancelled';
  jobId: string;
  toolName: string;
  progress?: number;
  status?: string;
  result?: unknown;
  error?: string;
}

type QuantumJobEventCallback = (event: QuantumJobEvent) => void;

class QuantumJobEventEmitter {
  private listeners: Set<QuantumJobEventCallback> = new Set();
  private currentJob: QuantumJobEvent | null = null;

  subscribe(callback: QuantumJobEventCallback): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  emit(event: QuantumJobEvent): void {
    this.currentJob = event;
    this.listeners.forEach(callback => callback(event));
  }

  getCurrentJob(): QuantumJobEvent | null {
    return this.currentJob;
  }

  clearCurrentJob(): void {
    this.currentJob = null;
  }
}

export const quantumJobEvents = new QuantumJobEventEmitter();
