# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum_graph Setup Script
===========================

Installation and configuration for Quantum-Enhanced Scientific Visualization

Author: Spectrix R&D / BioQL Team
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    long_description = readme_file.read_text()
else:
    long_description = "Quantum-Enhanced Scientific Visualization Platform"

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
else:
    requirements = []

setup(
    name="quantum_graph",
    version="1.0.0",
    description="Quantum-Enhanced Scientific Visualization for Biotechnology Research",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Spectrix R&D / BioQL Team",
    author_email="support@spectrixrd.com",
    url="https://github.com/spectrix/quantum_graph",
    license="Proprietary",
    packages=find_packages(exclude=["tests", "docs", "examples"]),
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinxcontrib-napoleon>=0.7",
        ],
        "viz": [
            "plotly>=5.18.0",
            "seaborn>=0.13.0",
            "bokeh>=3.3.0",
        ],
    },
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "quantum-viz=backend.api.quantum_viz_api:main",
            "quantum-optimize=quantum_core.optimizers.adaptive_quantum_optimizer:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords=[
        "quantum computing",
        "scientific visualization",
        "biotechnology",
        "protein structure",
        "drug discovery",
        "metabolomics",
        "proteomics",
        "molecular dynamics",
        "computational biology",
        "quantum chemistry",
    ],
    include_package_data=True,
    zip_safe=False,
)
