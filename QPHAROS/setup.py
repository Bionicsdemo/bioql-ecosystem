#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS - Quantum Pharmaceutical Optimization System
Setup configuration for PyPI distribution
"""

import os

from setuptools import find_packages, setup


# Read long description from README
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="utf-8") as f:
        return f.read()


setup(
    name="qpharos",
    version="1.1.0",
    description="Quantum Pharmaceutical Optimization System - 5-Layer Quantum Drug Discovery with 4 Usage Schemas",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Heinz Jungbluth",
    author_email="heinz@bionics-ai.biz",
    url="https://github.com/yourusername/qpharos",
    project_urls={
        "Documentation": "https://docs.bioql.bio/qpharos",
        "Source": "https://github.com/yourusername/qpharos",
        "Tracker": "https://github.com/yourusername/qpharos/issues",
        "Homepage": "https://bioql.bio/qpharos",
    },
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    install_requires=[
        "bioql>=6.0.0",  # Requires BioQL v6.0+
        "numpy>=1.21.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="quantum computing drug discovery pharmaceutical docking vqe qaoa qec ibm-quantum",
    license="Apache-2.0",
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "qpharos=qpharos.cli:main",
        ],
    },
)
