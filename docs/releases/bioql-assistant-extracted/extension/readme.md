# BioQL Code Assistant v4.0 🧬⚛️

**Interactive AI Agent for BioQL 5.0.1**

Generate quantum code with automatic Qualtran visualizations, Quantum Error Correction (QEC), and multi-backend execution support.

---

## ✨ Features

### 🆕 New in v4.0.0

#### 📊 Automatic Qualtran Visualizations
- **Every experiment generates professional graphs** automatically
- Measurement histograms with percentages
- Circuit diagrams with ASCII art
- QEC resource overhead analysis
- High-resolution PNG output (300 DPI)
- Saved to `bioql_visualizations/` directory

#### 🔧 Interactive Parameter Collection
- Agent **asks for missing parameters** before generating code
- Collects: qubits, backend, QEC type, shots, hardware/simulator
- Maintains conversation state across requests
- Natural language responses accepted

#### 🛡️ Quantum Error Correction (QEC)
- **Surface Code** - Best for large circuits (overhead: (2d-1)²)
- **Steane Code** - 7:1 qubit overhead, good for medium tasks
- **Shor Code** - 9:1 qubit overhead, simplest
- Automatic physical qubit calculation
- QEC cost estimation in comments

#### 🌐 Multi-Backend Support
- **AWS Braket** - SV1 simulator, TN1, IonQ/Rigetti QPUs
- **IBM Quantum** - Up to 133 qubits (Torino)
- **IonQ** - Trapped-ion quantum computers
- **Simulator** - Local fast simulation

### 🎯 Core Capabilities

- ✅ Generate quantum code from natural language
- ✅ Fix and optimize existing code
- ✅ Explain complex quantum circuits
- ✅ Run on real quantum hardware
- ✅ Interactive chat interface (@bioql)
- ✅ Inline code completions
- ✅ Autonomous code improvements

---

## 📦 Installation

### From VSIX File
1. Download `bioql-assistant-4.0.0.vsix`
2. Open VS Code
3. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
4. Type: **Extensions: Install from VSIX**
5. Select the downloaded `.vsix` file

### From Command Line
```bash
code --install-extension bioql-assistant-4.0.0.vsix
```

---

## ⚙️ Configuration

### Required Settings

1. **API Key** (Required)
   ```json
   "bioql.apiKey": "your_bioql_api_key_here"
   ```
   Get your API key at: https://bioql.com/signup

### Optional Settings

```json
{
  // Default quantum backend
  "bioql.defaultBackend": "simulator",  // Options: simulator, ibm, ionq, aws, aws_braket

  // Enable QEC by default
  "bioql.enableQEC": false,

  // QEC code type
  "bioql.qecType": "surface_code",  // Options: surface_code, steane, shor

  // Default measurement shots
  "bioql.defaultShots": 1000,

  // Enable automatic visualizations
  "bioql.enableVisualizations": true,

  // Inference mode
  "bioql.mode": "modal"  // Options: modal, template, local, ollama
}
```

---

## 🚀 Usage

### Commands

#### Generate Code
**Shortcut:** `Cmd+Shift+G` (Mac) / `Ctrl+Shift+G` (Windows/Linux)

```
Command Palette → BioQL: Generate Code from Description
```

**Example:**
```
Input: "Create a Bell state with surface code QEC on AWS Braket"

Generated Code:
- Includes all imports (matplotlib, pathlib)
- Full quantum circuit code
- Automatic Qualtran visualization
- QEC parameters configured
- High-resolution graphs saved
```

#### Fix Code
**Shortcut:** `Cmd+Shift+F` (Mac) / `Ctrl+Shift+F` (Windows/Linux)

```
Command Palette → BioQL: Fix Current Code
```

Select problematic code → Run command → Code automatically fixed

#### Chat Interface
Type `@bioql` in VS Code Chat

**Examples:**
```
@bioql create a ghz state with 3 qubits
@bioql dock metformin to AMPK with high fidelity QEC
@bioql explain this quantum circuit
@bioql optimize this code for AWS Braket
```

---

## 📊 Visualization Examples

### Bell State Output
```
bioql_visualizations/
├── bell_state_complete_analysis.png
│   ├── Measurement Histogram (|00⟩ vs |11⟩)
│   ├── Circuit Diagram (H, CNOT gates)
│   └── Resource Estimation
```

### Bell State with QEC Output
```
bioql_visualizations/
├── bell_state_results_qec.png
│   ├── Measurement Results
│   └── QEC Overhead Breakdown
└── bell_state_circuit_qec.png
    ├── Circuit Diagram
    └── QEC Configuration Details
```

### Molecular Docking Output
```
bioql_visualizations/
└── docking_metformin_AMPK_qec.png
    ├── Measurement Histogram
    ├── QEC Resource Overhead
    ├── Molecular Structure (Ligand → Receptor)
    ├── Experiment Configuration
    ├── Results Summary
    └── Binding Affinity
```

---

## 🎓 Interactive Flow Example

```
1. User: "create a bell state"

2. Agent: 🤔 I need some more information:
   - Which quantum backend? (simulator/IBM/IonQ/AWS)
   - Hardware or simulator?
   - How many shots? (1000 recommended)
   - Enable Quantum Error Correction?

3. User: "AWS Braket simulator, 1000 shots, yes QEC with surface code"

4. Agent: ✅ Generates complete code with:
   - Quantum circuit
   - AWS Braket configuration
   - QEC parameters (surface_code, distance=3)
   - Automatic visualizations
   - Saved to bioql_visualizations/
```

---

## 🎨 Generated Code Features

### Always Included:
- ✅ Import statements (os, matplotlib, pathlib)
- ✅ API key setup with environment variable
- ✅ Clear print statements showing configuration
- ✅ Quantum execution with proper backend
- ✅ Result processing and display
- ✅ **Automatic Qualtran visualizations**
- ✅ Error handling
- ✅ High-resolution graph export (300 DPI)

### If QEC Enabled:
- ✅ QEC parameters (type, logical qubits, distance)
- ✅ Physical qubit calculation
- ✅ Cost estimation in comments
- ✅ QEC overhead visualization
- ✅ Fidelity tracking

---

## 💰 Pricing

- **Code Generation**: $0.00125 per request
- **With QEC**: Additional QEC overhead cost (calculated automatically)
- **Balance Display**: Real-time balance tracking in Output panel

View costs in **Output → BioQL Assistant**

---

## 📈 Supported Operations

### Quantum States
- Bell State
- GHZ State (multi-qubit entanglement)
- Custom superposition states

### Quantum Algorithms
- VQE (Variational Quantum Eigensolver)
- QAOA (Quantum Approximate Optimization)
- Grover's Algorithm
- Shor's Algorithm

### Molecular Simulations
- Molecular Docking
- ADME Prediction
- Toxicity Analysis
- Binding Affinity Calculation

---

## 📝 Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| BioQL: Generate Code | Cmd/Ctrl+Shift+G | Generate from natural language |
| BioQL: Fix Code | Cmd/Ctrl+Shift+F | Fix selected code |
| BioQL: Explain Code | - | Explain selected code |
| BioQL: Optimize Circuit | - | Optimize quantum circuit |
| BioQL: Run on Quantum Computer | - | Execute on real hardware |

---

## 🔍 Troubleshooting

### "API key required"
Set your API key in VS Code settings:
```json
"bioql.apiKey": "bioql_your_key_here"
```

### "No visualizations generated"
Check that `bioql.enableVisualizations` is `true` in settings.

### "Agent timeout"
Increase timeout in settings or simplify the request.

### "Backend not available"
Verify backend is spelled correctly: `simulator`, `ibm`, `ionq`, `aws`, `aws_braket`

---

## 🆕 Changelog

### v4.0.0 (2025-10-05)
- ✅ Interactive parameter collection
- ✅ Automatic Qualtran visualizations (always enabled)
- ✅ QEC support (Surface, Steane, Shor codes)
- ✅ Multi-backend support (AWS Braket, IonQ, IBM)
- ✅ Conversation state management
- ✅ Natural language parameter responses
- ✅ High-resolution graph export (300 DPI)

### v3.4.0 (Previous)
- Autonomous code fixing
- Inline completions
- Chat interface

---

## 📚 Resources

- **BioQL Documentation**: https://docs.bioql.com
- **PyPI Package**: https://pypi.org/project/bioql/5.0.1/
- **GitHub**: https://github.com/bioql/bioql
- **AWS Braket Guide**: Included in BioQL 5.0.1 examples
- **API Key Signup**: https://bioql.com/signup

---

## 📞 Support

- **GitHub**: https://github.com/bioql/bioql
- **Email**: support@spectrixrd.com
- **Chat**: @bioql in VS Code

---

## 📄 License

Proprietary - © 2024-2025 SpectrixRD. All rights reserved.

---

**BioQL v4.0** - Making quantum computing accessible through natural language 🧬⚛️
