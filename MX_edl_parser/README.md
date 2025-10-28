# MX EDL Parser

A robust EDL (Edit Decision List) parser with intelligent clip detection and gap analysis.

## Features

- **Dual Parser System**: Uses pycmx library for robust parsing with automatic fallback to built-in parser
- **Gap Detection**: Treats clips with gaps > 1 frame as separate instances
- **Configurable FPS**: Default 23.976, customizable via command line
- **Multiple Output Formats**: TXT, CSV, and Excel
- **Analytics**: Generate detailed statistics about clip usage and duration
- **Validation**: Warns about invalid timecode ranges

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Minimum installation (built-in parser only)
# No external dependencies required - uses Python standard library
```

## Usage

```bash
# Basic usage (uses pycmx if available, falls back to built-in)
python MX_edl_parser.py your_file.edl

# Specify FPS (default is 23.976)
python MX_edl_parser.py your_file.edl --fps 24

# Output to CSV
python MX_edl_parser.py your_file.edl --format csv

# Output to Excel (requires pandas)
python MX_edl_parser.py your_file.edl --format excel

# Generate all formats
python MX_edl_parser.py your_file.edl --format all

# Generate analytics report
python MX_edl_parser.py your_file.edl --analytics

# Prevent overwriting existing files
python MX_edl_parser.py your_file.edl --no-overwrite
```

## Requirements

- Python 3.6+
- pycmx (recommended, optional) - Robust CMX 3600 EDL parsing
- pandas (optional) - Excel export support
- openpyxl (optional) - Excel engine for pandas

## How It Works

1. **Parsing**: Uses pycmx library if available for better format support
2. **Grouping**: Groups edits by clip name or source file
3. **Gap Analysis**: Identifies gaps > 1 frame between consecutive edits
4. **Instance Creation**: Creates separate instances for clips separated by gaps
5. **Timecode Consolidation**: Takes first Source In and last Source Out for each instance

## Default FPS

The parser uses **23.976 fps** as the default frame rate for timecode calculations. This can be overridden with the `--fps` argument.

## Supported Frame Rates

Common frame rates include:
- 23.976 (default)
- 24
- 25
- 29.97
- 30
- 59.94
- 60

## Output

Each output includes:
- Clip Name/Source File
- Source In timecode
- Source Out timecode
- Sequence In timecode
- Sequence Out timecode

## Analytics

When using `--analytics`, generates:
- Total clip count
- Total sequence duration
- Longest/shortest clips
- Percentage of timeline per clip
- Sorted by percentage (descending)
