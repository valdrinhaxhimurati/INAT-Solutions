# Installer Assets

This directory contains the assets used by the Inno Setup installer.

## Files

- `wizard-large.bmp` (493x312): Large image displayed on the left side of the installer wizard
- `wizard-small.bmp` (55x55): Small icon displayed in the installer window title bar
- `header.bmp` (160x32): Header logo displayed in a custom top panel

## Regenerating Assets

The BMP assets are generated from the main logo file (`INAT SOLUTIONS.png`) using the `generate_assets.py` script.

To regenerate the assets:

```bash
cd installer
python3 generate_assets.py
```

The script uses the brand colors defined in `INAT-Solutions.iss`:
- Primary color: `#26A69A` (teal/turquoise)
- Secondary color: `#1E8E85` (darker shade for gradients)

## Design Details

- **wizard-large.bmp**: Features a gradient background from the primary to secondary brand color with the logo centered
- **wizard-small.bmp**: Shows the logo on a solid brand color background
- **header.bmp**: Displays the logo on a white background for the custom header panel

All images are in BMP format as required by Inno Setup. The logo transparency is properly handled by compositing it onto colored backgrounds.
