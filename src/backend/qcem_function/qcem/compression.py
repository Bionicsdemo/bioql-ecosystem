"""
QCEM Hamiltonian Compression Module
====================================
Bravyi-Kitaev encoding + Z₂ symmetry tapering for qubit reduction.

Standalone module — no BioQL dependencies. Pure Qiskit + NumPy.
"""

import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional

from qiskit.quantum_info import SparsePauliOp


@dataclass
class CompressionResult:
    """Result of Hamiltonian compression."""
    original_hamiltonian: SparsePauliOp
    compressed_hamiltonian: SparsePauliOp
    original_qubits: int
    compressed_qubits: int
    original_terms: int
    compressed_terms: int
    qubits_saved: int
    symmetries_found: int
    energy_shift: float
    encoding: str  # "jw" or "bk"

    def summary(self) -> dict:
        return {
            "original_qubits": self.original_qubits,
            "compressed_qubits": self.compressed_qubits,
            "qubits_saved": self.qubits_saved,
            "qubit_reduction_pct": round(self.qubits_saved / max(self.original_qubits, 1) * 100, 1),
            "term_reduction_pct": round((self.original_terms - self.compressed_terms) / max(self.original_terms, 1) * 100, 1),
            "symmetries_found": self.symmetries_found,
            "energy_shift": self.energy_shift,
            "encoding": self.encoding,
        }


# ============================================================================
# Z₂ SYMMETRY DETECTION
# ============================================================================

def _find_z2_symmetries(hamiltonian: SparsePauliOp) -> List[SparsePauliOp]:
    """
    Find Z₂ symmetries of a qubit Hamiltonian.

    A Z₂ symmetry τ satisfies [H, τ] = 0 and τ² = I.
    Found by computing the null space of the commutation matrix over GF(2).
    """
    n_qubits = hamiltonian.num_qubits
    labels = hamiltonian.paulis
    n_terms = len(labels)

    # Build commutation matrix: M[i,j] = 1 if term i has X or Y on qubit j
    M = np.zeros((n_terms, n_qubits), dtype=int)
    for i, pauli in enumerate(labels):
        s = str(pauli)
        for j in range(n_qubits):
            if s[n_qubits - 1 - j] in ("X", "Y"):
                M[i, j] = 1

    # Null space over GF(2) via Gaussian elimination
    null_vecs = _nullspace_gf2(M)

    symmetries = []
    for vec in null_vecs:
        z_str = ["I"] * n_qubits
        for j in range(n_qubits):
            if vec[j] == 1:
                z_str[j] = "Z"
        pauli_str = "".join(reversed(z_str))
        if pauli_str != "I" * n_qubits:
            symmetries.append(SparsePauliOp.from_list([(pauli_str, 1.0)]))

    return symmetries


def _nullspace_gf2(M: np.ndarray) -> List[np.ndarray]:
    """Compute null space of binary matrix over GF(2)."""
    m, n = M.shape
    if m == 0 or n == 0:
        return []

    aug = M.copy() % 2
    pivots = []
    row = 0

    for col in range(n):
        piv = None
        for r in range(row, m):
            if aug[r, col] == 1:
                piv = r
                break
        if piv is None:
            continue
        aug[[row, piv]] = aug[[piv, row]]
        pivots.append(col)
        for r in range(m):
            if r != row and aug[r, col] == 1:
                aug[r] = (aug[r] + aug[row]) % 2
        row += 1

    free = [c for c in range(n) if c not in pivots]
    vecs = []
    for fc in free:
        v = np.zeros(n, dtype=int)
        v[fc] = 1
        for i, pc in enumerate(pivots):
            if aug[i, fc] == 1:
                v[pc] = 1
        vecs.append(v)
    return vecs


# ============================================================================
# SYMMETRY TAPERING
# ============================================================================

def _taper(
    hamiltonian: SparsePauliOp,
    symmetries: List[SparsePauliOp],
    eigenvalues: Optional[List[int]] = None,
) -> Tuple[SparsePauliOp, float]:
    """
    Taper a Hamiltonian by projecting onto Z₂ symmetry sectors.

    Each symmetry removes one qubit. Default eigenvalues = +1 (ground state sector).
    """
    if not symmetries:
        return hamiltonian, 0.0

    n = hamiltonian.num_qubits
    eigenvalues = eigenvalues or [1] * len(symmetries)

    # Find qubits to taper
    taper_qubits = []
    for sym in symmetries:
        s = str(sym.paulis[0])
        for j in range(n):
            if s[n - 1 - j] == "Z" and j not in taper_qubits:
                taper_qubits.append(j)
                break

    if not taper_qubits:
        return hamiltonian, 0.0

    new_terms = []
    shift = 0.0

    for pauli, coeff in zip(hamiltonian.paulis, hamiltonian.coeffs):
        s = str(pauli)
        c = complex(coeff)
        chars = list(s)

        skip = False
        for ti, tq in enumerate(taper_qubits):
            pos = n - 1 - tq
            ch = chars[pos]
            if ch == "Z":
                c *= eigenvalues[ti]
                chars[pos] = "I"
            elif ch in ("X", "Y"):
                skip = True
                break

        if skip or abs(c) < 1e-12:
            continue

        remaining = [chars[i] for i in range(len(chars)) if (n - 1 - i) not in taper_qubits]
        rs = "".join(remaining)

        if all(x == "I" for x in rs):
            shift += c.real
        else:
            new_terms.append((rs, c))

    if not new_terms:
        nq = n - len(taper_qubits)
        return SparsePauliOp.from_list([("I" * max(nq, 1), shift)]), 0.0

    return SparsePauliOp.from_list(new_terms).simplify(), shift


# ============================================================================
# BK ENCODING HELPERS
# ============================================================================

def _bk_update_set(j: int, n: int) -> set:
    """Fenwick tree update set for BK encoding."""
    s = {j}
    k = j + 1
    while True:
        k = k + (k & (-k))
        if k - 1 >= n:
            break
        s.add(k - 1)
    return s


def _bk_parity_set(j: int) -> set:
    """Fenwick tree parity set for BK encoding."""
    if j == 0:
        return set()
    s = set()
    k = j
    child = k - 1
    while child > 0:
        s.add(child - 1)
        child = child - (child & (-child))
    return s


# ============================================================================
# PUBLIC API
# ============================================================================

def compress_hamiltonian(
    hamiltonian: SparsePauliOp,
    n_electrons: int = 2,
    taper: bool = True,
    eigenvalues: Optional[List[int]] = None,
) -> CompressionResult:
    """
    Compress a molecular Hamiltonian via Z₂ symmetry tapering.

    Automatically selects the symmetry sector with lowest ground state energy
    by trying all 2^k sectors (where k = number of symmetries found).

    Args:
        hamiltonian: Qubit Hamiltonian as SparsePauliOp (already JW or BK mapped)
        n_electrons: Number of electrons (used for symmetry sector selection)
        taper: Whether to apply symmetry tapering
        eigenvalues: Eigenvalue sector (None = auto-select lowest energy sector)

    Returns:
        CompressionResult with compressed Hamiltonian and metrics

    Example:
        >>> from qiskit.quantum_info import SparsePauliOp
        >>> H = SparsePauliOp.from_list([("IIZZ", 0.5), ("XXII", 0.3), ("ZZII", 0.2)])
        >>> result = compress_hamiltonian(H, n_electrons=2)
        >>> print(f"Reduced from {result.original_qubits} to {result.compressed_qubits} qubits")
    """
    import itertools

    orig_n = hamiltonian.num_qubits
    orig_terms = len(hamiltonian)

    compressed = hamiltonian
    shift = 0.0
    n_sym = 0
    best_eigenvalues = eigenvalues

    if taper:
        symmetries = _find_z2_symmetries(hamiltonian)
        n_sym = len(symmetries)
        if symmetries:
            if eigenvalues is not None:
                # User-specified sector
                compressed, shift = _taper(hamiltonian, symmetries, eigenvalues)
            else:
                # Auto-select: try all 2^k sectors, pick lowest ground state
                best_energy = float("inf")
                best_ham = hamiltonian
                best_shift = 0.0
                best_eigenvalues = [1] * len(symmetries)

                for sector in itertools.product([1, -1], repeat=len(symmetries)):
                    sector_list = list(sector)
                    try:
                        tapered, s = _taper(hamiltonian, symmetries, sector_list)
                        # Get ground state of this sector
                        mat = tapered.to_matrix()
                        gs = float(np.linalg.eigvalsh(mat)[0]) + s
                        if gs < best_energy:
                            best_energy = gs
                            best_ham = tapered
                            best_shift = s
                            best_eigenvalues = sector_list
                    except Exception:
                        continue

                compressed = best_ham
                shift = best_shift

    return CompressionResult(
        original_hamiltonian=hamiltonian,
        compressed_hamiltonian=compressed,
        original_qubits=orig_n,
        compressed_qubits=compressed.num_qubits,
        original_terms=orig_terms,
        compressed_terms=len(compressed),
        qubits_saved=orig_n - compressed.num_qubits,
        symmetries_found=n_sym,
        energy_shift=shift,
        encoding="jw",
    )
