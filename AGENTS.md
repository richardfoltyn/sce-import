# Project-Specific Instructions for AI Agents

- Follow the instructions in the global user-configuration instructions.
- This file contains additional project-specific instructions.

## Python

- This project exclusively targets Python 3.14
  (`requires-python = "==3.14.*"`). Use Python 3.14 language features where
  appropriate. This overrides any generic instruction requiring Python 3.13
  compatibility.
- This project uses `uv` to manage the local Python environment.
- Do not attempt to install additional packages in the local `venv`, unless explicitly asked to do so.
- `ruff` and `ty` for type checking are installed directly in the operating system. Run them using the `uv run` prefix (e.g., `uv run ty check` and `uv run ruff check`) to ensure they use the local `.venv` environment and resolve dependencies correctly. Do not attempt to install them in the local environment.

### Execution and unit tests

- Never run the main script `main.py` unless explicitly asked to do so as it takes a long time.
- Run unit tests only at the **end** of a task, if applicable.
- When applicable, run pytest targets in parallel with pytest-xdist, using
  `uv run pytest -n auto <test paths>`.

## Vendored survey plots

- `src/SCE/plots.py` is a vendored, byte-for-byte copy of
  `$HOME/repos/survey-plots/src/plots.py`.
- Do not edit, restyle, or format the vendored file in this repository, except for prototyping changes that will be pushed upstream.
- Update it only by selecting an explicit `survey-plots` Git revision and copying
  that revision's `src/plots.py`. SCE is not required to track the latest upstream
  revision or update in lockstep with other surveys.
- Consult `API.md` from the selected upstream revision and use only names listed
  in `plots.__all__`.
- Preserve the `# SPDX-License-Identifier: LGPL-3.0-or-later` header.
- After updating the vendored file, run:

  ```bash
  uv run ruff check --no-fix src/SCE/plots.py
  uv run ruff format --check src/SCE/plots.py
  uv run ty check src/SCE/plots.py
  uv run pytest -n auto
  ```

## Data

- The raw data is provided as Excel files in `$HOME/data/SCE`: `FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx`, `FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx`, `frbny-sce-public-microdata-20-24.xlsx`, and `frbny-sce-public-microdata-latest.xlsx`.

## Questionnaire

- The processed, layout-preserved, and cleaned text of the Survey of Consumer Expectations (SCE) questionnaire is located at [`QUESTIONNAIRE.txt`](QUESTIONNAIRE.txt).

## Run directory

- The run directory is `$HOME/run/sce-import`.
- Its subdirectories are `cache`, `graphs`, `logs`, `output`, and `stata`.
- Stata artifacts are under `$HOME/run/sce-import/stata`, with `graphs`,
  `logs`, and `output` subdirectories.

## SCE data invariants

- Assume that the survey importing pipeline in [`src/SCE/importer.py`](file:///home/richard/repos/sce-import/src/SCE/importer.py) or main entry points like [`src/main.py`](file:///home/richard/repos/sce-import/src/main.py) process and structure the raw data correctly.
- Treat the resulting schema, index layout, and required identifiers as established invariants. Do not add defensive checks or alternate code paths for arbitrary unprepared DataFrames, missing required columns, or duplicate labels unless the user explicitly requests such support.

## Stata

- A Stata installation should be available in `/opt/stata/19/stata-se` or similar.
- Ask for approval before running Stata, a static code analysis usually is good enough.
