import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd

from SCE.enums import EmplTypeEnum



def import_file(df: pd.DataFrame) -> pd.DataFrame:
    logger = logging.getLogger()

    df = df.rename(columns={'date': 'wid', 'survey_date': 'date'})

    df = df.set_index(['userid', 'wid']).sort_index()

    df_new = pd.DataFrame(index=df.index)

    # Financially better or worse off than 12 months ago?
    df_new['Q1_financial_past12'] = df['Q1'].fillna(-1).astype(np.int8)

    # Financially better or worse off in 12 months?
    df_new['Q1_financial_next12'] = df['Q2'].fillna(-1).astype(np.int8)

    # % percent change to move primary residence in next 12 months?
    df_new['Q3_move'] = df['Q3']

    # % chance that unemployment will be higher 12 months from now?
    df_new['Q4_unrate_up'] = df['Q4new']

    # % chance that interest rates on savings will be higher 12 months from now?
    df_new['Q5_irate_up'] = df['Q5new']

    # % chance that stock prices will be higher 12 months from now?
    df_new['Q6_stocks_up'] = df['Q6new']

    # Merge questions Q8v2 and Q8v2part2
    df_new['Q8_infl'] = df['Q8v2part2']
    # Check if sign needs to be flipped
    deflation = df['Q8v2'] == 2
    if (df.loc[deflation, 'Q8v2part2'].fillna(0.0) <= 0).all():
        # Sign is already correct
        pass
    elif (df.loc[deflation, 'Q8v2part2'].fillna(0.0) >= 0).all():
        # Sign needs to be flipped
        df_new.loc[deflation, 'Q8_infl'] *= -1
    else:
        logger.warning('Q8v2part2 has ambiguous sign')

    # Q9: inflation forecast bins. Ignore the statistics they have computed from these
    for i in range(1, 11):
        df_new[f'Q9_infl_bin{i}'] = df[f'Q9_bin{i}']

    # --- Q9b: Inflation/deflation between 24-36 months from now ---
    # Merge questions Q9bv2 and Q9bv2part2
    df_new['Q9b_infl_3y'] = df['Q9bv2part2']
    # Check if sign needs to be flipped
    deflation = df['Q9bv2'] == 2
    if (df.loc[deflation, 'Q9bv2part2'].fillna(0.0) <= 0).all():
        # Sign is already correct
        pass
    elif (df.loc[deflation, 'Q9bv2part2'].fillna(0.0) >= 0).all():
        # Sign needs to be flipped
        df_new.loc[deflation, 'Q9b_infl_3y'] *= -1
    else:
        logger.warning('Q9bv2part2 has ambiguous sign')

    # Q9c: inflation forecast bins, months 24-36 from interview. Ignore the statistics
    # they have computed from these.
    for i in range(1, 11):
        df_new[f'Q9c_bin{i}'] = df[f'Q9c_bin{i}']

    # --- Q1a: Inflation/deflation between 48-60 months from now ---

    if 'Q1a' in df.columns:
        prefix = "Q1a"
        # Merge questions Q1a and Q1a_part2
        df_new[f'{prefix}_infl_5y'] = df[f'{prefix}_part2']
        # Check if sign needs to be flipped
        deflation = df[prefix] == 2
        if (df.loc[deflation, f'{prefix}_part2'].fillna(0.0) <= 0).all():
            # Sign is already correct
            pass
        elif (df.loc[deflation, f'{prefix}_part2'].fillna(0.0) >= 0).all():
            # Sign needs to be flipped
            df_new.loc[deflation, f'{prefix}_infl_5y'] *= -1
        else:
            logger.warning(f'{prefix}_part2 has ambiguous sign')

        # Q9new2: inflation forecast bins, months 48-60 from interview. Ignore the
        # statistics
        # they have computed from these.
        for i in range(1, 11):
            df_new[f'Q9new2_bin{i}'] = df[f'Q9new2_bin{i}']

    # --- Employment ---

    # Coded as indicator variable as multiple responses are permitted
    d = df.filter(regex='Q10_.*', axis=1)
    columns = d.columns.to_list()
    df_new[columns] = df[columns]

    options = (1, 2, 4, 5)
    columns = [f'Q10_{i}' for i in options]
    mask = (d[columns] == 1).any(axis=1)
    df_new['Q11'] = 0
    df_new.loc[mask, 'Q11'] = df.loc[mask, 'Q11'].fillna(0.0).astype(int)

    # Q12: Self-employed?
    # The questionaire does not specify the coding, assume 1 = work for someone else,
    # 2 = self-employed
    df_new['Q12new'] = df['Q12new']

    # Q14new: chance to leave current job in next 12 months
    df_new['Q14new'] = df['Q14new']

    # Q15: Looking for job? Yes = 1, No = 2
    df_new["Q15"] = df["Q15"]

    # Q16: How long have you been unemployed (in months)
    df_new['Q16'] = df['Q16']

    # Q17new: Chance to find and accept job in next 12 months
    df_new['Q17new'] = df['Q17new']

    # Q18new: Chance to find and accept job in next 3 months
    df_new['Q18new'] = df['Q18new']

    # Q19: How long have you been out of work (only if Q15 = 2)
    df_new['Q19'] = df['Q19']





    return df_new
