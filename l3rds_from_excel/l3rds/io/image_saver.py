"""Image saving utilities with format conversion.

This module handles saving generated images in various formats with
proper handling of bit depth, transparency, and file management.
"""

import numpy as np
from pathlib import Path

from PIL import Image

from l3rds.config.models import OutputConfig
from l3rds.utils.constants import BIT_DEPTH_8_TO_16_MULTIPLIER
from l3rds.utils.exceptions import ImageSaveError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class ImageSaver:
    """Saves images with format conversion and bit depth handling.

    Example:
        >>> saver = ImageSaver(output_config)
        >>> path = saver.save(image, "output_dir", "filename")
    """

    def __init__(self, output_config: OutputConfig):
        """Initialize image saver.

        Args:
            output_config: Output configuration
        """
        self.config = output_config

    def save(
        self,
        image: Image.Image,
        output_dir: str | Path,
        filename: str,
    ) -> Path:
        """Save image with configured format and settings.

        Args:
            image: PIL Image to save
            output_dir: Output directory
            filename: Base filename (without extension)

        Returns:
            Path to saved file

        Raises:
            ImageSaveError: If save fails

        Example:
            >>> path = saver.save(image, "output/", "john_doe")
        """
        output_path = self._get_output_path(output_dir, filename)

        # Check if file exists and should skip
        if self.config.skip_existing and output_path.exists():
            logger.info(f"Skipping existing file: {output_path}")
            return output_path

        try:
            # Handle 16-bit TIFF specially
            if self._is_16bit_tiff():
                self._save_16bit_tiff(image, output_path)
            else:
                # Standard save using PIL
                image.save(output_path)

            logger.info(f"Saved image: {output_path}")
            return output_path

        except Exception as e:
            raise ImageSaveError(
                f"Failed to save image: {e}",
                output_path=str(output_path),
                format=self.config.format,
            ) from e

    def _get_output_path(self, output_dir: str | Path, filename: str) -> Path:
        """Get full output path with proper extension.

        Args:
            output_dir: Output directory
            filename: Base filename

        Returns:
            Complete output path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine extension
        if self.config.format.lower() in ("tiff", "tif"):
            ext = ".tiff"
        else:
            ext = f".{self.config.format.lower()}"

        return output_dir / f"{filename}{ext}"

    def _is_16bit_tiff(self) -> bool:
        """Check if output is 16-bit TIFF.

        Returns:
            True if 16-bit TIFF
        """
        return (
            self.config.format.lower() in ("tiff", "tif")
            and self.config.bit_depth == 16
        )

    def _save_16bit_tiff(self, image: Image.Image, output_path: Path) -> None:
        """Save image as 16-bit TIFF.

        Args:
            image: PIL Image
            output_path: Output path

        Raises:
            ImageSaveError: If tifffile not available or save fails
        """
        try:
            import tifffile
        except ImportError:
            logger.warning(
                "tifffile module not found. Using 8-bit TIFF instead. "
                "To enable 16-bit support: pip install tifffile"
            )
            image.save(output_path)
            return

        # Convert PIL image to numpy array
        arr = np.array(image)

        # Scale from 8-bit to 16-bit range (0-255 -> 0-65535)
        arr = arr.astype(np.uint16) * BIT_DEPTH_8_TO_16_MULTIPLIER

        # Save as 16-bit TIFF
        tifffile.imwrite(output_path, arr, photometric="rgb")
        logger.debug(f"Saved 16-bit TIFF: {output_path}")
