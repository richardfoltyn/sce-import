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
- This project uses a private external library:
  - `pydynopt`: located in `$HOME/repos/pydynopt` (access in read-only mode).
- `ruff` and `ty` for type checking are installed directly in the operating system. Run them using the `uv run` prefix (e.g., `uv run ty check` and `uv run ruff check`) to ensure they use the local `.venv` environment and resolve dependencies correctly. Do not attempt to install them in the local environment.

### Execution and unit tests

- Never run the main script `main.py` unless explicitly asked to do so as it takes a long time.
- Run unit tests only at the **end** of a task, if applicable.
- When applicable, run pytest targets in parallel with pytest-xdist, using
  `uv run pytest -n auto <test paths>`.

## SCE data invariants

- Assume that the survey importing pipeline in [`src/SCE/importer.py`](file:///home/richard/repos/sce-import/src/SCE/importer.py) or main entry points like [`src/main.py`](file:///home/richard/repos/sce-import/src/main.py) process and structure the raw data correctly.
- Treat the resulting schema, index layout, and required identifiers as established invariants. Do not add defensive checks or alternate code paths for arbitrary unprepared DataFrames, missing required columns, or duplicate labels unless the user explicitly requests such support.

## Stata

- A Stata installation should be available in `/opt/stata/19/stata-se` or similar.
- Ask for approval before running Stata, a static code analysis usually is good enough.

## Questionnaire

- The processed, layout-preserved, and cleaned text of the Survey of Consumer Expectations (SCE) questionnaire is located at [`QUESTIONNAIRE.txt`](QUESTIONNAIRE.txt) in the workspace root.
