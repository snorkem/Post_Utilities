import os
import pandas as pd
from pathlib import Path
import sys
import re
import logging

# Column names to search in the excel sheet. Program will use the first sheet in the file, ignoring others.
FILES_TO_RENAME_COL = 'Master Original Name'
RENAME_TO_COL = 'Avid Proxy Name'
MASTER_FILE_SUFFIX = '_M'  # This goes after every file name to denote it is a master file.

# Get excel file as user args
excel_file = Path(sys.argv[1])
target_dir = Path(sys.argv[2])


# Read the excel file into
df = pd.read_excel(excel_file)

# Define columns from spreadsheet to pull from by their headers.
# Can be modified for another project or if the spreadsheet changes.
proxy_names = df[RENAME_TO_COL]
master_file_names = df[FILES_TO_RENAME_COL]

# Set up a logger to record what's going on.
logname = 'renames.log'

logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S",
                    level=logging.DEBUG)
logger = logging.getLogger('Rename Files From Excel')

# Check if filename is valid ascii characters and has no illegal path characters.
def is_ascii(filename, index):
    re1 = re.compile(r"[<>/{}[\]~`]")
    try:
        filename.encode('ascii')
        if re1.search(filename):
            print(f'Invalid path char detected in Master Original Names column {index+2}')
            logger.error(f'Invalid path char detected in Master Original Names column {index+2}')
            quit()
        return True
    except UnicodeEncodeError:
        print(f'Non-ascii name in proxy name {filename} on row {index+2}. Quiting.')
        logger.error(f'Non-ascii name in proxy name {filename} on row {index+2}. Quiting.')
        return False
    except AttributeError:
        print(f'Empty cell, perhaps, on line {index+2}?')
        logger.error(f'Empty cell, perhaps, on line {index+2}?')

def get_files_to_rename(target_dir):
    files_to_rename = []
    if target_dir.is_dir() is True:
        print('Target is directory. Continuing.'), logger.info('Target is directory. Continuing.')
        logging.info('This is a test.')
        for file_path in target_dir.iterdir():
            if Path(file_path).is_file():
                files_to_rename.append(file_path)
    else:
        print('Target is not a directory')
        quit()
    # cleanup list
    for file in files_to_rename:
        if Path(file).name.startswith('.'):
            print(f'Found {file}... removing from list.'), logger.info(f'Found {file}... removing from list.')
            files_to_rename.remove(file)
    return files_to_rename

def are_there_dups(file_list):
    boolean = not file_list.is_unique
    if boolean is True:
        return True
    else:
        return False

def rename_files(target_files, master_file_names):
    rename_count = 0
    num_master_names_checked = 0
    print(f'Examining {len(target_files)} files...'), logger.info(f'Examining {len(target_files)} files...')
    for series_name, master_name in master_file_names.items():
        row_num = series_name + 2
        for file in target_files:
            file_name = os.path.splitext(os.path.basename(file))[0]
            file_ext = os.path.splitext(os.path.basename(file))[1]
            if file_name == master_name:
                log_entry = (f'Searching sheet row {row_num} and found a match with master name {master_name}\n'
                             f'Found that {file_name}{file_ext} matches a file in the list of master files...\n'
                             f'The proxy name is: {proxy_names[series_name]}')
                print(log_entry), logger.info(log_entry)
                try:
                    new_file_name = proxy_names[series_name] + MASTER_FILE_SUFFIX + file_ext
                    Path.rename(file, (os.path.dirname(file) + '/' + new_file_name))
                    rename_count += 1
                    print(f'rename count is now {rename_count}')
                except FileNotFoundError as e:
                    print(f'Duplicate in list? On line {row_num}' + str(e)), logger.error(f'Duplicate in list? On line '
                                                                                          f'{row_num}')
                    continue
                except TypeError:
                    print(f'Empty cell on line {row_num}?'), logger.info(f'Empty cell on line {row_num}?')
                else:
                    print(f'Renaming {file} to: {new_file_name}\n'), logger.info(f'Renaming {file} to: {new_file_name}')
        num_master_names_checked += 1
    print(f'Files renamed: {rename_count}.\nChecked against: {num_master_names_checked} master names.')
    logger.info(f'Files renamed: {rename_count}.\nChecked against: {num_master_names_checked} master names.')

def main():
    # Check if columns have valid names and characters.
    for series_name, file in proxy_names.items():
        if is_ascii(file, series_name) is False:
            quit()
    for series_name, file in master_file_names.items():
        if is_ascii(file, series_name) is False:
            quit()
    # Check if columns have any duplicate entries. Quit program if they do.
    proxy_dup_check = are_there_dups(proxy_names)
    master_dup_check = are_there_dups(master_file_names)
    print(master_dup_check)
    if proxy_dup_check is True:
        print(f'Dups found in {RENAME_TO_COL}. Fix.'), logger.info('Dups found in proxy names columns. Fix.')
        quit()
    elif master_dup_check is True:
        print(f'Dups found in {FILES_TO_RENAME_COL}. Fix.'), logger.info('Dups found in proxy names columns. Fix.')
        quit()
    else:
        # Run the main renaming function
        rename_files(get_files_to_rename(target_dir), master_file_names)


if __name__ == '__main__':
    main()