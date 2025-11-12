"""
CRISPR Delivery Systems Design
===============================

Templates for:
1. AAV (Adeno-Associated Virus) vector design
2. LNP (Lipid Nanoparticle) formulation
3. Delivery optimization for different tissues

Clinical delivery systems used in:
- Luxturna (AAV2 for retinal dystrophy) - FDA approved
- Zolgensma (AAV9 for SMA) - FDA approved
- Patisiran (LNP for hATTR amyloidosis) - FDA approved
- COVID-19 mRNA vaccines (LNP) - FDA approved
"""

from typing import Dict, List, Any


class DeliverySystemDesigner:
    """
    Design CRISPR delivery systems for clinical applications
    """

    def __init__(self):
        """Initialize delivery system designer"""
        self.aav_serotypes = self._load_aav_serotypes()
        self.lnp_formulations = self._load_lnp_formulations()
        self.tissue_targeting = self._load_tissue_targeting()

    def _load_aav_serotypes(self) -> Dict[str, Dict[str, Any]]:
        """
        Load AAV serotype database

        Each serotype has different tissue tropism
        """
        return {
            "AAV1": {
                "tropism": ["Muscle", "Heart", "CNS"],
                "transduction_efficiency": "High",
                "immunogenicity": "Medium",
                "clinical_use": ["Muscular dystrophy"],
                "packaging_capacity": "4.7 kb"
            },
            "AAV2": {
                "tropism": ["Retina", "CNS", "Liver"],
                "transduction_efficiency": "Medium",
                "immunogenicity": "Low",
                "clinical_use": ["Luxturna (retinal dystrophy)", "Hemophilia B"],
                "packaging_capacity": "4.7 kb",
                "fda_approved": True
            },
            "AAV5": {
                "tropism": ["Lung", "CNS", "Retina"],
                "transduction_efficiency": "High",
                "immunogenicity": "Low",
                "clinical_use": ["Cystic fibrosis trials"],
                "packaging_capacity": "4.7 kb"
            },
            "AAV8": {
                "tropism": ["Liver", "Muscle", "CNS"],
                "transduction_efficiency": "Very High",
                "immunogenicity": "Medium",
                "clinical_use": ["Hemophilia A/B"],
                "packaging_capacity": "4.7 kb"
            },
            "AAV9": {
                "tropism": ["CNS", "Heart", "Liver", "Muscle"],
                "transduction_efficiency": "Very High",
                "immunogenicity": "Medium",
                "clinical_use": ["Zolgensma (SMA)", "CNS disorders"],
                "packaging_capacity": "4.7 kb",
                "fda_approved": True,
                "crosses_bbb": True
            },
            "AAVrh10": {
                "tropism": ["CNS", "Muscle", "Liver"],
                "transduction_efficiency": "High",
                "immunogenicity": "Low",
                "clinical_use": ["CNS gene therapy trials"],
                "packaging_capacity": "4.7 kb"
            }
        }

    def _load_lnp_formulations(self) -> Dict[str, Dict[str, Any]]:
        """
        Load LNP formulation database

        LNPs used in mRNA therapeutics
        """
        return {
            "MC3-LNP": {
                "components": {
                    "ionizable_lipid": "MC3 (DLin-MC3-DMA)",
                    "helper_lipid": "DSPC",
                    "cholesterol": "Cholesterol",
                    "peg_lipid": "DMG-PEG2000"
                },
                "ratio": "50:10:38.5:1.5",
                "particle_size": "80-100 nm",
                "clinical_use": ["Patisiran (hATTR)"],
                "fda_approved": True,
                "target_tissue": "Liver"
            },
            "SM-102-LNP": {
                "components": {
                    "ionizable_lipid": "SM-102",
                    "helper_lipid": "DSPC",
                    "cholesterol": "Cholesterol",
                    "peg_lipid": "DMG-PEG2000"
                },
                "ratio": "50:10:38.5:1.5",
                "particle_size": "80-100 nm",
                "clinical_use": ["Moderna COVID-19 vaccine"],
                "fda_approved": True,
                "target_tissue": "Muscle (IM injection)"
            },
            "ALC-0315-LNP": {
                "components": {
                    "ionizable_lipid": "ALC-0315",
                    "helper_lipid": "DSPC",
                    "cholesterol": "Cholesterol",
                    "peg_lipid": "ALC-0159"
                },
                "ratio": "46.3:9.4:42.7:1.6",
                "particle_size": "80-100 nm",
                "clinical_use": ["Pfizer-BioNTech COVID-19 vaccine"],
                "fda_approved": True,
                "target_tissue": "Muscle (IM injection)"
            }
        }

    def _load_tissue_targeting(self) -> Dict[str, Dict[str, Any]]:
        """
        Load tissue-specific targeting strategies
        """
        return {
            "Liver": {
                "preferred_delivery": ["AAV8", "LNP"],
                "route": "Intravenous",
                "challenges": ["Pre-existing immunity", "Dose-dependent toxicity"],
                "clinical_examples": ["Hemophilia gene therapy", "Patisiran"]
            },
            "CNS": {
                "preferred_delivery": ["AAV9", "AAVrh10"],
                "route": "Intrathecal or Intravenous",
                "challenges": ["BBB crossing", "Immune response"],
                "clinical_examples": ["Zolgensma (SMA)"]
            },
            "Retina": {
                "preferred_delivery": ["AAV2", "AAV5"],
                "route": "Subretinal injection",
                "challenges": ["Limited injection volume", "Surgical precision"],
                "clinical_examples": ["Luxturna"]
            },
            "Muscle": {
                "preferred_delivery": ["AAV1", "AAV9", "LNP"],
                "route": "Intramuscular",
                "challenges": ["Distribution", "Immune response"],
                "clinical_examples": ["Muscular dystrophy trials", "mRNA vaccines"]
            },
            "Lung": {
                "preferred_delivery": ["AAV5", "LNP"],
                "route": "Inhalation or IV",
                "challenges": ["Mucociliary clearance", "Immune cells"],
                "clinical_examples": ["Cystic fibrosis trials"]
            }
        }

    def design_aav_vector(self, target_gene: str, target_tissue: str,
                         cas9_variant: str = "SpCas9") -> Dict[str, Any]:
        """
        Design AAV vector for CRISPR delivery

        Args:
            target_gene: Gene to edit
            target_tissue: Target tissue
            cas9_variant: Cas9 variant (SpCas9, SaCas9, etc.)

        Returns:
            AAV vector design specification
        """
        # Select AAV serotype based on tissue
        tissue_info = self.tissue_targeting.get(target_tissue, {})
        preferred_aavs = tissue_info.get('preferred_delivery', ['AAV9'])

        # Filter for AAV vectors only
        aav_options = [aav for aav in preferred_aavs if aav.startswith('AAV')]
        selected_aav = aav_options[0] if aav_options else 'AAV9'

        aav_info = self.aav_serotypes[selected_aav]

        # Design vector components
        vector_design = {
            'serotype': selected_aav,
            'tropism': aav_info['tropism'],
            'target_tissue': target_tissue,
            'target_gene': target_gene,
            'packaging_capacity': aav_info['packaging_capacity'],
            'components': {
                'promoter': self._select_promoter(target_tissue, cas9_variant),
                'cas9': cas9_variant,
                'grna_scaffold': 'tracrRNA',
                'polya': 'SV40 polyA',
                'itr': '5\' and 3\' ITR (AAV2)'
            },
            'estimated_size': self._calculate_vector_size(cas9_variant),
            'clinical_considerations': {
                'immunogenicity': aav_info['immunogenicity'],
                'pre_existing_immunity': '30-60% of population',
                'dosing': '1e13 - 1e14 vg/kg',
                'route': tissue_info.get('route', 'Intravenous'),
                'manufacturing': 'Suspension cell culture (HEK293 or SF9)'
            },
            'regulatory_path': {
                'preclinical': ['Biodistribution', 'Toxicology', 'Immunogenicity'],
                'clinical': ['Phase I (safety)', 'Phase II (efficacy)', 'Phase III (pivotal)'],
                'approval': 'BLA (Biologics License Application)'
            }
        }

        return vector_design

    def design_lnp_formulation(self, target_tissue: str,
                               payload_type: str = "Cas9_mRNA") -> Dict[str, Any]:
        """
        Design LNP formulation for CRISPR delivery

        Args:
            target_tissue: Target tissue
            payload_type: Type of payload (Cas9_mRNA, RNP, etc.)

        Returns:
            LNP formulation specification
        """
        # Select LNP based on tissue
        if target_tissue == "Liver":
            lnp_type = "MC3-LNP"
        elif target_tissue == "Muscle":
            lnp_type = "SM-102-LNP"
        else:
            lnp_type = "SM-102-LNP"  # Default

        lnp_info = self.lnp_formulations[lnp_type]
        tissue_info = self.tissue_targeting.get(target_tissue, {})

        formulation_design = {
            'lnp_type': lnp_type,
            'target_tissue': target_tissue,
            'payload': payload_type,
            'components': lnp_info['components'],
            'molar_ratio': lnp_info['ratio'],
            'particle_size': lnp_info['particle_size'],
            'encapsulation': {
                'method': 'Microfluidic mixing',
                'efficiency': '> 90%',
                'n_p_ratio': '3-6 (nitrogen/phosphate)'
            },
            'formulation_buffer': {
                'buffer': 'Citrate or Acetate',
                'ph': '4.0 - 5.0 (for mixing)',
                'final_ph': '7.4 (physiological)',
                'excipients': ['Sucrose (cryoprotectant)', 'Tris-HCl']
            },
            'dosing': {
                'payload_amount': '0.1 - 2 mg mRNA',
                'administration': tissue_info.get('route', 'Intravenous'),
                'frequency': 'Single dose or repeat dosing'
            },
            'storage': {
                'temperature': '-80°C to -20°C',
                'stability': '6-12 months frozen',
                'thawing': 'Room temperature or 2-8°C'
            },
            'clinical_considerations': {
                'immunogenicity': 'Low (minimal innate immune activation)',
                'biodistribution': f'Primary accumulation in {target_tissue}',
                'clearance': 'Hepatic metabolism',
                'safety': 'Generally well-tolerated'
            },
            'manufacturing': {
                'lipid_synthesis': 'Chemical synthesis (GMP)',
                'lnp_formation': 'Microfluidic mixing (Precision NanoSystems)',
                'purification': 'Tangential flow filtration (TFF)',
                'qa_qc': ['Particle size (DLS)', 'Encapsulation (Quant-iT)', 'Endotoxin']
            }
        }

        return formulation_design

    def _select_promoter(self, tissue: str, cas9: str) -> str:
        """Select tissue-specific promoter"""
        tissue_promoters = {
            "Liver": "TBG (thyroxine-binding globulin)",
            "CNS": "hSyn (human synapsin)",
            "Muscle": "CK8 (muscle creatine kinase)",
            "Retina": "VMD2 (vitelliform macular dystrophy 2)",
            "Lung": "SP-C (surfactant protein C)"
        }

        return tissue_promoters.get(tissue, "CMV (ubiquitous)")

    def _calculate_vector_size(self, cas9: str) -> str:
        """Calculate estimated vector size"""
        cas9_sizes = {
            "SpCas9": "4.1 kb",
            "SaCas9": "3.2 kb",  # Smaller, fits better in AAV
            "CjCas9": "2.9 kb"   # Even smaller
        }

        # Total size = Cas9 + gRNA + promoter + polyA + ITRs
        base_size = cas9_sizes.get(cas9, "4.1 kb")

        return f"~{base_size} (Cas9) + 0.3 kb (gRNA) + 0.5 kb (promoter) = Total ~{float(base_size.split()[0]) + 0.8:.1f} kb"


def generate_delivery_template(target_gene: str, target_tissue: str,
                               disease: str, delivery_type: str = "AAV") -> str:
    """
    Generate delivery system design template

    Args:
        target_gene: Target gene
        target_tissue: Target tissue
        disease: Disease indication
        delivery_type: 'AAV' or 'LNP'

    Returns:
        Python code template for delivery system
    """
    designer = DeliverySystemDesigner()

    if delivery_type == "AAV":
        design = designer.design_aav_vector(target_gene, target_tissue)

        template = f'''#!/usr/bin/env python3
"""
AAV Vector Design for CRISPR Therapy
=====================================

Target Gene: {target_gene}
Target Tissue: {target_tissue}
Disease: {disease}

AAV Serotype: {design['serotype']}
Tropism: {', '.join(design['tropism'])}
"""

print("="*80)
print("AAV VECTOR DESIGN SPECIFICATION")
print("="*80)
print()

# Vector Components
print("VECTOR COMPONENTS:")
print("-"*80)
print(f"Serotype: {design['serotype']}")
print(f"Promoter: {design['components']['promoter']}")
print(f"Cas9: {design['components']['cas9']}")
print(f"gRNA Scaffold: {design['components']['grna_scaffold']}")
print(f"PolyA Signal: {design['components']['polya']}")
print(f"ITRs: {design['components']['itr']}")
print()

# Size Calculation
print("PACKAGING:")
print("-"*80)
print(f"Estimated Size: {design['estimated_size']}")
print(f"Packaging Capacity: {design['packaging_capacity']}")
print()

# Clinical Considerations
print("CLINICAL PARAMETERS:")
print("-"*80)
print(f"Route: {design['clinical_considerations']['route']}")
print(f"Dose: {design['clinical_considerations']['dosing']}")
print(f"Immunogenicity: {design['clinical_considerations']['immunogenicity']}")
print(f"Pre-existing Immunity: {design['clinical_considerations']['pre_existing_immunity']}")
print()

# Manufacturing
print("MANUFACTURING:")
print("-"*80)
print(f"Cell Line: {design['clinical_considerations']['manufacturing']}")
print("Production: Triple plasmid transfection")
print("Purification: Iodixanol gradient ultracentrifugation")
print("QC: qPCR titration, purity, sterility, endotoxin")
print()

# Regulatory Path
print("REGULATORY PATH:")
print("-"*80)
print("Preclinical Studies:")
for study in design['regulatory_path']['preclinical']:
    print(f"  ✅ {study}")
print()
print("Clinical Development:")
for phase in design['regulatory_path']['clinical']:
    print(f"  ✅ {phase}")
print()
print(f"Approval: {design['regulatory_path']['approval']}")
print()

print("="*80)
print("🎯 AAV vector design complete!")
print("📋 Next: CMC development and IND filing")
print("="*80)
'''

    else:  # LNP
        design = designer.design_lnp_formulation(target_tissue)

        template = f'''#!/usr/bin/env python3
"""
LNP Formulation for CRISPR Therapy
===================================

Target Tissue: {target_tissue}
Disease: {disease}

LNP Type: {design['lnp_type']}
Payload: {design['payload']}
"""

print("="*80)
print("LNP FORMULATION SPECIFICATION")
print("="*80)
print()

# Formulation Components
print("FORMULATION COMPONENTS:")
print("-"*80)
print(f"Ionizable Lipid: {design['components']['ionizable_lipid']}")
print(f"Helper Lipid: {design['components']['helper_lipid']}")
print(f"Cholesterol: {design['components']['cholesterol']}")
print(f"PEG-Lipid: {design['components']['peg_lipid']}")
print(f"Molar Ratio: {design['molar_ratio']}")
print()

# Physical Properties
print("PHYSICAL PROPERTIES:")
print("-"*80)
print(f"Particle Size: {design['particle_size']}")
print(f"Encapsulation Method: {design['encapsulation']['method']}")
print(f"Encapsulation Efficiency: {design['encapsulation']['efficiency']}")
print(f"N/P Ratio: {design['encapsulation']['n_p_ratio']}")
print()

# Formulation Buffer
print("FORMULATION BUFFER:")
print("-"*80)
print(f"Mixing Buffer: {design['formulation_buffer']['buffer']}")
print(f"Mixing pH: {design['formulation_buffer']['ph']}")
print(f"Final pH: {design['formulation_buffer']['final_ph']}")
print(f"Excipients: {', '.join(design['formulation_buffer']['excipients'])}")
print()

# Dosing
print("DOSING:")
print("-"*80)
print(f"Payload Amount: {design['dosing']['payload_amount']}")
print(f"Route: {design['dosing']['administration']}")
print(f"Frequency: {design['dosing']['frequency']}")
print()

# Storage
print("STORAGE & STABILITY:")
print("-"*80)
print(f"Temperature: {design['storage']['temperature']}")
print(f"Stability: {design['storage']['stability']}")
print(f"Thawing: {design['storage']['thawing']}")
print()

# Manufacturing
print("MANUFACTURING PROCESS:")
print("-"*80)
for step, method in design['manufacturing'].items():
    print(f"  {step}: {method}")
print()

print("="*80)
print("🎯 LNP formulation design complete!")
print("📋 Next: GMP manufacturing and stability studies")
print("="*80)
'''

    return template


if __name__ == "__main__":
    # Test delivery system design
    designer = DeliverySystemDesigner()

    print("="*80)
    print("CRISPR Delivery Systems - Tests")
    print("="*80)
    print()

    # Test 1: AAV design
    print("Test 1: AAV Vector for PCSK9 (Liver)")
    print("-"*80)
    aav_design = designer.design_aav_vector("PCSK9", "Liver", "SpCas9")
    print(f"Serotype: {aav_design['serotype']}")
    print(f"Promoter: {aav_design['components']['promoter']}")
    print(f"Size: {aav_design['estimated_size']}")
    print(f"Route: {aav_design['clinical_considerations']['route']}")
    print()

    # Test 2: LNP design
    print("Test 2: LNP Formulation for Muscle")
    print("-"*80)
    lnp_design = designer.design_lnp_formulation("Muscle", "Cas9_mRNA")
    print(f"LNP Type: {lnp_design['lnp_type']}")
    print(f"Components: {lnp_design['components']['ionizable_lipid']}")
    print(f"Particle Size: {lnp_design['particle_size']}")
    print(f"Route: {lnp_design['dosing']['administration']}")
