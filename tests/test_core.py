from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image

from rimg.core import apply_mask, build_zip, dimensions_to_pixels, process_image, resize_image
from rimg.models import ProcessedImage, ProcessOptions, ResizeOptions


def test_dimensions_to_pixels_converts_centimeters() -> None:
    options = ResizeOptions(width=2, height=3, unit="cm", dpi=254)

    assert dimensions_to_pixels(options) == (200, 300)


def test_resize_image_fit_preserves_aspect_ratio() -> None:
    image = Image.new("RGBA", (100, 50), "red")

    resized = resize_image(image, ResizeOptions(width=20, height=20, mode="fit"))

    assert resized.size == (20, 10)


def test_resize_image_fill_crop_preserves_target_size() -> None:
    image = Image.new("RGBA", (100, 50), "red")

    resized = resize_image(image, ResizeOptions(width=20, height=20, mode="fill_crop"))

    assert resized.size == (20, 20)


def test_process_image_resizes_and_renames_output() -> None:
    source = BytesIO()
    Image.new("RGB", (20, 10), "red").save(source, format="PNG")

    processed = process_image(
        "sample.png",
        source.getvalue(),
        ProcessOptions(resize=ResizeOptions(width=8, height=6), output_format="JPEG"),
    )

    with Image.open(BytesIO(processed.data)) as image:
        assert image.size == (8, 6)
        assert image.format == "JPEG"
    assert processed.filename == "sample.jpg"
    assert processed.mime_type == "image/jpeg"


def test_apply_mask_distinguishes_circle_from_ellipse() -> None:
    image = Image.new("RGBA", (100, 60), "red")

    circle = apply_mask(image, "circle")
    ellipse = apply_mask(image, "ellipse")

    assert circle.getchannel("A").getpixel((5, 30)) == 0
    assert ellipse.getchannel("A").getpixel((5, 30)) == 255
    assert circle.getchannel("A").getpixel((50, 30)) == 255


def test_build_zip_contains_processed_images() -> None:
    archive_bytes = build_zip([ProcessedImage("one.png", b"data", "image/png")])

    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert archive.namelist() == ["one.png"]
        assert archive.read("one.png") == b"data"


@pytest.mark.parametrize("output_format", ["JPEG", "WEBP"])
def test_process_image_honors_target_size_for_lossy_formats(output_format: str) -> None:
    source = BytesIO()
    Image.effect_noise((512, 512), 100).convert("RGB").save(source, format="PNG")
    raw = source.getvalue()

    unbounded = process_image(
        "sample.png",
        raw,
        ProcessOptions(resize=ResizeOptions(width=512, height=512), output_format=output_format),
    )
    bounded = process_image(
        "sample.png",
        raw,
        ProcessOptions(
            resize=ResizeOptions(width=512, height=512),
            output_format=output_format,
            max_kb=120,
        ),
    )

    assert len(bounded.data) <= 120 * 1024
    assert len(bounded.data) <= len(unbounded.data)


def test_process_image_warns_when_target_size_cannot_be_reached() -> None:
    source = BytesIO()
    Image.effect_noise((512, 512), 100).convert("RGB").save(source, format="PNG")

    processed = process_image(
        "sample.png",
        source.getvalue(),
        ProcessOptions(
            resize=ResizeOptions(width=512, height=512),
            output_format="JPEG",
            max_kb=1,
        ),
    )

    assert len(processed.data) > 1024
    assert processed.warnings
    assert processed.warnings[0].startswith("Target max size 1 KB could not be reached")


def test_build_zip_renames_duplicate_filenames() -> None:
    archive_bytes = build_zip(
        [
            ProcessedImage("image.png", b"first", "image/png"),
            ProcessedImage("image.png", b"second", "image/png"),
            ProcessedImage("image.png", b"third", "image/png"),
        ]
    )

    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert archive.namelist() == ["image.png", "image_2.png", "image_3.png"]
        assert archive.read("image.png") == b"first"
        assert archive.read("image_2.png") == b"second"
        assert archive.read("image_3.png") == b"third"
