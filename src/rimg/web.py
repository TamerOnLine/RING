from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import streamlit as st

from rimg.config import (
    BATCH_WARNING_FILE_COUNT,
    BATCH_WARNING_TOTAL_BYTES,
    DEFAULT_PRESET_KEY,
    PREVIEW_IMAGE_LIMIT,
    PROCESSING_PRESETS,
    SUPPORTED_INPUT_EXTENSIONS,
    SUPPORTED_MASKS,
    SUPPORTED_OUTPUT_FORMATS,
    SUPPORTED_RESIZE_MODES,
    SUPPORTED_TARGET_SIZE_FORMATS,
)
from rimg.core import ZipArchiveBuilder, process_image
from rimg.models import ProcessedImage, ProcessOptions, ResizeOptions
from rimg.ranges import filter_positions

RESIZE_MODE_LABELS = {
    "fit": "Fit",
    "fill_crop": "Fill crop",
    "stretch": "Stretch",
}
REPORT_FILENAME = "rimg-report.txt"
UPLOAD_WIDGET_KEY_PREFIX = "uploaded_images"
UPLOAD_WIDGET_VERSION_KEY = "upload_widget_version"


class UploadedFileLike(Protocol):
    name: str
    size: int

    def getvalue(self) -> bytes:
        ...


@dataclass(frozen=True)
class PreviewImage:
    source_name: str
    source_data: bytes
    processed: ProcessedImage


@dataclass(frozen=True)
class PreparedUpload:
    name: str
    data: bytes
    size: int

    def getvalue(self) -> bytes:
        return self.data


@dataclass(frozen=True)
class BatchAssessment:
    total_files: int
    total_bytes: int
    warnings: tuple[str, ...]

    @property
    def requires_confirmation(self) -> bool:
        return bool(self.warnings)


@dataclass(frozen=True)
class ProcessingUpdate:
    current_file: str
    completed: int
    total: int
    processed_count: int
    failed_count: int
    last_error: str | None = None


@dataclass(frozen=True)
class BatchArchiveResult:
    zip_bytes: bytes | None
    processed_count: int
    failures: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class BatchFileReport:
    source_name: str
    status: str
    output_name: str | None = None
    output_bytes: int | None = None
    warnings: tuple[str, ...] = ()
    error: str | None = None


def run() -> None:
    st.set_page_config(page_title="Rimg", page_icon="R", layout="wide")
    st.title("Rimg")
    st.caption("Batch image resize, mask, and compression studio.")
    _ensure_settings_state()

    uploaded_files = st.file_uploader(
        "Images",
        type=list(SUPPORTED_INPUT_EXTENSIONS),
        accept_multiple_files=True,
        key=_upload_widget_key(),
    )
    if uploaded_files:
        clear_col, _ = st.columns([0.28, 0.72])
        with clear_col:
            st.button(
                "Clear All Uploaded Files",
                use_container_width=True,
                on_click=_clear_uploaded_files,
            )

    left, right = st.columns([0.36, 0.64], gap="large")
    with left:
        st.subheader("Settings")
        preset_key = st.selectbox(
            "Preset",
            options=list(PROCESSING_PRESETS),
            format_func=lambda key: PROCESSING_PRESETS[key].label,
            key="preset_key",
            on_change=_apply_selected_preset,
        )
        st.caption(PROCESSING_PRESETS[preset_key].description)
        restore_last_used = "last_used_settings" in st.session_state
        st.button(
            "Restore Last Used",
            disabled=not restore_last_used,
            use_container_width=True,
            on_click=_restore_last_used_settings,
        )
        if restore_last_used:
            st.caption("Last successful settings are available for restore in this session.")
        unit = st.segmented_control("Unit", ["px", "cm"], key="resize_unit")
        resize_mode = st.selectbox(
            "Resize mode",
            list(SUPPORTED_RESIZE_MODES),
            format_func=lambda mode: RESIZE_MODE_LABELS[mode],
            key="resize_mode",
        )
        width = st.number_input("Width", min_value=1, step=10, key="resize_width")
        height = st.number_input("Height", min_value=1, step=10, key="resize_height")
        dpi = st.number_input("DPI", min_value=72, max_value=1200, step=10, key="resize_dpi")
        mask = st.selectbox("Mask", list(SUPPORTED_MASKS), key="mask")
        output_format = st.selectbox(
            "Output format",
            list(SUPPORTED_OUTPUT_FORMATS),
            key="output_format",
        )
        target_size_supported = _supports_target_size(output_format)
        if not target_size_supported:
            st.session_state["max_kb_enabled"] = False
        max_kb_enabled = st.checkbox(
            "Target max size",
            disabled=not target_size_supported,
            help="Available for JPEG and WEBP outputs only.",
            key="max_kb_enabled",
        )
        max_kb: int | None = None
        if not target_size_supported:
            st.caption("Target max size is available for JPEG and WEBP only.")
        elif max_kb_enabled:
            max_kb = st.number_input("Max KB", min_value=10, step=10, key="max_kb")
        range_expression = st.text_input("Range", placeholder="1,3,6-9,12-", key="range_expression")
        auto_index = st.checkbox("Auto-index files without numbers", key="auto_index")

    with right:
        st.subheader("Queue")
        if not uploaded_files:
            st.info("Upload images to start processing.")
            return

        selected_uploads, selection_error = _select_uploads(
            uploaded_files,
            range_expression,
            auto_index=auto_index,
        )
        if selection_error is not None:
            st.error(f"Invalid range expression: {selection_error}")
            return
        selected_uploads = _prepare_uploads(selected_uploads)

        st.caption(f"{len(selected_uploads)} of {len(uploaded_files)} image(s) selected.")
        if not selected_uploads:
            st.warning("No images match the current range selection.")
            return

        st.dataframe(
            [
                {"filename": file.name, "size_kb": round(file.size / 1024, 1)}
                for file in selected_uploads
            ],
            hide_index=True,
            use_container_width=True,
        )

        options = _build_process_options(
            width=int(width),
            height=int(height),
            unit=unit,
            dpi=int(dpi),
            resize_mode=resize_mode,
            mask=mask,
            output_format=output_format,
            max_kb_enabled=max_kb_enabled,
            max_kb=int(max_kb) if max_kb else None,
        )
        current_settings = _session_settings_snapshot(
            preset_key=preset_key,
            width=int(width),
            height=int(height),
            unit=unit,
            dpi=int(dpi),
            resize_mode=resize_mode,
            mask=mask,
            output_format=output_format,
            max_kb_enabled=max_kb_enabled,
            max_kb=int(max_kb) if max_kb else None,
            range_expression=range_expression,
            auto_index=auto_index,
        )
        _remember_session_settings(current_settings)

        with st.expander("Processing options"):
            st.json(asdict(options))

        batch_assessment = _assess_batch(selected_uploads)
        st.caption(
            f"Selected batch: {batch_assessment.total_files} file(s) • "
            f"{_format_bytes(batch_assessment.total_bytes)} total"
        )
        process_disabled = False
        if batch_assessment.requires_confirmation:
            st.warning("Large batch detected. Review the notes below before processing.")
            for warning in batch_assessment.warnings:
                st.write(f"- {warning}")
            confirm_processing = st.checkbox(
                "I understand this batch may take longer and use more memory.",
                key=_batch_confirmation_key(batch_assessment),
            )
            process_disabled = not confirm_processing
            if process_disabled:
                st.caption("Confirm the large batch warning to enable processing.")

        st.subheader("Preview")
        preview_count = min(PREVIEW_IMAGE_LIMIT, len(selected_uploads))
        st.caption(f"Previewing the first {preview_count} selected image(s).")
        preview_images, preview_failures = _build_preview_images(selected_uploads, options)
        if preview_images:
            for preview in preview_images:
                st.markdown(f"**{preview.source_name}**")
                original_col, processed_col = st.columns(2)
                with original_col:
                    st.caption("Original")
                    st.image(preview.source_data, use_container_width=True)
                with processed_col:
                    size_kb = round(len(preview.processed.data) / 1024, 1)
                    st.caption(f"{preview.processed.filename} • {size_kb} KB")
                    st.image(preview.processed.data, use_container_width=True)
                    for warning in preview.processed.warnings:
                        st.warning(warning)
        if preview_failures:
            st.warning(f"Preview failed for {len(preview_failures)} image(s).")
            _render_failures(preview_failures, title="Preview errors")

        if st.button(
            "Process",
            type="primary",
            use_container_width=True,
            disabled=process_disabled,
        ):
            status = st.status("Starting batch processing...", expanded=True)
            progress_bar = st.progress(0.0, text="Preparing batch...")
            summary_slot = st.empty()
            failure_slot = st.empty()
            recent_failures: list[str] = []

            def on_progress(update: ProcessingUpdate) -> None:
                progress_value = update.completed / update.total if update.total else 1.0
                progress_bar.progress(progress_value, text=_progress_label(update))
                summary_slot.info(_progress_summary(update))
                status.update(
                    label=(
                        f"Processing {update.current_file} "
                        f"({update.completed}/{update.total})"
                    ),
                    state="running",
                )
                if update.last_error is not None:
                    recent_failures.append(update.last_error)
                    failure_slot.warning(_failure_summary(recent_failures))

            batch_result = _process_uploads_to_zip(
                selected_uploads,
                options,
                progress_callback=on_progress,
            )
            if batch_result.processed_count == 0 or batch_result.zip_bytes is None:
                progress_bar.progress(1.0, text="Batch finished with errors.")
                summary_slot.error(
                    "No images could be processed with the current files and options."
                )
                status.update(label="Batch failed", state="error")
                _render_failures(batch_result.failures)
                return

            progress_bar.progress(1.0, text="Batch complete.")
            summary_slot.success(
                f"Processed {batch_result.processed_count} image(s), "
                f"failed {len(batch_result.failures)}, "
                f"total {len(selected_uploads)}."
            )
            status.update(
                label=(
                    f"Batch complete: {batch_result.processed_count} processed, "
                    f"{len(batch_result.failures)} failed, {len(selected_uploads)} total."
                ),
                state="complete",
            )
            _save_last_used_settings(current_settings)

            st.success(f"Processed {batch_result.processed_count} image(s).")
            if batch_result.failures:
                st.warning(
                    f"Skipped {len(batch_result.failures)} image(s) because of processing errors."
                )
                _render_failures(batch_result.failures)
            if batch_result.warnings:
                st.warning(
                    f"{len(batch_result.warnings)} processed image(s) finished with warnings."
                )
                _render_warnings(batch_result.warnings)
            st.download_button(
                "Download ZIP",
                data=batch_result.zip_bytes,
                file_name="rimg-output.zip",
                mime="application/zip",
                use_container_width=True,
            )


def _select_uploads(
    uploaded_files: Sequence[UploadedFileLike],
    range_expression: str,
    auto_index: bool,
) -> tuple[list[UploadedFileLike], str | None]:
    filenames = [file.name for file in uploaded_files]
    try:
        selected_positions = filter_positions(filenames, range_expression, auto_index=auto_index)
    except ValueError as exc:
        return [], str(exc)
    return [uploaded_files[position] for position in selected_positions], None


def _process_uploads(
    uploaded_files: Sequence[UploadedFileLike | PreparedUpload],
    options: ProcessOptions,
    progress_callback: Callable[[ProcessingUpdate], None] | None = None,
) -> tuple[list[ProcessedImage], list[str]]:
    processed: list[ProcessedImage] = []
    failures: list[str] = []
    total = len(uploaded_files)

    for completed, file in enumerate(uploaded_files, start=1):
        last_error: str | None = None
        try:
            processed.append(process_image(file.name, file.getvalue(), options))
        except (OSError, ValueError) as exc:
            last_error = f"{file.name}: {exc}"
            failures.append(last_error)
        if progress_callback is not None:
            progress_callback(
                ProcessingUpdate(
                    current_file=file.name,
                    completed=completed,
                    total=total,
                    processed_count=len(processed),
                    failed_count=len(failures),
                    last_error=last_error,
                )
            )

    return processed, failures


def _process_uploads_to_zip(
    uploaded_files: Sequence[UploadedFileLike | PreparedUpload],
    options: ProcessOptions,
    progress_callback: Callable[[ProcessingUpdate], None] | None = None,
) -> BatchArchiveResult:
    builder = ZipArchiveBuilder()
    processed_count = 0
    failures: list[str] = []
    warnings: list[str] = []
    report_entries: list[BatchFileReport] = []
    total = len(uploaded_files)

    try:
        for completed, file in enumerate(uploaded_files, start=1):
            last_error: str | None = None
            try:
                processed = process_image(file.name, file.getvalue(), options)
                archive_name = builder.add_image(processed)
                processed_count += 1
                warnings.extend(_image_warnings(file.name, processed))
                report_entries.append(
                    BatchFileReport(
                        source_name=file.name,
                        status="processed",
                        output_name=archive_name,
                        output_bytes=len(processed.data),
                        warnings=processed.warnings,
                    )
                )
            except (OSError, ValueError) as exc:
                last_error = f"{file.name}: {exc}"
                failures.append(last_error)
                report_entries.append(
                    BatchFileReport(
                        source_name=file.name,
                        status="failed",
                        error=str(exc),
                    )
                )
            if progress_callback is not None:
                progress_callback(
                    ProcessingUpdate(
                        current_file=file.name,
                        completed=completed,
                        total=total,
                        processed_count=processed_count,
                        failed_count=len(failures),
                        last_error=last_error,
                    )
            )
        if processed_count == 0:
            builder.close()
            return BatchArchiveResult(
                zip_bytes=None,
                processed_count=0,
                failures=failures,
                warnings=warnings,
            )
        builder.add_text(REPORT_FILENAME, _build_batch_report(report_entries))
        return BatchArchiveResult(
            zip_bytes=builder.finish(),
            processed_count=processed_count,
            failures=failures,
            warnings=warnings,
        )
    except Exception:
        builder.close()
        raise


def _build_preview_images(
    uploaded_files: Sequence[UploadedFileLike | PreparedUpload],
    options: ProcessOptions,
    limit: int = PREVIEW_IMAGE_LIMIT,
) -> tuple[list[PreviewImage], list[str]]:
    preview_images: list[PreviewImage] = []
    failures: list[str] = []

    for file in uploaded_files[:limit]:
        source_data = file.getvalue()
        try:
            processed = process_image(file.name, source_data, options)
        except (OSError, ValueError) as exc:
            failures.append(f"{file.name}: {exc}")
            continue
        preview_images.append(
            PreviewImage(
                source_name=file.name,
                source_data=source_data,
                processed=processed,
            )
        )

    return preview_images, failures


def _render_failures(failures: Sequence[str], title: str = "Skipped files") -> None:
    if not failures:
        return
    with st.expander(title):
        for failure in failures:
            st.write(failure)


def _render_warnings(warnings: Sequence[str], title: str = "Warnings") -> None:
    if not warnings:
        return
    with st.expander(title):
        for warning in warnings:
            st.write(warning)


def _image_warnings(source_name: str, image: ProcessedImage) -> list[str]:
    return [f"{source_name}: {warning}" for warning in image.warnings]


def _build_batch_report(entries: Sequence[BatchFileReport]) -> str:
    processed_count = sum(entry.status == "processed" for entry in entries)
    failed_count = sum(entry.status == "failed" for entry in entries)
    warning_count = sum(len(entry.warnings) for entry in entries)

    lines = [
        "Rimg processing report",
        "",
        f"Processed: {processed_count}",
        f"Failed: {failed_count}",
        f"Warnings: {warning_count}",
        "",
        "Files:",
    ]
    for entry in entries:
        if entry.status == "processed":
            status = "WARNING" if entry.warnings else "OK"
            output_name = entry.output_name or "-"
            output_size = _format_bytes(entry.output_bytes or 0)
            lines.append(f"- {entry.source_name} -> {output_name} {status} ({output_size})")
            for warning in entry.warnings:
                lines.append(f"  WARNING: {warning}")
        else:
            lines.append(f"- {entry.source_name} FAILED: {entry.error or 'Unknown error'}")
    return "\n".join(lines) + "\n"


def _supports_target_size(output_format: str) -> bool:
    return output_format in SUPPORTED_TARGET_SIZE_FORMATS


def _assess_batch(
    uploaded_files: Sequence[UploadedFileLike],
    file_warning_threshold: int | None = BATCH_WARNING_FILE_COUNT,
    byte_warning_threshold: int | None = BATCH_WARNING_TOTAL_BYTES,
) -> BatchAssessment:
    total_files = len(uploaded_files)
    total_bytes = sum(file.size for file in uploaded_files)
    warnings: list[str] = []
    if (
        file_warning_threshold is not None
        and file_warning_threshold > 0
        and total_files >= file_warning_threshold
    ):
        warnings.append(
            f"{total_files} files selected. "
            "Consider splitting very large jobs into smaller batches."
        )
    if (
        byte_warning_threshold is not None
        and byte_warning_threshold > 0
        and total_bytes >= byte_warning_threshold
    ):
        warnings.append(
            f"{_format_bytes(total_bytes)} selected in total. "
            "Processing may take longer and use more memory."
        )
    return BatchAssessment(
        total_files=total_files,
        total_bytes=total_bytes,
        warnings=tuple(warnings),
    )


def _format_bytes(total_bytes: int) -> str:
    if total_bytes < 1024 * 1024:
        return f"{round(total_bytes / 1024, 1)} KB"
    return f"{round(total_bytes / (1024 * 1024), 1)} MB"


def _progress_label(update: ProcessingUpdate) -> str:
    return (
        f"Processing {update.completed}/{update.total}: {update.current_file} "
        f"• {update.processed_count} done • {update.failed_count} failed"
    )


def _progress_summary(update: ProcessingUpdate) -> str:
    return (
        f"Processed: {update.processed_count} | "
        f"Failed: {update.failed_count} | "
        f"Total: {update.total}"
    )


def _failure_summary(failures: Sequence[str], limit: int = 3) -> str:
    recent = list(failures[-limit:])
    lines = ["Recent errors:"]
    lines.extend(f"- {failure}" for failure in recent)
    remaining = len(failures) - len(recent)
    if remaining > 0:
        lines.append(f"- ... and {remaining} more")
    return "\n".join(lines)


def _batch_confirmation_key(batch_assessment: BatchAssessment) -> str:
    return (
        f"confirm_large_batch_{batch_assessment.total_files}_"
        f"{batch_assessment.total_bytes}"
    )


def _ensure_settings_state() -> None:
    st.session_state.setdefault(UPLOAD_WIDGET_VERSION_KEY, 0)
    if "preset_key" not in st.session_state:
        st.session_state["preset_key"] = DEFAULT_PRESET_KEY
    st.session_state.setdefault(
        "manual_processing_settings",
        _settings_from_preset(DEFAULT_PRESET_KEY),
    )
    st.session_state.setdefault("active_preset_key", st.session_state["preset_key"])
    for key, value in _settings_for_active_preset(st.session_state["preset_key"]).items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("range_expression", "")
    st.session_state.setdefault("auto_index", True)


def _upload_widget_key() -> str:
    return f"{UPLOAD_WIDGET_KEY_PREFIX}_{st.session_state[UPLOAD_WIDGET_VERSION_KEY]}"


def _clear_uploaded_files() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(f"{UPLOAD_WIDGET_KEY_PREFIX}_"):
            del st.session_state[key]
    st.session_state[UPLOAD_WIDGET_VERSION_KEY] += 1


def _apply_selected_preset() -> None:
    previous_preset = st.session_state.get("active_preset_key", DEFAULT_PRESET_KEY)
    if previous_preset == DEFAULT_PRESET_KEY:
        st.session_state["manual_processing_settings"] = _processing_settings_from_state()
    for key, value in _settings_for_active_preset(st.session_state["preset_key"]).items():
        st.session_state[key] = value
    st.session_state["active_preset_key"] = st.session_state["preset_key"]


def _settings_from_preset(preset_key: str) -> dict[str, Any]:
    preset = PROCESSING_PRESETS[preset_key]
    max_kb = preset.options.max_kb
    return {
        "resize_unit": preset.options.resize.unit,
        "resize_width": preset.options.resize.width,
        "resize_height": preset.options.resize.height,
        "resize_dpi": preset.options.resize.dpi,
        "resize_mode": preset.options.resize.mode,
        "mask": preset.options.mask,
        "output_format": preset.options.output_format,
        "max_kb_enabled": max_kb is not None,
        "max_kb": max_kb or 300,
    }


def _settings_for_active_preset(preset_key: str) -> dict[str, Any]:
    if preset_key == DEFAULT_PRESET_KEY:
        return dict(
            st.session_state.get(
                "manual_processing_settings",
                _settings_from_preset(preset_key),
            )
        )
    return _settings_from_preset(preset_key)


def _processing_settings_from_state() -> dict[str, Any]:
    return {
        "resize_unit": st.session_state["resize_unit"],
        "resize_width": st.session_state["resize_width"],
        "resize_height": st.session_state["resize_height"],
        "resize_dpi": st.session_state["resize_dpi"],
        "resize_mode": st.session_state["resize_mode"],
        "mask": st.session_state["mask"],
        "output_format": st.session_state["output_format"],
        "max_kb_enabled": st.session_state["max_kb_enabled"],
        "max_kb": st.session_state["max_kb"],
    }


def _session_settings_snapshot(
    *,
    preset_key: str,
    width: int,
    height: int,
    unit: str,
    dpi: int,
    resize_mode: str,
    mask: str,
    output_format: str,
    max_kb_enabled: bool,
    max_kb: int | None,
    range_expression: str,
    auto_index: bool,
) -> dict[str, Any]:
    return {
        "preset_key": preset_key,
        "resize_unit": unit,
        "resize_width": width,
        "resize_height": height,
        "resize_dpi": dpi,
        "resize_mode": resize_mode,
        "mask": mask,
        "output_format": output_format,
        "max_kb_enabled": max_kb_enabled,
        "max_kb": max_kb or 300,
        "range_expression": range_expression,
        "auto_index": auto_index,
    }


def _apply_session_settings(snapshot: dict[str, Any]) -> None:
    for key, value in snapshot.items():
        st.session_state[key] = value


def _remember_session_settings(snapshot: dict[str, Any]) -> None:
    st.session_state["active_preset_key"] = snapshot["preset_key"]
    if snapshot["preset_key"] == DEFAULT_PRESET_KEY:
        st.session_state["manual_processing_settings"] = {
            key: snapshot[key]
            for key in _settings_from_preset(DEFAULT_PRESET_KEY)
        }


def _save_last_used_settings(snapshot: dict[str, Any]) -> None:
    st.session_state["last_used_settings"] = dict(snapshot)


def _restore_last_used_settings() -> None:
    snapshot = st.session_state.get("last_used_settings")
    if snapshot is None:
        return
    _apply_session_settings(snapshot)
    st.session_state["active_preset_key"] = snapshot["preset_key"]
    if snapshot["preset_key"] == DEFAULT_PRESET_KEY:
        st.session_state["manual_processing_settings"] = {
            key: snapshot[key]
            for key in _settings_from_preset(DEFAULT_PRESET_KEY)
        }


def _prepare_uploads(
    uploaded_files: Sequence[UploadedFileLike],
) -> list[PreparedUpload]:
    return [
        PreparedUpload(
            name=file.name,
            data=file.getvalue(),
            size=file.size,
        )
        for file in uploaded_files
    ]


def _build_process_options(
    *,
    width: int,
    height: int,
    unit: str,
    dpi: int,
    resize_mode: str,
    mask: str,
    output_format: str,
    max_kb_enabled: bool,
    max_kb: int | None,
) -> ProcessOptions:
    size_limit = max_kb if max_kb_enabled and _supports_target_size(output_format) else None
    return ProcessOptions(
        resize=ResizeOptions(width=width, height=height, unit=unit, dpi=dpi, mode=resize_mode),
        mask=mask,
        max_kb=size_limit,
        output_format=output_format,
    )


if __name__ == "__main__":
    run()
