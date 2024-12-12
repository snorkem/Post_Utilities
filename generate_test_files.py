import os.path
import pandas as pd
from pathlib import Path
import sys
import unicodedata
import re

from openpyxl.worksheet.print_settings import PrintArea

excel_file = Path(sys.argv[1])
target_dir = Path(sys.argv[2])

master_file_suffix = '_M'
df = pd.read_excel(excel_file)
proxy_names = df['Avid Proxy Name']
master_file_names = df['Master Original Name']

re1 = re.compile(r"[<>/{}[\]~`]");

def make_dummy_files(target_dir, files):
    for index, item in files.items():
        item += '.mov'
        if re1.search(item):
            print(f"RE1: Invalid char detected in Master Names column {index+2}")
            quit()
        print(f'Generating: ' + str(Path(target_dir/item)))
        Path.touch(target_dir / item)


make_dummy_files(target_dir, master_file_names)
