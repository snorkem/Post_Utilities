#!/usr/bin/env python3
"""
File Search and Copy Utility v3.1
==================================
This script searches for files in one or more source directories
based on a list of filenames or by parsing an EDL file, then copies
them to a destination directory. All operations are logged to detailed log files.

The script provides robust error handling, detailed logging, and multiple
strategies for locating files specified in EDL files.

Author: Claude
Version: 3.1
"""

import os
import sys
import re
import shutil
import argparse
import subprocess
import time
import datetime
import signal
import hashlib
import chardet
from typing import List, Dict, Set, Tuple, Optional, Union, Any
from pathlib import Path
import fnmatch
import logging
import traceback
import tempfile
import multiprocessing
from multiprocessing import Pool
import xxhash


# Set up signal handlers for graceful termination
def setup_signal_handlers():
    """Configure signal handlers for graceful termination."""
    def signal_handler(sig, frame):
        print("\nReceived termination signal. Cleaning up...")
        sys.exit(130)  # 128 + SIGINT(2) = 130
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


class ProgressBar:
    """Simple progress bar utility for displaying progress during operations."""
    
    def __init__(self, total: int, width: int = 50, prefix: str = 'Progress'):
        self.total = max(1, total)  # Avoid division by zero
        self.width = width
        self.prefix = prefix
        self.count = 0
        self.start_time = time.time()
        
    def update(self, count: Optional[int] = None) -> None:
        """Update progress bar with current count."""
        if count is not None:
            self.count = count
        else:
            self.count += 1
        
        # Calculate progress metrics    
        percent = min(100, self.count * 100 // self.total)
        filled_width = self.width * self.count // self.total
        bar = '#' * filled_width + ' ' * (self.width - filled_width)
        
        # Calculate ETA if we have progress
        if self.count > 0:
            elapsed = time.time() - self.start_time
            rate = self.count / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.count) / rate if rate > 0 else 0
            eta_str = f"ETA: {self._format_time(remaining)}" if self.count < self.total else f"Time: {self._format_time(elapsed)}"
        else:
            eta_str = "ETA: --:--"
        
        # Update the progress display
        sys.stdout.write(f'\r{self.prefix}: [{bar}] {percent}% ({self.count}/{self.total}) {eta_str}')
        sys.stdout.flush()
        
        if self.count >= self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into a human-readable time string."""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"


class Logger:
    """Handles all logging operations for the script."""
    
    def __init__(self, log_file: str, dry_run: bool = False, debug: bool = False):
        self.log_file = log_file
        self.dry_run = dry_run
        self.debug_mode = debug
        self.missing_log = f"{log_file}.missing.txt"
        self.existing_log = f"{log_file}.existing.txt"
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Set up regular logging with appropriate level
        log_level = logging.DEBUG if debug else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger('file_copier')
        
        # Create log directory and initialize log files in normal mode
        if not dry_run:
            self._initialize_log_files()
        
        # For debug mode, also log to debug file
        if debug:
            self.debug_log = f"{log_file}.debug.txt"
            os.makedirs(os.path.dirname(self.debug_log), exist_ok=True)
            debug_handler = logging.FileHandler(self.debug_log, mode='w')
            debug_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(debug_handler)
            
            self.debug(f"Debug logging initialized to: {self.debug_log}")
    
    def _initialize_log_files(self) -> None:
        """Initialize or append to log files with headers."""
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize or append to missing files log
        self._initialize_or_append_log(
            self.missing_log, 
            "=== Missing Files Log ===", 
            f"=== {'First' if not os.path.exists(self.missing_log) else ''} Session: {self.timestamp} ==="
        )
        
        # Initialize or append to existing files log
        self._initialize_or_append_log(
            self.existing_log, 
            "=== Existing Files Log ===", 
            f"=== {'First' if not os.path.exists(self.existing_log) else ''} Session: {self.timestamp} ==="
        )
        
        # Initialize or append to main log file
        self._initialize_or_append_log(
            self.log_file, 
            "======================================================", 
            f"{'NEW SESSION: ' if os.path.exists(self.log_file) else ''}File Search and Copy Operation v3.1 - {datetime.datetime.now()}"
        )
    
    def _initialize_or_append_log(self, log_path: str, header: str, session_header: str) -> None:
        """Initialize or append to a log file with appropriate headers."""
        try:
            mode = 'a' if os.path.exists(log_path) else 'w'
            with open(log_path, mode, encoding='utf-8') as f:
                if mode == 'a':
                    f.write("\n\n")
                f.write(f"{header}\n")
                f.write(f"{session_header}\n")
        except Exception as e:
            self.logger.error(f"Error initializing log file {log_path}: {str(e)}")
    
    def log(self, message: str, console: bool = True) -> None:
        """Log a message to the log file and optionally to the console."""
        try:
            if self.dry_run:
                # For dry run, just print to console
                if console:
                    self.logger.info(message)
            else:
                # Log to file
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{message}\n")
                
                # Also log to console if requested
                if console:
                    self.logger.info(message)
        except Exception as e:
            # Fall back to console if file logging fails
            self.logger.error(f"Error writing to log file: {str(e)}")
            if console:
                self.logger.info(message)
    
    def debug(self, message: str) -> None:
        """Log a debug message if debug mode is enabled."""
        if self.debug_mode:
            self.logger.debug(f"DEBUG: {message}")
            
            # Also log to debug file if not in dry run mode
            if not self.dry_run:
                try:
                    with open(self.debug_log, 'a', encoding='utf-8') as f:
                        f.write(f"{datetime.datetime.now()} - DEBUG: {message}\n")
                except Exception as e:
                    self.logger.error(f"Error writing to debug log: {str(e)}")
    
    def log_missing(self, pattern: str) -> None:
        """Log a missing pattern to the missing files log."""
        if not self.dry_run:
            try:
                with open(self.missing_log, 'a', encoding='utf-8') as f:
                    f.write(f"{pattern}\n")
            except Exception as e:
                self.logger.error(f"Error writing to missing files log: {str(e)}")
    
    def log_existing(self, filename: str) -> None:
        """Log an existing file to the existing files log."""
        if not self.dry_run:
            try:
                with open(self.existing_log, 'a', encoding='utf-8') as f:
                    f.write(f"{filename}\n")
            except Exception as e:
                self.logger.error(f"Error writing to existing files log: {str(e)}")


class EDLParser:
    """Handles parsing of EDL files to extract source filenames."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def parse_edl_file(self, edl_file: str) -> List[str]:
        """
        Parse an EDL file to extract source filenames.
        Returns a list of unique source filenames.
        
        Args:
            edl_file: Path to the EDL file
            
        Returns:
            List of unique source filenames found in the EDL
            
        Raises:
            ValueError: If the EDL file does not contain any SOURCE FILE fields
        """
        self.logger.log(f"Parsing EDL file: {edl_file}")
        
        # Detect file encoding
        encoding = self._detect_file_encoding(edl_file)
        self.logger.debug(f"Detected encoding for {edl_file}: {encoding}")
        
        try:
            # Read the entire file content
            with open(edl_file, 'r', encoding=encoding, errors='replace') as f:
                edl_content = f.read()
            
            # Check if the EDL contains any SOURCE FILE fields
            if not re.search(r'\*SOURCE FILE:', edl_content):
                error_msg = f"Error: EDL file does not contain any SOURCE FILE fields\n" \
                          f"This EDL appears to be invalid or incomplete. Processing aborted."
                self.logger.log(error_msg)
                raise ValueError(error_msg)
            
            # Split the file into lines to get a more accurate count
            lines = edl_content.splitlines()
            
            # Find all SOURCE FILE lines
            source_file_lines = []
            for line in lines:
                if '*SOURCE FILE:' in line:
                    source_file_lines.append(line)
            
            total_lines = len(source_file_lines)
            self.logger.log(f"Total SOURCE FILE lines found: {total_lines}")
            
            # Create progress bar if more than 10 files
            progress = ProgressBar(total_lines, prefix='EDL Parsing Progress') if total_lines > 10 else None
            
            # Process SOURCE FILE lines
            unique_files = set()
            for i, line in enumerate(source_file_lines):
                # Extract filename - using the split approach for robustness
                if '*SOURCE FILE:' in line:
                    # Get everything after *SOURCE FILE:
                    filename = line.split('*SOURCE FILE:', 1)[1].strip()
                    if filename:  # Only add non-empty filenames
                        unique_files.add(filename)
                        self.logger.debug(f"Found source file: {filename}")
                
                # Update progress bar
                if progress:
                    progress.update(i + 1)
            
            # Convert to sorted list
            result = sorted(list(unique_files))
            self.logger.log(f"Found {len(result)} unique source files in EDL")
            
            # Log first few patterns for debugging
            if result:
                self.logger.log("First 5 source files found in EDL:")
                for i, file in enumerate(result[:5]):
                    self.logger.log(f"  {i+1}. {file}")
            
            return result
            
        except Exception as e:
            self.logger.log(f"Error parsing EDL file: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise
    
    def _detect_file_encoding(self, file_path: str) -> str:
        """
        Detect the encoding of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected encoding
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)  # Read a sample of the file
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
            confidence = result['confidence']
            
            # If confidence is low, try to be more cautious
            if confidence < 0.7:
                self.logger.debug(f"Low confidence ({confidence}) in detected encoding {encoding}. Fallback to utf-8.")
                return 'utf-8'
                
            return encoding
        except Exception as e:
            self.logger.debug(f"Error detecting file encoding: {str(e)}")
            return 'utf-8'  # Default to UTF-8 in case of error


class FileFinder:
    """Handles finding files based on patterns across source directories."""
    
    def __init__(self, logger: Logger, case_sensitive: bool = True, use_regex: bool = False, 
                 max_workers: Optional[int] = None):
        self.logger = logger
        self.case_sensitive = case_sensitive
        self.use_regex = use_regex
        self.max_workers = max_workers
        # Track statistics
        self.dirs_searched_set = set()  # To keep track of unique directories
        self.total_dirs_searched = 0
        
        if self.max_workers is None:
            # Use half of available CPU cores by default
            self.max_workers = max(1, multiprocessing.cpu_count() // 2)
        self.logger.debug(f"Initialized FileFinder with {self.max_workers} max workers")
    
    def reset_statistics(self):
        """Reset search statistics."""
        self.dirs_searched_set = set()
        self.total_dirs_searched = 0
        
    def find_files_parallel(self, patterns: List[str], source_dirs: List[str], exclude_patterns: List[str] = None,
                          max_size_mb: int = 0) -> Dict[str, Tuple[List[str], bool]]:
        """
        Find files matching multiple patterns across source directories using parallel processing.
        
        Args:
            patterns: List of file patterns to search for
            source_dirs: List of directories to search
            exclude_patterns: List of patterns to exclude
            max_size_mb: Maximum file size in MB (0 for no limit)
            
        Returns:
            Dictionary mapping each pattern to a tuple (found_files, pattern_found)
        """
        # Use the sequential debug version instead - much more reliable
        return self.find_files_sequential(patterns, source_dirs, exclude_patterns, max_size_mb)
    
    def find_files_sequential(self, patterns: List[str], source_dirs: List[str], exclude_patterns: List[str] = None,
                            max_size_mb: int = 0) -> Dict[str, Tuple[List[str], bool]]:
        """
        Sequential version of find_files_parallel.
        
        This processes each pattern one by one with detailed logging.
        """
        self.logger.log("Using sequential processing with detailed logging")
        self.reset_statistics()
        
        # Dictionary to store results
        pattern_to_files = {}
        all_dirs_searched = set()
        
        # Process each pattern
        for pattern in patterns:
            try:
                self.logger.debug(f"Processing pattern: {pattern}")
                
                # Find files for this pattern
                found_files, pattern_found, dirs_searched = self.find_file(
                    pattern, source_dirs, exclude_patterns, max_size_mb
                )
                
                # Store results
                pattern_to_files[pattern] = (found_files, pattern_found)
                all_dirs_searched.update(dirs_searched)
                
                # Log results
                if found_files:
                    self.logger.debug(f"Found {len(found_files)} files for pattern {pattern}")
                    for i, file_path in enumerate(found_files[:3]):
                        self.logger.debug(f"  Match {i+1}: {file_path}")
                else:
                    self.logger.debug(f"No files found for pattern {pattern}")
            
            except Exception as e:
                self.logger.log(f"Error processing pattern {pattern}: {str(e)}")
                self.logger.debug(traceback.format_exc())
                # Store empty results in case of error
                pattern_to_files[pattern] = ([], False)
        
        # Store the directories searched
        self.dirs_searched_set = all_dirs_searched
        self.total_dirs_searched = len(self.dirs_searched_set)
        
        return pattern_to_files
    
    @staticmethod
    def _parallel_search_task(pattern: str, source_dirs: List[str], case_sensitive: bool, 
                            use_regex: bool, exclude_patterns: List[str] = None,
                            max_size_mb: int = 0) -> Tuple[str, List[str], bool, Set[str]]:
        """
        Static task function for parallel file finding.
        This avoids issues with pickling class methods in multiprocessing.
        
        Returns:
            Tuple (pattern, found_files, pattern_found, dirs_searched)
        """
        try:
            # Set up minimal logging for worker processes
            worker_logger = logging.getLogger(f"worker-{os.getpid()}")
            worker_logger.setLevel(logging.INFO)
            
            # Create local finder
            finder = FileFinder(worker_logger, case_sensitive, use_regex)
            
            # Find files
            found_files, pattern_found, dirs_searched = finder.find_file(
                pattern, source_dirs, exclude_patterns, max_size_mb
            )
            
            return pattern, found_files, pattern_found, dirs_searched
        except Exception as e:
            # Create a basic logger for error reporting
            logging.error(f"Error in parallel search task for pattern {pattern}: {str(e)}")
            logging.debug(traceback.format_exc())
            return pattern, [], False, set()
    
    def find_file(self, pattern: str, source_dirs: List[str], exclude_patterns: List[str] = None, 
             max_size_mb: int = 0, first_match_only: bool = False) -> Tuple[List[str], bool, Set[str]]:
        """
        Find files matching a pattern across source directories.
        
        Args:
            pattern: File pattern to search for
            source_dirs: List of directories to search
            exclude_patterns: List of patterns to exclude
            max_size_mb: Maximum file size in MB (0 for no limit)
            
        Returns:
            Tuple (list of found files, pattern_found flag, set of directories searched)
        """
        found_files = []
        pattern_found = False
        dirs_searched = set()
        
        # Log the pattern being processed
        self.logger.log(f"Processing pattern: {pattern}", console=False)
        self.logger.debug(f"Searching for pattern: {pattern} in {len(source_dirs)} directories")
        
        for src_dir in source_dirs:
            self.logger.log(f"  Searching in: {src_dir}", console=False)
            
            # Track directories searched
            matches, subdirs_searched = self._find_matches(pattern, src_dir, first_match_only)
            
            if matches:
                pattern_found = True
                self.logger.log(f"    Found matches in {src_dir}", console=False)
                
                # Process each found file
                for file_path in matches:
                    # Make sure file exists and is readable
                    if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                        self.logger.debug(f"Skipping inaccessible file: {file_path}")
                        continue
                    
                    # Skip files that match exclude patterns
                    if exclude_patterns and self._should_exclude(file_path, exclude_patterns):
                        self.logger.log(f"    Excluded: {file_path}", console=False)
                        continue
                    
                    # Skip files that exceed max size
                    if max_size_mb > 0:
                        try:
                            file_size_mb = self._get_file_size_mb(file_path)
                            if file_size_mb > max_size_mb:
                                self.logger.log(f"    Size exceeded ({file_size_mb:.2f} MB): {file_path}", console=False)
                                continue
                        except (OSError, IOError) as e:
                            self.logger.debug(f"Error checking file size for {file_path}: {str(e)}")
                            continue
                    
                    # Add file to found files
                    found_files.append(file_path)
        
        return found_files, pattern_found, dirs_searched
    
    def _find_matches(self, pattern: str, src_dir: str, first_match_only: bool = False) -> Tuple[List[str], Set[str]]:
        """
        Find files matching pattern in source directory using appropriate method.
        Enhanced with debug statements to trace directory traversal.
        
        Args:
            pattern: File pattern to search for
            src_dir: Directory to search in
            first_match_only: If True, stop after finding the first match
            
        Returns:
            Tuple (list of matching files, set of directories searched)
        """
        matches = []  # Use a list to maintain order of discovery
        dirs_searched = set()
        
        self.logger.debug(f"Searching for '{pattern}' in {src_dir} (first_match_only={first_match_only})")
        
        # Debug counters
        subdirectory_count = 0
        file_count = 0
        
        try:
            # Ensure the source directory exists and is readable
            if not os.path.isdir(src_dir):
                self.logger.debug(f"Source directory does not exist: {src_dir}")
                return matches, dirs_searched
                
            if not os.access(src_dir, os.R_OK):
                self.logger.debug(f"Source directory is not readable: {src_dir}")
                return matches, dirs_searched
            
            # For EDL files with case-insensitive searches
            if not self.case_sensitive:
                self.logger.debug(f"Using case-insensitive search for pattern: {pattern}")
                
                # Convert pattern to uppercase for comparison
                upper_pattern = pattern.upper()
                
                # Extract base name if pattern has extension
                base_pattern = os.path.splitext(upper_pattern)[0] if '.' in pattern else upper_pattern
                self.logger.debug(f"Extracted base pattern: {base_pattern}")
                
                # Process ampersands and special characters for better matching
                special_char_pattern = re.sub(r'[&\s\(\)\[\]\-\+\.]', '.', upper_pattern)
                
                # First pass: Look for all matching files
                for root, dirs, files in os.walk(src_dir):
                    # Track this directory
                    dirs_searched.add(root)
                    subdirectory_count += 1
                    
                    # Debug directory traversal
                    if subdirectory_count % 20 == 0:
                        self.logger.debug(f"Traversed {subdirectory_count} directories, current: {root}")
                    
                    for filename in files:
                        file_count += 1
                        full_path = os.path.join(root, filename)
                        
                        # Debug file examination
                        if file_count % 1000 == 0:
                            self.logger.debug(f"Examined {file_count} files")
                        
                        # Case-insensitive comparison with filename
                        upper_filename = filename.upper()
                        
                        # 1. Check for exact match
                        if upper_filename == upper_pattern:
                            matches.append(full_path)
                            self.logger.debug(f"Found exact match: {full_path}")
                            if first_match_only:
                                break
                            continue
                        
                        # 2. Check for base name match
                        if '.' in filename:
                            file_base = os.path.splitext(upper_filename)[0]
                            if file_base == base_pattern:
                                matches.append(full_path)
                                self.logger.debug(f"Found base name match: {full_path}")
                                if first_match_only:
                                    break
                                continue
                        
                        # 3. Check for substring match (like using '*' in shell script)
                        if upper_pattern in upper_filename or base_pattern in upper_filename:
                            matches.append(full_path)
                            self.logger.debug(f"Found substring match: {full_path}")
                            if first_match_only:
                                break
                            continue
                        
                        # 4. Special handling for EDL file paths with problematic characters
                        if '&' in pattern or ' ' in pattern or '(' in pattern or ')' in pattern:
                            if re.search(special_char_pattern, upper_filename):
                                matches.append(full_path)
                                self.logger.debug(f"Found special character match: {full_path}")
                                if first_match_only:
                                    break
                                continue
                    
                    # If we found a match and only want the first one, stop searching directories
                    if matches and first_match_only:
                        break
                
                self.logger.debug(f"Case-insensitive search completed. Examined {file_count} files in {subdirectory_count} directories.")
            
            # For case-sensitive or regex searches
            else:
                if self.use_regex:
                    # Regular expression matching
                    try:
                        regex = re.compile(pattern)
                        self.logger.debug(f"Using regex search with pattern: {pattern}")
                        
                        for root, dirs, files in os.walk(src_dir):
                            # Track this directory
                            dirs_searched.add(root)
                            subdirectory_count += 1
                            
                            # Debug directory traversal
                            if subdirectory_count % 20 == 0:
                                self.logger.debug(f"Traversed {subdirectory_count} directories, current: {root}")
                            
                            for filename in files:
                                file_count += 1
                                full_path = os.path.join(root, filename)
                                
                                # Debug file examination
                                if file_count % 1000 == 0:
                                    self.logger.debug(f"Examined {file_count} files")
                                
                                if regex.search(filename):
                                    matches.append(full_path)
                                    self.logger.debug(f"Found regex match: {full_path}")
                                    if first_match_only:
                                        break
                            
                            # If we found a match and only want the first one, stop searching directories
                            if matches and first_match_only:
                                break
                        
                        self.logger.debug(f"Regex search completed. Examined {file_count} files in {subdirectory_count} directories.")
                    except re.error as e:
                        self.logger.log(f"Warning: Invalid regex pattern: {pattern} - Error: {e}", console=True)
                else:
                    # Glob pattern matching
                    self.logger.debug(f"Using glob search with pattern: {pattern}")
                    
                    for root, dirs, files in os.walk(src_dir):
                        # Track this directory
                        dirs_searched.add(root)
                        subdirectory_count += 1
                        
                        # Debug directory traversal
                        if subdirectory_count % 20 == 0:
                            self.logger.debug(f"Traversed {subdirectory_count} directories, current: {root}")
                        
                        for filename in files:
                            file_count += 1
                            full_path = os.path.join(root, filename)
                            
                            # Debug file examination
                            if file_count % 1000 == 0:
                                self.logger.debug(f"Examined {file_count} files")
                            
                            # Add wildcard behavior like the shell script
                            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(filename, pattern + "*"):
                                matches.append(full_path)
                                self.logger.debug(f"Found glob match: {full_path}")
                                if first_match_only:
                                    break
                        
                        # If we found a match and only want the first one, stop searching directories
                        if matches and first_match_only:
                            break
                    
                    self.logger.debug(f"Glob search completed. Examined {file_count} files in {subdirectory_count} directories.")
            
            # Log results
            if matches:
                self.logger.debug(f"Found {len(matches)} files matching '{pattern}'")
                self.logger.log(f"    Found {len(matches)} files matching pattern: {pattern}", console=False)
                for i, match in enumerate(matches[:3]):  # Log first 3 matches
                    self.logger.log(f"      Match {i+1}: {os.path.basename(match)}", console=False)
                if len(matches) > 3:
                    self.logger.log(f"      ... and {len(matches) - 3} more", console=False)
            else:
                self.logger.debug(f"No files found matching '{pattern}'")
                self.logger.log(f"    No matches found for pattern: {pattern}", console=False)
            
            self.logger.debug(f"Search statistics: Searched {len(dirs_searched)} directories, {file_count} files examined, {len(matches)} matches found")
            
        except Exception as e:
            self.logger.debug(f"Error in _find_matches: {str(e)}")
            self.logger.debug(traceback.format_exc())
            print(f"Error searching: {e}")
            
        return matches, dirs_searched
    
    def _should_exclude(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """Check if a file should be excluded based on exclude patterns."""
        filename = os.path.basename(file_path)
        for pattern in exclude_patterns:
            if self.use_regex:
                try:
                    if re.search(pattern, filename):
                        return True
                except re.error:
                    continue  # Ignore invalid regex
            else:
                if fnmatch.fnmatch(filename, pattern):
                    return True
        return False
    
    def _get_file_size_mb(self, file_path: str) -> float:
        """Get file size in megabytes."""
        return os.path.getsize(file_path) / (1024 * 1024)
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """
        Calculate a similarity score between two strings.
        Used for fuzzy matching when exact matches fail.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score (0-1)
        """
        # Simple implementation using common substrings
        # For more advanced fuzzy matching, consider libraries like fuzzywuzzy
        if not str1 or not str2:
            return 0
            
        # Find common characters
        s1, s2 = set(str1), set(str2)
        common_chars = len(s1.intersection(s2))
        total_chars = len(s1.union(s2))
        
        # Calculate similarity
        return common_chars / total_chars if total_chars > 0 else 0


class FileCopier:
    """Handles the actual file copying operations."""
    
    def __init__(self, logger: Logger, dry_run: bool = False, verify: bool = False):
        self.logger = logger
        self.dry_run = dry_run
        self.verify = verify
        self.transfer_start_time = 0
        self.total_bytes_transferred = 0
        
        # Keep track of failures
        self.copy_failures = []
    
    def copy_files(self, files_to_copy: List[Tuple[str, str]], show_progress: bool = False) -> Tuple[int, int]:
        """
        Copy files from source to destination.
        
        Args:
            files_to_copy: List of (source_path, dest_path) tuples
            show_progress: Whether to show progress bar
            
        Returns:
            Tuple (copied_count, total_bytes_copied)
        """
        copied_count = 0
        total_bytes_copied = 0
        
        # Reset failure list
        self.copy_failures = []
        
        if not files_to_copy:
            return copied_count, total_bytes_copied
        
        if show_progress:
            progress = ProgressBar(len(files_to_copy), prefix='Copy Progress')
        else:
            progress = None
        
        self.transfer_start_time = time.time()
        
        for i, (src_path, dest_path) in enumerate(files_to_copy):
            if not self.dry_run:
                success, file_size = self._copy_file(src_path, dest_path)
                
                if success:
                    copied_count += 1
                    total_bytes_copied += file_size
                    self.total_bytes_transferred += file_size
                    
                    # Calculate and display transfer speed periodically
                    if copied_count % 10 == 0 and progress is None:  # Only show if not using progress bar
                        speed = self._calculate_transfer_speed()
                        sys.stdout.write(f"\rTransfer Speed: {speed:.2f} MB/s")
                        sys.stdout.flush()
            else:
                # In dry run mode, just log what would happen
                self.logger.log(f"  WOULD COPY: {src_path} -> {dest_path}", console=False)
                copied_count += 1
                try:
                    total_bytes_copied += os.path.getsize(src_path)
                except (FileNotFoundError, PermissionError):
                    pass
            
            # Update progress bar
            if progress:
                progress.update(i + 1)
        
        # Show final progress information
        if progress is None and not self.dry_run and copied_count > 0:
            speed = self._calculate_transfer_speed()
            sys.stdout.write(f"\rTransfer Speed: {speed:.2f} MB/s\n")
            sys.stdout.flush()
        
        # Log any failures
        if self.copy_failures:
            self.logger.log(f"\nWARNING: {len(self.copy_failures)} files could not be copied:", console=True)
            for src, dest, error in self.copy_failures[:10]:  # Show first 10 failures
                self.logger.log(f"  {src} -> {dest}: {error}", console=True)
            
            if len(self.copy_failures) > 10:
                self.logger.log(f"  ... and {len(self.copy_failures) - 10} more failures", console=True)
        
        return copied_count, total_bytes_copied
    
    def _copy_file(self, src_path: str, dest_path: str) -> Tuple[bool, int]:
        """
        Copy a single file with verification.
        
        Args:
            src_path: Source file path
            dest_path: Destination file path
            
        Returns:
            Tuple (success, file_size)
        """
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Get file size for reporting
            file_size = os.path.getsize(src_path)
            
            # Copy file
            shutil.copy2(src_path, dest_path)
            
            # Verify copy if requested
            if self.verify:
                if not self._verify_copy(src_path, dest_path):
                    error_msg = "File verification failed"
                    self.logger.log(f"  ERROR: {error_msg}: {src_path} -> {dest_path}", console=False)
                    self.copy_failures.append((src_path, dest_path, error_msg))
                    return False, 0
            
            # Log success
            self.logger.log(f"  Copied to: {dest_path}", console=False)
            return True, file_size
                
        except Exception as e:
            self.logger.log(f"  ERROR: Failed to copy: {src_path} -> {dest_path}", console=False)
            self.logger.log(f"  Error details: {str(e)}", console=False)
            self.copy_failures.append((src_path, dest_path, str(e)))
            return False, 0
    
    def _verify_copy(self, src_path: str, dest_path: str) -> bool:
        """
        Verify that a file was copied correctly using size and hash comparison.
        
        Args:
            src_path: Source file path
            dest_path: Destination file path
            
        Returns:
            True if verification passed, False otherwise
        """
        try:
            # Check file sizes match
            src_size = os.path.getsize(src_path)
            dest_size = os.path.getsize(dest_path)
            
            if src_size != dest_size:
                error_msg = f"File size mismatch: {src_path} ({src_size} bytes) -> {dest_path} ({dest_size} bytes)"
                self.logger.log(f"  VERIFY ERROR: {error_msg}")
                return False
            
            # Determine hash strategy based on file size
            if src_size > 1 * 1024 * 1024 * 1024:  # Files larger than 1GB
                # For very large files, use a sample-based hash to reduce computation time
                src_hash = self._calculate_sample_hash(src_path)
                dest_hash = self._calculate_sample_hash(dest_path)
                hash_type = "sampled hash"
            else:
                # For smaller files, calculate full hash
                src_hash = self._calculate_file_hash(src_path)
                dest_hash = self._calculate_file_hash(dest_path)
                hash_type = "full hash"
            
            # Compare hashes
            if src_hash != dest_hash:
                error_msg = f"Hash mismatch: {src_path} ({hash_type}, src hash: {src_hash}) -> {dest_path} (dest hash: {dest_hash})"
                self.logger.log(f"  VERIFY ERROR: {error_msg}")
                return False
            
            # Log successful verification
            self.logger.log(f"  VERIFY SUCCESS: {src_path} ({src_size} bytes, {hash_type}: {src_hash})")
            
            return True
        except Exception as e:
            error_msg = f"Verification error for {src_path}: {str(e)}"
            self.logger.log(f"  VERIFY ERROR: {error_msg}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def _calculate_sample_hash(self, file_path: str) -> str:
        """
        Calculate a hash for very large files by sampling specific parts of the file.
        
        This method calculates a hash based on:
        - First 16 KB
        - Middle 16 KB
        - Last 16 KB
        
        Args:
            file_path: Path to the file
            
        Returns:
            XXHash64 hash of sampled file sections
        """
        hasher = xxhash.xxh64()
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'rb') as f:
            # Sample sections for very large files
            sample_size = 16 * 1024  # 16 KB
            
            # Read first 16 KB
            f.seek(0)
            hasher.update(f.read(sample_size))
            
            # Read middle 16 KB
            if file_size > 3 * sample_size:
                f.seek(file_size // 2 - sample_size // 2)
                hasher.update(f.read(sample_size))
            
            # Read last 16 KB
            if file_size > 2 * sample_size:
                f.seek(file_size - sample_size)
                hasher.update(f.read(sample_size))
        
        return hasher.hexdigest()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate XXHash64 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            XXHash64 hash as hex string
        """
        hasher = xxhash.xxh64()
        with open(file_path, 'rb') as f:
            # Read file in chunks to avoid loading large files into memory
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _calculate_transfer_speed(self) -> float:
        """Calculate current transfer speed in MB/s."""
        elapsed_time = max(1, time.time() - self.transfer_start_time)
        return self.total_bytes_transferred / elapsed_time / (1024 * 1024)


class DiskSpaceChecker:
    """Checks available disk space before copy operations."""
    
    @staticmethod
    def check_available_space(dest_dir: str, required_kb: int) -> bool:
        """
        Check if there's enough disk space in the destination directory.
        
        Args:
            dest_dir: Destination directory
            required_kb: Required space in KB
            
        Returns:
            True if enough space is available, False otherwise
        """
        try:
            # Ensure the directory exists for checking
            os.makedirs(dest_dir, exist_ok=True)
            
            # Get available space
            if sys.platform == 'win32':
                free_bytes = shutil.disk_usage(dest_dir).free
                available_kb = free_bytes // 1024
            else:
                try:
                    # Use df command on Unix-like systems for more accurate space info
                    df_output = subprocess.check_output(['df', '-k', dest_dir]).decode('utf-8')
                    available_kb = int(df_output.strip().split('\n')[1].split()[3])
                except (subprocess.SubprocessError, IndexError, ValueError):
                    # Fallback to Python's disk_usage
                    free_bytes = shutil.disk_usage(dest_dir).free
                    available_kb = free_bytes // 1024
            
            # Check if enough space is available with a safety margin (5%)
            safety_margin = int(required_kb * 0.05)
            total_required = required_kb + safety_margin
            
            if available_kb < total_required:
                print(f"Error: Insufficient disk space in destination directory.")
                print(f"Available: {available_kb // 1024} MB")
                print(f"Required: {total_required // 1024} MB (including 5% safety margin)")
                return False
            
            return True
        except Exception as e:
            print(f"Error checking disk space: {str(e)}")
            return False


class FileProcessor:
    """Main class that orchestrates the file copying process."""
    
    def __init__(self, args):
        # Core parameters
        self.source_dirs = args.source_dirs
        self.dest_dir = args.dest_dir
        self.file_list = args.file_list
        self.edl_file = args.edl_file
        self.log_file = args.log_file
        
        # Operation flags
        self.show_progress = args.show_progress
        self.use_regex = args.use_regex
        self.max_size = args.max_size
        self.exclude_file = args.exclude_file
        self.dry_run = args.dry_run
        self.verify = args.verify
        self.debug = args.debug
        self.parallel = args.parallel
        self.max_workers = args.max_workers
        self.first_match_only = args.first_match_only
        
        # EDL files use case-insensitive search by default
        self.case_sensitive = not args.edl_file
        
        # Initialize logger
        self.logger = Logger(args.log_file, args.dry_run, args.debug)
        
        # Initialize other components
        self.edl_parser = EDLParser(self.logger)
        self.file_finder = FileFinder(self.logger, self.case_sensitive, self.use_regex, self.max_workers)
        self.file_copier = FileCopier(self.logger, self.dry_run, self.verify)
        
        # Statistics
        self.total_patterns = 0
        self.found_files = 0
        self.copied_files = 0
        self.skipped_files = 0
        self.missing_patterns = 0
        self.existing_files = 0
        self.size_exceeded_files = 0
        self.excluded_files = 0
        self.total_bytes_copied = 0
        self.missing_patterns_list = []
        self.total_dirs_searched = 0
    
    def run(self):
        """Run the file processing operation."""
        try:
            start_time = time.time()
            self.logger.debug(f"Starting file processing operation")
            
            # Validate all inputs
            self._validate_inputs()
            
            # Load exclude patterns if specified
            exclude_patterns = self._load_exclude_patterns()
            
            # Get file patterns to process
            if self.edl_file:
                patterns = self.edl_parser.parse_edl_file(self.edl_file)
            else:
                patterns = self._load_file_list()
            
            self.total_patterns = len(patterns)
            
            # Log initial information
            self._log_initial_info(exclude_patterns)
            
            # Process each pattern
            all_files_to_process = []
            all_files_to_copy = []
            all_dirs_searched = set()
            
            # Show progress for pattern search if necessary
            if self.show_progress and self.total_patterns > 5:
                print(f"Analyzing files across {len(self.source_dirs)} source directories...")
                progress = ProgressBar(self.total_patterns, prefix='Pattern Search Progress')
            else:
                progress = None
            
            # Process file patterns (either in parallel or sequentially)
            if self.parallel and self.total_patterns > 1:
                self.logger.log(f"Using parallel processing with {self.file_finder.max_workers} workers")
                
                # Find files in parallel
                pattern_to_files = self.file_finder.find_files_parallel(patterns, self.source_dirs, 
                                                                     exclude_patterns, self.max_size, 
                                                                     self.first_match_only)  # Pass first_match_only
                
                # Process results
                for i, pattern in enumerate(patterns):
                    # Update progress
                    if progress:
                        progress.update(i + 1)
                    
                    # Get results for this pattern
                    if pattern in pattern_to_files:
                        found_files, pattern_found = pattern_to_files[pattern]
                        
                        # Debug output
                        self.logger.debug(f"Pattern {pattern}: Found {len(found_files)} files, pattern_found={pattern_found}")
                        
                        # Process found files
                        self._process_found_files(pattern, found_files, pattern_found, all_files_to_process, 
                                               all_files_to_copy)
                
                # Get total directories searched from the finder
                all_dirs_searched = self.file_finder.dirs_searched_set
                
            else:
                # Process patterns sequentially
                for i, pattern in enumerate(patterns):
                    # Update progress
                    if progress:
                        progress.update(i + 1)
                    
                    # Find files matching the pattern
                    found_files, pattern_found, dirs_searched = self.file_finder.find_file(
                        pattern, self.source_dirs, exclude_patterns, self.max_size, self.first_match_only  # Pass first_match_only
                    )
                    
                    # Add to the total directories searched
                    all_dirs_searched.update(dirs_searched)
                    
                    # Process found files
                    self._process_found_files(pattern, found_files, pattern_found, all_files_to_process, 
                                           all_files_to_copy)
            
            # Store total directories searched
            self.total_dirs_searched = len(all_dirs_searched)
            self.logger.debug(f"Traversed a total of {self.total_dirs_searched} directories")
            
            # Finish progress display
            if progress:
                print()  # New line after progress bar
            
            # Calculate total size of files to copy
            total_size_bytes = sum(os.path.getsize(src) for src, _ in all_files_to_copy)
            total_size_kb = total_size_bytes // 1024
            
            # Check disk space
            if not self.dry_run:
                if not DiskSpaceChecker.check_available_space(self.dest_dir, total_size_kb):
                    self.logger.log("Error: Insufficient disk space for copy operation")
                    return 1
            else:
                self.logger.log(f"Would check for at least {total_size_kb // 1024} MB of free space in {self.dest_dir}")
            
            # Log information about files to copy
            self._log_files_info(all_files_to_process, all_files_to_copy, total_size_kb)
            
            # Copy files
            self.found_files = len(all_files_to_process)
            self.copied_files, self.total_bytes_copied = self.file_copier.copy_files(
                all_files_to_copy, self.show_progress
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            self.logger.debug(f"Operation completed in {elapsed_time:.2f} seconds")
            
            # Log summary
            self._log_summary(elapsed_time)
            
            return 0
        
        except KeyboardInterrupt:
            self.logger.log("\nOperation cancelled by user.")
            return 130  # 128 + SIGINT(2)
        except Exception as e:
            self.logger.log(f"Error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 1
    
    def _process_found_files(self, pattern: str, found_files: List[str], pattern_found: bool,
                      all_files: List[Tuple[str, str]], files_to_copy: List[Tuple[str, str]]) -> None:
        # Use a set to track unique source paths
        unique_src_paths = set()
        
        # Handle when pattern wasn't found
        if not pattern_found:
            self.logger.log(f"  No files found matching: {pattern} in any source directory", console=False)
            self.logger.log_missing(pattern)
            self.missing_patterns += 1
            self.missing_patterns_list.append(pattern)
            return
        
        # Process found files
        for src_path in found_files:
            # Skip if this source path has already been processed
            if src_path in unique_src_paths:
                continue
            
            unique_src_paths.add(src_path)
            
            filename = os.path.basename(src_path)
            dest_path = os.path.join(self.dest_dir, filename)
            
            # Add file to processing list
            all_files.append((src_path, dest_path))
            
            # Check if file already exists in destination
            if not os.path.exists(dest_path):
                files_to_copy.append((src_path, dest_path))
            else:
                self.existing_files += 1
                self.logger.log_existing(filename)
    
    def _validate_inputs(self):
        """Validate all input parameters."""
        # Check source directories
        for src_dir in self.source_dirs:
            if not os.path.isdir(src_dir):
                raise ValueError(f"Source directory does not exist: {src_dir}")
            
            if not os.access(src_dir, os.R_OK):
                raise ValueError(f"Source directory is not readable: {src_dir}")
        
        # Check EDL file or file list
        if self.edl_file:
            if not os.path.isfile(self.edl_file):
                raise ValueError(f"EDL file does not exist: {self.edl_file}")
            
            if not os.access(self.edl_file, os.R_OK):
                raise ValueError(f"EDL file is not readable: {self.edl_file}")
        elif self.file_list:
            if not os.path.isfile(self.file_list):
                raise ValueError(f"File list does not exist: {self.file_list}")
            
            if not os.access(self.file_list, os.R_OK):
                raise ValueError(f"File list is not readable: {self.file_list}")
        else:
            raise ValueError("Either file list (-f) or EDL file (--edl) must be specified")
        
        # Check exclude file
        if self.exclude_file:
            if not os.path.isfile(self.exclude_file):
                raise ValueError(f"Exclude file does not exist: {self.exclude_file}")
            
            if not os.access(self.exclude_file, os.R_OK):
                raise ValueError(f"Exclude file is not readable: {self.exclude_file}")
        
        # Create destination directory if it doesn't exist
        if not self.dry_run and not os.path.isdir(self.dest_dir):
            try:
                os.makedirs(self.dest_dir)
                print(f"Created destination directory: {self.dest_dir}")
            except Exception as e:
                raise ValueError(f"Failed to create destination directory: {self.dest_dir} - {str(e)}")
        elif self.dry_run and not os.path.isdir(self.dest_dir):
            print(f"Note: Destination directory does not exist, but would be created in actual run: {self.dest_dir}")
        
        # Validate max_workers
        if self.max_workers is not None and self.max_workers <= 0:
            raise ValueError(f"Max workers must be a positive integer: {self.max_workers}")
    
    def _load_exclude_patterns(self) -> List[str]:
        """Load exclude patterns from exclude file."""
        exclude_patterns = []
        
        if self.exclude_file and os.path.isfile(self.exclude_file):
            try:
                with open(self.exclude_file, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            exclude_patterns.append(line)
                
                self.logger.log(f"Loaded {len(exclude_patterns)} exclude patterns")
                
            except Exception as e:
                self.logger.log(f"Warning: Error loading exclude patterns: {str(e)}")
        
        return exclude_patterns
    
    def _load_file_list(self) -> List[str]:
        """Load file patterns from file list."""
        patterns = []
        
        try:
            with open(self.file_list, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
            
            self.logger.debug(f"Loaded {len(patterns)} patterns from {self.file_list}")
            
        except Exception as e:
            self.logger.log(f"Error loading file list: {str(e)}")
            raise
        
        return patterns
    
    def _log_initial_info(self, exclude_patterns: List[str]) -> None:
        """Log initial information about the copy operation."""
        self.logger.log("======================================================")
        self.logger.log(f"Source Directories: {', '.join(self.source_dirs)}")
        self.logger.log(f"Destination Directory: {self.dest_dir}")
        
        if self.edl_file:
            self.logger.log(f"EDL File: {self.edl_file}")
            self.logger.log("Using case-insensitive file matching")
        else:
            self.logger.log(f"File List: {self.file_list}")
        
        if self.use_regex:
            self.logger.log("Using regular expressions for pattern matching")
        
        if exclude_patterns:
            self.logger.log(f"Exclude File: {self.exclude_file} ({len(exclude_patterns)} patterns)")
        
        if self.max_size > 0:
            self.logger.log(f"Maximum File Size: {self.max_size} MB")
        
        if self.verify:
            self.logger.log("Verification: Enabled")
        
        if self.parallel:
            self.logger.log(f"Parallel Processing: Enabled ({self.file_finder.max_workers} workers)")
            
        if self.dry_run:
            self.logger.log("DRY RUN MODE: No files will be copied")
            
        self.logger.log("======================================================")
        self.logger.log("")
    
    def _log_files_info(self, all_files: List[Tuple[str, str]], files_to_copy: List[Tuple[str, str]], 
                       total_size_kb: int) -> None:
        """Log information about files to copy."""
        msg_prefix = '' if not self.dry_run else 'Would '
        
        self.logger.log(f"Files to {msg_prefix}process: {len(all_files)}")
        self.logger.log(f"Files to {msg_prefix}copy: {len(files_to_copy)}")
        self.logger.log(f"Total copy size {msg_prefix}be: {total_size_kb // 1024} MB")
        
        if self.show_progress:
            print(f"Files to {msg_prefix}process: {len(all_files)}")
            print(f"Files to {msg_prefix}copy: {len(files_to_copy)}")
            print(f"Total copy size {msg_prefix}be: {total_size_kb // 1024} MB")
            print("")
            
            if self.dry_run:
                print("Analyzing what would be copied (dry run)...")
            else:
                print("Starting copy operation...")
    
    def _log_summary(self, elapsed_time: float) -> None:
            """Log summary statistics."""
            # Calculate transfer speed
            avg_speed = (self.total_bytes_copied / max(1, elapsed_time)) / (1024 * 1024) if elapsed_time > 0 else 0
            
            # Format time for display
            time_str = self._format_time(elapsed_time)
            
            # Create summary text
            summary = [
                "",
                "======================================================",
                f"{'Dry Run ' if self.dry_run else ''}Summary - {datetime.datetime.now()}",
                f"Source directories specified: {len(self.source_dirs)}",
                f"Total directories searched: {self.total_dirs_searched}",
                f"Patterns processed: {self.total_patterns}",
                f"Files found : {self.found_files}",
                f"Files {'that would be ' if self.dry_run else ''}copied : {self.copied_files}",
                f"Files {'that would be ' if self.dry_run else ''}skipped : {self.existing_files}",
                f"Patterns with no matches: {self.missing_patterns}",
                f"Files excluded by pattern: {self.excluded_files}",
                f"Files excluded by size: {self.size_exceeded_files}",
                f"Total data {'that would be ' if self.dry_run else ''}copied: {self.total_bytes_copied // (1024 * 1024)} MB",
                f"Total elapsed time: {time_str}"
            ]
            
            # Add speed information if applicable
            if elapsed_time > 0 and self.total_bytes_copied > 0:
                summary.append(f"Average Transfer Speed: {avg_speed:.2f} MB/s")
            
            # Add EDL file information if applicable
            if self.edl_file:
                summary.append(f"EDL file parsed: {self.edl_file}")
            
            summary.append("======================================================")
            
            # Log summary
            for line in summary:
                self.logger.log(line)
            
            # Output summary to console
            print(f"{'Dry run completed' if self.dry_run else 'Operation completed'}. See {self.log_file} for details.")
            print(f"Source directories specified: {len(self.source_dirs)}")
            print(f"Total directories searched: {self.total_dirs_searched}")
            print(f"Patterns processed: {self.total_patterns}")
            print(f"Files found : {self.found_files}")
            print(f"Files {'that would be ' if self.dry_run else ''}copied : {self.copied_files}")
            print(f"Files {'that would be ' if self.dry_run else ''}skipped : {self.existing_files}")
            print(f"Patterns with no matches: {self.missing_patterns}")
            
            if self.excluded_files > 0:
                print(f"Files excluded by pattern: {self.excluded_files}")
            if self.size_exceeded_files > 0:
                print(f"Files excluded by size: {self.size_exceeded_files}")
            
            print(f"Total data {'that would be ' if self.dry_run else ''}copied: {self.total_bytes_copied // (1024 * 1024)} MB")
            print(f"Total elapsed time: {time_str}")
            
            if self.edl_file:
                print(f"EDL file parsed: {self.edl_file}")
            
            # Display information about additional log files
            if not self.dry_run:
                if self.missing_patterns > 0:
                    print(f"Missing files log: {self.logger.missing_log} ({self.missing_patterns} patterns with no matches)")
                if self.existing_files > 0:
                    print(f"Existing files log: {self.logger.existing_log} ({self.existing_files} files already in destination)")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into a human-readable time string."""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="File Search and Copy Utility v3.1",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Required options
    parser.add_argument('-s', '--source', dest='source_dirs', required=True, 
                        help='One or more directories to search in (comma-separated)')
    parser.add_argument('-d', '--dest', dest='dest_dir', required=True,
                        help='Directory to copy files to')
    parser.add_argument('-l', '--log', dest='log_file', required=True,
                        help='Log file to write operations to (will append if exists)')
    
    # File list options (one required)
    file_group = parser.add_mutually_exclusive_group(required=True)
    file_group.add_argument('-f', '--file-list', dest='file_list',
                          help='File containing list of filenames to search for (one per line)')
    file_group.add_argument('--edl', dest='edl_file',
                          help='Parse an EDL file to extract source filenames (uses case-insensitive search)')
    
    # Additional options
    parser.add_argument('-p', '--progress', dest='show_progress', action='store_true',
                        help='Show progress during copy operations')
    parser.add_argument('-r', '--regex', dest='use_regex', action='store_true',
                        help='Use regular expressions instead of glob patterns')
    parser.add_argument('-m', '--max-size', dest='max_size', type=int, default=0,
                        help='Skip files larger than MAX_SIZE (in MB)')
    parser.add_argument('-x', '--exclude', dest='exclude_file',
                        help='Skip files that match patterns in EXCLUDE_FILE')
    parser.add_argument('-n', '--dry-run', dest='dry_run', action='store_true',
                        help='Perform a dry run (no actual file copying)')
    parser.add_argument('--first-match-only', dest='first_match_only', action='store_true',
                   help='Only use the first match found for each pattern')
    
    # New advanced options
    parser.add_argument('--verify', dest='verify', action='store_true',
                        help='Verify copied files with size and hash comparison')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='Enable detailed debug logging')
    parser.add_argument('--parallel', dest='parallel', action='store_true',
                        help='Use parallel processing for file searching')
    parser.add_argument('--max-workers', dest='max_workers', type=int,
                        help='Maximum number of worker processes for parallel operations')
    
    args = parser.parse_args()
    
    # Process source directories
    args.source_dirs = [d.strip() for d in args.source_dirs.split(',')]
    
    return args


def display_usage():
    """Display usage examples."""
    script_name = os.path.basename(sys.argv[0])
    usage_text = f"""
Examples:
  # Using a simple file list:
  {script_name} -s /path/source1,/path/source2 -d /path/dest -f files.txt -l log.txt

  # Parsing an EDL file to extract source filenames:
  {script_name} -s /path/source1,/path/source2 -d /path/dest --edl project.edl -l log.txt

  # Perform a dry run with an EDL file:
  {script_name} -s /path/source1,/path/source2 -d /path/dest --edl project.edl -l log.txt -n
  
  # Using glob patterns (default):
  # First create a file list:
  #   echo "*.jpg" > files.txt       # Match all JPG files
  #   echo "doc_*.pdf" >> files.txt  # Match PDFs starting with "doc_"
  #   echo "file_[0-9].txt" >> files.txt  # Match file_0.txt through file_9.txt
  # Then run:
  {script_name} -s /path/source1,/path/source2 -d /path/dest -f files.txt -l log.txt

  # Using regular expressions (with -r flag):
  # First create a file with regex patterns:
  #   echo "^.*\\.jpg$" > regex.txt         # Match all JPG files
  #   echo "^doc_.*\\.pdf$" >> regex.txt    # Match PDFs starting with "doc_"
  #   echo "^file_[0-9]\\.txt$" >> regex.txt  # Match file_0.txt through file_9.txt
  # Then run:
  {script_name} -s /path/source1,/path/source2 -d /path/dest -f regex.txt -l log.txt -r

  # Advanced usage with verification and parallel processing:
  {script_name} -s /path/source1,/path/source2 -d /path/dest --edl project.edl -l log.txt -p --verify --parallel
"""
    print(usage_text)


def main():
    """Main entry point for the script."""
    # Setup signal handlers for graceful termination
    setup_signal_handlers()
    
    try:
        args = parse_arguments()
        processor = FileProcessor(args)
        return processor.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130  # 128 + SIGINT(2)
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
