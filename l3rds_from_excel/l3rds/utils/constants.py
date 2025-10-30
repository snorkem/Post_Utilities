"""Constants for lower thirds generation.

This module contains all magic numbers and ratios extracted from the original
codebase, making them centralized, named, and type-safe.
"""

from typing import Final

# Font size ratios relative to canvas height
MAIN_FONT_SIZE_RATIO: Final[float] = 1 / 18  # height / 18
SECONDARY_FONT_SIZE_RATIO: Final[float] = 1 / 25  # height / 25

# Vertical spacing ratio relative to main font size
VERTICAL_SPACING_RATIO: Final[float] = 0.5  # main_font_size / 2

# Padding ratios relative to canvas height
PADDING_RATIO: Final[float] = 0.02
PADDING_MULTIPLIER: Final[int] = 2

# Bar dimension ratios
BAR_HEIGHT_RATIO: Final[float] = 1 / 6  # height / 6
BAR_Y_POSITION_RATIO: Final[float] = 0.75  # 3/4 down the frame
BAR_PADDING_RATIO: Final[float] = 0.02

# Shadow defaults
DEFAULT_SHADOW_OFFSET_X: Final[int] = 2
DEFAULT_SHADOW_OFFSET_Y: Final[int] = 2
DEFAULT_SHADOW_BLUR: Final[int] = 20
DEFAULT_SHADOW_OPACITY: Final[int] = 128

# Blur conversion ranges
BLUR_SUBTLE_MIN: Final[int] = 1
BLUR_SUBTLE_MAX: Final[int] = 20
BLUR_MODERATE_MAX: Final[int] = 70
BLUR_HEAVY_MAX: Final[int] = 100

BLUR_SUBTLE_OUTPUT_MIN: Final[float] = 0.3
BLUR_SUBTLE_OUTPUT_MAX: Final[float] = 2.0
BLUR_MODERATE_OUTPUT_MIN: Final[float] = 2.0
BLUR_MODERATE_OUTPUT_MAX: Final[float] = 10.0
BLUR_HEAVY_OUTPUT_MIN: Final[float] = 10.0
BLUR_HEAVY_OUTPUT_MAX: Final[float] = 30.0

# Image format defaults
DEFAULT_IMAGE_WIDTH: Final[int] = 1920
DEFAULT_IMAGE_HEIGHT: Final[int] = 1080
DEFAULT_BIT_DEPTH: Final[int] = 16
DEFAULT_FORMAT: Final[str] = "png"

# Canvas dimension limits
MIN_IMAGE_WIDTH: Final[int] = 320
MAX_IMAGE_WIDTH: Final[int] = 7680
MIN_IMAGE_HEIGHT: Final[int] = 240
MAX_IMAGE_HEIGHT: Final[int] = 4320

# Bit depth scaling factor for 16-bit conversion
BIT_DEPTH_8_TO_16_MULTIPLIER: Final[int] = 257  # 65535 / 255

# Default colors
DEFAULT_BG_COLOR: Final[tuple[int, int, int]] = (0, 0, 0)  # Black
DEFAULT_TEXT_COLOR: Final[tuple[int, int, int]] = (255, 255, 255)  # White
DEFAULT_BAR_COLOR: Final[tuple[int, int, int, int]] = (0, 0, 0, 0)  # Transparent black
DEFAULT_SHADOW_COLOR: Final[str] = "black"

# Font system directories
FONT_DIRECTORIES: Final[tuple[str, ...]] = (
    "/usr/share/fonts/",  # Linux
    "/System/Library/Fonts/",  # macOS
    "C:\\Windows\\Fonts\\",  # Windows
    "~/.fonts/",  # User fonts on Linux
    "~/Library/Fonts/",  # User fonts on macOS
)

# Font file extensions
FONT_EXTENSIONS: Final[tuple[str, ...]] = ('.ttf', '.otf', '.ttc')

# Default fallback fonts (in order of preference)
DEFAULT_FONTS: Final[tuple[str, ...]] = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
)


class Dimensions:
    """Calculate standard dimensions based on canvas size.

    This class encapsulates all dimension calculations that depend on
    canvas width and height, using the ratios defined above.

    Attributes:
        width: Canvas width in pixels
        height: Canvas height in pixels

    Example:
        >>> dims = Dimensions(1920, 1080)
        >>> dims.main_font_size
        60
        >>> dims.padding
        43
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize with canvas dimensions.

        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
        """
        self.width = width
        self.height = height

    @property
    def main_font_size(self) -> int:
        """Calculate default main font size."""
        return int(self.height * MAIN_FONT_SIZE_RATIO)

    @property
    def secondary_font_size(self) -> int:
        """Calculate default secondary font size."""
        return int(self.height * SECONDARY_FONT_SIZE_RATIO)

    @property
    def padding(self) -> int:
        """Calculate default padding from edges."""
        return int(self.height * PADDING_RATIO) * PADDING_MULTIPLIER

    @property
    def bar_height(self) -> int:
        """Calculate default bar height."""
        return int(self.height * BAR_HEIGHT_RATIO)

    @property
    def bar_y_position(self) -> int:
        """Calculate default bar Y position."""
        return int(self.height * BAR_Y_POSITION_RATIO)

    @property
    def bar_padding(self) -> int:
        """Calculate default bar padding."""
        return int(self.height * BAR_PADDING_RATIO)

    def vertical_spacing(self, main_font_size: int) -> int:
        """Calculate vertical spacing based on main font size.

        Args:
            main_font_size: Size of the main font in points

        Returns:
            Vertical spacing in pixels
        """
        return int(main_font_size * VERTICAL_SPACING_RATIO)
