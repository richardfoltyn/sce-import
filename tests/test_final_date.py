"""Regression fixtures for the inclusive SCE final-date cutoff."""

from argparse import ArgumentParser
import datetime

import pandas as pd
import pytest

from env import EnvConfig
import main as main_module
from main import process_data, restrict_to_final_date


def _processed_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create paired processed frames around a final-date boundary.

    Returns
    -------
    df_full
        Synthetic full SCE data.
    df_extract
        Synthetic SCE extract with the same panel index and dates.
    """
    index = pd.MultiIndex.from_tuples(
        [(101, 1), (101, 2), (202, 1)], names=["userid", "wid"]
    )
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    df_full = pd.DataFrame({"date": dates, "Q47": [1, 2, 3]}, index=index)
    df_extract = pd.DataFrame(
        {"date": dates, "hh_inc_bin": [1, 2, 3]}, index=index
    )
    return df_full, df_extract


@pytest.mark.parametrize(
    "cutoff",
    [datetime.date(2024, 1, 2), pd.Timestamp("2024-01-02 23:59:00")],
    ids=["date", "timestamp"],
)
def test_final_date_is_inclusive(
    cutoff: datetime.date | pd.Timestamp,
) -> None:
    """Verify date and Timestamp cutoffs retain observations on the end date."""
    df_full, df_extract = _processed_frames()

    full_filtered, extract_filtered = restrict_to_final_date(
        df_full, df_extract, cutoff
    )

    expected_index = df_full.index[:2]
    pd.testing.assert_index_equal(full_filtered.index, expected_index)
    pd.testing.assert_index_equal(extract_filtered.index, expected_index)


def test_process_data_filters_before_income_rank_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify observations after the cutoff never reach either ACS merge."""
    processed_full, processed_extract = _processed_frames()
    merge_dates: list[pd.Series] = []

    def fake_process_sce(
        _df_orig: pd.DataFrame,
        decimals_percent: int | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return synthetic processed frames without loading raw SCE data."""
        return processed_full.copy(), processed_extract.copy()

    def fake_merge_inc_rank(
        df: pd.DataFrame,
        varname_inc_bin: str,
        _df_ranks: pd.DataFrame,
    ) -> pd.Series:
        """Record dates presented to a synthetic ACS rank merge."""
        merge_dates.append(df["date"].copy())
        return pd.Series(50.0, index=df.index, name=f"{varname_inc_bin}_rank")

    monkeypatch.setattr(main_module, "process_sce", fake_process_sce)
    monkeypatch.setattr(main_module, "merge_inc_rank", fake_merge_inc_rank)

    df_full, df_extract = process_data(
        pd.DataFrame(),
        pd.DataFrame({"year": [2024]}),
        final_date=datetime.date(2024, 1, 2),
    )

    assert len(merge_dates) == 2
    assert all(dates.max() <= pd.Timestamp("2024-01-02") for dates in merge_dates)
    pd.testing.assert_index_equal(df_full.index, df_extract.index)
    assert len(df_full) == 2


def test_final_date_cli_accepts_iso_date() -> None:
    """Verify the CLI converts a valid ISO date to a calendar date."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)

    args = parser.parse_args(["--final-date", "2024-10-01"])

    assert args.final_date == datetime.date(2024, 10, 1)


def test_final_date_cli_rejects_invalid_date(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify malformed CLI dates fail with a concise format instruction."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)

    with pytest.raises(SystemExit):
        parser.parse_args(["--final-date", "2024-02-30"])

    assert "invalid date '2024-02-30'; expected YYYY-MM-DD" in capsys.readouterr().err
