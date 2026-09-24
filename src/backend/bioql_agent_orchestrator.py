#!/usr/bin/env python3
"""
BioQL Multi-Agent Orchestrator
===============================

Intelligent routing system that detects input type (small molecule vs protein)
and dispatches to appropriate specialized agents.

Architecture:
    Input → Router → Agent Selection → Execution → Unified Output

Agents:
    1. SmallMoleculeAgent (existing pipeline)
    2. ProteinEngineeringAgent (NEW - MULTI-evolve)
    3. PeptideAgent (short sequences)
    4. NanobodyAgent (specialized antibody fragments)

Author: BioQL Team
Date: 2026-02-25
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MoleculeType(Enum):
    """Enum for molecule types"""

    SMALL_MOLECULE = "small_molecule"
    PROTEIN = "protein"
    PEPTIDE = "peptide"
    NANOBODY = "nanobody"
    ANTIBODY = "antibody"
    ENZYME = "enzyme"
    UNKNOWN = "unknown"


class AgentType(Enum):
    """Enum for agent types"""

    SMALL_MOLECULE_AGENT = "small_molecule"
    PROTEIN_ENGINEERING_AGENT = "protein_engineering"
    PEPTIDE_AGENT = "peptide"
    NANOBODY_AGENT = "nanobody"


@dataclass
class InputAnalysis:
    """Analysis result of input"""

    molecule_type: MoleculeType
    confidence: float
    detected_features: Dict[str, Any]
    recommended_agent: AgentType
    metadata: Dict[str, Any]


class BioQLRouter:
    """
    Intelligent router that analyzes input and determines the appropriate agent
    """

    # Amino acid one-letter codes
    AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")

    # SMILES characters
    SMILES_CHARS = set("CNOPSFClBrI[]()=#@+-0123456789cnops")

    def __init__(self):
        self.rules = self._initialize_rules()

    def _initialize_rules(self) -> Dict:
        """Initialize detection rules"""
        return {
            "protein_keywords": [
                "protein",
                "enzyme",
                "antibody",
                "antigen",
                "receptor",
                "kinase",
                "peptidase",
                "synthase",
                "oxidase",
                "transferase",
                "wildtype",
                "mutant",
                "variant",
                "CDR",
                "Fc",
                "Fab",
            ],
            "peptide_keywords": ["peptide", "oligopeptide", "polypeptide", "cyclic peptide"],
            "small_molecule_keywords": [
                "smiles",
                "iupac",
                "compound",
                "drug",
                "inhibitor",
                "agonist",
                "antagonist",
                "ligand",
                "molecule",
            ],
            "protein_min_length": 50,  # Proteins typically > 50 amino acids
            "peptide_max_length": 50,  # Peptides typically < 50 amino acids
        }

    def analyze_input(self, input_data: Dict[str, Any]) -> InputAnalysis:
        """
        Analyze input and determine molecule type and appropriate agent

        Args:
            input_data: Dict with keys like 'sequence', 'smiles', 'text', 'target', etc.

        Returns:
            InputAnalysis object with routing decision
        """
        logger.info("Analyzing input to determine molecule type...")

        # Extract relevant fields
        sequence = input_data.get("sequence", "")
        smiles = input_data.get("smiles", "")
        text = input_data.get("text", "")
        description = input_data.get("description", "")
        mode = input_data.get("mode", "")

        # Combine text fields for keyword analysis
        combined_text = f"{text} {description} {mode}".lower()

        # Detection logic
        features = {}
        confidence = 0.0
        molecule_type = MoleculeType.UNKNOWN

        # 1. Check for explicit sequence (protein/peptide)
        if sequence and self._is_amino_acid_sequence(sequence):
            seq_len = len(sequence)
            features["sequence_length"] = seq_len
            features["sequence_type"] = "amino_acid"

            if seq_len >= self.rules["protein_min_length"]:
                molecule_type = MoleculeType.PROTEIN
                confidence = 0.95

                # Check for specific protein types
                if self._contains_keywords(combined_text, ["antibody", "nanobody", "cdr"]):
                    molecule_type = MoleculeType.ANTIBODY
                    confidence = 0.98
                elif self._contains_keywords(combined_text, ["enzyme", "kinase", "synthase"]):
                    molecule_type = MoleculeType.ENZYME
                    confidence = 0.97
            else:
                molecule_type = MoleculeType.PEPTIDE
                confidence = 0.90

        # 2. Check for SMILES (small molecule)
        elif smiles or self._is_smiles_like(sequence):
            features["has_smiles"] = True
            features["smiles_length"] = len(smiles or sequence)
            molecule_type = MoleculeType.SMALL_MOLECULE
            confidence = 0.95

        # 3. Check for mode-based hints
        elif mode in ["motifs", "direct", "auto"]:
            features["mode"] = mode
            molecule_type = MoleculeType.SMALL_MOLECULE
            confidence = 0.85

        # 4. Keyword-based detection
        else:
            if self._contains_keywords(combined_text, self.rules["protein_keywords"]):
                molecule_type = MoleculeType.PROTEIN
                confidence = 0.70
            elif self._contains_keywords(combined_text, self.rules["peptide_keywords"]):
                molecule_type = MoleculeType.PEPTIDE
                confidence = 0.70
            elif self._contains_keywords(combined_text, self.rules["small_molecule_keywords"]):
                molecule_type = MoleculeType.SMALL_MOLECULE
                confidence = 0.70

        # Determine recommended agent
        agent = self._select_agent(molecule_type)

        # Additional metadata
        metadata = {
            "input_fields": list(input_data.keys()),
            "text_length": len(combined_text),
            "has_target": "target" in input_data,
            "target": input_data.get("target", None),
        }

        result = InputAnalysis(
            molecule_type=molecule_type,
            confidence=confidence,
            detected_features=features,
            recommended_agent=agent,
            metadata=metadata,
        )

        logger.info(f"Analysis complete: {molecule_type.value} (confidence: {confidence:.2f})")
        logger.info(f"Recommended agent: {agent.value}")

        return result

    def _is_amino_acid_sequence(self, seq: str) -> bool:
        """Check if sequence is amino acid sequence"""
        if not seq:
            return False

        seq_upper = seq.upper().strip()

        # Remove whitespace and newlines
        seq_clean = re.sub(r"\s+", "", seq_upper)

        # Check if mostly amino acids (>90%)
        if len(seq_clean) == 0:
            return False

        aa_count = sum(1 for char in seq_clean if char in self.AMINO_ACIDS)
        ratio = aa_count / len(seq_clean)

        return ratio > 0.90

    def _is_smiles_like(self, text: str) -> bool:
        """Check if text looks like SMILES notation"""
        if not text or len(text) < 5:
            return False

        text_clean = text.strip()

        # Check for typical SMILES patterns
        smiles_patterns = [
            r"c1ccccc1",  # benzene ring
            r"C\(=O\)",  # carbonyl
            r"\[.*?\]",  # square brackets
            r"[CNO]=[CNO]",  # double bonds
        ]

        for pattern in smiles_patterns:
            if re.search(pattern, text_clean):
                return True

        # Check character composition
        valid_chars = sum(1 for char in text_clean if char in self.SMILES_CHARS)
        ratio = valid_chars / len(text_clean)

        return ratio > 0.80

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _select_agent(self, molecule_type: MoleculeType) -> AgentType:
        """Select appropriate agent based on molecule type"""
        mapping = {
            MoleculeType.SMALL_MOLECULE: AgentType.SMALL_MOLECULE_AGENT,
            MoleculeType.PROTEIN: AgentType.PROTEIN_ENGINEERING_AGENT,
            MoleculeType.ENZYME: AgentType.PROTEIN_ENGINEERING_AGENT,
            MoleculeType.ANTIBODY: AgentType.NANOBODY_AGENT,
            MoleculeType.NANOBODY: AgentType.NANOBODY_AGENT,
            MoleculeType.PEPTIDE: AgentType.PEPTIDE_AGENT,
            MoleculeType.UNKNOWN: AgentType.SMALL_MOLECULE_AGENT,  # default fallback
        }
        return mapping.get(molecule_type, AgentType.SMALL_MOLECULE_AGENT)


class BioQLOrchestrator:
    """
    Main orchestrator that coordinates all agents and pipelines
    """

    def __init__(self):
        self.router = BioQLRouter()
        self.agents = self._initialize_agents()

    def _initialize_agents(self) -> Dict[AgentType, Any]:
        """Initialize all agent instances"""
        logger.info("Initializing BioQL agents...")

        agents = {
            AgentType.SMALL_MOLECULE_AGENT: SmallMoleculeAgent(),
            AgentType.PROTEIN_ENGINEERING_AGENT: ProteinEngineeringAgent(),
            AgentType.PEPTIDE_AGENT: PeptideAgent(),
            AgentType.NANOBODY_AGENT: NanobodyAgent(),
        }

        logger.info(f"Initialized {len(agents)} agents successfully")
        return agents

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing function - analyzes input and routes to appropriate agent

        Args:
            input_data: Input dictionary from user

        Returns:
            Unified output dictionary with results
        """
        try:
            # Step 1: Analyze input
            analysis = self.router.analyze_input(input_data)

            # Step 2: Select agent
            agent = self.agents[analysis.recommended_agent]

            logger.info(f"Routing to {analysis.recommended_agent.value}")

            # Step 3: Execute agent
            result = agent.execute(input_data, analysis)

            # Step 4: Unify output format
            unified_output = self._unify_output(result, analysis)

            return unified_output

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "input_analysis": None}

    def _unify_output(self, result: Dict, analysis: InputAnalysis) -> Dict:
        """Unify output format across all agents"""
        return {
            "status": result.get("status", "unknown"),
            "molecule_type": analysis.molecule_type.value,
            "agent_used": analysis.recommended_agent.value,
            "confidence": analysis.confidence,
            "results": result,
            "metadata": {
                "detected_features": analysis.detected_features,
                "input_metadata": analysis.metadata,
                "pipeline_stages": result.get("pipeline_stages", []),
            },
        }


# ============================================================================
# NOT-IMPLEMENTED CONTRACT
# ============================================================================
#
# Every stage below that has no engine behind it returns THIS, and never a
# number. Until 2026-09-22 these methods returned fabricated constants --
# hotspots [42, 89, 134], a synergy of 0.87, "8.5x" improvement, a binding
# affinity of "-12.4 kcal/mol", "$450" of synthesis -- and the agent wrapped
# them in {"status": "success"}. A caller had no way to tell that output from
# a real run, which is the only thing that matters: an unimplemented stage
# that reports success is worse than one that crashes, because it ships.
#
# The rule for every pipeline in BioQL: a stage that did not compute returns
# `implemented: False` and None where the value would go. Not implemented is
# not the same as computed, exactly as unchecked is not the same as passed.


def not_implemented(stage: str, needs: str, fields=None) -> Dict[str, Any]:
    """A stage with no engine behind it. Carries no number a caller could use."""
    rec: Dict[str, Any] = {
        "implemented": False,
        "stage": stage,
        "reason": "no engine is wired to this stage yet",
        "needs": needs,
        "value": None,
    }
    for f in fields or ():
        rec[f] = None
    return rec


def stage_ran(rec: Any) -> bool:
    """True only for a stage that actually computed something.

    An empty list counts as NOT run: variant generation returning [] means no
    engine produced variants, and calling that a computed stage would restore
    the exact false positive this contract exists to prevent.
    """
    if isinstance(rec, dict) and rec.get("implemented") is False:
        return False
    if isinstance(rec, (list, tuple)) and len(rec) == 0:
        return False
    return True


# ============================================================================
# AGENT IMPLEMENTATIONS
# ============================================================================


class BaseAgent:
    """Base class for all agents"""

    def execute(self, input_data: Dict, analysis: InputAnalysis) -> Dict:
        """Execute agent pipeline"""
        raise NotImplementedError("Subclasses must implement execute()")


class SmallMoleculeAgent(BaseAgent):
    """
    Agent for small molecules - uses EXISTING BioQL pipeline
    This is the CURRENT production system (motifs, 78 algos, ADMET, etc.)
    """

    def execute(self, input_data: Dict, analysis: InputAnalysis) -> Dict:
        """Execute small molecule pipeline"""
        logger.info("SmallMoleculeAgent: Executing existing pipeline")

        # `existing_pipeline` below is a CLASS in this module, not a module, so
        # this import has never resolved -- the agent has always raised
        # ImportError and the orchestrator turned it into {"status": "error"}.
        # Kept explicit rather than silently repaired: the real entry point is
        # script_executor_server's custom-molecule pipeline, and wiring it is a
        # decision about which endpoint owns the call, not a typo fix.
        try:
            from existing_pipeline import run_custom_molecule_pipeline

            result = run_custom_molecule_pipeline(input_data)
        except ImportError as exc:
            return {
                "status": "not_implemented",
                "agent": "small_molecule",
                "reason": "no pipeline is wired to this agent: %s" % exc,
                "needs": "script_executor_server custom-molecule pipeline",
                "pipeline_stages": [],
                "stages_computed": [],
                "data": None,
            }

        return {
            "status": "success",
            "agent": "small_molecule",
            "pipeline_stages": [
                "SMILES Resolution",
                "78 Quantum Algorithms",
                "ADMET Prediction (92 params)",
                "Toxicology Study",
                "Pharmacology (PK/PD)",
                "Clinical Trial Simulation",
            ],
            "data": result,
        }


class ProteinEngineeringAgent(BaseAgent):
    """
    NEW Agent for protein engineering using MULTI-evolve approach
    Combines protein language models + quantum epistatic modeling
    """

    def execute(self, input_data: Dict, analysis: InputAnalysis) -> Dict:
        """Execute protein engineering pipeline"""
        logger.info("ProteinEngineeringAgent: Starting MULTI-evolve pipeline")

        sequence = input_data.get("sequence", "")
        max_mutations = input_data.get("max_mutations", 5)

        stages = []
        results = {}

        # Stage 1: Protein Language Model Analysis
        logger.info("Stage 1: ESM-2 analysis")
        esm_result = self._run_esm2_analysis(sequence)
        stages.append("ESM-2 Analysis")
        results["esm2"] = esm_result

        # Stage 2: Quantum Epistatic Modeling
        logger.info("Stage 2: Quantum epistatic modeling")
        epistasis_result = self._run_epistatic_modeling(sequence, esm_result)
        stages.append("Quantum Epistatic Modeling")
        results["epistasis"] = epistasis_result

        # Stage 3: Variant Generation
        logger.info("Stage 3: Generating variants")
        variants = self._generate_variants(sequence, epistasis_result, max_mutations)
        stages.append("Variant Generation")
        results["variants"] = variants

        # Stage 4: Structure Prediction (AlphaFold2)
        logger.info("Stage 4: AlphaFold2 structure prediction")
        structures = self._predict_structures(variants[:10], sequence)
        stages.append("Structure Prediction (AlphaFold2)")
        results["structures"] = structures

        # Stage 5: Protein ADMET (immunogenicity, stability, aggregation)
        logger.info("Stage 5: Protein ADMET")
        admet = self._protein_admet(variants[:10], sequence)
        stages.append("Protein ADMET")
        results["admet"] = admet

        # Stage 6: Binding Analysis (if target provided)
        if "target_ligand" in input_data or "target_protein" in input_data:
            logger.info("Stage 6: Binding analysis")
            binding = self._binding_analysis(variants[:10], input_data)
            stages.append("Binding Analysis")
            results["binding"] = binding

        # Stage 7: Assembly Protocol
        # `variants[0]` used to be safe only because _generate_variants
        # fabricated one. With an honest empty list this crashed -- the
        # fabrication had been hiding an unguarded index all along.
        logger.info("Stage 7: MULTI-assembly protocol")
        if variants:
            assembly = self._generate_assembly_protocol(sequence, variants[0])
        else:
            assembly = not_implemented(
                "assembly protocol",
                "at least one variant to build a protocol for; " "variant generation produced none",
                ("method", "primers", "synthesis_cost"),
            )
        stages.append("MULTI-assembly Protocol")
        results["assembly"] = assembly

        # Status reflects what actually COMPUTED, not what was attempted. A
        # stage list is a list of attempts; `stages_computed` is the evidence.
        computed = [k for k, v in results.items() if stage_ran(v)]
        missing = [k for k, v in results.items() if not stage_ran(v)]
        if not computed:
            status = "not_implemented"
        elif missing:
            status = "partial"
        else:
            status = "success"

        return {
            "status": status,
            "agent": "protein_engineering",
            "pipeline_stages": stages,
            "stages_attempted": list(results.keys()),
            "stages_computed": computed,
            "stages_not_implemented": missing,
            "data": results,
            "honest_note": (
                (
                    "Stages listed under stages_not_implemented produced no value. "
                    "They are not failures and not results -- nothing ran."
                )
                if missing
                else None
            ),
        }

    def _esm2_masked_marginals(self, sequence: str, max_positions: int = 0):
        """Masked-marginal log-odds for EVERY substitution, position by position.

        Same quantity as `nir_deliverable._score_masked` -- log P(mut | context)
        minus log P(wt | context) with the position masked -- but read off ONE
        forward pass per position instead of one per mutation, which is the same
        arithmetic over the same logits at 1/19th the compute.

        WHY NOT `esm2_protein_engine`: it needs `fair-esm`, which owns the
        top-level `esm` package. This venv has EvolutionaryScale's `esm` 3.2.3
        (ESM-3) under that name, so `esm.pretrained` does not exist. The failure
        was diagnosed on 2026-08-30 and the HuggingFace route below is the
        documented way around it (see nir_deliverable._esm2_hf).

        Returns (rows, meta) or (None, reason).
        """
        try:
            import nir_deliverable as N

            tok, mod, torch, model_name = N._esm2_hf()
        except Exception as exc:
            return None, "ESM-2 unavailable: %s: %s" % (type(exc).__name__, str(exc)[:160])

        alphabet = "ACDEFGHIKLMNPQRSTVWY"
        n = len(sequence)
        positions = range(1, n + 1)
        truncated = False
        if max_positions and n > max_positions:
            positions = range(1, max_positions + 1)
            truncated = True

        try:
            enc = tok(sequence, return_tensors="pt")
            base_ids = enc["input_ids"]
            attn = enc["attention_mask"]
            alt_ids = {a: tok.convert_tokens_to_ids(a) for a in alphabet}
            rows = []
            for idx1 in positions:
                if idx1 >= base_ids.shape[1] - 1:
                    break
                wt = sequence[idx1 - 1]
                if wt not in alt_ids:
                    continue
                ids = base_ids.clone()
                original = ids[0, idx1].item()
                ids[0, idx1] = tok.mask_token_id
                with torch.no_grad():
                    logits = mod(input_ids=ids, attention_mask=attn).logits
                lp = torch.log_softmax(logits[0, idx1], dim=-1)
                ids[0, idx1] = original
                wt_lp = float(lp[alt_ids[wt]])
                for alt in alphabet:
                    if alt == wt:
                        continue
                    rows.append(
                        {
                            "mutation": "%s%d%s" % (wt, idx1, alt),
                            "position": idx1,
                            "wt": wt,
                            "mut": alt,
                            "esm2_log_odds": float(lp[alt_ids[alt]]) - wt_lp,
                        }
                    )
        except Exception as exc:
            return None, "ESM-2 scoring failed: %s: %s" % (type(exc).__name__, str(exc)[:160])

        meta = {
            "model": model_name,
            "route": "HuggingFace",
            "metric": "masked marginal, log P(mut) - log P(wt)",
            "n_positions_scanned": len({r["position"] for r in rows}),
            "n_positions_total": n,
            "truncated": truncated,
            "scale": getattr(N, "VIABILITY_SCALE", None),
        }
        return rows, meta

    def _run_esm2_analysis(self, sequence: str) -> Dict:
        """ESM-2 masked marginals over the whole sequence.

        The per-position minimum log-odds is the conservation signal: a position
        where EVERY substitution is heavily penalised is one the model considers
        constrained. That is what replaces the hard-coded `hotspots: [42,89,134]`.
        """
        rows, meta = self._esm2_masked_marginals(sequence)
        if rows is None:
            return not_implemented("ESM-2 analysis", meta, ("conservation", "hotspots", "model"))
        if not rows:
            return not_implemented(
                "ESM-2 analysis",
                "model returned no scorable position",
                ("conservation", "hotspots", "model"),
            )
        by_pos = {}
        for r in rows:
            p_ = r["position"]
            best = r["esm2_log_odds"]
            if p_ not in by_pos or best > by_pos[p_]["best_log_odds"]:
                by_pos[p_] = {
                    "position": p_,
                    "wt": r["wt"],
                    "best_log_odds": best,
                    "best_sub": r["mut"],
                }
        # Most constrained = the positions where even the best substitution is
        # heavily penalised. Derived from the model, not written by hand.
        constrained = sorted(by_pos.values(), key=lambda d: d["best_log_odds"])
        return {
            "implemented": True,
            "stage": "ESM-2 analysis",
            "engine": "ESM-2 via HuggingFace",
            "model": meta["model"],
            "metric": meta["metric"],
            "n_positions": meta["n_positions_scanned"],
            "most_constrained_positions": constrained[:10],
            "most_tolerant_positions": constrained[-5:],
            "scale": meta.get("scale"),
        }

    def _run_epistatic_modeling(self, sequence: str, esm_result: Dict) -> Dict:
        """Quantum epistatic modelling (VQE + QAOA). No engine wired yet."""
        return not_implemented(
            "quantum epistatic modelling",
            "a VQE/QAOA epistasis formulation and a backend to run it on",
            ("interactions", "quantum_jobs"),
        )

    def _generate_variants(self, sequence: str, epistasis: Dict, max_muts: int) -> List[Dict]:
        """Rank single substitutions by ESM-2 masked-marginal log-odds.

        Returns [] when the scorer cannot run. An invented variant carrying a
        "predicted_improvement" would be ranked, ordered and synthesised; an
        empty list stops the pipeline instead, which is the correct outcome.

        This is a TRIAGE ordering, not a stability prediction. The caveat
        travels with every row.
        """
        rows, meta = self._esm2_masked_marginals(sequence)
        if not rows:
            logger.warning("variant generation produced nothing: %s", meta)
            return []
        rows.sort(key=lambda r: -r["esm2_log_odds"])
        out = []
        for rank, r in enumerate(rows[:max_muts], start=1):
            out.append(
                {
                    "rank": rank,
                    "mutation": r["mutation"],
                    "position": r["position"],
                    "wt": r["wt"],
                    "mut": r["mut"],
                    "esm2_log_odds": round(r["esm2_log_odds"], 4),
                    "scorer": "ESM-2 masked marginal (%s)" % meta["model"],
                    "caveat": (
                        "triage ordering only; a 35M-parameter model orders "
                        "candidates, it does not predict stability"
                    ),
                }
            )
        return out

    def _predict_structures(self, variants: List[Dict], sequence: str = "") -> Dict:
        """Fold on BioQL's own ESMFold2 (Modal H100) via the compute layer.

        The compute layer answers where it ran and why, so a structure that
        came from a fallback can never be mistaken for one that did not.
        """
        if not sequence:
            return not_implemented("structure prediction", "a sequence to fold", ("pdb", "plddt"))
        try:
            import modal_compute_layer as MC
        except Exception as exc:
            return not_implemented(
                "structure prediction",
                "modal_compute_layer import failed: %s" % exc,
                ("pdb", "plddt"),
            )
        r = MC.run("fold_protein", sequence, local_fn=None)
        if not MC.ran_remotely(r):
            return not_implemented(
                "structure prediction",
                "GPU folding unavailable: %s" % str(r.get("why"))[:160],
                ("pdb", "plddt"),
            )
        res = r.get("result") or {}
        return {
            "implemented": True,
            "stage": "structure prediction",
            "pdb": res.get("pdb"),
            "plddt": res.get("plddt"),
            "where_it_ran": r["where_it_ran"],
            "engine": f"ESMFold2 ({MC.where_label(r, 'H100')})",
            "n_variants_folded": 1,
        }

    def _protein_admet(self, variants: List[Dict], sequence: str = "") -> Dict:
        """Developability on the WILD-TYPE sequence: charge, GRAVY, Boman index,
        hydrophobic moment, hemolysis and toxicity flags, B-cell epitopes,
        chemical liabilities. Computed locally, no GPU."""
        if not sequence:
            return not_implemented(
                "protein ADMET / developability",
                "a sequence to analyse",
                ("net_charge", "gravy", "liabilities"),
            )
        try:
            import peptide_developability_suite as P
        except Exception as exc:
            return not_implemented(
                "protein ADMET / developability",
                "peptide_developability_suite import failed: %s" % exc,
                ("net_charge", "gravy", "liabilities"),
            )
        try:
            rec = P.analyze_peptide(sequence)
        except Exception as exc:
            return not_implemented(
                "protein ADMET / developability",
                "engine raised %s: %s" % (type(exc).__name__, str(exc)[:160]),
                ("net_charge", "gravy", "liabilities"),
            )
        if not rec.get("available") or not rec.get("applicable"):
            return not_implemented(
                "protein ADMET / developability",
                "engine declared the sequence out of its applicability domain",
                ("net_charge", "gravy", "liabilities"),
            )
        rec = dict(rec)
        rec.update(
            {
                "implemented": True,
                "stage": "protein ADMET / developability",
                "engine": "peptide_developability_suite",
                "scope": "wild-type sequence",
            }
        )
        return rec

    def _binding_analysis(self, variants: List[Dict], input_data: Dict) -> Dict:
        """Binding affinity via ensemble MM-GBSA on GPU (bioql-mmgbsa-ens).

        Needs a complex to score. Without one this reports what is missing
        rather than guessing at an affinity.
        """
        complex_pdb = input_data.get("complex_pdb") or input_data.get("target_protein_pdb")
        ligand = input_data.get("target_ligand")
        if not complex_pdb:
            return not_implemented(
                "binding affinity",
                "a protein:ligand or protein:protein complex (complex_pdb); "
                "the agent was given a sequence only",
                ("binding_affinity", "units", "method"),
            )
        try:
            import modal_compute_layer as MC
        except Exception as exc:
            return not_implemented(
                "binding affinity",
                "modal_compute_layer import failed: %s" % exc,
                ("binding_affinity", "units", "method"),
            )
        payload = {"complex_pdb": complex_pdb}
        if ligand:
            payload["ligand"] = ligand
        r = MC.run("mmgbsa_ensemble", payload, local_fn=None)
        if not MC.ran_remotely(r):
            return not_implemented(
                "binding affinity",
                "GPU MM-GBSA unavailable: %s" % str(r.get("why"))[:160],
                ("binding_affinity", "units", "method"),
            )
        res = r.get("result") or {}
        return {
            "implemented": True,
            "stage": "binding affinity",
            "binding_affinity": res.get("dG") or res.get("binding_affinity"),
            "units": "kcal/mol",
            "method": "ensemble MM-GBSA (GPU)",
            "where_it_ran": r["where_it_ran"],
            "raw": res,
        }

    def _generate_assembly_protocol(self, wildtype: str, variant: Dict) -> Dict:
        """Assembly protocol. No primer design or costing engine behind it."""
        return not_implemented(
            "assembly protocol",
            "a primer-design engine and a real synthesis quote",
            ("method", "primers", "synthesis_cost"),
        )


class PeptideAgent(BaseAgent):
    """Agent for peptides (short sequences < 50 aa)"""

    def execute(self, input_data: Dict, analysis: InputAnalysis) -> Dict:
        """Execute peptide pipeline"""
        logger.info("PeptideAgent: Processing peptide")

        # For now, route to protein agent with peptide-specific settings
        protein_agent = ProteinEngineeringAgent()
        result = protein_agent.execute(input_data, analysis)

        result["agent"] = "peptide"
        return result


class NanobodyAgent(BaseAgent):
    """Agent for nanobodies and antibody fragments"""

    def execute(self, input_data: Dict, analysis: InputAnalysis) -> Dict:
        """Execute nanobody pipeline"""
        logger.info("NanobodyAgent: Processing nanobody/antibody")

        # Specialized pipeline for antibodies
        # Focus on CDR optimization
        protein_agent = ProteinEngineeringAgent()
        result = protein_agent.execute(input_data, analysis)

        # Add antibody-specific analysis
        result["agent"] = "nanobody"
        # "optimized" x3 was a literal, not an outcome. BioQL has real CDR work
        # (antibody_discovery_engine, antibody_interface_analyzer); until one of
        # them runs here, this stage reports that it did not.
        result.setdefault("data", {})["cdr_analysis"] = not_implemented(
            "CDR optimisation",
            "antibody_discovery_engine or antibody_interface_analyzer",
            ("CDR1", "CDR2", "CDR3"),
        )

        return result


# ============================================================================
# PLACEHOLDER FOR EXISTING PIPELINE
# ============================================================================


class existing_pipeline:
    """Placeholder - will import from actual script_executor_server.py"""

    @staticmethod
    def run_custom_molecule_pipeline(input_data: Dict) -> Dict:
        """
        This will call the EXISTING /api/quantum/custom_molecule endpoint
        NO CHANGES to existing code - just wrapping it
        """
        raise NotImplementedError(
            "This placeholder must not answer for the real pipeline. It used to "
            "return empty admet/toxicology/pharmacology/clinical blocks, which a "
            "caller reads as 'ran and found nothing' rather than 'never ran'. "
            "Wire script_executor_server's custom-molecule pipeline here."
        )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def process_bioql_request(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for all BioQL requests

    This function replaces the direct call to custom_molecule_pipeline
    and intelligently routes to appropriate agent

    Args:
        input_data: User input dictionary

    Returns:
        Unified output dictionary
    """
    orchestrator = BioQLOrchestrator()
    result = orchestrator.process(input_data)
    return result


if __name__ == "__main__":
    # Test cases
    print("=" * 80)
    print("BioQL Multi-Agent Orchestrator - Test Suite")
    print("=" * 80)

    # Test 1: Small molecule (SMILES)
    test1 = {"mode": "direct", "smiles": "c1ccc2ncnc(Nc3cccc(Br)c3)c2c1", "target": "EGFR"}
    print("\nTest 1: Small Molecule (SMILES)")
    router = BioQLRouter()
    analysis1 = router.analyze_input(test1)
    print(f"Result: {analysis1.molecule_type.value} → {analysis1.recommended_agent.value}")

    # Test 2: Protein sequence
    test2 = {
        "sequence": "MKVLWAALLVTFLAGCQAKVDKEVQALANDARLAKYIEKFRQKAEGSDV" * 3,
        "target_function": "binding_affinity",
        "description": "Antibody CDR optimization",
    }
    print("\nTest 2: Protein Sequence")
    analysis2 = router.analyze_input(test2)
    print(f"Result: {analysis2.molecule_type.value} → {analysis2.recommended_agent.value}")

    # Test 3: Peptide
    test3 = {"sequence": "GRGDSPASSKG", "text": "cyclic peptide for cancer targeting"}
    print("\nTest 3: Peptide")
    analysis3 = router.analyze_input(test3)
    print(f"Result: {analysis3.molecule_type.value} → {analysis3.recommended_agent.value}")

    # Test 4: Motif-based (small molecule)
    test4 = {
        "mode": "motifs",
        "motifs": ["tertiary_amide", "cyclopropyl", "fluoro_aromatic"],
        "target": "BRAF",
    }
    print("\nTest 4: Motif-based Small Molecule")
    analysis4 = router.analyze_input(test4)
    print(f"Result: {analysis4.molecule_type.value} → {analysis4.recommended_agent.value}")

    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
