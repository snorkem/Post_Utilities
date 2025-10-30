"""Excel and CSV file loading utilities.

This module provides a unified interface for loading data from
Excel and CSV files using pandas.
"""

from pathlib import Path
from typing import Iterator

import pandas as pd

from l3rds.utils.exceptions import InvalidExcelDataError
from l3rds.utils.logger import get_logger

logger = get_logger(__name__)


class ExcelLoader:
    """Loads data from Excel or CSV files.

    This class provides a simple interface for loading tabular data
    from various file formats, with error handling and validation.

    Example:
        >>> loader = ExcelLoader()
        >>> for row in loader.load("data.xlsx"):
        ...     print(row['Main Text'])
    """

    def load(self, file_path: str | Path) -> pd.DataFrame:
        """Load data from CSV or Excel file.

        Args:
            file_path: Path to the file to load

        Returns:
            DataFrame containing the loaded data

        Raises:
            InvalidExcelDataError: If file cannot be loaded or is invalid

        Example:
            >>> loader = ExcelLoader()
            >>> df = loader.load("data.xlsx")
            >>> len(df)
            10
        """
        path = Path(file_path)

        logger.info(f"Loading data from {path}")

        try:
            if path.suffix.lower() == ".csv":
                data = pd.read_csv(path)
            elif path.suffix.lower() in (".xlsx", ".xls"):
                data = pd.read_excel(path)
            else:
                raise InvalidExcelDataError(
                    f"Unsupported file format: {path.suffix}. "
                    "Please use CSV or Excel files (.csv, .xlsx, .xls)."
                )
        except FileNotFoundError:
            raise InvalidExcelDataError(f"File not found: {path}")
        except PermissionError:
            raise InvalidExcelDataError(f"Permission denied reading file: {path}")
        except Exception as e:
            raise InvalidExcelDataError(f"Error loading file: {e}")

        # Basic validation
        if data.empty:
            raise InvalidExcelDataError(
                f"File is empty: {path}",
                row_index=0,
            )

        if len(data.columns) < 1:
            raise InvalidExcelDataError(
                f"File must have at least 1 column. "
                f"At minimum: one text column (Main Text or Secondary Text). Found {len(data.columns)} columns."
            )

        logger.info(
            f"Loaded {len(data)} rows with {len(data.columns)} columns from {path.name}"
        )
        logger.debug(f"Columns: {list(data.columns)}")

        return data

    def iter_rows(self, file_path: str | Path) -> Iterator[pd.Series]:
        """Iterate over rows in a file.

        Args:
            file_path: Path to the file to load

        Yields:
            Series objects representing each row

        Raises:
            InvalidExcelDataError: If file cannot be loaded

        Example:
            >>> loader = ExcelLoader()
            >>> for row in loader.iter_rows("data.xlsx"):
            ...     print(row['Main Text'])
        """
        data = self.load(file_path)

        for index, row in data.iterrows():
            yield row

    def get_row_count(self, file_path: str | Path) -> int:
        """Get the number of rows in a file.

        Args:
            file_path: Path to the file

        Returns:
            Number of data rows (excluding header)

        Raises:
            InvalidExcelDataError: If file cannot be loaded

        Example:
            >>> loader = ExcelLoader()
            >>> count = loader.get_row_count("data.xlsx")
        """
        data = self.load(file_path)
        return len(data)

    @staticmethod
    def get_column_names(data: pd.DataFrame) -> list[str]:
        """Get column names from DataFrame.

        Args:
            data: DataFrame to inspect

        Returns:
            List of column names

        Example:
            >>> loader = ExcelLoader()
            >>> df = loader.load("data.xlsx")
            >>> columns = loader.get_column_names(df)
        """
        return data.columns.tolist()
