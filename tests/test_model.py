"""Model identification from the Bluetooth name."""

import pytest

from custom_components.flipr_local.model import get_flipr_model


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (None, "Flipr"),
        ("", "Flipr"),
        ("Flipr 12345", "Flipr"),
        ("F3A1B2", "Flipr AnalysR 3"),
        ("f31abc", "Flipr AnalysR 3"),  # case-insensitive
        ("F2B123", "Flipr AnalysR"),
        ("Flipr 01234", "Flipr Start Max"),
        ("FLIPR 00999", "Flipr Start Max"),
        ("Something else", "Flipr"),
    ],
)
def test_model_from_bluetooth_name(name, expected):
    assert get_flipr_model(name) == expected
