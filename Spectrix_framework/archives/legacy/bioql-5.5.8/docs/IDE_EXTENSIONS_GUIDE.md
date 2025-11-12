# BioQL IDE Extensions Installation Guide

## Overview

BioQL provides comprehensive IDE extensions for both Cursor and Windsurf IDEs, enabling natural language quantum programming for bioinformatics applications. This guide covers installation, configuration, and usage of both extensions.

## 🚀 Quick Installation

### Prerequisites
```bash
# Install BioQL framework
pip install bioql

# Verify installation
bioql check
```

### Cursor IDE Extension
```bash
# Automatic installation
bioql install cursor

# Manual verification
cursor --version
```

### Windsurf IDE Plugin
```bash
# Automatic installation
bioql install windsurf

# Manual verification (if windsurf command is available)
windsurf --version
```

## 📁 Extension Structure

### Cursor Extension (`ide_extensions/cursor/`)
```
cursor/
├── package.json                 # Extension manifest
├── src/
│   └── extension.js             # Main extension code
├── syntaxes/
│   ├── bioql.tmLanguage.json    # BioQL syntax highlighting
│   └── python-bioql.tmLanguage.json  # Python injection
├── snippets/
│   ├── bioql-snippets.json      # BioQL code snippets
│   └── python-bioql-snippets.json    # Python snippets
├── language-configuration/
│   └── bioql-configuration.json # Language configuration
├── icons/                       # Extension icons
└── README.md                    # Extension documentation
```

### Windsurf Plugin (`ide_extensions/windsurf/`)
```
windsurf/
├── plugin.xml                   # Plugin manifest
├── src/
│   ├── BioQLLanguage.java       # Language definition
│   ├── BioQLFileType.java       # File type handler
│   ├── completion/              # Code completion
│   ├── actions/                 # Plugin actions
│   └── services/                # Background services
├── syntaxes/                    # Syntax highlighting
├── snippets/                    # Code templates
├── icons/                       # Plugin icons
└── README.md                    # Plugin documentation
```

## 🔧 Manual Installation

### Cursor IDE Extension

1. **Prerequisites Check**
   ```bash
   # Check if Cursor is installed
   cursor --version

   # Check Node.js (optional for development)
   node --version
   npm --version
   ```

2. **Manual Installation Steps**
   ```bash
   # Navigate to BioQL directory
   cd /path/to/bioql

   # Run installation script
   python install_cursor_extension.py
   ```

3. **Extension Directory Location**
   - **Windows**: `%APPDATA%\Cursor\User\extensions\bioql-cursor-1.0.0`
   - **macOS**: `~/.cursor/extensions/bioql-cursor-1.0.0`
   - **Linux**: `~/.cursor/extensions/bioql-cursor-1.0.0`

### Windsurf IDE Plugin

1. **Prerequisites Check**
   ```bash
   # Check if Java is installed (for compilation)
   java -version
   javac -version
   ```

2. **Manual Installation Steps**
   ```bash
   # Navigate to BioQL directory
   cd /path/to/bioql

   # Run installation script
   python install_windsurf_extension.py
   ```

3. **Plugin Directory Location**
   - **Windows**: `%APPDATA%\Windsurf\plugins\bioql-windsurf`
   - **macOS**: `~/Library/Application Support/Windsurf/plugins/bioql-windsurf`
   - **Linux**: `~/.windsurf/plugins/bioql-windsurf`

## 🎯 Features Comparison

| Feature | Cursor Extension | Windsurf Plugin |
|---------|------------------|-----------------|
| **Syntax Highlighting** | ✅ Full BioQL + Python | ✅ Full BioQL + Java integration |
| **Code Completion** | ✅ Quantum + Bio terms | ✅ AI-enhanced completion |
| **Live Preview** | ✅ Quantum circuits | ✅ Advanced visualization |
| **Error Detection** | ✅ Basic validation | ✅ Advanced diagnostics |
| **Debugging** | ✅ Basic debugging | ✅ Quantum state inspection |
| **AI Integration** | ❌ Basic | ✅ Full Windsurf AI |
| **Research Tools** | ❌ Limited | ✅ Paper integration |
| **Code Snippets** | ✅ 12 snippets | ✅ 20+ templates |
| **Documentation** | ✅ Hover docs | ✅ Research references |

## 🛠️ Configuration

### Cursor Extension Settings

Access via: `File → Preferences → Settings → Extensions → BioQL`

```json
{
  "bioql.quantumBackend": "qasm_simulator",
  "bioql.defaultShots": 1024,
  "bioql.enableLivePreview": true,
  "bioql.bioContextAware": true,
  "bioql.debugMode": false,
  "bioql.autoSave": true
}
```

### Windsurf Plugin Settings

Access via: `Settings → Plugins → BioQL Language Support`

- **Research Context**: Enable biological research context
- **AI Optimization**: Automatic code optimization level
- **Paper Integration**: Auto-cite research papers
- **Quantum Backend**: AI-recommended backend selection
- **Biological Validation**: AI plausibility checking

## 📝 Usage Examples

### Basic BioQL File (.bql)

```bioql
# example.bql - Quantum protein folding analysis

# Create Bell state for quantum entanglement study
create bell state with 2 qubits
apply hadamard gate to qubit 0
apply cnot gate from qubit 0 to qubit 1
measure all qubits

# Analyze protein structure
analyze protein hemoglobin folding
simulate 100 amino acid interactions
optimize energy landscape using qaoa algorithm
measure folding stability

# DNA sequence alignment
align dna sequences ATCGATCGATCG and ATCGATCGATCG
use quantum fourier transform for pattern matching
find optimal alignment with 95% similarity
measure alignment score
```

### Python Integration

```python
# quantum_bio.py - BioQL in Python

from bioql import quantum, QuantumResult

# Natural language quantum programming
def analyze_protein_folding():
    result = quantum(
        "analyze protein insulin folding with 50 amino acids",
        shots=2048,
        backend="qasm_simulator"
    )

    if result.success:
        print(f"Folding energy: {result.energy}")
        print(f"Biological insight: {result.bio_interpretation}")
        return result
    else:
        print(f"Analysis failed: {result.error}")
        return None

# Drug discovery simulation
def simulate_drug_binding():
    result = quantum(
        "simulate drug aspirin binding to cyclooxygenase protein",
        shots=1024,
        optimize=True
    )

    return result.counts

# Run analysis
if __name__ == "__main__":
    protein_result = analyze_protein_folding()
    drug_result = simulate_drug_binding()
```

## 🔍 Code Snippets

### Available Snippets (Both IDEs)

1. **`bell`** - Bell state creation
2. **`protein`** - Protein folding analysis
3. **`dna`** - DNA sequence processing
4. **`drug`** - Drug binding simulation
5. **`circuit`** - General quantum circuit
6. **`enzyme`** - Enzyme catalysis modeling
7. **`qft`** - Quantum Fourier Transform
8. **`error`** - Quantum error correction
9. **`superposition`** - Quantum superposition
10. **`entangle`** - Quantum entanglement
11. **`orbital`** - Molecular orbital calculation
12. **`phylogeny`** - Phylogenetic analysis

### Cursor-Specific Python Snippets

1. **`bioql-import`** - Import BioQL modules
2. **`quantum`** - Quantum function call
3. **`bioql-protein`** - Protein analysis in Python
4. **`bioql-dna`** - DNA processing in Python
5. **`bioql-drug`** - Drug discovery in Python
6. **`bioql-error`** - Error handling
7. **`bioql-batch`** - Batch processing
8. **`bioql-viz`** - Result visualization

## 🎮 Keyboard Shortcuts

### Cursor Extension
- **`Ctrl+Shift+Q`** (Cmd+Shift+Q on Mac): Run quantum code
- **`Ctrl+Shift+V`** (Cmd+Shift+V on Mac): Visualize circuit
- **`Ctrl+Space`**: Trigger autocompletion
- **`F12`**: Go to definition
- **`Shift+F12`**: Find all references

### Windsurf Plugin
- **`Ctrl+Shift+Q`**: Run quantum code with AI analysis
- **`Ctrl+Shift+V`**: Visualize circuit with AI insights
- **`Ctrl+Shift+A`**: Ask AI about code
- **`Ctrl+Shift+O`**: AI-powered optimization
- **`Alt+Enter`**: Show intention actions

## 🔧 Troubleshooting

### Common Issues

#### Extension Not Loading
```bash
# Check BioQL installation
bioql check

# Reinstall extension
bioql install cursor  # or windsurf

# Check IDE version
cursor --version  # Should be 1.74.0+
```

#### Syntax Highlighting Not Working
1. Check file extension is `.bql` or `.bioql`
2. Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"
3. Verify extension is enabled in settings

#### Quantum Code Execution Fails
```bash
# Test BioQL directly
python -c "from bioql import quantum; print(quantum('test', shots=10))"

# Check quantum backend
bioql quantum "create bell state" --backend qasm_simulator

# Verify dependencies
pip install qiskit qiskit-aer
```

#### Autocompletion Not Appearing
1. Enable "Bio Context Aware" in settings
2. Check language mode is set to "BioQL"
3. Try manual trigger with `Ctrl+Space`
4. Restart IDE

### Getting Help

#### Cursor Extension
- Check extension output: `View → Output → BioQL`
- Enable debug mode in settings
- Visit: https://github.com/bioql/bioql-cursor-extension

#### Windsurf Plugin
- Check plugin logs: `Help → Show Log in Explorer`
- Enable AI diagnostics in settings
- Visit: https://github.com/bioql/bioql-windsurf-plugin

#### General BioQL Support
- Documentation: https://bioql.org/docs
- Discord: https://discord.gg/bioql
- GitHub Issues: https://github.com/bioql/bioql/issues

## 🚀 Advanced Usage

### Research Workflow (Windsurf)

1. **Literature Review**
   ```
   AI: "Find papers on quantum protein folding algorithms"
   → Automatically cites relevant research
   → Suggests quantum approaches
   ```

2. **Code Development**
   ```bioql
   # AI suggests optimal algorithms for your research goal
   analyze protein [AI: suggests specific proteins]
   use [AI: recommends VQE vs QAOA] algorithm
   optimize [AI: suggests parameters]
   ```

3. **Result Analysis**
   ```
   AI: "Your results match Smith et al. (2023) within 5% accuracy"
   → Automatic validation against literature
   → Suggests publication opportunities
   ```

### Custom Backend Integration

```python
# custom_backend.py
from bioql import QuantumBackend

class MyQuantumBackend(QuantumBackend):
    def execute(self, circuit, shots):
        # Custom quantum execution logic
        return results

# Register backend
bioql.register_backend("my_backend", MyQuantumBackend())

# Use in IDE
result = quantum("analyze protein", backend="my_backend")
```

## 🔄 Updates and Maintenance

### Automatic Updates
- Extensions check for updates automatically
- BioQL framework updates: `pip install --upgrade bioql`

### Manual Updates
```bash
# Update BioQL
pip install --upgrade bioql

# Reinstall extensions
bioql install cursor
bioql install windsurf
```

### Version Compatibility
- **Cursor**: Requires VS Code engine 1.74.0+
- **Windsurf**: Requires IntelliJ platform 223+
- **BioQL**: Python 3.8+ with Qiskit 0.45.0+

## 📊 Performance Optimization

### Cursor Extension
- Enable/disable live preview based on file size
- Adjust autocompletion trigger delay
- Use local quantum simulator for development

### Windsurf Plugin
- Configure AI assistance level
- Optimize quantum backend selection
- Enable/disable research paper integration

## 🤝 Contributing

### Extension Development
1. Fork the repository
2. Set up development environment
3. Make changes and test locally
4. Submit pull request with documentation

### Reporting Issues
1. Check existing issues first
2. Provide IDE version and OS details
3. Include BioQL version: `bioql --version`
4. Attach relevant log files

---

**🎉 Ready to start quantum bioinformatics programming!**

Visit [bioql.org](https://bioql.org) for tutorials, examples, and research collaborations.