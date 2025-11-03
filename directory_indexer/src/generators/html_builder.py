"""
HTML Template Builder

This module provides functionality for loading and assembling HTML templates
from separate component files.
"""

from pathlib import Path
from typing import Dict, Optional


class HtmlBuilder:
    """
    Builds HTML pages from component templates using placeholder replacement.

    This class manages the loading of HTML templates and components from the
    templates directory, and provides methods to assemble complete HTML pages
    by replacing placeholders with actual content.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the HTML builder.

        Args:
            templates_dir: Root directory containing templates. If None, uses
                          the default templates directory relative to this file.
        """
        if templates_dir is None:
            # Default to templates directory in project root
            project_root = Path(__file__).parent.parent.parent
            templates_dir = project_root / 'templates' / 'html'

        self.templates_dir = Path(templates_dir)
        self._template_cache: Dict[str, str] = {}

    def load_template(self, template_path: str) -> str:
        """
        Load an HTML template file.

        Args:
            template_path: Relative path to template from templates_dir
                          (e.g., 'base.html', 'json_mode/main.html')

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        # Check cache first
        if template_path in self._template_cache:
            return self._template_cache[template_path]

        full_path = self.templates_dir / template_path

        if not full_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_path} "
                f"(looked in {full_path})"
            )

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Cache the template
        self._template_cache[template_path] = content

        return content

    def load_component(self, mode: str, component_name: str) -> str:
        """
        Load an HTML component file for a specific mode.

        Args:
            mode: Mode name ('json_mode' or 'db_mode' or 'shared')
            component_name: Component name (e.g., 'header', 'tabs', 'table')

        Returns:
            Component HTML content as string

        Raises:
            FileNotFoundError: If component file doesn't exist
        """
        component_path = f"{mode}/components/{component_name}.html"
        return self.load_template(component_path)

    def render_template(self, template: str, context: Dict[str, str]) -> str:
        """
        Render a template by replacing {placeholders} with context values.

        Args:
            template: Template string with {placeholder} syntax
            context: Dictionary mapping placeholder names to replacement values

        Returns:
            Rendered template string with placeholders replaced
        """
        result = template

        for key, value in context.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        return result

    def assemble_page(
        self,
        mode: str,
        components: Dict[str, str],
        context: Dict[str, str]
    ) -> str:
        """
        Assemble a complete HTML page from components.

        This method:
        1. Loads the mode-specific main template
        2. Replaces placeholders in components with context values
        3. Replaces component placeholders with component HTML
        4. Loads the base template
        5. Replaces placeholders in base template with assembled content and context

        Args:
            mode: Mode name ('json_mode' or 'db_mode')
            components: Dictionary mapping component names to their HTML content
            context: Dictionary mapping placeholder names to values

        Returns:
            Complete HTML page as string
        """
        # Load mode-specific main template
        main_template = self.load_template(f"{mode}/main.html")

        # First, apply context to all components (for shared components with placeholders)
        rendered_components = {
            name: self.render_template(component, context)
            for name, component in components.items()
        }

        # Replace component placeholders in main template
        main_content = self.render_template(main_template, rendered_components)

        # Load base template
        base_template = self.load_template('base.html')

        # Extract modals component (goes outside container in base.html)
        modals_html = rendered_components.get('modals', '')

        # Assemble final page
        final_context = {
            **context,
            'page_content': main_content,
            'modals': modals_html
        }

        return self.render_template(base_template, final_context)

    def load_all_components(self, mode: str, shared: bool = True) -> Dict[str, str]:
        """
        Load all standard components for a mode, preferring shared over mode-specific.

        Args:
            mode: Mode name ('json_mode' or 'db_mode')
            shared: If True, tries to load shared components first (default: True)

        Returns:
            Dictionary mapping component names to their HTML content
        """
        components = {}

        # Standard component names
        component_names = [
            'header',
            'controls',
            'table',
            'browse',
            'statistics',
            'footer',
            'modals'
        ]

        # Load components, preferring shared over mode-specific
        for component_name in component_names:
            loaded = False

            # Try shared first
            if shared:
                try:
                    components[component_name] = self.load_component('shared', component_name)
                    loaded = True
                except FileNotFoundError:
                    pass

            # Fall back to mode-specific
            if not loaded:
                try:
                    components[component_name] = self.load_component(mode, component_name)
                except FileNotFoundError:
                    # Component may not exist for this mode
                    components[component_name] = ''

        # Always load tabs from shared
        if shared:
            try:
                components['tabs'] = self.load_component('shared', 'tabs')
            except FileNotFoundError:
                # Fallback to empty if shared component doesn't exist
                pass

        return components

    def load_css(self, mode: str) -> str:
        """
        Load and combine CSS files for a specific mode.

        Args:
            mode: Mode name ('json_mode' or 'db_mode')

        Returns:
            Combined CSS string

        Raises:
            FileNotFoundError: If CSS files don't exist
        """
        # CSS files are in templates/common/
        css_dir = self.templates_dir.parent / 'common'

        # Load common CSS (required for all modes)
        common_css_path = css_dir / 'common.css'
        if not common_css_path.exists():
            raise FileNotFoundError(f"Common CSS not found: {common_css_path}")

        with open(common_css_path, 'r', encoding='utf-8') as f:
            common_css = f.read()

        # Load mode-specific CSS
        mode_css_path = css_dir / f'{mode}.css'
        mode_css = ''
        if mode_css_path.exists():
            with open(mode_css_path, 'r', encoding='utf-8') as f:
                mode_css = f.read()

        # Load browse mode CSS (shared by both modes)
        browse_css_path = css_dir / 'browse_mode.css'
        browse_css = ''
        if browse_css_path.exists():
            with open(browse_css_path, 'r', encoding='utf-8') as f:
                browse_css = f.read()

        # Combine CSS
        return f"{common_css}\n\n{mode_css}\n\n{browse_css}"

    def clear_cache(self):
        """Clear the template cache."""
        self._template_cache.clear()
