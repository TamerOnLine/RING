import pytest

from rimg.ranges import (
    assign_indexes,
    extract_number,
    filter_filenames,
    filter_positions,
    parse_range_expression,
)


def test_extract_number_returns_first_number() -> None:
    assert extract_number("product-42-main.png") == 42


def test_assign_indexes_can_auto_index_missing_numbers() -> None:
    indexed = assign_indexes(["cover.png", "item-7.jpg"], auto_index=True)
    assert [(item.name, item.index, item.position) for item in indexed] == [
        ("cover.png", 1, 1),
        ("item-7.jpg", 7, 2),
    ]


def test_parse_range_expression_supports_open_ended_ranges() -> None:
    assert parse_range_expression("2,4-5,7-", max_index=9) == {2, 4, 5, 7, 8, 9}


def test_filter_filenames_keeps_original_order() -> None:
    filenames = ["img-3.png", "img-1.png", "img-2.png"]
    assert filter_filenames(filenames, "1-2", auto_index=False) == ["img-1.png", "img-2.png"]


def test_filter_positions_preserves_duplicate_filenames_by_position() -> None:
    filenames = ["same.png", "other.png", "same.png"]
    assert filter_positions(filenames, "3", auto_index=True) == [2]


def test_filter_filenames_skips_unnumbered_files_without_auto_index() -> None:
    filenames = ["cover.png", "intro.png"]
    assert filter_filenames(filenames, "1", auto_index=False) == []


def test_parse_range_expression_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        parse_range_expression("0")
