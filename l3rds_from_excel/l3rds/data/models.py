"""Data models for extracted Excel row data.

This module defines dataclasses for storing extracted and validated
data from Excel/CSV rows.
"""

from dataclasses import dataclass


@dataclass
class RowData:
    """Extracted and validated data from an Excel row.

    This dataclass holds all the data extracted from a single row of
    an Excel or CSV file, including both required and optional fields.

    Attributes:
        main_text: Primary text to display
        secondary_text: Secondary text to display
        justification: Text position (e.g., "lower left", "center")
        main_font: Main font name or path (optional, falls back to config/GUI)
        secondary_font: Secondary font name or path (optional)
        file_name: Custom output filename (optional)
        main_font_size: Custom main font size (optional)
        secondary_font_size: Custom secondary font size (optional)
        padding: Custom padding value (optional)
        wrap_text: Enable text wrapping (optional)
        wrap_padding: Distance from image border where text wraps (optional)
        position_offset_x: Horizontal position offset in pixels (optional)
        position_offset_y: Vertical position offset in pixels (optional)
        main_color: Main text color (optional)
        secondary_color: Secondary text color (optional)
        bg_color: Background color (optional)
        bar_color: Bar color (optional)
        text_outline: Text outline specification (optional)
        text_shadow: Whether shadow is enabled
        shadow_color: Shadow color (optional)

    Example:
        >>> row = RowData(
        ...     main_text="John Doe",
        ...     secondary_text="Director",
        ...     justification="lower left",
        ...     main_font="Arial"
        ... )
    """

    # Required fields
    main_text: str
    secondary_text: str
    justification: str
    main_font: str | None = None

    # Optional fields
    secondary_font: str | None = None
    file_name: str | None = None
    main_font_size: int | None = None
    secondary_font_size: int | None = None
    padding: int | None = None

    # Text wrapping overrides
    wrap_text: bool = False
    wrap_padding: int | None = None

    # Position offset overrides
    position_offset_x: int = 0
    position_offset_y: int = 0

    # Optional color overrides
    main_color: str | None = None
    secondary_color: str | None = None
    bg_color: str | None = None
    bar_color: str | None = None

    # Optional effect overrides
    text_outline: str | None = None
    text_shadow: bool = False
    shadow_color: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize data."""
        # Strip whitespace from text fields
        self.main_text = self.main_text.strip()
        self.secondary_text = self.secondary_text.strip()

        # Validate that at least one text field is provided
        if not self.main_text and not self.secondary_text:
            raise ValueError(
                "At least one of main_text or secondary_text must be provided"
            )

        # Normalize justification to lowercase
        self.justification = self.justification.lower().strip()

    @property
    def has_color_overrides(self) -> bool:
        """Check if row has any color overrides.

        Returns:
            True if any color field is specified
        """
        return any(
            [
                self.main_color is not None,
                self.secondary_color is not None,
                self.bg_color is not None,
                self.bar_color is not None,
            ]
        )

    @property
    def has_font_size_overrides(self) -> bool:
        """Check if row has font size overrides.

        Returns:
            True if any font size field is specified
        """
        return self.main_font_size is not None or self.secondary_font_size is not None

    @property
    def has_effect_overrides(self) -> bool:
        """Check if row has effect overrides.

        Returns:
            True if any effect field is specified
        """
        return self.text_outline is not None or self.text_shadow

    def get_output_filename(self) -> str:
        """Get the output filename, using file_name, main_text, or secondary_text.

        Returns:
            Filename to use for output (without extension)

        Example:
            >>> row = RowData(main_text="John Doe", ..., file_name="john")
            >>> row.get_output_filename()
            'john'
        """
        if self.file_name:
            return self._sanitize_filename(self.file_name)
        elif self.main_text:
            return self._sanitize_filename(self.main_text)
        else:
            # Fall back to secondary_text if main_text is empty
            return self._sanitize_filename(self.secondary_text)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename by removing invalid characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename

        Example:
            >>> RowData._sanitize_filename("John/Doe")
            'John_Doe'
        """
        # Replace path separators
        safe = filename.replace("/", "_").replace("\\", "_")

        # Keep only alphanumeric, underscore, hyphen, and period
        safe = "".join(char for char in safe if char.isalnum() or char in "_-.")

        return safe
