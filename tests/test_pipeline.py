"""Tests for pipeline functions (pre_filter from index.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from index import pre_filter


class TestPreFilter:
    def test_url_rejected(self):
        assert pre_filter("https://example.com") is False

    def test_http_url_rejected(self):
        assert pre_filter("http://example.com/foo") is False

    def test_short_text_rejected(self):
        assert pre_filter("ab") is False

    def test_only_symbols_rejected(self):
        assert pre_filter("!!!") is False

    def test_english_text_accepted(self):
        assert pre_filter("I wish for peace") is True

    def test_arabic_text_accepted(self):
        assert pre_filter("أتمنى السلام") is True

    def test_mixed_text_accepted(self):
        assert pre_filter("أتمنى peace") is True

    def test_empty_string_rejected(self):
        assert pre_filter("") is False

    def test_whitespace_rejected(self):
        assert pre_filter("   ") is False

    def test_numeric_only_rejected(self):
        assert pre_filter("12345") is False

    def test_three_chars_accepted(self):
        assert pre_filter("abc") is True
