import datetime
import hashlib
import logging
import os.path
from typing import Optional

import pandas as pd

from SCE.constants import VARNAME_ID
from SCE.importer import merge_inc_rank, process_sce
from env import EnvConfig, env_setup


def md5sum(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096 * 4), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def process_data(
    df_orig: pd.DataFrame,
    df_ranks: Optional[pd.DataFrame] = None,
    final_date: Optional[datetime.date] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Precess SCE raw data and return a full data set and a reduced extract.

    Parameters
    ----------
    df_orig : pd.DataFrame
        Original SCE data, concatenated into single DataFrame.
    df_ranks : pd.DataFrame, optional
        Mapping of family income in USD to income ranks
    final_date : datetime.date, optional
        If not None, restrict sample to dates before and including this date.

    Returns
    -------
    df_full : pd.DataFrame
        Processed full data set
    df_extract : pd.DataFrame
        Processed extract data set
    """

    logger = logging.getLogger("SCE")

    # Process raw data, create full data set and smaller extract
    df_full, df_extract = process_sce(df_orig)

    # --- Merge HH income ranks from ACS ---

    if df_ranks is not None:

        df_rank = merge_inc_rank(df_full, "Q47", df_ranks)
        df_full = pd.concat((df_full, df_rank), axis=1)

        df_rank = merge_inc_rank(df_extract, "hh_inc_bin", df_ranks)
        df_extract = pd.concat((df_extract, df_rank), axis=1)

    # --- Restrict sample by final date ---

    if final_date is not None:
        logger.info(f"Restricting sample to dates before and including {final_date}")
        keep = df_full["date"] <= final_date
        if (n := len(keep) - keep.sum()) > 0:
            logger.warning(f"  {n:,d} observations are excluded from the full data set")
        df_full = df_full[keep].copy()

        keep = df_extract["date"] <= final_date
        if (n := len(keep) - keep.sum()) > 0:
            logger.warning(f"  {n:,d} observations are excluded from the extract")
        df_extract = df_extract[keep].copy()

    return df_full, df_extract


def main(econf: EnvConfig):

    logger = logging.getLogger("SCE")

    # File names are assumed to be those from the SCE website
    files = [
        "FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx",
        "FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx",
        "frbny-sce-public-microdata-latest.xlsx",
    ]

    # --- Merge individual raw Excel files ---

    # NOTE: Merging needs to be done BEFORE processing as otherwise spells span
    # multiple data sets and the propagation of questions asked only of new participants
    # are not handled correctly.

    df_all = []

    for file in files:
        path = os.path.join(econf.inputdir, file)

        hsh = md5sum(path)
        fn_cache = os.path.join(econf.cachedir, hsh + ".pkl.xz")
        if os.path.isfile(fn_cache):
            logger.info(f"Reading cached file {fn_cache}")
            df = pd.read_pickle(fn_cache)
        else:
            logger.info(f"Reading in {path}")
            # Skip the first line which contains the license terms
            df = pd.read_excel(path, skiprows=1)
            df.to_pickle(fn_cache)

        logger.info(f"  Initial intervew date: {df['survey_date'].dt.date.min()}")
        logger.info(f"  Final intervew date:   {df['survey_date'].dt.date.max()}")

        df_all.append(df)

    df_orig = pd.concat(df_all, axis=0)
    df_orig = df_orig.sort_values(by=[VARNAME_ID, "date"]).reset_index(drop=True)

    # --- Load income rank data from ACS ---

    fn = os.path.join(econf.repodir, "data", "IPUMS_ftotinc_rank_by_year_sce_bins.csv")
    df_ranks = pd.read_csv(fn)

    # --- Process SCE data ---

    # The Fed NY silently updates the current file, so there is no way to get exactly
    # the same sample as earlier. Impose some terminal date to keep the sample period
    # the same.
    final_date = pd.to_datetime("2024-10-01")

    df_full, df_extract = process_data(df_orig, df_ranks, final_date)

    # --- Tabulate distribution of spell lengths ---

    df_obs = df_orig.groupby(VARNAME_ID).size().value_counts().sort_index()
    s = df_obs.to_string(header=True)
    s = s.replace("\n", "\n\t")
    logger.info(f"Distribution of spell lengths: \n\t{s}")

    # --- Store results ---

    fn = os.path.join(econf.datadir, "sce_extract.pkl.xz")
    logger.info(f"Saving SCE extract to {fn}")
    df_extract.to_pickle(fn, protocol=5)

    fn = os.path.join(econf.datadir, "sce_full.pkl.xz")
    logger.info(f"Saving full SCE data to {fn}")
    df_full.to_pickle(fn, protocol=5)

    # --- Export to Stata ---

    fn = os.path.join(econf.datadir, "sce_extract.dta")
    logger.info(f"Saving SCE extract to {fn}")
    df_extract.to_stata(fn, convert_dates={"date": "td"}, version=118, write_index=True)

    fn = os.path.join(econf.datadir, "sce_full.dta")
    logger.info(f"Saving full SCE data to {fn}")
    df_full.to_stata(fn, convert_dates={"date": "td"}, version=118, write_index=True)


if __name__ == "__main__":
    main(env_setup())
