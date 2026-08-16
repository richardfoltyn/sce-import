"""
Module to set up environment for running all Python scripts.

- Define the `EnvConfig` class used to hold parsed CLI arguments.
- Wire up logging and runtime paths.

Author: Richard Foltyn
"""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
import datetime
import logging
from pathlib import Path
import platform
import sys
from typing import Any, Self

import numpy as np
import pandas as pd

old_factory = logging.getLogRecordFactory()


def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    """
    Record factory to attach relative time attributes.

    Parameters
    ----------
    *args
        Positional arguments.
    **kwargs
        Keyword arguments.

    Returns
    -------
    logging.LogRecord
        The created log record with custom relative time attributes.
    """
    record = old_factory(*args, **kwargs)

    # Created timestamp in seconds
    created = record.relativeCreated / 1000.0

    rdays = int(created / 60 / 60 / 24)
    rem = created % (60 * 60 * 24)
    rhours = int(rem / 60 / 60)
    rem = rem % (60 * 60)
    rminutes = int(rem / 60)
    rseconds = rem % 60

    record.rday = rdays  # type: ignore[attr-defined]
    record.rhrs = rhours  # type: ignore[attr-defined]
    record.rmin = rminutes  # type: ignore[attr-defined]
    record.rsec = rseconds  # type: ignore[attr-defined]

    return record


def configure_logging(reltime: bool = True) -> None:
    """
    Configure a logging framework with the default console handler.

    Parameters
    ----------
    reltime
        Print time stamp as relative time since logging start.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Console
    ch = logging.StreamHandler(sys.stdout)
    # Set the default log level to INFO, otherwise we'll be flooded by MPL, etc. log messages
    ch.setLevel(logging.INFO)

    if reltime:
        # Set custom RecordFactory to attach relative time attributes
        logging.setLogRecordFactory(record_factory)
        fmt = "[{rday:d}d {rhrs:02d}:{rmin:02d}:{rsec:04.1f}] {name} {levelname}: {message}"
        formatter = logging.Formatter(fmt=fmt, style="{")
    else:
        fmt = "[%(asctime)s] %(name)s %(levelname)s: %(message)s"
        # Format used the (asctime) field
        datefmt = "%H:%M:%S"
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    # Turn off DEBUG messages for Matplotlib, etc.
    logger = logging.getLogger("matplotlib")
    logger.setLevel(logging.INFO)

    logger = logging.getLogger("numexpr.utils")
    logger.setLevel(logging.WARNING)

    logger = logging.getLogger("fontTools")
    logger.setLevel(logging.WARNING)


def add_logfile(
    file: Path | str,
    *,
    logdir: Path | str | None = None,
    file_timestamp: bool = False,
    date: bool = False,
    time: bool = False,
    reltime: bool = False,
    append: bool = False,
) -> logging.FileHandler:
    """
    Add file handler to current logger.

    Parameters
    ----------
    file
        Log file name or path.
    logdir
        Log directory.
    file_timestamp
        If true, append time stamp to log file.
    date
        Add date to log output.
    time
        Add time stamp to log output.
    reltime
        Add relative time stamp since logging start. Ignores `date` and `time`
        arguments.
    append
        If true, append to existing log file.

    Returns
    -------
    logging.FileHandler
        The added file handler.
    """
    timestamp = datetime.datetime.now()
    path = Path(file)

    if file_timestamp:
        suffix = timestamp.strftime("%Y%m%d-%Hh%Mm")
        root = path.stem
        ext = path.suffix or ".log"
        path = path.with_name(f"{root}-{suffix}{ext}")

    if logdir:
        path = Path(logdir) / path

    logger = logging.getLogger()

    mode = "a" if append else "w"
    fh = logging.FileHandler(path, mode=mode)
    fh.setLevel(logging.DEBUG)

    if date or time:
        fmt = "%(asctime)s %(name)s %(levelname)s: %(message)s"
        # Format used the (asctime) field
        tokens = []
        if date:
            tokens.append("%Y-%m-%d")
        if time:
            tokens.append("%H:%M:%S")
        datefmt = " ".join(tokens)
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    elif reltime:
        # Set custom RecordFactory to attach relative time attributes
        logging.setLogRecordFactory(record_factory)
        fmt = (
            "[{rday:d}d {rhrs:02d}:{rmin:02d}:{rsec:04.1f}] {name} {levelname}: "
            "{message}"
        )
        formatter = logging.Formatter(fmt=fmt, style="{")
    else:
        fmt = "%(name)s %(levelname)s: %(message)s"
        formatter = logging.Formatter(fmt=fmt)

    fh.setFormatter(formatter)

    logger.addHandler(fh)

    logger.info(f"Log started on {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Logging to {path}")

    info = platform.uname()
    tokens = []
    if info.node:
        tokens.append(f"host {info.node}")
    tokens.append(
        " ".join(tok for tok in (info.system, info.release, info.version) if tok)
    )
    logger.info(f"Running on {', '.join(tok.strip() for tok in tokens)}")

    return fh


projname = "sce-import"
homedir = Path("~").expanduser()

repodir = Path(__file__).resolve().parent.parent
inputdir = homedir / "data" / "SCE"

rundir = homedir / "run" / projname
# Defaults are relative to rundir
graphdir = Path("graphs")
datadir = Path("output")
logdir = Path("logs")
cachedir = Path("cache")

# TODO: Remove in final version
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 150)
pd.set_option("display.max_info_columns", 200)

np.set_printoptions(linewidth=150)


def parse_iso_date(value: str) -> datetime.date:
    """Parse an ISO calendar date for a command-line option.

    Parameters
    ----------
    value
        Date text in ``YYYY-MM-DD`` format.

    Returns
    -------
    datetime.date
        Parsed calendar date.

    Raises
    ------
    ArgumentTypeError
        If ``value`` is not a valid date in the required format.
    """
    message = f"invalid date {value!r}; expected YYYY-MM-DD"
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(message) from exc

    # date.fromisoformat also accepts compact ISO forms; require the documented
    # dashed CLI representation to keep invocation and error messages predictable.
    if value != parsed.isoformat():
        raise ArgumentTypeError(message)

    return parsed


class EnvConfig(Namespace):
    """
    Custom Namespace class used to hold parsed command-line arguments.

    Holds either user-provided overrides or resolved defaults as `pathlib.Path` objects.
    """

    repodir: Path
    inputdir: Path
    rundir: Path
    graphdir: Path
    datadir: Path
    logdir: Path
    cachedir: Path
    final_date: datetime.date | None

    def __init__(self) -> None:
        """
        Initialize the EnvConfig instance with default Path placeholders.
        """
        super().__init__()

        # Private inputs for parsing (can be None)
        self._inputdir: Path | None = None
        self._rundir: Path | None = None
        self._graphdir: Path | None = None
        self._datadir: Path | None = None
        self._logdir: Path | None = None
        self._cachedir: Path | None = None

        # Public fields (guaranteed to be Path)
        self.repodir = repodir
        self.inputdir = Path(inputdir)
        self.rundir = Path(rundir)
        self.graphdir = Path()
        self.datadir = Path()
        self.logdir = Path()
        self.cachedir = Path()
        self.final_date = None

    def set_defaults(self) -> None:
        """
        Set default values for missing attributes.
        """
        self.inputdir = self._inputdir if self._inputdir is not None else inputdir
        self.rundir = self._rundir if self._rundir is not None else rundir

        self.graphdir = _resolve_path(self._graphdir, graphdir, self.rundir)
        self.datadir = _resolve_path(self._datadir, datadir, self.rundir)
        self.logdir = _resolve_path(self._logdir, logdir, self.rundir)
        self.cachedir = _resolve_path(self._cachedir, cachedir, self.rundir)

    def create_directories(self) -> None:
        """
        Create run-time directories.
        """
        dirs = (
            self.graphdir,
            self.datadir,
            self.logdir,
            self.cachedir,
        )
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def configure_logging(self) -> None:
        """
        Configure logging.
        """
        configure_logging()

    def post_process(self) -> None:
        """
        Post-process parsed command-line arguments and set derived values.
        """
        pass

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        """
        Add command-line arguments to the parser.

        Parameters
        ----------
        parser
            The argument parser to add arguments to.
        """

        parser.add_argument(
            "--input-dir",
            dest="_inputdir",
            type=Path,
            help="Input directory",
        )
        parser.add_argument(
            "--run-dir",
            dest="_rundir",
            type=Path,
            help="Runtime directory",
        )
        parser.add_argument(
            "--data-dir",
            dest="_datadir",
            type=Path,
            help="Output directory for results",
        )
        parser.add_argument(
            "--graph-dir",
            dest="_graphdir",
            type=Path,
            help="Output directory for graphs",
        )
        parser.add_argument(
            "--log-dir",
            dest="_logdir",
            type=Path,
            help="Logging directory",
        )
        parser.add_argument(
            "--cache-dir",
            dest="_cachedir",
            type=Path,
            help="Cache directory",
        )
        parser.add_argument(
            "--final-date",
            type=parse_iso_date,
            metavar="YYYY-MM-DD",
            help="inclusive final survey date (default: unbounded)",
        )

    @classmethod
    def setup(
        cls,
        *args: Any,
        description: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """
        Parse command-line arguments and create a configured environment.

        Parameters
        ----------
        description
            The parser description.

        Returns
        -------
        Self
            The configured environment.
        """
        parser = ArgumentParser(description=description or "SCE importer")
        cls.add_arguments(parser)

        econf = cls()
        parser.parse_args(*args, namespace=econf, **kwargs)

        econf.set_defaults()
        econf.create_directories()
        econf.configure_logging()
        econf.post_process()

        return econf


def _resolve_path(
    value: Path | None,
    default_path: Path,
    base_dir: Path,
) -> Path:
    """
    Resolve a user override path against a base directory.

    Parameters
    ----------
    value
        The user-specified override path, if any.
    default_path
        The default relative path to use if no override is provided.
    base_dir
        The base directory to resolve relative paths against.

    Returns
    -------
    Path
        The fully resolved path.
    """
    path = value if value is not None else default_path
    if not path.is_absolute():
        path = base_dir / path
    return path
