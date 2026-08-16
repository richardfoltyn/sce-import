"""Regression fixtures for selectable export formats (SCE-017)."""

from argparse import ArgumentParser

import pytest

from env import EXPORT_FORMATS, EnvConfig, parse_export_formats

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pickle", {"pickle"}),
        ("stata", {"stata"}),
        ("pickle,stata", {"pickle", "stata"}),
        ("pickle,stata,excel,csv", {"pickle", "stata", "excel", "csv"}),
        ("CSV,EXCEL", {"csv", "excel"}),  # case-insensitive
        ("pickle , stata , csv", {"pickle", "stata", "csv"}),  # whitespace tolerance
    ],
)
def test_parse_export_formats_valid(raw: str, expected: set[str]) -> None:
    """Verify valid format strings parse to the expected set."""
    assert parse_export_formats(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "pickle,invalid",
        "json",
        "pickle,xml,csv",
    ],
)
def test_parse_export_formats_invalid(raw: str) -> None:
    """Verify unknown format names raise ArgumentTypeError."""
    with pytest.raises(Exception, match="unknown export format"):
        parse_export_formats(raw)


def test_export_formats_constant() -> None:
    """Verify the supported formats frozenset has the expected members."""
    assert frozenset({"pickle", "stata", "excel", "csv"}) == EXPORT_FORMATS


def test_cli_default_formats() -> None:
    """Verify the CLI defaults to pickle-only."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)
    args = parser.parse_args([])
    assert args.formats == {"pickle"}


def test_cli_explicit_formats() -> None:
    """Verify the CLI accepts a comma-separated list."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)
    args = parser.parse_args(["--formats", "pickle,stata,csv"])
    assert args.formats == {"pickle", "stata", "csv"}


def test_cli_invalid_format_fails() -> None:
    """Verify unknown format names fail during argument parsing."""
    parser = ArgumentParser()
    EnvConfig.add_arguments(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--formats", "pickle,json"])
