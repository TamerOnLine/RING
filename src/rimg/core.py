from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from tempfile import SpooledTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw, ImageOps

from rimg.config import (
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_MASKS,
    SUPPORTED_RESIZE_MODES,
    SUPPORTED_TARGET_SIZE_FORMATS,
)
from rimg.models import ProcessedImage, ProcessOptions, ResizeOptions
from rimg.utils import mime_type_for_format, output_filename, unique_filename

ZIP_SPOOL_LIMIT_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class EncodingResult:
    data: bytes
    warnings: tuple[str, ...] = ()


class ZipArchiveBuilder:
    def __init__(self, spool_limit_bytes: int = ZIP_SPOOL_LIMIT_BYTES) -> None:
        self._used_names: set[str] = set()
        self._buffer = SpooledTemporaryFile(max_size=spool_limit_bytes)
        self._archive = ZipFile(self._buffer, "w", ZIP_DEFLATED)

    def add_image(self, image: ProcessedImage) -> str:
        archive_name = unique_filename(image.filename, self._used_names)
        self._archive.writestr(archive_name, image.data)
        return archive_name

    def add_text(self, filename: str, text: str) -> str:
        archive_name = unique_filename(filename, self._used_names)
        self._archive.writestr(archive_name, text.encode("utf-8"))
        return archive_name

    def finish(self) -> bytes:
        self._archive.close()
        self._buffer.seek(0)
        data = self._buffer.read()
        self._buffer.close()
        return data

    def close(self) -> None:
        self._archive.close()
        self._buffer.close()


def dimensions_to_pixels(options: ResizeOptions) -> tuple[int, int]:
    if options.unit == "px":
        return options.width, options.height
    if options.unit == "cm":
        return (
            max(1, round(options.width / 2.54 * options.dpi)),
            max(1, round(options.height / 2.54 * options.dpi)),
        )
    raise ValueError(f"Unsupported resize unit: {options.unit}")


def resize_image(image: Image.Image, options: ResizeOptions) -> Image.Image:
    target_size = dimensions_to_pixels(options)
    if options.mode not in SUPPORTED_RESIZE_MODES:
        raise ValueError(f"Unsupported resize mode: {options.mode}")
    if options.mode == "stretch":
        return image.resize(target_size, Image.Resampling.LANCZOS)
    if options.mode == "fit":
        return ImageOps.contain(image, target_size, Image.Resampling.LANCZOS)
    if options.mode == "fill_crop":
        return ImageOps.fit(image, target_size, Image.Resampling.LANCZOS)
    raise ValueError(f"Unsupported resize mode: {options.mode}")


def process_image(filename: str, raw: bytes, options: ProcessOptions) -> ProcessedImage:
    output_format = _normalize_format(options.output_format)
    with Image.open(BytesIO(raw)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image = resize_image(image, options.resize)
        image = apply_mask(image, options.mask)
        encoded = _encode_image_with_warnings(image, output_format, options.max_kb)

    return ProcessedImage(
        filename=output_filename(filename, output_format),
        data=encoded.data,
        mime_type=mime_type_for_format(output_format),
        warnings=encoded.warnings,
    )


def apply_mask(image: Image.Image, mask: str) -> Image.Image:
    if mask == "none":
        return image
    if mask not in SUPPORTED_MASKS:
        raise ValueError(f"Unsupported mask: {mask}")

    alpha = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(alpha)
    draw.ellipse(_mask_bounds(image.size, mask), fill=255)

    masked = image.copy()
    masked.putalpha(alpha)
    return masked


def encode_image(image: Image.Image, output_format: str, max_kb: int | None) -> bytes:
    return _encode_image_with_warnings(image, output_format, max_kb).data


def _encode_image_with_warnings(
    image: Image.Image,
    output_format: str,
    max_kb: int | None,
) -> EncodingResult:
    output_format = _normalize_format(output_format)
    if output_format == "JPEG":
        image = _flatten_for_jpeg(image)

    if max_kb and output_format in SUPPORTED_TARGET_SIZE_FORMATS:
        return _encode_to_target_size(image, output_format, max_kb)

    buffer = BytesIO()
    save_kwargs = {"optimize": True}
    if output_format in {"JPEG", "WEBP"}:
        save_kwargs["quality"] = 90
    image.save(buffer, format=output_format, **save_kwargs)
    return EncodingResult(buffer.getvalue())


def build_zip(images: Iterable[ProcessedImage]) -> bytes:
    builder = ZipArchiveBuilder()
    try:
        for image in images:
            builder.add_image(image)
        return builder.finish()
    except Exception:
        builder.close()
        raise


def _encode_to_target_size(image: Image.Image, output_format: str, max_kb: int) -> EncodingResult:
    target_bytes = max_kb * 1024
    best: bytes | None = None
    low, high = 1, 95

    while low <= high:
        quality = (low + high) // 2
        buffer = BytesIO()
        image.save(buffer, format=output_format, quality=quality, optimize=True)
        data = buffer.getvalue()

        if len(data) <= target_bytes:
            best = data
            low = quality + 1
        else:
            high = quality - 1

    if best is not None:
        return EncodingResult(best)

    buffer = BytesIO()
    image.save(buffer, format=output_format, quality=1, optimize=True)
    data = buffer.getvalue()
    return EncodingResult(
        data=data,
        warnings=(
            f"Target max size {max_kb} KB could not be reached; "
            f"smallest output is {_format_kb(len(data))} KB.",
        ),
    )


def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
    background = Image.new("RGB", image.size, "white")
    background.paste(image, mask=image.getchannel("A"))
    return background


def _format_kb(size_bytes: int) -> str:
    return f"{size_bytes / 1024:.1f}"


def _mask_bounds(size: tuple[int, int], mask: str) -> tuple[int, int, int, int]:
    width, height = size
    if mask == "ellipse":
        return (0, 0, width - 1, height - 1)

    diameter = min(width, height)
    left = (width - diameter) // 2
    top = (height - diameter) // 2
    return (left, top, left + diameter - 1, top + diameter - 1)


def _normalize_format(value: str) -> str:
    normalized = value.upper()
    if normalized == "JPG":
        return "JPEG"
    if normalized not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(f"Unsupported output format: {value}")
    return normalized
