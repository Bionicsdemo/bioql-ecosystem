"""
SMILES Neutralization Module for BioQL
=======================================

Safely neutralizes charged molecules while preserving molecular structure.
Critical for AutoDock Vina compatibility and accurate quantum chemistry calculations.

Author: BioQL Team
Version: 5.5.8
"""

from rdkit import Chem
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import rdMolStandardize, but don't fail if not available
try:
    from rdkit.Chem import rdMolStandardize
    HAS_MOL_STANDARDIZE = True
except ImportError:
    HAS_MOL_STANDARDIZE = False
    logger.warning("rdMolStandardize not available - using manual neutralization only")


def neutralize_smiles(smiles: str, strict: bool = False) -> str:
    """
    Neutralize charged SMILES while preserving molecular structure.

    Uses rdMolStandardize.Uncharger if available, otherwise falls back to manual neutralization:
    - Removes formal charges where chemically appropriate
    - Preserves quaternary ammonium ions if strict=True
    - Handles aromatic systems correctly
    - Preserves zwitterions in amino acids if strict=True

    Args:
        smiles: Input SMILES (may contain charges like [N+] or [O-])
        strict: If True, preserve quaternary ammoniums and zwitterions

    Returns:
        neutral_smiles: Neutralized SMILES string

    Examples:
        >>> neutralize_smiles("CC(=O)[O-]")  # Acetate
        'CC(=O)O'

        >>> neutralize_smiles("CC[NH3+]")  # Ethylamine
        'CCN'

        >>> neutralize_smiles("C[N+](C)(C)C")  # Tetramethylammonium
        'C[N+](C)(C)C'
    """
    try:
        # Parse SMILES without full sanitization first
        mol = Chem.MolFromSmiles(smiles, sanitize=False)
        if mol is None:
            logger.warning(f"Invalid SMILES - RDKit cannot parse: {smiles}")
            return smiles  # Return original if can't parse

        # Check if already neutral
        total_charge = sum([atom.GetFormalCharge() for atom in mol.GetAtoms()])
        if total_charge == 0:
            # Still sanitize to catch other issues
            try:
                Chem.SanitizeMol(mol)
                canonical_smiles = Chem.MolToSmiles(mol)
                return canonical_smiles
            except Exception as e:
                logger.warning(f"Sanitization failed for neutral molecule: {e}")
                return smiles

        # Sanitize (but skip kekulization for now to avoid aromatic issues)
        try:
            Chem.SanitizeMol(mol, sanitizeOps=Chem.SANITIZE_ALL^Chem.SANITIZE_KEKULIZE)
        except Exception as e:
            logger.warning(f"Pre-sanitization failed: {e}, attempting manual neutralization")
            return _manual_neutralize(mol, strict)

        # Try rdMolStandardize.Uncharger if available
        if HAS_MOL_STANDARDIZE:
            try:
                uncharger = rdMolStandardize.Uncharger(canonicalOrder=not strict)
                neutral_mol = uncharger.uncharge(mol)

                # Final sanitization including kekulization
                try:
                    Chem.SanitizeMol(neutral_mol)
                except Exception as e:
                    logger.warning(f"Post-neutralization sanitization failed: {e}")
                    return _manual_neutralize(mol, strict)

                neutral_smiles = Chem.MolToSmiles(neutral_mol)
                final_charge = sum([atom.GetFormalCharge() for atom in neutral_mol.GetAtoms()])

                if final_charge == 0:
                    return neutral_smiles
                else:
                    logger.warning(f"Uncharger left residual charge: {final_charge}, trying manual")
                    return _manual_neutralize(mol, strict)

            except Exception as e:
                logger.warning(f"Uncharger failed: {e}, attempting manual neutralization")
                return _manual_neutralize(mol, strict)
        else:
            # rdMolStandardize not available, use manual neutralization
            return _manual_neutralize(mol, strict)

    except Exception as e:
        logger.error(f"Neutralization error for SMILES '{smiles}': {e}")
        return smiles  # Return original if all fails


def _manual_neutralize(mol: Chem.Mol, strict: bool) -> str:
    """
    Fallback manual neutralization for when rdMolStandardize fails or is unavailable.

    Args:
        mol: RDKit molecule object (may have charges)
        strict: If True, preserve quaternary ammoniums

    Returns:
        neutral_smiles: Neutralized SMILES string
    """
    try:
        mol_copy = Chem.RWMol(mol)
        neutralized_count = 0

        for atom in mol_copy.GetAtoms():
            charge = atom.GetFormalCharge()

            if charge == 0:
                continue

            # Don't neutralize quaternary ammoniums in strict mode
            if strict and atom.GetSymbol() == 'N' and charge == 1:
                neighbors = [n.GetSymbol() for n in atom.GetNeighbors()]
                if neighbors.count('C') == 4:  # Quaternary ammonium
                    continue

            # Neutralize carboxylates: -O^- -> -OH
            if atom.GetSymbol() == 'O' and charge == -1:
                atom.SetFormalCharge(0)
                atom.SetNumExplicitHs(atom.GetNumExplicitHs() + 1)
                neutralized_count += 1

            # Neutralize ammonium: -NH3^+ -> -NH2
            elif atom.GetSymbol() == 'N' and charge == 1:
                atom.SetFormalCharge(0)
                # Don't adjust hydrogens for aromatic nitrogens
                if not atom.GetIsAromatic() and atom.GetNumExplicitHs() > 0:
                    atom.SetNumExplicitHs(atom.GetNumExplicitHs() - 1)
                neutralized_count += 1

            # Neutralize other charged atoms
            else:
                atom.SetFormalCharge(0)
                neutralized_count += 1

        # Try full sanitization first
        try:
            Chem.SanitizeMol(mol_copy)
        except Exception:
            # If full sanitization fails, try without kekulization
            try:
                Chem.SanitizeMol(mol_copy, sanitizeOps=Chem.SANITIZE_ALL^Chem.SANITIZE_KEKULIZE)
            except Exception as e2:
                logger.warning(f"Sanitization after neutralization failed: {e2}")

        neutral_smiles = Chem.MolToSmiles(mol_copy)

        logger.info(f"Manual neutralization: {neutralized_count} atoms neutralized")

        return neutral_smiles

    except Exception as e:
        logger.error(f"Manual neutralization failed: {e}")
        # Return original SMILES as last resort
        try:
            return Chem.MolToSmiles(mol)
        except:
            return ""


def validate_neutral_smiles(smiles: str) -> Tuple[bool, str]:
    """
    Validate that SMILES is properly neutralized and suitable for docking/quantum calculations.

    Args:
        smiles: SMILES string to validate

    Returns:
        (is_valid, message)
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "Invalid SMILES"

        # Check net charge
        charge = sum([atom.GetFormalCharge() for atom in mol.GetAtoms()])
        if charge != 0:
            return False, f"Molecule has net charge: {charge}. Use neutralize_smiles() first."

        # Try sanitization
        try:
            Chem.SanitizeMol(mol)
        except Exception as e:
            return False, f"Sanitization failed: {e}"

        # Try 3D embedding (critical test for docking)
        try:
            from rdkit.Chem import AllChem
            test_mol = Chem.AddHs(mol)
            result = AllChem.EmbedMolecule(test_mol, randomSeed=42)
            if result != 0:
                return False, "3D embedding failed - molecule may be too complex or have invalid geometry"
        except Exception as e:
            return False, f"3D embedding error: {e}"

        return True, "Valid neutral SMILES"

    except Exception as e:
        return False, f"Validation error: {e}"
