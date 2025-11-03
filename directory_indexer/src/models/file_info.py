"""
File information data model.

This module defines the FileInfo class for representing file metadata.
"""

from dataclasses import dataclass
from typing import Optional


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
