"""
Input/Output utilities for CRISPR-QAI

Handles:
- CSV loading/saving for guide sequences
- Result serialization
- Batch processing I/O
"""

import csv
from typing import List, Dict, Any, Optional
import json


def load_guides_csv(
    csv_path: str,
    sequence_column: str = 'sequence',
    id_column: Optional[str] = 'guide_id'
) -> List[Dict[str, Any]]:
    """
    Load guide RNA sequences from CSV file

    Args:
        csv_path: Path to CSV file
        sequence_column: Name of column containing sequences
        id_column: Name of column containing guide IDs (optional)

    Returns:
        List of guide dictionaries

    CSV Format:
        guide_id,sequence,target_gene
        guide_001,ATCGAAGTC,BRCA1
        guide_002,GCTAGCTA,TP53

    Example:
        >>> guides = load_guides_csv('guides.csv')
        >>> print(f"Loaded {len(guides)} guides")
    """
    guides = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            if sequence_column not in row:
                raise ValueError(
                    f"Column '{sequence_column}' not found in CSV. "
                    f"Available: {list(row.keys())}"
                )

            guide_data = {
                'sequence': row[sequence_column].strip().upper()
            }

            # Add guide ID if available
            if id_column and id_column in row:
                guide_data['guide_id'] = row[id_column]

            # Include all other columns as metadata
            for key, value in row.items():
                if key not in [sequence_column, id_column]:
                    guide_data[key] = value

            guides.append(guide_data)

    return guides


def save_results_csv(
    results: List[Dict[str, Any]],
    output_path: str,
    include_metadata: bool = True
) -> None:
    """
    Save CRISPR-QAI results to CSV file

    Args:
        results: List of result dictionaries (from rank_guides_batch, etc.)
        output_path: Path to output CSV file
        include_metadata: Include all metadata fields

    Example:
        >>> ranked = rank_guides_batch(guides, shots=1000)
        >>> save_results_csv(ranked, 'ranked_guides.csv')
    """
    if not results:
        raise ValueError("results cannot be empty")

    # Determine CSV columns
    base_columns = [
        'rank',
        'guide_sequence',
        'composite_score',
        'energy_estimate',
        'confidence',
        'gc_content',
        'runtime_seconds',
        'backend'
    ]

    # Add metadata columns if requested
    all_columns = base_columns.copy()
    if include_metadata:
        metadata_keys = set()
        for result in results:
            metadata_keys.update(result.keys())

        # Add metadata columns not in base
        for key in metadata_keys:
            if key not in all_columns:
                all_columns.append(key)

    # Write CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()

        for result in results:
            # Only write columns that exist in result
            row = {k: result.get(k, '') for k in all_columns}

            # Format floats
            for key in ['composite_score', 'energy_estimate', 'confidence',
                        'gc_content', 'runtime_seconds']:
                if key in row and isinstance(row[key], float):
                    row[key] = f"{row[key]:.6f}"

            writer.writerow(row)


def save_results_json(
    results: List[Dict[str, Any]],
    output_path: str,
    pretty: bool = True
) -> None:
    """
    Save CRISPR-QAI results to JSON file

    Args:
        results: List of result dictionaries
        output_path: Path to output JSON file
        pretty: Use pretty printing (indented)

    Example:
        >>> ranked = rank_guides_batch(guides, shots=1000)
        >>> save_results_json(ranked, 'ranked_guides.json')
    """
    with open(output_path, 'w') as f:
        if pretty:
            json.dump(results, f, indent=2)
        else:
            json.dump(results, f)


def load_results_json(json_path: str) -> List[Dict[str, Any]]:
    """
    Load CRISPR-QAI results from JSON file

    Args:
        json_path: Path to JSON file

    Returns:
        List of result dictionaries

    Example:
        >>> results = load_results_json('ranked_guides.json')
        >>> print(f"Loaded {len(results)} results")
    """
    with open(json_path, 'r') as f:
        results = json.load(f)

    return results


def load_fasta(fasta_path: str) -> List[Dict[str, str]]:
    """
    Load sequences from FASTA file

    Args:
        fasta_path: Path to FASTA file

    Returns:
        List of dictionaries with 'id' and 'sequence'

    FASTA Format:
        >guide_001 BRCA1
        ATCGAAGTC
        >guide_002 TP53
        GCTAGCTA

    Example:
        >>> guides = load_fasta('guides.fasta')
        >>> for g in guides:
        ...     print(f"{g['id']}: {g['sequence']}")
    """
    sequences = []
    current_id = None
    current_seq = []

    with open(fasta_path, 'r') as f:
        for line in f:
            line = line.strip()

            if line.startswith('>'):
                # Save previous sequence
                if current_id is not None:
                    sequences.append({
                        'id': current_id,
                        'sequence': ''.join(current_seq).upper()
                    })

                # Start new sequence
                current_id = line[1:].split()[0]
                current_seq = []

            else:
                current_seq.append(line)

        # Save last sequence
        if current_id is not None:
            sequences.append({
                'id': current_id,
                'sequence': ''.join(current_seq).upper()
            })

    return sequences


def save_fasta(
    sequences: List[Dict[str, str]],
    output_path: str,
    line_length: int = 80
) -> None:
    """
    Save sequences to FASTA file

    Args:
        sequences: List of dictionaries with 'id' and 'sequence'
        output_path: Path to output FASTA file
        line_length: Maximum characters per line (default: 80)

    Example:
        >>> seqs = [
        ...     {'id': 'guide_001', 'sequence': 'ATCGAAGTC'},
        ...     {'id': 'guide_002', 'sequence': 'GCTAGCTA'}
        ... ]
        >>> save_fasta(seqs, 'guides.fasta')
    """
    with open(output_path, 'w') as f:
        for seq_dict in sequences:
            seq_id = seq_dict.get('id', 'unknown')
            seq = seq_dict.get('sequence', '')

            # Write header
            f.write(f'>{seq_id}\n')

            # Write sequence (wrapped at line_length)
            for i in range(0, len(seq), line_length):
                f.write(seq[i:i + line_length] + '\n')


def batch_load_guides(
    file_path: str,
    file_format: Optional[str] = None
) -> List[str]:
    """
    Load guide sequences from CSV or FASTA (auto-detect format)

    Args:
        file_path: Path to input file
        file_format: File format ('csv' or 'fasta'), auto-detected if None

    Returns:
        List of guide RNA sequences

    Example:
        >>> guides = batch_load_guides('guides.csv')
        >>> print(f"Loaded {len(guides)} guides")
    """
    if file_format is None:
        # Auto-detect format
        if file_path.endswith('.csv'):
            file_format = 'csv'
        elif file_path.endswith(('.fasta', '.fa', '.fna')):
            file_format = 'fasta'
        else:
            raise ValueError(
                f"Cannot auto-detect format for {file_path}. "
                f"Specify file_format='csv' or 'fasta'"
            )

    if file_format == 'csv':
        guides_data = load_guides_csv(file_path)
        return [g['sequence'] for g in guides_data]

    elif file_format == 'fasta':
        fasta_data = load_fasta(file_path)
        return [s['sequence'] for s in fasta_data]

    else:
        raise ValueError(f"Unknown format: {file_format}")
