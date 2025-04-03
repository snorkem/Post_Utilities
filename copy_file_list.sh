#!/bin/zsh

# ================================================
# File Search and Copy Utility v2.8
# ================================================
# This script searches for files in one or more source directories
# based on a list of filenames (with wildcard support) and copies
# them to a destination directory. All operations are logged to a
# detailed log file.
# The script will:
# - Parse EDL files to extract source filenames (when --edl flag is used)
# - Search across multiple source directories
# - Skip any files that already exist in the destination
# - Append to the log file if it already exists
# - Track missing files and existing files in separate logs
# - Show progress during file copy operations
# - Check available disk space before starting
# - Support advanced pattern matching including regex
# - Support dry run mode to preview what would be copied
# - Use case-insensitive search when processing EDL files
# ================================================

# Display usage information with examples
usage() {
    SCRIPT_NAME=$(basename "$0")
    cat << EOF
Usage: ${SCRIPT_NAME} -s SOURCE_DIR1[,SOURCE_DIR2,...] -d DEST_DIR (-f FILE_LIST | --edl EDL_FILE) -l LOG_FILE [OPTIONS]

Required Options:
  -s SOURCE_DIRS  One or more directories to search in (comma-separated)
  -d DEST_DIR     Directory to copy files to
  -l LOG_FILE     Log file to write operations to (will append if exists)

File List Options (must use one of these):
  -f FILE_LIST    File containing list of filenames to search for (one per line)
  --edl EDL_FILE  Parse an EDL file to extract source filenames (uses case-insensitive search)

Additional Options:
  -p              Show progress during copy operations
  -r              Use regular expressions instead of glob patterns
  -m MAX_SIZE     Skip files larger than MAX_SIZE (in MB)
  -x EXCLUDE_FILE Skip files that match patterns in EXCLUDE_FILE
  -n              Perform a dry run (no actual file copying)
  -h              Display this help message

Advanced Pattern Matching:
  By default, the script uses glob patterns (*, ?, [abc], etc.).
  When -r is specified, patterns are treated as regular expressions.
  When --edl is used, search is automatically case-insensitive to handle uppercase EDL filenames.

Examples:
  # Using a simple file list:
  ${SCRIPT_NAME} -s /path/source1,/path/source2 -d /path/dest -f files.txt -l log.txt

  # Parsing an EDL file to extract source filenames:
  ${SCRIPT_NAME} -s /path/source1,/path/source2 -d /path/dest --edl project.edl -l log.txt

  # Perform a dry run with an EDL file:
  ${SCRIPT_NAME} -s /path/source1,/path/source2 -d /path/dest --edl project.edl -l log.txt -n
  
  # Using glob patterns (default):
  # First create a file list:
  #   echo "*.jpg" > files.txt       # Match all JPG files
  #   echo "doc_*.pdf" >> files.txt  # Match PDFs starting with "doc_"
  #   echo "file_[0-9].txt" >> files.txt  # Match file_0.txt through file_9.txt
  # Then run:
  ${SCRIPT_NAME} -s /path/source1,/path/source2 -d /path/dest -f files.txt -l log.txt

  # Using regular expressions (with -r flag):
  # First create a file with regex patterns:
  #   echo "^.*\\.jpg$" > regex.txt         # Match all JPG files
  #   echo "^doc_.*\\.pdf$" >> regex.txt    # Match PDFs starting with "doc_"
  #   echo "^file_[0-9]\\.txt$" >> regex.txt  # Match file_0.txt through file_9.txt
  #   echo "^(report|summary)_.*$" >> regex.txt  # Match files starting with "report_" or "summary_"
  # Then run:
  ${SCRIPT_NAME} -s /path/source1,/path/source2 -d /path/dest -f regex.txt -l log.txt -r

  # Exclude patterns (with -x flag):
  # First create an exclude list:
  #   echo "*.tmp" > exclude.txt  # Exclude all .tmp files
  # Then run:
  ${SCRIPT_NAME} -s /path/source1,/path/source2 -d /path/dest -f files.txt -l log.txt -x exclude.txt
EOF
    exit 1
}

# Progress bar function for EDL parsing
show_edl_parse_progress() {
    local current_line="$1"
    local total_lines="$2"
    local width=50
    
    # Calculate percentage
    local percent=$((current_line * 100 / total_lines))
    local completed=$((width * current_line / total_lines))
    
    # Clear the current line and print progress bar
    printf "\r[EDL Parsing Progress] ["
    printf "%${completed}s" | tr ' ' '#'
    printf "%$((width - completed))s" | tr ' ' ' '
    printf "] %3d%% (%d/%d lines)" "$percent" "$current_line" "$total_lines"
    
    # Ensure the progress bar is fully printed on completion
    if [[ $current_line -eq $total_lines ]]; then
        printf "\n"
    fi
}

# Modify parse_edl_file to include progress tracking
parse_edl_file() {
    local edl_file="$1"
    local output_file="$2"
    
    echo "Parsing EDL file: $edl_file"
    
    # Count total lines in the EDL file
    local total_lines=$(grep -c "*SOURCE FILE:" "$edl_file")
    echo "Total SOURCE FILE lines: $total_lines"
    
    # Create a temporary file to track progress
    local temp_output=$(mktemp)
    
    # Counter for progress
    local current_line=0
    
    # Process SOURCE FILE lines with progress tracking
    while IFS= read -r line; do
        # Extract filename and add to output
        echo "$line" | sed 's/\*SOURCE FILE: *//' >> "$temp_output"
        
        # Increment line counter
        ((current_line++))
        
        # Show progress
        show_edl_parse_progress "$current_line" "$total_lines"
    done < <(grep "*SOURCE FILE:" "$edl_file")
    
    # Sort and remove duplicates
    sort -u "$temp_output" > "$output_file"
    
    # Remove temporary file
    rm "$temp_output"
    
    local file_count=$(wc -l < "$output_file")
    echo "Found $file_count unique source files in EDL"
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

# New progress bar function for pattern searching
show_pattern_search_progress() {
    local current_pattern="$1"
    local total_patterns="$2"
    local current_pattern_name="$3"
    local width=50
    
    # Calculate percentage
    local percent=$((current_pattern * 100 / total_patterns))
    local completed=$((width * current_pattern / total_patterns))
    
    # Use \r to return to start of line and overwrite
    printf "\r[Pattern Search Progress] ["
    printf "%${completed}s" | tr ' ' '#'
    printf "%$((width - completed))s" | tr ' ' ' '
    printf "] %3d%% (%d/%d patterns)" "$percent" "$current_pattern" "$total_patterns"

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
EDL_FILE=""
LOG_FILE=""
SHOW_PROGRESS=0
USE_REGEX=0
MAX_SIZE=0  # No limit by default
EXCLUDE_FILE=""
DRY_RUN=0   # Actual copy by default
CASE_SENSITIVE=1 # Default to case-sensitive matching
EDL_GLOB_MODE=1 # Default to enhanced glob pattern for EDL (*.* wildcard)

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s)
            IFS=',' read -rA SOURCE_DIRS <<< "$2"
            shift 2
            ;;
        -d)
            DEST_DIR="$2"
            shift 2
            ;;
        -f)
            FILE_LIST="$2"
            shift 2
            ;;
        --edl)
            EDL_FILE="$2"
            CASE_SENSITIVE=0 # EDL files typically have uppercase filenames, use case-insensitive search
            shift 2
            ;;
        -l)
            LOG_FILE="$2"
            shift 2
            ;;
        -p)
            SHOW_PROGRESS=1
            shift
            ;;
        -r)
            USE_REGEX=1
            shift
            ;;
        -m)
            MAX_SIZE="$2"
            shift 2
            ;;
        -x)
            EXCLUDE_FILE="$2"
            shift 2
            ;;
        -n)
            DRY_RUN=1
            shift
            ;;
        -h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [[ ${#SOURCE_DIRS[@]} -eq 0 || -z "$DEST_DIR" || -z "$LOG_FILE" ]]; then
    echo "Error: Missing required parameters"
    usage
fi

# Ensure we have either FILE_LIST or EDL_FILE
if [[ -z "$FILE_LIST" && -z "$EDL_FILE" ]]; then
    echo "Error: Either FILE_LIST (-f) or EDL_FILE (--edl) must be specified"
    usage
fi

if [[ -n "$FILE_LIST" && -n "$EDL_FILE" ]]; then
    echo "Error: Cannot specify both FILE_LIST (-f) and EDL_FILE (--edl)"
    usage
fi

# Ensure source directories exist
for src_dir in "${SOURCE_DIRS[@]}"; do
    if [[ ! -d "$src_dir" ]]; then
        echo "Error: Source directory does not exist: $src_dir"
        exit 1
    fi
done

# If using an EDL file, ensure it exists
if [[ -n "$EDL_FILE" ]]; then
    if [[ ! -f "$EDL_FILE" ]]; then
        echo "Error: EDL file does not exist: $EDL_FILE"
        exit 1
    fi
    
    # Create a temporary file to store the extracted file list
    TEMP_FILE_LIST=$(mktemp)
    parse_edl_file "$EDL_FILE" "$TEMP_FILE_LIST"
    FILE_LIST="$TEMP_FILE_LIST"
    
    echo "Using file list extracted from EDL: $FILE_LIST"
else
    # Ensure file list exists
    if [[ ! -f "$FILE_LIST" ]]; then
        echo "Error: File list does not exist: $FILE_LIST"
        exit 1
    fi
fi

# Check exclude file if specified
if [[ -n "$EXCLUDE_FILE" && ! -f "$EXCLUDE_FILE" ]]; then
    echo "Error: Exclude file does not exist: $EXCLUDE_FILE"
    exit 1
fi

# Create destination directory if it doesn't exist and not in dry run mode
if [[ ! -d "$DEST_DIR" && $DRY_RUN -eq 0 ]]; then
    mkdir -p "$DEST_DIR"
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to create destination directory: $DEST_DIR"
        exit 1
    fi
    echo "Created destination directory: $DEST_DIR"
elif [[ ! -d "$DEST_DIR" && $DRY_RUN -eq 1 ]]; then
    echo "Note: Destination directory does not exist, but would be created in actual run: $DEST_DIR"
fi

# Check if log file directory exists and is writable
LOG_DIR=$(dirname "$LOG_FILE")
if [[ ! -d "$LOG_DIR" ]]; then
    if [[ $DRY_RUN -eq 0 ]]; then
        mkdir -p "$LOG_DIR"
        if [[ $? -ne 0 ]]; then
            echo "Error: Failed to create log directory: $LOG_DIR"
            exit 1
        fi
    else
        echo "Note: Log directory does not exist, but would be created in actual run: $LOG_DIR"
    fi
fi

# Set up additional log files for tracking missing and existing files
MISSING_FILES_LOG="${LOG_FILE}.missing.txt"
EXISTING_FILES_LOG="${LOG_FILE}.existing.txt"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Check if we need to create or append to log files
if [[ $DRY_RUN -eq 0 ]]; then
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
            echo "NEW SESSION: File Search and Copy Operation v2.8 - $(date)" >> "$LOG_FILE"
            echo "======================================================" >> "$LOG_FILE"
        }; then
            echo "Error: Cannot write to log file: $LOG_FILE"
            exit 1
        fi
    else
        # Create new log file with initial header
        if ! {
            echo "======================================================" > "$LOG_FILE"
            echo "File Search and Copy Operation v2.8 - $(date)" >> "$LOG_FILE"
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
    if [[ -n "$EDL_FILE" ]]; then
        echo "EDL File: $EDL_FILE" >> "$LOG_FILE"
        echo "Using case-insensitive file matching" >> "$LOG_FILE"
        echo "Using enhanced glob patterns with *.* wildcard" >> "$LOG_FILE"
    fi
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
else
    # For dry run, create a temporary log file
    DRY_RUN_LOG=$(mktemp)
    echo "======================================================" > "$DRY_RUN_LOG"
    echo "DRY RUN: File Search and Copy Operation v2.8 - $(date)" >> "$DRY_RUN_LOG"
    echo "======================================================" >> "$DRY_RUN_LOG"
    echo "Source Directories: ${SOURCE_DIRS[*]}" >> "$DRY_RUN_LOG"
    echo "Destination Directory: $DEST_DIR" >> "$DRY_RUN_LOG"
    echo "File List: $FILE_LIST" >> "$DRY_RUN_LOG"
    if [[ -n "$EDL_FILE" ]]; then
        echo "EDL File: $EDL_FILE" >> "$DRY_RUN_LOG"
        echo "Using case-insensitive file matching" >> "$DRY_RUN_LOG"
        echo "Using enhanced glob patterns with *.* wildcard" >> "$DRY_RUN_LOG"
    fi
    if [[ $USE_REGEX -eq 1 ]]; then
        echo "Using regular expressions for pattern matching" >> "$DRY_RUN_LOG"
    fi
    if [[ -n "$EXCLUDE_FILE" ]]; then
        echo "Exclude File: $EXCLUDE_FILE" >> "$DRY_RUN_LOG"
    fi
    if [[ $MAX_SIZE -gt 0 ]]; then
        echo "Maximum File Size: $MAX_SIZE MB" >> "$DRY_RUN_LOG"
    fi
    echo "======================================================" >> "$DRY_RUN_LOG"
    echo "" >> "$DRY_RUN_LOG"
    
    echo "DRY RUN MODE: No files will be copied" >> "$DRY_RUN_LOG"
    echo "" >> "$DRY_RUN_LOG"
fi

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
    
    if [[ $DRY_RUN -eq 0 ]]; then
        echo "Loaded ${#exclude_patterns[@]} exclude patterns" >> "$LOG_FILE"
    else
        echo "Loaded ${#exclude_patterns[@]} exclude patterns" >> "$DRY_RUN_LOG"
    fi
fi

# Create a list of all files to be copied (for progress tracking)
all_files_to_process=()
all_files_to_copy=()

# First pass: identify all files that need to be processed
if [[ $DRY_RUN -eq 0 ]]; then
    echo "Analyzing files to copy..." >> "$LOG_FILE"
else
    echo "Analyzing files that would be copied..." >> "$DRY_RUN_LOG"
fi

if [[ $SHOW_PROGRESS -eq 1 ]]; then
    echo "Analyzing files across ${#SOURCE_DIRS[@]} source directories..."
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

current_pattern=0
total_patterns=${#file_patterns[@]}

# For each pattern, search across all source directories
for file_pattern in "${file_patterns[@]}"; do
    # Increment pattern counter
    ((current_pattern++))
    
    # Show progress for current pattern
    show_pattern_search_progress "$current_pattern" "$total_patterns" "$file_pattern"

    if [[ $DRY_RUN -eq 0 ]]; then
        echo "Processing pattern: $file_pattern" >> "$LOG_FILE"
    else
        echo "Processing pattern: $file_pattern" >> "$DRY_RUN_LOG"
    fi
    
    # Flag to track if the pattern was found in any source directory
    pattern_found=0
    
    # Search in each source directory
    for src_dir in "${SOURCE_DIRS[@]}"; do
        if [[ $DRY_RUN -eq 0 ]]; then
            echo "  Searching in: $src_dir" >> "$LOG_FILE"
        else
            echo "  Searching in: $src_dir" >> "$DRY_RUN_LOG"
        fi
        
        # Use find with regex or glob pattern and adjust case sensitivity
        if [[ $USE_REGEX -eq 1 ]]; then
            # Use regex pattern with -regex option to find
            if [[ $CASE_SENSITIVE -eq 1 ]]; then
                found=$(find "$src_dir" -type f -regex "$src_dir/$file_pattern" 2>/dev/null)
            else
                found=$(find "$src_dir" -type f -iregex "$src_dir/$file_pattern" 2>/dev/null)
            fi
        else {
            # Use standard glob pattern
            if [[ $CASE_SENSITIVE -eq 1 ]]; then
                found=$(find "$src_dir" -type f -name "$file_pattern" 2>/dev/null)
            else {
                found=$(find "$src_dir" -type f -iname "$file_pattern*" 2>/dev/null)
            }
            fi
        }
        fi
        
        # Process found files
        if [[ -n "$found" ]]; then
            pattern_found=1
            if [[ $DRY_RUN -eq 0 ]]; then
                echo "    Found matches in $src_dir" >> "$LOG_FILE"
            else
                echo "    Found matches in $src_dir" >> "$DRY_RUN_LOG"
            fi
            
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
                    if [[ $DRY_RUN -eq 0 ]]; then
                        echo "    Excluded: $file" >> "$LOG_FILE"
                    else
                        echo "    Excluded: $file" >> "$DRY_RUN_LOG"
                    fi
                    continue
                fi
                
                # Check file size if MAX_SIZE is set
                if [[ $MAX_SIZE -gt 0 ]]; then
                    local file_size_kb=$(du -k "$file" | awk '{print $1}')
                    local file_size_mb=$((file_size_kb / 1024))
                    
                    if (( file_size_mb > MAX_SIZE )); then
                        ((size_exceeded_files++))
                        if [[ $DRY_RUN -eq 0 ]]; then
                            echo "    Size exceeded ($file_size_mb MB): $file" >> "$LOG_FILE"
                        else
                            echo "    Size exceeded ($file_size_mb MB): $file" >> "$DRY_RUN_LOG"
                        fi
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
        if [[ $DRY_RUN -eq 0 ]]; then
            echo "  No files found matching: $file_pattern in any source directory" >> "$LOG_FILE"
            echo "$file_pattern" >> "$MISSING_FILES_LOG"
        else
            echo "  No files found matching: $file_pattern in any source directory" >> "$DRY_RUN_LOG"
        fi
        missing_patterns_array+=("$file_pattern")
        ((missing_patterns++))
    fi
done

# Calculate total size of files to copy
total_size_bytes=$(calculate_total_size "${all_files_to_copy[@]}")
total_size_kb=$((total_size_bytes / 1024))

# Check if there's enough disk space (skip in dry run mode)
if [[ $DRY_RUN -eq 0 ]]; then
    if ! check_disk_space "$DEST_DIR" "$total_size_kb"; then
        echo "Error: Insufficient disk space for copy operation" >> "$LOG_FILE"
        exit 1
    fi
else
    # In dry run mode, just log what we would check
    echo "Would check for at least $((total_size_kb / 1024)) MB of free space in $DEST_DIR" >> "$DRY_RUN_LOG"
fi

# Log information about files to copy
if [[ $DRY_RUN -eq 0 ]]; then
    echo "Files to process: ${#all_files_to_process[@]}" >> "$LOG_FILE"
    echo "Files to copy: ${#all_files_to_copy[@]}" >> "$LOG_FILE"
    echo "Total copy size: $((total_size_kb / 1024)) MB" >> "$LOG_FILE"
else
    echo "Files that would be processed: ${#all_files_to_process[@]}" >> "$DRY_RUN_LOG"
    echo "Files that would be copied: ${#all_files_to_copy[@]}" >> "$DRY_RUN_LOG"
    echo "Total copy size would be: $((total_size_kb / 1024)) MB" >> "$DRY_RUN_LOG"
fi

# Show initial progress message
if [[ $SHOW_PROGRESS -eq 1 ]]; then
    if [[ $DRY_RUN -eq 0 ]]; then
        echo "Files to process: ${#all_files_to_process[@]}"
        echo "Files to copy: ${#all_files_to_copy[@]}"
        echo "Total copy size: $((total_size_kb / 1024)) MB"
        echo ""
        echo "Starting copy operation..."
    else
        echo "Files that would be processed: ${#all_files_to_process[@]}"
        echo "Files that would be copied: ${#all_files_to_copy[@]}"
        echo "Total copy size would be: $((total_size_kb / 1024)) MB"
        echo ""
        echo "Analyzing what would be copied (dry run)..."
    fi
    display_progress 0 ${#all_files_to_process[@]}
fi

# Process each file
current_file=0
for file in "${all_files_to_process[@]}"; do
    ((current_file++))
    
    # Extract just the filename
    filename=$(basename "$file")
    
    # Log the found file
    if [[ $DRY_RUN -eq 0 ]]; then
        echo "  Processing: $file" >> "$LOG_FILE"
    else
        echo "  Would process: $file" >> "$DRY_RUN_LOG"
    fi
    ((found_files++))
    
    # Check if destination file already exists
    if [[ -f "$DEST_DIR/$filename" ]]; then
        if [[ $DRY_RUN -eq 0 ]]; then
            echo "  SKIPPED: File already exists in destination: $filename" >> "$LOG_FILE"
            echo "$filename" >> "$EXISTING_FILES_LOG"
        else
            echo "  WOULD SKIP: File already exists in destination: $filename" >> "$DRY_RUN_LOG"
        fi
        ((skipped_files++))
        ((existing_files++))
    else {
        # Get file size for reporting
        file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        
        if [[ $DRY_RUN -eq 0 ]]; then
            # Actual copy operation
            if cp "$file" "$DEST_DIR/"; then
                echo "  Copied to: $DEST_DIR/$filename" >> "$LOG_FILE"
                ((copied_files++))
                ((total_bytes_copied += file_size))
            else
                echo "  ERROR: Failed to copy: $file" >> "$LOG_FILE"
            fi
        else
            # In dry run mode, just log what would happen
            echo "  WOULD COPY: $file -> $DEST_DIR/$filename" >> "$DRY_RUN_LOG"
            ((copied_files++))
            ((total_bytes_copied += file_size))
        fi
    }
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
if [[ $DRY_RUN -eq 0 ]]; then
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
        if [[ -n "$EDL_FILE" ]]; then
            echo "EDL file parsed: $EDL_FILE" >> "$LOG_FILE"
        fi
        echo "======================================================" >> "$LOG_FILE"
    } || echo "Failed to write summary to log file"
else {
    # For dry run, log to the dry run log
    echo "" >> "$DRY_RUN_LOG"
    echo "======================================================" >> "$DRY_RUN_LOG"
    echo "Dry Run Summary - $(date)" >> "$DRY_RUN_LOG"
    echo "Source directories searched: ${#SOURCE_DIRS[@]}" >> "$DRY_RUN_LOG"
    echo "Patterns processed: $total_patterns" >> "$DRY_RUN_LOG"
    echo "Files found: $found_files" >> "$DRY_RUN_LOG"
    echo "Files that would be copied: $copied_files" >> "$DRY_RUN_LOG"
    echo "Files that would be skipped (already exist): $skipped_files" >> "$DRY_RUN_LOG"
    echo "Patterns with no matches: $missing_patterns" >> "$DRY_RUN_LOG"
    echo "Files excluded by pattern: $excluded_files" >> "$DRY_RUN_LOG"
    echo "Files excluded by size: $size_exceeded_files" >> "$DRY_RUN_LOG"
    echo "Total data that would be copied: $((total_bytes_copied / 1024 / 1024)) MB" >> "$DRY_RUN_LOG"
    if [[ -n "$EDL_FILE" ]]; then
        echo "EDL file parsed: $EDL_FILE" >> "$DRY_RUN_LOG"
    fi
    echo "======================================================" >> "$DRY_RUN_LOG"
    
    # Copy dry run log to the specified log file so it can be viewed later
    cp "$DRY_RUN_LOG" "$LOG_FILE"
    
    # Clean up temporary log file
    rm "$DRY_RUN_LOG"
}
fi

# Output summary to console
if [[ $DRY_RUN -eq 0 ]]; then
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
    if [[ -n "$EDL_FILE" ]]; then
        echo "EDL file parsed: $EDL_FILE"
    fi
else
    echo "Dry run completed. See $LOG_FILE for details."
    echo "Source directories searched: ${#SOURCE_DIRS[@]}"
    echo "Patterns processed: $total_patterns"
    echo "Files found: $found_files"
    echo "Files that would be copied: $copied_files"
    echo "Files that would be skipped (already exist): $skipped_files"
    echo "Patterns with no matches: $missing_patterns"
    if [[ $excluded_files -gt 0 ]]; then
        echo "Files excluded by pattern: $excluded_files"
    fi
    if [[ $size_exceeded_files -gt 0 ]]; then
        echo "Files excluded by size: $size_exceeded_files"
    fi
    echo "Total data that would be copied: $((total_bytes_copied / 1024 / 1024)) MB"
    if [[ -n "$EDL_FILE" ]]; then
        echo "EDL file parsed: $EDL_FILE"
    fi
fi

# Display information about additional log files
if [[ $DRY_RUN -eq 0 ]]; then
    if [[ $missing_patterns -gt 0 ]]; then
        echo "Missing files log: $MISSING_FILES_LOG ($missing_patterns patterns with no matches)"
    fi

    if [[ $existing_files -gt 0 ]]; then
        echo "Existing files log: $EXISTING_FILES_LOG ($existing_files files already in destination)"
    fi
fi

# Clean up temporary file list if it was created from an EDL file
if [[ -n "$EDL_FILE" && -f "$TEMP_FILE_LIST" ]]; then
    echo "Removing temporary file list extracted from EDL"
    rm "$TEMP_FILE_LIST"
fi

exit 0
