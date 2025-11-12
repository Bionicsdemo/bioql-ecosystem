"""
Molecular Benchmarks for BioQL Quantum Chemistry

This module provides validated test cases for quantum chemistry calculations,
comparing against known experimental and theoretical results.

Benchmark Molecules:
- H2: Simplest molecule (validation)
- LiH: Ionic bond (different from H2)
- H2O: Bent geometry, multiple bonds
- NH3: Pyramidal geometry
- CH4: Tetrahedral geometry

Each benchmark includes:
- Experimental geometry
- Known HF energy
- Known correlation energy (if available)
- Expected number of qubits
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from .quantum_chemistry import QuantumMolecule, build_molecular_hamiltonian, validate_hamiltonian


@dataclass
class BenchmarkResult:
    """Results from a molecular benchmark calculation."""
    molecule_name: str
    n_qubits: int
    hf_energy_calc: float  # Calculated HF energy (Hartree)
    hf_energy_ref: Optional[float]  # Reference HF energy (Hartree)
    ground_energy_calc: float  # Calculated ground state (Hartree)
    correlation_energy: float  # Correlation energy (Hartree)
    error_vs_ref: Optional[float]  # Error vs reference (kcal/mol)
    validated: bool
    pauli_terms_count: int


# Benchmark molecules with experimental geometries and reference energies
BENCHMARK_MOLECULES = {
    'H2': {
        'geometry': [
            ('H', (0.0, 0.0, 0.0)),
            ('H', (0.0, 0.0, 0.74))  # Experimental bond length (Å)
        ],
        'charge': 0,
        'multiplicity': 1,
        'basis': 'sto-3g',
        'hf_energy_ref': -1.117,  # Reference HF/sto-3g (Hartree)
        'description': 'Hydrogen molecule - simplest test case'
    },

    'LiH': {
        'geometry': [
            ('Li', (0.0, 0.0, 0.0)),
            ('H', (0.0, 0.0, 1.596))  # Experimental bond length (Å)
        ],
        'charge': 0,
        'multiplicity': 1,
        'basis': 'sto-3g',
        'hf_energy_ref': -7.863,  # Reference HF/sto-3g (Hartree)
        'description': 'Lithium hydride - ionic bond'
    },

    'H2O': {
        'geometry': [
            ('O', (0.0, 0.0, 0.0)),
            ('H', (0.0, 0.757, 0.587)),  # Experimental geometry
            ('H', (0.0, -0.757, 0.587))  # 104.5° angle
        ],
        'charge': 0,
        'multiplicity': 1,
        'basis': 'sto-3g',
        'hf_energy_ref': -74.963,  # Reference HF/sto-3g (Hartree)
        'description': 'Water molecule - bent geometry'
    },

    'NH3': {
        'geometry': [
            ('N', (0.0, 0.0, 0.0)),
            ('H', (0.0, 0.937, 0.383)),
            ('H', (0.812, -0.469, 0.383)),
            ('H', (-0.812, -0.469, 0.383))
        ],
        'charge': 0,
        'multiplicity': 1,
        'basis': 'sto-3g',
        'hf_energy_ref': -55.454,  # Reference HF/sto-3g (Hartree)
        'description': 'Ammonia - pyramidal geometry'
    },
}


def run_benchmark(
    molecule_name: str,
    basis: str = 'sto-3g',
    transformation: str = 'jordan_wigner',
    verbose: bool = True
) -> BenchmarkResult:
    """
    Run quantum chemistry benchmark for a specific molecule.

    Args:
        molecule_name: Name of molecule from BENCHMARK_MOLECULES
        basis: Basis set (default: sto-3g)
        transformation: Qubit mapping (jordan_wigner or bravyi_kitaev)
        verbose: Print detailed results

    Returns:
        BenchmarkResult with calculated and reference values
    """
    if molecule_name not in BENCHMARK_MOLECULES:
        raise ValueError(f"Unknown molecule: {molecule_name}. Available: {list(BENCHMARK_MOLECULES.keys())}")

    mol_data = BENCHMARK_MOLECULES[molecule_name]

    # Create molecule
    molecule = QuantumMolecule(
        geometry=mol_data['geometry'],
        charge=mol_data['charge'],
        multiplicity=mol_data['multiplicity'],
        basis=basis,
        name=molecule_name
    )

    if verbose:
        print(f"\n{'='*80}")
        print(f"Benchmark: {molecule_name}")
        print(f"Description: {mol_data['description']}")
        print(f"Basis: {basis}")
        print(f"{'='*80}")

    # Build Hamiltonian
    ham_data = build_molecular_hamiltonian(molecule, transformation=transformation)

    # Validate
    validations = validate_hamiltonian(ham_data)

    # Extract results
    hf_calc = ham_data['hf_energy']
    ground_calc = ham_data['ground_state_energy']
    correlation = ground_calc - hf_calc
    hf_ref = mol_data.get('hf_energy_ref')

    # Calculate error
    error_kcal = None
    if hf_ref is not None:
        error_hartree = abs(hf_calc - hf_ref)
        error_kcal = error_hartree * 627.509  # Convert to kcal/mol

    result = BenchmarkResult(
        molecule_name=molecule_name,
        n_qubits=ham_data['n_qubits'],
        hf_energy_calc=hf_calc,
        hf_energy_ref=hf_ref,
        ground_energy_calc=ground_calc,
        correlation_energy=correlation,
        error_vs_ref=error_kcal,
        validated=validations['physically_valid'],
        pauli_terms_count=len(ham_data['pauli_terms'])
    )

    if verbose:
        print(f"\n📊 Results:")
        print(f"   Qubits required: {result.n_qubits}")
        print(f"   Pauli terms: {result.pauli_terms_count}")
        print(f"\n⚡ Energies (Hartree):")
        print(f"   HF (calculated): {hf_calc:.6f}")
        if hf_ref:
            print(f"   HF (reference):  {hf_ref:.6f}")
            print(f"   Error: {error_kcal:.4f} kcal/mol")
        print(f"   Ground state: {ground_calc:.6f}")
        print(f"   Correlation: {correlation:.6f} ({correlation * 627.509:.2f} kcal/mol)")
        print(f"\n✅ Validation: {'PASSED' if result.validated else 'FAILED'}")

        # Chemical accuracy check
        if error_kcal is not None:
            chemical_accuracy = 1.6  # kcal/mol
            if error_kcal < chemical_accuracy:
                print(f"   ✅ Within chemical accuracy ({error_kcal:.4f} < {chemical_accuracy} kcal/mol)")
            else:
                print(f"   ⚠️  Outside chemical accuracy ({error_kcal:.4f} > {chemical_accuracy} kcal/mol)")

    return result


def run_all_benchmarks(
    basis: str = 'sto-3g',
    transformation: str = 'jordan_wigner'
) -> Dict[str, BenchmarkResult]:
    """
    Run all available benchmarks and return summary.

    Args:
        basis: Basis set for calculations
        transformation: Qubit mapping method

    Returns:
        Dictionary of molecule_name -> BenchmarkResult
    """
    results = {}

    print("\n" + "="*80)
    print("BioQL Quantum Chemistry Benchmark Suite")
    print("="*80)

    for mol_name in BENCHMARK_MOLECULES:
        try:
            result = run_benchmark(mol_name, basis=basis, transformation=transformation, verbose=True)
            results[mol_name] = result
        except Exception as e:
            print(f"\n❌ Error benchmarking {mol_name}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(f"\n{'Molecule':<10} {'Qubits':<8} {'HF Error (kcal/mol)':<20} {'Validated':<10}")
    print("-" * 80)

    for mol_name, result in results.items():
        error_str = f"{result.error_vs_ref:.4f}" if result.error_vs_ref is not None else "N/A"
        validated_str = "✅ PASS" if result.validated else "❌ FAIL"
        print(f"{mol_name:<10} {result.n_qubits:<8} {error_str:<20} {validated_str:<10}")

    return results


if __name__ == "__main__":
    # Run all benchmarks
    results = run_all_benchmarks(basis='sto-3g', transformation='jordan_wigner')

    print("\n" + "="*80)
    print("✅ Benchmark suite completed")
    print("="*80)
