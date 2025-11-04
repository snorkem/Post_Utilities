"""Text rendering utilities.

This module provides functionality for rendering text with various effects
like letter spacing and text transformations.
"""

from PIL import ImageDraw, ImageFont

from l3rds.resources.colors import ColorParser
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class TextTransformer:
    """Transforms text case.

    Example:
        >>> transformer = TextTransformer()
        >>> transformer.transform("hello", "upper")
        'HELLO'
    """

    @staticmethod
    def transform(text: str, transform_type: str) -> str:
        """Transform text based on the specified type.

        Args:
            text: Text to transform
            transform_type: Transformation (none, upper, lower, title, capitalize, swapcase)

        Returns:
            Transformed text

        Example:
            >>> TextTransformer.transform("hello world", "title")
            'Hello World'
        """
        if transform_type == "upper":
            return text.upper()
        elif transform_type == "lower":
            return text.lower()
        elif transform_type == "title":
            return text.title()
        elif transform_type == "capitalize":
            return text.capitalize()
        elif transform_type == "swapcase":
            return text.swapcase()
        else:  # 'none' or any other value
            return text


class TextRenderer:
    """Renders text with various effects and transformations.

    This class handles all aspects of text rendering including:
    - Letter spacing
    - Text transformations
    - Color application
    - Dimension calculation

    Attributes:
        color_parser: ColorParser instance

    Example:
        >>> renderer = TextRenderer()
        >>> renderer.draw_text(draw, (100, 100), "Hello", font, "white")
    """

    def __init__(self, color_parser: ColorParser | None = None):
        """Initialize text renderer.

        Args:
            color_parser: ColorParser instance (creates default if None)
        """
        self.color_parser = color_parser or ColorParser()

    def wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        letter_spacing: int = 0,
        transform: str = "none",
    ) -> list[str]:
        """Wrap text to fit within max width.

        This method breaks text into multiple lines to ensure each line
        fits within the specified maximum width. It preserves explicit
        newline characters (\n) in the text before applying word wrapping.

        Args:
            draw: ImageDraw object
            text: Text to wrap (may contain \n for explicit line breaks)
            font: Font to use
            max_width: Maximum width in pixels
            letter_spacing: Character spacing
            transform: Text transformation

        Returns:
            List of text lines

        Example:
            >>> renderer = TextRenderer()
            >>> lines = renderer.wrap_text(draw, "Long text here", font, 200)
            ['Long text', 'here']
            >>> lines = renderer.wrap_text(draw, "Line 1\nLine 2", font, 200)
            ['Line 1', 'Line 2']
        """
        # Transform text first
        transformed_text = TextTransformer.transform(text, transform)

        # Split on explicit newlines first to preserve intentional line breaks
        explicit_lines = transformed_text.split('\n')

        # Word-wrap each explicit line
        all_lines = []
        for line in explicit_lines:
            # Split into words
            words = line.split()
            if not words:
                # Empty line (e.g., from consecutive newlines)
                all_lines.append("")
                continue

            current_line = []

            for word in words:
                # Try adding word to current line
                test_line = ' '.join(current_line + [word])
                width, _ = self.measure_text(draw, test_line, font, letter_spacing, "none")

                if width <= max_width:
                    current_line.append(word)
                else:
                    # Current line is full, start new line
                    if current_line:
                        all_lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # Single word too long, force it anyway
                        all_lines.append(word)

            # Add remaining words from this explicit line
            if current_line:
                all_lines.append(' '.join(current_line))

        return all_lines if all_lines else [""]

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        position: tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
        letter_spacing: int = 0,
        transform: str = "none",
        max_width: int | None = None,
    ) -> None:
        """Draw text with optional letter spacing and wrapping.

        Args:
            draw: ImageDraw object
            position: (x, y) position
            text: Text to draw
            font: Font to use
            color: Text color
            letter_spacing: Character spacing in pixels
            transform: Text transformation
            max_width: Maximum width for wrapping (None = no wrapping)

        Example:
            >>> renderer = TextRenderer()
            >>> renderer.draw_text(draw, (100, 100), "Hello", font, "white", letter_spacing=5)
            >>> renderer.draw_text(draw, (100, 100), "Long text", font, "white", max_width=200)
        """
        # Handle text wrapping if max_width is specified
        if max_width is not None:
            lines = self.wrap_text(draw, text, font, max_width, letter_spacing, transform)
            x, y = position

            for line in lines:
                self.draw_text(draw, (x, y), line, font, color, letter_spacing, "none", max_width=None)
                # Measure line height for next Y position
                _, line_height = self.measure_text(draw, line, font, letter_spacing, "none", max_width=None)
                y += line_height
            return

        # Transform text
        transformed_text = TextTransformer.transform(text, transform)

        # Parse color
        text_color = self.color_parser.parse(color)

        x, y = position

        # Handle letter spacing
        if letter_spacing < 0 and len(transformed_text) > 1:
            # Negative spacing: draw each character individually
            for char in transformed_text:
                draw.text((x, y), char, font=font, fill=text_color)
                char_bbox = draw.textbbox((0, 0), char, font=font)
                char_width = char_bbox[2] - char_bbox[0]
                x += char_width + letter_spacing

        elif letter_spacing > 0:
            # Positive spacing: add spaces between characters
            spaced_text = " ".join(transformed_text)
            draw.text((x, y), spaced_text, font=font, fill=text_color)

        else:
            # No special spacing
            draw.text((x, y), transformed_text, font=font, fill=text_color)

    def measure_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        letter_spacing: int = 0,
        transform: str = "none",
        max_width: int | None = None,
    ) -> tuple[int, int]:
        """Measure text dimensions, with optional wrapping.

        Args:
            draw: ImageDraw object
            text: Text to measure
            font: Font to use
            letter_spacing: Character spacing in pixels
            transform: Text transformation
            max_width: Maximum width for wrapping (None = no wrapping)

        Returns:
            Tuple of (width, height) in pixels

        Example:
            >>> renderer = TextRenderer()
            >>> width, height = renderer.measure_text(draw, "Hello", font)
            >>> width, height = renderer.measure_text(draw, "Long text", font, max_width=200)
        """
        # Handle text wrapping if max_width is specified
        if max_width is not None:
            lines = self.wrap_text(draw, text, font, max_width, letter_spacing, transform)

            # Measure each line
            max_line_width = 0
            total_height = 0

            for line in lines:
                width, height = self.measure_text(draw, line, font, letter_spacing, "none", max_width=None)
                max_line_width = max(max_line_width, width)
                total_height += height

            return (max_line_width, total_height)

        # Transform text
        transformed_text = TextTransformer.transform(text, transform)

        if letter_spacing > 0:
            # Measure with spaces
            spaced_text = " ".join(transformed_text)
            bbox = draw.textbbox((0, 0), spaced_text, font=font)
        elif letter_spacing < 0 and len(transformed_text) > 1:
            # Calculate cumulative width for negative spacing
            total_width = 0
            max_height = 0

            for i, char in enumerate(transformed_text):
                char_bbox = draw.textbbox((0, 0), char, font=font)
                char_width = char_bbox[2] - char_bbox[0]
                char_height = char_bbox[3] - char_bbox[1]
                total_width += char_width
                # Add spacing between characters (not after the last one)
                if i < len(transformed_text) - 1:
                    total_width += letter_spacing
                max_height = max(max_height, char_height)

            return (total_width, max_height)
        else:
            # Normal measurement
            bbox = draw.textbbox((0, 0), transformed_text, font=font)

        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        return (width, height)

    def prepare_text_positions(
        self,
        draw: ImageDraw.ImageDraw,
        main_text: str,
        secondary_text: str,
        main_font: ImageFont.FreeTypeFont,
        secondary_font: ImageFont.FreeTypeFont,
        main_position: tuple[int, int],
        secondary_position: tuple[int, int],
        letter_spacing: int = 0,
        transform: str = "none",
        max_width: int | None = None,
    ) -> list[tuple[tuple[int, int], str, ImageFont.FreeTypeFont]]:
        """Prepare text positions for effects rendering.

        This creates a list of text positions that can be used by
        effects like shadows and outlines. Supports multi-line wrapped text.

        Args:
            draw: ImageDraw object
            main_text: Main text
            secondary_text: Secondary text
            main_font: Main font
            secondary_font: Secondary font
            main_position: Main text position
            secondary_position: Secondary text position
            letter_spacing: Character spacing
            transform: Text transformation
            max_width: Maximum width for wrapping (None = no wrapping)

        Returns:
            List of (position, text, font) tuples

        Example:
            >>> positions = renderer.prepare_text_positions(...)
        """
        positions = []

        # Handle wrapped text if max_width is specified
        if max_width is not None:
            # Wrap main text
            main_lines = self.wrap_text(draw, main_text, main_font, max_width, letter_spacing, transform)
            x, y = main_position
            for line in main_lines:
                # Handle letter spacing for position preparation
                if letter_spacing > 0:
                    line_spaced = " ".join(line)
                else:
                    line_spaced = line
                positions.append(((x, y), line_spaced, main_font))
                # Move Y position down for next line
                _, line_height = self.measure_text(draw, line, main_font, letter_spacing, "none", max_width=None)
                y += line_height

            # Wrap secondary text
            secondary_lines = self.wrap_text(draw, secondary_text, secondary_font, max_width, letter_spacing, transform)
            x, y = secondary_position
            for line in secondary_lines:
                # Handle letter spacing for position preparation
                if letter_spacing > 0:
                    line_spaced = " ".join(line)
                else:
                    line_spaced = line
                positions.append(((x, y), line_spaced, secondary_font))
                # Move Y position down for next line
                _, line_height = self.measure_text(draw, line, secondary_font, letter_spacing, "none", max_width=None)
                y += line_height

            return positions

        # No wrapping - original single-line logic
        # Transform text
        main_text_transformed = TextTransformer.transform(main_text, transform)
        secondary_text_transformed = TextTransformer.transform(secondary_text, transform)

        # Handle letter spacing for position preparation
        if letter_spacing > 0:
            main_text_spaced = " ".join(main_text_transformed)
            secondary_text_spaced = " ".join(secondary_text_transformed)
        else:
            main_text_spaced = main_text_transformed
            secondary_text_spaced = secondary_text_transformed

        return [
            (main_position, main_text_spaced, main_font),
            (secondary_position, secondary_text_spaced, secondary_font),
        ]
