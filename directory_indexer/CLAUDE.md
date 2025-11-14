# Update this file whenever initiating a git commit (Required)

## Project Summary

**Directory Indexer** is a powerful Python tool for creating interactive HTML archives of directory structures. It's designed to handle datasets ranging from small personal projects to massive enterprise archives with millions of files.

### Purpose

This tool scans a directory tree and generates a self-contained interactive web archive that allows users to:
- Browse the complete file structure offline
- Search and filter files by name, extension, or path
- Sort by name, size, date, or extension
- View comprehensive statistics and analytics
- Export/share the archive as a portable HTML file or database

### Key Features

**Two Operating Modes:**
1. **JSON Mode** (default for <200k files)
   - Single self-contained HTML file
   - All data embedded inline
   - Works anywhere, no server required
   - Perfect for sharing and archiving

2. **Database Mode** (auto-enabled for 200k+ files)
   - Separate SQLite database + HTML viewer
   - Memory-efficient chunked loading
   - Handles 1M+ files smoothly
   - Includes launcher scripts for easy deployment

**Interactive Interface:**
- Real-time search across file names and paths
- Filter by file extension
- Multi-column sorting (name, path, size, extension, date)
- Virtual scrolling for 60fps performance
- File type icons with visual indicators
- Color-coded file sizes
- Responsive design

**Analytics Dashboard:**
- Total file count and size statistics
- Top extensions by count and size
- Largest files list
- Most recently modified files
- Directory depth analysis
- Scan timestamp tracking

### Architecture

**Core Components:**
- `scan_directory()`: Recursively scans directory and collects file metadata
- `build_directory_tree()`: Constructs hierarchical directory structure
- `generate_html()`: Creates JSON mode HTML with embedded data
- `generate_html_with_db()`: Creates database mode HTML viewer
- `create_database()`: Builds SQLite database for large datasets
- Configuration classes for UI, Database, Progress, Server, Display, and Statistics

**Technology Stack:**
- Pure Python 3.7+ (standard library only - no external dependencies)
- SQLite for database mode
- JavaScript for interactive frontend
- HTML5/CSS3 for responsive UI
- Virtual DOM rendering for performance

### Performance Characteristics

**Indexing Speed:**
- 10,000-20,000 files/second on SSD
- 5,000-10,000 files/second on HDD
- Progress updates every 1,000 files

**Scalability:**
- JSON mode: Up to 200k files (200-400 MB HTML)
- Database mode: Tested with 1M+ files
- Database size: ~300 bytes per file
- No practical upper limit in DB mode

**Runtime Performance:**
- Smooth 60fps scrolling via virtual rendering
- Sub-second search responses
- Instant database-backed sorting
- 100 rows per query in DB mode

### Usage

```bash
# Basic usage (auto-detects mode)
python directory_indexer.py /path/to/directory

# Force database mode
python directory_indexer.py /path/to/directory --extdb

# Custom output location
python directory_indexer.py /path/to/directory output.html
```

**Database Mode Viewing:**
- macOS: Double-click `macOS/start.command`
- Windows: Double-click `Windows/start.bat`
- Manual: `cd data && python serve.py`

### File Structure

**REFACTORED (November 2024):**
The project has been refactored from a single 5,000+ line monolithic file into a modular, object-oriented architecture:

```
directory_indexer/
├── directory_indexer.py          # Main entry point (316 lines)
├── src/
│   ├── config/settings.py        # Configuration classes
│   ├── core/
│   │   ├── scanner.py            # DirectoryScanner class
│   │   ├── database.py           # DatabaseManager class
│   │   └── tree_builder.py       # DirectoryTreeBuilder class
│   ├── models/
│   │   ├── file_info.py          # FileInfo dataclass
│   │   └── scan_result.py        # ScanResult dataclass
│   ├── utils/
│   │   ├── formatting.py         # Formatting utilities
│   │   └── path_resolver.py      # Path resolution
│   └── generators/
│       ├── templates.py          # Template loader
│       └── legacy_generators.py  # HTML/JS generation
├── templates/common/             # CSS templates
└── tests/fixtures/               # Test data
```

**Key Benefits:**
- Modular architecture with clear separation of concerns
- Object-oriented design following SOLID principles
- Type hints throughout
- Comprehensive docstrings
- 100% backward compatible
- Easy to maintain and extend

See `REFACTORING_COMPLETE.md` for full details.

**Output Structure (JSON Mode):**
```
output_folder/
└── index_DriveName_20251028_143022.html
```

**Output Structure (Database Mode):**
```
output_folder/
├── data/
│   ├── index.html (viewer)
│   ├── index.db (SQLite database)
│   └── serve.py (HTTP server)
├── macOS/
│   └── start.command (launcher)
└── Windows/
    └── start.bat (launcher)
```

### Design Philosophy

- **Zero Dependencies**: Uses only Python standard library for maximum portability
- **Performance First**: Optimized for handling massive datasets efficiently
- **User-Friendly**: Automatic mode selection and launcher scripts
- **Offline Capable**: JSON mode works without any server or network
- **Shareable**: Easy to distribute and use by non-technical users
- **Future-Proof**: Self-contained archives remain accessible indefinitely

### Use Cases

- Archiving project directories before deletion
- Creating searchable catalogs of media libraries
- Documenting large file servers or NAS systems
- Tracking backups and external drive contents
- Sharing directory listings with clients/collaborators
- Compliance and audit trail documentation
- Digital asset management and inventory

### Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Part of Post Production Utilities

This tool is part of a larger toolkit for post-production workflows, alongside:
- L3rds generator (subtitle/lower-third graphics)
- ALE converter (Avid Log Exchange tools)
- File rename utilities
- Media reporting tools

