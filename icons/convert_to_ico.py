#!/usr/bin/env python3
"""
Script to convert PNG/JPG images to proper ICO format for Windows applications.
This script creates multi-size icons which are required for proper display
at different resolutions (taskbar, desktop, file explorer, etc.)
Supports transparency preservation for PNG files with alpha channels.
"""

import os
import sys
from PIL import Image


def convert_image_to_ico(input_path, output_path=None):
    """
    Convert an image to ICO format with multiple sizes, preserving transparency.
    
    Args:
        input_path (str): Path to the input image file
        output_path (str, optional): Path for the output ICO file. 
                                    If not provided, uses same name as input with .ico extension.
    
    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_path):
            print(f"Error: Input file '{input_path}' not found.")
            return False
            
        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(input_path)[0]
            output_path = base_name + '.ico'
        
        # Open the image
        print(f"Opening image: {input_path}")
        img = Image.open(input_path)
        
        # Handle different image modes to preserve transparency
        if img.mode == 'P':
            # Convert palette images to RGBA to preserve transparency
            img = img.convert('RGBA')
        elif img.mode == 'LA':
            # Convert grayscale with alpha to RGBA
            img = img.convert('RGBA')
        elif img.mode == 'RGB' or img.mode == 'L':
            # For RGB or grayscale images, convert to RGB (no transparency)
            if img.mode == 'L':
                img = img.convert('RGB')
        # For RGBA images, keep as is to preserve transparency
        
        # Define standard icon sizes
        icon_sizes = [
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256)
        ]
        
        # Print image mode for debugging
        print(f"Image mode: {img.mode}")
        if img.mode == 'RGBA':
            print("Transparency will be preserved in the ICO file")
        
        # Save as ICO with multiple sizes
        print("Creating multi-size icon with sizes:", [f"{s[0]}x{s[1]}" for s in icon_sizes])
        
        img.save(
            output_path,
            format='ICO',
            sizes=icon_sizes
        )
        
        print(f"Successfully converted '{input_path}' to '{output_path}'")
        return True
        
    except Exception as e:
        print(f"Error converting image: {e}")
        return False


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python convert_to_ico.py <input_image_file> [output_ico_file]")
        print("Example: python convert_to_ico.py my_image.png app_icon.ico")
        print("Supports PNG, JPG, JPEG, and other common image formats")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = convert_image_to_ico(input_file, output_file)
    if success:
        print("Conversion completed successfully!")
    else:
        print("Conversion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()