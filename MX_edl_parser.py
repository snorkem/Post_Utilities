#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Standalone EDL Parser that finds entries with the same name and combines them into one entry:
- Source In from the first occurrence
- Source Out from the last occurrence
- Sequence In from the first occurrence
- Sequence Out from the last occurrence

No external libraries required.
Supports output in TXT, CSV, and Excel formats (Excel requires pandas).
"""

import sys
import os
import re
import csv
from collections import defaultdict

# Try to import pandas for Excel output (optional)
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class EDLEdit:
    """Simple class to represent an EDL edit"""
    def __init__(self):
        self.event_num = ""
        self.reel = ""
        self.channel = ""
        self.transition = ""
        self.source_in = ""
        self.source_out = ""
        self.record_in = ""
        self.record_out = ""
        self.source_file = ""
        self.clip_name = ""


def parse_timecode(tc_str):
    """
    Parse a timecode string into frame count for sorting purposes
    
    Args:
        tc_str (str): Timecode string in format "HH:MM:SS:FF"
        
    Returns:
        int: Frame count
    """
    # Convert semicolons to colons for consistent handling
    tc_str = tc_str.replace(';', ':')
    
    # Split the timecode
    parts = tc_str.split(':')
    if len(parts) != 4:
        return 0
    
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        frames = int(parts[3])
        
        # Use 24 as default fps for sorting purposes only
        fps = 24
        return frames + (seconds * fps) + (minutes * 60 * fps) + (hours * 60 * 60 * fps)
    except ValueError:
        return 0


def frames_to_timecode(frames):
    """
    Convert frame count to timecode string
    
    Args:
        frames (int): Number of frames
        
    Returns:
        str: Timecode string in format HH:MM:SS:FF
    """
    # Use 24 fps for conversion (adjust as needed)
    fps = 24
    
    total_seconds = frames // fps
    remaining_frames = frames % fps
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"


def fix_timecode(tc_str):
    """
    Ensure timecode is properly formatted
    
    Args:
        tc_str (str): Timecode string
        
    Returns:
        str: Formatted timecode
    """
    # Convert semicolons to colons
    tc_str = tc_str.replace(';', ':')
    
    # Match the timecode pattern
    match = re.match(r'(\d{1,2}):(\d{1,2}):(\d{1,2})[:|;](\d{1,2})', tc_str)
    if match:
        hours, minutes, seconds, frames = match.groups()
        
        # Ensure all parts are properly zero-padded
        hours = hours.zfill(2)
        minutes = minutes.zfill(2)
        seconds = seconds.zfill(2)
        frames = frames.zfill(2)
        
        return f"{hours}:{minutes}:{seconds}:{frames}"
    
    return tc_str


def parse_edl_file(edl_file_path):
    """
    Parse an EDL file without using external libraries
    
    Args:
        edl_file_path (str): Path to the EDL file
        
    Returns:
        dict: Dictionary with combined clip information
    """
    # Check if file exists
    if not os.path.exists(edl_file_path):
        print(f"Error: File {edl_file_path} does not exist.")
        return None
    
    # Read the EDL file
    with open(edl_file_path, 'r') as f:
        lines = f.readlines()
    
    # Process the EDL file
    current_edit = None
    edits = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip title and FCM lines
        if line.startswith('TITLE:') or line.startswith('FCM:'):
            continue
        
        # Process event/edit lines (standard form)
        # Format is typically: [event#] [reel] [channel] [transition] [trans_op] [src_in] [src_out] [rec_in] [rec_out]
        event_match = re.match(r'(\d+)\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+(\S+))?\s+(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})\s+(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})\s+(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})\s+(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})', line)
        
        if event_match:
            current_edit = EDLEdit()
            current_edit.event_num = event_match.group(1)
            current_edit.reel = event_match.group(2)
            current_edit.channel = event_match.group(3)
            current_edit.transition = event_match.group(4)
            current_edit.source_in = event_match.group(6)
            current_edit.source_out = event_match.group(7)
            current_edit.record_in = event_match.group(8)
            current_edit.record_out = event_match.group(9)
            edits.append(current_edit)
            continue
        
        # Process comments, clip names and source files
        if line.startswith('*') and current_edit:
            if "FROM CLIP NAME:" in line:
                current_edit.clip_name = line.split("FROM CLIP NAME:")[1].strip()
            elif "SOURCE FILE:" in line:
                current_edit.source_file = line.split("SOURCE FILE:")[1].strip()
    
    # Group edits by clip name or source file
    clips = defaultdict(list)
    
    for edit in edits:
        # Use source_file if available, otherwise use clip_name
        clip_id = edit.source_file if edit.source_file else edit.clip_name
        
        # Skip if no identifier is available
        if not clip_id:
            continue
        
        # Add edit to the appropriate group
        clips[clip_id].append(edit)
    
    # Process clips to create combined entries
    result = {}
    
    for clip_id, clip_edits in clips.items():
        if len(clip_edits) > 0:
            # Sort edits by record in timecode
            sorted_edits = sorted(clip_edits, key=lambda x: parse_timecode(x.record_in))
            
            # Get first and last occurrences
            first_edit = sorted_edits[0]
            last_edit = sorted_edits[-1]
            
            # Create combined entry
            result[clip_id] = {
                'source_in': fix_timecode(first_edit.source_in),
                'source_out': fix_timecode(last_edit.source_out),
                'sequence_in': fix_timecode(first_edit.record_in),
                'sequence_out': fix_timecode(last_edit.record_out)
            }
    
    return result


def prepare_edl_data(clips):
    """
    Prepare structured data from clips dictionary for various output formats
    
    Args:
        clips (dict): Dictionary containing combined clip information
        
    Returns:
        list: List of dictionaries with clip data
    """
    if not clips:
        return []
    
    data = []
    
    for clip_id, timecodes in clips.items():
        data.append({
            'Clip Name/Source File': clip_id,
            'Source In': timecodes['source_in'],
            'Source Out': timecodes['source_out'],
            'Sequence In': timecodes['sequence_in'],
            'Sequence Out': timecodes['sequence_out']
        })
    
    # Sort data by Sequence In timecode
    data.sort(key=lambda x: parse_timecode(x['Sequence In']))
    
    return data


def format_edl_output(clips, format_type='txt'):
    """
    Format clips dictionary into the requested output format
    
    Args:
        clips (dict): Dictionary containing combined clip information
        format_type (str): Output format ('txt', 'csv', or 'excel')
        
    Returns:
        str: Formatted output string (for txt format only)
    """
    if not clips:
        return "No clips found."
    
    # Get structured data
    data = prepare_edl_data(clips)
    
    if format_type == 'txt':
        output = []
        columns = ['Clip Name/Source File', 'Source In', 'Source Out', 'Sequence In', 'Sequence Out']
        
        # Add header
        header = columns[0].ljust(40)
        for col in columns[1:]:
            header += col.ljust(15)
        output.append(header)
        output.append("-" * 100)
        
        # Add data rows
        for row in data:
            # Format the row
            line = (f"{row['Clip Name/Source File'][:38]}..".ljust(40) if len(row['Clip Name/Source File']) > 38 
                   else row['Clip Name/Source File'].ljust(40))
            
            for col in columns[1:]:
                line += row[col].ljust(15)
            output.append(line)
            output.append("-" * 100)
        
        return "\n".join(output)
    
    # Other formats don't return anything as they save directly to file
    return None


def save_csv(data, output_file):
    """
    Save data as CSV file
    
    Args:
        data (list): List of dictionaries with clip data
        output_file (str): Output file path
    """
    columns = ['Clip Name/Source File', 'Source In', 'Source Out', 'Sequence In', 'Sequence Out']
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"CSV output saved to: {output_file}")


def save_excel(data, output_file):
    """
    Save data as Excel file
    
    Args:
        data (list): List of dictionaries with clip data
        output_file (str): Output file path
    """
    if not PANDAS_AVAILABLE:
        print("Warning: pandas is not installed. Excel output is not available.")
        print("Install pandas with: pip install pandas openpyxl")
        return False
    
    # Convert data to DataFrame
    df = pd.DataFrame(data)
    
    # Write to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='EDL Clips')
        
        # Auto-adjust column widths
        worksheet = writer.sheets['EDL Clips']
        for i, col in enumerate(df.columns):
            max_width = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 2  # Add a little extra space
            # Excel column index starts at 1
            worksheet.column_dimensions[chr(65 + i)].width = max_width
    
    print(f"Excel output saved to: {output_file}")
    return True


def analyze_clips(csv_file_path):
    """
    Analyze the parsed EDL data from CSV file to generate statistics
    
    Args:
        csv_file_path (str): Path to the CSV file with parsed EDL data
        
    Returns:
        dict: Dictionary containing analytics data
    """
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file {csv_file_path} does not exist.")
        return None
    
    # Read the CSV file
    with open(csv_file_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
    
    # Calculate clip durations and total time
    for clip in data:
        # Calculate source duration
        source_in_frames = parse_timecode(clip['Source In'])
        source_out_frames = parse_timecode(clip['Source Out'])
        source_duration_frames = source_out_frames - source_in_frames
        
        # Calculate sequence duration
        sequence_in_frames = parse_timecode(clip['Sequence In'])
        sequence_out_frames = parse_timecode(clip['Sequence Out'])
        sequence_duration_frames = sequence_out_frames - sequence_in_frames
        
        # Store durations in frames
        clip['Source Duration (frames)'] = source_duration_frames
        clip['Sequence Duration (frames)'] = sequence_duration_frames
        
        # Store durations in timecode format
        clip['Source Duration'] = frames_to_timecode(source_duration_frames)
        clip['Sequence Duration'] = frames_to_timecode(sequence_duration_frames)
    
    # Calculate total sequence duration (sum of all sequence durations)
    total_sequence_duration = sum(int(clip['Sequence Duration (frames)']) for clip in data)
    
    # Calculate basic statistics
    stats = {
        'total_clips': len(data),
        'total_sequence_duration_frames': total_sequence_duration,
        'total_sequence_duration': frames_to_timecode(total_sequence_duration),
        'clips_by_percentage': [],
        'longest_clip': None,
        'shortest_clip': None
    }
    
    # Find longest and shortest clips
    if data:
        longest_clip = max(data, key=lambda x: int(x['Sequence Duration (frames)']))
        shortest_clip = min(data, key=lambda x: int(x['Sequence Duration (frames)']))
        
        stats['longest_clip'] = {
            'name': longest_clip['Clip Name/Source File'],
            'duration': longest_clip['Sequence Duration'],
            'duration_frames': longest_clip['Sequence Duration (frames)']
        }
        
        stats['shortest_clip'] = {
            'name': shortest_clip['Clip Name/Source File'],
            'duration': shortest_clip['Sequence Duration'],
            'duration_frames': shortest_clip['Sequence Duration (frames)']
        }
    
    # Calculate percentage of total time for each clip
    for clip in data:
        percentage = (int(clip['Sequence Duration (frames)']) / total_sequence_duration) * 100 if total_sequence_duration > 0 else 0
        
        clip_stats = {
            'name': clip['Clip Name/Source File'],
            'duration': clip['Sequence Duration'],
            'duration_frames': clip['Sequence Duration (frames)'],
            'percentage': percentage
        }
        
        stats['clips_by_percentage'].append(clip_stats)
    
    # Sort clips by percentage (descending)
    stats['clips_by_percentage'].sort(key=lambda x: x['percentage'], reverse=True)
    
    return stats


def generate_analytics_report(stats, output_file):
    """
    Generate a formatted analytics report
    
    Args:
        stats (dict): Statistics dictionary from analyze_clips
        output_file (str): Path to save the report
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not stats:
        return False
    
    try:
        with open(output_file, 'w') as f:
            f.write("EDL ANALYTICS REPORT\n")
            f.write("===================\n\n")
            
            # Basic stats
            f.write(f"Total number of unique clips: {stats['total_clips']}\n")
            f.write(f"Total sequence duration: {stats['total_sequence_duration']}\n\n")
            
            # Longest/shortest clips
            if stats['longest_clip']:
                f.write(f"Longest clip: {stats['longest_clip']['name']}\n")
                f.write(f"  Duration: {stats['longest_clip']['duration']} ({stats['longest_clip']['duration_frames']} frames)\n\n")
            
            if stats['shortest_clip']:
                f.write(f"Shortest clip: {stats['shortest_clip']['name']}\n")
                f.write(f"  Duration: {stats['shortest_clip']['duration']} ({stats['shortest_clip']['duration_frames']} frames)\n\n")
            
            # Clips by percentage
            f.write("Clips by percentage of total time:\n")
            f.write("---------------------------------\n")
            for i, clip in enumerate(stats['clips_by_percentage'], 1):
                f.write(f"{i}. {clip['name']}\n")
                f.write(f"   Duration: {clip['duration']} ({clip['duration_frames']} frames)\n")
                f.write(f"   Percentage: {clip['percentage']:.2f}%\n\n")
        
        print(f"Analytics report saved to: {output_file}")
        return True
    
    except Exception as e:
        print(f"Error generating analytics report: {e}")
        return False


def generate_excel_analytics(stats, output_file):
    """
    Generate Excel analytics report with charts
    
    Args:
        stats (dict): Statistics dictionary from analyze_clips
        output_file (str): Path to save the Excel report
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not stats or not PANDAS_AVAILABLE:
        return False
    
    try:
        # Create dataframe for clip percentages
        percentage_data = []
        for clip in stats['clips_by_percentage']:
            clip_name = clip['name']
            # Truncate long names for better display
            if len(clip_name) > 30:
                clip_name = clip_name[:27] + "..."
                
            percentage_data.append({
                'Clip Name': clip_name,
                'Duration': float(clip['duration_frames']),
                'Percentage': clip['percentage']
            })
        
        df = pd.DataFrame(percentage_data)
        
        # Create Excel writer
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write summary sheet
            summary_data = {
                'Metric': [
                    'Total Clips', 
                    'Total Duration (frames)', 
                    'Total Duration',
                    'Longest Clip',
                    'Longest Clip Duration',
                    'Shortest Clip',
                    'Shortest Clip Duration'
                ],
                'Value': [
                    stats['total_clips'],
                    stats['total_sequence_duration_frames'],
                    stats['total_sequence_duration'],
                    stats['longest_clip']['name'] if stats['longest_clip'] else 'N/A',
                    stats['longest_clip']['duration'] if stats['longest_clip'] else 'N/A',
                    stats['shortest_clip']['name'] if stats['shortest_clip'] else 'N/A',
                    stats['shortest_clip']['duration'] if stats['shortest_clip'] else 'N/A'
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Write detailed percentages
            df.to_excel(writer, sheet_name='Clip Percentages', index=False)
            
            # Adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for i, col in enumerate(worksheet.columns):
                    max_length = 0
                    column = col[0].column_letter  # Get the column name
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2) if max_length < 50 else 50
                    worksheet.column_dimensions[column].width = adjusted_width
        
        print(f"Excel analytics report saved to: {output_file}")
        return True
    
    except Exception as e:
        print(f"Error generating Excel analytics report: {e}")
        return False


def main():
    """Main function to process EDL file"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Standalone EDL Parser')
    parser.add_argument('edl_file', help='Path to the EDL file')
    parser.add_argument('--format', choices=['txt', 'csv', 'excel', 'all'], default='txt', 
                        help='Output format (default: txt)')
    parser.add_argument('--analytics', action='store_true',
                        help='Generate analytics report')
    
    args = parser.parse_args()
    
    print(f"Parsing EDL file: {args.edl_file}")
    
    clips = parse_edl_file(args.edl_file)
    
    if not clips:
        return
    
    # Process output based on format
    base_path = os.path.splitext(args.edl_file)[0]
    output_formats = [args.format] if args.format != 'all' else ['txt', 'csv', 'excel']
    
    data = prepare_edl_data(clips)
    csv_file_path = None
    
    for format_type in output_formats:
        if format_type == 'txt':
            output = format_edl_output(clips, 'txt')
            output_file = f"{base_path}_parsed.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"Text output saved to: {output_file}")
            
            # Print to console as well
            print("\nOutput:")
            print(output)
            
        elif format_type == 'csv':
            output_file = f"{base_path}_parsed.csv"
            save_csv(data, output_file)
            csv_file_path = output_file
            
        elif format_type == 'excel':
            output_file = f"{base_path}_parsed.xlsx"
            save_excel(data, output_file)
    
    # If CSV wasn't explicitly requested but is needed for analytics, create it
    if args.analytics and csv_file_path is None and 'csv' not in output_formats:
        csv_file_path = f"{base_path}_parsed.csv"
        save_csv(data, csv_file_path)
    
    # Generate analytics if requested
    if args.analytics and csv_file_path:
        print("\nGenerating analytics reports...")
        stats = analyze_clips(csv_file_path)
        
        if stats:
            # Generate text report
            txt_analytics_file = f"{base_path}_analytics.txt"
            generate_analytics_report(stats, txt_analytics_file)
            
            # Generate Excel report if pandas is available
            if PANDAS_AVAILABLE:
                excel_analytics_file = f"{base_path}_analytics.xlsx"
                generate_excel_analytics(stats, excel_analytics_file)
            else:
                print("Pandas not available. Excel analytics report will not be generated.")
                print("Install pandas with: pip install pandas openpyxl")
    
    print("\nAll processing complete!")


if __name__ == "__main__":
    main()
