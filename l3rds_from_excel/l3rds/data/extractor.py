"""Excel row data extraction utilities.

This module provides classes for extracting and validating data from
Excel/CSV rows, eliminating the repetitive column-checking code from
the original implementation.
"""

from typing import Any

import pandas as pd

from l3rds.data.models import RowData
from l3rds.utils.exceptions import InvalidExcelDataError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class ColumnMapper:
    """Maps Excel columns to expected field names.

    This class handles the mapping between various column name aliases
    and the standardized field names used internally.

    Example:
        >>> mapper = ColumnMapper()
        >>> mapper.find_column(row, 'main_color')
        'Main Color'
    """

    # Column name aliases - maps field name to list of acceptable column names
    COLUMN_ALIASES: dict[str, list[str]] = {
        # Required fields
        "main_text": ["Main Text"],
        "secondary_text": ["Secondary Text"],
        "justification": ["Justification"],
        # Optional fields
        "main_font": ["Main Font", "Font"],
        "secondary_font": ["Secondary Font"],
        "main_color": ["Main Color", "Main Text Color"],
        "secondary_color": ["Secondary Color", "Secondary Text Color"],
        "bg_color": ["Background Color", "BG Color"],
        "bar_color": ["Bar Color"],
        "text_outline": ["Text Outline", "Outline"],
        "text_shadow": ["Text Shadow", "Shadow"],
        "shadow_color": ["Shadow Color"],
        "file_name": ["File Name"],
        "main_font_size": ["Main Font Size"],
        "secondary_font_size": ["Secondary Font Size"],
        "padding": ["Padding"],
        "wrap_text": ["Text Wrap", "Wrap Text"],
        "wrap_padding": ["Wrap Padding", "Text Wrap Padding"],
        "position_offset_x": ["Position Offset X", "Horizontal Offset", "Offset X"],
        "position_offset_y": ["Position Offset Y", "Vertical Offset", "Offset Y"],
    }

    @classmethod
    def find_column(cls, row: pd.Series, field_name: str) -> str | None:
        """Find the actual column name for a field.

        Args:
            row: Pandas Series (Excel row)
            field_name: Logical field name

        Returns:
            Actual column name if found and has a value, None otherwise

        Example:
            >>> mapper = ColumnMapper()
            >>> col = mapper.find_column(row, 'main_color')
        """
        aliases = cls.COLUMN_ALIASES.get(field_name, [field_name])
        column_names = row.index.tolist()

        for col in column_names:
            col_stripped = col.strip()
            if col_stripped in aliases and pd.notna(row[col]):
                return col

        return None

    @classmethod
    def find_column_by_name(cls, row: pd.Series, field_name: str) -> str | None:
        """Find the actual column name for a field, regardless of whether it has a value.

        This method is used for required fields where we need to find the column
        even if it's empty, so we can provide proper validation errors.

        Args:
            row: Pandas Series (Excel row)
            field_name: Logical field name

        Returns:
            Actual column name if found, None otherwise

        Example:
            >>> mapper = ColumnMapper()
            >>> col = mapper.find_column_by_name(row, 'main_text')
            'Main Text'
        """
        aliases = cls.COLUMN_ALIASES.get(field_name, [field_name])
        column_names = row.index.tolist()

        for col in column_names:
            col_stripped = col.strip()
            if col_stripped in aliases:
                return col

        return None

    @classmethod
    def get_value(cls, row: pd.Series, field_name: str, default: Any = None) -> Any:
        """Get value for a field from the row.

        Args:
            row: Pandas Series (Excel row)
            field_name: Logical field name
            default: Default value if not found

        Returns:
            Field value or default

        Example:
            >>> mapper = ColumnMapper()
            >>> color = mapper.get_value(row, 'main_color', 'white')
        """
        col = cls.find_column(row, field_name)
        if col is not None:
            return row[col]
        return default


class ExcelRowExtractor:
    """Extracts and validates data from Excel rows.

    This class handles all the logic for extracting data from Excel/CSV rows,
    eliminating the repetitive column-checking code from the original
    implementation (200+ lines).

    Attributes:
        column_mapper: ColumnMapper instance
        debug: Enable debug logging

    Example:
        >>> extractor = ExcelRowExtractor(debug=True)
        >>> row_data = extractor.extract_row(row)
    """

    def __init__(self, column_mapper: ColumnMapper | None = None, debug: bool = False, default_justification: str = "lower left"):
        """Initialize the extractor.

        Args:
            column_mapper: Column mapper (creates default if None)
            debug: Enable debug output
            default_justification: Default justification when Excel doesn't specify (default: "lower left")
        """
        self.column_mapper = column_mapper or ColumnMapper()
        self.debug = debug
        self.default_justification = default_justification

    def extract_row(self, row: pd.Series, row_index: int | None = None) -> RowData:
        """Extract data from an Excel row.

        Args:
            row: Pandas Series representing a row
            row_index: Optional row index for error messages

        Returns:
            RowData object with extracted values

        Raises:
            InvalidExcelDataError: If required fields are missing or invalid

        Example:
            >>> extractor = ExcelRowExtractor()
            >>> for i, row in df.iterrows():
            ...     data = extractor.extract_row(row, i)
        """
        column_names = row.index.tolist()

        if self.debug:
            logger.debug(f"Processing row {row_index}: {dict(row)}")

        # Validate that at least one text column exists
        main_text_col = self.column_mapper.find_column_by_name(row, "main_text")
        secondary_text_col = self.column_mapper.find_column_by_name(row, "secondary_text")

        if main_text_col is None and secondary_text_col is None:
            available_cols = ", ".join([f"'{col}'" for col in column_names])
            raise InvalidExcelDataError(
                f"Missing required columns: At least one of 'Main Text' or 'Secondary Text' must be present. "
                f"Available columns: {available_cols}",
                row_index=row_index,
            )

        # Extract text fields (now optional, but at least one must be provided)
        try:
            main_text = ""
            secondary_text = ""

            # Extract main text if column exists and has value
            if main_text_col is not None and pd.notna(row[main_text_col]):
                main_text = str(row[main_text_col]).strip()

            # Extract secondary text if column exists and has value
            if secondary_text_col is not None and pd.notna(row[secondary_text_col]):
                secondary_text = str(row[secondary_text_col]).strip()

            # Validate that at least one is non-empty
            if not main_text and not secondary_text:
                raise InvalidExcelDataError(
                    f"At least one of 'Main Text' or 'Secondary Text' must be provided",
                    row_index=row_index,
                )

            # Justification is now optional - use default if not provided
            justification_col = self.column_mapper.find_column_by_name(row, "justification")
            if justification_col:
                justification = self._get_string_field(row, "justification", row_index) or self.default_justification
            else:
                justification = self.default_justification
        except InvalidExcelDataError:
            raise
        except Exception as e:
            raise InvalidExcelDataError(
                f"Error reading text fields: {e}",
                row_index=row_index,
            )

        # Create RowData with required fields (main_font is now optional)
        data = RowData(
            main_text=main_text,
            secondary_text=secondary_text,
            justification=justification,
        )

        # Extract optional font fields (now including main_font)
        data.main_font = self._get_string_field(row, "main_font", row_index)
        data.secondary_font = self._get_string_field(row, "secondary_font", row_index)
        data.file_name = self._get_string_field(row, "file_name", row_index)

        # Extract numeric fields
        data.main_font_size = self._get_int_field(row, "main_font_size", row_index)
        data.secondary_font_size = self._get_int_field(
            row, "secondary_font_size", row_index
        )
        data.padding = self._get_int_field(row, "padding", row_index)

        # Extract text wrapping fields
        data.wrap_text = self._get_bool_field(row, "wrap_text", row_index)
        data.wrap_padding = self._get_int_field(row, "wrap_padding", row_index)

        # Extract position offset fields
        data.position_offset_x = self._get_int_field(row, "position_offset_x", row_index) or 0
        data.position_offset_y = self._get_int_field(row, "position_offset_y", row_index) or 0

        # Extract color fields (stored as strings for later parsing)
        data.main_color = self._get_string_field(row, "main_color", row_index)
        data.secondary_color = self._get_string_field(row, "secondary_color", row_index)
        data.bg_color = self._get_string_field(row, "bg_color", row_index)
        data.bar_color = self._get_string_field(row, "bar_color", row_index)

        # Extract effect fields
        data.text_outline = self._get_string_field(row, "text_outline", row_index)
        data.text_shadow = self._get_bool_field(row, "text_shadow", row_index)
        data.shadow_color = self._get_string_field(row, "shadow_color", row_index)

        if self.debug:
            logger.debug(f"Extracted row data: {data}")

        return data

    def _get_required_string(
        self, row: pd.Series, column: str, row_index: int | None
    ) -> str:
        """Get required string field value.

        Args:
            row: Pandas Series
            column: Column name
            row_index: Row index for error messages

        Returns:
            String value

        Raises:
            InvalidExcelDataError: If field is missing or empty
        """
        if pd.isna(row[column]):
            raise InvalidExcelDataError(
                f"Required field is empty",
                row_index=row_index,
                column_name=column,
            )

        value = str(row[column]).strip()

        if not value:
            raise InvalidExcelDataError(
                f"Required field is empty",
                row_index=row_index,
                column_name=column,
            )

        return value

    def _get_string_field(
        self, row: pd.Series, field_name: str, row_index: int | None
    ) -> str | None:
        """Get optional string field value.

        Args:
            row: Pandas Series
            field_name: Field name to look up
            row_index: Row index for error messages

        Returns:
            String value or None
        """
        value = self.column_mapper.get_value(row, field_name)
        if value is not None:
            result = str(value).strip()
            if self.debug:
                logger.debug(
                    f"Row {row_index}: Found {field_name} = '{result}'"
                )
            return result
        return None

    def _get_int_field(
        self, row: pd.Series, field_name: str, row_index: int | None
    ) -> int | None:
        """Get optional integer field value.

        Args:
            row: Pandas Series
            field_name: Field name to look up
            row_index: Row index for error messages

        Returns:
            Integer value or None
        """
        value = self.column_mapper.get_value(row, field_name)
        if value is not None:
            try:
                result = int(float(str(value).strip()))
                if self.debug:
                    logger.debug(
                        f"Row {row_index}: Found {field_name} = {result}"
                    )
                return result
            except ValueError as e:
                logger.warning(
                    f"Row {row_index}: Cannot parse {field_name} as integer: {value}. "
                    f"Error: {e}"
                )
        return None

    def _get_bool_field(
        self, row: pd.Series, field_name: str, row_index: int | None
    ) -> bool:
        """Get optional boolean field value.

        Args:
            row: Pandas Series
            field_name: Field name to look up
            row_index: Row index for error messages

        Returns:
            Boolean value (defaults to False)
        """
        value = self.column_mapper.get_value(row, field_name)
        if value is not None:
            str_value = str(value).lower().strip()
            result = str_value in ("yes", "true", "1", "on", "enabled")
            if self.debug and result:
                logger.debug(
                    f"Row {row_index}: Found {field_name} = {result}"
                )
            return result
        return False
