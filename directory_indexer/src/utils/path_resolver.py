"""
Output path resolution utilities.

This module handles resolving output file paths based on user input and directory structure.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional


class OutputPathResolver:
    """Resolves output file paths based on user input."""

    def __init__(self, root_path: str, output_arg: Optional[str] = None):
        """Initialize the path resolver.

        Args:
            root_path: The root directory being indexed
            output_arg: Optional output path argument from user
        """
        self.root_path = Path(root_path)
        self.output_arg = output_arg

    def resolve(self) -> str:
        """Resolve the final output path.

        Returns:
            Absolute path to the output HTML file

        Logic:
            - If no output arg: Create timestamped subfolder in root_path
            - If absolute path to existing dir: Create timestamped file in that dir
            - If absolute path (file): Use as-is
            - If relative path: Create subfolder in root_path
        """
        if self.output_arg:
            # User specified output path
            output_path = Path(self.output_arg)
            if output_path.is_absolute():
                # Check if it's an existing directory
                if output_path.is_dir():
                    # Generate filename inside the directory
                    return self._generate_file_in_dir(output_path)
                else:
                    # Use as filename (file or non-existent path)
                    return str(output_path)
            else:
                # Relative path specified - create subfolder in target directory
                return self._create_subfolder_with_relative(output_path)
        else:
            # Auto-generate filename and create subfolder
            return self._auto_generate_path()

    def _generate_file_in_dir(self, directory: Path) -> str:
        """Generate a timestamped filename in the given directory."""
        dir_name = self.root_path.name or 'root'
        base_name = f"index_{dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return str(directory / f"{base_name}.html")

    def _create_subfolder_with_relative(self, relative_path: Path) -> str:
        """Create subfolder in root_path based on relative path."""
        base_name = relative_path.stem  # filename without extension
        output_dir = self.root_path / base_name
        output_dir.mkdir(exist_ok=True)
        return str(output_dir / relative_path.name)

    def _auto_generate_path(self) -> str:
        """Auto-generate a timestamped path in root directory."""
        dir_name = self.root_path.name or 'root'
        base_name = f"index_{dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = self.root_path / base_name
        output_dir.mkdir(exist_ok=True)
        return str(output_dir / f"{base_name}.html")

    @staticmethod
    def get_directory_name(path: str) -> str:
        """Get the last component of a directory path.

        Args:
            path: Directory path

        Returns:
            Directory name or 'root' if empty
        """
        dir_name = Path(path).name
        return dir_name if dir_name else 'root'
