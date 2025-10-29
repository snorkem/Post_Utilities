# File Search and Copy Utility - Usage Guide

A powerful tool for searching and copying files across multiple directories with support for EDL parsing, glob patterns, and regex matching. Available in both CLI and GUI versions.

**Version:** 3.2 (CLI) / 1.1 (GUI)

## Table of Contents
- [Overview](#overview)
- [CLI Version](#cli-version)
- [GUI Version](#gui-version)
- [Features](#features)
- [Usage Examples](#usage-examples)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

## Overview

### What It Does

This utility searches for files across multiple source directories and copies them to destination directories. It's particularly useful for:

- **Post-Production Workflows:** Extract files referenced in EDL (Edit Decision List) files
- **Asset Management:** Copy files matching specific patterns from large media libraries
- **Batch Operations:** Process hundreds or thousands of files automatically
- **Archive Restoration:** Locate and copy files from backup drives

### Key Features

✅ **Multiple Search Modes:**
- Simple filename matching
- Glob patterns (`*.mov`, `file_[0-9].mp4`)
- Regular expressions
- EDL file parsing (automatic source file extraction)

✅ **Robust File Handling:**
- Multiple source directories (searches all)
- Multiple destination directories (copies to all)
- Automatic duplicate handling
- File verification (size + hash comparison)
- Size filtering (skip large files)

✅ **Safety Features:**
- Dry-run mode (preview without copying)
- Detailed logging (main log + missing files log)
- Progress tracking with ETA
- Graceful error handling

✅ **Two Interfaces:**
- **CLI:** Fast, scriptable, automation-friendly
- **GUI:** User-friendly, real-time progress, drag-and-drop

---

## CLI Version

### Installation & Requirements

```bash
# Required Python version
python3 --version  # 3.7+

# Install dependencies
pip install xxhash chardet
```

### Basic Syntax

```bash
python copy_file_list.py -s SOURCE_DIRS -d DEST_DIRS -l LOG_FILE \
    (-f FILE_LIST | --edl EDL_FILE) [OPTIONS]
```

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `-s, --source` | Source directory to search (can be repeated) | `-s /media/drive1 -s /media/drive2` |
| `-d, --dest` | Destination directory (can be repeated) | `-d /output -d /backup` |
| `-l, --log` | Log file path (will append if exists) | `-l operations.log` |
| `-f, --file-list` | Text file with filenames/patterns (one per line) | `-f files.txt` |
| `--edl` | EDL file to parse for source filenames | `--edl project.edl` |

**Note:** You must specify **either** `-f` or `--edl`, not both.

### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-p, --progress` | Show progress bar during copy operations | Off |
| `-r, --regex` | Use regex instead of glob patterns | Glob |
| `-m, --max-size` | Skip files larger than N MB | No limit |
| `-x, --exclude` | File with exclude patterns (one per line) | None |
| `-n, --dry-run` | Preview without copying | Off |
| `--first-match-only` | Use only the first match found per pattern | Off |
| `--verify` | Verify copied files (size + hash check) | Off |
| `--debug` | Enable detailed debug logging | Off |

### Log Files

The utility creates two log files:

1. **Main Log** (`operations.log`):
   - All operations and results
   - Copy successes and failures
   - Timestamps and statistics

2. **Missing Files Log** (`operations.log.missing.txt`):
   - Files that couldn't be found
   - Quick reference for troubleshooting
   - One filename per line

---

## GUI Version

### Installation & Requirements

```bash
# Install GUI dependencies
pip install PyQt5 xxhash chardet

# Launch the GUI
python copy_file_list_gui.py
```

### GUI Interface Overview

The GUI is organized into tabs for easy navigation:

#### 1. **Source/Destination Tab**

**Source Directories:**
- Click "Add Source Directory" to add search locations
- Can add multiple source directories
- Files will be searched across all sources
- Remove directories with the "Remove" button

**Destination Directory:**
- Click "Select Destination Directory"
- Files will be copied to this location
- Subdirectories will be created if needed

**Input Method:**
- **File List:** Select a text file with filenames/patterns
- **EDL File:** Select an EDL file for automatic parsing

#### 2. **Options Tab**

**Search Options:**
- ☑️ **Use Regular Expressions:** Enable regex mode (default: glob)
- ☑️ **First Match Only:** Stop after finding first match per pattern
- ☑️ **Verify Files:** Check copied files with hash comparison

**Size Limits:**
- **Max File Size (MB):** Skip files larger than this (0 = no limit)

**Advanced:**
- **Exclude File:** Text file with patterns to skip
- ☑️ **Dry Run:** Preview without copying
- ☑️ **Debug Mode:** Detailed logging
- ☑️ **Show Progress:** Enable progress bar

#### 3. **Run Tab**

**Start Operation:**
- Click "Start" to begin
- Real-time console output
- Progress bar with current/total files
- Currently processing file shown

**Control Buttons:**
- **Start:** Begin file copy operation
- **Stop:** Terminate current operation
- **Clear Console:** Clear output display

**Output Display:**
- Color-coded messages (green = success, red = error, orange = warning)
- Scrollable console output
- Auto-saves to log file

---

## Features

### 1. EDL File Parsing

**What is an EDL?**
An Edit Decision List is a text file used in video editing that contains information about clips, timecodes, and source files.

**Automatic Source Extraction:**
The utility automatically parses EDL files and extracts source filenames from lines like:
```
* SOURCE FILE: clip_001.mov
* FROM CLIP NAME: interview_take3.mp4
```

**Benefits:**
- No need to manually create file lists
- Automatically extracts all referenced media
- Case-insensitive matching (finds `Clip001.mov` if EDL has `clip001.MOV`)

**Example:**
```bash
# Parse EDL and copy all referenced files
python copy_file_list.py \
    -s /media/raw_footage \
    -d /media/project_files \
    --edl final_cut.edl \
    -l copy_log.txt
```

### 2. Pattern Matching

#### Glob Patterns (Default)

Simple wildcards for flexible matching:

| Pattern | Matches | Example |
|---------|---------|---------|
| `*` | Any characters | `*.mov` matches all MOV files |
| `?` | Single character | `file_?.mp4` matches `file_1.mp4`, `file_A.mp4` |
| `[abc]` | Character set | `file_[123].mp4` matches `file_1.mp4`, `file_2.mp4` |
| `[0-9]` | Character range | `clip_[0-9][0-9].mov` matches `clip_00.mov` to `clip_99.mov` |

**Example file list** (`patterns.txt`):
```
*.mp4
*.mov
interview_*.wav
scene_[0-9][0-9]_take*.mov
```

#### Regular Expressions

More powerful pattern matching with `-r` flag:

| Pattern | Matches |
|---------|---------|
| `^.*\.mp4$` | All MP4 files |
| `^interview_\d+\.mov$` | `interview_001.mov`, `interview_002.mov`, etc. |
| `^scene_\d{2}_take\d+\.` | `scene_01_take1.mov`, `scene_05_take12.mp4` |
| `(clip\|scene)_\d+` | Files starting with "clip" or "scene" followed by numbers |

**Example regex file** (`regex_patterns.txt`):
```
^.*\.mov$
^interview_\d+_[a-zA-Z]+\.wav$
^B00[0-9]C[0-9]{3}.*\.mxf$
```

### 3. Multiple Source/Destination Directories

**Multiple Sources:**
Search across multiple drives or folders:
```bash
python copy_file_list.py \
    -s /Volumes/Drive1 \
    -s /Volumes/Drive2 \
    -s /network/archive \
    -d /output \
    -f files.txt -l log.txt
```

**Multiple Destinations:**
Copy to multiple locations simultaneously:
```bash
python copy_file_list.py \
    -s /media/raw \
    -d /project/media \
    -d /backup/media \
    -f files.txt -l log.txt
```

### 4. Dry-Run Mode

Preview operations without copying:

```bash
python copy_file_list.py \
    -s /source \
    -d /dest \
    -f files.txt \
    -l log.txt \
    -n  # Dry run flag
```

**Output shows:**
```
WOULD COPY: /source/file1.mp4 → /dest/file1.mp4
WOULD COPY: /source/file2.mov → /dest/file2.mov
MISSING: file3.wav (not found in any source directory)

Dry run completed. No files were copied.
```

### 5. File Verification

Ensure copied files are identical to originals:

```bash
python copy_file_list.py \
    -s /source \
    -d /dest \
    -f files.txt \
    -l log.txt \
    --verify  # Enable verification
```

**Verification Process:**
1. Copy file to destination
2. Compare file sizes
3. Compute xxHash checksums
4. Verify checksums match
5. Log verification result

**Note:** Verification adds ~20-30% to total copy time but ensures data integrity.

---

## Usage Examples

### Example 1: Copy Specific Files

**Scenario:** Copy a list of specific files from one drive to another.

**File list** (`my_files.txt`):
```
clip_001.mov
clip_002.mov
interview_final.wav
graphics_logo.png
```

**Command:**
```bash
python copy_file_list.py \
    -s /Volumes/MediaDrive \
    -d /Volumes/ProjectDrive/assets \
    -f my_files.txt \
    -l copy_log.txt \
    -p  # Show progress
```

### Example 2: EDL-Based Media Copy

**Scenario:** Extract and copy all media referenced in an EDL file.

**Command:**
```bash
python copy_file_list.py \
    -s /Volumes/RawFootage \
    -s /Volumes/Backup \
    -d /Project/Media \
    --edl final_edit.edl \
    -l edl_copy.log \
    -p --verify  # Progress + verification
```

### Example 3: Pattern Matching with Glob

**Scenario:** Copy all MP4 and MOV files matching a pattern.

**Pattern file** (`video_patterns.txt`):
```
*.mp4
*.mov
*_final_*.mp4
scene_[0-9][0-9]_*.mov
```

**Command:**
```bash
python copy_file_list.py \
    -s /Volumes/Camera1 \
    -s /Volumes/Camera2 \
    -d /Project/Video \
    -f video_patterns.txt \
    -l video_copy.log \
    -p
```

### Example 4: Regex Pattern Matching

**Scenario:** Complex pattern matching with regular expressions.

**Regex file** (`advanced_patterns.txt`):
```
^A00[0-9]C[0-9]{3}.*\.mxf$
^interview_\d{3}_take\d+\.mov$
^(scene|clip)_\d+_[a-z]+\.mp4$
```

**Command:**
```bash
python copy_file_list.py \
    -s /media/professional \
    -d /output \
    -f advanced_patterns.txt \
    -l regex_copy.log \
    -r  # Enable regex mode
    -p
```

### Example 5: Size Filtering

**Scenario:** Copy files but skip anything larger than 100MB.

**Command:**
```bash
python copy_file_list.py \
    -s /source \
    -d /dest \
    -f files.txt \
    -l log.txt \
    -m 100  # Max 100 MB
    -p
```

### Example 6: Exclude Patterns

**Scenario:** Copy all files except thumbnails and temp files.

**Exclude file** (`exclude.txt`):
```
*_thumb.jpg
*.tmp
*.cache
*.DS_Store
```

**Command:**
```bash
python copy_file_list.py \
    -s /source \
    -d /dest \
    -f files.txt \
    -l log.txt \
    -x exclude.txt  # Apply exclusions
    -p
```

### Example 7: Dry Run First, Then Execute

**Scenario:** Preview operation before copying.

**Step 1 - Dry run:**
```bash
python copy_file_list.py \
    -s /source \
    -d /dest \
    -f files.txt \
    -l log.txt \
    -n  # Dry run
```

**Review log, then Step 2 - Execute:**
```bash
python copy_file_list.py \
    -s /source \
    -d /dest \
    -f files.txt \
    -l log.txt \
    # Remove -n flag to actually copy
```

### Example 8: Using GUI for Interactive Copy

**Scenario:** Non-technical user needs to copy files from EDL.

**Steps:**
1. Launch GUI: `python copy_file_list_gui.py`
2. Click "Add Source Directory" → Select `/Volumes/MediaDrive`
3. Click "Select Destination Directory" → Select `/Project/Media`
4. Select "EDL File" radio button
5. Click "Browse" → Select `project.edl`
6. Go to "Options" tab → Check "Show Progress"
7. Go to "Run" tab → Click "Start"
8. Monitor real-time progress and console output

---

## Advanced Usage

### Automation with Scripts

**Bash script for nightly backups:**

```bash
#!/bin/bash
# daily_media_copy.sh

DATE=$(date +%Y%m%d)
LOG_DIR="/logs/media_copy"
mkdir -p "$LOG_DIR"

python3 /path/to/copy_file_list.py \
    -s /Volumes/Production \
    -s /Volumes/Archive \
    -d /Volumes/Backup \
    -f /config/daily_files.txt \
    -l "$LOG_DIR/copy_$DATE.log" \
    -p --verify

# Email log if errors occurred
if grep -q "ERROR" "$LOG_DIR/copy_$DATE.log"; then
    mail -s "Media Copy Errors - $DATE" admin@example.com < "$LOG_DIR/copy_$DATE.log"
fi
```

**Schedule with cron:**
```bash
# Run daily at 2 AM
0 2 * * * /path/to/daily_media_copy.sh
```

### Python API Usage

The utility can be imported as a module:

```python
from copy_file_list import FileCopyUtility, Logger

# Initialize
logger = Logger('operation.log', dry_run=False)
copier = FileCopyUtility(
    source_dirs=['/source1', '/source2'],
    dest_dirs=['/dest'],
    logger=logger,
    progress=True,
    verify=True
)

# Copy files
patterns = ['*.mp4', '*.mov']
copier.copy_files(patterns)

# Or parse EDL
from copy_file_list import EDLParser
parser = EDLParser(logger)
filenames = parser.parse_edl_file('project.edl')
copier.copy_files(filenames)
```

### Handling Paths with Commas

**Paths containing commas must be quoted:**

```bash
# Incorrect (will fail)
python copy_file_list.py -s /path/with,comma -d /dest -f files.txt -l log.txt

# Correct (quoted)
python copy_file_list.py -s "/path/with,comma" -d /dest -f files.txt -l log.txt
```

### Large-Scale Operations

**Copying 10,000+ files:**

1. **Use dry-run first** to estimate time:
   ```bash
   time python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt -n
   ```

2. **Use first-match-only** if you have duplicates:
   ```bash
   python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt --first-match-only
   ```

3. **Monitor with progress bar:**
   ```bash
   python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt -p
   ```

4. **Verify critical files only:**
   ```bash
   # Create separate lists for critical vs non-critical files
   python copy_file_list.py -s /src -d /dst -f critical.txt -l log.txt -p --verify
   python copy_file_list.py -s /src -d /dst -f other.txt -l log.txt -p
   ```

---

## Troubleshooting

### Issue: "File not found" for files that exist

**Causes:**
1. Case sensitivity mismatch
2. Hidden characters in filenames
3. File in subdirectory not being searched

**Solutions:**

1. **Check exact filename:**
   ```bash
   ls -la /source | grep filename
   ```

2. **Use glob pattern to catch variations:**
   ```
   # Instead of: exact_name.mp4
   # Use:
   *exact_name*.mp4
   ```

3. **Enable debug mode:**
   ```bash
   python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt --debug
   ```
   Check log for detailed search information.

---

### Issue: Copy is very slow

**Causes:**
1. Network drive latency
2. Large files
3. File verification enabled
4. Many small files

**Solutions:**

1. **Copy to local drive first:**
   ```bash
   # Copy to fast local disk
   python copy_file_list.py -s /network -d /tmp/local -f files.txt -l log.txt
   # Then move to final destination
   mv /tmp/local/* /final/destination/
   ```

2. **Disable verification for speed:**
   ```bash
   # Without --verify flag
   python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt -p
   ```

3. **Split large operations:**
   ```bash
   # Split file list into chunks
   split -l 1000 large_list.txt chunk_
   # Process each chunk
   for chunk in chunk_*; do
       python copy_file_list.py -s /src -d /dst -f $chunk -l log_$chunk.txt -p
   done
   ```

---

### Issue: "Permission denied" errors

**Solution:**

```bash
# Run with appropriate permissions
sudo python3 copy_file_list.py -s /src -d /dst -f files.txt -l log.txt

# Or fix ownership
sudo chown -R $USER:$USER /destination/directory
```

---

### Issue: GUI doesn't start

**Cause:** Missing PyQt5 dependency

**Solution:**
```bash
# Install PyQt5
pip install PyQt5

# If that fails, try:
pip3 install PyQt5

# On macOS with Homebrew Python:
/opt/homebrew/bin/pip3 install PyQt5
```

---

### Issue: Duplicate files being copied

**Default behavior:** If file exists, creates `filename_1.ext`, `filename_2.ext`, etc.

**To skip duplicates, use --first-match-only:**
```bash
python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt --first-match-only
```

---

### Issue: Out of disk space

**Solution - Check space first:**

```bash
# Check available space
df -h /destination

# Estimate required space (dry run)
python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt -n | grep "Total size"
```

---

### Issue: EDL parsing finds no files

**Causes:**
1. EDL format not recognized
2. No "SOURCE FILE" lines in EDL
3. Encoding issues

**Solutions:**

1. **Check EDL format:**
   ```bash
   head -20 project.edl
   # Look for lines like:
   # * SOURCE FILE: filename.mov
   ```

2. **Try different encoding:**
   The tool auto-detects encoding, but if it fails, convert first:
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 project.edl > project_utf8.edl
   ```

3. **Extract filenames manually:**
   ```bash
   grep "SOURCE FILE" project.edl | sed 's/.*: //' > filenames.txt
   python copy_file_list.py -s /src -d /dst -f filenames.txt -l log.txt
   ```

---

### Issue: Progress bar not showing

**Cause:** Progress disabled or output redirected

**Solution:**
```bash
# Ensure -p flag is present
python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt -p

# Don't redirect stdout if you want to see progress
# Bad:  python script.py -p > output.txt
# Good: python script.py -p | tee output.txt
```

---

## Performance Notes

### Speed Estimates

**SSD to SSD:**
- ~100-500 MB/s (depends on drive and interface)
- 1000 small files (1 MB each): ~10-20 seconds
- 100 large files (1 GB each): ~3-5 minutes

**HDD to HDD:**
- ~50-150 MB/s
- 1000 small files: ~30-60 seconds (seek time overhead)
- 100 large files: ~10-15 minutes

**Network Drive:**
- ~10-100 MB/s (depends on network speed)
- Add 2-5× time for network latency

**With Verification:**
- Add ~20-30% to copy time (hash computation)

### Memory Usage

- **CLI:** ~50-100 MB RAM (constant)
- **GUI:** ~100-200 MB RAM (PyQt5 overhead)
- **Large file lists (100k+ files):** May use up to 500 MB RAM

---

## Tips & Best Practices

### 1. Always Test with Dry Run First

```bash
# Dry run to preview
python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt -n

# Review log
less log.txt

# If good, run for real
python copy_file_list.py -s /src -d /dst -f files.txt -l log.txt
```

### 2. Use Verification for Critical Files

```bash
# For important media or archival copies
python copy_file_list.py -s /src -d /dst -f critical.txt -l log.txt --verify
```

### 3. Organize File Lists by Type

Instead of one huge list:
```
all_files.txt (10,000 lines)
```

Use multiple organized lists:
```
video_files.txt (1,000 lines)
audio_files.txt (5,000 lines)
graphics_files.txt (4,000 lines)
```

Then run separately with appropriate options.

### 4. Keep Logs for Audit Trail

```bash
# Organized log naming
python copy_file_list.py \
    -s /src -d /dst \
    -f files.txt \
    -l "logs/copy_$(date +%Y%m%d_%H%M%S).log"
```

### 5. Check Missing Files Log

After copying, review missing files:
```bash
cat operations.log.missing.txt

# If many missing, might need to:
# - Add more source directories
# - Fix file list patterns
# - Check if files were renamed
```

---

## System Requirements

**Python:** 3.7+

**Dependencies:**
- `xxhash` (fast hash computation)
- `chardet` (encoding detection for EDL files)
- `PyQt5` (GUI only)

**Platforms:**
- macOS
- Linux
- Windows

**Recommended Hardware:**
- 4 GB RAM minimum
- SSD for best performance
- Fast network connection (for network drives)

---

## Support & Contributing

For issues, feature requests, or contributions, please refer to the main project repository.

**Common Use Cases:**
- Post-production media consolidation
- Archive restoration
- Batch file operations
- EDL-based workflows
- Asset management

---

## Version History

**v3.2 (CLI):**
- Added EDL parsing support
- Improved pattern matching
- Better error handling
- Progress bar with ETA

**v1.1 (GUI):**
- Real-time console output
- Color-coded messages
- Settings persistence
- Improved progress tracking

---

## License

This tool is part of the Post Production Utilities toolkit.
