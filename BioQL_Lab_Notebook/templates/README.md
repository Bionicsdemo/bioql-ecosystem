# BioQL Lab Notebook - Experiment Templates

This directory contains pre-built, copy-paste ready experiment templates for computational biology and drug discovery workflows.

## Available Templates

### 1. **virtual_screening.json**
**Category:** Drug Discovery  
**Difficulty:** Intermediate  
**Runtime:** 2-4 hours  
**Cost:** $15-30  

Screen 1000+ molecules against a protein target using molecular docking and ML-based scoring. Includes:
- Target protein preparation
- Compound library loading and filtering
- Molecular docking (AutoDock Vina, GNINA)
- Consensus scoring and ML re-ranking
- Hit selection with diversity filtering
- Interaction analysis
- Comprehensive reporting

**Use Case:** Identify potential hit compounds from large chemical libraries

---

### 2. **lead_optimization.json**
**Category:** Drug Discovery  
**Difficulty:** Advanced  
**Runtime:** 4-8 hours per iteration  
**Cost:** $30-60 per cycle  

Iterative improvement of lead compounds through systematic structural modifications. Includes:
- Baseline profiling of current lead
- SAR analysis and binding mode analysis
- Liability identification
- Focused analog generation
- Multi-parameter optimization (potency, selectivity, ADME)
- Synthetic route planning
- Iterative design-make-test cycles

**Use Case:** Optimize confirmed hits to meet target product profile

---

### 3. **adme_profiling.json**
**Category:** ADME/Tox  
**Difficulty:** Intermediate  
**Runtime:** 1-2 hours  
**Cost:** $10-25 per compound  

Complete ADME/Tox analysis pipeline predicting pharmaceutical properties. Includes:
- Physicochemical property calculation
- Drug-likeness evaluation (Lipinski, Veber, etc.)
- Absorption predictions (Caco-2, solubility, bioavailability)
- Distribution predictions (PPB, VDss, BBB penetration)
- Metabolism profiling (CYP interactions, metabolite prediction)
- Excretion and PK parameter prediction
- Comprehensive toxicity screening (hERG, Ames, hepatotox)
- Species scaling and translation

**Use Case:** Evaluate drug-like properties and safety profile of candidates

---

### 4. **protein_docking.json**
**Category:** Structural Biology  
**Difficulty:** Advanced  
**Runtime:** 3-6 hours  
**Cost:** $20-40 per complex  

Computational prediction of protein-protein interaction complexes. Includes:
- Structure preparation and validation
- Interface prediction from experimental data
- Rigid-body docking (ZDOCK, ClusPro)
- AlphaFold-Multimer predictions
- Refinement with flexible side-chains
- Binding affinity prediction
- Hot spot identification
- Molecular dynamics validation
- In silico mutagenesis for protein engineering

**Use Case:** Predict protein-protein binding modes and guide antibody design

---

### 5. **crispr_design.json**
**Category:** Genome Engineering  
**Difficulty:** Intermediate  
**Runtime:** 30-60 minutes  
**Cost:** $5-15 per target  

CRISPR/Cas9 guide RNA design with comprehensive off-target analysis. Includes:
- Target site identification in gene
- Guide RNA scoring (Doench 2016, DeepHF, Azimuth)
- Genome-wide off-target analysis
- Sequence feature checking (SNPs, homopolymers)
- Multi-parameter ranking
- Oligonucleotide design for cloning
- Validation primer design
- Editing outcome prediction (inDelphi)
- HDR template design
- Delivery strategy recommendations
- Complete experimental protocols

**Use Case:** Design highly specific and efficient CRISPR guides for gene editing

---

### 6. **denovo_generation.json**
**Category:** Drug Discovery  
**Difficulty:** Advanced  
**Runtime:** 4-8 hours  
**Cost:** $40-80 per campaign  

Generate novel drug-like molecules from scratch using generative AI. Includes:
- Known inhibitor analysis
- Multiple generative model training (MolGPT, MoFlow, DiffSBDD, Reinvent)
- Large-scale molecule generation (100K+ candidates)
- Multi-stage filtering (drug-likeness, novelty)
- Docking and activity prediction
- ADME/Tox profiling
- Selectivity prediction
- Synthetic accessibility analysis
- Diversity selection
- In silico validation (MD, FEP)
- Synthesis protocol generation

**Use Case:** Design completely novel compounds optimized for target and drug-like properties

---

### 7. **qsar_modeling.json**
**Category:** Computational Chemistry  
**Difficulty:** Advanced  
**Runtime:** 2-4 hours  
**Cost:** $15-35 per model  

Build QSAR models using quantum descriptors and machine learning. Includes:
- Dataset loading and curation
- Classical descriptor calculation (1800+ descriptors)
- Quantum chemical descriptor calculation (DFT, 127 descriptors)
- Feature selection (multiple methods)
- Training ensemble of ML models (RF, XGBoost, GNN, etc.)
- Rigorous validation (CV, test set, Y-randomization)
- Applicability domain definition
- Model interpretation (SHAP, PDPs)
- Prospective predictions with confidence
- OECD-compliant reporting

**Use Case:** Predict biological activity from structure and understand SAR drivers

---

## Template Structure

Each template includes:

### Metadata
- Title and description
- Category and difficulty level
- Estimated runtime and cost
- Tags for searchability
- Version and creation date

### Content Cells
1. **Markdown cells**: Scientific background, instructions in English, expected outcomes
2. **Code cells**: Pre-filled @bioql commands ready to customize
3. **Structured workflow**: Step-by-step progression
4. **Quality checkpoints**: Validation at each stage
5. **Next steps**: Follow-up experiments and analyses

### Scientific Rigor
- Detailed methodology explanations
- Expected results and interpretation guidelines
- Quality control checks
- Troubleshooting tips
- Literature references

## How to Use Templates

### Option 1: Direct Copy
1. Open template JSON file
2. Copy all cells
3. Paste into new BioQL notebook
4. Customize parameters (marked with **Customize:**)
5. Execute cells sequentially

### Option 2: Import via BioQL
```python
@bioql load_template virtual_screening
```

### Option 3: Modify and Save
1. Load template
2. Adjust for your specific target/project
3. Save as new template
4. Reuse for similar experiments

## Customization Points

All templates have clearly marked customization points:

```markdown
**Customize**: Replace with your target PDB ID or upload custom structure.
```

Common parameters to adjust:
- Target protein/gene
- Input files and data sources
- Thresholds and cutoffs
- Number of compounds/iterations
- Computational resource allocation
- Output formats

## Best Practices

1. **Read through entire template** before starting
2. **Customize parameters** for your specific use case
3. **Validate early steps** before proceeding
4. **Save intermediate results** at checkpoints
5. **Document deviations** from template in markdown cells
6. **Export final reports** for records

## Template Quality Standards

All templates meet these criteria:
- ✓ Scientifically validated workflows
- ✓ Industry-standard methods
- ✓ Clear English instructions
- ✓ Expected outcomes described
- ✓ Cost and time estimates provided
- ✓ Copy-paste ready commands
- ✓ Comprehensive documentation
- ✓ References to literature

## Support and Contributions

### Getting Help
- Check template markdown cells for detailed instructions
- Review expected outputs for each step
- Consult scientific background sections
- Refer to cited literature

### Contributing New Templates
Templates are welcome for:
- Common experimental workflows
- Published computational methods
- Best-practice protocols
- Validated pipelines

Contact: bioql-support@example.com

## Version History

- **v1.0** (2025-10-25): Initial release
  - 7 core templates covering drug discovery and computational biology
  - Comprehensive documentation
  - OECD-compliant where applicable

## License

Templates are provided under MIT License for academic and commercial use.

## Citation

If you use these templates in published work, please cite:
```
BioQL Lab Notebook Templates (2025). Computational Drug Discovery Templates.
Version 1.0. https://github.com/bioql/templates
```

---

**Happy Experimenting!**

For questions, issues, or template requests, please open an issue on GitHub or contact support.
