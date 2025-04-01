#!/usr/bin/env python3
"""
Media Metadata Extractor

A tool to recursively scan a directory for media files, extract metadata using ffprobe,
and save the results to a spreadsheet.

Usage:
    python media_metadata_extractor.py /path/to/directory
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
import pandas as pd
from datetime import datetime


# Supported media file extensions
MEDIA_EXTENSIONS = [
    '.mp4', '.mov', '.mxf', '.avi', '.mkv', '.wmv', '.mpg', '.mpeg',
    '.m4v', '.webm', '.flv', '.vob', '.dv', '.3gp', '.m2ts', '.mts',
    '.ts', '.qt', '.f4v', '.ogv', '.divx', '.hevc', '.h264', '.h265'
]


def is_media_file(file_path):
    """Check if a file is a supported media file based on its extension."""
    return file_path.suffix.lower() in MEDIA_EXTENSIONS


def run_ffprobe(file_path):
    """
    Run ffprobe on the file and return the JSON output.
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            '-show_chapters',
            '-show_programs',
            '-show_error',
            str(file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error analyzing {file_path}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error parsing ffprobe output for {file_path}")
        return None


def extract_timecode(metadata):
    """
    Extract SMPTE timecode from metadata.
    """
    timecode = None
    
    # Look for timecode in stream tags
    if 'streams' in metadata:
        for stream in metadata['streams']:
            if 'tags' in stream:
                # Check for common timecode tag names
                for tag_name in ['timecode', 'TIMECODE', 'TIME', 'SMPTE_TIMECODE', 'start_timecode']:
                    if tag_name in stream.get('tags', {}):
                        return stream['tags'][tag_name]
    
    # Look in format tags
    if 'format' in metadata and 'tags' in metadata['format']:
        for tag_name in ['timecode', 'TIMECODE', 'TIME', 'SMPTE_TIMECODE', 'start_timecode']:
            if tag_name in metadata['format'].get('tags', {}):
                return metadata['format']['tags'][tag_name]
    
    return timecode


def get_video_stream(metadata):
    """
    Get the primary video stream from metadata.
    """
    if 'streams' in metadata:
        for stream in metadata['streams']:
            if stream.get('codec_type') == 'video' and stream.get('disposition', {}).get('default', 1) == 1:
                return stream
        
        # If no default video stream found, return the first video stream
        for stream in metadata['streams']:
            if stream.get('codec_type') == 'video':
                return stream
    
    return None


def get_audio_stream(metadata):
    """
    Get the primary audio stream from metadata.
    """
    if 'streams' in metadata:
        for stream in metadata['streams']:
            if stream.get('codec_type') == 'audio' and stream.get('disposition', {}).get('default', 1) == 1:
                return stream
        
        # If no default audio stream found, return the first audio stream
        for stream in metadata['streams']:
            if stream.get('codec_type') == 'audio':
                return stream
    
    return None


def extract_metadata(file_path):
    """
    Extract relevant metadata from a media file.
    """
    file_path = Path(file_path)
    metadata = run_ffprobe(file_path)
    
    if not metadata:
        return None
    
    result = {
        'file_name': file_path.name,
        'file_path': str(file_path),
        'file_size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
        'file_extension': file_path.suffix.lower(),
        'timecode': extract_timecode(metadata),
    }
    
    # Get format information
    if 'format' in metadata:
        format_info = metadata['format']
        result.update({
            'format_name': format_info.get('format_name', ''),
            'format_long_name': format_info.get('format_long_name', ''),
            'duration': float(format_info.get('duration', 0)),
            'bit_rate': int(format_info.get('bit_rate', 0)) if format_info.get('bit_rate') else 0,
        })
    
    # Get video stream information
    video_stream = get_video_stream(metadata)
    if video_stream:
        result.update({
            'video_codec': video_stream.get('codec_name', ''),
            'video_codec_long': video_stream.get('codec_long_name', ''),
            'width': video_stream.get('width', 0),
            'height': video_stream.get('height', 0),
            'resolution': f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
            'display_aspect_ratio': video_stream.get('display_aspect_ratio', ''),
            'pix_fmt': video_stream.get('pix_fmt', ''),
            'color_space': video_stream.get('color_space', ''),
            'color_transfer': video_stream.get('color_transfer', ''),
            'color_primaries': video_stream.get('color_primaries', ''),
            'frame_rate': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream.get('r_frame_rate') else 0,
            'bit_depth': '',  # Will try to extract from pix_fmt
        })
        
        # Try to extract bit depth from pixel format
        pix_fmt = video_stream.get('pix_fmt', '')
        if pix_fmt:
            if '10' in pix_fmt:
                result['bit_depth'] = '10-bit'
            elif '12' in pix_fmt:
                result['bit_depth'] = '12-bit'
            elif '16' in pix_fmt:
                result['bit_depth'] = '16-bit'
            else:
                result['bit_depth'] = '8-bit'
    
    # Get audio stream information
    audio_stream = get_audio_stream(metadata)
    if audio_stream:
        result.update({
            'audio_codec': audio_stream.get('codec_name', ''),
            'audio_codec_long': audio_stream.get('codec_long_name', ''),
            'sample_rate': audio_stream.get('sample_rate', ''),
            'channels': audio_stream.get('channels', 0),
            'channel_layout': audio_stream.get('channel_layout', ''),
        })
    
    return result


def scan_directory(directory_path):
    """
    Recursively scan a directory for media files and extract metadata.
    """
    directory_path = Path(directory_path)
    metadata_list = []
    
    print(f"Scanning directory: {directory_path}")
    
    # Count total files for progress reporting
    total_files = sum(1 for p in directory_path.glob('**/*') if p.is_file() and is_media_file(p))
    processed_files = 0
    
    for file_path in directory_path.glob('**/*'):
        if file_path.is_file() and is_media_file(file_path):
            processed_files += 1
            print(f"Processing file {processed_files}/{total_files}: {file_path.name}")
            
            metadata = extract_metadata(file_path)
            if metadata:
                metadata_list.append(metadata)
    
    return metadata_list


def save_to_excel(metadata_list, output_path=None):
    """
    Save the metadata list to an Excel file.
    """
    if not metadata_list:
        print("No metadata to save.")
        return
    
    # Create a DataFrame from the metadata list
    df = pd.DataFrame(metadata_list)
    
    # Reorder columns to prioritize important information
    important_columns = [
        'file_name', 'file_path', 'timecode', 'resolution', 'width', 'height',
        'color_space', 'color_transfer', 'color_primaries', 'bit_depth', 'frame_rate',
        'duration', 'video_codec', 'audio_codec', 'format_name', 'file_size_mb'
    ]
    
    # Ensure all important columns exist, and append any additional columns
    columns = [col for col in important_columns if col in df.columns]
    columns += [col for col in df.columns if col not in important_columns]
    
    df = df[columns]
    
    # Generate output filename if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"media_metadata_{timestamp}.xlsx"
    
    # Save to Excel
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"Metadata saved to: {output_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Extract metadata from media files and save to Excel.')
    parser.add_argument('directory', help='Directory to scan for media files')
    parser.add_argument('-o', '--output', help='Output Excel file path')
    
    args = parser.parse_args()
    
    # Check if ffprobe is available
    try:
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffprobe not found. Please install ffmpeg and make sure it's in your PATH.")
        return 1
    
    # Scan directory for media files and extract metadata
    metadata_list = scan_directory(args.directory)
    
    if not metadata_list:
        print("No media files found in the specified directory.")
        return 1
    
    # Save metadata to Excel
    save_to_excel(metadata_list, args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
