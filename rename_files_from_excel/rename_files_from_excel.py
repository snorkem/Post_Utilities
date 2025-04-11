import os
import pandas as pd
from pathlib import Path
import sys
import re
import logging
import argparse
import shutil
from datetime import datetime


def setup_logger(logname='renames.log'):
    """Set up and return a logger with appropriate configuration."""
    log_file_path = os.path.abspath(logname)
    
    logging.basicConfig(
        filename=log_file_path,
        filemode='a',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG
    )
    return logging.getLogger('Rename Files From Excel'), log_file_path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Rename files based on Excel spreadsheet mapping.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('excel_file', 
                        help='Path to Excel file containing filename mappings')
    
    parser.add_argument('target_dir', 
                        help='Directory containing files to rename')
    
    parser.add_argument('--files-col', 
                        default='Master Original Name',
                        help='Column name in Excel containing original filenames')
    
    parser.add_argument('--rename-col', 
                        default='Avid Proxy Name',
                        help='Column name in Excel containing new filenames')
    
    parser.add_argument('--suffix', 
                        default='_M',
                        help='Suffix to add to renamed files')
    
    parser.add_argument('--log', 
                        default='renames.log',
                        help='Path to log file')
    
    parser.add_argument('--no-recursive', 
                        action='store_true',
                        dest='no_recursive',
                        default=False,
                        help='Disable recursive search in subdirectories (default: recursive search enabled)')
    
    parser.add_argument('--force', 
                        action='store_true',
                        help='Overwrite existing files during rename')
    
    parser.add_argument('--dry-run', 
                        action='store_true',
                        help='Show what would be renamed without making changes')
    
    return parser.parse_args()


def is_ascii(filename, index, column_name, logger):
    """Check if filename is valid ascii characters and has no illegal path characters."""
    re1 = re.compile(r"[<>/{}[\]~`]")
    try:
        if pd.isna(filename):
            error_msg = f'Empty cell in {column_name} on row {index+2}'
            print(error_msg)
            logger.error(error_msg)
            return False
            
        if re1.search(str(filename)):
            error_msg = f'Invalid path char detected in {column_name} on row {index+2}'
            print(error_msg)
            logger.error(error_msg)
            return False
        
        # Try to encode to ascii to catch non-ascii characters
        str(filename).encode('ascii')
        return True
    except UnicodeEncodeError:
        error_msg = f'Non-ascii name in {column_name} "{filename}" on row {index+2}'
        print(error_msg)
        logger.error(error_msg)
        return False
    except AttributeError:
        error_msg = f'Empty cell, perhaps, on line {index+2}?'
        print(error_msg)
        logger.error(error_msg)
        return False


def get_files_to_rename(target_dir, recursive=True, logger=None):
    """Recursively collect all non-hidden files from directory and subdirectories."""
    files_to_rename = []
    
    if not target_dir.is_dir():
        print('Target is not a directory')
        if logger:
            logger.error('Target is not a directory: %s', target_dir)
        return files_to_rename
        
    print(f'Target is directory: {target_dir}. Collecting files...')
    if logger:
        logger.info('Target is directory: %s. Collecting files...', target_dir)
    
    try:
        if recursive:
            # Use rglob for recursive search
            for file_path in target_dir.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    files_to_rename.append(file_path)
                    
        else:
            # Use iterdir for non-recursive search
            for file_path in target_dir.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    files_to_rename.append(file_path)
    
    except Exception as e:
        error_msg = f'Error collecting files from {target_dir}: {str(e)}'
        print(error_msg)
        if logger:
            logger.error(error_msg)
            
    return files_to_rename


def are_there_dups(series):
    """Check if a pandas Series contains duplicate values."""
    return not series.is_unique


def rename_files(target_files, master_file_names, proxy_names, suffix, logger, force=False, dry_run=False):
    """Rename files based on mapping in Excel file."""
    rename_count = 0
    skipped_count = 0
    errors_count = 0
    
    # Create a lookup dictionary for faster access
    rename_map = {}
    for index, master_name in master_file_names.items():
        if pd.notna(master_name) and pd.notna(proxy_names[index]):
            rename_map[str(master_name)] = str(proxy_names[index])
    
    print(f'Examining {len(target_files)} files...')
    logger.info(f'Examining {len(target_files)} files...')
    
    # Process each file
    for file_path in target_files:
        file_name = file_path.stem
        file_ext = file_path.suffix
        
        if file_name in rename_map:
            new_name = rename_map[file_name] + suffix + file_ext
            new_path = file_path.parent / new_name
            
            try:
                # Check if destination exists
                if new_path.exists():
                    if force and not dry_run:
                        # If force flag is true, create a backup before overwriting
                        backup_path = new_path.with_name(f"{new_path.stem}_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}{new_path.suffix}")
                        shutil.copy2(new_path, backup_path)
                        print(f"Backed up existing file to: {backup_path}")
                        logger.info(f"Backed up existing file: {new_path} -> {backup_path}")
                    else:
                        print(f"Skipping {file_path} - destination already exists: {new_path}")
                        logger.warning(f"Skipping rename - destination exists: {new_path}")
                        skipped_count += 1
                        continue
                
                # Perform rename or simulate it
                if dry_run:
                    print(f"Would rename: {file_path.name} -> {new_name}")
                    logger.info(f"Dry run: would rename {file_path} -> {new_path}")
                    rename_count += 1
                else:
                    file_path.rename(new_path)
                    print(f"Renamed: {file_path.name} -> {new_path.name}")
                    logger.info(f"Renamed: {file_path} -> {new_path}")
                    rename_count += 1
                
            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                errors_count += 1
    
    dry_run_prefix = "Dry run - " if dry_run else ""
    summary = (f"{dry_run_prefix}Summary: {rename_count} files {'would be ' if dry_run else ''}renamed, "
              f"{skipped_count} skipped (destinations exist), {errors_count} errors")
    print(summary)
    logger.info(summary)
    
    return rename_count


def check_single_sheet(excel_file, logger):
    """Check if the Excel file contains only a single sheet."""
    try:
        # Use pandas ExcelFile to get sheet names
        xls = pd.ExcelFile(excel_file)
        sheet_names = xls.sheet_names
        
        if len(sheet_names) > 1:
            error_msg = f"Excel file contains multiple sheets: {', '.join(sheet_names)}. Only single-sheet files are supported."
            print(error_msg)
            logger.error(error_msg)
            return False, sheet_names[0]
        
        return True, sheet_names[0]
        
    except Exception as e:
        error_msg = f"Error checking Excel sheets: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return False, None


def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logger
    logger, log_path = setup_logger(args.log)
    print(f"Logging to: {log_path}")
    
    # Convert string paths to Path objects and normalize them
    excel_file = Path(os.path.abspath(args.excel_file))
    target_dir = Path(os.path.abspath(args.target_dir))
    
    # Column names from arguments
    files_to_rename_col = args.files_col
    rename_to_col = args.rename_col
    master_file_suffix = args.suffix
    
    # Determine if recursive search is enabled (default is True)
    recursive = not args.no_recursive
    
    print(f"Starting file renaming process:")
    print(f"Excel file: {excel_file}")
    print(f"Target directory: {target_dir}")
    print(f"Original filenames column: {files_to_rename_col}")
    print(f"New filenames column: {rename_to_col}")
    print(f"Suffix: {master_file_suffix}")
    print(f"Recursive search: {recursive}")
    print(f"Force overwrite: {args.force}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 50)
    
    # Log the configuration
    logger.info("Configuration: excel=%s, target_dir=%s, files_col=%s, rename_col=%s, suffix=%s, recursive=%s, force=%s, dry_run=%s",
               excel_file, target_dir, files_to_rename_col, rename_to_col, master_file_suffix, 
               recursive, args.force, args.dry_run)
    
    try:
        # Verify the Excel file has the correct extension
        if not excel_file.name.lower().endswith(('.xlsx', '.xls')):
            error_msg = f"The specified file is not an Excel file (.xlsx or .xls): {excel_file}"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
            
        # Verify the Excel file exists
        if not excel_file.exists():
            error_msg = f"The specified Excel file does not exist: {excel_file}"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Check if Excel file has only one sheet
        single_sheet, sheet_name = check_single_sheet(excel_file, logger)
        if not single_sheet:
            error_msg = "This script only supports Excel files with a single sheet."
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Read the Excel file into dataframe
        try:
            df = pd.read_excel(excel_file, sheet_name=0)  # Always use first sheet
            print(f"Successfully read Excel file with {len(df)} rows from sheet '{sheet_name}'")
            logger.info(f"Successfully read Excel file with {len(df)} rows from sheet '{sheet_name}'")
        except Exception as e:
            error_msg = f"Error reading Excel file: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Verify required columns exist
        if files_to_rename_col not in df.columns:
            error_msg = f"Required column not found: '{files_to_rename_col}'"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
            
        if rename_to_col not in df.columns:
            error_msg = f"Required column not found: '{rename_to_col}'"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Define columns from spreadsheet to pull from by their headers.
        proxy_names = df[rename_to_col]
        master_file_names = df[files_to_rename_col]
        
        # Validate filenames
        invalid_rows = []
        for index, (master_name, proxy_name) in enumerate(zip(master_file_names, proxy_names)):
            if not is_ascii(master_name, index, files_to_rename_col, logger) or \
               not is_ascii(proxy_name, index, rename_to_col, logger):
                invalid_rows.append(index + 2)  # +2 for Excel row number
        
        if invalid_rows:
            error_msg = f"Invalid filenames found in rows: {', '.join(map(str, invalid_rows))}"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Check for duplicates
        if are_there_dups(master_file_names):
            error_msg = f"Duplicate values found in '{files_to_rename_col}' column"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
            
        if are_there_dups(proxy_names):
            error_msg = f"Duplicate values found in '{rename_to_col}' column"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Verify target directory exists
        if not target_dir.exists():
            error_msg = f"Target directory does not exist: {target_dir}"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
            
        if not target_dir.is_dir():
            error_msg = f"Target is not a directory: {target_dir}"
            print(error_msg)
            logger.error(error_msg)
            sys.exit(1)
        
        # Collect files to process
        files_to_rename = get_files_to_rename(target_dir, recursive, logger)
        
        if not files_to_rename:
            print("No files found to rename.")
            logger.info("No files found to rename.")
            sys.exit(0)
            
        # Perform renaming
        rename_files(files_to_rename, master_file_names, proxy_names, master_file_suffix, 
                    logger, force=args.force, dry_run=args.dry_run)
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        logger.exception(error_msg)
        sys.exit(1)


if __name__ == '__main__':
    main()