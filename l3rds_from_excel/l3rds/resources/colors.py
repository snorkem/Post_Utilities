"""Color parsing and conversion utilities.

This module provides a unified interface for parsing color specifications
in various formats (names, hex codes, RGB values) into RGB(A) tuples.
"""

import re
from typing import Final

from l3rds.utils.exceptions import ColorParseError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)

# Type alias for color tuples
ColorTuple = tuple[int, int, int] | tuple[int, int, int, int]


class ColorParser:
    """Parses color specifications into RGB(A) tuples.

    This class provides a unified interface for parsing colors in multiple
    formats and converting them to RGB or RGBA tuples suitable for PIL.

    Supported formats:
        - Color names: "red", "blue", "dark gray", etc.
        - Hex codes: "#FF0000", "00FF00" (with or without #)
        - RGB values: "255,0,0", "rgb(255,0,0)"
        - RGBA values: "red,128", "255,0,0,128"

    Example:
        >>> parser = ColorParser()
        >>> parser.parse("red")
        (255, 0, 0)
        >>> parser.parse("#00FF00")
        (0, 255, 0)
        >>> parser.parse("255,0,0,128")
        (255, 0, 0, 128)
    """

    # Color name lookup table
    COLOR_NAMES: Final[dict[str, tuple[int, int, int]]] = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "purple": (128, 0, 128),
        "orange": (255, 165, 0),
        "pink": (255, 192, 203),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
        "brown": (165, 42, 42),
        "navy": (0, 0, 128),
        "teal": (0, 128, 128),
        "lime": (0, 255, 0),
        "maroon": (128, 0, 0),
        "olive": (128, 128, 0),
        "silver": (192, 192, 192),
        "gold": (255, 215, 0),
        "indigo": (75, 0, 130),
        "violet": (238, 130, 238),
        "turquoise": (64, 224, 208),
        "tan": (210, 180, 140),
        "salmon": (250, 128, 114),
        "sky blue": (135, 206, 235),
        "khaki": (240, 230, 140),
        "crimson": (220, 20, 60),
        "dark blue": (0, 0, 139),
        "dark green": (0, 100, 0),
        "dark red": (139, 0, 0),
        "dark gray": (169, 169, 169),
        "dark grey": (169, 169, 169),
        "light gray": (211, 211, 211),
        "light grey": (211, 211, 211),
        "light blue": (173, 216, 230),
        "light green": (144, 238, 144),
        "light red": (255, 102, 102),
        "transparent": (0, 0, 0, 0),
    }

    # Regex patterns for different formats
    HEX_PATTERN: Final = re.compile(r"^#?([0-9a-fA-F]{6})$")
    RGB_PATTERN1: Final = re.compile(r"^rgb\((\d+),\s*(\d+),\s*(\d+)\)$")
    RGB_PATTERN2: Final = re.compile(r"^(\d+),\s*(\d+),\s*(\d+)$")
    RGBA_PATTERN: Final = re.compile(r"^(.+),\s*(\d+)$")

    @classmethod
    def parse(
        cls,
        color_spec: str | None,
        default_alpha: int = 255,
        fallback: ColorTuple | None = None,
        strict: bool = False,
    ) -> ColorTuple:
        """Parse a color specification into RGB(A) tuple.

        Args:
            color_spec: Color specification (name, hex, RGB, or RGBA)
            default_alpha: Default alpha value if not specified (0-255)
            fallback: Color to return if parsing fails (defaults to black)
            strict: If True, raise exception on parse failure instead of using fallback

        Returns:
            RGB or RGBA tuple

        Raises:
            ColorParseError: If strict=True and color cannot be parsed

        Example:
            >>> ColorParser.parse("red")
            (255, 0, 0)
            >>> ColorParser.parse("#FF0000")
            (255, 0, 0)
            >>> ColorParser.parse("255,0,0,128")
            (255, 0, 0, 128)
        """
        if color_spec is None:
            if fallback is None:
                fallback = (0, 0, 0)
            return fallback

        color_str = str(color_spec).lower().strip()

        # Try each parsing method in order
        result = (
            cls._parse_name(color_str)
            or cls._parse_hex(color_str)
            or cls._parse_rgb(color_str)
            or cls._parse_rgba(color_str)
        )

        if result is None:
            error_msg = f"Color '{color_spec}' not recognized"

            if strict:
                raise ColorParseError(
                    error_msg,
                    color_spec=color_spec,
                    expected_format="name, #RRGGBB, R,G,B, or R,G,B,A",
                )

            logger.warning(f"{error_msg}. Using fallback.")
            if fallback is None:
                fallback = (0, 0, 0)
            return fallback

        # Add alpha if not present and default_alpha is specified
        if len(result) == 3 and default_alpha != 255:
            return (*result, default_alpha)

        return result

    @classmethod
    def _parse_name(cls, color_str: str) -> ColorTuple | None:
        """Parse color name.

        Args:
            color_str: Lowercase color name

        Returns:
            RGB(A) tuple if found, None otherwise
        """
        return cls.COLOR_NAMES.get(color_str)

    @classmethod
    def _parse_hex(cls, color_str: str) -> tuple[int, int, int] | None:
        """Parse hex color code.

        Args:
            color_str: Hex color (with or without #)

        Returns:
            RGB tuple if valid, None otherwise
        """
        match = cls.HEX_PATTERN.match(color_str)
        if match:
            hex_value = match.group(1)
            return (
                int(hex_value[0:2], 16),
                int(hex_value[2:4], 16),
                int(hex_value[4:6], 16),
            )
        return None

    @classmethod
    def _parse_rgb(cls, color_str: str) -> tuple[int, int, int] | None:
        """Parse RGB format.

        Args:
            color_str: RGB string in format "R,G,B" or "rgb(R,G,B)"

        Returns:
            RGB tuple if valid, None otherwise
        """
        match = cls.RGB_PATTERN1.match(color_str) or cls.RGB_PATTERN2.match(color_str)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))

            # Validate range
            if all(0 <= val <= 255 for val in (r, g, b)):
                return (r, g, b)

        return None

    @classmethod
    def _parse_rgba(cls, color_str: str) -> ColorTuple | None:
        """Parse RGBA format.

        Args:
            color_str: RGBA string in format "color,alpha" where color
                      is any valid color format and alpha is 0-255

        Returns:
            RGBA tuple if valid, None otherwise
        """
        match = cls.RGBA_PATTERN.match(color_str)
        if match:
            color_part = match.group(1)
            alpha_str = match.group(2)

            try:
                alpha = int(alpha_str)

                # Validate alpha range
                if not 0 <= alpha <= 255:
                    return None

                # Recursively parse the color part
                rgb = cls.parse(color_part, default_alpha=alpha, strict=False)
                if rgb:
                    return (*rgb[:3], alpha)
            except ValueError:
                return None

        return None

    @classmethod
    def to_hex(cls, color: ColorTuple) -> str:
        """Convert RGB(A) tuple to hex string.

        Args:
            color: RGB or RGBA tuple

        Returns:
            Hex color string (e.g., "#FF0000")

        Example:
            >>> ColorParser.to_hex((255, 0, 0))
            '#FF0000'
        """
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    @classmethod
    def add_alpha(cls, color: ColorTuple, alpha: int = 255) -> tuple[int, int, int, int]:
        """Add alpha channel to RGB color.

        Args:
            color: RGB or RGBA tuple
            alpha: Alpha value (0-255)

        Returns:
            RGBA tuple

        Example:
            >>> ColorParser.add_alpha((255, 0, 0), 128)
            (255, 0, 0, 128)
        """
        return (*color[:3], alpha)

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """Check if a color name is recognized.

        Args:
            name: Color name to check

        Returns:
            True if name is recognized

        Example:
            >>> ColorParser.is_valid_name("red")
            True
            >>> ColorParser.is_valid_name("invalid")
            False
        """
        return name.lower() in cls.COLOR_NAMES

    @classmethod
    def get_available_names(cls) -> list[str]:
        """Get list of all available color names.

        Returns:
            Sorted list of color names

        Example:
            >>> names = ColorParser.get_available_names()
            >>> "red" in names
            True
        """
        return sorted(cls.COLOR_NAMES.keys())
