"""Configuration validation utilities.

This module provides validation functions for configuration objects,
ensuring all values are within acceptable ranges and combinations are valid.
"""

from pathlib import Path

from l3rds.config.models import DefaultConfig
from l3rds.utils.constants import (
    MIN_IMAGE_WIDTH,
    MAX_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    MAX_IMAGE_HEIGHT,
)
from l3rds.utils.exceptions import ConfigurationError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """Validator for configuration objects.

    This class provides static methods for validating different aspects
    of configuration, ensuring values are sensible and compatible.

    Example:
        >>> config = DefaultConfig()
        >>> ConfigValidator.validate(config)
        >>> # Raises ConfigurationError if invalid
    """

    @classmethod
    def validate(cls, config: DefaultConfig, input_file: str | None = None) -> None:
        """Validate entire configuration.

        Args:
            config: Configuration to validate
            input_file: Optional input file path to check

        Raises:
            ConfigurationError: If configuration is invalid

        Example:
            >>> config = DefaultConfig(width=100000)  # Too wide
            >>> ConfigValidator.validate(config)  # Raises exception
        """
        cls.validate_dimensions(config)
        cls.validate_text_config(config)
        cls.validate_bar_config(config)
        cls.validate_output_config(config)

        if input_file:
            cls.validate_input_file(input_file)

    @classmethod
    def validate_dimensions(cls, config: DefaultConfig) -> None:
        """Validate image dimensions.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If dimensions are invalid
        """
        if config.width < MIN_IMAGE_WIDTH:
            raise ConfigurationError(
                f"Image width too small (minimum: {MIN_IMAGE_WIDTH}px)",
                config_key="width",
                invalid_value=config.width,
            )

        if config.width > MAX_IMAGE_WIDTH:
            raise ConfigurationError(
                f"Image width too large (maximum: {MAX_IMAGE_WIDTH}px)",
                config_key="width",
                invalid_value=config.width,
            )

        if config.height < MIN_IMAGE_HEIGHT:
            raise ConfigurationError(
                f"Image height too small (minimum: {MIN_IMAGE_HEIGHT}px)",
                config_key="height",
                invalid_value=config.height,
            )

        if config.height > MAX_IMAGE_HEIGHT:
            raise ConfigurationError(
                f"Image height too large (maximum: {MAX_IMAGE_HEIGHT}px)",
                config_key="height",
                invalid_value=config.height,
            )

        logger.debug(f"Dimensions validated: {config.width}x{config.height}")

    @classmethod
    def validate_text_config(cls, config: DefaultConfig) -> None:
        """Validate text configuration.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If text configuration is invalid
        """
        # Validate font sizes if specified
        if config.text.main_font_size is not None:
            if config.text.main_font_size <= 0:
                raise ConfigurationError(
                    "Main font size must be positive",
                    config_key="text.main_font_size",
                    invalid_value=config.text.main_font_size,
                )

            if config.text.main_font_size > 500:
                logger.warning(
                    f"Main font size ({config.text.main_font_size}pt) is very large. "
                    "This may cause layout issues."
                )

        if config.text.secondary_font_size is not None:
            if config.text.secondary_font_size <= 0:
                raise ConfigurationError(
                    "Secondary font size must be positive",
                    config_key="text.secondary_font_size",
                    invalid_value=config.text.secondary_font_size,
                )

        # Validate letter spacing
        if abs(config.text.letter_spacing) > 100:
            logger.warning(
                f"Letter spacing ({config.text.letter_spacing}px) is very large. "
                "This may cause layout issues."
            )

        # Shadow validation is handled in ShadowConfig.__post_init__
        # Outline validation is handled in OutlineConfig.__post_init__

        logger.debug("Text configuration validated")

    @classmethod
    def validate_bar_config(cls, config: DefaultConfig) -> None:
        """Validate bar configuration.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If bar configuration is invalid
        """
        if config.bar.height is not None:
            if config.bar.height < 0:
                raise ConfigurationError(
                    "Bar height cannot be negative",
                    config_key="bar.height",
                    invalid_value=config.bar.height,
                )

            if config.bar.height > config.height:
                raise ConfigurationError(
                    f"Bar height ({config.bar.height}px) exceeds image height ({config.height}px)",
                    config_key="bar.height",
                    invalid_value=config.bar.height,
                )

        logger.debug("Bar configuration validated")

    @classmethod
    def validate_output_config(cls, config: DefaultConfig) -> None:
        """Validate output configuration.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If output configuration is invalid
        """
        # Warn about transparency with JPEG
        if config.output.transparent and config.output.format.lower() in ("jpg", "jpeg"):
            logger.warning(
                "JPEG format does not support transparency. "
                "Transparency will be ignored. Consider using PNG or TIFF."
            )

        # Warn about 16-bit with non-TIFF
        if config.output.bit_depth == 16 and config.output.format.lower() not in (
            "tiff",
            "tif",
        ):
            logger.warning(
                f"16-bit depth only supported for TIFF format. "
                f"Using 8-bit for {config.output.format.upper()}."
            )

        logger.debug(f"Output configuration validated: {config.output.format}")

    @classmethod
    def validate_input_file(cls, input_file: str) -> None:
        """Validate input file exists and is readable.

        Args:
            input_file: Path to input file

        Raises:
            ConfigurationError: If input file is invalid
        """
        path = Path(input_file)

        if not path.exists():
            raise ConfigurationError(
                f"Input file does not exist: {input_file}",
                config_key="input_file",
                invalid_value=input_file,
            )

        if not path.is_file():
            raise ConfigurationError(
                f"Input path is not a file: {input_file}",
                config_key="input_file",
                invalid_value=input_file,
            )

        # Check file extension
        valid_extensions = (".csv", ".xlsx", ".xls")
        if path.suffix.lower() not in valid_extensions:
            logger.warning(
                f"Input file has unusual extension: {path.suffix}. "
                f"Expected one of {valid_extensions}"
            )

        logger.debug(f"Input file validated: {input_file}")

    @classmethod
    def validate_output_dir(cls, output_dir: str, create: bool = True) -> None:
        """Validate output directory exists or can be created.

        Args:
            output_dir: Path to output directory
            create: If True, create directory if it doesn't exist

        Raises:
            ConfigurationError: If output directory is invalid
        """
        path = Path(output_dir)

        if path.exists() and not path.is_dir():
            raise ConfigurationError(
                f"Output path exists but is not a directory: {output_dir}",
                config_key="output_dir",
                invalid_value=output_dir,
            )

        if not path.exists():
            if create:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created output directory: {output_dir}")
                except Exception as e:
                    raise ConfigurationError(
                        f"Cannot create output directory: {e}",
                        config_key="output_dir",
                        invalid_value=output_dir,
                    )
            else:
                raise ConfigurationError(
                    f"Output directory does not exist: {output_dir}",
                    config_key="output_dir",
                    invalid_value=output_dir,
                )

        logger.debug(f"Output directory validated: {output_dir}")
