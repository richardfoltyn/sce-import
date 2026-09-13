"""Test the SCE-specific diagnostic plotting orchestration."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from env import EnvConfig
import main_plot_diag
from SCE.annotations import (
    PERCENT_VARIABLES,
    USD_VARIABLES,
    VARIABLE_LABELS_SHORT,
)
from SCE.constants import VARNAME_ID, VARNAME_WEIGHT, VARNAME_WID
from SCE.plots import OutlierMethod, OutlierTail


def test_main_configures_all_diagnostic_plots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass SCE columns, labels, and policies to the shared plotting API."""
    idx = pd.MultiIndex.from_tuples(
        [(1, 202401)],
        names=(VARNAME_ID, VARNAME_WID),
    )
    df_data = pd.DataFrame(
        {
            VARNAME_WEIGHT: [0.5],
            "date": [pd.Timestamp("2024-01-01")],
            "infl_1y": [2.0],
            "prob_lose_job": [10.0],
            "num_lit_q3": [10.0],
            "num_lit_q6": [5.0],
            "num_lit_q1": [150.0],
            "working": [1],
            "custom_metric": [3.0],
        },
        index=idx,
    )
    df_data.attrs["variable_labels"] = {
        "infl_1y": "Long inflation label",
        "working": "Currently working",
        "custom_metric": "Custom label",
    }
    value_labels = {"custom_metric": {3: "Three"}}
    df_data.attrs["value_labels"] = value_labels

    data_dir = tmp_path / "output"
    graph_dir = tmp_path / "graphs"
    log_dir = tmp_path / "logs"
    data_dir.mkdir()
    input_path = data_dir / "sce_extract.pkl.zst"
    input_path.touch()

    econf = EnvConfig()
    econf.datadir = data_dir
    econf.graphdir = graph_dir
    econf.logdir = log_dir

    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def recorder(name: str) -> Callable[..., Path]:
        def record(*args: object, **kwargs: object) -> Path:
            calls.append((name, args, kwargs))
            return args[2]  # type: ignore

        return record

    def read_pickle(_path: Path) -> pd.DataFrame:
        return df_data

    def add_logfile(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(main_plot_diag.pd, "read_pickle", read_pickle)
    monkeypatch.setattr(main_plot_diag, "add_logfile", add_logfile)
    monkeypatch.setattr(main_plot_diag, "plot_nobs_by_id", recorder("nobs_by_id"))
    monkeypatch.setattr(
        main_plot_diag,
        "plot_nobs_by_wave",
        recorder("nobs_by_wave"),
    )
    monkeypatch.setattr(
        main_plot_diag,
        "plot_stats_by_wave",
        recorder("stats_by_wave"),
    )

    main_plot_diag.main(econf)

    assert [name for name, _, _ in calls] == [
        "nobs_by_id",
        "nobs_by_wave",
        "stats_by_wave",
        "stats_by_wave",
        "stats_by_wave",
        "stats_by_wave",
    ]
    output_names: list[str] = []
    for _, args, _ in calls:
        output_path = args[2]
        assert isinstance(output_path, Path)
        output_names.append(output_path.name)
    assert output_names == [
        "sce_indiv_obs.pdf",
        "sce_nobs.pdf",
        "sce_descriptive.pdf",
        "sce_descriptive_no_outliers.pdf",
        "sce_descriptive_weighted.pdf",
        "sce_descriptive_weighted_no_outliers.pdf",
    ]

    variables = calls[0][1][1]
    assert variables == (
        VARNAME_WEIGHT,
        "infl_1y",
        "prob_lose_job",
        "num_lit_q3",
        "num_lit_q6",
        "num_lit_q1",
        "working",
        "custom_metric",
    )
    assert calls[1][1][1] == variables
    stats_variables = (
        "infl_1y",
        "prob_lose_job",
        "num_lit_q3",
        "num_lit_q6",
        "num_lit_q1",
        "working",
        "custom_metric",
    )
    for _, args, _ in calls[2:]:
        assert args[1] == stats_variables

    assert calls[0][2]["id_column"] == VARNAME_ID
    assert calls[1][2]["wave_column"] == VARNAME_WID
    for _, _, kwargs in calls[1:]:
        assert kwargs["x_column"] == "date"

    labels = calls[0][2]["variable_labels"]
    assert isinstance(labels, dict)
    assert labels["infl_1y"] == VARIABLE_LABELS_SHORT["infl_1y"]
    assert labels["num_lit_q1"] == VARIABLE_LABELS_SHORT["num_lit_q1"]
    assert calls[1][2]["variable_labels"] == labels

    stat_labels = calls[2][2]["variable_labels"]
    assert isinstance(stat_labels, dict)
    assert stat_labels["infl_1y"] == f"{VARIABLE_LABELS_SHORT['infl_1y']} (%)"
    assert stat_labels["prob_lose_job"] == (
        f"{VARIABLE_LABELS_SHORT['prob_lose_job']} (%)"
    )
    assert stat_labels["num_lit_q1"] == (
        f"{VARIABLE_LABELS_SHORT['num_lit_q1']} ($)".replace("$", r"\$")
    )
    assert stat_labels["num_lit_q3"] == VARIABLE_LABELS_SHORT["num_lit_q3"]
    assert stat_labels["working"] == "Currently working"
    assert stat_labels["custom_metric"] == "Custom label"
    assert USD_VARIABLES.isdisjoint(PERCENT_VARIABLES)
    for _, _, kwargs in calls[2:]:
        assert kwargs["variable_labels"] == stat_labels
        assert kwargs["value_labels"] == value_labels
        assert kwargs["compact_variables"] == USD_VARIABLES

    assert "weight_column" not in calls[2][2]
    assert "weight_column" not in calls[3][2]
    assert calls[4][2]["weight_column"] == VARNAME_WEIGHT
    assert calls[5][2]["weight_column"] == VARNAME_WEIGHT

    for index in (3, 5):
        kwargs = calls[index][2]
        outlier_methods = kwargs["outlier_method"]
        assert isinstance(outlier_methods, dict)
        assert outlier_methods == dict.fromkeys(stats_variables, OutlierMethod.IQR) | {
            "num_lit_q3": OutlierMethod.QUANTILE,
            "num_lit_q6": OutlierMethod.QUANTILE,
        }
        assert kwargs["outlier_tail_fraction"] == 0.025
        assert kwargs["outlier_iqr_factor"] == 100.0
        outlier_tails = kwargs["outlier_tails"]
        assert isinstance(outlier_tails, dict)
        assert outlier_tails["prob_lose_job"] is OutlierTail.NONE
