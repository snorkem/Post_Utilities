"""Preview functionality for generated images.

This module provides cross-platform preview capabilities for generated
lower third images.
"""

import os
import subprocess
import sys
import tempfile

from PIL import Image

from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class PreviewManager:
    """Manages image preview across platforms.

    Example:
        >>> preview = PreviewManager()
        >>> preview.show(image)
    """

    @staticmethod
    def show(image: Image.Image, wait_for_user: bool = True) -> None:
        """Show a preview of the image.

        Saves the image to a temporary file and opens it with the
        default system viewer.

        Args:
            image: PIL Image to preview
            wait_for_user: If True, wait for user to press Enter

        Example:
            >>> PreviewManager.show(image)
        """
        # Create temporary file
        # Note: We get the filename but let the context manager close the handle
        # before saving the image. This prevents file handle leaks on Windows.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_filename = temp_file.name
        # File handle is now properly closed

        # Save image to temporary file
        image.save(temp_filename)

        logger.info(f"Preview image saved to: {temp_filename}")
        logger.info("Opening preview with system default viewer...")

        # Validate temp filename to prevent command injection
        if not os.path.isfile(temp_filename) or not temp_filename.endswith('.png'):
            logger.error(f"Invalid temporary file: {temp_filename}")
            return

        # Open with default viewer based on platform
        try:
            if sys.platform == "win32":
                os.startfile(temp_filename)
            elif sys.platform == "darwin":  # macOS
                # Use subprocess.run with timeout for security and reliability
                subprocess.run(["open", temp_filename], timeout=5, check=False)
            else:  # Linux and other Unix-like
                subprocess.run(["xdg-open", temp_filename], timeout=5, check=False)
        except subprocess.TimeoutExpired:
            logger.warning("Preview viewer timed out after 5 seconds")
        except Exception as e:
            logger.warning(f"Could not open preview automatically: {e}")
            logger.info(f"Please open {temp_filename} manually to view the preview.")

        if wait_for_user:
            input("\nPress Enter to continue...")
            # Clean up temporary file after user views it
            try:
                os.unlink(temp_filename)
            except Exception as e:
                logger.debug(f"Could not delete temporary file: {e}")
        else:
            # Don't delete immediately - let the system viewer open it first
            # The OS will clean up /tmp files periodically
            logger.debug(f"Temporary preview file: {temp_filename} (not immediately cleaned up)")
