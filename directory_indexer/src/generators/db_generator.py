"""
Database Mode Generator
Generates HTML viewer with external SQLite database for directory indexer
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from .html_builder import HtmlBuilder
from .component_builder import ComponentBuilder
from .js_bundler import JavaScriptBundler
from .statistics_builder import StatisticsBuilder
from ..utils.formatting import get_size_human_readable


class DbGenerator:
    """
    Generator for database mode HTML output.

    This class orchestrates the generation of an HTML viewer file that
    loads data from an external SQLite database file.
    """

    def __init__(self):
        """Initialize the database mode generator with all required builders."""
        self.html_builder = HtmlBuilder()
        self.component_builder = ComponentBuilder()
        self.js_bundler = JavaScriptBundler()
        self.stats_builder = StatisticsBuilder()

    def generate(
        self,
        db_filename: str,
        root_path: str,
        total_size: int,
        extension_stats: Dict[str, Dict[str, Any]],
        files_data: List[Dict[str, Any]],
        output_file: str,
        db_size: int = 0
    ) -> None:
        """
        Generate HTML viewer file for database mode.

        Args:
            db_filename: Name of the SQLite database file
            root_path: Root directory path
            total_size: Total size of all files in bytes
            extension_stats: Extension statistics dictionary
            files_data: List of file dictionaries (for statistics pre-generation)
            output_file: Path where HTML file will be written
            db_size: Size of the database file in bytes (optional)
        """
        print("Building HTML components for database mode...")

        # Build context dictionary
        context = self._build_context(
            db_filename, root_path, total_size, extension_stats, files_data, db_size
        )

        print("Loading HTML templates...")

        # Load main template
        main_html = self.html_builder.load_template('db_mode/main.html')

        # Load all components
        components = self.html_builder.load_all_components('db_mode')

        print("Generating JavaScript bundle...")

        # Bundle JavaScript for database mode
        javascript_bundle = self.js_bundler.bundle_for_mode('db')

        # Get external scripts (sql.js for database mode)
        external_scripts = self.js_bundler.get_external_scripts('db')

        # Add JavaScript and external scripts to context
        context['javascript'] = self.js_bundler.wrap_in_script_tag(javascript_bundle)
        context['external_scripts'] = external_scripts

        print("Assembling final HTML...")

        # Load CSS styles
        css_styles = self.html_builder.load_css('db_mode')
        context['css_styles'] = css_styles

        # DB mode needs db_init_script to set window.dbFilename
        context['data_scripts'] = context['db_init_script']

        # Assemble the complete page
        final_html = self.html_builder.assemble_page(
            'db_mode',
            components,
            context
        )

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_html)

        print(f"✓ HTML viewer file generated: {output_file}")

    def _build_context(
        self,
        db_filename: str,
        root_path: str,
        total_size: int,
        extension_stats: Dict[str, Dict[str, Any]],
        files_data: List[Dict[str, Any]],
        db_size: int = 0
    ) -> Dict[str, str]:
        """
        Build context dictionary for template rendering.

        Args:
            db_filename: Name of the database file
            root_path: Root directory path
            total_size: Total size in bytes
            extension_stats: Extension statistics
            files_data: List of file dictionaries (for pre-generating statistics)
            db_size: Size of the database file in bytes

        Returns:
            Dictionary of template variables
        """
        root_name = Path(root_path).name or 'Root'
        generated_date = datetime.now().strftime('%Y-%m-%d')
        generated_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Build statistics components (pre-generated from data)
        stats_components = self.stats_builder.build_statistics_html(
            extension_stats, files_data
        )

        # Build extension options
        extension_options = self.component_builder.build_extension_options(extension_stats)

        # Create database initialization script
        db_init_script = self._create_db_init_script(db_filename)

        # Format database size
        db_size_human = get_size_human_readable(db_size) if db_size > 0 else "Unknown"

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
            'db_filename': db_filename,
            'db_init_script': db_init_script,
            'db_size_human': db_size_human,
            # Mode-specific placeholders for shared components
            'mode_suffix': ' • Database Mode',
            'db_mode_badge': f'<div class="db-mode-badge">🗄️ Database Mode • {db_size_human}</div>',
            'path_tooltip': '',  # No tooltip in DB mode
            'loading_title': 'Loading Database...',
            'loading_stats_initial': 'Initializing sql.js...',
            'column_settings_button': '',  # No column settings in DB mode
            'column_settings_panel': '',  # No column settings panel
            'browse_file_count': '<span class="file-count" id="browseFileCount"></span>',
            'path_column_name': 'directory',
            'size_column_name': 'size_bytes',
            'table_rows': '',  # No initial rows in DB mode
        }

    def _create_db_init_script(self, db_filename: str) -> str:
        """
        Create JavaScript initialization script for database.

        Args:
            db_filename: Name of the database file

        Returns:
            JavaScript code that sets the database filename
        """
        return f"""<script type="text/javascript">
window.dbFilename = '{db_filename}';
</script>"""

    def generate_css(self) -> str:
        """
        Generate or load CSS styles for database mode.

        Returns:
            CSS string
        """
        # For now, CSS is embedded in the HTML templates
        # This method is a placeholder for future CSS extraction
        return ""


# Convenience function for backward compatibility
def generate_html_with_db(
    db_filename: str,
    root_path: str,
    total_size: int,
    extension_stats: Dict[str, Dict[str, Any]],
    files_data: List[Dict[str, Any]],
    output_file: str,
    db_size: int = 0
) -> None:
    """
    Generate HTML viewer file with external database.

    This is a convenience function that creates a DbGenerator instance
    and calls its generate() method.

    Args:
        db_filename: Name of the SQLite database file
        root_path: Root directory path
        total_size: Total size of all files in bytes
        extension_stats: Extension statistics dictionary
        files_data: List of file dictionaries (for statistics)
        output_file: Path where HTML file will be written
        db_size: Size of the database file in bytes (optional)
    """
    generator = DbGenerator()
    generator.generate(db_filename, root_path, total_size, extension_stats, files_data, output_file, db_size)
