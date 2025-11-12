#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quillow: Willow-Style Quantum Error Correction System
Setup configuration
"""

import os

from setuptools import find_packages, setup


# Read README for long description
def read_long_description():
    here = os.path.abspath(os.path.dirname(__file__))
    readme_path = os.path.join(here, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Quillow: Advanced Fault-Tolerant Quantum Computing Framework"


setup(
    name="quillow",
    version="1.0.0",
    author="SpectrixRD",
    author_email="contact@spectrixrd.com",
    description="Willow-style quantum error correction framework with surface codes, MWPM decoding, and real quantum hardware integration",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/spectrixrd/quillow",
    project_urls={
        "Documentation": "https://quillow.readthedocs.io",
        "Source": "https://github.com/spectrixrd/quillow",
        "Tracker": "https://github.com/spectrixrd/quillow/issues",
        "BioQL Platform": "https://bioql.bio",
    },
    packages=find_packages(exclude=["tests*", "examples*", "docs*", "benchmarks*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.9",
    install_requires=[
        "stim>=1.12.0",  # Fast stabilizer circuit simulator
        "pymatching>=2.0.0",  # MWPM decoder
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "numba>=0.56.0",  # JIT compilation
        "matplotlib>=3.5.0",
        "networkx>=2.8.0",  # Graph algorithms
        "tqdm>=4.64.0",  # Progress bars
        "click>=8.0.0",  # CLI framework
        "pyyaml>=6.0",  # Configuration
        "loguru>=0.6.0",  # Logging
        "pydantic>=2.0.0",  # Data validation
        "requests>=2.28.0",  # HTTP client for BioQL API
    ],
    extras_require={
        "gpu": [
            "torch>=2.0.0",  # GPU acceleration
            "cupy>=12.0.0",  # CUDA arrays
        ],
        "cloud": [
            "modal>=0.55.0",  # Modal GPU cloud
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
            "build>=0.10.0",
            "twine>=4.0.0",
        ],
        "api": [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
        ],
        "all": [
            "torch>=2.0.0",
            "cupy>=12.0.0",
            "modal>=0.55.0",
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "quillow=api.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "quantum computing",
        "quantum error correction",
        "surface codes",
        "fault-tolerant quantum computing",
        "MWPM",
        "syndrome decoding",
        "Willow",
        "BioQL",
        "quantum chemistry",
    ],
    license="MIT",
    platforms=["any"],
)
