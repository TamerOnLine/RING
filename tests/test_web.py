from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZipFile

from PIL import Image

from rimg.models import ProcessOptions, ResizeOptions
from rimg.web import (
    _assess_batch,
    _build_preview_images,
    _build_process_options,
    _failure_summary,
    _prepare_uploads,
    _process_uploads,
    _process_uploads_to_zip,
    _select_uploads,
    _session_settings_snapshot,
    _settings_from_preset,
    _supports_target_size,
)


@dataclass
class FakeUpload:
    name: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def getvalue(self) -> bytes:
        return self.data


@dataclass
class CountingUpload(FakeUpload):
    calls: int = 0

    def getvalue(self) -> bytes:
        self.calls += 1
        return self.data


def test_select_uploads_reports_invalid_ranges() -> None:
    uploads = [
        FakeUpload("img-1.png", b""),
        FakeUpload("img-2.png", b""),
    ]

    selected, error = _select_uploads(uploads, "3-1", auto_index=False)

    assert selected == []
    assert error == "Invalid descending range: 3-1"


def test_process_uploads_skips_invalid_images() -> None:
    source = BytesIO()
    Image.new("RGB", (12, 12), "red").save(source, format="PNG")
    uploads = [
        FakeUpload("good.png", source.getvalue()),
        FakeUpload("bad.png", b"not-an-image"),
    ]

    processed, failures = _process_uploads(
        uploads,
        ProcessOptions(resize=ResizeOptions(width=8, height=8), output_format="PNG"),
    )

    assert [image.filename for image in processed] == ["good.png"]
    assert len(failures) == 1
    assert failures[0].startswith("bad.png:")


def test_select_uploads_keeps_duplicate_names_distinct() -> None:
    uploads = [
        FakeUpload("same.png", b"one"),
        FakeUpload("other.png", b"two"),
        FakeUpload("same.png", b"three"),
    ]

    selected, error = _select_uploads(uploads, "3", auto_index=True)

    assert error is None
    assert selected == [uploads[2]]


def test_supports_target_size_only_for_lossy_formats() -> None:
    assert _supports_target_size("JPEG") is True
    assert _supports_target_size("WEBP") is True
    assert _supports_target_size("PNG") is False


def test_settings_from_preset_returns_expected_values() -> None:
    settings = _settings_from_preset("avatar_circle")

    assert settings["resize_width"] == 512
    assert settings["resize_height"] == 512
    assert settings["resize_unit"] == "px"
    assert settings["resize_mode"] == "fill_crop"
    assert settings["mask"] == "circle"
    assert settings["output_format"] == "PNG"
    assert settings["max_kb_enabled"] is False


def test_session_settings_snapshot_includes_restore_fields() -> None:
    snapshot = _session_settings_snapshot(
        preset_key="web_compressed",
        width=1600,
        height=1200,
        unit="px",
        dpi=300,
        resize_mode="fit",
        mask="none",
        output_format="JPEG",
        max_kb_enabled=True,
        max_kb=240,
        range_expression="1-3",
        auto_index=False,
    )

    assert snapshot["preset_key"] == "web_compressed"
    assert snapshot["resize_width"] == 1600
    assert snapshot["resize_mode"] == "fit"
    assert snapshot["max_kb"] == 240
    assert snapshot["range_expression"] == "1-3"
    assert snapshot["auto_index"] is False


def test_build_process_options_ignores_target_size_for_png() -> None:
    options = _build_process_options(
        width=800,
        height=600,
        unit="px",
        dpi=300,
        resize_mode="fit",
        mask="none",
        output_format="PNG",
        max_kb_enabled=True,
        max_kb=200,
    )

    assert options == ProcessOptions(
        resize=ResizeOptions(width=800, height=600, unit="px", dpi=300, mode="fit"),
        mask="none",
        max_kb=None,
        output_format="PNG",
    )


def test_build_preview_images_returns_processed_previews() -> None:
    source = BytesIO()
    Image.new("RGB", (20, 10), "blue").save(source, format="PNG")
    uploads = [FakeUpload("preview.png", source.getvalue())]

    previews, failures = _build_preview_images(
        uploads,
        ProcessOptions(resize=ResizeOptions(width=8, height=6), output_format="JPEG"),
    )

    assert failures == []
    assert [preview.source_name for preview in previews] == ["preview.png"]
    assert previews[0].processed.filename == "preview.jpg"

    with Image.open(BytesIO(previews[0].processed.data)) as image:
        assert image.size == (8, 6)
        assert image.format == "JPEG"


def test_build_preview_images_reports_invalid_images() -> None:
    uploads = [FakeUpload("bad.png", b"not-an-image")]

    previews, failures = _build_preview_images(
        uploads,
        ProcessOptions(resize=ResizeOptions(width=8, height=6), output_format="PNG"),
    )

    assert previews == []
    assert failures
    assert failures[0].startswith("bad.png:")


def test_prepare_uploads_reads_each_file_once() -> None:
    uploads = [CountingUpload("one.png", b"abc"), CountingUpload("two.png", b"def")]

    prepared = _prepare_uploads(uploads)

    assert [item.name for item in prepared] == ["one.png", "two.png"]
    assert [item.data for item in prepared] == [b"abc", b"def"]
    assert [upload.calls for upload in uploads] == [1, 1]


def test_assess_batch_adds_warnings_for_large_batches() -> None:
    uploads = [
        FakeUpload("one.png", b"a" * 70),
        FakeUpload("two.png", b"b" * 70),
    ]

    assessment = _assess_batch(
        uploads,
        file_warning_threshold=2,
        byte_warning_threshold=100,
    )

    assert assessment.total_files == 2
    assert assessment.total_bytes == 140
    assert assessment.requires_confirmation is True
    assert len(assessment.warnings) == 2


def test_assess_batch_has_no_default_warning_limits() -> None:
    uploads = [FakeUpload("one.png", b"a" * 1024) for _ in range(50)]

    assessment = _assess_batch(uploads)

    assert assessment.total_files == 50
    assert assessment.total_bytes == 50 * 1024
    assert assessment.requires_confirmation is False
    assert assessment.warnings == ()


def test_failure_summary_limits_recent_errors() -> None:
    summary = _failure_summary(
        ["one.png: bad", "two.png: bad", "three.png: bad", "four.png: bad"],
        limit=2,
    )

    assert "three.png: bad" in summary
    assert "four.png: bad" in summary
    assert "one.png: bad" not in summary
    assert "... and 2 more" in summary


def test_process_uploads_reports_progress_updates() -> None:
    source = BytesIO()
    Image.new("RGB", (12, 12), "green").save(source, format="PNG")
    uploads = [
        FakeUpload("good.png", source.getvalue()),
        FakeUpload("bad.png", b"not-an-image"),
    ]
    updates = []

    processed, failures = _process_uploads(
        uploads,
        ProcessOptions(resize=ResizeOptions(width=8, height=8), output_format="PNG"),
        progress_callback=updates.append,
    )

    assert [image.filename for image in processed] == ["good.png"]
    assert len(failures) == 1
    assert len(updates) == 2
    assert updates[0].completed == 1
    assert updates[0].processed_count == 1
    assert updates[0].failed_count == 0
    assert updates[0].last_error is None
    assert updates[1].completed == 2
    assert updates[1].processed_count == 1
    assert updates[1].failed_count == 1
    assert updates[1].last_error.startswith("bad.png:")


def test_process_uploads_to_zip_streams_processed_results() -> None:
    source = BytesIO()
    Image.new("RGB", (12, 12), "purple").save(source, format="PNG")
    uploads = [
        FakeUpload("same.png", source.getvalue()),
        FakeUpload("same.png", source.getvalue()),
        FakeUpload("bad.png", b"not-an-image"),
    ]

    result = _process_uploads_to_zip(
        uploads,
        ProcessOptions(resize=ResizeOptions(width=8, height=8), output_format="PNG"),
    )

    assert result.processed_count == 2
    assert len(result.failures) == 1
    assert result.failures[0].startswith("bad.png:")
    assert result.zip_bytes is not None

    with ZipFile(BytesIO(result.zip_bytes)) as archive:
        assert archive.namelist() == ["same.png", "same_2.png", "rimg-report.txt"]
        report = archive.read("rimg-report.txt").decode("utf-8")

    assert "Processed: 2" in report
    assert "Failed: 1" in report
    assert "same.png -> same.png OK" in report
    assert "same.png -> same_2.png OK" in report
    assert "bad.png FAILED:" in report


def test_process_uploads_to_zip_reports_target_size_warnings() -> None:
    source = BytesIO()
    Image.effect_noise((512, 512), 100).convert("RGB").save(source, format="PNG")
    uploads = [FakeUpload("large.png", source.getvalue())]

    result = _process_uploads_to_zip(
        uploads,
        ProcessOptions(
            resize=ResizeOptions(width=512, height=512),
            output_format="JPEG",
            max_kb=1,
        ),
    )

    assert result.processed_count == 1
    assert result.failures == []
    assert result.warnings
    assert result.warnings[0].startswith("large.png: Target max size 1 KB could not be reached")
    assert result.zip_bytes is not None

    with ZipFile(BytesIO(result.zip_bytes)) as archive:
        assert "rimg-report.txt" in archive.namelist()
        report = archive.read("rimg-report.txt").decode("utf-8")

    assert "Warnings: 1" in report
    assert "large.png -> large.jpg WARNING" in report
    assert "WARNING: Target max size 1 KB could not be reached" in report
