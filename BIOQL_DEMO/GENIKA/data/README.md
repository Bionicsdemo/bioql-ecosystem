# Sample Data for BioQL Demos

This directory contains synthetic sample data for demonstrating BioQL capabilities to Genika Multiomics.

**⚠️ IMPORTANT:** All data in this directory is **synthetic/simulated** and does not represent real patient information.

---

## Files Included

### 1. `sample_proteomics.csv`

**Description:** Protein expression data from simulated Type 2 Diabetes patient

**Format:** CSV (Comma-Separated Values)

**Columns:**
- `protein_id`: UniProt identifier
- `gene_name`: Gene symbol
- `protein_name`: Full protein name
- `expression_level`: Normalized expression (log2 fold change)
- `p_value`: Statistical significance
- `ptm_sites`: Post-translational modification sites
- `confidence`: Confidence score (0-1)

**Size:** ~100 proteins

**Example:**
```csv
protein_id,gene_name,protein_name,expression_level,p_value,ptm_sites,confidence
P35568,IRS1,Insulin receptor substrate 1,2.34,0.001,"Y612;Y632;S307",0.95
P04150,GCG,Glucagon,1.87,0.003,"S61",0.92
```

### 2. `sample_metabolomics.mzML`

**Description:** MS/MS spectrum data from patient plasma sample

**Format:** mzML (Mass Spectrometry Markup Language)

**Contents:**
- Precursor m/z values
- Fragment ion m/z and intensities
- Collision energies
- Scan metadata

**Metabolites Expected:**
- Glucose metabolites
- Amino acids
- Lipids
- Organic acids

**Size:** ~50 MS/MS spectra

**Tool to view:** MSConvert, Skyline, or pyteomics

### 3. `sample_variants.vcf`

**Description:** Genomic variants from simulated diabetes patient

**Format:** VCF (Variant Call Format)

**Variants Included:**
- TCF7L2 rs7903146 (Type 2 Diabetes risk)
- PPARG rs1801282 (Diabetes protective)
- FTO rs9939609 (Obesity-related diabetes)
- Additional SNPs in metabolic genes

**Size:** ~20 variants

**Example:**
```vcf
#CHROM  POS         ID          REF  ALT  QUAL  FILTER  INFO
10      114758349   rs7903146   C    T    100   PASS    AF=0.42;GENE=TCF7L2
3       12393125    rs1801282   C    G    100   PASS    AF=0.50;GENE=PPARG
```

### 4. `sample_clinical_data.json`

**Description:** Clinical metadata for simulated patient

**Format:** JSON

**Fields:**
- patient_id
- age, gender, BMI
- diagnosis
- lab_values (glucose, HbA1c, lipids)
- medications
- family_history

**Example:**
```json
{
  "patient_id": "GENIKA-PT-2025-001",
  "age": 54,
  "gender": "female",
  "bmi": 31.2,
  "diagnosis": "Type 2 Diabetes Mellitus",
  "lab_values": {
    "fasting_glucose_mgdl": 156,
    "hba1c_percent": 7.8,
    "total_cholesterol_mgdl": 245
  }
}
```

---

## Data Generation

All sample data was generated using:

1. **Proteomics:** Simulated using biological pathway models
2. **Metabolomics:** Generated MS/MS spectra using MSsim
3. **Genomics:** Real variant IDs with simulated allele frequencies
4. **Clinical:** Synthetic patient profiles based on population statistics

**No real patient data was used.**

---

## Usage in Demos

### Demo 1: Multi-Omics Integration

Uses:
- `sample_proteomics.csv` → ProteomicsAnalysisCircuit
- `sample_metabolomics.mzML` → MetabolomicsCircuit
- `sample_variants.vcf` → Genomic context
- `sample_clinical_data.json` → Clinical metadata

### Demo 2: Drug Discovery Pipeline

Uses:
- `sample_clinical_data.json` → Patient profile
- Simulated EGFR L858R mutation data
- Synthetic drug candidate SMILES strings
- Simulated binding affinity data

---

## Creating Your Own Sample Data

To test BioQL with your own data:

### Proteomics Data

**Required format:** CSV with columns:
```
protein_id,gene_name,expression_level,p_value
```

**Example preparation:**
```python
import pandas as pd

# Load your proteomics data
df = pd.read_excel('your_proteomics.xlsx')

# Rename columns to match BioQL format
df_bioql = df.rename(columns={
    'Protein': 'protein_id',
    'Gene': 'gene_name',
    'Log2FC': 'expression_level',
    'P.Value': 'p_value'
})

# Save
df_bioql.to_csv('my_proteomics.csv', index=False)
```

### Metabolomics Data

**Required format:** mzML or MSP

**Conversion:**
```bash
# Convert from vendor format using MSConvert
msconvert your_data.raw --mzML --filter "peakPicking true 1-"
```

### Genomics Data

**Required format:** Standard VCF

**Your VCF should have:**
- CHROM, POS, ID, REF, ALT columns
- INFO field with gene annotations
- Properly formatted genotypes

---

## Data Quality Checks

Before running demos, verify:

### Proteomics
- ✓ No missing values in required columns
- ✓ Expression values are numeric
- ✓ P-values between 0 and 1
- ✓ Protein IDs are valid (UniProt format)

### Metabolomics
- ✓ mzML validates against schema
- ✓ MS/MS spectra present (not just MS1)
- ✓ Precursor m/z values reasonable (50-2000)
- ✓ Fragment ions present for each spectrum

### Genomics
- ✓ VCF passes validation (vcftools --vcf file.vcf)
- ✓ Chromosome names match reference (chr1 vs 1)
- ✓ Positions are valid for genome build
- ✓ Gene annotations present in INFO field

---

## Example: Loading Sample Data in Python

```python
# Proteomics
import pandas as pd
proteomics = pd.read_csv('data/sample_proteomics.csv')
print(f"Loaded {len(proteomics)} proteins")

# Metabolomics
from pyteomics import mzml
spectra = mzml.read('data/sample_metabolomics.mzML')
print(f"Loaded {len(list(spectra))} MS/MS spectra")

# Genomics
import vcf
vcf_reader = vcf.Reader(filename='data/sample_variants.vcf')
variants = list(vcf_reader)
print(f"Loaded {len(variants)} variants")

# Clinical
import json
with open('data/sample_clinical_data.json') as f:
    clinical = json.load(f)
print(f"Patient: {clinical['patient_id']}")
```

---

## Data Privacy & Security

**For Genika Real Data:**

When using actual patient data with BioQL:

1. **De-identification:** Remove all PHI (Personal Health Information)
2. **Encryption:** Use AES-256 encryption at rest
3. **Access Control:** RBAC with MFA
4. **Audit Logs:** Complete audit trail
5. **Compliance:** LGPD, HIPAA, GDPR compliant

**BioQL Security Features:**
- ✅ Data never leaves your infrastructure (on-premise option)
- ✅ Quantum computations don't expose raw data
- ✅ Results encrypted in transit (TLS 1.3)
- ✅ SOC 2 Type II certified
- ✅ BAA available for HIPAA compliance

---

## Support

For help with data preparation:
- 📧 support@bioql.bio
- 📖 https://docs.bioql.bio/data-preparation
- 💬 Slack: #data-preparation channel

---

## Additional Resources

### Data Format Specifications

- **VCF:** https://samtools.github.io/hts-specs/VCFv4.3.pdf
- **mzML:** http://www.psidev.info/mzml
- **CSV:** Standard comma-separated values

### Validation Tools

- **VCF:** vcftools, bcftools
- **mzML:** msconvert, ProteoWizard
- **Proteomics:** Perseus, MaxQuant

### Sample Datasets (Public)

- **Proteomics:** ProteomeXchange (PXD datasets)
- **Metabolomics:** MetaboLights
- **Genomics:** 1000 Genomes, gnomAD

---

**Questions?** Contact support@bioql.bio

---

*Data is the foundation of precision medicine* 📊
