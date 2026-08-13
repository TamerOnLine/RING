# Rimg Architecture

Rimg follows the `src/` package layout described in `PROJECT_STRUCTURE_GUIDE.md`.

## Runtime Flow

1. `rimg.cli` loads host and port from `rimg.config`.
2. The CLI launches `streamlit run src/rimg/web.py`.
3. `rimg.web` collects UI options, filters the upload queue, and delegates image work.
4. `rimg.core` resizes, masks, compresses, and packages the processed images.
5. `rimg.utils` provides filename and MIME helpers used by the processing layer.

## Module Responsibilities

- `rimg.cli`: command-line entry point and Streamlit process launch.
- `rimg.web`: Streamlit interface, preset application, preview rendering, session restore, upload selection, and user-facing validation.
- `rimg.core`: image transformation pipeline and ZIP archive generation, including incremental archive writing.
- `rimg.ranges`: range parsing plus stable selection by filename order or extracted number.
- `rimg.config`: environment-backed defaults and supported format constants.
- `rimg.models`: shared immutable data models.
- `rimg.utils`: filename normalization, MIME lookups, and duplicate-name handling.
- `rimg.logging`: logging setup for CLI execution.
- `rimg.features`: reserved namespace for future isolated feature modules.

## Processing Pipeline

For each selected upload, the core layer applies the following steps:

1. Open the image from memory and normalize orientation via EXIF transpose.
2. Convert to `RGBA` so masking and alpha handling stay consistent.
3. Calculate the target size from pixels or centimeter-to-pixel conversion with DPI.
4. Resize using `fit`, `fill_crop`, or `stretch` mode.
5. Apply an optional `circle` or `ellipse` alpha mask.
6. Encode to the requested output format.
7. When `max_kb` is enabled, search for a quality setting for `JPEG` or `WEBP`.
8. Attach a warning if even the lowest quality cannot reach the requested target size.
9. Build a ZIP archive with collision-safe output names such as `image.png`, `image_2.png`, `image_3.png`.
10. Add `rimg-report.txt` with processed, failed, and warning details.
11. Use a spooled temporary archive buffer so larger batches can spill to disk before the final download payload is produced.

## Development Workflow

The recommended local commands are:

- `make install`
- `make dev`
- `make test`
- `make lint`
- `make format`
- `make check`

`Makefile` delegates to the shell wrappers in `scripts/`, so the commands work both with and without an activated virtual environment as long as `.venv` exists.

## Quality Gates

- `ruff` enforces import order and core lint rules.
- `pytest` covers CLI behavior, config loading, image processing, range parsing, and web helper logic.
- GitHub Actions runs lint and tests on pushes and pull requests.
