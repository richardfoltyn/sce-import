import numpy as np
import pandas as pd


def import_file(fn: str) -> pd.DataFrame:
    # Skip first line which contains the license terms
    df = pd.read_excel(fn, skiprows=1)

    # Fix wave and interview date
    year = df['date'] // 100
    month = df['date'] % 100

    date = pd.to_datetime(
        pd.DataFrame({'year': year, 'month': month, 'day': np.ones_like(year)})
    )

    df['wave'] = date
    del df['date']
    df = df.rename(columns={'survey_date': 'date'})




    return df
