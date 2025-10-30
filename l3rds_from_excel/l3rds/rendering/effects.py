"""Text effect implementations for shadows and outlines.

This module provides classes for applying visual effects to text,
including shadows and outlines.
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from l3rds.config.models import ShadowConfig, OutlineConfig
from l3rds.resources.colors import ColorParser
from l3rds.utils.constants import (
    BLUR_SUBTLE_MIN,
    BLUR_SUBTLE_MAX,
    BLUR_MODERATE_MAX,
    BLUR_HEAVY_MAX,
    BLUR_SUBTLE_OUTPUT_MIN,
    BLUR_SUBTLE_OUTPUT_MAX,
    BLUR_MODERATE_OUTPUT_MIN,
    BLUR_MODERATE_OUTPUT_MAX,
    BLUR_HEAVY_OUTPUT_MIN,
    BLUR_HEAVY_OUTPUT_MAX,
)
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class BlurConverter:
    """Converts 1-100 blur scale to Gaussian blur radius.

    This class provides a non-linear mapping from an intuitive 1-100
    blur scale to appropriate Gaussian blur radius values for PIL.
    """

    @staticmethod
    def convert(blur_value: int) -> float:
        """Convert 1-100 scale to Gaussian blur radius.

        Args:
            blur_value: Blur intensity (1-100)

        Returns:
            Gaussian blur radius (0.3-30.0)

        Example:
            >>> BlurConverter.convert(20)
            2.0
            >>> BlurConverter.convert(50)
            6.0
        """
        # Clamp to valid range
        blur_value = max(BLUR_SUBTLE_MIN, min(BLUR_HEAVY_MAX, int(blur_value)))

        # Map to appropriate output range
        if blur_value <= BLUR_SUBTLE_MAX:
            # Subtle blur range: 0.3 to 2.0
            input_range = BLUR_SUBTLE_MAX - BLUR_SUBTLE_MIN
            output_range = BLUR_SUBTLE_OUTPUT_MAX - BLUR_SUBTLE_OUTPUT_MIN
            normalized = (blur_value - BLUR_SUBTLE_MIN) / input_range
            return BLUR_SUBTLE_OUTPUT_MIN + (normalized * output_range)

        elif blur_value <= BLUR_MODERATE_MAX:
            # Moderate blur range: 2.0 to 10.0
            input_range = BLUR_MODERATE_MAX - BLUR_SUBTLE_MAX
            output_range = BLUR_MODERATE_OUTPUT_MAX - BLUR_MODERATE_OUTPUT_MIN
            normalized = (blur_value - BLUR_SUBTLE_MAX) / input_range
            return BLUR_MODERATE_OUTPUT_MIN + (normalized * output_range)

        else:
            # Heavy blur range: 10.0 to 30.0
            input_range = BLUR_HEAVY_MAX - BLUR_MODERATE_MAX
            output_range = BLUR_HEAVY_OUTPUT_MAX - BLUR_HEAVY_OUTPUT_MIN
            normalized = (blur_value - BLUR_MODERATE_MAX) / input_range
            return BLUR_HEAVY_OUTPUT_MIN + (normalized * output_range)


class ShadowEffect:
    """Applies shadow effect to text.

    This class creates a blurred shadow layer that can be composited
    with the main image.

    Attributes:
        config: Shadow configuration
        color_parser: ColorParser instance

    Example:
        >>> shadow = ShadowEffect(shadow_config)
        >>> shadow_img = shadow.create_shadow_layer(...)
    """

    def __init__(self, config: ShadowConfig, color_parser: ColorParser | None = None):
        """Initialize shadow effect.

        Args:
            config: Shadow configuration
            color_parser: ColorParser instance (creates default if None)
        """
        self.config = config
        self.color_parser = color_parser or ColorParser()

    def create_shadow_layer(
        self,
        canvas_size: tuple[int, int],
        text_positions: list[tuple[tuple[int, int], str, ImageFont.FreeTypeFont]],
    ) -> Image.Image:
        """Create a shadow layer for the given text.

        Args:
            canvas_size: (width, height) of canvas
            text_positions: List of (position, text, font) tuples

        Returns:
            RGBA image with shadow

        Example:
            >>> positions = [((100, 100), "Hello", font)]
            >>> shadow_img = shadow.create_shadow_layer((1920, 1080), positions)
        """
        if not self.config.enabled:
            # Return transparent image if shadow not enabled
            return Image.new("RGBA", canvas_size, (0, 0, 0, 0))

        logger.debug("Creating shadow layer")

        # Parse shadow color
        shadow_rgb = self.color_parser.parse(self.config.color)
        shadow_color = (*shadow_rgb[:3], self.config.opacity)

        # Convert blur value
        blur_radius = BlurConverter.convert(self.config.blur)

        # Create transparent image for shadow
        shadow_img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)

        # Draw all text with offset
        for (x, y), text, font in text_positions:
            shadow_x = x + self.config.offset_x
            shadow_y = y + self.config.offset_y

            shadow_draw.text(
                (shadow_x, shadow_y),
                text,
                font=font,
                fill=shadow_color,
            )

        # Apply Gaussian blur
        if blur_radius > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        logger.debug(f"Shadow created with blur radius {blur_radius:.2f}")
        return shadow_img


class OutlineEffect:
    """Applies outline effect to text.

    This class creates text outlines by drawing the text multiple times
    with small offsets.

    Attributes:
        config: Outline configuration
        color_parser: ColorParser instance

    Example:
        >>> outline = OutlineEffect(outline_config)
        >>> outline.draw_outline(draw, positions)
    """

    def __init__(self, config: OutlineConfig, color_parser: ColorParser | None = None):
        """Initialize outline effect.

        Args:
            config: Outline configuration
            color_parser: ColorParser instance (creates default if None)
        """
        self.config = config
        self.color_parser = color_parser or ColorParser()

    def draw_outline(
        self,
        draw: ImageDraw.ImageDraw,
        text_positions: list[tuple[tuple[int, int], str, ImageFont.FreeTypeFont]],
    ) -> None:
        """Draw text outline on the given draw context.

        Args:
            draw: ImageDraw object to draw on
            text_positions: List of (position, text, font) tuples

        Example:
            >>> draw = ImageDraw.Draw(image)
            >>> positions = [((100, 100), "Hello", font)]
            >>> outline.draw_outline(draw, positions)
        """
        if not self.config.enabled:
            return

        logger.debug(f"Drawing {self.config.width}px outline")

        # Parse outline color
        outline_rgb = self.color_parser.parse(self.config.color)
        outline_color = (*outline_rgb[:3], self.config.opacity)

        width = self.config.width

        # Draw text multiple times with offsets to create outline
        for (x, y), text, font in text_positions:
            for offset_x in range(-width, width + 1):
                for offset_y in range(-width, width + 1):
                    # Skip the center (will be drawn later as main text)
                    if offset_x == 0 and offset_y == 0:
                        continue

                    draw.text(
                        (x + offset_x, y + offset_y),
                        text,
                        font=font,
                        fill=outline_color,
                    )
