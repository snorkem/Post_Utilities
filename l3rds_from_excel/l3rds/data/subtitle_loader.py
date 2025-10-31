"""Subtitle file loader for Lower Thirds Generator.

This module provides a unified interface for loading both STL and SRT subtitle files,
converting them to a format suitable for image generation.
"""

from pathlib import Path
from typing import Tuple, List, Union

from l3rds.data.stl_parser import parse_stl_file, STLSubtitle, detect_stl_fps
from l3rds.data.srt_parser import parse_srt_file, SRTSubtitle
from l3rds.utils.logger import get_logger
from l3rds.utils.exceptions import L3rdsException

logger = get_logger(__name__)

# Type alias for subtitle objects
SubtitleEntry = Union[STLSubtitle, SRTSubtitle]


class SubtitleLoader:
    """Load and parse subtitle files (STL or SRT format)."""

    SUPPORTED_EXTENSIONS = {'.stl', '.srt'}

    def __init__(self):
        """Initialize the subtitle loader."""
        pass

    def load(self, file_path: str | Path, fps: float | None = None) -> Tuple[List[SubtitleEntry], float]:
        """Load subtitles from STL or SRT file.

        Args:
            file_path: Path to subtitle file (.stl or .srt)
            fps: Frame rate for subtitle timecodes (optional)
                 - For STL: Auto-detected if not provided
                 - For SRT: Defaults to 30 if not provided

        Returns:
            Tuple of (subtitle_list, effective_fps)
            - subtitle_list: List of STLSubtitle or SRTSubtitle objects
            - effective_fps: The frame rate used for parsing

        Raises:
            L3rdsException: If file format is unsupported or parsing fails
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        # Detect format from extension
        extension = file_path.suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise L3rdsException(
                f"Unsupported subtitle format: {extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        # Parse based on format
        try:
            if extension == '.stl':
                return self._load_stl(file_path, fps)
            elif extension == '.srt':
                return self._load_srt(file_path, fps)
        except FileNotFoundError:
            raise
        except Exception as e:
            raise L3rdsException(f"Failed to parse {extension.upper()} file: {e}") from e

    def _load_stl(self, file_path: Path, fps: float | None) -> Tuple[List[STLSubtitle], float]:
        """Load STL subtitle file.

        Args:
            file_path: Path to STL file
            fps: Optional FPS override (auto-detect if None)

        Returns:
            Tuple of (subtitles_list, effective_fps)

        Raises:
            ValueError: If FPS cannot be determined
        """
        logger.info(f"Loading STL file: {file_path}")

        # If FPS not provided, try to detect it
        if fps is None:
            detected_fps = detect_stl_fps(file_path)
            if detected_fps is not None:
                logger.info(f"Auto-detected FPS: {detected_fps}")
                fps = detected_fps
            else:
                raise ValueError(
                    "Could not auto-detect FPS from STL file. "
                    "Please specify FPS using --subtitle-fps argument or GUI control."
                )
        else:
            logger.info(f"Using user-specified FPS: {fps}")

        # Parse the STL file
        subtitles, effective_fps = parse_stl_file(file_path, fps)

        logger.info(f"Loaded {len(subtitles)} subtitles from STL file at {effective_fps} fps")
        return subtitles, effective_fps

    def _load_srt(self, file_path: Path, fps: float | None) -> Tuple[List[SRTSubtitle], float]:
        """Load SRT subtitle file.

        Args:
            file_path: Path to SRT file
            fps: Frame rate for timecode conversion (defaults to 30)

        Returns:
            Tuple of (subtitles_list, effective_fps)
        """
        logger.info(f"Loading SRT file: {file_path}")

        # SRT uses milliseconds, needs FPS for frame-based timecode conversion
        if fps is None:
            fps = 23.976  # Default FPS for SRT
            logger.info(f"Using default FPS for SRT: {fps}")
        else:
            logger.info(f"Using user-specified FPS: {fps}")

        # Parse the SRT file
        subtitles, effective_fps = parse_srt_file(file_path, fps)

        logger.info(f"Loaded {len(subtitles)} subtitles from SRT file at {effective_fps} fps")
        return subtitles, effective_fps

    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported subtitle formats.

        Returns:
            List of supported file extensions (with dots)
        """
        return list(SubtitleLoader.SUPPORTED_EXTENSIONS)

    @staticmethod
    def is_subtitle_file(file_path: str | Path) -> bool:
        """Check if file is a supported subtitle format.

        Args:
            file_path: Path to check

        Returns:
            True if file has a supported subtitle extension
        """
        extension = Path(file_path).suffix.lower()
        return extension in SubtitleLoader.SUPPORTED_EXTENSIONS
