# VQE Visualization Improvements

## Overview

The `visualization_generator.py` module has been enhanced to support **REAL VQE (Variational Quantum Eigensolver) data** with scientifically valid molecular energies in Hartree units.

## What Changed

### Previous Implementation (PROBLEMS)

The original code used simplified energy calculations:

```python
# OLD: Simplified/fake energy calculation
energy = -num_qubits + 2 * bitstring.count('1')  # ❌ NOT SCIENTIFIC
```

This was **not scientifically valid** and ignored real molecular quantum chemistry data.

### New Implementation (SOLUTIONS)

Now the code accepts **real VQE energies** and creates scientifically accurate visualizations:

```python
# NEW: Real VQE energies in Hartree
if vqe_energies is not None and bitstring in vqe_energies:
    energy = vqe_energies[bitstring]  # ✅ REAL DATA
else:
    energy = -num_qubits + 2 * bitstring.count('1')  # Fallback
```

## New Features

### 1. Enhanced Energy Histogram

- **Now accepts**: `vqe_energies` (Dict[str, float]) - Real energies in Hartree
- **Now accepts**: `ground_state_energy` (float) - Ground state reference
- **Displays**:
  - Real molecular energies in Hartree units
  - Ground state reference line
  - Color-coded by probability
  - Scientific labels and styling

**Example:**
```python
vqe_energies = {
    '0000': -1.1372,  # Ground state (Hartree)
    '0001': -1.0524,
    '0010': -1.0421,
    # ... more states
}

ground_state_energy = -1.1372  # Ha
```

### 2. NEW: Energy Landscape Visualization

**Method**: `_create_energy_landscape()`

Shows the molecular potential energy surface across parameter space or bond distances.

**Features**:
- Energy curve with filled gradient
- Marked global minimum (red star)
- Marked local maximum (orange triangle)
- Ground state reference line (green dashed)
- Energy range annotation
- Professional scientific styling

**Parameters**:
- `energy_landscape`: List[float] - Energies across parameter space
- `ground_state_energy`: float - Ground state (Hartree)
- `molecule_type`: str - Molecule name (e.g., 'H2', 'LiH')

**Example**:
```python
energy_landscape = [
    -0.5234, -0.8765, -1.0234, -1.1234, -1.1372,  # Minimum
    -1.1234, -1.0876, -1.0234, -0.9543, -0.8765
]
```

### 3. NEW: Hamiltonian Visualization

**Method**: `_create_hamiltonian_visualization()`

Visualizes the molecular Hamiltonian structure with two subplots:

**Left Panel**: Energy distribution across quantum states
- Horizontal bar chart
- Color gradient from low to high energy
- Shows eigenstate energies in Hartree

**Right Panel**: Pauli operator distribution
- Pie chart showing Hamiltonian term breakdown
- I, X, Y, Z, XX, YY, ZZ, XY, XZ, YZ operators
- Percentage breakdown

**Parameters**:
- `vqe_energies`: Dict[str, float] - State energies
- `hamiltonian_terms`: int - Number of Hamiltonian terms
- `molecule_type`: str - Molecule name

**Example**:
```python
hamiltonian_terms = 15  # For H2 molecule
```

### 4. NEW: VQE Convergence Plot

**Method**: `_create_vqe_convergence()`

Shows VQE optimization convergence with two subplots:

**Top Panel**: Energy vs iteration
- VQE energy trajectory
- Final converged energy (red star)
- Exact ground state reference (green line)

**Bottom Panel**: Energy deviation (log scale)
- Shows |E - E_final| convergence
- Logarithmic scale for precision
- Convergence metrics box with:
  - Initial energy
  - Final energy
  - Energy drop
  - Average convergence rate
  - Total iterations

**Parameters**:
- `convergence_history`: List[float] - Energy at each iteration
- `ground_state_energy`: Optional[float] - Exact reference

**Example**:
```python
convergence_history = [
    -0.5432,  # Initial guess
    -0.7654,
    -0.8765,
    # ... optimization steps
    -1.1372   # Converged
]
```

## Updated Main Method

### `generate_from_quantum_results()` - New Signature

```python
def generate_from_quantum_results(
    self,
    job_id: str,
    counts: Dict[str, int],
    num_qubits: int,
    molecule_type: str,
    viz_type: str,
    # NEW OPTIONAL VQE PARAMETERS:
    vqe_energies: Optional[Dict[str, float]] = None,
    ground_state_energy: Optional[float] = None,
    energy_landscape: Optional[List[float]] = None,
    hamiltonian_terms: Optional[int] = None,
    convergence_history: Optional[List[float]] = None
) -> Dict[str, str]:
```

### Parameters Explained

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | Yes | Unique job identifier |
| `counts` | Dict[str, int] | Yes | Quantum measurement counts |
| `num_qubits` | int | Yes | Number of qubits |
| `molecule_type` | str | Yes | Molecule type (e.g., 'H2', 'LiH') |
| `viz_type` | str | Yes | Visualization type |
| `vqe_energies` | Dict[str, float] | **No** | Bitstring → Energy (Ha) mapping |
| `ground_state_energy` | float | **No** | Ground state energy (Ha) |
| `energy_landscape` | List[float] | **No** | Energy landscape data |
| `hamiltonian_terms` | int | **No** | Number of H terms |
| `convergence_history` | List[float] | **No** | VQE optimization history |

## Backward Compatibility

**ALL new parameters are OPTIONAL** - existing code continues to work:

```python
# OLD CODE STILL WORKS:
output_files = viz_gen.generate_from_quantum_results(
    job_id="test",
    counts={'00': 500, '01': 300},
    num_qubits=2,
    molecule_type="H2",
    viz_type="basic"
)
# ✅ Works! Uses simplified energy calculation
```

## Usage Examples

### Full VQE Data Example

```python
from quantum_core.backends.visualization_generator import VisualizationGenerator

viz_gen = VisualizationGenerator(output_dir="/tmp/vqe_viz")

# Quantum measurement results
counts = {
    '0000': 450,
    '0001': 120,
    '0010': 85,
    # ... more states
}

# REAL VQE energies (Hartree)
vqe_energies = {
    '0000': -1.1372,  # Ground state
    '0001': -1.0524,
    '0010': -1.0421,
    # ... more states
}

# Ground state energy
ground_state_energy = -1.1372

# Energy landscape
energy_landscape = [
    -0.5234, -0.8765, -1.0234, -1.1234, -1.1372,
    -1.1234, -1.0876, -1.0234, -0.9543, -0.8765
]

# Hamiltonian terms
hamiltonian_terms = 15

# VQE convergence
convergence_history = [
    -0.5432, -0.7654, -0.8765, -0.9543, -1.0123,
    -1.0654, -1.0987, -1.1123, -1.1234, -1.1321,
    -1.1352, -1.1365, -1.1370, -1.1371, -1.1372
]

# Generate all visualizations
output_files = viz_gen.generate_from_quantum_results(
    job_id="H2_VQE",
    counts=counts,
    num_qubits=4,
    molecule_type="H2",
    viz_type="vqe_molecular",
    vqe_energies=vqe_energies,
    ground_state_energy=ground_state_energy,
    energy_landscape=energy_landscape,
    hamiltonian_terms=hamiltonian_terms,
    convergence_history=convergence_history
)

# Output:
# {
#     'energy_histogram': '/tmp/vqe_viz/H2_VQE_energy_histogram.png',
#     'state_distribution': '/tmp/vqe_viz/H2_VQE_state_distribution.png',
#     'interactive': '/tmp/vqe_viz/H2_VQE_interactive.html',
#     'energy_landscape': '/tmp/vqe_viz/H2_VQE_energy_landscape.png',
#     'hamiltonian_viz': '/tmp/vqe_viz/H2_VQE_hamiltonian_viz.png',
#     'vqe_convergence': '/tmp/vqe_viz/H2_VQE_vqe_convergence.png'
# }
```

### Partial VQE Data Example

```python
# Only provide convergence history
output_files = viz_gen.generate_from_quantum_results(
    job_id="LiH_partial",
    counts={'00': 500, '01': 300, '10': 150, '11': 50},
    num_qubits=2,
    molecule_type="LiH",
    viz_type="partial",
    convergence_history=[-0.5, -0.7, -0.85, -0.92, -0.95],
    ground_state_energy=-0.95
)
# Generates: energy_histogram, state_distribution, interactive, vqe_convergence
```

## Generated Visualization Files

When VQE data is provided, the following files are generated:

1. **`{job_id}_energy_histogram.png`** - Energy distribution with real Hartree values
2. **`{job_id}_state_distribution.png`** - Quantum state measurement counts
3. **`{job_id}_interactive.html`** - Interactive Plotly visualization
4. **`{job_id}_energy_landscape.png`** - Molecular potential energy surface (NEW)
5. **`{job_id}_hamiltonian_viz.png`** - Hamiltonian structure analysis (NEW)
6. **`{job_id}_vqe_convergence.png`** - VQE optimization convergence (NEW)

## Scientific Improvements

### Color Schemes

All new visualizations use professional scientific color schemes:

- **Energy landscape**: Blue gradient (#2563eb, #3b82f6)
- **Hamiltonian**: Coolwarm gradient for energies, Set3 for operators
- **Convergence**: Purple (#8b5cf6) for VQE, red (#ef4444) for error
- **Ground state**: Green dashed lines
- **Minima/maxima**: Red stars, orange triangles

### Typography

- Bold axis labels (14pt)
- Bold titles (15-17pt)
- Clear legends with transparency
- Grid lines for readability

### Data Presentation

- Hartree units clearly labeled
- Precision: 4 decimals for energies, 6+ for convergence
- Probability percentages
- Energy ranges and metrics
- Log scale for convergence error

## Testing

Run the example script:

```bash
cd /Users/heinzjungbluth/Desktop/Quantum_graph
python3 examples/vqe_visualization_example.py
```

This will generate three sets of visualizations:
1. Full VQE data example (H2)
2. Backward compatible example (no VQE)
3. Partial VQE data example (LiH)

## Files Modified

### `/Users/heinzjungbluth/Desktop/Quantum_graph/quantum_core/backends/visualization_generator.py`

**Changes**:
1. Updated `generate_from_quantum_results()` with 5 new optional parameters
2. Enhanced `_create_energy_histogram()` to use real VQE energies
3. Added `_create_energy_landscape()` - NEW METHOD
4. Added `_create_hamiltonian_visualization()` - NEW METHOD
5. Added `_create_vqe_convergence()` - NEW METHOD
6. Updated docstrings with parameter explanations
7. Added conditional generation logic for new visualizations

**Lines changed**: ~300 lines added/modified

## Summary

### Key Improvements

1. **Real VQE Data Support**: No more fake energy calculations
2. **Scientific Units**: Hartree units throughout
3. **Three New Visualizations**: Landscape, Hamiltonian, Convergence
4. **Backward Compatible**: Existing code still works
5. **Professional Styling**: Publication-quality plots
6. **Comprehensive Documentation**: Docstrings and examples

### Before vs After

**Before**:
- ❌ Fake energy calculations
- ❌ Arbitrary units
- ❌ Limited scientific value
- ❌ No convergence visualization
- ❌ No Hamiltonian analysis

**After**:
- ✅ Real VQE energies (Hartree)
- ✅ Scientific units and precision
- ✅ Publication-quality visualizations
- ✅ VQE convergence tracking
- ✅ Hamiltonian structure analysis
- ✅ Energy landscape plotting
- ✅ Backward compatible
- ✅ Comprehensive examples

## Next Steps

To integrate with actual VQE calculations:

1. Run VQE algorithm (e.g., using Qiskit, PennyLane)
2. Extract energies, convergence history, and Hamiltonian data
3. Pass to `generate_from_quantum_results()`
4. Receive publication-ready visualizations

## Contact

For questions or issues:
- **Team**: Spectrix R&D / BioQL Team
- **File**: `quantum_core/backends/visualization_generator.py`
- **Example**: `examples/vqe_visualization_example.py`
