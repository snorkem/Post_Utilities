#!/usr/bin/env python3
"""
Directory Structure Archiver
Generates an interactive HTML file showing all files in a directory tree
with names, full paths, sizes, and extensions.

Features:
- Virtual scrolling for smooth performance
- Progressive chunk loading (5000 files at a time)
- Sortable columns, search, and filtering
- Adjustable column widths
- File statistics and visualizations

Performance Notes:
- Optimized for datasets up to ~200,000 files
- For datasets with 200K+ files, browsers may struggle with memory constraints
- For very large datasets (1M+ files), consider archiving subdirectories separately
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html import escape as html_escape_builtin

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

                files_data.append({
                    'name': filename,
                    'path': str(filepath),
                    'relative_path': str(filepath.relative_to(root_path)),
                    'directory': str(parent_dir.relative_to(root_path)),
                    'size_bytes': size_bytes,
                    'size_human': get_size(size_bytes),
                    'extension': extension,
                    'icon': get_icon(extension),
                    'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

                total_size += size_bytes

                # Track extension statistics (no more dict membership check needed)
                extension_stats[extension]['count'] += 1
                extension_stats[extension]['size'] += size_bytes

                if len(files_data) % 1000 == 0:
                    print(f"  Processed {len(files_data)} files...")

            except (PermissionError, OSError):
                error_count += 1
                continue

    print(f"✓ Scan complete: {len(files_data)} files found")
    if error_count > 0:
        print(f"  ({error_count} files skipped due to permission errors)")

    # Convert defaultdict back to regular dict for compatibility
    return files_data, total_size, dict(extension_stats)

def generate_html(files_data, root_path, total_size, extension_stats, output_file):
    """Generate interactive HTML file"""
    
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Index: {root_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            background: #f5f5f5;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            margin-bottom: 10px;
            font-size: 28px;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .stat-label {{
            opacity: 0.9;
            margin-bottom: 5px;
            font-size: 13px;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        
        .tabs {{
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .tab {{
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}
        
        .tab:hover {{
            background: #e9ecef;
            color: #333;
        }}
        
        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
            background: white;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .controls {{
            padding: 20px 30px;
            background: #fafafa;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 300px;
            padding: 12px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 6px;
            outline: none;
        }}
        
        .search-box:focus {{
            border-color: #667eea;
        }}
        
        .filter-group {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .filter-label {{
            font-size: 13px;
            color: #666;
            font-weight: 500;
        }}
        
        select {{
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            outline: none;
        }}
        
        select:focus {{
            border-color: #667eea;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}

        /* Column width controls */
        th:nth-child(1) {{ width: var(--col-name-width, 20%); }} /* File Name */
        th:nth-child(2) {{ width: var(--col-type-width, 8%); }}  /* Type */
        th:nth-child(3) {{ width: var(--col-path-width, 45%); }} /* Path */
        th:nth-child(4) {{ width: var(--col-size-width, 15%); }} /* Size */
        th:nth-child(5) {{ width: var(--col-modified-width, 12%); }} /* Modified */

        th {{
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
        }}
        
        th:hover {{
            background: #e9ecef;
        }}
        
        th::after {{
            content: ' ↕';
            opacity: 0.3;
            font-size: 12px;
        }}
        
        th.sort-asc::after {{
            content: ' ↑';
            opacity: 1;
        }}
        
        th.sort-desc::after {{
            content: ' ↓';
            opacity: 1;
        }}
        
        /* Column resize handles */
        .resize-handle {{
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            width: 8px;
            cursor: col-resize;
            z-index: 20;
            background: transparent;
        }}

        .resize-handle:hover {{
            background: rgba(102, 126, 234, 0.3);
        }}

        .resize-handle.resizing {{
            background: rgba(102, 126, 234, 0.5);
        }}

        th {{
            position: relative;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 13px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .file-icon {{
            font-size: 18px;
            margin-right: 8px;
        }}
        
        .file-name {{
            font-weight: 500;
            color: #333;
            display: flex;
            align-items: center;
        }}
        
        .file-path {{
            color: #666;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            word-break: break-all;
        }}
        
        .file-extension {{
            display: inline-block;
            padding: 3px 10px;
            background: #e3f2fd;
            color: #1976d2;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .size-cell {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .size-bar-container {{
            flex: 1;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            min-width: 50px;
            max-width: 100px;
        }}
        
        .size-bar {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }}
        
        .size-text {{
            text-align: right;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #555;
            white-space: nowrap;
            min-width: 70px;
        }}
        
        .modified {{
            color: #666;
            font-size: 12px;
            white-space: nowrap;
        }}
        
        .no-results {{
            padding: 40px;
            text-align: center;
            color: #999;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        
        .stat-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
        }}
        
        .stat-card h3 {{
            font-size: 16px;
            margin-bottom: 15px;
            color: #333;
        }}
        
        .stat-list {{
            list-style: none;
        }}
        
        .stat-list-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .stat-list-item:last-child {{
            border-bottom: none;
        }}
        
        .stat-list-label {{
            font-size: 13px;
            color: #666;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .stat-list-value {{
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }}
        
        .progress-bar {{
            height: 6px;
            background: #e0e0e0;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 5px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }}
        
        .footer {{
            padding: 20px 30px;
            text-align: center;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}
        
        .result-count {{
            padding: 10px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            font-size: 13px;
            color: #666;
        }}

        /* Settings Panel */
        .settings-panel {{
            padding: 20px 30px;
            background: #fafafa;
            border-bottom: 1px solid #e0e0e0;
            display: none;
        }}

        .settings-panel.visible {{
            display: block;
        }}

        .settings-toggle {{
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: background 0.3s;
        }}

        .settings-toggle:hover {{
            background: #5568d3;
        }}

        .settings-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }}

        .setting-item {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .setting-label {{
            font-size: 13px;
            font-weight: 600;
            color: #333;
        }}

        .setting-input {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .setting-input input[type="range"] {{
            flex: 1;
            cursor: pointer;
        }}

        .setting-value {{
            min-width: 50px;
            text-align: right;
            font-size: 13px;
            color: #666;
            font-family: 'Monaco', 'Courier New', monospace;
        }}

        .preset-buttons {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}

        .preset-btn {{
            padding: 8px 16px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .preset-btn:hover {{
            border-color: #667eea;
            color: #667eea;
        }}

        .preset-btn.reset {{
            background: #ff6b6b;
            color: white;
            border-color: #ff6b6b;
        }}

        .preset-btn.reset:hover {{
            background: #ee5a52;
            border-color: #ee5a52;
        }}

        .path-tooltip {{
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
        }}

        .path-tooltip.visible {{
            display: block;
        }}

        /* Virtual scrolling styles */
        .table-container {{
            position: relative;
            height: 600px;
            overflow-y: auto;
            overflow-x: auto;
        }}

        .table-spacer {{
            position: relative;
            width: 100%;
        }}

        .table-viewport {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            will-change: transform;
        }}

        /* Loading progress bar */
        .loading-overlay {{
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
        }}

        .loading-overlay.hidden {{
            display: none;
        }}

        .loading-content {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            min-width: 400px;
        }}

        .loading-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }}

        .loading-progress-bar {{
            height: 24px;
            background: #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 10px;
        }}

        .loading-progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: 600;
        }}

        .loading-stats {{
            font-size: 13px;
            color: #666;
            text-align: center;
        }}
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
        const CHUNK_SIZE = 5000;

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
        
        function updateSortHeaders() {{
            document.querySelectorAll('th[data-column]').forEach(header => {{
                header.classList.remove('sort-asc', 'sort-desc');
                if (header.dataset.column === currentSort.column) {{
                    header.classList.add(currentSort.ascending ? 'sort-asc' : 'sort-desc');
                }}
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
                </tr>
            `;
            }}).join('');
        }}

        // Throttle scroll events for performance
        function throttle(func, limit) {{
            let inThrottle;
            return function() {{
                const args = arguments;
                const context = this;
                if (!inThrottle) {{
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }}
            }}
        }}

        // Add scroll event listener for virtual scrolling
        document.getElementById('tableContainer').addEventListener('scroll', throttle(renderTable, 16));

        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

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
    # Use list comprehension with join for better performance
    extension_options = '\n'.join(
        f'<option value="{html_escape_builtin(ext)}">{html_escape_builtin(ext)} ({stats["count"]} files)</option>'
        for ext, stats in sorted_extensions
    )
    
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
    
    # Prepare data for chunked JSON (5000 files per chunk)
    CHUNK_SIZE = 5000
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
            'icon': f['icon']
        } for f in chunk]
        data_chunks.append(chunk_data)

    # Convert chunks to JSON
    data_chunks_json = json.dumps(data_chunks)

    # Fill in template (cache Path object)
    root_path_obj = Path(root_path)
    total_file_count = len(files_data)
    html_content = html_template.format(
        root_name=root_path_obj.name or 'root',
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
        top_extensions_by_count=''.join(top_extensions_by_count_html),
        top_extensions_by_size=''.join(top_extensions_by_size_html),
        largest_files=''.join(largest_files_html),
        recent_files=''.join(recent_files_html)
    )

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✓ Archive created: {output_file}")
    print(f"  Open it in your browser to view the interactive archive.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python directory_indexer.py <directory_path> [output_file.html]")
        print("\nExample:")
        print("  python directory_indexer.py /Volumes/MyDrive archive.html")
        sys.exit(1)

    root_path = sys.argv[1]

    if not os.path.exists(root_path):
        print(f"Error: Directory '{root_path}' does not exist.")
        sys.exit(1)

    if not os.path.isdir(root_path):
        print(f"Error: '{root_path}' is not a directory.")
        sys.exit(1)

    # Determine output file
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        dir_name = Path(root_path).name or 'root'
        output_file = f"index_{dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    print("=" * 60)
    print("Directory Structure Archiver")
    print("=" * 60)

    # Scan directory
    files_data, total_size, extension_stats = scan_directory(root_path)

    if len(files_data) == 0:
        print("\nNo files found in the directory.")
        sys.exit(0)

    # Warn about large datasets
    if len(files_data) > 200000:
        print("\n" + "!" * 60)
        print("WARNING: Large dataset detected!")
        print(f"  Files to archive: {len(files_data):,}")
        print("\n  This tool works best with up to ~200,000 files.")
        print("  With 200K+ files, the HTML file may be very large and")
        print("  browsers may struggle to load it due to memory constraints.")
        print("\n  Recommendation:")
        print("  - Consider archiving subdirectories separately")
        print("  - Or use external database solutions for very large datasets")
        print("!" * 60)

        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(0)

    # Generate HTML
    print(f"\nGenerating HTML archive...")
    generate_html(files_data, root_path, total_size, extension_stats, output_file)

    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Files archived: {len(files_data):,}")
    print(f"  Total size: {get_size_human_readable(total_size)}")
    print(f"  Output file: {output_file}")
    print(f"{'=' * 60}\n")

if __name__ == "__main__":
    main()
