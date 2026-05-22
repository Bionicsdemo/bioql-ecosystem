from setuptools import setup, find_packages

setup(
    name="qcem",
    version="0.1.0",
    description="Quantum Compression-Enhanced Mitigation — A Qiskit Function by BioQL",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="BioQL Quantum Team",
    license="Apache-2.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "qiskit>=2.0",
        "numpy>=1.22",
        "scipy>=1.9",
    ],
    extras_require={
        "ibm": ["qiskit-ibm-runtime>=0.20"],
        "nature": ["qiskit-nature>=0.7", "pyscf>=2.3"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
    ],
)
