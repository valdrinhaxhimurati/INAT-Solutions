# Installer Asset Improvements

## Problem
The installer assets (BMP files) were appearing mostly white and the logo was not aesthetically pleasing. The issue was caused by converting the PNG logo (which has a transparent background) directly to BMP format, which doesn't support transparency. This resulted in white backgrounds where transparency should have been.

## Solution
Created a Python script (`installer/generate_assets.py`) that properly generates installer assets from the logo with the brand colors defined in the Inno Setup configuration:

- **Primary Color**: `#26A69A` (teal/turquoise)
- **Secondary Color**: `#1E8E85` (darker shade for gradients)

## Changes Made

### 1. wizard-large.bmp (493x312)
- **Before**: Mostly white (93.4% white pixels) with barely visible logo
- **After**: Beautiful gradient background from brand primary to secondary color with centered logo
- **Result**: 0% white pixels, 55.6% brand color pixels

### 2. wizard-small.bmp (55x55)
- **Before**: Mostly white (81.6% white pixels) with small logo
- **After**: Logo on solid brand color background
- **Result**: 0% white pixels, 94.9% brand color pixels

### 3. header.bmp (160x32)
- **Before**: Mostly white (95.3% white pixels)
- **After**: Logo on white background (intentional for header panel)
- **Result**: Properly composited logo with no transparency issues

## How to Regenerate Assets

If the logo changes or you need to adjust the assets:

```bash
cd installer
python3 generate_assets.py
```

The script requires Python 3 with Pillow (PIL) installed:
```bash
pip install Pillow
```

## Technical Details

The script handles the PNG transparency properly by:
1. Loading the logo with alpha channel (RGBA mode)
2. Creating backgrounds with brand colors
3. Compositing the logo onto the backgrounds using the alpha channel
4. Converting to RGB mode before saving as BMP

This ensures the logo looks professional and matches the application's branding.

## Verification

You can verify the generated assets using:

```bash
cd installer/assets
file *.bmp  # Check file formats
```

The BMP files should be:
- Windows 3.x format bitmaps
- 24-bit RGB color (no alpha channel)
- Correct dimensions (493x312, 55x55, 160x32)

## Integration with Inno Setup

The assets are referenced in `INAT-Solutions.iss`:

```ini
WizardImageFile={#MyAssetsDir}\wizard-large.bmp
WizardSmallImageFile={#MyAssetsDir}\wizard-small.bmp
```

And the header logo is extracted and displayed in the custom branding code:

```pascal
ExtractTemporaryFile('header.bmp');
TopLogo.Bitmap.LoadFromFile(ExpandConstant('{tmp}\header.bmp'));
```

No changes to the Inno Setup script were needed - the improved assets work with the existing configuration.
