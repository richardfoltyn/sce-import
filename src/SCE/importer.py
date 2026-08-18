"""
Module to import and process SCE survey data.

- Processes raw survey variables and maps them to clean representations.
- Flips signs for variables where decreases were coded as positive.
- Computes correct data types and formats demographic indicators.
- Merges external family income ranks based on ACS data.

Author: Richard Foltyn
"""

from collections.abc import Collection, Iterable
import logging

import numpy as np
import pandas as pd

from SCE.codings import (
    COLLEGE_RECODE,
    COUPLE_RECODE,
    EDUCATION_TO_EDUC4,
    FEMALE_RECODE,
    HISPANIC_RECODE,
    HOUSEHOLD_CHANGED_RECODE,
    OWNER_RECODE,
    Q10_OTHER_COLUMNS,
    Q10_WORKING_COLUMNS,
    SAME_EMPLOYER_RECODE,
    SELF_EMPLOYED_RECODE,
    SPOUSE_OTHER_COLUMNS,
    SPOUSE_WORKING_COLUMNS,
    YES_NO_RECODE,
    BinaryRecode,
)
from SCE.constants import VARNAME_ID, VARNAME_WID
from SCE.datatypes import NULLABLE_INT8_COLUMNS
from SCE.pandas_helpers import merge_if_na, tile_const

LOGGER_NAME: str = "SCE"

# Valid age range for SCE respondents.
# Lower bound: the NY Fed SCE targets adults aged 18 and older.
# Upper bound: 120 is used as a generous sentinel that flags obvious data-entry
# errors (e.g., 511) without encoding a survey design limit the questionnaire
# does not state.
AGE_MIN: int = 18
AGE_MAX: int = 120


def clean_age(s: pd.Series) -> pd.Series:
    """Set implausible age responses to missing and log the count.

    Parameters
    ----------
    s
        Raw age column (``Q32``) from the SCE survey. Only values in
        ``[AGE_MIN, AGE_MAX]`` are kept; everything else is replaced with
        ``pd.NA``.

    Returns
    -------
    Copy of ``s`` with out-of-domain values set to ``pd.NA``.

    Notes
    -----
    The SCE questionnaire (Q32) does not state an explicit upper age bound.
    ``AGE_MAX = 120`` is therefore chosen as an unambiguously impossible
    ceiling rather than a design restriction. ``AGE_MIN = 18`` reflects the
    NY Fed SCE recruitment criterion that all panel members must be adults.
    """
    result = s.copy(deep=True)
    invalid = result.notna() & ((result < AGE_MIN) | (result > AGE_MAX))
    n_invalid = int(invalid.sum())
    if n_invalid:
        logger = logging.getLogger(LOGGER_NAME)
        logger.warning(
            f"Q32 (age): {n_invalid:,d} out-of-domain value(s) outside "
            f"[{AGE_MIN}, {AGE_MAX}] set to missing"
        )
        result = result.where(~invalid)
    return result


def flip_negative(
    s: pd.Series,
    direction: pd.Series,
    *,
    decrease_code: int,
) -> pd.Series:
    """Conservatively normalize an unsigned change Series when its convention is clear.

    Parameters
    ----------
    s
        Values that may contain either unsigned magnitudes or signed changes.
    direction
        Direction responses associated with the values. Missing responses are
        distinct from explicit non-decrease responses.
    decrease_code
        Direction code identifying a decrease or deflation.

    Returns
    -------
    A copy of the values. Explicit decreases are negated only when every
    non-missing value in the Series is nonnegative.

    Notes
    -----
    The source convention can change between survey releases. A Series that
    mixes signed and unsigned values is therefore left entirely unchanged rather
    than normalized row by row. Values with missing direction are always
    preserved, although a negative such value prevents classifying the complete
    Series as uniformly unsigned.
    """
    result = s.copy(deep=True)

    has_value = result.notna()
    has_direction = direction.notna()
    decrease = has_direction & direction.eq(decrease_code)
    non_decrease = has_direction & direction.ne(decrease_code)

    decrease_values = has_value & decrease
    non_decrease_values = has_value & non_decrease
    missing_direction_values = has_value & ~has_direction

    n_decrease = int(decrease_values.sum())
    n_non_decrease = int(non_decrease_values.sum())
    n_missing_direction = int(missing_direction_values.sum())
    counts = (
        f"{n_decrease:,d} decrease, {n_non_decrease:,d} non-decrease, "
        f"{n_missing_direction:,d} missing direction"
    )

    logger = logging.getLogger(LOGGER_NAME)
    name = result.name

    if n_decrease + n_non_decrease == 0:
        logger.info(
            f"No values with observed direction in {name}; leaving unchanged ({counts})"
        )
        return result

    signed = (result.loc[decrease_values] <= 0).all() and (
        result.loc[non_decrease_values] >= 0
    ).all()
    uniformly_unsigned = (result.loc[has_value] >= 0).all()

    if signed:
        logger.info(
            f"Signs in {name} are already normalized; leaving unchanged ({counts})"
        )
    elif uniformly_unsigned:
        n_flipped = int((result.loc[decrease_values] > 0).sum())
        logger.info(
            f"Unsigned sign convention in {name}; flipping {n_flipped:,d} "
            f"explicit decrease values ({counts})"
        )
        result.loc[decrease_values] *= -1
    else:
        positive_decrease = int((result.loc[decrease_values] > 0).sum())
        negative_decrease = int((result.loc[decrease_values] < 0).sum())
        negative_non_decrease = int((result.loc[non_decrease_values] < 0).sum())
        logger.warning(
            f"{name} has mixed or contradictory sign evidence; leaving unchanged "
            f"({counts})"
        )
        logger.warning(
            f"  observed decreases: {positive_decrease:,d} positive and "
            f"{negative_decrease:,d} negative values"
        )
        if negative_non_decrease:
            logger.warning(
                f"  observed non-decreases: {negative_non_decrease:,d} negative values"
            )

    return result


def recode_binary_response(
    values: pd.Series,
    *,
    coding: BinaryRecode,
) -> pd.Series:
    """Apply an authoritative binary recode without losing missingness.

    Parameters
    ----------
    values
        Source responses containing categorical questionnaire codes.
    coding
        Source codes explicitly classified as true, false, or unclassifiable.

    Returns
    -------
    Responses represented as nullable 0/1 integers. Missing source values
    and explicitly unclassifiable codes remain ``pd.NA``.
    """
    result = pd.Series(
        pd.NA,
        index=values.index,
        dtype=pd.Int8Dtype(),
        name=values.name,
    )
    result.loc[values.isin(coding.false_codes)] = 0
    result.loc[values.isin(coding.true_codes)] = 1
    return result


def any_selected_indicator(
    indicators: pd.DataFrame,
    *,
    selected_columns: list[str] | tuple[str, ...] | None = None,
    unknown_columns: tuple[str, ...] = (),
) -> pd.Series:
    """Aggregate selected categories from a multi-response question.

    Parameters
    ----------
    indicators
        Indicator columns for all categories in a multi-response question.
    selected_columns
        Columns whose selection should produce one. If omitted, selection of
        any supplied column produces one.
    unknown_columns
        Unclassifiable categories. A row selecting only one of these categories
        produces missing rather than zero.

    Returns
    -------
    Nullable 0/1 integers. A row is missing when all response indicators
    are missing or only an unclassifiable category is selected. An observed
    row without a selected true category is otherwise zero.
    """
    selected = indicators
    if selected_columns is not None:
        selected = indicators[list(selected_columns)]

    result = selected.eq(1).any(axis=1)
    all_missing = indicators.isna().all(axis=1)

    unknown_only = pd.Series(False, index=indicators.index)
    if unknown_columns:
        unknown_selected = indicators[list(unknown_columns)].eq(1).any(axis=1)
        known = indicators.drop(columns=list(unknown_columns))
        known_selected = known.eq(1).any(axis=1)
        unknown_only = unknown_selected & ~known_selected

    return result.mask(all_missing | unknown_only).astype(pd.Int8Dtype())


def propagate_household_composition(
    initial: pd.DataFrame,
    updates: pd.DataFrame,
    *,
    by: str = VARNAME_ID,
) -> pd.DataFrame:
    """Propagate complete household-composition states within respondents.

    Parameters
    ----------
    initial
        Household-composition responses from initial interviews.
    updates
        Household-composition responses from repeat interviews, with columns
        aligned to ``initial``.
    by
        Name of the respondent index level.

    Returns
    -------
    Household-composition states forward-filled within each respondent.

    Notes
    -----
    A composition response is treated as an atomic state and is used only when
    all components are observed. Complete repeat-interview responses take
    precedence when both sources are present on the same row.
    """
    initial_complete = initial.notna().all(axis=1)
    update_complete = updates.notna().all(axis=1)

    composition = initial.copy(deep=True)
    composition.loc[~initial_complete, :] = np.nan
    composition.loc[update_complete, :] = updates.loc[update_complete, :]

    return composition.groupby(level=by, sort=False).ffill()


def apply_sce_output_dtypes(
    df: pd.DataFrame,
    *,
    int8_columns: Collection[str],
) -> pd.DataFrame:
    """Apply the stable dtype contract to one processed SCE output.

    Parameters
    ----------
    df
        Processed SCE data to cast.
    int8_columns
        Columns containing nullable categorical, binary, or small count values.

    Returns
    -------
    Copy of the data with stable output dtypes.

    Notes
    -----
    Columns not identified as dates, categorical codes, or integral counts are
    represented as ``float64``. This includes weights, probabilities,
    percentages, ranks, durations that admit fractional responses, and other
    measured quantities.
    """
    result = df.copy(deep=True)
    index = result.index.to_frame(index=False).astype(
        {VARNAME_ID: "int64", VARNAME_WID: "int64"}
    )
    result.index = pd.MultiIndex.from_frame(index)

    dtypes: dict[str, str] = dict.fromkeys(result.columns, "float64")
    dtypes["date"] = "datetime64[ns]"

    int8_info = np.iinfo(np.int8)
    for name in int8_columns:
        if name not in result.columns:
            continue
        observed = result[name].dropna()
        if observed.mod(1).ne(0).any():
            raise ValueError(f"Column {name} contains non-integral values")
        if observed.lt(int8_info.min).any() or observed.gt(int8_info.max).any():
            raise ValueError(
                f"Column {name} contains values outside the Int8 range "
                f"[{int8_info.min}, {int8_info.max}]"
            )
        dtypes[name] = "Int8"

    return result.astype(dtypes)


def _process_general_expectations(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process general financial and economic expectations (Q1--Q6)."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # Financially better or worse off than 12 months ago?
    df_full["Q1"] = df["Q1"].fillna(-1).astype(np.int8)
    df_extract["financial_past_12m"] = df_full["Q1"]

    # Financially better or worse off in 12 months?
    df_full["Q2"] = df["Q2"].fillna(-1).astype(np.int8)
    df_extract["financial_12m"] = df_full["Q2"]

    # percent change to move primary residence in next 12 months?
    df_full["Q3"] = df["Q3"]
    df_extract["prob_move_house"] = df_full["Q3"]

    # % chance that unemployment will be higher 12 months from now?
    df_full["Q4new"] = df["Q4new"]
    df_extract["prob_unrate_up"] = df_full["Q4new"]

    # % chance that interest rates on savings will be higher 12 months from now?
    df_full["Q5new"] = df["Q5new"]
    df_extract["prob_irate_up"] = df_full["Q5new"]

    # % chance that stock prices will be higher 12 months from now?
    df_full["Q6new"] = df["Q6new"]
    df_extract["prob_stocks_up"] = df_full["Q6new"]

    return df_full, df_extract


def _process_inflation(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process inflation point forecasts and density summaries."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # --- Inflation ---

    # Merge questions Q8v2 and Q8v2part2
    varname = "Q8v2part2"
    df_full[varname] = df[varname]
    # Check that sign was flipped in Q8v2part2 (direction: 1=increase, 2=decrease)
    df_full[varname] = flip_negative(df_full[varname], df["Q8v2"], decrease_code=2)

    df_extract["infl_1y"] = df_full[varname]

    # Q9: inflation forecast bins.
    columns = [f"Q9_bin{i}" for i in range(1, 11)]
    df_full[columns] = df[columns]

    df_extract["infl_1y_bin_mean"] = df["Q9_mean"]
    df_extract["infl_1y_bin_var"] = df["Q9_var"]
    df_extract["infl_1y_bin_median"] = df["Q9_cent50"]
    df_extract["infl_1y_bin_iqr"] = df["Q9_iqr"]
    # Rescale to [0, 100] to be in line with all other prob responses
    df_extract["infl_1y_bin_prob_defl"] = df["Q9_probdeflation"] * 100.0

    # --- Q9b: Inflation/deflation between 24-36 months from now ---
    # Merge questions Q9bv2 and Q9bv2part2
    varname = "Q9bv2part2"
    df_full[varname] = df[varname]
    # Check if sign needs to be flipped (direction: 1=increase, 2=decrease)
    df_full[varname] = flip_negative(df_full[varname], df["Q9bv2"], decrease_code=2)

    df_extract["infl_3y"] = df_full[varname]

    # Q9c: inflation forecast bins, months 24-36 from interview date.
    columns = [f"Q9c_bin{i}" for i in range(1, 11)]
    df_full[columns] = df[columns]

    df_extract["infl_3y_bin_mean"] = df["Q9c_mean"]
    df_extract["infl_3y_bin_var"] = df["Q9c_var"]
    df_extract["infl_3y_bin_median"] = df["Q9c_cent50"]
    df_extract["infl_3y_bin_iqr"] = df["Q9c_iqr"]
    # Rescale to [0, 100] to be in line with all other prob responses
    df_extract["infl_3y_bin_prob_defl"] = df["Q9c_probdeflation"] * 100.0

    # --- Q1a: Inflation/deflation between 48-60 months from now ---

    if "Q1a" in df.columns:
        # Variable name changed in later surveys
        varname = "Q1apart2"
        # Merge questions Q1a and Q1apart2
        df_full[varname] = df[varname]
        # Check if sign needs to be flipped (direction: 1=increase, 2=decrease)
        df_full[varname] = flip_negative(df_full[varname], df["Q1a"], decrease_code=2)

        df_extract["infl_5y"] = df_full[varname]

        # Preserve the seven available Q9new2 summaries in df_full under original names
        q9new2_source_cols = [
            "Q9new2_cent25",
            "Q9new2_cent50",
            "Q9new2_cent75",
            "Q9new2_iqr",
            "Q9new2_mean",
            "Q9new2_probdeflation",
            "Q9new2_var",
        ]
        q9new2_present = [col for col in q9new2_source_cols if col in df.columns]
        df_full[q9new2_present] = df[q9new2_present]

        # Preserve legacy bin columns in df_full if they exist
        cols_q9 = [f"Q9new2_bin{i}" for i in range(1, 11)]
        columns = df.filter(items=cols_q9, axis=1).columns.to_list()
        if columns:
            df_full[columns] = df[columns]

        # Expose five-year summaries in extract using names parallel to 1y/3y
        if "Q9new2_mean" in df.columns:
            df_extract["infl_5y_bin_mean"] = df["Q9new2_mean"]
        if "Q9new2_var" in df.columns:
            df_extract["infl_5y_bin_var"] = df["Q9new2_var"]
        if "Q9new2_cent50" in df.columns:
            df_extract["infl_5y_bin_median"] = df["Q9new2_cent50"]
        if "Q9new2_iqr" in df.columns:
            df_extract["infl_5y_bin_iqr"] = df["Q9new2_iqr"]
        if "Q9new2_probdeflation" in df.columns:
            # Rescale probability from [0, 1] to [0, 100] consistently
            df_extract["infl_5y_bin_prob_defl"] = df["Q9new2_probdeflation"] * 100.0

    return df_full, df_extract


def _process_labor_market(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process employment, job-search, and earnings questions (Q10--Q24)."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # --- Employment ---

    # Q10 stores each permitted employment status as a separate 0/1 indicator.
    d = df.filter(regex=r"^Q10_\d+$", axis=1)
    columns = d.columns.to_list()
    df_full[columns] = df[columns]

    # `working` means working now (full-/part-time), not merely job-attached;
    # an Other-only response is unclassifiable rather than explicitly not working.
    df_extract["working"] = any_selected_indicator(
        d,
        selected_columns=Q10_WORKING_COLUMNS,
        unknown_columns=Q10_OTHER_COLUMNS,
    )

    # Q11: Current number of jobs, conditional on working, temp layoff, or on leave
    df_full["Q11"] = df["Q11"]
    df_extract["num_jobs"] = df_full["Q11"]

    # Q12new: do you work for someone else or are you self-employed?
    # Coding: (1) Work for someone else, (2) Self-employed — see EmplTypeEnum.
    df_full["Q12new"] = df["Q12new"]
    df_extract["self_employed"] = recode_binary_response(
        df_full["Q12new"], coding=SELF_EMPLOYED_RECODE
    )

    # Q13new: change that R will lose main/current job
    df_full["Q13new"] = df["Q13new"]
    df_extract["prob_lose_job"] = df_full["Q13new"]

    # Q14new: chance to leave current job in next 12 months
    df_full["Q14new"] = df["Q14new"]
    df_extract["prob_leave_job"] = df_full["Q14new"]

    # Q15 is asked only of respondents who are not working but would like to;
    # structural missingness therefore must not be interpreted as "No."
    df_full["Q15"] = df["Q15"]
    df_extract["looking_for_job"] = recode_binary_response(
        df_full["Q15"], coding=YES_NO_RECODE
    )

    # Q16: How long have you been unemployed (in months)
    df_full["Q16"] = df["Q16"]
    # Check that this is missing whenever R is NOT looking for a job
    assert df_full.loc[df_full["Q15"] != 1, "Q16"].isna().all()

    # Q17new: Chance to find and accept job in next 12 months
    df_full["Q17new"] = df["Q17new"]
    df_extract["prob_accept_job_12m"] = df_full["Q17new"]

    # Q18new: Chance to find and accept job in next 3 months
    df_full["Q18new"] = df["Q18new"]
    df_extract["prob_accept_job_3m"] = df_full["Q18new"]

    # Q19: How long have you been out of work (only if Q15 = 2)
    df_full["Q19"] = df["Q19"]
    # Check that this is missing whenever R is *not* not looking for a job
    assert df_full.loc[df_full["Q15"] != 2, "Q19"].isna().all()

    # Merge Q16 and Q19: how long have you been unemployed / out of work?
    df_extract["jobless_length"] = merge_if_na(df_full[["Q16", "Q19"]])

    # Q20new: Chance to start looking for job in next 12 months
    df_full["Q20new"] = df["Q20new"]
    df_extract["prob_search_job_12m"] = df_full["Q20new"]

    # Q21new: Chance to start looking for job in next 3 months
    df_full["Q21new"] = df["Q21new"]
    df_extract["prob_search_job_3m"] = df_full["Q21new"]

    # Q22new: suppose you lost job this month, chance to find & accept job in
    # next 3 months
    df_full["Q22new"] = df["Q22new"]

    # --- Earnings ---

    # Q23v2: Earnings increase/decrease over next 12 months
    df_full["Q23v2"] = df["Q23v2"]
    # Q23v2part2: percent increase/decrease in earnings
    varname = "Q23v2part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["Q23v2"], decrease_code=3)

    df_extract["earnings_change"] = df_full[varname]

    # Q24: PMF over earnings changes
    d = df.filter(regex="Q24_.*", axis=1)
    columns = d.columns.to_list()
    df_full[columns] = df[columns]

    return df_full, df_extract


def _process_household_finances(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process household finances, spending, taxes, and credit (Q25--Q30)."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # Q25v2: Change in overall household income
    df_full["Q25v2"] = df["Q25v2"]
    # Q25v2part2: percent increase/decrease in household income
    varname = "Q25v2part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["Q25v2"], decrease_code=3)

    df_extract["hh_inc_change"] = df_full[varname]

    # --- Spending ---

    # Q26v2: total HH spending increase/decrease?
    df_full["Q26v2"] = df["Q26v2"]
    # Q26v2part2: percent increase/decrease in household spending
    varname = "Q26v2part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["Q26v2"], decrease_code=3)

    df_extract["hh_spending_change"] = df_full[varname]

    # --- Taxes ---

    # Q27v2: total amount of taxes increases/decreases?
    df_full["Q27v2"] = df["Q27v2"]
    # Q27v2part2: percent increase/decrease in total taxes
    varname = "Q27v2part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["Q27v2"], decrease_code=3)

    df_extract["taxes_change"] = df_full[varname]

    # --- Credit conditions ---

    # Q28: credit conditions compared to past 12 months
    df_full["Q28"] = df["Q28"]
    df_extract["credit_cond_past_12m"] = df_full["Q28"]

    # Q29: Credit conditions 12 months from now
    df_full["Q29"] = df["Q29"]
    df_extract["credit_cond_12m"] = df_full["Q29"]

    # Q30new: prob. to miss debt payment over next 3 months
    df_full["Q30new"] = df["Q30new"]
    df_extract["prob_miss_paym_3m"] = df_full["Q30new"]

    return df_full, df_extract


def _process_housing_and_macro(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process house-price and government-debt expectations (Q31, C1--C3)."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # --- House prices ---

    # Q31v2: nationwide house prices increase/decrease?
    df_full["Q31v2"] = df["Q31v2"]
    # Q31v2part2: percent increase/decrease in house prices
    varname = "Q31v2part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["Q31v2"], decrease_code=3)

    df_extract["house_price_change"] = df_full[varname]

    # C1: PMF over national house price changes
    d = df.filter(regex="C1_.*", axis=1)
    columns = d.columns.to_list()
    df_full[columns] = df[columns]

    # C2: nationwide house prices increase/decrease between 24 and 36 months from now?
    df_full["C2"] = df["C2"]
    # C2part2: percent increase/decrease in house prices
    varname = "C2part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["C2"], decrease_code=3)

    df_extract["house_price_change_3y"] = df_full[varname]

    # --- Government debt ---

    # C3: US government debt increase/decrease?
    df_full["C3"] = df["C3"]
    # C3part2: percent increase/decrease in US government debt
    varname = "C3part2"
    df_full[varname] = df[varname]
    df_full[varname] = flip_negative(df_full[varname], df["C3"], decrease_code=3)

    df_extract["govt_debt_change"] = df_full[varname]

    return df_full, df_extract


# Answer key for the official, currently published SCE core questionnaire.
# The FRBNY does not publish a versioned historical core questionnaire. Responses
# recorded for incumbent panel members before their first public-data observation
# are therefore preserved but not scored below.
NUMERICAL_LITERACY_ANSWER_KEY: dict[str, float] = {
    "QNUM1": 150.0,
    "QNUM2": 200.0 * 1.1**2,
    "QNUM3": 10.0,
    "QNUM5": 100.0,
    "QNUM6": 10_000.0 * 0.0005,
    "QNUM8": 3.0,
    "QNUM9": 2.0,
}


def score_numerical_literacy_response(
    values: pd.Series,
    *,
    answer: float,
    eligible: pd.Series,
) -> pd.Series:
    """Score responses whose questionnaire version is established.

    Parameters
    ----------
    values
        Numerical-literacy responses for one question.
    answer
        Correct answer in the currently published SCE core questionnaire.
    eligible
        Boolean indicator for responses known to use that questionnaire. The
        core questionnaire asks these questions only of new respondents, so
        production processing supplies ``tenure == 1``.

    Returns
    -------
    Nullable 0/1 correctness indicator. Missing responses and responses
    from an unverified questionnaire version remain missing.
    """
    result = pd.Series(pd.NA, index=values.index, dtype=pd.Int8Dtype())
    scored = values.notna() & eligible
    result.loc[scored] = np.isclose(
        values.loc[scored],
        answer,
        rtol=0.0,
        atol=1.0e-6,
    ).astype(np.int8)
    return result


def _process_financial_literacy(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process numerical and financial literacy questions."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # The published questionnaire asks QNUM* only of new respondents. The first
    # public wave nevertheless contains responses for incumbent pilot members
    # with tenure greater than one, including answer patterns inconsistent with
    # the published questions. Their raw values remain useful, but without the
    # historical instrument their correctness cannot be established.
    eligible = df["tenure"].eq(1)
    qnum_columns = list(NUMERICAL_LITERACY_ANSWER_KEY)
    has_response = df[qnum_columns].notna()
    unverified_rows = ~eligible & has_response.any(axis=1)
    if unverified_rows.any():
        n_rows = int(unverified_rows.sum())
        n_responses = int(has_response.loc[unverified_rows].sum().sum())
        logging.getLogger(LOGGER_NAME).warning(
            f"Numerical literacy: preserving {n_responses:,d} response(s) from "
            f"{n_rows:,d} non-new-respondent row(s), but leaving correctness "
            "missing because the historical questionnaire is unavailable"
        )

    for source_name, answer in NUMERICAL_LITERACY_ANSWER_KEY.items():
        question_number = source_name.removeprefix("QNUM").lower()
        extract_name = f"num_lit_q{question_number}"

        df_full[source_name] = df[source_name]
        df_extract[extract_name] = df_full[source_name]
        df_extract[f"{extract_name}_correct"] = score_numerical_literacy_response(
            df_extract[extract_name],
            answer=answer,
            eligible=eligible,
        )

    return df_full, df_extract


def _process_demographics(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process initial respondent demographics (Q32--Q37)."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # --- Demographic questions (new respondents only) ---

    # Q32: current age at first interview (asked of new respondents only).
    # Implausible values (e.g. 0, 3, 511) are set to missing before tiling so
    # that they are not propagated to every subsequent wave for that user.
    # Bounds: see AGE_MIN / AGE_MAX constants.
    df_full["Q32"] = tile_const(clean_age(df["Q32"]), VARNAME_ID, "Int8")

    # Broadcast age across all waves since it does not seem to be asked again.
    df_extract["age_init"] = df_full["Q32"]

    # Q33: gender — coding: (1) Female, (2) Male.
    df_full["Q33"] = tile_const(df["Q33"], VARNAME_ID, "Int8")
    df_extract["female"] = recode_binary_response(df_full["Q33"], coding=FEMALE_RECODE)

    # Q34: Hispanic/Latino origin — coding: (1) Yes, (2) No.
    df_full["Q34"] = tile_const(df["Q34"], VARNAME_ID, "Int8")
    df_extract["hispanic"] = recode_binary_response(
        df_full["Q34"], coding=HISPANIC_RECODE
    )

    # Q35 records race only at the initial interview. Preserve these sparse raw
    # responses in the full output and tile only descriptively named indicators.
    d = df.filter(regex=r"^Q35_\d+$", axis=1)
    races = tile_const(d, VARNAME_ID, "Int8")
    df_full = pd.concat((df_full, d), axis=1)
    df_extract["black"] = races["Q35_2"]

    # Q36: highest education level — codes 1–8 map to specific levels;
    # code 9 is "Other (please specify)".
    df_full["Q36"] = tile_const(df["Q36"], VARNAME_ID, "Int8")

    # Count code-9 ("Other") education responses. These are unclassifiable and
    # are treated as missing in both derived variables below.
    n_educ_other = int((df_full["Q36"] == 9).sum())
    if n_educ_other:
        logging.getLogger(LOGGER_NAME).warning(
            f"Q36 (education): {n_educ_other:,d} code-9 ('Other') response(s) "
            "set to missing in both 'college' and 'educ'"
        )

    # Binary college indicator: codes 5–8 are college-level degrees; codes 1–4
    # are below college; code 9 (Other) is treated as missing (not as non-college)
    # because the respondent's actual qualification is unknown.
    df_extract["college"] = recode_binary_response(
        df_full["Q36"], coding=COLLEGE_RECODE
    )
    # Coarser education with 4 categories (Educ4Enum): LT HS=1, HS=2,
    # Some college (including associate's degree)=3, College degree=4.
    # Code 9 (Other) is unmapped and therefore remains missing.
    df_extract["educ"] = df_full["Q36"].map(EDUCATION_TO_EDUC4).astype(pd.Int8Dtype())

    # Q37: How long working at current job? (categorical)
    df_full["Q37"] = df["Q37"]

    return df_full, df_extract


def _process_household_background(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process household background and repeat-interview updates (Q38--D6)."""
    df_full = pd.DataFrame(index=df.index)
    df_extract = pd.DataFrame(index=df.index)

    # Q38: Initial question: Married or living with partner?
    # NOTE: Will be updated for later waves below
    df_full["Q38"] = df["Q38"]

    # HH2 records each spouse/partner employment status as a separate indicator.
    spouse_status_columns = [f"HH2_{i}" for i in range(1, 12)]
    d = df.filter(items=spouse_status_columns, axis=1)
    if d.shape[1] > 0:
        df_full = pd.concat((df_full, d), axis=1)

    # Q39 and Q40 don't seem to be present in public data set

    # 41: How long have you lived at primary residence?
    df_full["Q41"] = df["Q41"]

    # 42: How many years in total lived in current state?
    df_full["Q42"] = df["Q42"]

    # Q43: do you own or rent your primary residence?
    # Coding: (1) Own, (2) Rent, (3) Other (please specify). Code 3 is treated
    # as missing because the arrangement is unspecified; it must not be equated
    # with renting.
    df_full["Q43"] = df["Q43"]
    df_extract["owner"] = recode_binary_response(df_full["Q43"], coding=OWNER_RECODE)

    # Q44: Own any other homes?
    df_full["Q44"] = df["Q44"]

    # Q45new records counts for nine household-member categories at the initial
    # interview; complete D2new responses replace this state at repeat interviews.
    columns_hh_comp = [f"Q45new_{i}" for i in range(1, 10)]
    df_full = pd.concat((df_full, df[columns_hh_comp]), axis=1)

    # Q45b: self-reported health
    df_full["Q45b"] = df["Q45b"]
    df_extract["health"] = df_full["Q45b"]

    # Q46: Financial decision making
    df_full["Q46"] = tile_const(df["Q46"], VARNAME_ID, "Int8")

    # QRA1: Willingness to take financial risk
    if "QRA1" in df.columns:
        df_full["QRA1"] = tile_const(df["QRA1"], VARNAME_ID, "Int8")

        df_extract["take_fin_risk"] = df_full["QRA1"]

    # QRA2: Willingness to take risk in daily activities
    if "QRA2" in df.columns:
        df_full["QRA2"] = tile_const(df["QRA2"], VARNAME_ID, "Int8")

    # Q47: Total pre-tax family income during the past 12 months
    df_full["Q47"] = df["Q47"]

    # --- Questions to repeat respondents ---

    # D1 is asked only at repeat interviews: 1 means unchanged and 2 changed.
    # Missing initial-interview responses must remain distinct from "unchanged."
    df_full["D1"] = df["D1"]
    df_extract["hh_changed"] = recode_binary_response(
        df_full["D1"], coding=HOUSEHOLD_CHANGED_RECODE
    )

    # D2new is a complete replacement state when observed. In particular, 2013
    # incumbent-panel baselines contain valid D2new responses with missing D1.
    columns_hh_updates = [f"D2new_{i}" for i in range(1, 10)]
    hh_updates = df[columns_hh_updates].copy(deep=True)
    hh_updates.columns = columns_hh_comp
    df_full[columns_hh_comp] = propagate_household_composition(
        df_full[columns_hh_comp], hh_updates
    )

    # Number of kids implied by HH composition
    # Select relevant columns containing kids of various ages
    columns = [f"Q45new_{i}" for i in range(2, 6)]
    kids = df_full[columns].sum(axis=1, min_count=4)
    if kids.notna().all():
        kids = kids.astype(int)
    df_extract["num_kids"] = kids

    # D3: moved to a new primary residence since last interview?
    df_full["D3"] = df["D3"]

    # DSAME: Worked at same employer in last survey?
    df_full["DSAME"] = df["DSAME"]
    # DSAME Other does not establish whether the employer is the same.
    df_extract["same_employer"] = recode_binary_response(
        df_full["DSAME"], coding=SAME_EMPLOYER_RECODE
    )

    # DQ38: currently married or living with partner? (repeat-interview update to Q38)
    # Coding: (1) Yes, (2) No.
    df_full["Q38"] = merge_if_na(df_full["Q38"], df["DQ38"])
    df_extract["couple"] = recode_binary_response(df_full["Q38"], coding=COUPLE_RECODE)

    # DHH2 repeats the HH2 multi-response question; merge updates into the
    # canonical HH2 fields before deriving spouse employment.
    d = df.filter(regex=r"^DHH2_\d+$", axis=1)
    for name, col in d.items():
        # Remove the leading "D" to align repeat responses with HH2 fields.
        if isinstance(name, str):
            dst = name[1:]
            df_full[dst] = merge_if_na(df_full[dst], col)

    if spouse_status_columns[0] in df_full.columns:
        # Full-time, part-time, and self-employment mean working; an Other-only
        # response is unclassifiable rather than explicitly not working.
        df_extract["spouse_working"] = any_selected_indicator(
            df_full[spouse_status_columns],
            selected_columns=SPOUSE_WORKING_COLUMNS,
            unknown_columns=SPOUSE_OTHER_COLUMNS,
        )

    # D6: Current total pre-tax family income (11 income bins)
    df_full["Q47"] = merge_if_na(df_full["Q47"], df["D6"])
    df_extract["hh_inc_bin"] = df_full["Q47"]

    return df_full, df_extract


def process_sce(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process raw SCE data into the full and reduced extract datasets.

    Parameters
    ----------
    df
        Raw SCE DataFrame.

    Returns
    -------
    df_full
        Processed full dataset containing curated source-named variables.
    df_extract
        Reduced dataset containing descriptively named derived variables.
    """
    df = df.rename(columns={"date": VARNAME_WID, "survey_date": "date"})
    # Panel identifiers are required by the SCE schema and never admit missing values.
    df = df.astype({VARNAME_ID: "int64", VARNAME_WID: "int64"})
    df = df.set_index([VARNAME_ID, VARNAME_WID]).sort_index()

    # Common meta-variables are present in both outputs.
    columns = ["tenure", "weight"]
    df_full_common = df[columns].copy(deep=True)
    df_extract_common = df[columns].copy(deep=True)

    # Convert datetime64[ns] to dates because the time is always midnight.
    date = df["date"].values.astype("datetime64[D]")  # type: ignore
    df_full_common["date"] = date
    df_extract_common["date"] = date

    full_parts: list[pd.DataFrame] = [df_full_common]
    extract_parts: list[pd.DataFrame] = [df_extract_common]

    df_full_general, df_extract_general = _process_general_expectations(df)
    full_parts.append(df_full_general)
    extract_parts.append(df_extract_general)

    df_full_inflation, df_extract_inflation = _process_inflation(df)
    full_parts.append(df_full_inflation)
    extract_parts.append(df_extract_inflation)

    df_full_labor, df_extract_labor = _process_labor_market(df)
    full_parts.append(df_full_labor)
    extract_parts.append(df_extract_labor)

    df_full_finances, df_extract_finances = _process_household_finances(df)
    full_parts.append(df_full_finances)
    extract_parts.append(df_extract_finances)

    df_full_housing, df_extract_housing = _process_housing_and_macro(df)
    full_parts.append(df_full_housing)
    extract_parts.append(df_extract_housing)

    df_full_fin_lit, df_extract_fin_lit = _process_financial_literacy(df)
    full_parts.append(df_full_fin_lit)
    extract_parts.append(df_extract_fin_lit)

    df_full_demographics, df_extract_demographics = _process_demographics(df)
    full_parts.append(df_full_demographics)
    extract_parts.append(df_extract_demographics)

    df_full_household, df_extract_household = _process_household_background(df)
    full_parts.append(df_full_household)
    extract_parts.append(df_extract_household)

    df_full = pd.concat(full_parts, axis=1, verify_integrity=True)
    df_extract = pd.concat(extract_parts, axis=1, verify_integrity=True)

    df_full = df_full.sort_index()
    df_extract = df_extract.sort_index()

    df_full = apply_sce_output_dtypes(
        df_full,
        int8_columns=NULLABLE_INT8_COLUMNS,
    )
    df_extract = apply_sce_output_dtypes(
        df_extract,
        int8_columns=NULLABLE_INT8_COLUMNS,
    )

    return df_full, df_extract


def income_reference_year(dates: pd.Series) -> pd.Series:
    """Assign the ACS reference year from the SCE interview month.

    Parameters
    ----------
    dates
        SCE interview dates.

    Returns
    -------
    ACS reference years, indexed like ``dates``.

    Notes
    -----
    SCE household income refers to the preceding 12 months. Interviews from
    January through June use the previous calendar year, while interviews from
    July through December use the current calendar year. Calendar-month periods
    ensure that the interview day cannot affect this assignment.
    """
    survey_month = dates.dt.to_period("M")
    # The existing ACS alignment switches reference years halfway through the
    # survey year because respondents report income over the preceding 12 months.
    previous_year = survey_month.dt.month.le(6).astype(np.int8)
    return (survey_month.dt.year - previous_year).rename("year")


def expand_income_rank_years(
    df_ranks: pd.DataFrame,
    required_years: Iterable[int],
) -> pd.DataFrame:
    """Expand ACS income ranks to all required years by income bin.

    Parameters
    ----------
    df_ranks
        ACS rank mapping with ``year``, ``ibin``, and ``rank`` columns.
    required_years
        ACS reference years required by the SCE observations.

    Returns
    -------
    Rank mappings on a complete year-by-income-bin grid. Internal and
    future missing years use the latest preceding mapping for the same bin.

    Raises
    ------
    ValueError
        If a required year predates the first ACS year or a complete mapping
        cannot be constructed by carrying prior ranks forward.

    Notes
    -----
    SCE income bins have fixed nominal boundaries. When an ACS mapping is not
    available for a reference year, the policy is therefore to retain the most
    recent mapping independently within each income bin. Future ACS mappings
    are never used to back-fill earlier years.
    """
    logger = logging.getLogger(LOGGER_NAME)

    required = np.asarray(list(required_years), dtype=np.int64)
    source = df_ranks[["year", "ibin", "rank"]].copy()
    first_year = int(source["year"].min())
    last_year = int(source["year"].max())

    if required.size and (earliest_required := int(required.min())) < first_year:
        raise ValueError(
            f"SCE income reference year {earliest_required} predates the first "
            f"available ACS rank year {first_year}; backward filling is not allowed"
        )

    final_year = max(last_year, int(required.max()) if required.size else last_year)
    years = np.arange(first_year, final_year + 1)
    bins = np.sort(source["ibin"].unique())
    grid = pd.MultiIndex.from_product([years, bins], names=["year", "ibin"]).to_frame(
        index=False
    )

    source["_source_year"] = source["year"]
    expanded = grid.merge(source, on=["year", "ibin"], how="left", validate="1:1")
    # Carry ranks down each bin separately because different income bins are not
    # economically interchangeable, even when their ACS year is the same.
    expanded[["rank", "_source_year"]] = expanded.groupby("ibin", sort=False)[
        ["rank", "_source_year"]
    ].ffill()

    missing = expanded[expanded["rank"].isna()][["year", "ibin"]]
    if not missing.empty:
        keys = list(missing.itertuples(index=False, name=None))
        raise ValueError(
            "ACS ranks cannot form a complete year-by-income-bin mapping; "
            f"missing keys: {keys}"
        )

    required_set = set(required.tolist())
    substitutions = expanded[
        expanded["year"].isin(required_set)
        & expanded["_source_year"].ne(expanded["year"])
    ]
    for (source_year, target_year), rows in substitutions.groupby(
        ["_source_year", "year"], sort=True
    ):
        substituted_bins = rows["ibin"].tolist()
        logger.warning(
            "  Using ACS income ranks from %d for reference year %d, bins %s",
            source_year,
            target_year,
            substituted_bins,
        )

    return expanded[["year", "ibin", "rank"]]


def merge_inc_rank(
    df: pd.DataFrame,
    varname_inc_bin: str,
    df_ranks: pd.DataFrame,
) -> pd.Series:
    """
    Merge median income rank conditional on income bin.

    Parameters
    ----------
    df
        SCE data DataFrame.
    varname_inc_bin
        Income bin variable name.
    df_ranks
        Income rank data from ACS.

    Returns
    -------
    The merged income rank Series.
    """
    logger = logging.getLogger(LOGGER_NAME)

    logger.info("Merging income rank to income bins")

    years_in_ranks = np.sort(df_ranks["year"].unique())
    logger.info("  Income years available in ACS data: ")
    logger.info(f"    {years_in_ranks}")

    df = df.copy()
    df["year"] = income_reference_year(df["date"])
    years_in_sce = np.sort(df["year"].unique())
    df_ranks = expand_income_rank_years(df_ranks, years_in_sce)

    # Rescale to rank percentiles on [0, 100]
    if df_ranks["rank"].max() <= 1.0:
        df_ranks["rank"] = df_ranks["rank"] * 100.0

    # Merge total household income
    varname_rank = varname_inc_bin + "_rank"
    df_ranks = df_ranks.rename(columns={"rank": varname_rank, "ibin": varname_inc_bin})
    index_names = df.index.names
    if index_names is not None:
        df = df.reset_index(drop=False)

    df_ranks = df_ranks[["year", varname_inc_bin, varname_rank]].copy()

    df = df.merge(
        df_ranks,
        how="left",
        on=["year", varname_inc_bin],
        validate="m:1",
    )

    unmatched = df[varname_inc_bin].notna() & df[varname_rank].isna()
    if unmatched.any():
        # Every reported SCE income bin must have an ACS rank for its assigned
        # reference year; otherwise the output would silently lose rank coverage.
        keys = list(
            df.loc[unmatched, ["year", varname_inc_bin]]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
        raise ValueError(
            f"Income ranks are unavailable for non-missing {varname_inc_bin} "
            f"responses at keys: {keys}"
        )

    if index_names is not None:
        df = df.set_index(index_names).sort_index()

    return df[varname_rank]
