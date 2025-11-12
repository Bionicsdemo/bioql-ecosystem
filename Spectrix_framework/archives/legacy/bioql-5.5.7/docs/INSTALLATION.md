# BioQL Installation Guide

## Quick Install

```bash
pip install bioql
```

## Installation with Extras

### Drug Discovery Features

```bash
# AutoDock Vina support
pip install bioql[vina]

# Visualization support
pip install bioql[viz]

# Molecular dynamics
pip install bioql[openmm]

# All drug discovery features
pip install bioql[vina,viz,openmm]
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/bioql/bioql.git
cd bioql

# Install in development mode
pip install -e .[dev]

# Install all extras
pip install -e .[vina,viz,openmm,dev]
```

## System Requirements

- **Python**: 3.8 or higher (3.11 recommended)
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Disk Space**: 500MB for base install, 2GB with all extras

## External Dependencies

### AutoDock Vina (Optional)

Download from: http://vina.scripps.edu/download.html

```bash
# Linux/Mac
wget http://vina.scripps.edu/download/vina_1.2.5_linux_x86_64
chmod +x vina_1.2.5_linux_x86_64
sudo mv vina_1.2.5_linux_x86_64 /usr/local/bin/vina

# Or add to PATH
export PATH=$PATH:/path/to/vina
```

### PyMOL (Optional)

```bash
# Using conda (recommended)
conda install -c conda-forge pymol-open-source

# Or pip (may have limited functionality)
pip install pymol-open-source
```

### OpenMM (Optional)

```bash
# Using conda (recommended)
conda install -c conda-forge openmm

# Or pip
pip install openmm
```

## Verification

```bash
# Check installation
bioql check

# Show version
bioql --version

# Run tests
pytest tests/
```

## API Key Setup

For quantum computing features:

```bash
# Set environment variable
export BIOQL_API_KEY=your_key_here

# Or configure interactively
bioql setup-keys
```

Get your API key at: https://bioql.com/signup

## Troubleshooting

### ImportError: No module named 'rdkit'

```bash
pip install bioql[vina]
```

### "Vina executable not found"

Download Vina and add to PATH, or specify path:

```python
from bioql.docking.vina_runner import VinaRunner
runner = VinaRunner(vina_executable="/path/to/vina")
```

### PyMOL not working

Use conda installation for best compatibility:

```bash
conda install -c conda-forge pymol-open-source
```

### Permission denied errors

On Unix/Linux, you may need sudo for global installation:

```bash
sudo pip install bioql
```

Or install in user directory:

```bash
pip install --user bioql
```

## Uninstallation

```bash
pip uninstall bioql
```

## Support

- Issues: https://github.com/bioql/bioql/issues
- Documentation: https://docs.bioql.com
- Email: support@bioql.com