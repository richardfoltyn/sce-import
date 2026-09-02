# SCE Extract Variable Codebook

This document describes the processed variables in `sce_extract` produced by
[`src/main.py`](src/main.py). The unit of observation is a respondent in a survey
wave, identified by the `userid`–`wid` index.

## Conventions

- `NA` denotes a missing, inapplicable, or unclassifiable response unless stated
  otherwise. The categorical-value column lists nonmissing codes.
- Probabilities and percent chances are on a 0–100 scale.
- In the source column, `A` + `B` means that both fields are used, while `A` / `B`
  means that the fields are coalesced. The latter usually combines an
  initial-interview field with its repeat-interview counterpart.

## Contents

- [Panel identifiers and survey metadata](#panel-identifiers-and-survey-metadata)
- [Financial well-being and economic expectations](#financial-well-being-and-economic-expectations)
- [Inflation expectations](#inflation-expectations)
- [Employment, job search, and earnings](#employment-job-search-and-earnings)
- [Household finances, credit, housing, and government debt](#household-finances-credit-housing-and-government-debt)
- [Numerical and financial literacy](#numerical-and-financial-literacy)
- [Respondent characteristics](#respondent-characteristics)
- [Household characteristics and dynamics](#household-characteristics-and-dynamics)

## Panel identifiers and survey metadata

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `userid` | Respondent identifier; first index level | `userid` | — |
| `wid` | Survey-wave identifier in `YYYYMM` form; second index level | `date` | — |
| `date` | Calendar date of the interview | `survey_date` | — |
| `tenure` | Respondent's panel tenure in survey waves | `tenure` | — |
| `weight` | Survey sampling weight | `weight` | — |

## Financial well-being and economic expectations

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `financial_past_12m` | Financial situation relative to 12 months ago | `Q1` | `1` = much worse; `2` = somewhat worse; `3` = about the same; `4` = somewhat better; `5` = much better |
| `financial_12m` | Expected financial situation 12 months ahead | `Q2` | `1` = much worse; `2` = somewhat worse; `3` = about the same; `4` = somewhat better; `5` = much better |
| `prob_move_house` | Chance of moving primary residence within 12 months | `Q3` | — |
| `prob_unrate_up` | Chance the U.S. unemployment rate is higher in 12 months | `Q4new` | — |
| `prob_irate_up` | Chance savings-account interest rates are higher in 12 months | `Q5new` | — |
| `prob_stocks_up` | Chance U.S. stock prices are higher in 12 months | `Q6new` | — |

## Inflation expectations

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `infl_1y` | Signed point forecast for inflation over the next 12 months | `Q8v2` + `Q8v2part2` | — |
| `infl_1y_bin_mean` | Mean of the one-year inflation density | `Q9_mean` (from `Q9_bin1`–`Q9_bin10`) | — |
| `infl_1y_bin_var` | Variance of the one-year inflation density | `Q9_var` (from `Q9_bin1`–`Q9_bin10`) | — |
| `infl_1y_bin_median` | Median of the one-year inflation density | `Q9_cent50` (from `Q9_bin1`–`Q9_bin10`) | — |
| `infl_1y_bin_iqr` | Interquartile range of the one-year inflation density | `Q9_iqr` (from `Q9_bin1`–`Q9_bin10`) | — |
| `infl_1y_bin_prob_defl` | Probability of deflation over the next 12 months | `Q9_probdeflation` (from `Q9_bin1`–`Q9_bin10`) | — |
| `infl_3y` | Signed point forecast for inflation 24–36 months ahead | `Q9bv2` + `Q9bv2part2` | — |
| `infl_3y_bin_mean` | Mean of the 24–36-month inflation density | `Q9c_mean` (from `Q9c_bin1`–`Q9c_bin10`) | — |
| `infl_3y_bin_var` | Variance of the 24–36-month inflation density | `Q9c_var` (from `Q9c_bin1`–`Q9c_bin10`) | — |
| `infl_3y_bin_median` | Median of the 24–36-month inflation density | `Q9c_cent50` (from `Q9c_bin1`–`Q9c_bin10`) | — |
| `infl_3y_bin_iqr` | Interquartile range of the 24–36-month inflation density | `Q9c_iqr` (from `Q9c_bin1`–`Q9c_bin10`) | — |
| `infl_3y_bin_prob_defl` | Probability of deflation 24–36 months ahead | `Q9c_probdeflation` (from `Q9c_bin1`–`Q9c_bin10`) | — |
| `infl_5y` | Signed point forecast for inflation 48–60 months ahead | `Q1a` + `Q1apart2` | — |
| `infl_5y_bin_mean` | Mean of the 48–60-month inflation density | `Q9new2_mean` (from `Q9new2_bin1`–`Q9new2_bin10`) | — |
| `infl_5y_bin_var` | Variance of the 48–60-month inflation density | `Q9new2_var` (from `Q9new2_bin1`–`Q9new2_bin10`) | — |
| `infl_5y_bin_median` | Median of the 48–60-month inflation density | `Q9new2_cent50` (from `Q9new2_bin1`–`Q9new2_bin10`) | — |
| `infl_5y_bin_iqr` | Interquartile range of the 48–60-month inflation density | `Q9new2_iqr` (from `Q9new2_bin1`–`Q9new2_bin10`) | — |
| `infl_5y_bin_prob_defl` | Probability of deflation 48–60 months ahead | `Q9new2_probdeflation` (from `Q9new2_bin1`–`Q9new2_bin10`) | — |

Table notes:

- `infl_1y`: Combines the reported magnitude with the direction response; negative
  values denote deflation.
- `infl_1y_bin_var`: Summarizes the respondent's ten-bin density and is measured
  in squared percentage points.
- `infl_1y_bin_prob_defl`: Summarizes the respondent's ten-bin density; the raw
  0–1 probability is rescaled to 0–100.
- `infl_3y`: Combines the reported magnitude with the direction response; negative
  values denote deflation.
- `infl_3y_bin_var`: Summarizes the respondent's ten-bin density and is measured
  in squared percentage points.
- `infl_3y_bin_prob_defl`: Summarizes the respondent's ten-bin density; the raw
  0–1 probability is rescaled to 0–100.
- `infl_5y`: Combines the reported magnitude with the direction response; negative
  values denote deflation. It is available only when the five-year point-forecast
  questions are present; earlier observations are `NA`.
- `infl_5y_bin_mean`: Summarizes the respondent's ten-bin density when the
  five-year density questions are present; earlier observations are `NA`.
- `infl_5y_bin_var`: Summarizes the respondent's ten-bin density when available
  and is measured in squared percentage points; earlier observations are `NA`.
- `infl_5y_bin_median`: Summarizes the respondent's ten-bin density when the
  five-year density questions are present; earlier observations are `NA`.
- `infl_5y_bin_iqr`: Summarizes the respondent's ten-bin density when the
  five-year density questions are present; earlier observations are `NA`.
- `infl_5y_bin_prob_defl`: Summarizes the respondent's ten-bin density when
  available; the raw 0–1 probability is rescaled to 0–100, and earlier
  observations are `NA`.

## Employment, job search, and earnings

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `working` | Currently working full- or part-time | `Q10_1`–`Q10_10` | `0` = no; `1` = yes |
| `num_jobs` | Number of current jobs | `Q11` | — |
| `self_employed` | Main job is self-employment | `Q12new` | `0` = works for someone else; `1` = self-employed |
| `prob_lose_job` | Chance of losing the main/current job within 12 months | `Q13new` | — |
| `prob_leave_job` | Chance of voluntarily leaving the main/current job within 12 months | `Q14new` | — |
| `looking_for_job` | Currently looking for a job | `Q15` | `0` = no; `1` = yes |
| `prob_accept_job_12m` | Chance of finding and accepting a job within 12 months | `Q17new` | — |
| `prob_accept_job_3m` | Chance of finding and accepting a job within 3 months | `Q18new` | — |
| `jobless_length` | Months unemployed or out of work | `Q16` / `Q19` | — |
| `prob_search_job_12m` | Chance of starting a job search within 12 months | `Q20new` | — |
| `prob_search_job_3m` | Chance of starting a job search within 3 months | `Q21new` | — |
| `earnings_change` | Expected signed change in own-job earnings over 12 months | `Q23v2` + `Q23v2part2` | — |

Table notes:

- `working`: Full-time and part-time selections map to 1, observed nonworking
  categories map to 0, and an "Other"-only response remains `NA`.
- `earnings_change`: Combines the reported magnitude with the direction response;
  negative values denote an expected decrease.

## Household finances, credit, housing, and government debt

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `hh_inc_change` | Expected signed change in household income over 12 months | `Q25v2` + `Q25v2part2` | — |
| `hh_spending_change` | Expected signed change in household spending over 12 months | `Q26v2` + `Q26v2part2` | — |
| `taxes_change` | Expected signed change in total taxes over 12 months | `Q27v2` + `Q27v2part2` | — |
| `credit_cond_past_12m` | Credit availability relative to 12 months ago | `Q28` | `1` = much harder; `2` = somewhat harder; `3` = equally easy/hard; `4` = somewhat easier; `5` = much easier |
| `credit_cond_12m` | Expected credit availability in 12 months relative to now | `Q29` | `1` = much harder; `2` = somewhat harder; `3` = equally easy/hard; `4` = somewhat easier; `5` = much easier |
| `prob_miss_paym_3m` | Chance of missing a required debt payment within 3 months | `Q30new` | — |
| `house_price_change` | Expected signed change in national house prices over 12 months | `Q31v2` + `Q31v2part2` | — |
| `house_price_change_3y` | Expected signed change in national house prices 24–36 months ahead | `C2` + `C2part2` | — |
| `govt_debt_change` | Expected signed change in U.S. government debt over 12 months | `C3` + `C3part2` | — |

Table notes:

- `hh_inc_change`: Combines the reported magnitude with the direction response;
  negative values denote an expected decrease.
- `hh_spending_change`: Combines the reported magnitude with the direction
  response; negative values denote an expected decrease.
- `taxes_change`: Combines the reported magnitude with the direction response;
  negative values denote an expected decrease.
- `house_price_change`: Combines the reported magnitude with the direction
  response; negative values denote an expected decrease.
- `house_price_change_3y`: Combines the reported magnitude with the direction
  response; negative values denote an expected decrease.
- `govt_debt_change`: Combines the reported magnitude with the direction response;
  negative values denote an expected decrease.

## Numerical and financial literacy

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `num_lit_q1` | Half-price cost of a \$300 sofa, in dollars | `QNUM1` | — |
| `num_lit_q1_correct` | Correct sofa answer (`150`) | `QNUM1` + `tenure` | `0` = incorrect; `1` = correct |
| `num_lit_q2` | Value of \$200 after two years at 10% annual compound interest, in dollars | `QNUM2` | — |
| `num_lit_q2_correct` | Correct compound-interest answer (`242`) | `QNUM2` + `tenure` | `0` = incorrect; `1` = correct |
| `num_lit_q3` | Expected winners when 1,000 people each have a 1% chance | `QNUM3` | — |
| `num_lit_q3_correct` | Correct lottery answer (`10`) | `QNUM3` + `tenure` | `0` = incorrect; `1` = correct |
| `num_lit_q5` | Expected cases among 1,000 people at 10% prevalence | `QNUM5` | — |
| `num_lit_q5_correct` | Correct disease-prevalence answer (`100`) | `QNUM5` + `tenure` | `0` = incorrect; `1` = correct |
| `num_lit_q6` | Expected infections among 10,000 people at probability 0.0005 | `QNUM6` | — |
| `num_lit_q6_correct` | Correct infection-probability answer (`5`) | `QNUM6` + `tenure` | `0` = incorrect; `1` = correct |
| `num_lit_q8` | Purchasing power with 1% interest and 2% inflation | `QNUM8` | `1` = more than today; `2` = exactly the same; `3` = less than today |
| `num_lit_q8_correct` | Correct purchasing-power answer (`3`) | `QNUM8` + `tenure` | `0` = incorrect; `1` = correct |
| `num_lit_q9` | Whether a single stock is safer than a stock mutual fund | `QNUM9` | `1` = true; `2` = false |
| `num_lit_q9_correct` | Correct diversification answer (`2`) | `QNUM9` + `tenure` | `0` = incorrect; `1` = correct |

Table notes:

- `num_lit_q1_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.
- `num_lit_q2_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.
- `num_lit_q3_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.
- `num_lit_q5_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.
- `num_lit_q6_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.
- `num_lit_q8_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.
- `num_lit_q9_correct`: Is calculated only for an observed response from a new
  respondent (`tenure == 1`); other observations are `NA` because their
  questionnaire version cannot be established.

## Respondent characteristics

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `age_init` | Age at initial interview, propagated across waves; values outside 18–120 are set to `NA` | `Q32` | — |
| `female` | Respondent is female | `Q33` | `0` = no; `1` = yes |
| `hispanic` | Respondent is of Hispanic, Latino, or Spanish origin | `Q34` | `0` = no; `1` = yes |
| `black` | Respondent selected Black or African American as a race | `Q35_2` | `0` = no; `1` = yes |
| `college` | Respondent has a bachelor's, master's, doctoral, or professional degree | `Q36` | `0` = no; `1` = yes |
| `educ` | Four-category educational attainment | `Q36` | `1` = less than high school; `2` = high school or equivalent; `3` = some college or associate's degree; `4` = bachelor's degree or higher |
| `health` | Self-reported general health | `Q45b` | `1` = excellent; `2` = very good; `3` = good; `4` = fair; `5` = poor |
| `take_fin_risk` | Willingness to take financial risks | `QRA1` | Integer scale `1`–`7`: `1` = not willing at all; `7` = very willing |

Table notes:

- `age_init`: Uses the initial response, propagates it across the respondent's
  waves, and maps values outside 18–120 to `NA` before propagation.
- `female`: Uses the initial response and propagates it across the respondent's
  waves.
- `hispanic`: Uses the initial response and propagates it across the respondent's
  waves.
- `black`: Uses the initial `Q35_2` indicator and propagates it across the
  respondent's waves.
- `college`: Uses the initial response and propagates it across the respondent's
  waves; a `Q36` response of "Other" maps to `NA`.
- `educ`: Uses the initial response and propagates it across the respondent's
  waves; a `Q36` response of "Other" maps to `NA`.
- `health`: Is retained only where observed and is available from April 2015.
- `take_fin_risk`: Uses the initial response, propagates it across the respondent's
  waves, and is available from April 2015.

## Household characteristics and dynamics

| Variable | Brief description | Original variable(s) | Categorical values |
|---|---|---|---|
| `owner` | Respondent or partner owns the primary residence | `Q43` | `0` = rents; `1` = owns |
| `hh_changed` | Household composition changed since the previous survey | `D1` | `0` = unchanged; `1` = changed |
| `num_kids` | Number of co-resident children of any age | `Q45new_2`–`Q45new_5` / `D2new_2`–`D2new_5` | — |
| `same_employer` | Works at the same employer as at the previous survey | `DSAME` | `0` = different employer or not previously employed; `1` = same employer |
| `couple` | Currently married or living with a partner | `Q38` / `DQ38` | `0` = no; `1` = yes |
| `spouse_working` | Spouse/partner works full-time, part-time, or is self-employed | `HH2_1`–`HH2_11` / `DHH2_1`–`DHH2_11` | `0` = no; `1` = yes |
| `hh_inc_bin` | Combined pre-tax household income during the past 12 months | `Q47` / `D6` | `1` = less than \$10,000; `2` = \$10,000–\$19,999; `3` = \$20,000–\$29,999; `4` = \$30,000–\$39,999; `5` = \$40,000–\$49,999; `6` = \$50,000–\$59,999; `7` = \$60,000–\$74,999; `8` = \$75,000–\$99,999; `9` = \$100,000–\$149,999; `10` = \$150,000–\$199,999; `11` = \$200,000 or more |
| `hh_inc_bin_rank` | Person-weighted median ACS family-income rank for the income bin and reference year, on 0–1 | `Q47` / `D6` + `survey_date` + `year`, `ibin`, and `rank` in [`data/IPUMS_ftotinc_rank_by_year_sce_bins.csv`](data/IPUMS_ftotinc_rank_by_year_sce_bins.csv) | — |

Table notes:

- `owner`: Maps a `Q43` response of "Other" to `NA`.
- `num_kids`: Uses a complete initial `Q45new` household-composition state,
  replaces it with complete `D2new` updates when observed, carries the last
  complete state forward within the respondent, and then sums the child counts.
- `same_employer`: Maps a `DSAME` response of "Other" to `NA`.
- `spouse_working`: Combines initial `HH2` responses with repeat-interview `DHH2`
  updates. An "Other"-only response maps to `NA`, known nonworking statuses map to
  0, and the source questions are available from June 2014.
- `hh_inc_bin_rank`: Uses the previous calendar year for January–June interviews
  and the current calendar year for July–December interviews. When that ACS mapping
  is unavailable, it carries forward the most recent prior mapping separately
  within each income bin.
