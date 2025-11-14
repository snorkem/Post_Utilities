"""
Statistics Builder
Generates statistics HTML components for the directory indexer
"""

from typing import Dict, List, Any
from .component_builder import ComponentBuilder
from ..config.settings import StatisticsConfig


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
                extension_stats, limit=StatisticsConfig.TOP_EXTENSIONS_COUNT
            ),
            'top_extensions_by_size': self.component_builder.build_top_extensions_by_size(
                extension_stats, limit=StatisticsConfig.TOP_EXTENSIONS_COUNT
            ),
            'largest_files': self.component_builder.build_largest_files(
                files_data, limit=StatisticsConfig.LARGEST_FILES_COUNT
            ),
            'recent_files': self.component_builder.build_recent_files(
                files_data, limit=StatisticsConfig.RECENT_FILES_COUNT
            ),
            'recent_created': self.component_builder.build_recent_created_files(
                files_data, limit=StatisticsConfig.RECENT_FILES_COUNT
            )
        }
