# BioQL 5.7.0 Release Notes

**Release Date:** October 13, 2025

## 🎉 Major Update: Complete ADME/Tox/Drug-Likeness Integration

This release fixes critical issues with bio_interpretation data completeness and updates the VSCode extension to generate correct code for BioQL 5.7.0.

---

## ✅ Fixed

### Bio-Interpretation Data Completeness (CRITICAL FIX)

Previously, many fields in `result.bio_interpretation` were showing as "N/A". This release adds **comprehensive drug discovery data**:

#### Drug-Likeness Scores
- ✅ **QED Score** (Quantitative Estimate of Drug-likeness): 0.0-1.0 scale
- ✅ **SA Score** (Synthetic Accessibility): 1.0-10.0 scale (lower = easier to synthesize)
- ✅ **Lipinski Rule of 5** violations count (0-4)

#### ADME Predictions
- ✅ **Oral Bioavailability**: High/Medium/Low prediction
- ✅ **BBB Permeability**: Blood-brain barrier crossing prediction
- ✅ **P-gp Substrate**: P-glycoprotein substrate prediction
- ✅ **TPSA**: Topological Polar Surface Area
- ✅ **Rotatable Bonds**: Molecular flexibility metric

#### Toxicity Predictions
- ✅ **Toxicity Class**: Low Risk / Medium Risk / High Risk
- ✅ **Ames Test**: Mutagenicity prediction (Positive/Negative)
- ✅ **Hepatotoxicity**: Liver toxicity risk (Low/Medium/High)
- ✅ **Cardiotoxicity**: Heart toxicity risk (Low/Medium/High)

#### Molecular Interactions
- ✅ **H-bonds**: Estimated hydrogen bond count
- ✅ **Hydrophobic Contacts**: Strength prediction (Strong/Moderate/Weak/Minimal)
- ✅ **π-Stacking**: Aromatic interaction likelihood (Likely/Possible/Unlikely)
- ✅ **Salt Bridges**: Ionic interaction likelihood (Likely/Possible/Unlikely)

---

## 🔧 Changed

### VSCode Extension v4.13.0

**Updated Code Generation:**
- ✅ Modal server (`modal_serve_vscode.py`) updated to BioQL 5.7.0 API
- ✅ De novo drug design template shows all new fields
- ✅ Molecular docking template displays comprehensive data
- ✅ Model prompt updated from "BioQL 5.4.1" → "BioQL 5.7.0"
- ✅ Generated code correctly accesses `bio = result.bio_interpretation`

**Installation:**
```bash
# Install updated extension in Cursor/VSCode
code --install-extension bioql-assistant-4.13.0.vsix
```

---

## 📊 API Changes

### Before (5.6.2)
```python
result = quantum("Design drug for cancer", backend='ibm_torino', api_key=key)

# Many fields were N/A
if hasattr(result, 'binding_affinity'):
    print(result.binding_affinity)  # Worked
if hasattr(result, 'qed_score'):
    print(result.qed_score)  # N/A - didn't work
```

### After (5.7.0)
```python
result = quantum("Design drug for cancer", backend='ibm_torino', api_key=key)

# Access comprehensive data via bio_interpretation
bio = result.bio_interpretation

# All fields populated
print(f"Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
print(f"QED Score: {bio['qed_score']:.2f}")
print(f"SA Score: {bio['sa_score']:.1f}/10")
print(f"Oral Bioavailability: {bio['oral_bioavailability']}")
print(f"Toxicity Class: {bio['toxicity_class']}")
print(f"H-bonds: {bio['h_bonds']}")
print(f"Lipinski Pass: {bio['lipinski_pass']}")
```

---

## 🧪 Testing Results

**Test Script:** `/Users/heinzjungbluth/Desktop/quick_test_fields.py`

```
Testing 24 fields:

  ✅ designed_molecule              = c1ccc2c(c1)c(cc(n2)c3ccccc3)c4ccccc4
  ✅ molecule_name                  = BioQL-DRUG-005
  ✅ binding_affinity               = -5.064405833938427
  ✅ qed_score                      = 0.46789105751559995
  ✅ sa_score                       = 1.0
  ✅ molecular_weight               = 281.358
  ✅ logP                           = 5.568800000000004
  ✅ h_bond_donors                  = 0
  ✅ h_bond_acceptors               = 1
  ✅ tpsa                           = 12.89
  ✅ rotatable_bonds                = 2
  ✅ oral_bioavailability           = Medium
  ✅ bbb_permeability               = High
  ✅ pgp_substrate                  = No
  ✅ toxicity_class                 = High Risk
  ✅ ames_test                      = Negative
  ✅ hepatotoxicity                 = High
  ✅ cardiotoxicity                 = Medium
  ✅ h_bonds                        = ~0
  ✅ hydrophobic_contacts           = Strong
  ✅ pi_stacking                    = Likely
  ✅ salt_bridges                   = Possible
  ✅ lipinski_pass                  = False
  ✅ lipinski_violations            = 1

✅ ALL FIELDS POPULATED SUCCESSFULLY!
```

---

## 📦 Installation

```bash
# Upgrade to 5.7.0
pip install --upgrade bioql

# Verify version
python -c "import bioql; print(bioql.__version__)"
# Output: 5.7.0

# Test comprehensive fields
python -c "
from bioql import quantum
result = quantum('Design drug for cancer', backend='simulator', api_key='test')
bio = result.bio_interpretation
print(f'QED: {bio.get(\"qed_score\", \"N/A\")}')
print(f'Toxicity: {bio.get(\"toxicity_class\", \"N/A\")}')
"
```

---

## 🔬 Technical Details

### Files Modified

**BioQL Framework:**
- `bioql/bio_interpreter.py` (lines 245-400): Added comprehensive property calculations

**VSCode Extension:**
- `modal_serve_vscode.py`: Updated code generation templates
- `package.json`: Version 4.13.0

### Dependencies

No new dependencies required. All calculations use existing libraries:
- RDKit (for QED and molecular properties)
- NumPy (for calculations)
- Rules-based logic (for toxicity predictions)

---

## 🚀 What's Next

**Version 5.8.0 (Planned):**
- Integration with external ADME prediction APIs
- Machine learning-based toxicity models
- Expanded interaction prediction with docking pose analysis
- Real-time visualization of molecular properties

---

## 📞 Support

- **Documentation**: https://docs.bioql.com
- **Issues**: https://github.com/bioql/bioql/issues
- **PyPI**: https://pypi.org/project/bioql/5.7.0/

---

## 🙏 Contributors

This release was developed by the BioQL team at SpectrixRD with assistance from Claude Code.

**Happy Drug Discovery! 🧬🔬**
