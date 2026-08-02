# ImgGone

A simple GUI tool for finding and deleting corrupted image files on Linux/KDE.

## What it does

Scans a folder for image files and tries to decode each one. Any image that fails to open — corrupted, empty, or a broken symlink — gets listed so you can delete it.

**Detected error types:**
- `Corrupted image: failed to decode` — file exists but can't be read as an image
- `Empty file (0 bytes)` — zero-byte image file
- `Broken symlink` — image link pointing to a missing file
- `Permission denied` / `I/O Error` — OS-level read failures

**Supported formats:** PNG, JPG/JPEG, GIF, BMP, WebP, TIFF, ICO, PBM, PGM, PPM

## Requirements

- Python 3.10+
- PyQt6

```bash
pip install PyQt6
```

## Usage

```bash
python3 main.py
```

1. Click **Browse…** and select a folder
2. Check **Include subfolders** to scan recursively
3. Click **Scan**
4. Select the corrupted images in the list
5. Click **Delete Selected** and confirm
