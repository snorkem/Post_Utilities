# Post Production Utilities

A playground of Python tools I cobbled together using brains + a little claude.ai that'll make your post-production life way easier! 🎬✨
Some of the scripts have GUI versions that you can use if you're less comfortable with terminal. All these were developed primarily for use on MacOS systems.

## The Toolbox

### 1. ALE Converter
**File:** `ale_converter.py`

Your Swiss Army knife for Avid Log Exchange (ALE) files. This bad boy can:
- Merge ALE files with external databases
- Export data to CSV or Excel
- Convert spreadsheets to ALE format
- Work some serious metadata magic

### 2. Media Reporter
**File:** `media-reporter.py`

The Sherlock Holmes of media file investigation. Pulls out every juicy detail about your media files using FFprobe:
- Decode video mysteries
- Uncover audio secrets
- Reveal file specs in multiple formats
- Extract timecodes like a pro

### 3. File Search and Copy Utility
**File:** `copy_file_list.py`

Your digital asset hunting and gathering expert. This tool:
- Searches files across multiple directories
- Copies files with ninja-like precision
- Supports crazy-flexible pattern matching
- Logs everything meticulously

### 4. Lower Thirds Generator
**File:** `l3rds_from_excel.py`

Turn boring spreadsheets into slick graphics! Creates lower thirds that:
- Pop out from Excel or CSV data
- Let you play with fonts, colors, and effects
- Work in GUI or command-line mode
- Support multiple image formats

### 5. File Renaming Utility
**File:** `rename_files_from_excel.py`

The ultimate file name makeover artist. Quickly:
- Rename batches of files
- Follow spreadsheet naming rules
- Keep detailed logs of all transformations

### 6. Directory Indexer
**File:** `directory_indexer.py`

Your visual directory explorer on steroids! Creates beautiful, interactive HTML archives:
- Scans entire directory trees (handles up to 200K files smoothly)
- Generates single-file HTML reports with zero dependencies
- Live search, sort, and filter capabilities
- Works offline - perfect for archiving project drives!

**Performance Note:** Optimized for datasets up to ~200,000 files. For massive archives (1M+ files), consider indexing subdirectories separately.

## Get Started

Grab the dependencies from the requirments.txt in each utility folder:
