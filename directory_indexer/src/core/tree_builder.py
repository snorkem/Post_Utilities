"""
Directory tree building for Directory Indexer.

This module provides functionality to build hierarchical tree structures
from flat file lists for visualization purposes.
"""

from typing import Dict, List, Any
from pathlib import Path


class DirectoryTreeBuilder:
    """
    Builds hierarchical tree structures from flat file lists.

    This class takes a flat list of file information and constructs a nested
    dictionary representing the folder hierarchy with aggregated metadata.
    """

    def __init__(self, root_path: Path):
        """
        Initialize the DirectoryTreeBuilder.

        Args:
            root_path: Root directory being indexed
        """
        self.root_path = root_path

    def build_tree(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a hierarchical tree structure from flat file list.

        Creates a nested dictionary representing the folder hierarchy with
        file counts, total sizes, and file lists at each level.

        Args:
            files_data: List of file information dictionaries

        Returns:
            Dictionary representing the root of the tree with nested structure
        """
        tree = {
            'name': Path(self.root_path).name or str(self.root_path),
            'path': '',
            'type': 'folder',
            'children': {},
            'file_count': 0,
            'total_size': 0,
            'files': []
        }

        for file_info in files_data:
            # Split the relative path into parts
            rel_path = file_info['relative_path']
            parts = Path(rel_path).parts

            # Check if file is in root directory (single path component)
            if len(parts) == 1:
                # File is in root directory
                tree['files'].append(file_info)
                tree['file_count'] += 1
                tree['total_size'] += file_info['size_bytes']
                continue

            current = tree

            # Navigate/create folder structure
            for i, part in enumerate(parts[:-1]):  # Exclude filename
                if part not in current['children']:
                    current['children'][part] = {
                        'name': part,
                        'path': str(Path(*parts[:i+1])),
                        'type': 'folder',
                        'children': {},
                        'file_count': 0,
                        'total_size': 0,
                        'files': []
                    }
                current = current['children'][part]

            # Add file to its parent folder
            current['files'].append(file_info)
            current['file_count'] += 1
            current['total_size'] += file_info['size_bytes']

            # Update root tree counts (for files in subdirectories only)
            tree['file_count'] += 1
            tree['total_size'] += file_info['size_bytes']

        return tree
