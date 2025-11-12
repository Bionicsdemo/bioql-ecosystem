"""
Dynamic Library Bridge - Meta-wrapper for calling any Python library via natural language

This module enables BioQL to interpret natural language commands and dynamically
call functions from any installed Python library without writing explicit code.

Examples:
    >>> from bioql import dynamic_call
    >>> result = dynamic_call("Use RDKit to calculate molecular weight of aspirin SMILES CC(=O)OC1=CC=CC=C1C(=O)O")
    >>> result = dynamic_call("Use numpy to calculate mean of array [1, 2, 3, 4, 5]")
    >>> result = dynamic_call("Use pandas to read CSV file data.csv and show first 5 rows")
"""

import importlib
import inspect
import re
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class DynamicCallResult:
    """Result of a dynamic library call."""

    success: bool
    library: Optional[str]
    function: Optional[str]
    result: Any
    code_executed: Optional[str]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Library function registry - maps common terms to actual library.function paths
LIBRARY_REGISTRY = {
    # Chemistry libraries
    "rdkit": {
        "module": "rdkit.Chem",
        "aliases": ["rdkit", "chem toolkit", "molecule"],
        "common_functions": {
            "calculate molecular weight": "Descriptors.MolWt",
            "calculate logp": "Descriptors.MolLogP",
            "calculate descriptors": "Descriptors",
            "parse smiles": "MolFromSmiles",
            "convert to smiles": "MolToSmiles",
            "add hydrogens": "AddHs",
            "remove hydrogens": "RemoveHs",
            "generate 3d": "AllChem.EmbedMolecule",
            "optimize geometry": "AllChem.MMFFOptimizeMolecule",
        },
    },
    "openbabel": {
        "module": "openbabel.openbabel",
        "aliases": ["openbabel", "babel", "chemical converter"],
        "common_functions": {
            "convert format": "OBConversion",
            "add hydrogens": "OBMol.AddHydrogens",
            "build 3d": "OBBuilder.Build",
        },
    },
    # Docking libraries
    "autodock": {
        "module": None,  # External binary
        "aliases": ["vina", "autodock", "autodock vina", "docking"],
        "common_functions": {
            "dock ligand": "vina_dock",
            "run docking": "vina_dock",
        },
    },
    # Visualization
    "pymol": {
        "module": "pymol",
        "aliases": ["pymol", "molecular visualization", "visualize protein"],
        "common_functions": {
            "load structure": "cmd.load",
            "show cartoon": "cmd.show_as",
            "color by": "cmd.color",
            "save image": "cmd.png",
        },
    },
    "py3dmol": {
        "module": "py3Dmol",
        "aliases": ["py3dmol", "3dmol", "web visualization"],
        "common_functions": {
            "view structure": "view",
            "add style": "setStyle",
        },
    },
    # Scientific computing
    "numpy": {
        "module": "numpy",
        "aliases": ["numpy", "np", "numerical", "array"],
        "common_functions": {
            "calculate mean": "mean",
            "calculate std": "std",
            "calculate sum": "sum",
            "create array": "array",
            "random numbers": "random.rand",
        },
    },
    "scipy": {
        "module": "scipy",
        "aliases": ["scipy", "scientific python"],
        "common_functions": {
            "optimize": "optimize.minimize",
            "integrate": "integrate.quad",
            "linear algebra": "linalg",
        },
    },
    "pandas": {
        "module": "pandas",
        "aliases": ["pandas", "pd", "dataframe", "csv"],
        "common_functions": {
            "read csv": "read_csv",
            "read excel": "read_excel",
            "show first rows": "DataFrame.head",
            "describe data": "DataFrame.describe",
        },
    },
    # Bioinformatics
    "biopython": {
        "module": "Bio",
        "aliases": ["biopython", "bio", "sequence analysis"],
        "common_functions": {
            "parse fasta": "SeqIO.parse",
            "parse pdb": "PDB.PDBParser",
            "align sequences": "pairwise2.align",
            "translate dna": "Seq.translate",
        },
    },
}


class DynamicLibraryBridge:
    """
    Bridge for dynamically calling Python libraries via natural language.

    This class uses pattern matching and the library registry to interpret
    natural language commands and execute corresponding library functions.
    """

    def __init__(self):
        self.registry = LIBRARY_REGISTRY
        logger.info("Initialized DynamicLibraryBridge")

    def parse_command(self, command: str) -> Dict[str, Any]:
        """
        Parse natural language command to extract library, function, and arguments.

        Args:
            command: Natural language command

        Returns:
            Dictionary with parsed components
        """
        command_lower = command.lower()

        # Pattern: "Use [library] to [action] [arguments]"
        use_pattern = r"use\s+(\w+)\s+to\s+(.+)"
        match = re.search(use_pattern, command_lower)

        if match:
            library_name = match.group(1)
            action_and_args = match.group(2)

            # Find library in registry
            library_info = None
            for lib_key, lib_data in self.registry.items():
                if library_name in lib_data.get("aliases", []):
                    library_info = lib_data
                    break

            if library_info:
                # Try to match action to known functions
                best_match = None
                best_score = 0

                for func_desc, func_path in library_info.get("common_functions", {}).items():
                    if func_desc in action_and_args:
                        score = len(func_desc)
                        if score > best_score:
                            best_match = func_path
                            best_score = score

                return {
                    "library": library_name,
                    "library_module": library_info.get("module"),
                    "function": best_match,
                    "action": action_and_args,
                    "raw_command": command,
                }

        # Pattern: "Call [library].[function] with [arguments]"
        call_pattern = r"call\s+([\w.]+)\s+(?:with\s+)?(.+)"
        match = re.search(call_pattern, command_lower)

        if match:
            function_path = match.group(1)
            arguments = match.group(2)

            parts = function_path.split(".")
            library_name = parts[0]
            function_name = ".".join(parts[1:]) if len(parts) > 1 else None

            return {
                "library": library_name,
                "library_module": library_name,
                "function": function_name,
                "arguments": arguments,
                "raw_command": command,
            }

        return {
            "library": None,
            "function": None,
            "raw_command": command,
            "error": "Could not parse command",
        }

    def extract_arguments(self, text: str) -> Dict[str, Any]:
        """
        Extract arguments from text using pattern matching.

        Args:
            text: Text containing arguments

        Returns:
            Dictionary of extracted arguments
        """
        args = {}

        # Extract SMILES patterns
        smiles_patterns = [
            r"smiles\s+([A-Za-z0-9()\[\]=#@+\-]+)",
            r"(?:of|for)\s+([A-Za-z0-9()\[\]=#@+\-]{5,})",
        ]
        for pattern in smiles_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                args["smiles"] = match.group(1)
                break

        # Extract file paths
        file_patterns = [
            r"file\s+([\w/.]+\.\w+)",
            r"from\s+([\w/.]+\.\w+)",
            r"([\w/.]+\.(?:pdb|csv|txt|mol2|sdf))",
        ]
        for pattern in file_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                args["file_path"] = match.group(1)
                break

        # Extract arrays
        array_pattern = r"\[([0-9,\s.]+)\]"
        match = re.search(array_pattern, text)
        if match:
            array_str = match.group(1)
            args["array"] = [float(x.strip()) for x in array_str.split(",")]

        # Extract numbers
        number_pattern = r"(\d+\.?\d*)"
        numbers = re.findall(number_pattern, text)
        if numbers and "array" not in args:
            args["numbers"] = [float(n) for n in numbers]

        return args

    def execute(self, command: str) -> DynamicCallResult:
        """
        Execute a natural language command by calling the appropriate library.

        Args:
            command: Natural language command

        Returns:
            DynamicCallResult with execution results

        Example:
            >>> bridge = DynamicLibraryBridge()
            >>> result = bridge.execute("Use RDKit to calculate molecular weight of aspirin SMILES CC(=O)OC1=CC=CC=C1C(=O)O")
        """
        logger.info(f"Executing command: {command}")

        # Parse command
        parsed = self.parse_command(command)

        if "error" in parsed:
            return DynamicCallResult(
                success=False,
                library=None,
                function=None,
                result=None,
                code_executed=None,
                error_message=parsed["error"],
            )

        library_name = parsed.get("library")
        library_module = parsed.get("library_module")
        function_path = parsed.get("function")

        if not library_name or not function_path:
            return DynamicCallResult(
                success=False,
                library=library_name,
                function=function_path,
                result=None,
                code_executed=None,
                error_message="Could not determine library or function",
            )

        # Extract arguments
        args = self.extract_arguments(parsed.get("action", "") or parsed.get("arguments", ""))

        try:
            # Import library
            module = importlib.import_module(library_module)
            logger.debug(f"Imported module: {library_module}")

            # Navigate to function
            func = module
            for part in function_path.split("."):
                func = getattr(func, part)

            logger.debug(f"Found function: {function_path}")

            # Execute function with extracted arguments
            # Special handling for RDKit
            if library_name == "rdkit":
                if "calculate molecular weight" in parsed.get("action", ""):
                    from rdkit import Chem
                    from rdkit.Chem import Descriptors

                    if "smiles" in args:
                        mol = Chem.MolFromSmiles(args["smiles"])
                        if mol:
                            result = Descriptors.MolWt(mol)
                            code = f"from rdkit import Chem\nfrom rdkit.Chem import Descriptors\nmol = Chem.MolFromSmiles('{args['smiles']}')\nresult = Descriptors.MolWt(mol)"

                            return DynamicCallResult(
                                success=True,
                                library=library_name,
                                function="Descriptors.MolWt",
                                result=result,
                                code_executed=code,
                                metadata={"args": args},
                            )

            # Special handling for numpy
            elif library_name in ["numpy", "np"]:
                import numpy as np

                if "array" in args:
                    arr = np.array(args["array"])
                    if "mean" in parsed.get("action", ""):
                        result = np.mean(arr)
                        code = f"import numpy as np\narr = np.array({args['array']})\nresult = np.mean(arr)"
                    elif "std" in parsed.get("action", ""):
                        result = np.std(arr)
                        code = f"import numpy as np\narr = np.array({args['array']})\nresult = np.std(arr)"
                    elif "sum" in parsed.get("action", ""):
                        result = np.sum(arr)
                        code = f"import numpy as np\narr = np.array({args['array']})\nresult = np.sum(arr)"
                    else:
                        result = arr
                        code = f"import numpy as np\nresult = np.array({args['array']})"

                    return DynamicCallResult(
                        success=True,
                        library=library_name,
                        function=func.__name__ if callable(func) else str(func),
                        result=result,
                        code_executed=code,
                        metadata={"args": args},
                    )

            # Special handling for pandas
            elif library_name in ["pandas", "pd"]:
                import pandas as pd

                if "file_path" in args and "read csv" in parsed.get("action", ""):
                    df = pd.read_csv(args["file_path"])
                    if "first" in parsed.get("action", "") or "head" in parsed.get("action", ""):
                        result = df.head()
                    else:
                        result = df
                    code = f"import pandas as pd\ndf = pd.read_csv('{args['file_path']}')\nresult = df.head()"

                    return DynamicCallResult(
                        success=True,
                        library=library_name,
                        function="read_csv",
                        result=result,
                        code_executed=code,
                        metadata={"args": args},
                    )

            # Generic function call
            result = func(**args) if args else func()
            code = f"from {library_module} import *\nresult = {function_path}({', '.join(f'{k}={repr(v)}' for k, v in args.items())})"

            return DynamicCallResult(
                success=True,
                library=library_name,
                function=function_path,
                result=result,
                code_executed=code,
                metadata={"args": args},
            )

        except ImportError as e:
            error_msg = f"Library {library_name} not installed: {e}"
            logger.error(error_msg)
            return DynamicCallResult(
                success=False,
                library=library_name,
                function=function_path,
                result=None,
                code_executed=None,
                error_message=error_msg,
            )

        except Exception as e:
            error_msg = f"Error executing command: {e}"
            logger.error(error_msg)
            return DynamicCallResult(
                success=False,
                library=library_name,
                function=function_path,
                result=None,
                code_executed=None,
                error_message=error_msg,
                metadata={"args": args},
            )


# Global bridge instance
_bridge = None


def dynamic_call(command: str) -> DynamicCallResult:
    """
    Execute a natural language command by calling the appropriate library.

    This is the main entry point for the dynamic library bridge system.

    Args:
        command: Natural language command describing what to do

    Returns:
        DynamicCallResult with execution results

    Examples:
        >>> result = dynamic_call("Use RDKit to calculate molecular weight of aspirin SMILES CC(=O)OC1=CC=CC=C1C(=O)O")
        >>> print(f"Molecular weight: {result.result}")

        >>> result = dynamic_call("Use numpy to calculate mean of array [1, 2, 3, 4, 5]")
        >>> print(f"Mean: {result.result}")

        >>> result = dynamic_call("Use pandas to read CSV file data.csv and show first 5 rows")
        >>> print(result.result)
    """
    global _bridge
    if _bridge is None:
        _bridge = DynamicLibraryBridge()

    return _bridge.execute(command)


def register_library(
    name: str,
    module: str,
    aliases: List[str],
    common_functions: Dict[str, str],
):
    """
    Register a new library for dynamic calling.

    Args:
        name: Library key name
        module: Python module path
        aliases: List of alias names for recognition
        common_functions: Dictionary mapping descriptions to function paths
    """
    LIBRARY_REGISTRY[name] = {
        "module": module,
        "aliases": aliases,
        "common_functions": common_functions,
    }
    logger.info(f"Registered library: {name}")