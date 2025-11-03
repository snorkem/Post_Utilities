"""
Directory scanning functionality.

This module provides the DirectoryScanner class for recursively scanning directories
and collecting file metadata.
"""

import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple

from ..models import FileInfo, ScanResult
from ..utils import get_size_human_readable, get_file_icon
from ..config.settings import ProgressConfig


class DirectoryScanner:
    """Handles directory scanning and file metadata collection."""

    def __init__(self, root_path: str):
        """Initialize the directory scanner.

        Args:
            root_path: Path to the root directory to scan
        """
        self.root_path = Path(root_path).resolve()
        self.files_data = []
        self.total_size = 0
        self.error_count = 0
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

        # Cache frequently used methods for performance
        get_size = get_size_human_readable
        get_icon = get_file_icon

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Convert dirpath once per directory
            dir_path_obj = Path(dirpath)

            for filename in filenames:
                file_data = self._process_file(dir_path_obj, filename, get_size, get_icon)
                if file_data:
                    self.files_data.append(file_data)

                    # Report progress periodically
                    if len(self.files_data) % ProgressConfig.REPORT_INTERVAL == 0:
                        print(f"  Processed {len(self.files_data)} files...")

        print(f"✓ Scan complete: {len(self.files_data)} files found")
        if self.error_count > 0:
            print(f"  ({self.error_count} files skipped due to permission errors)")

        # Convert defaultdict back to regular dict for compatibility
        extension_stats_dict = dict(self.extension_stats)

        # Convert file data dictionaries to FileInfo objects
        file_info_objects = [
            FileInfo(
                name=f['name'],
                full_path=f['relative_path'],
                size=f['size_bytes'],
                extension=f['extension'],
                modified=datetime.strptime(f['modified'], '%Y-%m-%d %H:%M:%S').timestamp()
            )
            for f in self.files_data
        ]

        return ScanResult(
            root_path=str(self.root_path),
            files_data=file_info_objects,
            total_size=self.total_size,
            extension_stats=extension_stats_dict
        )

    def scan_legacy(self) -> Tuple[List[Dict], int, Dict]:
        """Scan directory and return results in legacy format.

        This method maintains backward compatibility with the original
        return format: (files_data, total_size, extension_stats)

        Returns:
            Tuple of (files_data list, total_size int, extension_stats dict)
        """
        scan_result = self.scan()
        return self.files_data, self.total_size, scan_result.extension_stats

    def _process_file(
        self,
        dir_path_obj: Path,
        filename: str,
        get_size,
        get_icon
    ) -> Dict:
        """Process a single file and return its metadata.

        Args:
            dir_path_obj: Path object for the directory
            filename: Name of the file
            get_size: Function to format file size
            get_icon: Function to get file icon

        Returns:
            Dictionary containing file metadata, or None if file couldn't be processed
        """
        try:
            filepath = dir_path_obj / filename
            stat_info = filepath.stat()
            extension = filepath.suffix.lower() or '(none)'

            # Cache expensive operations
            size_bytes = stat_info.st_size
            parent_dir = filepath.parent

            # Handle cross-platform creation time
            try:
                # macOS/BSD uses st_birthtime for true creation time
                created_timestamp = stat_info.st_birthtime
            except AttributeError:
                # Linux/Windows uses st_ctime (inode change time, closest to creation)
                created_timestamp = stat_info.st_ctime

            file_data = {
                'name': filename,
                'path': str(filepath),
                'relative_path': str(filepath.relative_to(self.root_path)),
                'directory': str(parent_dir.relative_to(self.root_path)),
                'size_bytes': size_bytes,
                'size_human': get_size(size_bytes),
                'extension': extension,
                'icon': get_icon(extension),
                'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'created': datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            }

            self.total_size += size_bytes

            # Track extension statistics
            self.extension_stats[extension]['count'] += 1
            self.extension_stats[extension]['size'] += size_bytes

            return file_data

        except (PermissionError, OSError):
            self.error_count += 1
            return None
