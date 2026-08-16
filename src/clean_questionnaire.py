"""
Convert and clean the SCE PDF questionnaire to plain text.

This script runs ``pdftotext -layout`` to extract text from the questionnaire PDF,
preserves the visual column structure, cleans up Private Use Area characters,
and maps smart quotes, en-dashes, and ellipses to standard ASCII equivalents.

Author: Richard Foltyn
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Define module-level logger
logger = logging.getLogger("SCE.questionnaire")


def extract_text(pdf_path: Path) -> str:
    """
    Extract text from the PDF using ``pdftotext`` with layout preservation.

    Parameters
    ----------
    pdf_path
        Path to the PDF file.

    Returns
    -------
    The extracted layout text.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except FileNotFoundError:
        logger.error("pdftotext command not found. Please install poppler-utils.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running pdftotext: {e.stderr}")
        sys.exit(1)


def strip_preamble(text: str) -> str:
    """
    Remove the licensing and disclaimer preamble from the questionnaire text.

    Parameters
    ----------
    text
        The questionnaire text.

    Returns
    -------
    The questionnaire text starting with the survey title.
    """
    match = re.search(r"(?m)^[^\S\n]*Survey of Consumer Expectations[^\S\n]*$", text)
    if match:
        return text[match.start() :].lstrip("\x0c\n\r")
    return text


def clean_text(text: str) -> str:
    """
    Clean up non-ASCII and Private Use Area characters from the questionnaire text.

    Parameters
    ----------
    text
        The raw extracted text from the PDF questionnaire.

    Returns
    -------
    The cleaned plain text with standard ASCII equivalents.
    """
    # Replace Private Use Area characters representing radio buttons and checkboxes
    text = text.replace("\uf06d", "( )")
    text = text.replace("\uf071", "[ ]")

    # Replace smart quotes and other non-ASCII punctuation
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "--")
    text = text.replace("\u2026", "...")
    text = text.replace("\u00a9", "(c)")

    # Replace uppercase letter O when used as a radio button bullet at start of line
    text = re.sub(r"(?m)^(\x0c?\s*)O(\s+)", r"\1( )\2", text)

    return text


def main() -> None:
    # Set up logging configuration to output to standard error
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Convert and clean the SCE PDF questionnaire to plain text."
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the SCE PDF questionnaire.",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path
    workspace_dir = Path(__file__).resolve().parent.parent

    if shutil.which("pdftotext") is None:
        logger.error("pdftotext command not found. Please install poppler-utils.")
        sys.exit(1)

    if not pdf_path.exists():
        logger.error(f"Questionnaire PDF not found at {pdf_path}")
        sys.exit(1)

    logger.info(f"Extracting and cleaning text from {pdf_path.name}...")
    raw_text = extract_text(pdf_path)
    cleaned_text = clean_text(raw_text)
    final_text = strip_preamble(cleaned_text)

    # Write cleaned plain text (replacing form feeds with newlines)
    txt_content = final_text.replace("\x0c", "\n")
    txt_lines = [line.rstrip() for line in txt_content.splitlines()]
    txt_output = "\n".join(txt_lines)

    txt_path = workspace_dir / "QUESTIONNAIRE.txt"
    txt_path.write_text(txt_output, encoding="utf-8")
    logger.info(f"Saved cleaned plain text to {txt_path}")


if __name__ == "__main__":
    main()
