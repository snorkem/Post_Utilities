#!/bin/zsh

# ================================================
# v2.5
# File Search and Copy Utility -- written with Claude Sonnet 3.7
# ================================================
# This script searches for files in a source directory based on a list
# of filenames (with wildcard support) and copies them to a destination
# directory. All operations are logged to a detailed log file.
# The script will:
# - Skip any files that already exist in the destination
# - Append to the log file if it already exists
# ================================================

# Display usage information
usage() {
    echo "Usage: $0 -s SOURCE_DIR -d DEST_DIR -f FILE_LIST -l LOG_FILE"
    echo ""
    echo "Options:"
    echo "  -s SOURCE_DIR   Directory to search in"
    echo "  -d DEST_DIR     Directory to copy files to"
    echo "  -f FILE_LIST    File containing list of filenames to search for (one per line)"
    echo "  -l LOG_FILE     Log file to write operations to (will append if exists)"
    echo "  -h              Display this help message"
    exit 1
}

# Initialize variables
SOURCE_DIR=""
DEST_DIR=""
FILE_LIST=""
LOG_FILE=""

# Process command line arguments
while getopts "s:d:f:l:h" opt; do
    case $opt in
        s) SOURCE_DIR="$OPTARG" ;;
        d) DEST_DIR="$OPTARG" ;;
        f) FILE_LIST="$OPTARG" ;;
        l) LOG_FILE="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate required parameters
if [[ -z "$SOURCE_DIR" || -z "$DEST_DIR" || -z "$FILE_LIST" || -z "$LOG_FILE" ]]; then
    echo "Error: Missing required parameters"
    usage
fi

# Ensure source directory exists
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# Ensure file list exists
if [[ ! -f "$FILE_LIST" ]]; then
    echo "Error: File list does not exist: $FILE_LIST"
    exit 1
fi

# Create destination directory if it doesn't exist
if [[ ! -d "$DEST_DIR" ]]; then
    mkdir -p "$DEST_DIR"
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to create destination directory: $DEST_DIR"
        exit 1
    fi
    echo "Created destination directory: $DEST_DIR"
fi

# Check if log file directory exists and is writable
LOG_DIR=$(dirname "$LOG_FILE")
if [[ ! -d "$LOG_DIR" ]]; then
    mkdir -p "$LOG_DIR"
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to create log directory: $LOG_DIR"
        exit 1
    fi
fi

# Set up additional log files for tracking missing and existing files
MISSING_FILES_LOG="${LOG_FILE}.missing"
EXISTING_FILES_LOG="${LOG_FILE}.existing"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Initialize or append to missing files log
if [[ -f "$MISSING_FILES_LOG" ]]; then
    echo "" >> "$MISSING_FILES_LOG"
    echo "=== Missing Files Session: $TIMESTAMP ===" >> "$MISSING_FILES_LOG"
    echo "Source Directory: $SOURCE_DIR" >> "$MISSING_FILES_LOG"
    echo "File List: $FILE_LIST" >> "$MISSING_FILES_LOG"
    echo "" >> "$MISSING_FILES_LOG"
else
    echo "=== Missing Files Log ===" > "$MISSING_FILES_LOG"
    echo "=== First Session: $TIMESTAMP ===" >> "$MISSING_FILES_LOG"
    echo "Source Directory: $SOURCE_DIR" >> "$MISSING_FILES_LOG"
    echo "File List: $FILE_LIST" >> "$MISSING_FILES_LOG"
    echo "" >> "$MISSING_FILES_LOG"
fi

# Initialize or append to existing files log
if [[ -f "$EXISTING_FILES_LOG" ]]; then
    echo "" >> "$EXISTING_FILES_LOG"
    echo "=== Existing Files Session: $TIMESTAMP ===" >> "$EXISTING_FILES_LOG"
    echo "Source Directory: $SOURCE_DIR" >> "$EXISTING_FILES_LOG"
    echo "Destination Directory: $DEST_DIR" >> "$EXISTING_FILES_LOG"
    echo "" >> "$EXISTING_FILES_LOG"
else
    echo "=== Existing Files Log ===" > "$EXISTING_FILES_LOG"
    echo "=== First Session: $TIMESTAMP ===" >> "$EXISTING_FILES_LOG"
    echo "Source Directory: $SOURCE_DIR" >> "$EXISTING_FILES_LOG"
    echo "Destination Directory: $DEST_DIR" >> "$EXISTING_FILES_LOG"
    echo "" >> "$EXISTING_FILES_LOG"
fi

# Initialize or append to log file with header
# Check if the log file exists
if [[ -f "$LOG_FILE" ]]; then
    # Append a separator and new session header to existing log
    if ! {
        echo "" >> "$LOG_FILE"
        echo "======================================================" >> "$LOG_FILE"
        echo "NEW SESSION: File Search and Copy Operation - $(date)" >> "$LOG_FILE"
        echo "======================================================" >> "$LOG_FILE"
    }; then
        echo "Error: Cannot write to log file: $LOG_FILE"
        exit 1
    fi
else
    # Create new log file with initial header
    if ! {
        echo "======================================================" > "$LOG_FILE"
        echo "File Search and Copy Operation - $(date)" >> "$LOG_FILE"
        echo "======================================================" >> "$LOG_FILE"
    }; then
        echo "Error: Cannot write to log file: $LOG_FILE"
        exit 1
    fi
fi

# Continue with log file initialization
echo "Source Directory: $SOURCE_DIR" >> "$LOG_FILE"
echo "Destination Directory: $DEST_DIR" >> "$LOG_FILE"
echo "File List: $FILE_LIST" >> "$LOG_FILE"
echo "======================================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Counter for statistics
total_patterns=0
found_files=0
copied_files=0
skipped_files=0
missing_patterns=0  # New counter for missing patterns
existing_files=0    # New counter for existing files

# Make sure the file list is readable
if [[ ! -r "$FILE_LIST" ]]; then
    echo "Error: File list is not readable: $FILE_LIST"
    exit 1
fi

# Process each file pattern in the list
while IFS= read -r file_pattern || [[ -n "$file_pattern" ]]; do
    # Skip empty lines and comments
    if [[ -z "$file_pattern" || "$file_pattern" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Trim leading/trailing whitespace
    file_pattern=$(echo "$file_pattern" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    
    ((total_patterns++))
    
    echo "Processing pattern: $file_pattern" >> "$LOG_FILE"
    
    # Use find command to locate files matching the pattern
    # -type f ensures we only find files, not directories
    found=$(find "$SOURCE_DIR" -type f -name "$file_pattern" 2>"$LOG_FILE.error")
    
    # Check for find command errors
    if [[ -s "$LOG_FILE.error" ]]; then
        echo "  ERROR during find operation:" >> "$LOG_FILE"
        cat "$LOG_FILE.error" >> "$LOG_FILE"
        rm -f "$LOG_FILE.error"
    else
        rm -f "$LOG_FILE.error"
    fi
    
    # If no files found, log and continue
    if [[ -z "$found" ]]; then
        echo "  No files found matching: $file_pattern" >> "$LOG_FILE"
        # Log missing file to missing files log
        echo "$file_pattern" >> "$MISSING_FILES_LOG"
        ((missing_patterns++))
        continue
    fi
    
    # Process each found file
    echo "$found" | while IFS= read -r file; do
        # Extract just the filename
        filename=$(basename "$file")
        
        # Log the found file
        echo "  Found: $file" >> "$LOG_FILE"
        
        # Update found_files counter (using a temp file to avoid subshell issues)
        echo "found" >> "$LOG_FILE.count"
        
        # Check if destination file already exists
        if [[ -f "$DEST_DIR/$filename" ]]; then
            echo "  SKIPPED: File already exists in destination: $filename" >> "$LOG_FILE"
            echo "skipped" >> "$LOG_FILE.count"
            # Log to existing files log
            echo "$filename" >> "$EXISTING_FILES_LOG"
            echo "existing" >> "$LOG_FILE.count"
        else
            # Copy the file to destination only if it doesn't exist
            if cp "$file" "$DEST_DIR/"; then
                echo "  Copied to: $DEST_DIR/$filename" >> "$LOG_FILE"
                echo "copied" >> "$LOG_FILE.count"
            else
                echo "  ERROR: Failed to copy: $file" >> "$LOG_FILE"
            fi
        fi
    done
done < "$FILE_LIST"

# Count the operations from the temp file to avoid subshell variable scope issues
if [[ -f "$LOG_FILE.count" ]]; then
    found_files=$(grep -c "found" "$LOG_FILE.count")
    copied_files=$(grep -c "copied" "$LOG_FILE.count")
    skipped_files=$(grep -c "skipped" "$LOG_FILE.count")
    existing_files=$(grep -c "existing" "$LOG_FILE.count")
    rm -f "$LOG_FILE.count"
fi

# Log summary statistics
echo "" >> "$LOG_FILE"
echo "======================================================" >> "$LOG_FILE"
echo "Summary - $(date)" >> "$LOG_FILE"
echo "Patterns processed: $total_patterns" >> "$LOG_FILE"
echo "Files found: $found_files" >> "$LOG_FILE"
echo "Files copied: $copied_files" >> "$LOG_FILE"
echo "Files skipped (already existed): $skipped_files" >> "$LOG_FILE"
echo "Patterns with no matches: $missing_patterns" >> "$LOG_FILE"
echo "======================================================" >> "$LOG_FILE"

# Output summary to console
echo "Operation completed. See $LOG_FILE for details."
echo "Patterns processed: $total_patterns"
echo "Files found: $found_files"
echo "Files copied: $copied_files"
echo "Files skipped (already existed): $skipped_files"
echo "Patterns with no matches: $missing_patterns"

# Display information about additional log files
if [[ $missing_patterns -gt 0 ]]; then
    echo "Missing files log: $MISSING_FILES_LOG ($missing_patterns patterns with no matches)"
fi

if [[ $existing_files -gt 0 ]]; then
    echo "Existing files log: $EXISTING_FILES_LOG ($existing_files files already in destination)"
fi

exit 0
