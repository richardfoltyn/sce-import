"""Regression fixtures for carrying ACS income ranks to required SCE years."""

import pandas as pd
import pytest

from SCE.importer import expand_income_rank_years, merge_inc_rank


def _rank_mapping() -> pd.DataFrame:
    """Create a two-bin ACS mapping with one internal missing year.

    Returns
    -------
    pd.DataFrame
        Synthetic rank mappings for 2020 and 2022.
    """
    return pd.DataFrame(
        {
            "year": [2020, 2020, 2022, 2022],
            "ibin": [1, 2, 1, 2],
            "rank": [0.10, 0.80, 0.20, 0.90],
        }
    )


def test_income_ranks_fill_internal_and_future_years_within_bin() -> None:
    """Verify each missing year uses the preceding rank from the same bin."""
    result = expand_income_rank_years(_rank_mapping(), [2020, 2021, 2022, 2023])

    expected = pd.DataFrame(
        {
            "year": [2020, 2020, 2021, 2021, 2022, 2022, 2023, 2023],
            "ibin": [1, 2, 1, 2, 1, 2, 1, 2],
            "rank": [0.10, 0.80, 0.10, 0.80, 0.20, 0.90, 0.20, 0.90],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_income_rank_expansion_rejects_pre_acs_years() -> None:
    """Verify required years before the first ACS mapping are not back-filled."""
    with pytest.raises(ValueError, match="predates the first available ACS rank year"):
        expand_income_rank_years(_rank_mapping(), [2019])


def test_future_complete_mapping_remains_many_to_one_mergeable() -> None:
    """Verify all 11 SCE bins can use the final ACS year in a future year."""
    bins = list(range(1, 12))
    ranks = pd.DataFrame(
        {
            "year": [2024] * 11,
            "ibin": bins,
            "rank": [value / 100 for value in bins],
        }
    )
    index = pd.MultiIndex.from_arrays(
        [[101] * 11, bins], names=["userid", "wid"]
    )
    sce = pd.DataFrame(
        {"date": pd.to_datetime(["2025-07-01"] * 11), "Q47": bins},
        index=index,
    )

    result = merge_inc_rank(sce, "Q47", ranks)

    expected = pd.Series(
        [float(value) for value in bins], index=index, name="Q47_rank"
    )
    pd.testing.assert_series_equal(result, expected, check_exact=False)


def test_merge_requires_rank_coverage_for_reported_income_bins() -> None:
    """Verify an observed SCE bin without an ACS mapping fails explicitly."""
    sce = pd.DataFrame(
        {"date": pd.to_datetime(["2020-07-01"]), "Q47": [3]},
        index=pd.MultiIndex.from_tuples([(101, 1)], names=["userid", "wid"]),
    )

    with pytest.raises(ValueError, match="Income ranks are unavailable"):
        merge_inc_rank(sce, "Q47", _rank_mapping())
