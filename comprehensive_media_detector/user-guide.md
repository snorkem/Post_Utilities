# COMPREHENSIVE MEDIA DETECTOR
# User Guide

**Version 1.0**  
April 2025

---

![Media Detector Logo](https://via.placeholder.com/800x200?text=Comprehensive+Media+Detector)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
   - [System Requirements](#system-requirements)
   - [Installing Python](#installing-python)
   - [Installing FFmpeg](#installing-ffmpeg)
   - [Installing Required Python Packages](#installing-required-python-packages)
3. [Basic Usage](#basic-usage)
   - [Running Your First Analysis](#running-your-first-analysis)
   - [Understanding the Output](#understanding-the-output)
4. [Advanced Features](#advanced-features)
   - [Black Frame Detection](#black-frame-detection)
   - [Flash Frame Detection](#flash-frame-detection)
   - [Audio Silence Detection](#audio-silence-detection)
   - [Output Formats](#output-formats)
5. [Command Line Options](#command-line-options)
6. [Troubleshooting](#troubleshooting)
7. [Appendix: Sample Reports](#appendix-sample-reports)

---

<div style="page-break-after: always;"></div>

## 1. Introduction

The Comprehensive Media Detector is a powerful tool designed to analyze video and audio files for quality control purposes. It was created to help media professionals identify common issues that can affect content quality.

### Key Features

The program detects three types of events:

- **Black Frames**: Sections of video where the image is completely or nearly black
- **Flash Frames**: Sudden bright frames that may cause discomfort or trigger photosensitive conditions
- **Silent Audio**: Sections where the audio drops out or falls below a specified threshold

### Use Cases

- **Video Editors**: Identify unwanted black or flash frames that may have been introduced during editing
- **Quality Control**: Verify that content meets technical specifications before delivery
- **Content Creators**: Ensure media is free from issues that could affect viewer experience
- **Broadcasters**: Check for compliance with photosensitivity guidelines
- **Archivists**: Identify potential issues in digitized or legacy content

The Comprehensive Media Detector provides a simple command-line interface that works consistently across Windows, macOS, and Linux platforms, making it suitable for integration into existing workflows.

<div style="page-break-after: always;"></div>

## 2. Installation

### System Requirements

- **Operating System**: 
  - Windows 10 or 11
  - macOS 10.15 or higher
  - Linux (Ubuntu 18.04+, Fedora 30+, or similar)
- **Python**: Version 3.7 or higher
- **FFmpeg**: Version 4.0 or higher
- **RAM**: 4GB minimum (8GB recommended for HD/4K video files)
- **Storage**: Sufficient disk space for your media files
- **Processor**: Multi-core CPU recommended for faster analysis

### Installing Python

#### Windows:
1. **Download Python:**
   - Visit the official Python website: https://www.python.org/downloads/
   - Click on the "Download Python" button for the latest version
   - **Important**: Check the box that says "Add Python to PATH" during installation
   
   ![Python Installation](https://via.placeholder.com/500x300?text=Python+Installation+Screenshot)

2. **Verify Installation:**
   - Open Command Prompt (search for "cmd" in the Start menu)
   - Type the following command and press Enter:
     ```
     python --version
     ```
   - You should see a response like "Python 3.x.x"

#### macOS:
1. **Install Python using Homebrew (recommended):**
   - Open Terminal
   - Install Homebrew if not already installed:
     ```
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```
   - Install Python:
     ```
     brew install python
     ```

2. **Alternatively, download from Python website:**
   - Visit https://www.python.org/downloads/macos/
   - Download the macOS installer
   - Open the downloaded .pkg file and follow the installation prompts

3. **Verify Installation:**
   - Open Terminal
   - Type:
     ```
     python3 --version
     ```

#### Linux:
1. **Install Python using package manager:**
   - For Ubuntu/Debian:
     ```
     sudo apt update
     sudo apt install python3 python3-pip
     ```
   - For Fedora:
     ```
     sudo dnf install python3 python3-pip
     ```

2. **Verify Installation:**
   - Open Terminal
   - Type:
     ```
     python3 --version
     ```

### Installing FFmpeg

#### Windows:
1. **Download FFmpeg:**
   - Visit https://ffmpeg.org/download.html
   - Click on "Windows Builds" under "Get packages & executable files"
   - Download a build from one of the provided links (e.g., gyan.dev or BtbN)
   - Extract the ZIP file to a location on your computer (e.g., C:\ffmpeg)

2. **Add FFmpeg to your PATH:**
   - Search for "Environment Variables" in the Start menu
   - Click "Edit the system environment variables"
   - Click "Environment Variables" button
   - Under "System variables", find "Path" and click "Edit"
   - Click "New" and add the path to the FFmpeg bin folder (e.g., C:\ffmpeg\bin)
   - Click "OK" to close all dialogs

   ![Adding to PATH](https://via.placeholder.com/500x300?text=Adding+to+PATH+Screenshot)

#### macOS:
1. **Install using Homebrew (recommended):**
   - Open Terminal
   - Install Homebrew if not already installed (see Python installation section)
   - Install FFmpeg:
     ```
     brew install ffmpeg
     ```

2. **Verify Installation:**
   - Type:
     ```
     ffmpeg -version
     ```

#### Linux:
1. **Install using package manager:**
   - For Ubuntu/Debian:
     ```
     sudo apt update
     sudo apt install ffmpeg
     ```
   - For Fedora:
     ```
     sudo dnf install ffmpeg
     ```

2. **Verify Installation:**
   - Type:
     ```
     ffmpeg -version
     ```

### Installing Required Python Packages

The Comprehensive Media Detector requires additional Python packages for certain features, particularly for Excel output.

1. **Open a terminal/command prompt**
2. **Navigate to your project directory:**
   ```
   cd path/to/directory/containing/comprehensive_media_detector.py
   ```
3. **Install required packages:**
   ```
   pip install pandas openpyxl
   ```
   On some systems, you might need to use `pip3` instead of `pip`:
   ```
   pip3 install pandas openpyxl
   ```

<div style="page-break-after: always;"></div>

## 3. Basic Usage

### Running Your First Analysis

Let's start by analyzing a video file to detect black frames, flash frames, and audio silence.

1. **Open a terminal/command prompt**
2. **Navigate to the directory containing the script:**
   ```
   cd path/to/directory/containing/comprehensive_media_detector.py
   ```
3. **Run the program with a video file:**
   ```
   python comprehensive_media_detector.py -i path/to/your/video.mp4
   ```
   Replace "path/to/your/video.mp4" with the actual path to your video file.

   On macOS/Linux, you might need to use `python3` instead:
   ```
   python3 comprehensive_media_detector.py -i path/to/your/video.mp4
   ```

4. **Wait for the analysis to complete:**
   The program will display progress information as it analyzes the file.
   
   ![Analysis Progress](https://via.placeholder.com/500x150?text=Analysis+Progress)

5. **View the results:**
   When the analysis is complete, the program will create a report file in the same directory as your video file. By default, this will be named `[your_video_name]_analysis.txt`.

### Understanding the Output

The program generates a report containing detailed information about any detected events. 

#### Report Sections

1. **Header Information:**
   - File name and format
   - File size and bit rate
   - Video resolution and frame rate (if applicable)
   - Audio channels and sample rate (if applicable)
   - Total duration
   - Total frame count (for video)

2. **Summary Statistics:**
   - Total number of events detected
   - Number of black frame segments
   - Number of flash frame segments
   - Number of silence segments

3. **Detailed Event List:**
   A chronological list of all detected events, including:
   - Event number
   - Event type (BLACK, FLASH, or SILENCE)
   - Start and end times in SMPTE timecode format (HH:MM:SS:FF)
   - Start and end times in seconds
   - Duration in timecode and seconds
   - Start and end frame numbers (for video events)
   - Total frame count for each event

#### Example Output:

```
==============================================================================
MEDIA ANALYSIS REPORT
==============================================================================
File: sample_video.mp4
Format: mp4
Size: 24.35 MB
Bit Rate: 2500.21 kbps
Resolution: 1920x1080
FPS: 29.97
Audio: 2 channels, 48.0 kHz
Duration: 0:05:30
Total frames: 9885
Total events detected: 5
- Black segments: 2
- Flash segments: 1
- Silence segments: 2
------------------------------------------------------------------------------

#    TYPE       START TC        END TC          DURATION TC      START (s)    END (s)      DURATION (s)  START FRAME  END FRAME    FRAMES  
--------------------------------------------------------------------------------------------------------------------------------------
1    BLACK      00:00:00:00     00:00:00:12     00:00:00:12      0.000        0.401        0.401         0            12           12      
2    SILENCE    00:01:30:05     00:01:35:20     00:00:05:15      90.167       95.678       5.511         2701         2867         166     
3    FLASH      00:02:15:10     00:02:15:13     00:00:00:03      135.345      135.434      0.089         4056         4059         3       
4    BLACK      00:04:20:01     00:04:20:25     00:00:00:24      260.034      260.836      0.802         7794         7796         2       
5    SILENCE    00:05:25:15     00:05:30:00     00:00:04:15      325.501      330.000      4.499         9755         9885         130     
```

<div style="page-break-after: always;"></div>

## 4. Advanced Features

### Black Frame Detection

The program identifies sections of video where the image is predominantly black. This detection is controlled by a threshold parameter, which determines how dark a frame must be to be considered "black."

#### Use Cases:
- Find unintended black frames between scenes
- Detect encoding issues that may cause black frames
- Identify intentional fade-to-black sections that may be too long
- Check for blank sections in archival footage

#### Adjusting Black Frame Detection:

You can adjust the sensitivity of black frame detection using the `-b` or `--black-th` parameter:
```
python comprehensive_media_detector.py -i video.mp4 -b 0.05
```

The threshold is a value between 0 and 1:
- **Lower values** (e.g., 0.05) make detection more strict, only finding very dark frames
- **Higher values** (e.g., 0.2) make detection more lenient, finding frames with some brightness

![Black Frame Thresholds](https://via.placeholder.com/600x200?text=Black+Frame+Threshold+Examples)

#### Example Command:
For content that requires strict quality control:
```
python comprehensive_media_detector.py -i video.mp4 -b 0.05 -d 0.01
```
This will detect very dark frames (below 5% brightness) that last at least 0.01 seconds.

### Flash Frame Detection

Flash frame detection identifies sudden bright frames or sequences that could cause viewer discomfort or trigger photosensitive conditions. This is particularly important for content that will be viewed by a wide audience.

#### Use Cases:
- Identify editing errors that introduced flash frames
- Check for compliance with photosensitivity guidelines
- Find problematic camera flashes or bright transitions
- Detect strobe effects or rapid light changes

#### Adjusting Flash Detection:

Adjust flash detection sensitivity with the `-l` or `--flash-th` parameter:
```
python comprehensive_media_detector.py -i video.mp4 -l 0.8
```

The threshold is a value between 0 and 1:
- **Lower values** (e.g., 0.8) detect more subtle brightness changes
- **Higher values** (e.g., 0.95) only detect extreme flashes

#### Example Command:
For screening content with photosensitivity concerns:
```
python comprehensive_media_detector.py -i video.mp4 -l 0.8 --detect-black=False --detect-silence=False
```
This will focus only on detecting flash frames with increased sensitivity (detecting frames above 80% brightness).

### Audio Silence Detection

This feature identifies sections where audio is silent or below a specified volume threshold. It's useful for finding audio dropouts, encoding issues, or intentional silent segments.

#### Use Cases:
- Detect audio dropouts or encoding problems
- Find missing audio segments
- Identify intentional silence that may be too long
- Check for audio sync issues (when combined with black frame detection)

#### Adjusting Silence Detection:

Adjust the silence detection threshold with the `-s` or `--silence-th` parameter:
```
python comprehensive_media_detector.py -i video.mp4 -s -50
```

The threshold is in decibels (dB):
- **Higher values** (e.g., -40 dB) detect quieter sounds as silence
- **Lower values** (e.g., -70 dB) only detect near-complete silence

#### Example Command:
For detecting subtle audio issues:
```
python comprehensive_media_detector.py -i video.mp4 -s -40 --detect-black=False --detect-flash=False
```
This will focus only on audio silence detection with increased sensitivity.

### Output Formats

The program supports three output formats to accommodate different workflows.

#### 1. TXT Format (Default)

A human-readable text file with well-formatted columns:
```
python comprehensive_media_detector.py -i video.mp4 -f txt
```

Benefits:
- Easy to read directly
- Compatible with any text editor
- Compact file size

#### 2. CSV Format

Comma-separated values format for importing into spreadsheet software:
```
python comprehensive_media_detector.py -i video.mp4 -f csv
```

Benefits:
- Import into Excel, Google Sheets, or other spreadsheet applications
- Easy sorting and filtering of results
- Compatible with data analysis tools

#### 3. XLSX Format

Native Excel format with proper formatting:
```
python comprehensive_media_detector.py -i video.mp4 -f xlsx
```

Benefits:
- Proper column formatting and data types
- Multiple sheets with organized information
- Direct integration with Excel workflows

**Note**: XLSX format requires the pandas and openpyxl packages to be installed.

<div style="page-break-after: always;"></div>

## 5. Command Line Options

The Comprehensive Media Detector provides numerous command line options to customize its behavior. Here's a complete reference:

### Required Parameters

| Option | Description | Example |
|--------|-------------|---------|
| `-i`, `--input` | Input media file to analyze (required) | `-i video.mp4` |

### Output Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-o`, `--output` | Output file name | `<input>_analysis.<format>` | `-o report.txt` |
| `-f`, `--format` | Output format (txt, csv, xlsx) | `txt` | `-f xlsx` |

### Detection Thresholds

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-d`, `--duration` | Minimum event duration in seconds | `0.02` | `-d 0.5` |
| `-b`, `--black-th` | Threshold for black frame detection (0-1) | `0.1` | `-b 0.05` |
| `-l`, `--flash-th` | Threshold for flash frame detection (0-1) | `0.9` | `-l 0.8` |
| `-s`, `--silence-th` | Threshold for silence detection in dB | `-60` | `-s -50` |

### Video Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-r`, `--fps` | Frames per second (auto-detected if not specified) | auto | `-r 30` |

### Detection Toggles

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--detect-black` | Enable/disable black frame detection | `True` | `--detect-black=False` |
| `--detect-flash` | Enable/disable flash frame detection | `True` | `--detect-flash=False` |
| `--detect-silence` | Enable/disable silence detection | `True` | `--detect-silence=False` |

### Other Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-v`, `--verbose` | Enable verbose output | `False` | `-v` |
| `-h`, `--help` | Show help message | N/A | `--help` |

### Example Commands

Here are some example commands for common use cases:

1. **Basic analysis with default settings:**
   ```
   python comprehensive_media_detector.py -i video.mp4
   ```

2. **Detect only black frames with custom threshold:**
   ```
   python comprehensive_media_detector.py -i video.mp4 --detect-flash=False --detect-silence=False -b 0.05
   ```

3. **Detect only audio silence with custom threshold:**
   ```
   python comprehensive_media_detector.py -i video.mp4 --detect-black=False --detect-flash=False -s -50
   ```

4. **Analyze with custom minimum duration (0.5 seconds):**
   ```
   python comprehensive_media_detector.py -i video.mp4 -d 0.5
   ```

5. **Generate an Excel report with a custom output name:**
   ```
   python comprehensive_media_detector.py -i video.mp4 -f xlsx -o custom_report.xlsx
   ```

6. **Analyze with all detection types and custom thresholds:**
   ```
   python comprehensive_media_detector.py -i video.mp4 -b 0.05 -l 0.85 -s -45 -d 0.1
   ```

<div style="page-break-after: always;"></div>

## 6. Troubleshooting

This section addresses common issues that users might encounter when running the Comprehensive Media Detector.

### Installation Issues

#### Problem: "Python is not recognized as an internal or external command"

**Solution (Windows):**
1. Make sure you checked "Add Python to PATH" during installation
2. If you skipped this step, you can:
   - Reinstall Python with the PATH option checked, or
   - Manually add Python to your PATH environment variable
   
   To manually add Python to PATH:
   1. Find your Python installation folder (e.g., C:\Python39)
   2. Follow the steps to edit the PATH environment variable
   3. Add both the main Python folder and the Scripts subfolder

**Solution (macOS/Linux):**
1. Use `python3` instead of `python`
2. Or add an alias in your shell profile:
   ```
   echo 'alias python=python3' >> ~/.bash_profile
   source ~/.bash_profile
   ```

#### Problem: "FFmpeg/FFprobe is not installed or not found in PATH"

**Check if FFmpeg is installed:**
```
ffmpeg -version
```

If this gives an error:

**Windows:**
1. Make sure you added the FFmpeg bin directory to your PATH
2. Restart your command prompt after making PATH changes
3. Try using the full path to FFmpeg temporarily:
   ```
   C:\path\to\ffmpeg\bin\ffmpeg.exe -version
   ```

**macOS:**
1. If using Homebrew, reinstall FFmpeg:
   ```
   brew reinstall ffmpeg
   ```
2. Check if FFmpeg is in your PATH:
   ```
   which ffmpeg
   ```

**Linux:**
1. Reinstall FFmpeg using your package manager
2. Make sure you have sufficient permissions

#### Problem: "Error: pandas is required for Excel output"

This occurs when trying to output in XLSX format without the required packages.

**Solution:**
```
pip install pandas openpyxl
```

Or on some systems:
```
pip3 install pandas openpyxl
```

### Analysis Issues

#### Problem: No events detected despite known issues in the file

**Solutions:**
1. **Adjust the thresholds**:
   - For black frames: Lower the threshold (`-b 0.05`) to detect darker frames
   - For flash frames: Lower the threshold (`-l 0.7`) to catch more subtle flashes
   - For silence: Increase the threshold (`-s -50`) to detect quieter audio as silence
   
2. **Reduce the minimum duration**:
   - Use a smaller duration value (`-d 0.01`) to detect brief events

3. **Check the file format**:
   - Some container formats or codecs may not be fully compatible
   - Try converting the file to a different format using FFmpeg:
     ```
     ffmpeg -i input.mkv -c:v libx264 -c:a aac output.mp4
     ```

4. **Enable verbose mode**:
   - Use the `-v` flag to see detailed processing information:
     ```
     python comprehensive_media_detector.py -i video.mp4 -v
     ```

#### Problem: Too many false positives

**Solutions:**
1. **Make the thresholds more strict**:
   - For black frames: Increase the threshold (`-b 0.15`) to only detect very dark frames
   - For flash frames: Increase the threshold (`-l 0.95`) to only detect extreme flashes
   - For silence: Lower the threshold (`-s -70`) to only detect complete silence
   
2. **Increase the minimum duration**:
   - Use a larger duration value (`-d 0.1` or higher) to ignore very brief events
   
3. **Disable detection types you don't need**:
   - Use the detection toggles to focus only on what you need:
     ```
     python comprehensive_media_detector.py -i video.mp4 --detect-flash=False --detect-silence=False
     ```

#### Problem: The program runs very slowly on large files

**Solutions:**
1. **Process only what you need**:
   - Disable detection types you don't need
   - Consider analyzing smaller segments if possible

2. **Hardware considerations**:
   - Run on a machine with more CPU cores
   - Close other CPU-intensive applications
   - Ensure sufficient RAM is available

3. **Generate a simple output format**:
   - Use TXT format instead of XLSX for faster processing

<div style="page-break-after: always;"></div>

## 7. Appendix: Sample Reports

### Sample TXT Report

```
==============================================================================
MEDIA ANALYSIS REPORT
==============================================================================
File: sample_video.mp4
Format: mp4
Size: 24.35 MB
Bit Rate: 2500.21 kbps
Resolution: 1920x1080
FPS: 29.97
Audio: 2 channels, 48.0 kHz
Duration: 0:05:30
Total frames: 9885
Total events detected: 5
- Black segments: 2
- Flash segments: 1
- Silence segments: 2
------------------------------------------------------------------------------

#    TYPE       START TC        END TC          DURATION TC      START (s)    END (s)      DURATION (s)  START FRAME  END FRAME    FRAMES  
--------------------------------------------------------------------------------------------------------------------------------------
1    BLACK      00:00:00:00     00:00:00:12     00:00:00:12      0.000        0.401        0.401         0            12           12      
2    SILENCE    00:01:30:05     00:01:35:20     00:00:05:15      90.167       95.678       5.511         2701         2867         166     
3    FLASH      00:02:15:10     00:02:15:13     00:00:00:03      135.345      135.434      0.089         4056         4059         3       
4    BLACK      00:04:20:01     00:04:20:25     00:00:00:24      260.034      260.836      0.802         7794         7796         2       
5    SILENCE    00:05:25:15     00:05:30:00     00:00:04:15      325.501      330.000      4.499         9755         9885         130     
```

### Sample CSV Report

When opened in a spreadsheet application, the CSV report will look like this:

![CSV Report](https://via.placeholder.com/600x200?text=CSV+Report+Example)

The CSV format includes the same information as the TXT report but in a format that can be easily imported into spreadsheet software for further analysis or filtering.

### Sample XLSX Report

The Excel report organizes the same information in a professionally formatted workbook:

![Excel Report](https://via.placeholder.com/600x400?text=Excel+Report+Example)

Benefits of the XLSX format include:
- Multiple sheets for organizing different types of information
- Proper data formatting (numbers, dates, etc.)
- Cell formatting for improved readability
- Built-in filtering and sorting capabilities
- Easy generation of charts and visualizations from the data

<div style="page-break-after: always;"></div>

## Step-by-Step Tutorial: Complete Workflow

Let's walk through a complete workflow for analyzing a video file from start to finish.

### Step 1: Prepare Your Environment

1. Open your terminal or command prompt
2. Navigate to your working directory:
   ```
   cd /path/to/your/working/directory
   ```
3. Ensure you have Python and FFmpeg installed:
   ```
   python --version
   ffmpeg -version
   ```
4. Make sure you have the Comprehensive Media Detector script:
   ```
   ls comprehensive_media_detector.py
   ```

### Step 2: Run a Basic Analysis

1. Run the script on your video file:
   ```
   python comprehensive_media_detector.py -i your_video.mp4
   ```
2. Review the terminal output to see if any problems are detected
3. Check the generated report file (`your_video_analysis.txt`)

### Step 3: Refine Your Analysis

Based on the initial results, you might want to adjust the parameters:

1. For more sensitive black frame detection:
   ```
   python comprehensive_media_detector.py -i your_video.mp4 -b 0.05
   ```
2. For more sensitive flash frame detection:
   ```
   python comprehensive_media_detector.py -i your_video.mp4 -l 0.8
   ```
3. For more sensitive silence detection:
   ```
   python comprehensive_media_detector.py -i your_video.mp4 -s -45
   ```

### Step 4: Generate a Comprehensive Report

For a detailed report in Excel format:
```
python comprehensive_media_detector.py -i your_video.mp4 -f xlsx -b 0.05 -l 0.85 -s -50 -d 0.1 -o detailed_report.xlsx
```

This command:
- Sets a 5% threshold for black frame detection
- Sets an 85% threshold for flash frame detection
- Sets a -50dB threshold for silence detection
- Sets a minimum duration of 0.1 seconds for all events
- Outputs to an Excel file named "detailed_report.xlsx"

### Step 5: Review and Take Action

1. Open the generated Excel report
2. Review the detected events
3. Use the timecodes to locate any problematic sections in your video editing software
4. Make necessary corrections to your content

---

## Conclusion

The Comprehensive Media Detector provides a powerful, flexible way to analyze media files for quality control purposes. By following this guide, you should now be able to:

- Install and set up the tool correctly
- Run basic and advanced analyses on your media files
- Interpret the results and make informed decisions
- Customize the analysis to fit your specific requirements

For additional help or to report issues, please contact the program developers.

---

© 2025 Comprehensive Media Detector Team. All rights reserved.

*End of User Guide*