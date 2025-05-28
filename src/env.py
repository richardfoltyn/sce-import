"""
Module to set up environment for running all Python scripts

Author: Richard Foltyn
"""

import argparse
from argparse import ArgumentParser

from os.path import expanduser, join
import os.path

from pydynopt.utils.logging import configure_logging

projname = "sce-import"
homedir = expanduser("~")

scriptdir = os.path.dirname(__file__)
repodir = os.path.abspath(join(scriptdir, "..", ".."))

inputdir = join(homedir, "data", "SCE")

rundir = join(homedir, "run", projname)
# Defaults are relative to rundir
graphdir = "graphs"
datadir = "output"
logdir = "logs"
cachedir = "cache"

# TODO: Remove in final version
import pandas as pd
import numpy as np

pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 150)
pd.set_option("display.max_info_columns", 200)

np.set_printoptions(linewidth=150)



class EnvConfig(argparse.Namespace):
    """
    Custom Namespace class used to hold parsed command-line arguments
    or default values.
    """

    def __init__(self):
        super(EnvConfig, self).__init__()

        self.inputdir = inputdir
        self.repodir = repodir
        self.rundir = rundir
        self.graphdir = None
        self.datadir = None
        self.logdir = None

    def set_defaults(self):
        """
        Set default values for missing attributes
        """

        # Set default subdirectories in rundir if none were specified
        attrs = "graphdir", "datadir", "logdir", "cachedir"

        for attr in attrs:
            value = getattr(self, attr, None)
            default = globals()[attr]
            if not value:
                setattr(self, attr, join(self.rundir, default))

    def post_process(self):
        # Create runtime directories
        attrs = "graphdir", "datadir", "logdir", "cachedir"

        for attr in attrs:
            value = getattr(self, attr)
            os.makedirs(value, exist_ok=True)


def env_setup() -> EnvConfig:
    """
    Perform environment setup, taking into account default values and
    user-provided CLI arguments.
    """

    p = ArgumentParser(description="SCE importer")
    p.add_argument(
        "--repo-dir",
        action="store",
        required=False,
        dest="repodir",
        default=repodir,
        help="Git repository root",
    )
    p.add_argument(
        "--input-dir", action="store", required=False, dest="inputdir", default=inputdir
    )
    p.add_argument(
        "--run-dir",
        action="store",
        required=False,
        dest="rundir",
        default=rundir,
        help="Runtime directory",
    )
    p.add_argument(
        "--data-dir",
        action="store",
        required=False,
        dest="datadir",
        default=None,
        help="Output directory for results",
    )
    p.add_argument(
        "--graph-dir",
        action="store",
        required=False,
        dest="graphdir",
        default=None,
        help="Output directory for graphs",
    )
    p.add_argument(
        "--log-dir",
        action="store",
        required=False,
        dest="logdir",
        default=None,
        help="Logging directory",
    )
    p.add_argument(
        "--cache-dir",
        action="store",
        required=False,
        dest="cachedir",
        default=None,
        help="Cache directory",
    )

    econf = EnvConfig()
    econf = p.parse_args(namespace=econf)

    econf.set_defaults()
    econf.post_process()

    configure_logging()

    return econf
