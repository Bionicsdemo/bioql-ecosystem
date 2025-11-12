"""
BioQL Molecular Utilities
==========================
Utilities for SMILES validation, PDB searching and downloading.

Author: BioQL Team
Version: 5.0.1
"""

import requests
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
import time

# ==============================================================================
# SMILES VALIDATION AND PARSING
# ==============================================================================

def validate_smiles(smiles: str) -> Dict[str, Any]:
    """
    Validate SMILES string and extract molecular properties.

    Uses RDKit if available, otherwise basic validation.

    Args:
        smiles: SMILES string to validate

    Returns:
        {
            "valid": bool,
            "canonical_smiles": str,
            "molecular_weight": float,
            "formula": str,
            "num_atoms": int,
            "num_bonds": int,
            "error": str (if invalid)
        }
    """
    result = {
        "valid": False,
        "smiles": smiles,
        "error": None
    }

    # Basic validation: check for valid characters
    valid_chars = set("CNOSPFClBrIHcnos0123456789[]()=#@+-\\/%.")
    if not all(c in valid_chars for c in smiles):
        result["error"] = "Invalid characters in SMILES"
        return result

    # Try to use RDKit if available
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            result["error"] = "RDKit cannot parse SMILES"
            return result

        result.update({
            "valid": True,
            "canonical_smiles": Chem.MolToSmiles(mol),
            "molecular_weight": Descriptors.MolWt(mol),
            "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
            "num_atoms": mol.GetNumAtoms(),
            "num_bonds": mol.GetNumBonds(),
            "num_heavy_atoms": mol.GetNumHeavyAtoms(),
            "logp": Descriptors.MolLogP(mol),
            "h_bond_donors": Descriptors.NumHDonors(mol),
            "h_bond_acceptors": Descriptors.NumHAcceptors(mol),
            "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
            "aromatic_rings": Descriptors.NumAromaticRings(mol)
        })

    except ImportError:
        # RDKit not available - basic validation passed
        result["valid"] = True
        result["canonical_smiles"] = smiles
        result["note"] = "RDKit not available - basic validation only"

    except Exception as e:
        result["error"] = f"SMILES validation error: {str(e)}"

    return result


def normalize_smiles(smiles: str) -> str:
    """
    Normalize SMILES to canonical form.

    Args:
        smiles: Input SMILES

    Returns:
        Canonical SMILES or original if RDKit unavailable
    """
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return Chem.MolToSmiles(mol)
    except:
        pass

    return smiles


# ==============================================================================
# PDB SEARCHING AND DOWNLOADING
# ==============================================================================

def search_pdb_rcsb(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search RCSB PDB database for structures.

    Args:
        query: Search query (PDB ID, protein name, gene name, etc.)
        max_results: Maximum number of results to return

    Returns:
        List of matching PDB entries with metadata
    """
    results = []

    # If query looks like a PDB ID (4 characters), try direct lookup first
    if len(query) == 4 and query.isalnum():
        pdb_info = get_pdb_info(query.upper())
        if pdb_info["found"]:
            return [pdb_info]

    # Search API
    search_url = "https://search.rcsb.org/rcsbsearch/v2/query"

    search_query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "struct.title",
                "operator": "contains_words",
                "value": query
            }
        },
        "return_type": "entry",
        "request_options": {
            "results_content_type": ["experimental"],
            "return_all_hits": False,
            "results_verbosity": "verbose"
        }
    }

    try:
        response = requests.post(search_url, json=search_query, timeout=10)

        if response.status_code == 200:
            data = response.json()

            result_set = data.get("result_set", [])
            for entry in result_set[:max_results]:
                pdb_id = entry.get("identifier", "")
                if pdb_id:
                    pdb_info = get_pdb_info(pdb_id)
                    if pdb_info["found"]:
                        results.append(pdb_info)

    except Exception as e:
        print(f"RCSB PDB search error: {e}")

    return results


def search_pdb_by_uniprot(uniprot_id: str) -> List[Dict[str, Any]]:
    """
    Find PDB structures for a UniProt ID.

    Args:
        uniprot_id: UniProt accession (e.g., P12345)

    Returns:
        List of PDB entries
    """
    url = f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{uniprot_id}"

    results = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()

            for uniprot, mappings in data.items():
                for mapping in mappings.get("PDB", {}).values():
                    for pdb_entry in mapping:
                        pdb_id = pdb_entry.get("pdb_id", "")
                        if pdb_id:
                            pdb_info = get_pdb_info(pdb_id.upper())
                            if pdb_info["found"]:
                                results.append(pdb_info)

    except Exception as e:
        print(f"UniProt → PDB search error: {e}")

    return results


def get_pdb_info(pdb_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a PDB entry.

    Args:
        pdb_id: 4-character PDB ID (e.g., 2Y94)

    Returns:
        {
            "found": bool,
            "pdb_id": str,
            "title": str,
            "resolution": float,
            "method": str,
            "organism": str,
            "release_date": str,
            "protein_name": str,
            "gene_name": str,
            "chains": list,
            "download_url": str
        }
    """
    pdb_id = pdb_id.upper()

    result = {
        "found": False,
        "pdb_id": pdb_id
    }

    # Try RCSB PDB REST API
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            result.update({
                "found": True,
                "title": data.get("struct", {}).get("title", ""),
                "method": data.get("exptl", [{}])[0].get("method", ""),
                "release_date": data.get("rcsb_accession_info", {}).get("initial_release_date", ""),
                "download_url": f"https://files.rcsb.org/download/{pdb_id}.pdb"
            })

            # Resolution (if X-ray)
            if "refine" in data:
                result["resolution"] = data["refine"][0].get("ls_d_res_high")

            # Get more details from summary API
            summary_url = f"https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/1"
            try:
                summary_response = requests.get(summary_url, timeout=5)
                if summary_response.status_code == 200:
                    summary_data = summary_response.json()

                    result["protein_name"] = summary_data.get("rcsb_polymer_entity", {}).get("pdbx_description", "")
                    result["organism"] = summary_data.get("rcsb_entity_source_organism", [{}])[0].get("scientific_name", "")

                    gene_info = summary_data.get("rcsb_entity_source_organism", [{}])[0].get("rcsb_gene_name", [])
                    result["gene_name"] = gene_info[0].get("value", "") if gene_info else ""
            except:
                pass

        elif response.status_code == 404:
            result["error"] = f"PDB ID {pdb_id} not found"
        else:
            result["error"] = f"RCSB PDB API error: {response.status_code}"

    except Exception as e:
        result["error"] = f"Error fetching PDB info: {str(e)}"

    return result


def download_pdb(pdb_id: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Download PDB file from RCSB PDB.

    Args:
        pdb_id: 4-character PDB ID
        output_dir: Directory to save file (default: current directory)

    Returns:
        {
            "success": bool,
            "pdb_id": str,
            "file_path": str,
            "size_bytes": int,
            "error": str (if failed)
        }
    """
    pdb_id = pdb_id.upper()

    result = {
        "success": False,
        "pdb_id": pdb_id
    }

    # Set output directory
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{pdb_id}.pdb"

    # Download from RCSB PDB
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            # Save to file
            with open(output_file, 'w') as f:
                f.write(response.text)

            result.update({
                "success": True,
                "file_path": str(output_file),
                "size_bytes": output_file.stat().st_size,
                "url": url
            })

        elif response.status_code == 404:
            result["error"] = f"PDB file {pdb_id}.pdb not found on RCSB PDB"
        else:
            result["error"] = f"Download failed: HTTP {response.status_code}"

    except Exception as e:
        result["error"] = f"Download error: {str(e)}"

    return result


def smart_pdb_search(query: str) -> Dict[str, Any]:
    """
    Intelligent PDB search that handles various query types.

    Supports:
    - Direct PDB IDs (e.g., "2Y94")
    - Protein names (e.g., "AMPK kinase")
    - Gene names (e.g., "PRKAA1")
    - UniProt IDs (e.g., "P12345")

    Args:
        query: Search query

    Returns:
        {
            "query": str,
            "query_type": str,
            "results": list,
            "best_match": dict (if found)
        }
    """
    result = {
        "query": query,
        "results": []
    }

    # Detect query type
    if len(query) == 4 and query.isalnum():
        result["query_type"] = "pdb_id"
        pdb_info = get_pdb_info(query.upper())
        if pdb_info["found"]:
            result["results"] = [pdb_info]
            result["best_match"] = pdb_info

    elif re.match(r'^[A-Z][0-9][A-Z0-9]{3}[0-9]$', query.upper()):
        result["query_type"] = "uniprot_id"
        result["results"] = search_pdb_by_uniprot(query.upper())
        if result["results"]:
            result["best_match"] = result["results"][0]

    else:
        result["query_type"] = "text_search"
        result["results"] = search_pdb_rcsb(query, max_results=5)
        if result["results"]:
            result["best_match"] = result["results"][0]

    return result


# ==============================================================================
# INTEGRATED MOLECULAR PROCESSING
# ==============================================================================

def process_molecular_inputs(ligand: str, receptor: str,
                            ligand_smiles: Optional[str] = None,
                            receptor_pdb: Optional[str] = None) -> Dict[str, Any]:
    """
    Process and validate molecular inputs for docking/binding affinity.

    Args:
        ligand: Ligand name or SMILES
        receptor: Receptor name or PDB ID
        ligand_smiles: Explicit SMILES (optional)
        receptor_pdb: Explicit PDB ID or file (optional)

    Returns:
        {
            "ligand": {
                "name": str,
                "smiles": str,
                "valid": bool,
                "properties": dict
            },
            "receptor": {
                "name": str,
                "pdb_id": str,
                "pdb_file": str,
                "info": dict
            }
        }
    """
    result = {
        "ligand": {"name": ligand},
        "receptor": {"name": receptor}
    }

    # Process ligand
    if ligand_smiles:
        smiles_validation = validate_smiles(ligand_smiles)
        result["ligand"].update({
            "smiles": ligand_smiles,
            "valid": smiles_validation["valid"],
            "properties": smiles_validation
        })
    else:
        # Assume ligand is a SMILES string
        smiles_validation = validate_smiles(ligand)
        if smiles_validation["valid"]:
            result["ligand"].update({
                "smiles": ligand,
                "valid": True,
                "properties": smiles_validation
            })
        else:
            result["ligand"]["valid"] = False
            result["ligand"]["error"] = "Could not parse as SMILES"

    # Process receptor
    if receptor_pdb:
        # Explicit PDB provided
        if len(receptor_pdb) == 4 and receptor_pdb.isalnum():
            pdb_info = get_pdb_info(receptor_pdb.upper())
            result["receptor"].update({
                "pdb_id": receptor_pdb.upper(),
                "info": pdb_info
            })
        else:
            result["receptor"]["pdb_file"] = receptor_pdb
    else:
        # Try to find PDB
        search_result = smart_pdb_search(receptor)
        if search_result.get("best_match"):
            best = search_result["best_match"]
            result["receptor"].update({
                "pdb_id": best["pdb_id"],
                "info": best
            })
        else:
            result["receptor"]["error"] = "PDB not found"

    return result


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("BioQL Molecular Utilities - Examples")
    print("=" * 80)

    # Test 1: Validate SMILES
    print("\n1. SMILES Validation:")
    smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
    validation = validate_smiles(smiles)
    print(f"   SMILES: {smiles}")
    print(f"   Valid: {validation['valid']}")
    if validation['valid']:
        print(f"   MW: {validation.get('molecular_weight', 'N/A')} Da")
        print(f"   Formula: {validation.get('formula', 'N/A')}")

    # Test 2: Custom SMILES
    print("\n2. Custom SMILES (Caffeine):")
    custom_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
    validation = validate_smiles(custom_smiles)
    print(f"   SMILES: {custom_smiles}")
    print(f"   Valid: {validation['valid']}")

    # Test 3: PDB Info
    print("\n3. PDB Information:")
    pdb_info = get_pdb_info("2Y94")
    print(f"   PDB ID: {pdb_info['pdb_id']}")
    print(f"   Found: {pdb_info['found']}")
    if pdb_info['found']:
        print(f"   Title: {pdb_info.get('title', 'N/A')[:60]}...")
        print(f"   Method: {pdb_info.get('method', 'N/A')}")

    # Test 4: Search PDB
    print("\n4. PDB Search:")
    search = smart_pdb_search("AMPK kinase")
    print(f"   Query: {search['query']}")
    print(f"   Type: {search['query_type']}")
    print(f"   Results: {len(search['results'])}")
    if search.get('best_match'):
        best = search['best_match']
        print(f"   Best match: {best['pdb_id']} - {best.get('title', 'N/A')[:50]}...")

    # Test 5: Download PDB
    print("\n5. Download PDB:")
    download = download_pdb("2Y94", "/tmp/bioql_pdb")
    print(f"   Success: {download['success']}")
    if download['success']:
        print(f"   File: {download['file_path']}")
        print(f"   Size: {download['size_bytes']:,} bytes")

    print("\n" + "=" * 80)
