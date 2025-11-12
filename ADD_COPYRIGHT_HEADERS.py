#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Add Copyright Headers to BioQL Ecosystem Python Files

This script adds copyright headers to all Python files in the BioQL ecosystem
that don't already have them. It preserves shebangs and existing docstrings.

Usage:
    python ADD_COPYRIGHT_HEADERS.py [--dry-run] [--directory DIR]

Options:
    --dry-run       Show what would be changed without making changes
    --directory     Target directory (default: current directory)
    --exclude       Comma-separated list of directories to exclude (default: .venv,venv,archives,build,dist,__pycache__)
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple

COPYRIGHT_HEADER = """# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text
"""

# Directories to exclude by default
DEFAULT_EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "env",
    ".env",
    "archives",
    "legacy",
    "build",
    "dist",
    "egg-info",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".git",
    ".svn",
}


def has_copyright_header(content: str) -> bool:
    """Check if file already has a copyright header."""
    lines = content.split("\n")
    # Check first 10 lines for copyright
    for line in lines[:10]:
        if "Copyright" in line and ("SpectrixRD" in line or "Spectrix" in line):
            return True
    return False


def extract_shebang(content: str) -> Tuple[str, str]:
    """Extract shebang line if present."""
    lines = content.split("\n")
    if lines and lines[0].startswith("#!"):
        return lines[0], "\n".join(lines[1:])
    return "", content


def add_copyright_header(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add copyright header to a Python file.

    Returns:
        True if file was modified (or would be modified in dry-run)
        False if no modification needed
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    # Check if already has copyright
    if has_copyright_header(content):
        return False

    # Extract shebang if present
    shebang, rest_content = extract_shebang(content)

    # Build new content
    new_content_parts = []

    if shebang:
        new_content_parts.append(shebang)

    new_content_parts.append(COPYRIGHT_HEADER)

    # Add rest of content (remove leading newlines)
    rest_content = rest_content.lstrip("\n")
    new_content_parts.append(rest_content)

    new_content = "\n".join(new_content_parts)

    if dry_run:
        print(f"[DRY RUN] Would add header to: {file_path}")
        return True

    # Write modified content
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Added header to: {file_path}")
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False


def find_python_files(root_dir: Path, exclude_dirs: Set[str]) -> List[Path]:
    """Find all Python files in directory tree, excluding certain directories."""
    python_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove excluded directories from search
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        # Find Python files
        for filename in filenames:
            if filename.endswith(".py"):
                file_path = Path(dirpath) / filename
                python_files.append(file_path)

    return python_files


def main():
    parser = argparse.ArgumentParser(
        description="Add copyright headers to Python files in BioQL ecosystem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--directory", type=str, default=".", help="Target directory (default: current directory)"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help="Comma-separated list of additional directories to exclude",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include all directories (ignore default exclusions)",
    )

    args = parser.parse_args()

    # Setup exclusions
    if args.include_all:
        exclude_dirs = set()
    else:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS.copy()

    if args.exclude:
        exclude_dirs.update(args.exclude.split(","))

    # Resolve directory
    root_dir = Path(args.directory).resolve()

    if not root_dir.exists():
        print(f"Error: Directory not found: {root_dir}")
        return 1

    print(f"Scanning for Python files in: {root_dir}")
    print(f"Excluding directories: {', '.join(sorted(exclude_dirs))}")

    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")

    # Find all Python files
    python_files = find_python_files(root_dir, exclude_dirs)
    print(f"\nFound {len(python_files)} Python files")

    # Process files
    modified_count = 0
    for file_path in python_files:
        if add_copyright_header(file_path, dry_run=args.dry_run):
            modified_count += 1

    # Summary
    print(f"\n{'Would modify' if args.dry_run else 'Modified'} {modified_count} files")
    print(f"Skipped {len(python_files) - modified_count} files (already have headers)")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
