# image-auto-crop
Scripts to automatically crop whitespace around SVG files. Useful for files downloaded from AI image generators.

## Installation

This script requires Python 3 and uses only standard library modules (no external dependencies).

## Usage

### Basic Usage

To analyze an SVG file and see the suggested crop dimensions (dry-run mode):

```bash
python3 svg_auto_crop.py path/to/file.svg
```

To actually crop the SVG file in-place:

```bash
python3 svg_auto_crop.py --apply --inplace path/to/file.svg
```

### Command-Line Options

- **`paths`** (required): One or more SVG files, directories, or glob patterns to process
- **`--margin MARGIN`** or **`-m MARGIN`**: Margin (in pixels) to add around the bounding box (default: 8)
- **`--apply`** or **`-a`**: Apply cropping to files (overwrite mode)
- **`--inplace`**: Modify files in-place (must be used with `--apply`)
- **`--no-backup`**: Do not create a `.bak` backup file when applying changes (default: creates backup)
- **`--dry-run`**: Only show suggestions without modifying files (default behavior)

### Examples

**Analyze a single SVG file:**
```bash
python3 svg_auto_crop.py image.svg
```

**Crop a single SVG file with default margin (8px) and create a backup:**
```bash
python3 svg_auto_crop.py --apply --inplace image.svg
```

**Crop with a custom margin (20px):**
```bash
python3 svg_auto_crop.py --apply --inplace --margin 20 image.svg
```

**Process multiple SVG files:**
```bash
python3 svg_auto_crop.py --apply --inplace file1.svg file2.svg file3.svg
```

**Process all SVG files in a directory:**
```bash
python3 svg_auto_crop.py --apply --inplace path/to/directory/
```

**Process SVG files using glob patterns:**
```bash
python3 svg_auto_crop.py --apply --inplace "*.svg"
python3 svg_auto_crop.py --apply --inplace "images/**/*.svg"
```

**Crop without creating backup files:**
```bash
python3 svg_auto_crop.py --apply --inplace --no-backup image.svg
```

## How It Works

The script analyzes SVG files to compute the tight bounding box around all visible elements, ignoring background elements and transparent rectangles. It then:

1. Calculates the minimum and maximum x,y coordinates of all path points, circles, and rectangles
2. Adds a configurable margin around the bounding box
3. Updates the SVG's `viewBox`, `width`, and `height` attributes to crop to the calculated bounds
4. Optionally removes large background rectangles or groups with `id="background-logo"`

## Features

- **Smart background detection**: Ignores transparent rectangles and large background elements
- **Transform support**: Properly handles SVG transform attributes (matrix, translate)
- **Backup creation**: Creates `.bak` backup files by default before modifying originals
- **Batch processing**: Process multiple files, directories, or glob patterns in one command
- **Dry-run mode**: Preview changes before applying them

## License

See [LICENSE](LICENSE) file for details.
