"""Regression fixtures for nullable conditional binary indicators."""

import numpy as np
import pandas as pd

from SCE.importer import any_selected_indicator, recode_binary_response


def test_binary_response_recodes_preserve_missingness() -> None:
    """Verify opposite response codings retain yes, no, and not-asked states."""
    q15 = pd.Series([1.0, 2.0, np.nan], name="Q15")
    d1 = pd.Series([1.0, 2.0, np.nan], name="D1")

    looking_for_job = recode_binary_response(q15, true_code=1, false_code=2)
    hh_changed = recode_binary_response(d1, true_code=2, false_code=1)

    expected_looking = pd.Series([1, 0, pd.NA], dtype="Int8", name="Q15")
    expected_changed = pd.Series([0, 1, pd.NA], dtype="Int8", name="D1")
    pd.testing.assert_series_equal(looking_for_job, expected_looking)
    pd.testing.assert_series_equal(hh_changed, expected_changed)


def test_selected_indicator_uses_all_columns_to_determine_missingness() -> None:
    """Verify observed non-selections are zero while all-missing rows stay missing."""
    indicators = pd.DataFrame(
        {
            "status_1": [1.0, 0.0, 0.0, 0.0, np.nan],
            "status_2": [0.0, 1.0, 0.0, np.nan, np.nan],
            "status_3": [0.0, 0.0, 1.0, 1.0, np.nan],
            "status_4": [0.0, 0.0, 0.0, np.nan, np.nan],
        }
    )

    result = any_selected_indicator(
        indicators, selected_columns=["status_1", "status_2"]
    )

    expected = pd.Series([1, 1, 0, 0, pd.NA], dtype="Int8")
    pd.testing.assert_series_equal(result, expected)


def test_spouse_working_covers_initial_and_repeat_status_rows() -> None:
    """Verify merged HH2 rows classify all working categories and missing states."""
    index = pd.MultiIndex.from_tuples(
        [(101, 1), (101, 2), (202, 1), (202, 2), (303, 1)],
        names=["userid", "wid"],
    )
    columns = [f"HH2_{i}" for i in range(1, 12)]
    statuses = pd.DataFrame(0.0, index=index, columns=columns)
    statuses.loc[(101, 1), "HH2_1"] = 1.0  # Initial full-time response
    statuses.loc[(101, 2), "HH2_2"] = 1.0  # Repeat part-time response
    statuses.loc[(202, 1), "HH2_3"] = 1.0  # Self-employed response
    statuses.loc[(202, 2), "HH2_8"] = 1.0  # Observed retiree response
    statuses.loc[(303, 1), :] = np.nan

    result = any_selected_indicator(
        statuses, selected_columns=["HH2_1", "HH2_2", "HH2_3"]
    )

    expected = pd.Series([1, 1, 1, 0, pd.NA], dtype="Int8", index=index)
    pd.testing.assert_series_equal(result, expected)
