"""
Scan result data model.

This module defines the ScanResult class for encapsulating directory scan results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Union
from .file_info import FileInfo


@dataclass
class ScanResult:
    """Encapsulates the results of a directory scan.

    Attributes:
        root_path: The root directory that was scanned
        files_data: List of file data (either FileInfo objects or dicts)
        total_size: Total size of all files in bytes
        extension_stats: Dictionary mapping extensions to their statistics
                        Format: {'.ext': {'count': int, 'size': int}}
    """
    root_path: str
    files_data: List[Union[FileInfo, Dict[str, Any]]] = field(default_factory=list)
    total_size: int = 0
    extension_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        """Get the total number of files."""
        return len(self.files_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert scan result to dictionary format.

        Handles both FileInfo objects and dictionary entries.
        Useful for JSON serialization.
        """
        files_list = []
        for f in self.files_data:
            if isinstance(f, FileInfo):
                # Convert FileInfo object to dict
                files_list.append({
                    'name': f.name,
                    'full_path': f.full_path,
                    'size': f.size,
                    'extension': f.extension,
                    'modified': f.modified
                })
            else:
                # Already a dict - extract relevant fields
                files_list.append({
                    'name': f.get('name', ''),
                    'full_path': f.get('relative_path', ''),
                    'size': f.get('size_bytes', 0),
                    'extension': f.get('extension', ''),
                    'modified': f.get('modified', '')
                })

        return {
            'root_path': self.root_path,
            'file_count': self.file_count,
            'total_size': self.total_size,
            'extension_stats': self.extension_stats,
            'files': files_list
        }
