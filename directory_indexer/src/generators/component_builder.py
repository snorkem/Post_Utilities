"""
Component Builder

This module provides functionality for building dynamic HTML components
from file data and statistics.
"""

from typing import Dict, List, Any
from html import escape as html_escape
from ..utils.formatting import get_size_human_readable, get_file_icon


class ComponentBuilder:
    """
    Builds dynamic HTML components from data.

    This class generates HTML snippets for various UI components like
    extension options, statistics tables, and file lists.
    """

    @staticmethod
    def build_extension_options(extension_stats: Dict[str, Dict[str, Any]]) -> str:
        """
        Build HTML options for extension filter dropdown.

        Args:
            extension_stats: Dictionary mapping extensions to their statistics
                           (count, size, etc.)

        Returns:
            HTML string containing <option> elements
        """
        sorted_extensions = sorted(
            extension_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        return '\n'.join(
            f'<option value="{html_escape(ext)}">'
            f'{html_escape(ext)} ({stats["count"]} files)</option>'
            for ext, stats in sorted_extensions
        )

    @staticmethod
    def build_top_extensions_by_count(
        extension_stats: Dict[str, Dict[str, Any]],
        limit: int = 10
    ) -> str:
        """
        Build HTML for top extensions by file count.

        Args:
            extension_stats: Dictionary mapping extensions to their statistics
            limit: Maximum number of extensions to display (default: 10)

        Returns:
            HTML string containing list items
        """
        sorted_extensions = sorted(
            extension_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:limit]

        if not sorted_extensions:
            return '<li class="stat-list-item">No data available</li>'

        max_count = sorted_extensions[0][1]['count']

        html_items = []
        for ext, stats in sorted_extensions:
            percentage = (stats['count'] / max_count * 100) if max_count > 0 else 0
            html_items.append(f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label">
                                <span>{get_file_icon(ext)}</span>
                                <span>{html_escape(ext)}</span>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 80px;">
                                <span class="stat-list-value">{stats['count']:,}</span>
                                <div class="progress-bar" style="width: 60px;">
                                    <div class="progress-fill" style="width: {percentage}%"></div>
                                </div>
                            </div>
                        </li>""")

        return ''.join(html_items)

    @staticmethod
    def build_top_extensions_by_size(
        extension_stats: Dict[str, Dict[str, Any]],
        limit: int = 10
    ) -> str:
        """
        Build HTML for top extensions by total size.

        Args:
            extension_stats: Dictionary mapping extensions to their statistics
            limit: Maximum number of extensions to display (default: 10)

        Returns:
            HTML string containing list items
        """
        sorted_extensions = sorted(
            extension_stats.items(),
            key=lambda x: x[1]['size'],
            reverse=True
        )[:limit]

        if not sorted_extensions:
            return '<li class="stat-list-item">No data available</li>'

        max_size = sorted_extensions[0][1]['size']

        html_items = []
        for ext, stats in sorted_extensions:
            percentage = (stats['size'] / max_size * 100) if max_size > 0 else 0
            html_items.append(f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label">
                                <span>{get_file_icon(ext)}</span>
                                <span>{html_escape(ext)}</span>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 100px;">
                                <span class="stat-list-value">{get_size_human_readable(stats['size'])}</span>
                                <div class="progress-bar" style="width: 80px;">
                                    <div class="progress-fill" style="width: {percentage}%"></div>
                                </div>
                            </div>
                        </li>""")

        return ''.join(html_items)

    @staticmethod
    def build_largest_files(files_data: List[Dict[str, Any]], limit: int = 10) -> str:
        """
        Build HTML for largest files list.

        Args:
            files_data: List of file dictionaries with size and name info
            limit: Maximum number of files to display (default: 10)

        Returns:
            HTML string containing list items
        """
        sorted_files = sorted(
            files_data,
            key=lambda x: x['size_bytes'],
            reverse=True
        )[:limit]

        if not sorted_files:
            return '<li class="stat-list-item">No files available</li>'

        html_items = []
        for file_info in sorted_files:
            html_items.append(f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                                <span>{file_info['icon']}</span>
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {html_escape(file_info['name'])}
                                </span>
                            </div>
                            <span class="stat-list-value">{file_info['size_human']}</span>
                        </li>""")

        return ''.join(html_items)

    @staticmethod
    def build_recent_files(files_data: List[Dict[str, Any]], limit: int = 10) -> str:
        """
        Build HTML for recently modified files list.

        Args:
            files_data: List of file dictionaries with modified date info
            limit: Maximum number of files to display (default: 10)

        Returns:
            HTML string containing list items
        """
        sorted_files = sorted(
            files_data,
            key=lambda x: x['modified'],
            reverse=True
        )[:limit]

        if not sorted_files:
            return '<li class="stat-list-item">No files available</li>'

        html_items = []
        for file_info in sorted_files:
            html_items.append(f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                                <span>{file_info['icon']}</span>
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {html_escape(file_info['name'])}
                                </span>
                            </div>
                            <span class="stat-list-value" style="font-size: 11px;">{file_info['modified']}</span>
                        </li>""")

        return ''.join(html_items)

    @staticmethod
    def build_recent_created_files(
        files_data: List[Dict[str, Any]],
        limit: int = 10
    ) -> str:
        """
        Build HTML for recently created files list.

        Args:
            files_data: List of file dictionaries with created date info
            limit: Maximum number of files to display (default: 10)

        Returns:
            HTML string containing list items
        """
        sorted_files = sorted(
            files_data,
            key=lambda x: x['created'],
            reverse=True
        )[:limit]

        if not sorted_files:
            return '<li class="stat-list-item">No files available</li>'

        html_items = []
        for file_info in sorted_files:
            html_items.append(f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                                <span>{file_info['icon']}</span>
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {html_escape(file_info['name'])}
                                </span>
                            </div>
                            <span class="stat-list-value" style="font-size: 11px;">{file_info['created']}</span>
                        </li>""")

        return ''.join(html_items)

    @staticmethod
    def build_file_rows(files_data: List[Dict[str, Any]], max_file_size: int) -> str:
        """
        Build HTML table rows for file list (used in JSON mode).

        Args:
            files_data: List of file dictionaries
            max_file_size: Maximum file size for calculating size bar percentage

        Returns:
            HTML string containing table rows

        Note:
            In the current implementation, table rows are rendered by JavaScript
            using virtual scrolling. This method is kept for potential future use
            or for generating initial/fallback HTML.
        """
        if not files_data:
            return ''

        html_rows = []
        for file in files_data:
            size_percent = (
                (file['size_bytes'] / max_file_size * 100)
                if max_file_size > 0
                else 0
            )

            html_rows.append(f"""
                <tr>
                    <td>
                        <div class="file-name">
                            <span class="file-icon">{file['icon']}</span>
                            <span>{html_escape(file['name'])}</span>
                        </div>
                    </td>
                    <td><span class="file-extension">{html_escape(file['extension'])}</span></td>
                    <td class="file-path">{html_escape(file['directory'])}</td>
                    <td>
                        <div class="size-cell">
                            <div class="size-bar-container">
                                <div class="size-bar" style="width: {size_percent:.1f}%"></div>
                            </div>
                            <span class="size-text">{file['size_human']}</span>
                        </div>
                    </td>
                    <td class="modified">{file['modified']}</td>
                    <td class="modified">{file['created']}</td>
                </tr>""")

        return ''.join(html_rows)
