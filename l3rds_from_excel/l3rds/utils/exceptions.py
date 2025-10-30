"""Custom exception classes for the l3rds package.

This module defines a hierarchy of exceptions for different error conditions,
making it easier to handle and report errors with appropriate context.
"""


class L3rdsException(Exception):
    """Base exception for all l3rds-related errors.

    All custom exceptions in the l3rds package inherit from this base class,
    making it easy to catch all l3rds-specific errors.
    """

    pass


class InvalidExcelDataError(L3rdsException):
    """Raised when Excel/CSV data is malformed or invalid.

    This exception is raised when:
    - Required columns are missing
    - Data types are incorrect
    - Values are out of valid range
    - File format is unsupported

    Attributes:
        row_index: Optional row number where error occurred
        column_name: Optional column name where error occurred
        message: Human-readable error message
    """

    def __init__(
        self,
        message: str,
        row_index: int | None = None,
        column_name: str | None = None,
    ) -> None:
        """Initialize with error details.

        Args:
            message: Description of the error
            row_index: Row number where error occurred (0-indexed)
            column_name: Column name where error occurred
        """
        self.row_index = row_index
        self.column_name = column_name

        # Build detailed error message
        error_parts = [message]
        if row_index is not None:
            error_parts.append(f"at row {row_index + 1}")
        if column_name:
            error_parts.append(f"in column '{column_name}'")

        super().__init__(" ".join(error_parts))


class FontLoadError(L3rdsException):
    """Raised when a font cannot be loaded.

    This exception is raised when:
    - Font file doesn't exist
    - Font file is corrupt
    - Font format is unsupported
    - System has no available fonts

    Attributes:
        font_spec: Font specification that failed to load
        attempted_paths: Paths that were attempted (if any)
    """

    def __init__(
        self,
        message: str,
        font_spec: str | None = None,
        attempted_paths: list[str] | None = None,
    ) -> None:
        """Initialize with font loading error details.

        Args:
            message: Description of the error
            font_spec: Font name or path that was requested
            attempted_paths: List of paths that were tried
        """
        self.font_spec = font_spec
        self.attempted_paths = attempted_paths or []

        error_parts = [message]
        if font_spec:
            error_parts.append(f"for font '{font_spec}'")
        if attempted_paths:
            paths_str = ", ".join(attempted_paths[:3])  # Show first 3
            if len(attempted_paths) > 3:
                paths_str += f", and {len(attempted_paths) - 3} more"
            error_parts.append(f"(tried: {paths_str})")

        super().__init__(" ".join(error_parts))


class ColorParseError(L3rdsException):
    """Raised when a color specification cannot be parsed.

    This exception is raised when:
    - Color name is not recognized
    - Hex code is malformed
    - RGB values are out of range
    - Format is unrecognized

    Attributes:
        color_spec: Color specification that failed to parse
        expected_format: Expected format (optional)
    """

    def __init__(
        self,
        message: str,
        color_spec: str | None = None,
        expected_format: str | None = None,
    ) -> None:
        """Initialize with color parsing error details.

        Args:
            message: Description of the error
            color_spec: Color specification that was provided
            expected_format: Description of expected format
        """
        self.color_spec = color_spec
        self.expected_format = expected_format

        error_parts = [message]
        if color_spec:
            error_parts.append(f"for color '{color_spec}'")
        if expected_format:
            error_parts.append(f"(expected format: {expected_format})")

        super().__init__(" ".join(error_parts))


class ImageGenerationError(L3rdsException):
    """Raised when image generation fails.

    This exception is raised when:
    - Image rendering fails
    - Text drawing fails
    - Layer compositing fails
    - Effect application fails

    Attributes:
        stage: Stage of generation where error occurred
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize with image generation error details.

        Args:
            message: Description of the error
            stage: Stage where error occurred (e.g., "text rendering", "shadow effect")
            details: Additional technical details
        """
        self.stage = stage
        self.details = details

        error_parts = [message]
        if stage:
            error_parts.append(f"during {stage}")
        if details:
            error_parts.append(f"({details})")

        super().__init__(" ".join(error_parts))


class ImageSaveError(L3rdsException):
    """Raised when saving an image fails.

    This exception is raised when:
    - Output directory doesn't exist
    - No write permission
    - Disk is full
    - Format conversion fails

    Attributes:
        output_path: Path where save was attempted
        format: Image format that was requested
    """

    def __init__(
        self,
        message: str,
        output_path: str | None = None,
        format: str | None = None,
    ) -> None:
        """Initialize with image save error details.

        Args:
            message: Description of the error
            output_path: Path where save was attempted
            format: Image format (png, jpg, tiff)
        """
        self.output_path = output_path
        self.format = format

        error_parts = [message]
        if output_path:
            error_parts.append(f"at path '{output_path}'")
        if format:
            error_parts.append(f"(format: {format})")

        super().__init__(" ".join(error_parts))


class ConfigurationError(L3rdsException):
    """Raised when configuration is invalid.

    This exception is raised when:
    - Config file is malformed
    - Required settings are missing
    - Values are out of valid range
    - Conflicting settings detected

    Attributes:
        config_key: Configuration key that has an issue
        invalid_value: The invalid value (if applicable)
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        invalid_value: object = None,
    ) -> None:
        """Initialize with configuration error details.

        Args:
            message: Description of the error
            config_key: Configuration key with issue
            invalid_value: The value that was invalid
        """
        self.config_key = config_key
        self.invalid_value = invalid_value

        error_parts = [message]
        if config_key:
            error_parts.append(f"for setting '{config_key}'")
        if invalid_value is not None:
            error_parts.append(f"(value: {invalid_value!r})")

        super().__init__(" ".join(error_parts))
