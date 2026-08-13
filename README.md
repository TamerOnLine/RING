# Rimg

Rimg is a professional batch image tool for resizing, masking, and compressing images from a clean Streamlit web interface.

## Features

- Batch upload for JPG, PNG, WebP, and BMP images
- Resize by pixels or centimeters with DPI conversion
- Aspect-ratio resize modes: fit, fill crop, or stretch
- Built-in presets for common web, avatar, social, and print export tasks
- Restore the last successful settings during the current session
- Optional circle or ellipse mask with transparency
- JPEG/WebP quality search to target a maximum file size
- Clear warnings when the requested target size cannot be reached
- Filename range selection such as `5`, `2-6`, `-4`, `7-`, `1,3,6-9`
- Live preview for the first selected images before running the full batch
- Live processing progress with processed/failed counters during batch execution
- Safety warnings for unusually large batches before processing starts
- Incremental ZIP packaging during processing to reduce peak memory pressure
- Included `rimg-report.txt` summary inside each ZIP download
- Download all processed images as one ZIP file

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
make dev
```

Open `http://localhost:8501`.

## CLI

```bash
rimg --help
rimg web
rimg serve
rimg --host 127.0.0.1 --port 8600
```

The default host and port can also be configured with `RIMG_HOST` and `RIMG_PORT`.
The target max-size option is available for `JPEG` and `WEBP` outputs.

## Development

```bash
make install
make dev
make check
```

Equivalent script wrappers are available in `scripts/`:

```bash
bash scripts/install.sh
bash scripts/dev.sh
bash scripts/test.sh
bash scripts/lint.sh
bash scripts/format.sh
```

## Project Layout

```text
src/rimg/
  cli.py        Command line entry point
  config.py     Defaults and environment configuration
  core.py       Image processing logic
  logging.py    Logging configuration
  models.py     Shared data structures
  ranges.py     Filename range parser
  utils.py      Shared helpers
  web.py        Streamlit application
  features/     Isolated future feature modules
docs/
  architecture.md
scripts/
  dev.sh
  format.sh
  install.sh
  lint.sh
  release.sh
  test.sh
tests/
  test_cli.py
  test_config.py
  test_core.py
  test_ranges.py
```
