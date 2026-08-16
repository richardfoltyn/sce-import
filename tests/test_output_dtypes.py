import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from SCE.importer import apply_sce_output_dtypes
from SCE.pandas_helpers import tile_const

NULLABLE_INT8_COLUMNS = {"tenure", "Q33", "Q11", "female", "num_jobs"}
FULL_INT8_COLUMNS = NULLABLE_INT8_COLUMNS
EXTRACT_INT8_COLUMNS = NULLABLE_INT8_COLUMNS


def test_output_dtype_contract_is_stable_and_non_mutating() -> None:
    index = pd.MultiIndex.from_tuples(
        [(1, 1), (1, 2)], names=["userid", "wid"]
    )
    df_full = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "weight": [1, 2],
            "tenure": [1, 16],
            "Q33": [1, np.nan],
            "Q11": [2, np.nan],
            "Q3": [25, np.nan],
        },
        index=index,
    )
    df_extract = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "weight": [1, 2],
            "tenure": [1, 16],
            "female": [1, np.nan],
            "num_jobs": [2, np.nan],
            "prob_move_house": [25, np.nan],
        },
        index=index,
    )
    original_full = df_full.copy(deep=True)
    original_extract = df_extract.copy(deep=True)

    full = apply_sce_output_dtypes(
        df_full,
        int8_columns=FULL_INT8_COLUMNS,
    )
    extract = apply_sce_output_dtypes(
        df_extract,
        int8_columns=EXTRACT_INT8_COLUMNS,
    )

    assert str(full["tenure"].dtype) == "Int8"
    assert str(full["Q33"].dtype) == "Int8"
    assert str(full["Q11"].dtype) == "Int8"
    assert full["Q3"].dtype == np.dtype("float64")
    assert str(extract["tenure"].dtype) == "Int8"
    assert str(extract["female"].dtype) == "Int8"
    assert str(extract["num_jobs"].dtype) == "Int8"
    assert extract["prob_move_house"].dtype == np.dtype("float64")
    assert extract["date"].dtype == np.dtype("datetime64[ns]")
    assert isinstance(extract.index, pd.MultiIndex)
    assert all(level.dtype == np.dtype("int64") for level in extract.index.levels)
    assert_frame_equal(df_full, original_full)
    assert_frame_equal(df_extract, original_extract)

    fully_observed_full = df_full.fillna({"Q33": 2, "Q11": 1, "Q3": 50})
    fully_observed_extract = df_extract.fillna(
        {"female": 0, "num_jobs": 1, "prob_move_house": 50}
    )
    full_observed = apply_sce_output_dtypes(
        fully_observed_full,
        int8_columns=FULL_INT8_COLUMNS,
    )
    extract_observed = apply_sce_output_dtypes(
        fully_observed_extract,
        int8_columns=EXTRACT_INT8_COLUMNS,
    )
    assert full_observed.dtypes.equals(full.dtypes)
    assert extract_observed.dtypes.equals(extract.dtypes)


def test_fractional_category_is_rejected() -> None:
    index = pd.MultiIndex.from_tuples([(1, 1)], names=["userid", "wid"])
    df_full = pd.DataFrame(
        {"date": pd.to_datetime(["2024-01-01"]), "Q33": [1.5]}, index=index
    )
    with pytest.raises(ValueError, match="Q33 contains non-integral values"):
        apply_sce_output_dtypes(
            df_full,
            int8_columns=FULL_INT8_COLUMNS,
        )


def test_out_of_range_category_is_rejected() -> None:
    index = pd.MultiIndex.from_tuples([(1, 1)], names=["userid", "wid"])
    df_full = pd.DataFrame(
        {"date": pd.to_datetime(["2024-01-01"]), "Q33": [128]}, index=index
    )

    with pytest.raises(ValueError, match="Q33 contains values outside the Int8 range"):
        apply_sce_output_dtypes(
            df_full,
            int8_columns=FULL_INT8_COLUMNS,
        )


def test_tile_const_uses_nullable_dtype_without_mutating_input() -> None:
    index = pd.MultiIndex.from_tuples(
        [(1, 1), (1, 2), (2, 1)], names=["userid", "wid"]
    )
    values = pd.Series([1.0, np.nan, np.nan], index=index, name="category")
    original = values.copy(deep=True)

    result = tile_const(values, "userid", "Int8")

    expected = pd.Series([1, 1, pd.NA], index=index, name="category", dtype="Int8")
    assert isinstance(result, pd.Series)
    pd.testing.assert_series_equal(result, expected)
    pd.testing.assert_series_equal(values, original)


def test_nullable_outputs_export_values_and_missingness(tmp_path) -> None:
    index = pd.MultiIndex.from_tuples(
        [(1, 1), (2, 1)], names=["userid", "wid"]
    )
    df_extract = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "female": [1, np.nan],
            "num_jobs": [2, np.nan],
            "prob_move_house": [25.5, np.nan],
        },
        index=index,
    )
    extract = apply_sce_output_dtypes(
        df_extract,
        int8_columns=EXTRACT_INT8_COLUMNS,
    )

    pickle_path = tmp_path / "extract.pkl.zst"
    extract.to_pickle(pickle_path, protocol=5)
    assert_frame_equal(pd.read_pickle(pickle_path), extract)

    stata_path = tmp_path / "extract.dta"
    extract.to_stata(
        stata_path, convert_dates={"date": "td"}, version=118, write_index=True
    )
    stata = pd.read_stata(stata_path)
    assert stata["female"].tolist()[:1] == [1.0]
    assert stata.loc[1, ["female", "num_jobs", "prob_move_house"]].isna().all()
    assert stata["date"].tolist() == list(extract["date"])

    excel_path = tmp_path / "extract.xlsx"
    extract.to_excel(excel_path, index=True)
    excel = pd.read_excel(excel_path, index_col=[0, 1])
    excel_values = excel.loc[
        (1, 1), ["female", "num_jobs", "prob_move_house"]
    ]
    assert isinstance(excel_values, pd.Series)
    assert list(excel_values) == [1.0, 2.0, 25.5]
    assert excel.loc[(2, 1), ["female", "num_jobs", "prob_move_house"]].isna().all()

    csv_path = tmp_path / "extract.csv"
    extract.to_csv(csv_path, index=True)
    csv = pd.read_csv(csv_path, index_col=[0, 1])
    csv_values = csv.loc[(1, 1), ["female", "num_jobs", "prob_move_house"]]
    assert isinstance(csv_values, pd.Series)
    assert list(csv_values) == [1.0, 2.0, 25.5]
    assert csv.loc[(2, 1), ["female", "num_jobs", "prob_move_house"]].isna().all()
