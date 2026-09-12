"""Create diagnostic plots from the processed SCE extract.

- Read the compressed Pickle produced by the importer.
- Write respondent, observation-count, and descriptive-statistics reports.

Author: Richard Foltyn
"""

import logging

import pandas as pd

from env import EnvConfig, add_logfile
from SCE.diagnostics import run_diagnostics


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
    run_diagnostics(df_data, econf.graphdir)


if __name__ == "__main__":
    main(EnvConfig.setup())
