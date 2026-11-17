"""Value matching: did this evidence span actually supply this value?

Matching is deliberately conservative. A value counts as supplied by a
span only when the normalised value appears in the span — as an exact
structured field, or as a substring of the span's text. Near-misses do
not count: "PK-301" is not supplied by "PK-310", and "12A" is not
supplied by "12B". Numbers compare numerically ("12.0" == "12");
dates compare as dates ("5 Dec 2026" == "2026-12-05").
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_DATE_FORMATS = ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%Y/%m/%d")
_WS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase, strip, collapse whitespace. The canonical text form."""
    return _WS.sub(" ", str(text).strip().lower())


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _as_date(value: Any) -> str | None:
    """Parse a date-like value to ISO form, or None if it is not a date."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def values_equal(arg_value: Any, span_value: Any) -> bool:
    """Strict equality after normalisation: numbers, dates, then text."""
    if arg_value is None or span_value is None:
        return arg_value is span_value
    num_a, num_b = _as_number(arg_value), _as_number(span_value)
    if num_a is not None and num_b is not None:
        return num_a == num_b
    date_a, date_b = _as_date(arg_value), _as_date(span_value)
    if date_a is not None and date_b is not None:
        return date_a == date_b
    if date_a is not None or date_b is not None:
        return False
    return normalize_text(arg_value) == normalize_text(span_value)


def value_in_text(arg_value: Any, text: str) -> bool:
    """True when the argument value appears inside a free-text span.

    Short values (under 3 characters) never match by substring — a
    one-letter seat row is not evidence. Numbers and dates must appear
    as whole tokens, not as part of a longer number.
    """
    if arg_value is None or text is None:
        return False
    date = _as_date(arg_value)
    if date is not None:
        hay = normalize_text(text)
        if date in hay:
            return True
        if normalize_text(arg_value) in hay:
            return True
        # The same date written in another format ("5 Dec 2026").
        candidates = re.findall(
            r"\d{4}-\d{2}-\d{2}|\d{1,2}\s+[a-z]{3,9}\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}",
            hay,
        )
        return any(_as_date(c) == date for c in candidates)
    num = _as_number(arg_value)
    if num is not None:
        tokens = re.findall(r"-?\d+(?:\.\d+)?", str(text))
        return any(_as_number(t) == num for t in tokens)
    needle = normalize_text(arg_value)
    if len(needle) < 3:
        return False
    return needle in normalize_text(text)


def flatten(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten nested dicts/lists to (field path, leaf value) pairs."""
    out: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.extend(flatten(value, path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            out.extend(flatten(value, f"{prefix}[{index}]"))
    else:
        out.append((prefix, data))
    return out


def find_in_structured(arg_value: Any, data: Any) -> str | None:
    """Return the field path whose leaf equals the argument value.

    Exact field matches are checked first; a long text leaf that
    merely contains the value also counts (e.g. a summary string
    mentioning the flight id), and reports its field path.
    """
    leaves = flatten(data)
    for path, leaf in leaves:
        if values_equal(arg_value, leaf):
            return path
    for path, leaf in leaves:
        if isinstance(leaf, str) and value_in_text(arg_value, leaf):
            return path
    return None
