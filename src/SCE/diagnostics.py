"""Create diagnostic plots for the processed SCE extract.

- Plot respondent spell lengths and nonmissing observations by survey wave.
- Plot weighted and unweighted longitudinal descriptive statistics.
- Apply consistent panel annotations, axis formatting, and outlier suppression.

Author: Richard Foltyn
"""

from collections.abc import Callable, Sequence
import logging
from pathlib import Path
from textwrap import fill
from typing import Literal

from matplotlib.axes import Axes
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator, StrMethodFormatter
import numpy as np
import numpy.typing as npt
import pandas as pd

from SCE.annotations import USD_VARIABLES, VARIABLE_LABELS_SHORT
from SCE.constants import VARNAME_ID, VARNAME_WID

FIGURE_WIDTH = 16.2
ROW_HEIGHT = 2.835
NCOLS = 5
MAX_Y_TICKS = 5
TICK_LABEL_SIZE = 10
VARIABLE_LABEL_SIZE = 11
FIGURE_TITLE_SIZE = 14
YLIM_MARGIN = 0.05
TOP_YLIM_MARGIN = 0.05
OUTLIER_IQR_FACTOR = 100.0

STEEL_BLUE = "steelblue"
MEAN_COLOR = "black"
LINE_WIDTH = 1.0
MEAN_LINE_WIDTH = 0.75
IQR_ALPHA = 0.25

_EXCLUDED_VARIABLES = frozenset({VARNAME_ID, VARNAME_WID, "date"})
_WEIGHT_VARIABLES = frozenset({"weight"})
_BOUNDED_VARIABLES = frozenset(
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

type PanelPlotter = Callable[[Axes, str], None]
type OutlierStrategy = Literal["none", "upper", "two-sided"]


class SuffixFormatter(FuncFormatter):
    """Format tick values using compact suffixes (`k`, `m`, `bn`, `tr`)."""

    _SCALES = (
        (1.0e12, "tr"),
        (1.0e9, "bn"),
        (1.0e6, "m"),
        (1.0e3, "k"),
    )

    def __init__(self, default: str | None = None) -> None:
        """Create a formatter that shortens large magnitudes.

        Parameters
        ----------
        default
            Format specifier used for values without suffix, such as ``.2f``.
            If omitted, Matplotlib's default formatting is used.
        """
        self.default = default
        super().__init__(self._format_value)

    def _format_value(self, value: float, _position: int) -> str:
        """Format one tick value."""
        scaled = value
        suffix = ""
        for scale, candidate in self._SCALES:
            if abs(value) >= scale:
                scaled = value / scale
                suffix = candidate
                break

        if int(scaled) == scaled:
            fmt = ".0f"
        elif not suffix and self.default is not None:
            fmt = self.default
        else:
            fmt = ""

        sign = "$-$" if scaled < 0.0 else ""
        return f"{sign}{abs(scaled):{fmt}}{suffix}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(default={self.default!r})"


def _as_float_array(values: pd.Series) -> npt.NDArray[np.float64]:
    """Convert a Series to a float array with missing values represented by NaN."""
    array = values.to_numpy(dtype=np.float64, na_value=np.nan)
    return np.asarray(array, dtype=np.float64)


def _diagnostic_variables(df_data: pd.DataFrame) -> tuple[str, ...]:
    """Return the ordered variables included in diagnostic plots."""
    return tuple(str(name) for name in df_data if str(name) not in _EXCLUDED_VARIABLES)


def _variable_annotation(df_data: pd.DataFrame, variable: str) -> str:
    """Return a short or attached label, falling back to the variable name."""
    labels = df_data.attrs.get("variable_labels", {})
    return VARIABLE_LABELS_SHORT.get(variable, labels.get(variable, variable))


def _is_indicator(values: pd.Series) -> bool:
    """Return whether an integer-valued Series contains only indicator codes."""
    if not pd.api.types.is_integer_dtype(values.dtype):
        return False

    observed = _as_float_array(values)
    observed = observed[np.isfinite(observed)]
    return observed.size > 0 and bool(np.isin(observed, (0.0, 1.0)).all())


def _valid_weighted_values(
    values: npt.ArrayLike,
    weights: npt.ArrayLike,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Return finite values and corresponding finite, positive weights."""
    value_array = np.asarray(values, dtype=np.float64)
    weight_array = np.asarray(weights, dtype=np.float64)
    valid = np.isfinite(value_array) & np.isfinite(weight_array) & (weight_array > 0.0)
    return value_array[valid], weight_array[valid]


def _unweighted_moments(
    values: npt.NDArray[np.float64],
) -> tuple[float, float, float, float]:
    """Calculate an unweighted mean, median, and interquartile endpoints."""
    valid = values[np.isfinite(values)]
    if valid.size == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")

    q1, median, q3 = np.quantile(valid, [0.25, 0.5, 0.75])
    return float(valid.mean()), float(median), float(q1), float(q3)


def _weighted_moments(
    values: npt.NDArray[np.float64],
    weights: npt.NDArray[np.float64],
) -> tuple[float, float, float, float]:
    """Calculate a weighted mean, median, and interquartile endpoints."""
    valid_values, valid_weights = _valid_weighted_values(values, weights)
    if valid_values.size == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")

    q1, median, q3 = np.quantile(
        valid_values,
        [0.25, 0.5, 0.75],
        weights=valid_weights,
        method="inverted_cdf",
    )
    mean = np.average(valid_values, weights=valid_weights)
    return float(mean), float(median), float(q1), float(q3)


def _outlier_strategy(df_data: pd.DataFrame, variable: str) -> OutlierStrategy:
    """Select a mean-tail suppression strategy for one variable."""
    values = df_data[variable]
    value_labels = df_data.attrs.get("value_labels", {})
    if (
        variable in _BOUNDED_VARIABLES
        or variable in value_labels
        or pd.api.types.is_integer_dtype(values.dtype)
    ):
        return "none"

    observed = _as_float_array(values)
    observed = observed[np.isfinite(observed)]
    if observed.size == 0 or (observed.min() >= 0.0 and observed.max() <= 1.0):
        return "none"
    if observed.min() < 0.0:
        return "two-sided"
    return "upper"


def _mean_outlier_mask(
    values: npt.NDArray[np.float64],
    weights: npt.NDArray[np.float64] | None,
    strategy: OutlierStrategy,
) -> npt.NDArray[np.bool_]:
    """Identify observations beyond the configured IQR fences."""
    valid = np.isfinite(values)
    if weights is not None:
        valid &= np.isfinite(weights) & (weights > 0.0)
    mask = np.zeros(values.shape, dtype=bool)
    if strategy == "none" or not np.any(valid):
        return mask

    if weights is None:
        _, _, q1, q3 = _unweighted_moments(values)
    else:
        _, _, q1, q3 = _weighted_moments(values, weights)
    iqr = max(q3 - q1, 1.0)

    if strategy in {"upper", "two-sided"}:
        mask |= valid & (values > q3 + OUTLIER_IQR_FACTOR * iqr)
    if strategy == "two-sided":
        mask |= valid & (values < q1 - OUTLIER_IQR_FACTOR * iqr)

    return mask


def _stats_by_wave(
    df_data: pd.DataFrame,
    variable: str,
    *,
    weight_column: str | None,
    suppress_mean_outliers: bool,
) -> tuple[pd.DataFrame, int]:
    """Calculate wave moments and optionally suppress outliers from the mean."""
    rows: list[dict[str, object]] = []
    n_masked = 0
    strategy = _outlier_strategy(df_data, variable)

    for _, df_wave in df_data.groupby(VARNAME_WID, sort=True, observed=False):
        values = _as_float_array(df_wave[variable])
        weights = (
            _as_float_array(df_wave[weight_column])
            if weight_column is not None
            else None
        )
        if weights is None:
            mean, median, q1, q3 = _unweighted_moments(values)
        else:
            mean, median, q1, q3 = _weighted_moments(values, weights)

        if suppress_mean_outliers:
            mask = _mean_outlier_mask(values, weights, strategy)
            n_masked += int(np.count_nonzero(mask))
            retained = values.copy()
            retained[mask] = np.nan
            if weights is None:
                mean, _, _, _ = _unweighted_moments(retained)
            else:
                mean, _, _, _ = _weighted_moments(retained, weights)

        rows.append(
            {
                "date": df_wave["date"].median(),
                "mean": mean,
                "median": median,
                "q1": q1,
                "q3": q3,
            }
        )

    df_result = pd.DataFrame(
        rows,
        columns=("date", "mean", "median", "q1", "q3"),
    )
    return df_result, n_masked


def _style_date_axis(ax: Axes) -> None:
    """Apply common formatting to the survey-wave date axis."""
    ax.margins(x=0.0)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", labelrotation=0, labelsize=TICK_LABEL_SIZE)


def _add_top_clearance(ax: Axes) -> None:
    """Reserve clearance between plotted values and the panel annotation."""
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom, top + TOP_YLIM_MARGIN * (top - bottom))


def _style_count_axis(ax: Axes) -> None:
    """Format a nonnegative integer count axis."""
    ax.margins(y=YLIM_MARGIN)
    ax.set_ylim(bottom=0.0)
    ax.yaxis.set_major_locator(
        MaxNLocator(
            nbins=MAX_Y_TICKS - 1,
            integer=True,
            min_n_ticks=1,
        )
    )
    ax.yaxis.set_major_formatter(SuffixFormatter())
    ax.tick_params(axis="y", labelrotation=90, labelsize=TICK_LABEL_SIZE)
    _add_top_clearance(ax)


def _style_stat_axis(ax: Axes, df_data: pd.DataFrame, variable: str) -> None:
    """Format a descriptive-statistics axis without fixing indicator limits."""
    values = df_data[variable]
    value_labels = df_data.attrs.get("value_labels", {}).get(variable)
    indicator = _is_indicator(values)

    ax.margins(y=YLIM_MARGIN)
    ax.tick_params(axis="y", labelrotation=90, labelsize=TICK_LABEL_SIZE)

    if not indicator and value_labels:
        codes = np.array(sorted(value_labels), dtype=np.float64)
        ax.set_ylim(codes[0] - 0.25, codes[-1] + 0.25)
        ax.set_yticks(codes)
    elif variable in USD_VARIABLES:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=MAX_Y_TICKS - 1, min_n_ticks=1))
        ax.yaxis.set_major_formatter(SuffixFormatter())
    elif pd.api.types.is_integer_dtype(values.dtype) and not indicator:
        ax.yaxis.set_major_locator(
            MaxNLocator(
                nbins=MAX_Y_TICKS - 1,
                integer=True,
                min_n_ticks=1,
            )
        )
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    else:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=MAX_Y_TICKS - 1, min_n_ticks=1))

    _add_top_clearance(ax)


def _annotate_panel(ax: Axes, annotation: str) -> None:
    """Place a wrapped variable label tightly in the upper-left panel corner."""
    wrapped = "\n".join(fill(line, width=38) for line in annotation.splitlines())
    text = ax.annotate(
        wrapped,
        xy=(0.02, 0.98),
        xycoords="axes fraction",
        ha="left",
        va="top",
        fontsize=VARIABLE_LABEL_SIZE,
        fontstyle="italic",
    )
    text.set_in_layout(False)


def _draw_descriptive_legend(ax: Axes) -> None:
    """Draw the descriptive-statistics legend in a blank panel."""
    handles = (
        Line2D([], [], color=STEEL_BLUE, linewidth=LINE_WIDTH),
        Line2D([], [], color=MEAN_COLOR, linewidth=MEAN_LINE_WIDTH),
        Patch(facecolor=STEEL_BLUE, alpha=IQR_ALPHA, edgecolor="none"),
    )
    ax.set_axis_off()
    ax.legend(
        handles,
        ("Median", "Mean", "IQR"),
        loc="upper left",
        frameon=False,
        fontsize=TICK_LABEL_SIZE,
    )


def _write_grid(
    variables: Sequence[str],
    output_path: Path,
    plot_panel: PanelPlotter,
    *,
    suptitle: str,
    descriptive_legend: bool = False,
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> Path:
    """Write one five-column diagnostic grid and close its figure."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    first = int(descriptive_legend)
    nrows = (len(variables) + first + NCOLS - 1) // NCOLS

    with plt.rc_context({"font.family": "serif"}):
        fig, axes = plt.subplots(
            nrows,
            NCOLS,
            figsize=(FIGURE_WIDTH, ROW_HEIGHT * nrows),
            sharex=True,
            squeeze=False,
            constrained_layout=True,
        )
        try:
            if descriptive_legend:
                _draw_descriptive_legend(axes[0, 0])

            plot_axes = tuple(axes.flat)[first:]
            for ax, variable in zip(plot_axes, variables, strict=False):
                plot_panel(ax, variable)

            for ax in plot_axes[len(variables) :]:
                ax.set_visible(False)

            if xlabel is not None:
                fig.supxlabel(xlabel, fontsize=VARIABLE_LABEL_SIZE)
            if ylabel is not None:
                fig.supylabel(ylabel, fontsize=VARIABLE_LABEL_SIZE)
            fig.suptitle(suptitle, fontsize=FIGURE_TITLE_SIZE)
            fig.savefig(output_path)
        finally:
            plt.close(fig)

    logging.getLogger("PLOTS").info("Wrote diagnostic plot: %s", output_path)
    return output_path


def plot_nobs_indiv(
    df_data: pd.DataFrame,
    variables: Sequence[str],
    output_path: Path,
    *,
    suptitle: str,
) -> Path:
    """Plot the distribution of observations per respondent by variable."""
    df_nobs = df_data.groupby(VARNAME_ID, sort=False)[list(variables)].count()
    nmax = int(df_data.groupby(VARNAME_ID, sort=False).size().max())
    bins = [count - 0.5 for count in range(nmax + 2)]

    def plot_panel(ax: Axes, variable: str) -> None:
        """Draw one respondent observation-count histogram."""
        ax.hist(
            df_nobs[variable].to_numpy(),
            bins,
            color=STEEL_BLUE,
            linewidth=0.4,
            rwidth=0.9,
            edgecolor="white",
        )
        ax.set_xticks(np.arange(nmax + 1))
        ax.set_xlim(-0.75, nmax + 0.25)
        ax.tick_params(axis="x", labelsize=TICK_LABEL_SIZE)
        _style_count_axis(ax)
        _annotate_panel(ax, _variable_annotation(df_data, variable))

    return _write_grid(
        variables,
        output_path,
        plot_panel,
        suptitle=suptitle,
        xlabel="Nobs. per individual",
        ylabel="Respondents",
    )


def plot_nobs_wave(
    df_data: pd.DataFrame,
    variables: Sequence[str],
    output_path: Path,
    *,
    suptitle: str,
) -> Path:
    """Plot nonmissing observation counts by survey wave."""
    groups = df_data.groupby(VARNAME_WID, sort=True, observed=False)
    df_nobs = groups[list(variables)].count()
    dates = groups["date"].median()

    def plot_panel(ax: Axes, variable: str) -> None:
        """Draw nonmissing observation counts for one variable."""
        ax.plot(
            dates,
            df_nobs[variable],
            color=STEEL_BLUE,
            linewidth=LINE_WIDTH,
        )
        ax.grid(color="grey", linestyle=":")
        _style_date_axis(ax)
        _style_count_axis(ax)
        _annotate_panel(ax, _variable_annotation(df_data, variable))

    return _write_grid(
        variables,
        output_path,
        plot_panel,
        suptitle=suptitle,
        xlabel="Wave",
        ylabel="Number of observations",
    )


def plot_stats_wave(
    df_data: pd.DataFrame,
    variables: Sequence[str],
    output_path: Path,
    *,
    suptitle: str,
    weight_column: str | None = None,
    suppress_mean_outliers: bool = False,
) -> Path:
    """Plot means, medians, and interquartile ranges by survey wave."""
    logger = logging.getLogger("PLOTS")

    def plot_panel(ax: Axes, variable: str) -> None:
        """Draw descriptive statistics for one variable."""
        df_stats, n_masked = _stats_by_wave(
            df_data,
            variable,
            weight_column=weight_column,
            suppress_mean_outliers=suppress_mean_outliers,
        )
        if suppress_mean_outliers:
            logger.info(
                "Outlier suppression for %s (%s, %g*IQR): %d rows masked",
                variable,
                _outlier_strategy(df_data, variable),
                OUTLIER_IQR_FACTOR,
                n_masked,
            )

        dates = df_stats["date"].to_numpy()
        mean = df_stats["mean"].to_numpy(dtype=np.float64)
        median = df_stats["median"].to_numpy(dtype=np.float64)
        q1 = df_stats["q1"].to_numpy(dtype=np.float64)
        q3 = df_stats["q3"].to_numpy(dtype=np.float64)

        ax.fill_between(
            dates,
            q1,
            q3,
            color=STEEL_BLUE,
            alpha=IQR_ALPHA,
            linewidth=0.0,
        )
        ax.plot(
            dates,
            median,
            color=STEEL_BLUE,
            linewidth=LINE_WIDTH,
            alpha=0.8,
            zorder=50,
        )
        ax.plot(
            dates,
            mean,
            color=MEAN_COLOR,
            linewidth=MEAN_LINE_WIDTH,
            alpha=0.7,
            zorder=100,
        )
        _style_date_axis(ax)
        _style_stat_axis(ax, df_data, variable)
        _annotate_panel(ax, _variable_annotation(df_data, variable))

    return _write_grid(
        variables,
        output_path,
        plot_panel,
        suptitle=suptitle,
        descriptive_legend=True,
        xlabel="Wave",
    )


def run_diagnostics(df_data: pd.DataFrame, graph_dir: Path) -> tuple[Path, ...]:
    """Write all diagnostic reports for the processed SCE extract."""
    df_plot = df_data.reset_index()
    variables = _diagnostic_variables(df_plot)
    stats_variables = tuple(
        variable for variable in variables if variable not in _WEIGHT_VARIABLES
    )

    paths = (
        plot_nobs_indiv(
            df_plot,
            variables,
            graph_dir / "sce_indiv_obs.pdf",
            suptitle="SCE: Number of Observations per Respondent by Variable",
        ),
        plot_nobs_wave(
            df_plot,
            variables,
            graph_dir / "sce_nobs.pdf",
            suptitle="SCE: Number of Observations per Wave by Variable",
        ),
        plot_stats_wave(
            df_plot,
            stats_variables,
            graph_dir / "sce_descriptive.pdf",
            suptitle="SCE: Descriptive Statistics by Wave (with Outliers)",
        ),
        plot_stats_wave(
            df_plot,
            stats_variables,
            graph_dir / "sce_descriptive_no_outliers.pdf",
            suptitle="SCE: Descriptive Statistics by Wave (No Outliers)",
            suppress_mean_outliers=True,
        ),
        plot_stats_wave(
            df_plot,
            stats_variables,
            graph_dir / "sce_descriptive_weighted.pdf",
            suptitle=("SCE: Descriptive Statistics by Wave (Weighted, with Outliers)"),
            weight_column="weight",
        ),
        plot_stats_wave(
            df_plot,
            stats_variables,
            graph_dir / "sce_descriptive_weighted_no_outliers.pdf",
            suptitle=("SCE: Descriptive Statistics by Wave (Weighted, No Outliers)"),
            weight_column="weight",
            suppress_mean_outliers=True,
        ),
    )
    return paths
