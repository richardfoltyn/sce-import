"""Regression tests for numerical-literacy scoring."""

import logging

import numpy as np
import pandas as pd
import pytest

from SCE.importer import _process_financial_literacy


def _panel_index(n: int) -> pd.MultiIndex:
    """Create a minimal panel index for financial-literacy fixtures."""
    return pd.MultiIndex.from_tuples(
        [(100 + i, 202401) for i in range(n)],
        names=["userid", "wid"],
    )


def test_current_responses_are_scored_and_incumbent_responses_are_not(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Preserve unverified incumbent answers without classifying them."""
    index = _panel_index(4)
    df = pd.DataFrame(
        {
            "tenure": [1, 1, 1, 7],
            "QNUM1": [150.0, 140.0, np.nan, 550.0],
            "QNUM2": [242.0, 240.0, np.nan, 20.0],
            "QNUM3": [10.0, 100.0, np.nan, 10.0],
            "QNUM5": [100.0, 10.0, np.nan, 100.0],
            "QNUM6": [5.0, 50.0, np.nan, 5.0],
            "QNUM8": [3.0, 1.0, np.nan, np.nan],
            "QNUM9": [2.0, 1.0, np.nan, np.nan],
        },
        index=index,
    )
    original = df.copy(deep=True)

    with caplog.at_level(logging.WARNING, logger="SCE"):
        df_full, df_extract = _process_financial_literacy(df)

    expected = pd.Series([1, 0, pd.NA, pd.NA], index=index, dtype="Int8")
    for question in (1, 2, 3, 5, 6, 8, 9):
        pd.testing.assert_series_equal(
            df_extract[f"num_lit_q{question}_correct"],
            expected.rename(f"num_lit_q{question}_correct"),
        )

    for source in ("QNUM1", "QNUM2", "QNUM3", "QNUM5", "QNUM6", "QNUM8", "QNUM9"):
        pd.testing.assert_series_equal(df_full[source], df[source])

    assert df_extract["num_lit_q1"].iloc[-1] == 550.0
    assert df_extract["num_lit_q2"].iloc[-1] == 20.0
    assert "preserving 5 response(s) from 1 non-new-respondent row(s)" in caplog.text
    pd.testing.assert_frame_equal(df, original)


def test_all_categorical_numeracy_codes_use_the_published_answer_key() -> None:
    """Exercise every permitted response code for QNUM8 and QNUM9."""
    index = _panel_index(3)
    df = pd.DataFrame(
        {
            "tenure": [1, 1, 1],
            "QNUM1": [np.nan] * 3,
            "QNUM2": [np.nan] * 3,
            "QNUM3": [np.nan] * 3,
            "QNUM5": [np.nan] * 3,
            "QNUM6": [np.nan] * 3,
            "QNUM8": [1, 2, 3],
            "QNUM9": [1, 2, np.nan],
        },
        index=index,
    )

    _, result = _process_financial_literacy(df)

    expected_q8 = pd.Series(
        [0, 0, 1], index=index, dtype="Int8", name="num_lit_q8_correct"
    )
    expected_q9 = pd.Series(
        [0, 1, pd.NA], index=index, dtype="Int8", name="num_lit_q9_correct"
    )
    pd.testing.assert_series_equal(result["num_lit_q8_correct"], expected_q8)
    pd.testing.assert_series_equal(result["num_lit_q9_correct"], expected_q9)


def test_numeric_scoring_uses_only_a_small_absolute_tolerance() -> None:
    """Allow storage noise around QNUM2's answer without accepting nearby answers."""
    index = _panel_index(3)
    df = pd.DataFrame(
        {
            "tenure": [1, 1, 1],
            "QNUM1": [np.nan] * 3,
            "QNUM2": [242.0, 242.0 + 0.5e-6, 242.0 + 2.0e-6],
            "QNUM3": [np.nan] * 3,
            "QNUM5": [np.nan] * 3,
            "QNUM6": [np.nan] * 3,
            "QNUM8": [np.nan] * 3,
            "QNUM9": [np.nan] * 3,
        },
        index=index,
    )

    _, result = _process_financial_literacy(df)

    expected = pd.Series(
        [1, 1, 0], index=index, dtype="Int8", name="num_lit_q2_correct"
    )
    pd.testing.assert_series_equal(result["num_lit_q2_correct"], expected)
