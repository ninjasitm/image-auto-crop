# svg-auto-crop

Scripts to automatically crop whitespace around SVG files. Useful for files downloaded from AI image generators.

## Installation

This script requires Python 3 and uses only standard library modules as base dependencies. Optional dependencies include:

- **`cairosvg`**: For rasterization to PNG format (install via `pip install cairosvg`)

## Usage

### Basic Usage

To analyze an SVG file and see the suggested crop dimensions (dry-run mode):

```bash
python3 svg_auto_crop.py path/to/file.svg
```

To actually crop the SVG file in-place:

```bash
python3 svg_auto_crop.py --apply path/to/file.svg
```

### Command-Line Options

- **`paths`** (required): One or more SVG files, directories, or glob patterns to process
- **`--margin MARGIN`** or **`-m MARGIN`**: Margin (in pixels) to add around the bounding box (default: 8)
- **`--apply`** or **`-a`**: Apply cropping to files and write changes to disk (without this flag the script runs in dry-run mode)
- **`--no-backup`**: Do not create a `.bak` backup file when applying changes (default: creates backup)
- **`--backup-overwrite`**: When creating `.bak` backups, overwrite an existing `.bak` if present (default)
- **`--backup-no-overwrite`**: Do not overwrite an existing `.bak` backup; if it exists, skip creating a new backup
- **`--verify`** or **`-v`**: Verify that artwork bbox fits inside viewBox (after apply if using `--apply`). If verification fails and `--revert-on-fail` was passed, the original `.bak` will be restored
- **`--revert-on-fail`**: If `--apply` and `--verify` are used and verification fails, revert the change by restoring the `.bak` backup
- **`--responsive`**: Set SVG root to responsive mode according to `--responsive-mode` when applying
- **`--responsive-mode`**: Choose responsive behavior: `'percent'` sets width/height='100%' (default); `'remove'` deletes width/height attributes
- **`--svg-class`**: Add a CSS class attribute to the SVG root when applying (space-separated classes allowed)
- **`--rasterize`**: Rasterize SVGs to PNGs using cairosvg (requires cairosvg to be installed)
- **`--raster-dpi`**: Optional DPI to use for rasterization (default depends on cairosvg)
- **`--raster-outdir`**: Optional directory to write PNGs into (default: same folder as SVG)

### Examples

**Analyze a single SVG file (dry-run):**

```bash
python3 svg_auto_crop.py image.svg
```

**Crop a single SVG file with default margin (8px) and create a backup:**

```bash
python3 svg_auto_crop.py --apply image.svg
```

**Crop with a custom margin (20px):**

```bash
python3 svg_auto_crop.py --apply --margin 20 image.svg
```

**Process multiple SVG files:**

```bash
python3 svg_auto_crop.py --apply file1.svg file2.svg file3.svg
```

**Process all SVG files in a directory:**

```bash
python3 svg_auto_crop.py --apply path/to/directory/
```

**Process SVG files using glob patterns:**

```bash
python3 svg_auto_crop.py --apply "*.svg"
python3 svg_auto_crop.py --apply "images/**/*.svg"
```

**Crop without creating backup files:**

```bash
python3 svg_auto_crop.py --apply --no-backup image.svg
```

**Apply crop with responsive mode (width/height set to 100%):**

```bash
python3 svg_auto_crop.py --apply --responsive image.svg
```

**Apply crop with responsive mode (width/height attributes removed):**

```bash
python3 svg_auto_crop.py --apply --responsive --responsive-mode remove image.svg
```

**Apply crop, add a CSS class, and verify:**

```bash
python3 svg_auto_crop.py --apply --svg-class "icon icon-large" --verify image.svg
```

**Apply crop, verify, and revert on failure:**

```bash
python3 svg_auto_crop.py --apply --verify --revert-on-fail image.svg
```

**Rasterize SVGs to PNG after cropping (requires cairosvg):**

```bash
python3 svg_auto_crop.py --apply --rasterize image.svg
```

**Rasterize to a specific directory with custom DPI:**

```bash
python3 svg_auto_crop.py --apply --rasterize --raster-dpi 300 --raster-outdir ./png-output/ image.svg
```

## How It Works

The script analyzes SVG files to compute the tight bounding box around all visible elements, ignoring background elements and transparent rectangles. It then:

1. Parses SVG transform attributes (matrix, translate) and applies them to calculate actual positions
2. Calculates the minimum and maximum x,y coordinates of all path points, circles, and rectangles
3. Adds a configurable margin around the bounding box
4. Updates the SVG's `viewBox`, `width`, and `height` attributes to crop to the calculated bounds
5. Optionally removes large background rectangles or groups with `id="background-logo"`
6. Optionally sets responsive width/height attributes or removes them entirely
7. Optionally adds CSS classes to the SVG root
8. Optionally verifies the result and reverts on failure
9. Optionally rasterizes the result to PNG

## Features

- **Smart background detection**: Ignores transparent rectangles and large background elements
- **Transform support**: Properly handles SVG transform attributes (matrix, translate)
- **Backup creation**: Creates `.bak` backup files by default before modifying originals
- **Backup control**: Choose to overwrite or preserve existing `.bak` files
- **Verification**: Verify that artwork bounding box fits within the computed viewBox
- **Revert on failure**: Automatically restore from backup if verification fails
- **Responsive SVGs**: Set responsive width/height attributes or remove them entirely
- **CSS class support**: Add CSS classes to SVG root elements
- **Rasterization**: Convert SVGs to PNGs with optional DPI control
- **Batch processing**: Process multiple files, directories, or glob patterns in one command
- **Dry-run mode**: Preview changes before applying them (default behavior)

## License

See [LICENSE](LICENSE) file for details.
