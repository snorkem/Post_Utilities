"""
Configuration settings for Directory Indexer.

This module contains all configuration classes used throughout the application.
Each class groups related configuration constants for better organization.
"""


class UIConfig:
    """User interface rendering configuration."""
    ROW_HEIGHT = 45  # Height of each table row in pixels
    BUFFER_SIZE = 10  # Extra rows to render above/below viewport
    CHUNK_SIZE = 5000  # Files per chunk in JSON mode
    CHUNK_LOAD_DELAY_MS = 50  # Delay between loading chunks
    SCROLL_THROTTLE_MS = 16  # ~60fps scroll throttle (1000/60)


class DatabaseConfig:
    """Database mode configuration."""
    FILE_COUNT_THRESHOLD = 150_000  # Switch to DB mode above this count
    PAGE_SIZE = 100  # Rows to fetch per database query
    BATCH_SIZE = 1000  # Database insert batch size


class ProgressConfig:
    """Progress reporting configuration."""
    REPORT_INTERVAL = 1000  # Report progress every N files


class ServerConfig:
    """HTTP server configuration."""
    DEFAULT_PORT = 8000  # Default port for serve.py


class DisplayConfig:
    """Display formatting configuration."""
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    DATE_FORMAT_SHORT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    DATETIME_FORMAT_DISPLAY = '%Y-%m-%d, %H:%M:%S'


class StatisticsConfig:
    """Statistics generation configuration."""
    TOP_EXTENSIONS_COUNT = 10  # Show top N extensions
    TOP_FILES_COUNT = 10  # Show top N largest files
    RECENT_FILES_COUNT = 10  # Show top N recent files
