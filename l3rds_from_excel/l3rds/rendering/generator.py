"""High-level generator orchestrator for lower thirds.

This module provides the main API for generating lower third images,
combining all the components into a simple interface.
"""

from PIL import Image

from l3rds.config.models import DefaultConfig
from l3rds.data.models import RowData
from l3rds.rendering.builder import LowerThirdBuilder
from l3rds.resources.colors import ColorParser
from l3rds.resources.fonts import FontLoader
from l3rds.utils.exceptions import ImageGenerationError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class LowerThirdGenerator:
    """High-level generator for lower third images.

    This class provides a simple API for generating lower thirds from
    Excel data, handling all the complexity internally.

    Example:
        >>> config = DefaultConfig()
        >>> generator = LowerThirdGenerator(config)
        >>> image = generator.generate_from_row(row_data)
    """

    def __init__(self, config: DefaultConfig):
        """Initialize the generator.

        Args:
            config: Configuration for generation
        """
        self.config = config
        self.font_loader = FontLoader()
        self.color_parser = ColorParser()

    def generate_from_row(self, row_data: RowData) -> Image.Image:
        """Generate a lower third image from row data.

        Args:
            row_data: Extracted row data

        Returns:
            Generated PIL Image

        Raises:
            ImageGenerationError: If generation fails

        Example:
            >>> image = generator.generate_from_row(row_data)
        """
        try:
            logger.info(f"Generating lower third for: {row_data.main_text}")

            # Create builder and construct image
            builder = LowerThirdBuilder(
                self.config,
                row_data,
                self.font_loader,
                self.color_parser,
            )

            image = (
                builder.create_canvas()
                .draw_bar()
                .load_fonts()
                .calculate_layout()
                .create_text_layer()
                .apply_shadow()
                .apply_outline()
                .render_text()
                .composite_layers()
                .build()
            )

            return image

        except Exception as e:
            raise ImageGenerationError(
                f"Failed to generate image for '{row_data.main_text}'",
                details=str(e),
            ) from e

    def generate_preview(self, row_data: RowData) -> Image.Image:
        """Generate a preview image (same as generate_from_row).

        Args:
            row_data: Extracted row data

        Returns:
            Generated PIL Image
        """
        return self.generate_from_row(row_data)
