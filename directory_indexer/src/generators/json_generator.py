"""
JSON Mode Generator
Generates HTML with embedded JSON data for directory indexer
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from .html_builder import HtmlBuilder
from .component_builder import ComponentBuilder
from .js_bundler import JavaScriptBundler
from .statistics_builder import StatisticsBuilder
from ..utils.formatting import get_size_human_readable


class JsonGenerator:
    """
    Generator for JSON mode HTML output.

    This class orchestrates the generation of a single HTML file with
    embedded JSON data for all files in the directory tree.
    """

    def __init__(self):
        """Initialize the JSON generator with all required builders."""
        self.html_builder = HtmlBuilder()
        self.component_builder = ComponentBuilder()
        self.js_bundler = JavaScriptBundler()
        self.stats_builder = StatisticsBuilder()

    def generate(
        self,
        files_data: List[Any],  # Can be dict or FileInfo objects
        root_path: str,
        total_size: int,
        extension_stats: Dict[str, Dict[str, Any]],
        output_file: str,
        directory_tree: Dict[str, Any] = None
    ) -> None:
        """
        Generate HTML file with embedded JSON data.

        Args:
            files_data: List of all file dictionaries or FileInfo objects
            root_path: Root directory path
            total_size: Total size of all files in bytes
            extension_stats: Extension statistics dictionary
            output_file: Path where HTML file will be written
            directory_tree: Optional directory tree structure (for browse mode)
        """
        print("Building HTML components...")

        # Convert FileInfo objects to dictionaries if needed
        files_data = self._normalize_files_data(files_data)

        # Build context dictionary
        context = self._build_context(
            files_data, root_path, total_size, extension_stats, directory_tree
        )

        print("Loading HTML templates...")

        # Load main template
        main_html = self.html_builder.load_template('json_mode/main.html')

        # Load all components
        components = self.html_builder.load_all_components('json_mode')

        print("Generating JavaScript bundle...")

        # Bundle JavaScript
        javascript_bundle = self.js_bundler.bundle_for_mode('json')

        # Get external scripts (none for JSON mode)
        external_scripts = self.js_bundler.get_external_scripts('json')

        # Add JavaScript and external scripts to context
        context['javascript'] = self.js_bundler.wrap_in_script_tag(javascript_bundle)
        context['external_scripts'] = external_scripts

        print("Assembling final HTML...")

        # Load CSS styles
        css_styles = self.html_builder.load_css('json_mode')
        context['css_styles'] = css_styles

        # Create data scripts that set window variables
        data_scripts = f'''<script type="text/javascript">
// Embedded file data for JSON mode
window.fileData = {context['file_data_json']};
window.directoryTree = {context['directory_tree_json']};
</script>'''
        context['data_scripts'] = data_scripts

        # Assemble the complete page
        final_html = self.html_builder.assemble_page(
            'json_mode',
            components,
            context
        )

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_html)

        print(f"✓ HTML file generated: {output_file}")

    def _build_context(
        self,
        files_data: List[Dict[str, Any]],
        root_path: str,
        total_size: int,
        extension_stats: Dict[str, Dict[str, Any]],
        directory_tree: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """
        Build context dictionary for template rendering.

        Args:
            files_data: List of all file dictionaries
            root_path: Root directory path
            total_size: Total size in bytes
            extension_stats: Extension statistics
            directory_tree: Optional directory tree structure

        Returns:
            Dictionary of template variables
        """
        root_name = Path(root_path).name or 'Root'
        generated_date = datetime.now().strftime('%Y-%m-%d')
        generated_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Build statistics components
        stats_components = self.stats_builder.build_statistics_html(
            extension_stats, files_data
        )

        # Build extension options
        extension_options = self.component_builder.build_extension_options(extension_stats)

        # Embed JSON data
        files_json = self._embed_json_data(files_data)

        # Embed directory tree (if provided)
        if directory_tree:
            directory_tree_json = json.dumps(directory_tree, separators=(',', ':'))
        else:
            # Create minimal tree structure
            directory_tree_json = json.dumps({
                'name': root_name,
                'file_count': len(files_data),
                'total_size': total_size,
                'children': {},
                'files': []
            }, separators=(',', ':'))

        # Build column settings panel HTML
        column_settings_panel = '''<div class="settings-panel" id="settingsPanel">
    <h3 style="margin-bottom: 15px; font-size: 16px; color: #333;">Column Width Settings</h3>
    <div class="settings-grid">
        <div class="setting-item">
            <label class="setting-label">File Name</label>
            <div class="setting-input">
                <input type="range" id="nameWidth" min="10" max="50" value="20">
                <span class="setting-value" id="nameValue">20%</span>
            </div>
        </div>
        <div class="setting-item">
            <label class="setting-label">Type</label>
            <div class="setting-input">
                <input type="range" id="typeWidth" min="5" max="20" value="8">
                <span class="setting-value" id="typeValue">8%</span>
            </div>
        </div>
        <div class="setting-item">
            <label class="setting-label">Path</label>
            <div class="setting-input">
                <input type="range" id="pathWidth" min="20" max="70" value="45">
                <span class="setting-value" id="pathValue">45%</span>
            </div>
        </div>
        <div class="setting-item">
            <label class="setting-label">Size</label>
            <div class="setting-input">
                <input type="range" id="sizeWidth" min="10" max="25" value="15">
                <span class="setting-value" id="sizeValue">15%</span>
            </div>
        </div>
        <div class="setting-item">
            <label class="setting-label">Modified</label>
            <div class="setting-input">
                <input type="range" id="modifiedWidth" min="8" max="20" value="12">
                <span class="setting-value" id="modifiedValue">12%</span>
            </div>
        </div>
    </div>
    <div class="preset-buttons">
        <button class="preset-btn" data-preset="compact">Compact</button>
        <button class="preset-btn" data-preset="default">Default</button>
        <button class="preset-btn" data-preset="wide-path">Wide Path</button>
        <button class="preset-btn reset" id="resetWidths">Reset to Default</button>
    </div>
</div>'''

        return {
            'root_path': root_path,
            'root_name': root_name,
            'total_files': f"{len(files_data):,}",
            'total_size_human': get_size_human_readable(total_size),
            'total_extensions': str(len(extension_stats)),
            'generated_date': generated_date,
            'generated_datetime': generated_datetime,
            'extension_options': extension_options,
            'top_extensions_by_count': stats_components['top_extensions_by_count'],
            'top_extensions_by_size': stats_components['top_extensions_by_size'],
            'largest_files': stats_components['largest_files'],
            'recent_files': stats_components['recent_files'],
            'recent_created': stats_components['recent_created'],
            'file_data_json': files_json,
            'directory_tree_json': directory_tree_json,
            # Mode-specific placeholders for shared components
            'mode_suffix': '',  # Empty for JSON mode
            'db_mode_badge': '',  # Empty for JSON mode
            'path_tooltip': '<div class="path-tooltip" id="pathTooltip"></div>',
            'loading_title': 'Loading File Data...',
            'loading_stats_initial': 'Preparing...',
            'column_settings_button': '<button class="settings-toggle" id="settingsToggle">⚙️ Column Widths</button>',
            'column_settings_panel': column_settings_panel,
            'browse_file_count': '',  # Empty for JSON mode
            'path_column_name': 'path',
            'size_column_name': 'size',
            'table_rows': '',  # Rows populated dynamically by JavaScript
        }

    def _normalize_files_data(self, files_data: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert files_data to list of dictionaries.

        Args:
            files_data: List of file dictionaries or FileInfo objects

        Returns:
            List of file dictionaries
        """
        if not files_data:
            return []

        # Check if first item is a FileInfo object (has to_dict method)
        first_item = files_data[0]
        if hasattr(first_item, 'to_dict'):
            return [f.to_dict() for f in files_data]
        else:
            return files_data

    def _embed_json_data(self, files_data: List[Dict[str, Any]]) -> str:
        """
        Convert file data to JSON string.

        Args:
            files_data: List of file dictionaries

        Returns:
            JSON string of file data
        """
        # Convert to JSON with minimal formatting for size
        return json.dumps(files_data, separators=(',', ':'))

    def generate_css(self) -> str:
        """
        Generate or load CSS styles for JSON mode.

        Returns:
            CSS string
        """
        # For now, CSS is embedded in the HTML templates
        # This method is a placeholder for future CSS extraction
        return ""


# Convenience function for backward compatibility
def generate_html(
    files_data: List[Dict[str, Any]],
    root_path: str,
    total_size: int,
    extension_stats: Dict[str, Dict[str, Any]],
    output_file: str,
    directory_tree: Dict[str, Any] = None
) -> None:
    """
    Generate HTML file with embedded JSON data.

    This is a convenience function that creates a JsonGenerator instance
    and calls its generate() method.

    Args:
        files_data: List of all file dictionaries
        root_path: Root directory path
        total_size: Total size of all files in bytes
        extension_stats: Extension statistics dictionary
        output_file: Path where HTML file will be written
        directory_tree: Optional directory tree structure
    """
    generator = JsonGenerator()
    generator.generate(files_data, root_path, total_size, extension_stats, output_file, directory_tree)
