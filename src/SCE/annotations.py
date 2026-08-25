"""
Variable labels mappings for original and processed SCE survey variables.

- VARIABLE_LABELS_ORIG: Raw/original question labels.
- VARIABLE_LABELS: Modern/clean question labels.
- VARIABLE_LABELS_FULL: Complete labels for the processed full output.
- VALUE_LABELS: Categorical value labels for encoded response codes.

Author: Richard Foltyn
"""

from collections.abc import Iterable

from SCE.enums import INCOME_CATEGORIES, Educ4Enum, EmplStatusEnum, WellBeingEnum

VARIABLE_LABELS_ORIG: dict[str, str] = {
    "tenure": "Tenure on survey",
    "weight": "Sampling weight",
    "Q1": "Financially better/worse off than 12 months ago",
    "Q2": "Financially better/worse off 12 months from now",
    "Q3": "Prob to move house",
    "Q4new": "Prob unemployment higher in 12 months",
    "Q5new": "Prob interest rates higher in 12 months",
    "Q6new": "Prob stocks higher in 12 months",
    "Q8v2": "Inflation/deflation over next 12 months?",
    "Q8v2part2": "Rate of inflation/deflation over next 12 months",
    "Q9": "Prob of different inflation rates over the next 12 months?",
    "Q9bv2": "Will there be inflation or deflation 24 to 36 months from now?",
    "Q9bv2part2": "Rate of inflation/deflation 24 to 36 months from now",
    "Q9c": "Prob of different inflation rates 24 to 36 months from now",
    "Q1a": "Will there be inflation or deflation 48 to 60 months from now?",
    "Q1apart2": "Rate of inflation/deflation 48 to 60 months from now",
    "Q9new2": "Prob of different inflation rates 48 to 60 months from now",
    "Q10": "Current employment situation",
    "Q11": "Number of jobs",
    "Q12new": "Do you work for someone else or are you self-employed?",
    "ES1": "What type of self-employed work do you do?",
    "ES2": "How many paid employees does your business have?",
    "ES3new": "Chance your business will have more workers next year?",
    "ES4": "How many hours per week have you worked recently?",
    "ES5": "How many hours per week do you expect to work?",
    "Q13new": "Prob to lose job over next 12 months",
    "Q14new": "Prob to leave job over next 12 months",
    "Q15": "Looking for job?",
    "Q16": "How long have you been unemployed?",
    "Q17new": "Prob to accept job over next 12 months",
    "Q18new": "Prob to accept job over next 3 months",
    "Q19": "How long have you been out of work?",
    "Q20new": "Prob to start looking for a job within 12 months",
    "Q21new": "Prob to start looking for a job within 3 months?",
    "Q22new": "Prob to accept job over next 3 months if lost job",
    "Q23v2": "Earnings increase/decrease",
    "Q23v2part2": "Percent change in earnings",
    "Q24": "Chance your job earnings will change by a certain percent?",
    "Q25v2": "HH income increase/decrease",
    "Q25v2part2": "Percent change in HH income",
    "Q26v2": "HH spending increase/decrease",
    "Q26v2part2": "Percent change in HH spending",
    "Q27v2": "Taxes increase/decrease",
    "Q27v2part2": "Percent change in taxes",
    "Q28": "Credit conditions vs 12 months ago",
    "Q29": "Credit conditions in 12 months",
    "Q30new": "Prob to miss debt payment over 3 months?",
    "Q31v2": "House prices increase/decrease",
    "Q31v2part2": "Percent change in house prices",
    "C1": "Chance home prices will change by a certain percent?",
    "C2": "House prices incr/decr 24 to 36 months from now",
    "C2part2": "% change in house prices 24 to 36 months from now",
    "C3": "Gov debt increase/decrease",
    "C3part2": "Percent change in government debt",
    "C4info": "How will prices of items change in twelve months?",
    "QNUM1": "A $300 sofa is half price. What is the cost?",
    "QNUM2": "$200 savings earns 10% yearly. Total after two years?",
    "QNUM3": "1% chance of winning. How many winners out of 1000?",
    "QNUM5": "10% get a disease. How many out of 1,000?",
    "QNUM6": "Infection chance 0.0005. How many infected out of 10,000?",
    "QNUM8": "Interest 1%, inflation 2%. Can you buy more/less?",
    "QNUM9": "Single stock safer than MF",
    "Q32": "Initial age",
    "Q33": "Gender",
    "Q34": "Hispanic/Latino?",
    "Q35": "Race",
    "Q36": "Education",
    "Q37": "How long in current job?",
    "Q38": "Married/living with partner?",
    "HH2": "Partner's employment status",
    "Q39": "ZIP code",
    "Q40": "State of residence",
    "Q41": "Years lived in current residence",
    "Q42": "Years lived in current state?",
    "Q43": "Own/rent residence?",
    "Q43a": "In whose name is your home owned or rented?",
    "Q44": "Own any other homes?",
    "Q45new": "How many people live in your household besides you?",
    "Q45b": "Self-reported health",
    "Q46": "Financial decision making",
    "QRA1": "Willingness to take financial risks?",
    "QRA2": "Willingness to take risks in daily activities?",
    "Q47": "Total HH income during past 12 months",
    "D1": "Current HH same as at last survey?",
    "D2new": "How many people currently live in your household?",
    "D3": "Moved since last survey?",
    "D4": "What is your current ZIP code?",
    "D5": "In which state do you currently live?",
    "DSAME": "Same job as last survey?",
    "dQ38": "Married/living with partner?",
    "dHH2": "Partner's employment status",
    "D6": "Total HH income during past 12 months",
    "Q48": "How interesting did you find this survey?",
    "Q49": "Do you have any other comments about the survey?",
}

VARIABLE_LABELS: dict[str, str] = {
    # Panel identifiers (written as columns when write_index=True in to_stata)
    "userid": "Respondent identifier",
    "wid": "Wave identifier (YYYYMM)",
    # Meta-variables
    "tenure": "Tenure on survey",
    "weight": "Sampling weight",
    "date": "Interview date",
    # Financial well-being (WellBeingEnum: 1=Much worse, 5=Much better)
    "financial_past_12m": "Financially better/worse off than 12 months ago",
    "financial_12m": "Financially better/worse off 12 months from now",
    # Expectations
    "prob_move_house": "Prob to move house",
    "prob_unrate_up": "Prob unemployment higher in 12 months",
    "prob_irate_up": "Prob interest rates higher in 12 months",
    "prob_stocks_up": "Prob stocks higher in 12 months",
    # Inflation — point forecasts
    "infl_1y": "Rate of inflation/deflation over next 12 months",
    "infl_3y": "Rate of inflation/deflation 24 to 36 months from now",
    "infl_5y": "Rate of inflation/deflation 48 to 60 months from now",
    # Inflation — 1-year density summaries
    "infl_1y_bin_mean": "Mean of expected inflation rate over next 12 months",
    "infl_1y_bin_var": "Variance of expected inflation rate over next 12 months",
    "infl_1y_bin_median": "Median of expected inflation rate over next 12 months",
    "infl_1y_bin_iqr": "IQR of expected inflation rate over next 12 months",
    "infl_1y_bin_prob_defl": "Probability of deflation over next 12 months",
    # Inflation — 3-year density summaries
    "infl_3y_bin_mean": "Mean of expected inflation rate 24 to 36 months from now",
    "infl_3y_bin_var": "Variance of expected inflation rate 24 to 36 months from now",
    "infl_3y_bin_median": "Median of expected inflation rate 24 to 36 months from now",
    "infl_3y_bin_iqr": "IQR of expected inflation rate 24 to 36 months from now",
    "infl_3y_bin_prob_defl": "Probability of deflation 24 to 36 months from now",
    # Inflation — 5-year density summaries
    "infl_5y_bin_mean": "Mean of expected inflation rate 48 to 60 months from now",
    "infl_5y_bin_var": "Variance of expected inflation rate 48 to 60 months from now",
    "infl_5y_bin_median": "Median of expected inflation rate 48 to 60 months from now",
    "infl_5y_bin_iqr": "IQR of expected inflation rate 48 to 60 months from now",
    "infl_5y_bin_prob_defl": "Probability of deflation 48 to 60 months from now",
    # Employment
    "working": "Currently working?",
    "num_jobs": "Number of jobs",
    "self_employed": "Self-employed?",
    "prob_lose_job": "Prob to lose job over next 12 months",
    "prob_leave_job": "Prob to leave job over next 12 months",
    "looking_for_job": "Looking for job?",
    "prob_accept_job_12m": "Prob to accept job over next 12 months",
    "prob_accept_job_3m": "Prob to accept job over next 3 months",
    "jobless_length": "How long unempl/out of work?",
    "prob_search_job_12m": "Prob to start looking for a job within 12 months",
    "prob_search_job_3m": "Prob to start looking for a job within 3 months?",
    # Income and spending changes
    "earnings_change": "Percent change in earnings",
    "hh_inc_change": "Percent change in HH income",
    "hh_spending_change": "Percent change in HH spending",
    "taxes_change": "Percent change in taxes",
    # Credit conditions (Q28/Q29: 1=Much harder, 3=Equally easy/hard, 5=Much easier)
    "credit_cond_past_12m": "Credit conditions vs 12 months ago",
    "credit_cond_12m": "Credit conditions in 12 months",
    # Other financial
    "prob_miss_paym_3m": "Prob to miss debt payment over 3 months?",
    "house_price_change": "Percent change in house prices",
    "house_price_change_3y": "Percent change in house prices 24 to 36 months from now",
    "govt_debt_change": "Percent change in government debt",
    # Numerical literacy
    "num_lit_q1": "A $300 sofa is half price. What is the cost?",
    "num_lit_q1_correct": "Num Q1 correct",
    "num_lit_q2": "$200 savings earns 10% yearly. Total after two years?",
    "num_lit_q2_correct": "Num Q2 correct",
    "num_lit_q3": "1% chance of winning. How many winners out of 1000?",
    "num_lit_q3_correct": "Num Q3 correct",
    "num_lit_q5": "10% get a disease. How many out of 1,000?",
    "num_lit_q5_correct": "Num Q5 correct",
    "num_lit_q6": "Infection chance 0.0005. How many infected out of 10,000?",
    "num_lit_q6_correct": "Num Q6 correct",
    "num_lit_q8": "Interest 1%, inflation 2%. Can you buy more/less?",
    "num_lit_q8_correct": "Num Q8 correct",
    "num_lit_q9": "Single stock safer than MF",
    "num_lit_q9_correct": "Num Q9 correct",
    # Demographics
    "age_init": "Initial age",
    "female": "Female?",
    "hispanic": "Hispanic/Latino?",
    "black": "Black/AA?",
    "educ": "Education",
    "college": "College degree?",
    "owner": "Owns primary residence?",
    "num_kids": "Number of kids",
    # Health (Q45b: 1=Excellent, 2=Very good, 3=Good, 4=Fair, 5=Poor)
    "health": "Self-reported health",
    "take_fin_risk": "Willingness to take financial risks?",
    # HH income (11 bins from the SCE questionnaire, Q47)
    "hh_inc_bin": "Total HH income bin (1-11)",
    # ACS income rank (0-1) conditional on income bin and survey year
    "hh_inc_bin_rank": "ACS income rank for HH income bin",
    # Full-output equivalent of hh_inc_bin_rank (Q47_rank appears only in df_full)
    "Q47_rank": "ACS income rank for HH income bin (full output)",
    # HH dynamics (repeat-interview variables)
    # D1 coding: 1=unchanged, 2=changed; derived hh_changed is 1 when changed, 0 when unchanged
    "hh_changed": "HH changed since last survey",
    "same_employer": "Same job as last survey?",
    "couple": "Married/living with partner?",
    "spouse_working": "Spouse/partner currently working?",
}


_DENSITY_BIN_DESCRIPTIONS: dict[int, str] = {
    1: "+12% or more",
    2: "+8% to +12%",
    3: "+4% to +8%",
    4: "+2% to +4%",
    5: "0% to +2%",
    6: "-2% to 0%",
    7: "-4% to -2%",
    8: "-8% to -4%",
    9: "-12% to -8%",
    10: "-12% or less",
}

_PARTNER_EMPLOYMENT_CATEGORIES: dict[int, str] = {
    1: "Working full-time for someone",
    2: "Working part-time for someone",
    3: "Self-employed",
    4: "Not working, but would like to work",
    5: "Temporarily laid off",
    6: "On sick or other leave",
    7: "Permanently disabled or unable to work",
    8: "Retiree or early retiree",
    9: "Student, at school or in training",
    10: "Homemaker",
    11: "Other",
}

_RACE_CATEGORIES: dict[int, str] = {
    1: "White",
    2: "Black or African American",
    3: "American Indian or Alaska Native",
    4: "Asian",
    5: "Native Hawaiian or Other Pacific Islander",
    6: "Other",
}

_HOUSEHOLD_COMPOSITION_CATEGORIES: dict[int, str] = {
    1: "Spouse/partner",
    2: "Children age 25 or older",
    3: "Children age 18 to 24",
    4: "Children age 6 to 17",
    5: "Children age 5 or younger",
    6: "Respondent's or partner's parents",
    7: "Other relatives",
    8: "Non-relatives",
    9: "Lives alone",
}

_DENSITY_SUMMARY_LABELS: dict[str, str] = {
    "cent25": "25th percentile",
    "cent50": "Median",
    "cent75": "75th percentile",
    "iqr": "IQR",
    "mean": "Mean",
    "probdeflation": "Probability of a negative change",
    "var": "Variance",
}

_FULL_FAMILY_LABELS: dict[str, str] = {
    **{
        f"Q9_bin{code}": f"1y inflation rate: P({description})"
        for code, description in _DENSITY_BIN_DESCRIPTIONS.items()
    },
    **{
        f"Q9c_bin{code}": f"3y inflation rate: P({description})"
        for code, description in _DENSITY_BIN_DESCRIPTIONS.items()
    },
    **{
        f"Q9new2_bin{code}": f"5y inflation rate: P({description})"
        for code, description in _DENSITY_BIN_DESCRIPTIONS.items()
    },
    **{
        f"Q9new2_{suffix}": f"5y inflation density: {description}"
        for suffix, description in _DENSITY_SUMMARY_LABELS.items()
    },
    **{
        f"Q10_{int(status)}": f"Employment status: {status}"
        for status in EmplStatusEnum
    },
    **{
        f"Q24_bin{code}": f"12m earnings change: P({description})"
        for code, description in _DENSITY_BIN_DESCRIPTIONS.items()
    },
    **{
        f"Q24_{suffix}": f"Earnings density: {description}"
        for suffix, description in _DENSITY_SUMMARY_LABELS.items()
    },
    **{
        f"C1_bin{code}": f"1y house-price change: P({description})"
        for code, description in _DENSITY_BIN_DESCRIPTIONS.items()
    },
    **{
        f"C1_{suffix}": f"House-price density: {description}"
        for suffix, description in _DENSITY_SUMMARY_LABELS.items()
    },
    **{
        f"Q35_{code}": f"Race selected: {description}"
        for code, description in _RACE_CATEGORIES.items()
    },
    **{
        f"HH2_{code}": f"Partner employment: {description}"
        for code, description in _PARTNER_EMPLOYMENT_CATEGORIES.items()
    },
    **{
        f"Q45new_{code}": f"HH composition: {description}"
        for code, description in _HOUSEHOLD_COMPOSITION_CATEGORIES.items()
    },
}

# The full output retains source-style question names, while its panel identifiers,
# interview date, and ACS rank are introduced by processing. Keep the two namespaces
# separate so full-output coverage does not depend on the reduced-extract labels.
VARIABLE_LABELS_FULL: dict[str, str] = {
    **VARIABLE_LABELS_ORIG,
    **_FULL_FAMILY_LABELS,
    **{name: VARIABLE_LABELS[name] for name in ("userid", "wid", "date", "Q47_rank")},
}


# Financial well-being (Q1/Q2): codes 1-5 per WellBeingEnum.
# Code -1 is used as a fill-in placeholder for structurally missing responses.
_WELL_BEING_LABELS: dict[int, str] = {int(e): str(e) for e in WellBeingEnum}

# Binary 0/1 indicators derived from yes/no questionnaire responses
_BINARY_LABELS: dict[int, str] = {0: "No", 1: "Yes"}

_FULL_BINARY_INDICATORS: frozenset[str] = frozenset(
    {f"Q10_{code}" for code in range(1, 11)}
    | {f"Q35_{code}" for code in range(1, 7)}
    | {f"HH2_{code}" for code in range(1, 12)}
    | {"Q45new_9"}
)

# Credit conditions (Q28/Q29): 1=Much harder ... 5=Much easier.
# Verified against questionnaire text (Q28, Q29).
_CREDIT_COND_LABELS: dict[int, str] = {
    1: "Much harder",
    2: "Somewhat harder",
    3: "Equally easy/hard",
    4: "Somewhat easier",
    5: "Much easier",
}

# Self-reported health (Q45b): 1=Excellent ... 5=Poor.
# Verified against questionnaire text (Q45b).
_HEALTH_LABELS: dict[int, str] = {
    1: "Excellent",
    2: "Very good",
    3: "Good",
    4: "Fair",
    5: "Poor",
}

# Coarse education (Educ4Enum): 1=<HS, 2=HS, 3=Some college, 4=College+
_EDUC4_LABELS: dict[int, str] = {int(e): str(e) for e in Educ4Enum}

VALUE_LABELS: dict[str, dict[int, str]] = {
    **dict.fromkeys(_FULL_BINARY_INDICATORS, _BINARY_LABELS),
    # Financial well-being (code -1 = fillna placeholder for structurally missing)
    "Q1": _WELL_BEING_LABELS,
    "financial_past_12m": _WELL_BEING_LABELS,
    "Q2": _WELL_BEING_LABELS,
    "financial_12m": _WELL_BEING_LABELS,
    # HH income bins (codes 1-11, see INCOME_CATEGORIES in enums.py)
    "Q47": INCOME_CATEGORIES,
    "hh_inc_bin": INCOME_CATEGORIES,
    # Credit conditions (codes 1-5 from Q28/Q29)
    "Q28": _CREDIT_COND_LABELS,
    "credit_cond_past_12m": _CREDIT_COND_LABELS,
    "Q29": _CREDIT_COND_LABELS,
    "credit_cond_12m": _CREDIT_COND_LABELS,
    # Self-reported health (codes 1-5 from Q45b)
    "Q45b": _HEALTH_LABELS,
    "health": _HEALTH_LABELS,
    # Coarse education (codes 1-4 from Educ4Enum)
    "educ": _EDUC4_LABELS,
    # Binary (0=No, 1=Yes) indicators
    "working": _BINARY_LABELS,
    "female": _BINARY_LABELS,
    "hispanic": _BINARY_LABELS,
    "black": _BINARY_LABELS,
    "college": _BINARY_LABELS,
    "owner": _BINARY_LABELS,
    # hh_changed: 1 = composition changed since last survey; 0 = unchanged
    "hh_changed": _BINARY_LABELS,
    "looking_for_job": _BINARY_LABELS,
    "self_employed": _BINARY_LABELS,
    "couple": _BINARY_LABELS,
    "spouse_working": _BINARY_LABELS,
    "same_employer": _BINARY_LABELS,
}


def check_label_coverage(
    columns: Iterable[str],
    labels: dict[str, str],
) -> tuple[set[str], set[str]]:
    """Return columns without a label and label keys with no matching column.

    Parameters
    ----------
    columns
        Column names present in the output frame (and any index levels that
        will be written as columns, e.g. when using ``write_index=True``).
    labels
        Variable label mapping to audit.

    Returns
    -------
    unlabeled
        Column names that have no entry in ``labels``.
    phantom
        Keys in ``labels`` that do not appear in ``columns``.

    Notes
    -----
    ``phantom`` is non-empty when a label key refers to a column that is only
    present in one output (e.g. ``Q47_rank`` only appears in ``df_full``).
    Such entries are not errors by themselves; the caller decides which phantom
    keys are acceptable.
    """
    column_set = set(columns)
    label_set = set(labels)
    return column_set - label_set, label_set - column_set
