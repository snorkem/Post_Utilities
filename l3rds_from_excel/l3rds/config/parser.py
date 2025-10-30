"""Command-line argument parser for lower thirds generator.

This module provides a unified parser for converting command-line arguments
into configuration objects.
"""

import argparse
from typing import Any

from l3rds.config.models import (
    DefaultConfig,
    TextConfig,
    ShadowConfig,
    OutlineConfig,
    BarConfig,
    OutputConfig,
)
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigParser:
    """Parser for command-line arguments.

    This class creates an argparse parser and converts the parsed arguments
    into a DefaultConfig object.

    Example:
        >>> parser = ConfigParser()
        >>> config = parser.parse_args(['input.xlsx', 'output/'])
    """

    def __init__(self) -> None:
        """Initialize the argument parser."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all options.

        Returns:
            Configured ArgumentParser
        """
        parser = argparse.ArgumentParser(
            description="Generate lower third graphics from CSV or Excel data.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog(),
        )

        # Required arguments (unless using --generate-template)
        parser.add_argument("input_file", nargs="?", help="Path to CSV or Excel file")
        parser.add_argument("output_dir", nargs="?", help="Directory to save generated images")

        # Configuration file
        parser.add_argument(
            "--config",
            type=str,
            help="Load settings from JSON configuration file",
        )

        # Dimensions
        dims_group = parser.add_argument_group("Dimensions")
        dims_group.add_argument(
            "--width", type=int, default=1920, help="Image width (default: 1920)"
        )
        dims_group.add_argument(
            "--height", type=int, default=1080, help="Image height (default: 1080)"
        )

        # Colors
        color_group = parser.add_argument_group("Colors")
        color_group.add_argument(
            "--bg-color",
            default="black",
            help="Background color (default: black)",
        )
        color_group.add_argument(
            "--text-color",
            default="white",
            help="Main text color (default: white)",
        )
        color_group.add_argument(
            "--secondary-text-color",
            default=None,
            help="Secondary text color (default: same as text-color)",
        )
        color_group.add_argument(
            "--bar-color",
            default="black,0",
            help="Lower third bar color with optional alpha (default: black,0)",
        )

        # Text settings
        text_group = parser.add_argument_group("Text Settings")
        text_group.add_argument(
            "--letter-spacing",
            type=int,
            default=0,
            help="Character spacing in pixels (default: 0)",
        )
        text_group.add_argument(
            "--vertical-spacing",
            type=int,
            default=None,
            help="Space between main and secondary text in pixels",
        )
        text_group.add_argument(
            "--text-transform",
            default="none",
            choices=["none", "upper", "lower", "title"],
            help="Text case transformation (default: none)",
        )
        text_group.add_argument(
            "--wrap-text",
            action="store_true",
            help="Enable text wrapping",
        )
        text_group.add_argument(
            "--wrap-padding",
            type=int,
            default=None,
            help="Distance from image border where text wraps in pixels (required if wrapping enabled)",
        )
        text_group.add_argument(
            "--position-offset-x",
            type=int,
            default=0,
            help="Horizontal text position offset in pixels (positive=right, negative=left)",
        )
        text_group.add_argument(
            "--position-offset-y",
            type=int,
            default=0,
            help="Vertical text position offset in pixels (positive=down, negative=up)",
        )

        # Effects
        effects_group = parser.add_argument_group("Text Effects")
        effects_group.add_argument(
            "--text-shadow",
            action="store_true",
            help="Enable text shadow effect",
        )
        effects_group.add_argument(
            "--shadow-offset",
            default="2,2",
            help="Shadow offset as X,Y in pixels (default: 2,2)",
        )
        effects_group.add_argument(
            "--shadow-blur",
            type=int,
            default=20,
            help="Shadow blur amount 1-100 (default: 20)",
        )
        effects_group.add_argument(
            "--shadow-color",
            default="black",
            help="Shadow color (default: black)",
        )
        effects_group.add_argument(
            "--shadow-opacity",
            type=int,
            default=128,
            help="Shadow opacity 0-255 (default: 128)",
        )
        effects_group.add_argument(
            "--text-outline",
            default=None,
            help="Text outline as WIDTH,COLOR[,ALPHA] (e.g., 2,black,255)",
        )

        # Bar settings
        bar_group = parser.add_argument_group("Bar Settings")
        bar_group.add_argument(
            "--bar-height",
            type=int,
            default=None,
            help="Custom bar height in pixels",
        )
        bar_group.add_argument(
            "--bar-opacity",
            type=int,
            default=None,
            help="Bar transparency 0-255",
        )

        # Output settings
        output_group = parser.add_argument_group("Output Settings")
        output_group.add_argument(
            "--format",
            default="png",
            choices=["png", "jpg", "tiff"],
            help="Output format (default: png)",
        )
        output_group.add_argument(
            "--bit-depth",
            type=int,
            default=16,
            choices=[8, 16],
            help="Bit depth for TIFF images (default: 16). JPG is always 8-bit.",
        )
        output_group.add_argument(
            "--transparent",
            action="store_true",
            help="Use transparent background (PNG and TIFF only, ignored for JPG)",
        )
        output_group.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip generation if output file already exists",
        )

        # Modes and logging
        mode_group = parser.add_argument_group("Modes and Logging")
        mode_group.add_argument(
            "--test",
            action="store_true",
            help="Preview only the first image to check settings",
        )
        mode_group.add_argument(
            "--debug",
            action="store_true",
            help="Show detailed debug information",
        )
        mode_group.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging output",
        )
        mode_group.add_argument(
            "--quiet",
            action="store_true",
            help="Minimize logging output",
        )
        mode_group.add_argument(
            "--log-file",
            type=str,
            default=None,
            help="Write log output to file",
        )
        mode_group.add_argument(
            "--generate-template",
            type=str,
            metavar="OUTPUT_FILE",
            default=None,
            help="Generate Excel template file and exit (e.g., template.xlsx)",
        )

        return parser

    def _get_epilog(self) -> str:
        """Get epilog text for help message.

        Returns:
            Epilog text
        """
        return """
Excel/CSV Format:
  Required columns (in order):
    1. Main Text      - Primary text (typically a name)
    2. Secondary Text - Secondary text (typically a title)
    3. Justification  - Text position (e.g., "Lower Left", "Center Bottom")
    4. Main Font      - Font name or path to font file

  Optional columns:
    - Secondary Font, File Name, Main Font Size, Secondary Font Size
    - Padding, Main Color, Secondary Color, Background Color, Bar Color
    - Text Outline, Text Shadow, Shadow Color

  Note: Colors in Excel/CSV override command-line options per row.

Examples:
  Generate Excel template (no input/output required):
    python l3rds_from_excel.py --generate-template template.xlsx

  Basic usage:
    python l3rds_from_excel.py input.xlsx output/

  Custom dimensions and colors:
    python l3rds_from_excel.py input.xlsx output/ --width 1280 --height 720 \\
      --bg-color black --text-color white --bar-color "blue,150"

  With text effects:
    python l3rds_from_excel.py input.xlsx output/ --text-shadow \\
      --shadow-color black --text-outline "2,white"

  Test mode (preview first image):
    python l3rds_from_excel.py input.xlsx output/ --test

  Using configuration file:
    python l3rds_from_excel.py input.xlsx output/ --config settings.json

  16-bit TIFF for professional workflows:
    python l3rds_from_excel.py input.xlsx output/ --format tiff --bit-depth 16
"""

    def parse_args(self, args: list[str] | None = None) -> tuple[DefaultConfig, dict[str, Any]]:
        """Parse command-line arguments.

        Args:
            args: Arguments to parse (None = use sys.argv)

        Returns:
            Tuple of (config, extra_args) where extra_args contains
            input_file, output_dir, and test mode flag

        Example:
            >>> parser = ConfigParser()
            >>> config, extra = parser.parse_args(['input.xlsx', 'output/'])
        """
        parsed = self.parser.parse_args(args)

        # Load base config from file if specified
        if parsed.config:
            logger.info(f"Loading configuration from {parsed.config}")
            config = DefaultConfig.from_json(parsed.config)
        else:
            config = DefaultConfig()

        # Override with command-line arguments
        self._apply_args_to_config(config, parsed)

        # Extra arguments not in DefaultConfig
        extra_args = {
            "input_file": parsed.input_file,
            "output_dir": parsed.output_dir,
            "test_mode": parsed.test,
            "generate_template": parsed.generate_template,
        }

        return config, extra_args

    def _apply_args_to_config(self, config: DefaultConfig, args: argparse.Namespace) -> None:
        """Apply parsed arguments to configuration object.

        Args:
            config: Configuration to modify
            args: Parsed arguments
        """
        # Basic settings
        config.width = args.width
        config.height = args.height
        config.bg_color = args.bg_color

        # Logging
        if args.quiet:
            config.log_level = "WARNING"
        elif args.verbose or args.debug:
            config.log_level = "DEBUG"
        else:
            config.log_level = "INFO"

        config.debug = args.debug
        config.log_file = args.log_file

        # Text configuration
        config.text.text_color = args.text_color
        config.text.secondary_text_color = args.secondary_text_color
        config.text.letter_spacing = args.letter_spacing
        config.text.vertical_spacing = args.vertical_spacing
        config.text.text_transform = args.text_transform
        config.text.wrap_text = args.wrap_text
        config.text.wrap_padding = args.wrap_padding
        config.text.position_offset_x = args.position_offset_x
        config.text.position_offset_y = args.position_offset_y

        # Shadow configuration
        config.text.shadow.enabled = args.text_shadow
        if args.shadow_offset:
            parts = args.shadow_offset.split(",")
            if len(parts) >= 1:
                config.text.shadow.offset_x = int(parts[0])
            if len(parts) >= 2:
                config.text.shadow.offset_y = int(parts[1])

        config.text.shadow.blur = args.shadow_blur
        config.text.shadow.color = args.shadow_color
        config.text.shadow.opacity = args.shadow_opacity

        # Outline configuration
        if args.text_outline:
            config.text.outline = OutlineConfig.from_string(args.text_outline)

        # Bar configuration
        config.bar.color = args.bar_color
        config.bar.height = args.bar_height
        config.bar.opacity = args.bar_opacity

        # Output configuration
        config.output.format = args.format
        config.output.bit_depth = args.bit_depth
        config.output.transparent = args.transparent
        config.output.skip_existing = args.skip_existing

        # Enforce JPG format constraints
        if config.output.format == "jpg":
            if config.output.bit_depth != 8:
                logger.warning(
                    f"JPG format does not support {config.output.bit_depth}-bit depth. "
                    f"Forcing to 8-bit."
                )
                config.output.bit_depth = 8

            if config.output.transparent:
                logger.warning(
                    "JPG format does not support transparency. "
                    "Disabling transparent background."
                )
                config.output.transparent = False
