"""Tests for authoritative categorical recodes and response-domain cleaning."""

import numpy as np
import pandas as pd
import pytest

from SCE.codings import (
    COLLEGE_RECODE,
    COUPLE_RECODE,
    FEMALE_RECODE,
    HISPANIC_RECODE,
    OWNER_RECODE,
)
from SCE.enums import (
    EducationEnum,
    GenderEnum,
    ResidenceOwnershipEnum,
    YesNoEnum,
)
from SCE.importer import (
    AGE_MAX,
    AGE_MIN,
    _process_demographics,
    clean_age,
    recode_binary_response,
)


def _demographics_frame(**responses: float) -> pd.DataFrame:
    """Create one initial-interview row for the demographics processor."""
    index = pd.MultiIndex.from_tuples([(101, 202401)], names=["userid", "wid"])
    data: dict[str, list[float]] = {
        "Q32": [40.0],
        "Q33": [np.nan],
        "Q34": [np.nan],
        "Q36": [np.nan],
        "Q37": [np.nan],
        **{f"Q35_{code}": [0.0] for code in range(1, 7)},
    }
    for name, value in responses.items():
        data[name] = [value]
    return pd.DataFrame(data, index=index)


@pytest.mark.parametrize(
    "code,expected",
    [(GenderEnum.FEMALE, 1), (GenderEnum.MALE, 0)],
)
def test_gender_codes_are_applied_by_demographics_processor(
    code: GenderEnum, expected: int
) -> None:
    """Exercise every allowed Q33 code through the production processor."""
    _, result = _process_demographics(_demographics_frame(Q33=float(code)))
    assert result["female"].iloc[0] == expected


@pytest.mark.parametrize(
    "code,expected",
    [(YesNoEnum.YES, 1), (YesNoEnum.NO, 0)],
)
def test_hispanic_codes_are_applied_by_demographics_processor(
    code: YesNoEnum, expected: int
) -> None:
    """Exercise every allowed Q34 code through the production processor."""
    _, result = _process_demographics(_demographics_frame(Q34=float(code)))
    assert result["hispanic"].iloc[0] == expected


@pytest.mark.parametrize(
    "code,expected_college,expected_educ",
    [
        (EducationEnum.LT_HS, 0, 1),
        (EducationEnum.HS, 0, 2),
        (EducationEnum.SOME_COLLEGE, 0, 3),
        (EducationEnum.ASSOCIATE_DEGREE, 0, 3),
        (EducationEnum.BACHELORS_DEGREE, 1, 4),
        (EducationEnum.MASTERS_DEGREE, 1, 4),
        (EducationEnum.DOCTORAL_DEGREE, 1, 4),
        (EducationEnum.PROFESSIONAL_DEGREE, 1, 4),
        (EducationEnum.OTHER, None, None),
    ],
)
def test_education_codes_are_applied_consistently(
    code: EducationEnum,
    expected_college: int | None,
    expected_educ: int | None,
) -> None:
    """Exercise every Q36 code, including unclassifiable Other responses."""
    _, result = _process_demographics(_demographics_frame(Q36=float(code)))

    if expected_college is None:
        assert pd.isna(result["college"].iloc[0])
        assert pd.isna(result["educ"].iloc[0])
    else:
        assert result["college"].iloc[0] == expected_college
        assert result["educ"].iloc[0] == expected_educ


@pytest.mark.parametrize(
    "code,expected",
    [
        (ResidenceOwnershipEnum.OWN, 1),
        (ResidenceOwnershipEnum.RENT, 0),
        (ResidenceOwnershipEnum.OTHER, None),
    ],
)
def test_ownership_codes_have_explicit_other_policy(
    code: ResidenceOwnershipEnum, expected: int | None
) -> None:
    """Verify every Q43 code uses the production ownership recode."""
    values = pd.Series([int(code)], dtype="Int8")
    result = recode_binary_response(values, coding=OWNER_RECODE)
    if expected is None:
        assert result.isna().all()
    else:
        assert result.iloc[0] == expected


@pytest.mark.parametrize(
    "code,expected",
    [(YesNoEnum.YES, 1), (YesNoEnum.NO, 0)],
)
def test_couple_codes_use_production_recode(
    code: YesNoEnum, expected: int
) -> None:
    """Verify every Q38/DQ38 code uses the production couple recode."""
    values = pd.Series([int(code)], dtype="Int8")
    result = recode_binary_response(values, coding=COUPLE_RECODE)
    assert result.iloc[0] == expected


def test_binary_recodes_cover_their_complete_source_domains() -> None:
    """Ensure authoritative recodes explicitly classify every allowed code."""
    assert FEMALE_RECODE.source_codes == frozenset(map(int, GenderEnum))
    assert HISPANIC_RECODE.source_codes == frozenset(map(int, YesNoEnum))
    assert COUPLE_RECODE.source_codes == frozenset(map(int, YesNoEnum))
    assert COLLEGE_RECODE.source_codes == frozenset(map(int, EducationEnum))
    assert OWNER_RECODE.source_codes == frozenset(map(int, ResidenceOwnershipEnum))


def test_missing_categorical_responses_remain_missing() -> None:
    """Verify source missingness survives all demographic recodes."""
    _, result = _process_demographics(_demographics_frame())
    assert result[["female", "hispanic", "college", "educ"]].isna().all().all()


# ---------------------------------------------------------------------------
# clean_age() — age bounds and missing handling
# ---------------------------------------------------------------------------


def test_clean_age_valid_range_preserved() -> None:
    """Ages within [AGE_MIN, AGE_MAX] are not modified."""
    ages = [AGE_MIN, 35, 55, AGE_MAX]
    values = pd.Series(ages, dtype="Float64")
    result = clean_age(values)
    pd.testing.assert_series_equal(result, values)


@pytest.mark.parametrize("bad_age", [0, 3, 4, 17, AGE_MAX + 1, 511])
def test_clean_age_out_of_domain_set_to_missing(bad_age: int) -> None:
    """Out-of-domain ages are replaced with missing."""
    values = pd.Series([bad_age], dtype="Float64")
    result = clean_age(values)
    assert result.isna().all(), f"Expected NA for age {bad_age}, got {result.iloc[0]}"


def test_clean_age_boundary_values_kept() -> None:
    """Boundary values AGE_MIN and AGE_MAX are not cleared."""
    values = pd.Series([AGE_MIN, AGE_MAX], dtype="Float64")
    result = clean_age(values)
    assert result.notna().all()


def test_clean_age_missing_passthrough() -> None:
    """Pre-existing missing values are not disturbed."""
    values = pd.Series([pd.NA, 30, pd.NA], dtype="Float64")
    result = clean_age(values)
    assert result.isna().iloc[0]
    assert result.iloc[1] == 30
    assert result.isna().iloc[2]


def test_clean_age_returns_copy() -> None:
    """The cleaner must not mutate the input Series."""
    values = pd.Series([0, 25, 511], dtype="Float64")
    original = values.copy()
    clean_age(values)
    pd.testing.assert_series_equal(values, original)


def test_clean_age_mixed_valid_and_invalid() -> None:
    """Only invalid entries are cleared; valid entries survive unchanged."""
    values = pd.Series([0, 25, 511, 70, np.nan], dtype="Float64")
    result = clean_age(values)
    expected = pd.Series([np.nan, 25, np.nan, 70, np.nan], dtype="Float64")
    pd.testing.assert_series_equal(result, expected)
