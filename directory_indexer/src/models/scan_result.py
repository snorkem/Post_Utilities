"""
Scan result data model.

This module defines the ScanResult class for encapsulating directory scan results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from .file_info import FileInfo


@dataclass
class ScanResult:
    """Encapsulates the results of a directory scan.

    Attributes:
        root_path: The root directory that was scanned
        files_data: List of FileInfo objects for all discovered files
        total_size: Total size of all files in bytes
        extension_stats: Dictionary mapping extensions to their statistics
                        Format: {'.ext': {'count': int, 'size': int}}
    """
    root_path: str
    files_data: List[FileInfo] = field(default_factory=list)
    total_size: int = 0
    extension_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        """Get the total number of files."""
        return len(self.files_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert scan result to dictionary format.

        Useful for JSON serialization.
        """
        return {
            'root_path': self.root_path,
            'file_count': self.file_count,
            'total_size': self.total_size,
            'extension_stats': self.extension_stats,
            'files': [
                {
                    'name': f.name,
                    'full_path': f.full_path,
                    'size': f.size,
                    'extension': f.extension,
                    'modified': f.modified
                }
                for f in self.files_data
            ]
        }
