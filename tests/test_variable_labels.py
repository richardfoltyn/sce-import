"""Tests for variable and value label metadata on processed SCE outputs."""

import numpy as np
import pandas as pd
from pandas.io.stata import StataReader
import pytest

from main import apply_metadata, process_data
from SCE.annotations import VALUE_LABELS, VARIABLE_LABELS, VARIABLE_LABELS_FULL


def _raw_fixture() -> pd.DataFrame:
    """Return one raw observation covering every production processing block."""
    scalar_columns = [
        "Q1",
        "Q2",
        "Q3",
        "Q4new",
        "Q5new",
        "Q6new",
        "Q8v2",
        "Q8v2part2",
        "Q9_mean",
        "Q9_var",
        "Q9_cent50",
        "Q9_iqr",
        "Q9_probdeflation",
        "Q9bv2",
        "Q9bv2part2",
        "Q9c_mean",
        "Q9c_var",
        "Q9c_cent50",
        "Q9c_iqr",
        "Q9c_probdeflation",
        "Q1a",
        "Q1apart2",
        "Q9new2_cent25",
        "Q9new2_cent50",
        "Q9new2_cent75",
        "Q9new2_iqr",
        "Q9new2_mean",
        "Q9new2_probdeflation",
        "Q9new2_var",
        "Q11",
        "Q12new",
        "Q13new",
        "Q14new",
        "Q15",
        "Q16",
        "Q17new",
        "Q18new",
        "Q19",
        "Q20new",
        "Q21new",
        "Q22new",
        "Q23v2",
        "Q23v2part2",
        "Q25v2",
        "Q25v2part2",
        "Q26v2",
        "Q26v2part2",
        "Q27v2",
        "Q27v2part2",
        "Q28",
        "Q29",
        "Q30new",
        "Q31v2",
        "Q31v2part2",
        "C2",
        "C2part2",
        "C3",
        "C3part2",
        "QNUM1",
        "QNUM2",
        "QNUM3",
        "QNUM5",
        "QNUM6",
        "QNUM8",
        "QNUM9",
        "Q32",
        "Q33",
        "Q34",
        "Q36",
        "Q37",
        "Q38",
        "Q41",
        "Q42",
        "Q43",
        "Q44",
        "Q45b",
        "Q46",
        "QRA1",
        "QRA2",
        "Q47",
        "D1",
        "D3",
        "DSAME",
        "DQ38",
        "D6",
    ]
    data: dict[str, list[object]] = {name: [np.nan] for name in scalar_columns}
    data.update(
        {
            "userid": [101],
            "date": [202401],
            "survey_date": [pd.Timestamp("2024-01-01")],
            "tenure": [1],
            "weight": [0.5],
            "Q1": [3],
            "Q2": [3],
            "Q32": [40],
            "Q33": [1],
            "Q34": [2],
            "Q36": [5],
            "Q38": [2],
            "Q43": [2],
            "Q47": [1],
        }
    )

    for prefix in ("Q9", "Q9c", "Q9new2", "Q24", "C1"):
        for code in range(1, 11):
            data[f"{prefix}_bin{code}"] = [10.0]

    for prefix in ("Q24", "C1"):
        for suffix in (
            "cent25",
            "cent50",
            "cent75",
            "iqr",
            "mean",
            "probdeflation",
            "var",
        ):
            data[f"{prefix}_{suffix}"] = [0.0]

    for code in range(1, 11):
        data[f"Q10_{code}"] = [0]
    for code in range(1, 7):
        data[f"Q35_{code}"] = [0]
    for code in range(1, 12):
        data[f"HH2_{code}"] = [0]
        data[f"DHH2_{code}"] = [np.nan]
    for code in range(1, 10):
        data[f"Q45new_{code}"] = [0]
        data[f"D2new_{code}"] = [np.nan]

    return pd.DataFrame(data)


@pytest.fixture(scope="module")
def processed_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return metadata-bearing outputs from the production processing path."""
    df_ranks = pd.DataFrame({"year": [2023], "ibin": [1], "rank": [0.1]})
    df_full, df_extract = process_data(_raw_fixture(), df_ranks)
    df_full = apply_metadata(
        df_full,
        VARIABLE_LABELS_FULL,
        VALUE_LABELS,
        output_name="full",
    )
    df_extract = apply_metadata(
        df_extract,
        VARIABLE_LABELS,
        VALUE_LABELS,
        output_name="extract",
    )
    return df_full, df_extract


def _output_names(df: pd.DataFrame) -> set[str]:
    """Return data and named-index fields written to Stata."""
    return {str(name) for name in df.columns} | {
        str(name) for name in df.index.names if name is not None
    }


def test_processed_outputs_have_complete_variable_metadata(
    processed_outputs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Production full and extract outputs must attach one label per field."""
    for df in processed_outputs:
        assert set(df.attrs["variable_labels"]) == _output_names(df)


def test_full_output_generated_family_labels_are_applied(
    processed_outputs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Retained source families, including optional fields, receive useful labels."""
    df_full, _ = processed_outputs
    labels = df_full.attrs["variable_labels"]

    assert labels["Q9_bin1"] == "1y inflation rate: P(+12% or more)"
    assert labels["Q9new2_probdeflation"].endswith("Probability of a negative change")
    assert "Permanently disabled" in labels["Q10_6"]
    assert "Black or African American" in labels["Q35_2"]
    assert "Self-employed" in labels["HH2_3"]
    assert labels["Q45new_2"] == "HH composition: Children age 25 or older"
    assert labels["D1"] == "Current HH same as at last survey?"


def test_applied_metadata_contains_no_phantom_keys(
    processed_outputs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Only labels for fields in the corresponding output may be attached."""
    df_full, df_extract = processed_outputs

    assert "financial_past_12m" not in df_full.attrs["variable_labels"]
    assert "Q1" not in df_extract.attrs["variable_labels"]
    assert set(df_full.attrs["value_labels"]) <= set(df_full.columns)
    assert set(df_extract.attrs["value_labels"]) <= set(df_extract.columns)


def test_metadata_application_rejects_unlabeled_output_field() -> None:
    """Schema drift must fail before an unlabeled field reaches an export."""
    index = pd.MultiIndex.from_tuples([(1, 202401)], names=["userid", "wid"])
    df = pd.DataFrame(
        {"date": [pd.Timestamp("2024-01-01")], "new_field": [1]}, index=index
    )

    with pytest.raises(
        ValueError,
        match=r"extract output fields without labels: new_field",
    ):
        apply_metadata(
            df,
            VARIABLE_LABELS,
            VALUE_LABELS,
            output_name="extract",
        )


def test_hh_changed_label_has_correct_direction() -> None:
    """The derived field label must describe one as a household change."""
    label = VARIABLE_LABELS["hh_changed"]
    assert "unchaged" not in label.lower()
    assert "changed" in label.lower()


def test_extract_metadata_roundtrips_through_stata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Extract variable and value labels survive a Stata round-trip."""
    index = pd.MultiIndex.from_tuples(
        [(101, 202401), (102, 202401)], names=["userid", "wid"]
    )
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "hh_inc_bin": pd.array([3, 6], dtype="Int8"),
            "female": pd.array([1, 0], dtype="Int8"),
        },
        index=index,
    )
    df = apply_metadata(
        df,
        VARIABLE_LABELS,
        VALUE_LABELS,
        output_name="extract",
    )
    value_labels: dict[str, dict[float, str]] = {
        name: {float(code): label for code, label in labels.items()}
        for name, labels in df.attrs["value_labels"].items()
    }

    stata_path = tmp_path / "extract.dta"
    df.to_stata(
        stata_path,
        convert_dates={"date": "td"},
        version=118,
        write_index=True,
        variable_labels=df.attrs["variable_labels"],
        value_labels=value_labels,
    )

    with StataReader(stata_path) as reader:
        written_var = reader.variable_labels()
        written_val = reader.value_labels()

    assert written_var["hh_inc_bin"] == VARIABLE_LABELS["hh_inc_bin"]
    assert written_var["female"] == VARIABLE_LABELS["female"]
    assert written_var["userid"] == VARIABLE_LABELS["userid"]
    assert written_val["hh_inc_bin"][3] == "$20,000 to $29,999"
    assert written_val["female"] == {0: "No", 1: "Yes"}


def test_full_metadata_roundtrips_through_stata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Generated full-output variable and value labels survive a Stata round-trip."""
    index = pd.MultiIndex.from_tuples(
        [(101, 202401), (102, 202401)], names=["userid", "wid"]
    )
    df = pd.DataFrame(
        {
            "Q10_6": pd.array([1, 0], dtype="Int8"),
            "Q47": pd.array([3, 6], dtype="Int8"),
        },
        index=index,
    )
    df = apply_metadata(
        df,
        VARIABLE_LABELS_FULL,
        VALUE_LABELS,
        output_name="full",
    )
    value_labels: dict[str, dict[float, str]] = {
        name: {float(code): label for code, label in labels.items()}
        for name, labels in df.attrs["value_labels"].items()
    }

    stata_path = tmp_path / "full.dta"
    df.to_stata(
        stata_path,
        version=118,
        write_index=True,
        variable_labels=df.attrs["variable_labels"],
        value_labels=value_labels,
    )

    with StataReader(stata_path) as reader:
        written_var = reader.variable_labels()
        written_val = reader.value_labels()

    assert written_var["Q10_6"] == VARIABLE_LABELS_FULL["Q10_6"]
    assert written_val["Q10_6"] == {0: "No", 1: "Yes"}
    assert written_val["Q47"][6] == "$50,000 to $59,999"


def test_metadata_roundtrips_through_pickle(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Pickle preserves attached full-output variable and value metadata."""
    index = pd.MultiIndex.from_tuples([(1, 202401)], names=["userid", "wid"])
    df = pd.DataFrame({"Q47": pd.array([1], dtype="Int8")}, index=index)
    original = df.copy(deep=True)
    df = apply_metadata(
        df,
        VARIABLE_LABELS_FULL,
        VALUE_LABELS,
        output_name="full",
    )

    pickle_path = tmp_path / "full.pkl.zst"
    df.to_pickle(pickle_path, protocol=5)
    restored = pd.read_pickle(pickle_path)

    assert restored.attrs == df.attrs
    assert not original.attrs
