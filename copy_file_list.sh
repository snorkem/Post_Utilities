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
    cat << EOF
Usage: $0 -s SOURCE_DIR -d DEST_DIR -f FILE_LIST [-l LOG_FILE] [-h]

Options:
  -s SOURCE_DIR   Directory to search in (required)
  -d DEST_DIR     Directory to copy files to (required)
  -f FILE_LIST    File containing list of filenames to search for (required)
  -l LOG_FILE     Log file to write operations to (optional, defaults to script name with .log)
  -h              Display this help message
EOF
    exit 1
}

# Error handling function
error_exit() {
    echo "ERROR: $1" >&2
    exit 1
}

# Log message function
log_message() {
    local log_file="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$log_file"
}

# Initialize variables with defaults
SOURCE_DIR=""
DEST_DIR=""
FILE_LIST=""
LOG_FILE="${0%.sh}.log"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

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
[[ -z "$SOURCE_DIR" ]] && error_exit "Source directory is required"
[[ -z "$DEST_DIR" ]] && error_exit "Destination directory is required"
[[ -z "$FILE_LIST" ]] && error_exit "File list is required"

# Validate directories and file list
[[ ! -d "$SOURCE_DIR" ]] && error_exit "Source directory does not exist: $SOURCE_DIR"
[[ ! -f "$FILE_LIST" ]] && error_exit "File list does not exist: $FILE_LIST"

# Ensure destination directory exists
mkdir -p "$DEST_DIR" || error_exit "Failed to create destination directory: $DEST_DIR"

# Create log directory if needed
mkdir -p "$(dirname "$LOG_FILE")" || error_exit "Failed to create log directory"

# Setup missing and existing files logs
MISSING_FILES_LOG="${LOG_FILE}.missing"
EXISTING_FILES_LOG="${LOG_FILE}.existing"

# Initialize or append to missing files log
if [[ -f "$MISSING_FILES_LOG" ]]; then
    echo "" >> "$MISSING_FILES_LOG"
    echo "=== Missing Files Session: $TIMESTAMP ===" >> "$MISSING_FILES_LOG"
    echo "Source Directory: $SOURCE_DIR" >> "$MISSING_FILES_LOG"
else
    {
        echo "=== Missing Files Log ===" > "$MISSING_FILES_LOG"
        echo "=== First Session: $TIMESTAMP ===" >> "$MISSING_FILES_LOG"
        echo "Source Directory: $SOURCE_DIR" >> "$MISSING_FILES_LOG"
    }
fi

# Initialize or append to existing files log
if [[ -f "$EXISTING_FILES_LOG" ]]; then
    echo "" >> "$EXISTING_FILES_LOG"
    echo "=== Existing Files Session: $TIMESTAMP ===" >> "$EXISTING_FILES_LOG"
    echo "Source Directory: $SOURCE_DIR" >> "$EXISTING_FILES_LOG"
else
    {
        echo "=== Existing Files Log ===" > "$EXISTING_FILES_LOG"
        echo "=== First Session: $TIMESTAMP ===" >> "$EXISTING_FILES_LOG"
        echo "Source Directory: $SOURCE_DIR" >> "$EXISTING_FILES_LOG"
    }
fi

# Initialize main log file
{
    echo "======================================================" > "$LOG_FILE"
    echo "File Search and Copy Operation - $(date)" >> "$LOG_FILE"
    echo "Source Directory: $SOURCE_DIR" >> "$LOG_FILE"
    echo "Destination Directory: $DEST_DIR" >> "$LOG_FILE"
    echo "File List: $FILE_LIST" >> "$LOG_FILE"
    echo "======================================================" >> "$LOG_FILE"
} || error_exit "Cannot write to log file: $LOG_FILE"

# Initialize counters
typeset -i total_patterns=0 found_files=0 copied_files=0 skipped_files=0 missing_patterns=0 existing_files=0

# Process file list
while IFS= read -r file_pattern || [[ -n "$file_pattern" ]]; do
    # Skip empty lines and comments
    [[ -z "$file_pattern" || "$file_pattern" =~ ^[[:space:]]*# ]] && continue
    
    # Trim whitespace
    file_pattern=$(printf '%s' "$file_pattern" | xargs)
    
    ((total_patterns++))
    log_message "$LOG_FILE" "Processing pattern: $file_pattern"
    
    # Use improved find with error handling
    mapfile -t found_files < <(find "$SOURCE_DIR" -type f -name "$file_pattern" 2>/dev/null)
    
    if (( ${#found_files[@]} == 0 )); then
        # No files found in source directory
        echo "$file_pattern" >> "$MISSING_FILES_LOG"
        log_message "$LOG_FILE" "NO SOURCE: No files found matching pattern: $file_pattern"
        ((missing_patterns++))
        continue
    fi
    
    # Process found files
    for file in "${found_files[@]}"; do
        filename=$(basename "$file")
        dest_file="$DEST_DIR/$filename"
        
        log_message "$LOG_FILE" "  Found: $file"
        ((found_files++))
        
        if [[ -f "$dest_file" ]]; then
            echo "$filename" >> "$EXISTING_FILES_LOG"
            log_message "$LOG_FILE" "  EXISTING: $filename already in destination"
            log_message "$EXISTING_FILES_LOG" "$filename"
            ((skipped_files++))
            ((existing_files++))
        else
            if cp -p "$file" "$dest_file"; then
                log_message "$LOG_FILE" "  Copied to: $dest_file"
                ((copied_files++))
            else
                log_message "$LOG_FILE" "  ERROR: Failed to copy: $file"
            fi
        fi
    done
done < "$FILE_LIST"

# Log summary
{
    echo "" >> "$LOG_FILE"
    echo "======================================================" >> "$LOG_FILE"
    echo "Summary - $(date)" >> "$LOG_FILE"
    echo "Patterns processed: $total_patterns" >> "$LOG_FILE"
    echo "Files found: $found_files" >> "$LOG_FILE"
    echo "Files copied: $copied_files" >> "$LOG_FILE"
    echo "Files skipped (already existed): $skipped_files" >> "$LOG_FILE"
    echo "Patterns with no matches: $missing_patterns" >> "$LOG_FILE"
    echo "======================================================" >> "$LOG_FILE"
} || error_exit "Failed to write summary to log file"

# Console output
echo "Operation completed. See $LOG_FILE for details."
echo "Patterns processed: $total_patterns"
echo "Files found: $found_files"
echo "Files copied: $copied_files"
echo "Files skipped (already existed): $skipped_files"
echo "Patterns with no matches: $missing_patterns"

# Provide log file information
if [[ -s "$MISSING_FILES_LOG" ]]; then
    missing_patterns_count=$(grep -c "=== Missing Files" "$MISSING_FILES_LOG")
    echo "Missing files log created: $MISSING_FILES_LOG"
    echo "Number of patterns with no source matches: $missing_patterns"
fi

if [[ -s "$EXISTING_FILES_LOG" ]]; then
    existing_files_count=$(grep -c "=== Existing Files" "$EXISTING_FILES_LOG")
    echo "Existing files log created: $EXISTING_FILES_LOG"
    echo "Number of files already in destination: $existing_files"
fi

exit 0

