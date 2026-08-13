# Rimg Examples

## Quick Run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
make dev
```

Open `http://localhost:8501`.

## Example Workflow

1. Upload a batch of `JPG`, `PNG`, `WEBP`, or `BMP` files.
2. Choose the resize unit:
   `px` for direct pixel dimensions, or `cm` with a DPI value for print workflows.
3. Optionally set a `circle` or `ellipse` mask.
4. Start from a preset like `Web Compressed`, `Avatar Circle`, or `Print 10x15 cm`.
5. Fine-tune the output format or size rules if needed.
6. Review the live preview for the first selected images.
7. Restore the last successful settings if you want to repeat the same workflow.
8. Enable `Target max size` only when exporting `JPEG` or `WEBP`.
9. Filter the queue with a range like `1,3,6-9,12-`.
10. Review any large-batch warning and confirm before starting if needed.
11. Process the files, follow the live progress, and download one ZIP archive.

## Example Ranges

- `5`: select item number 5
- `2-6`: select items 2 through 6
- `-4`: select items 1 through 4
- `7-`: select item 7 through the last indexed file
- `1,3,6-9`: combine individual items and ranges

## Environment Overrides

```bash
RIMG_HOST=0.0.0.0 RIMG_PORT=8600 make dev
```

This starts the Streamlit app on a custom host and port.
