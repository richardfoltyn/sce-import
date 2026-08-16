# sce-import

`sce-import` is a Python-based utility to import, clean, structure, and export the Survey of Consumer Expectations (SCE) microdata from the Federal Reserve Bank of New York (FRBNY). It concatenates raw Excel datasets, maps variable labels, attaches variable and value labels to Stata and Pickle outputs, performs sign corrections, and merges external family income ranks computed from American Community Survey (ACS) data.

## Author

- **Richard Foltyn**

## Features

- **Raw Data Concatenation**: Merges multiple historical and latest raw Excel microdata files (e.g., `FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx`, `FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx`, and `frbny-sce-public-microdata-latest.xlsx`).
- **Data Standardization**: Converts raw variables into standard representations, flips incorrect signs where decreases were coded as positive (e.g., in inflation/deflation rate responses), and maps categoricals.
- **ACS Income Rank Integration**: Merges external household total income ranks computed from IPUMS ACS data.
- **Multiple Export Formats**: Exports processed full datasets and reduced extracts
  to the formats selected via ``--formats``. Supported formats are
  Zstandard-compressed Pickle (``.pkl.zst``), Stata (``.dta``), Excel (``.xlsx``),
  and CSV (``.csv``). The default is ``pickle`` only; pass
  ``--formats pickle,stata,excel(csv`` to write all formats.
- **Diagnostic Plotting**: Generates plots illustrating panel spell lengths, observation counts per survey wave, and longitudinal statistics (mean, median, IQR) for variables over waves.

## Requirements

- **Python**: `==3.14.*`
- **Dependency & Environment Manager**: [uv](https://github.com/astral-sh/uv)
- **External Dependencies**:
  - Standard scientific libraries: `pandas >=3.0`, `numpy >=2.5`, `matplotlib >=3.11`, `openpyxl >=3.1`
  - System utilities: `poppler-utils` (specifically `pdftotext`, required only for processing the PDF questionnaire)
- **Development Dependencies**:
  - `pydynopt` (located in a sibling directory `../pydynopt` in editable mode; required only for the diagnostic plotting script `src/main_plot_diag.py`)

## Usage

All commands should be executed within the `uv` virtual environment.

### 1. Import and Process Data

```bash
uv run src/main.py
```

Optional CLI flags:
- `--input-dir <path>`: Directory containing raw SCE Excel sheets (defaults to `~/data/SCE`).
- `--run-dir <path>`: Runtime output base directory (defaults to `~/run/sce-import`).
- `--data-dir <path>`: Directory for processed output files (defaults to `<run-dir>/output`).
- `--graph-dir <path>`: Directory for diagnostic plots (defaults to `<run-dir>/graphs`).
- `--final-date YYYY-MM-DD`: Inclusive final survey date to retain. The default is
  unbounded.
- `--formats fmt,fmt,...`: Comma-separated list of export formats to write.  Valid
  values are `pickle`, `stata`, `excel`, `csv`.  The default is `pickle`.  Pickle
  is always fastest; Excel export can take several minutes for large data sets.

Because FRBNY updates the latest workbook in place, pass `--final-date` when a
reproducible, date-pinned sample is required. For example:

```bash
uv run src/main.py --final-date 2024-10-01
```

### 2. Generate Diagnostic Plots

```bash
uv run src/main_plot_diag.py
```

### 3. Extract and Clean Questionnaire Text

To extract the SCE questionnaire from PDF and clean it into a layout-preserved plain-text format:
```bash
uv run src/clean_questionnaire.py <path_to_pdf>
```

This runs `pdftotext -layout` to preserve horizontal layout structure, maps Wingdings radio buttons and checkboxes to standard `( )` and `[ ]` characters, converts non-ASCII punctuation to standard ASCII, strips the licensing preamble, and saves the result to `QUESTIONNAIRE.txt` at the root of the workspace.

### 4. Code Quality & Type Checking

To run code formatting, linting, and type checking:
```bash
uv run ruff check
uv run ty check
```

## License

This project is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3.0)**.

Refer to [`LICENSE.txt`](file:///home/richard/repos/sce-import/LICENSE.txt) for the full license terms.
