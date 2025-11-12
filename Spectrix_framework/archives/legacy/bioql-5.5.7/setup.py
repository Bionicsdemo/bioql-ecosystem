#!/usr/bin/env python3
"""
BioQL: Quantum Computing for Bioinformatics
"""

import os

from setuptools import find_packages, setup


# Read the contents of README file
def read_long_description():
    """Read the long description from README.md"""
    here = os.path.abspath(os.path.dirname(__file__))
    readme_path = os.path.join(here, "README.md")

    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback for encoding issues
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    else:
        return "BioQL: A quantum computing framework for bioinformatics applications"


# Read requirements from requirements.txt
def read_requirements():
    """Read requirements from requirements.txt"""
    here = os.path.abspath(os.path.dirname(__file__))
    requirements_path = os.path.join(here, "requirements.txt")

    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        # Fallback to default requirements
        return [
            "qiskit>=0.45.0",
            "qiskit-aer",
            "numpy>=1.21.0",
            "matplotlib>=3.5.0",
            "biopython>=1.79",
            "requests>=2.28.0",  # REQUIRED for API key authentication
            "python-dotenv>=0.19.0",
            "pydantic>=2.0.0",  # DevKit IR schemas
            "loguru>=0.7.0",  # Enhanced logging
            "uuid6>=2023.5.2",  # UUID support for IR
        ]


setup(
    name="bioql",
    version="5.5.8",
    author="BioQL Development Team - SpectrixRD",
    author_email="bioql@spectrixrd.com",
    description="Enterprise Quantum Computing v5.5.8 - CHARGED MOLECULE FIX: Auto-neutralization for N+/O- atoms, robust 3D embedding, CRISPR IN-SILICO + DYNAMIC PDB/SMILES: GLP1R obesity drug design, pharmaceutical scoring (Lipinski, QED, SA Score, PAINS) - IBM Torino 133q validated",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/bioql",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/bioql/issues",
        "Source": "https://github.com/yourusername/bioql",
        "Documentation": "https://bioql.readthedocs.io/",
    },
    packages=find_packages(exclude=["tests*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
            "isort>=5.10.0",
            "pre-commit>=2.20.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "sphinx-autodoc-typehints>=1.19.0",
        ],
        "cloud": [
            "boto3>=1.26.0",  # AWS Braket
            "azure-quantum>=1.0.0",  # Azure Quantum
            "cirq-ionq>=1.0.0",  # IonQ
        ],
        "visualization": [
            "plotly>=5.0.0",
            "seaborn>=0.11.0",
            "pandas>=1.4.0",
        ],
        "vina": [
            "meeko>=0.4.0",  # Ligand preparation for Vina
            "rdkit>=2022.9.1",  # Chemistry toolkit
            "openbabel-wheel>=3.1.1",  # Chemical format conversion
        ],
        "viz": [
            "py3Dmol>=2.0.0",  # 3D molecular visualization
            "pillow>=9.0.0",  # Image processing
        ],
        "quantum_chemistry": [
            "openfermionpyscf>=0.5",  # REAL quantum chemistry with PySCF
            "pyscf>=2.0.0",  # Python-based quantum chemistry
        ],
        "openmm": [
            "openmm>=8.0.0",  # Molecular dynamics
        ],
    },
    entry_points={
        "console_scripts": [
            "bioql=bioql.cli:main",
            "bioql-compiler=bioql.compiler:main",
            "bioql-quantum=bioql.quantum_connector:main",
            "bioql-crispr=bioql.crispr_qai.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "bioql": [
            "data/*.json",
            "data/*.yaml",
            "templates/*.qasm",
            "schemas/*.json",
            "examples/aws_braket/*.sh",
            "examples/aws_braket/*.md",
            "examples/aws_braket/*.qasm",
        ],
    },
    zip_safe=False,
    keywords=[
        "quantum computing",
        "bioinformatics",
        "drug discovery",
        "molecular docking",
        "SMILES validation",
        "PDB search",
        "binding affinity",
        "ADME prediction",
        "toxicity prediction",
        "pharmacophore modeling",
        "protein folding",
        "qiskit",
        "quantum algorithms",
        "computational biology",
        "quantum machine learning",
        "VQE",
        "QAOA",
        "QNN",
        "rdkit",
        "biopython",
        "natural language processing",
        "intermediate representation",
        "sequence alignment",
        "devkit",
        "error mitigation",
        "QEC",
        "surface code",
        "provenance logging",
        "compliance",
        "chemistry benchmarks",
        "backend optimization",
        "enterprise",
        "21 CFR Part 11",
    ],
    license="MIT",
    platforms=["any"],
)
