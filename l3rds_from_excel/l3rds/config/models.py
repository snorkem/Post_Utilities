"""Configuration data models for lower thirds generation.

This module defines type-safe configuration dataclasses that encapsulate
all settings for lower third image generation. These models support:
- JSON serialization/deserialization
- Validation
- Default values
- Type safety
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from l3rds.utils.constants import (
    DEFAULT_IMAGE_WIDTH,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_BIT_DEPTH,
    DEFAULT_FORMAT,
    DEFAULT_BG_COLOR,
    DEFAULT_TEXT_COLOR,
    DEFAULT_BAR_COLOR,
    DEFAULT_SHADOW_OFFSET_X,
    DEFAULT_SHADOW_OFFSET_Y,
    DEFAULT_SHADOW_BLUR,
    DEFAULT_SHADOW_OPACITY,
    DEFAULT_SHADOW_COLOR,
    Dimensions,
)

from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ShadowConfig:
    """Configuration for text shadow effects.

    Attributes:
        enabled: Whether shadow is enabled
        offset_x: Horizontal offset in pixels
        offset_y: Vertical offset in pixels
        blur: Blur amount (1-100 scale)
        color: Shadow color (name, hex, or RGB string)
        opacity: Shadow opacity (0-255)

    Example:
        >>> shadow = ShadowConfig(enabled=True, blur=30, opacity=180)
    """

    enabled: bool = False
    offset_x: int = DEFAULT_SHADOW_OFFSET_X
    offset_y: int = DEFAULT_SHADOW_OFFSET_Y
    blur: int = DEFAULT_SHADOW_BLUR
    color: str = DEFAULT_SHADOW_COLOR
    opacity: int = DEFAULT_SHADOW_OPACITY

    def __post_init__(self) -> None:
        """Validate shadow configuration."""
        if not 1 <= self.blur <= 100:
            raise ValueError(f"Shadow blur must be between 1 and 100, got {self.blur}")
        if not 0 <= self.opacity <= 255:
            raise ValueError(f"Shadow opacity must be between 0 and 255, got {self.opacity}")


@dataclass
class OutlineConfig:
    """Configuration for text outline effects.

    Attributes:
        width: Outline width in pixels (0 = disabled)
        color: Outline color
        opacity: Outline opacity (0-255)

    Example:
        >>> outline = OutlineConfig(width=2, color="black", opacity=255)
    """

    width: int = 0
    color: str = "black"
    opacity: int = 255

    def __post_init__(self) -> None:
        """Validate outline configuration."""
        if self.width < 0:
            raise ValueError(f"Outline width cannot be negative, got {self.width}")
        if not 0 <= self.opacity <= 255:
            raise ValueError(f"Outline opacity must be between 0 and 255, got {self.opacity}")

    @property
    def enabled(self) -> bool:
        """Check if outline is enabled."""
        return self.width > 0

    @classmethod
    def from_string(cls, outline_str: str | None) -> "OutlineConfig":
        """Parse outline from string like '2,black,128'.

        Args:
            outline_str: Outline specification string

        Returns:
            OutlineConfig instance

        Example:
            >>> config = OutlineConfig.from_string("2,black,128")
            >>> config.width
            2
        """
        if not outline_str:
            return cls()

        parts = outline_str.split(",")
        config = cls()

        if len(parts) >= 1:
            try:
                config.width = int(parts[0].strip())
            except ValueError:
                logger.warning(f"Invalid outline width: {parts[0]}")

        if len(parts) >= 2:
            config.color = parts[1].strip()

        if len(parts) >= 3:
            try:
                config.opacity = int(parts[2].strip())
            except ValueError:
                logger.warning(f"Invalid outline opacity: {parts[2]}")

        return config


@dataclass
class TextConfig:
    """Configuration for text rendering.

    Attributes:
        main_font: Main font name or path
        secondary_font: Secondary font name or path (None = use main font)
        main_font_size: Main font size in points (None = auto-calculate)
        secondary_font_size: Secondary font size in points (None = auto-calculate)
        text_color: Main text color
        secondary_text_color: Secondary text color (None = use text_color)
        letter_spacing: Character spacing in pixels
        vertical_spacing: Space between main and secondary text (None = auto-calculate)
        text_transform: Text transformation (none, upper, lower, title)
        shadow: Shadow configuration
        outline: Outline configuration
        wrap_text: Enable text wrapping
        wrap_padding: Distance from image border where text wraps in pixels
        position_offset_x: Horizontal position offset in pixels (positive=right, negative=left)
        position_offset_y: Vertical position offset in pixels (positive=down, negative=up)

    Example:
        >>> text = TextConfig(
        ...     main_font="Arial",
        ...     text_color="white",
        ...     shadow=ShadowConfig(enabled=True)
        ... )
    """

    main_font: str = "Arial"
    secondary_font: str | None = None
    main_font_size: int | None = None
    secondary_font_size: int | None = None
    text_color: str = "white"
    secondary_text_color: str | None = None
    letter_spacing: int = 0
    vertical_spacing: int | None = None
    text_transform: str = "none"
    shadow: ShadowConfig = field(default_factory=ShadowConfig)
    outline: OutlineConfig = field(default_factory=OutlineConfig)
    wrap_text: bool = False
    wrap_padding: int | None = None
    position_offset_x: int = 0
    position_offset_y: int = 0

    def __post_init__(self) -> None:
        """Validate text configuration."""
        valid_transforms = ("none", "upper", "lower", "title", "capitalize", "swapcase")
        if self.text_transform not in valid_transforms:
            raise ValueError(
                f"Invalid text_transform '{self.text_transform}', "
                f"must be one of {valid_transforms}"
            )

        # Validate text wrapping
        if self.wrap_text and self.wrap_padding is None:
            raise ValueError("wrap_padding is required when wrap_text is enabled")
        if self.wrap_padding is not None and self.wrap_padding < 1:
            raise ValueError(f"wrap_padding must be at least 1, got {self.wrap_padding}")

    def get_main_font_size(self, dimensions: Dimensions) -> int:
        """Get main font size, using default if not specified.

        Args:
            dimensions: Canvas dimensions for calculating default

        Returns:
            Font size in points
        """
        return self.main_font_size or dimensions.main_font_size

    def get_secondary_font_size(self, dimensions: Dimensions) -> int:
        """Get secondary font size, using default if not specified.

        Args:
            dimensions: Canvas dimensions for calculating default

        Returns:
            Font size in points
        """
        return self.secondary_font_size or dimensions.secondary_font_size

    def get_vertical_spacing(self, main_font_size: int, dimensions: Dimensions) -> int:
        """Get vertical spacing, using default if not specified.

        Args:
            main_font_size: Main font size for calculating default
            dimensions: Canvas dimensions

        Returns:
            Vertical spacing in pixels
        """
        return self.vertical_spacing or dimensions.vertical_spacing(main_font_size)


@dataclass
class BarConfig:
    """Configuration for lower third bar.

    Attributes:
        color: Bar color (with optional alpha)
        height: Bar height in pixels (None = auto-calculate)
        opacity: Bar opacity override (None = use color's alpha)
        y_position_ratio: Vertical position as ratio of canvas height (0.0-1.0)

    Example:
        >>> bar = BarConfig(color="blue", opacity=150, y_position_ratio=0.75)
    """

    color: str = "black,0"
    height: int | None = None
    opacity: int | None = None
    y_position_ratio: float = 0.75

    def __post_init__(self) -> None:
        """Validate bar configuration."""
        if self.opacity is not None and not 0 <= self.opacity <= 255:
            raise ValueError(f"Bar opacity must be between 0 and 255, got {self.opacity}")
        if not 0.0 <= self.y_position_ratio <= 1.0:
            raise ValueError(
                f"Bar y_position_ratio must be between 0.0 and 1.0, "
                f"got {self.y_position_ratio}"
            )

    def get_height(self, dimensions: Dimensions) -> int:
        """Get bar height, using default if not specified.

        Args:
            dimensions: Canvas dimensions for calculating default

        Returns:
            Bar height in pixels
        """
        return self.height or dimensions.bar_height


@dataclass
class OutputConfig:
    """Configuration for output files.

    Attributes:
        format: Output format (png, jpg, tiff)
        bit_depth: Bit depth for TIFF (8 or 16)
        transparent: Use transparent background
        skip_existing: Skip generation if file already exists

    Example:
        >>> output = OutputConfig(format="png", transparent=True)
    """

    format: str = DEFAULT_FORMAT
    bit_depth: int = DEFAULT_BIT_DEPTH
    transparent: bool = False
    skip_existing: bool = False

    def __post_init__(self) -> None:
        """Validate output configuration."""
        valid_formats = ("png", "jpg", "jpeg", "tiff", "tif")
        if self.format.lower() not in valid_formats:
            raise ValueError(
                f"Invalid format '{self.format}', must be one of {valid_formats}"
            )

        valid_bit_depths = (8, 16)
        if self.bit_depth not in valid_bit_depths:
            raise ValueError(
                f"Invalid bit_depth {self.bit_depth}, must be one of {valid_bit_depths}"
            )


@dataclass
class DefaultConfig:
    """Default configuration for all lower thirds.

    This is the main configuration class that contains all settings for
    generating lower third images.

    Attributes:
        width: Image width in pixels
        height: Image height in pixels
        bg_color: Background color
        padding: Padding from edges in pixels (None = auto-calculate)
        text: Text configuration
        bar: Bar configuration
        output: Output configuration
        debug: Enable debug output
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path

    Example:
        >>> config = DefaultConfig(
        ...     width=1920,
        ...     height=1080,
        ...     text=TextConfig(main_font="Arial"),
        ...     output=OutputConfig(format="png")
        ... )
    """

    width: int = DEFAULT_IMAGE_WIDTH
    height: int = DEFAULT_IMAGE_HEIGHT
    bg_color: str = "black"
    padding: int | None = None
    default_justification: str = "lower left"  # Default text position when Excel doesn't specify
    text: TextConfig = field(default_factory=TextConfig)
    bar: BarConfig = field(default_factory=BarConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    debug: bool = False
    log_level: str = "INFO"
    log_file: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.width <= 0:
            raise ValueError(f"Width must be positive, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"Height must be positive, got {self.height}")

    @property
    def dimensions(self) -> Dimensions:
        """Get Dimensions helper for this configuration.

        Returns:
            Dimensions instance
        """
        return Dimensions(self.width, self.height)

    def get_padding(self) -> int:
        """Get padding, using default if not specified.

        Returns:
            Padding in pixels
        """
        return self.padding or self.dimensions.padding

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation

        Example:
            >>> config = DefaultConfig()
            >>> data = config.to_dict()
        """
        return asdict(self)

    def to_json(self, filepath: str | Path) -> None:
        """Save configuration to JSON file.

        Args:
            filepath: Path to JSON file

        Example:
            >>> config = DefaultConfig()
            >>> config.to_json("settings.json")
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved configuration to {path}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DefaultConfig":
        """Create configuration from dictionary.

        Args:
            data: Dictionary with configuration data

        Returns:
            DefaultConfig instance

        Example:
            >>> data = {"width": 1920, "height": 1080}
            >>> config = DefaultConfig.from_dict(data)
        """
        # Handle nested dataclasses
        if "text" in data and isinstance(data["text"], dict):
            if "shadow" in data["text"] and isinstance(data["text"]["shadow"], dict):
                data["text"]["shadow"] = ShadowConfig(**data["text"]["shadow"])
            if "outline" in data["text"] and isinstance(data["text"]["outline"], dict):
                data["text"]["outline"] = OutlineConfig(**data["text"]["outline"])
            data["text"] = TextConfig(**data["text"])

        if "bar" in data and isinstance(data["bar"], dict):
            data["bar"] = BarConfig(**data["bar"])

        if "output" in data and isinstance(data["output"], dict):
            data["output"] = OutputConfig(**data["output"])

        return cls(**data)

    @classmethod
    def from_json(cls, filepath: str | Path) -> "DefaultConfig":
        """Load configuration from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            DefaultConfig instance

        Example:
            >>> config = DefaultConfig.from_json("settings.json")
        """
        path = Path(filepath)

        with open(path, "r") as f:
            data = json.load(f)

        logger.info(f"Loaded configuration from {path}")
        config = cls.from_dict(data)

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

        return config
