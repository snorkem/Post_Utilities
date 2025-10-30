"""Lower third image builder using the Builder pattern.

This module implements step-by-step construction of lower third images,
breaking apart the massive 568-line generation function from the original code.
"""

from PIL import Image, ImageDraw

from l3rds.config.models import DefaultConfig
from l3rds.data.models import RowData
from l3rds.rendering.effects import ShadowEffect, OutlineEffect
from l3rds.rendering.positioning import TextDimensions, PositionStrategyFactory
from l3rds.rendering.text_renderer import TextRenderer
from l3rds.resources.colors import ColorParser
from l3rds.resources.fonts import FontLoader
from l3rds.utils.exceptions import ImageGenerationError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class LowerThirdBuilder:
    """Builder for constructing lower third images step by step.

    This class implements the Builder pattern for creating lower third
    images, allowing for clear separation of construction steps and
    making the code more maintainable and testable.

    Example:
        >>> builder = LowerThirdBuilder(config, row_data)
        >>> image = (builder
        ...     .create_canvas()
        ...     .draw_bar()
        ...     .load_fonts()
        ...     .calculate_layout()
        ...     .create_text_layer()
        ...     .apply_shadow()
        ...     .apply_outline()
        ...     .render_text()
        ...     .composite_layers()
        ...     .build())
    """

    def __init__(
        self,
        config: DefaultConfig,
        row_data: RowData,
        font_loader: FontLoader | None = None,
        color_parser: ColorParser | None = None,
    ):
        """Initialize the builder.

        Args:
            config: Default configuration
            row_data: Row data from Excel
            font_loader: FontLoader instance
            color_parser: ColorParser instance
        """
        self.config = config
        self.row_data = row_data
        self.font_loader = font_loader or FontLoader()
        self.color_parser = color_parser or ColorParser()
        self.text_renderer = TextRenderer(self.color_parser)

        # State for building
        self.image: Image.Image | None = None
        self.draw: ImageDraw.ImageDraw | None = None
        self.text_layer: Image.Image | None = None
        self.text_draw: ImageDraw.ImageDraw | None = None

        # Layout calculated values
        self.main_font = None
        self.secondary_font = None
        self.main_x = 0
        self.main_y = 0
        self.secondary_x = 0
        self.secondary_y = 0
        self.max_width = None  # For text wrapping

        # Colors (with row overrides)
        self.bg_color = self._get_color(row_data.bg_color, config.bg_color)
        self.main_text_color = self._get_color(row_data.main_color, config.text.text_color)
        self.secondary_text_color = self._get_color(
            row_data.secondary_color,
            config.text.secondary_text_color or config.text.text_color,
        )
        self.bar_color = self._get_color(row_data.bar_color, config.bar.color)

        # Apply bar opacity override if specified
        if config.bar.opacity is not None:
            bar_rgb = self.color_parser.parse(self.bar_color)
            self.bar_color_rgba = (*bar_rgb[:3], config.bar.opacity)
        else:
            self.bar_color_rgba = self.color_parser.parse(self.bar_color, default_alpha=0)

    def _get_color(self, row_value: str | None, config_value: str) -> str:
        """Get color, preferring row value over config."""
        return row_value if row_value is not None else config_value

    def create_canvas(self) -> "LowerThirdBuilder":
        """Create the base canvas with background.

        Returns:
            Self for method chaining
        """
        logger.debug(f"Creating canvas: {self.config.width}x{self.config.height}")

        # Determine image mode
        if self.config.output.transparent:
            mode = "RGBA"
            bg_rgba = self.color_parser.parse(self.bg_color, default_alpha=0)
        else:
            mode = "RGB"
            bg_rgba = self.color_parser.parse(self.bg_color)

        self.image = Image.new(mode, (self.config.width, self.config.height), color=bg_rgba)
        self.draw = ImageDraw.Draw(self.image)

        return self

    def draw_bar(self) -> "LowerThirdBuilder":
        """Draw the lower third bar.

        Returns:
            Self for method chaining
        """
        if self.draw is None:
            raise ImageGenerationError("Must call create_canvas() before draw_bar()")

        bar_height = self.config.bar.get_height(self.config.dimensions)
        bar_y = int(self.config.height * self.config.bar.y_position_ratio)

        logger.debug(f"Drawing bar: height={bar_height}, y={bar_y}, color={self.bar_color_rgba}")

        self.draw.rectangle(
            [(0, bar_y), (self.config.width, bar_y + bar_height)],
            fill=self.bar_color_rgba,
        )

        return self

    def load_fonts(self) -> "LowerThirdBuilder":
        """Load main and secondary fonts with priority chain.

        Priority for main font: Excel > JSON config > GUI > hardcoded "Arial"
        Priority for secondary font: Excel > (GUI main if no Excel main) > JSON secondary > JSON main
        Priority for font sizes: Excel > JSON config > auto-calculated

        Returns:
            Self for method chaining
        """
        # Font size priority: Excel > JSON config > auto-calculated
        main_font_size = (
            self.row_data.main_font_size
            or self.config.text.main_font_size
            or self.config.text.get_main_font_size(self.config.dimensions)
        )
        secondary_font_size = (
            self.row_data.secondary_font_size
            or self.config.text.secondary_font_size
            or self.config.text.get_secondary_font_size(self.config.dimensions)
        )

        # Main font priority: Excel > JSON config > hardcoded "Arial"
        main_font_spec = self.row_data.main_font or self.config.text.main_font or "Arial"

        # Secondary font priority is more complex:
        # 1. If Excel specifies secondary font, use it
        # 2. If Excel specifies main font but not secondary, use Excel main font at secondary size
        # 3. If Excel doesn't specify main font:
        #    - If Excel specifies secondary, use GUI main + Excel secondary
        #    - If Excel doesn't specify secondary, use GUI secondary (or GUI main if secondary not set)
        if self.row_data.secondary_font:
            # Excel has explicit secondary font
            secondary_font_spec = self.row_data.secondary_font
        elif self.row_data.main_font:
            # Excel has main font but not secondary - use Excel main for both
            secondary_font_spec = None  # load_font_pair will use main_font_spec
        else:
            # Excel has no main font - use GUI/config secondary (or main if not set)
            secondary_font_spec = self.config.text.secondary_font or None

        logger.debug(
            f"Loading fonts: main={main_font_spec} ({main_font_size}pt), "
            f"secondary={secondary_font_spec or 'same as main'} ({secondary_font_size}pt)"
        )

        self.main_font, self.secondary_font = self.font_loader.load_font_pair(
            main_font_spec,
            secondary_font_spec,
            main_font_size,
            secondary_font_size,
        )

        return self

    def calculate_layout(self) -> "LowerThirdBuilder":
        """Calculate text positions based on justification.

        Returns:
            Self for method chaining
        """
        if self.draw is None or self.main_font is None:
            raise ImageGenerationError("Must call create_canvas() and load_fonts() before calculate_layout()")

        # Get padding (with row override if specified)
        padding = self.row_data.padding if self.row_data.padding is not None else self.config.get_padding()

        # Calculate max width for text wrapping
        wrap_enabled = self.row_data.wrap_text or self.config.text.wrap_text
        wrap_padding = self.row_data.wrap_padding if self.row_data.wrap_padding is not None else self.config.text.wrap_padding

        self.max_width = None
        if wrap_enabled and wrap_padding:
            self.max_width = self.config.width - (2 * wrap_padding)

        # Measure text dimensions (with optional wrapping)
        main_width, main_height = self.text_renderer.measure_text(
            self.draw,
            self.row_data.main_text,
            self.main_font,
            self.config.text.letter_spacing,
            self.config.text.text_transform,
            max_width=self.max_width,
        )

        secondary_width, secondary_height = self.text_renderer.measure_text(
            self.draw,
            self.row_data.secondary_text,
            self.secondary_font,
            self.config.text.letter_spacing,
            self.config.text.text_transform,
            max_width=self.max_width,
        )

        # Get vertical spacing
        main_font_size = self.main_font.size if hasattr(self.main_font, 'size') else self.config.text.get_main_font_size(self.config.dimensions)
        vertical_spacing = self.config.text.get_vertical_spacing(main_font_size, self.config.dimensions)

        # Create dimensions object
        dimensions = TextDimensions(
            main_width=main_width,
            main_height=main_height,
            secondary_width=secondary_width,
            secondary_height=secondary_height,
            padding=padding,
            vertical_spacing=vertical_spacing,
        )

        # Get position strategy
        strategy = PositionStrategyFactory.get_strategy(self.row_data.justification)

        # Calculate positions
        bar_y = int(self.config.height * self.config.bar.y_position_ratio)
        bar_padding = self.config.dimensions.bar_padding

        self.main_x, self.main_y, self.secondary_x, self.secondary_y = strategy.calculate_position(
            dimensions,
            self.config.width,
            self.config.height,
            bar_y,
            bar_padding,
        )

        # Constrain positions to wrap_padding safe zone if wrapping is enabled
        if wrap_enabled and wrap_padding:
            # Ensure text doesn't start before the left wrap_padding boundary
            if self.main_x < wrap_padding:
                self.main_x = wrap_padding
            if self.secondary_x < wrap_padding:
                self.secondary_x = wrap_padding
            logger.debug(f"Applied wrap_padding constraints: min_x={wrap_padding}")

        # Apply position offsets (row override or config)
        offset_x = self.row_data.position_offset_x if self.row_data.position_offset_x != 0 else self.config.text.position_offset_x
        offset_y = self.row_data.position_offset_y if self.row_data.position_offset_y != 0 else self.config.text.position_offset_y

        if offset_x != 0 or offset_y != 0:
            self.main_x += offset_x
            self.main_y += offset_y
            self.secondary_x += offset_x
            self.secondary_y += offset_y
            logger.debug(f"Applied position offsets: x={offset_x}, y={offset_y}")

        logger.debug(f"Layout calculated: main=({self.main_x}, {self.main_y}), sec=({self.secondary_x}, {self.secondary_y})")

        return self

    def create_text_layer(self) -> "LowerThirdBuilder":
        """Create transparent layer for text.

        Returns:
            Self for method chaining
        """
        self.text_layer = Image.new("RGBA", (self.config.width, self.config.height), (0, 0, 0, 0))
        self.text_draw = ImageDraw.Draw(self.text_layer)

        return self

    def apply_shadow(self) -> "LowerThirdBuilder":
        """Apply shadow effect to text.

        Returns:
            Self for method chaining
        """
        if not self.config.text.shadow.enabled and not self.row_data.text_shadow:
            return self

        if self.image is None or self.text_draw is None:
            raise ImageGenerationError("Must call create_canvas() and create_text_layer() before apply_shadow()")

        # Prepare text positions for shadow
        positions = self.text_renderer.prepare_text_positions(
            self.text_draw,
            self.row_data.main_text,
            self.row_data.secondary_text,
            self.main_font,
            self.secondary_font,
            (self.main_x, self.main_y),
            (self.secondary_x, self.secondary_y),
            self.config.text.letter_spacing,
            self.config.text.text_transform,
            max_width=self.max_width,
        )

        # Override shadow color if specified in row
        shadow_config = self.config.text.shadow
        if self.row_data.shadow_color:
            shadow_config.color = self.row_data.shadow_color

        # Create and apply shadow
        shadow = ShadowEffect(shadow_config, self.color_parser)
        shadow_layer = shadow.create_shadow_layer((self.config.width, self.config.height), positions)

        # Composite shadow with main image
        if self.image.mode != "RGBA":
            self.image = self.image.convert("RGBA")
        self.image = Image.alpha_composite(self.image, shadow_layer)

        return self

    def apply_outline(self) -> "LowerThirdBuilder":
        """Apply outline effect to text.

        Returns:
            Self for method chaining
        """
        outline_config = self.config.text.outline

        # Override with row data if specified
        if self.row_data.text_outline:
            outline_config = OutlineEffect.from_string(self.row_data.text_outline)

        if not outline_config.enabled:
            return self

        if self.text_draw is None:
            raise ImageGenerationError("Must call create_text_layer() before apply_outline()")

        # Prepare text positions for outline
        positions = self.text_renderer.prepare_text_positions(
            self.text_draw,
            self.row_data.main_text,
            self.row_data.secondary_text,
            self.main_font,
            self.secondary_font,
            (self.main_x, self.main_y),
            (self.secondary_x, self.secondary_y),
            self.config.text.letter_spacing,
            self.config.text.text_transform,
            max_width=self.max_width,
        )

        # Apply outline
        outline = OutlineEffect(outline_config, self.color_parser)
        outline.draw_outline(self.text_draw, positions)

        return self

    def render_text(self) -> "LowerThirdBuilder":
        """Render the actual text.

        Returns:
            Self for method chaining
        """
        if self.text_draw is None:
            raise ImageGenerationError("Must call create_text_layer() before render_text()")

        logger.debug("Rendering text")

        # Draw main text
        self.text_renderer.draw_text(
            self.text_draw,
            (self.main_x, self.main_y),
            self.row_data.main_text,
            self.main_font,
            self.main_text_color,
            self.config.text.letter_spacing,
            self.config.text.text_transform,
            max_width=self.max_width,
        )

        # Draw secondary text
        self.text_renderer.draw_text(
            self.text_draw,
            (self.secondary_x, self.secondary_y),
            self.row_data.secondary_text,
            self.secondary_font,
            self.secondary_text_color,
            self.config.text.letter_spacing,
            self.config.text.text_transform,
            max_width=self.max_width,
        )

        return self

    def composite_layers(self) -> "LowerThirdBuilder":
        """Composite all layers together.

        Returns:
            Self for method chaining
        """
        if self.image is None or self.text_layer is None:
            raise ImageGenerationError("Must call create_canvas() and create_text_layer() before composite_layers()")

        logger.debug("Compositing layers")

        # Ensure both images are in RGBA mode
        if self.image.mode != "RGBA":
            self.image = self.image.convert("RGBA")

        self.image = Image.alpha_composite(self.image, self.text_layer)

        return self

    def build(self) -> Image.Image:
        """Return the final constructed image.

        Returns:
            Final PIL Image

        Raises:
            ImageGenerationError: If image not fully constructed
        """
        if self.image is None:
            raise ImageGenerationError("Image not constructed. Call construction methods first.")

        logger.info(f"Lower third built: {self.row_data.main_text}")
        return self.image
