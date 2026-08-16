"""Regression tests for inflation density summaries and centralized rounding."""

import pandas as pd
import pytest

from SCE.importer import _process_inflation


def _inflation_frame(custom_data: dict[str, float | int]) -> pd.DataFrame:
    """Create a one-row panel frame containing the inflation source variables."""
    data: dict[str, float | int] = {
        "Q8v2": 1,
        "Q8v2part2": 2.5,
        "Q9_mean": 2.3,
        "Q9_var": 1.2,
        "Q9_cent50": 2.5,
        "Q9_iqr": 1.5,
        "Q9_probdeflation": 0.05,
        "Q9bv2": 1,
        "Q9bv2part2": 1.5,
        "Q9c_mean": 1.2,
        "Q9c_var": 0.8,
        "Q9c_cent50": 1.0,
        "Q9c_iqr": 0.5,
        "Q9c_probdeflation": 0.12,
    }
    data.update({f"Q9_bin{i}": 10.0 for i in range(1, 11)})
    data.update({f"Q9c_bin{i}": 10.0 for i in range(1, 11)})
    data.update(custom_data)

    index = pd.MultiIndex.from_tuples(
        [(10001, 202401)],
        names=["userid", "wid"],
    )
    return pd.DataFrame([data], index=index)


def test_inflation_summaries_extraction_and_scaling() -> None:
    """Five-year density summaries are retained, extracted, and scaled."""
    df = _inflation_frame(
        {
            "Q1a": 2,
            "Q1apart2": 0.8,
            "Q9new2_cent25": 0.1,
            "Q9new2_cent50": 0.5,
            "Q9new2_cent75": 1.2,
            "Q9new2_iqr": 1.1,
            "Q9new2_mean": 0.6,
            "Q9new2_probdeflation": 0.15,
            "Q9new2_var": 0.4,
        }
    )

    df_full, df_extract = _process_inflation(df, decimals_percent=None)

    idx = (10001, 202401)
    assert df_extract.loc[idx, "infl_5y"] == -0.8
    assert df_extract.loc[idx, "infl_5y_bin_mean"] == 0.6
    assert df_extract.loc[idx, "infl_5y_bin_var"] == 0.4
    assert df_extract.loc[idx, "infl_5y_bin_median"] == 0.5
    assert df_extract.loc[idx, "infl_5y_bin_iqr"] == 1.1
    assert df_extract.loc[idx, "infl_5y_bin_prob_defl"] == 15.0

    assert df_full.loc[idx, "Q9new2_cent25"] == 0.1
    assert df_full.loc[idx, "Q9new2_cent75"] == 1.2
    assert df_full.loc[idx, "Q9new2_mean"] == 0.6
    assert df_full.loc[idx, "Q9new2_var"] == 0.4
    assert df_full.loc[idx, "Q9new2_cent50"] == 0.5
    assert df_full.loc[idx, "Q9new2_iqr"] == 1.1
    assert df_full.loc[idx, "Q9new2_probdeflation"] == 0.15


@pytest.mark.parametrize(
    "decimals_percent,expected_1y,expected_1y_mean,expected_3y,expected_5y_prob",
    [
        (2, 2.54, 2.35, -1.54, 15.43),
        (0, 3.0, 2.0, -2.0, 15.0),
    ],
)
def test_centralized_rounding(
    decimals_percent: int,
    expected_1y: float,
    expected_1y_mean: float,
    expected_3y: float,
    expected_5y_prob: float,
) -> None:
    """Rounding applies consistently across all inflation horizons."""
    df = _inflation_frame(
        {
            "Q8v2": 1,
            "Q8v2part2": 2.54321,
            "Q9_mean": 2.3456,
            "Q9_var": 1.2345,
            "Q9bv2": 2,
            "Q9bv2part2": 1.54321,
            "Q9c_mean": 1.2345,
            "Q9c_var": 0.8765,
            "Q1a": 2,
            "Q1apart2": 0.84321,
            "Q9new2_cent25": 0.1,
            "Q9new2_cent50": 0.5,
            "Q9new2_cent75": 1.2,
            "Q9new2_iqr": 1.1,
            "Q9new2_mean": 0.6,
            "Q9new2_probdeflation": 0.154321,
            "Q9new2_var": 0.4,
        }
    )

    _, df_extract = _process_inflation(df, decimals_percent)

    idx = (10001, 202401)
    assert df_extract.loc[idx, "infl_1y"] == expected_1y
    assert df_extract.loc[idx, "infl_1y_bin_mean"] == expected_1y_mean
    assert df_extract.loc[idx, "infl_3y"] == expected_3y
    assert df_extract.loc[idx, "infl_5y_bin_prob_defl"] == expected_5y_prob
