"""Test extensions to the vendored survey plotting module."""

from SCE import plots


def test_outlier_method_can_vary_by_variable() -> None:
    """Resolve mapped methods and disable omitted variables."""
    config = {
        "quantile": plots.OutlierMethod.QUANTILE,
        "iqr": plots.OutlierMethod.IQR,
    }

    assert (
        plots._resolve_outlier_method("quantile", config)
        is plots.OutlierMethod.QUANTILE
    )
    assert plots._resolve_outlier_method("iqr", config) is plots.OutlierMethod.IQR
    assert plots._resolve_outlier_method("omitted", config) is plots.OutlierMethod.NONE
    assert (
        plots._resolve_outlier_method("value", plots.OutlierMethod.IQR)
        is plots.OutlierMethod.IQR
    )
