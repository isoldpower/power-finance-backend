import pytest

from read_at_least_py import parse_read_at_least


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("100", 100),
        ("  100  ", 100),
        ("1", 1),
        (None, None),
        ("", None),
        ("   ", None),
        ("0", None),
        ("-5", None),
        ("abc", None),
        ("12.5", None),
        ("100:deadbeef", 100),
        (":deadbeef", None),
    ],
)
def test_parse_read_at_least(raw, expected):
    assert parse_read_at_least(raw) == expected
