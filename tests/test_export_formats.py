"""Regression fixtures for selectable export formats (SCE-017)."""

from argparse import ArgumentParser

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from env import EXPORT_FORMATS, EnvConfig, parse_export_formats
from main import prepare_csv_export

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pickle", {"pickle"}),
        ("stata", {"stata"}),
        ("pickle,stata", {"pickle", "stata"}),
        ("pickle,stata,excel,csv", {"pickle", "stata", "excel", "csv"}),
        ("CSV,EXCEL", {"csv", "excel"}),  # case-insensitive
        ("pickle , stata , csv", {"pickle", "stata", "csv"}),  # whitespace tolerance
    ],
)
def test_parse_export_formats_valid(raw: str, expected: set[str]) -> None:
    """Verify valid format strings parse to the expected set."""
    assert parse_export_formats(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "pickle,invalid",
        "json",
        "pickle,xml,csv",
    ],
)
def test_parse_export_formats_invalid(raw: str) -> None:
    """Verify unknown format names raise ArgumentTypeError."""
    with pytest.raises(Exception, match="unknown export format"):
        parse_export_formats(raw)


def test_export_formats_constant() -> None:
    """Verify the supported formats frozenset has the expected members."""
    assert frozenset({"pickle", "stata", "excel", "csv"}) == EXPORT_FORMATS


def test_cli_default_formats() -> None:
    """Verify the CLI defaults to pickle-only."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)
    args = parser.parse_args([])
    assert args.formats == {"pickle"}


def test_cli_explicit_formats() -> None:
    """Verify the CLI accepts a comma-separated list."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)
    args = parser.parse_args(["--formats", "pickle,stata,csv"])
    assert args.formats == {"pickle", "stata", "csv"}


def test_cli_invalid_format_fails() -> None:
    """Verify unknown format names fail during argument parsing."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--formats", "pickle,json"])


def test_prepare_csv_export_rounds_only_percentages_and_percentiles() -> None:
    """CSV presentation rounding leaves unrelated values and input untouched."""
    df = pd.DataFrame(
        {
            "prob_move_house": [12.3456, float("nan")],
            "infl_1y": [2.3456, -1.2345],
            "infl_5y_bin_prob_defl": [15.4321, 2.3456],
            "earnings_change": [3.4567, -2.3456],
            "house_price_change_3y": [4.5678, -3.4567],
            "hh_inc_bin_rank": [63.4567, 81.2345],
            "Q47_rank": [62.3456, 80.1234],
            "weight": [0.123456, 0.654321],
            "jobless_length": [1.23456, 7.65432],
        }
    )
    original = df.copy(deep=True)

    result = prepare_csv_export(df, decimals_percent=2)

    assert result["prob_move_house"].tolist()[0] == 12.35
    assert pd.isna(result["prob_move_house"].iloc[1])
    assert result["infl_1y"].tolist() == [2.35, -1.23]
    assert result["infl_5y_bin_prob_defl"].tolist() == [15.43, 2.35]
    assert result["earnings_change"].tolist() == [3.46, -2.35]
    assert result["house_price_change_3y"].tolist() == [4.57, -3.46]
    assert result["hh_inc_bin_rank"].tolist() == [63.46, 81.23]
    assert result["Q47_rank"].tolist() == [62.35, 80.12]
    assert result["weight"].tolist() == original["weight"].tolist()
    assert result["jobless_length"].tolist() == original["jobless_length"].tolist()
    assert_frame_equal(df, original)
