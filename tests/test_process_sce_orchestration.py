"""Tests for explicit assembly of the SCE processing blocks."""

from collections.abc import Callable

import pandas as pd
import pytest

import SCE.importer as importer


def _processor(
    name: str,
) -> Callable[..., tuple[pd.DataFrame, pd.DataFrame]]:
    """Return a stub processor with uniquely named output fragments."""

    def process(
        df: pd.DataFrame,
        *_args: object,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        df_full = pd.DataFrame({f"full_{name}": 1.0}, index=df.index)
        df_extract = pd.DataFrame({f"extract_{name}": 2.0}, index=df.index)
        return df_full, df_extract

    return process


def test_process_sce_assembles_explicit_processing_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The orchestrator combines every block without mutating raw input."""
    processor_names = [
        "general_expectations",
        "inflation",
        "labor_market",
        "household_finances",
        "housing_and_macro",
        "financial_literacy",
        "demographics",
        "household_background",
    ]
    for name in processor_names:
        monkeypatch.setattr(importer, f"_process_{name}", _processor(name))

    df_raw = pd.DataFrame(
        {
            "userid": [10],
            "date": [202401],
            "survey_date": pd.to_datetime(["2024-01-01"]),
            "tenure": [1],
            "weight": [0.5],
        }
    )
    original = df_raw.copy(deep=True)

    df_full, df_extract = importer.process_sce(df_raw, decimals_percent=2)

    expected_full = [
        "tenure",
        "weight",
        "date",
        *(f"full_{name}" for name in processor_names),
    ]
    expected_extract = [
        "tenure",
        "weight",
        "date",
        *(f"extract_{name}" for name in processor_names),
    ]
    assert df_full.columns.tolist() == expected_full
    assert df_extract.columns.tolist() == expected_extract
    assert df_full.index.names == ["userid", "wid"]
    assert df_extract.index.equals(df_full.index)
    pd.testing.assert_frame_equal(df_raw, original)
