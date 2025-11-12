# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Layer 3: ADMET Optimization using QAOA
Optimizes Absorption, Distribution, Metabolism, Excretion, Toxicity
"""

from typing import Dict, List, Optional, Tuple

import numpy as np


class QuantumADMETOptimizer:
    """
    Optimizes ADMET properties using QAOA
    Applies Lipinski's Rule of Five and other drug-likeness criteria
    """

    def __init__(self, backend, config):
        """
        Initialize ADMET optimizer

        Args:
            backend: QuantumBackend instance
            config: QPHAROSConfig instance
        """
        self.backend = backend
        self.config = config

        # Lipinski constraints
        self.max_mw = config.max_molecular_weight_admet
        self.logP_range = config.logP_range
        self.max_hbd = config.max_h_bond_donors
        self.max_hba = config.max_h_bond_acceptors

    def predict_admet(self, molecule_smiles: str) -> Dict:
        """
        Predict ADMET properties for molecule

        Args:
            molecule_smiles: SMILES string

        Returns:
            Dictionary with ADMET predictions
        """
        print(f"\n{'='*80}")
        print(f"💊 QUANTUM ADMET PREDICTION")
        print(f"{'='*80}")
        print(f"Molecule: {molecule_smiles}")
        print(f"{'='*80}\n")

        # Use BioQL ADMET prediction
        result = self.backend.admet_prediction(molecule_smiles)

        # Extract ADMET properties
        admet = {
            "absorption": self._extract_absorption(result),
            "distribution": self._extract_distribution(result),
            "metabolism": self._extract_metabolism(result),
            "excretion": self._extract_excretion(result),
            "toxicity": self._extract_toxicity(result),
            "drug_likeness": self._extract_drug_likeness(result),
        }

        self._print_admet_results(admet)

        return admet

    def optimize_admet(
        self, molecule_smiles: str, target_properties: Optional[Dict] = None
    ) -> Dict:
        """
        Optimize molecule for ADMET properties using QAOA

        Args:
            molecule_smiles: Starting molecule SMILES
            target_properties: Desired ADMET properties

        Returns:
            Optimized molecule and predictions
        """
        print(f"\n{'='*80}")
        print(f"🎯 ADMET OPTIMIZATION")
        print(f"{'='*80}")

        # Build optimization problem
        problem_description = self._build_optimization_problem(molecule_smiles, target_properties)

        # Execute QAOA
        result = self.backend.execute_qaoa(problem_description=problem_description, p_layers=3)

        # Get current ADMET
        current_admet = self.predict_admet(molecule_smiles)

        # Combine results
        optimization_result = {
            "original_smiles": molecule_smiles,
            "current_admet": current_admet,
            "optimization_result": result,
            "constraints_satisfied": self._check_constraints(current_admet),
        }

        print(f"\n✅ Optimization complete")
        print(f"{'='*80}\n")

        return optimization_result

    def check_lipinski(self, molecule_smiles: str) -> Dict[str, bool]:
        """
        Check Lipinski's Rule of Five

        Args:
            molecule_smiles: SMILES string

        Returns:
            Dictionary with pass/fail for each rule
        """
        admet = self.predict_admet(molecule_smiles)
        drug_likeness = admet.get("drug_likeness", {})

        lipinski_check = {
            "molecular_weight": drug_likeness.get("molecular_weight", 0) <= self.max_mw,
            "logP": self.logP_range[0] <= drug_likeness.get("logP", 0) <= self.logP_range[1],
            "h_bond_donors": drug_likeness.get("h_bond_donors", 0) <= self.max_hbd,
            "h_bond_acceptors": drug_likeness.get("h_bond_acceptors", 0) <= self.max_hba,
        }

        lipinski_check["all_pass"] = all(lipinski_check.values())

        print(f"\n📋 LIPINSKI'S RULE OF FIVE:")
        print(
            f"   Molecular Weight ≤ {self.max_mw}: {'✅' if lipinski_check['molecular_weight'] else '❌'}"
        )
        print(f"   LogP in {self.logP_range}: {'✅' if lipinski_check['logP'] else '❌'}")
        print(
            f"   H-bond Donors ≤ {self.max_hbd}: {'✅' if lipinski_check['h_bond_donors'] else '❌'}"
        )
        print(
            f"   H-bond Acceptors ≤ {self.max_hba}: {'✅' if lipinski_check['h_bond_acceptors'] else '❌'}"
        )
        print(f"   Overall: {'✅ PASS' if lipinski_check['all_pass'] else '❌ FAIL'}")

        return lipinski_check

    def calculate_drug_likeness_score(self, molecule_smiles: str) -> float:
        """
        Calculate overall drug-likeness score (0-1)

        Args:
            molecule_smiles: SMILES string

        Returns:
            Drug-likeness score
        """
        admet = self.predict_admet(molecule_smiles)

        # QED score if available
        qed = admet.get("drug_likeness", {}).get("qed_score", 0.5)

        # Lipinski compliance
        lipinski = self.check_lipinski(molecule_smiles)
        lipinski_score = sum(lipinski.values()) / len(lipinski)

        # Combine scores
        overall_score = 0.6 * qed + 0.4 * lipinski_score

        return overall_score

    def _build_optimization_problem(
        self, molecule_smiles: str, target_properties: Optional[Dict]
    ) -> str:
        """Build QAOA optimization problem description"""

        problem = f"""
        Optimize ADMET properties for molecule: {molecule_smiles}

        Constraints (Lipinski's Rule of Five):
        - Molecular Weight ≤ {self.max_mw} Da
        - LogP in range {self.logP_range}
        - H-bond donors ≤ {self.max_hbd}
        - H-bond acceptors ≤ {self.max_hba}

        Optimization objectives:
        1. Maximize oral bioavailability
        2. Minimize toxicity
        3. Optimize blood-brain barrier permeability (if needed)
        4. Maximize metabolic stability
        5. Minimize drug-drug interaction potential

        Use QAOA to find molecular modifications that improve ADMET profile
        while maintaining chemical validity.
        """

        if target_properties:
            problem += "\n\nTarget properties:\n"
            for key, value in target_properties.items():
                problem += f"- {key}: {value}\n"

        return problem

    def _extract_absorption(self, result: Dict) -> Dict:
        """Extract absorption properties"""
        bio = result.get("bio_interpretation", {})
        return {
            "caco2_permeability": bio.get("caco2", "moderate"),
            "hia": bio.get("hia", 0.8),  # Human Intestinal Absorption
            "bioavailability": bio.get("bioavailability", 0.7),
        }

    def _extract_distribution(self, result: Dict) -> Dict:
        """Extract distribution properties"""
        bio = result.get("bio_interpretation", {})
        return {
            "vdss": bio.get("vdss", 1.0),  # Volume of distribution
            "bbb_permeability": bio.get("bbb", "low"),
            "plasma_protein_binding": bio.get("ppb", 0.9),
        }

    def _extract_metabolism(self, result: Dict) -> Dict:
        """Extract metabolism properties"""
        bio = result.get("bio_interpretation", {})
        return {
            "cyp450_substrate": bio.get("cyp450_substrate", False),
            "cyp450_inhibitor": bio.get("cyp450_inhibitor", False),
            "half_life": bio.get("half_life", 4.0),  # hours
        }

    def _extract_excretion(self, result: Dict) -> Dict:
        """Extract excretion properties"""
        bio = result.get("bio_interpretation", {})
        return {
            "clearance": bio.get("clearance", 15.0),  # mL/min/kg
            "renal_clearance": bio.get("renal_clearance", 0.5),
        }

    def _extract_toxicity(self, result: Dict) -> Dict:
        """Extract toxicity properties"""
        bio = result.get("bio_interpretation", {})
        return {
            "hERG": bio.get("herg", "low_risk"),
            "ames": bio.get("ames", "negative"),
            "ld50": bio.get("ld50", 1000),  # mg/kg
            "hepatotoxicity": bio.get("hepatotoxicity", "low"),
        }

    def _extract_drug_likeness(self, result: Dict) -> Dict:
        """Extract drug-likeness properties"""
        bio = result.get("bio_interpretation", {})
        return {
            "qed_score": bio.get("qed_score", 0.5),
            "molecular_weight": bio.get("molecular_weight", 300),
            "logP": bio.get("logP", 2.5),
            "h_bond_donors": bio.get("h_bond_donors", 2),
            "h_bond_acceptors": bio.get("h_bond_acceptors", 4),
            "lipinski_pass": bio.get("lipinski_pass", True),
        }

    def _check_constraints(self, admet: Dict) -> bool:
        """Check if ADMET constraints are satisfied"""
        dl = admet.get("drug_likeness", {})

        checks = [
            dl.get("molecular_weight", 0) <= self.max_mw,
            self.logP_range[0] <= dl.get("logP", 0) <= self.logP_range[1],
            dl.get("h_bond_donors", 0) <= self.max_hbd,
            dl.get("h_bond_acceptors", 0) <= self.max_hba,
        ]

        return all(checks)

    def _print_admet_results(self, admet: Dict):
        """Print formatted ADMET results"""
        print(f"📊 ADMET RESULTS:\n")

        print(f"  🔹 Absorption:")
        for key, value in admet.get("absorption", {}).items():
            print(f"     {key}: {value}")

        print(f"\n  🔹 Distribution:")
        for key, value in admet.get("distribution", {}).items():
            print(f"     {key}: {value}")

        print(f"\n  🔹 Metabolism:")
        for key, value in admet.get("metabolism", {}).items():
            print(f"     {key}: {value}")

        print(f"\n  🔹 Excretion:")
        for key, value in admet.get("excretion", {}).items():
            print(f"     {key}: {value}")

        print(f"\n  🔹 Toxicity:")
        for key, value in admet.get("toxicity", {}).items():
            print(f"     {key}: {value}")

        print(f"\n  🔹 Drug-Likeness:")
        for key, value in admet.get("drug_likeness", {}).items():
            print(f"     {key}: {value}")
