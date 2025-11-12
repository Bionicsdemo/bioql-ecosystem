"""
Regulatory Documentation Generator for CRISPR Therapies
========================================================

Generates IND-ready documentation including:
1. Safety Assessment Reports
2. CMC (Chemistry, Manufacturing, and Controls) documentation
3. Preclinical study templates
4. Clinical protocol outlines

Compliant with:
- FDA IND requirements (21 CFR 312)
- ICH guidelines (Q1-Q12, E6)
- Gene Therapy regulatory framework
"""

from typing import Dict, List, Any
from datetime import datetime


class RegulatoryDocGenerator:
    """
    Generate regulatory documentation for CRISPR gene therapies
    """

    def __init__(self):
        """Initialize regulatory doc generator"""
        self.fda_sections = self._load_fda_sections()

    def _load_fda_sections(self) -> Dict[str, List[str]]:
        """Load FDA IND application sections"""
        return {
            "Form_FDA_1571": [
                "Sponsor information",
                "Drug product name",
                "IND number (if amendment)",
                "Phase of clinical investigation",
                "Clinical investigators",
                "Previous IND information"
            ],
            "Introductory_Statement": [
                "Name of drug",
                "Active ingredients",
                "Pharmacological class",
                "Structural formula",
                "Dosage form and route",
                "Objectives and planned duration"
            ],
            "General_Investigational_Plan": [
                "Rationale for drug or study",
                "Indication(s) to be studied",
                "General approach",
                "Kinds of clinical trials planned",
                "Estimated number of patients"
            ],
            "Investigators_Brochure": [
                "Drug substance description",
                "Summary of pharmacological and toxicological effects",
                "Pharmacokinetics and biological disposition",
                "Summary of previous human experience",
                "Summary of adverse reactions"
            ],
            "Clinical_Protocol": [
                "Study objectives",
                "Investigator qualifications",
                "Patient selection criteria",
                "Study design",
                "Dosage and administration",
                "Clinical observations and tests",
                "Informed consent"
            ],
            "CMC_Information": [
                "Drug substance (gene construct)",
                "Drug product (final formulation)",
                "Placebo if applicable",
                "Labels and labeling",
                "Manufacturing information",
                "Stability data"
            ],
            "Pharmacology_Toxicology": [
                "Pharmacology studies",
                "Toxicology studies",
                "Genotoxicity studies",
                "Biodistribution studies",
                "Immunogenicity studies",
                "Integration site analysis"
            ],
            "Previous_Human_Experience": [
                "If any (published literature)",
                "Investigator-initiated studies",
                "Foreign clinical data"
            ]
        }

    def generate_safety_assessment(self, target_gene: str, grna_sequence: str,
                                   offtarget_results: Dict[str, Any],
                                   delivery_system: str) -> str:
        """
        Generate comprehensive safety assessment report

        Args:
            target_gene: Target gene
            grna_sequence: gRNA sequence
            offtarget_results: Off-target prediction results
            delivery_system: AAV or LNP

        Returns:
            Safety assessment report
        """
        report = f'''
================================================================================
CRISPR GENE THERAPY SAFETY ASSESSMENT REPORT
================================================================================

Date: {datetime.now().strftime("%Y-%m-%d")}
Protocol ID: CRISPR-{target_gene}-001
Gene Target: {target_gene}

================================================================================
1. EXECUTIVE SUMMARY
================================================================================

This safety assessment evaluates the potential risks associated with CRISPR/Cas9-
mediated gene editing targeting {target_gene} using guide RNA sequence:

gRNA: {grna_sequence}

Key Safety Findings:
✅ Guide RNA specificity score: {offtarget_results.get('specificity_score', 'N/A')}/100
✅ Predicted off-target sites: {offtarget_results.get('num_offtargets', 'N/A')}
✅ Delivery system: {delivery_system}

================================================================================
2. GUIDE RNA SAFETY PROFILE
================================================================================

2.1 Sequence Analysis
---------------------
Guide RNA Sequence: {grna_sequence}
PAM Site: NGG (SpCas9)
GC Content: {offtarget_results.get('gc_content', 'N/A')}%
Seed Region GC: {offtarget_results.get('seed_gc', 'N/A')}%

2.2 Off-Target Risk Assessment
-------------------------------
Specificity Score: {offtarget_results.get('specificity_score', 'N/A')}/100
Risk Level: {offtarget_results.get('risk_level', 'To be determined')}

Potential Off-Target Sites: {offtarget_results.get('num_offtargets', 0)}
  - High risk (0-2 mismatches): {offtarget_results.get('high_risk_sites', 0)}
  - Medium risk (3 mismatches): {offtarget_results.get('medium_risk_sites', 0)}
  - Low risk (4+ mismatches): {offtarget_results.get('low_risk_sites', 0)}

2.3 Mitigation Strategies
--------------------------
✅ Use high-fidelity Cas9 variants (e.g., SpCas9-HF1, eSpCas9)
✅ Optimize delivery dose to minimize off-target editing
✅ Perform GUIDE-seq or CIRCLE-seq validation
✅ Monitor patients with whole-genome sequencing

================================================================================
3. DELIVERY SYSTEM SAFETY
================================================================================

Delivery Vector: {delivery_system}

{"AAV Safety Profile:" if "AAV" in delivery_system else "LNP Safety Profile:"}
- Immunogenicity: {"Medium (AAV capsid)" if "AAV" in delivery_system else "Low (lipid)"}
- Integration risk: {"Low (episomal)" if "AAV" in delivery_system else "None"}
- Pre-existing immunity: {"30-60% population" if "AAV" in delivery_system else "Minimal"}
- Dose-limiting toxicity: {"Hepatotoxicity" if "AAV" in delivery_system else "Transient inflammation"}

Safety Monitoring:
✅ Anti-AAV antibody titers (baseline and follow-up)
✅ Liver function tests (ALT, AST, bilirubin)
✅ Complete blood count (CBC)
✅ Inflammatory markers (CRP, IL-6)

================================================================================
4. GENOTOXICITY RISK ASSESSMENT
================================================================================

4.1 Chromosomal Translocations
-------------------------------
Risk Level: Low to Medium
Monitoring: Karyotyping and FISH analysis

4.2 Large Deletions
--------------------
Risk Level: Low (with optimized gRNA design)
Monitoring: Long-read sequencing (PacBio/Nanopore)

4.3 On-Target Mutations
------------------------
Risk Level: Minimal with validated gRNA
Monitoring: Sanger sequencing of edited locus

================================================================================
5. PRECLINICAL SAFETY STUDIES REQUIRED
================================================================================

5.1 In Vitro Studies (COMPLETED/PLANNED)
-----------------------------------------
□ Cell viability assays
□ Editing efficiency (% indels)
□ Off-target analysis (GUIDE-seq/CIRCLE-seq)
□ Chromosomal stability (karyotyping)

5.2 In Vivo Studies (REQUIRED FOR IND)
---------------------------------------
□ Biodistribution study (GLP)
  - Dose: 1e12, 5e12, 1e13 vg/kg (AAV) or equivalent (LNP)
  - Timepoints: Days 1, 7, 28, 90
  - Tissues: Liver, spleen, heart, brain, gonads, injection site

□ Toxicology study (GLP)
  - 13-week repeat dose toxicity
  - Species: Non-human primates (NHP) preferred
  - Endpoints: Clinical observations, hematology, chemistry, histopathology

□ Integration site analysis
  - NGS-based integration mapping
  - Clonal expansion monitoring

□ Reproductive/Developmental toxicity (if applicable)
  - Embryo-fetal development study
  - Pre/postnatal development study

================================================================================
6. CLINICAL MONITORING PLAN
================================================================================

6.1 Phase I Safety Endpoints
-----------------------------
Primary: Dose-limiting toxicities (DLTs)
Secondary: Adverse events (AEs), serious AEs (SAEs)

6.2 Monitoring Schedule
------------------------
Baseline: Complete medical history, labs, imaging
Weekly (Months 1-3): Safety labs, AE monitoring
Monthly (Months 4-12): Safety labs, efficacy markers
Quarterly (Years 2-5): Long-term safety monitoring
Annually (Years 6-15): Long-term follow-up (FDA requirement)

6.3 Safety Stopping Rules
--------------------------
✅ Grade 4 treatment-related AE (except transient lab abnormalities)
✅ Grade 3 treatment-related AE in > 33% of patients
✅ Any case of clonal expansion or malignancy
✅ Severe immunogenicity requiring immunosuppression

================================================================================
7. RISK-BENEFIT ASSESSMENT
================================================================================

Potential Benefits:
✅ Permanent genetic correction
✅ Disease modification or cure
✅ Reduced need for lifelong medication

Potential Risks:
⚠️  Off-target editing (mitigated by high-fidelity Cas9)
⚠️  Immunogenicity (manageable with immunosuppression)
⚠️  Unknown long-term effects (15-year follow-up required)

Overall Assessment: {"FAVORABLE for clinical development" if offtarget_results.get('specificity_score', 0) > 70 else "REQUIRES OPTIMIZATION before clinical development"}

================================================================================
8. REGULATORY RECOMMENDATIONS
================================================================================

✅ RECOMMENDED NEXT STEPS:
1. Complete in vitro off-target validation (GUIDE-seq/CIRCLE-seq)
2. Conduct GLP biodistribution and toxicology studies
3. Develop CMC documentation for vector manufacturing
4. Prepare clinical protocol and informed consent
5. Submit pre-IND meeting request to FDA

📋 IND Application Target: 18-24 months from now

================================================================================
9. REFERENCES
================================================================================

1. FDA Guidance: Human Gene Therapy for Rare Diseases (2020)
2. FDA Guidance: Chemistry, Manufacturing, and Control (CMC) Information for Human Gene Therapy INDs (2020)
3. ICH E6(R2): Good Clinical Practice
4. Doench et al. (2016) Nat Biotechnol - Optimized sgRNA design
5. Hsu et al. (2013) Nat Biotechnol - DNA targeting specificity

================================================================================
REPORT PREPARED BY: BioQL Quantum CRISPR Design System v5.4.4
CONFIDENTIAL - FOR REGULATORY SUBMISSION PURPOSES ONLY
================================================================================
'''

        return report

    def generate_ind_checklist(self, target_gene: str, disease: str) -> str:
        """
        Generate IND application checklist

        Args:
            target_gene: Target gene
            disease: Disease indication

        Returns:
            IND checklist
        """
        checklist = f'''
================================================================================
IND APPLICATION CHECKLIST
================================================================================

Gene Therapy Product: CRISPR/Cas9 targeting {target_gene}
Indication: {disease}
Date: {datetime.now().strftime("%Y-%m-%d")}

================================================================================
SECTION 1: ADMINISTRATIVE (Form FDA 1571)
================================================================================

□ Form FDA 1571 (signed by sponsor or authorized representative)
□ Table of contents
□ Introductory statement and general investigational plan
□ Name and qualifications of investigators
□ Statement of investigator (Form FDA 1572) for each PI

================================================================================
SECTION 2: DRUG PRODUCT INFORMATION
================================================================================

□ Investigator's Brochure
  □ Physical, chemical, and pharmaceutical properties
  □ Formulation
  □ Pharmacological and toxicological effects (animals)
  □ Pharmacokinetics and biological disposition
  □ Previous human experience

================================================================================
SECTION 3: CLINICAL PROTOCOL
================================================================================

□ Study title and protocol number
□ Objectives and rationale
□ Investigator qualifications and experience
□ Patient selection criteria
  □ Inclusion criteria
  □ Exclusion criteria
□ Study design and methodology
  □ Phase (I, II, or III)
  □ Control group (if any)
  □ Randomization and blinding
□ Dose escalation plan (for Phase I)
□ Clinical endpoints
  □ Primary endpoints
  □ Secondary endpoints
  □ Exploratory endpoints
□ Safety monitoring plan
  □ Adverse event reporting
  □ Data Safety Monitoring Board (DSMB) charter
□ Statistical considerations
□ Informed consent document

================================================================================
SECTION 4: CMC (CHEMISTRY, MANUFACTURING, AND CONTROLS)
================================================================================

□ Drug Substance (Gene Construct)
  □ Vector map and sequence
  □ Plasmid construction
  □ Sequence verification
  □ Stability data

□ Drug Product (Final Formulation)
  □ Description and composition
  □ Manufacturing process
    □ Cell line (for AAV: HEK293, SF9, etc.)
    □ Transfection/infection method
    □ Purification method
    □ Formulation and fill/finish
  □ Process controls and validation
  □ Batch records (3 representative batches)
  □ Characterization
    □ Identity (PCR, sequencing)
    □ Purity (SDS-PAGE, Western blot, ddPCR)
    □ Potency (in vitro transduction assay)
    □ Safety (sterility, endotoxin, mycoplasma, RCR/RCL)

□ Container Closure System
□ Stability data (at least 3 time points)
□ Label and labeling
  □ Immediate container label
  □ Outer package label
  □ Investigational use statement

================================================================================
SECTION 5: PHARMACOLOGY AND TOXICOLOGY
================================================================================

□ Pharmacology Studies
  □ Mechanism of action
  □ In vitro editing efficiency
  □ Off-target analysis (computational + experimental)

□ Toxicology Studies (GLP-compliant)
  □ Biodistribution study
    □ Species: Non-human primate (preferred)
    □ Dose levels: 3 (including clinical dose)
    □ Timepoints: 1, 7, 28, 90 days
    □ Tissues analyzed: 20+ organs
    □ Endpoints: Vector DNA, mRNA, protein
  □ Repeat-dose toxicity study (13-week or 26-week)
    □ Species: NHP
    □ Dose levels: 3 + vehicle control
    □ Clinical observations daily
    □ Hematology and clinical chemistry
    □ Histopathology (all major organs)
  □ Genotoxicity studies
    □ Integration site analysis
    □ Chromosomal aberration test
  □ Reproductive toxicology (if indicated)
  □ Immunogenicity and immunotoxicity

□ Study Reports
  □ GLP statement
  □ Quality assurance inspections
  □ Data tables and individual animal data
  □ Pathology peer review

================================================================================
SECTION 6: PREVIOUS HUMAN EXPERIENCE
================================================================================

□ Literature search results
□ Published clinical data (if any)
□ Foreign regulatory approvals
□ Investigator-initiated trials

================================================================================
SECTION 7: ADDITIONAL INFORMATION
================================================================================

□ Gene Therapy Appendix
  □ Vector design and construct
  □ Vector production and testing
  □ Biodistribution and persistence
  □ Integration studies (for integrating vectors)
  □ Shedding studies
  □ Patient follow-up plan (15 years per FDA)

□ Institutional Review Board (IRB) information
  □ List of participating institutions
  □ IRB approval letters (can be submitted later)

□ Other
  □ Environmental assessment (or categorical exclusion)
  □ Previous IND correspondence (if applicable)
  □ Any additional data requested by FDA

================================================================================
SUBMISSION TIMELINE
================================================================================

Recommended Timeline for IND Submission:

Months -24 to -18: Construct optimization, pilot manufacturing
Months -18 to -12: GLP biodistribution study
Months -12 to -6:  GLP toxicology study (13-week)
Months -6 to -3:   CMC process validation, analytical method development
Months -3 to -1:   IND document compilation, quality review
Month 0:           IND submission to FDA
Day 30:            FDA response (clinical hold or proceed)
Month 1-2:         IRB submissions and site initiation
Month 2-3:         First patient enrollment (if no clinical hold)

================================================================================
ESTIMATED COSTS (USD)
================================================================================

GLP Studies:                     $2-5 million
Vector Manufacturing (GMP):      $1-3 million
Analytical Development:          $500K - $1M
Regulatory Consulting:           $200K - $500K
Clinical Site Setup:             $500K - $1M

TOTAL PRE-IND COSTS:            $4.2 - $10.5 million

================================================================================
CONTACT INFORMATION
================================================================================

FDA Division: Division of Cellular and Gene Therapies (DCGT)
Office: Office of Tissues and Advanced Therapies (OTAT)
Center: CBER (Center for Biologics Evaluation and Research)

Pre-IND Meeting: HIGHLY RECOMMENDED
Submit request: 3 months before intended IND submission
Meeting occurs: ~60 days after request
Topics: CMC strategy, nonclinical program, clinical trial design

================================================================================
CHECKLIST GENERATED BY: BioQL Quantum CRISPR Design System v5.4.4
CONFIDENTIAL - FOR INTERNAL USE ONLY
================================================================================
'''

        return checklist


if __name__ == "__main__":
    # Test regulatory doc generation
    generator = RegulatoryDocGenerator()

    print("="*80)
    print("Regulatory Documentation Generator - Test")
    print("="*80)
    print()

    # Generate safety assessment
    offtarget_results = {
        'specificity_score': 85.3,
        'gc_content': 55.0,
        'seed_gc': 62.5,
        'risk_level': 'LOW',
        'num_offtargets': 3,
        'high_risk_sites': 0,
        'medium_risk_sites': 1,
        'low_risk_sites': 2
    }

    report = generator.generate_safety_assessment(
        "PCSK9",
        "GATACCATGATCACGAAGGT",
        offtarget_results,
        "AAV8"
    )

    print(report[:2000])  # Print first 2000 chars
    print("...")
    print(f"\n✅ Full safety report generated ({len(report)} characters)")
    print()

    # Generate IND checklist
    checklist = generator.generate_ind_checklist("PCSK9", "Hypercholesterolemia")
    print("✅ IND checklist generated")
    print(f"   Sections: {len(generator.fda_sections)}")
    print(f"   Length: {len(checklist)} characters")
