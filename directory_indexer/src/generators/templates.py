"""
Template utilities for HTML generation.

This module provides utilities for loading CSS templates and building HTML components.
"""

from pathlib import Path
from typing import Dict, Any


class TemplateLoader:
    """Loads CSS and template files from the templates directory."""

    def __init__(self, templates_dir: Path = None):
        """
        Initialize the TemplateLoader.

        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default to templates/ directory relative to project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            templates_dir = project_root / 'templates'

        self.templates_dir = templates_dir

    def load_css(self, css_file: str) -> str:
        """
        Load CSS content from a file.

        Args:
            css_file: Relative path to CSS file from templates directory

        Returns:
            CSS content as string
        """
        css_path = self.templates_dir / css_file
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()

    def get_common_css(self) -> str:
        """
        Get common CSS used in both HTML templates.

        Returns:
            Common CSS content
        """
        return self.load_css('common/common.css')

    def get_json_mode_css(self) -> str:
        """
        Get CSS specific to JSON/inline mode.

        Returns:
            JSON mode CSS content
        """
        return self.load_css('common/json_mode.css')

    def get_db_mode_css(self) -> str:
        """
        Get CSS specific to database mode.

        Returns:
            Database mode CSS content
        """
        return self.load_css('common/db_mode.css')

    def get_browse_mode_css(self) -> str:
        """
        Get CSS for browse/hierarchical view.

        Returns:
            Browse mode CSS content
        """
        return self.load_css('common/browse_mode.css')


def generate_extension_options(extension_stats: Dict[str, Any]) -> str:
    """
    Generate HTML option elements for extension filter dropdown.

    Args:
        extension_stats: Dictionary of extension statistics

    Returns:
        HTML option elements as string
    """
    sorted_extensions = sorted(
        extension_stats.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )

    options = ['<option value="">All File Types</option>']
    for ext, stats in sorted_extensions:
        count = stats['count']
        display_ext = ext if ext else '(no extension)'
        options.append(f'<option value="{ext}">{display_ext} ({count:,})</option>')

    return '\n'.join(options)
