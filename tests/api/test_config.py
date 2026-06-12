import pytest

from src.api.config import Settings


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("true", True),
        ("development", True),
        ("release", False),
        ("production", False),
    ],
)
def test_debug_accepts_common_environment_strings(monkeypatch, raw_value, expected):
    monkeypatch.setenv("DEBUG", raw_value)

    settings = Settings(_env_file=None)

    assert settings.DEBUG is expected
