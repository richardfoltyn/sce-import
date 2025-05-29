import logging

import numpy as np
import pandas as pd

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

    varname_id = "userid"
    varname_wid = "wid"
    df = df.rename(columns={"date": varname_wid, "survey_date": "date"})
    df = df.set_index([varname_id, varname_wid]).sort_index()

    # meta-variables to be copied directly
    columns = ["tenure", "weight"]
    df_new = df[columns].copy(deep=True)
    df_simple = df[columns].copy(deep=True)

    # Financially better or worse off than 12 months ago?
    df_new["Q1"] = df["Q1"].fillna(-1).astype(np.int8)
    df_simple["financial_past_12m"] = df_new["Q1"]

    # Financially better or worse off in 12 months?
    df_new["Q2"] = df["Q2"].fillna(-1).astype(np.int8)
    df_simple["financial_12m"] = df_new["Q2"]

    # % percent change to move primary residence in next 12 months?
    df_new["Q3"] = df["Q3"]
    df_simple["prob_move_house"] = df_new["Q3"]

    # % chance that unemployment will be higher 12 months from now?
    df_new["Q4new"] = df["Q4new"]
    df_simple["prob_unrate_up"] = df_new["Q4new"]

    # % chance that interest rates on savings will be higher 12 months from now?
    df_new["Q5new"] = df["Q5new"]
    df_simple["prob_irate_up"] = df_new["Q5new"]

    # % chance that stock prices will be higher 12 months from now?
    df_new["Q6new"] = df["Q6new"]
    df_simple["prob_stocks_up"] = df_new["Q6new"]

    # Merge questions Q8v2 and Q8v2part2
    varname = "Q8v2part2"
    df_new[varname] = df[varname]
    # Check if sign needs to be flipped
    deflation = df["Q8v2"] == 2
    flip_sign(df_new, varname, deflation)

    df_simple["infl_1y"] = df_new[varname]

    # Q9: inflation forecast bins.
    columns = [f"Q9_bin{i}" for i in range(1, 11)]
    df_new[columns] = df[columns]

    df_simple["infl_1y_bin_mean"] = df["Q9_mean"]
    df_simple["infl_1y_bin_var"] = df["Q9_var"]
    df_simple["infl_1y_bin_median"] = df["Q9_cent50"]
    df_simple["infl_1y_bin_iqr"] = df["Q9_iqr"]
    df_simple["infl_1y_bin_prob_defl"] = df["Q9_probdeflation"]

    # --- Q9b: Inflation/deflation between 24-36 months from now ---
    # Merge questions Q9bv2 and Q9bv2part2
    varname = "Q9bv2part2"
    df_new[varname] = df[varname]
    # Check if sign needs to be flipped
    deflation = df["Q9bv2"] == 2
    flip_sign(df_new, varname, deflation)

    df_simple["infl_3y"] = df_new[varname]

    # Q9c: inflation forecast bins, months 24-36 from interview.
    columns = [f"Q9c_bin{i}" for i in range(1, 11)]
    df_new[columns] = df[columns]

    # --- Q1a: Inflation/deflation between 48-60 months from now ---

    if "Q1a" in df.columns:
        varname = "Q1a_part2"
        # Merge questions Q1a and Q1a_part2
        df_new[varname] = df[varname]
        # Check if sign needs to be flipped
        deflation = df[varname] == 2
        flip_sign(df_new, varname, deflation)

        df_simple["infl_5y"] = df_new[varname]

        # Q9new2: inflation forecast bins, months 48-60 from interview.
        columns = [f"Q9new2_bin{i}" for i in range(1, 11)]
        df_new[columns] = df[columns]

    # --- Employment ---

    # Coded as indicator variable as multiple responses are permitted
    d = df.filter(regex="Q10_.*", axis=1)
    columns = d.columns.to_list()
    df_new[columns] = df[columns]

    df_simple["working"] = (df[["Q10_1", "Q10_2"]] == 1).any(axis=1).astype(np.uint8)

    mask = (d[[f"Q10_{i}" for i in (1, 2, 4, 5)]] == 1).any(axis=1)
    df_new["Q11"] = 0
    df_new.loc[mask, "Q11"] = df.loc[mask, "Q11"].fillna(0.0).astype(int)

    df_simple["num_jobs"] = df_new["Q11"]

    # Q12: Self-employed?
    # The questionaire does not specify the coding, assume 1 = work for someone else,
    # 2 = self-employed
    df_new["Q12new"] = df["Q12new"]
    df_simple["self_employed"] = (df_new["Q12new"] == 2).astype(int)

    # Q13new: change that R will lose main/current job
    df_new["Q13new"] = df["Q13new"]
    df_simple["prob_lose_job"] = df_new["Q13new"]

    # Q14new: chance to leave current job in next 12 months
    df_new["Q14new"] = df["Q14new"]
    df_simple["prob_leave_job"] = df_new["Q14new"]

    # Q15: Looking for job? Yes = 1, No = 2
    df_new["Q15"] = df["Q15"]
    df_simple["looking_for_job"] = (df_new["Q15"] == 1).astype(int)

    # Q16: How long have you been unemployed (in months)
    df_new["Q16"] = df["Q16"]
    # Check that this is missing whenever R is NOT looking for a job
    assert df_new.loc[df_new["Q15"] != 1, "Q16"].isna().all()

    # Q17new: Chance to find and accept job in next 12 months
    df_new["Q17new"] = df["Q17new"]
    df_simple["prob_accept_job_12m"] = df_new["Q17new"]

    # Q18new: Chance to find and accept job in next 3 months
    df_new["Q18new"] = df["Q18new"]
    df_simple["prob_accept_job_3m"] = df_new["Q18new"]

    # Q19: How long have you been out of work (only if Q15 = 2)
    df_new["Q19"] = df["Q19"]
    # Check that this is missing whenever R is *not* not looking for a job
    assert df_new.loc[df_new["Q15"] != 2, "Q19"].isna().all()

    # Merge Q16 and Q19: how long have you been unemployed / out of work?
    df_simple["jobless_length"] = merge_if_na(df_new[["Q16", "Q19"]])

    # Q20new: Chance to start looking for job in next 12 months
    df_new["Q20new"] = df["Q20new"]
    df_simple["prob_search_job_12m"] = df_new["Q20new"]

    # Q21new: Chance to start looking for job in next 3 months
    df_new["Q21new"] = df["Q21new"]
    df_simple["prob_search_job_3m"] = df_new["Q21new"]

    # Q22new: suppose you lost job this month, chance to find & accept job in
    # next 3 months
    df_new["Q22new"] = df["Q22new"]

    # Periodically create non-fragmented copies of DataFrames to avoid pandas warnings.
    df_new = df_new.copy()
    df_simple = df_simple.copy()

    # --- Earnings ---

    # Q23v2: Earnings increase/decrease over next 12 months
    df_new["Q23v2"] = df["Q23v2"]
    # Q23v2part2: percent increase/decrease in earnings
    varname = "Q23v2part2"
    df_new[varname] = df[varname]
    negative = df["Q23v2"] == 3
    flip_sign(df_new, varname, negative)

    df_simple["earnings_change"] = df_new[varname]

    # Q24: PMF over earnings changes
    d = df.filter(regex="Q24_.*", axis=1)
    columns = d.columns.to_list()
    df_new[columns] = df[columns]

    # Q25v2: Change in overall household income
    df_new["Q25v2"] = df["Q25v2"]
    # Q25v2part2: percent increase/decrease in household income
    varname = "Q25v2part2"
    df_new[varname] = df[varname]
    negative = df[varname] == 3
    flip_sign(df_new, varname, negative)

    df_simple["hh_income_change"] = df_new[varname]

    # --- Spending ---

    # Q26v2: total HH spending increase/decrease?
    df_new["Q26v2"] = df["Q26v2"]
    # Q26v2part2: percent increase/decrease in household spending
    varname = "Q26v2part2"
    df_new[varname] = df[varname]
    negative = df[varname] == 3
    flip_sign(df_new, varname, negative)

    df_simple["hh_spending_change"] = df_new[varname]

    # --- Taxes ---

    # Q27v2: total amount of taxes increases/decreases?
    df_new["Q27v2"] = df["Q27v2"]
    # Q27v2part2: percent increase/decrease in total taxes
    varname = "Q27v2part2"
    df_new[varname] = df[varname]
    negative = df[varname] == 3
    flip_sign(df_new, varname, negative)

    df_simple["taxes_change"] = df_new[varname]

    # --- Credit conditions ---

    # Q28: credit conditions compared to past 12 months
    df_new["Q28"] = df["Q28"]
    df_simple["credit_cond_past12m"] = df_new["Q28"]

    # Q29: Credit conditions 12 months from now
    df_new["Q29"] = df["Q29"]
    df_simple["credit_cond_12m"] = df_new["Q29"]

    # Q30new: prob. to miss debt payment over next 3 months
    df_new["Q30new"] = df["Q30new"]
    df_simple["prob_miss_paym_3m"] = df_new["Q30new"]

    # --- House prices ---

    # Q31v2: nationwide house prices increase/decrease?
    df_new["Q31v2"] = df["Q31v2"]
    # Q31v2part2: percent increase/decrease in house prices
    varname = "Q31v2part2"
    df_new[varname] = df[varname]
    negative = df[varname] == 3
    flip_sign(df_new, varname, negative)

    df_simple["house_price_change"] = df[varname]

    # C1: PMF over national house price changes
    d = df.filter(regex="C1_.*", axis=1)
    columns = d.columns.to_list()
    df_new[columns] = df[columns]

    # C2: nationwide house prices increase/decrease between 24 and 36 months from now?
    df_new["C2"] = df["C2"]
    # C2part2: percent increase/decrease in house prices
    varname = "C2part2"
    df_new[varname] = df[varname]
    negative = df[varname] == 3
    flip_sign(df_new, varname, negative)

    df_simple["house_price_change_3y"] = df_new[varname]

    # --- Government debt ---

    # C2: nationwide house prices increase/decrease between 24 and 36 months from now?
    df_new["C3"] = df["C3"]
    # C3part2: percent increase/decrease in house prices
    varname = "C3part2"
    df_new[varname] = df[varname]
    negative = df[varname] == 3
    flip_sign(df_new, varname, negative)

    # Periodically create non-fragmented copies of DataFrames to avoid pandas warnings.
    df_new = df_new.copy()
    df_simple = df_simple.copy()

    # --- Numerical literacy questions ---

    # QNUM1: Compute 50% discounted price from $300
    df_new["QNUM1"] = df["QNUM1"]
    df_simple["num_lit_q1"] = df_new["QNUM1"]
    df_simple["num_lit_q1_correct"] = np.where(
        df_simple["num_lit_q1"].notna(), df_simple["num_lit_q1"] == 150, np.nan
    )

    # QNUM2: Gross interest of 10% on $200 after 2 years
    df_new["QNUM2"] = df["QNUM2"]
    df_simple["num_lit_q2"] = df_new["QNUM2"]
    df_simple["num_lit_q2_correct"] = np.where(
        df_simple["num_lit_q2"].notna(),
        (df_simple["num_lit_q2"] - 200 * 1.1**2).abs() < 1.0e-6,
        np.nan,
    )

    # QNUM3: Number of lottery winners out of 1,000 if chance is 1%
    df_new["QNUM3"] = df["QNUM3"]
    df_simple["num_lit_q3"] = df_new["QNUM3"]
    df_simple["num_lit_q3_correct"] = np.where(
        df_simple["num_lit_q3"].notna(),
        df_simple["num_lit_q3"] == 10,
        np.nan,
    )

    # QNUM5: Expected number of people with disease out of 1,000 if chance = 10%
    df_new["QNUM5"] = df["QNUM5"]
    df_simple["num_lit_q5"] = df_new["QNUM5"]
    df_simple["num_lit_q5_correct"] = np.where(
        df_simple["num_lit_q5"].notna(),
        df_simple["num_lit_q5"] == 100,
        np.nan,
    )

    # QNUM6: Expected number of infected out of 10,000 if chance = 0.0005
    df_new["QNUM6"] = df["QNUM6"]
    df_simple["num_lit_q6"] = df_new["QNUM6"]
    df_simple["num_lit_q6_correct"] = np.where(
        df_simple["num_lit_q6"].notna(),
        df_simple["num_lit_q6"] == 10000 * 0.0005,
        np.nan,
    )

    # QNUM8: Big 3: interest rate vs. inflation question
    # Interest rate = 1%, inflation = 2%.
    # Answers: (1) more than today (2) exactly the same (3) less than today
    df_new["QNUM8"] = df["QNUM8"]
    df_simple["num_lit_q8"] = df_new["QNUM8"]
    df_simple["num_lit_q8_correct"] = np.where(
        df_simple["num_lit_q8"].notna(),
        df_simple["num_lit_q8"] == 3,
        np.nan,
    )

    # QNUM9: Big 3: Buying a single company stock is safer than mutual fund
    # Answers: (1) True (2) False
    df_new["QNUM9"] = df["QNUM9"]
    df_simple["num_lit_q9"] = df_new["QNUM9"]
    df_simple["num_lit_q9_correct"] = np.where(
        df_simple["num_lit_q9"].notna(),
        df_simple["num_lit_q9"] == 2,
        np.nan,
    )

    # --- Demographic questions ---

    # Q32: Current age (only asked of now respondents)
    df_new["Q32"] = tile_const(df["Q32"], varname_id, int)

    # Broadcast age across all waves since it does not seem to be asked again.
    df_simple["age_init"] = df_new["Q32"]

    # Q33: gender: (1) Female (2) Male
    df_new["Q33"] = tile_const(df["Q33"], varname_id, np.uint8)
    female = df_new["Q33"].map({1: 1, 2: 0}, na_action="ignore")
    df_simple["female"] = female

    # Q34: Hispanic
    df_new["Q34"] = tile_const(df["Q34"], varname_id, np.uint8)
    hispanic = df_new["Q34"].map({1: 1, 2: 0}, na_action="ignore")
    df_simple["hispanic"] = hispanic

    # Q35: Races (multiple responses possible)
    d = df.filter(regex="Q35.*", axis=1)
    races = tile_const(d, varname_id, np.uint8)
    df_new = pd.concat((df_new, d), axis=1)
    df_simple["black"] = races["Q35_2"]

    # Q36: Highest level of education
    df_new["Q36"] = tile_const(df["Q36"], varname_id, np.uint8)
    df_simple["college"] = np.where(
        df_new["Q36"].notna(), df_new["Q36"].isin((5, 6, 7, 8)), np.nan
    )
    # Coarser education with 4 categories: LT HS, HS, Some college, College degree
    df_simple["educ"] = df_new["Q36"].map(
        {1: 1, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4, 7: 4, 8: 4}, na_action="ignore"
    )

    # Q37: How long working at current job? (categorical)
    df_new["Q37"] = df["Q37"]

    # Q38: Married or living with partner?
    df_new["Q38"] = df["Q38"]
    couple = df_new["Q38"].map({1: 1, 2: 0}, na_action="ignore")
    df_simple["couple_init"] = tile_const(couple, varname_id, np.uint8)

    # HH2: Spouses employment situation?
    if "HH2" in df.columns:
        df_new["HH2"] = df["HH2"]

    # Q39 and Q40 don't seem to be present in public data set

    # 41: How long have you lived at primary residence?
    df_new["Q41"] = df["Q41"]

    # 42: How many years in total lived in current state?
    df_new["Q42"] = df["Q42"]

    # Q43: Rent/own current residence
    df_new["Q43"] = df["Q43"]
    df_simple["owner"] = df_new["Q43"].map({1: 1, 2: 0, 3: 0}, na_action="ignore")

    # Q44: Own any other homes?
    df_new["Q44"] = df["Q44"]

    # Q45new: Number of other HH members (multiple variables for multiple categories)
    d = df.filter(regex="Q45new_.*", axis=1)
    df_new = pd.concat((df_new, d), axis=1)

    kids = df[["Q45new_2", "Q45new_3", "Q45new_3", "Q45new_4"]].sum(axis=1, min_count=4)
    if kids.notna().all():
        kids = kids.astype(int)
    df_simple["num_kids"] = kids

    # Q45b: self-reported health
    df_new["Q45b"] = df["Q45b"]
    df_simple["health"] = try_cast(df_new["Q45b"], np.uint8)

    # Q46: Financial decision making
    df_new["Q46"] = tile_const(df["Q46"], varname_id, np.uint8)

    # QRA1: Willingness to take financial risk
    if "QRA1" in df.columns:
        df_new['QRA1'] = tile_const(df["QRA1"], varname_id, np.uint8)

        df_simple["take_fin_risk"] = df_new['QRA1']

    # QRA2: Willingness to take risk in daily activities
    if "QRA2" in df.columns:
        df_new["QRA2"] = tile_const(df["QRA2"], varname_id, np.uint8)

    # Q47: Total pre-tax family income during the past 12 months
    df_new["Q47"] = df["Q47"]
    df_simple["fam_income"] = df_new["Q47"]

    return df_new, df_simple
