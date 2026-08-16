"""
Helper functions for working with pandas DataFrames and Series.

- merge_if_na: Incrementally merge Series replacing missing values.
- tile_const: Broadcast a constant value within groups across group observations.
- try_cast: Attempt to cast variables to a target dtype, logging warnings on failure.

Author: Richard Foltyn
"""

import logging
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
        tiled = try_cast(tiled, dtype)

    return tiled


def try_cast(
    values: pd.Series | pd.DataFrame,
    dtype: Any,
) -> pd.Series | pd.DataFrame:
    """
    Attempt to cast columns/values to a target dtype.

    Emits warnings if values cannot be cast due to NA values.

    Parameters
    ----------
    values
        The pandas Series or DataFrame to cast.
    dtype
        The target data type.

    Returns
    -------
    pd.Series or pd.DataFrame
        The cast pandas Series or DataFrame.
    """
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
