"""Production-path fixtures for employment response codings."""

import numpy as np
import pandas as pd

from SCE.codings import (
    Q10_OTHER_COLUMNS,
    Q10_WORKING_COLUMNS,
    SAME_EMPLOYER_RECODE,
    SELF_EMPLOYED_RECODE,
)
from SCE.enums import EmplStatusEnum, EmplTypeEnum, SameEmployerEnum
from SCE.importer import (
    _process_labor_market,
    any_selected_indicator,
    recode_binary_response,
)


def _labor_market_frame() -> pd.DataFrame:
    """Create one row for every Q10 status plus an all-missing row."""
    index = pd.MultiIndex.from_tuples(
        [*((100 + code, 202401) for code in range(1, 11)), (999, 202401)],
        names=["userid", "wid"],
    )
    statuses = pd.DataFrame(
        0.0,
        index=index,
        columns=[f"Q10_{code}" for code in range(1, 11)],
    )
    for row, code in zip(index[:-1], range(1, 11), strict=True):
        statuses.loc[row, f"Q10_{code}"] = 1.0
    statuses.loc[index[-1], :] = np.nan

    n_rows = len(index)
    other = pd.DataFrame(
        {
            "Q11": [np.nan] * n_rows,
            "Q12new": [1.0, 2.0, *([np.nan] * (n_rows - 2))],
            "Q13new": [np.nan] * n_rows,
            "Q14new": [np.nan] * n_rows,
            "Q15": [1.0, 2.0, *([np.nan] * (n_rows - 2))],
            "Q16": [np.nan] * n_rows,
            "Q17new": [np.nan] * n_rows,
            "Q18new": [np.nan] * n_rows,
            "Q19": [np.nan] * n_rows,
            "Q20new": [np.nan] * n_rows,
            "Q21new": [np.nan] * n_rows,
            "Q22new": [np.nan] * n_rows,
            "Q23v2": [np.nan] * n_rows,
            "Q23v2part2": [np.nan] * n_rows,
        },
        index=index,
    )
    return pd.concat((statuses, other), axis=1)


def test_labor_processor_covers_every_q10_status() -> None:
    """Apply the approved literal-working and Other policies to all Q10 codes."""
    df = _labor_market_frame()

    _, result = _process_labor_market(df)

    expected = pd.Series(
        [1, 1, 0, 0, 0, 0, 0, 0, 0, pd.NA, pd.NA],
        index=df.index,
        dtype="Int8",
        name="working",
    )
    pd.testing.assert_series_equal(result["working"], expected)
    assert {int(code) for code in EmplStatusEnum} == set(range(1, 11))


def test_labor_processor_uses_employment_type_and_job_search_recodes() -> None:
    """Exercise every Q12new and Q15 code through the labor processor."""
    df = _labor_market_frame()

    _, result = _process_labor_market(df)

    expected_self_employed = pd.Series(
        [0, 1, *([pd.NA] * 9)],
        index=df.index,
        dtype="Int8",
        name="self_employed",
    )
    expected_looking = pd.Series(
        [1, 0, *([pd.NA] * 9)],
        index=df.index,
        dtype="Int8",
        name="looking_for_job",
    )
    pd.testing.assert_series_equal(result["self_employed"], expected_self_employed)
    pd.testing.assert_series_equal(result["looking_for_job"], expected_looking)


def test_q10_other_defers_to_an_explicit_known_status() -> None:
    """An Other selection is missing only when no known status is selected."""
    columns = [f"Q10_{code}" for code in range(1, 11)]
    statuses = pd.DataFrame(0.0, index=range(3), columns=columns)
    statuses.loc[0, "Q10_10"] = 1.0
    statuses.loc[1, ["Q10_1", "Q10_10"]] = 1.0
    statuses.loc[2, ["Q10_7", "Q10_10"]] = 1.0

    result = any_selected_indicator(
        statuses,
        selected_columns=Q10_WORKING_COLUMNS,
        unknown_columns=Q10_OTHER_COLUMNS,
    )

    expected = pd.Series([pd.NA, 1, 0], dtype="Int8")
    pd.testing.assert_series_equal(result, expected)


def test_same_employer_covers_every_dsame_code_and_missing() -> None:
    """Treat DSAME Other as unclassifiable rather than a different employer."""
    values = pd.Series([1, 2, 3, 4, 5, pd.NA], dtype="Int8", name="DSAME")

    result = recode_binary_response(values, coding=SAME_EMPLOYER_RECODE)

    expected = pd.Series([1, 1, 0, 0, pd.NA, pd.NA], dtype="Int8", name="DSAME")
    pd.testing.assert_series_equal(result, expected)
    assert SAME_EMPLOYER_RECODE.source_codes == frozenset(map(int, SameEmployerEnum))


def test_employment_type_recode_covers_its_source_enum() -> None:
    """Ensure no Q12new enum member lacks an explicit transformation policy."""
    assert SELF_EMPLOYED_RECODE.source_codes == frozenset(map(int, EmplTypeEnum))
