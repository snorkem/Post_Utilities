#!/usr/bin/env python3
"""
Directory Structure Archiver
Generates an interactive HTML file showing all files in a directory tree
with names, full paths, sizes, and extensions.
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html import escape as html_escape_builtin


# ============================================================================
# Configuration Constants
# ============================================================================

class UIConfig:
    """User interface rendering configuration."""
    ROW_HEIGHT = 45  # Height of each table row in pixels
    BUFFER_SIZE = 10  # Extra rows to render above/below viewport
    CHUNK_SIZE = 5000  # Files per chunk in JSON mode
    CHUNK_LOAD_DELAY_MS = 50  # Delay between loading chunks
    SCROLL_THROTTLE_MS = 16  # ~60fps scroll throttle (1000/60)


class DatabaseConfig:
    """Database mode configuration."""
    FILE_COUNT_THRESHOLD = 200_000  # Switch to DB mode above this count
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


# ============================================================================
# Utility Functions
# ============================================================================

def get_size_human_readable(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def get_file_icon(extension):
    """Return emoji icon for file type"""
    icon_map = {
        # Documents
        '.pdf': '📄', '.doc': '📝', '.docx': '📝', '.txt': '📝', '.rtf': '📝',
        '.md': '📝', '.odt': '📝',
        # Spreadsheets
        '.xls': '📊', '.xlsx': '📊', '.csv': '📊', '.ods': '📊',
        # Presentations
        '.ppt': '📊', '.pptx': '📊', '.key': '📊', '.odp': '📊',
        # Images
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', 
        '.bmp': '🖼️', '.svg': '🖼️', '.webp': '🖼️', '.ico': '🖼️',
        '.heic': '🖼️', '.raw': '🖼️', '.tiff': '🖼️', '.tif': '🖼️',
        # Videos
        '.mp4': '🎬', '.avi': '🎬', '.mov': '🎬', '.mkv': '🎬',
        '.wmv': '🎬', '.flv': '🎬', '.webm': '🎬', '.m4v': '🎬',
        '.mxf': '🎬', '.r3d': '🎬',
        # Audio
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.aac': '🎵',
        '.ogg': '🎵', '.m4a': '🎵', '.wma': '🎵',
        # Archives
        '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦',
        '.gz': '📦', '.bz2': '📦', '.xz': '📦',
        # Code
        '.py': '💻', '.js': '💻', '.html': '💻', '.css': '💻',
        '.java': '💻', '.cpp': '💻', '.c': '💻', '.h': '💻',
        '.php': '💻', '.rb': '💻', '.go': '💻', '.rs': '💻',
        '.swift': '💻', '.kt': '💻', '.ts': '💻', '.jsx': '💻',
        '.tsx': '💻', '.vue': '💻', '.json': '💻', '.xml': '💻',
        '.yaml': '💻', '.yml': '💻', '.sh': '💻', '.bat': '💻',
        # Executables & Installers
        '.exe': '⚙️', '.app': '⚙️', '.dmg': '⚙️', '.pkg': '⚙️',
        '.deb': '⚙️', '.rpm': '⚙️',
        # Databases
        '.db': '🗄️', '.sqlite': '🗄️', '.sql': '🗄️',
        # Fonts
        '.ttf': '🔤', '.otf': '🔤', '.woff': '🔤', '.woff2': '🔤',
    }
    return icon_map.get(extension.lower(), '📎')

def get_common_css():
    """Return common CSS styles used in both HTML templates"""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            background: #f5f5f5;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }

        .header h1 {
            margin-bottom: 10px;
            font-size: 28px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
        }

        .stat-label {
            opacity: 0.9;
            margin-bottom: 5px;
            font-size: 13px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
        }

        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }

        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }

        .tab:hover {
            background: #e9ecef;
            color: #333;
        }

        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
            background: white;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .controls {
            padding: 20px 30px;
            background: #fafafa;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        .search-box {
            flex: 1;
            min-width: 300px;
            padding: 12px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 6px;
            outline: none;
        }

        .search-box:focus {
            border-color: #667eea;
        }

        .filter-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .filter-label {
            font-size: 13px;
            color: #666;
            font-weight: 500;
        }

        select {
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            outline: none;
        }

        select:focus {
            border-color: #667eea;
        }

        table {
            width: 100%;
            min-width: 1200px;
            border-collapse: collapse;
            table-layout: fixed;
        }

        th {
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            cursor: pointer;
            user-select: none;
            position: sticky;
            top: 0;
            z-index: 10;
            border-bottom: 2px solid #ddd;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        th:hover {
            background: #e9ecef;
        }

        th::after {
            content: ' ↕';
            opacity: 0.3;
            font-size: 12px;
        }

        th.sort-asc::after {
            content: ' ↑';
            opacity: 1;
        }

        th.sort-desc::after {
            content: ' ↓';
            opacity: 1;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 13px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .file-icon {
            font-size: 18px;
            margin-right: 8px;
        }

        .file-name {
            font-weight: 500;
            color: #333;
            display: flex;
            align-items: center;
        }

        .file-path {
            color: #666;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            word-break: break-all;
        }

        .file-extension {
            display: inline-block;
            padding: 3px 10px;
            background: #e3f2fd;
            color: #1976d2;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .size-cell {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .size-bar-container {
            flex: 1;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            min-width: 50px;
            max-width: 100px;
        }

        .size-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }

        .size-text {
            text-align: right;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #555;
            white-space: nowrap;
            min-width: 70px;
        }

        .modified {
            color: #666;
            font-size: 12px;
            white-space: nowrap;
        }

        .no-results {
            padding: 40px;
            text-align: center;
            color: #999;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }

        .stat-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
        }

        .stat-card h3 {
            font-size: 16px;
            margin-bottom: 15px;
            color: #333;
        }

        .stat-list {
            list-style: none;
        }

        .stat-list-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }

        .stat-list-item:last-child {
            border-bottom: none;
        }

        .stat-list-label {
            font-size: 13px;
            color: #666;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stat-list-value {
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }

        .progress-bar {
            height: 6px;
            background: #e0e0e0;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 5px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }

        .footer {
            padding: 20px 30px;
            text-align: center;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }

        .result-count {
            padding: 10px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            font-size: 13px;
            color: #666;
        }

        .table-container {
            position: relative;
            height: 600px;
            overflow-y: auto;
            overflow-x: auto;
        }

        .table-spacer {
            position: relative;
            width: 100%;
        }

        .table-viewport {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            will-change: transform;
        }

        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }

        .loading-overlay.hidden {
            display: none;
        }

        .loading-content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            min-width: 400px;
        }

        .loading-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }

        .loading-progress-bar {
            height: 24px;
            background: #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 10px;
        }

        .loading-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: 600;
        }

        .loading-stats {
            font-size: 13px;
            color: #666;
            text-align: center;
        }
"""

def get_common_css_inline_mode():
    """Return CSS specific to inline mode (with column resizing and settings panel)"""
    return """
        /* Column width controls */
        th:nth-child(1) { width: var(--col-name-width, 20%); } /* File Name */
        th:nth-child(2) { width: var(--col-type-width, 8%); }  /* Type */
        th:nth-child(3) { width: var(--col-path-width, 35%); } /* Path */
        th:nth-child(4) { width: var(--col-size-width, 13%); } /* Size */
        th:nth-child(5) { width: var(--col-modified-width, 12%); } /* Modified */
        th:nth-child(6) { width: var(--col-created-width, 12%); } /* Created */

        /* Column resize handles */
        .resize-handle {
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            width: 8px;
            cursor: col-resize;
            z-index: 20;
            background: transparent;
        }

        .resize-handle:hover {
            background: rgba(102, 126, 234, 0.3);
        }

        .resize-handle.resizing {
            background: rgba(102, 126, 234, 0.5);
        }

        th {
            position: relative;
        }

        /* Settings Panel */
        .settings-panel {
            padding: 20px 30px;
            background: #fafafa;
            border-bottom: 1px solid #e0e0e0;
            display: none;
        }

        .settings-panel.visible {
            display: block;
        }

        .settings-toggle {
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: background 0.3s;
        }

        .settings-toggle:hover {
            background: #5568d3;
        }

        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }

        .setting-item {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .setting-label {
            font-size: 13px;
            font-weight: 600;
            color: #333;
        }

        .setting-input {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .setting-input input[type="range"] {
            flex: 1;
            cursor: pointer;
        }

        .setting-value {
            min-width: 50px;
            text-align: right;
            font-size: 13px;
            color: #666;
            font-family: 'Monaco', 'Courier New', monospace;
        }

        .preset-buttons {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .preset-btn {
            padding: 8px 16px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .preset-btn:hover {
            border-color: #667eea;
            color: #667eea;
        }

        .preset-btn.reset {
            background: #ff6b6b;
            color: white;
            border-color: #ff6b6b;
        }

        .preset-btn.reset:hover {
            background: #ee5a52;
            border-color: #ee5a52;
        }

        .path-tooltip {
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-family: 'Monaco', 'Courier New', monospace;
            z-index: 1000;
            pointer-events: none;
            white-space: nowrap;
            max-width: 600px;
            overflow: hidden;
            text-overflow: ellipsis;
            display: none;
        }

        .path-tooltip.visible {
            display: block;
        }
"""

def get_common_css_db_mode():
    """Return CSS specific to database mode"""
    return """
        th:nth-child(1) { width: 20%; } /* File Name */
        th:nth-child(2) { width: 8%; }  /* Type */
        th:nth-child(3) { width: 35%; } /* Path */
        th:nth-child(4) { width: 13%; } /* Size */
        th:nth-child(5) { width: 12%; } /* Modified */
        th:nth-child(6) { width: 12%; } /* Created */

        .db-mode-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 12px;
            margin-top: 10px;
        }
"""

def get_common_javascript():
    """Return common JavaScript utility functions used in both HTML templates"""
    return """
        function throttle(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function updateSortHeaders() {
            document.querySelectorAll('th[data-column]').forEach(header => {
                header.classList.remove('sort-asc', 'sort-desc');
                if (header.dataset.column === currentSort.column) {
                    header.classList.add(currentSort.ascending ? 'sort-asc' : 'sort-desc');
                }
            });
        }
"""

def generate_extension_options(extension_stats):
    """Generate HTML options for extension filter dropdown"""
    sorted_extensions = sorted(extension_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    return '\n'.join(
        f'<option value="{html_escape_builtin(ext)}">{html_escape_builtin(ext)} ({stats["count"]} files)</option>'
        for ext, stats in sorted_extensions
    )

def calculate_total_files(extension_stats):
    """Calculate total number of files from extension statistics"""
    return sum(stats['count'] for stats in extension_stats.values())

def get_directory_name(path):
    """Get directory name from path, returning 'root' for empty names"""
    return Path(path).name or 'root'

def scan_directory(root_path):
    """Scan directory and collect file information"""
    files_data = []
    total_size = 0
    error_count = 0
    # Use defaultdict to avoid dictionary membership checks
    extension_stats = defaultdict(lambda: {'count': 0, 'size': 0})

    root_path = Path(root_path).resolve()

    print(f"Scanning {root_path}...")

    # Cache frequently used methods
    get_size = get_size_human_readable
    get_icon = get_file_icon

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Convert dirpath once per directory
        dir_path_obj = Path(dirpath)

        for filename in filenames:
            try:
                filepath = dir_path_obj / filename
                stat_info = filepath.stat()
                extension = filepath.suffix.lower() or '(none)'

                # Cache expensive operations
                size_bytes = stat_info.st_size
                parent_dir = filepath.parent

                # Handle cross-platform creation time
                try:
                    # macOS/BSD uses st_birthtime for true creation time
                    created_timestamp = stat_info.st_birthtime
                except AttributeError:
                    # Linux/Windows uses st_ctime (inode change time, closest to creation)
                    created_timestamp = stat_info.st_ctime

                files_data.append({
                    'name': filename,
                    'path': str(filepath),
                    'relative_path': str(filepath.relative_to(root_path)),
                    'directory': str(parent_dir.relative_to(root_path)),
                    'size_bytes': size_bytes,
                    'size_human': get_size(size_bytes),
                    'extension': extension,
                    'icon': get_icon(extension),
                    'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'created': datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                })

                total_size += size_bytes

                # Track extension statistics (no more dict membership check needed)
                extension_stats[extension]['count'] += 1
                extension_stats[extension]['size'] += size_bytes

                if len(files_data) % ProgressConfig.REPORT_INTERVAL == 0:
                    print(f"  Processed {len(files_data)} files...")

            except (PermissionError, OSError):
                error_count += 1
                continue

    print(f"✓ Scan complete: {len(files_data)} files found")
    if error_count > 0:
        print(f"  ({error_count} files skipped due to permission errors)")

    # Convert defaultdict back to regular dict for compatibility
    return files_data, total_size, dict(extension_stats)

def create_database(files_data, total_size, extension_stats, root_path, db_path):
    """Create SQLite database with file information"""
    print(f"\nCreating SQLite database: {db_path}")

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
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

    cursor.execute('''
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

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

    # Insert metadata
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                   ('total_files', str(len(files_data))))
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                   ('total_size', str(total_size)))
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                   ('root_path', str(root_path)))
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                   ('generated_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Insert extension stats
    for ext, stats in extension_stats.items():
        cursor.execute('INSERT INTO extension_stats (extension, count, total_size) VALUES (?, ?, ?)',
                       (ext, stats['count'], stats['size']))

    # Insert files in batches for performance
    BATCH_SIZE = DatabaseConfig.BATCH_SIZE
    for i in range(0, len(files_data), BATCH_SIZE):
        batch = files_data[i:i + BATCH_SIZE]
        cursor.executemany('''
            INSERT INTO files (name, path, relative_path, directory, size_bytes, size_human, extension, modified, created, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [(f['name'], f['path'], f['relative_path'], f['directory'], f['size_bytes'],
               f['size_human'], f['extension'], f['modified'], f['created'], f['icon']) for f in batch])

        if (i + BATCH_SIZE) % 10000 == 0:
            print(f"  Inserted {min(i + BATCH_SIZE, len(files_data)):,} / {len(files_data):,} files...")

    conn.commit()
    conn.close()

    db_size = os.path.getsize(db_path)
    print(f"✓ Database created: {db_path}")
    print(f"  Database size: {get_size_human_readable(db_size)}")
    return db_size

def generate_html(files_data, root_path, total_size, extension_stats, output_file):
    """Generate interactive HTML file"""
    
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Index: {root_name}</title>
    <style>
{css_common}
{css_inline_mode}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Directory Index</h1>
            <div style="opacity: 0.9; margin-top: 10px; font-size: 14px;">{root_path}</div>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-label">Total Files</div>
                    <div class="stat-value">{total_files}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Size</div>
                    <div class="stat-value">{total_size_human}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">File Types</div>
                    <div class="stat-value">{total_extensions}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Generated</div>
                    <div class="stat-value">{generated_date}</div>
                </div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" data-tab="files">📋 All Files</button>
            <button class="tab" data-tab="stats">📊 Statistics</button>
        </div>
        
        <div id="filesTab" class="tab-content active">
            <div class="controls">
                <input type="text" id="searchBox" class="search-box" placeholder="🔍 Search files by name, path, or extension...">
                <div class="filter-group">
                    <span class="filter-label">Extension:</span>
                    <select id="extensionFilter">
                        <option value="">All Types</option>
                        {extension_options}
                    </select>
                </div>
                <button class="settings-toggle" id="settingsToggle">⚙️ Column Widths</button>
            </div>

            <div class="settings-panel" id="settingsPanel">
                <h3 style="margin-bottom: 15px; font-size: 16px; color: #333;">Column Width Settings</h3>
                <div class="settings-grid">
                    <div class="setting-item">
                        <label class="setting-label">File Name</label>
                        <div class="setting-input">
                            <input type="range" id="nameWidth" min="10" max="50" value="20">
                            <span class="setting-value" id="nameValue">20%</span>
                        </div>
                    </div>
                    <div class="setting-item">
                        <label class="setting-label">Type</label>
                        <div class="setting-input">
                            <input type="range" id="typeWidth" min="5" max="20" value="8">
                            <span class="setting-value" id="typeValue">8%</span>
                        </div>
                    </div>
                    <div class="setting-item">
                        <label class="setting-label">Path</label>
                        <div class="setting-input">
                            <input type="range" id="pathWidth" min="20" max="70" value="45">
                            <span class="setting-value" id="pathValue">45%</span>
                        </div>
                    </div>
                    <div class="setting-item">
                        <label class="setting-label">Size</label>
                        <div class="setting-input">
                            <input type="range" id="sizeWidth" min="10" max="25" value="15">
                            <span class="setting-value" id="sizeValue">15%</span>
                        </div>
                    </div>
                    <div class="setting-item">
                        <label class="setting-label">Modified</label>
                        <div class="setting-input">
                            <input type="range" id="modifiedWidth" min="8" max="20" value="12">
                            <span class="setting-value" id="modifiedValue">12%</span>
                        </div>
                    </div>
                </div>
                <div class="preset-buttons">
                    <button class="preset-btn" data-preset="compact">Compact</button>
                    <button class="preset-btn" data-preset="default">Default</button>
                    <button class="preset-btn" data-preset="wide-path">Wide Path</button>
                    <button class="preset-btn reset" id="resetWidths">Reset to Default</button>
                </div>
            </div>
            
            <div class="result-count" id="resultCount">
                Showing <strong id="resultNumber">{total_files}</strong> files
            </div>

            <div class="table-container" id="tableContainer">
                <div class="table-spacer" id="tableSpacer"></div>
                <div class="table-viewport" id="tableViewport">
                    <table id="fileTable">
                        <thead>
                            <tr>
                                <th data-column="name">File Name</th>
                                <th data-column="extension">Type</th>
                                <th data-column="path">Path</th>
                                <th data-column="size">Size</th>
                                <th data-column="modified">Modified</th>
                                <th data-column="created">Created</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">
                            {table_rows}
                        </tbody>
                    </table>
                    <div id="noResults" class="no-results" style="display: none;">
                        No files match your search criteria.
                    </div>
                </div>
            </div>
        </div>
        
        <div id="statsTab" class="tab-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📊 Top 10 File Types by Count</h3>
                    <ul class="stat-list">
                        {top_extensions_by_count}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>💾 Top 10 File Types by Size</h3>
                    <ul class="stat-list">
                        {top_extensions_by_size}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>📁 Largest Files</h3>
                    <ul class="stat-list">
                        {largest_files}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>📅 Recently Modified</h3>
                    <ul class="stat-list">
                        {recent_files}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>🆕 Recently Created</h3>
                    <ul class="stat-list">
                        {recent_created}
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Generated on {generated_datetime} • {total_files} files • {total_size_human}
        </div>
    </div>

    <div class="path-tooltip" id="pathTooltip"></div>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="loading-title">Loading File Data...</div>
            <div class="loading-progress-bar">
                <div class="loading-progress-fill" id="loadingProgressFill">0%</div>
            </div>
            <div class="loading-stats" id="loadingStats">Preparing...</div>
        </div>
    </div>

    <script>
        // Progressive chunk loading
        let tableData = [];
        let chunksLoaded = 0;
        let totalChunks = 0;
        const CHUNK_SIZE = {chunk_size};

        // Data chunks will be embedded below
        const dataChunks = {data_chunks_json};
        totalChunks = dataChunks.length;

        // Total files passed from Python (no need to calculate in JS!)
        const totalFiles = {total_files_raw};

        let currentSort = {{ column: 'name', ascending: true }};
        let filteredData = [];
        let maxFileSize = 0;

        // Virtual scrolling configuration
        const ROW_HEIGHT = 45;
        const BUFFER_SIZE = 10;
        let virtualScroll = {{
            startIndex: 0,
            endIndex: 0,
            visibleRows: 0
        }};

        // Column width management
        const defaultWidths = {{
            name: 20,
            type: 8,
            path: 45,
            size: 15,
            modified: 12
        }};

        const presets = {{
            compact: {{ name: 18, type: 8, path: 40, size: 20, modified: 14 }},
            default: {{ name: 20, type: 8, path: 45, size: 15, modified: 12 }},
            'wide-path': {{ name: 15, type: 8, path: 55, size: 12, modified: 10 }}
        }};

        // Common utility functions
{js_common}

        // Load saved widths from localStorage or use defaults
        function loadColumnWidths() {{
            const saved = localStorage.getItem('columnWidths');
            return saved ? JSON.parse(saved) : {{ ...defaultWidths }};
        }}

        // Save column widths to localStorage
        function saveColumnWidths(widths) {{
            localStorage.setItem('columnWidths', JSON.stringify(widths));
        }}

        // Apply column widths to the table
        function applyColumnWidths(widths) {{
            const root = document.documentElement;
            root.style.setProperty('--col-name-width', widths.name + '%');
            root.style.setProperty('--col-type-width', widths.type + '%');
            root.style.setProperty('--col-path-width', widths.path + '%');
            root.style.setProperty('--col-size-width', widths.size + '%');
            root.style.setProperty('--col-modified-width', widths.modified + '%');

            // Update slider values
            document.getElementById('nameWidth').value = widths.name;
            document.getElementById('typeWidth').value = widths.type;
            document.getElementById('pathWidth').value = widths.path;
            document.getElementById('sizeWidth').value = widths.size;
            document.getElementById('modifiedWidth').value = widths.modified;

            // Update display values
            document.getElementById('nameValue').textContent = widths.name + '%';
            document.getElementById('typeValue').textContent = widths.type + '%';
            document.getElementById('pathValue').textContent = widths.path + '%';
            document.getElementById('sizeValue').textContent = widths.size + '%';
            document.getElementById('modifiedValue').textContent = widths.modified + '%';
        }}

        // Initialize with saved or default widths
        let currentWidths = loadColumnWidths();
        applyColumnWidths(currentWidths);

        // Settings panel toggle
        document.getElementById('settingsToggle').addEventListener('click', () => {{
            const panel = document.getElementById('settingsPanel');
            panel.classList.toggle('visible');
        }});

        // Width slider event listeners
        const widthSliders = [
            {{ id: 'nameWidth', key: 'name', valueId: 'nameValue' }},
            {{ id: 'typeWidth', key: 'type', valueId: 'typeValue' }},
            {{ id: 'pathWidth', key: 'path', valueId: 'pathValue' }},
            {{ id: 'sizeWidth', key: 'size', valueId: 'sizeValue' }},
            {{ id: 'modifiedWidth', key: 'modified', valueId: 'modifiedValue' }}
        ];

        widthSliders.forEach(slider => {{
            const element = document.getElementById(slider.id);
            const valueDisplay = document.getElementById(slider.valueId);

            element.addEventListener('input', (e) => {{
                const value = parseInt(e.target.value);
                valueDisplay.textContent = value + '%';
                currentWidths[slider.key] = value;
                applyColumnWidths(currentWidths);
                saveColumnWidths(currentWidths);
            }});
        }});

        // Preset buttons
        document.querySelectorAll('.preset-btn[data-preset]').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const presetName = btn.dataset.preset;
                currentWidths = {{ ...presets[presetName] }};
                applyColumnWidths(currentWidths);
                saveColumnWidths(currentWidths);
            }});
        }});

        // Reset button
        document.getElementById('resetWidths').addEventListener('click', () => {{
            currentWidths = {{ ...defaultWidths }};
            applyColumnWidths(currentWidths);
            saveColumnWidths(currentWidths);
        }});

        // Column resize functionality
        function initColumnResize() {{
            const table = document.getElementById('fileTable');
            const headers = table.querySelectorAll('th');

            headers.forEach((header, index) => {{
                // Skip the last header (no resize needed)
                if (index === headers.length - 1) return;

                const resizeHandle = document.createElement('div');
                resizeHandle.className = 'resize-handle';
                header.appendChild(resizeHandle);

                let startX, startWidth, columnKey;
                const columnKeys = ['name', 'type', 'path', 'size', 'modified'];

                resizeHandle.addEventListener('mousedown', (e) => {{
                    e.preventDefault();
                    e.stopPropagation();

                    columnKey = columnKeys[index];
                    startX = e.pageX;
                    startWidth = currentWidths[columnKey];

                    resizeHandle.classList.add('resizing');
                    document.body.style.cursor = 'col-resize';
                    document.body.style.userSelect = 'none';

                    document.addEventListener('mousemove', handleMouseMove);
                    document.addEventListener('mouseup', handleMouseUp);
                }});

                function handleMouseMove(e) {{
                    const diff = e.pageX - startX;
                    const tableWidth = table.offsetWidth;
                    const percentChange = (diff / tableWidth) * 100;
                    const newWidth = Math.max(5, Math.min(70, startWidth + percentChange));

                    currentWidths[columnKey] = Math.round(newWidth);
                    applyColumnWidths(currentWidths);
                }}

                function handleMouseUp() {{
                    resizeHandle.classList.remove('resizing');
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';

                    document.removeEventListener('mousemove', handleMouseMove);
                    document.removeEventListener('mouseup', handleMouseUp);

                    saveColumnWidths(currentWidths);
                }}
            }});
        }}

        // Path tooltip functionality
        function initPathTooltips() {{
            const tooltip = document.getElementById('pathTooltip');

            document.addEventListener('mouseover', (e) => {{
                const pathCell = e.target.closest('.file-path');
                if (pathCell) {{
                    const fullPath = pathCell.textContent;
                    tooltip.textContent = fullPath;
                    tooltip.classList.add('visible');
                    updateTooltipPosition(e);
                }}
            }});

            document.addEventListener('mousemove', (e) => {{
                if (e.target.closest('.file-path')) {{
                    updateTooltipPosition(e);
                }}
            }});

            document.addEventListener('mouseout', (e) => {{
                if (!e.relatedTarget || !e.relatedTarget.closest('.file-path')) {{
                    tooltip.classList.remove('visible');
                }}
            }});

            function updateTooltipPosition(e) {{
                const offset = 15;
                tooltip.style.left = (e.pageX + offset) + 'px';
                tooltip.style.top = (e.pageY + offset) + 'px';
            }}
        }}

        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                const tabName = tab.dataset.tab;
                
                // Update active tab
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Update active content
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(tabName + 'Tab').classList.add('active');
            }});
        }});
        
        // Search functionality
        document.getElementById('searchBox').addEventListener('input', filterTable);
        document.getElementById('extensionFilter').addEventListener('change', filterTable);
        
        function filterTable() {{
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const extensionFilter = document.getElementById('extensionFilter').value;

            filteredData = tableData.filter(file => {{
                const matchesSearch = searchTerm === '' ||
                    file.name.toLowerCase().includes(searchTerm) ||
                    file.path.toLowerCase().includes(searchTerm) ||
                    file.directory.toLowerCase().includes(searchTerm);

                const matchesExtension = extensionFilter === '' || file.extension === extensionFilter;

                return matchesSearch && matchesExtension;
            }});

            renderTable();
        }}
        
        // Sort functionality
        document.querySelectorAll('th[data-column]').forEach(header => {{
            header.addEventListener('click', () => {{
                const column = header.dataset.column;
                
                if (currentSort.column === column) {{
                    currentSort.ascending = !currentSort.ascending;
                }} else {{
                    currentSort.column = column;
                    currentSort.ascending = true;
                }}
                
                sortTable(column, currentSort.ascending);
                updateSortHeaders();
                renderTable();
            }});
        }});
        
        function sortTable(column, ascending) {{
            filteredData.sort((a, b) => {{
                let valA = a[column];
                let valB = b[column];
                
                if (column === 'size') {{
                    valA = a.size_bytes;
                    valB = b.size_bytes;
                }}
                
                if (typeof valA === 'string') {{
                    valA = valA.toLowerCase();
                    valB = valB.toLowerCase();
                }}
                
                if (valA < valB) return ascending ? -1 : 1;
                if (valA > valB) return ascending ? 1 : -1;
                return 0;
            }});
        }}

        function renderTable() {{
            const tbody = document.getElementById('tableBody');
            const noResults = document.getElementById('noResults');
            const container = document.getElementById('tableContainer');
            const spacer = document.getElementById('tableSpacer');
            const viewport = document.getElementById('tableViewport');

            if (filteredData.length === 0) {{
                tbody.style.display = 'none';
                noResults.style.display = 'block';
                return;
            }}

            tbody.style.display = '';
            noResults.style.display = 'none';

            // Update result count
            document.getElementById('resultNumber').textContent = filteredData.length.toLocaleString();

            // Calculate virtual scroll parameters
            const scrollTop = container.scrollTop;
            const containerHeight = container.clientHeight;
            const totalHeight = filteredData.length * ROW_HEIGHT;

            // Set spacer height to create scrollable area
            spacer.style.height = totalHeight + 'px';

            // Calculate visible row indices
            virtualScroll.visibleRows = Math.ceil(containerHeight / ROW_HEIGHT);
            virtualScroll.startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_SIZE);
            virtualScroll.endIndex = Math.min(
                filteredData.length,
                virtualScroll.startIndex + virtualScroll.visibleRows + (BUFFER_SIZE * 2)
            );

            // Transform viewport to correct position
            viewport.style.transform = `translateY(${{virtualScroll.startIndex * ROW_HEIGHT}}px)`;

            // Render only visible rows
            const visibleData = filteredData.slice(virtualScroll.startIndex, virtualScroll.endIndex);

            tbody.innerHTML = visibleData.map(file => {{
                const sizePercent = maxFileSize > 0 ? (file.size_bytes / maxFileSize * 100).toFixed(1) : 0;
                return `
                <tr>
                    <td>
                        <div class="file-name">
                            <span class="file-icon">${{file.icon}}</span>
                            <span>${{escapeHtml(file.name)}}</span>
                        </div>
                    </td>
                    <td><span class="file-extension">${{escapeHtml(file.extension)}}</span></td>
                    <td class="file-path">${{escapeHtml(file.directory)}}</td>
                    <td>
                        <div class="size-cell">
                            <div class="size-bar-container">
                                <div class="size-bar" style="width: ${{sizePercent}}%"></div>
                            </div>
                            <span class="size-text">${{file.size_human}}</span>
                        </div>
                    </td>
                    <td class="modified">${{file.modified}}</td>
                    <td class="modified">${{file.created}}</td>
                </tr>
            `;
            }}).join('');
        }}

        // Add scroll event listener for virtual scrolling
        document.getElementById('tableContainer').addEventListener('scroll', throttle(renderTable, 16));

        // Progressive chunk loading function
        function loadNextChunk() {{
            if (chunksLoaded >= totalChunks) {{
                // All chunks loaded - hide overlay
                document.getElementById('loadingOverlay').classList.add('hidden');
                return;
            }}

            // Load current chunk
            const chunk = dataChunks[chunksLoaded];
            tableData.push(...chunk);
            chunksLoaded++;

            // Update progress
            const progress = Math.round((chunksLoaded / totalChunks) * 100);
            const progressFill = document.getElementById('loadingProgressFill');
            const loadingStats = document.getElementById('loadingStats');

            progressFill.style.width = progress + '%';
            progressFill.textContent = progress + '%';
            loadingStats.textContent = `Loaded ${{tableData.length.toLocaleString()}} of ${{totalFiles.toLocaleString()}} files...`;

            // Update maxFileSize incrementally (only check current chunk)
            if (chunk.length > 0) {{
                const chunkMax = Math.max(...chunk.map(f => f.size_bytes || 0));
                maxFileSize = Math.max(maxFileSize, chunkMax);
            }}

            // Update filtered data
            filteredData = [...tableData];

            // Initialize UI on first chunk
            if (chunksLoaded === 1) {{
                updateSortHeaders();
                initColumnResize();
                initPathTooltips();
            }}

            // Update table
            renderTable();

            // Load next chunk with small delay to keep UI responsive
            setTimeout(loadNextChunk, 50);
        }}

        // Start loading chunks
        if (totalChunks > 0) {{
            loadNextChunk();
        }} else {{
            // No data
            document.getElementById('loadingOverlay').classList.add('hidden');
            updateSortHeaders();
            renderTable();
            initColumnResize();
            initPathTooltips();
        }}
    </script>
</body>
</html>"""
    
    
    # Generate extension filter options
    sorted_extensions = sorted(extension_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    extension_options = generate_extension_options(extension_stats)
    
    # Generate statistics for top extensions by count
    top_ext_count = sorted_extensions[:10]
    max_count = top_ext_count[0][1]['count'] if top_ext_count else 1
    # Use list comprehension instead of loop with append
    top_extensions_by_count_html = [
        f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label">
                                <span>{get_file_icon(ext)}</span>
                                <span>{html_escape_builtin(ext)}</span>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 80px;">
                                <span class="stat-list-value">{stats['count']:,}</span>
                                <div class="progress-bar" style="width: 60px;">
                                    <div class="progress-fill" style="width: {stats['count'] / max_count * 100}%"></div>
                                </div>
                            </div>
                        </li>"""
        for ext, stats in top_ext_count
    ]
    
    # Generate statistics for top extensions by size
    top_ext_size = sorted(extension_stats.items(), key=lambda x: x[1]['size'], reverse=True)[:10]
    max_size = top_ext_size[0][1]['size'] if top_ext_size else 1
    # Use list comprehension instead of loop with append
    top_extensions_by_size_html = [
        f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label">
                                <span>{get_file_icon(ext)}</span>
                                <span>{html_escape_builtin(ext)}</span>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 100px;">
                                <span class="stat-list-value">{get_size_human_readable(stats['size'])}</span>
                                <div class="progress-bar" style="width: 80px;">
                                    <div class="progress-fill" style="width: {stats['size'] / max_size * 100}%"></div>
                                </div>
                            </div>
                        </li>"""
        for ext, stats in top_ext_size
    ]
    
    # Generate largest files
    sorted_by_size = sorted(files_data, key=lambda x: x['size_bytes'], reverse=True)[:10]
    # Use list comprehension instead of loop with append
    largest_files_html = [
        f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                                <span>{file_info['icon']}</span>
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {html_escape_builtin(file_info['name'])}
                                </span>
                            </div>
                            <span class="stat-list-value">{file_info['size_human']}</span>
                        </li>"""
        for file_info in sorted_by_size
    ]
    
    # Generate recently modified files
    sorted_by_date = sorted(files_data, key=lambda x: x['modified'], reverse=True)[:10]
    # Use list comprehension instead of loop with append
    recent_files_html = [
        f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                                <span>{file_info['icon']}</span>
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {html_escape_builtin(file_info['name'])}
                                </span>
                            </div>
                            <span class="stat-list-value" style="font-size: 11px;">{file_info['modified']}</span>
                        </li>"""
        for file_info in sorted_by_date
    ]

    # Generate recently created files
    sorted_by_created = sorted(files_data, key=lambda x: x['created'], reverse=True)[:10]
    recent_created_html = [
        f"""
                        <li class="stat-list-item">
                            <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                                <span>{file_info['icon']}</span>
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {html_escape_builtin(file_info['name'])}
                                </span>
                            </div>
                            <span class="stat-list-value" style="font-size: 11px;">{file_info['created']}</span>
                        </li>"""
        for file_info in sorted_by_created
    ]

    # Prepare data for chunked JSON (5000 files per chunk)
    CHUNK_SIZE = UIConfig.CHUNK_SIZE
    data_chunks = []

    for i in range(0, len(files_data), CHUNK_SIZE):
        chunk = files_data[i:i + CHUNK_SIZE]
        chunk_data = [{
            'name': f['name'],
            'extension': f['extension'],
            'path': f['path'],
            'relative_path': f['relative_path'],
            'directory': f['directory'],
            'size_human': f['size_human'],
            'size_bytes': f['size_bytes'],
            'modified': f['modified'],
            'created': f['created'],
            'icon': f['icon']
        } for f in chunk]
        data_chunks.append(chunk_data)

    # Convert chunks to JSON
    data_chunks_json = json.dumps(data_chunks)

    # Fill in template (cache Path object)
    total_file_count = len(files_data)
    html_content = html_template.format(
        root_name=get_directory_name(root_path),
        root_path=str(root_path),
        total_files=f"{total_file_count:,}",  # Formatted for display
        total_files_raw=total_file_count,  # Raw number for JavaScript
        total_size_human=get_size_human_readable(total_size),
        total_extensions=len(extension_stats),
        generated_date=datetime.now().strftime('%Y-%m-%d'),
        generated_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        extension_options=extension_options,
        table_rows='',  # Will be rendered by JavaScript
        data_chunks_json=data_chunks_json,
        chunk_size=UIConfig.CHUNK_SIZE,
        top_extensions_by_count=''.join(top_extensions_by_count_html),
        top_extensions_by_size=''.join(top_extensions_by_size_html),
        largest_files=''.join(largest_files_html),
        recent_files=''.join(recent_files_html),
        recent_created=''.join(recent_created_html),
        css_common=get_common_css(),
        css_inline_mode=get_common_css_inline_mode(),
        js_common=get_common_javascript()
    )

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✓ Archive created: {output_file}")
    print(f"  Open it in your browser to view the interactive archive.")

def generate_html_with_db(db_filename, root_path, total_size, extension_stats, output_file, db_size):
    """Generate interactive HTML file that queries SQLite database via sql.js"""

    # Database will be loaded via fetch (requires HTTP server)
    db_path = os.path.join(os.path.dirname(output_file) or '.', db_filename)

    # Count total files from extension stats
    total_files = sum(stats['count'] for stats in extension_stats.values())

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Index: {root_name}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.js"></script>
    <style>
{css_common}
{css_db_mode}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Directory Index</h1>
            <div style="opacity: 0.9; margin-top: 10px; font-size: 14px;">{root_path}</div>
            <div class="db-mode-badge">🗄️ Database Mode • {db_size_human}</div>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-label">Total Files</div>
                    <div class="stat-value">{total_files}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Size</div>
                    <div class="stat-value">{total_size_human}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">File Types</div>
                    <div class="stat-value">{total_extensions}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Generated</div>
                    <div class="stat-value">{generated_date}</div>
                </div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" data-tab="files">📋 All Files</button>
            <button class="tab" data-tab="stats">📊 Statistics</button>
        </div>

        <div id="filesTab" class="tab-content active">
            <div class="controls">
                <input type="text" id="searchBox" class="search-box" placeholder="🔍 Search files by name, path, or extension...">
                <div class="filter-group">
                    <span class="filter-label">Extension:</span>
                    <select id="extensionFilter">
                        <option value="">All Types</option>
                        {extension_options}
                    </select>
                </div>
            </div>

            <div class="result-count" id="resultCount">
                Showing <strong id="resultNumber">{total_files}</strong> files
            </div>

            <div class="table-container" id="tableContainer">
                <div class="table-spacer" id="tableSpacer"></div>
                <div class="table-viewport" id="tableViewport">
                    <table id="fileTable">
                        <thead>
                            <tr>
                                <th data-column="name">File Name</th>
                                <th data-column="extension">Type</th>
                                <th data-column="directory">Path</th>
                                <th data-column="size_bytes">Size</th>
                                <th data-column="modified">Modified</th>
                                <th data-column="created">Created</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">
                        </tbody>
                    </table>
                    <div id="noResults" class="no-results" style="display: none;">
                        No files match your search criteria.
                    </div>
                </div>
            </div>
        </div>

        <div id="statsTab" class="tab-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📊 Top 10 File Types by Count</h3>
                    <ul class="stat-list" id="topExtensionsByCount">
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>💾 Top 10 File Types by Size</h3>
                    <ul class="stat-list" id="topExtensionsBySize">
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>📁 Largest Files</h3>
                    <ul class="stat-list" id="largestFiles">
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>📅 Recently Modified</h3>
                    <ul class="stat-list" id="recentFiles">
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>🆕 Recently Created</h3>
                    <ul class="stat-list" id="recentCreatedFiles">
                    </ul>
                </div>
            </div>
        </div>

        <div class="footer">
            Generated on {generated_datetime} • {total_files} files • {total_size_human} • Database Mode
        </div>
    </div>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="loading-title">Loading Database...</div>
            <div class="loading-progress-bar">
                <div class="loading-progress-fill" id="loadingProgressFill">0%</div>
            </div>
            <div class="loading-stats" id="loadingStats">Initializing sql.js...</div>
        </div>
    </div>

    <script>
        let db = null;
        let currentSort = {{ column: 'name', ascending: true }};
        let currentFilter = {{ search: '', extension: '' }};
        let maxFileSize = 0;
        let totalFilteredCount = 0;

        // Virtual scrolling configuration
        const ROW_HEIGHT = 45;
        const BUFFER_SIZE = 10;
        const PAGE_SIZE = 100; // Number of rows to fetch at once

        let virtualScroll = {{
            startIndex: 0,
            endIndex: 0,
            visibleRows: 0
        }};

        // Common utility functions
{js_common}

        // Initialize sql.js and load database
        async function initDatabase() {{
            try {{
                // Update progress
                updateLoadingProgress(10, 'Loading sql.js library...');

                // Initialize SQL.js
                const SQL = await initSqlJs({{
                    locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/${{file}}`
                }});

                updateLoadingProgress(30, 'Fetching database file...');

                // Fetch the database file
                const response = await fetch('{db_filename}');
                if (!response.ok) {{
                    throw new Error('Failed to load database. Make sure to run this via HTTP server (python serve.py)');
                }}
                const arrayBuffer = await response.arrayBuffer();
                const bytes = new Uint8Array(arrayBuffer);

                updateLoadingProgress(70, 'Initializing database...');

                // Create database
                db = new SQL.Database(bytes);

                updateLoadingProgress(90, 'Loading statistics...');

                // Calculate max file size for progress bars
                const maxSizeResult = db.exec('SELECT MAX(size_bytes) as max_size FROM files');
                if (maxSizeResult.length > 0 && maxSizeResult[0].values.length > 0) {{
                    maxFileSize = maxSizeResult[0].values[0][0] || 0;
                }}

                updateLoadingProgress(100, 'Ready!');

                // Initialize UI
                await initializeUI();

                // Hide loading overlay
                document.getElementById('loadingOverlay').classList.add('hidden');

            }} catch (error) {{
                console.error('Failed to load database:', error);
                document.getElementById('loadingStats').textContent = 'Error loading database: ' + error.message;
            }}
        }}

        function updateLoadingProgress(percent, message) {{
            const fill = document.getElementById('loadingProgressFill');
            const stats = document.getElementById('loadingStats');
            fill.style.width = percent + '%';
            fill.textContent = percent + '%';
            stats.textContent = message;
        }}

        async function initializeUI() {{
            // Load statistics tab data
            loadStatistics();

            // Initial table render
            updateFilteredCount();
            renderTable();

            // Set up event listeners
            document.getElementById('searchBox').addEventListener('input', handleFilterChange);
            document.getElementById('extensionFilter').addEventListener('change', handleFilterChange);

            // Set up sort headers
            document.querySelectorAll('th[data-column]').forEach(header => {{
                header.addEventListener('click', () => {{
                    const column = header.dataset.column;
                    if (currentSort.column === column) {{
                        currentSort.ascending = !currentSort.ascending;
                    }} else {{
                        currentSort.column = column;
                        currentSort.ascending = true;
                    }}
                    updateSortHeaders();
                    renderTable();
                }});
            }});

            // Tab switching
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.addEventListener('click', () => {{
                    const tabName = tab.dataset.tab;
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    document.getElementById(tabName + 'Tab').classList.add('active');
                }});
            }});

            // Virtual scroll
            document.getElementById('tableContainer').addEventListener('scroll', throttle(renderTable, 16));

            updateSortHeaders();
        }}

        function handleFilterChange() {{
            currentFilter.search = document.getElementById('searchBox').value.toLowerCase();
            currentFilter.extension = document.getElementById('extensionFilter').value;
            updateFilteredCount();
            renderTable();
        }}

        function updateFilteredCount() {{
            let query = 'SELECT COUNT(*) as count FROM files WHERE 1=1';
            const params = [];

            if (currentFilter.search) {{
                query += ' AND (LOWER(name) LIKE ? OR LOWER(directory) LIKE ?)';
                params.push('%' + currentFilter.search + '%', '%' + currentFilter.search + '%');
            }}

            if (currentFilter.extension) {{
                query += ' AND extension = ?';
                params.push(currentFilter.extension);
            }}

            const result = db.exec(query, params);
            totalFilteredCount = result[0]?.values[0]?.[0] || 0;
            document.getElementById('resultNumber').textContent = totalFilteredCount.toLocaleString();
        }}

        function renderTable() {{
            const tbody = document.getElementById('tableBody');
            const noResults = document.getElementById('noResults');
            const container = document.getElementById('tableContainer');
            const spacer = document.getElementById('tableSpacer');
            const viewport = document.getElementById('tableViewport');

            if (totalFilteredCount === 0) {{
                tbody.style.display = 'none';
                noResults.style.display = 'block';
                return;
            }}

            tbody.style.display = '';
            noResults.style.display = 'none';

            // Calculate virtual scroll parameters
            const scrollTop = container.scrollTop;
            const containerHeight = container.clientHeight;
            const totalHeight = totalFilteredCount * ROW_HEIGHT;

            spacer.style.height = totalHeight + 'px';

            virtualScroll.visibleRows = Math.ceil(containerHeight / ROW_HEIGHT);
            virtualScroll.startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_SIZE);
            virtualScroll.endIndex = Math.min(
                totalFilteredCount,
                virtualScroll.startIndex + virtualScroll.visibleRows + (BUFFER_SIZE * 2)
            );

            viewport.style.transform = `translateY(${{virtualScroll.startIndex * ROW_HEIGHT}}px)`;

            // Build query
            let query = 'SELECT name, extension, directory, size_bytes, size_human, modified, created, icon FROM files WHERE 1=1';
            const params = [];

            if (currentFilter.search) {{
                query += ' AND (LOWER(name) LIKE ? OR LOWER(directory) LIKE ?)';
                params.push('%' + currentFilter.search + '%', '%' + currentFilter.search + '%');
            }}

            if (currentFilter.extension) {{
                query += ' AND extension = ?';
                params.push(currentFilter.extension);
            }}

            // Add sorting
            query += ` ORDER BY ${{currentSort.column}} ${{currentSort.ascending ? 'ASC' : 'DESC'}}`;

            // Add pagination
            query += ` LIMIT ? OFFSET ?`;
            params.push(virtualScroll.endIndex - virtualScroll.startIndex, virtualScroll.startIndex);

            // Execute query
            const result = db.exec(query, params);

            if (result.length === 0 || result[0].values.length === 0) {{
                tbody.innerHTML = '';
                return;
            }}

            // Render rows
            const rows = result[0].values;
            tbody.innerHTML = rows.map(row => {{
                const [name, extension, directory, size_bytes, size_human, modified, created, icon] = row;
                const sizePercent = maxFileSize > 0 ? (size_bytes / maxFileSize * 100).toFixed(1) : 0;
                return `
                <tr>
                    <td>
                        <div class="file-name">
                            <span class="file-icon">${{escapeHtml(icon)}}</span>
                            <span>${{escapeHtml(name)}}</span>
                        </div>
                    </td>
                    <td><span class="file-extension">${{escapeHtml(extension)}}</span></td>
                    <td class="file-path">${{escapeHtml(directory)}}</td>
                    <td>
                        <div class="size-cell">
                            <div class="size-bar-container">
                                <div class="size-bar" style="width: ${{sizePercent}}%"></div>
                            </div>
                            <span class="size-text">${{escapeHtml(size_human)}}</span>
                        </div>
                    </td>
                    <td class="modified">${{escapeHtml(modified)}}</td>
                    <td class="modified">${{escapeHtml(created)}}</td>
                </tr>
            `;
            }}).join('');
        }}

        function loadStatistics() {{
            // Top extensions by count
            const countResult = db.exec('SELECT extension, count, total_size FROM extension_stats ORDER BY count DESC LIMIT 10');
            if (countResult.length > 0) {{
                const maxCount = countResult[0].values[0]?.[1] || 1;
                document.getElementById('topExtensionsByCount').innerHTML = countResult[0].values.map(row => {{
                    const [ext, count, size] = row;
                    return `
                    <li class="stat-list-item">
                        <div class="stat-list-label">
                            <span>${{escapeHtml(ext)}}</span>
                        </div>
                        <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 80px;">
                            <span class="stat-list-value">${{count.toLocaleString()}}</span>
                            <div class="progress-bar" style="width: 60px;">
                                <div class="progress-fill" style="width: ${{count / maxCount * 100}}%"></div>
                            </div>
                        </div>
                    </li>`;
                }}).join('');
            }}

            // Top extensions by size
            const sizeResult = db.exec('SELECT extension, count, total_size FROM extension_stats ORDER BY total_size DESC LIMIT 10');
            if (sizeResult.length > 0) {{
                const maxSize = sizeResult[0].values[0]?.[2] || 1;
                document.getElementById('topExtensionsBySize').innerHTML = sizeResult[0].values.map(row => {{
                    const [ext, count, size] = row;
                    return `
                    <li class="stat-list-item">
                        <div class="stat-list-label">
                            <span>${{escapeHtml(ext)}}</span>
                        </div>
                        <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 100px;">
                            <span class="stat-list-value">${{formatBytes(size)}}</span>
                            <div class="progress-bar" style="width: 80px;">
                                <div class="progress-fill" style="width: ${{size / maxSize * 100}}%"></div>
                            </div>
                        </div>
                    </li>`;
                }}).join('');
            }}

            // Largest files
            const largestResult = db.exec('SELECT name, size_human, icon FROM files ORDER BY size_bytes DESC LIMIT 10');
            if (largestResult.length > 0) {{
                document.getElementById('largestFiles').innerHTML = largestResult[0].values.map(row => {{
                    const [name, size_human, icon] = row;
                    return `
                    <li class="stat-list-item">
                        <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                            <span>${{escapeHtml(icon)}}</span>
                            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                ${{escapeHtml(name)}}
                            </span>
                        </div>
                        <span class="stat-list-value">${{escapeHtml(size_human)}}</span>
                    </li>`;
                }}).join('');
            }}

            // Recently modified
            const recentResult = db.exec('SELECT name, modified, icon FROM files ORDER BY modified DESC LIMIT 10');
            if (recentResult.length > 0) {{
                document.getElementById('recentFiles').innerHTML = recentResult[0].values.map(row => {{
                    const [name, modified, icon] = row;
                    return `
                    <li class="stat-list-item">
                        <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                            <span>${{escapeHtml(icon)}}</span>
                            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                ${{escapeHtml(name)}}
                            </span>
                        </div>
                        <span class="stat-list-value" style="font-size: 11px;">${{escapeHtml(modified)}}</span>
                    </li>`;
                }}).join('');
            }}

            // Recently created
            const recentCreatedResult = db.exec('SELECT name, created, icon FROM files ORDER BY created DESC LIMIT 10');
            if (recentCreatedResult.length > 0) {{
                document.getElementById('recentCreatedFiles').innerHTML = recentCreatedResult[0].values.map(row => {{
                    const [name, created, icon] = row;
                    return `
                    <li class="stat-list-item">
                        <div class="stat-list-label" style="flex: 1; overflow: hidden;">
                            <span>${{escapeHtml(icon)}}</span>
                            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                ${{escapeHtml(name)}}
                            </span>
                        </div>
                        <span class="stat-list-value" style="font-size: 11px;">${{escapeHtml(created)}}</span>
                    </li>`;
                }}).join('');
            }}
        }}

        function formatBytes(bytes) {{
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let size = bytes;
            let unitIndex = 0;
            while (size >= 1024 && unitIndex < units.length - 1) {{
                size /= 1024;
                unitIndex++;
            }}
            return size.toFixed(2) + ' ' + units[unitIndex];
        }}

        // Start loading database on page load
        initDatabase();
    </script>
</body>
</html>"""

    # Generate extension filter options
    extension_options = generate_extension_options(extension_stats)

    # Fill in template
    total_file_count = calculate_total_files(extension_stats)
    html_content = html_template.format(
        root_name=get_directory_name(root_path),
        root_path=str(root_path),
        total_files=f"{total_file_count:,}",
        total_size_human=get_size_human_readable(total_size),
        total_extensions=len(extension_stats),
        generated_date=datetime.now().strftime('%Y-%m-%d, %H:%M:%S'),
        generated_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        extension_options=extension_options,
        db_filename=os.path.basename(db_path),
        db_size_human=get_size_human_readable(db_size),
        css_common=get_common_css(),
        css_db_mode=get_common_css_db_mode(),
        js_common=get_common_javascript()
    )

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✓ HTML viewer created: {output_file}")

def generate_server_script(output_dir, html_filename, port=ServerConfig.DEFAULT_PORT):
    """Generate a simple Python HTTP server script for viewing the database mode files"""

    server_script = f'''#!/usr/bin/env python3
"""
Simple HTTP Server for Directory Index Viewer
Serves the HTML file and database with proper CORS headers

Usage:
    python serve.py [port]

Default port: {port}
"""
import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else {port}

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers for local file access"""

    def end_headers(self):
        # Allow cross-origin requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        # Prevent caching for development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        # Customize log format
        sys.stderr.write("[%s] %s\\n" % (self.log_date_time_string(), format % args))

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    Handler = CORSRequestHandler

    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("=" * 60)
            print("Directory Index Viewer Server")
            print("=" * 60)
            print(f"Serving at http://localhost:{{PORT}}")
            print(f"\\nOpen in browser: http://localhost:{{PORT}}/{html_filename}")
            print("\\nPress Ctrl+C to stop the server")
            print("=" * 60)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\n\\nServer stopped.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {{PORT}} is already in use.")
            print(f"Try a different port: python serve.py <port_number>")
            sys.exit(1)
        else:
            raise
'''

    server_path = os.path.join(output_dir, 'serve.py')
    with open(server_path, 'w') as f:
        f.write(server_script)

    # Make executable on Unix-like systems
    try:
        os.chmod(server_path, 0o755)
    except (NotImplementedError, OSError):
        pass  # Windows doesn't support chmod or filesystem doesn't support permissions

    return server_path

def generate_launcher_scripts(macos_dir, windows_dir, html_filename, port=ServerConfig.DEFAULT_PORT):
    """Generate cross-platform launcher scripts for macOS and Windows"""

    # macOS .command script (zsh) - navigates to ../data/
    macos_script = f'''#!/bin/zsh
# Directory Index Viewer Launcher (macOS)
# Double-click this file to start the server and open the viewer

# Get the directory where this script is located and navigate to data folder
SCRIPT_DIR="${{0:a:h}}"
cd "$SCRIPT_DIR/../data"

echo "============================================================"
echo "Starting Directory Index Viewer"
echo "============================================================"
echo ""
echo "Working directory: $(pwd)"
echo ""

# Start the Python server in background
python3 serve.py {port} &
SERVER_PID=$!

echo "Server starting on http://localhost:{port}"
echo "Server PID: $SERVER_PID"
echo ""

# Wait for server to initialize
sleep 2

# Open in default browser
echo "Opening browser..."
open "http://localhost:{port}/{html_filename}"
echo ""
echo "Server is running. Close this window to stop the server."
echo "============================================================"
echo ""

# Wait for user to close terminal (keeps server running)
wait $SERVER_PID
'''

    # Windows .bat script - navigates to ..\data\
    windows_script = f'''@echo off
REM Directory Index Viewer Launcher (Windows)
REM Double-click this file to start the server and open the viewer

REM Get the directory where this script is located and navigate to data folder
cd /d "%~dp0..\\data"

echo ============================================================
echo Starting Directory Index Viewer
echo ============================================================
echo.
echo Working directory: %CD%
echo.

REM Start the Python server
echo Starting server on http://localhost:{port}
start /b python serve.py {port}

REM Wait for server to initialize
timeout /t 2 /nobreak >nul

REM Open in default browser
echo Opening browser...
start http://localhost:{port}/{html_filename}

echo.
echo Server is running. Press Ctrl+C or close this window to stop.
echo ============================================================
echo.

REM Keep window open and wait
pause
'''

    # Write macOS script to macOS directory
    macos_path = os.path.join(macos_dir, 'start.command')
    with open(macos_path, 'w', newline='\n') as f:
        f.write(macos_script)

    # Make executable on Unix-like systems
    try:
        os.chmod(macos_path, 0o755)
    except (NotImplementedError, OSError):
        pass  # Not supported on this platform/filesystem

    # Write Windows script to Windows directory
    windows_path = os.path.join(windows_dir, 'start.bat')
    with open(windows_path, 'w', newline='\r\n') as f:
        f.write(windows_script)

    return macos_path, windows_path

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Directory Structure Archiver - Generate interactive HTML archives of directory contents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python directory_indexer.py /Volumes/MyDrive
    → Creates /Volumes/MyDrive/index_MyDrive_YYYYMMDD_HHMMSS/...

  python directory_indexer.py /Volumes/MyDrive archive.html
    → Creates /Volumes/MyDrive/archive/archive.html

  python directory_indexer.py /Volumes/MyDrive /tmp/output.html
    → Creates /tmp/output.html (absolute file path)

  python directory_indexer.py /Volumes/MyDrive /tmp
    → Creates /tmp/index_MyDrive_YYYYMMDD_HHMMSS.html (absolute dir path)

  python directory_indexer.py /Volumes/MyDrive --extdb
    → Forces database mode for any size

Output Location:
  - Without output path: Creates subfolder in target directory
  - With relative path: Creates subfolder named after file in target directory
  - With absolute directory path: Generates file in that directory
  - With absolute file path: Uses exact path specified

Modes:
  - JSON mode (default for <200k files): Embeds data in HTML file
  - Database mode (auto for 200k+ files): Creates SQLite database + HTML viewer
    * Generates 3 files: .html, .db, and serve.py
    * Requires running HTTP server: python serve.py
    * Much more efficient for large datasets
  - Use --extdb to force database mode
  - Use --json to force JSON mode (not recommended for large datasets)
        """
    )

    parser.add_argument('directory', help='Directory path to archive')
    parser.add_argument('output', nargs='?', help='Output HTML file path (optional)')
    parser.add_argument('--extdb', action='store_true',
                       help='Force external database mode (creates .db + .html files)')
    parser.add_argument('--json', action='store_true',
                       help='Force JSON mode (embed data in HTML file)')

    # Parse arguments
    args = parser.parse_args()

    root_path = args.directory

    if not os.path.exists(root_path):
        print(f"Error: Directory '{root_path}' does not exist.")
        sys.exit(1)

    if not os.path.isdir(root_path):
        print(f"Error: '{root_path}' is not a directory.")
        sys.exit(1)

    # Determine output file
    if args.output:
        # User specified output path
        output_path = Path(args.output)
        if output_path.is_absolute():
            # Check if it's an existing directory
            if output_path.is_dir():
                # Generate filename inside the directory
                dir_name = Path(root_path).name or 'root'
                base_name = f"index_{dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                output_file = str(output_path / f"{base_name}.html")
            else:
                # Use as filename (file or non-existent path)
                output_file = str(output_path)
        else:
            # Relative path specified - create subfolder in target directory
            base_name = output_path.stem  # filename without extension
            output_dir = Path(root_path) / base_name
            output_dir.mkdir(exist_ok=True)
            output_file = str(output_dir / output_path.name)
    else:
        # Auto-generate filename and create subfolder
        dir_name = Path(root_path).name or 'root'
        base_name = f"index_{dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = Path(root_path) / base_name
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f"{base_name}.html")

    print("=" * 60)
    print("Directory Structure Archiver")
    print("=" * 60)
    print(f"Output location: {output_file}")
    print("=" * 60)

    # Scan directory
    files_data, total_size, extension_stats = scan_directory(root_path)

    if len(files_data) == 0:
        print("\nNo files found in the directory.")
        sys.exit(0)

    file_count = len(files_data)

    # Determine mode: database vs JSON
    use_database = args.extdb or (file_count > DatabaseConfig.FILE_COUNT_THRESHOLD and not args.json)

    if use_database:
        # Database mode
        if args.json:
            print("\nWarning: --json flag ignored due to large dataset size")

        print("\n" + "=" * 60)
        print("DATABASE MODE")
        print("=" * 60)
        print(f"  Files to archive: {file_count:,}")
        print(f"  Mode: External SQLite database")
        print(f"  Reason: " + ("--extdb flag specified" if args.extdb else f"File count ({file_count:,}) > 200,000"))
        print("=" * 60)

        # Create folder structure
        output_path_obj = Path(output_file)
        base_output_dir = output_path_obj.parent

        # Create subdirectories
        data_dir = base_output_dir / 'data'
        macos_dir = base_output_dir / 'macOS'
        windows_dir = base_output_dir / 'Windows'

        data_dir.mkdir(parents=True, exist_ok=True)
        macos_dir.mkdir(parents=True, exist_ok=True)
        windows_dir.mkdir(parents=True, exist_ok=True)

        # Update file paths to use data directory
        html_basename = output_path_obj.name
        html_file = data_dir / html_basename
        db_filename = str(data_dir / (output_path_obj.stem + '.db'))

        # Create database
        db_size = create_database(files_data, total_size, extension_stats, root_path, db_filename)

        # Generate HTML viewer
        print(f"\nGenerating HTML viewer...")
        generate_html_with_db(os.path.basename(db_filename), root_path, total_size,
                             extension_stats, str(html_file), db_size)

        # Generate server script (in data folder)
        server_script = generate_server_script(str(data_dir), html_basename)
        print(f"✓ Server script created: {server_script}")

        # Generate launcher scripts (in platform folders)
        macos_launcher, windows_launcher = generate_launcher_scripts(
            str(macos_dir), str(windows_dir), html_basename
        )
        print(f"✓ macOS launcher created: {macos_launcher}")
        print(f"✓ Windows launcher created: {windows_launcher}")

        print(f"\n{'=' * 60}")
        print(f"Summary:")
        print(f"  Files archived: {file_count:,}")
        print(f"  Total size: {get_size_human_readable(total_size)}")
        print(f"  Output folder: {base_output_dir}")
        print(f"    data/")
        print(f"      {html_basename}")
        print(f"      {os.path.basename(db_filename)} ({get_size_human_readable(db_size)})")
        print(f"      serve.py")
        print(f"    macOS/")
        print(f"      start.command")
        print(f"    Windows/")
        print(f"      start.bat")
        print(f"\nQuick start:")
        print(f"  macOS:   Double-click macOS/start.command")
        print(f"  Windows: Double-click Windows/start.bat")
        print(f"  Manual:  cd data && python serve.py")
        print(f"{'=' * 60}\n")

    else:
        # JSON mode (original behavior)
        print("\n" + "=" * 60)
        print("JSON MODE")
        print("=" * 60)
        print(f"  Files to archive: {file_count:,}")
        print(f"  Mode: Embedded JSON in HTML")
        print("=" * 60)

        # Warn about large datasets in JSON mode
        if file_count > DatabaseConfig.FILE_COUNT_THRESHOLD and args.json:
            print("\n" + "!" * 60)
            print("WARNING: Large dataset in JSON mode!")
            print(f"  Files to archive: {file_count:,}")
            print("\n  The HTML file will be very large and browsers may")
            print("  struggle to load it due to memory constraints.")
            print("\n  Recommendation:")
            print("  - Remove --json flag to use database mode automatically")
            print("  - Or use --extdb flag explicitly")
            print("!" * 60)

            response = input("\nContinue anyway? (y/n): ").strip().lower()
            if response != 'y':
                print("Aborted.")
                sys.exit(0)

        # Generate HTML with embedded JSON
        print(f"\nGenerating HTML archive...")
        generate_html(files_data, root_path, total_size, extension_stats, output_file)

        print(f"\n{'=' * 60}")
        print(f"Summary:")
        print(f"  Files archived: {file_count:,}")
        print(f"  Total size: {get_size_human_readable(total_size)}")
        print(f"  Output file: {output_file}")
        print(f"{'=' * 60}\n")

if __name__ == "__main__":
    main()
