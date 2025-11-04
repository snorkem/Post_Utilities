"""Font discovery and loading utilities.

This module provides a unified interface for discovering system fonts
and loading them with proper fallback handling. It eliminates the
140+ lines of duplicated font logic from the original implementation.
"""

import os
import random
import threading
from pathlib import Path
from typing import Final

from PIL import ImageFont

from l3rds.utils.constants import (
    FONT_DIRECTORIES,
    FONT_EXTENSIONS,
    DEFAULT_FONTS,
)
from l3rds.utils.exceptions import FontLoadError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class FontDiscovery:
    """Discovers and caches available fonts on the system.

    This class scans system font directories once and caches the results
    for performance. It provides methods for finding fonts by name or
    selecting random fonts.

    Attributes:
        _font_cache: Cached list of discovered fonts
        _cache_lock: Thread lock for protecting cache access

    Example:
        >>> discovery = FontDiscovery()
        >>> fonts = discovery.discover_fonts()
        >>> len(fonts) > 0
        True
    """

    _font_cache: list[Path] | None = None
    _cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def discover_fonts(cls) -> list[Path]:
        """Discover all available fonts on the system.

        This method scans system font directories and returns a list of
        all font files. Results are cached for performance.
        Thread-safe using double-checked locking pattern.

        Returns:
            List of paths to font files

        Example:
            >>> fonts = FontDiscovery.discover_fonts()
            >>> any(f.name.lower().contains('arial') for f in fonts)
            True
        """
        # First check without lock for performance (double-checked locking)
        if cls._font_cache is not None:
            return cls._font_cache

        # Acquire lock for cache initialization
        with cls._cache_lock:
            # Check again in case another thread initialized while we waited
            if cls._font_cache is not None:
                return cls._font_cache

            logger.info("Discovering system fonts...")
            fonts: list[Path] = []

            for font_dir_str in FONT_DIRECTORIES:
                font_dir = Path(os.path.expanduser(font_dir_str))

                if not font_dir.exists():
                    continue

                logger.debug(f"Scanning font directory: {font_dir}")

                try:
                    for root, dirs, files in os.walk(font_dir):
                        for file in files:
                            if file.lower().endswith(FONT_EXTENSIONS):
                                font_path = Path(root) / file
                                fonts.append(font_path)
                except PermissionError:
                    logger.warning(f"Permission denied accessing font directory: {font_dir}")
                except Exception as e:
                    logger.warning(f"Error scanning font directory {font_dir}: {e}")

            cls._font_cache = fonts
            logger.info(f"Discovered {len(fonts)} fonts on system")

            return fonts

    @classmethod
    def find_font_by_name(cls, name: str) -> Path | None:
        """Find a font file by partial name match.

        Args:
            name: Font name or partial name

        Returns:
            Path to font file if found, None otherwise

        Example:
            >>> path = FontDiscovery.find_font_by_name("Arial")
            >>> path is not None
            True
        """
        fonts = cls.discover_fonts()
        name_lower = name.lower()

        # Try exact match first (case-insensitive)
        for font_path in fonts:
            if name_lower == font_path.stem.lower():
                logger.debug(f"Found exact font match: {font_path}")
                return font_path

        # Try substring match
        for font_path in fonts:
            if name_lower in font_path.name.lower():
                logger.debug(f"Found font by substring: {font_path}")
                return font_path

        logger.debug(f"Font '{name}' not found")
        return None

    @classmethod
    def get_random_font(cls) -> Path | None:
        """Get a random font from discovered fonts.

        Returns:
            Path to random font file, or None if no fonts found

        Example:
            >>> font = FontDiscovery.get_random_font()
            >>> font is not None
            True
        """
        fonts = cls.discover_fonts()

        if not fonts:
            logger.warning("No fonts available for random selection")
            return None

        selected = random.choice(fonts)
        logger.info(f"Randomly selected font: {selected.name}")
        return selected

    @classmethod
    def get_default_font(cls) -> Path | None:
        """Get a default system font.

        Returns:
            Path to default font, or None if none found

        Example:
            >>> font = FontDiscovery.get_default_font()
            >>> font is not None
            True
        """
        for font_str in DEFAULT_FONTS:
            font_path = Path(font_str)
            if font_path.exists():
                logger.debug(f"Found default font: {font_path}")
                return font_path

        logger.debug("No default fonts found")
        return None

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the font cache.

        Use this if fonts are installed during runtime and need to be
        re-discovered.

        Example:
            >>> FontDiscovery.clear_cache()
            >>> fonts = FontDiscovery.discover_fonts()  # Re-scans directories
        """
        cls._font_cache = None
        logger.debug("Font cache cleared")


class FontLoader:
    """Loads fonts with fallback logic.

    This class handles loading fonts from various specifications
    (names, paths, "Random") with proper fallback handling.

    Attributes:
        font_discovery: FontDiscovery instance

    Example:
        >>> loader = FontLoader()
        >>> font = loader.load_font("Arial", 48)
    """

    def __init__(self, font_discovery: FontDiscovery | None = None):
        """Initialize the font loader.

        Args:
            font_discovery: FontDiscovery instance (creates default if None)
        """
        self.discovery = font_discovery or FontDiscovery()

    def load_font(
        self,
        font_spec: str | None,
        size: int,
        fallback_to_default: bool = True,
    ) -> ImageFont.FreeTypeFont:
        """Load a font with fallback to default.

        Args:
            font_spec: Font name, path, or "Random"
            size: Font size in points
            fallback_to_default: If True, fall back to default font on failure

        Returns:
            Loaded font object

        Raises:
            FontLoadError: If font cannot be loaded and fallback_to_default is False

        Example:
            >>> loader = FontLoader()
            >>> font = loader.load_font("Arial", 48)
            >>> font.size
            48
        """
        if not font_spec:
            logger.debug(f"No font specified, using default at {size}pt")
            return self._load_default_font(size, fallback_to_default)

        # Handle special "Random" keyword
        if font_spec.lower().strip() == "random":
            return self._load_random_font(size, fallback_to_default)

        # Try direct path
        if os.path.exists(font_spec):
            try:
                font = ImageFont.truetype(font_spec, size=size)
                logger.info(f"Loaded font from path: {font_spec} at {size}pt")
                return font
            except Exception as e:
                logger.warning(f"Cannot load font from path {font_spec}: {e}")

        # Try finding by name
        font_path = self.discovery.find_font_by_name(font_spec)
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), size=size)
                logger.info(f"Loaded font '{font_spec}' at {size}pt")
                return font
            except Exception as e:
                logger.warning(f"Cannot load font {font_path}: {e}")

        # Font not found
        logger.warning(f"Font '{font_spec}' not found")

        if fallback_to_default:
            return self._load_default_font(size, fallback_to_default)
        else:
            raise FontLoadError(
                f"Font not found",
                font_spec=font_spec,
            )

    def _load_random_font(
        self,
        size: int,
        fallback_to_default: bool = True,
    ) -> ImageFont.FreeTypeFont:
        """Load a random font.

        Args:
            size: Font size in points
            fallback_to_default: Fall back to default if random fails

        Returns:
            Loaded font object

        Raises:
            FontLoadError: If no fonts available and fallback_to_default is False
        """
        font_path = self.discovery.get_random_font()

        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), size=size)
                logger.info(f"Loaded random font: {font_path.name} at {size}pt")
                return font
            except Exception as e:
                logger.warning(f"Cannot load random font {font_path}: {e}")

        logger.warning("No fonts available for random selection")

        if fallback_to_default:
            return self._load_default_font(size, fallback_to_default)
        else:
            raise FontLoadError(
                "No fonts available for random selection",
                font_spec="Random",
            )

    def _load_default_font(
        self,
        size: int,
        fallback_to_pil: bool = True,
    ) -> ImageFont.FreeTypeFont:
        """Load a default system font.

        Args:
            size: Font size in points
            fallback_to_pil: Fall back to PIL's built-in font if needed

        Returns:
            Loaded font object

        Raises:
            FontLoadError: If no default font available and fallback_to_pil is False
        """
        default_path = self.discovery.get_default_font()

        if default_path:
            try:
                font = ImageFont.truetype(str(default_path), size=size)
                logger.info(f"Loaded default font: {default_path.name} at {size}pt")
                return font
            except Exception as e:
                logger.warning(f"Cannot load default font {default_path}: {e}")

        # Last resort - PIL's built-in default font
        if fallback_to_pil:
            logger.warning("Using PIL's built-in default font (size will be fixed)")
            return ImageFont.load_default()
        else:
            raise FontLoadError(
                "No default fonts available on system",
                attempted_paths=[str(p) for p in DEFAULT_FONTS],
            )

    def load_font_pair(
        self,
        main_font_spec: str | None,
        secondary_font_spec: str | None,
        main_size: int,
        secondary_size: int,
    ) -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
        """Load main and secondary fonts.

        If secondary font is not specified, uses the main font at a different size.

        Args:
            main_font_spec: Main font specification
            secondary_font_spec: Secondary font specification (None = use main)
            main_size: Main font size in points
            secondary_size: Secondary font size in points

        Returns:
            Tuple of (main_font, secondary_font)

        Example:
            >>> loader = FontLoader()
            >>> main, sec = loader.load_font_pair("Arial", None, 48, 36)
        """
        # Load main font
        main_font = self.load_font(main_font_spec, main_size)

        # Load secondary font
        if secondary_font_spec:
            secondary_font = self.load_font(secondary_font_spec, secondary_size)
        else:
            # Use main font spec at secondary size
            secondary_font = self.load_font(main_font_spec, secondary_size)

        return main_font, secondary_font
