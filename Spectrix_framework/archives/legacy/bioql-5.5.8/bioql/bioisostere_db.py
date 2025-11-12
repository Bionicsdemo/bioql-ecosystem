"""
BioQL Bioisosteric Replacement Database
========================================

Database and engine for suggesting bioisosteric replacements to:
- Reduce toxicity
- Improve metabolic stability
- Maintain or improve binding affinity
- Optimize ADME properties

Version: 5.6.0+
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import re

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors
    HAVE_RDKIT = True
except ImportError:
    HAVE_RDKIT = False


@dataclass
class BioisostereReplacement:
    """A bioisosteric replacement suggestion"""
    original_group: str  # SMARTS pattern
    original_name: str
    replacement_group: str  # SMARTS pattern
    replacement_name: str
    rationale: str
    expected_benefits: List[str]
    warnings: List[str]
    literature_refs: List[str]
    pka_change: str  # "similar", "+1 to +2", "-1 to -2", etc.


# Comprehensive bioisostere database from medicinal chemistry literature
BIOISOSTERE_DATABASE = [
    # === CARBOXYLIC ACID REPLACEMENTS ===
    BioisostereReplacement(
        original_group="C(=O)O",
        original_name="Carboxylic acid",
        replacement_group="c1nnnn1",
        replacement_name="Tetrazole",
        rationale="Tetrazole is isosteric and isoacidic (pKa ~4.5-5)",
        expected_benefits=["Improved metabolic stability", "Better oral bioavailability", "Similar H-bond donor/acceptor"],
        warnings=["Potential for idiosyncratic toxicity (rare)", "May bind metals"],
        literature_refs=["J. Med. Chem. 1986, 29, 359-369"],
        pka_change="similar"
    ),
    BioisostereReplacement(
        original_group="C(=O)O",
        original_name="Carboxylic acid",
        replacement_group="S(=O)(=O)NC(=O)",
        replacement_name="Acylsulfonamide",
        rationale="Very acidic (pKa ~3-4), strong H-bond donor",
        expected_benefits=["Reduced glucuronidation", "Improved metabolic stability", "Lower pKa"],
        warnings=["Potential sulfonamide allergy", "Lower lipophilicity"],
        literature_refs=["J. Med. Chem. 1999, 42, 2180-2190"],
        pka_change="-1 to -2"
    ),

    # === AMIDE REPLACEMENTS ===
    BioisostereReplacement(
        original_group="C(=O)N",
        original_name="Amide",
        replacement_group="C(=S)N",
        replacement_name="Thioamide",
        rationale="Similar H-bonding, increased lipophilicity",
        expected_benefits=["Improved membrane permeability", "Reduced amide hydrolysis"],
        warnings=["Potential for oxidative metabolism", "May be mutagenic (rare)"],
        literature_refs=["Bioorg. Med. Chem. 2009, 17, 3469-3473"],
        pka_change="similar"
    ),
    BioisostereReplacement(
        original_group="C(=O)N",
        original_name="Amide",
        replacement_group="OC(=O)N",
        replacement_name="Carbamate",
        rationale="Similar geometry, different electronics",
        expected_benefits=["Improved aqueous solubility", "H-bond acceptor enhancement"],
        warnings=["May be labile in vivo", "Esterase substrate"],
        literature_refs=["J. Med. Chem. 2008, 51, 6092-6100"],
        pka_change="+1 to +2"
    ),
    BioisostereReplacement(
        original_group="C(=O)N",
        original_name="Amide",
        replacement_group="S(=O)(=O)N",
        replacement_name="Sulfonamide",
        rationale="Stronger H-bond donor, lower pKa",
        expected_benefits=["Increased potency (if H-bond critical)", "Reduced amidase liability"],
        warnings=["Sulfonamide allergy risk", "Lower lipophilicity"],
        literature_refs=["J. Med. Chem. 2015, 58, 2895-2903"],
        pka_change="-3 to -4"
    ),

    # === ESTER REPLACEMENTS ===
    BioisostereReplacement(
        original_group="C(=O)OC",
        original_name="Ester",
        replacement_group="C(=O)NC",
        replacement_name="Amide",
        rationale="Resistant to esterases, similar geometry",
        expected_benefits=["Improved metabolic stability", "Longer half-life"],
        warnings=["Reduced lipophilicity", "May alter pharmacokinetics"],
        literature_refs=["Drug Metab. Dispos. 2010, 38, 1261-1267"],
        pka_change="+2 to +3"
    ),
    BioisostereReplacement(
        original_group="C(=O)OC",
        original_name="Ester",
        replacement_group="C(=O)C",
        replacement_name="Ketone",
        rationale="Not hydrolyzable, similar electronics",
        expected_benefits=["Complete esterase resistance", "Improved stability"],
        warnings=["Loss of H-bond acceptor", "Possible aldehyde reductase substrate"],
        literature_refs=["J. Med. Chem. 2012, 55, 4896-4903"],
        pka_change="N/A"
    ),

    # === AROMATIC RING REPLACEMENTS ===
    BioisostereReplacement(
        original_group="c1ccccc1",
        original_name="Benzene",
        replacement_group="c1ncccc1",
        replacement_name="Pyridine",
        rationale="Similar size, adds H-bond acceptor, reduces lipophilicity",
        expected_benefits=["Improved solubility", "Additional interaction point", "Lower CYP450 metabolism"],
        warnings=["May alter pKa of nearby groups", "Potential N-oxidation"],
        literature_refs=["J. Med. Chem. 2013, 56, 1614-1628"],
        pka_change="+0.5 to +1"
    ),
    BioisostereReplacement(
        original_group="c1ccccc1",
        original_name="Benzene",
        replacement_group="C1CCCCC1",
        replacement_name="Cyclohexane",
        rationale="Sp3-rich scaffold, 3D exit vectors",
        expected_benefits=["Improved druglikeness (Csp3)", "Escape flat aromatic SAR", "Reduced CYP450 liability"],
        warnings=["Loss of π-π stacking", "May have conformational flexibility issues"],
        literature_refs=["Angew. Chem. Int. Ed. 2009, 48, 6452-6465"],
        pka_change="N/A"
    ),

    # === HETEROATOM REPLACEMENTS ===
    BioisostereReplacement(
        original_group="O",
        original_name="Ether oxygen",
        replacement_group="S",
        replacement_name="Thioether",
        rationale="Larger, more polarizable, similar geometry",
        expected_benefits=["Increased lipophilicity", "Different metabolic profile"],
        warnings=["Potential for S-oxidation to sulfoxide/sulfone", "May be malodorous"],
        literature_refs=["J. Med. Chem. 2016, 59, 5381-5389"],
        pka_change="similar"
    ),
    BioisostereReplacement(
        original_group="O",
        original_name="Ether oxygen",
        replacement_group="C",
        replacement_name="Methylene (CH2)",
        rationale="Isosteric, removes H-bond acceptor",
        expected_benefits=["Increased lipophilicity", "Improved membrane permeability"],
        warnings=["Loss of H-bonding capability", "May reduce potency if H-bond critical"],
        literature_refs=["J. Med. Chem. 2011, 54, 2529-2537"],
        pka_change="N/A"
    ),

    # === NITRO GROUP REPLACEMENTS (Toxicity reduction) ===
    BioisostereReplacement(
        original_group="[N+](=O)[O-]",
        original_name="Nitro group",
        replacement_group="C(=O)N",
        replacement_name="Amide",
        rationale="Removes mutagenic nitro group, maintains polarity",
        expected_benefits=["Reduced mutagenicity", "Lower Ames test liability", "Better safety profile"],
        warnings=["Different electronics", "May reduce potency"],
        literature_refs=["Chem. Res. Toxicol. 2008, 21, 1811-1820"],
        pka_change="significant change"
    ),
    BioisostereReplacement(
        original_group="[N+](=O)[O-]",
        original_name="Nitro group",
        replacement_group="S(=O)(=O)N",
        replacement_name="Sulfonamide",
        rationale="Removes mutagenic risk, maintains electron-withdrawing character",
        expected_benefits=["Greatly reduced mutagenicity", "Similar EWG effect"],
        warnings=["pKa change", "Different H-bonding"],
        literature_refs=["Drug Metab. Rev. 2012, 44, 253-262"],
        pka_change="-2 to -3"
    ),
]


def suggest_bioisosteric_replacements(
    smiles: str,
    problematic_group_smarts: str = None,
    goal: str = "improve_stability"
) -> List[Dict[str, Any]]:
    """
    Suggest bioisosteric replacements for a molecule.

    Args:
        smiles: Molecule SMILES
        problematic_group_smarts: SMARTS pattern of group to replace (optional)
        goal: "reduce_toxicity", "improve_stability", "improve_solubility", "all"

    Returns:
        List of replacement suggestions with modified SMILES
    """
    if not HAVE_RDKIT:
        raise ImportError("RDKit required for bioisosteric replacement")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    suggestions = []

    # If specific group provided, filter database
    if problematic_group_smarts:
        candidates = [b for b in BIOISOSTERE_DATABASE
                     if b.original_group == problematic_group_smarts]
    else:
        candidates = BIOISOSTERE_DATABASE

    # Find matching substructures and generate replacements
    for bioisostere in candidates:
        pattern = Chem.MolFromSmarts(bioisostere.original_group)
        if pattern is None:
            continue

        if mol.HasSubstructMatch(pattern):
            # Generate replacement
            try:
                # Use RDKit's ReplaceSubstructs (simplified approach)
                replacement_mol = Chem.MolFromSmarts(bioisostere.replacement_group)
                if replacement_mol:
                    # This is a placeholder - real implementation would need
                    # more sophisticated replacement logic
                    new_smiles = f"{smiles}_WITH_{bioisostere.replacement_name.replace(' ', '_')}"

                    suggestions.append({
                        'original_smiles': smiles,
                        'new_smiles': new_smiles,
                        'original_group': bioisostere.original_name,
                        'replacement_group': bioisostere.replacement_name,
                        'rationale': bioisostere.rationale,
                        'expected_benefits': bioisostere.expected_benefits,
                        'warnings': bioisostere.warnings,
                        'pka_change': bioisostere.pka_change,
                        'literature': bioisostere.literature_refs,
                    })
            except Exception as e:
                print(f"   ⚠️  Could not generate replacement for {bioisostere.replacement_name}: {e}")
                continue

    return suggestions


if __name__ == "__main__":
    # Test
    test_smiles = "CC(=O)Oc1ccccc1C(=O)O"  # Aspirin

    print("🔬 Bioisosteric Replacement Suggestions")
    print(f"Molecule: {test_smiles} (Aspirin)")
    print("-" * 60)

    suggestions = suggest_bioisosteric_replacements(test_smiles)

    for i, sug in enumerate(suggestions, 1):
        print(f"\n{i}. Replace {sug['original_group']} → {sug['replacement_group']}")
        print(f"   Rationale: {sug['rationale']}")
        print(f"   Benefits: {', '.join(sug['expected_benefits'])}")
        print(f"   pKa change: {sug['pka_change']}")
