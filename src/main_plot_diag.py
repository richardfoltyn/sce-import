"""
Create diagnostic plots for SCE variables.

Author: Richard Foltyn
"""

import os.path
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from SCE.constants import VARNAME_ID, VARNAME_WID
from pydynopt.plot import plot_grid, DefaultStyle, AbstractStyle

from env import env_setup, EnvConfig
from pydynopt.plot.baseplots import hide_subplot

# Variables to exclude from diagnostic plots
VARLIST_EXCLUDE = ["userid", "wid"]


def plot_nobs_indiv(df: pd.DataFrame, style: Optional[AbstractStyle] = None, **kwargs):
    """
    Plot histogram of observations per individual for each variable to illustrate how
    unbalanced the panel is.

    Parameters
    ----------
    df : pd.DataFrame
    style : AbstractStyle, optional
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

    def plot(ax, idx, data):
        i, j = idx

        k = i * ncol + j

        if k >= nvars:
            hide_subplot(ax)
            return

        varname = columns[k]

        # Histogram bins
        bins = np.arange(nmax + 1)
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
            **style.text
        )

    # Collapse data by individual
    df_nobs = df.groupby([VARNAME_ID]).count()

    kw_plot = {
        "xlabel": "Nobs. per individual",
        "xticks": np.arange(nmax + 1) + 0.5,
        "xticklabels": np.arange(nmax + 1),
        "xlim": (-0.25, nmax + 0.75),
        "sharex": True,
        "sharey": False,
        "legend": True,
        "legend_loc": "upper right",
    }
    kw_plot.update(**kwargs)

    plot_grid(plot, nrow, ncol, style=style, data=df_nobs, **kw_plot)


def plot_nobs_wave(df: pd.DataFrame, style: Optional[AbstractStyle] = None, **kwargs):
    """
    Plot the number of non-missing observations for each variable by wave.

    Parameters
    ----------
    df : pd.DataFrame
    style : AbstractStyle, optional
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

    xvalues = df.groupby(VARNAME_WID)['date'].median()

    def plot(ax, idx, data: pd.DataFrame):
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
            **style.text
        )

    # --- Plot number of non-missing values ---

    # Collapse data
    collapsed = df.groupby(VARNAME_WID).count()

    kw_plot = {
        "sharex": True,
        "sharey": False,
        "xlabel": "Wave",
        "legend": True,
        "legend_loc": "lower left",
    }
    kw_plot.update(**kwargs)

    plot_grid(plot, nrow, ncol, style=style, data=collapsed, **kw_plot)


def plot_stats_wave(df: pd.DataFrame, style: Optional[AbstractStyle] = None, **kwargs):
    """
    Plot descriptive statistics (mean, median, IQR) for each variable as a time
    series across survey waves.

    Parameters
    ----------
    df : pd.DataFrame
    style : AbstractStyle, optional
    """

    df = df.reset_index()

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

    xvalues = df.groupby(VARNAME_WID)['date'].median()

    # --- Plotting function ---

    def plot(ax, idx, data: pd.DataFrame):
        i, j = idx

        k = i * ncol + j

        kw_line = {"lw": 1.0, "color": "steelblue"}
        kw_mean = {
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
            **style.text
        )

    # --- Plot mean and IQR ---

    groups = df.groupby(VARNAME_WID)

    df_mean = groups[columns].mean()
    df_qntl = groups[columns].quantile([0.25, 0.5, 0.75])
    data = (df_mean, df_qntl)

    kw_plot = {"sharex": True, "sharey": False, "xlabel": "Wave"}
    kw_plot.update(**kwargs)

    plot_grid(plot, nrow, ncol, style=style, data=data, **kw_plot)


def main(econf: EnvConfig):
    """

    Parameters
    ----------
    econf : env.EnvConfig
    """

    fn = os.path.join(econf.datadir, "SCE_extract.pkl.xz")
    df = pd.read_pickle(fn)

    # Plot histogram of individual obs.
    fn = os.path.join(econf.graphdir, "SEC_indiv_obs.pdf")
    plot_nobs_indiv(df, outfile=fn)

    # Plot timeseries of N. obs. by variable
    fn = os.path.join(econf.graphdir, "SCE_nobs.pdf")
    plot_nobs_wave(df, outfile=fn)

    # Plot timeseries of descriptive statistic by variable
    fn = os.path.join(econf.graphdir, "SCE_descriptive.pdf")
    plot_stats_wave(df, outfile=fn)


if __name__ == "__main__":
    main(env_setup())
