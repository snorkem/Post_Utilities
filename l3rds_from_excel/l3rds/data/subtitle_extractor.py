"""Subtitle extractor for Lower Thirds Generator.

This module converts subtitle entries (STL/SRT) to RowData objects
suitable for image generation.
"""

import re
from typing import Union

from l3rds.data.models import RowData
from l3rds.data.stl_parser import STLSubtitle
from l3rds.data.srt_parser import SRTSubtitle
from l3rds.config.models import DefaultConfig
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)

# Type alias for subtitle objects
SubtitleEntry = Union[STLSubtitle, SRTSubtitle]


class SubtitleRowExtractor:
    """Extract RowData from subtitle entries for image generation."""

    FILENAME_FORMAT_TIMECODE = "timecode"
    FILENAME_FORMAT_TEXT = "text"
    FILENAME_FORMAT_COMBINED = "combined"

    def __init__(
        self,
        config: DefaultConfig,
        filename_format: str = "timecode"
    ):
        """Initialize the subtitle extractor.

        Args:
            config: Default configuration for generating images
            filename_format: How to generate filenames
                - "timecode": {number}_{tc_in}_{tc_out}
                - "text": {number}_{sanitized_text}
                - "combined": {number}_{tc_in}_{sanitized_text}
        """
        self.config = config
        self.filename_format = filename_format.lower()

        if self.filename_format not in [self.FILENAME_FORMAT_TIMECODE,
                                       self.FILENAME_FORMAT_TEXT,
                                       self.FILENAME_FORMAT_COMBINED]:
            logger.warning(
                f"Unknown filename format '{filename_format}', defaulting to 'timecode'"
            )
            self.filename_format = self.FILENAME_FORMAT_TIMECODE

    def extract_from_subtitle(
        self,
        subtitle: SubtitleEntry,
        index: int
    ) -> RowData:
        """Convert a subtitle entry to RowData for image generation.

        Args:
            subtitle: STLSubtitle or SRTSubtitle object
            index: Subtitle index (0-based, for filename generation)

        Returns:
            RowData object ready for image generation
        """
        # Generate filename based on user preference
        filename = self.generate_subtitle_filename(subtitle, index)

        # Create RowData
        # Per user requirements: secondary_text should be empty (no timecode on image)
        row_data = RowData(
            main_text=subtitle.text,
            secondary_text="",  # Empty per user requirement
            justification=self.config.default_justification,
            main_font=None,  # Will use config default
            file_name=filename,
        )

        logger.debug(f"Extracted subtitle {index + 1}: {filename}")
        return row_data

    def generate_subtitle_filename(
        self,
        subtitle: SubtitleEntry,
        index: int
    ) -> str:
        """Generate filename for subtitle image.

        Args:
            subtitle: Subtitle entry
            index: Subtitle index (0-based)

        Returns:
            Filename without extension

        Examples:
            Timecode format: "0001_01-00-05-12_01-00-08-00"
            Text format: "0001_Hello_World"
            Combined format: "0001_01-00-05-12_Hello_World"
        """
        # Format subtitle number with leading zeros
        number = f"{index + 1:04d}"

        # Get sanitized timecodes (replace colons with dashes for filesystem safety)
        tc_in = self._format_timecode(subtitle.time_in)
        tc_out = self._format_timecode(subtitle.time_out)

        # Get sanitized text
        sanitized_text = self._sanitize_text_for_filename(subtitle.text)

        # Generate filename based on format
        if self.filename_format == self.FILENAME_FORMAT_TIMECODE:
            return f"{number}_{tc_in}_{tc_out}"
        elif self.filename_format == self.FILENAME_FORMAT_TEXT:
            return f"{number}_{sanitized_text}"
        elif self.filename_format == self.FILENAME_FORMAT_COMBINED:
            return f"{number}_{tc_in}_{sanitized_text}"
        else:
            # Fallback (shouldn't reach here due to __init__ validation)
            return f"{number}_{tc_in}_{tc_out}"

    @staticmethod
    def _format_timecode(timecode) -> str:
        """Format timecode object to filesystem-safe string.

        Args:
            timecode: Timecode object

        Returns:
            Formatted string like "01-00-05-12" (HH-MM-SS-FF)
        """
        # Timecode.__str__() returns "HH:MM:SS:FF"
        tc_str = str(timecode)

        # Replace colons with dashes for filesystem compatibility
        return tc_str.replace(":", "-")

    @staticmethod
    def _sanitize_text_for_filename(text: str, max_length: int = 30) -> str:
        """Sanitize subtitle text for use in filename.

        Args:
            text: Original subtitle text
            max_length: Maximum length of sanitized text

        Returns:
            Sanitized text suitable for filename

        Examples:
            "Hello, World!" -> "Hello_World"
            "Line 1\\nLine 2" -> "Line_1_Line_2"
        """
        # Replace newlines and multiple spaces with single space
        text = re.sub(r'[\n\r]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        # Replace spaces with underscores
        text = text.replace(' ', '_')

        # Remove non-alphanumeric characters except underscore and hyphen
        text = re.sub(r'[^a-zA-Z0-9_-]', '', text)

        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length]

        # Ensure we have something (fallback if text was all special chars)
        if not text:
            text = "subtitle"

        return text
