"""Regression fixtures for conservative sign-convention normalization."""

import logging

import numpy as np
import pandas as pd
import pytest

from SCE.importer import flip_negative


def test_uniformly_unsigned_series_flips_only_observed_decreases(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify an unambiguously unsigned Series is normalized conservatively."""
    values = pd.Series([4.0, 2.0, 0.0, np.nan, 7.0], name="change")
    direction = pd.Series([1.0, 3.0, 3.0, 3.0, np.nan])
    original = values.copy()
    caplog.set_level(logging.INFO, logger="SCE")

    result = flip_negative(values, direction, decrease_code=3)

    expected = pd.Series([4.0, -2.0, -0.0, np.nan, 7.0], name="change")
    pd.testing.assert_series_equal(result, expected)
    pd.testing.assert_series_equal(values, original)
    assert "flipping 1 explicit decrease values" in caplog.text
    assert "1 missing direction" in caplog.text


def test_signed_series_preserves_values_with_missing_direction(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify missing direction is neither changed nor treated as non-decrease."""
    values = pd.Series([4.0, -2.0, 0.0, -5.0, np.nan], name="change")
    direction = pd.Series([1.0, 3.0, 2.0, np.nan, 3.0])
    caplog.set_level(logging.INFO, logger="SCE")

    result = flip_negative(values, direction, decrease_code=3)

    pd.testing.assert_series_equal(result, values)
    assert "already normalized" in caplog.text
    assert "1 missing direction" in caplog.text
    assert not [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]


def test_mixed_sign_conventions_are_left_entirely_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify mixed signed and unsigned decreases never trigger row-wise fixes."""
    values = pd.Series([4.0, -2.0, 3.0, -1.0], name="change")
    direction = pd.Series([1, 3, 3, 1])
    caplog.set_level(logging.INFO, logger="SCE")

    result = flip_negative(values, direction, decrease_code=3)

    pd.testing.assert_series_equal(result, values)
    assert "mixed or contradictory sign evidence" in caplog.text
    assert "observed decreases: 1 positive and 1 negative values" in caplog.text
    assert "observed non-decreases: 1 negative values" in caplog.text


def test_series_without_observed_directions_is_preserved(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify direction-free values cannot trigger convention inference."""
    values = pd.Series([4.0, -2.0, np.nan], name="change")
    direction = pd.Series([np.nan, np.nan, np.nan])
    caplog.set_level(logging.INFO, logger="SCE")

    result = flip_negative(values, direction, decrease_code=3)

    pd.testing.assert_series_equal(result, values)
    assert "No values with observed direction" in caplog.text
    assert "2 missing direction" in caplog.text
