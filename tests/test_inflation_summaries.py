"""Regression fixtures for five-year inflation density summaries and centralized rounding.

Author: Richard Foltyn
"""

import numpy as np
import pandas as pd
import pytest

from SCE.importer import process_sce


def _make_dummy_sce_df(custom_data: dict[str, list]) -> pd.DataFrame:
    """Create a dummy raw SCE DataFrame with all required columns.

    Parameters
    ----------
    custom_data
        Dictionary mapping column names to custom lists of values.

    Returns
    -------
    pd.DataFrame
        Dummy raw SCE DataFrame.
    """
    n = len(next(iter(custom_data.values()))) if custom_data else 1
    data = {
        "survey_date": pd.to_datetime(["2024-01-01"] * n),
        "userid": [10001 + i for i in range(n)],
        "date": [202401 + i for i in range(n)],
        "tenure": [1] * n,
        "weight": [1.0] * n,
        "Q1": [3] * n,
        "Q2": [3] * n,
        "Q3": [10] * n,
        "Q4new": [20] * n,
        "Q5new": [30] * n,
        "Q6new": [40] * n,
        "Q8v2": [1] * n,
        "Q8v2part2": [2.5] * n,
        "Q9_mean": [2.3] * n,
        "Q9_var": [1.2] * n,
        "Q9_cent50": [2.5] * n,
        "Q9_iqr": [1.5] * n,
        "Q9_probdeflation": [0.05] * n,
        "Q9bv2": [1] * n,
        "Q9bv2part2": [1.5] * n,
        "Q9c_mean": [1.2] * n,
        "Q9c_var": [0.8] * n,
        "Q9c_cent50": [1.0] * n,
        "Q9c_iqr": [0.5] * n,
        "Q9c_probdeflation": [0.12] * n,
        "Q10_1": [1] * n,
        "Q10_2": [0] * n,
        "Q11": [1] * n,
        "Q12new": [1] * n,
        "Q13new": [10] * n,
        "Q14new": [15] * n,
        "Q15": [1] * n,
        "Q16": [2] * n,
        "Q17new": [20] * n,
        "Q18new": [30] * n,
        "Q19": [np.nan] * n,
        "Q20new": [40] * n,
        "Q21new": [50] * n,
        "Q22new": [60] * n,
        "Q23v2": [1] * n,
        "Q23v2part2": [2.0] * n,
        "Q24_1": [10] * n,
        "Q25v2": [1] * n,
        "Q25v2part2": [3.0] * n,
        "Q26v2": [1] * n,
        "Q26v2part2": [4.0] * n,
        "Q27v2": [1] * n,
        "Q27v2part2": [5.0] * n,
        "Q28": [3] * n,
        "Q29": [3] * n,
        "Q30new": [10] * n,
        "Q31v2": [1] * n,
        "Q31v2part2": [2.5] * n,
        "C1_1": [10] * n,
        "C2": [1] * n,
        "C2part2": [1.5] * n,
        "C3": [1] * n,
        "C3part2": [1.2] * n,
        "QNUM1": [150] * n,
        "QNUM2": [242] * n,
        "QNUM3": [10] * n,
        "QNUM5": [100] * n,
        "QNUM6": [5] * n,
        "QNUM8": [3] * n,
        "QNUM9": [2] * n,
        "Q32": [45] * n,
        "Q33": [1] * n,
        "Q34": [2] * n,
        "Q35_1": [1] * n,
        "Q35_2": [0] * n,
        "Q36": [6] * n,
        "Q37": [3] * n,
        "Q38": [1] * n,
        "Q41": [5] * n,
        "Q42": [10] * n,
        "Q43": [1] * n,
        "Q44": [2] * n,
        "Q45b": [2] * n,
        "Q46": [1] * n,
        "Q47": [6] * n,
        "D1": [1] * n,
        "D3": [2] * n,
        "DSAME": [1] * n,
        "DQ38": [1] * n,
        "D6": [6] * n,
    }
    for i in range(1, 10):
        data[f"Q45new_{i}"] = [0.0] * n
        data[f"D2new_{i}"] = [0.0] * n
    for i in range(1, 11):
        data[f"Q9_bin{i}"] = [10.0] * n
        data[f"Q9c_bin{i}"] = [10.0] * n
    for i in range(1, 12):
        data[f"HH2_{i}"] = [0.0] * n

    for col, values in custom_data.items():
        data[col] = values

    return pd.DataFrame(data)


def test_inflation_summaries_extraction_and_scaling() -> None:
    """Verify that five-year density summaries are extracted and scaled correctly."""
    custom_data = {
        "Q1a": [2],
        "Q1apart2": [0.8],
        "Q9new2_cent25": [0.1],
        "Q9new2_cent50": [0.5],
        "Q9new2_cent75": [1.2],
        "Q9new2_iqr": [1.1],
        "Q9new2_mean": [0.6],
        "Q9new2_probdeflation": [0.15],
        "Q9new2_var": [0.4],
    }
    df_raw = _make_dummy_sce_df(custom_data)

    df_full, df_extract = process_sce(df_raw, decimals_percent=None)

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
    """Verify that centralized rounding applies correctly across all horizons."""
    custom_data = {
        "Q8v2": [1],
        "Q8v2part2": [2.54321],
        "Q9_mean": [2.3456],
        "Q9_var": [1.2345],
        "Q9_cent50": [2.5],
        "Q9_iqr": [1.5],
        "Q9_probdeflation": [0.05],
        "Q9bv2": [2],
        "Q9bv2part2": [1.54321],
        "Q9c_mean": [1.2345],
        "Q9c_var": [0.8765],
        "Q9c_cent50": [1.0],
        "Q9c_iqr": [0.5],
        "Q9c_probdeflation": [0.12],
        "Q1a": [2],
        "Q1apart2": [0.84321],
        "Q9new2_cent25": [0.1],
        "Q9new2_cent50": [0.5],
        "Q9new2_cent75": [1.2],
        "Q9new2_iqr": [1.1],
        "Q9new2_mean": [0.6],
        "Q9new2_probdeflation": [0.154321],
        "Q9new2_var": [0.4],
    }
    df_raw = _make_dummy_sce_df(custom_data)

    _, df_extract = process_sce(df_raw, decimals_percent=decimals_percent)

    idx = (10001, 202401)
    assert df_extract.loc[idx, "infl_1y"] == expected_1y
    assert df_extract.loc[idx, "infl_1y_bin_mean"] == expected_1y_mean
    assert df_extract.loc[idx, "infl_3y"] == expected_3y
    assert df_extract.loc[idx, "infl_5y_bin_prob_defl"] == expected_5y_prob


def test_house_price_extract_uses_normalized_full_value() -> None:
    """Verify full and extract house-price changes share sign normalization."""
    df_raw = _make_dummy_sce_df(
        {
            "Q31v2": [3],
            "Q31v2part2": [2.5],
        }
    )

    df_full, df_extract = process_sce(df_raw)

    idx = (10001, 202401)
    assert df_full.loc[idx, "Q31v2part2"] == -2.5
    assert df_extract.loc[idx, "house_price_change"] == -2.5
