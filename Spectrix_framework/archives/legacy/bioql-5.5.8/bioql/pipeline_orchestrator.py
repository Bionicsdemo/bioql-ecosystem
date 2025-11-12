"""BioQL Pipeline Orchestrator - Complete end-to-end drug discovery pipeline"""
from typing import Dict, Any
import json
from pathlib import Path
from datetime import datetime

def run_complete_pipeline(
    smiles: str,
    target_name: str,
    pdb_id: str,
    disease: str,
    backend: str = 'simulator',
    shots: int = 2000
) -> Dict[str, Any]:
    """
    Execute complete drug discovery pipeline:
    1. Structural validation
    2. Chemical properties
    3. Primary target docking
    4. ADME/Tox prediction
    5. Off-target screening
    6. Resistance analysis
    7. Competitive benchmarking
    8. Final report generation
    """
    print("="*80)
    print("🚀 BioQL COMPLETE DRUG DISCOVERY PIPELINE")
    print("="*80)
    print(f"Molecule: {smiles}")
    print(f"Target: {target_name} ({pdb_id})")
    print(f"Disease: {disease}")
    print(f"Quantum Backend: {backend}")
    print(f"Shots: {shots}")
    print("="*80)
    
    pipeline_results = {
        'metadata': {
            'smiles': smiles,
            'target': target_name,
            'pdb_id': pdb_id,
            'disease': disease,
            'timestamp': datetime.now().isoformat(),
            'bioql_version': '5.6.0'
        },
        'steps': {}
    }
    
    # === STEP 1: STRUCTURAL VALIDATION ===
    print("\n" + "="*80)
    print("STEP 1/9: STRUCTURAL VALIDATION")
    print("="*80)
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError("Invalid SMILES")
        
        validation = {
            'valid': True,
            'canonical_smiles': Chem.MolToSmiles(mol),
            'inchi': Chem.MolToInchi(mol),
            'inchikey': Chem.MolToInchiKey(mol),
            'num_atoms': mol.GetNumAtoms(),
            'num_heavy_atoms': mol.GetNumHeavyAtoms(),
            'stereocenters': len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
        }
        print(f"✅ SMILES valid")
        print(f"   InChIKey: {validation['inchikey']}")
        print(f"   Atoms: {validation['num_atoms']} (heavy: {validation['num_heavy_atoms']})")
        print(f"   Stereocenters: {validation['stereocenters']}")
    except Exception as e:
        validation = {'valid': False, 'error': str(e)}
        print(f"❌ Validation failed: {e}")
        return pipeline_results
    
    pipeline_results['steps']['1_validation'] = validation
    
    # === STEP 2: CHEMICAL PROPERTIES ===
    print("\n" + "="*80)
    print("STEP 2/9: CHEMICAL PROPERTIES & DRUGLIKENESS")
    print("="*80)
    try:
        from bioql.chem.pharma_scores import calculate_pharmaceutical_scores
        chem_props = calculate_pharmaceutical_scores(smiles)
        print(f"✅ Lipinski: {'PASS' if chem_props.get('lipinski_compliant') else 'FAIL'}")
        print(f"   QED: {chem_props.get('qed_score', 0):.3f}")
        print(f"   SA Score: {chem_props.get('sa_score', 0):.2f}")
        print(f"   PAINS: {chem_props.get('pains_alerts', 0)}")
    except Exception as e:
        chem_props = {'error': str(e)}
        print(f"⚠️  Error: {e}")
    
    pipeline_results['steps']['2_chemical_properties'] = chem_props
    
    # === STEP 3: PRIMARY TARGET DOCKING ===
    print("\n" + "="*80)
    print("STEP 3/9: PRIMARY TARGET DOCKING (QUANTUM)")
    print("="*80)
    try:
        from bioql import quantum
        import os
        api_key = os.getenv('BIOQL_API_KEY', 'demo_key')
        
        result = quantum(
            f"Analyze ligand with SMILES {smiles} docking to receptor PDB {pdb_id}. Calculate binding affinity, Ki, and key interactions.",
            backend=backend,
            shots=shots,
            api_key=api_key
        )
        
        docking = {
            'success': result.success,
            'binding_affinity_kcal_mol': getattr(result, 'binding_affinity', None),
            'ki_nm': getattr(result, 'ki', None),
            'ic50_nm': getattr(result, 'ic50', None),
        }
        print(f"✅ Docking complete")
        if docking['binding_affinity_kcal_mol']:
            print(f"   Binding Affinity: {docking['binding_affinity_kcal_mol']:.2f} kcal/mol")
            print(f"   Ki: {docking['ki_nm']:.2f} nM")
    except Exception as e:
        docking = {'error': str(e)}
        print(f"❌ Docking failed: {e}")
    
    pipeline_results['steps']['3_primary_docking'] = docking
    
    # === STEP 4: ADME/TOX PREDICTION ===
    print("\n" + "="*80)
    print("STEP 4/9: ADME/TOXICITY PREDICTION")
    print("="*80)
    try:
        from bioql.adme_predictor import predict_adme_toxicity
        adme_tox = predict_adme_toxicity(smiles, use_web_services=False)
        print(f"✅ ADME/Tox predicted")
        print(f"   Oral bioavailability: {adme_tox['adme']['bioavailability']['oral_bioavailability_percent']:.1f}%")
        print(f"   hERG risk: {adme_tox['toxicity']['cardiotoxicity']['qt_prolongation_risk']}")
        print(f"   Ames: {'Positive' if adme_tox['toxicity']['mutagenicity']['ames_mutagenic'] else 'Negative'}")
    except Exception as e:
        adme_tox = {'error': str(e)}
        print(f"⚠️  Error: {e}")
    
    pipeline_results['steps']['4_adme_toxicity'] = adme_tox
    
    # === STEP 5: OFF-TARGET SCREENING ===
    print("\n" + "="*80)
    print("STEP 5/9: OFF-TARGET SCREENING (Top 10)")
    print("="*80)
    try:
        from bioql.offtarget_panel import screen_offtargets
        offtargets = screen_offtargets(smiles)
        print(f"✅ Screened {offtargets['targets_screened']} off-targets")
        print(f"   High risk: {len(offtargets.get('high_risk', []))}")
    except Exception as e:
        offtargets = {'error': str(e)}
        print(f"⚠️  Error: {e}")
    
    pipeline_results['steps']['5_offtarget_screening'] = offtargets
    
    # === STEP 6: RESISTANCE ANALYSIS ===
    print("\n" + "="*80)
    print("STEP 6/9: RESISTANCE PROFILING")
    print("="*80)
    try:
        from bioql.resistance_profiler import analyze_resistance_profile
        resistance = analyze_resistance_profile(smiles, target_name, pdb_id)
        print(f"✅ Tested {resistance['mutations_tested']} known mutations")
        print(f"   Resistance risk: {resistance['resistance_risk']}")
    except Exception as e:
        resistance = {'error': str(e)}
        print(f"⚠️  Error: {e}")
    
    pipeline_results['steps']['6_resistance_analysis'] = resistance
    
    # === STEP 7: SIMILARITY SEARCH ===
    print("\n" + "="*80)
    print("STEP 7/9: SIMILARITY SEARCH (ChEMBL/PubChem)")
    print("="*80)
    try:
        from bioql.similarity_search import similarity_search_pipeline
        similarity = similarity_search_pipeline(smiles, min_similarity=0.7)
        print(f"✅ Found {similarity['total_hits']} similar molecules")
    except Exception as e:
        similarity = {'error': str(e)}
        print(f"⚠️  Error: {e}")
    
    pipeline_results['steps']['7_similarity_search'] = similarity
    
    # === STEP 8: COMPETITIVE BENCHMARKING ===
    print("\n" + "="*80)
    print("STEP 8/9: COMPETITIVE BENCHMARKING")
    print("="*80)
    print("⚠️  Manual comparison with approved drugs recommended")
    pipeline_results['steps']['8_benchmarking'] = {'status': 'manual'}
    
    # === STEP 9: FINAL ASSESSMENT ===
    print("\n" + "="*80)
    print("STEP 9/9: FINAL ASSESSMENT & REPORT")
    print("="*80)
    
    # Calculate overall score
    score = 0
    max_score = 7
    
    if validation.get('valid'): score += 1
    if chem_props.get('lipinski_compliant'): score += 1
    if docking.get('binding_affinity_kcal_mol', 0) < -7: score += 1
    if adme_tox.get('adme', {}).get('bioavailability', {}).get('oral_bioavailability_percent', 0) > 30: score += 1
    if not adme_tox.get('toxicity', {}).get('mutagenicity', {}).get('ames_mutagenic', True): score += 1
    if adme_tox.get('toxicity', {}).get('cardiotoxicity', {}).get('qt_prolongation_risk', 'High') != 'High': score += 1
    if resistance.get('resistance_risk') == 'Low': score += 1
    
    assessment = {
        'overall_score': f"{score}/{max_score}",
        'percentage': int((score/max_score)*100),
        'verdict': 'Excellent' if score >= 6 else 'Good' if score >= 4 else 'Moderate' if score >= 2 else 'Poor',
        'recommendation': 'Proceed to in vitro testing' if score >= 5 else 'Optimize further' if score >= 3 else 'Major redesign needed'
    }
    
    pipeline_results['steps']['9_final_assessment'] = assessment
    
    print(f"\n{'='*80}")
    print(f"📊 FINAL ASSESSMENT: {assessment['verdict'].upper()}")
    print(f"{'='*80}")
    print(f"Overall Score: {assessment['overall_score']} ({assessment['percentage']}%)")
    print(f"Recommendation: {assessment['recommendation']}")
    
    # Save report
    report_dir = Path("bioql_pipeline_reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"pipeline_{target_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_path, 'w') as f:
        json.dump(pipeline_results, f, indent=2, default=str)
    
    print(f"\n💾 Full report saved: {report_path}")
    
    return pipeline_results
