"""
JavaScript Bundler
Combines multiple JavaScript modules into a single bundled script for HTML embedding
"""

import os
from pathlib import Path
from typing import List, Optional


class JavaScriptBundler:
    """
    Bundles JavaScript modules into a single script for embedding in HTML.

    This class loads individual JavaScript module files and combines them in the correct
    order to create a single bundled script. It handles both JSON mode and database mode
    with their respective dependencies.
    """

    # Module load order for JSON mode
    JSON_MODE_MODULES = [
        # Common utilities (no dependencies)
        'common/utils.js',
        'common/sorting.js',

        # Table components
        'table/VirtualTableRenderer.js',
        'table/TableFilter.js',
        'table/TableSorter.js',

        # UI components
        'components/ColumnManager.js',
        'components/TabManager.js',
        'components/Tooltip.js',

        # Data layer (depends on common utilities)
        'data/DataService.js',
        'data/JsonDataLoader.js',

        # Browse mode (depends on data layer and utilities)
        'browse/BrowseState.js',
        'browse/TreeRenderer.js',
        'browse/FileListRenderer.js',
        'browse/BreadcrumbManager.js',
        'browse/BrowseController.js',

        # Entry point (depends on everything above)
        'json-mode.js'
    ]

    # Module load order for database mode
    DB_MODE_MODULES = [
        # Common utilities
        'common/utils.js',
        'common/sorting.js',

        # Table components
        'table/TableSorter.js',

        # UI components
        'components/ColumnManager.js',
        'components/TabManager.js',
        'components/Tooltip.js',

        # Data layer (database-specific)
        'data/DataService.js',
        'data/DatabaseLoader.js',

        # Browse mode (limited support in DB mode)
        'browse/BrowseState.js',
        'browse/TreeRenderer.js',
        'browse/FileListRenderer.js',
        'browse/BreadcrumbManager.js',
        'browse/BrowseController.js',

        # Entry point
        'db-mode.js'
    ]

    def __init__(self, js_dir: Optional[str] = None):
        """
        Initialize the JavaScript bundler.

        Args:
            js_dir: Path to the JavaScript templates directory.
                   If None, uses default location relative to this file.
        """
        if js_dir is None:
            # Default to templates/js directory relative to project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            js_dir = project_root / 'templates' / 'js'

        self.js_dir = Path(js_dir)

        if not self.js_dir.exists():
            raise FileNotFoundError(f"JavaScript directory not found: {self.js_dir}")

    def load_module(self, module_path: str) -> str:
        """
        Load a single JavaScript module file.

        Args:
            module_path: Relative path to the module within js_dir (e.g., 'common/utils.js')

        Returns:
            str: Content of the JavaScript module

        Raises:
            FileNotFoundError: If the module file doesn't exist
        """
        full_path = self.js_dir / module_path

        if not full_path.exists():
            raise FileNotFoundError(f"JavaScript module not found: {full_path}")

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            raise IOError(f"Error reading JavaScript module {module_path}: {e}")

    def bundle_modules(self, module_list: List[str]) -> str:
        """
        Bundle multiple JavaScript modules into a single script.

        Args:
            module_list: List of module paths to bundle in order

        Returns:
            str: Combined JavaScript code
        """
        bundled_code = []

        for module_path in module_list:
            try:
                module_content = self.load_module(module_path)

                # Add module separator comment
                separator = f"\n// ========== {module_path} ==========\n"
                bundled_code.append(separator)
                bundled_code.append(module_content)
                bundled_code.append("\n")

            except FileNotFoundError as e:
                print(f"Warning: {e}")
                continue
            except Exception as e:
                print(f"Error loading module {module_path}: {e}")
                continue

        return ''.join(bundled_code)

    def bundle_for_mode(self, mode: str) -> str:
        """
        Bundle JavaScript for the specified mode.

        Args:
            mode: Either 'json' or 'db' (database)

        Returns:
            str: Bundled JavaScript code for the specified mode

        Raises:
            ValueError: If mode is not 'json' or 'db'
        """
        if mode == 'json':
            module_list = self.JSON_MODE_MODULES
        elif mode == 'db' or mode == 'database':
            module_list = self.DB_MODE_MODULES
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'json' or 'db'")

        return self.bundle_modules(module_list)

    def wrap_in_script_tag(self, js_code: str, script_type: str = 'text/javascript') -> str:
        """
        Wrap JavaScript code in HTML <script> tags.

        Args:
            js_code: JavaScript code to wrap
            script_type: Script type attribute (default: 'text/javascript')

        Returns:
            str: JavaScript wrapped in script tags
        """
        return f'<script type="{script_type}">\n{js_code}\n</script>'

    def get_external_scripts(self, mode: str) -> str:
        """
        Get external script tags needed for the specified mode.

        Args:
            mode: Either 'json' or 'db'

        Returns:
            str: HTML script tags for external dependencies
        """
        if mode == 'db' or mode == 'database':
            # Database mode requires sql.js
            return '''<script src="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.js"></script>'''
        else:
            # JSON mode has no external dependencies
            return ''
