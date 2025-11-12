"""
BioQL 5.0.9 - Complete Drug Discovery Templates
=================================================
100% QUANTUM computing platform for drug discovery.
All computations execute on REAL quantum hardware (IBM Quantum, IonQ, AWS Braket).

Uses VQE (Variational Quantum Eigensolver) for:
- Molecular docking and binding affinity calculations
- Conformational sampling from quantum states
- Energy calculations from quantum measurements

6 complete modules with all biochemical/pharmacological constants.

Author: BioQL Team
Version: 5.0.9
"""

# ==============================================================================
# MOLECULAR STRUCTURE DATABASES
# ==============================================================================

LIGAND_SMILES = {
    "metformin": "CN(C)C(=N)NC(=N)N",
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "ibuprofen": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "penicillin": "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O",
    "morphine": "CN1CCC23C4C1CC5=C2C(=C(C=C5)O)OC3C(C=C4)O",
    "warfarin": "CC(=O)CC(c1ccccc1)c1c(O)c2ccccc2oc1=O",
    "dopamine": "NCCc1ccc(O)c(O)c1",
    "serotonin": "NCCc1c[nH]c2ccc(O)cc12",
    "glucose": "OCC1OC(O)C(O)C(O)C1O",
    "atp": "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)OP(=O)(O)OP(=O)(O)O)C(O)C1O",
    "nad": "NC(=O)c1ccc[n+](c1)C1OC(COP(=O)(O)OP(=O)(O)OCC2OC(n3cnc4c(N)ncnc43)C(O)C2O)C(O)C1O",
    "paracetamol": "CC(=O)Nc1ccc(O)cc1",
    "viagra": "CCCC1=NN(C2=C1N=C(NC2=O)C3=C(C=CC(=C3)S(=O)(=O)N4CCN(CC4)C)OCC)C",
    "lipitor": "CC(C)c1c(C(=O)Nc2ccccc2)c(-c2ccccc2)c(-c2ccc(F)cc2)n1CC[C@@H](O)C[C@@H](O)CC(=O)O",
    "semaglutide": "CCCCCCCCCCCCCCCCCC(=O)N[C@@H](CO)C(=O)N[C@@H](CC(C)C)C(=O)N[C@@H](CC1=CC=CC=C1)C(=O)N[C@@H](CC(=O)O)C(=O)N[C@@H](CCC(=O)O)C(=O)N",
    "liraglutide": "CCCCCCCCCCCCCCCCC(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CO)C(=O)N[C@@H](CC(C)C)C(=O)N[C@@H](CC1=CC=CC=C1)C(=O)N",
    "ozempic": "CCCCCCCCCCCCCCCCCC(=O)N[C@@H](CO)C(=O)N[C@@H](CC(C)C)C(=O)N[C@@H](CC1=CC=CC=C1)C(=O)N[C@@H](CC(=O)O)C(=O)N[C@@H](CCC(=O)O)C(=O)N"
}

RECEPTOR_PDB = {
    "ampk": "2Y94",  # AMPK kinase domain
    "cox-1": "1EQG",  # Cyclooxygenase-1
    "cox-2": "5IKT",  # Cyclooxygenase-2
    "ace": "1O86",  # Angiotensin Converting Enzyme
    "thrombin": "1PPB",  # Thrombin
    "hiv-protease": "1HXB",  # HIV-1 Protease
    "egfr": "1M17",  # Epidermal Growth Factor Receptor
    "ace2": "6M0J",  # ACE2 (SARS-CoV-2 target)
    "spike": "6VXX",  # SARS-CoV-2 Spike protein
    "mtor": "4JSP",  # mTOR kinase
    "kinase": "1ATP",  # Generic kinase
    "protease": "1MTW",  # Generic protease
    "glp1r": "6B3J",  # GLP-1 Receptor (obesity/diabetes)
    "glp-1r": "6B3J",  # GLP-1 Receptor (alternative name)
    "gip": "7DTY",  # GIP Receptor (obesity/diabetes)
    "gipr": "7DTY",  # GIP Receptor (alternative name)
    "dpp4": "1X70",  # DPP-4 (diabetes)
    "sglt2": "5CGD"  # SGLT2 (diabetes)
}

# ==============================================================================
# TEMPLATE 1: MOLECULAR DOCKING
# ==============================================================================

DOCKING_TEMPLATE = '''from bioql import quantum
import os
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("=" * 80)
print("🧬 BioQL 5.0.9 - QUANTUM Molecular Docking")
print("⚛️  100% Quantum Computing Platform")
print("=" * 80)
print()
print("📊 CONFIGURATION:")
print(f"  Ligand: {ligand}")
print(f"  SMILES: {smiles}")
print(f"  Receptor: {receptor}")
print(f"  PDB ID: {pdb_id}")
print(f"  Quantum Backend: {backend}")
print(f"  Shots (measurements): {shots}")
print()
print("-" * 80)

try:
    # 100% QUANTUM DOCKING - VQE execution on REAL quantum hardware
    result = quantum(
        "Analyze ligand with SMILES {smiles} docking to receptor PDB {pdb_id}. "
        "Execute VQE on quantum hardware to calculate molecular Hamiltonian ground state. "
        "Calculate binding affinity in kcal/mol from quantum energy measurements. "
        "Sample conformational space using quantum state measurements. "
        "Identify key interactions from quantum state analysis: hydrogen bonds, hydrophobic contacts, pi-stacking. "
        "Calculate inhibition constant Ki from quantum binding energy. "
        "Return complete docking scores derived from quantum measurements.",
        backend='{backend}',
        shots={shots},
        api_key=api_key
    )

    print("\\n" + "=" * 80)
    print("✅ DOCKING COMPLETE!")
    print("=" * 80)
    print()

    # Quantum measurement results
    print("⚛️ QUANTUM STATES MEASURED:")
    for state, count in result.counts.items():
        print(f"  |{{state}}⟩: {{count}} counts ({{count}}/{shots}*100:.1f}%)")
    print()

    # Binding affinity and docking scores
    if hasattr(result, 'binding_affinity'):
        print("📊 DOCKING SCORES:")
        print(f"  Binding Affinity: {result.binding_affinity:.2f} kcal/mol")

        if hasattr(result, 'best_pose_score'):
            print(f"  Best Pose Score: {result.best_pose_score:.2f} kcal/mol")

        if hasattr(result, 'num_poses'):
            print(f"  Poses Explored: {result.num_poses:,} conformations")
        print()

    # Pharmacological parameters
    if hasattr(result, 'ki') or hasattr(result, 'ic50'):
        print("💊 PHARMACOLOGICAL PARAMETERS:")
        if hasattr(result, 'ki'):
            print(f"  Ki (Inhibition Constant): {result.ki:.2f} nM")
        if hasattr(result, 'ic50'):
            print(f"  IC50: {result.ic50:.2f} nM")
        if hasattr(result, 'kd'):
            print(f"  Kd (Dissociation Constant): {result.kd:.2f} nM")
        print()

    # Molecular interactions
    if hasattr(result, 'interactions'):
        print("🔗 KEY INTERACTIONS:")
        for interaction in result.interactions[:10]:
            print(f"  • {{interaction}}")
        print()

    # Interpretation
    print("📋 INTERPRETATION:")
    if hasattr(result, 'binding_affinity'):
        ba = result.binding_affinity
        if ba < -12:
            print("  ✓ Binding Strength: STRONG")
            print("  ✓ Activity: High affinity binding")
            print("  ✓ Drug Potential: HIGH")
        elif ba < -7.5:
            print("  ⚠ Binding Strength: MODERATE")
            print("  ⚠ Activity: Moderate affinity")
            print("  ⚠ Drug Potential: MEDIUM")
        else:
            print("  ✗ Binding Strength: WEAK")
            print("  ✗ Activity: Low affinity")
            print("  ✗ Drug Potential: LOW")
    print()

    # Visualization
    print("=" * 80)
    print("📊 Generating Visualizations...")
    print("=" * 80)

    viz_dir = Path("bioql_visualizations")
    viz_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Quantum states
    states = list(result.counts.keys())
    counts = list(result.counts.values())
    axes[0, 0].bar(range(len(states)), counts, color='purple', alpha=0.7)
    axes[0, 0].set_xticks(range(len(states)))
    axes[0, 0].set_xticklabels([f'|{{s}}⟩' for s in states], rotation=45)
    axes[0, 0].set_title('Quantum State Distribution')
    axes[0, 0].set_ylabel('Counts')

    # Plot 2: Binding affinity
    if hasattr(result, 'binding_affinity'):
        axes[0, 1].barh(['Binding\\nAffinity'], [abs(result.binding_affinity)], color='green', alpha=0.7)
        axes[0, 1].set_title(f'Binding Affinity: {result.binding_affinity:.2f} kcal/mol')
        axes[0, 1].set_xlabel('|ΔG| (kcal/mol)')

    # Plot 3: Pharmacological parameters
    if hasattr(result, 'ki'):
        ki_log = np.log10(result.ki) if result.ki > 0 else 0
        axes[1, 0].bar(['Ki (log nM)'], [ki_log], color='orange', alpha=0.7)
        axes[1, 0].set_title(f'Inhibition Constant: {result.ki:.2f} nM')
        axes[1, 0].set_ylabel('log₁₀(nM)')

    # Plot 4: Summary text
    summary = f"DOCKING SUMMARY\\n\\n"
    summary += f"Ligand: {ligand}\\n"
    summary += f"Receptor: {receptor}\\n"
    if hasattr(result, 'binding_affinity'):
        summary += f"ΔG: {result.binding_affinity:.2f} kcal/mol\\n"
    if hasattr(result, 'ki'):
        summary += f"Ki: {result.ki:.2f} nM\\n"
    if hasattr(result, 'num_poses'):
        summary += f"Poses: {result.num_poses}\\n"
    summary += f"Backend: {backend}\\n"
    summary += f"Shots: {shots}"

    axes[1, 1].text(0.1, 0.5, summary, fontsize=10, family='monospace',
                    verticalalignment='center')
    axes[1, 1].axis('off')

    plt.suptitle('BioQL Molecular Docking Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    viz_path = viz_dir / 'docking_{ligand}_{receptor}.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    print(f"\\n✅ Saved: {{viz_path}}")
    print(f"📁 Directory: {viz_dir.absolute()}")
    print()

except Exception as e:
    print(f"\\n❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''

# ==============================================================================
# TEMPLATE 2: BINDING AFFINITY
# ==============================================================================

BINDING_AFFINITY_TEMPLATE = '''from bioql import quantum
import os
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("=" * 80)
print("🧬 BioQL 5.0.1 - Binding Affinity Calculation")
print("=" * 80)
print()
print("📊 CONFIGURATION:")
print(f"  Ligand: {ligand}")
print(f"  SMILES: {smiles}")
print(f"  Receptor: {receptor}")
print(f"  PDB ID: {pdb_id}")
print(f"  Backend: {backend}")
print(f"  Shots: {shots}")
print()
print("-" * 80)

try:
    # VQE-based binding affinity calculation
    result = quantum(
        "Calculate binding affinity between ligand SMILES {smiles} and receptor PDB {pdb_id}. "
        "Use VQE to find ground state energy of the molecular complex Hamiltonian. "
        "Include Coulomb interactions, Van der Waals (Lennard-Jones), hydrogen bonds. "
        "Calculate Kd (dissociation constant) using ΔG = -RT ln(Kd) with R=0.001987 kcal/(mol·K) and T=298.15K. "
        "Calculate Ki (inhibition constant) and IC50. "
        "Determine ligand efficiency = ΔG / heavy_atom_count. "
        "Identify interaction types: H-bonds, hydrophobic, pi-stacking, electrostatic.",
        backend='{backend}',
        shots={shots},
        api_key=api_key
    )

    print("\\n" + "=" * 80)
    print("✅ BINDING AFFINITY CALCULATION COMPLETE!")
    print("=" * 80)
    print()

    # Results
    print("🧪 BINDING ENERGETICS:")
    if hasattr(result, 'binding_energy'):
        print(f"  Binding Energy (ΔG): {result.binding_energy:.2f} kcal/mol")

    if hasattr(result, 'vqe_energy'):
        print(f"  VQE Ground State: {result.vqe_energy:.6f} Hartree")

    if hasattr(result, 'binding_affinity_kd'):
        print(f"  Kd (Dissociation): {result.binding_affinity_kd:.2f} nM")
    print()

    print("💊 PHARMACOLOGICAL CONSTANTS:")
    if hasattr(result, 'ki'):
        print(f"  Ki (Inhibition): {result.ki:.2f} nM")
    if hasattr(result, 'ic50'):
        print(f"  IC50: {result.ic50:.2f} nM")
    if hasattr(result, 'ligand_efficiency'):
        print(f"  Ligand Efficiency: {result.ligand_efficiency:.3f}")
    print()

    print("🔗 INTERACTION TYPES:")
    if hasattr(result, 'interaction_types'):
        for itype in result.interaction_types:
            print(f"  • {itype.replace('_', ' ').title()}")
    print()

    # Interpretation
    print("📋 BINDING AFFINITY CLASSIFICATION:")
    if hasattr(result, 'binding_energy'):
        be = result.binding_energy
        if be < -12:
            print("  Category: STRONG BINDER")
            print(f"  Kd range: 0.01 - 10 nM")
        elif be < -7.5:
            print("  Category: MODERATE BINDER")
            print(f"  Kd range: 10 - 1000 nM")
        else:
            print("  Category: WEAK BINDER")
            print(f"  Kd range: > 1000 nM")
    print()

    # Visualization
    print("=" * 80)
    print("📊 Generating Visualizations...")
    print("=" * 80)

    viz_dir = Path("bioql_visualizations")
    viz_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Binding energy
    if hasattr(result, 'binding_energy'):
        categories = ['Strong\\n(-12 to -16)', 'Moderate\\n(-7.5 to -12)', 'Weak\\n(-3 to -7.5)']
        ranges = [(-16, -12), (-12, -7.5), (-7.5, -3)]
        colors = ['green', 'orange', 'red']

        be = result.binding_energy
        category_idx = 2 if be > -7.5 else (1 if be > -12 else 0)

        axes[0, 0].barh(categories, [4, 4.5, 4.5], color=['lightgray']*3, alpha=0.3)
        axes[0, 0].barh([categories[category_idx]], [abs(be)], color=colors[category_idx], alpha=0.7)
        axes[0, 0].set_xlabel('|ΔG| (kcal/mol)')
        axes[0, 0].set_title(f'Binding Energy: {be:.2f} kcal/mol')

    # Plot 2: Pharmacological constants
    if hasattr(result, 'ki') and hasattr(result, 'ic50'):
        params = ['Ki', 'IC50']
        values = [np.log10(result.ki), np.log10(result.ic50)]
        axes[0, 1].bar(params, values, color=['blue', 'purple'], alpha=0.7)
        axes[0, 1].set_ylabel('log₁₀(nM)')
        axes[0, 1].set_title('Pharmacological Parameters')

    # Plot 3: Interaction types
    if hasattr(result, 'interaction_types'):
        axes[1, 0].pie([1]*len(result.interaction_types), labels=result.interaction_types,
                       autopct='', startangle=90)
        axes[1, 0].set_title('Interaction Types')

    # Plot 4: Summary
    summary = f"BINDING AFFINITY SUMMARY\\n\\n"
    summary += f"Ligand: {ligand}\\n"
    summary += f"Receptor: {receptor}\\n\\n"
    if hasattr(result, 'binding_energy'):
        summary += f"ΔG: {result.binding_energy:.2f} kcal/mol\\n"
    if hasattr(result, 'binding_affinity_kd'):
        summary += f"Kd: {result.binding_affinity_kd:.2f} nM\\n"
    if hasattr(result, 'ki'):
        summary += f"Ki: {result.ki:.2f} nM\\n"
    if hasattr(result, 'ic50'):
        summary += f"IC50: {result.ic50:.2f} nM\\n"
    if hasattr(result, 'ligand_efficiency'):
        summary += f"LE: {result.ligand_efficiency:.3f}\\n"

    axes[1, 1].text(0.1, 0.5, summary, fontsize=10, family='monospace',
                    verticalalignment='center')
    axes[1, 1].axis('off')

    plt.suptitle('BioQL Binding Affinity Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    viz_path = viz_dir / 'binding_affinity_{ligand}_{receptor}.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    print(f"\\n✅ Saved: {{viz_path}}")
    print()

except Exception as e:
    print(f"\\n❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''

# ==============================================================================
# TEMPLATE 3: ADME PREDICTION
# ==============================================================================

ADME_TEMPLATE = '''from bioql import quantum
import os
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("=" * 80)
print("💊 BioQL 5.0.1 - ADME Prediction")
print("=" * 80)
print()
print("📊 CONFIGURATION:")
print(f"  Molecule: {molecule}")
print(f"  SMILES: {smiles}")
print(f"  Backend: {backend}")
print(f"  Shots: {shots}")
print()
print("-" * 80)

try:
    # QNN-based ADME prediction
    result = quantum(
        "Predict ADME properties for molecule SMILES {smiles}. "
        "Use Quantum Neural Network to predict: "
        "Absorption score (0-1 scale, oral bioavailability), "
        "Distribution score (0-1 scale, tissue distribution), "
        "Metabolism score (0-1 scale, hepatic clearance), "
        "Excretion score (0-1 scale, renal clearance). "
        "Calculate overall bioavailability percentage. "
        "Estimate half-life in hours. "
        "Check Lipinski Rule of Five: MW≤500, logP≤5, HBD≤5, HBA≤10.",
        backend='{backend}',
        shots={shots},
        api_key=api_key
    )

    print("\\n" + "=" * 80)
    print("✅ ADME PREDICTION COMPLETE!")
    print("=" * 80)
    print()

    # ADME scores
    print("📊 ADME SCORES (0-1 scale):")
    if hasattr(result, 'absorption_score'):
        print(f"  Absorption (A): {result.absorption_score:.3f}")
    if hasattr(result, 'distribution_score'):
        print(f"  Distribution (D): {result.distribution_score:.3f}")
    if hasattr(result, 'metabolism_score'):
        print(f"  Metabolism (M): {result.metabolism_score:.3f}")
    if hasattr(result, 'excretion_score'):
        print(f"  Excretion (E): {result.excretion_score:.3f}")
    print()

    # Pharmacokinetic parameters
    print("⏱️ PHARMACOKINETIC PARAMETERS:")
    if hasattr(result, 'bioavailability'):
        print(f"  Bioavailability: {result.bioavailability:.1f}%")
    if hasattr(result, 'half_life'):
        print(f"  Half-life (t½): {result.half_life:.2f} hours")
    if hasattr(result, 'clearance'):
        print(f"  Clearance: {result.clearance:.2f} mL/min/kg")
    if hasattr(result, 'volume_distribution'):
        print(f"  Volume of Distribution: {result.volume_distribution:.2f} L/kg")
    print()

    # Lipinski Rule of Five
    print("📋 LIPINSKI RULE OF FIVE:")
    if hasattr(result, 'molecular_weight'):
        mw_pass = result.molecular_weight <= 500
        print(f"  Molecular Weight: {result.molecular_weight:.1f} Da {'✓' if mw_pass else '✗'} (≤500)")
    if hasattr(result, 'logp'):
        logp_pass = result.logp <= 5
        print(f"  logP: {result.logp:.2f} {'✓' if logp_pass else '✗'} (≤5)")
    if hasattr(result, 'h_bond_donors'):
        hbd_pass = result.h_bond_donors <= 5
        print(f"  H-bond Donors: {result.h_bond_donors} {'✓' if hbd_pass else '✗'} (≤5)")
    if hasattr(result, 'h_bond_acceptors'):
        hba_pass = result.h_bond_acceptors <= 10
        print(f"  H-bond Acceptors: {result.h_bond_acceptors} {'✓' if hba_pass else '✗'} (≤10)")
    print()

    # Drug-likeness
    print("💊 DRUG-LIKENESS ASSESSMENT:")
    if hasattr(result, 'lipinski_violations'):
        viol = result.lipinski_violations
        if viol == 0:
            print(f"  ✓ PASSES Lipinski Rule (0 violations)")
            print(f"  ✓ High drug-likeness")
        elif viol == 1:
            print(f"  ⚠ 1 Lipinski violation (acceptable)")
            print(f"  ⚠ Moderate drug-likeness")
        else:
            print(f"  ✗ {viol} Lipinski violations")
            print(f"  ✗ Low drug-likeness")
    print()

    # Visualization
    print("=" * 80)
    print("📊 Generating Visualizations...")
    print("=" * 80)

    viz_dir = Path("bioql_visualizations")
    viz_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: ADME radar chart
    if all(hasattr(result, attr) for attr in ['absorption_score', 'distribution_score',
                                                'metabolism_score', 'excretion_score']):
        categories = ['Absorption', 'Distribution', 'Metabolism', 'Excretion']
        values = [result.absorption_score, result.distribution_score,
                  result.metabolism_score, result.excretion_score]

        angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        ax = plt.subplot(2, 2, 1, projection='polar')
        ax.plot(angles, values, 'o-', linewidth=2, color='blue', alpha=0.7)
        ax.fill(angles, values, alpha=0.25, color='blue')
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 1)
        ax.set_title('ADME Profile', fontsize=12, fontweight='bold', pad=20)
        ax.grid(True)

    # Plot 2: Bioavailability
    if hasattr(result, 'bioavailability'):
        bio = result.bioavailability
        axes[0, 1].barh(['Bioavailability'], [bio], color='green' if bio > 50 else 'orange', alpha=0.7)
        axes[0, 1].set_xlim(0, 100)
        axes[0, 1].set_xlabel('Percentage (%)')
        axes[0, 1].set_title(f'Bioavailability: {bio:.1f}%')

    # Plot 3: Lipinski compliance
    if hasattr(result, 'molecular_weight') and hasattr(result, 'logp'):
        lipinski_params = ['MW', 'logP', 'HBD', 'HBA']
        values = [
            result.molecular_weight / 500 * 100,  # Normalize to percentage
            result.logp / 5 * 100,
            getattr(result, 'h_bond_donors', 0) / 5 * 100,
            getattr(result, 'h_bond_acceptors', 0) / 10 * 100
        ]
        colors = ['green' if v <= 100 else 'red' for v in values]

        axes[1, 0].bar(lipinski_params, values, color=colors, alpha=0.7)
        axes[1, 0].axhline(y=100, color='black', linestyle='--', linewidth=2, label='Limit')
        axes[1, 0].set_ylabel('% of Limit')
        axes[1, 0].set_title('Lipinski Rule Compliance')
        axes[1, 0].legend()

    # Plot 4: Summary
    summary = f"ADME SUMMARY\\n\\n"
    summary += f"Molecule: {molecule}\\n\\n"
    if hasattr(result, 'absorption_score'):
        summary += f"Absorption: {result.absorption_score:.2f}\\n"
    if hasattr(result, 'distribution_score'):
        summary += f"Distribution: {result.distribution_score:.2f}\\n"
    if hasattr(result, 'metabolism_score'):
        summary += f"Metabolism: {result.metabolism_score:.2f}\\n"
    if hasattr(result, 'excretion_score'):
        summary += f"Excretion: {result.excretion_score:.2f}\\n\\n"
    if hasattr(result, 'bioavailability'):
        summary += f"Bioavailability: {result.bioavailability:.1f}%\\n"
    if hasattr(result, 'half_life'):
        summary += f"Half-life: {result.half_life:.1f} h\\n"
    if hasattr(result, 'lipinski_violations'):
        summary += f"Lipinski: {result.lipinski_violations} violations"

    axes[1, 1].text(0.1, 0.5, summary, fontsize=10, family='monospace',
                    verticalalignment='center')
    axes[1, 1].axis('off')

    plt.suptitle('BioQL ADME Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    viz_path = viz_dir / 'adme_{molecule}.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    print(f"\\n✅ Saved: {{viz_path}}")
    print()

except Exception as e:
    print(f"\\n❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''

# ==============================================================================
# TEMPLATE 4: TOXICITY PREDICTION
# ==============================================================================

TOXICITY_TEMPLATE = '''from bioql import quantum
import os
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("=" * 80)
print("⚠️  BioQL 5.0.1 - Toxicity Prediction")
print("=" * 80)
print()
print("📊 CONFIGURATION:")
print(f"  Molecule: {molecule}")
print(f"  SMILES: {smiles}")
print(f"  Backend: {backend}")
print(f"  Shots: {shots}")
print()
print("-" * 80)

try:
    # QNN-based toxicity prediction
    result = quantum(
        "Predict toxicity endpoints for molecule SMILES {smiles}. "
        "Use Quantum Neural Network to predict (0-1 risk scores): "
        "Hepatotoxicity (liver toxicity), "
        "Cardiotoxicity (heart toxicity), "
        "Mutagenicity (DNA damage, Ames test), "
        "Cytotoxicity (cell toxicity), "
        "Neurotoxicity (nervous system). "
        "Calculate overall risk level (low/medium/high/severe). "
        "Identify toxicophore alerts (nitro groups, epoxides, aldehydes). "
        "Provide recommendations.",
        backend='{backend}',
        shots={shots},
        api_key=api_key
    )

    print("\\n" + "=" * 80)
    print("✅ TOXICITY PREDICTION COMPLETE!")
    print("=" * 80)
    print()

    # Toxicity endpoints
    print("⚠️  TOXICITY RISK SCORES (0-1 scale):")
    if hasattr(result, 'hepatotoxicity_risk'):
        print(f"  Hepatotoxicity (Liver): {result.hepatotoxicity_risk:.3f}")
    if hasattr(result, 'cardiotoxicity_risk'):
        print(f"  Cardiotoxicity (Heart): {result.cardiotoxicity_risk:.3f}")
    if hasattr(result, 'mutagenicity_risk'):
        print(f"  Mutagenicity (DNA): {result.mutagenicity_risk:.3f}")
    if hasattr(result, 'cytotoxicity_risk'):
        print(f"  Cytotoxicity (Cell): {result.cytotoxicity_risk:.3f}")
    if hasattr(result, 'neurotoxicity_risk'):
        print(f"  Neurotoxicity (Nervous): {result.neurotoxicity_risk:.3f}")
    print()

    # Overall risk
    print("📋 OVERALL RISK ASSESSMENT:")
    if hasattr(result, 'overall_risk_score'):
        risk = result.overall_risk_score
        if risk < 0.25:
            category = "LOW"
            action = "Continue development"
            color_cat = "✓"
        elif risk < 0.5:
            category = "MEDIUM"
            action = "Additional testing required"
            color_cat = "⚠"
        elif risk < 0.75:
            category = "HIGH"
            action = "Modification recommended"
            color_cat = "⚠"
        else:
            category = "SEVERE"
            action = "Discard compound"
            color_cat = "✗"

        print(f"  {color_cat} Risk Level: {category} (score: {risk:.3f})")
        print(f"  {color_cat} Action: {action}")
    print()

    # Toxicophore alerts
    if hasattr(result, 'toxicophore_alerts'):
        print("🚨 TOXICOPHORE ALERTS:")
        if len(result.toxicophore_alerts) == 0:
            print("  ✓ No structural alerts detected")
        else:
            for alert in result.toxicophore_alerts:
                print(f"  ⚠ {alert}")
    print()

    # Recommendations
    if hasattr(result, 'recommendations'):
        print("💡 RECOMMENDATIONS:")
        for rec in result.recommendations:
            print(f"  • {rec}")
    print()

    # Visualization
    print("=" * 80)
    print("📊 Generating Visualizations...")
    print("=" * 80)

    viz_dir = Path("bioql_visualizations")
    viz_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Toxicity endpoints bar chart
    if hasattr(result, 'hepatotoxicity_risk'):
        endpoints = ['Hepato', 'Cardio', 'Mutagen', 'Cyto', 'Neuro']
        risks = [
            getattr(result, 'hepatotoxicity_risk', 0),
            getattr(result, 'cardiotoxicity_risk', 0),
            getattr(result, 'mutagenicity_risk', 0),
            getattr(result, 'cytotoxicity_risk', 0),
            getattr(result, 'neurotoxicity_risk', 0)
        ]
        colors_list = ['red' if r > 0.5 else 'orange' if r > 0.25 else 'green' for r in risks]

        axes[0, 0].bar(endpoints, risks, color=colors_list, alpha=0.7)
        axes[0, 0].axhline(y=0.25, color='yellow', linestyle='--', label='Medium threshold')
        axes[0, 0].axhline(y=0.5, color='orange', linestyle='--', label='High threshold')
        axes[0, 0].axhline(y=0.75, color='red', linestyle='--', label='Severe threshold')
        axes[0, 0].set_ylabel('Risk Score')
        axes[0, 0].set_title('Toxicity Endpoints')
        axes[0, 0].set_ylim(0, 1)
        axes[0, 0].legend(fontsize=8)

    # Plot 2: Overall risk gauge
    if hasattr(result, 'overall_risk_score'):
        risk = result.overall_risk_score

        # Create semi-circle gauge
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)

        ax = plt.subplot(2, 2, 2, projection='polar')
        ax.plot(theta, r, 'k-', linewidth=2)

        # Color segments
        segments = [
            (0, np.pi*0.25, 'green'),
            (np.pi*0.25, np.pi*0.5, 'yellow'),
            (np.pi*0.5, np.pi*0.75, 'orange'),
            (np.pi*0.75, np.pi, 'red')
        ]
        for start, end, color in segments:
            theta_seg = np.linspace(start, end, 20)
            ax.fill_between(theta_seg, 0, 1, color=color, alpha=0.3)

        # Needle
        needle_angle = risk * np.pi
        ax.plot([needle_angle, needle_angle], [0, 0.9], 'k-', linewidth=3)

        ax.set_ylim(0, 1)
        ax.set_xticks([0, np.pi*0.25, np.pi*0.5, np.pi*0.75, np.pi])
        ax.set_xticklabels(['Low', 'Med', 'High', 'Severe', ''])
        ax.set_yticks([])
        ax.set_title(f'Overall Risk: {risk:.3f}', fontsize=12, fontweight='bold', pad=20)

    # Plot 3: Toxicophore alerts
    if hasattr(result, 'toxicophore_alerts'):
        alert_text = "TOXICOPHORE ALERTS\\n\\n"
        if len(result.toxicophore_alerts) == 0:
            alert_text += "✓ No structural alerts\\n"
            alert_text += "✓ Clean structure\\n"
        else:
            for i, alert in enumerate(result.toxicophore_alerts[:5], 1):
                alert_text += f"{i}. {alert}\\n"

        axes[1, 0].text(0.1, 0.5, alert_text, fontsize=10, family='monospace',
                        verticalalignment='center')
        axes[1, 0].set_title('Structural Alerts')
        axes[1, 0].axis('off')

    # Plot 4: Summary
    summary = f"TOXICITY SUMMARY\\n\\n"
    summary += f"Molecule: {molecule}\\n\\n"
    if hasattr(result, 'overall_risk_score'):
        summary += f"Overall Risk: {result.overall_risk_score:.3f}\\n"
    if hasattr(result, 'hepatotoxicity_risk'):
        summary += f"Hepatotox: {result.hepatotoxicity_risk:.2f}\\n"
    if hasattr(result, 'cardiotoxicity_risk'):
        summary += f"Cardiotox: {result.cardiotoxicity_risk:.2f}\\n"
    if hasattr(result, 'mutagenicity_risk'):
        summary += f"Mutagenic: {result.mutagenicity_risk:.2f}\\n"
    if hasattr(result, 'cytotoxicity_risk'):
        summary += f"Cytotox: {result.cytotoxicity_risk:.2f}\\n"
    if hasattr(result, 'neurotoxicity_risk'):
        summary += f"Neurotox: {result.neurotoxicity_risk:.2f}\\n\\n"
    if hasattr(result, 'toxicophore_alerts'):
        summary += f"Alerts: {len(result.toxicophore_alerts)}"

    axes[1, 1].text(0.1, 0.5, summary, fontsize=10, family='monospace',
                    verticalalignment='center')
    axes[1, 1].axis('off')

    plt.suptitle('BioQL Toxicity Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    viz_path = viz_dir / 'toxicity_{molecule}.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    print(f"\\n✅ Saved: {{viz_path}}")
    print()

except Exception as e:
    print(f"\\n❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''

# ==============================================================================
# TEMPLATE 5: PHARMACOPHORE MODELING
# ==============================================================================

PHARMACOPHORE_TEMPLATE = '''from bioql import quantum
import os
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("=" * 80)
print("🎯 BioQL 5.0.1 - Pharmacophore Modeling")
print("=" * 80)
print()
print("📊 CONFIGURATION:")
print(f"  Molecule: {molecule}")
print(f"  SMILES: {smiles}")
print(f"  Backend: {backend}")
print(f"  Shots: {shots}")
print()
print("-" * 80)

try:
    # Quantum pharmacophore modeling
    result = quantum(
        "Generate pharmacophore model for molecule SMILES {smiles}. "
        "Identify essential pharmacophore features: "
        "H-bond donors (OH, NH), H-bond acceptors (O, N), "
        "Hydrophobic regions (aliphatic, aromatic), "
        "Aromatic rings (benzene, heterocycles), "
        "Charged groups (positive: NH3+, negative: COO-). "
        "Calculate 3D positions (x,y,z coordinates) for each feature. "
        "Determine distance constraints between features. "
        "Calculate pharmacophore score (0-1, how well-defined). "
        "Use quantum conformer generation for 3D geometry.",
        backend='{backend}',
        shots={shots},
        api_key=api_key
    )

    print("\\n" + "=" * 80)
    print("✅ PHARMACOPHORE MODEL GENERATED!")
    print("=" * 80)
    print()

    # Pharmacophore features
    print("🎯 PHARMACOPHORE FEATURES:")
    if hasattr(result, 'features'):
        feature_counts = {}
        for feature in result.features:
            ftype = feature.get('type', 'unknown')
            feature_counts[ftype] = feature_counts.get(ftype, 0) + 1
            pos = feature.get('position', (0, 0, 0))
            print(f"  • {ftype.replace('_', ' ').title()}: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")

        print()
        print("📊 FEATURE SUMMARY:")
        for ftype, count in feature_counts.items():
            print(f"  {ftype.replace('_', ' ').title()}: {{count}}")
    print()

    # Distance constraints
    if hasattr(result, 'constraints'):
        print("📏 DISTANCE CONSTRAINTS:")
        for i, constraint in enumerate(result.constraints[:5], 1):
            dist = constraint.get('distance', 0)
            tol = constraint.get('tolerance', 0)
            feat1 = constraint.get('feature1', '?')
            feat2 = constraint.get('feature2', '?')
            print(f"  {i}. {feat1} ↔ {feat2}: {dist:.2f} ± {tol:.2f} Å")
    print()

    # Pharmacophore score
    if hasattr(result, 'pharmacophore_score'):
        score = result.pharmacophore_score
        print(f"⭐ PHARMACOPHORE SCORE: {score:.3f}")
        if score > 0.7:
            print(f"  ✓ Well-defined pharmacophore")
        elif score > 0.5:
            print(f"  ⚠ Moderately defined pharmacophore")
        else:
            print(f"  ✗ Poorly defined pharmacophore")
    print()

    # Visualization
    print("=" * 80)
    print("📊 Generating Visualizations...")
    print("=" * 80)

    viz_dir = Path("bioql_visualizations")
    viz_dir.mkdir(exist_ok=True)

    fig = plt.figure(figsize=(14, 10))

    # Plot 1: 3D pharmacophore (projected to 2D)
    if hasattr(result, 'features'):
        ax1 = fig.add_subplot(221, projection='3d')

        feature_colors = {
            'hbond_donor': 'blue',
            'hbond_acceptor': 'red',
            'hydrophobic': 'green',
            'aromatic': 'purple',
            'positive_charge': 'cyan',
            'negative_charge': 'magenta'
        }

        for feature in result.features:
            ftype = feature.get('type', 'unknown')
            pos = feature.get('position', (0, 0, 0))
            color = feature_colors.get(ftype, 'gray')
            ax1.scatter(*pos, c=color, s=200, alpha=0.7, edgecolors='black', linewidth=2)
            ax1.text(pos[0], pos[1], pos[2], ftype[:4], fontsize=8)

        ax1.set_xlabel('X (Å)')
        ax1.set_ylabel('Y (Å)')
        ax1.set_zlabel('Z (Å)')
        ax1.set_title('3D Pharmacophore Model')

    # Plot 2: Feature distribution
    if hasattr(result, 'features'):
        ax2 = fig.add_subplot(222)

        feature_counts = {}
        for feature in result.features:
            ftype = feature.get('type', 'unknown')
            feature_counts[ftype] = feature_counts.get(ftype, 0) + 1

        types = list(feature_counts.keys())
        counts = list(feature_counts.values())
        colors = [feature_colors.get(t, 'gray') for t in types]

        ax2.bar(range(len(types)), counts, color=colors, alpha=0.7)
        ax2.set_xticks(range(len(types)))
        ax2.set_xticklabels([t.replace('_', '\\n') for t in types], fontsize=9)
        ax2.set_ylabel('Count')
        ax2.set_title('Feature Distribution')

    # Plot 3: Distance matrix
    if hasattr(result, 'constraints'):
        ax3 = fig.add_subplot(223)

        # Create distance matrix
        n_features = len(result.features) if hasattr(result, 'features') else 5
        dist_matrix = np.zeros((n_features, n_features))

        for constraint in result.constraints:
            i = constraint.get('feature1_idx', 0)
            j = constraint.get('feature2_idx', 0)
            dist = constraint.get('distance', 0)
            if i < n_features and j < n_features:
                dist_matrix[i, j] = dist
                dist_matrix[j, i] = dist

        im = ax3.imshow(dist_matrix, cmap='viridis', aspect='auto')
        ax3.set_title('Distance Matrix (Å)')
        ax3.set_xlabel('Feature Index')
        ax3.set_ylabel('Feature Index')
        plt.colorbar(im, ax=ax3)

    # Plot 4: Summary
    ax4 = fig.add_subplot(224)

    summary = f"PHARMACOPHORE SUMMARY\\n\\n"
    summary += f"Molecule: {molecule}\\n\\n"
    if hasattr(result, 'features'):
        summary += f"Features: {len(result.features)}\\n"
    if hasattr(result, 'constraints'):
        summary += f"Constraints: {len(result.constraints)}\\n"
    if hasattr(result, 'pharmacophore_score'):
        summary += f"Score: {result.pharmacophore_score:.3f}\\n\\n"

    if hasattr(result, 'features'):
        summary += "Feature Types:\\n"
        for ftype, count in feature_counts.items():
            summary += f"  {ftype.replace('_', ' ')}: {{count}}\\n"

    ax4.text(0.1, 0.5, summary, fontsize=10, family='monospace',
             verticalalignment='center')
    ax4.axis('off')

    plt.suptitle('BioQL Pharmacophore Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    viz_path = viz_dir / 'pharmacophore_{molecule}.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    print(f"\\n✅ Saved: {{viz_path}}")
    print()

except Exception as e:
    print(f"\\n❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''

# ==============================================================================
# TEMPLATE 6: PROTEIN FOLDING
# ==============================================================================

PROTEIN_FOLDING_TEMPLATE = '''from bioql import quantum
import os
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

api_key = os.getenv('BIOQL_API_KEY', 'your_api_key_here')

print("=" * 80)
print("🧬 BioQL 5.0.1 - Protein Folding")
print("=" * 80)
print()
print("📊 CONFIGURATION:")
print(f"  Sequence: {sequence}")
print(f"  Length: {sequence_length} amino acids")
print(f"  Backend: {backend}")
print(f"  Shots: {shots}")
print()
print("-" * 80)

try:
    # QAOA-based protein folding
    result = quantum(
        "Fold protein sequence '{sequence}' using QAOA optimization. "
        "Sequence length: {sequence_length} amino acids. "
        "Use 2D HP lattice model (Hydrophobic-Polar). "
        "Minimize folding energy considering: "
        "Hydrophobic interactions (H-H contacts: -1.0), "
        "Polar interactions (P-P contacts: 0), "
        "H-P interactions: 0. "
        "Find optimal conformation on 2D square lattice. "
        "Calculate total folding energy. "
        "Identify secondary structure elements (alpha-helix, beta-sheet). "
        "Return contact map and 3D coordinates.",
        backend='{backend}',
        shots={shots},
        api_key=api_key
    )

    print("\\n" + "=" * 80)
    print("✅ PROTEIN FOLDING COMPLETE!")
    print("=" * 80)
    print()

    # Folding energy
    print("⚡ FOLDING ENERGETICS:")
    if hasattr(result, 'folding_energy'):
        print(f"  Folding Energy: {result.folding_energy:.2f} (arbitrary units)")
        print(f"  Lower is better (more stable)")
    print()

    # Conformation
    if hasattr(result, 'conformation'):
        print(f"🧬 CONFORMATION:")
        print(f"  Coordinates: {len(result.conformation)} positions")
        for i, coord in enumerate(result.conformation[:10], 1):
            print(f"  AA{i}: ({coord[0]:.1f}, {coord[1]:.1f})")
        if len(result.conformation) > 10:
            print(f"  ... ({len(result.conformation) - 10} more)")
    print()

    # Secondary structure
    if hasattr(result, 'secondary_structure'):
        print(f"📐 SECONDARY STRUCTURE:")
        ss_counts = {}
        for ss in result.secondary_structure:
            ss_counts[ss] = ss_counts.get(ss, 0) + 1

        for ss_type, count in ss_counts.items():
            print(f"  {ss_type}: {{count}} residues")
    print()

    # Contact map
    if hasattr(result, 'contact_map'):
        n_contacts = sum(sum(row) for row in result.contact_map) // 2
        print(f"🔗 CONTACTS: {n_contacts} interactions")
    print()

    # Visualization
    print("=" * 80)
    print("📊 Generating Visualizations...")
    print("=" * 80)

    viz_dir = Path("bioql_visualizations")
    viz_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: 2D folded structure
    if hasattr(result, 'conformation'):
        coords = result.conformation
        x = [c[0] for c in coords]
        y = [c[1] for c in coords]

        axes[0, 0].plot(x, y, 'o-', markersize=10, linewidth=2, color='blue', alpha=0.7)

        # Color by residue type if available
        if hasattr(result, 'sequence_types'):
            colors = ['red' if t == 'H' else 'blue' for t in result.sequence_types]
            axes[0, 0].scatter(x, y, c=colors, s=200, alpha=0.7, edgecolors='black', linewidth=2)

        axes[0, 0].set_xlabel('X')
        axes[0, 0].set_ylabel('Y')
        axes[0, 0].set_title('2D Folded Structure')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].set_aspect('equal')

    # Plot 2: Contact map
    if hasattr(result, 'contact_map'):
        im = axes[0, 1].imshow(result.contact_map, cmap='binary', aspect='auto')
        axes[0, 1].set_xlabel('Residue Index')
        axes[0, 1].set_ylabel('Residue Index')
        axes[0, 1].set_title('Contact Map')
        plt.colorbar(im, ax=axes[0, 1])

    # Plot 3: Secondary structure distribution
    if hasattr(result, 'secondary_structure'):
        ss_counts = {}
        for ss in result.secondary_structure:
            ss_counts[ss] = ss_counts.get(ss, 0) + 1

        ss_types = list(ss_counts.keys())
        counts = list(ss_counts.values())

        axes[1, 0].bar(ss_types, counts, color=['red', 'blue', 'green'][:len(ss_types)], alpha=0.7)
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_title('Secondary Structure')

    # Plot 4: Summary
    summary = f"PROTEIN FOLDING SUMMARY\\n\\n"
    summary += f"Sequence: {sequence}\\n"
    summary += f"Length: {sequence_length} AA\\n\\n"
    if hasattr(result, 'folding_energy'):
        summary += f"Energy: {result.folding_energy:.2f}\\n"
    if hasattr(result, 'contact_map'):
        n_contacts = sum(sum(row) for row in result.contact_map) // 2
        summary += f"Contacts: {n_contacts}\\n\\n"
    if hasattr(result, 'secondary_structure'):
        for ss_type, count in ss_counts.items():
            summary += f"{ss_type}: {{count}}\\n"

    axes[1, 1].text(0.1, 0.5, summary, fontsize=10, family='monospace',
                    verticalalignment='center')
    axes[1, 1].axis('off')

    plt.suptitle('BioQL Protein Folding Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()

    viz_path = viz_dir / 'protein_folding_{sequence[:10]}.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    print(f"\\n✅ Saved: {{viz_path}}")
    print()

except Exception as e:
    print(f"\\n❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''

# ==============================================================================
# TEMPLATE SELECTOR FUNCTION
# ==============================================================================

def get_template(task_type, params):
    """
    Select and format the appropriate template based on task type.

    Args:
        task_type: One of 'docking', 'binding_affinity', 'adme', 'toxicity',
                   'pharmacophore', 'protein_folding'
        params: Dictionary with parameters like ligand, receptor, backend, shots, etc.

    Returns:
        Formatted Python code string ready to execute
    """
    templates = {
        'docking': DOCKING_TEMPLATE,
        'binding_affinity': BINDING_AFFINITY_TEMPLATE,
        'adme': ADME_TEMPLATE,
        'toxicity': TOXICITY_TEMPLATE,
        'pharmacophore': PHARMACOPHORE_TEMPLATE,
        'protein_folding': PROTEIN_FOLDING_TEMPLATE
    }

    template = templates.get(task_type)
    if not template:
        raise ValueError(f"Unknown task type: {task_type}")

    # Format template with params
    return template.format(**params)


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Example 1: Docking
    docking_params = {
        'ligand': 'Aspirin',
        'smiles': LIGAND_SMILES['aspirin'],
        'receptor': 'COX-1',
        'pdb_id': RECEPTOR_PDB['cox-1'],
        'backend': 'ibm_torino',
        'shots': 1000
    }

    docking_code = get_template('docking', docking_params)
    print("=" * 80)
    print("DOCKING TEMPLATE EXAMPLE")
    print("=" * 80)
    print(docking_code[:500])
    print("...")

    # Example 2: ADME
    adme_params = {
        'molecule': 'Metformin',
        'smiles': LIGAND_SMILES['metformin'],
        'backend': 'ibm_torino',
        'shots': 1000
    }

    adme_code = get_template('adme', adme_params)
    print("\n" + "=" * 80)
    print("ADME TEMPLATE EXAMPLE")
    print("=" * 80)
    print(adme_code[:500])
    print("...")
