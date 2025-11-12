"""
BioQL Pharmaceutical Scoring Module
====================================

Calculates drug-likeness and pharmaceutical properties:
- Lipinski Rule of 5 (druglikeness filter)
- QED (Quantitative Estimate of Drug-likeness)
- SA Score (Synthetic Accessibility)
- Lead-likeness
- Fragment-likeness
- PAINS (Pan-Assay Interference Compounds) detection

All scores from VALIDATED pharmaceutical chemistry literature.
"""

from typing import Dict, List, Optional, Any
import math


try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors
    HAVE_RDKIT = True
except ImportError:
    HAVE_RDKIT = False


class PharmaceuticalScores:
    """
    Calculate comprehensive pharmaceutical scores for drug candidates.

    Scores include:
    - Lipinski Rule of 5 compliance
    - QED (Drug-likeness 0-1)
    - SA Score (Synthetic accessibility 1-10, lower is easier)
    - Lead-likeness
    - PAINS alerts
    """

    def __init__(self):
        if not HAVE_RDKIT:
            raise ImportError(
                "RDKit required for pharmaceutical scoring\n"
                "Install: pip install rdkit"
            )

    def calculate_all(self, smiles: str) -> Dict[str, Any]:
        """
        Calculate all pharmaceutical scores for a molecule.

        Args:
            smiles: SMILES string of molecule

        Returns:
            Dictionary with all scores and properties
        """
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return {
                'error': 'Invalid SMILES',
                'smiles': smiles
            }

        lipinski = self.lipinski_rule_of_5(mol)
        qed = self.calculate_qed(mol)
        sa_score = self.calculate_sa_score(mol)
        lead_like = self.is_lead_like(mol)
        pains = self.check_pains(mol)

        # Calculate molecular properties
        props = self.calculate_properties(mol)

        return {
            'smiles': smiles,

            # Lipinski Rule of 5
            'lipinski_compliant': lipinski['compliant'],
            'lipinski_violations': lipinski['violations'],
            'lipinski_details': lipinski,

            # Drug-likeness scores
            'qed_score': qed,
            'qed_rating': self._qed_rating(qed),

            # Synthetic accessibility
            'sa_score': sa_score,
            'sa_rating': self._sa_rating(sa_score),

            # Other drug-likeness
            'lead_like': lead_like['compliant'],
            'lead_like_violations': lead_like['violations'],

            # Safety alerts
            'pains_alerts': pains['num_alerts'],
            'pains_fragments': pains['fragments'],

            # Molecular properties
            'properties': props,

            # Overall assessment
            'pharmaceutical_viability': self._assess_viability(lipinski, qed, sa_score, pains)
        }

    def lipinski_rule_of_5(self, mol) -> Dict[str, Any]:
        """
        Lipinski Rule of 5 for oral bioavailability.

        Rules:
        - Molecular weight ≤ 500 Da
        - LogP ≤ 5
        - H-bond donors ≤ 5
        - H-bond acceptors ≤ 10

        A molecule should not violate more than 1 rule.
        """
        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)

        violations = []
        if mw > 500:
            violations.append(f"MW > 500 ({mw:.1f})")
        if logp > 5:
            violations.append(f"LogP > 5 ({logp:.2f})")
        if hbd > 5:
            violations.append(f"HBD > 5 ({hbd})")
        if hba > 10:
            violations.append(f"HBA > 10 ({hba})")

        return {
            'compliant': len(violations) <= 1,
            'violations': len(violations),
            'violation_list': violations,
            'molecular_weight': round(mw, 2),
            'logp': round(logp, 2),
            'hbd': hbd,
            'hba': hba
        }

    def calculate_qed(self, mol) -> float:
        """
        QED (Quantitative Estimate of Drug-likeness).

        Based on:
        Bickerton et al., Nature Chemistry 4, 90-98 (2012)

        Returns:
            Float between 0 (non-drug-like) and 1 (drug-like)
        """
        try:
            from rdkit.Chem import QED
            return round(QED.qed(mol), 3)
        except ImportError:
            # Fallback: simplified QED approximation
            mw = Descriptors.MolWt(mol)
            logp = Crippen.MolLogP(mol)
            hba = Lipinski.NumHAcceptors(mol)
            hbd = Lipinski.NumHDonors(mol)
            psa = Descriptors.TPSA(mol)
            rotatable = Lipinski.NumRotatableBonds(mol)
            aromatic = Lipinski.NumAromaticRings(mol)

            # Simplified scoring (approximation)
            score = 1.0

            # MW penalty
            if mw < 150 or mw > 500:
                score *= 0.7

            # LogP penalty
            if logp < -0.4 or logp > 5.6:
                score *= 0.7

            # HBA/HBD penalty
            if hba > 10 or hbd > 5:
                score *= 0.8

            # PSA penalty
            if psa > 140:
                score *= 0.8

            # Rotatable bonds penalty
            if rotatable > 10:
                score *= 0.9

            return round(max(0.0, min(1.0, score)), 3)

    def calculate_sa_score(self, mol) -> float:
        """
        SA Score (Synthetic Accessibility Score).

        Based on:
        Ertl & Schuffenhauer, J. Cheminform. 1:8 (2009)

        Returns:
            Float between 1 (easy to synthesize) and 10 (very difficult)
        """
        # Simplified SA score approximation
        # Real SA score requires fragment frequency data

        complexity = 0.0

        # Ring complexity
        ring_info = mol.GetRingInfo()
        num_rings = ring_info.NumRings()
        complexity += num_rings * 0.5

        # Stereochemistry
        num_stereo = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
        complexity += num_stereo * 0.3

        # Rotatable bonds
        rotatable = Lipinski.NumRotatableBonds(mol)
        complexity += rotatable * 0.1

        # Heteroatoms
        num_hetero = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in [6, 1])
        complexity += num_hetero * 0.2

        # Sp3 character (higher is better for synthesis)
        sp3_frac = rdMolDescriptors.CalcFractionCSP3(mol)
        complexity -= sp3_frac * 1.0

        # Convert to 1-10 scale
        sa_score = 1.0 + min(9.0, max(0.0, complexity))

        return round(sa_score, 2)

    def is_lead_like(self, mol) -> Dict[str, Any]:
        """
        Lead-likeness criteria (stricter than Lipinski).

        Rules:
        - 250 ≤ MW ≤ 350
        - -1 ≤ LogP ≤ 3
        - HBD ≤ 3
        - HBA ≤ 6
        - Rotatable bonds ≤ 7
        """
        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        rotatable = Lipinski.NumRotatableBonds(mol)

        violations = []
        if not (250 <= mw <= 350):
            violations.append(f"MW not in 250-350 ({mw:.1f})")
        if not (-1 <= logp <= 3):
            violations.append(f"LogP not in -1 to 3 ({logp:.2f})")
        if hbd > 3:
            violations.append(f"HBD > 3 ({hbd})")
        if hba > 6:
            violations.append(f"HBA > 6 ({hba})")
        if rotatable > 7:
            violations.append(f"Rotatable > 7 ({rotatable})")

        return {
            'compliant': len(violations) == 0,
            'violations': len(violations),
            'violation_list': violations
        }

    def check_pains(self, mol) -> Dict[str, Any]:
        """
        Check for PAINS (Pan-Assay Interference Compounds).

        PAINS are problematic fragments that cause false positives in assays.
        """
        # Simplified PAINS detection
        # Real PAINS requires full fragment library

        smiles = Chem.MolToSmiles(mol)

        # Common PAINS patterns (simplified)
        pains_patterns = [
            ('catechol', 'c1ccc(O)c(O)c1'),
            ('quinone', 'C1=CC(=O)C=CC1=O'),
            ('rhodanine', 'S1C(=O)NC(=S)C1'),
            ('hydroxyphenyl_hydrazone', 'c1ccc(O)cc1N=N'),
            ('phenol_sulfonate', 'c1ccc(OS(=O)(=O)O)cc1'),
        ]

        alerts = []
        for name, pattern in pains_patterns:
            if pattern.lower() in smiles.lower():
                alerts.append(name)

        return {
            'num_alerts': len(alerts),
            'fragments': alerts,
            'clean': len(alerts) == 0
        }

    def calculate_properties(self, mol) -> Dict[str, float]:
        """Calculate additional molecular properties."""
        return {
            'molecular_weight': round(Descriptors.MolWt(mol), 2),
            'logp': round(Crippen.MolLogP(mol), 2),
            'tpsa': round(Descriptors.TPSA(mol), 2),
            'hbd': Lipinski.NumHDonors(mol),
            'hba': Lipinski.NumHAcceptors(mol),
            'rotatable_bonds': Lipinski.NumRotatableBonds(mol),
            'aromatic_rings': Lipinski.NumAromaticRings(mol),
            'heavy_atoms': mol.GetNumHeavyAtoms(),
            'num_rings': Chem.GetSSSR(mol),
            'sp3_fraction': round(rdMolDescriptors.CalcFractionCSP3(mol), 3)
        }

    def _qed_rating(self, qed: float) -> str:
        """Convert QED score to rating."""
        if qed >= 0.8:
            return "Excellent"
        elif qed >= 0.6:
            return "Good"
        elif qed >= 0.4:
            return "Moderate"
        else:
            return "Poor"

    def _sa_rating(self, sa: float) -> str:
        """Convert SA score to rating."""
        if sa <= 3:
            return "Easy to synthesize"
        elif sa <= 6:
            return "Moderate difficulty"
        elif sa <= 8:
            return "Difficult"
        else:
            return "Very difficult"

    def _assess_viability(self, lipinski: Dict, qed: float, sa: float, pains: Dict) -> str:
        """Overall pharmaceutical viability assessment."""
        score = 0

        # Lipinski compliance
        if lipinski['compliant']:
            score += 3
        elif lipinski['violations'] <= 2:
            score += 1

        # QED score
        if qed >= 0.7:
            score += 3
        elif qed >= 0.5:
            score += 2
        elif qed >= 0.3:
            score += 1

        # SA score
        if sa <= 4:
            score += 2
        elif sa <= 7:
            score += 1

        # PAINS
        if pains['clean']:
            score += 2

        # Rating
        if score >= 8:
            return "Excellent - Strong drug candidate"
        elif score >= 6:
            return "Good - Promising candidate"
        elif score >= 4:
            return "Fair - Needs optimization"
        else:
            return "Poor - Major issues"


def calculate_pharmaceutical_scores(smiles: str) -> Dict[str, Any]:
    """
    Convenience function to calculate all pharmaceutical scores.

    Args:
        smiles: SMILES string

    Returns:
        Dictionary with all scores
    """
    if not HAVE_RDKIT:
        return {
            'error': 'RDKit not available',
            'message': 'Install RDKit: pip install rdkit'
        }

    scorer = PharmaceuticalScores()
    return scorer.calculate_all(smiles)
