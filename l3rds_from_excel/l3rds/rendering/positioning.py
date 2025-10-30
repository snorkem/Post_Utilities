"""Text positioning strategies for lower thirds.

This module implements the Strategy pattern for calculating text positions,
eliminating 92 lines of nested conditional logic from the original implementation.
"""

from dataclasses import dataclass
from typing import Protocol

from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextDimensions:
    """Dimensions and positioning information for text.

    Attributes:
        main_width: Width of main text in pixels
        main_height: Height of main text in pixels
        secondary_width: Width of secondary text in pixels
        secondary_height: Height of secondary text in pixels
        padding: Padding from edges in pixels
        vertical_spacing: Space between main and secondary text in pixels

    Example:
        >>> dims = TextDimensions(200, 60, 150, 40, 20, 10)
    """

    main_width: int
    main_height: int
    secondary_width: int
    secondary_height: int
    padding: int
    vertical_spacing: int


class PositionStrategy(Protocol):
    """Protocol for text positioning strategies.

    Strategies implementing this protocol calculate positions for
    main and secondary text based on the chosen justification.
    """

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate positions for main and secondary text.

        Args:
            dimensions: Text dimensions
            canvas_width: Canvas width in pixels
            canvas_height: Canvas height in pixels
            bar_y_position: Y position of lower third bar
            bar_padding: Padding inside bar

        Returns:
            Tuple of (main_x, main_y, secondary_x, secondary_y)
        """
        ...


class LowerLeftStrategy:
    """Position text in lower left corner (traditional lower third).

    Example:
        >>> strategy = LowerLeftStrategy()
        >>> positions = strategy.calculate_position(dims, 1920, 1080, 810, 20)
    """

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate lower left positions."""
        main_x = dimensions.padding
        secondary_x = dimensions.padding
        main_y = bar_y_position + bar_padding
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Lower left position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class LowerRightStrategy:
    """Position text in lower right corner."""

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate lower right positions."""
        main_x = canvas_width - dimensions.main_width - dimensions.padding
        secondary_x = canvas_width - dimensions.secondary_width - dimensions.padding
        main_y = bar_y_position + bar_padding
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Lower right position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class LowerCenterStrategy:
    """Position text in lower center (center bottom)."""

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate lower center positions."""
        main_x = (canvas_width - dimensions.main_width) // 2
        secondary_x = (canvas_width - dimensions.secondary_width) // 2
        main_y = bar_y_position + bar_padding
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Lower center position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class UpperLeftStrategy:
    """Position text in upper left corner."""

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate upper left positions."""
        main_x = dimensions.padding
        secondary_x = dimensions.padding
        main_y = dimensions.padding
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Upper left position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class UpperRightStrategy:
    """Position text in upper right corner."""

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate upper right positions."""
        main_x = canvas_width - dimensions.main_width - dimensions.padding
        secondary_x = canvas_width - dimensions.secondary_width - dimensions.padding
        main_y = dimensions.padding
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Upper right position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class UpperCenterStrategy:
    """Position text in upper center (center top)."""

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate upper center positions."""
        main_x = (canvas_width - dimensions.main_width) // 2
        secondary_x = (canvas_width - dimensions.secondary_width) // 2
        main_y = dimensions.padding
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Upper center position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class CenterCenterStrategy:
    """Position text in absolute center of canvas."""

    def calculate_position(
        self,
        dimensions: TextDimensions,
        canvas_width: int,
        canvas_height: int,
        bar_y_position: int,
        bar_padding: int,
    ) -> tuple[int, int, int, int]:
        """Calculate center center positions."""
        total_text_height = (
            dimensions.main_height + dimensions.vertical_spacing + dimensions.secondary_height
        )
        start_y = (canvas_height - total_text_height) // 2

        main_x = (canvas_width - dimensions.main_width) // 2
        secondary_x = (canvas_width - dimensions.secondary_width) // 2
        main_y = start_y
        secondary_y = main_y + dimensions.main_height + dimensions.vertical_spacing

        logger.debug(f"Center center position: main=({main_x}, {main_y}), sec=({secondary_x}, {secondary_y})")
        return (main_x, main_y, secondary_x, secondary_y)


class PositionStrategyFactory:
    """Factory for creating position strategies based on justification.

    This factory maps justification strings to appropriate strategy classes,
    providing a clean interface for position calculation.

    Example:
        >>> factory = PositionStrategyFactory()
        >>> strategy = factory.get_strategy("lower left")
        >>> isinstance(strategy, LowerLeftStrategy)
        True
    """

    _strategies: dict[str, type[PositionStrategy]] = {
        # Lower positions
        "lower left": LowerLeftStrategy,
        "lower right": LowerRightStrategy,
        "lower center": LowerCenterStrategy,
        "center bottom": LowerCenterStrategy,  # Alias
        # Upper positions
        "upper left": UpperLeftStrategy,
        "upper right": UpperRightStrategy,
        "upper center": UpperCenterStrategy,
        "center top": UpperCenterStrategy,  # Alias
        # Center position
        "center center": CenterCenterStrategy,
        "center": CenterCenterStrategy,  # Alias
        # Legacy single-word positions (default to lower)
        "left": LowerLeftStrategy,
        "right": LowerRightStrategy,
    }

    @classmethod
    def get_strategy(cls, justification: str) -> PositionStrategy:
        """Get appropriate positioning strategy for justification.

        Args:
            justification: Justification string (e.g., "lower left", "center top")

        Returns:
            PositionStrategy instance

        Example:
            >>> strategy = PositionStrategyFactory.get_strategy("lower left")
            >>> type(strategy).__name__
            'LowerLeftStrategy'
        """
        # Normalize justification
        normalized = justification.lower().strip()

        # Look up strategy class
        strategy_class = cls._strategies.get(normalized, LowerLeftStrategy)

        logger.debug(f"Selected {strategy_class.__name__} for '{justification}'")

        # Instantiate and return
        return strategy_class()

    @classmethod
    def get_available_justifications(cls) -> list[str]:
        """Get list of all available justification strings.

        Returns:
            Sorted list of justification strings

        Example:
            >>> justifications = PositionStrategyFactory.get_available_justifications()
            >>> "lower left" in justifications
            True
        """
        return sorted(cls._strategies.keys())
