#!/usr/bin/env python3
"""
Comprehensive Media Detector

This script uses FFmpeg to detect black frames, flash frames, and audio silence in video files
and formats the output with proper timecodes at the correct frame rate.

Usage:
    python media_detector.py -i input_video.mp4 [options]

Options:
    -i, --input FILE       Input video file (required)
    -o, --output FILE      Output file (default: <input_name>_analysis.txt)
    -f, --format FORMAT    Output format: txt, csv, xlsx (default: txt)
    -d, --duration SEC     Minimum event duration in seconds (default: 0.02)
    -b, --black-th FLOAT   Pixel threshold for black (0-1, default: 0.1)
    -l, --flash-th FLOAT   Pixel threshold for flash (0-1, default: 0.9)
    -s, --silence-th FLOAT Noise threshold for silence in dB (default: -60)
    -r, --fps FLOAT        Frames per second (default: auto-detect, fallback to 24.0)
    -v, --verbose          Enable verbose output
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import timedelta

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class EventType:
    """Enumeration for event types"""
    BLACK = "black"
    FLASH = "flash"
    SILENCE = "silence"


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Detect black frames, flash frames, and audio silence in media files")
    
    parser.add_argument("-i", "--input", required=True, help="Input video file")
    parser.add_argument("-o", "--output", help="Output file (default: <input_name>_analysis.txt)")
    parser.add_argument("-f", "--format", choices=["txt", "csv", "xlsx"], default="txt",
                        help="Output format (default: txt)")
    parser.add_argument("-d", "--duration", type=float, default=0.02,
                        help="Minimum event duration in seconds (default: 0.02)")
    parser.add_argument("-b", "--black-th", type=float, default=0.1,
                        help="Pixel threshold for black (0-1, default: 0.1)")
    parser.add_argument("-l", "--flash-th", type=float, default=0.9,
                        help="Pixel threshold for flash (0-1, default: 0.9)")
    parser.add_argument("-s", "--silence-th", type=float, default=-60,
                        help="Noise threshold for silence in dB (default: -60)")
    parser.add_argument("-r", "--fps", type=float, default=24.0,
                        help="Frames per second (default: auto-detect, fallback to 24.0)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--detect-black", action="store_true", default=True,
                        help="Enable black frame detection (default: True)")
    parser.add_argument("--detect-flash", action="store_true", default=True,
                        help="Enable flash frame detection (default: True)")
    parser.add_argument("--detect-silence", action="store_true", default=True,
                        help="Enable audio silence detection (default: True)")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' not found")
        sys.exit(1)
    
    # Set default output file if not specified
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}_analysis.{args.format}"
    
    # Check if pandas is available for xlsx output
    if args.format == "xlsx" and not PANDAS_AVAILABLE:
        print("Error: pandas is required for Excel output. Install with 'pip install pandas openpyxl'")
        sys.exit(1)
    
    return args


def seconds_to_timecode(seconds, fps=24.0):
    """
    Convert seconds to SMPTE timecode (HH:MM:SS:FF).
    
    Args:
        seconds: Time in seconds
        fps: Frames per second
        
    Returns:
        Timecode string in HH:MM:SS:FF format
    """
    # Handle negative times (shouldn't happen but just in case)
    if seconds < 0:
        seconds = 0
        
    # Calculate total frames and convert to timecode parts
    total_frames = round(seconds * fps)
    
    hours = int(total_frames // (3600 * fps))
    minutes = int((total_frames % (3600 * fps)) // (60 * fps))
    secs = int((total_frames % (60 * fps)) // fps)
    frames = int(total_frames % fps)
    
    # Ensure the frame count is valid for the given fps
    if frames >= int(fps):
        frames = int(fps) - 1
        
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def frame_count(seconds, fps=24.0):
    """Convert seconds to frame count."""
    if seconds < 0:
        seconds = 0
    return round(seconds * fps)


def get_video_fps(input_file):
    """
    Get the frame rate of a video file using ffprobe.
    
    Args:
        input_file: Path to the input video file
        
    Returns:
        Frame rate as a float, or None if it cannot be determined
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        fps_str = result.stdout.strip()
        
        # FFprobe often returns frame rate as a fraction (e.g., "24000/1001")
        if '/' in fps_str:
            numerator, denominator = map(float, fps_str.split('/'))
            if denominator != 0:  # Avoid division by zero
                fps = numerator / denominator
            else:
                fps = 24.0  # Default to 24 fps if invalid fraction
        else:
            # If not a fraction, convert to float directly
            fps = float(fps_str)
        
        # Round to 3 decimal places for display
        fps = round(fps, 3)
        
        print(f"Detected video frame rate: {fps} fps")
        return fps
    except (subprocess.SubprocessError, ValueError) as e:
        print(f"Warning: Could not detect frame rate: {e}")
        print("Using default frame rate of 24.0 fps")
        return 24.0


def has_audio_stream(input_file):
    """
    Check if the input file has an audio stream.
    
    Args:
        input_file: Path to the input file
        
    Returns:
        Boolean indicating if the file has an audio stream
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Check if there are any audio streams
        return 'streams' in info and len(info['streams']) > 0
    except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return False


def get_media_info(input_file):
    """
    Get detailed media information using ffprobe.
    
    Args:
        input_file: Path to the input file
        
    Returns:
        Dictionary with media information
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Initialize with defaults
        media_info = {
            'width': 0,
            'height': 0,
            'fps': 24.0,
            'duration': 0,
            'total_frames': 0,
            'has_video': False,
            'has_audio': False,
            'audio_channels': 0,
            'audio_sample_rate': 0,
            'format_name': '',
            'size_bytes': 0,
            'bit_rate': 0
        }
        
        # Extract format information
        if 'format' in info:
            media_info['format_name'] = info['format'].get('format_name', '')
            if 'duration' in info['format']:
                media_info['duration'] = float(info['format']['duration'])
            if 'size' in info['format']:
                media_info['size_bytes'] = int(info['format']['size'])
            if 'bit_rate' in info['format']:
                media_info['bit_rate'] = int(info['format']['bit_rate'])
        
        # Process each stream
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                media_info['has_video'] = True
                media_info['width'] = int(stream.get('width', 0))
                media_info['height'] = int(stream.get('height', 0))
                
                # Get frame rate
                fps_str = stream.get('r_frame_rate', '24/1')
                if '/' in fps_str:
                    numerator, denominator = map(float, fps_str.split('/'))
                    fps = numerator / denominator if denominator != 0 else 24.0
                else:
                    fps = float(fps_str)
                
                media_info['fps'] = round(fps, 3)
                
                # Calculate total frames if we have duration and fps
                if media_info['duration'] > 0 and media_info['fps'] > 0:
                    media_info['total_frames'] = int(media_info['duration'] * media_info['fps'])
                
            elif stream.get('codec_type') == 'audio':
                media_info['has_audio'] = True
                media_info['audio_channels'] = int(stream.get('channels', 0))
                media_info['audio_sample_rate'] = int(stream.get('sample_rate', 0))
        
        return media_info
    except (subprocess.SubprocessError, ValueError, json.JSONDecodeError) as e:
        print(f"Warning: Could not get media info: {e}")
        return {
            'width': 0,
            'height': 0,
            'fps': 24.0,
            'duration': 0,
            'total_frames': 0,
            'has_video': False,
            'has_audio': False,
            'audio_channels': 0,
            'audio_sample_rate': 0,
            'format_name': '',
            'size_bytes': 0,
            'bit_rate': 0
        }


def detect_black_frames(input_file, duration=0.02, pixel_threshold=0.1, verbose=False):
    """
    Use FFmpeg to detect black frames in a video file.
    
    Args:
        input_file: Path to the input video file
        duration: Minimum duration of black frames to detect
        pixel_threshold: Threshold for considering a pixel "black" (0-1)
        verbose: Enable verbose output
        
    Returns:
        List of dictionaries containing black frame information
    """
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vf", f"blackdetect=d={duration}:pix_th={pixel_threshold}",
        "-an",  # Disable audio
        "-f", "null",  # Output to null
        "-"  # Output to stdout/stderr
    ]
    
    # Add verbosity options
    if not verbose:
        cmd.insert(1, "-hide_banner")
    
    # Run FFmpeg and capture stderr where blackdetect outputs its results
    print(f"Running black frame detection: {' '.join(cmd)}")
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    
    # Print raw output in verbose mode
    if verbose:
        print("\nRaw FFmpeg Output (Black Detection):")
        print("-" * 80)
        print(result.stderr)
        print("-" * 80)
    
    # Parse the output line by line to extract black frame information
    black_frames = []
    for line in result.stderr.splitlines():
        if "black_start" in line and "black_end" in line and "black_duration" in line:
            if verbose:
                print(f"Found blackdetect line: {line}")
            
            # Initialize variables
            start_time = end_time = duration = None
            
            # Extract values using manual parsing
            parts = line.split()
            for part in parts:
                if part.startswith("black_start:"):
                    start_time = float(part.split(":", 1)[1])
                elif part.startswith("black_end:"):
                    end_time = float(part.split(":", 1)[1])
                elif part.startswith("black_duration:"):
                    duration = float(part.split(":", 1)[1])
            
            # If all values were found, add to results
            if start_time is not None and end_time is not None and duration is not None:
                black_frames.append({
                    "type": EventType.BLACK,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration
                })
    
    return black_frames


def detect_flash_frames(input_file, duration=0.02, flash_threshold=0.9, verbose=False):
    """
    Use FFmpeg to detect flash frames in a video file.
    
    Args:
        input_file: Path to the input video file
        duration: Minimum duration of flash to detect
        flash_threshold: Threshold for considering a frame "flashed" (0-1)
        verbose: Enable verbose output
        
    Returns:
        List of dictionaries containing flash frame information
    """
    # For flash detection, we use the select filter with scene detection
    # where we set a high threshold to catch sudden brightness changes
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vf", f"select='gt(scene,{flash_threshold})',showinfo",
        "-f", "null",
        "-"
    ]
    
    # Add verbosity options
    if not verbose:
        cmd.insert(1, "-hide_banner")
    
    # Run FFmpeg and capture stderr
    print(f"Running flash frame detection: {' '.join(cmd)}")
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    
    # Print raw output in verbose mode
    if verbose:
        print("\nRaw FFmpeg Output (Flash Detection):")
        print("-" * 80)
        print(result.stderr)
        print("-" * 80)
    
    # Parse the showinfo lines for frame info
    flash_frames = []
    previous_timestamp = None
    flash_start = None
    
    # First, gather all the detected frame timestamps
    timestamps = []
    for line in result.stderr.splitlines():
        if "pts_time:" in line:
            # Extract the timestamp
            # The format is typically: "[Parsed_showinfo_1 @ ...] n:   X pts: ... pts_time:123.456 ..."
            pts_time_part = line.split("pts_time:")[1].split()[0]
            try:
                timestamp = float(pts_time_part)
                timestamps.append(timestamp)
            except ValueError:
                continue
    
    # Now group consecutive frames into flash segments
    if timestamps:
        flash_start = timestamps[0]
        flash_end = flash_start
        
        for i in range(1, len(timestamps)):
            # If this frame is consecutive with the previous one
            if timestamps[i] - flash_end <= duration * 2:  # Allow a small gap (2x duration)
                flash_end = timestamps[i]
            else:
                # End of a flash segment
                if flash_end - flash_start >= duration:  # Only add if it meets minimum duration
                    flash_frames.append({
                        "type": EventType.FLASH,
                        "start_time": flash_start,
                        "end_time": flash_end,
                        "duration": flash_end - flash_start
                    })
                # Start new segment
                flash_start = timestamps[i]
                flash_end = flash_start
        
        # Don't forget the last segment
        if flash_end - flash_start >= duration:
            flash_frames.append({
                "type": EventType.FLASH,
                "start_time": flash_start,
                "end_time": flash_end,
                "duration": flash_end - flash_start
            })
    
    return flash_frames


def detect_silence(input_file, duration=0.02, noise_threshold=-60, verbose=False):
    """
    Use FFmpeg to detect audio silence in a media file.
    
    Args:
        input_file: Path to the input file
        duration: Minimum duration of silence to detect
        noise_threshold: Threshold for considering audio as "silent" in dB
        verbose: Enable verbose output
        
    Returns:
        List of dictionaries containing silence information
    """
    # Check if the file has an audio stream first
    if not has_audio_stream(input_file):
        print("No audio stream found in the file. Skipping silence detection.")
        return []
    
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-af", f"silencedetect=n={noise_threshold}dB:d={duration}",
        "-f", "null",
        "-"
    ]
    
    # Add verbosity options
    if not verbose:
        cmd.insert(1, "-hide_banner")
    
    # Run FFmpeg and capture stderr
    print(f"Running audio silence detection: {' '.join(cmd)}")
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    
    # Print raw output in verbose mode
    if verbose:
        print("\nRaw FFmpeg Output (Silence Detection):")
        print("-" * 80)
        print(result.stderr)
        print("-" * 80)
    
    # Parse the output to extract silence information
    silence_events = []
    
    # The format is like:
    # [silencedetect @ ...] silence_start: 10.5
    # [silencedetect @ ...] silence_end: 15.2 | silence_duration: 4.7
    
    start_time = None
    
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            try:
                start_time = float(line.split("silence_start:")[1].strip())
                if verbose:
                    print(f"Found silence start: {start_time}")
            except (ValueError, IndexError):
                start_time = None
        
        elif "silence_end:" in line and "silence_duration:" in line and start_time is not None:
            try:
                end_part = line.split("silence_end:")[1].strip()
                end_time = float(end_part.split()[0])
                
                duration_part = line.split("silence_duration:")[1].strip()
                silence_duration = float(duration_part)
                
                if verbose:
                    print(f"Found silence end: {end_time}, duration: {silence_duration}")
                
                silence_events.append({
                    "type": EventType.SILENCE,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": silence_duration
                })
                
                # Reset start time
                start_time = None
            except (ValueError, IndexError):
                continue
    
    return silence_events


def create_txt_report(events, output_file, input_file, fps=24.0, media_info=None):
    """Create a text report of detected media events."""
    with open(output_file, 'w') as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write(f"MEDIA ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"File: {os.path.basename(input_file)}\n")
        
        # Add media information if available
        if media_info:
            f.write(f"Format: {media_info['format_name']}\n")
            f.write(f"Size: {media_info['size_bytes'] / (1024*1024):.2f} MB\n")
            f.write(f"Bit Rate: {media_info['bit_rate'] / 1000:.2f} kbps\n")
            
            if media_info['has_video']:
                f.write(f"Resolution: {media_info['width']}x{media_info['height']}\n")
                f.write(f"FPS: {media_info['fps']}\n")
            
            if media_info['has_audio']:
                f.write(f"Audio: {media_info['audio_channels']} channels, {media_info['audio_sample_rate'] / 1000:.1f} kHz\n")
            
            f.write(f"Duration: {timedelta(seconds=media_info['duration'])}\n")
            
            if media_info['has_video']:
                f.write(f"Total frames: {media_info['total_frames']}\n")
        
        # Count event types
        black_frames = sum(1 for event in events if event["type"] == EventType.BLACK)
        flash_frames = sum(1 for event in events if event["type"] == EventType.FLASH)
        silence_events = sum(1 for event in events if event["type"] == EventType.SILENCE)
        
        f.write(f"Total events detected: {len(events)}\n")
        f.write(f"- Black segments: {black_frames}\n")
        f.write(f"- Flash segments: {flash_frames}\n")
        f.write(f"- Silence segments: {silence_events}\n")
        f.write("-" * 80 + "\n\n")
        
        # Write column headers
        f.write(f"{'#':<5} {'TYPE':<10} {'START TC':<15} {'END TC':<15} {'DURATION TC':<15} {'START (s)':<12} {'END (s)':<12} {'DURATION (s)':<12} {'START FRAME':<12} {'END FRAME':<12} {'FRAMES':<8}\n")
        f.write("-" * 140 + "\n")
        
        # Write event information
        for i, event in enumerate(events, 1):
            start_tc = seconds_to_timecode(event["start_time"], fps)
            end_tc = seconds_to_timecode(event["end_time"], fps)
            duration_tc = seconds_to_timecode(event["duration"], fps)
            
            start_frame = frame_count(event["start_time"], fps)
            end_frame = frame_count(event["end_time"], fps)
            frame_duration = end_frame - start_frame
            
            type_str = event["type"].upper()
            
            f.write(f"{i:<5} {type_str:<10} {start_tc:<15} {end_tc:<15} {duration_tc:<15} "
                    f"{event['start_time']:<12.3f} {event['end_time']:<12.3f} {event['duration']:<12.3f} "
                    f"{start_frame:<12} {end_frame:<12} {frame_duration:<8}\n")


def create_csv_report(events, output_file, input_file, fps=24.0, media_info=None):
    """Create a CSV report of detected media events."""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write metadata as comments
        f.write(f"# MEDIA ANALYSIS REPORT\n")
        f.write(f"# File: {os.path.basename(input_file)}\n")
        
        # Add media information if available
        if media_info:
            f.write(f"# Format: {media_info['format_name']}\n")
            f.write(f"# Size: {media_info['size_bytes'] / (1024*1024):.2f} MB\n")
            f.write(f"# Bit Rate: {media_info['bit_rate'] / 1000:.2f} kbps\n")
            
            if media_info['has_video']:
                f.write(f"# Resolution: {media_info['width']}x{media_info['height']}\n")
                f.write(f"# FPS: {media_info['fps']}\n")
            
            if media_info['has_audio']:
                f.write(f"# Audio: {media_info['audio_channels']} channels, {media_info['audio_sample_rate'] / 1000:.1f} kHz\n")
            
            f.write(f"# Duration: {timedelta(seconds=media_info['duration'])}\n")
            
            if media_info['has_video']:
                f.write(f"# Total frames: {media_info['total_frames']}\n")
        
        # Count event types
        black_frames = sum(1 for event in events if event["type"] == EventType.BLACK)
        flash_frames = sum(1 for event in events if event["type"] == EventType.FLASH)
        silence_events = sum(1 for event in events if event["type"] == EventType.SILENCE)
        
        f.write(f"# Total events detected: {len(events)}\n")
        f.write(f"# - Black segments: {black_frames}\n")
        f.write(f"# - Flash segments: {flash_frames}\n")
        f.write(f"# - Silence segments: {silence_events}\n")
        f.write("#\n")
        
        # Write column headers
        writer.writerow([
            "Event", "Type", "Start TC", "End TC", "Duration TC", 
            "Start (s)", "End (s)", "Duration (s)",
            "Start Frame", "End Frame", "Frames"
        ])
        
        # Write event information
        for i, event in enumerate(events, 1):
            start_tc = seconds_to_timecode(event["start_time"], fps)
            end_tc = seconds_to_timecode(event["end_time"], fps)
            duration_tc = seconds_to_timecode(event["duration"], fps)
            
            start_frame = frame_count(event["start_time"], fps)
            end_frame = frame_count(event["end_time"], fps)
            frame_duration = end_frame - start_frame
            
            type_str = event["type"].upper()
            
            writer.writerow([
                i, type_str, start_tc, end_tc, duration_tc,
                f"{event['start_time']:.3f}", f"{event['end_time']:.3f}", f"{event['duration']:.3f}",
                start_frame, end_frame, frame_duration
            ])


def create_xlsx_report(events, output_file, input_file, fps=24.0, media_info=None):
    """Create an Excel report of detected media events."""
    # Create DataFrame
    data = []
    for i, event in enumerate(events, 1):
        start_tc = seconds_to_timecode(event["start_time"], fps)
        end_tc = seconds_to_timecode(event["end_time"], fps)
        duration_tc = seconds_to_timecode(event["duration"], fps)
        
        start_frame = frame_count(event["start_time"], fps)
        end_frame = frame_count(event["end_time"], fps)
        frame_duration = end_frame - start_frame
        
        type_str = event["type"].upper()
        
        data.append([
            i, type_str, start_tc, end_tc, duration_tc,
            event["start_time"], event["end_time"], event["duration"],
            start_frame, end_frame, frame_duration
        ])
    
    df = pd.DataFrame(data, columns=[
        "Event", "Type", "Start TC", "End TC", "Duration TC", 
        "Start (s)", "End (s)", "Duration (s)",
        "Start Frame", "End Frame", "Frames"
    ])
    
    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Create metadata for the sheet
        metadata_rows = [
            ["MEDIA ANALYSIS REPORT", ""],
            ["File", os.path.basename(input_file)]
        ]
        
        # Add media information if available
        if media_info:
            metadata_rows.extend([
                ["Format", media_info['format_name']],
                ["Size (MB)", f"{media_info['size_bytes'] / (1024*1024):.2f}"],
                ["Bit Rate (kbps)", f"{media_info['bit_rate'] / 1000:.2f}"]
            ])
            
            if media_info['has_video']:
                metadata_rows.extend([
                    ["Resolution", f"{media_info['width']}x{media_info['height']}"],
                    ["FPS", media_info['fps']]
                ])
            
            if media_info['has_audio']:
                metadata_rows.append(
                    ["Audio", f"{media_info['audio_channels']} channels, {media_info['audio_sample_rate'] / 1000:.1f} kHz"]
                )
            
            metadata_rows.append(["Duration", str(timedelta(seconds=media_info['duration']))])
            
            if media_info['has_video']:
                metadata_rows.append(["Total frames", media_info['total_frames']])
        
        # Count event types
        black_frames = sum(1 for event in events if event["type"] == EventType.BLACK)
        flash_frames = sum(1 for event in events if event["type"] == EventType.FLASH)
        silence_events = sum(1 for event in events if event["type"] == EventType.SILENCE)
        
        metadata_rows.extend([
            ["Total events detected", len(events)],
            ["Black segments", black_frames],
            ["Flash segments", flash_frames],
            ["Silence segments", silence_events],
            ["", ""]
        ])
        
        metadata_df = pd.DataFrame(metadata_rows)
        metadata_df.to_excel(writer, sheet_name='Media Analysis', index=False, header=False)
        
        # Write events data
        df.to_excel(writer, sheet_name='Media Analysis', startrow=len(metadata_rows) + 1, index=False)
        
        # Format columns
        worksheet = writer.sheets['Media Analysis']
        for col in ['F', 'G', 'H']:  # Format seconds columns
            for row in range(len(metadata_rows) + 3, len(metadata_rows) + 3 + len(data)):
                cell = f"{col}{row}"
                worksheet[cell].number_format = '0.000'


def main():
    """Main function."""
    args = parse_arguments()
    
    # Check if FFmpeg and FFprobe are installed
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: FFmpeg/FFprobe is not installed or not found in PATH")
        sys.exit(1)
    
    # Get detailed media information
    media_info = get_media_info(args.input)
    
    # Auto-detect frame rate if not specified with -r/--fps flag
    if args.fps == 24.0 and media_info['has_video']:  # Check if default value is being used
        if media_info['fps'] > 0:
            args.fps = media_info['fps']
        else:
            # Fallback to direct detection if get_media_info didn't provide fps
            detected_fps = get_video_fps(args.input)
            if detected_fps:
                args.fps = detected_fps
    
    print(f"Analyzing media file: {args.input}")
    
    # Initialize empty list for all detected events
    all_events = []
    
    # Detect black frames if enabled and file has video
    if args.detect_black and media_info['has_video']:
        black_frames = detect_black_frames(
            args.input,
            duration=args.duration,
            pixel_threshold=args.black_th,
            verbose=args.verbose
        )
        all_events.extend(black_frames)
        print(f"Found {len(black_frames)} black segments.")
    
    # Detect flash frames if enabled and file has video
    if args.detect_flash and media_info['has_video']:
        flash_frames = detect_flash_frames(
            args.input,
            duration=args.duration,
            flash_threshold=args.flash_th,
            verbose=args.verbose
        )
        all_events.extend(flash_frames)
        print(f"Found {len(flash_frames)} flash segments.")
    
    # Detect audio silence if enabled and file has audio
    if args.detect_silence and media_info['has_audio']:
        silence_events = detect_silence(
            args.input,
            duration=args.duration,
            noise_threshold=args.silence_th,
            verbose=args.verbose
        )
        all_events.extend(silence_events)
        print(f"Found {len(silence_events)} silence segments.")
    
    # Sort all events by start time
    all_events.sort(key=lambda x: x["start_time"])
    
    if not all_events:
        print("No events detected in the media file.")
        return
    
    print(f"Total events detected: {len(all_events)}")
    
    # Create report based on format
    if args.format == "txt":
        create_txt_report(all_events, args.output, args.input, args.fps, media_info)
    elif args.format == "csv":
        create_csv_report(all_events, args.output, args.input, args.fps, media_info)
    elif args.format == "xlsx":
        create_xlsx_report(all_events, args.output, args.input, args.fps, media_info)
    
    print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()