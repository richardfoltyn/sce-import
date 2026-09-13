"""Create diagnostic plots from the processed SCE extract.

- Read the compressed Pickle produced by the importer.
- Write respondent, observation-count, and descriptive-statistics reports.

Author: Richard Foltyn
"""

import logging

import pandas as pd

from env import EnvConfig, add_logfile
from SCE.annotations import (
    PERCENT_VARIABLES,
    USD_VARIABLES,
    VARIABLE_LABELS_SHORT,
)
from SCE.constants import VARNAME_ID, VARNAME_WEIGHT, VARNAME_WID
from SCE.plots import (
    OutlierMethod,
    OutlierTail,
    plot_nobs_by_id,
    plot_nobs_by_wave,
    plot_stats_by_wave,
)

_EXCLUDED_VARIABLES = frozenset({VARNAME_ID, VARNAME_WID, "date"})
_NO_OUTLIER_TRIMMING_VARIABLES = frozenset(
    {
        "prob_move_house",
        "prob_unrate_up",
        "prob_irate_up",
        "prob_stocks_up",
        "infl_1y_bin_prob_defl",
        "infl_3y_bin_prob_defl",
        "infl_5y_bin_prob_defl",
        "prob_lose_job",
        "prob_leave_job",
        "prob_accept_job_12m",
        "prob_accept_job_3m",
        "prob_search_job_12m",
        "prob_search_job_3m",
        "prob_miss_paym_3m",
        "hh_inc_bin_rank",
    }
)
_QUANTILE_OUTLIER_VARIABLES = frozenset({"num_lit_q3", "num_lit_q6"})
_OUTLIER_TAIL_FRACTION = 0.025
_OUTLIER_IQR_FACTOR = 100.0


def main(econf: EnvConfig) -> None:
    """Generate and save diagnostic plots.

    Parameters
    ----------
    econf
        Parsed environment configuration.
    """
    add_logfile("sce-plot-diag.log", logdir=econf.logdir, reltime=True)
    logger = logging.getLogger("SCE")

    path = econf.datadir / "sce_extract.pkl.zst"
    if not path.is_file():
        raise SystemExit(
            f"Pickle output not found: {path}\n"
            "Re-run the importer with '--formats pickle' to generate the "
            "required output."
        )

    logger.info("Reading processed SCE extract from %s", path)
    df_data: pd.DataFrame = pd.read_pickle(path)
    df_plot = df_data.reset_index()

    variables = tuple(
        str(name) for name in df_plot if str(name) not in _EXCLUDED_VARIABLES
    )
    stats_variables = tuple(
        variable for variable in variables if variable != VARNAME_WEIGHT
    )
    variable_labels = df_plot.attrs.get("variable_labels", {}) | VARIABLE_LABELS_SHORT
    stat_variable_labels = {
        variable: (
            f"{label} ($)"
            if variable in USD_VARIABLES
            else f"{label} (%)"
            if variable in PERCENT_VARIABLES
            else label
        ).replace("$", r"\$")
        for variable, label in variable_labels.items()
    }
    value_labels = df_plot.attrs.get("value_labels", {})
    outlier_methods = {
        variable: (
            OutlierMethod.QUANTILE
            if variable in _QUANTILE_OUTLIER_VARIABLES
            else OutlierMethod.IQR
        )
        for variable in stats_variables
    }
    outlier_tails = dict.fromkeys(_NO_OUTLIER_TRIMMING_VARIABLES, OutlierTail.NONE)

    plot_nobs_by_id(
        df_plot,
        variables,
        econf.graphdir / "sce_indiv_obs.pdf",
        id_column=VARNAME_ID,
        suptitle="SCE: Number of Observations per Respondent by Variable",
        variable_labels=variable_labels,
        xlabel="Nobs. per individual",
        ylabel="Respondents",
    )
    plot_nobs_by_wave(
        df_plot,
        variables,
        econf.graphdir / "sce_nobs.pdf",
        wave_column=VARNAME_WID,
        x_column="date",
        suptitle="SCE: Number of Observations per Wave by Variable",
        variable_labels=variable_labels,
    )
    plot_stats_by_wave(
        df_plot,
        stats_variables,
        econf.graphdir / "sce_descriptive.pdf",
        wave_column=VARNAME_WID,
        x_column="date",
        suptitle="SCE: Descriptive Statistics by Wave (with Outliers)",
        variable_labels=stat_variable_labels,
        value_labels=value_labels,
        compact_variables=USD_VARIABLES,
    )
    plot_stats_by_wave(
        df_plot,
        stats_variables,
        econf.graphdir / "sce_descriptive_no_outliers.pdf",
        wave_column=VARNAME_WID,
        x_column="date",
        suptitle="SCE: Descriptive Statistics by Wave (No Outliers)",
        variable_labels=stat_variable_labels,
        value_labels=value_labels,
        compact_variables=USD_VARIABLES,
        outlier_method=outlier_methods,
        outlier_tails=outlier_tails,
        outlier_tail_fraction=_OUTLIER_TAIL_FRACTION,
        outlier_iqr_factor=_OUTLIER_IQR_FACTOR,
    )
    plot_stats_by_wave(
        df_plot,
        stats_variables,
        econf.graphdir / "sce_descriptive_weighted.pdf",
        wave_column=VARNAME_WID,
        x_column="date",
        weight_column=VARNAME_WEIGHT,
        suptitle="SCE: Descriptive Statistics by Wave (Weighted, with Outliers)",
        variable_labels=stat_variable_labels,
        value_labels=value_labels,
        compact_variables=USD_VARIABLES,
    )
    plot_stats_by_wave(
        df_plot,
        stats_variables,
        econf.graphdir / "sce_descriptive_weighted_no_outliers.pdf",
        wave_column=VARNAME_WID,
        x_column="date",
        weight_column=VARNAME_WEIGHT,
        suptitle="SCE: Descriptive Statistics by Wave (Weighted, No Outliers)",
        variable_labels=stat_variable_labels,
        value_labels=value_labels,
        compact_variables=USD_VARIABLES,
        outlier_method=outlier_methods,
        outlier_tails=outlier_tails,
        outlier_tail_fraction=_OUTLIER_TAIL_FRACTION,
        outlier_iqr_factor=_OUTLIER_IQR_FACTOR,
    )


if __name__ == "__main__":
    main(EnvConfig.setup())
