"""Regression tests for inflation density summaries and source precision."""

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

    df_full, df_extract = _process_inflation(df)

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


def test_processing_preserves_precision_and_full_extract_equality() -> None:
    """Processing remains lossless before presentation-specific CSV rounding."""
    df = _inflation_frame(
        {
            "Q8v2": 1,
            "Q8v2part2": 2.54321,
            "Q9bv2": 2,
            "Q9bv2part2": 1.54321,
            "Q1a": 2,
            "Q1apart2": 0.84321,
            "Q9new2_mean": 0.61234,
            "Q9new2_probdeflation": 0.154321,
        }
    )

    df_full, df_extract = _process_inflation(df)

    idx = (10001, 202401)
    point_forecasts = (
        ("Q8v2part2", "infl_1y", 2.54321),
        ("Q9bv2part2", "infl_3y", -1.54321),
        ("Q1apart2", "infl_5y", -0.84321),
    )
    for source, extract, expected in point_forecasts:
        assert df_full.loc[idx, source] == expected
        assert df_extract.loc[idx, extract] == expected

    assert df_full.loc[idx, "Q9new2_mean"] == 0.61234
    assert df_extract.loc[idx, "infl_5y_bin_mean"] == 0.61234
    assert df_full.loc[idx, "Q9new2_probdeflation"] == 0.154321
    assert df_extract.loc[idx, "infl_5y_bin_prob_defl"] == pytest.approx(15.4321)
