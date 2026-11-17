"""Tests for value matching — the conservative core of the audit."""

from luck_audit.matching import (
    find_in_structured,
    flatten,
    normalize_text,
    value_in_text,
    values_equal,
)


def test_normalize_text():
    assert normalize_text("  PK-301\t\n") == "pk-301"
    assert normalize_text("Amna   Raheeba") == "amna raheeba"


def test_values_equal_case_insensitive():
    assert values_equal("PK-301", "pk-301")
    assert not values_equal("PK-301", "PK-310")


def test_values_equal_numbers():
    assert values_equal(12, 12.0)
    assert values_equal("12", 12)
    assert not values_equal("12A", 12)


def test_values_equal_dates():
    assert values_equal("2026-12-05", "5 Dec 2026")
    assert values_equal("2026-12-05", "05/12/2026")
    assert not values_equal("2026-12-05", "2026-12-06")
    assert not values_equal("2026-12-05", "not a date")


def test_value_in_text_substring():
    assert value_in_text("PK-301", "Book flight PK-301 please")
    assert not value_in_text("PK-301", "Book flight PK-310 please")


def test_value_in_text_short_values_never_match():
    # A one- or two-character string is not evidence by substring.
    assert not value_in_text("A", "Seat 14A is free")
    assert not value_in_text("1A", "Seat 14A is free")
    # But a genuine number still matches as a whole token.
    assert value_in_text("14", "Seat 14B is free")


def test_value_in_text_number_token():
    assert value_in_text(14, "Seat 14B is free")
    assert not value_in_text(15, "Seat 14B is free")


def test_value_in_text_date():
    assert value_in_text("2026-12-05", "on 5 Dec 2026")
    assert not value_in_text("2026-12-06", "on 5 Dec 2026")


def test_flatten_nested():
    data = {"a": {"b": [1, {"c": "x"}]}, "d": "y"}
    flat = dict(flatten(data))
    assert flat["a.b[0]"] == 1
    assert flat["a.b[1].c"] == "x"
    assert flat["d"] == "y"


def test_find_in_structured_exact_field():
    data = {"flights": [{"flight_id": "PK-301", "seats": ["14B"]}]}
    assert find_in_structured("PK-301", data) == "flights[0].flight_id"
    assert find_in_structured("14B", data) == "flights[0].seats[0]"


def test_find_in_structured_text_leaf():
    data = {"summary": "Flight PK-301 departs 08:00"}
    assert find_in_structured("PK-301", data) == "summary"


def test_find_in_structured_miss():
    assert find_in_structured("PK-999", {"flight_id": "PK-301"}) is None
