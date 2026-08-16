"""
Tests for SCE-014: variable and value label metadata.

Covers:
- Complete coverage of the extract schema (no unlabeled columns, no phantom keys).
- Corrected ``hh_changed`` label direction and spelling.
- Stata roundtrip: variable and value labels survive a write/read cycle.
- ``apply_metadata`` stores filtered labels in ``DataFrame.attrs``.

Author: Richard Foltyn
"""

import pandas as pd
from pandas.io.stata import StataReader

from SCE.annotations import VALUE_LABELS, VARIABLE_LABELS, check_label_coverage

# ---------------------------------------------------------------------------
# Expected extract schema
# ---------------------------------------------------------------------------

# Full extract column schema including the optional 5-year density summaries
# and the ACS income rank column added by merge_inc_rank. This serves as a
# regression fixture: any addition or removal must be intentional.
EXTRACT_COLUMNS: frozenset[str] = frozenset(
    {
        "tenure",
        "weight",
        "date",
        "financial_past_12m",
        "financial_12m",
        "prob_move_house",
        "prob_unrate_up",
        "prob_irate_up",
        "prob_stocks_up",
        "infl_1y",
        "infl_1y_bin_mean",
        "infl_1y_bin_var",
        "infl_1y_bin_median",
        "infl_1y_bin_iqr",
        "infl_1y_bin_prob_defl",
        "infl_3y",
        "infl_3y_bin_mean",
        "infl_3y_bin_var",
        "infl_3y_bin_median",
        "infl_3y_bin_iqr",
        "infl_3y_bin_prob_defl",
        "infl_5y",
        "infl_5y_bin_mean",
        "infl_5y_bin_var",
        "infl_5y_bin_median",
        "infl_5y_bin_iqr",
        "infl_5y_bin_prob_defl",
        "working",
        "num_jobs",
        "self_employed",
        "prob_lose_job",
        "prob_leave_job",
        "looking_for_job",
        "prob_accept_job_12m",
        "prob_accept_job_3m",
        "jobless_length",
        "prob_search_job_12m",
        "prob_search_job_3m",
        "earnings_change",
        "hh_inc_change",
        "hh_spending_change",
        "taxes_change",
        "credit_cond_past_12m",
        "credit_cond_12m",
        "prob_miss_paym_3m",
        "house_price_change",
        "house_price_change_3y",
        "govt_debt_change",
        "num_lit_q1",
        "num_lit_q1_correct",
        "num_lit_q2",
        "num_lit_q2_correct",
        "num_lit_q3",
        "num_lit_q3_correct",
        "num_lit_q5",
        "num_lit_q5_correct",
        "num_lit_q6",
        "num_lit_q6_correct",
        "num_lit_q8",
        "num_lit_q8_correct",
        "num_lit_q9",
        "num_lit_q9_correct",
        "age_init",
        "female",
        "hispanic",
        "black",
        "college",
        "educ",
        "owner",
        "num_kids",
        "health",
        "take_fin_risk",
        "hh_changed",
        "same_employer",
        "couple",
        "spouse_working",
        "hh_inc_bin",
        "hh_inc_bin_rank",
    }
)

# Index level names that become columns when to_stata is called with write_index=True
EXTRACT_INDEX_NAMES: frozenset[str] = frozenset({"userid", "wid"})

# Label keys that refer legitimately to full-output-only columns and are not
# expected to appear in the extract schema.
FULL_ONLY_LABELS: frozenset[str] = frozenset({"Q47_rank"})


# ---------------------------------------------------------------------------
# Coverage tests
# ---------------------------------------------------------------------------


def test_every_extract_column_has_a_variable_label() -> None:
    """Every extract column and index level must have exactly one variable label."""
    columns = EXTRACT_COLUMNS | EXTRACT_INDEX_NAMES
    unlabeled, _ = check_label_coverage(columns, VARIABLE_LABELS)
    assert not unlabeled, (
        f"Extract columns without a variable label: {sorted(unlabeled)}"
    )


def test_no_unexpected_phantom_labels() -> None:
    """No label key should refer to a nonexistent extract column (except full-only fields)."""
    columns = EXTRACT_COLUMNS | EXTRACT_INDEX_NAMES
    _, phantom = check_label_coverage(columns, VARIABLE_LABELS)
    unexpected = phantom - FULL_ONLY_LABELS
    assert not unexpected, (
        f"Label keys referring to nonexistent extract columns: {sorted(unexpected)}"
    )


# ---------------------------------------------------------------------------
# hh_changed direction and spelling test
# ---------------------------------------------------------------------------


def test_hh_changed_label_corrects_typo_and_direction() -> None:
    """hh_changed label must say 'changed' and not contain the old misspelling."""
    label = VARIABLE_LABELS["hh_changed"]
    # The old label read "HH unchaged from last survey" — both typo and wrong direction.
    assert "unchaged" not in label.lower(), (
        f"Typo 'unchaged' still present in hh_changed label: {label!r}"
    )
    # The derived field is 1 when the household composition DID change (D1 == 2).
    assert "changed" in label.lower(), (
        f"Label does not convey the correct direction: {label!r}"
    )


# ---------------------------------------------------------------------------
# Stata roundtrip: variable and value labels
# ---------------------------------------------------------------------------


def test_variable_and_value_labels_stata_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Variable and value labels survive a to_stata / StataReader roundtrip."""
    index = pd.MultiIndex.from_tuples(
        [(101, 202401), (102, 202401)], names=["userid", "wid"]
    )
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            # hh_inc_bin: income-bin code from INCOME_CATEGORIES (1-11)
            "hh_inc_bin": pd.array([3, 6], dtype="Int8"),
            # female: binary indicator
            "female": pd.array([1, 0], dtype="Int8"),
        },
        index=index,
    )

    # Build filtered label dicts that match the columns/index levels present.
    all_names = set(df.columns) | {n for n in df.index.names if n is not None}
    var_labels = {k: v for k, v in VARIABLE_LABELS.items() if k in all_names}
    # pandas-stubs declares value_labels keys as float; convert to satisfy ty.
    val_labels: dict[str, dict[float, str]] = {
        k: {float(code): label for code, label in v.items()}
        for k, v in VALUE_LABELS.items()
        if k in df.columns
    }

    stata_path = tmp_path / "fixture.dta"
    df.to_stata(
        stata_path,
        convert_dates={"date": "td"},
        version=118,
        write_index=True,
        variable_labels=var_labels,
        value_labels=val_labels,
    )

    with StataReader(stata_path) as reader:
        written_var = reader.variable_labels()
        written_val = reader.value_labels()

    # Variable labels for columns and index levels
    assert written_var.get("hh_inc_bin") == VARIABLE_LABELS["hh_inc_bin"]
    assert written_var.get("female") == VARIABLE_LABELS["female"]
    assert written_var.get("userid") == VARIABLE_LABELS["userid"]

    # Value labels for the income-bin variable (code 3 = "$20,000 to $29,999")
    hh_val = written_val.get("hh_inc_bin", {})
    assert hh_val.get(3) == "$20,000 to $29,999", (
        f"Unexpected income-bin label for code 3: {hh_val.get(3)!r}"
    )
    assert hh_val.get(6) == "$50,000 to $59,999", (
        f"Unexpected income-bin label for code 6: {hh_val.get(6)!r}"
    )

    # Value labels for the binary female variable (0=No, 1=Yes)
    fem_val = written_val.get("female", {})
    assert fem_val.get(0) == "No", f"Unexpected label for female=0: {fem_val.get(0)!r}"
    assert fem_val.get(1) == "Yes", f"Unexpected label for female=1: {fem_val.get(1)!r}"


# ---------------------------------------------------------------------------
# apply_metadata stores labels in attrs
# ---------------------------------------------------------------------------


def test_apply_metadata_stores_labels_in_attrs() -> None:
    """apply_metadata must populate attrs and filter to present columns/index levels."""
    # Import here so the test does not depend on main.py side effects.
    from main import apply_metadata

    index = pd.MultiIndex.from_tuples([(1, 202401)], names=["userid", "wid"])
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01"]),
            "hh_inc_bin": pd.array([3], dtype="Int8"),
            "female": pd.array([1], dtype="Int8"),
            # Column with no label entry should not appear in the stored dict.
            "_internal": [99.0],
        },
        index=index,
    )

    result = apply_metadata(df, VARIABLE_LABELS, VALUE_LABELS)

    stored_var = result.attrs["variable_labels"]
    stored_val = result.attrs["value_labels"]

    # Index level labels are included (Stata uses them with write_index=True)
    assert "userid" in stored_var
    assert "wid" in stored_var
    # Column labels are included
    assert "hh_inc_bin" in stored_var
    assert "female" in stored_var
    # No phantom key for a column that doesn't exist in this frame
    assert "_internal" not in stored_var
    # Value labels for present columns
    assert "hh_inc_bin" in stored_val
    assert "female" in stored_val
    # Input is not mutated
    assert "variable_labels" not in df.attrs
