from __future__ import annotations

import re
from collections.abc import Iterable

from rimg.models import NumberedSelection

NUMBER_RE = re.compile(r"(\d+)")


def extract_number(filename: str) -> int | None:
    match = NUMBER_RE.search(filename)
    if not match:
        return None
    return int(match.group(1))


def assign_indexes(filenames: Iterable[str], auto_index: bool) -> list[NumberedSelection]:
    numbered: list[NumberedSelection] = []
    for position, filename in enumerate(filenames, start=1):
        index = extract_number(filename)
        if index is None and auto_index:
            index = position
        if index is not None:
            numbered.append(NumberedSelection(filename, index, position))
    return numbered


def parse_range_expression(expression: str, max_index: int | None = None) -> set[int] | None:
    expression = expression.strip()
    if not expression:
        return None

    selected: set[int] = set()
    for raw_part in expression.split(","):
        part = raw_part.strip()
        if not part:
            continue

        if "-" not in part:
            selected.add(_positive_int(part))
            continue

        start_text, end_text = part.split("-", 1)
        start = int(start_text) if start_text else 1
        if end_text:
            end = int(end_text)
        elif max_index is not None:
            end = max_index
        else:
            selected.add(start)
            continue

        if start < 1 or end < 1:
            raise ValueError("Range values must be positive")
        if start > end:
            raise ValueError(f"Invalid descending range: {part}")

        selected.update(range(start, end + 1))

    return selected


def filter_filenames(filenames: list[str], expression: str, auto_index: bool) -> list[str]:
    selected_positions = filter_positions(filenames, expression, auto_index)
    return [filenames[position] for position in selected_positions]


def filter_positions(filenames: list[str], expression: str, auto_index: bool) -> list[int]:
    numbered = assign_indexes(filenames, auto_index=auto_index)
    max_index = max((item.index for item in numbered), default=None)
    selected = parse_range_expression(expression, max_index=max_index)
    if selected is None:
        return list(range(len(filenames)))

    selected_positions = {item.position - 1 for item in numbered if item.index in selected}
    return [
        position
        for position in range(len(filenames))
        if position in selected_positions
    ]


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError("Range values must be positive")
    return parsed
