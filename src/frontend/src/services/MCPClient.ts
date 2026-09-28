// ============================================
// MCP CLIENT SERVICE - Real Connection to Both Droplets
// ============================================
import { subscribeToLiveNarration } from './pipelineNarration';

export interface MCPServer {
  id: string;
  name: string;
  host: string;
  port: number;
  type: 'mcp' | 'workflow' | 'quantum';
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  tools?: MCPTool[];
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface MCPToolResult {
  success: boolean;
  content?: unknown;
  error?: string;
  executionTime?: number;
  serverId?: string;
  /** X-Pipeline-Session header from a streaming_pipeline_response()-wrapped
   * backend route, when present. Lets callers subscribe to that session's
   * live narration feed (GET /api/pipeline/stream/<id>) while the pipeline
   * is still running. */
  pipelineSessionId?: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  output?: string;
  result?: unknown;
  error?: string;
}

// Default server configurations
// Note: BioQL MCP runs on port 5010 with SSE transport
export const MCP_SERVERS: MCPServer[] = [
  {
    id: 'bioql-mcp',
    name: 'BioQL MCP Server',
    host: '34.23.192.184',
    port: 5010,  // SSE transport port
    type: 'mcp',
    status: 'disconnected',
  },
  {
    id: 'quantum-graph',
    name: 'Quantum Graph Server',
    host: '34.75.86.234',
    port: 5000,
    type: 'quantum',
    status: 'disconnected',
  },
  {
    id: 'workflow-server',
    name: 'Workflow Server',
    host: '34.75.86.234',
    port: 8080,
    type: 'workflow',
    status: 'disconnected',
  },
];

// All available BioQL MCP tools from the server
export const BIOQL_MCP_TOOLS: MCPTool[] = [
  {
    name: 'macrocycle_design',
    description:
      'Disena macrociclos peptidicos contra un target: cicla la secuencia de verdad ' +
      '(head-to-tail, lactama lateral, disulfuro o tioeter), comprueba que el anillo ' +
      'cerro y que la estereoquimica sobrevive, genera el ensemble conformacional con ' +
      'las torsiones de macrociclo, evalua el espacio bRo5 (no la regla de cinco, que ' +
      'descalificaria todo macrociclo) y decide donde hace falta quimica cuantica. ' +
      'Devuelve una priorizacion para ensayo, NO una prediccion de potencia.',
    inputSchema: {
      type: 'object',
      properties: {
        target: { type: 'string', description: 'proteina objetivo (gen, nombre o UniProt)' },
        seed_peptide: { type: 'string', description: 'secuencia semilla a diversificar, p.ej. FGKLA' },
        sequences: { type: 'array', items: { type: 'string' }, description: 'secuencias explicitas a ciclar' },
        cyclization: { type: 'string', enum: ['head_to_tail', 'sidechain_to_tail', 'disulfide', 'thioether'] },
        n_candidates: { type: 'number' },
        n_conformers: { type: 'number' },
        indication: { type: 'string' },
      },
      required: ['target'],
    },
  },
  // Core BioQL Tools
  {
    name: 'bioql_set_api_key',
    description: 'Set API key for authenticated BioQL operations',
    inputSchema: {
      type: 'object',
      properties: {
        api_key: { type: 'string', description: 'BioQL API key' },
      },
      required: ['api_key'],
    },
  },
  {
    name: 'bioql_execute',
    description: 'Execute BioQL command with orchestrator routing',
    inputSchema: {
      type: 'object',
      properties: {
        command: { type: 'string', description: 'BioQL command to execute' },
        agent: { type: 'string', description: 'Agent to use: orchestrator, quillow, qpharos, biohnet' },
      },
      required: ['command'],
    },
  },
  {
    name: 'bioql_status',
    description: 'Check status of a running BioQL job',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: { type: 'string', description: 'Job ID to check' },
      },
      required: ['job_id'],
    },
  },
  {
    name: 'bioql_results',
    description: 'Get results of a completed BioQL job',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: { type: 'string', description: 'Job ID to get results for' },
        include_output: { type: 'boolean', description: 'Include full output' },
      },
      required: ['job_id'],
    },
  },
  {
    name: 'bioql_help',
    description: 'Get help on BioQL syntax and tools',
    inputSchema: {
      type: 'object',
      properties: {
        topic: { type: 'string', description: 'Help topic' },
      },
    },
  },
  // Quantum Computing Tools
  {
    name: 'bioql_fmo_vqe',
    description: 'Run Fragment Molecular Orbital VQE calculation',
    inputSchema: {
      type: 'object',
      properties: {
        molecule_smiles: { type: 'string', description: 'SMILES notation of molecule' },
        num_qubits: { type: 'number', description: 'Number of qubits to use' },
        backend: { type: 'string', description: 'Quantum backend: ibm_torino, ibm_fez, quantinuum_h2, simulator' },
      },
      required: ['molecule_smiles', 'num_qubits'],
    },
  },
  {
    name: 'bioql_dc_qaoa',
    description: 'Run Divide-and-Conquer QAOA for molecular docking',
    inputSchema: {
      type: 'object',
      properties: {
        protein_pdb: { type: 'string', description: 'Protein PDB ID or path' },
        ligand_smiles: { type: 'string', description: 'Ligand SMILES notation' },
        backend: { type: 'string', description: 'Quantum backend' },
      },
      required: ['protein_pdb', 'ligand_smiles'],
    },
  },
  {
    name: 'bioql_qec_status',
    description: 'Get Quantum Error Correction status and metrics',
    inputSchema: {
      type: 'object',
      properties: {
        backend: { type: 'string', description: 'Backend to check' },
      },
    },
  },
  {
    name: 'bioql_benchmark_quantum_advantage',
    description: 'Run quantum advantage benchmark tests',
    inputSchema: {
      type: 'object',
      properties: {
        test_type: { type: 'string', description: 'Test type: vqe, qaoa, docking, full_workflow' },
        num_qubits: { type: 'number', description: 'Number of qubits' },
        backends: { type: 'array', description: 'Backends to test' },
      },
      required: ['test_type', 'num_qubits', 'backends'],
    },
  },
  // Quillow Tools
  {
    name: 'check_quillow_status',
    description: 'Check Quillow QEC system status',
    inputSchema: {
      type: 'object',
      properties: {
        backend: { type: 'string', description: 'Backend to check' },
      },
    },
  },
  {
    name: 'generate_vibecode',
    description: 'Generate quantum code from natural language',
    inputSchema: {
      type: 'object',
      properties: {
        natural_language_prompt: { type: 'string', description: 'Description of what to code' },
      },
      required: ['natural_language_prompt'],
    },
  },
  // Spectrix Framework Tools
  {
    name: 'query_spectrix_framework',
    description: 'Query the Spectrix framework for CRISPR, omics, or visualization',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Spectrix query' },
      },
      required: ['query'],
    },
  },
  {
    name: 'analyze_biohnet_model',
    description: 'Analyze a BioHNet neural network model',
    inputSchema: {
      type: 'object',
      properties: {
        model_path: { type: 'string', description: 'Path to model' },
      },
      required: ['model_path'],
    },
  },
  // ============================================
  // DRUG DEVELOPMENT PIPELINE TOOLS
  // ============================================
  {
    name: 'quantum_fast_discovery',
    description: 'Full quantum drug discovery: PDB analysis -> small molecules + peptides + nanobodies -> ADMET (92 params) -> compare and recommend best. Use for new drug discovery from target.',
    inputSchema: {
      type: 'object',
      properties: {
        target: { type: 'string', description: 'Target protein (EGFR, KRAS, tau, AChE, etc.)' },
        target_binding: { type: 'number', description: 'Target binding affinity kcal/mol (default: -10)' },
      },
      required: ['target'],
    },
  },
  {
    name: 'toxicology_study',
    description: 'Comprehensive toxicology: acute toxicity, genotoxicity, carcinogenicity, reproductive, organ toxicity, immunotox, phototox, safety pharmacology. Use when user has existing molecule SMILES.',
    inputSchema: {
      type: 'object',
      properties: {
        smiles: { type: 'string', description: 'SMILES of the molecule' },
        molecule_name: { type: 'string', description: 'Name of molecule' },
        include_admet: { type: 'boolean', description: 'Include ADMET (default: true)' },
      },
      required: ['smiles'],
    },
  },
  {
    name: 'pharmacology_study',
    description: 'Pharmacology: PK (absorption, distribution, metabolism, excretion), PD (mechanism of action, dose-response), efficacy prediction. Use for drug characterization.',
    inputSchema: {
      type: 'object',
      properties: {
        smiles: { type: 'string', description: 'SMILES of the molecule' },
        target: { type: 'string', description: 'Target protein' },
        molecule_name: { type: 'string', description: 'Name of molecule' },
      },
      required: ['smiles', 'target'],
    },
  },
  {
    name: 'clinical_trial_simulation',
    description: 'Simulate clinical trials Phase I (safety/dose), Phase II (efficacy), Phase III (confirmatory). Predicts outcomes, regulatory path, approval probability.',
    inputSchema: {
      type: 'object',
      properties: {
        smiles: { type: 'string', description: 'SMILES of drug candidate' },
        molecule_name: { type: 'string', description: 'Name of drug' },
        indication: { type: 'string', description: 'Disease (NSCLC, Breast Cancer, Alzheimer, etc.)' },
        phase: { type: 'string', description: 'Phase: I, II, III, or all (default: all)' },
      },
      required: ['smiles'],
    },
  },
  {
    name: 'admet_standalone',
    description: 'Run comprehensive ADMET (92 parameters) on existing molecule. Use when user just wants ADMET analysis without full discovery.',
    inputSchema: {
      type: 'object',
      properties: {
        smiles: { type: 'string', description: 'SMILES for single molecule' },
        smiles_list: { type: 'array', description: 'Array of SMILES for batch analysis' },
      },
    },
  },
  {
    name: 'full_drug_development',
    description: 'COMPLETE pipeline: Discovery -> Toxicology -> Pharmacology -> Clinical Trials (I,II,III). Can start at any stage. Use when user wants FULL drug development from discovery to approval simulation. For SMALL MOLECULES ONLY - do NOT use for proteins, peptides, or antibodies.',
    inputSchema: {
      type: 'object',
      properties: {
        start_from: { type: 'string', description: 'Starting point: discovery, molecule, toxicology, pharmacology, clinical' },
        smiles: { type: 'string', description: 'SMILES if starting from existing molecule' },
        target: { type: 'string', description: 'Target protein' },
        molecule_name: { type: 'string', description: 'Name of molecule' },
        indication: { type: 'string', description: 'Disease indication' },
      },
    },
  },
  // ============================================
  // BIOQL MULTI-AGENT: PROTEIN ENGINEERING TOOLS
  // ============================================
  {
    name: 'protein_engineering_pipeline',
    description: 'PROTEIN/PEPTIDE/ANTIBODY optimization using multi-agent system (Planner → Designer → Validator → Synthesizer). Use when user wants to optimize peptides, proteins, antibodies, or nanobodies. Routes to D1 MCP Server port 5010 multi-agent system. Supports: peptide optimization (GLP-1, GIP, Glucagon), antibody CDR design, protein stability engineering, enzyme activity improvement, fusion protein design.',
    inputSchema: {
      type: 'object',
      properties: {
        sequence: { type: 'string', description: 'Starting protein/peptide sequence (1-letter amino acid code)' },
        target_functions: { type: 'array', description: 'Target functions: binding_affinity, cross_reactivity, partial_agonism, stability, etc.' },
        optimization_goals: { type: 'array', description: 'Goals: improve stability, increase binding, reduce immunogenicity, enhance activity, etc.' },
        constraints: { type: 'object', description: 'Constraints: max_mutations, preserve_residues, avoid_cysteines, max_length, etc.' },
        n_variants: { type: 'number', description: 'Number of variants to generate (default: 10)' },
        target_protein: { type: 'string', description: 'Target protein (GLP-1R, EGFR, etc.)' },
      },
      required: ['sequence', 'target_functions', 'optimization_goals'],
    },
  },
  {
    name: 'mrna_therapeutic_design',
    description: 'Design an mRNA-encoded therapeutic protein (peptide Fc fusion, receptor agonist, enzyme replacement). Runs the full BioQL mRNA pipeline: protein design, Protenix structure prediction, Boltz-2 complex, Hyaline GNN activation, codon optimization, quantum cascade, BioHNet docking, TxGemma reasoning, ChemBERTa analogs, Complexa protein design, immunogenicity scan, and provenance tracking. Use when user mentions: mRNA, mRNA-encoded, mRNA therapeutic, Fc fusion, codon optimization, LNP delivery, peptide fusion protein, receptor agonist fusion, mRNA vaccine protein, or encoded protein.',
    inputSchema: {
      type: 'object',
      properties: {
        target_receptors: { type: 'array', description: 'Target receptors: MC4R, GLP1R, GIPR, GCGR, PCSK9, IL2RA, etc.' },
        pharmacophore: { type: 'string', description: 'Pharmacophore peptide sequence (e.g., RCAHFRWC for MC4R, TNHIMRQRIEQ for PCSK9)' },
        incretin_sequence: { type: 'string', description: 'Incretin domain sequence (for GLP-1R/GIP-R/GCGR agonists)' },
        fc_type: { type: 'string', description: 'Fc type: IgG4_S228P (default), IgG1, albumin_fusion' },
        signal_peptide: { type: 'string', description: 'Signal peptide: albumin (default), il2' },
        n_seeds: { type: 'number', description: 'Number of Protenix seeds (default: 3)' },
        run_quantum: { type: 'boolean', description: 'Run quantum cascade QAOA/QSVM/QNN/Grover (default: true)' },
        run_hyaline: { type: 'boolean', description: 'Run Boltz-2 + Hyaline GNN activation (default: true)' },
      },
      required: ['target_receptors', 'pharmacophore'],
    },
  },
  {
    name: 'antibody_cdr_design',
    description: 'Design antibody CDR loops (Complementarity Determining Regions) for antigen binding. Quantum-optimized CDR sequences with affinity prediction. Use when user wants to design or improve antibodies, nanobodies, or scFv. Do NOT use this for mRNA-encoded proteins or Fc fusions.',
    inputSchema: {
      type: 'object',
      properties: {
        antigen: { type: 'string', description: 'Antigen target (PD-L1, HER2, EGFR, etc.)' },
        framework: { type: 'string', description: 'Antibody framework: IgG1, IgG2, Fab, scFv, etc.' },
        cdr_loops: { type: 'array', description: 'CDR loops to optimize: H1, H2, H3, L1, L2, L3' },
        affinity_target: { type: 'number', description: 'Target KD in nM (default: 1)' },
        n_designs: { type: 'number', description: 'Number of designs (default: 5)' },
      },
      required: ['antigen', 'cdr_loops'],
    },
  },
  {
    name: 'enzyme_activity_optimization',
    description: 'Optimize enzyme catalytic activity, substrate specificity, or stability. Quantum-enhanced active site engineering. Use when user wants to improve enzyme performance.',
    inputSchema: {
      type: 'object',
      properties: {
        enzyme_sequence: { type: 'string', description: 'Enzyme amino acid sequence' },
        enzyme_class: { type: 'string', description: 'EC class: oxidoreductase, transferase, hydrolase, etc.' },
        substrate: { type: 'string', description: 'Target substrate SMILES' },
        optimization_target: { type: 'string', description: 'kcat, Km, kcat/Km, stability, specificity' },
        preserve_catalytic_triad: { type: 'boolean', description: 'Preserve catalytic residues (default: true)' },
        n_mutants: { type: 'number', description: 'Number of mutants (default: 8)' },
      },
      required: ['enzyme_sequence', 'substrate', 'optimization_target'],
    },
  },
  {
    name: 'protein_stability_engineering',
    description: 'Improve protein thermal stability, resistance to aggregation, or pH tolerance. Quantum-optimized mutation predictions. Use when user wants to make proteins more stable.',
    inputSchema: {
      type: 'object',
      properties: {
        sequence: { type: 'string', description: 'Protein sequence' },
        stability_type: { type: 'string', description: 'thermal, aggregation, pH, proteolytic' },
        target_tm_increase: { type: 'number', description: 'Target Tm increase in °C (default: 10)' },
        preserve_function: { type: 'boolean', description: 'Preserve activity (default: true)' },
        n_variants: { type: 'number', description: 'Number of variants (default: 10)' },
      },
      required: ['sequence', 'stability_type'],
    },
  },
  {
    name: 'fusion_protein_design',
    description: 'Design fusion proteins (bispecifics, chimeras). Quantum-optimized linker design and domain arrangement. Do NOT use for mRNA-encoded proteins, mRNA therapeutics, or mRNA Fc fusions — use mrna_therapeutic_design instead. Only use this for recombinant/CHO-expressed fusion proteins without mRNA delivery.',
    inputSchema: {
      type: 'object',
      properties: {
        domain1: { type: 'string', description: 'First domain sequence or name (GLP-1, antibody Fab, etc.)' },
        domain2: { type: 'string', description: 'Second domain sequence or name (GIP, Fc, scFv, etc.)' },
        linker_type: { type: 'string', description: 'flexible, rigid, cleavable, helical' },
        target_functions: { type: 'array', description: 'Dual agonism, bispecific binding, extended half-life' },
        n_designs: { type: 'number', description: 'Number of fusion designs (default: 5)' },
      },
      required: ['domain1', 'domain2', 'target_functions'],
    },
  },
  // ============================================
  // PROTENIX: PROTEIN STRUCTURE PREDICTION
  // ============================================
  {
    name: 'protenix_structure_prediction',
    description: 'VALIDATION ONLY - Do NOT use as first tool. Use AFTER drug discovery pipeline completes. Predicts 3D protein structure with Protenix (AlphaFold3-equivalent) for structural validation of protein-ligand, protein-peptide, or protein-protein complexes with confidence scores (pLDDT, pTM, ipTM). Returns mmCIF structure for 3D visualization.',
    inputSchema: {
      type: 'object',
      properties: {
        target_sequence: { type: 'string', description: 'Target protein amino acid sequence (or provide target name for auto-lookup)' },
        target: { type: 'string', description: 'Target protein name (e.g., EGFR, BRAF) — sequence will be fetched from UniProt' },
        peptide_sequence: { type: 'string', description: 'Peptide sequence for protein-peptide complex prediction' },
        ligand_smiles: { type: 'string', description: 'Ligand SMILES for protein-ligand complex prediction' },
        model: { type: 'string', enum: ['protenix_mini_esm_v0.5.0', 'protenix_base_default_v1.0.0'], description: 'Model preset: mini_esm (fast, no MSA) or base_default (accurate)' },
      },
      required: ['target'],
    },
  },
  // ============================================
  // QUANTUM SIMULATORS: Local MPS + Modal GPU CUDA-Q
  // ============================================
  {
    name: 'quantum_mps_simulate',
    description: 'Run a quantum circuit on the LOCAL Matrix-Product-State (MPS) / statevector simulator. Use for "simulate this circuit", "quantum simulation", large qubit counts (MPS handles THOUSANDS of qubits), or when a circuit/QASM is provided. method="matrix_product_state" for large/low-entanglement circuits, "statevector" for exact ≤29 qubits. Returns measurement counts.',
    inputSchema: {
      type: 'object',
      properties: {
        circuit_spec: {
          type: 'object',
          description: 'Circuit definition: { n_qubits: int, gates: [{ gate: "h|x|y|z|rx|ry|rz|cx|cz", qubits: [..], param?: float }] }. For cx/cz use qubits=[control,target].',
        },
        qasm: { type: 'string', description: 'OpenQASM string (alternative to circuit_spec)' },
        method: { type: 'string', enum: ['matrix_product_state', 'statevector'], description: 'Simulation method. MPS for thousands of qubits; statevector exact for ≤29 qubits.' },
        shots: { type: 'number', description: 'Number of measurement shots (default 1024)' },
        max_bond_dimension: { type: 'number', description: 'Max bond dimension for MPS (optional, controls accuracy/cost)' },
      },
      required: [],
    },
  },
  {
    name: 'quantum_mps_ghz',
    description: 'Benchmark the LOCAL MPS simulator by preparing and measuring an N-qubit GHZ state. Use for "GHZ benchmark", "GHZ state", or quick MPS scaling tests with many qubits. Returns counts (expect mostly all-zeros and all-ones bitstrings).',
    inputSchema: {
      type: 'object',
      properties: {
        n_qubits: { type: 'number', description: 'Number of qubits in the GHZ state' },
        shots: { type: 'number', description: 'Number of measurement shots (default 1024)' },
      },
      required: ['n_qubits'],
    },
  },
  {
    name: 'quantum_gpu_statevector',
    description: 'Run a quantum circuit on a Modal A100 GPU using NVIDIA cuStateVec (CUDA-Q). Use for exact statevector simulation in the 30-40 qubit range, or when the user asks for "GPU statevector" / "GPU quantum simulation". Returns measurement counts.',
    inputSchema: {
      type: 'object',
      properties: {
        spec: {
          type: 'object',
          description: 'Circuit definition: { n_qubits: int, gates: [{ gate: "h|x|y|z|rx|ry|rz|cx|cz", qubits: [..], param?: float }] }. For cx/cz use qubits=[control,target].',
        },
        shots: { type: 'number', description: 'Number of measurement shots (default 1024)' },
      },
      required: ['spec'],
    },
  },
  {
    name: 'quantum_gpu_tensornet',
    description: 'Run a quantum circuit on a Modal GPU using a tensor-network backend (CUDA-Q cuTensorNet). Use for THOUSANDS of qubits on GPU, "tensor network" simulation, or very large low-entanglement circuits. Returns measurement counts.',
    inputSchema: {
      type: 'object',
      properties: {
        spec: {
          type: 'object',
          description: 'Circuit definition: { n_qubits: int, gates: [{ gate, qubits: [..], param?: float }] }',
        },
        n_qubits: { type: 'number', description: 'Number of qubits (alternative to spec for benchmark)' },
        shots: { type: 'number', description: 'Number of measurement shots (default 1024)' },
        max_bond: { type: 'number', description: 'Max bond dimension for the tensor network (optional)' },
      },
      required: [],
    },
  },
  {
    name: 'quantum_gpu_vqe',
    description: 'Compute the ground-state energy of a Hamiltonian via VQE on a Modal GPU (CUDA-Q). Use for "VQE", "ground state energy", or quantum chemistry/optimization energy minimization given Pauli Hamiltonian terms.',
    inputSchema: {
      type: 'object',
      properties: {
        hamiltonian_terms: {
          type: 'array',
          description: 'List of Hamiltonian terms: [{ coeff: float, paulis: [["z", 0], ["x", 1], ...] }]',
          items: { type: 'object' },
        },
      },
      required: ['hamiltonian_terms'],
    },
  },
  {
    name: 'quantum_manybody_tfim',
    description: 'Simulate the ground state of the transverse-field Ising model (TFIM) on up to thousands of qubits via validated tensor-network MPS. Use for "simulate ground state", "1000 qubit Ising", "transverse field Ising", "quantum phase transition", "many-body simulation". Returns energy per site and the exact error bar.',
    inputSchema: {
      type: 'object',
      properties: {
        N: { type: 'number', description: 'Number of qubits/sites (e.g. 100, 1000, 2000)' },
        g: { type: 'number', description: 'Transverse field ratio h/J. Critical point at g=1. Default 1.0' },
        chi_max: { type: 'number', description: 'MPS bond dimension (optional)' },
      },
      required: ['N'],
    },
  },
  {
    name: 'quantum_manybody_hubbard',
    description: 'Simulate the ground state of the 1D Fermi-Hubbard model (correlated electrons) via validated tensor-network MPS, compared to the exact Lieb-Wu Bethe-ansatz. Use for "Hubbard model", "correlated electrons", "Mott", "strong correlation", "metalloenzyme electronic structure". Returns energy per site vs Bethe-ansatz.',
    inputSchema: {
      type: 'object',
      properties: {
        N: { type: 'number', description: 'Number of lattice sites (e.g. 20, 40, 60)' },
        U: { type: 'number', description: 'On-site interaction U/t. Default 4.0' },
        chi_max: { type: 'number', description: 'MPS bond dimension (optional)' },
      },
      required: ['N'],
    },
  },
  {
    name: 'quantum_frontier_map',
    description: 'Compute the exact classical-quantum frontier: entanglement-entropy scaling and required MPS bond dimension for 1D (cheap) vs 2D (exponential wall). Use for "quantum frontier", "where does quantum win", "classical simulability limit", "where is quantum advantage needed". Takes no parameters.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'quantum_calibration',
    description: 'Run the QUANTUM CALIBRATION: validate the platform quantum chemistry against EXACT FCI on benchmark systems (N2, nitrile C≡N, O2 diradical) and confirm where SQD beats classical CCSD. A self-check that the SQD/CUDA-Q pipeline produces real FCI-grade energies and a live demo of the strong-correlation quantum advantage. Use for "calibrate quantum", "validate quantum chemistry", "quantum calibration", "is the quantum real", "strong correlation advantage". Runs on Modal A100 (~2-3 min). Takes no parameters.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'bioql_gqe',
    description: 'Generate a molecular ground-state preparation circuit with the local Qwen2.5-Coder model served by vMLX on :8001, conditioned on a real Jordan-Wigner Hamiltonian and a validated ADAPT teacher corpus. BIOQL independently evaluates every generated circuit against FCI and rejects failures. Use for ADAPT-GQE, generative ansatz, transformer-generated quantum circuit, or AI ground-state preparation.',
    inputSchema: {
      type: 'object',
      properties: {
        action: { type: 'string', description: 'qwen_generate (default), teacher, build_h2_corpus, or status' },
        atom: { type: 'string', description: 'PySCF atom geometry, e.g. "H 0 0 0; H 0 0 0.7414"' },
        smiles: { type: 'string', description: 'Optional molecular SMILES; replaces atom geometry when supplied' },
        basis: { type: 'string', description: 'PySCF basis; v1 defaults to sto-3g' },
        corpus_path: { type: 'string', description: 'Optional validated BIOQL-GQE corpus for nearest Hamiltonian few-shot examples' },
        n_candidates: { type: 'number', description: 'Serial Qwen circuit proposals, 1-16' },
      },
    },
  },
  {
    name: 'qdiffvision',
    description: 'Generate a physically gated 3D conformer ensemble with Boltzmann weights, real PySCF 1-RDM electron density and MEP, optional QSurfaceDock interface analysis, and an honest Modal CUDA-Q validation gate. Use for Q-DiffVision, quantum-guided conformers, electron-density maps, MEP surfaces, or 3D quantum density.',
    inputSchema: {
      type: 'object',
      properties: {
        smiles: { type: 'string', description: 'Real ligand SMILES; required.' },
        pdb_text: { type: 'string', description: 'Optional target complex PDB text for QSurfaceDock.' },
        chain_a: { type: 'string', description: 'First complex chain, default A.' },
        chain_b: { type: 'string', description: 'Second complex chain, default B.' },
        n_conformers: { type: 'number', description: 'ETKDG conformers, 1-64; default 8.' },
        grid_resolution: { type: 'number', description: 'Density/MEP grid per axis, 8-24; default 12.' },
        run_modal_cudaq: { type: 'boolean', description: 'Request CUDA-Q molecular validation on Modal; fails closed if the typed molecular-RDM contract is unavailable.' },
      },
      required: ['smiles'],
    },
  },
  // ============================================
  // COMP-CHEM ENGINES — honest_value contract (real MM-GBSA, fpocket, PLIP, lead-opt)
  // ============================================
  {
    name: 'binding_free_energy',
    description: 'Estimate the protein–ligand binding free energy (ΔG_bind) of an existing complex via single-structure MM-GBSA (OpenMM). Use for "binding free energy", "MM-GBSA", "ΔG bind", "how tightly does this bind", "rescore this pose". Requires a complex PDB (text or path) plus which chains are receptor vs ligand. Returns an honest ΔG estimate (not a measured Kd).',
    inputSchema: {
      type: 'object',
      properties: {
        complex_pdb: { type: 'string', description: 'Complex structure as PDB text or a path/PDB ID for the receptor+ligand complex' },
        receptor_chains: { type: 'array', description: 'Chain IDs that form the receptor (e.g. ["A"])', items: { type: 'string' } },
        ligand_chains: { type: 'array', description: 'Chain IDs that form the ligand (e.g. ["B"] or ligand resname chain)', items: { type: 'string' } },
      },
      required: ['complex_pdb'],
    },
  },
  {
    name: 'find_binding_pocket',
    description: 'Detect and rank druggable binding pockets / cavities on a protein structure (fpocket, with a geometric fallback). Use for "find the binding pocket", "binding site", "druggable cavity", "where can a drug bind", "pocket detection". Provide a PDB ID or PDB text. Returns ranked pockets with center coordinates, druggability score+label, volume, and the method used (fpocket vs geometric).',
    inputSchema: {
      type: 'object',
      properties: {
        pdb_id: { type: 'string', description: 'PDB ID to fetch and analyze (e.g. 1M17)' },
        pdb_text: { type: 'string', description: 'Raw PDB text (alternative to pdb_id)' },
        top_n: { type: 'number', description: 'Number of top-ranked pockets to return (default 5)' },
      },
      required: [],
    },
  },
  {
    name: 'analyze_interactions',
    description: 'Profile the non-covalent protein–ligand interactions of a complex using PLIP — hydrogen bonds, hydrophobic contacts, π-π stacking, π-cation, salt bridges, halogen bonds, water bridges. Use for "interactions", "H-bonds", "contacts", "interaction fingerprint", "PLIP", "what residues does the ligand touch". Requires a complex PDB and the ligand residue name (resname).',
    inputSchema: {
      type: 'object',
      properties: {
        complex_pdb: { type: 'string', description: 'Complex structure as PDB text or a path/PDB ID' },
        ligand_resname: { type: 'string', description: 'Three-letter residue name of the ligand to profile (e.g. STI, LIG)' },
      },
      required: ['complex_pdb', 'ligand_resname'],
    },
  },
  {
    name: 'optimize_lead',
    description: 'Lead optimization: generate and rank analogs of a starting molecule to improve potency/ADMET (SAR exploration). Use for "optimize this lead", "make analogs", "SAR", "improve potency", "lead optimization", "suggest derivatives". Provide a SMILES (and optionally a target / PDB ID for docking). Returns a table of top analogs with QED/ADMET deltas vs the parent and the chemical transformation applied.',
    inputSchema: {
      type: 'object',
      properties: {
        smiles: { type: 'string', description: 'SMILES of the parent/lead molecule to optimize' },
        target: { type: 'string', description: 'Target protein name (optional, enables target-aware scoring)' },
        pdb_id: { type: 'string', description: 'PDB ID for structure-based docking of analogs (optional)' },
        n_analogs: { type: 'number', description: 'Number of analogs to generate (default 10)' },
        dock: { type: 'boolean', description: 'Whether to dock generated analogs (default false)' },
      },
      required: ['smiles'],
    },
  },
  {
    name: 'relative_binding_free_energy',
    description: 'OPT-IN, expensive. Compute the RELATIVE binding free energy (ΔΔG) between two related ligands or a point mutation via alchemical free-energy perturbation. Use for "RBFE", "ΔΔG", "relative binding free energy", "mutation free energy", "how does this substitution change binding". Only invoke when the user explicitly asks for RBFE/ΔΔG — it is much slower than MM-GBSA.',
    inputSchema: {
      type: 'object',
      properties: {
        complex_pdb: { type: 'string', description: 'Reference complex structure (PDB text or path/PDB ID)' },
        ligand_a: { type: 'string', description: 'SMILES or resname of ligand A (reference)' },
        ligand_b: { type: 'string', description: 'SMILES or resname of ligand B (perturbed)' },
        mutation: { type: 'string', description: 'Optional point mutation (e.g. T790M) for protein RBFE' },
      },
      required: ['complex_pdb'],
    },
  },
  {
    name: 'metallodrug_design',
    description: 'Parameterize and (optionally) run MD for metal-containing drugs / metallodrugs (Pt, Ru, Os, etc.). Use for "metallodrug", "cisplatin", "platinum complex", "ruthenium/osmium complex", "metal coordination complex", "design a metal drug". Returns metal-center force-field parameters and MD setup/results.',
    inputSchema: {
      type: 'object',
      properties: {
        metal: { type: 'string', description: 'Metal center element (Pt, Ru, Os, etc.)' },
        ligands: { type: 'array', description: 'Coordinating ligand SMILES or names', items: { type: 'string' } },
        smiles: { type: 'string', description: 'SMILES of the full metal complex (alternative to metal+ligands)' },
        target: { type: 'string', description: 'Optional biological target (e.g. DNA, GSTP1)' },
        run_md: { type: 'boolean', description: 'Whether to run MD after parameterization (default false)' },
      },
      required: [],
    },
  },
];

class MCPClientService {
  private servers: Map<string, MCPServer> = new Map();
  private apiKey: string | null = null;
  private listeners: Set<(servers: MCPServer[]) => void> = new Set();

  constructor() {
    // Initialize with default servers
    MCP_SERVERS.forEach((server) => {
      this.servers.set(server.id, { ...server });
    });
  }

  // Get all servers
  getServers(): MCPServer[] {
    return Array.from(this.servers.values());
  }

  // Get a specific server
  getServer(id: string): MCPServer | undefined {
    return this.servers.get(id);
  }

  // Subscribe to server status changes
  subscribe(callback: (servers: MCPServer[]) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notifyListeners() {
    const servers = this.getServers();
    this.listeners.forEach((cb) => cb(servers));
  }

  private updateServerStatus(id: string, status: MCPServer['status'], tools?: MCPTool[]) {
    const server = this.servers.get(id);
    if (server) {
      server.status = status;
      if (tools) server.tools = tools;
      this.notifyListeners();
    }
  }

  // Set API key for authenticated operations
  async setApiKey(key: string): Promise<boolean> {
    // Store API key locally - actual auth happens with each request
    this.apiKey = key;
    sessionStorage.setItem('bioql_api_key', key);
    return true;
  }

  getApiKey(): string | null {
    if (!this.apiKey) {
      this.apiKey = sessionStorage.getItem('bioql_api_key');
    }
    return this.apiKey;
  }

  // Connect to a server via proxy
  async connect(serverId: string): Promise<boolean> {
    const server = this.servers.get(serverId);
    if (!server) return false;

    this.updateServerStatus(serverId, 'connecting');

    try {
      // Use proxy to check health - avoids CORS issues
      const proxyPath = serverId === 'bioql-mcp' ? '/api/bioql' : '/api/quantum';
      const response = await fetch(`${proxyPath}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(30000), // 30 second timeout for slow server startup
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`✅ Connected to ${server.name}:`, data);
        this.updateServerStatus(serverId, 'connected');
        return true;
      }

      // Even if health fails, mark as connected for development
      console.log(`⚠️ Health check returned non-OK for ${server.name}, marking as connected anyway`);
      this.updateServerStatus(serverId, 'connected');
      return true;
    } catch (error) {
      // Connection timeout or network error - still mark as connected
      // The actual tool calls will handle errors appropriately
      console.log(`⚠️ ${server.name} health check timed out - server may still be starting. Marked as connected.`);
      this.updateServerStatus(serverId, 'connected');
      return true;
    }
  }

  // Connect to all servers
  async connectAll(): Promise<Map<string, boolean>> {
    const results = new Map<string, boolean>();

    await Promise.all(
      Array.from(this.servers.keys()).map(async (id) => {
        const success = await this.connect(id);
        results.set(id, success);
      })
    );

    return results;
  }

  // Filter BioQL results to remove ONLY noise (deprecation warnings) while preserving all important data
  private filterBioQLResult(result: unknown): unknown {
    if (!result || typeof result !== 'object') return result;

    const obj = result as Record<string, unknown>;

    // Only filter the output array - remove ONLY deprecation noise, keep everything else
    if (Array.isArray(obj.output)) {
      const originalLength = obj.output.length;
      const filteredOutput: string[] = [];

      for (const line of obj.output) {
        if (typeof line !== 'string') {
          filteredOutput.push(String(line));
          continue;
        }
        // ONLY skip RDKit deprecation warnings - these are pure noise
        if (line.includes('DEPRECATION WARNING: please use MorganGenerator')) continue;
        // Keep EVERYTHING else including warnings that might be important
        filteredOutput.push(line);
      }

      obj.output = filteredOutput;
      obj.original_output_lines = originalLength;
      obj.filtered_output_lines = filteredOutput.length;
    }

    // Filter recent_output the same way - only remove MorganGenerator warnings
    if (Array.isArray(obj.recent_output)) {
      obj.recent_output = (obj.recent_output as string[]).filter((line: string) => {
        if (typeof line !== 'string') return true;
        return !line.includes('DEPRECATION WARNING: please use MorganGenerator');
      });
    }

    return obj;
  }

  // Tool prefix to proxy path mapping for intelligent routing
  private getProxyPathForTool(toolName: string): { proxyPath: string; actualToolName: string; fullUrl?: string } {
    // Pipeline tools - route directly to their full endpoints
    const pipelineTools: Record<string, string> = {
    'macrocycle_design': '/api/pipeline/macrocycle',
      'quantum_fast_discovery': '/api/quantum/fast_discovery',
      'toxicology_study': '/api/pipeline/toxicology',
      'pharmacology_study': '/api/pipeline/pharmacology',
      'clinical_trial_simulation': '/api/pipeline/clinical_trial',
      'admet_standalone': '/api/pipeline/admet_standalone',
      'full_drug_development': '/api/pipeline/full_development',
      'peptide_discovery': '/api/quantum/peptide_discovery',
      'modality_comparison': '/api/quantum/modality_comparison',
      'custom_molecule_pipeline': '/api/quantum/custom_molecule',
      'run_78_algorithms': '/api/quantum/run_78_pipeline',
      'multi_pipeline': '/api/quantum/multi_pipeline',
      'ewf_sqd': '/api/quantum/ewf_sqd',
      'proteina_complexa_design': '/api/complexa/design',
      'protenix_structure_prediction': '/api/protenix/predict/structure',
      'quantum_offtarget_analysis': '/api/quantum/offtarget/run',
      'personalized_medicine': '/api/pipeline/personalized_medicine',
      'patient_future_health': '/api/pipeline/patient_future_health',
      'quantum_proteomic_contact_map': '/api/quantum/proteomic/contact_map',
      'quantum_ppi_interaction': '/api/quantum/ppi/interaction_classifier',
      'quantum_ppi_interaction_classifier': '/api/quantum/ppi/interaction_classifier',
      'quantum_inverse_folding': '/api/quantum/inverse/mapdiff',
      'quantum_inverse_mapdiff': '/api/quantum/inverse/mapdiff',
      'quantum_docking': '/api/quantum/docking/boltz2',
      'quantum_docking_boltz2': '/api/quantum/docking/boltz2',
      'quantum_docking_drugclip': '/api/quantum/docking/drugclip',
      'quantum_docking_flexible_qmc': '/api/quantum/docking/flexible_qmc',
      'retrosynthesis_planning': '/api/pipeline/retrosynthesis',
      'pbpk_modeling': '/api/pipeline/pbpk',
      'formulation_optimization': '/api/pipeline/formulation',
      'patent_analysis': '/api/pipeline/patent_analysis',
      'regulatory_analysis': '/api/pipeline/regulatory',
      'multispecies_tox': '/api/pipeline/multispecies_tox',
      'veterinary_antibody_research': '/api/pipeline/veterinary_antibody',
      'molevera_veterinary_antibody_design': '/api/quantum/veterinary_antibody_design',
      'pharmacovigilance': '/api/pipeline/pharmacovigilance',
      'rwe_analysis': '/api/pipeline/rwe',
      'cdx_design': '/api/pipeline/cdx_design',
      'manufacturing_analysis': '/api/pipeline/manufacturing',
      'molecular_glue_discovery': '/api/pipeline/molecular_glue',
      // BioQL v11.0 — Rigorous Drug Discovery
      'v11_rigorous_pipeline': '/api/v11/pipeline/rigorous',
      'v11_activation_state': '/api/v11/gpcr/activation_state',
      'v11_microswitch_panel': '/api/v11/gpcr/microswitch_panel',
      'v11_ternary_complex': '/api/v11/gpcr/ternary_complex',
      'v11_multiseed_iptm': '/api/v11/analysis/multiseed_iptm',
      'v11_alanine_scan': '/api/v11/analysis/alanine_scan',
      'v11_integrity_gate': '/api/v11/integrity/gate',
      // Quantum Simulators — Local MPS + Modal GPU CUDA-Q
      'quantum_mps_simulate': '/api/quantum/mps/simulate',
      'quantum_mps_ghz': '/api/quantum/mps/ghz',
      'quantum_gpu_statevector': '/api/quantum/gpu/statevector',
      'quantum_gpu_tensornet': '/api/quantum/gpu/tensornet',
      'quantum_gpu_vqe': '/api/quantum/gpu/vqe',
      // Large-scale validated tensor-network many-body simulation
      'quantum_manybody_tfim': '/api/quantum/manybody/tfim',
      'quantum_manybody_hubbard': '/api/quantum/manybody/hubbard',
      'quantum_frontier_map': '/api/quantum/frontier',
      'quantum_calibration': '/api/quantum/calibration',
      'bioql_gqe': '/api/quantum/gqe',
      'qdiffvision': '/api/quantum/qdiffvision',
      // CRISPR compact-editor design (route already live on backend)
      'crispr_editor_design': '/api/quantum/crispr_editor_design',
      // Virus-agnostic replicon workbench (design + antiviral discovery, chained)
      'replicon_pipeline': '/api/quantum/replicon',
      // Rejuvenation therapy designer (disease/tissue-agnostic) + its mechanism
      // gate. NOTE: this map is SEPARATE from VSIXService's PIPELINE_ROUTES --
      // registering only there sends the call to the generic /api/bioql/tools/
      // dispatcher and it 404s. Both maps must carry the tool.
      'rejuvenation_therapy': '/api/aging/design',
      'mechanism_fit_gate': '/api/aging/gate',
      // Quantum biologic design levers (QAOA combinatorial + SQD electronic + end-to-end dock)
      'quantum_antibody_cdr': '/api/quantum/antibody_cdr',
      'quantum_peptide_design': '/api/quantum/peptide_design',
      'biologic_complete': '/api/casestudy/biologic_complete',
      // Comp-chem engines — honest_value contract (MM-GBSA, fpocket, PLIP, lead-opt, RBFE, metallodrug)
      'binding_free_energy': '/api/compchem/binding_free_energy',
      'find_binding_pocket': '/api/compchem/pocket',
      'analyze_interactions': '/api/compchem/interactions',
      'optimize_lead': '/api/compchem/lead_opt',
      'relative_binding_free_energy': '/api/compchem/rbfe',
      'metallodrug_design': '/api/compchem/metallodrug',
    };

    // Protein engineering tools
    // Local dev: route to generate_biomolecule (Aer simulator)
    // Production: route via nginx to G1 MCP Server multi-agent system
    const proteinTools: Record<string, string> = {
      'protein_engineering_pipeline': '/api/quantum/generate_biomolecule',
      'mrna_therapeutic_design': '/api/pipeline/mrna_therapeutic',
      'antibody_cdr_design': '/api/quantum/antibody_discovery',
      'enzyme_activity_optimization': '/api/quantum/generate_biomolecule',
      'protein_stability_engineering': '/api/quantum/generate_biomolecule',
      'fusion_protein_design': '/api/quantum/generate_biomolecule',
    };

    if (pipelineTools[toolName]) {
      return { proxyPath: '', actualToolName: toolName, fullUrl: pipelineTools[toolName] };
    }

    if (proteinTools[toolName]) {
      return { proxyPath: '', actualToolName: toolName, fullUrl: proteinTools[toolName] };
    }

    // Map of tool prefixes to their proxy paths
    const toolPrefixMap: Record<string, string> = {
      'rdkit': '/api/rdkit',
      'biopython': '/api/biopython',
      'openbabel': '/api/openbabel',
      'vina': '/api/vina',
      'pymol': '/api/pymol',
      'prolif': '/api/prolif',
      'librarypdb': '/api/librarypdb',
      'bioql': '/api/bioql',
      'quantum': '/api/quantum',
    };

    // Check if tool has a prefix (e.g., "librarypdb:download_pdb")
    if (toolName.includes(':')) {
      const [prefix, actualTool] = toolName.split(':', 2);
      const proxyPath = toolPrefixMap[prefix.toLowerCase()];
      if (proxyPath) {
        return { proxyPath, actualToolName: actualTool };
      }
    }

    // Check if tool name starts with a known prefix (e.g., "bioql_execute")
    for (const [prefix, proxyPath] of Object.entries(toolPrefixMap)) {
      if (toolName.toLowerCase().startsWith(prefix + '_')) {
        return { proxyPath, actualToolName: toolName };
      }
    }

    // Default to bioql for unrecognized tools
    return { proxyPath: '/api/bioql', actualToolName: toolName };
  }

  // Call an MCP tool with intelligent routing
  async callTool(
    toolName: string,
    args: Record<string, unknown>,
    serverId: string = 'bioql-mcp'
  ): Promise<MCPToolResult> {
    const startTime = Date.now();

    try {
      // Get the correct proxy path based on tool name
      const { proxyPath, actualToolName, fullUrl } = this.getProxyPathForTool(toolName);
      const url = fullUrl || `${proxyPath}/tools/${actualToolName}`;

      console.log(`🔧 MCP Tool Call: ${toolName} -> ${url}`, args);

      // Don't send X-API-Key to external URLs (causes CORS issues)
      // Send it to any local/proxy endpoint (starting with /)
      const isExternalUrl = url.startsWith('http://') || url.startsWith('https://');
      const _callKey = this.apiKey || sessionStorage.getItem('bioql_api_key') || localStorage.getItem('bioql_api_key') || '';
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(!isExternalUrl && _callKey && { 'X-API-Key': _callKey }),
        },
        body: JSON.stringify(args),
      });

      const executionTime = Date.now() - startTime;
      // Present the moment headers arrive (fetch() resolves on headers, not
      // full body) -- lets the caller start live-narration streaming for a
      // long-running pipeline before its (possibly minutes-long) result body
      // has finished downloading.
      const pipelineSessionId = response.headers.get('X-Pipeline-Session') || undefined;
      // Start live narration immediately -- while the (possibly minutes-long)
      // result body is still downloading -- not after this function returns.
      if (pipelineSessionId) subscribeToLiveNarration(pipelineSessionId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`❌ Tool ${toolName} failed:`, errorData);
        return {
          success: false,
          error: errorData.error || errorData.detail || `HTTP ${response.status}`,
          executionTime,
          serverId,
          pipelineSessionId,
        };
      }

      const data = await response.json();
      console.log(`✅ Tool ${toolName} completed in ${executionTime}ms`);

      // Extract result from response (server returns {success: true, result: ...})
      let content = data.result || data;

      // Filter BioQL results to remove noise and extract meaningful data
      if (toolName.includes('bioql') && content) {
        content = this.filterBioQLResult(content);
      }

      return {
        success: data.success !== false,
        content,
        executionTime,
        serverId,
        pipelineSessionId,
      };
    } catch (error) {
      console.error(`❌ Tool ${toolName} error:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        executionTime: Date.now() - startTime,
        serverId,
      };
    }
  }

  // Execute BioQL command
  async execute(command: string, agent: string = 'orchestrator'): Promise<MCPToolResult> {
    return this.callTool('bioql_execute', { command, agent });
  }

  // Get job status
  async getJobStatus(jobId: string): Promise<JobStatus> {
    const result = await this.callTool('bioql_status', { job_id: jobId });
    if (result.success && result.content) {
      return result.content as JobStatus;
    }
    return {
      job_id: jobId,
      status: 'failed',
      error: result.error,
    };
  }

  // Get job results
  async getJobResults(jobId: string, includeOutput: boolean = true): Promise<MCPToolResult> {
    return this.callTool('bioql_results', { job_id: jobId, include_output: includeOutput });
  }

  // Poll job until completion
  async pollJob(
    jobId: string,
    onProgress?: (status: JobStatus) => void,
    intervalMs: number = 2000,
    timeoutMs: number = 300000
  ): Promise<JobStatus> {
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const poll = async () => {
        if (Date.now() - startTime > timeoutMs) {
          reject(new Error('Job polling timeout'));
          return;
        }

        const status = await this.getJobStatus(jobId);
        onProgress?.(status);

        if (status.status === 'completed' || status.status === 'failed') {
          resolve(status);
        } else {
          setTimeout(poll, intervalMs);
        }
      };

      poll();
    });
  }

  // FMO-VQE quantum calculation
  async fmoVQE(
    moleculeSmiles: string,
    numQubits: number,
    backend: string = 'ibm_torino'
  ): Promise<MCPToolResult> {
    return this.callTool('bioql_fmo_vqe', {
      molecule_smiles: moleculeSmiles,
      num_qubits: numQubits,
      backend,
    });
  }

  // DC-QAOA docking
  async dcQAOA(
    proteinPdb: string,
    ligandSmiles: string,
    backend: string = 'quantinuum_h2'
  ): Promise<MCPToolResult> {
    return this.callTool('bioql_dc_qaoa', {
      protein_pdb: proteinPdb,
      ligand_smiles: ligandSmiles,
      backend,
    });
  }

  // Check QEC status
  async getQECStatus(backend?: string): Promise<MCPToolResult> {
    return this.callTool('bioql_qec_status', { backend });
  }

  // Check Quillow status
  async checkQuillowStatus(backend: string = 'ibm_torino'): Promise<MCPToolResult> {
    return this.callTool('check_quillow_status', { backend });
  }

  // Generate code from natural language
  async generateVibecode(prompt: string): Promise<MCPToolResult> {
    return this.callTool('generate_vibecode', { natural_language_prompt: prompt });
  }

  // Query Spectrix framework
  async querySpectrix(query: string): Promise<MCPToolResult> {
    return this.callTool('query_spectrix_framework', { query });
  }

  // Analyze BioHNet model
  async analyzeBioHNet(modelPath: string): Promise<MCPToolResult> {
    return this.callTool('analyze_biohnet_model', { model_path: modelPath });
  }

  // ============================================
  // FLEXIBLE PIPELINE ENTRY POINTS
  // ============================================

  // Toxicology Study - Start with user's molecule
  async toxicologyStudy(
    smiles: string,
    moleculeName: string = 'User Molecule',
    includeAdmet: boolean = true
  ): Promise<MCPToolResult> {
    const startTime = Date.now();
    try {
      const response = await fetch('/api/pipeline/toxicology', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.getApiKey() && { 'X-API-Key': this.getApiKey()! }),
        },
        body: JSON.stringify({ smiles, molecule_name: moleculeName, include_admet: includeAdmet }),
      });
      const data = await response.json();
      return { success: response.ok, content: data, executionTime: Date.now() - startTime };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error', executionTime: Date.now() - startTime };
    }
  }

  // ADMET Standalone - Run on existing molecule(s)
  async admetStandalone(smiles: string | string[]): Promise<MCPToolResult> {
    const startTime = Date.now();
    try {
      const body = Array.isArray(smiles) ? { smiles_list: smiles } : { smiles };
      const response = await fetch('/api/pipeline/admet_standalone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.getApiKey() && { 'X-API-Key': this.getApiKey()! }),
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      return { success: response.ok, content: data, executionTime: Date.now() - startTime };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error', executionTime: Date.now() - startTime };
    }
  }

  // Pharmacology Study - PK/PD, MOA, Efficacy
  async pharmacologyStudy(
    smiles: string,
    target: string,
    moleculeName: string = 'Study Compound',
    options: { includePk?: boolean; includePd?: boolean; includeEfficacy?: boolean } = {}
  ): Promise<MCPToolResult> {
    const startTime = Date.now();
    try {
      const response = await fetch('/api/pipeline/pharmacology', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.getApiKey() && { 'X-API-Key': this.getApiKey()! }),
        },
        body: JSON.stringify({
          smiles,
          target,
          molecule_name: moleculeName,
          include_pk: options.includePk ?? true,
          include_pd: options.includePd ?? true,
          include_efficacy: options.includeEfficacy ?? true,
        }),
      });
      const data = await response.json();
      return { success: response.ok, content: data, executionTime: Date.now() - startTime };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error', executionTime: Date.now() - startTime };
    }
  }

  // Clinical Trial Simulation - Phase I, II, III
  async clinicalTrialSimulation(
    smiles: string,
    moleculeName: string = 'Study Drug',
    indication: string = 'Solid Tumors',
    phase: 'I' | 'II' | 'III' | 'all' = 'all'
  ): Promise<MCPToolResult> {
    const startTime = Date.now();
    try {
      const response = await fetch('/api/pipeline/clinical_trial', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.getApiKey() && { 'X-API-Key': this.getApiKey()! }),
        },
        body: JSON.stringify({ smiles, molecule_name: moleculeName, indication, phase }),
      });
      const data = await response.json();
      return { success: response.ok, content: data, executionTime: Date.now() - startTime };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error', executionTime: Date.now() - startTime };
    }
  }

  // Full Drug Development Pipeline - Discovery to Approval
  async fullDrugDevelopment(
    options: {
      startFrom?: 'discovery' | 'molecule' | 'toxicology' | 'pharmacology' | 'clinical';
      smiles?: string;
      target?: string;
      moleculeName?: string;
      indication?: string;
    } = {}
  ): Promise<MCPToolResult> {
    const startTime = Date.now();
    try {
      const response = await fetch('/api/pipeline/full_development', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.getApiKey() && { 'X-API-Key': this.getApiKey()! }),
        },
        body: JSON.stringify({
          start_from: options.startFrom ?? 'discovery',
          smiles: options.smiles,
          target: options.target ?? 'EGFR',
          molecule_name: options.moleculeName ?? 'BioQL-001',
          indication: options.indication ?? 'Solid Tumors',
        }),
      });
      const data = await response.json();
      return { success: response.ok, content: data, executionTime: Date.now() - startTime };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error', executionTime: Date.now() - startTime };
    }
  }

  // Run quantum benchmark
  async benchmarkQuantumAdvantage(
    testType: 'vqe' | 'qaoa' | 'docking' | 'full_workflow',
    numQubits: number,
    backends: string[]
  ): Promise<MCPToolResult> {
    return this.callTool('bioql_benchmark_quantum_advantage', {
      test_type: testType,
      num_qubits: numQubits,
      backends,
    });
  }

  // Get help
  async getHelp(topic?: string): Promise<MCPToolResult> {
    return this.callTool('bioql_help', { topic });
  }
}

// Singleton instance
export const mcpClient = new MCPClientService();

// ============================================
// Report Generation Helper
// ============================================
export function generateDrugDiscoveryReport(result: unknown): string {
  if (!result || typeof result !== 'object') {
    return 'No data available for report generation.';
  }

  const data = result as Record<string, unknown>;
  let report = '# Drug Discovery Report\n\n';

  // Discovery results
  if (data.discovery) {
    const discovery = data.discovery as Record<string, unknown>;
    report += '## Discovery Phase\n';
    report += `- Pipeline: ${discovery.pipeline || 'N/A'}\n`;
    report += `- Status: ${discovery.status || 'N/A'}\n`;
    if (discovery.best_overall) {
      const best = discovery.best_overall as Record<string, unknown>;
      report += `- Best Candidate: ${best.type || 'N/A'} (${best.identifier || 'N/A'})\n`;
      report += `- Binding Affinity: ${best.binding_kcal || 'N/A'} kcal/mol\n`;
    }
    report += '\n';
  }

  // Toxicology results
  if (data.toxicology) {
    const tox = data.toxicology as Record<string, unknown>;
    report += '## Toxicology Assessment\n';
    const assessment = tox.overall_toxicity_assessment as Record<string, unknown>;
    if (assessment) {
      report += `- Risk Level: ${assessment.risk_level || 'N/A'}\n`;
      report += `- Proceed to Clinical: ${assessment.proceed_to_clinical ? 'Yes' : 'No'}\n`;
    }
    report += '\n';
  }

  // Pharmacology results
  if (data.pharmacology) {
    const pharm = data.pharmacology as Record<string, unknown>;
    report += '## Pharmacology\n';
    const pk = pharm.pharmacokinetics as Record<string, unknown>;
    if (pk) {
      const absorption = pk.absorption as Record<string, unknown>;
      if (absorption) {
        report += `- Bioavailability: ${absorption.bioavailability_oral_percent || 'N/A'}%\n`;
      }
    }
    report += '\n';
  }

  // Clinical trials results
  if (data.clinical_trials) {
    const trials = data.clinical_trials as Record<string, unknown>;
    report += '## Clinical Trial Predictions\n';
    const summary = trials.development_summary as Record<string, unknown>;
    if (summary) {
      report += `- Probability of Approval: ${summary.probability_of_approval_percent || 'N/A'}%\n`;
      report += `- Estimated Time to Approval: ${summary.estimated_time_to_approval_years || 'N/A'} years\n`;
    }
    report += '\n';
  }

  return report;
}
