# Lower Thirds Generator: User Manual

## Introduction

The Lower Thirds Generator is a powerful tool that creates professional-looking lower third graphics from Excel or CSV files. Lower thirds are the text overlays typically seen at the bottom of videos to identify speakers, locations, or provide additional information.

This guide will help you set up and use the Lower Thirds Generator, even if you have limited programming experience. The application is available in both a graphical user interface (GUI) version and a command-line interface (CLI) version.

## System Requirements

- Python 3.6 or higher
- Windows, macOS, or Linux operating system
- For CLI version: Basic understanding of using command-line/terminal
- An Excel (.xlsx) or CSV file with your text data

## Installation Guide

### Step 1: Install Python (if not already installed)

1. Visit python.org/downloads/
2. Download the latest version for your operating system
3. Run the installer
   - On Windows: Make sure to check "Add Python to PATH" during installation
   - On macOS/Linux: The installer should handle path settings automatically

### Step 2: Install Required Dependencies

Open your command prompt (Windows) or terminal (macOS/Linux) and run the following command:

```
pip install -r requirements.txt
```

Or install the dependencies individually:

```
pip install pillow pandas numpy PyQt5
```

If you want to create TIFF images with 16-bit depth, also install:

```
pip install tifffile
```

### Step 3: Download the Lower Thirds Generator

Download the following files from the source provided to you:
- `l3rds_gui.py` - The graphical user interface version
- `l3rds_from_excel.py` - The command-line version

## Preparing Your Data

Create an Excel (.xlsx) or CSV file with at least the following columns:

1. **Main Text**: The primary text (typically a name)
2. **Secondary Text**: The secondary text (typically a title or description)
3. **Justification**: Text position ("Left", "Right", "Center", "Lower Left", etc.)
4. **Main Font**: Font name or path to a font file

Optional columns you can add:
- **Secondary Font**: Font for the secondary text
- **File Name**: Custom filename for the output image
- **Main Font Size**: Custom font size for the main text
- **Secondary Font Size**: Custom font size for the secondary text
- **Padding**: Additional padding from the edge (in pixels)
- **Main Color**: Color for the main text (e.g., "white", "red", "#FFFFFF")
- **Secondary Color**: Color for the secondary text
- **Background Color**: Background color for the image
- **Bar Color**: Color for the lower third bar with optional transparency (e.g., "blue,128")
- **Text Outline**: Outline for text (format: WIDTH,COLOR[,OPACITY], e.g., "2,black")
- **Text Shadow**: Enable shadow (Yes/No or True/False)
- **Shadow Color**: Color for text shadow

## Using the GUI Version

### Starting the Application

1. Open your command prompt or terminal
2. Navigate to the folder containing the script
   ```
   cd path/to/script/folder
   ```
3. Run the GUI application
   ```
   python l3rds_gui.py
   ```

### Basic Usage

1. **File Selection Tab**:
   - Click "Browse..." to select your input Excel/CSV file
   - Click "Browse..." to select your output directory
   - Set dimensions and color preferences
   - Select output format options

2. **Advanced Settings Tab**:
   - Configure text effects (shadow, outline, spacing)
   - Adjust bar settings and other advanced options
   
3. **Generate Lower Thirds**:
   - Click "Test (Preview First)" to preview only the first lower third
   - Click "Generate Lower Thirds" to create all lower thirds from your file

### Main Features of the GUI

- Color selection with visual color pickers
- Real-time log display of the generation process
- Progress tracking for multiple lower thirds
- All settings accessible through an intuitive interface
- Preview option to test settings before full generation

## Using the CLI Version

### Basic Usage

1. Open your command prompt or terminal
2. Navigate to the folder containing the script
   ```
   cd path/to/script/folder
   ```
3. Run the script with your input file and output folder
   ```
   python l3rds_from_excel.py input.xlsx output_folder
   ```

This will generate lower thirds for all rows in your Excel/CSV file and save them in the specified output folder.

### Testing Your Settings

Before generating all images, you can test the settings on the first row:

```
python l3rds_from_excel.py input.xlsx output_folder --test
```

This will generate and preview only the first image, showing you all the settings being used.

### Common Command Options

Here are some commonly used options:

```
--width 1920           Set the image width (default: 1920)
--height 1080          Set the image height (default: 1080)
--bg-color blue        Set background color (default: black)
--text-color yellow    Set main text color (default: white)
--bar-color "red,128"  Set bar color with opacity (default: black,0)
--transparent          Use transparent background
--text-shadow          Enable text shadow effect
--format png           Output format: png, jpg, or tiff (default: png)
```

## Color Specification

You can specify colors in several ways:

1. **Color names**: "red", "blue", "darkgreen", "lightblue", etc.
2. **Hex codes**: "#FF0000" (red), "#0000FF" (blue)
3. **RGB values**: "255,0,0" (red), "0,0,255" (blue)
4. **With transparency**: "red,128" (semi-transparent red)

### Colors in Excel vs. Application Settings

Colors specified in your Excel/CSV file will override settings in both the GUI and command-line versions for individual rows. This allows you to have different color schemes for different lower thirds in the same batch.

## Example Command Lines (CLI Version)

### Basic usage with default settings:
```
python l3rds_from_excel.py credits.xlsx output_images
```

### Change dimensions and format:
```
python l3rds_from_excel.py credits.xlsx output_images --width 1280 --height 720 --format jpg
```

### Custom colors with transparency:
```
python l3rds_from_excel.py credits.xlsx output_images --bg-color black --text-color white --bar-color "blue,150"
```

### Add text effects:
```
python l3rds_from_excel.py credits.xlsx output_images --text-shadow --shadow-color "black" --text-outline "2,white"
```

## Troubleshooting

### Common Issues:

1. **"Python is not recognized as a command"**:
   - Solution: Make sure Python is installed and added to your PATH

2. **"Module not found" errors**:
   - Solution: Install missing modules using pip
     ```
     pip install [module_name]
     ```

3. **Font not found**:
   - Solution: Specify the full path to the font file or use a common system font

4. **Issues with transparency**:
   - Solution: Make sure to use PNG or TIFF format (JPG doesn't support transparency)

5. **Image quality issues**:
   - Solution: Use TIFF format with 16-bit depth for highest quality
     ```
     python l3rds_from_excel.py input.xlsx output_folder --format tiff --bit-depth 16
     ```

6. **GUI not starting**:
   - Solution: Make sure PyQt5 is installed:
     ```
     pip install PyQt5
     ```

## Advanced Usage

For more control over your lower thirds, explore these additional options in both the GUI and CLI versions:

- Shadow offset (default: 2,2)
- Shadow blur amount (default: 20)
- Shadow opacity (default: 128)
- Letter spacing between characters
- Vertical spacing between main and secondary text
- Text transformation (none, upper, lower, title)
- Custom bar height for the lower third bar

## Getting Help (CLI Version)

To see all available command line options:

```
python l3rds_from_excel.py --help
```

This will display comprehensive information about all the parameters and options available.

## Example Workflow

1. Create your Excel file with names, titles, and optional color settings
2. Start the GUI version: `python l3rds_gui.py`
3. Load your Excel file and select output folder
4. Test settings with the "Test (Preview First)" button
5. Adjust settings if needed
6. Generate all lower thirds with the "Generate Lower Thirds" button
7. Use the generated images in your video editing software

By following this guide, you should be able to create professional-looking lower thirds for your videos quickly and easily, even with limited programming experience.
