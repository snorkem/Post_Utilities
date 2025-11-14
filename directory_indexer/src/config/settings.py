"""
Configuration settings for Directory Indexer.

This module contains all configuration classes used throughout the application.
Each class groups related configuration constants for better organization.
"""


class DatabaseConfig:
    """Database mode configuration."""
    FILE_COUNT_THRESHOLD = 200_000  # Switch to DB mode above this count
    PAGE_SIZE = 100  # Rows to fetch per database query
    BATCH_SIZE = 5000  # Database insert batch size (optimized for performance)


class ProgressConfig:
    """Progress reporting configuration."""
    REPORT_INTERVAL = 1000  # Report progress every N files


class ServerConfig:
    """HTTP server configuration."""
    DEFAULT_PORT = 8000  # Default port for serve.py


class StatisticsConfig:
    """Statistics generation configuration."""
    TOP_EXTENSIONS_COUNT = 10  # Show top N extensions in summary
    LARGEST_FILES_COUNT = 50  # Show top N largest files
    RECENT_FILES_COUNT = 50  # Show top N recent files
