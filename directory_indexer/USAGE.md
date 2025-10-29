# Directory Indexer - Usage Guide

A powerful tool for creating interactive HTML archives of directory structures with support for massive datasets.

## Table of Contents
- [Quick Start](#quick-start)
- [Operating Modes](#operating-modes)
- [Command-Line Options](#command-line-options)
- [Usage Examples](#usage-examples)
- [Output Structure](#output-structure)
- [Features](#features)
- [Performance Notes](#performance-notes)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Basic Usage
```bash
# Index a directory (auto-detects best mode)
python directory_indexer.py /path/to/directory

# Specify output location
python directory_indexer.py /path/to/directory output.html

# Force database mode for large datasets
python directory_indexer.py /path/to/directory --extdb
```

### Viewing the Archive

**JSON Mode (single file):**
- Just open the HTML file in any browser
- No server needed, works offline

**Database Mode (large datasets):**
- **macOS**: Double-click `macOS/start.command`
- **Windows**: Double-click `Windows/start.bat`
- **Manual**: `cd data && python serve.py`

---

## Operating Modes

### JSON Mode (Default for < 200k files)

**Best for:** Small to medium datasets (up to ~200,000 files)

**Characteristics:**
- Single self-contained HTML file
- All data embedded in the file
- Works anywhere, no server required
- Instant loading
- Easy to share and archive

**When to use:**
- Personal projects and smaller drives
- When you need a portable archive
- When simplicity is preferred

### Database Mode (Auto for 200k+ files)

**Best for:** Large datasets (200k - 1M+ files)

**Characteristics:**
- Separate SQLite database + HTML viewer
- Memory-efficient chunked loading
- Requires HTTP server to run
- Handles massive datasets smoothly
- Auto-generates launcher scripts

**When to use:**
- Enterprise/production environments
- Large external drives or network shares
- Archive servers with millions of files
- When performance is critical

---

## Command-Line Options

### Positional Arguments

```bash
directory       Directory path to archive (required)
output          Output HTML file path (optional)
```

### Optional Flags

```bash
--extdb         Force external database mode
                Creates .db + .html + serve.py files

--json          Force JSON mode (embed data in HTML)
                Not recommended for large datasets

--help, -h      Show help message and exit
```

---

## Usage Examples

### Example 1: Basic Directory Indexing
```bash
python directory_indexer.py /Volumes/MyDrive
```
**Output:**
```
/Volumes/MyDrive/index_MyDrive_20251028_143022/
├── index_MyDrive_20251028_143022.html (JSON mode, < 200k files)
```

### Example 2: Large Dataset (Database Mode)
```bash
python directory_indexer.py /Volumes/ProjectArchive --extdb
```
**Output:**
```
/Volumes/ProjectArchive/index_ProjectArchive_20251028_143022/
├── data/
│   ├── index.html          # Interactive viewer
│   ├── index.db            # SQLite database
│   └── serve.py            # HTTP server script
├── macOS/
│   └── start.command       # Double-click to launch (macOS)
└── Windows/
    └── start.bat           # Double-click to launch (Windows)
```

### Example 3: Specify Custom Output Location
```bash
# Output to specific file
python directory_indexer.py /Volumes/MyDrive /tmp/my_archive.html

# Output to specific directory
python directory_indexer.py /Volumes/MyDrive /tmp

# Relative path (creates subfolder in target directory)
python directory_indexer.py /Volumes/MyDrive archive.html
```

### Example 4: Force JSON Mode for Small Archive
```bash
python directory_indexer.py /Volumes/SmallProject --json
```

### Example 5: Index Subdirectory of Large Drive
```bash
# Instead of indexing entire 2TB drive, index specific subdirectory
python directory_indexer.py /Volumes/LargeDrive/ProjectFolder --extdb
```

---

## Output Structure

### JSON Mode Output
```
output_folder/
└── index_DriveName_20251028_143022.html    # Single file (2-500 MB typical)
```

### Database Mode Output
```
output_folder/
├── data/                          # Core application files
│   ├── index.html                 # Interactive web viewer (~300 KB)
│   ├── index.db                   # SQLite database (size varies)
│   └── serve.py                   # Python HTTP server script
│
├── macOS/                         # macOS launcher
│   └── start.command              # Double-click to run
│
└── Windows/                       # Windows launcher
    └── start.bat                  # Double-click to run
```

**Database Size Estimates:**
- 100k files: ~20-30 MB
- 500k files: ~100-150 MB
- 1M files: ~200-300 MB

---

## Features

### Interactive Interface

**Search & Filter:**
- Real-time search across file names and paths
- Filter by extension (e.g., show only `.mp4` files)
- Case-insensitive matching

**Sorting:**
- Sort by: Name, Path, Size, Extension, Date Modified
- Ascending/descending order
- Fast in-memory sorting for JSON mode
- Database-backed sorting for DB mode

**Visual Elements:**
- File type icons (📄 documents, 🎬 videos, 🖼️ images, etc.)
- Color-coded file sizes
- Responsive table layout
- Virtual scrolling (60fps smooth scrolling)

### Statistics Dashboard

**Overview:**
- Total file count
- Total size (human-readable)
- Directory depth
- Scan timestamp

**Top Extensions:**
- Most common file types by count
- Largest file types by total size
- Percentage breakdowns

**Largest Files:**
- Top 10 largest files
- Full paths and sizes
- Quick navigation links

**Recent Activity:**
- 10 most recently modified files
- Modification timestamps
- Useful for finding recent work

---

## Performance Notes

### JSON Mode Performance

**File Count Limits:**
- **Recommended:** Up to 100k files (50-100 MB HTML)
- **Maximum:** ~200k files (200-400 MB HTML)
- **Browser Limit:** Most browsers struggle beyond 500 MB HTML files

**Loading Times:**
- < 50k files: Instant
- 50k-100k files: 1-3 seconds
- 100k-200k files: 3-10 seconds
- > 200k files: Use database mode instead

**Memory Usage:**
- HTML file size × 2-3 in browser RAM
- 100k files ≈ 200-400 MB browser memory
- 200k files ≈ 600-800 MB browser memory

### Database Mode Performance

**Indexing Speed:**
- ~10,000-20,000 files/second (SSD)
- ~5,000-10,000 files/second (HDD)
- Progress updates every 1,000 files

**Runtime Performance:**
- Smooth 60fps scrolling (virtual rendering)
- ~100 rows loaded per query
- Search: Sub-second for most queries
- Sort: Instant (database-indexed)

**Scalability:**
- Tested with 1M+ files
- Database size grows linearly
- No practical upper limit (SQLite limitation: ~140 TB)

---

## Troubleshooting

### Issue: "Browser won't load the HTML file"

**Cause:** File too large for JSON mode

**Solution:**
```bash
# Re-run with database mode
python directory_indexer.py /path/to/directory --extdb
```

---

### Issue: "Failed to load database" error in browser

**Cause:** Database mode requires HTTP server

**Solution:**
```bash
# Start the server
cd data
python serve.py

# Or use launcher scripts
# macOS: Double-click macOS/start.command
# Windows: Double-click Windows/start.bat
```

---

### Issue: "Address already in use" when starting server

**Cause:** Port 8000 already in use

**Solution:**
```bash
# Use a different port
cd data
python serve.py 8080  # Try port 8080 instead

# Or kill the existing server
lsof -ti:8000 | xargs kill  # macOS/Linux
```

---

### Issue: Indexing is very slow

**Causes & Solutions:**

1. **Network drive over slow connection**
   ```bash
   # Copy directory to local disk first, then index
   rsync -av /network/drive /local/temp
   python directory_indexer.py /local/temp
   ```

2. **Many small files on HDD**
   - Expected behavior (disk I/O bound)
   - Consider SSD if frequently indexing

3. **Permission issues slowing scan**
   - Check for inaccessible folders
   - Run with appropriate permissions

---

### Issue: Database mode produces huge .db file

**Expected Behavior:** Database size proportional to file count

**Typical Sizes:**
- 100k files: 20-30 MB
- 500k files: 100-150 MB
- 1M files: 200-300 MB

**If excessively large:**
- Check for very long file paths (> 1000 chars)
- Check for unusual characters in filenames

---

### Issue: Search not working

**JSON Mode:**
- JavaScript must be enabled in browser
- Clear browser cache and reload

**Database Mode:**
- Ensure server is running
- Check browser console for errors (F12)
- Verify database file exists in same folder

---

### Issue: Icons not displaying

**Cause:** Browser font rendering issue

**Solution:**
- Use modern browser (Chrome, Firefox, Safari, Edge)
- Update browser to latest version
- Enable emoji support in browser settings

---

## Advanced Usage

### Scripting and Automation

```bash
#!/bin/bash
# Index multiple drives automatically

for drive in /Volumes/Drive*; do
    echo "Indexing $drive..."
    python directory_indexer.py "$drive" --extdb
done
```

### Scheduled Indexing (macOS)

Create a LaunchAgent for periodic indexing:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.directory_indexer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/directory_indexer.py</string>
        <string>/Volumes/MyDrive</string>
        <string>--extdb</string>
    </array>
    <key>StartInterval</key>
    <integer>86400</integer>  <!-- Run daily -->
</dict>
</plist>
```

Save to `~/Library/LaunchAgents/com.user.directory_indexer.plist`

---

## Tips & Best Practices

### For Best Performance

1. **Choose the right mode:**
   - < 100k files: JSON mode (default)
   - 100k-200k files: Either works, JSON is simpler
   - > 200k files: Database mode (automatic)

2. **Index locally when possible:**
   - Network drives: Copy → Index → Delete copy
   - Cloud storage: Download → Index → Upload result

3. **Organize large archives:**
   - Index subdirectories separately
   - Better for navigation and loading
   - Example: `/ProjectArchive/2024/` vs entire `/ProjectArchive/`

4. **Regular maintenance:**
   - Re-index when directory structure changes significantly
   - Keep archives dated for version tracking
   - Clean up old indexes periodically

### For Sharing

**JSON Mode:**
- Perfect for email attachments
- Upload to cloud storage and share link
- No setup required for recipients

**Database Mode:**
- Zip the entire output folder
- Recipients extract and run launcher
- Include brief instructions (double-click start.command/start.bat)

---

## System Requirements

**Python:** 3.7+

**Dependencies:** None (uses only Python standard library)

**Browser Support:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Disk Space:**
- JSON mode: 2-3× file count in bytes
- Database mode: ~300 bytes per file

**Memory:**
- Indexing: ~100-500 MB RAM
- Viewing (JSON): 2-3× HTML file size
- Viewing (DB): ~100-200 MB RAM

---

## License & Support

This tool is part of the Post Production Utilities toolkit.

For issues, questions, or contributions, please refer to the main project repository.
