"""Focused regression tests for independently processed SCE question blocks."""

import numpy as np
import pandas as pd

from SCE.importer import (
    _process_demographics,
    _process_general_expectations,
    _process_housing_and_macro,
)


def test_financial_well_being_preserves_missing_responses() -> None:
    """Q1 and Q2 missing responses remain nullable rather than sentinel-coded."""
    index = pd.MultiIndex.from_tuples(
        [(10001, 202401), (10002, 202401)],
        names=["userid", "wid"],
    )
    df = pd.DataFrame(
        {
            "Q1": [1, np.nan],
            "Q2": [np.nan, 5],
            "Q3": [10.0, 20.0],
            "Q4new": [30.0, 40.0],
            "Q5new": [50.0, 60.0],
            "Q6new": [70.0, 80.0],
        },
        index=index,
    )

    df_full, df_extract = _process_general_expectations(df)

    expected_q1 = pd.Series([1, pd.NA], index=index, dtype="Int8", name="Q1")
    expected_q2 = pd.Series([pd.NA, 5], index=index, dtype="Int8", name="Q2")
    pd.testing.assert_series_equal(df_full["Q1"], expected_q1)
    pd.testing.assert_series_equal(df_full["Q2"], expected_q2)
    pd.testing.assert_series_equal(
        df_extract["financial_past_12m"],
        expected_q1.rename("financial_past_12m"),
    )
    pd.testing.assert_series_equal(
        df_extract["financial_12m"],
        expected_q2.rename("financial_12m"),
    )


def test_house_price_extract_uses_normalized_source_value() -> None:
    """Full and extract house-price changes share one sign normalization."""
    index = pd.MultiIndex.from_tuples(
        [(10001, 202401)],
        names=["userid", "wid"],
    )
    df = pd.DataFrame(
        {
            "Q31v2": [3],
            "Q31v2part2": [2.5],
            "C1_1": [10.0],
            "C2": [1],
            "C2part2": [1.5],
            "C3": [1],
            "C3part2": [1.2],
        },
        index=index,
    )

    df_full, df_extract = _process_housing_and_macro(df)

    idx = (10001, 202401)
    assert df_full.loc[idx, "Q31v2part2"] == -2.5
    assert df_extract.loc[idx, "house_price_change"] == -2.5


def test_race_source_is_sparse_and_extract_indicator_is_tiled() -> None:
    """Race source fields remain sparse while extract indicators are tiled."""
    index = pd.MultiIndex.from_tuples(
        [(101, 202401), (101, 202402)],
        names=["userid", "wid"],
    )
    df = pd.DataFrame(
        {
            "Q32": [45, np.nan],
            "Q33": [1, np.nan],
            "Q34": [2, np.nan],
            "Q35_1": [0, np.nan],
            "Q35_2": [1, np.nan],
            "Q35_note": ["initial response", np.nan],
            "Q36": [6, np.nan],
            "Q37": [3, np.nan],
        },
        index=index,
    )

    df_full, df_extract = _process_demographics(df)

    assert "black" not in df_full.columns
    assert df_full["Q35_2"].tolist()[0] == 1
    assert pd.isna(df_full["Q35_2"].iloc[1])
    assert df_extract["black"].tolist() == [1, 1]
    assert "Q35_note" not in df_full.columns
