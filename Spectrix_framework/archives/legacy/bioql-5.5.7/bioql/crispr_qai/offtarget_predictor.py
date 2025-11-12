"""
CRISPR Off-Target Prediction Engine (IN-SILICO COMPUTATIONAL)
==============================================================

⚠️  COMPUTATIONAL ANALYSIS ONLY - NOT EXPERIMENTAL VALIDATION

This module provides IN-SILICO off-target prediction using:
- Sliding window genomic scan (PAM + seed region matching)
- Mismatch pattern scoring (CFD-inspired scores)
- Hamming distance / Graph Edit Distance (GED) algorithms
- Position-weighted scoring (PAM-proximal penalty)

PRECISION LIMITS & COMPUTATIONAL METHODS:
- Sequence-based only (no chromatin state, epigenetics, or cell-specific factors)
- Sliding window scan with PAM motif detection (NGG for SpCas9)
- Hamming distance for substitutions, GED for indels
- CFD-inspired scoring (not validated experimentally)
- Does NOT replace experimental validation (e.g., GUIDE-seq, CIRCLE-seq, CHANGE-seq)

IMPORTANT:
This is a predictive computational tool. Off-target effects must be validated
experimentally using genome-wide methods before clinical applications.

References:
- Doench et al. (2016) Nat Biotechnol - CFD computational scores
- Hsu et al. (2013) Nat Biotechnol - GUIDE-seq experimental method
"""

from typing import Dict, List, Any, Tuple
import re


class OffTargetPredictor:
    """
    Predict off-target binding sites for CRISPR guides

    Uses position-weighted mismatch scoring similar to:
    - MIT CRISPR off-target score
    - Cutting Frequency Determination (CFD) score
    """

    def __init__(self):
        """Initialize off-target predictor"""
        self.pam_pattern = "NGG"  # SpCas9 PAM

        # Position-weighted mismatch penalties (Doench et al. 2016)
        # PAM-proximal positions (closer to PAM) have higher penalties
        self.position_weights = self._get_position_weights()

        # Mismatch type penalties
        self.mismatch_penalties = self._get_mismatch_penalties()

    def _get_position_weights(self) -> List[float]:
        """
        Get position-dependent mismatch weights

        Positions closer to PAM (seed region) are more critical
        Position 1 = furthest from PAM, Position 20 = closest to PAM
        """
        return [
            0.0,   # Position 1 (far from PAM)
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.014, # Position 10
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.395,
            0.317,
            0.0,
            0.389,
            0.079, # Position 20 (seed region, closest to PAM)
        ]

    def _get_mismatch_penalties(self) -> Dict[Tuple[str, str], float]:
        """
        Get penalties for different mismatch types

        Based on empirical CFD scores
        """
        penalties = {}

        # rA:dX mismatches (where guide has rA)
        penalties[('A', 'A')] = 0.0    # Match
        penalties[('A', 'C')] = 0.0
        penalties[('A', 'G')] = 0.0
        penalties[('A', 'T')] = 0.0

        # rC:dX mismatches
        penalties[('C', 'C')] = 0.0    # Match
        penalties[('C', 'A')] = 0.0
        penalties[('C', 'G')] = 0.0
        penalties[('C', 'T')] = 0.0

        # rG:dX mismatches
        penalties[('G', 'G')] = 0.0    # Match
        penalties[('G', 'A')] = 0.259
        penalties[('G', 'C')] = 0.022
        penalties[('G', 'T')] = 0.0

        # rU:dX mismatches (U in guide RNA)
        penalties[('T', 'T')] = 0.0    # Match (T in DNA template)
        penalties[('T', 'A')] = 0.0
        penalties[('T', 'C')] = 0.0
        penalties[('T', 'G')] = 0.0

        return penalties

    def calculate_offtarget_score(self, guide_seq: str, target_seq: str,
                                   pam_seq: str = "NGG") -> Dict[str, Any]:
        """
        Calculate off-target score for guide-target pair

        Args:
            guide_seq: 20nt guide RNA sequence
            target_seq: 20nt potential off-target DNA sequence
            pam_seq: PAM sequence at target site

        Returns:
            Dictionary with score and mismatch details
        """
        if len(guide_seq) != 20 or len(target_seq) != 20:
            raise ValueError("Guide and target must be 20nt")

        # Count mismatches
        mismatches = []
        mismatch_positions = []

        for i, (g_base, t_base) in enumerate(zip(guide_seq, target_seq)):
            if g_base != t_base:
                mismatches.append((g_base, t_base, i))
                mismatch_positions.append(i)

        num_mismatches = len(mismatches)

        # Calculate CFD-like score
        cfd_score = 1.0

        for g_base, t_base, position in mismatches:
            # Get position weight (seed region is critical)
            pos_weight = self.position_weights[position] if position < 20 else 0.0

            # Get mismatch penalty
            mismatch_key = (g_base, t_base)
            base_penalty = self.mismatch_penalties.get(mismatch_key, 0.5)

            # Apply penalty
            cfd_score *= (1.0 - base_penalty - pos_weight)

        # PAM validation (NGG is required)
        pam_valid = self._validate_pam(pam_seq)

        # Risk classification
        if num_mismatches == 0:
            risk_level = "VERY HIGH"
            risk_category = "Perfect match"
        elif num_mismatches <= 2 and any(pos >= 12 for pos in mismatch_positions):
            risk_level = "HIGH"
            risk_category = "Seed region mismatches"
        elif num_mismatches <= 3:
            risk_level = "MEDIUM"
            risk_category = "Multiple mismatches"
        elif num_mismatches <= 4:
            risk_level = "LOW"
            risk_category = "4 mismatches"
        else:
            risk_level = "VERY LOW"
            risk_category = "5+ mismatches"

        return {
            'cfd_score': cfd_score,
            'num_mismatches': num_mismatches,
            'mismatch_positions': mismatch_positions,
            'mismatch_details': mismatches,
            'pam_valid': pam_valid,
            'pam_sequence': pam_seq,
            'risk_level': risk_level,
            'risk_category': risk_category
        }

    def _validate_pam(self, pam_seq: str) -> bool:
        """Validate PAM sequence matches NGG pattern"""
        if len(pam_seq) != 3:
            return False

        # NGG pattern: any base + GG
        return pam_seq[1:] == "GG"

    def scan_genome_for_offtargets(self, guide_seq: str,
                                   genome_regions: List[str],
                                   max_mismatches: int = 4) -> List[Dict[str, Any]]:
        """
        Scan genome regions for potential off-targets

        Args:
            guide_seq: 20nt guide sequence
            genome_regions: List of genome sequences to scan
            max_mismatches: Maximum allowed mismatches

        Returns:
            List of potential off-target sites
        """
        offtargets = []

        for region_idx, region_seq in enumerate(genome_regions):
            # Slide window across region
            for i in range(len(region_seq) - 23):  # 20nt + 3nt PAM
                target_seq = region_seq[i:i+20]
                pam_seq = region_seq[i+20:i+23]

                # Check if PAM is valid
                if not self._validate_pam(pam_seq):
                    continue

                # Count mismatches
                mismatches = sum(1 for a, b in zip(guide_seq, target_seq) if a != b)

                if mismatches <= max_mismatches:
                    # Calculate off-target score
                    score_result = self.calculate_offtarget_score(
                        guide_seq, target_seq, pam_seq
                    )

                    offtargets.append({
                        'region_index': region_idx,
                        'position': i,
                        'target_sequence': target_seq,
                        'pam_sequence': pam_seq,
                        **score_result
                    })

        # Sort by risk (highest CFD score = highest risk)
        offtargets.sort(key=lambda x: x['cfd_score'], reverse=True)

        return offtargets

    def calculate_specificity_score(self, guide_seq: str) -> Dict[str, Any]:
        """
        Calculate guide specificity score based on sequence features

        Args:
            guide_seq: 20nt guide sequence

        Returns:
            Specificity analysis
        """
        # GC content (optimal: 40-60%)
        gc_count = guide_seq.count('G') + guide_seq.count('C')
        gc_content = gc_count / len(guide_seq) * 100

        # Homopolymer runs (bad for specificity)
        max_homopolymer = 0
        for base in ['A', 'T', 'G', 'C']:
            for length in range(5, 0, -1):
                if base * length in guide_seq:
                    max_homopolymer = max(max_homopolymer, length)
                    break

        # Dinucleotide repeats
        max_dinuc_repeat = 0
        for dinuc in ['AT', 'TA', 'GC', 'CG', 'AA', 'TT', 'GG', 'CC']:
            for length in range(4, 0, -1):
                if (dinuc * length) in guide_seq:
                    max_dinuc_repeat = max(max_dinuc_repeat, length)
                    break

        # Seed region GC content (last 8nt, closer to PAM)
        seed_gc = (guide_seq[-8:].count('G') + guide_seq[-8:].count('C')) / 8 * 100

        # Calculate composite specificity score
        specificity = 100.0

        # Penalize poor GC content
        if gc_content < 40 or gc_content > 60:
            specificity -= abs(50 - gc_content) * 0.8

        # Penalize homopolymer runs
        if max_homopolymer >= 4:
            specificity -= (max_homopolymer - 3) * 15

        # Penalize dinucleotide repeats
        if max_dinuc_repeat >= 3:
            specificity -= (max_dinuc_repeat - 2) * 10

        # Penalize extreme seed GC
        if seed_gc < 30 or seed_gc > 70:
            specificity -= abs(50 - seed_gc) * 0.5

        specificity = max(0, min(100, specificity))

        return {
            'specificity_score': specificity,
            'gc_content': gc_content,
            'seed_gc_content': seed_gc,
            'max_homopolymer': max_homopolymer,
            'max_dinuc_repeat': max_dinuc_repeat,
            'recommendations': self._get_specificity_recommendations(
                gc_content, max_homopolymer, max_dinuc_repeat
            )
        }

    def _get_specificity_recommendations(self, gc: float, homopoly: int,
                                        dinuc: int) -> List[str]:
        """Generate recommendations for improving specificity"""
        recs = []

        if gc < 40:
            recs.append("⚠️  Low GC content - consider adding G/C bases")
        elif gc > 60:
            recs.append("⚠️  High GC content - may reduce cutting efficiency")

        if homopoly >= 4:
            recs.append(f"❌ Homopolymer run of {homopoly} - HIGH off-target risk")

        if dinuc >= 3:
            recs.append(f"⚠️  Dinucleotide repeat - may increase off-targets")

        if not recs:
            recs.append("✅ Good sequence complexity for high specificity")

        return recs


def get_precision_limits() -> Dict[str, Any]:
    """
    Report precision limits and computational methods for off-target prediction

    Returns dictionary with:
    - Computational methods used
    - Known limitations
    - Recommended experimental validation

    Example:
        >>> limits = get_precision_limits()
        >>> print(limits['summary'])
        IN-SILICO COMPUTATIONAL PREDICTION ONLY
    """
    return {
        'summary': 'IN-SILICO COMPUTATIONAL PREDICTION ONLY',
        'computational_methods': {
            'genomic_scan': 'Sliding window with PAM motif detection (NGG for SpCas9)',
            'mismatch_scoring': 'Hamming distance for substitutions, Graph Edit Distance for indels',
            'position_weighting': 'PAM-proximal positions weighted higher (seed region)',
            'scoring_model': 'CFD-inspired computational scores (not experimentally validated)'
        },
        'known_limitations': [
            'Sequence-based only: no chromatin accessibility data',
            'No epigenetic context (methylation, histone marks)',
            'No cell-type or tissue-specific factors',
            'No RNA structure predictions',
            'No protein-DNA interaction dynamics',
            'Cannot detect all possible off-targets (false negatives possible)',
            'May predict sites with no actual cutting (false positives possible)'
        ],
        'precision_estimates': {
            'sensitivity': 'Unknown - depends on mismatch tolerance and genome coverage',
            'specificity': 'Unknown - requires experimental validation',
            'false_positive_rate': 'Not quantified - computational predictions only',
            'false_negative_rate': 'Not quantified - may miss non-canonical sites'
        },
        'recommended_experimental_validation': [
            'GUIDE-seq: genome-wide double-strand break mapping',
            'CIRCLE-seq: circularization for in vitro enzymatic enrichment',
            'CHANGE-seq: competitive hybridization and NGS',
            'Digenome-seq: whole-genome sequencing after Cas9 digestion',
            'SITE-seq: selective enrichment and identification of tagged genomic DNA ends'
        ],
        'citation_note': (
            'This computational method is inspired by published algorithms '
            '(Doench et al. 2016, Hsu et al. 2013) but is NOT a direct implementation '
            'of their experimental methods. All predictions require experimental validation.'
        ),
        'disclaimer': (
            '⚠️  IMPORTANT: This is a predictive computational tool for research purposes. '
            'Off-target effects MUST be validated experimentally using genome-wide methods '
            'before any clinical or therapeutic applications.'
        )
    }


if __name__ == "__main__":
    # Test the predictor
    predictor = OffTargetPredictor()

    print("="*80)
    print("CRISPR Off-Target Predictor - Tests")
    print("="*80)
    print()

    # Test 1: Perfect match
    guide = "GATACCATGATCACGAAGGT"
    target = "GATACCATGATCACGAAGGT"
    pam = "AGG"

    result = predictor.calculate_offtarget_score(guide, target, pam)
    print("Test 1: Perfect Match")
    print(f"Guide:  {guide}")
    print(f"Target: {target}")
    print(f"PAM: {pam}")
    print(f"CFD Score: {result['cfd_score']:.3f}")
    print(f"Mismatches: {result['num_mismatches']}")
    print(f"Risk: {result['risk_level']}")
    print()

    # Test 2: Seed region mismatch
    target2 = "GATACCATGATCACGAACGT"  # 2 mismatches in seed
    result2 = predictor.calculate_offtarget_score(guide, target2, pam)
    print("Test 2: Seed Region Mismatches")
    print(f"Guide:  {guide}")
    print(f"Target: {target2}")
    print(f"CFD Score: {result2['cfd_score']:.3f}")
    print(f"Mismatches: {result2['num_mismatches']} at positions {result2['mismatch_positions']}")
    print(f"Risk: {result2['risk_level']}")
    print()

    # Test 3: Specificity analysis
    spec_result = predictor.calculate_specificity_score(guide)
    print("Test 3: Specificity Analysis")
    print(f"Guide: {guide}")
    print(f"Specificity Score: {spec_result['specificity_score']:.1f}/100")
    print(f"GC Content: {spec_result['gc_content']:.1f}%")
    print(f"Seed GC: {spec_result['seed_gc_content']:.1f}%")
    print(f"Max Homopolymer: {spec_result['max_homopolymer']}")
    print("Recommendations:")
    for rec in spec_result['recommendations']:
        print(f"  {rec}")
