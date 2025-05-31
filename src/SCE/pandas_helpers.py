import logging

import pandas as pd


def merge_if_na(*data) -> pd.Series:
    """
    Return the values in the first element of `data`, but incrementally replace any
    missing values with non-missing values from remaining items in `data`.

    Parameters
    ----------
    data : List of pd.Series or pd.DataFrame

    Returns
    -------
    merged : pd.Series
    """

    data = pd.concat(data, axis=1)

    merged = data.iloc[:, 0].copy(deep=True)

    for name, var in data.iloc[:, 1:].items():
        mask = merged.isna() & var.notna()
        merged[mask] = var[mask]

    return merged


def tile_const(
    values: pd.Series | pd.DataFrame, by: str, dtype=None
) -> pd.Series | pd.DataFrame:
    """
    Tile non-missing value that is required to be constant within groups
    across all group observations.

    Parameters
    ----------
    values : pd.Series
    by : str
        Index level
    dtype :

    Returns
    -------
    pd.Series
    """

    index = values.index
    values = values.dropna()

    if (values.groupby(by).size() != 1).any():
        raise ValueError("Multiple non-NA values encountered")

    tiled = values.groupby(by).first().reindex(index, level=by)
    if dtype is not None:
        tiled = try_cast(tiled, dtype)

    return tiled


def try_cast(values: pd.Series | pd.DataFrame, dtype) -> pd.Series | pd.DataFrame:

    logger = logging.getLogger("SCE")

    dtype_name = getattr(dtype, "__name__", dtype)

    if isinstance(values, pd.DataFrame):
        for name in values.columns:
            try:
                values[name] = values[name].astype(dtype)
            except ValueError:
                n = values[name].isna().sum()
                logger.warning(
                    f"Failed to cast column {name} to {dtype_name} due to {n:,d} NA values."
                )
    else:
        try:
            values = values.astype(dtype)
        except ValueError:
            n = values.isna().sum()
            name = getattr(values, "name", None)
            if name:
                logger.warning(
                    f"Failed to cast {name} to {dtype_name} due to {n:,d} NA values."
                )
            else:
                logger.warning(
                    f"Failed to cast to {dtype_name} due to {n:,d} NA values."
                )

    return values
