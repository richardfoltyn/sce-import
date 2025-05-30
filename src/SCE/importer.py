import logging

import numpy as np
import pandas as pd

from SCE.constants import VARNAME_ID, VARNAME_WID
from SCE.pandas_helpers import merge_if_na, tile_const, try_cast


def flip_sign(df: pd.DataFrame, varname: str, negative: pd.Series) -> None:
    """
    Flip the sign of a variable if needed so that decreases are coded as
    negative numbers.

    Parameters
    ----------
    df : pd.DataFrame
    varname : str
    negative : pd.Series
    """

    logger = logging.getLogger("SCE")

    # Check if sign needs to be flipped
    if (df.loc[negative, varname].fillna(0.0) <= 0).all():
        # Sign is already correct
        logger.info(f"Leaving sign in {varname} unchanged")
    elif (df.loc[negative, varname].fillna(0.0) >= 0).all():
        # Sign needs to be flipped
        logger.info(f"Flipping sign in {varname} to negative")
        df.loc[negative, varname] *= -1
    else:
        logger.warning(f"{varname} has ambiguous sign")


def process_sce(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger = logging.getLogger("SCE")

    df = df.rename(columns={"date": VARNAME_WID, "survey_date": "date"})
    df = df.set_index([VARNAME_ID, VARNAME_WID]).sort_index()

    # meta-variables to be copied directly
    columns = ["date", "tenure", "weight"]
    df_full = df[columns].copy(deep=True)
    df_extract = df[columns].copy(deep=True)

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

    # --- Inflation ---

    # Merge questions Q8v2 and Q8v2part2
    varname = "Q8v2part2"
    df_full[varname] = df[varname]
    # Check if sign needs to be flipped
    deflation = df["Q8v2"] == 2
    flip_sign(df_full, varname, deflation)

    df_extract["infl_1y"] = df_full[varname]

    # Q9: inflation forecast bins.
    columns = [f"Q9_bin{i}" for i in range(1, 11)]
    df_full[columns] = df[columns]

    df_extract["infl_1y_bin_mean"] = df["Q9_mean"]
    df_extract["infl_1y_bin_var"] = df["Q9_var"]
    df_extract["infl_1y_bin_median"] = df["Q9_cent50"]
    df_extract["infl_1y_bin_iqr"] = df["Q9_iqr"]
    df_extract["infl_1y_bin_prob_defl"] = df["Q9_probdeflation"]

    # --- Q9b: Inflation/deflation between 24-36 months from now ---
    # Merge questions Q9bv2 and Q9bv2part2
    varname = "Q9bv2part2"
    df_full[varname] = df[varname]
    # Check if sign needs to be flipped
    deflation = df["Q9bv2"] == 2
    flip_sign(df_full, varname, deflation)

    df_extract["infl_3y"] = df_full[varname]

    # Q9c: inflation forecast bins, months 24-36 from interview date.
    columns = [f"Q9c_bin{i}" for i in range(1, 11)]
    df_full[columns] = df[columns]

    df_extract["infl_3y_bin_mean"] = df["Q9c_mean"]
    df_extract["infl_3y_bin_var"] = df["Q9c_var"]
    df_extract["infl_3y_bin_median"] = df["Q9c_cent50"]
    df_extract["infl_3y_bin_iqr"] = df["Q9c_iqr"]
    df_extract["infl_3y_bin_prob_defl"] = df["Q9c_probdeflation"]

    # --- Q1a: Inflation/deflation between 48-60 months from now ---

    if "Q1a" in df.columns:
        # Variable name changed in later surveys
        varname = "Q1apart2"
        # Merge questions Q1a and Q1apart2
        df_full[varname] = df[varname]
        # Check if sign needs to be flipped
        deflation = df["Q1a"] == 2
        flip_sign(df_full, varname, deflation)

        df_extract["infl_5y"] = df_full[varname]

        # Q9new2: inflation forecast bins, months 48-60 from interview.
        columns = [f"Q9new2_bin{i}" for i in range(1, 11)]
        # These columns are missing in later surveys
        columns = df.filter(items=columns, axis=1)
        df_full[columns] = df[columns]

    # --- Employment ---

    # Coded as indicator variable as multiple responses are permitted
    d = df.filter(regex="Q10_.*", axis=1)
    columns = d.columns.to_list()
    df_full[columns] = df[columns]

    df_extract["working"] = (df[["Q10_1", "Q10_2"]] == 1).any(axis=1).astype(np.uint8)

    # Q11: Current number of jobs, conditional on working, temp layoff, or on leave
    df_full["Q11"] = df["Q11"]
    df_extract["num_jobs"] = df_full["Q11"]

    # Q12: Self-employed?
    # The questionaire does not specify the coding, assume 1 = work for someone else,
    # 2 = self-employed
    df_full["Q12new"] = df["Q12new"]
    df_extract["self_employed"] = df_full["Q12new"].map({1:0, 2:1}, na_action="ignore")

    # Q13new: change that R will lose main/current job
    df_full["Q13new"] = df["Q13new"]
    df_extract["prob_lose_job"] = df_full["Q13new"]

    # Q14new: chance to leave current job in next 12 months
    df_full["Q14new"] = df["Q14new"]
    df_extract["prob_leave_job"] = df_full["Q14new"]

    # Q15: Looking for job? Yes = 1, No = 2
    df_full["Q15"] = df["Q15"]
    df_extract["looking_for_job"] = (df_full["Q15"] == 1).astype(int)

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

    # Periodically create non-fragmented copies of DataFrames to avoid pandas warnings.
    df_full = df_full.copy()
    df_extract = df_extract.copy()

    # --- Earnings ---

    # Q23v2: Earnings increase/decrease over next 12 months
    df_full["Q23v2"] = df["Q23v2"]
    # Q23v2part2: percent increase/decrease in earnings
    varname = "Q23v2part2"
    df_full[varname] = df[varname]
    negative = df["Q23v2"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["earnings_change"] = df_full[varname]

    # Q24: PMF over earnings changes
    d = df.filter(regex="Q24_.*", axis=1)
    columns = d.columns.to_list()
    df_full[columns] = df[columns]

    # Q25v2: Change in overall household income
    df_full["Q25v2"] = df["Q25v2"]
    # Q25v2part2: percent increase/decrease in household income
    varname = "Q25v2part2"
    df_full[varname] = df[varname]
    negative = df["Q25v2"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["hh_inc_change"] = df_full[varname]

    # --- Spending ---

    # Q26v2: total HH spending increase/decrease?
    df_full["Q26v2"] = df["Q26v2"]
    # Q26v2part2: percent increase/decrease in household spending
    varname = "Q26v2part2"
    df_full[varname] = df[varname]
    negative = df["Q26v2"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["hh_spending_change"] = df_full[varname]

    # --- Taxes ---

    # Q27v2: total amount of taxes increases/decreases?
    df_full["Q27v2"] = df["Q27v2"]
    # Q27v2part2: percent increase/decrease in total taxes
    varname = "Q27v2part2"
    df_full[varname] = df[varname]
    negative = df["Q27v2"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["taxes_change"] = df_full[varname]

    # --- Credit conditions ---

    # Q28: credit conditions compared to past 12 months
    df_full["Q28"] = df["Q28"]
    df_extract["credit_cond_past12m"] = df_full["Q28"]

    # Q29: Credit conditions 12 months from now
    df_full["Q29"] = df["Q29"]
    df_extract["credit_cond_12m"] = df_full["Q29"]

    # Q30new: prob. to miss debt payment over next 3 months
    df_full["Q30new"] = df["Q30new"]
    df_extract["prob_miss_paym_3m"] = df_full["Q30new"]

    # --- House prices ---

    # Q31v2: nationwide house prices increase/decrease?
    df_full["Q31v2"] = df["Q31v2"]
    # Q31v2part2: percent increase/decrease in house prices
    varname = "Q31v2part2"
    df_full[varname] = df[varname]
    negative = df["Q31v2"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["house_price_change"] = df[varname]

    # C1: PMF over national house price changes
    d = df.filter(regex="C1_.*", axis=1)
    columns = d.columns.to_list()
    df_full[columns] = df[columns]

    # C2: nationwide house prices increase/decrease between 24 and 36 months from now?
    df_full["C2"] = df["C2"]
    # C2part2: percent increase/decrease in house prices
    varname = "C2part2"
    df_full[varname] = df[varname]
    negative = df["C2"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["house_price_change_3y"] = df_full[varname]

    # --- Government debt ---

    # C3: US government debt increase/decrease?
    df_full["C3"] = df["C3"]
    # C3part2: percent increase/decrease in US government debt
    varname = "C3part2"
    df_full[varname] = df[varname]
    negative = df["C3"] == 3
    flip_sign(df_full, varname, negative)

    df_extract["govt_debt_change"] = df_full[varname]

    # Periodically create non-fragmented copies of DataFrames to avoid pandas warnings.
    df_full = df_full.copy()
    df_extract = df_extract.copy()

    # --- Numerical literacy questions ---

    # QNUM1: Compute 50% discounted price from $300
    df_full["QNUM1"] = df["QNUM1"]
    df_extract["num_lit_q1"] = df_full["QNUM1"]
    df_extract["num_lit_q1_correct"] = np.where(
        df_extract["num_lit_q1"].notna(), df_extract["num_lit_q1"] == 150, np.nan
    )

    # QNUM2: Gross interest of 10% on $200 after 2 years
    df_full["QNUM2"] = df["QNUM2"]
    df_extract["num_lit_q2"] = df_full["QNUM2"]
    df_extract["num_lit_q2_correct"] = np.where(
        df_extract["num_lit_q2"].notna(),
        (df_extract["num_lit_q2"] - 200 * 1.1**2).abs() < 1.0e-6,
        np.nan,
    )

    # QNUM3: Number of lottery winners out of 1,000 if chance is 1%
    df_full["QNUM3"] = df["QNUM3"]
    df_extract["num_lit_q3"] = df_full["QNUM3"]
    df_extract["num_lit_q3_correct"] = np.where(
        df_extract["num_lit_q3"].notna(),
        df_extract["num_lit_q3"] == 10,
        np.nan,
    )

    # QNUM5: Expected number of people with disease out of 1,000 if chance = 10%
    df_full["QNUM5"] = df["QNUM5"]
    df_extract["num_lit_q5"] = df_full["QNUM5"]
    df_extract["num_lit_q5_correct"] = np.where(
        df_extract["num_lit_q5"].notna(),
        df_extract["num_lit_q5"] == 100,
        np.nan,
    )

    # QNUM6: Expected number of infected out of 10,000 if chance = 0.0005
    df_full["QNUM6"] = df["QNUM6"]
    df_extract["num_lit_q6"] = df_full["QNUM6"]
    df_extract["num_lit_q6_correct"] = np.where(
        df_extract["num_lit_q6"].notna(),
        df_extract["num_lit_q6"] == 10000 * 0.0005,
        np.nan,
    )

    # QNUM8: Big 3: interest rate vs. inflation question
    # Interest rate = 1%, inflation = 2%.
    # Answers: (1) more than today (2) exactly the same (3) less than today
    df_full["QNUM8"] = df["QNUM8"]
    df_extract["num_lit_q8"] = df_full["QNUM8"]
    df_extract["num_lit_q8_correct"] = np.where(
        df_extract["num_lit_q8"].notna(),
        df_extract["num_lit_q8"] == 3,
        np.nan,
    )

    # QNUM9: Big 3: Buying a single company stock is safer than mutual fund
    # Answers: (1) True (2) False
    df_full["QNUM9"] = df["QNUM9"]
    df_extract["num_lit_q9"] = df_full["QNUM9"]
    df_extract["num_lit_q9_correct"] = np.where(
        df_extract["num_lit_q9"].notna(),
        df_extract["num_lit_q9"] == 2,
        np.nan,
    )

    # --- Demographic questions ---

    # Q32: Current age (only asked of now respondents)
    df_full["Q32"] = tile_const(df["Q32"], VARNAME_ID, int)

    # Broadcast age across all waves since it does not seem to be asked again.
    df_extract["age_init"] = df_full["Q32"]

    # Q33: gender: (1) Female (2) Male
    df_full["Q33"] = tile_const(df["Q33"], VARNAME_ID, np.uint8)
    female = df_full["Q33"].map({1: 1, 2: 0}, na_action="ignore")
    df_extract["female"] = female

    # Q34: Hispanic
    df_full["Q34"] = tile_const(df["Q34"], VARNAME_ID, np.uint8)
    hispanic = df_full["Q34"].map({1: 1, 2: 0}, na_action="ignore")
    df_extract["hispanic"] = hispanic

    # Q35: Races (multiple responses possible)
    d = df.filter(regex="Q35.*", axis=1)
    races = tile_const(d, VARNAME_ID, np.uint8)
    df_full = pd.concat((df_full, d), axis=1)
    df_extract["black"] = races["Q35_2"]

    # Q36: Highest level of education
    df_full["Q36"] = tile_const(df["Q36"], VARNAME_ID, np.uint8)
    df_extract["college"] = np.where(
        df_full["Q36"].notna(), df_full["Q36"].isin((5, 6, 7, 8)), np.nan
    )
    # Coarser education with 4 categories: LT HS, HS, Some college, College degree
    df_extract["educ"] = df_full["Q36"].map(
        {1: 1, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4, 7: 4, 8: 4}, na_action="ignore"
    )

    # Q37: How long working at current job? (categorical)
    df_full["Q37"] = df["Q37"]

    # Q38: Initial question: Married or living with partner?
    # NOTE: Will be updated for later waves below
    df_full["Q38"] = df["Q38"]

    # HH2: Spouses employment situation?
    d = df.filter(regex=r"^HH2_[\d]+$", axis=1)
    if d.shape[1] > 0:
        df_full = pd.concat((df_full, d), axis=1)

    # Q39 and Q40 don't seem to be present in public data set

    # 41: How long have you lived at primary residence?
    df_full["Q41"] = df["Q41"]

    # 42: How many years in total lived in current state?
    df_full["Q42"] = df["Q42"]

    # Q43: Rent/own current residence
    df_full["Q43"] = df["Q43"]
    df_extract["owner"] = df_full["Q43"].map({1: 1, 2: 0, 3: 0}, na_action="ignore")

    # Q44: Own any other homes?
    df_full["Q44"] = df["Q44"]

    # Q45new: Number of other HH members (multiple variables for multiple categories)
    # NOTE: Will be updated for later waves below
    d = df.filter(regex="Q45new_.*", axis=1)
    df_full = pd.concat((df_full, d), axis=1)

    # Q45b: self-reported health
    df_full["Q45b"] = df["Q45b"]
    df_extract["health"] = try_cast(df_full["Q45b"], np.uint8)

    # Q46: Financial decision making
    df_full["Q46"] = tile_const(df["Q46"], VARNAME_ID, np.uint8)

    # QRA1: Willingness to take financial risk
    if "QRA1" in df.columns:
        df_full["QRA1"] = tile_const(df["QRA1"], VARNAME_ID, np.uint8)

        df_extract["take_fin_risk"] = df_full["QRA1"]

    # QRA2: Willingness to take risk in daily activities
    if "QRA2" in df.columns:
        df_full["QRA2"] = tile_const(df["QRA2"], VARNAME_ID, np.uint8)

    # Q47: Total pre-tax family income during the past 12 months
    df_full["Q47"] = df["Q47"]

    # --- Questions to repeat respondents ---

    # D1 (repeat respondents only): household changed?
    df_full["D1"] = df["D1"]
    hh_changed = df_full["D1"] == 2
    df_extract["hh_changed"] = hh_changed.astype(np.uint8)

    # D2new: Updated HH members
    # Update the original variables in place instead of keep another set of variables
    d = df.filter(regex="D2new_.*", axis=1)
    columns = df.filter(regex="Q45new_.*", axis=1).columns.to_list()
    # Update HH composition in relevant waves
    df_comp = df_full[columns].copy(deep=True)
    df_comp.loc[hh_changed, columns] = d.loc[hh_changed].to_numpy()
    # Drop all waves other than the initial wave and waves where HH composition changed
    df_comp = df_comp.dropna()
    # Forward-fill initial/updated HH composition
    df_comp = df_comp.reindex(df_full.index, method="ffill")
    df_full[columns] = df_comp

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
    df_extract["same_employer"] = np.where(
        df_full["DSAME"].notna(), df_full["DSAME"].isin((1, 2)), np.nan
    )

    # DQ38: Currently married or living with partner?
    df_full["Q38"] = merge_if_na(df_full["Q38"], df["DQ38"])
    couple = df_full["Q38"].map({1: 1, 2: 0}, na_action="ignore")
    df_extract["couple"] = couple

    # dHH2: Spouses employment situation?
    d = df.filter(regex=r"^DHH2_[\d]+$", axis=1)
    if d.shape[1] > 0:
        for name, col in d.items():
            # Remove leading "D"
            dst = name[1:]
            df_full[dst] = merge_if_na(df_full[dst], col)

    if "HH_1" in df_full.columns:
        df_extract["spouse_working"] = (
            (df[["HH_1", "HH_2"]] == 1).any(axis=1).astype(np.uint8)
        )

    # D6: Current total pre-tax family income
    df_full["Q47"] = merge_if_na(df_full["Q47"], df["D6"])
    df_extract["hh_inc"] = df_full["Q47"]

    df_full = df_full.sort_index()
    df_extract = df_extract.sort_index()

    return df_full, df_extract


def merge_inc_rank(
    df: pd.DataFrame, varname_inc_bin: str, df_ranks: pd.DataFrame
) -> pd.Series:
    """
    Merge median income rank conditional on income bin.

    Parameters
    ----------
    df : pd.DataFrame
        SCE data
    varname_inc_bin : str
        Income bin variable name
    df_ranks : pd.DataFrame
        Income rank data from ACS

    Returns
    -------
    pd.Series
    """

    df = df.copy()
    # Household income is reported as income over the last 12 months. Align at the
    # beginning of the month and check fraction of past 12 months in current year.
    beg_month = df["date"] - pd.offsets.MonthBegin()
    # Fraction of last 12 months falling into current year
    frac = (beg_month.dt.month - 1) / 11
    # Select current or previous year based on fraction
    year = df["date"].dt.year - (frac < 0.5)

    df["year"] = year

    # Rescale to rank percentiles on [0, 100]
    df_ranks = df_ranks.copy()
    if df_ranks["rank"].max() <= 1.0:
        df_ranks["rank"] = df_ranks["rank"] * 100.0

    # Merge total household income
    varname_rank = varname_inc_bin + "_rank"
    df_ranks = df_ranks.rename(
        columns={"rank": varname_rank, "ibin": varname_inc_bin}
    )
    index_names = df.index.names
    if index_names is not None:
        df = df.reset_index(drop=False)

    df = df.merge(
        df_ranks[["year", varname_inc_bin, varname_rank]],
        how="left",
        on=["year", varname_inc_bin],
        validate="m:1",
    )

    if index_names is not None:
        df = df.set_index(index_names).sort_index()

    return df[varname_rank]
