#!/usr/bin/env python3
"""
Find duplicate files based on hash values and output duplicates to remove
based on directory priority.

Usage:
    find_duplicates.py <priority_file> <hash_file> [<hash_file> ...]

The priority file contains one directory per line, in order of preference.
Hash files contain whitespace-separated "HASH PATH" pairs.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


def parse_priority_file(priority_path: Path) -> List[str]:
    """
    Parse the priority directories file.

    Args:
        priority_path: Path to file containing priority directories (one per line)

    Returns:
        List of directory paths in priority order (highest first)

    Raises:
        FileNotFoundError: If priority file doesn't exist
        ValueError: If priority file is empty
    """
    if not priority_path.exists():
        raise FileNotFoundError(f"Priority file not found: {priority_path}")

    with open(priority_path, 'r', encoding='utf-8') as f:
        # Strip whitespace and filter empty lines
        priorities = [line.strip() for line in f if line.strip()]

    if not priorities:
        raise ValueError(f"Priority file is empty: {priority_path}")

    return priorities


def parse_hash_file(hash_path: Path) -> List[Tuple[str, str]]:
    """
    Parse a hash file containing "HASH PATH" pairs.

    Args:
        hash_path: Path to file containing whitespace-separated hash-path pairs

    Returns:
        List of (hash, path) tuples

    Raises:
        FileNotFoundError: If hash file doesn't exist
        ValueError: If hash file contains invalid lines
    """
    if not hash_path.exists():
        raise FileNotFoundError(f"Hash file not found: {hash_path}")

    hash_path_pairs = []

    with open(hash_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            # Split on whitespace, expecting exactly 2 parts
            parts = line.split(None, 1)
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid format in {hash_path} at line {line_num}: "
                    f"expected 'HASH PATH', got: {line}"
                )

            hash_value, file_path = parts
            hash_path_pairs.append((hash_value, file_path))

    return hash_path_pairs


def collect_all_hashes(hash_files: List[Path]) -> Dict[str, List[str]]:
    """
    Collect all hash-path pairs from multiple hash files.

    Args:
        hash_files: List of paths to hash files

    Returns:
        Dictionary mapping hash values to lists of file paths
    """
    hash_to_paths = defaultdict(list)

    for hash_file in hash_files:
        try:
            pairs = parse_hash_file(hash_file)
            for hash_value, file_path in pairs:
                hash_to_paths[hash_value].append(file_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error processing {hash_file}: {e}", file=sys.stderr)
            sys.exit(1)

    return hash_to_paths


def get_priority_index(path: str, priorities: List[str]) -> Optional[int]:
    """
    Determine the priority index for a given path.

    Uses most-specific-match logic: if multiple priority directories match,
    returns the index of the longest (most specific) matching directory.

    Args:
        path: File path to check
        priorities: List of priority directories in order

    Returns:
        Index of the matching priority directory (lower is higher priority),
        or None if path doesn't match any priority directory
    """
    best_match_index = None
    best_match_length = 0

    for index, priority_dir in enumerate(priorities):
        # Check if path starts with priority directory
        # Handle both with and without trailing slashes
        priority_normalized = priority_dir.rstrip('/')
        path_normalized = path.rstrip('/')

        if path_normalized.startswith(priority_normalized + '/') or \
           path_normalized == priority_normalized:
            # Keep the longest (most specific) match
            if len(priority_normalized) > best_match_length:
                best_match_index = index
                best_match_length = len(priority_normalized)

    return best_match_index


def find_keeper_path(paths: List[str], priorities: List[str]) -> str:
    """
    Determine which path to keep among duplicates based on priority.

    Args:
        paths: List of duplicate file paths
        priorities: List of priority directories in order

    Returns:
        The path to keep (highest priority or first encountered)
    """
    # Find paths with priority and their indices
    paths_with_priority = []
    paths_without_priority = []

    for path in paths:
        priority_idx = get_priority_index(path, priorities)
        if priority_idx is not None:
            paths_with_priority.append((priority_idx, path))
        else:
            paths_without_priority.append(path)

    # If any path has a priority, keep the highest priority one
    if paths_with_priority:
        # Sort by priority index (lowest index = highest priority)
        paths_with_priority.sort(key=lambda x: x[0])
        return paths_with_priority[0][1]

    # If no paths have priority, keep the first one encountered
    return paths_without_priority[0] if paths_without_priority else paths[0]


def find_duplicates_to_remove(
    hash_to_paths: Dict[str, List[str]],
    priorities: List[str]
) -> List[str]:
    """
    Identify duplicate files to remove based on priority.

    IMPORTANT: Only processes hashes with 2 or more files. Single files
    are NEVER considered duplicates and will not be included in the output.

    Args:
        hash_to_paths: Dictionary mapping hashes to file paths
        priorities: List of priority directories in order

    Returns:
        List of file paths to remove (sorted)
    """
    paths_to_remove = []

    for hash_value, paths in hash_to_paths.items():
        # Critical: Only process if there are actual duplicates (2+ files)
        # Single files must NEVER be reported as duplicates
        if len(paths) <= 1:
            continue

        # Additional defensive check: ensure we actually have multiple paths
        assert len(paths) >= 2, f"Logic error: processing hash {hash_value} with {len(paths)} path(s)"

        # Determine which path to keep
        keeper = find_keeper_path(paths, priorities)

        # All other paths should be removed
        for path in paths:
            if path != keeper:
                paths_to_remove.append(path)

    # Sort for consistent output
    return sorted(paths_to_remove)


def find_duplicates_to_keep(
    hash_to_paths: Dict[str, List[str]],
    priorities: List[str]
) -> List[str]:
    """
    Identify duplicate files to keep based on priority.

    IMPORTANT: Only processes hashes with 2 or more files. Single files
    are NEVER considered duplicates and will not be included in the output.

    Args:
        hash_to_paths: Dictionary mapping hashes to file paths
        priorities: List of priority directories in order

    Returns:
        List of file paths to keep (sorted), one per duplicate set
    """
    paths_to_keep = []

    for hash_value, paths in hash_to_paths.items():
        # Critical: Only process if there are actual duplicates (2+ files)
        # Single files must NEVER be reported as duplicates
        if len(paths) <= 1:
            continue

        # Additional defensive check: ensure we actually have multiple paths
        assert len(paths) >= 2, f"Logic error: processing hash {hash_value} with {len(paths)} path(s)"

        # Determine which path to keep
        keeper = find_keeper_path(paths, priorities)
        paths_to_keep.append(keeper)

    # Sort for consistent output
    return sorted(paths_to_keep)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Find duplicate files based on hash values and directory priority.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    %(prog)s priorities.txt hashes1.txt hashes2.txt
    %(prog)s --show-kept priorities.txt hashes1.txt hashes2.txt

Priority file format (one directory per line):
    /tank/Pictures
    /tank/Photos

Hash file format (whitespace-separated HASH PATH):
    abc123... /tank/Pictures/photo1.jpg
    def456... /tank/Photos/photo2.jpg

By default, outputs all duplicate files to REMOVE (all but the highest priority one).
With --show-kept, outputs only the files being KEPT (one per duplicate set).
        """
    )

    parser.add_argument(
        'priority_file',
        type=Path,
        help='File containing priority directories (one per line, highest priority first)'
    )

    parser.add_argument(
        'hash_files',
        type=Path,
        nargs='+',
        help='One or more files containing "HASH PATH" pairs'
    )

    parser.add_argument(
        '-k', '--show-kept',
        action='store_true',
        help='Show files to KEEP (one per duplicate set) instead of files to REMOVE'
    )

    args = parser.parse_args()

    # Parse priority directories
    try:
        priorities = parse_priority_file(args.priority_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading priority file: {e}", file=sys.stderr)
        sys.exit(1)

    # Collect all hash-path pairs
    hash_to_paths = collect_all_hashes(args.hash_files)

    # Find duplicates based on mode
    if args.show_kept:
        paths_to_output = find_duplicates_to_keep(hash_to_paths, priorities)
        mode_description = "kept"
    else:
        paths_to_output = find_duplicates_to_remove(hash_to_paths, priorities)
        mode_description = "to remove"

    # Output results
    for path in paths_to_output:
        print(path)

    # Exit with appropriate status code
    if not paths_to_output:
        # No duplicates found - this is success, but we can inform on stderr
        print("No duplicate files found.", file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()
