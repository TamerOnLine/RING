from __future__ import annotations

from pathlib import Path


def output_filename(filename: str, output_format: str) -> str:
    extension = "jpg" if output_format == "JPEG" else output_format.lower()
    return f"{Path(filename).stem}.{extension}"


def mime_type_for_format(output_format: str) -> str:
    return {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "BMP": "image/bmp",
    }[output_format]


def unique_filename(filename: str, used: set[str]) -> str:
    path = Path(filename)
    candidate = filename
    counter = 2
    while candidate in used:
        candidate = f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def unique_filenames(filenames: list[str]) -> list[str]:
    used: set[str] = set()
    unique: list[str] = []

    for filename in filenames:
        unique.append(unique_filename(filename, used))

    return unique
