"""
Create diagnostic plots for SCE variables.

- Plots histogram of observations per individual.
- Plots non-missing observations across survey waves.
- Plots descriptive statistics (mean, median, IQR) for variables over waves.

Author: Richard Foltyn
"""

import logging
from typing import Any

from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from pydynopt.plot import AbstractStyle, DefaultStyle, plot_grid
from pydynopt.plot.baseplots import hide_subplot

from env import EnvConfig, add_logfile
from SCE.constants import VARNAME_ID, VARNAME_WID

# Variables to exclude from diagnostic plots
VARLIST_EXCLUDE: list[str] = ["userid", "wid", "date"]


def plot_nobs_indiv(
    df: pd.DataFrame,
    style: AbstractStyle | None = None,
    **kwargs: Any,
) -> None:
    """
    Plot histogram of observations per individual for each variable.

    Illustrates how unbalanced the panel is.

    Parameters
    ----------
    df
        The SCE DataFrame.
    style
        Plot style specification.
    **kwargs
        Additional options passed to `plot_grid`.
    """
    df = df.reset_index()

    columns = [var for var in df.columns if var not in VARLIST_EXCLUDE]
    nvars = len(columns)
    ncol = 5
    nrow = int(np.ceil(nvars / ncol))

    if style is None:
        style = DefaultStyle()
        style.cell_size = 3.5
        style.aspect = 1.4
        style.grid = False

    nmax = df.groupby(VARNAME_ID).size().max()

    # --- Plotting function ---

    def plot(
        ax: Any,
        idx: tuple[int, int],
        data: pd.DataFrame | None = None,
        **kwargs: Any,
    ) -> None:
        if data is None:
            return
        i, j = idx

        k = i * ncol + j

        if k >= nvars:
            hide_subplot(ax)
            return

        varname = columns[k]

        # Histogram with half-integer edges so each integer count (0..nmax) gets
        # its own bin; integer-edge bins would merge the last two categories.
        bins = np.arange(-0.5, nmax + 1.5)
        x = data[varname].to_numpy()
        ax.hist(
            x,
            bins,
            color="steelblue",
            lw=0.4,
            rwidth=0.9,
            ec="white",
            label="Nobs. per indiv.",
        )

        ax.text(
            0.05,
            0.95,
            varname,
            transform=ax.transAxes,
            va="top",
            ha="left",
            **style.text,
        )

    # Collapse data by individual
    df_nobs = df.groupby([VARNAME_ID]).count()

    kw_plot: dict[str, Any] = {
        "xlabel": "Nobs. per individual",
        # Ticks centered on each integer; bin edges are at half-integers.
        "xticks": np.arange(nmax + 1),
        "xticklabels": np.arange(nmax + 1),
        "xlim": (-0.75, nmax + 0.25),
        "sharex": True,
        "sharey": False,
        "legend": True,
        "legend_loc": "upper right",
    }
    kw_plot.update(**kwargs)

    plot_grid(plot, nrow, ncol, style=style, data=df_nobs, **kw_plot)


def plot_nobs_wave(
    df: pd.DataFrame,
    style: AbstractStyle | None = None,
    **kwargs: Any,
) -> None:
    """
    Plot the number of non-missing observations for each variable by wave.

    Parameters
    ----------
    df
        The SCE DataFrame.
    style
        Plot style specification.
    **kwargs
        Additional options passed to `plot_grid`.
    """
    df = df.reset_index()

    columns = [var for var in df.columns if var not in VARLIST_EXCLUDE]
    nvars = len(columns)
    ncol = 5
    nrow = int(np.ceil(nvars / ncol))

    if style is None:
        style = DefaultStyle()
        style.cell_size = 3.0
        style.aspect = 1.3
        style.grid = False

    # --- Plotting function ---

    xvalues = df.groupby(VARNAME_WID)["date"].median()

    def plot(
        ax: Any,
        idx: tuple[int, int],
        data: pd.DataFrame | None = None,
        **kwargs: Any,
    ) -> None:
        if data is None:
            return
        i, j = idx

        k = i * ncol + j

        if k >= nvars:
            hide_subplot(ax)
            return

        varname = columns[k]

        yvalues = data[varname]
        ax.plot(
            xvalues,
            yvalues,
            label="Number of obs",
            lw=0.75,
            color="steelblue",
            marker="o",
            ms=2,
        )

        ax.text(
            0.05,
            0.95,
            varname,
            transform=ax.transAxes,
            va="top",
            ha="left",
            **style.text,
        )

    # --- Plot number of non-missing values ---

    # Collapse data
    collapsed = df.groupby(VARNAME_WID).count()

    kw_plot: dict[str, Any] = {
        "sharex": True,
        "sharey": False,
        "xlabel": "Wave",
        "legend": True,
        "legend_loc": "lower left",
    }
    kw_plot.update(**kwargs)

    plot_grid(plot, nrow, ncol, style=style, data=collapsed, **kw_plot)


def plot_stats_wave(
    df: pd.DataFrame,
    outliers: bool = True,
    style: AbstractStyle | None = None,
    **kwargs: Any,
) -> None:
    """
    Plot descriptive statistics (mean, median, IQR) for each variable by wave.

    Parameters
    ----------
    df
        The SCE DataFrame.
    outliers
        If false, drop extreme outliers which ruin the y-axis scale.
    style
        Plot style specification.
    **kwargs
        Additional options passed to `plot_grid`.
    """
    logger = logging.getLogger("SCE")

    columns = [var for var in df.columns if var not in VARLIST_EXCLUDE]
    nvars = len(columns)
    ncol = 5
    # Allow for dedicated legend panel
    nrow = int(np.ceil((nvars + 1) / ncol))

    if style is None:
        style = DefaultStyle()
        style.cell_size = 3.5
        style.aspect = 1.3
        style.grid = False

    xvalues = df.groupby(VARNAME_WID)["date"].median()

    # --- Plotting function ---

    def plot(
        ax: Any,
        idx: tuple[int, int],
        data: tuple[pd.DataFrame, pd.DataFrame] | None = None,
        **kwargs: Any,
    ) -> None:
        if data is None:
            return
        i, j = idx

        k = i * ncol + j

        kw_line: dict[str, Any] = {"lw": 1.0, "color": "steelblue"}
        kw_mean: dict[str, Any] = {
            "lw": 0.75,
            "color": "black",
            "alpha": 0.7,
            "ls": "-",
            "zorder": 100,
            "marker": "o",
            "ms": 2,
        }

        if k == 0:
            # Create dedicated panel with a legend
            handles = []
            labels = []

            line1 = Line2D((-1,), (-1,), **kw_line)
            line2 = Line2D((-1,), (-1,), **kw_mean)

            handles.extend((line1, line2))
            labels.extend(("Median", "Mean"))

            # IQR
            rect = Rectangle((-1, -1), 0, 0, color="steelblue", alpha=0.25)
            handles.append(rect)
            labels.append("IQR")

            ax.legend(handles, labels, loc="upper left", **style.legend)

            ax.set_ylim((0.0, 1.0))
            ax.set_ylabel("")
            ax.set_yticks([])
            ax.tick_params(bottom=False, left=False)

            return

        elif k > nvars:
            hide_subplot(ax)
            return

        varname = columns[k - 1]

        # Descriptive statistics
        df_mean, df_qntl = data

        # Mean
        yvalues = df_mean[varname]
        ax.plot(xvalues, yvalues, **kw_mean)

        # Median
        yvalues = df_qntl.loc[pd.IndexSlice[:, 0.50], varname]
        ax.plot(xvalues, yvalues, alpha=0.8, zorder=50, **kw_line)

        # IQR
        p25 = df_qntl.loc[pd.IndexSlice[:, 0.25], varname]
        p75 = df_qntl.loc[pd.IndexSlice[:, 0.75], varname]
        ax.fill_between(xvalues, p25, p75, color="steelblue", alpha=0.25, lw=0.0)
        ax.plot(xvalues, p25, lw=0.5, color="steelblue", alpha=0.5, zorder=10)
        ax.plot(xvalues, p75, lw=0.5, color="steelblue", alpha=0.5, zorder=10)

        ax.text(
            0.05,
            0.95,
            varname,
            transform=ax.transAxes,
            va="top",
            ha="left",
            **style.text,
        )

    # --- Plot mean and IQR ---

    groups = df.groupby(VARNAME_WID)

    df_qntl = groups[columns].quantile(np.array([0.25, 0.5, 0.75]))
    if outliers:
        df_mean = groups[columns].mean()
    else:
        # Eliminate extreme outliers outside of 100 * IQR.
        # q1 is the 25th percentile, q3 is the 75th percentile.
        q1 = df_qntl.xs(0.25, level=1, axis=0)
        q3 = df_qntl.xs(0.75, level=1, axis=0)
        iqr = q3 - q1
        # Impose min. IQR of 1 so that we ignore categoricals and responses where IQR
        # is 0 because most respondents answer the same (e.g. numerical literacy).
        iqr = iqr.clip(lower=1.0)
        df2 = df[columns].copy(deep=True)
        iqr = iqr.reindex(df2.index, level=VARNAME_WID)
        # Upper fence: q3 + 100*IQR; lower fence: q1 - 100*IQR.
        # This allows almost no outliers to remain (100*IQR vs. the
        # conventional 1.5*IQR) while keeping the y-axis readable.
        mask = (df2 > q3 + 100 * iqr) | (df2 < q1 - 100 * iqr)
        drop = mask.sum(axis=0)
        drop = drop[drop > 0].sort_values(ascending=False)
        if drop.any():
            s = drop.to_string().replace("\n", "\n\t")
            logger.info(f"Dropping outliers: \n\t{s}")
            df2[mask] = np.nan

        df_mean = df2.groupby(VARNAME_WID).mean()

    data = (df_mean, df_qntl)

    kw_plot: dict[str, Any] = {"sharex": True, "sharey": False, "xlabel": "Wave"}
    kw_plot.update(**kwargs)

    plot_grid(plot, nrow, ncol, style=style, data=data, **kw_plot)


def main(econf: EnvConfig) -> None:
    """
    Generate and save diagnostic plots.

    Parameters
    ----------
    econf
        Parsed environment configuration.
    """
    add_logfile("sce-plot-diag.log", logdir=econf.logdir, reltime=True)
    logger = logging.getLogger("SCE")

    fn = econf.datadir / "sce_extract.pkl.zst"
    if not fn.is_file():
        raise SystemExit(
            f"Pickle output not found: {fn}\n"
            "Re-run the importer with '--formats pickle' to generate the "
            "required output."
        )
    df: pd.DataFrame = pd.read_pickle(fn)

    # Plot histogram of individual obs.
    fn = econf.graphdir / "sce_indiv_obs.pdf"
    logger.info(f"Saving SCE individual observations to {fn}")
    plot_nobs_indiv(
        df,
        outfile=fn,
        suptitle="SCE: Number of Observations per Respondent by Variable",
    )

    # Plot timeseries of N. obs. by variable
    fn = econf.graphdir / "sce_nobs.pdf"
    logger.info(f"Saving SCE observations count to {fn}")
    plot_nobs_wave(
        df,
        outfile=fn,
        suptitle="SCE: Number of Observations per Wave by Variable",
    )

    # Plot timeseries of descriptive statistic by variable
    fn = econf.graphdir / "sce_descriptive.pdf"
    logger.info(f"Saving SCE descriptive statistics to {fn}")
    plot_stats_wave(
        df,
        outfile=fn,
        suptitle="SCE: Descriptive Statistics by Wave (with Outliers)",
    )

    fn = econf.graphdir / "sce_descriptive_no_outliers.pdf"
    logger.info(f"Saving SCE descriptive statistics (no outliers) to {fn}")
    plot_stats_wave(
        df,
        outliers=False,
        outfile=fn,
        suptitle="SCE: Descriptive Statistics by Wave (No Outliers)",
    )


if __name__ == "__main__":
    main(EnvConfig.setup())
