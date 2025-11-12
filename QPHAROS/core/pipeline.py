# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Main Pipeline
Integrates all 5 layers for complete drug discovery workflow
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..layers.layer1_encoding import QuantumMolecularEncoder
from ..layers.layer2_binding import QuantumBindingPredictor
from ..layers.layer3_admet import QuantumADMETOptimizer
from ..layers.layer4_generation import QuantumMolecularGAN
from ..layers.layer5_dynamics import QuantumMolecularDynamics
from .config import QPHAROSConfig
from .quantum_backend import QuantumBackend


class QuantumDrugDesignPipeline:
    """
    Complete quantum drug discovery pipeline
    Combines molecular encoding, binding prediction, ADMET optimization,
    molecular generation, and dynamics simulation
    """

    def __init__(
        self,
        target_protein: str,
        disease_profile: str,
        config: Optional[QPHAROSConfig] = None,
        backend: str = "ibm_torino",
    ):
        """
        Initialize QPHAROS pipeline

        Args:
            target_protein: PDB ID or structure file
            disease_profile: Disease indication
            config: Configuration object
            backend: Quantum backend name
        """
        # Initialize configuration
        if config is None:
            config = QPHAROSConfig()
        config.backend = backend
        self.config = config

        # Store target information
        self.target_protein = target_protein
        self.disease_profile = disease_profile

        # Initialize quantum backend
        self.backend = QuantumBackend(config)

        # Initialize all layers
        self.encoder = QuantumMolecularEncoder(self.backend, config)
        self.binding_predictor = QuantumBindingPredictor(self.backend, config)
        self.admet_optimizer = QuantumADMETOptimizer(self.backend, config)
        self.molecular_gan = QuantumMolecularGAN(self.backend, config)
        self.md_simulator = QuantumMolecularDynamics(self.backend, config)

        # Results storage
        self.results_history = []
        self.best_candidates = []

        print(f"\n{'='*80}")
        print(f"🧬 QPHAROS - Quantum Pharmaceutical Optimization System")
        print(f"{'='*80}")
        print(f"Target Protein: {target_protein}")
        print(f"Disease: {disease_profile}")
        print(f"Backend: {backend}")
        print(f"QEC: {config.qec_type if config.qec_enabled else 'Disabled'}")
        print(f"{'='*80}\n")

    def design_drug(
        self,
        iterations: int = 50,
        seed_molecules: Optional[List[str]] = None,
        save_results: bool = True,
    ) -> Dict:
        """
        Main drug design workflow

        Args:
            iterations: Number of design iterations
            seed_molecules: Optional seed molecules for generation
            save_results: Save results to disk

        Returns:
            Best drug candidate with full characterization
        """
        print(f"\n{'█'*80}")
        print(f"🚀 STARTING QUANTUM DRUG DESIGN")
        print(f"{'█'*80}")
        print(f"Iterations: {iterations}")
        print(f"Target: {self.target_protein}")
        print(f"Disease: {self.disease_profile}")
        print(f"{'█'*80}\n")

        best_molecule = None
        best_score = -np.inf

        for iteration in range(1, iterations + 1):
            print(f"\n{'▬'*80}")
            print(f"📍 ITERATION {iteration}/{iterations}")
            print(f"{'▬'*80}\n")

            # Step 1: Generate candidate molecules
            candidates = self._generate_candidates(seed_molecules, iteration)

            # Step 2: Filter by quick screening
            filtered = self._quick_filter(candidates)

            # Step 3: Deep evaluation of filtered candidates
            for idx, molecule in enumerate(filtered):
                print(f"\n🔬 Evaluating candidate {idx+1}/{len(filtered)}")
                print(f"   SMILES: {molecule}")

                try:
                    # Evaluate molecule
                    score_dict = self._evaluate_molecule(molecule)

                    # Calculate combined score
                    total_score = self._calculate_combined_score(score_dict)

                    # Update best candidate
                    if total_score > best_score:
                        best_score = total_score
                        best_molecule = molecule
                        print(f"\n   ⭐ NEW BEST CANDIDATE!")
                        print(f"   Score: {total_score:.4f}")

                    # Store in history
                    self.results_history.append(
                        {
                            "iteration": iteration,
                            "molecule": molecule,
                            "score": total_score,
                            "details": score_dict,
                        }
                    )

                except Exception as e:
                    print(f"\n   ❌ Evaluation failed: {e}")
                    continue

            # Step 4: Quantum refinement of best candidate
            if best_molecule:
                best_molecule = self._quantum_refine(best_molecule)
                seed_molecules = [best_molecule]  # Use best as seed for next iteration

            # Progress report
            print(f"\n{'─'*80}")
            print(f"📊 Iteration {iteration} Summary:")
            print(f"   Candidates evaluated: {len(filtered)}")
            print(f"   Best score: {best_score:.4f}")
            print(f"   Best molecule: {best_molecule}")
            print(f"{'─'*80}\n")

        # Final characterization
        print(f"\n{'█'*80}")
        print(f"🏁 DRUG DESIGN COMPLETE")
        print(f"{'█'*80}\n")

        final_results = self._final_characterization(best_molecule, best_score)

        if save_results:
            self._save_results(final_results)

        return final_results

    def _generate_candidates(
        self, seed_molecules: Optional[List[str]], iteration: int
    ) -> List[str]:
        """Generate candidate molecules"""
        print(f"🧪 Generating candidate molecules...")

        if seed_molecules:
            # Generate from seeds
            candidates = self.molecular_gan.generate_molecules(
                training_molecules=seed_molecules,
                n_generate=100,
                target_properties={"drug_like": True, "diversity": 0.7},
            )
        else:
            # Generate de novo
            candidates = [
                "COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2",  # berberine
                "CC(C)Cc1ccc(cc1)C(C)C(O)=O",  # ibuprofen
                "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # caffeine
            ]

        print(f"   Generated {len(candidates)} candidates")
        return candidates

    def _quick_filter(self, candidates: List[str]) -> List[str]:
        """Quick screening filter"""
        print(f"⚡ Quick screening filter...")

        filtered = []
        for mol in candidates[:20]:  # Limit to top 20 for deep evaluation
            # Quick Lipinski check
            try:
                lipinski = self.admet_optimizer.check_lipinski(mol)
                if lipinski.get("all_pass", False):
                    filtered.append(mol)
            except:
                pass

        print(f"   {len(filtered)} candidates passed filter")
        return filtered

    def _evaluate_molecule(self, molecule_smiles: str) -> Dict:
        """Complete molecule evaluation"""

        # Binding prediction
        print(f"   → Binding prediction...")
        binding_result = self.binding_predictor.predict_binding(
            ligand_smiles=molecule_smiles, protein_pdb=self.target_protein
        )

        binding_score = binding_result.get("binding_affinity", 0)

        # ADMET prediction
        print(f"   → ADMET prediction...")
        admet_result = self.admet_optimizer.predict_admet(molecule_smiles)
        admet_score = self.admet_optimizer.calculate_drug_likeness_score(molecule_smiles)

        # Stability check
        print(f"   → Stability simulation...")
        stability = self.md_simulator.calculate_stability(
            ligand_smiles=molecule_smiles, protein_pdb=self.target_protein
        )

        return {
            "binding_affinity": binding_score,
            "binding_result": binding_result,
            "admet_score": admet_score,
            "admet_result": admet_result,
            "stability": stability,
        }

    def _calculate_combined_score(self, score_dict: Dict) -> float:
        """Calculate weighted combined score"""

        binding_score = -score_dict.get("binding_affinity", 0) / 10.0  # Normalize
        admet_score = score_dict.get("admet_score", 0)
        stability_score = score_dict.get("stability", 0)

        # Weighted combination
        total_score = (
            self.config.binding_weight * binding_score
            + self.config.admet_weight * admet_score
            + self.config.stability_weight * stability_score
        )

        return total_score

    def _quantum_refine(self, molecule_smiles: str) -> str:
        """Quantum refinement of molecule"""
        print(f"\n🔧 Quantum refinement...")

        # Use QAOA to optimize
        optimization_result = self.admet_optimizer.optimize_admet(
            molecule_smiles=molecule_smiles, target_properties={"maximize_binding": True}
        )

        # Return refined molecule (same for now, would be modified in production)
        return molecule_smiles

    def _final_characterization(self, best_molecule: str, best_score: float) -> Dict:
        """Complete characterization of best candidate"""

        print(f"📋 Final characterization...")

        # Comprehensive binding analysis
        binding_result = self.binding_predictor.predict_binding(
            ligand_smiles=best_molecule, protein_pdb=self.target_protein
        )

        # Complete ADMET profile
        admet_result = self.admet_optimizer.predict_admet(best_molecule)

        # Full MD simulation
        md_trajectory = self.md_simulator.simulate_binding_dynamics(
            ligand_smiles=best_molecule, protein_pdb=self.target_protein
        )

        # Residence time
        residence_time = self.md_simulator.predict_residence_time(
            ligand_smiles=best_molecule, protein_pdb=self.target_protein
        )

        final_results = {
            "molecule": best_molecule,
            "score": best_score,
            "target_protein": self.target_protein,
            "disease": self.disease_profile,
            "binding": binding_result,
            "admet": admet_result,
            "dynamics": md_trajectory,
            "residence_time": residence_time,
            "timestamp": datetime.now().isoformat(),
        }

        self._print_final_report(final_results)

        return final_results

    def _print_final_report(self, results: Dict):
        """Print formatted final report"""

        print(f"\n{'='*80}")
        print(f"📊 FINAL DRUG CANDIDATE REPORT")
        print(f"{'='*80}\n")

        print(f"🧬 Molecule: {results['molecule']}")
        print(f"🎯 Target: {results['target_protein']}")
        print(f"🏥 Disease: {results['disease']}")
        print(f"⭐ Overall Score: {results['score']:.4f}")

        print(f"\n⚛️  BINDING AFFINITY:")
        binding = results["binding"]
        if binding.get("binding_affinity"):
            print(f"   Affinity: {binding['binding_affinity']:.2f} kcal/mol")
        if binding.get("ki"):
            print(f"   Ki: {binding['ki']:.2f} nM")
        if binding.get("ic50"):
            print(f"   IC50: {binding['ic50']:.2f} nM")

        print(f"\n💊 ADMET PROFILE:")
        admet = results["admet"]
        print(f"   Drug-likeness: {admet.get('drug_likeness', {}).get('qed_score', 0):.2f}")
        print(
            f"   Lipinski: {'✅ PASS' if admet.get('drug_likeness', {}).get('lipinski_pass') else '❌ FAIL'}"
        )

        print(f"\n🎬 MOLECULAR DYNAMICS:")
        print(f"   Stability: {results.get('dynamics', {}).get('n_frames', 0)} frames")
        print(f"   Residence time: {results['residence_time']:.2e} seconds")

        print(f"\n{'='*80}\n")

    def _save_results(self, results: Dict):
        """Save results to artifacts directory"""

        artifacts_dir = Path("qpharos_results")
        artifacts_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = artifacts_dir / f"drug_design_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"💾 Results saved: {results_file}")

    def validate_drug(self, molecule_smiles: str) -> Dict:
        """
        Validate drug candidate with comprehensive testing

        Args:
            molecule_smiles: SMILES string to validate

        Returns:
            Validation results
        """
        print(f"\n{'='*80}")
        print(f"✅ DRUG VALIDATION")
        print(f"{'='*80}\n")

        validation = {"efficacy": 0.0, "toxicity": 0.0, "bioavailability": 0.0}

        # Binding efficacy
        binding = self.binding_predictor.predict_binding(
            ligand_smiles=molecule_smiles, protein_pdb=self.target_protein
        )
        if binding.get("binding_affinity"):
            # More negative = better binding = higher efficacy
            validation["efficacy"] = min(1.0, -binding["binding_affinity"] / 15.0)

        # ADMET for toxicity and bioavailability
        admet = self.admet_optimizer.predict_admet(molecule_smiles)
        tox = admet.get("toxicity", {})
        abs = admet.get("absorption", {})

        validation["toxicity"] = 0.1 if tox.get("ames") == "negative" else 0.9
        validation["bioavailability"] = abs.get("bioavailability", 0.5)

        print(f"📊 Validation Results:")
        print(f"   Efficacy: {validation['efficacy']:.2%}")
        print(f"   Toxicity: {validation['toxicity']:.2%}")
        print(f"   Bioavailability: {validation['bioavailability']:.2%}")

        print(f"\n{'='*80}\n")

        return validation
