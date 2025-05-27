import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd

from SCE.enums import WELLBEING_LABELS, WELLBEING_CODES


# def to_categorical(data: pd.Series, codes: Sequence, labels: Sequence, ordered=True):
#
#     d = pd.Categorical(data, categories=codes, ordered=ordered)
#     d = d.rename_categories(labels)
#
#     s = pd.Series(d, index=data.index)
#
#     assert (s.cat.codes == data).all()
#
#     return s


def import_file(fn: str) -> pd.DataFrame:

    logger = logging.getLogger()

    # Skip first line which contains the license terms
    logger.info(f'Reading in {fn}')
    df = pd.read_excel(fn, skiprows=1, nrows=10000)

    df = df.rename(columns={'date': 'wave', 'survey_date': 'date'})

    df = df.set_index(['userid', 'wave']).sort_index()

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
    df_new['Q5_savrate_up'] = df['Q5new']

    # % chance that stock prices will be higher 12 months from now?
    df_new['Q6_stocks_up'] = df['Q6new']

    # Merge questions Q8v2 and Q8v2part2
    df_new['Q8_infl'] =  df['Q8v2part2']
    # Check if sign needs to be flipped
    deflation = df['Q8v2'] == 2
    if (df.loc[deflation, 'Q8v2part2'].fillna(0.0) <= 0).all():
        # Sign is already correct
        pass
    elif (df.loc[deflation, 'Q8v2part2'].fillna(0.0) >= 0).all():
        # Sign needs to be flipped
        df.loc[deflation, 'Q8_infl'] *= -1
    else:
        logger.warning('Q8v2part2 has ambiguous sign')

    # Q9: inflation forecast bins. Ignore the statistics they have computed from these
    for i in range(1, 11):
        df_new[f'Q9_infl_bin{i}'] = df[f'Q9_bin{i}']

    # Q9b: Inflation/deflation between 24-36 months from now
    # Merge questions Q9bv2 and Q9bv2part2
    df_new['Q9b_infl_3y'] =  df['Q9bv2part2']
    # Check if sign needs to be flipped
    deflation = df['Q9bv2'] == 2
    if (df.loc[deflation, 'Q9bv2part2'].fillna(0.0) <= 0).all():
        # Sign is already correct
        pass
    elif (df.loc[deflation, 'Q9bv2part2'].fillna(0.0) >= 0).all():
        # Sign needs to be flipped
        df.loc[deflation, 'Q9b_infl_3y'] *= -1
    else:
        logger.warning('Q9bv2part2 has ambiguous sign')

    # Q9c: inflation forecast bins, months 24-36 from interview. Ignore the statistics
    # they have computed from these.
    for i in range(1, 11):
        df_new[f'Q9c_bin{i}'] = df[f'Q9c_bin{i}']

    return df_new
