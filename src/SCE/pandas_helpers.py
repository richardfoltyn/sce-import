"""
Helper functions for working with pandas DataFrames and Series.

- merge_if_na: Incrementally merge Series replacing missing values.
- tile_const: Broadcast a constant value within groups across group observations.

Author: Richard Foltyn
"""

from typing import Any

import pandas as pd


def merge_if_na(*data: pd.Series | pd.DataFrame) -> pd.Series:
    """
    Incrementally replace missing values.

    Returns the values in the first element of `data`, but incrementally replaces
    any missing values with non-missing values from remaining items in `data`.

    Parameters
    ----------
    *data
        Positional pandas Series or DataFrames to merge.

    Returns
    -------
    pd.Series
        The merged Series.
    """
    df_data = pd.concat(data, axis=1)

    merged = df_data.iloc[:, 0].copy(deep=True)

    for _name, var in df_data.iloc[:, 1:].items():
        mask = merged.isna() & var.notna()
        merged[mask] = var[mask]

    return merged


def tile_const(
    values: pd.Series | pd.DataFrame,
    by: str,
    dtype: Any = None,
) -> pd.Series | pd.DataFrame:
    """
    Tile non-missing value that is required to be constant within groups.

    Broadcasts the single non-NA value within each group across all group
    observations.

    Parameters
    ----------
    values
        The pandas Series or DataFrame to tile.
    by
        The name of the index level to group by.
    dtype
        The target data type to cast to, optional.

    Returns
    -------
    pd.Series or pd.DataFrame
        The tiled pandas Series or DataFrame.
    """
    index = values.index
    values = values.dropna()

    if (values.groupby(by).size() != 1).any():
        raise ValueError("Multiple non-NA values encountered")

    tiled = values.groupby(by).first().reindex(index, level=by)
    if dtype is not None:
        tiled = tiled.astype(dtype)

    return tiled
