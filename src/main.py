"""
Main module to import and process SCE microdata.

- Concatenates multiple raw Excel datasets.
- Processes demographic and question variables.
- Merges external family income ranks.
- Exports the final processed datasets to Pickle, Stata, Excel, and CSV.

Author: Richard Foltyn
"""

import datetime
import hashlib
import logging
from pathlib import Path

import pandas as pd

from env import EnvConfig, add_logfile
from SCE.constants import VARNAME_ID
from SCE.importer import merge_inc_rank, process_sce


def md5sum(file_path: Path) -> str:
    """Compute the MD5 checksum of a file.

    Parameters
    ----------
    file_path
        Path to the file to check.

    Returns
    -------
    str
        MD5 checksum as a hexadecimal string.
    """
    hash_md5 = hashlib.md5()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(4096 * 4), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def restrict_to_final_date(
    df_full: pd.DataFrame,
    df_extract: pd.DataFrame,
    final_date: datetime.date | pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restrict processed SCE frames to an inclusive final survey date.

    Parameters
    ----------
    df_full
        Processed full SCE data.
    df_extract
        Processed SCE extract.
    final_date
        Final survey date to retain. Time components are ignored.

    Returns
    -------
    df_full
        Filtered full SCE data.
    df_extract
        Filtered SCE extract.
    """
    logger = logging.getLogger("SCE")

    # SCE interview dates identify calendar days without a meaningful time of
    # day, so normalize Timestamp inputs before applying the inclusive cutoff.
    cutoff = pd.Timestamp(final_date).normalize()
    logger.info(f"Restricting sample to dates before and including {cutoff.date()}")

    keep = df_full["date"] <= cutoff
    if (n := len(keep) - keep.sum()) > 0:
        logger.warning(f"  {n:,d} observations are excluded from the full data set")
    df_full = df_full[keep].copy()

    keep = df_extract["date"] <= cutoff
    if (n := len(keep) - keep.sum()) > 0:
        logger.warning(f"  {n:,d} observations are excluded from the extract")
    df_extract = df_extract[keep].copy()

    return df_full, df_extract


def process_data(
    df_orig: pd.DataFrame,
    df_ranks: pd.DataFrame | None = None,
    final_date: datetime.date | pd.Timestamp | None = None,
    decimals_percent: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process SCE raw data and return a full data set and a reduced extract.

    Parameters
    ----------
    df_orig
        Original SCE data, concatenated into single DataFrame.
    df_ranks
        Mapping of family income in USD to income ranks.
    final_date
        If not None, restrict the sample to dates before and including this date.
        Time components are ignored.
    decimals_percent
        If not None, round questions or statistics computed from question that are
        answered in percent to this many digits.

    Returns
    -------
    df_full
        Processed full data set.
    df_extract
        Processed extract data set.
    """
    # Process raw data, create full data set and smaller extract
    df_full, df_extract = process_sce(df_orig, decimals_percent=decimals_percent)

    # Restrict both outputs before the ACS merge so a pinned sample cannot fail
    # because later, excluded survey months lack a corresponding rank year.
    if final_date is not None:
        df_full, df_extract = restrict_to_final_date(df_full, df_extract, final_date)

    # --- Merge HH income ranks from ACS ---

    if df_ranks is not None:
        df_rank = merge_inc_rank(df_full, "Q47", df_ranks)
        df_full = pd.concat((df_full, df_rank), axis=1)

        df_rank = merge_inc_rank(df_extract, "hh_inc_bin", df_ranks)
        df_extract = pd.concat((df_extract, df_rank), axis=1)

    return df_full, df_extract


def main(econf: EnvConfig) -> None:
    """
    Main execution function for importing and processing SCE data.

    Parameters
    ----------
    econf
        Parsed environment configuration.
    """
    add_logfile("sce-import.log", logdir=econf.logdir, reltime=True)
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
        path = econf.inputdir / file

        hsh = md5sum(path)
        fn_cache = econf.cachedir / f"{hsh}.pkl.zst"
        if fn_cache.is_file():
            logger.info(f"Reading cached file {fn_cache}")
            df = pd.read_pickle(fn_cache)
        else:
            logger.info(f"Reading in {path}")
            # Skip the first line which contains the license terms
            df = pd.read_excel(path, skiprows=1)
            df.to_pickle(fn_cache, protocol=5)

        logger.info(f"  Initial interview date: {df['survey_date'].dt.date.min()}")
        logger.info(f"  Final interview date:   {df['survey_date'].dt.date.max()}")

        df_all.append(df)

    df_orig: pd.DataFrame = pd.concat(df_all, axis=0)
    df_orig = df_orig.sort_values(by=[VARNAME_ID, "date"]).reset_index(drop=True)

    # --- Load income rank data from ACS ---

    fn = econf.repodir / "data" / "IPUMS_ftotinc_rank_by_year_sce_bins.csv"
    df_ranks = pd.read_csv(fn)

    # --- Process SCE data ---

    df_full, df_extract = process_data(
        df_orig,
        df_ranks,
        final_date=econf.final_date,
        decimals_percent=2,
    )

    # --- Tabulate distribution of spell lengths ---

    df_obs = df_orig.groupby(VARNAME_ID).size().value_counts().sort_index()
    s = df_obs.to_string(header=True)
    s = s.replace("\n", "\n\t")
    logger.info(f"Distribution of spell lengths: \n\t{s}")

    # --- Store results ---

    fn = econf.datadir / "sce_extract.pkl.zst"
    logger.info(f"Saving SCE extract to {fn}")
    df_extract.to_pickle(fn, protocol=5)

    fn = econf.datadir / "sce_full.pkl.zst"
    logger.info(f"Saving full SCE data to {fn}")
    df_full.to_pickle(fn, protocol=5)

    # --- Export to Stata ---

    fn = econf.datadir / "sce_extract.dta"
    logger.info(f"Saving SCE extract to {fn}")
    df_extract.to_stata(fn, convert_dates={"date": "td"}, version=118, write_index=True)

    fn = econf.datadir / "sce_full.dta"
    logger.info(f"Saving full SCE data to {fn}")
    df_full.to_stata(fn, convert_dates={"date": "td"}, version=118, write_index=True)

    # --- Export to Excel ----

    fn = econf.datadir / "sce_extract.xlsx"
    logger.info(f"Saving SCE extract to {fn}")
    df_extract.to_excel(fn, index=True, sheet_name="SCE")

    # --- Export to CSV ---

    fn = econf.datadir / "sce_extract.csv"
    logger.info(f"Saving SCE extract to {fn}")
    df_extract.to_csv(fn, index=True)


if __name__ == "__main__":
    main(EnvConfig.setup())
