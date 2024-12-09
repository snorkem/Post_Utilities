import os.path
import pandas as pd
from pathlib import Path
import sys
import unicodedata

excel_file = Path('/Users/Alex/Desktop/20241120_Master and Proxy Comparison.xlsx')
target_dir = Path(sys.argv[1])

master_file_suffix = '_M'
df = pd.read_excel(excel_file)
proxy_names = df['Avid Proxy Name']
master_file_names = df['Master Original Name']

def is_ascii(filename):
    try:
        filename.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def get_files_to_rename():
    files_to_rename = []
    if target_dir.is_dir() is True:
        print('Target is directory. Continuing.')
        for file_path in target_dir.iterdir():
            files_to_rename.append(file_path)
    else:
        print('Target is not a directory')
        quit()
    print(f'Found {len(files_to_rename)} potential files to rename.')
    return files_to_rename

def rename_files(target_files, master_file_names):
    rename_count = 0
    num_master_names_checked = 0
    print(f'Examining {len(target_files)} files...')
    for series_name, master_name in master_file_names.items():
        for file in target_files:
            file_name = os.path.splitext(os.path.basename(file))[0]
            file_ext = os.path.splitext(os.path.basename(file))[1]
            if file_name == master_name:
                print(f'Searching sheet row {series_name}...')
                print(f'Found that {file_name}{file_ext} matches a file in the list of master files...')
                print(f'The proxy name is: {proxy_names[series_name]}')
                print(f'Renaming {file} to: ' + (
                            os.path.dirname(file) + '/' + proxy_names[series_name] + master_file_suffix + file_ext) + '\n')
                Path.rename(file, (os.path.dirname(file) + '/' + proxy_names[series_name] + master_file_suffix + file_ext))
                rename_count += 1
        num_master_names_checked += 1
    print(f'Files renamed: {rename_count}.\nChecked against: {num_master_names_checked} master names.')

def main():
    for series_name, file in proxy_names.items():
        if is_ascii(file) is False:
            print(f'Non-ascii name in proxy name "{file}" on row {series_name}. Quiting.')
            quit()
    rename_files(get_files_to_rename(), master_file_names)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print("I love Ben")
    main()