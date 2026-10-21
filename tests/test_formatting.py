"""Payload-condensing helpers, including the parsers agents feed free text to."""

from __future__ import annotations

import pytest

from platform_mcp.formatting import (
    clamp_limit,
    first_line,
    quote_filter_value,
    money_to_float,
    parse_duration_seconds,
    parse_list_arg,
    truncate,
)


class TestParseDuration:
    @pytest.mark.parametrize(
        ("text", "seconds"),
        [
            ("90s", 90),
            ("30m", 1800),
            ("2h", 7200),
            ("1d", 86400),
            ("1.5h", 5400),
            ("  6H  ", 21600),
            ("300", 300),
        ],
    )
    def test_understood_durations(self, text, seconds):
        assert parse_duration_seconds(text) == seconds

    @pytest.mark.parametrize("text", ["", "soon", "abcs", "h"])
    def test_unparseable_input_falls_back_to_the_default(self, text):
        assert parse_duration_seconds(text, default_seconds=42) == 42


class TestClampLimit:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0, 1), (-5, 1), (1, 1), (25, 25), (100, 100), (101, 100), (10**9, 100)],
    )
    def test_limit_is_bounded_to_one_through_maximum(self, value, expected):
        assert clamp_limit(value, 100) == expected


class TestTruncate:
    def test_short_text_is_untouched(self):
        assert truncate("hello") == "hello"

    def test_long_text_is_marked_as_cut(self):
        result = truncate("x" * 500, limit=100)
        assert len(result) == 100
        assert result.endswith("…")

    def test_none_becomes_empty(self):
        assert truncate(None) == ""


class TestFirstLine:
    def test_only_the_first_line_survives(self):
        assert first_line("boom\n  at frame one\n  at frame two") == "boom"

    def test_blank_input_is_empty(self):
        assert first_line("   ") == ""


class TestParseListArg:
    def test_splits_and_trims(self):
        assert parse_list_arg(" a , b ,c ") == ["a", "b", "c"]

    def test_empty_entries_are_dropped(self):
        assert parse_list_arg("a,,b,") == ["a", "b"]

    def test_empty_input_is_an_empty_list(self):
        assert parse_list_arg("") == []
        assert parse_list_arg(None) == []


class TestMoneyToFloat:
    def test_units_and_nanos_combine(self):
        class Money:
            units = -12
            nanos = -500000000

        assert money_to_float(Money()) == -12.5

    def test_none_is_none(self):
        assert money_to_float(None) is None


class TestQuoteFilterValue:
    """Values interpolated into Cloud filter strings must be escaped.

    A service or metric name containing a quote or backslash otherwise
    produces an opaque InvalidArgument from the API instead of the query
    the caller meant to write (#13).
    """

    def test_plain_values_pass_through(self):
        assert quote_filter_value("frontend") == "frontend"
        assert (
            quote_filter_value("compute.googleapis.com/instance/cpu/utilization")
            == "compute.googleapis.com/instance/cpu/utilization"
        )

    def test_a_quote_is_escaped(self):
        assert quote_filter_value('my"svc') == "my" + chr(92) + '"svc'

    def test_a_backslash_is_escaped(self):
        assert quote_filter_value("back" + chr(92) + "slash") == "back" + 2 * chr(92) + "slash"

    def test_backslash_then_quote_is_escaped_in_order(self):
        # The backslash is escaped first, then the quote, so a backslash
        # followed by a quote stays distinguishable inside the filter.
        raw = quote_filter_value("a" + chr(92) + '"b')
        assert raw == "a" + 3 * chr(92) + '"b'

    def test_the_escape_round_trips_in_the_documented_order(self):
        # Unescaping (backslash pairs first, then escaped quotes) recovers
        # the original value, so quoting does not lose information.
        original = 'x"y' + chr(92) + "z"
        raw = quote_filter_value(original)
        unescaped = raw.replace(2 * chr(92), chr(92)).replace(chr(92) + '"', '"')
        assert unescaped == original
