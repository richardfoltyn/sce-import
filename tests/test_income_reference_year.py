"""Regression fixtures for ACS income reference-year assignment."""

import pandas as pd

from SCE.importer import income_reference_year


def test_income_reference_year_at_half_year_boundaries() -> None:
    """Verify December/January, June/July, and leap-year assignments."""
    dates = pd.Series(
        pd.to_datetime(
            [
                "2023-12-31",
                "2024-01-01",
                "2024-02-29",
                "2024-06-30",
                "2024-07-01",
                "2024-12-31",
                "2025-01-01",
            ]
        ),
        name="date",
    )

    result = income_reference_year(dates)

    expected = pd.Series([2023, 2023, 2023, 2023, 2024, 2024, 2024], name="year")
    pd.testing.assert_series_equal(result, expected)


def test_income_reference_year_ignores_interview_day() -> None:
    """Verify dates in the same survey month use the same reference year."""
    dates = pd.Series(
        pd.to_datetime(
            [
                "2024-01-01",
                "2024-01-02",
                "2024-01-31",
                "2024-07-01",
                "2024-07-02",
                "2024-07-31",
            ]
        ),
        name="date",
    )

    result = income_reference_year(dates)

    expected = pd.Series([2023, 2023, 2023, 2024, 2024, 2024], name="year")
    pd.testing.assert_series_equal(result, expected)
