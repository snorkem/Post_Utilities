#!/usr/bin/env python3
"""
Lower Thirds Generator

A utility script to generate lower third graphics from Excel or CSV data.
This script is designed for visual effects and graphics workflows in film and TV.

EXCEL/CSV FORMAT:
Required columns (in this order):
1. Main Text      - The primary text (typically a name)
2. Secondary Text - The secondary text (typically a title or description)
3. Justification  - Text position: "Left", "Right", "Center", "Lower Left", "Lower Right", 
                    "Upper Left", "Upper Right", "Center Bottom", "Center Center", "Center Top"
4. Main Font      - Font name or path to font file for the main text

Optional columns:
- Secondary Font     - Font name or path for the secondary text (defaults to Main Font if not specified)
- File Name          - Custom filename for the output image
- Main Font Size     - Custom font size for the main text
- Secondary Font Size - Custom font size for the secondary text
- Padding            - Additional padding from the edge (in pixels)
- Main Color         - Color for the main text (can use color name or R,G,B)
- Secondary Color    - Color for the secondary text (can use color name or R,G,B)
- Background Color   - Background color for the image (can use color name or R,G,B)
- Bar Color          - Color for the lower third bar (can use color name or R,G,B[,A])
- Text Outline       - Outline for text (format: WIDTH,COLOR[,OPACITY])
- Text Shadow        - Enable shadow (Yes/No or True/False)
- Shadow Color       - Color for text shadow (can use color name or R,G,B)

USAGE:
    python lower_thirds.py input.xlsx output_folder [options]

OPTIONS:
    --width WIDTH                    Image width (default: 1920)
    --height HEIGHT                  Image height (default: 1080)
    --bg-color COLOR                 Background color (default: black) - Can use color name or R,G,B
    --text-color COLOR               Text color (default: white) - Can use color name or R,G,B
    --secondary-text-color COLOR     Secondary text color (default: same as text-color)
    --bar-color COLOR[,OPACITY]      Lower third bar color (default: black,0)
    --format {png,jpg,tiff}          Output format (default: png)
    --bit-depth {8,16}               Bit depth for TIFF images (default: 16)
    --transparent                    Use transparent background (for PNG and TIFF)
    --test                           Preview only the first image to check settings
    --debug                          Show additional debug information
    --text-shadow                    Enable text shadow effect
    --shadow-offset X,Y              Shadow offset X,Y in pixels (default: 2,2)
    --shadow-blur VALUE              Shadow blur amount 1-100 (default: 20)
    --shadow-color COLOR             Shadow color name or R,G,B (default: black)
    --shadow-opacity VALUE           Shadow opacity 0-255 (default: 128)
    --text-outline WIDTH,COLOR[,A]   Add outline to text (width in pixels, color, alpha)
    --letter-spacing PIXELS          Adjust spacing between characters
    --vertical-spacing PIXELS        Space between main and secondary text
    --text-transform {none,upper,lower,title}  Transform text case
    --bar-height PIXELS              Custom height for the lower third bar
    --bar-opacity VALUE              Set bar transparency (0-255)
    --skip-existing                  Skip generation if output file already exists

Note that colors can be specified in the Excel/CSV file and will override command-line options
for individual rows. This allows for different colors per lower third.
"""

import argparse
import os
import random
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
import numpy as np
import tempfile
import re

def color_name_to_rgb(color_name):
    """Convert common color names to RGB values."""
    color_map = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "purple": (128, 0, 128),
        "orange": (255, 165, 0),
        "pink": (255, 192, 203),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
        "brown": (165, 42, 42),
        "navy": (0, 0, 128),
        "teal": (0, 128, 128),
        "lime": (0, 255, 0),
        "maroon": (128, 0, 0),
        "olive": (128, 128, 0),
        "silver": (192, 192, 192),
        "gold": (255, 215, 0),
        "indigo": (75, 0, 130),
        "violet": (238, 130, 238),
        "turquoise": (64, 224, 208),
        "tan": (210, 180, 140),
        "salmon": (250, 128, 114),
        "skyblue": (135, 206, 235),
        "khaki": (240, 230, 140),
        "crimson": (220, 20, 60),
        "darkblue": (0, 0, 139),
        "darkgreen": (0, 100, 0),
        "darkred": (139, 0, 0),
        "darkgray": (169, 169, 169),
        "darkgrey": (169, 169, 169),
        "lightgray": (211, 211, 211),
        "lightgrey": (211, 211, 211),
        "lightblue": (173, 216, 230),
        "lightgreen": (144, 238, 144),
        "lightred": (255, 102, 102),
        "transparent": (0, 0, 0, 0),
    }
    
    # If input is None, return None
    if color_name is None:
        return None
    
    # Convert to lowercase and remove spaces
    color_name = str(color_name).lower().strip()
    
    # Check if it's a direct color name
    if color_name in color_map:
        return color_map[color_name]
    
    # Check if it's a hex color code (with or without #)
    hex_pattern = r'^#?([0-9a-fA-F]{6})$'
    match = re.match(hex_pattern, color_name)
    if match:
        hex_value = match.group(1)
        return (
            int(hex_value[0:2], 16),
            int(hex_value[2:4], 16),
            int(hex_value[4:6], 16)
        )
    
    # Check if it's in RGB format like "rgb(255,0,0)" or "255,0,0"
    rgb_pattern1 = r'^rgb\((\d+),\s*(\d+),\s*(\d+)\)$'
    rgb_pattern2 = r'^(\d+),\s*(\d+),\s*(\d+)$'
    
    match = re.match(rgb_pattern1, color_name)
    if not match:
        match = re.match(rgb_pattern2, color_name)
        
    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3))
        )
    
    # Check for color with alpha: "red,128" or "255,0,0,128"
    rgba_pattern = r'^(.+),\s*(\d+)$'
    match = re.match(rgba_pattern, color_name)
    if match:
        color_part = match.group(1)
        alpha = int(match.group(2))
        
        # Recursively process the color part
        rgb = color_name_to_rgb(color_part)
        if rgb:
            if len(rgb) == 3:
                return (*rgb, alpha)
            else:
                return (*rgb[:3], alpha)
    
    # Default to black if not recognized
    print(f"Warning: Color '{color_name}' not recognized. Using black instead.")
    return (0, 0, 0)

def parse_color_with_alpha(color_str, default_alpha=255):
    """Parse a color string which may include alpha component."""
    if not color_str:
        return None
        
    # Check for color with alpha: "red,128" or "255,0,0,128"
    rgba_pattern = r'^(.+),\s*(\d+)$'
    match = re.match(rgba_pattern, color_str)
    
    if match:
        color_part = match.group(1)
        alpha = int(match.group(2))
        
        # Get the RGB components
        rgb = color_name_to_rgb(color_part)
        if rgb:
            # Return RGBA
            if len(rgb) == 3:
                return (*rgb, alpha)
            else:
                return (*rgb[:3], alpha)
    
    # If no alpha specified in the string, process as regular color and add default alpha
    rgb = color_name_to_rgb(color_str)
    if rgb:
        if len(rgb) == 3:
            return (*rgb, default_alpha)
        return rgb  # Already has alpha
    
    return None

def load_data(file_path):
    """Load data from CSV or XLSX file."""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please use CSV or Excel files.")

def convert_blur_scale(blur_value):
    """Convert a 1-100 scale blur value to an appropriate Gaussian blur radius."""
    # Ensure value is within range
    blur_value = max(1, min(100, int(blur_value)))
    
    # Use a non-linear mapping for more intuitive feel
    # Low values (1-20): subtle blur (0.3-2.0)
    # Mid values (20-70): moderate blur (2.0-10.0)
    # High values (70-100): heavy blur (10.0-30.0)
    if blur_value < 20:
        # Subtle blur range: 0.3 to 2.0
        return 0.3 + (blur_value - 1) * (1.7 / 19)
    elif blur_value < 70:
        # Moderate blur range: 2.0 to 10.0
        return 2.0 + (blur_value - 20) * (8.0 / 50)
    else:
        # Heavy blur range: 10.0 to 30.0
        return 10.0 + (blur_value - 70) * (20.0 / 30)

def transform_text(text, transform_type):
    """Transform text based on the specified type."""
    if transform_type == 'upper':
        return text.upper()
    elif transform_type == 'lower':
        return text.lower()
    elif transform_type == 'title':
        return text.title()
    else:  # 'none' or any other value
        return text
        
def select_random_font():
    """Select a random font from system font directories."""
    # List all potential system font directories
    font_dirs = [
        "/usr/share/fonts/",  # Linux
        "/System/Library/Fonts/",  # macOS
        "C:\\Windows\\Fonts\\",  # Windows
        os.path.expanduser("~/.fonts/"),  # User fonts on Linux
        os.path.expanduser("~/Library/Fonts/"),  # User fonts on macOS
    ]
    
    # Collect all available font files
    available_fonts = []
    
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if file.endswith(('.ttf', '.otf', '.ttc')):
                        available_fonts.append(os.path.join(root, file))
    
    # If we found some fonts, return a random one
    if available_fonts:
        selected_font = random.choice(available_fonts)
        print(f"Randomly selected font: {os.path.basename(selected_font)}")
        return selected_font
    
    # Fallback to default fonts if no fonts found
    default_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "C:\\Windows\\Fonts\\arial.ttf",  # Windows
    ]
    
    for font in default_fonts:
        if os.path.exists(font):
            print(f"Using default font: {os.path.basename(font)}")
            return font
    
    # Last resort, return None and let the caller handle it
    print("Warning: No fonts found on the system.")
    return None

def find_font_file(font_name):
    """Find a font file by name or path."""
    if not font_name:
        return None
        
    # Handle the "Random" option
    if isinstance(font_name, str) and font_name.lower().strip() == "random":
        return select_random_font()
        
    # If it's a direct path and exists
    if os.path.exists(font_name):
        return font_name
        
    # Try to find the font by name in common font directories
    font_dirs = [
        "/usr/share/fonts/",  # Linux
        "/System/Library/Fonts/",  # macOS
        "C:\\Windows\\Fonts\\",  # Windows
        os.path.expanduser("~/.fonts/"),  # User fonts on Linux
        os.path.expanduser("~/Library/Fonts/"),  # User fonts on macOS
    ]
    
    # Try to find font by its name
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if font_name.lower() in file.lower() and file.endswith(('.ttf', '.otf', '.ttc')):
                        return os.path.join(root, file)
    
    # Fallback to default fonts
    default_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "C:\\Windows\\Fonts\\arial.ttf",  # Windows
    ]
    
    for font in default_fonts:
        if os.path.exists(font):
            return font
            
    return None

def generate_lower_third(row, output_dir=None, width=1920, height=1080, 
                         bg_color=(0, 0, 0), text_color=(255, 255, 255),
                         secondary_text_color=None,
                         bar_color=(0, 0, 0, 0), bar_height=None, bar_opacity=None,
                         format="png", bit_depth=16, transparent=False,
                         text_shadow=False, shadow_offset="2,2", 
                         shadow_blur=20, shadow_color="black", shadow_opacity=128,
                         text_outline=None,
                         letter_spacing=0, vertical_spacing=None,
                         text_transform='none',
                         preview_only=False, debug=False):
    """Generate a lower third image from a row of data."""
    if debug:
        print("\nDEBUG: Processing row:")
        for col_name, value in row.items():
            print(f"  {col_name}: {value} (type: {type(value)})")
    
    # Get column names for our DataFrame
    column_names = row.index.tolist()
    
    # Check for color specifications in the Excel/CSV data
    # These will override the command-line options if present
    
    # Check for Main Color in Excel
    for col in column_names:
        if col.strip() in ['Main Color', 'Main Text Color'] and pd.notna(row[col]):
            excel_text_color = color_name_to_rgb(str(row[col]))
            if excel_text_color:
                if debug:
                    print(f"DEBUG: Using main text color from Excel: {row[col]} -> {excel_text_color}")
                text_color = excel_text_color
                break
    
    # Check for Secondary Color in Excel
    for col in column_names:
        if col.strip() in ['Secondary Color', 'Secondary Text Color'] and pd.notna(row[col]):
            excel_secondary_color = color_name_to_rgb(str(row[col]))
            if excel_secondary_color:
                if debug:
                    print(f"DEBUG: Using secondary text color from Excel: {row[col]} -> {excel_secondary_color}")
                secondary_text_color = excel_secondary_color
                break
    
    # Check for Background Color in Excel
    for col in column_names:
        if col.strip() in ['Background Color', 'BG Color'] and pd.notna(row[col]):
            excel_bg_color = color_name_to_rgb(str(row[col]))
            if excel_bg_color:
                if debug:
                    print(f"DEBUG: Using background color from Excel: {row[col]} -> {excel_bg_color}")
                bg_color = excel_bg_color
                break
    
    # Check for Bar Color in Excel
    for col in column_names:
        if col.strip() in ['Bar Color'] and pd.notna(row[col]):
            excel_bar_color = parse_color_with_alpha(str(row[col]), 0)  # Default alpha 0
            if excel_bar_color:
                if debug:
                    print(f"DEBUG: Using bar color from Excel: {row[col]} -> {excel_bar_color}")
                bar_color = excel_bar_color
                break
    
    # Check for Text Outline in Excel
    for col in column_names:
        if col.strip() in ['Text Outline', 'Outline'] and pd.notna(row[col]):
            if debug:
                print(f"DEBUG: Using text outline from Excel: {row[col]}")
            text_outline = str(row[col])
            break
    
    # Check for Text Shadow in Excel
    for col in column_names:
        if col.strip() in ['Text Shadow', 'Shadow'] and pd.notna(row[col]):
            shadow_value = str(row[col]).lower().strip()
            if shadow_value in ['yes', 'true', '1', 'on']:
                if debug:
                    print(f"DEBUG: Enabling text shadow from Excel: {row[col]}")
                text_shadow = True
            break
    
    # Check for Shadow Color in Excel
    for col in column_names:
        if col.strip() in ['Shadow Color'] and pd.notna(row[col]) and text_shadow:
            excel_shadow_color = str(row[col])
            if debug:
                print(f"DEBUG: Using shadow color from Excel: {excel_shadow_color}")
            shadow_color = excel_shadow_color
            break
    
    # Set up image mode and background based on format and transparency
    if transparent:
        mode = "RGBA"
        bg_color = (*bg_color[:3], 0) if transparent else (*bg_color[:3], 255)  # Add alpha component
    else:
        mode = "RGB"
    
    # Create a new image with the specified background color
    img = Image.new(mode, (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Check if we have enough columns
    if len(column_names) < 4:
        raise ValueError("Row doesn't have enough columns. Expected at least 4 columns: "
                        "Main Text, Secondary Text, Justification, and Main Font.")
    
    # Get the core values from the row using column names
    # Assuming the first four columns are in this order
    main_text = str(row[column_names[0]]) if pd.notna(row[column_names[0]]) else ""
    secondary_text = str(row[column_names[1]]) if pd.notna(row[column_names[1]]) else ""
    justification = str(row[column_names[2]]).lower() if pd.notna(row[column_names[2]]) else "left"
    main_font_name = str(row[column_names[3]]) if pd.notna(row[column_names[3]]) else None
    
    # Apply text transformations if specified
    if text_transform != 'none':
        main_text = transform_text(main_text, text_transform)
        secondary_text = transform_text(secondary_text, text_transform)
    
    # Get optional values from named columns
    
    # Secondary Font
    secondary_font_name = None
    for col in column_names:
        if col.strip() == 'Secondary Font' and pd.notna(row[col]):
            secondary_font_name = str(row[col])
            if debug:
                print(f"DEBUG: Found Secondary Font: {secondary_font_name}")
            break
    
    # File name for output
    file_name = None
    for col in column_names:
        if col.strip() == 'File Name' and pd.notna(row[col]):
            file_name = str(row[col])
            if debug:
                print(f"DEBUG: Found File Name: {file_name}")
            break
    
    # Font sizes with exact column matching
    default_main_font_size = int(height / 18)
    default_secondary_font_size = int(height / 25)
    
    main_font_size = default_main_font_size
    secondary_font_size = default_secondary_font_size
    
    # Check for main font size
    for col in column_names:
        if col.strip() == 'Main Font Size' and pd.notna(row[col]):
            try:
                size_value = row[col]
                if debug:
                    print(f"DEBUG: Found Main Font Size: {size_value} (type: {type(size_value)})")
                
                # Handle different types of input
                if isinstance(size_value, (int, float)):
                    main_font_size = int(size_value)
                else:
                    # Try to convert string to number
                    main_font_size = int(float(str(size_value).strip()))
                
                if debug:
                    print(f"DEBUG: Using custom main font size: {main_font_size}")
            except Exception as e:
                if debug:
                    print(f"DEBUG: Error parsing Main Font Size: {e}")
            break
    
    # Check for secondary font size
    for col in column_names:
        if col.strip() == 'Secondary Font Size' and pd.notna(row[col]):
            try:
                size_value = row[col]
                if debug:
                    print(f"DEBUG: Found Secondary Font Size: {size_value} (type: {type(size_value)})")
                
                # Handle different types of input
                if isinstance(size_value, (int, float)):
                    secondary_font_size = int(size_value)
                else:
                    # Try to convert string to number
                    secondary_font_size = int(float(str(size_value).strip()))
                
                if debug:
                    print(f"DEBUG: Using custom secondary font size: {secondary_font_size}")
            except Exception as e:
                if debug:
                    print(f"DEBUG: Error parsing Secondary Font Size: {e}")
            break
    
    # Check for padding value
    default_padding = int(height * 0.02) * 2  # Default padding (same as before)
    padding = default_padding
    
    for col in column_names:
        if col.strip() == 'Padding' and pd.notna(row[col]):
            try:
                padding_value = row[col]
                if debug:
                    print(f"DEBUG: Found Padding: {padding_value} (type: {type(padding_value)})")
                
                # Handle different types of input
                if isinstance(padding_value, (int, float)):
                    padding = int(padding_value)
                else:
                    # Try to convert string to number
                    padding = int(float(str(padding_value).strip()))
                
                if debug:
                    print(f"DEBUG: Using custom padding: {padding}")
            except Exception as e:
                if debug:
                    print(f"DEBUG: Error parsing Padding: {e}")
            break
    
    # Load main font
    try:
        # Find main font file
        main_font_file = find_font_file(main_font_name)
        
        if main_font_file:
            main_font = ImageFont.truetype(main_font_file, size=main_font_size)
            if debug:
                print(f"DEBUG: Using main font: {main_font_file}")
        else:
            main_font = ImageFont.load_default()
            print(f"Warning: Main font '{main_font_name}' not found. Using default font.")
    except Exception as e:
        print(f"Warning: Main font loading issue: {e}. Using default font.")
        main_font = ImageFont.load_default()
    
    # Load secondary font (use main font if not specified)
    try:
        if secondary_font_name:
            # Find secondary font file
            secondary_font_file = find_font_file(secondary_font_name)
            
            if secondary_font_file:
                secondary_font = ImageFont.truetype(secondary_font_file, size=secondary_font_size)
                if debug:
                    print(f"DEBUG: Using secondary font: {secondary_font_file}")
            else:
                # Fall back to main font if available, otherwise default
                if main_font != ImageFont.load_default():
                    secondary_font = ImageFont.truetype(main_font_file, size=secondary_font_size)
                    print(f"Warning: Secondary font '{secondary_font_name}' not found. Using main font instead.")
                else:
                    secondary_font = ImageFont.load_default()
                    print(f"Warning: Secondary font '{secondary_font_name}' not found. Using default font.")
        else:
            # Use main font file if available
            if main_font != ImageFont.load_default():
                secondary_font = ImageFont.truetype(main_font_file, size=secondary_font_size)
            else:
                secondary_font = ImageFont.load_default()
    except Exception as e:
        print(f"Warning: Secondary font loading issue: {e}. Using default font.")
        secondary_font = ImageFont.load_default()
    
    if debug:
        print(f"DEBUG: Final main font size: {main_font_size}")
        print(f"DEBUG: Final secondary font size: {secondary_font_size}")
    
    # Set secondary text color if not specified
    if secondary_text_color is None:
        secondary_text_color = text_color
    
    # Calculate text dimensions
    main_bbox = draw.textbbox((0, 0), main_text, font=main_font)
    main_text_width = main_bbox[2] - main_bbox[0]
    main_text_height = main_bbox[3] - main_bbox[1]
    
    secondary_bbox = draw.textbbox((0, 0), secondary_text, font=secondary_font)
    secondary_text_width = secondary_bbox[2] - secondary_bbox[0]
    secondary_text_height = secondary_bbox[3] - secondary_bbox[1]
    
    # Calculate standard lower third dimensions (for traditional lower third)
    default_bar_height = height // 6  # Default height for lower third bar
    if bar_height is not None:
        bar_height_px = bar_height
    else:
        bar_height_px = default_bar_height
    
    bar_y_position = int(height * 0.75)  # Position at about 3/4 down the frame
    bar_padding = int(height * 0.02)  # Padding inside the bar
    
    # Modify bar color opacity if specified
    if bar_opacity is not None:
        if len(bar_color) == 3:
            bar_color = (*bar_color, bar_opacity)
        else:
            bar_color = (*bar_color[:3], bar_opacity)
    elif len(bar_color) == 3:
        bar_color = (*bar_color, 0)  # Add alpha if not provided - completely transparent by default
    
    # Draw lower third bar background
    draw.rectangle(
        [(0, bar_y_position), (width, bar_y_position + bar_height_px)],
        fill=bar_color
    )
    
    # Compute vertical spacing between main and secondary text
    if vertical_spacing is not None:
        vert_spacing = vertical_spacing
    else:
        vert_spacing = main_font_size // 2
    
    # Process extended justification options
    # Normalize justification value and extract position information
    justification = justification.lower().strip()
    
    # Determine horizontal and vertical positioning
    h_align = "left"  # Default horizontal alignment
    v_align = "lower"  # Default vertical alignment
    
    # Parse justification string to determine position
    if "lower left" in justification:
        h_align = "left"
        v_align = "lower"
    elif "lower right" in justification:
        h_align = "right"
        v_align = "lower"
    elif "upper left" in justification:
        h_align = "left"
        v_align = "upper"
    elif "upper right" in justification:
        h_align = "right"
        v_align = "upper"
    elif "center bottom" in justification:
        h_align = "center"
        v_align = "lower"
    elif "center top" in justification:
        h_align = "center"
        v_align = "upper"
    elif "center center" in justification:
        h_align = "center"
        v_align = "center"
    elif "left" in justification:
        h_align = "left"
        v_align = "lower"  # Default to lower for backward compatibility
    elif "right" in justification:
        h_align = "right"
        v_align = "lower"  # Default to lower for backward compatibility
    elif "center" in justification:
        h_align = "center"
        v_align = "lower"  # Default to lower for backward compatibility
    
    if debug:
        print(f"DEBUG: Parsed justification '{justification}' as horizontal: {h_align}, vertical: {v_align}")
    
    # Apply letter spacing if specified - this is not fully accurate for variable-width fonts
    # but provides a reasonable approximation
    if letter_spacing != 0:
        spaced_main_text = " ".join(main_text)
        spaced_secondary_text = " ".join(secondary_text)
        
        # Recalculate text dimensions with spacing
        main_bbox = draw.textbbox((0, 0), spaced_main_text, font=main_font)
        main_text_width = main_bbox[2] - main_bbox[0]
        
        secondary_bbox = draw.textbbox((0, 0), spaced_secondary_text, font=secondary_font)
        secondary_text_width = secondary_bbox[2] - secondary_bbox[0]
    else:
        spaced_main_text = main_text
        spaced_secondary_text = secondary_text
    
    # Calculate horizontal positioning
    if h_align == "left":
        main_x = padding
        secondary_x = padding
    elif h_align == "right":
        main_x = width - main_text_width - padding
        secondary_x = width - secondary_text_width - padding
    else:  # center
        main_x = (width - main_text_width) // 2
        secondary_x = (width - secondary_text_width) // 2
    
    # Calculate vertical positioning
    total_text_height = main_text_height + vert_spacing + secondary_text_height
    
    if v_align == "upper":
        # Place at top of frame with padding
        main_y = padding
        secondary_y = main_y + main_text_height + vert_spacing
    elif v_align == "lower":
        # Place at standard lower third position
        main_y = bar_y_position + bar_padding
        secondary_y = main_y + main_text_height + vert_spacing
    else:  # center
        # Center vertically in frame
        start_y = (height - total_text_height) // 2
        main_y = start_y
        secondary_y = main_y + main_text_height + vert_spacing
    
    # Create a text layer for applying effects
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    
    # Apply text outline if specified
    if text_outline:
        try:
            # Parse outline parameters
            outline_parts = text_outline.split(',')
            outline_width = int(outline_parts[0])
            
            # Parse the outline color (which can now be a color name)
            if len(outline_parts) >= 2:
                outline_color_spec = ','.join(outline_parts[1:])
                outline_color = parse_color_with_alpha(outline_color_spec, 255)
            else:
                outline_color = (0, 0, 0, 255)  # Default to black if not specified
                
            # Draw text outline by drawing text multiple times with small offsets
            for offset_x in range(-outline_width, outline_width + 1):
                for offset_y in range(-outline_width, outline_width + 1):
                    # Skip the center (will be drawn later)
                    if offset_x == 0 and offset_y == 0:
                        continue
                    
                    text_draw.text(
                        (main_x + offset_x, main_y + offset_y),
                        spaced_main_text,
                        font=main_font,
                        fill=outline_color
                    )
                    
                    text_draw.text(
                        (secondary_x + offset_x, secondary_y + offset_y),
                        spaced_secondary_text,
                        font=secondary_font,
                        fill=outline_color
                    )
        except Exception as e:
            print(f"Warning: Error applying text outline: {e}")
    
    # Apply text shadow if enabled
    if text_shadow:
        try:
            # Parse shadow offset
            offset_parts = shadow_offset.split(',')
            offset_x = int(offset_parts[0]) if len(offset_parts) >= 1 else 2
            offset_y = int(offset_parts[1]) if len(offset_parts) >= 2 else 2
            
            # Get blur value and convert to radius
            blur_radius = convert_blur_scale(shadow_blur)
            
            # Get shadow color and opacity
            shadow_rgb = color_name_to_rgb(shadow_color)
            shadow_color_rgba = (*shadow_rgb, shadow_opacity)
            
            # Create separate transparent image for the shadow
            shadow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_img)
            
            # Draw shadow text
            shadow_draw.text(
                (main_x + offset_x, main_y + offset_y),
                spaced_main_text,
                font=main_font,
                fill=shadow_color_rgba
            )
            
            shadow_draw.text(
                (secondary_x + offset_x, secondary_y + offset_y),
                spaced_secondary_text,
                font=secondary_font,
                fill=shadow_color_rgba
            )
            
            # Apply Gaussian blur to the shadow
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
            # Composite the shadow with the original image
            # Convert img to RGBA mode if it's not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = Image.alpha_composite(img, shadow_img)
            
            if debug:
                print(f"DEBUG: Applied shadow with color {shadow_rgb}, opacity {shadow_opacity}, blur {blur_radius}")
        except Exception as e:
            print(f"Warning: Error applying text shadow: {e}")
    
    # Draw the main text on the text layer
    text_draw.text(
        (main_x, main_y),
        spaced_main_text,
        font=main_font,
        fill=text_color
    )
    
    # Draw the secondary text on the text layer
    text_draw.text(
        (secondary_x, secondary_y),
        spaced_secondary_text,
        font=secondary_font,
        fill=secondary_text_color
    )
    
    # Composite the text layer with the original image
    # Make sure both images are in RGBA mode before alpha compositing
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    img = Image.alpha_composite(img, text_layer)
    
    # If preview only, return the image without saving
    if preview_only:
        return img
    
    # Create safe filename - use "File Name" column if available, otherwise use main text
    if file_name:
        safe_filename = file_name.replace('/', '_').replace('\\', '_')
    else:
        safe_filename = main_text.replace('/', '_').replace('\\', '_')
    
    safe_filename = ''.join(char for char in safe_filename if char.isalnum() or char in '_-.')
    
    # Prepare the output path with appropriate extension
    ext = ".tiff" if format.lower() in ["tiff", "tif"] else f".{format.lower()}"
    output_path = os.path.join(output_dir, f"{safe_filename}{ext}")
    
    # Skip if file exists and skip_existing is True
    if os.path.exists(output_path) and globals().get('skip_existing', False):
        print(f"Skipping existing file: {output_path}")
        return output_path
    
    # Handle 16-bit TIFF if specified
    if format.lower() in ["tiff", "tif"] and bit_depth == 16:
        # Convert PIL image to numpy array
        arr = np.array(img)
        # Scale from 8-bit to 16-bit range (0-255 -> 0-65535)
        arr = (arr.astype(np.uint16) * 257)
        # Save as 16-bit TIFF without compression
        try:
            from tifffile import imwrite
            imwrite(output_path, arr, photometric='rgb')
        except ImportError:
            print("Warning: tifffile module not found. Using PIL for TIFF export (8-bit only).")
            img.save(output_path)
    else:
        # For standard formats or 8-bit TIFF, use PIL's save
        img.save(output_path)
    
    return output_path
    
    return output_path
    
def show_preview(image):
    """
    Show a preview of the image using a simple approach that works on most systems.
    Saves the image to a temporary file and opens it with the default system viewer.
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    # Save the image to the temporary file
    image.save(temp_filename)
    
    # Print information
    print(f"Preview image saved to: {temp_filename}")
    print("Opening preview with system default viewer...")
    
    # Open the image with the default system viewer
    if sys.platform == 'win32':
        os.startfile(temp_filename)
    elif sys.platform == 'darwin':  # macOS
        import subprocess
        subprocess.call(['open', temp_filename])
    else:  # Linux and other Unix-like
        import subprocess
        try:
            subprocess.call(['xdg-open', temp_filename])
        except FileNotFoundError:
            print("Could not open the preview automatically.")
            print(f"Please open {temp_filename} manually to view the preview.")
    
    print("Close the preview window/application when done to continue.")
    
    # Wait for user input before proceeding
    input("Press Enter to continue...")
    
    # Try to clean up the temporary file (might fail if still open)
    try:
        os.unlink(temp_filename)
    except:
        pass

def main():
    # Setup argument parser with more helpful descriptions
    parser = argparse.ArgumentParser(
        description="Generate lower third graphics from CSV or Excel data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXCEL/CSV FORMAT:
Required columns (in this order):
1. Main Text      - The primary text (typically a name)
2. Secondary Text - The secondary text (typically a title or description)
3. Justification  - Text position: "Left", "Right", "Center", "Lower Left", "Lower Right", 
                    "Upper Left", "Upper Right", "Center Bottom", "Center Center", "Center Top"
4. Main Font      - Font name or path to font file for the main text

Optional columns:
- Secondary Font     - Font name or path for the secondary text (defaults to Main Font if not specified)
- File Name          - Custom filename for the output image
- Main Font Size     - Custom font size for the main text
- Secondary Font Size - Custom font size for the secondary text
- Padding            - Additional padding from the edge (in pixels)
- Main Color         - Color for the main text (can use color name or R,G,B)
- Secondary Color    - Color for the secondary text (can use color name or R,G,B)
- Background Color   - Background color for the image (can use color name or R,G,B)
- Bar Color          - Color for the lower third bar (can use color name or R,G,B[,A])
- Text Outline       - Outline for text (format: WIDTH,COLOR[,OPACITY])
- Text Shadow        - Enable shadow (Yes/No or True/False)
- Shadow Color       - Color for text shadow (can use color name or R,G,B)

NOTE: Colors specified in the Excel/CSV file will override command-line options for individual rows.

EXAMPLE EXCEL ROWS:
| Main Text      | Secondary Text      | Justification  | Main Font   | Main Color | Secondary Color | Background Color | Bar Color    |
|----------------|---------------------|----------------|-------------|------------|-----------------|------------------|--------------|
| John Smith     | Director            | Lower Left     | Arial       | white      | lightgray       | black            | navy,128     |
| Jane Doe       | Executive Producer  | Center Bottom  | Helvetica   | #FFFFFF    | #CCCCCC         | #000000          | darkblue,150 |
| Robert Johnson | VFX Supervisor      | Upper Right    | Arial Bold  | 255,255,255| 200,200,200     | 0,0,0            | red,100      |
        """
    )
    
    parser.add_argument("input_file", help="Path to CSV or Excel file")
    parser.add_argument("output_dir", help="Directory to save generated images")
    parser.add_argument("--width", type=int, default=1920, help="Image width (default: 1920)")
    parser.add_argument("--height", type=int, default=1080, help="Image height (default: 1080)")
    parser.add_argument("--bg-color", default="black", help="Background color (default: black) - Can use color name or R,G,B")
    parser.add_argument("--text-color", default="white", help="Text color (default: white) - Can use color name or R,G,B")
    parser.add_argument("--secondary-text-color", default=None, help="Secondary text color (default: same as text-color)")
    parser.add_argument("--bar-color", default="black,0", 
                      help="Lower third bar color (default: black,0) - Can use color name or R,G,B,A")
    parser.add_argument("--format", default="png", choices=["png", "jpg", "tiff"], 
                      help="Output format (default: png)")
    parser.add_argument("--bit-depth", type=int, default=16, choices=[8, 16],
                      help="Bit depth for TIFF images (default: 16)")
    parser.add_argument("--transparent", action="store_true", 
                      help="Use transparent background (for PNG and TIFF)")
    parser.add_argument("--text-shadow", action="store_true",
                      help="Enable text shadow effect")
    parser.add_argument("--shadow-offset", default="2,2",
                      help="Shadow offset as X,Y (default: 2,2)")
    parser.add_argument("--shadow-blur", type=int, default=20,
                      help="Shadow blur amount from 1-100 (default: 20)")
    parser.add_argument("--shadow-color", default="black",
                      help="Shadow color name or R,G,B (default: black)")
    parser.add_argument("--shadow-opacity", type=int, default=128,
                      help="Shadow opacity from 0-255 (default: 128)")
    parser.add_argument("--text-outline", default=None,
                      help="Add outline to text: WIDTH,COLOR[,OPACITY] (e.g. 2,black or 2,red,128)")
    parser.add_argument("--letter-spacing", type=int, default=0,
                      help="Adjust spacing between characters (in pixels)")
    parser.add_argument("--vertical-spacing", type=int, default=None,
                      help="Space between main and secondary text (in pixels)")
    parser.add_argument("--text-transform", default="none", choices=["none", "upper", "lower", "title"],
                      help="Transform text case (default: none)")
    parser.add_argument("--bar-height", type=int, default=None,
                      help="Custom height for the lower third bar (in pixels)")
    parser.add_argument("--bar-opacity", type=int, default=None,
                      help="Set bar transparency (0-255)")
    parser.add_argument("--skip-existing", action="store_true",
                      help="Skip generation if output file already exists")
    parser.add_argument("--test", action="store_true",
                      help="Preview only the first image to check settings")
    parser.add_argument("--debug", action="store_true",
                      help="Show additional debug information")
    
    args = parser.parse_args()
    
    # Store skip_existing as a global for access in the generate function
    globals()['skip_existing'] = args.skip_existing
    
    # Parse colors - now using color_name_to_rgb function for all color values
    try:
        # Parse background color - can be a color name or RGB values
        bg_color = color_name_to_rgb(args.bg_color)
        if not bg_color:
            bg_color = (0, 0, 0)  # Default to black if parsing fails
            
        # Parse main text color - can be a color name or RGB values
        text_color = color_name_to_rgb(args.text_color)
        if not text_color:
            text_color = (255, 255, 255)  # Default to white if parsing fails
        
        # Parse secondary text color if provided
        secondary_text_color = None
        if args.secondary_text_color:
            secondary_text_color = color_name_to_rgb(args.secondary_text_color)
        
        # Parse bar color with potential alpha
        bar_color = parse_color_with_alpha(args.bar_color, 0)  # Default alpha is 0 (transparent)
        if not bar_color:
            bar_color = (0, 0, 0, 0)  # Default to transparent black
    except Exception as e:
        print(f"Error parsing colors: {e}")
        print("Using default colors instead.")
        bg_color = (0, 0, 0)
        text_color = (255, 255, 255)
        secondary_text_color = None
        bar_color = (0, 0, 0, 0)
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)
    
    # Check dependencies for 16-bit TIFF
    if args.format.lower() in ["tiff", "tif"] and args.bit_depth == 16:
        try:
            import tifffile
        except ImportError:
            print("Warning: The tifffile package is required for 16-bit TIFF support.")
            print("8-bit TIFF will be used instead. To enable 16-bit support:")
            print("pip install tifffile numpy")
    
    # Create output directory if it doesn't exist and we're not in test mode
    if not args.test:
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"Output directory: {os.path.abspath(args.output_dir)}")
    
    # Load data
    try:
        data = load_data(args.input_file)
        print(f"Loaded {len(data)} rows from {args.input_file}")
        
        # Show column names in debug mode
        if args.debug:
            print(f"DEBUG: Columns found in the file: {list(data.columns)}")
        
        # Verify the data has the required columns
        if len(data.columns) < 3:
            print("Error: Input file must have at least 3 columns (Main Text, Secondary Text, Justification)")
            print(f"Found columns: {', '.join(data.columns)}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)
    
    # Test mode - only preview the first image
    if args.test:
        print("Test mode: Previewing first image only")
        try:
            # Generate the first image but don't save it
            first_row = data.iloc[0]
            
            # Parse shadow color for test mode
            shadow_color_rgb = color_name_to_rgb(args.shadow_color)
            shadow_color_rgba = (*shadow_color_rgb, args.shadow_opacity) if shadow_color_rgb else (0, 0, 0, args.shadow_opacity)
            
            # Parse text outline for test mode
            outline_color = None
            if args.text_outline:
                try:
                    outline_parts = args.text_outline.split(',')
                    outline_width = int(outline_parts[0])
                    outline_color_spec = ','.join(outline_parts[1:])
                    outline_color = parse_color_with_alpha(outline_color_spec, 255)
                except Exception as e:
                    if args.debug:
                        print(f"DEBUG: Error parsing outline specification: {e}")
            
            img = generate_lower_third(
                first_row,
                width=args.width,
                height=args.height,
                bg_color=bg_color,
                text_color=text_color,
                secondary_text_color=secondary_text_color,
                bar_color=bar_color,
                bar_height=args.bar_height,
                bar_opacity=args.bar_opacity,
                format=args.format,
                bit_depth=args.bit_depth,
                transparent=args.transparent,
                text_shadow=args.text_shadow,
                shadow_offset=args.shadow_offset,
                shadow_blur=args.shadow_blur,
                shadow_color=args.shadow_color,
                shadow_opacity=args.shadow_opacity,
                text_outline=args.text_outline,
                letter_spacing=args.letter_spacing,
                vertical_spacing=args.vertical_spacing,
                text_transform=args.text_transform,
                preview_only=True,
                debug=args.debug
            )
            
            # Show settings used for preview
            print("\nSettings used for preview:")
            print(f"  - Dimensions: {args.width}x{args.height}")
            print(f"  - Background: {args.bg_color} {bg_color}")
            print(f"  - Text color: {args.text_color} {text_color}")
            if secondary_text_color:
                print(f"  - Secondary text color: {args.secondary_text_color} {secondary_text_color}")
            print(f"  - Bar color: {args.bar_color} {bar_color}")
            if args.bar_height:
                print(f"  - Bar height: {args.bar_height} pixels")
            if args.bar_opacity is not None:
                print(f"  - Bar opacity: {args.bar_opacity}")
            if args.transparent:
                print("  - Transparent background: Yes")
            if args.text_shadow:
                print(f"  - Text shadow: Enabled")
                print(f"    - Shadow offset: {args.shadow_offset}")
                print(f"    - Shadow blur: {args.shadow_blur}")
                print(f"    - Shadow color: {args.shadow_color} {shadow_color_rgb}")
                print(f"    - Shadow opacity: {args.shadow_opacity}")
            if args.text_outline:
                print(f"  - Text outline: {args.text_outline}")
                if outline_color:
                    print(f"    - Parsed outline color: {outline_color}")
            if args.letter_spacing:
                print(f"  - Letter spacing: {args.letter_spacing} pixels")
            if args.vertical_spacing:
                print(f"  - Vertical spacing: {args.vertical_spacing} pixels")
            if args.text_transform != "none":
                print(f"  - Text transform: {args.text_transform}")
            print(f"  - Output format: {args.format}")
            if args.format.lower() in ["tiff", "tif"]:
                print(f"  - Bit depth: {args.bit_depth}-bit")
            
            # Show the preview
            show_preview(img)
            print("Preview complete. Run without --test to generate all images.")
            sys.exit(0)
        except Exception as e:
            print(f"Error generating preview: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Normal mode - generate all images
    count = 0
    for i, row in data.iterrows():
        try:
            output_path = generate_lower_third(
                row, 
                args.output_dir,
                width=args.width,
                height=args.height,
                bg_color=bg_color,
                text_color=text_color,
                secondary_text_color=secondary_text_color,
                bar_color=bar_color,
                bar_height=args.bar_height,
                bar_opacity=args.bar_opacity,
                format=args.format,
                bit_depth=args.bit_depth,
                transparent=args.transparent,
                text_shadow=args.text_shadow,
                shadow_offset=args.shadow_offset,
                shadow_blur=args.shadow_blur,
                shadow_color=args.shadow_color,
                shadow_opacity=args.shadow_opacity,
                text_outline=args.text_outline,
                letter_spacing=args.letter_spacing,
                vertical_spacing=args.vertical_spacing,
                text_transform=args.text_transform,
                debug=args.debug
            )
            count += 1
            print(f"Generated: {output_path}")
        except Exception as e:
            print(f"Error generating lower third for row {i}: {e}")
    
    print(f"Completed: {count} lower thirds generated in {args.output_dir}")
    if count < len(data):
        print(f"Warning: {len(data) - count} images failed to generate")

if __name__ == "__main__":
    # Print banner
    print("=" * 80)
    print("Lower Thirds Generator".center(80))
    print("=" * 80)
    
    try:
        main()
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)