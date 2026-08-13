from __future__ import annotations

import os
from dataclasses import dataclass

from rimg.models import ProcessingPreset, ProcessOptions, ResizeOptions

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 800
DEFAULT_DPI = 300
DEFAULT_RESIZE_MODE = "fit"
DEFAULT_PRESET_KEY = "manual"
PREVIEW_IMAGE_LIMIT = 2
# Disabled by default: no batch-size or total-bytes warning limits.
BATCH_WARNING_FILE_COUNT: int | None = None
BATCH_WARNING_TOTAL_BYTES: int | None = None
SUPPORTED_INPUT_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "bmp")
SUPPORTED_OUTPUT_FORMATS = ("PNG", "JPEG", "WEBP")
SUPPORTED_IMAGE_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "BMP"}
SUPPORTED_RESIZE_MODES = ("fit", "fill_crop", "stretch")
SUPPORTED_TARGET_SIZE_FORMATS = {"JPEG", "WEBP"}
SUPPORTED_MASKS = ("none", "circle", "ellipse")


@dataclass(frozen=True)
class AppConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


PROCESSING_PRESETS = {
    "manual": ProcessingPreset(
        label="Manual",
        description="Balanced defaults for manual resizing and export control.",
        options=ProcessOptions(
            resize=ResizeOptions(
                width=DEFAULT_WIDTH,
                height=DEFAULT_HEIGHT,
                unit="px",
                dpi=DEFAULT_DPI,
                mode=DEFAULT_RESIZE_MODE,
            ),
            mask="none",
            max_kb=None,
            output_format="PNG",
        ),
    ),
    "web_compressed": ProcessingPreset(
        label="Web Compressed",
        description="JPEG preset for websites, listings, and general sharing.",
        options=ProcessOptions(
            resize=ResizeOptions(
                width=1600,
                height=1600,
                unit="px",
                dpi=DEFAULT_DPI,
                mode="fit",
            ),
            mask="none",
            max_kb=300,
            output_format="JPEG",
        ),
    ),
    "avatar_circle": ProcessingPreset(
        label="Avatar Circle",
        description="Square PNG avatar with a circular crop mask.",
        options=ProcessOptions(
            resize=ResizeOptions(
                width=512,
                height=512,
                unit="px",
                dpi=DEFAULT_DPI,
                mode="fill_crop",
            ),
            mask="circle",
            max_kb=None,
            output_format="PNG",
        ),
    ),
    "social_square": ProcessingPreset(
        label="Social Square",
        description="1080px square JPEG for social posts and content cards.",
        options=ProcessOptions(
            resize=ResizeOptions(
                width=1080,
                height=1080,
                unit="px",
                dpi=DEFAULT_DPI,
                mode="fill_crop",
            ),
            mask="none",
            max_kb=500,
            output_format="JPEG",
        ),
    ),
    "print_10x15": ProcessingPreset(
        label="Print 10x15 cm",
        description="Classic photo print preset at 300 DPI.",
        options=ProcessOptions(
            resize=ResizeOptions(width=10, height=15, unit="cm", dpi=300, mode="fill_crop"),
            mask="none",
            max_kb=None,
            output_format="PNG",
        ),
    ),
}


def load_config() -> AppConfig:
    return AppConfig(
        host=os.getenv("RIMG_HOST", DEFAULT_HOST),
        port=_env_int("RIMG_PORT", DEFAULT_PORT),
    )


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
