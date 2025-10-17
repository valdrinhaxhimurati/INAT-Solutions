#!/usr/bin/env python3
"""
Generate installer assets (BMP files) from the logo with proper branding.

This script creates:
- wizard-large.bmp (493x312): Large wizard image with gradient background
- wizard-small.bmp (55x55): Small wizard image with logo
- header.bmp (160x32): Header logo on transparent/white background

The brand color #26A69A is used as the primary color.
"""

from PIL import Image, ImageDraw
import os

# Brand colors from INAT-Solutions.iss
BRAND_PRIMARY = "#26A69A"  # Teal/turquoise color
BRAND_SECONDARY = "#1E8E85"  # Darker shade for gradient

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_gradient_background(width, height, color_top, color_bottom):
    """Create a vertical gradient background."""
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    r1, g1, b1 = color_top
    r2, g2, b2 = color_bottom
    
    for y in range(height):
        # Calculate interpolation factor
        factor = y / height
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return image

def create_wizard_large(logo_path, output_path):
    """Create wizard-large.bmp (493x312) with gradient background and logo."""
    width, height = 493, 312
    
    # Create gradient background
    color_top = hex_to_rgb(BRAND_PRIMARY)
    color_bottom = hex_to_rgb(BRAND_SECONDARY)
    background = create_gradient_background(width, height, color_top, color_bottom)
    
    # Load and resize logo
    logo = Image.open(logo_path).convert('RGBA')
    
    # Calculate logo size to fit nicely (about 70% of the width)
    logo_width = int(width * 0.7)
    aspect_ratio = logo.size[1] / logo.size[0]
    logo_height = int(logo_width * aspect_ratio)
    
    # Resize logo
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    
    # Calculate position (centered)
    x = (width - logo_width) // 2
    y = (height - logo_height) // 2
    
    # Composite logo onto background
    background.paste(logo, (x, y), logo)
    
    # Convert to RGB and save as BMP
    background = background.convert('RGB')
    background.save(output_path, 'BMP')
    print(f"Created {output_path}")

def create_wizard_small(logo_path, output_path):
    """Create wizard-small.bmp (55x55) with logo on brand color background."""
    size = 55
    
    # Create solid background with brand color
    background = Image.new('RGB', (size, size), hex_to_rgb(BRAND_PRIMARY))
    
    # Load logo
    logo = Image.open(logo_path).convert('RGBA')
    
    # Resize logo to fit (about 80% of the size)
    logo_size = int(size * 0.8)
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
    
    # Calculate position (centered)
    offset = (size - logo_size) // 2
    
    # Composite logo onto background
    background.paste(logo, (offset, offset), logo)
    
    # Convert to RGB and save as BMP
    background = background.convert('RGB')
    background.save(output_path, 'BMP')
    print(f"Created {output_path}")

def create_header(logo_path, output_path):
    """Create header.bmp (160x32) with logo on white background."""
    width, height = 160, 32
    
    # Create white background
    background = Image.new('RGB', (width, height), (255, 255, 255))
    
    # Load logo
    logo = Image.open(logo_path).convert('RGBA')
    
    # Resize logo to fit height (with some padding)
    logo_height = height - 4  # 2px padding top and bottom
    aspect_ratio = logo.size[0] / logo.size[1]
    logo_width = int(logo_height * aspect_ratio)
    
    # Make sure width fits
    if logo_width > width - 8:
        logo_width = width - 8
        logo_height = int(logo_width / aspect_ratio)
    
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    
    # Calculate position (left-aligned with padding)
    x = 4
    y = (height - logo_height) // 2
    
    # Composite logo onto background
    background.paste(logo, (x, y), logo)
    
    # Convert to RGB and save as BMP
    background = background.convert('RGB')
    background.save(output_path, 'BMP')
    print(f"Created {output_path}")

def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, 'assets')
    
    # Logo path (one level up from installer directory)
    logo_path = os.path.join(script_dir, '..', 'INAT SOLUTIONS.png')
    
    if not os.path.exists(logo_path):
        print(f"Error: Logo not found at {logo_path}")
        return 1
    
    # Create assets directory if it doesn't exist
    os.makedirs(assets_dir, exist_ok=True)
    
    # Generate all assets
    create_wizard_large(logo_path, os.path.join(assets_dir, 'wizard-large.bmp'))
    create_wizard_small(logo_path, os.path.join(assets_dir, 'wizard-small.bmp'))
    create_header(logo_path, os.path.join(assets_dir, 'header.bmp'))
    
    print("\nAll installer assets generated successfully!")
    return 0

if __name__ == '__main__':
    exit(main())
