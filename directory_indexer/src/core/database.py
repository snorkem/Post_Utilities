"""
Database management for Directory Indexer.

This module provides database creation and management functionality for storing
file information when the dataset is too large for JSON mode.
"""

import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from ..config.settings import DatabaseConfig
from ..utils.formatting import SizeFormatter


class DatabaseManager:
    """
    Manages SQLite database creation and operations for file indexing.

    This class handles creating the database schema, inserting file records,
    and managing metadata for large file collections.
    """

    def __init__(self, db_path: str):
        """
        Initialize the DatabaseManager.

        Args:
            db_path: Path where the SQLite database will be created
        """
        self.db_path = db_path

    def create_database(
        self,
        files_data: List[Dict[str, Any]],
        total_size: int,
        extension_stats: Dict[str, Dict[str, Any]],
        root_path: Path
    ) -> int:
        """
        Create SQLite database with file information.

        Args:
            files_data: List of file information dictionaries
            total_size: Total size of all files in bytes
            extension_stats: Statistics grouped by file extension
            root_path: Root directory that was scanned

        Returns:
            Size of the created database file in bytes
        """
        print(f"\nCreating SQLite database: {self.db_path}")

        # Remove existing database if it exists
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create schema
        self._create_schema(cursor)

        # Insert data
        self._insert_metadata(cursor, files_data, total_size, root_path)
        self._insert_extension_stats(cursor, extension_stats)
        self._insert_files(cursor, files_data)

        conn.commit()
        conn.close()

        db_size = os.path.getsize(self.db_path)
        print(f"✓ Database created: {self.db_path}")
        print(f"  Database size: {SizeFormatter.format_size(db_size)}")
        return db_size

    def _create_schema(self, cursor: sqlite3.Cursor) -> None:
        """
        Create database tables and indexes.

        Args:
            cursor: SQLite cursor for executing commands
        """
        # Create files table
        cursor.execute('''
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                directory TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                size_human TEXT NOT NULL,
                extension TEXT NOT NULL,
                modified TEXT NOT NULL,
                created TEXT NOT NULL,
                icon TEXT NOT NULL
            )
        ''')

        # Create metadata table
        cursor.execute('''
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        # Create extension statistics table
        cursor.execute('''
            CREATE TABLE extension_stats (
                extension TEXT PRIMARY KEY,
                count INTEGER NOT NULL,
                total_size INTEGER NOT NULL
            )
        ''')

        # Create indexes for fast queries
        cursor.execute('CREATE INDEX idx_extension ON files(extension)')
        cursor.execute('CREATE INDEX idx_size ON files(size_bytes)')
        cursor.execute('CREATE INDEX idx_modified ON files(modified)')
        cursor.execute('CREATE INDEX idx_created ON files(created)')
        cursor.execute('CREATE INDEX idx_name ON files(name)')
        cursor.execute('CREATE INDEX idx_directory ON files(directory)')

        # Indexes for hierarchical queries and search performance
        cursor.execute('CREATE INDEX idx_directory_name ON files(directory, name)')
        cursor.execute('CREATE INDEX idx_name_lower ON files(LOWER(name))')
        cursor.execute('CREATE INDEX idx_directory_lower ON files(LOWER(directory))')

    def _insert_metadata(
        self,
        cursor: sqlite3.Cursor,
        files_data: List[Dict[str, Any]],
        total_size: int,
        root_path: Path
    ) -> None:
        """
        Insert metadata records.

        Args:
            cursor: SQLite cursor for executing commands
            files_data: List of file information dictionaries
            total_size: Total size of all files in bytes
            root_path: Root directory that was scanned
        """
        cursor.execute(
            'INSERT INTO metadata (key, value) VALUES (?, ?)',
            ('total_files', str(len(files_data)))
        )
        cursor.execute(
            'INSERT INTO metadata (key, value) VALUES (?, ?)',
            ('total_size', str(total_size))
        )
        cursor.execute(
            'INSERT INTO metadata (key, value) VALUES (?, ?)',
            ('root_path', str(root_path))
        )
        cursor.execute(
            'INSERT INTO metadata (key, value) VALUES (?, ?)',
            ('generated_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )

    def _insert_extension_stats(
        self,
        cursor: sqlite3.Cursor,
        extension_stats: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Insert extension statistics records.

        Args:
            cursor: SQLite cursor for executing commands
            extension_stats: Statistics grouped by file extension
        """
        for ext, stats in extension_stats.items():
            cursor.execute(
                'INSERT INTO extension_stats (extension, count, total_size) VALUES (?, ?, ?)',
                (ext, stats['count'], stats['size'])
            )

    def _insert_files(
        self,
        cursor: sqlite3.Cursor,
        files_data: List[Dict[str, Any]]
    ) -> None:
        """
        Insert file records in batches for performance.

        Args:
            cursor: SQLite cursor for executing commands
            files_data: List of file information dictionaries
        """
        batch_size = DatabaseConfig.BATCH_SIZE

        for i in range(0, len(files_data), batch_size):
            batch = files_data[i:i + batch_size]
            cursor.executemany('''
                INSERT INTO files (name, path, relative_path, directory, size_bytes,
                                   size_human, extension, modified, created, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                (
                    f['name'],
                    f['path'],
                    f['relative_path'],
                    f['directory'],
                    f['size_bytes'],
                    f['size_human'],
                    f['extension'],
                    f['modified'],
                    f['created'],
                    f['icon']
                )
                for f in batch
            ])

            if (i + batch_size) % 10000 == 0:
                print(f"  Inserted {min(i + batch_size, len(files_data)):,} / {len(files_data):,} files...")
