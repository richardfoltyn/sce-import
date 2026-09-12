# sce-import

`sce-import` is a Python-based utility to import, clean, structure, and export the Survey of Consumer Expectations (SCE) microdata from the Federal Reserve Bank of New York (FRBNY). It concatenates raw Excel datasets, maps variable labels, attaches variable and value labels to Stata and Pickle outputs, performs sign corrections, and merges external family income ranks computed from American Community Survey (ACS) data.

## Author

- **Richard Foltyn**

## Features

- **Raw Data Concatenation**: Merges historical and current raw Excel microdata files: `FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx`, `FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx`, `frbny-sce-public-microdata-20-24.xlsx`, and `frbny-sce-public-microdata-latest.xlsx`.
- **Data Standardization**: Converts raw variables into standard representations, flips incorrect signs where decreases were coded as positive (e.g., in inflation/deflation rate responses), and maps categoricals.
- **Output Metadata**: Attaches complete variable labels to full and extract
  outputs, plus applicable categorical value labels. Pickle stores them in
  `DataFrame.attrs`, Stata receives native labels, and an incomplete variable
  label registry stops the export.
- **ACS Income Rank Integration**: Merges external household total income ranks computed from IPUMS ACS data.
- **Multiple Export Formats**: Exports processed full datasets and reduced extracts
  to the formats selected via ``--formats``. Supported formats are
  Zstandard-compressed Pickle (``.pkl.zst``), Stata (``.dta``), Excel (``.xlsx``),
  and CSV (``.csv``). The default is ``pickle`` only; pass
  ``--formats pickle,stata,excel,csv`` to write all formats. CSV exports round
  percentage and percentile fields to two decimal places; other formats retain
  full processed precision.
- **Diagnostic Plotting**: Generates plots illustrating panel spell lengths,
  observation counts per survey wave, and weighted and unweighted longitudinal
  statistics (mean, median, IQR) for variables over waves.

## Requirements

- **Python**: `==3.14.*`
- **Dependency & Environment Manager**: [uv](https://github.com/astral-sh/uv)
- **External Dependencies**:
  - Standard scientific libraries: `pandas >=3.0`, `numpy >=2.5`, `matplotlib >=3.11`, `openpyxl >=3.1`
  - System utilities: `poppler-utils` (specifically `pdftotext`, required only for processing the PDF questionnaire)
## Usage

All commands should be executed within the `uv` virtual environment.

### 1. Verify Input Data Checksums

Before processing, check that local raw data files match expected MD5 checksums:
```bash
./manifest/verify_data.sh
```

For more options and instructions on recreating MD5 manifests, see [`manifest/README.md`](manifest/README.md).

### 2. Import and Process Data

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

### 3. Generate Diagnostic Plots

```bash
uv run src/main_plot_diag.py
```

### 4. Extract and Clean Questionnaire Text

To extract the SCE questionnaire from PDF and clean it into a layout-preserved plain-text format:
```bash
uv run src/clean_questionnaire.py <path_to_pdf>
```

This runs `pdftotext -layout` to preserve horizontal layout structure, maps Wingdings radio buttons and checkboxes to standard `( )` and `[ ]` characters, converts non-ASCII punctuation to standard ASCII, strips the licensing preamble, and saves the result to `QUESTIONNAIRE.txt` at the root of the workspace.

`QUESTIONNAIRE.txt` was extracted from the [official FRBNY SCE core
questionnaire](https://www.newyorkfed.org/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-survey-core-module-public-questionnaire.pdf).
The source PDF has SHA-256
`e30e2ef1f925cb90aef1d5d6c9b13c6307b1f311e40c5b894ad27ddf69066e93`.
FRBNY publishes this as a single, unversioned document rather than an archive of
historical core questionnaires.

Numerical-literacy correctness is therefore calculated only for responses from
new respondents (`tenure == 1`), as specified by the published questionnaire.
Raw responses recorded for incumbent pilot-panel members are retained, but their
correctness indicators remain missing because the historical instrument cannot
be established from the published documentation.

### 5. Code Quality & Type Checking

To run code formatting, linting, and type checking:
```bash
uv run ruff check
uv run ty check
```

## License

This project is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3.0)**.

Refer to [`LICENSE.txt`](file:///home/richard/repos/sce-import/LICENSE.txt) for the full license terms.
