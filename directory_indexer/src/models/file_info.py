"""
File information data model.

This module defines the FileInfo class for representing file metadata.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class FileInfo:
    """Represents metadata for a single file.

    Attributes:
        name: Filename (basename)
        full_path: Complete file path relative to scan root
        size: File size in bytes
        extension: File extension (including dot, e.g., '.txt')
        modified: Last modified timestamp (Unix epoch)
    """
    name: str
    full_path: str
    size: int
    extension: str
    modified: float

    @property
    def path_without_name(self) -> str:
        """Get the directory path without the filename."""
        return self.full_path.rsplit('/', 1)[0] if '/' in self.full_path else ''

    def to_dict(self) -> Dict[str, Any]:
        """Convert FileInfo to dictionary format expected by generators.

        Note: FileInfo stores relative paths only. The 'path' field in the
        original scanner output contains absolute paths, but FileInfo doesn't
        preserve this information. For consistency with scanner output format,
        we include both 'path' and 'relative_path' pointing to the same value.

        Returns:
            Dictionary with all required fields for HTML generation
        """
        from ..utils.formatting import SizeFormatter, IconMapper

        # Format the modified timestamp
        modified_str = datetime.fromtimestamp(self.modified).strftime('%Y-%m-%d %H:%M:%S')

        return {
            'name': self.name,
            'path': self.full_path,  # Note: FileInfo only stores relative paths
            'relative_path': self.full_path,
            'directory': self.path_without_name,
            'size_bytes': self.size,
            'size_human': SizeFormatter.format_size(self.size),
            'extension': self.extension,
            'icon': IconMapper.get_icon(self.extension),
            'modified': modified_str,
            'created': modified_str,  # FileInfo doesn't track creation time separately
        }
