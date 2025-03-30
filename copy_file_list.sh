#!/bin/zsh

# ================================================
# File Search and Copy Utility v2.7
# ================================================
# This script searches for files in one or more source directories
# based on a list of filenames (with wildcard support) and copies
# them to a destination directory. All operations are logged to a
# detailed log file.
# The script will:
# - Search across multiple source directories
# - Skip any files that already exist in the destination
# - Append to the log file if it already exists
# - Track missing files and existing files in separate logs
# - Show progress during file copy operations
# - Check available disk space before starting
# - Support advanced pattern matching including regex
# ================================================

# Display usage information with examples
usage() {
    cat << EOF
Usage: $0 -s SOURCE_DIR1[,SOURCE_DIR2,...] -d DEST_DIR -f FILE_LIST -l LOG_FILE [OPTIONS]

Required Options:
  -s SOURCE_DIRS  One or more directories to search in (comma-separated)
  -d DEST_DIR     Directory to copy files to
  -f FILE_LIST    File containing list of filenames to search for (one per line)
  -l LOG_FILE     Log file to write operations to (will append if exists)

Additional Options:
  -p              Show progress during copy operations
  -r              Use regular expressions instead of glob patterns
  -m MAX_SIZE     Skip files larger than MAX_SIZE (in MB)
  -x              Skip files that match patterns in FILE_LIST
  -h              Display this help message

Advanced Pattern Matching:
  By default, the script uses glob patterns (*, ?, [abc], etc.).
  When -r is specified, patterns are treated as regular expressions.

Examples:
  # Using multiple source directories:
  $0 -s /path/source1,/path/source2,/path/source3 -d /path/dest -f files.txt -l log.txt

  # Using glob patterns (default):
  echo "*.jpg" > files.txt       # Match all JPG files
  echo "doc_*.pdf" >> files.txt  # Match PDFs starting with "doc_"
  echo "file_[0-9].txt" >> files.txt  # Match file_0.txt through file_9.txt

  # Using regular expressions (with -r flag):
  echo "^.*\\.jpg$" > regex.txt         # Match all JPG files
  echo "^doc_.*\\.pdf$" >> regex.txt    # Match PDFs starting with "doc_"
  echo "^file_[0-9]\\.txt$" >> regex.txt  # Match file_0.txt through file_9.txt
  echo "^(report|summary)_.*$" >> regex.txt  # Match files starting with "report_" or "summary_"

  # Exclude patterns (with -x flag):
  echo "*.tmp" > exclude.txt  # Exclude all .tmp files
  $0 -s /path/source1,/path/source2 -d /path/dest -f files.txt -l log.txt -x exclude.txt
EOF
    exit 1
}

# Function to check available disk space
check_disk_space() {
    local dest_dir="$1"
    local required_space="$2"  # in KB
    
    # Get available space in KB
    local available_space=$(df -Pk "$dest_dir" | tail -1 | awk '{print $4}')
    
    if (( available_space < required_space )); then
        echo "Error: Insufficient disk space in destination directory."
        echo "Available: $(( available_space / 1024 )) MB"
        echo "Required: $(( required_space / 1024 )) MB"
        return 1
    fi
    return 0
}

# Function to display progress
display_progress() {
    local current="$1"
    local total="$2"
    local width=50
    local percent=$(( current * 100 / total ))
    local completed=$(( width * current / total ))
    
    printf "\rProgress: ["
    printf "%${completed}s" | tr ' ' '#'
    printf "%$(( width - completed ))s" | tr ' ' ' '
    printf "] %3d%% (%d/%d files)" "$percent" "$current" "$total"
}

# Function to calculate total size of files
calculate_total_size() {
    local file_list=("$@")
    local total_size=0
    
    for file in "${file_list[@]}"; do
        if [[ -f "$file" ]]; then
            local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
            (( total_size += file_size ))
        fi
    done
    
    echo $total_size
}

# Initialize variables
SOURCE_DIRS=()
DEST_DIR=""
FILE_LIST=""
LOG_FILE=""
SHOW_PROGRESS=0
USE_REGEX=0
MAX_SIZE=0  # No limit by default
EXCLUDE_FILE=""

# Process command line arguments
while getopts "s:d:f:l:prm:x:h" opt; do
    case $opt in
        s) IFS=',' read -rA SOURCE_DIRS <<< "$OPTARG" ;;
        d) DEST_DIR="$OPTARG" ;;
        f) FILE_LIST="$OPTARG" ;;
        l) LOG_FILE="$OPTARG" ;;
        p) SHOW_PROGRESS=1 ;;
        r) USE_REGEX=1 ;;
        m) MAX_SIZE="$OPTARG" ;;  # in MB
        x) EXCLUDE_FILE="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate required parameters
if [[ ${#SOURCE_DIRS[@]} -eq 0 || -z "$DEST_DIR" || -z "$FILE_LIST" || -z "$LOG_FILE" ]]; then
    echo "Error: Missing required parameters"
    usage
fi

# Ensure source directories exist
for src_dir in "${SOURCE_DIRS[@]}"; do
    if [[ ! -d "$src_dir" ]]; then
        echo "Error: Source directory does not exist: $src_dir"
        exit 1
    fi
done

# Ensure file list exists
if [[ ! -f "$FILE_LIST" ]]; then
    echo "Error: File list does not exist: $FILE_LIST"
    exit 1
fi

# Check exclude file if specified
if [[ -n "$EXCLUDE_FILE" && ! -f "$EXCLUDE_FILE" ]]; then
    echo "Error: Exclude file does not exist: $EXCLUDE_FILE"
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
MISSING_FILES_LOG="${LOG_FILE}.missing.txt"
EXISTING_FILES_LOG="${LOG_FILE}.existing.txt"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Initialize or append to missing files log
if [[ -f "$MISSING_FILES_LOG" ]]; then
    echo "" >> "$MISSING_FILES_LOG"
    echo "=== Missing Files Session: $TIMESTAMP ===" >> "$MISSING_FILES_LOG"
    echo "Source Directories: ${SOURCE_DIRS[*]}" >> "$MISSING_FILES_LOG"
    echo "File List: $FILE_LIST" >> "$MISSING_FILES_LOG"
    echo "" >> "$MISSING_FILES_LOG"
else
    echo "=== Missing Files Log ===" > "$MISSING_FILES_LOG"
    echo "=== First Session: $TIMESTAMP ===" >> "$MISSING_FILES_LOG"
    echo "Source Directories: ${SOURCE_DIRS[*]}" >> "$MISSING_FILES_LOG"
    echo "File List: $FILE_LIST" >> "$MISSING_FILES_LOG"
    echo "" >> "$MISSING_FILES_LOG"
fi

# Initialize or append to existing files log
if [[ -f "$EXISTING_FILES_LOG" ]]; then
    echo "" >> "$EXISTING_FILES_LOG"
    echo "=== Existing Files Session: $TIMESTAMP ===" >> "$EXISTING_FILES_LOG"
    echo "Source Directories: ${SOURCE_DIRS[*]}" >> "$EXISTING_FILES_LOG"
    echo "Destination Directory: $DEST_DIR" >> "$EXISTING_FILES_LOG"
    echo "" >> "$EXISTING_FILES_LOG"
else
    echo "=== Existing Files Log ===" > "$EXISTING_FILES_LOG"
    echo "=== First Session: $TIMESTAMP ===" >> "$EXISTING_FILES_LOG"
    echo "Source Directories: ${SOURCE_DIRS[*]}" >> "$EXISTING_FILES_LOG"
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
        echo "NEW SESSION: File Search and Copy Operation v2.7 - $(date)" >> "$LOG_FILE"
        echo "======================================================" >> "$LOG_FILE"
    }; then
        echo "Error: Cannot write to log file: $LOG_FILE"
        exit 1
    fi
else
    # Create new log file with initial header
    if ! {
        echo "======================================================" > "$LOG_FILE"
        echo "File Search and Copy Operation v2.7 - $(date)" >> "$LOG_FILE"
        echo "======================================================" >> "$LOG_FILE"
    }; then
        echo "Error: Cannot write to log file: $LOG_FILE"
        exit 1
    fi
fi

# Continue with log file initialization
echo "Source Directories: ${SOURCE_DIRS[*]}" >> "$LOG_FILE"
echo "Destination Directory: $DEST_DIR" >> "$LOG_FILE"
echo "File List: $FILE_LIST" >> "$LOG_FILE"
if [[ $USE_REGEX -eq 1 ]]; then
    echo "Using regular expressions for pattern matching" >> "$LOG_FILE"
fi
if [[ -n "$EXCLUDE_FILE" ]]; then
    echo "Exclude File: $EXCLUDE_FILE" >> "$LOG_FILE"
fi
if [[ $MAX_SIZE -gt 0 ]]; then
    echo "Maximum File Size: $MAX_SIZE MB" >> "$LOG_FILE"
fi
echo "======================================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Counter for statistics
total_patterns=0
found_files=0
copied_files=0
skipped_files=0
missing_patterns=0
existing_files=0
size_exceeded_files=0
excluded_files=0
total_bytes_copied=0

# Store patterns that weren't found in any source directory
missing_patterns_array=()

# Make sure the file list is readable
if [[ ! -r "$FILE_LIST" ]]; then
    echo "Error: File list is not readable: $FILE_LIST"
    exit 1
fi

# Load exclude patterns if specified
exclude_patterns=()
if [[ -n "$EXCLUDE_FILE" && -f "$EXCLUDE_FILE" ]]; then
    while IFS= read -r pattern || [[ -n "$pattern" ]]; do
        # Skip empty lines and comments
        if [[ -z "$pattern" || "$pattern" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Trim leading/trailing whitespace
        pattern=$(echo "$pattern" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        exclude_patterns+=("$pattern")
    done < "$EXCLUDE_FILE"
    
    echo "Loaded ${#exclude_patterns[@]} exclude patterns" >> "$LOG_FILE"
fi

# Create a list of all files to be copied (for progress tracking)
all_files_to_process=()
all_files_to_copy=()

# First pass: identify all files that need to be processed
echo "Analyzing files to copy..." >> "$LOG_FILE"
if [[ $SHOW_PROGRESS -eq 1 ]]; then
    echo "Analyzing files to copy across ${#SOURCE_DIRS[@]} source directories..."
fi

# Read the file list once
file_patterns=()
while IFS= read -r file_pattern || [[ -n "$file_pattern" ]]; do
    # Skip empty lines and comments
    if [[ -z "$file_pattern" || "$file_pattern" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Trim leading/trailing whitespace
    file_pattern=$(echo "$file_pattern" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    file_patterns+=("$file_pattern")
    ((total_patterns++))
done < "$FILE_LIST"

# For each pattern, search across all source directories
for file_pattern in "${file_patterns[@]}"; do
    echo "Processing pattern: $file_pattern" >> "$LOG_FILE"
    
    # Flag to track if the pattern was found in any source directory
    pattern_found=0
    
    # Search in each source directory
    for src_dir in "${SOURCE_DIRS[@]}"; do
        echo "  Searching in: $src_dir" >> "$LOG_FILE"
        
        # Use find with regex or glob pattern
        if [[ $USE_REGEX -eq 1 ]]; then
            # Use regex pattern with -regex option to find
            found=$(find "$src_dir" -type f -regex "$src_dir/$file_pattern" 2>/dev/null)
        else
            # Use standard glob pattern
            found=$(find "$src_dir" -type f -name "$file_pattern" 2>/dev/null)
        fi
        
        # Process found files
        if [[ -n "$found" ]]; then
            pattern_found=1
            echo "    Found matches in $src_dir" >> "$LOG_FILE"
            
            # Process each found file
            while IFS= read -r file; do
                # Check if file should be excluded
                local exclude_file=0
                for exclude_pattern in "${exclude_patterns[@]}"; do
                    if [[ $USE_REGEX -eq 1 ]]; then
                        if [[ "$(basename "$file")" =~ $exclude_pattern ]]; then
                            exclude_file=1
                            break
                        fi
                    else
                        if [[ "$(basename "$file")" = $exclude_pattern ]]; then
                            exclude_file=1
                            break
                        fi
                    fi
                done
                
                if [[ $exclude_file -eq 1 ]]; then
                    ((excluded_files++))
                    echo "    Excluded: $file" >> "$LOG_FILE"
                    continue
                fi
                
                # Check file size if MAX_SIZE is set
                if [[ $MAX_SIZE -gt 0 ]]; then
                    local file_size_kb=$(du -k "$file" | awk '{print $1}')
                    local file_size_mb=$((file_size_kb / 1024))
                    
                    if (( file_size_mb > MAX_SIZE )); then
                        ((size_exceeded_files++))
                        echo "    Size exceeded ($file_size_mb MB): $file" >> "$LOG_FILE"
                        continue
                    fi
                fi
                
                # Add file to processing list
                all_files_to_process+=("$file")
                
                # Check if file already exists in destination
                filename=$(basename "$file")
                if [[ ! -f "$DEST_DIR/$filename" ]]; then
                    all_files_to_copy+=("$file")
                fi
            done <<< "$found"
        fi
    done
    
    # If pattern wasn't found in any source directory, log it
    if [[ $pattern_found -eq 0 ]]; then
        echo "  No files found matching: $file_pattern in any source directory" >> "$LOG_FILE"
        echo "$file_pattern" >> "$MISSING_FILES_LOG"
        missing_patterns_array+=("$file_pattern")
        ((missing_patterns++))
    fi
done

# Calculate total size of files to copy
total_size_bytes=$(calculate_total_size "${all_files_to_copy[@]}")
total_size_kb=$((total_size_bytes / 1024))

# Check if there's enough disk space
if ! check_disk_space "$DEST_DIR" "$total_size_kb"; then
    echo "Error: Insufficient disk space for copy operation" >> "$LOG_FILE"
    exit 1
fi

# Log information about files to copy
echo "Files to process: ${#all_files_to_process[@]}" >> "$LOG_FILE"
echo "Files to copy: ${#all_files_to_copy[@]}" >> "$LOG_FILE"
echo "Total copy size: $((total_size_kb / 1024)) MB" >> "$LOG_FILE"

# Show initial progress message
if [[ $SHOW_PROGRESS -eq 1 ]]; then
    echo "Files to process: ${#all_files_to_process[@]}"
    echo "Files to copy: ${#all_files_to_copy[@]}"
    echo "Total copy size: $((total_size_kb / 1024)) MB"
    echo ""
    echo "Starting copy operation..."
    display_progress 0 ${#all_files_to_process[@]}
fi

# Process each file
current_file=0
for file in "${all_files_to_process[@]}"; do
    ((current_file++))
    
    # Extract just the filename
    filename=$(basename "$file")
    
    # Log the found file
    echo "  Processing: $file" >> "$LOG_FILE"
    ((found_files++))
    
    # Check if destination file already exists
    if [[ -f "$DEST_DIR/$filename" ]]; then
        echo "  SKIPPED: File already exists in destination: $filename" >> "$LOG_FILE"
        echo "$filename" >> "$EXISTING_FILES_LOG"
        ((skipped_files++))
        ((existing_files++))
    else
        # Get file size for reporting
        file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        
        # Copy the file to destination
        if cp "$file" "$DEST_DIR/"; then
            echo "  Copied to: $DEST_DIR/$filename" >> "$LOG_FILE"
            ((copied_files++))
            ((total_bytes_copied += file_size))
        else
            echo "  ERROR: Failed to copy: $file" >> "$LOG_FILE"
        fi
    fi
    
    # Update progress display
    if [[ $SHOW_PROGRESS -eq 1 ]]; then
        display_progress "$current_file" "${#all_files_to_process[@]}"
    fi
done

# Complete the progress display
if [[ $SHOW_PROGRESS -eq 1 ]]; then
    echo ""  # New line after progress bar
fi

# Log summary statistics
{
    echo "" >> "$LOG_FILE"
    echo "======================================================" >> "$LOG_FILE"
    echo "Summary - $(date)" >> "$LOG_FILE"
    echo "Source directories searched: ${#SOURCE_DIRS[@]}" >> "$LOG_FILE"
    echo "Patterns processed: $total_patterns" >> "$LOG_FILE"
    echo "Files found: $found_files" >> "$LOG_FILE"
    echo "Files copied: $copied_files" >> "$LOG_FILE"
    echo "Files skipped (already existed): $skipped_files" >> "$LOG_FILE"
    echo "Patterns with no matches: $missing_patterns" >> "$LOG_FILE"
    echo "Files excluded by pattern: $excluded_files" >> "$LOG_FILE"
    echo "Files excluded by size: $size_exceeded_files" >> "$LOG_FILE"
    echo "Total data copied: $((total_bytes_copied / 1024 / 1024)) MB" >> "$LOG_FILE"
    echo "======================================================" >> "$LOG_FILE"
} || echo "Failed to write summary to log file"

# Output summary to console
echo "Operation completed. See $LOG_FILE for details."
echo "Source directories searched: ${#SOURCE_DIRS[@]}"
echo "Patterns processed: $total_patterns"
echo "Files found: $found_files"
echo "Files copied: $copied_files"
echo "Files skipped (already existed): $skipped_files"
echo "Patterns with no matches: $missing_patterns"
if [[ $excluded_files -gt 0 ]]; then
    echo "Files excluded by pattern: $excluded_files"
fi
if [[ $size_exceeded_files -gt 0 ]]; then
    echo "Files excluded by size: $size_exceeded_files"
fi
echo "Total data copied: $((total_bytes_copied / 1024 / 1024)) MB"

# Display information about additional log files
if [[ $missing_patterns -gt 0 ]]; then
    echo "Missing files log: $MISSING_FILES_LOG ($missing_patterns patterns with no matches)"
fi

if [[ $existing_files -gt 0 ]]; then
    echo "Existing files log: $EXISTING_FILES_LOG ($existing_files files already in destination)"
fi

exit 0
