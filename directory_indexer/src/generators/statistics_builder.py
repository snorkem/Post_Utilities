"""
Statistics Builder
Generates statistics HTML components for the directory indexer
"""

from typing import Dict, List, Any
from .component_builder import ComponentBuilder


class StatisticsBuilder:
    """
    Builds the statistics section HTML for the directory indexer.

    This class aggregates data and generates HTML for various statistics
    including top extensions, largest files, and recent files.
    """

    def __init__(self):
        """Initialize the statistics builder with a component builder instance."""
        self.component_builder = ComponentBuilder()

    def build_statistics_html(
        self,
        extension_stats: Dict[str, Dict[str, Any]],
        files_data: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Build all statistics HTML components.

        Args:
            extension_stats: Dictionary mapping extensions to their statistics
                           (count, size, etc.)
            files_data: List of all file dictionaries

        Returns:
            Dictionary containing HTML strings for all statistics components:
            - top_extensions_by_count
            - top_extensions_by_size
            - largest_files
            - recent_files
            - recent_created
        """
        return {
            'top_extensions_by_count': self.component_builder.build_top_extensions_by_count(
                extension_stats, limit=10
            ),
            'top_extensions_by_size': self.component_builder.build_top_extensions_by_size(
                extension_stats, limit=10
            ),
            'largest_files': self.component_builder.build_largest_files(
                files_data, limit=50
            ),
            'recent_files': self.component_builder.build_recent_files(
                files_data, limit=50
            ),
            'recent_created': self.component_builder.build_recent_created_files(
                files_data, limit=50
            )
        }

    def build_extension_options(
        self,
        extension_stats: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Build extension filter dropdown options.

        Args:
            extension_stats: Dictionary mapping extensions to their statistics

        Returns:
            HTML string containing <option> elements
        """
        return self.component_builder.build_extension_options(extension_stats)

    def calculate_statistics(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate aggregate statistics from file data.

        Args:
            files_data: List of all file dictionaries

        Returns:
            Dictionary containing:
            - total_files: Total number of files
            - total_size: Total size in bytes
            - extension_stats: Extension statistics dictionary
            - largest_file: Largest file dictionary
            - oldest_file: Oldest modified file dictionary
            - newest_file: Newest modified file dictionary
        """
        if not files_data:
            return {
                'total_files': 0,
                'total_size': 0,
                'extension_stats': {},
                'largest_file': None,
                'oldest_file': None,
                'newest_file': None
            }

        total_size = sum(f.get('size', 0) for f in files_data)
        extension_stats = {}

        # Calculate per-extension statistics
        for file in files_data:
            ext = file.get('extension', 'no extension')
            if ext not in extension_stats:
                extension_stats[ext] = {
                    'count': 0,
                    'size': 0
                }
            extension_stats[ext]['count'] += 1
            extension_stats[ext]['size'] += file.get('size', 0)

        # Find extremes
        largest_file = max(files_data, key=lambda f: f.get('size', 0), default=None)

        # Sort by modified timestamp if available
        files_with_modified = [f for f in files_data if 'modified_ts' in f]
        if files_with_modified:
            oldest_file = min(files_with_modified, key=lambda f: f['modified_ts'])
            newest_file = max(files_with_modified, key=lambda f: f['modified_ts'])
        else:
            oldest_file = None
            newest_file = None

        return {
            'total_files': len(files_data),
            'total_size': total_size,
            'extension_stats': extension_stats,
            'largest_file': largest_file,
            'oldest_file': oldest_file,
            'newest_file': newest_file
        }

    def build_summary_stats(self, stats: Dict[str, Any]) -> str:
        """
        Build summary statistics HTML.

        Args:
            stats: Statistics dictionary from calculate_statistics()

        Returns:
            HTML string for summary statistics display
        """
        from ..utils.formatting import get_size_human_readable

        total_files = stats['total_files']
        total_size = stats['total_size']
        total_size_human = get_size_human_readable(total_size)
        extension_count = len(stats['extension_stats'])

        return f"""
        <div class="summary-stats">
            <div class="summary-stat">
                <div class="summary-stat-label">Total Files</div>
                <div class="summary-stat-value">{total_files:,}</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-label">Total Size</div>
                <div class="summary-stat-value">{total_size_human}</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-label">File Types</div>
                <div class="summary-stat-value">{extension_count}</div>
            </div>
        </div>
        """

    def build_complete_statistics_section(
        self,
        extension_stats: Dict[str, Dict[str, Any]],
        files_data: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Build complete statistics section with all components.

        This is a convenience method that generates all statistics HTML at once.

        Args:
            extension_stats: Dictionary mapping extensions to their statistics
            files_data: List of all file dictionaries

        Returns:
            Dictionary containing all statistics HTML components
        """
        stats_components = self.build_statistics_html(extension_stats, files_data)
        calculated_stats = self.calculate_statistics(files_data)
        stats_components['summary_stats'] = self.build_summary_stats(calculated_stats)

        return stats_components


# Convenience function for quick statistics generation
def build_statistics(
    extension_stats: Dict[str, Dict[str, Any]],
    files_data: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Convenience function to build all statistics HTML.

    Args:
        extension_stats: Dictionary mapping extensions to their statistics
        files_data: List of all file dictionaries

    Returns:
        Dictionary containing all statistics HTML components
    """
    builder = StatisticsBuilder()
    return builder.build_statistics_html(extension_stats, files_data)
