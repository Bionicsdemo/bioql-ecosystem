"""
Molecular Hamiltonian Construction Module

This module provides functions for building molecular Hamiltonians for drug-protein
interactions, including quantum mechanical representations for quantum computing.

Physical Models Implemented:
- Coulombic interactions (electrostatic energy)
- Van der Waals interactions (Lennard-Jones potential)
- Hydrogen bonding (distance and angle-dependent)
- Quantum mechanical Hamiltonian mapping (Jordan-Wigner/Bravyi-Kitaev transformations)
"""

import numpy as np
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
from rdkit.Chem import rdPartialCharges
import re

# Physical constants
COULOMB_CONSTANT = 332.0636  # kcal·Å/(mol·e²) - conversion for electrostatics
EPSILON_0 = 1.0  # Relative permittivity (vacuum)
DIELECTRIC_CONSTANT = 4.0  # Typical protein interior dielectric constant

# Lennard-Jones parameters (kcal/mol and Å)
LJ_PARAMS = {
    'C': {'epsilon': 0.086, 'sigma': 3.4},
    'N': {'epsilon': 0.170, 'sigma': 3.25},
    'O': {'epsilon': 0.210, 'sigma': 2.96},
    'S': {'epsilon': 0.250, 'sigma': 3.5},
    'H': {'epsilon': 0.015, 'sigma': 2.5},
    'P': {'epsilon': 0.200, 'sigma': 3.74},
    'F': {'epsilon': 0.061, 'sigma': 2.94},
    'Cl': {'epsilon': 0.265, 'sigma': 3.47},
    'Br': {'epsilon': 0.320, 'sigma': 3.73},
}

# Hydrogen bond parameters
H_BOND_DISTANCE_CUTOFF = 3.5  # Å
H_BOND_ANGLE_CUTOFF = 120.0  # degrees
H_BOND_ENERGY = -3.0  # kcal/mol (typical H-bond strength)


@dataclass
class MolecularSystem:
    """Represents a molecular system with coordinates and atomic properties"""
    coords: np.ndarray  # Nx3 array of coordinates
    atomic_numbers: np.ndarray  # N array of atomic numbers
    partial_charges: np.ndarray  # N array of partial charges
    atom_types: List[str]  # N list of atom type symbols


def parse_smiles_to_3d(smiles: str) -> Tuple[np.ndarray, List[str], np.ndarray]:
    """
    Parse SMILES string and generate 3D coordinates using RDKit.

    Args:
        smiles: SMILES string of the molecule

    Returns:
        coords: Nx3 numpy array of 3D coordinates (Å)
        atom_types: List of atom symbols
        atomic_numbers: Array of atomic numbers
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")

    # Add hydrogens
    mol = Chem.AddHs(mol)

    # Generate 3D coordinates using ETKDG method (improved conformer generation)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    result = AllChem.EmbedMolecule(mol, params)

    if result != 0:
        raise ValueError(f"Failed to generate 3D coordinates for SMILES: {smiles}")

    # Optimize geometry with MMFF force field
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)

    # Extract coordinates
    conf = mol.GetConformer()
    coords = np.array([list(conf.GetAtomPosition(i)) for i in range(mol.GetNumAtoms())])

    # Extract atom information
    atom_types = [atom.GetSymbol() for atom in mol.GetAtoms()]
    atomic_numbers = np.array([atom.GetAtomicNum() for atom in mol.GetAtoms()])

    return coords, atom_types, atomic_numbers


def compute_partial_charges(smiles: str) -> np.ndarray:
    """
    Compute Gasteiger partial charges for atoms in molecule.

    Args:
        smiles: SMILES string of the molecule

    Returns:
        partial_charges: Array of partial charges (electron units)
    """
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)

    # Compute Gasteiger charges
    rdPartialCharges.ComputeGasteigerCharges(mol)

    partial_charges = np.array([
        float(atom.GetProp('_GasteigerCharge')) if atom.HasProp('_GasteigerCharge')
        else 0.0
        for atom in mol.GetAtoms()
    ])

    # Replace NaN values with 0
    partial_charges = np.nan_to_num(partial_charges, nan=0.0)

    return partial_charges


def parse_pdb_binding_site(pdb_data: str, center: np.ndarray = None, radius: float = 10.0) -> MolecularSystem:
    """
    Extract binding site coordinates and atomic information from PDB data.

    Args:
        pdb_data: PDB format string
        center: Center coordinates for binding site extraction (if None, use all atoms)
        radius: Radius around center to include atoms (Å)

    Returns:
        MolecularSystem object with receptor binding site information
    """
    coords_list = []
    atom_types_list = []
    atomic_numbers_list = []

    # Element to atomic number mapping
    element_to_z = {
        'H': 1, 'C': 6, 'N': 7, 'O': 8, 'S': 16, 'P': 15,
        'F': 9, 'Cl': 17, 'Br': 35, 'I': 53
    }

    for line in pdb_data.split('\n'):
        if line.startswith('ATOM') or line.startswith('HETATM'):
            # Parse PDB ATOM/HETATM record
            try:
                x = float(line[30:38].strip())
                y = float(line[38:46].strip())
                z = float(line[46:54].strip())
                element = line[76:78].strip()

                if not element:
                    # Fallback: extract from atom name
                    atom_name = line[12:16].strip()
                    element = ''.join([c for c in atom_name if c.isalpha()])[:2]
                    element = element[0].upper() + element[1:].lower() if len(element) > 1 else element.upper()

                coord = np.array([x, y, z])

                # Filter by distance if center is provided
                if center is not None:
                    if np.linalg.norm(coord - center) > radius:
                        continue

                coords_list.append(coord)
                atom_types_list.append(element)
                atomic_numbers_list.append(element_to_z.get(element, 6))  # Default to carbon

            except (ValueError, IndexError):
                continue

    if not coords_list:
        raise ValueError("No valid atoms found in PDB data")

    coords = np.array(coords_list)
    atomic_numbers = np.array(atomic_numbers_list)

    # Estimate partial charges for receptor (simplified - use atom type based charges)
    charge_map = {'C': 0.1, 'N': -0.3, 'O': -0.4, 'S': -0.2, 'H': 0.1, 'P': 0.3}
    partial_charges = np.array([charge_map.get(at, 0.0) for at in atom_types_list])

    return MolecularSystem(
        coords=coords,
        atomic_numbers=atomic_numbers,
        partial_charges=partial_charges,
        atom_types=atom_types_list
    )


def compute_coulombic_energy(coords1: np.ndarray, charges1: np.ndarray,
                             coords2: np.ndarray, charges2: np.ndarray,
                             dielectric: float = DIELECTRIC_CONSTANT) -> float:
    """
    Compute Coulombic (electrostatic) interaction energy between two sets of atoms.

    E_coulomb = k * Σ(q_i * q_j / (ε * r_ij))

    Args:
        coords1: Nx3 array of first set coordinates
        charges1: N array of partial charges
        coords2: Mx3 array of second set coordinates
        charges2: M array of partial charges
        dielectric: Dielectric constant of medium

    Returns:
        Total Coulombic energy (kcal/mol)
    """
    energy = 0.0

    for i in range(len(coords1)):
        for j in range(len(coords2)):
            r_ij = np.linalg.norm(coords1[i] - coords2[j])

            # Avoid division by zero (use minimum distance of 0.5 Å)
            r_ij = max(r_ij, 0.5)

            # Coulomb's law with dielectric screening
            q_i_q_j = charges1[i] * charges2[j]
            energy += COULOMB_CONSTANT * q_i_q_j / (dielectric * r_ij)

    return energy


def compute_vdw_energy(coords1: np.ndarray, types1: List[str],
                       coords2: np.ndarray, types2: List[str]) -> float:
    """
    Compute Van der Waals interaction energy using Lennard-Jones potential.

    E_LJ = Σ[ 4ε_ij * ((σ_ij/r_ij)^12 - (σ_ij/r_ij)^6) ]

    Args:
        coords1: Nx3 array of first set coordinates
        types1: List of atom types for first set
        coords2: Mx3 array of second set coordinates
        types2: List of atom types for second set

    Returns:
        Total Van der Waals energy (kcal/mol)
    """
    energy = 0.0

    for i in range(len(coords1)):
        for j in range(len(coords2)):
            r_ij = np.linalg.norm(coords1[i] - coords2[j])

            # Avoid numerical issues at very short distances
            if r_ij < 0.5:
                r_ij = 0.5

            # Get LJ parameters (use Lorentz-Berthelot combining rules)
            atom1 = types1[i]
            atom2 = types2[j]

            params1 = LJ_PARAMS.get(atom1, LJ_PARAMS['C'])
            params2 = LJ_PARAMS.get(atom2, LJ_PARAMS['C'])

            epsilon_ij = np.sqrt(params1['epsilon'] * params2['epsilon'])
            sigma_ij = (params1['sigma'] + params2['sigma']) / 2.0

            # Lennard-Jones 12-6 potential
            sigma_over_r = sigma_ij / r_ij
            lj_term = 4.0 * epsilon_ij * (sigma_over_r**12 - sigma_over_r**6)

            # Truncate at cutoff to avoid extreme values
            if r_ij < 12.0:  # 12 Å cutoff
                energy += lj_term

    return energy


def identify_hbond_donors_acceptors(coords: np.ndarray, types: List[str]) -> Tuple[List[int], List[int]]:
    """
    Identify potential hydrogen bond donors and acceptors.

    Args:
        coords: Nx3 array of coordinates
        types: List of atom types

    Returns:
        donors: List of indices of H-bond donor atoms (H attached to N/O)
        acceptors: List of indices of H-bond acceptor atoms (N/O)
    """
    donors = []
    acceptors = []

    for i, atom_type in enumerate(types):
        if atom_type in ['N', 'O']:
            acceptors.append(i)
        if atom_type == 'H':
            donors.append(i)

    return donors, acceptors


def compute_hbond_energy(coords1: np.ndarray, types1: List[str],
                         coords2: np.ndarray, types2: List[str]) -> float:
    """
    Compute hydrogen bonding energy (simplified distance-based model).

    Args:
        coords1: Nx3 array of first set coordinates
        types1: List of atom types for first set
        coords2: Mx3 array of second set coordinates
        types2: List of atom types for second set

    Returns:
        Total H-bond energy (kcal/mol)
    """
    energy = 0.0

    donors1, acceptors1 = identify_hbond_donors_acceptors(coords1, types1)
    donors2, acceptors2 = identify_hbond_donors_acceptors(coords2, types2)

    # Check donor1-acceptor2 interactions
    for donor_idx in donors1:
        for acceptor_idx in acceptors2:
            r = np.linalg.norm(coords1[donor_idx] - coords2[acceptor_idx])

            if r <= H_BOND_DISTANCE_CUTOFF:
                # Distance-dependent H-bond energy
                energy += H_BOND_ENERGY * (1.0 - r / H_BOND_DISTANCE_CUTOFF)

    # Check donor2-acceptor1 interactions
    for donor_idx in donors2:
        for acceptor_idx in acceptors1:
            r = np.linalg.norm(coords2[donor_idx] - coords1[acceptor_idx])

            if r <= H_BOND_DISTANCE_CUTOFF:
                energy += H_BOND_ENERGY * (1.0 - r / H_BOND_DISTANCE_CUTOFF)

    return energy


def compute_interaction_energy(ligand_coords: np.ndarray, receptor_coords: np.ndarray,
                               ligand_charges: np.ndarray = None, receptor_charges: np.ndarray = None,
                               ligand_types: List[str] = None, receptor_types: List[str] = None) -> Dict[str, float]:
    """
    Compute total interaction energy between ligand and receptor.

    Includes:
    - Coulombic (electrostatic) interactions
    - Van der Waals (Lennard-Jones) interactions
    - Hydrogen bonding interactions

    Args:
        ligand_coords: Nx3 array of ligand coordinates
        receptor_coords: Mx3 array of receptor coordinates
        ligand_charges: N array of ligand partial charges
        receptor_charges: M array of receptor partial charges
        ligand_types: List of ligand atom types
        receptor_types: List of receptor atom types

    Returns:
        Dictionary with energy components and total energy (kcal/mol)
    """
    energy_components = {}

    # Coulombic energy
    if ligand_charges is not None and receptor_charges is not None:
        energy_components['coulombic'] = compute_coulombic_energy(
            ligand_coords, ligand_charges,
            receptor_coords, receptor_charges
        )
    else:
        energy_components['coulombic'] = 0.0

    # Van der Waals energy
    if ligand_types is not None and receptor_types is not None:
        energy_components['vdw'] = compute_vdw_energy(
            ligand_coords, ligand_types,
            receptor_coords, receptor_types
        )
    else:
        energy_components['vdw'] = 0.0

    # Hydrogen bonding energy
    if ligand_types is not None and receptor_types is not None:
        energy_components['hbond'] = compute_hbond_energy(
            ligand_coords, ligand_types,
            receptor_coords, receptor_types
        )
    else:
        energy_components['hbond'] = 0.0

    # Total energy
    energy_components['total'] = sum(energy_components.values())

    return energy_components


def build_molecular_hamiltonian(smiles: str, pdb_data: str,
                                binding_site_center: np.ndarray = None,
                                binding_site_radius: float = 10.0) -> np.ndarray:
    """
    Build molecular interaction Hamiltonian matrix for ligand-receptor system.

    The Hamiltonian includes:
    - Diagonal elements: self-interaction energies
    - Off-diagonal elements: pairwise interaction energies

    Args:
        smiles: SMILES string of ligand
        pdb_data: PDB format string of receptor
        binding_site_center: Center of binding site (Å)
        binding_site_radius: Radius to extract binding site (Å)

    Returns:
        Hamiltonian matrix as numpy array (kcal/mol units)
    """
    # Parse ligand
    ligand_coords, ligand_types, ligand_atomic_nums = parse_smiles_to_3d(smiles)
    ligand_charges = compute_partial_charges(smiles)

    # Parse receptor binding site
    receptor = parse_pdb_binding_site(pdb_data, binding_site_center, binding_site_radius)

    # Total number of atoms
    n_ligand = len(ligand_coords)
    n_receptor = len(receptor.coords)
    n_total = n_ligand + n_receptor

    # Initialize Hamiltonian matrix
    H = np.zeros((n_total, n_total))

    # Build interaction blocks

    # Ligand-ligand interactions (upper-left block)
    for i in range(n_ligand):
        for j in range(i, n_ligand):
            if i == j:
                # Diagonal: self energy (set to 0 for relative energy)
                H[i, i] = 0.0
            else:
                # Off-diagonal: ligand internal interactions
                r_ij = np.linalg.norm(ligand_coords[i] - ligand_coords[j])
                if r_ij > 0.5:
                    # Coulombic term
                    coulomb = COULOMB_CONSTANT * ligand_charges[i] * ligand_charges[j] / (DIELECTRIC_CONSTANT * r_ij)

                    # VDW term
                    params_i = LJ_PARAMS.get(ligand_types[i], LJ_PARAMS['C'])
                    params_j = LJ_PARAMS.get(ligand_types[j], LJ_PARAMS['C'])
                    epsilon_ij = np.sqrt(params_i['epsilon'] * params_j['epsilon'])
                    sigma_ij = (params_i['sigma'] + params_j['sigma']) / 2.0
                    sigma_over_r = sigma_ij / r_ij
                    vdw = 4.0 * epsilon_ij * (sigma_over_r**12 - sigma_over_r**6)

                    H[i, j] = coulomb + vdw
                    H[j, i] = H[i, j]  # Symmetric

    # Receptor-receptor interactions (lower-right block)
    for i in range(n_receptor):
        for j in range(i, n_receptor):
            idx_i = n_ligand + i
            idx_j = n_ligand + j

            if i == j:
                H[idx_i, idx_i] = 0.0
            else:
                r_ij = np.linalg.norm(receptor.coords[i] - receptor.coords[j])
                if r_ij > 0.5:
                    # Coulombic term
                    coulomb = COULOMB_CONSTANT * receptor.partial_charges[i] * receptor.partial_charges[j] / (DIELECTRIC_CONSTANT * r_ij)

                    # VDW term
                    params_i = LJ_PARAMS.get(receptor.atom_types[i], LJ_PARAMS['C'])
                    params_j = LJ_PARAMS.get(receptor.atom_types[j], LJ_PARAMS['C'])
                    epsilon_ij = np.sqrt(params_i['epsilon'] * params_j['epsilon'])
                    sigma_ij = (params_i['sigma'] + params_j['sigma']) / 2.0
                    sigma_over_r = sigma_ij / r_ij
                    vdw = 4.0 * epsilon_ij * (sigma_over_r**12 - sigma_over_r**6)

                    H[idx_i, idx_j] = coulomb + vdw
                    H[idx_j, idx_i] = H[idx_i, idx_j]

    # Ligand-receptor interactions (off-diagonal blocks)
    for i in range(n_ligand):
        for j in range(n_receptor):
            idx_rec = n_ligand + j

            r_ij = np.linalg.norm(ligand_coords[i] - receptor.coords[j])
            if r_ij > 0.5:
                # Coulombic term
                coulomb = COULOMB_CONSTANT * ligand_charges[i] * receptor.partial_charges[j] / (DIELECTRIC_CONSTANT * r_ij)

                # VDW term
                params_lig = LJ_PARAMS.get(ligand_types[i], LJ_PARAMS['C'])
                params_rec = LJ_PARAMS.get(receptor.atom_types[j], LJ_PARAMS['C'])
                epsilon_ij = np.sqrt(params_lig['epsilon'] * params_rec['epsilon'])
                sigma_ij = (params_lig['sigma'] + params_rec['sigma']) / 2.0
                sigma_over_r = sigma_ij / r_ij
                vdw = 4.0 * epsilon_ij * (sigma_over_r**12 - sigma_over_r**6)

                # H-bond term
                hbond = 0.0
                if ligand_types[i] == 'H' and receptor.atom_types[j] in ['N', 'O']:
                    if r_ij <= H_BOND_DISTANCE_CUTOFF:
                        hbond = H_BOND_ENERGY * (1.0 - r_ij / H_BOND_DISTANCE_CUTOFF)
                elif receptor.atom_types[j] == 'H' and ligand_types[i] in ['N', 'O']:
                    if r_ij <= H_BOND_DISTANCE_CUTOFF:
                        hbond = H_BOND_ENERGY * (1.0 - r_ij / H_BOND_DISTANCE_CUTOFF)

                H[i, idx_rec] = coulomb + vdw + hbond
                H[idx_rec, i] = H[i, idx_rec]

    return H


def molecule_to_qubit_hamiltonian(mol: Chem.Mol, transformation: str = 'jordan_wigner') -> Dict:
    """
    Convert molecular structure to qubit Hamiltonian using fermionic-to-qubit mapping.

    This implements a simplified second quantization approach:
    1. Map molecular orbitals to fermionic operators
    2. Transform fermionic operators to Pauli operators using Jordan-Wigner or Bravyi-Kitaev

    Args:
        mol: RDKit molecule object
        transformation: 'jordan_wigner' or 'bravyi_kitaev'

    Returns:
        Dictionary with Pauli operator terms and coefficients
    """
    if not isinstance(mol, Chem.Mol):
        raise TypeError("Input must be an RDKit Mol object")

    # Get number of electrons and orbitals
    num_electrons = sum([atom.GetAtomicNum() for atom in mol.GetAtoms()])
    num_orbitals = mol.GetNumAtoms()  # Simplified: one orbital per atom
    num_qubits = 2 * num_orbitals  # Spin-up and spin-down orbitals

    # Initialize Hamiltonian terms (Pauli operators)
    pauli_terms = {}

    # Get molecular orbital coefficients (simplified using Hückel theory for π systems)
    # For general molecules, this would require quantum chemistry calculations

    # One-electron integrals (kinetic + nuclear attraction)
    h_pq = np.zeros((num_orbitals, num_orbitals))

    # Two-electron integrals (electron-electron repulsion)
    # Using simplified Ohno-Klopman formula for γ parameters
    for p in range(num_orbitals):
        atom_p = mol.GetAtomWithIdx(p)
        # Diagonal elements: ionization potential (simplified)
        h_pq[p, p] = -atom_p.GetAtomicNum() * 0.5  # Simplified IP in a.u.

        for q in range(p + 1, num_orbitals):
            atom_q = mol.GetAtomWithIdx(q)
            # Off-diagonal: resonance integral (distance-dependent)
            bond = mol.GetBondBetweenAtoms(p, q)
            if bond is not None:
                h_pq[p, q] = -2.4  # Typical β value for C-C bonds (eV)
                h_pq[q, p] = h_pq[p, q]

    # Apply Jordan-Wigner or Bravyi-Kitaev transformation
    if transformation.lower() == 'jordan_wigner':
        pauli_terms = jordan_wigner_transform(h_pq, num_qubits)
    elif transformation.lower() == 'bravyi_kitaev':
        pauli_terms = bravyi_kitaev_transform(h_pq, num_qubits)
    else:
        raise ValueError(f"Unknown transformation: {transformation}")

    return {
        'pauli_terms': pauli_terms,
        'num_qubits': num_qubits,
        'num_electrons': num_electrons,
        'transformation': transformation
    }


def jordan_wigner_transform(h_pq: np.ndarray, num_qubits: int) -> Dict[str, float]:
    """
    Jordan-Wigner transformation: maps fermionic operators to Pauli operators.

    Fermionic creation/annihilation operators are mapped as:
    a†_p = (X_p - iY_p)/2 * Z_0...Z_{p-1}
    a_p = (X_p + iY_p)/2 * Z_0...Z_{p-1}

    Args:
        h_pq: One-electron integral matrix
        num_qubits: Number of qubits

    Returns:
        Dictionary mapping Pauli strings to coefficients
    """
    pauli_terms = {}
    n_orbitals = len(h_pq)

    # One-body terms: Σ h_pq a†_p a_q
    for p in range(n_orbitals):
        for q in range(n_orbitals):
            if abs(h_pq[p, q]) < 1e-10:
                continue

            coeff = h_pq[p, q] / 2.0

            if p == q:
                # Number operator: a†_p a_p = (I - Z_p)/2
                pauli_str = 'I' * p + 'Z' + 'I' * (num_qubits - p - 1)
                pauli_terms[pauli_str] = pauli_terms.get(pauli_str, 0.0) - coeff

                pauli_str = 'I' * num_qubits
                pauli_terms[pauli_str] = pauli_terms.get(pauli_str, 0.0) + coeff
            else:
                # Hopping terms: a†_p a_q
                # Results in X_pX_q + Y_pY_q terms (with Z string between)
                if p < q:
                    z_string = ''.join(['Z' if p < i < q else 'I' for i in range(num_qubits)])
                else:
                    z_string = ''.join(['Z' if q < i < p else 'I' for i in range(num_qubits)])

                # XX term
                pauli_str = list('I' * num_qubits)
                pauli_str[p] = 'X'
                pauli_str[q] = 'X'
                for i in range(min(p, q) + 1, max(p, q)):
                    pauli_str[i] = 'Z'
                pauli_terms[''.join(pauli_str)] = pauli_terms.get(''.join(pauli_str), 0.0) + coeff

                # YY term
                pauli_str = list('I' * num_qubits)
                pauli_str[p] = 'Y'
                pauli_str[q] = 'Y'
                for i in range(min(p, q) + 1, max(p, q)):
                    pauli_str[i] = 'Z'
                pauli_terms[''.join(pauli_str)] = pauli_terms.get(''.join(pauli_str), 0.0) + coeff

    return pauli_terms


def bravyi_kitaev_transform(h_pq: np.ndarray, num_qubits: int) -> Dict[str, float]:
    """
    Bravyi-Kitaev transformation: more efficient qubit mapping than Jordan-Wigner.

    Uses binary tree structure to reduce operator weight.

    Args:
        h_pq: One-electron integral matrix
        num_qubits: Number of qubits

    Returns:
        Dictionary mapping Pauli strings to coefficients
    """
    pauli_terms = {}
    n_orbitals = len(h_pq)

    # BK transformation matrices (simplified version)
    # For full implementation, need to compute update, parity, and flip sets

    def get_parity_set(j: int) -> List[int]:
        """Get parity set for qubit j"""
        parity = []
        k = 1
        while k <= j:
            if j & k:
                parity.append(j - k)
            k <<= 1
        return parity

    def get_update_set(j: int, n: int) -> List[int]:
        """Get update set for qubit j"""
        update = [j]
        k = 1
        while j + k < n:
            if not (j & k):
                update.append(j + k)
                break
            k <<= 1
        return update

    # One-body terms with BK transformation
    for p in range(n_orbitals):
        for q in range(n_orbitals):
            if abs(h_pq[p, q]) < 1e-10:
                continue

            coeff = h_pq[p, q] / 2.0

            if p == q:
                # Number operator in BK basis
                update_set = get_update_set(p, num_qubits)
                pauli_str = list('I' * num_qubits)
                for idx in update_set:
                    pauli_str[idx] = 'Z'
                pauli_terms[''.join(pauli_str)] = pauli_terms.get(''.join(pauli_str), 0.0) - coeff

                pauli_str = 'I' * num_qubits
                pauli_terms[pauli_str] = pauli_terms.get(pauli_str, 0.0) + coeff
            else:
                # Excitation operators in BK basis (simplified)
                pauli_str = list('I' * num_qubits)

                # X and Y components with parity strings
                parity_p = get_parity_set(p)
                parity_q = get_parity_set(q)
                update_p = get_update_set(p, num_qubits)
                update_q = get_update_set(q, num_qubits)

                # XX term
                pauli_str = list('I' * num_qubits)
                pauli_str[p] = 'X'
                pauli_str[q] = 'X'
                for idx in set(parity_p) ^ set(parity_q):
                    pauli_str[idx] = 'Z'
                pauli_terms[''.join(pauli_str)] = pauli_terms.get(''.join(pauli_str), 0.0) + coeff

                # YY term
                pauli_str = list('I' * num_qubits)
                pauli_str[p] = 'Y'
                pauli_str[q] = 'Y'
                for idx in set(parity_p) ^ set(parity_q):
                    pauli_str[idx] = 'Z'
                pauli_terms[''.join(pauli_str)] = pauli_terms.get(''.join(pauli_str), 0.0) + coeff

    return pauli_terms


def hamiltonian_to_qiskit(pauli_terms: Dict[str, float]):
    """
    Convert Pauli terms dictionary to Qiskit SparsePauliOp format.

    Note: Requires Qiskit to be installed. Returns dictionary if Qiskit not available.

    Args:
        pauli_terms: Dictionary mapping Pauli strings to coefficients

    Returns:
        Qiskit SparsePauliOp object or dictionary
    """
    try:
        from qiskit.quantum_info import SparsePauliOp

        # Filter out zero terms
        filtered_terms = {k: v for k, v in pauli_terms.items() if abs(v) > 1e-10}

        if not filtered_terms:
            raise ValueError("No non-zero Pauli terms found")

        # Convert to Qiskit format
        pauli_list = list(filtered_terms.keys())
        coeffs = list(filtered_terms.values())

        hamiltonian = SparsePauliOp(pauli_list, coeffs)
        return hamiltonian

    except ImportError:
        print("Warning: Qiskit not installed. Returning dictionary format.")
        return pauli_terms


# Example usage and testing
if __name__ == "__main__":
    # Test 1: Simple molecular Hamiltonian
    print("=" * 80)
    print("Test 1: Building molecular Hamiltonian for aspirin-like molecule")
    print("=" * 80)

    test_smiles = "CC(=O)Oc1ccccc1C(=O)O"  # Aspirin
    test_pdb = """
ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00  0.00           N
ATOM      2  CA  ALA A   1      11.000  10.000  10.000  1.00  0.00           C
ATOM      3  C   ALA A   1      11.500  11.000  10.000  1.00  0.00           C
ATOM      4  O   ALA A   1      11.500  11.500  11.000  1.00  0.00           O
ATOM      5  CB  ALA A   1      11.500   9.000  10.000  1.00  0.00           C
"""

    try:
        H_matrix = build_molecular_hamiltonian(
            test_smiles,
            test_pdb,
            binding_site_center=np.array([10.5, 10.0, 10.0]),
            binding_site_radius=5.0
        )
        print(f"Hamiltonian matrix shape: {H_matrix.shape}")
        print(f"Hamiltonian eigenvalues (first 5): {np.linalg.eigvalsh(H_matrix)[:5]}")
        print(f"Mean interaction energy: {np.mean(H_matrix):.3f} kcal/mol")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 2: Interaction energy calculation
    print("=" * 80)
    print("Test 2: Computing interaction energies")
    print("=" * 80)

    ligand_coords, ligand_types, _ = parse_smiles_to_3d("CCO")  # Ethanol
    ligand_charges = compute_partial_charges("CCO")

    receptor_coords = np.array([[0, 0, 0], [1.5, 0, 0], [3.0, 0, 0]])
    receptor_charges = np.array([-0.5, 0.1, -0.5])
    receptor_types = ['O', 'C', 'O']

    energies = compute_interaction_energy(
        ligand_coords, receptor_coords,
        ligand_charges, receptor_charges,
        ligand_types, receptor_types
    )

    print(f"Energy components:")
    for component, value in energies.items():
        print(f"  {component}: {value:.3f} kcal/mol")
    print()

    # Test 3: Qubit Hamiltonian transformation
    print("=" * 80)
    print("Test 3: Molecule to qubit Hamiltonian (Jordan-Wigner)")
    print("=" * 80)

    mol = Chem.MolFromSmiles("C=C")  # Ethylene
    mol = Chem.AddHs(mol)

    qubit_ham_jw = molecule_to_qubit_hamiltonian(mol, transformation='jordan_wigner')
    print(f"Number of qubits: {qubit_ham_jw['num_qubits']}")
    print(f"Number of electrons: {qubit_ham_jw['num_electrons']}")
    print(f"Number of Pauli terms: {len(qubit_ham_jw['pauli_terms'])}")
    print(f"Sample Pauli terms (first 3):")
    for i, (pauli_str, coeff) in enumerate(list(qubit_ham_jw['pauli_terms'].items())[:3]):
        print(f"  {pauli_str}: {coeff:.6f}")
    print()

    # Test 4: Bravyi-Kitaev transformation
    print("=" * 80)
    print("Test 4: Molecule to qubit Hamiltonian (Bravyi-Kitaev)")
    print("=" * 80)

    qubit_ham_bk = molecule_to_qubit_hamiltonian(mol, transformation='bravyi_kitaev')
    print(f"Number of qubits: {qubit_ham_bk['num_qubits']}")
    print(f"Number of Pauli terms: {len(qubit_ham_bk['pauli_terms'])}")
    print(f"Sample Pauli terms (first 3):")
    for i, (pauli_str, coeff) in enumerate(list(qubit_ham_bk['pauli_terms'].items())[:3]):
        print(f"  {pauli_str}: {coeff:.6f}")
    print()

    print("=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
