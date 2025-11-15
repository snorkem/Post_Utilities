"""
Directory scanning functionality.

This module provides the DirectoryScanner class for recursively scanning directories
and collecting file metadata.
"""

import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

from ..models import FileInfo, ScanResult
from ..config.settings import ProgressConfig


class DirectoryScanner:
    """Handles directory scanning and file metadata collection."""

    def __init__(self, root_path: str):
        """Initialize the directory scanner.

        Args:
            root_path: Path to the root directory to scan
        """
        self.root_path = Path(root_path).resolve()
        self.files_data: List[FileInfo] = []
        self.total_size = 0
        self.error_count = 0
        self.skipped_dirs = 0
        self.extension_stats = defaultdict(lambda: {'count': 0, 'size': 0})

    def scan(self) -> ScanResult:
        """Scan the directory and return results.

        Returns:
            ScanResult object containing all scan data

        Raises:
            FileNotFoundError: If root path doesn't exist
            NotADirectoryError: If root path is not a directory
        """
        if not self.root_path.exists():
            raise FileNotFoundError(f"Directory '{self.root_path}' does not exist")

        if not self.root_path.is_dir():
            raise NotADirectoryError(f"'{self.root_path}' is not a directory")

        print(f"Scanning {self.root_path}...")

        # Use os.scandir() for better performance (10-20% faster than os.walk)
        self._scan_directory(self.root_path)

        print(f"✓ Scan complete: {len(self.files_data)} files found")
        if self.error_count > 0 or self.skipped_dirs > 0:
            error_parts = []
            if self.error_count > 0:
                error_parts.append(f"{self.error_count} file{'s' if self.error_count != 1 else ''}")
            if self.skipped_dirs > 0:
                error_parts.append(f"{self.skipped_dirs} director{'ies' if self.skipped_dirs != 1 else 'y'}")
            print(f"  ({' and '.join(error_parts)} skipped due to permission errors)")

        # Convert defaultdict back to regular dict for compatibility
        extension_stats_dict = dict(self.extension_stats)

        return ScanResult(
            root_path=str(self.root_path),
            files_data=self.files_data,
            total_size=self.total_size,
            extension_stats=extension_stats_dict
        )

    def _scan_directory(self, dir_path: Path) -> None:
        """Recursively scan a directory using os.scandir() for better performance.

        Args:
            dir_path: Path to the directory to scan
        """
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    try:
                        # Check if it's a file (don't follow symlinks)
                        if entry.is_file(follow_symlinks=False):
                            file_info = self._process_file_from_entry(entry)
                            if file_info:
                                self.files_data.append(file_info)

                                # Report progress periodically
                                if len(self.files_data) % ProgressConfig.REPORT_INTERVAL == 0:
                                    print(f"  Processed {len(self.files_data)} files...")

                        # Recursively scan subdirectories
                        elif entry.is_dir(follow_symlinks=False):
                            self._scan_directory(Path(entry.path))

                    except (PermissionError, OSError):
                        # Skip files/dirs we can't access at the entry level
                        # Note: File processing errors are counted in _process_file_from_entry
                        continue

        except (PermissionError, OSError):
            # Can't access this directory itself
            self.skipped_dirs += 1

    def _process_file_from_entry(self, entry: os.DirEntry) -> FileInfo:
        """Process a single file from os.scandir() entry.

        Args:
            entry: os.DirEntry object from scandir()

        Returns:
            FileInfo object containing file metadata, or None if file couldn't be processed
        """
        try:
            # Get stat info directly from entry (more efficient)
            stat_info = entry.stat(follow_symlinks=False)
            filepath = Path(entry.path)
            extension = filepath.suffix.lower() or '(none)'

            # Cache expensive operations
            size_bytes = stat_info.st_size

            # Update totals and statistics
            self.total_size += size_bytes
            self.extension_stats[extension]['count'] += 1
            self.extension_stats[extension]['size'] += size_bytes

            # Create and return FileInfo object
            return FileInfo(
                name=entry.name,
                full_path=str(filepath.relative_to(self.root_path)),
                size=size_bytes,
                extension=extension,
                modified=stat_info.st_mtime
            )

        except (PermissionError, OSError):
            self.error_count += 1
            return None
