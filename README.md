# Picture Sort

A Python tool that automatically renames JPG image files based on their EXIF metadata creation date. The script adds a timestamp prefix to filenames in the format `YYYY-MM-DD-HH-MM-SS_originalfilename.jpg`, making it easier to organize and sort photos chronologically.

## Features

- Extracts creation date from EXIF metadata (`datetime_original` field)
- Automatically renames JPG files with date prefix
- Skips files that are already properly named (detects existing date prefixes)
- Preserves original filenames by appending them after the date prefix
- Only processes JPG files (case-insensitive)

## Requirements

- Python 3.12 or higher
- Dependencies:
  - `exif>=1.6.1` - For reading EXIF metadata
  - `pillow>=12.1.0` - Image processing library

## Installation

1. Install dependencies using `uv` (or your preferred package manager):
   ```bash
   uv sync
   ```

## Usage

Run the script from the command line with the `-p` or `--path` argument:

```bash
python main.py -p /path/to/your/photos
```

### Example

```bash
python main.py -p ~/Documents/photos
```

This will:
1. Scan all files in the specified directory
2. Extract EXIF creation dates from JPG files
3. Rename files that don't already have a date prefix
4. Format: `2024-01-15-14-30-45_originalname.jpg`

## How It Works

1. **File Detection**: Scans the specified directory for all files
2. **EXIF Extraction**: For each JPG file, reads the `datetime_original` field from EXIF metadata
3. **Naming Check**: Determines if a file already has a date prefix (24-digit format check)
4. **Renaming**: Renames files that need updating with the format: `YYYY-MM-DD-HH-MM-SS_originalfilename.extension`

## Notes

- Files without EXIF metadata or missing `datetime_original` field will be skipped
- Only JPG files are processed (case-insensitive)
- Files that already have a date prefix (detected by checking if the first part of the filename is 24 digits) are skipped
- The script performs in-place renaming - make sure to backup your files if needed
