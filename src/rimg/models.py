from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResizeOptions:
    width: int
    height: int
    unit: str = "px"
    dpi: int = 300
    mode: str = "stretch"


@dataclass(frozen=True)
class ProcessOptions:
    resize: ResizeOptions
    mask: str = "none"
    max_kb: int | None = None
    output_format: str = "PNG"


@dataclass(frozen=True)
class ProcessedImage:
    filename: str
    data: bytes
    mime_type: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessingPreset:
    label: str
    description: str
    options: ProcessOptions


@dataclass(frozen=True)
class NumberedSelection:
    name: str
    index: int
    position: int
