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
from SCE.annotations import (
    VALUE_LABELS,
    VARIABLE_LABELS,
    VARIABLE_LABELS_FULL,
    check_label_coverage,
)
from SCE.constants import VARNAME_ID
from SCE.importer import merge_inc_rank, process_sce

CSV_PERCENT_COLUMN_REGEX: str = (
    r"^(?:prob_|infl_)|_change(?:_3y)?$|^(?:hh_inc_bin_rank|Q47_rank)$"
)


def md5sum(file_path: Path) -> str:
    """Compute the MD5 checksum of a file.

    Parameters
    ----------
    file_path
        Path to the file to check.

    Returns
    -------
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


def apply_metadata(
    df: pd.DataFrame,
    variable_labels: dict[str, str],
    value_labels: dict[str, dict[int, str]],
    *,
    output_name: str,
) -> pd.DataFrame:
    """Attach variable and value label metadata to a processed SCE output.

    Parameters
    ----------
    df
        Processed SCE DataFrame with a ``(userid, wid)`` MultiIndex.
    variable_labels
        Mapping from column name (or index level name) to descriptive label.
    value_labels
        Mapping from column name to a ``{code: label}`` dict of value labels.
    output_name
        Dataset name used in coverage errors.

    Returns
    -------
    Copy of ``df`` with ``attrs["variable_labels"]`` and
    ``attrs["value_labels"]`` populated. Labels are filtered to names
    actually present so downstream exports do not fail on unknown keys.

    Notes
    -----
    The filtered dicts are stored in ``df.attrs`` so they survive Pickle
    round-trips. When passing to ``DataFrame.to_stata`` with
    ``write_index=True``, include index level names (e.g. ``userid``, ``wid``)
    in ``variable_labels`` so Stata receives labels for those columns too.
    """
    # Collect all names that will appear as columns in the Stata output,
    # including index levels when write_index=True is used.
    all_names: set[str] = set(df.columns.tolist())
    if df.index.names:
        all_names.update(str(n) for n in df.index.names if n is not None)

    unlabeled, _ = check_label_coverage(all_names, variable_labels)
    if unlabeled:
        names = ", ".join(sorted(unlabeled))
        raise ValueError(f"{output_name} output fields without labels: {names}")

    present_var = {k: v for k, v in variable_labels.items() if k in all_names}
    # Value labels only apply to data columns, not index levels.
    present_val = {k: v for k, v in value_labels.items() if k in df.columns}

    df = df.copy()
    df.attrs["variable_labels"] = present_var
    df.attrs["value_labels"] = present_val
    return df


def prepare_csv_export(
    df: pd.DataFrame,
    *,
    decimals_percent: int = 2,
) -> pd.DataFrame:
    """Prepare a rounded copy of processed SCE data for CSV export.

    Only quantities represented as percentages or percentiles are rounded:
    probabilities on ``[0, 100]``, inflation statistics, percentage changes,
    and ACS income ranks on ``[0, 1]``. Other measured quantities retain
    their processed precision.

    Parameters
    ----------
    df
        Processed SCE output to prepare.
    decimals_percent
        Number of decimal places retained for percentage-valued fields.

    Returns
    -------
    Copy of ``df`` with CSV presentation rounding applied.
    """
    result = df.copy(deep=True)
    columns = result.filter(regex=CSV_PERCENT_COLUMN_REGEX, axis=1).columns
    result[columns] = result[columns].round(decimals_percent)
    return result


def summarize_sample(df: pd.DataFrame, name: str) -> None:
    """Log sample summary statistics for a processed SCE dataset.

    Parameters
    ----------
    df
        Processed SCE DataFrame.
    name
        Name descriptor of the dataset (e.g., ``"full"`` or ``"extract"``).
    """
    logger = logging.getLogger("SCE")

    n_obs = len(df)
    if VARNAME_ID in df.index.names:
        n_indiv = df.index.get_level_values(VARNAME_ID).nunique()
    else:
        n_indiv = df[VARNAME_ID].nunique()

    min_date = pd.Timestamp(df["date"].min()).date()
    max_date = pd.Timestamp(df["date"].max()).date()
    n_vars = len(df.columns)

    fence = "=" * 80
    logger.info(fence)
    logger.info(f"Sample summary report ({name})")
    logger.info(fence)
    logger.info(f"  Number of observations: {n_obs:,d}")
    logger.info(f"  Number of individuals:  {n_indiv:,d}")
    logger.info(f"  First interview date:   {min_date}")
    logger.info(f"  Last interview date:    {max_date}")
    logger.info(f"  Number of variables:    {n_vars:,d}")
    logger.info("  Non-missing observations per variable:")

    non_missing = df.count()
    if not non_missing.empty:
        max_var_len = max(len(str(var)) for var in non_missing.index)
        max_count_len = max(len(f"{count:,d}") for count in non_missing.values)
        for var_name, count in non_missing.items():
            formatted_count = f"{count:,d}"
            logger.info(
                f"    {var_name!s:<{max_var_len}}  {formatted_count:>{max_count_len}}"
            )


def summarize_spell_lengths(df: pd.DataFrame) -> None:
    """Log the distribution of spell lengths across individuals.

    Parameters
    ----------
    df
        SCE DataFrame containing panel identifiers.
    """
    logger = logging.getLogger("SCE")

    if VARNAME_ID in df.index.names:
        counts = df.groupby(level=VARNAME_ID).size()
    else:
        counts = df.groupby(VARNAME_ID).size()

    df_obs = counts.value_counts().sort_index()

    fence = "=" * 80
    logger.info(fence)
    logger.info("Distribution of spell lengths")
    logger.info(fence)

    if not df_obs.empty:
        max_length_len = max(len(str(length)) for length in df_obs.index)
        max_count_len = max(len(f"{count:,d}") for count in df_obs.values)
        for length, count in df_obs.items():
            formatted_count = f"{count:,d}"
            logger.info(
                f"  {length!s:>{max_length_len}}  {formatted_count:>{max_count_len}}"
            )


def process_data(
    df_orig: pd.DataFrame,
    df_ranks: pd.DataFrame | None = None,
    final_date: datetime.date | pd.Timestamp | None = None,
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

    Returns
    -------
    df_full
        Processed full data set.
    df_extract
        Processed extract data set.
    """
    # Process raw data, create full data set and smaller extract
    df_full, df_extract = process_sce(df_orig)

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
    )

    # Attach variable/value label metadata so both Pickle and Stata exports carry it.
    df_full = apply_metadata(
        df_full,
        VARIABLE_LABELS_FULL,
        VALUE_LABELS,
        output_name="full",
    )
    df_extract = apply_metadata(
        df_extract,
        VARIABLE_LABELS,
        VALUE_LABELS,
        output_name="extract",
    )

    # --- Sample summary report ---

    summarize_sample(df_full, "full")
    summarize_sample(df_extract, "extract")

    # --- Tabulate distribution of spell lengths ---

    summarize_spell_lengths(df_orig)

    # --- Store results ---

    formats = econf.formats
    logger.info(f"Export formats selected: {', '.join(sorted(formats))}")

    # attrs (variable_labels, value_labels) survive the Pickle round-trip automatically.
    if "pickle" in formats:
        fn = econf.datadir / "sce_extract.pkl.zst"
        logger.info(f"Saving SCE extract to {fn}")
        df_extract.to_pickle(fn, protocol=5)

        fn = econf.datadir / "sce_full.pkl.zst"
        logger.info(f"Saving full SCE data to {fn}")
        df_full.to_pickle(fn, protocol=5)
    else:
        logger.info("Skipped export format: pickle")

    # --- Export to Stata ---

    if "stata" in formats:
        fn = econf.datadir / "sce_extract.dta"
        logger.info(f"Saving SCE extract to {fn}")
        df_extract.to_stata(
            fn,
            convert_dates={"date": "td"},
            version=118,
            write_index=True,
            variable_labels=df_extract.attrs.get("variable_labels", {}),
            value_labels=df_extract.attrs.get("value_labels", {}),
        )

        fn = econf.datadir / "sce_full.dta"
        logger.info(f"Saving full SCE data to {fn}")
        df_full.to_stata(
            fn,
            convert_dates={"date": "td"},
            version=118,
            write_index=True,
            variable_labels=df_full.attrs.get("variable_labels", {}),
            value_labels=df_full.attrs.get("value_labels", {}),
        )
    else:
        logger.info("Skipped export format: stata")

    # --- Export to Excel ---

    if "excel" in formats:
        fn = econf.datadir / "sce_extract.xlsx"
        logger.info(f"Saving SCE extract to {fn}")
        df_extract.to_excel(fn, index=True, sheet_name="SCE")
    else:
        logger.info("Skipped export format: excel")

    # --- Export to CSV ---

    if "csv" in formats:
        fn = econf.datadir / "sce_extract.csv"
        logger.info(f"Saving SCE extract to {fn}")
        df_csv = prepare_csv_export(df_extract, decimals_percent=2)
        df_csv.to_csv(fn, index=True)
    else:
        logger.info("Skipped export format: csv")


if __name__ == "__main__":
    main(EnvConfig.setup())
