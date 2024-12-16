import os
import sys
import pandas as pd
from pathlib import Path
import subprocess
import json
from timecode import Timecode

FILES_TO_GET_STATS = 'Master Original Name'
FILE_SIZE_COL = 'Master File Size (GB)'
DIMENSIONS_COL = 'Master Resolution'
CODEC_COL = 'Master Codec'
FRAME_RATE_COL ='Master FPS'
DURATION_COL = 'Master Duration'
START_TC_COL = 'Master Start'


STATS_TO_UPDATE = {
        'Thumbnail': 'Unknown', 'Name': 'Unknown', 'First File Name': 'Unknown', 'Manufacturer': 'Unknown', 'Size (GiB)': 'Unknown', 'Codec': 'Unknown',
        'Bitrate': 'Unknown', 'Frame Rate': 'Unknown', 'Width': 'Unknown', 'Height': 'Unknown',
        'Color Primaries': 'Unknown', 'White Balance': 'Unknown',  'Gamma': 'Unknown', 'Bit Depth': 'Unknown',
        'ISO/ASA': 'Unknown', 'Start Time': 'Unknown'
        }

# Get Excel file as user args
excel_file = Path(sys.argv[1])
target_dir = Path(sys.argv[2])
excel_file_out = Path(sys.argv[3])

# Read the Excel file into dataframe
df = pd.read_excel(excel_file)
df = df.fillna('')

# Define columns from spreadsheet to pull from by their headers.
file_names = df[FILES_TO_GET_STATS]
files_to_rename = []

def get_file_size_GiB(target_file: Path):
    # Returns GiB
    total_size = target_file.stat().st_size
    print(total_size)
    return round(total_size / 1000 ** 3, 2)

def get_file_paths(target_dir):
    if target_dir.is_dir() is True:
        print('Target is directory. Continuing.')
        for file_path in target_dir.iterdir():
            if Path(file_path).is_file():
                print('File found. Appending: ' + str(file_path))
                files_to_rename.append(file_path)
            elif Path(file_path).is_dir():
                print('Looking at subdirectory:' + str(file_path))
                get_file_paths(file_path)
    else:
        print('Target is not a directory')
        quit()
    # cleanup list
    for file in files_to_rename:
        if Path(file).name.startswith('.'):
            print(f'Found {file}... removing from list.')
            files_to_rename.remove(file)
    return files_to_rename

def convert_duration_tc_(fps, duration_from_json):
    tc1 = Timecode(fps, duration_from_json)
    tc1.set_fractional(False)
    return tc1

def get_file_stats(file: Path, stats_to_update):
    cmnd = ['ffprobe', '-print_format', 'json', '-show_format', '-show_streams', '-pretty', '-loglevel', 'quiet', file]
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
        print("========= error ========")
        print(err)
    media_stats = json.loads(out)['streams'][0]
    start_tc = convert_duration_tc_(str(media_stats['r_frame_rate']), str(media_stats['start_time']))
    stats_to_update.update({
        'Width': str(media_stats['width']),
        'Height': str(media_stats['height']),
        'Codec': str(media_stats['codec_name']),
        'Frame Rate': str(Timecode(media_stats['r_frame_rate']).framerate),
        'Duration': str(convert_duration_tc_(str(media_stats['r_frame_rate']), str(media_stats['duration']))),
        'Start Time': str(start_tc)
    })
    return stats_to_update

# Populate dataframe rows
def update_df_stats(df_in: pd.DataFrame, file_col: str):
    target_files = get_file_paths(target_dir)
    for row, value in df_in.iterrows():
        file_name_in_list = value[file_col]
        # print(target_files)
        # print(f'We\'re on row {row}')
        # print(file_name_in_list)
        for file in target_files:
            file_name = os.path.splitext(os.path.basename(file))[0]
            file_ext = os.path.splitext(os.path.basename(file))[1]
            if file_name == file_name_in_list:
                print(f'Looking at: {file_name}')
                print(f'{file} found! Matches name in spreadsheet.')
                new_file_stats = get_file_stats(file, STATS_TO_UPDATE)
                # print(new_file_stats)
                df_in.at[row, FILE_SIZE_COL] = get_file_size_GiB(file)
                df_in.at[row, DIMENSIONS_COL] = str(new_file_stats['Width'] + ' x ' + new_file_stats['Height'])
                df_in.at[row, CODEC_COL] = str(new_file_stats['Codec'])
                df_in.at[row, FRAME_RATE_COL] = str(new_file_stats['Frame Rate'])
                df_in.at[row, DURATION_COL] = str(new_file_stats['Duration'])
                df_in.at[row, START_TC_COL] = str(new_file_stats['Start Time'])
               # print(f'{file} resolution is {df.at[row, FILE_SIZE_COL]}')
               # print(f'start tc is {df.at[row, START_TC_COL]}')
    return df

def main():
    # run some shit
    if excel_file_out.suffix.lower() == '.xlsx':
        if target_dir.is_dir() is True:
            df_out = update_df_stats(df, FILES_TO_GET_STATS)
            print(f'Writing {excel_file_out}')
            df_out.to_excel(excel_file_out, index=False)
    else:
        print(excel_file.suffix.lower())
        print('Not valid output excel file name')

if __name__ == '__main__':
    main()