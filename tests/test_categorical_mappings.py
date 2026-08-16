"""Tests for categorical mappings and response-domain cleaning (SCE-013)."""

import numpy as np
import pandas as pd
import pytest

from SCE.importer import AGE_MAX, AGE_MIN, clean_age

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map(s: pd.Series, mapping: dict) -> pd.Series:
    """Apply a mapping dict with na_action='ignore', matching importer logic."""
    return s.map(mapping, na_action="ignore")


# ---------------------------------------------------------------------------
# Q12new → self_employed: (1) Work for someone else, (2) Self-employed
# ---------------------------------------------------------------------------


def test_self_employed_for_someone_else() -> None:
    """Code 1 maps to 0 (not self-employed)."""
    s = pd.Series([1], dtype="Float64")
    result = _map(s, {1: 0, 2: 1})
    assert result.iloc[0] == 0


def test_self_employed_self_employed() -> None:
    """Code 2 maps to 1 (self-employed)."""
    s = pd.Series([2], dtype="Float64")
    result = _map(s, {1: 0, 2: 1})
    assert result.iloc[0] == 1


def test_self_employed_missing_passthrough() -> None:
    """Missing responses remain missing (na_action='ignore')."""
    s = pd.Series([pd.NA], dtype="Float64")
    result = _map(s, {1: 0, 2: 1})
    assert result.isna().all()


# ---------------------------------------------------------------------------
# Q33 → female: (1) Female, (2) Male
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,expected", [(1, 1), (2, 0)])
def test_female_mapping(code: int, expected: int) -> None:
    """Each Q33 code maps to the correct binary indicator."""
    s = pd.Series([code], dtype="Float64")
    result = _map(s, {1: 1, 2: 0})
    assert result.iloc[0] == expected


def test_female_missing_passthrough() -> None:
    s = pd.Series([pd.NA], dtype="Float64")
    assert _map(s, {1: 1, 2: 0}).isna().all()


# ---------------------------------------------------------------------------
# Q34 → hispanic: (1) Yes, (2) No
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,expected", [(1, 1), (2, 0)])
def test_hispanic_mapping(code: int, expected: int) -> None:
    """Each Q34 code maps to the correct binary indicator."""
    s = pd.Series([code], dtype="Float64")
    result = _map(s, {1: 1, 2: 0})
    assert result.iloc[0] == expected


def test_hispanic_missing_passthrough() -> None:
    s = pd.Series([pd.NA], dtype="Float64")
    assert _map(s, {1: 1, 2: 0}).isna().all()


# ---------------------------------------------------------------------------
# Q38/DQ38 → couple: (1) Yes, (2) No
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,expected", [(1, 1), (2, 0)])
def test_couple_mapping(code: int, expected: int) -> None:
    """Each Q38 code maps to the correct binary indicator."""
    s = pd.Series([code], dtype="Float64")
    result = _map(s, {1: 1, 2: 0})
    assert result.iloc[0] == expected


def test_couple_missing_passthrough() -> None:
    s = pd.Series([pd.NA], dtype="Float64")
    assert _map(s, {1: 1, 2: 0}).isna().all()


# ---------------------------------------------------------------------------
# Q43 → owner: (1) Own→1, (2) Rent→0, (3) Other→missing
# ---------------------------------------------------------------------------


def test_owner_own() -> None:
    """Code 1 (Own) maps to 1."""
    s = pd.Series([1], dtype="Float64")
    assert _map(s, {1: 1, 2: 0}).iloc[0] == 1


def test_owner_rent() -> None:
    """Code 2 (Rent) maps to 0."""
    s = pd.Series([2], dtype="Float64")
    assert _map(s, {1: 1, 2: 0}).iloc[0] == 0


def test_owner_other_is_missing() -> None:
    """Code 3 (Other) must be missing, not 0.

    'Other (please specify)' is an unknown arrangement; treating it as renting
    would be incorrect.
    """
    s = pd.Series([3], dtype="Float64")
    # Code 3 is intentionally absent from the mapping so it falls through
    # to NaN via na_action='ignore'.
    result = _map(s, {1: 1, 2: 0})
    assert result.isna().all()


def test_owner_missing_passthrough() -> None:
    s = pd.Series([pd.NA], dtype="Float64")
    assert _map(s, {1: 1, 2: 0}).isna().all()


# ---------------------------------------------------------------------------
# Q36 → college (binary) and educ (4-category)
# ---------------------------------------------------------------------------

# Mapping constants mirroring importer.py
_COLLEGE_MAP = {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 1, 8: 1}
_EDUC_MAP = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4, 7: 4, 8: 4}


@pytest.mark.parametrize(
    "code,expected_college,expected_educ",
    [
        (1, 0, 1),  # Less than high school → non-college, LT HS
        (2, 0, 2),  # High school diploma → non-college, HS
        (3, 0, 3),  # Some college no degree → non-college, some college
        (4, 0, 3),  # Associate's degree → non-college, some college
        (5, 1, 4),  # Bachelor's → college, college degree
        (6, 1, 4),  # Master's → college, college degree
        (7, 1, 4),  # Doctoral → college, college degree
        (8, 1, 4),  # Professional → college, college degree
    ],
)
def test_education_mapping(
    code: int, expected_college: int, expected_educ: int
) -> None:
    """Every valid Q36 code maps consistently in both derived variables."""
    s = pd.Series([code], dtype="Float64")
    assert _map(s, _COLLEGE_MAP).iloc[0] == expected_college
    assert _map(s, _EDUC_MAP).iloc[0] == expected_educ


def test_education_code9_college_is_missing() -> None:
    """Code 9 (Other) yields missing in 'college', not 0.

    The respondent's actual qualification is unknown; treating it as
    non-college would misclassify the observation.
    """
    s = pd.Series([9], dtype="Float64")
    result = _map(s, _COLLEGE_MAP)
    assert result.isna().all()


def test_education_code9_educ_is_missing() -> None:
    """Code 9 (Other) yields missing in 'educ'."""
    s = pd.Series([9], dtype="Float64")
    result = _map(s, _EDUC_MAP)
    assert result.isna().all()


def test_education_missing_passthrough() -> None:
    """Missing Q36 responses remain missing in both derived columns."""
    s = pd.Series([pd.NA], dtype="Float64")
    assert _map(s, _COLLEGE_MAP).isna().all()
    assert _map(s, _EDUC_MAP).isna().all()


# ---------------------------------------------------------------------------
# clean_age() — age bounds and missing handling
# ---------------------------------------------------------------------------


def test_clean_age_valid_range_preserved() -> None:
    """Ages within [AGE_MIN, AGE_MAX] are not modified."""
    ages = [AGE_MIN, 35, 55, AGE_MAX]
    s = pd.Series(ages, dtype="Float64")
    result = clean_age(s)
    pd.testing.assert_series_equal(result, s)


@pytest.mark.parametrize("bad_age", [0, 3, 4, 17, AGE_MAX + 1, 511])
def test_clean_age_out_of_domain_set_to_missing(bad_age: int) -> None:
    """Out-of-domain ages are replaced with missing."""
    s = pd.Series([bad_age], dtype="Float64")
    result = clean_age(s)
    assert result.isna().all(), f"Expected NA for age {bad_age}, got {result.iloc[0]}"


def test_clean_age_boundary_values_kept() -> None:
    """Boundary values AGE_MIN and AGE_MAX are not cleared."""
    s = pd.Series([AGE_MIN, AGE_MAX], dtype="Float64")
    result = clean_age(s)
    assert result.notna().all()


def test_clean_age_missing_passthrough() -> None:
    """Pre-existing missing values are not disturbed."""
    s = pd.Series([pd.NA, 30, pd.NA], dtype="Float64")
    result = clean_age(s)
    assert result.isna().iloc[0]
    assert result.iloc[1] == 30
    assert result.isna().iloc[2]


def test_clean_age_returns_copy() -> None:
    """clean_age() must not mutate the input Series."""
    s = pd.Series([0, 25, 511], dtype="Float64")
    original = s.copy()
    clean_age(s)
    pd.testing.assert_series_equal(s, original)


def test_clean_age_mixed_valid_and_invalid() -> None:
    """Only invalid entries are cleared; valid entries survive unchanged."""
    s = pd.Series([0, 25, 511, 70, np.nan], dtype="Float64")
    result = clean_age(s)
    assert result.isna().iloc[0]   # 0 → missing
    assert result.iloc[1] == 25    # valid
    assert result.isna().iloc[2]   # 511 → missing
    assert result.iloc[3] == 70    # valid
    assert result.isna().iloc[4]   # already missing
