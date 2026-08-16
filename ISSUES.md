# SCE importer code-review issues

This document records the findings from a static and data-assisted review of the
SCE import, transformation, ACS-rank merge, export, and diagnostic code. Each
unchecked section is intended to be a self-contained task that can be completed
in a separate agent session.

## Review scope and evidence

Reviewed files:

- `src/SCE/importer.py`
- `src/SCE/pandas_helpers.py`
- `src/SCE/annotations.py`
- `src/SCE/enums.py`
- `src/main.py`
- `src/main_plot_diag.py`
- `src/env.py`
- `stata/main_ftotinc_IPUMS.do`
- `data/IPUMS_ftotinc_rank_by_year_sce_bins.csv`
- `README.md` and `pyproject.toml`

Checks performed:

- `uv run ruff check` — passed.
- `uv run ty check` — passed.
- Read-only inspection of the three Excel headers and existing cache/output
  files under `~/run/sce-import`.
- Static inspection of the Stata script and its existing log. Stata was not run.
- `src/main.py` was not run.

Snapshot-specific counts below are evidence from the currently available raw
files (180,268 observations through May 1, 2025), not assumptions that should be
hard-coded into production code.

Priority meanings:

- **P0:** existing output is silently corrupted or materially biased.
- **P1:** incorrect/incomplete output or a likely near-term runtime failure.
- **P2:** maintainability, metadata, reproducibility, performance, or diagnostic
  correctness.

---

## [x] SCE-001 — Prevent household composition from leaking across respondents

**Priority:** P0  
**Files:** `src/SCE/importer.py` (household update block around lines 535–559)

### Problem

Household composition is reindexed with a global forward fill:

```python
df_comp = df_comp.reindex(df_full.index, method="ffill")
```

The index is ordered by `(userid, wid)`, so a respondent without an observed
initial composition inherits the last composition of the preceding respondent.
This also contaminates derived `num_kids`.

The current raw-data snapshot contains 742 users without a complete `Q45new_*`
row. Reproducing the current algorithm and comparing it with a within-user
forward fill found 2,294 contaminated rows for 701 users. In addition, 1,029
complete `D2new_*` rows from 2013 have missing `D1`; the code ignores them even
though they are valid composition baselines for incumbent panel members.

### Task

1. Build composition update rows from every complete `Q45new_*` or `D2new_*`
   observation. Do not require `D1 == 2` when a complete `D2new_*` response is
   actually present; this is necessary for the 2013 incumbent-panel baseline.
2. Forward-fill strictly within `userid`, preserving missing values before a
   respondent's first observed composition.
3. Keep partial/incomplete update rows from overwriting a known complete state,
   or define and document component-wise update semantics if that is preferred.
4. Derive `num_kids` only from the corrected within-user state.
5. Factor this into a focused helper so its behavior can be checked without
   running the full importer.

### Acceptance criteria

- No value can propagate across a `userid` boundary.
- A user with no composition observation remains missing rather than inheriting
  another user's household.
- A complete `D2new_*` row with missing `D1` seeds that user's state.
- Values before the first observed state remain missing.
- A small multi-user regression fixture covers all four cases above.
- `uv run ruff check` and `uv run ty check` pass.

---

## [x] SCE-002 — Recompute ACS income ranks after excluding IPUMS sentinel values and applying weights consistently

**Priority:** P0  
**Files:** `stata/main_ftotinc_IPUMS.do`,
`data/IPUMS_ftotinc_rank_by_year_sce_bins.csv`

### Problem

The pooled-rank branch computes the CDF before recoding IPUMS missing-value
sentinels:

```stata
by year, sort: cumul ftotinc [fw=perwt], generate(rank)
...
replace ftotinc = max(0, ftotinc)
```

Unlike the later college branch, it never executes:

```stata
recode ftotinc (9999998/9999999 = .)
drop if missing(ftotinc)
```

The existing Stata log confirms that `9999999` is present: it is the unweighted
95th and weighted 99th percentile in the pooled sample. These records therefore
enter every CDF denominator and the top SCE income bin. The pooled branch also
uses an unweighted conditional median:

```stata
collapse (median) rank, by(year lbound)
```

while the later branch correctly supplies `[fw=perwt]`. The committed rank table
and every merged `Q47_rank`/`hh_inc_bin_rank` are consequently based on a biased
mapping.

### Task

1. Recode `9999998/9999999` to missing and drop missing `ftotinc` before `cumul`
   in the pooled branch.
2. Use `perwt` consistently when calculating the within-bin median rank.
3. Add diagnostics that report excluded sentinel counts by year and verify that
   no sentinel reaches `egen ... cut()`.
4. Regenerate `data/IPUMS_ftotinc_rank_by_year_sce_bins.csv` from the corrected
   script. Per `AGENTS.md`, ask for approval before running Stata.
5. Compare old and new mappings by year/bin and summarize the effect in the
   commit or task notes.

### Acceptance criteria

- The CDF and conditional median both use the intended ACS person weights.
- Missing-value sentinels are absent before ranking and binning.
- Every year has exactly bins 1–11, ranks are in `[0, 1]`, and ranks increase
  monotonically with `ibin` within year.
- The committed CSV is the output of the corrected script.
- The Python merge still passes `validate="m:1"` for the regenerated table.

### Completion notes

- The Stata 19 regeneration excluded 2,404,414 adult records with IPUMS
  `FTOTINC` sentinel codes, with unweighted counts reported separately for each
  year in the Stata log.
- The corrected mapping changed 175 of 187 year/bin ranks. The mean change was
  +0.0117 (1.17 percentile points), with changes ranging from -0.013 to +0.032;
  the largest was for 2008 bin 10, which moved from 0.892 to 0.924.
- All 17 years have unique bins 1–11, ranks in `[0, 1]`, and strictly increasing
  ranks within year. A synthetic merge covering every regenerated key passed
  the importer's `validate="m:1"` constraint.

---

## [x] SCE-003 — Preserve missingness in conditional binary indicators

**Priority:** P1  
**Files:** `src/SCE/importer.py` (derived indicators around lines 210, 232–234,
535–538, and the spouse derivation around lines 583–586)

### Problem

Equality followed by integer casting turns missing/not-applicable responses into
zero. Two material cases are:

```python
df_extract["looking_for_job"] = (df_full["Q15"] == 1).astype(int)
hh_changed = df_full["D1"] == 2
df_extract["hh_changed"] = hh_changed.astype(np.uint8)
```

In the current snapshot, 173,946 of 180,268 `Q15` values are structurally
missing, but all become `looking_for_job == 0`. Similarly, 23,709 missing `D1`
values—primarily initial interviews—become `hh_changed == 0`. “Not asked” is not
equivalent to “No.” The same pattern would affect `spouse_working` once its typo
is fixed, and can affect any future `any(axis=1).astype(...)` derivation when all
source indicators are missing.

### Task

1. Map explicit response codes to 0/1 while preserving missing source values,
   for example `Q15: {1: 1, 2: 0}` and `D1: {1: 0, 2: 1}`.
2. Introduce a small helper for “any selected indicator is true” that returns
   missing when all source indicators are missing.
3. Apply that helper to `working` and the repaired `spouse_working`; current
   fully observed `Q10_*` rows should remain unchanged.
4. Choose and document a consistent output representation for nullable binary
   variables (nullable boolean/integer or numeric 0/1/NA that exports safely to
   Stata).

### Acceptance criteria

- Missing `Q15` produces missing `looking_for_job`.
- Missing `D1` produces missing `hh_changed`.
- Explicit “No/unchanged” responses still produce zero.
- All-missing component rows produce missing aggregate indicators.
- Focused fixtures cover yes, no, and not-applicable states.

### Completion notes

- Conditional binary outputs now use pandas nullable `Int8` values (`0`, `1`,
  and `pd.NA`), which round-tripped successfully through the Stata writer.
- Cached-data validation covered all 180,268 observations. The existing
  fully-observed `working` results were unchanged, while only the 6,322 observed
  `Q15` and 156,559 observed `D1` responses receive non-missing derived values.
- Focused fixtures cover explicit yes/no codes, partial multi-response rows, and
  wholly missing conditional responses.

---

## [x] SCE-004 — Restore the missing `spouse_working` extract variable

**Priority:** P1  
**Files:** `src/SCE/importer.py` (lines 575–586),
`src/SCE/annotations.py`

### Problem

The raw fields are named `HH2_1`, `HH2_2`, … and `DHH2_1`, `DHH2_2`, …, but the
extract checks for and reads nonexistent `HH_1`/`HH_2` fields:

```python
if "HH_1" in df_full.columns:
    ... df[["HH_1", "HH_2"]] ...
```

The condition is always false for all three current source files, so
`spouse_working` is absent even though it is advertised in `VARIABLE_LABELS`.
After initial and repeat responses are merged, `df_full["HH2_1"]` and
`df_full["HH2_2"]` each have 98,382 non-missing observations.

### Task

1. Confirm from the SCE questionnaire/codebook that `HH2_1` and `HH2_2` are the
   full-time and part-time working categories.
2. Derive `spouse_working` from the merged `df_full` `HH2_*` fields, not the raw
   `df`, so `DHH2_*` updates are included.
3. Preserve missingness when no spouse-employment response is available, as
   specified in SCE-003.
4. Ensure the extract schema and labels include the repaired field.

### Acceptance criteria

- `spouse_working` is present whenever the source schema contains `HH2_*`.
- Initial `HH2_*` and repeat `DHH2_*` observations both contribute.
- Full-time/part-time maps to one, observed non-working statuses map to zero,
  and all-missing statuses remain missing.
- No references to `HH_1` or `HH_2` remain.

### Completion notes

- `spouse_working` is derived from the merged `df_full` `HH2_*` fields, so both
  initial `HH2_*` and repeat `DHH2_*` responses contribute.
- Per the questionnaire, full-time, part-time, and self-employment categories
  (`HH2_1`--`HH2_3`) map to one; observed categories `HH2_4`--`HH2_11` map to
  zero, and wholly missing responses remain missing.
- Cached-data validation produced 98,382 non-missing `spouse_working` values and
  confirmed coverage of both initial and repeat responses.

---

## [x] SCE-005 — Correct the ACS reference-year calculation on month-start interview dates

**Priority:** P1  
**Files:** `src/SCE/importer.py` (`merge_inc_rank`, lines 628–637)

### Problem

The code tries to align an interview date to the beginning of its month by
subtracting `pd.offsets.MonthBegin()`:

```python
beg_month = df["date"] - pd.offsets.MonthBegin()
```

For a date already on the first day of a month, pandas rolls it back to the
*previous* month. This changes the reference-year choice at the January and July
thresholds. In the current output, 395 observations (393 with reported income)
receive a different ACS year solely because their interview occurred on the
first day of January or July.

### Task

1. Extract the reference-year rule into a named helper.
2. Normalize dates with month-period semantics (or use the survey month
   directly) rather than subtracting an anchored offset.
3. Preserve the intended rule documented by the existing code: January–June map
   to the previous calendar year and July–December map to the current calendar
   year. If a different economic convention is desired, document and test it.
4. Use the same helper for both full and extract rank merges.

### Acceptance criteria

- January 1 and January 2 map to the same reference year.
- July 1 and July 2 map to the same reference year.
- Boundary fixtures cover December/January, June/July, and leap-year dates.
- Reference-year assignment depends on survey month, not interview day.

### Completion notes

- ACS reference years are now assigned by a shared, month-period-based helper:
  January--June map to the previous calendar year and July--December map to the
  current calendar year.
- Both full and extract rank merges use the helper through `merge_inc_rank`, so
  interview days at the January and July boundaries no longer alter the result.
- Focused fixtures cover December/January, June/July, same-month day invariance,
  and a leap-day interview.

---

## [ ] SCE-006 — Make `final_date` usable and apply it before the ACS merge

**Priority:** P1  
**Files:** `src/main.py` (`process_data` around lines 43–101 and `main` around
lines 159–168), `src/env.py`, `README.md`

### Problem

`process_data` documents `final_date` as `datetime.date`, but pandas 3 raises a
`TypeError` when a datetime64 Series is directly compared with a Python
`datetime.date`. The commented example happens to use `pd.to_datetime`, which
returns a `Timestamp` and hides the API mismatch.

The cutoff is also applied *after* `merge_inc_rank`. A caller cannot use a cutoff
to exclude survey years beyond the ACS table, because `merge_inc_rank` raises on
the untrimmed data first. Finally, the only way to set the cutoff is to edit
`src/main.py`; the runtime comment recommends pinning a terminal date while the
actual value is `None`.

### Task

1. Normalize any accepted cutoff input to `pd.Timestamp` (or a compatible NumPy
   scalar) before comparison.
2. Apply the cutoff to both processed frames before merging ACS ranks.
3. Add a documented `--final-date YYYY-MM-DD` CLI option to `EnvConfig`.
4. Decide whether the default should remain unbounded or be explicitly pinned;
   make code, comments, and README agree.
5. Keep exclusion counts in the log.

### Acceptance criteria

- `datetime.date`, `pd.Timestamp`, and the CLI ISO date all work consistently.
- Rows after the cutoff never reach `merge_inc_rank`.
- Full and extract retain identical index sets after filtering.
- An invalid CLI date fails with a concise argparse error.
- A small in-memory frame verifies inclusive end-date behavior without running
  `src/main.py`.

---

## [ ] SCE-007 — Implement a defined policy for SCE years newer than the ACS rank table

**Priority:** P1  
**Files:** `src/SCE/importer.py` (`merge_inc_rank`, lines 653–659)

### Problem

The function says it will forward-fill missing income-rank years, but instead
raises `NotImplementedError`. The committed ACS table ends in 2024. The current
SCE file reaches May 2025 and still maps to 2024 under the half-year rule, but
interviews from July 2025 onward will make the normal import fail.

### Task

1. Define the policy explicitly. The existing comments imply carrying the most
   recent available ACS mapping forward separately for each income bin.
2. Materialize the required `(year, ibin)` grid and fill ranks within `ibin`,
   without carrying values across bins.
3. Permit forward extrapolation after the last ACS year; reject or explicitly
   handle survey years before the first ACS year rather than silently
   back-filling them.
4. Log every source-to-target year substitution.
5. Validate post-merge coverage for every non-missing income-bin response.

### Acceptance criteria

- A survey year after the final ACS year receives that final year's rank for the
  same bin under the selected policy.
- Internal missing years fill from the preceding available year.
- No value is copied between income bins.
- Pre-ACS survey years fail with an informative error unless a separately
  documented policy is selected.
- A complete 11-bin mapping remains `m:1` mergeable.

---

## [ ] SCE-008 — Import five-year density summaries and apply percent rounding consistently

**Priority:** P1  
**Files:** `src/SCE/importer.py` (inflation block around lines 129–201),
`src/SCE/annotations.py`

### Problem

The current workbook has no `Q9new2_bin1`–`Q9new2_bin10` fields. It instead has
seven five-year summary fields:

- `Q9new2_cent25`, `Q9new2_cent50`, `Q9new2_cent75`
- `Q9new2_iqr`, `Q9new2_mean`, `Q9new2_probdeflation`, `Q9new2_var`

Each has 41,264 non-missing observations, but the importer looks only for the
nonexistent bin fields and silently drops all summaries. The extract therefore
has no five-year density moments.

The `decimals_percent` regexes also require a trailing underscore, so they round
`infl_1y_bin_*`/`infl_3y_bin_*` but exclude the point forecasts `infl_1y` and
`infl_3y`; five-year values are not rounded at all. With
`decimals_percent=2`, the existing output still contains 3,410 one-year, 2,733
three-year, and 263 five-year point forecasts with more than two decimal places.

### Task

1. Add five-year density summary fields to the full and extract outputs using
   naming parallel to the one- and three-year fields.
2. Scale `Q9new2_probdeflation` from `[0, 1]` to `[0, 100]` consistently.
3. Centralize horizon processing/rounding so 1y, 3y, and 5y point forecasts and
   density statistics follow one rule.
4. Preserve 25th/75th percentiles in full output if “full” is intended to retain
   source summaries; at minimum expose mean, variance, median, IQR, and
   deflation probability in the extract.
5. Add labels for every new extract field.

### Acceptance criteria

- All seven available `Q9new2_*` source summaries are intentionally retained or
  transformed; none is silently ignored.
- Five-year extract names parallel the 1y/3y naming scheme.
- `decimals_percent=N` rounds every documented percent-valued point/statistic to
  `N` places at all horizons.
- `decimals_percent=None` leaves source precision unchanged.

---

## [ ] SCE-009 — Make sign normalization row-safe and use normalized values in every extract

**Priority:** P1  
**Files:** `src/SCE/importer.py` (`flip_negative`, lines 21–63; sign-processing
blocks, especially line 348)

### Problem

`flip_negative` infers one convention for an entire Series. If it sees a mixture
of already-signed and unsigned values, it logs “ambiguous” and leaves known
wrong-sign rows unchanged. It also receives only a Boolean mask, so a missing
direction response is indistinguishable from an explicit non-decrease response.
This causes the current `Q1apart2` warning: 1,445 negative values with missing
`Q1a` are counted as wrong “positive-direction” values even though the signed
forecast itself is usable.

There is also a direct consistency bug in the house-price extract:

```python
df_extract["house_price_change"] = df[varname]
```

It bypasses the normalized `df_full[varname]`. Current source values happen to
already be signed, but any dataset that actually needs the advertised correction
would produce inconsistent full and extract outputs.

### Task

1. Redesign sign normalization to operate row by row on explicitly observed
   direction codes. Preserve signed values when the direction code is missing.
2. Correct positive magnitudes for explicit decrease/deflation responses without
   changing already-negative values.
3. Validate explicit increase responses separately; do not include missing
   direction rows in that validation.
4. Make all extracts, including `house_price_change`, read from the normalized
   full Series.
5. Log counts by action (flipped, already correct, missing direction, genuinely
   contradictory) rather than making an all-or-nothing decision.

### Acceptance criteria

- Mixed signed/unsigned decrease rows are normalized independently.
- Missing direction plus a negative signed value is preserved and does not
  generate a false contradiction warning.
- Every full/extract pair is equal after normalization.
- Focused fixtures cover increase, decrease, zero, missing value, missing
  direction, and mixed-convention input.

---

## [ ] SCE-010 — Store tiled race indicators in the full output

**Priority:** P1  
**Files:** `src/SCE/importer.py` (lines 465–469)

### Problem

The importer correctly computes tiled race responses:

```python
races = tile_const(d, VARNAME_ID, np.uint8)
```

but concatenates the original sparse `d` into `df_full` instead of `races`.
Consequently, `black` in the extract is tiled while `Q35_1`–`Q35_6` in the full
output are observed only on the initial interview. In the current full output,
`Q35_2` is non-missing on only 23,885 of 180,268 rows, whereas the tiled result
would be missing on only the six waves belonging to the respondent with no race
response.

### Task

1. Concatenate `races`, not `d`, into `df_full`.
2. Anchor the source-column regex to the intended `Q35_<number>` fields.
3. Keep full and extract race values sourced from the same tiled object.
4. Preserve missingness for respondents with no observed initial race response.

### Acceptance criteria

- Within a respondent, all `Q35_*` values equal the single observed initial
  response on every wave.
- Respondents with no observed race response remain missing.
- `df_full["Q35_2"]` and `df_extract["black"]` agree row for row.

---

## [ ] SCE-011 — Make Pickle cache/output compression real rather than nominal

**Priority:** P1  
**Files:** `src/main.py` (cache and output paths around lines 134–143 and
180–185), `src/main_plot_diag.py`, `README.md`, optionally `pyproject.toml`

### Problem

Pandas compression inference recognizes `.zst`, not `.zstd`. The code writes
`.pkl.zstd` without an explicit `compression=` argument, so the files are plain,
uncompressed Pickles. Their first bytes are the Pickle magic
`80 05 ...`, not a Zstandard frame.

Current examples:

- `sce_full.pkl.zstd`: 224.8 MB, uncompressed.
- older `sce_full.pkl.xz`: 10.0 MB.
- `sce_extract.pkl.zstd`: 99.7 MB, uncompressed.
- older `sce_extract.pkl.xz`: 5.3 MB.

The README's “zstd-compressed” claim is therefore false, and the content-addressed
cache consumes far more space than intended.

### Task

1. Choose one supported format:
   - use a recognized `.pkl.zst` suffix plus an explicit Zstandard compression
     setting and declared dependency, or
   - restore `.pkl.xz` and the built-in xz path.
2. Pass `compression=` explicitly on both reads and writes instead of relying on
   suffix inference.
3. Update the diagnostic reader and README to the same path/format.
4. Define migration behavior so existing uncompressed `.pkl.zstd` files are not
   accidentally opened as compressed streams. A new suffix is the simplest
   cache invalidation.
5. Verify cache and final-output round trips on a tiny DataFrame.

### Acceptance criteria

- File magic confirms the chosen compression format.
- Cache and output paths use one consistent extension.
- A round trip preserves index, dtypes, values, and dates.
- Existing mislabeled files cannot be mistaken for files in the new format.
- Compression support is represented in `pyproject.toml`/`uv.lock` if an
  optional codec is required.

---

## [ ] SCE-012 — Define stable nullable dtypes instead of all-or-nothing NumPy casts

**Priority:** P2  
**Files:** `src/SCE/pandas_helpers.py` (`try_cast`),
`src/SCE/importer.py`, export code in `src/main.py`

### Problem

`try_cast` attempts a NumPy integer cast and, if any value is missing, leaves the
entire Series as `float64`. The current log reports failed casts for age, gender,
Hispanic status, race, education, health, financial decision-making, and risk
questions. The current full output has 143 `float64` columns out of 157,
including nearly all categorical variables.

This makes output schema depend on whether a particular source release happens
to contain any missing values. It also turns binary/categorical variables into
unconstrained floats and produces noisy warnings for expected missingness.

### Task

1. Define an explicit dtype contract for identifiers, counts, categoricals,
   binary indicators, percentages, and dates.
2. Use pandas nullable integer/boolean dtypes where missingness is valid rather
   than attempting NumPy integer casts.
3. Make `try_cast` either perform the nullable conversion requested or remove it
   in favor of explicit per-field conversion.
4. Verify how nullable dtypes are represented in Pickle, Stata, Excel, and CSV;
   perform export-only conversions at the boundary if required.
5. Avoid mutating caller-owned DataFrames in a casting helper.

### Acceptance criteria

- Output dtypes do not change merely because one observation is missing.
- Expected missing values do not generate failed-cast warnings.
- Binary/category fields cannot silently acquire fractional values.
- All supported export formats preserve values and missingness on a small
  representative frame.

---

## [ ] SCE-013 — Verify categorical mappings and clean impossible response-domain values

**Priority:** P2  
**Files:** `src/SCE/importer.py`, `src/SCE/enums.py`,
`src/SCE/annotations.py`

### Problem

At least one production mapping is explicitly an assumption:

```python
# The questionnaire does not specify the coding, assume ...
```

Other mappings are embedded as anonymous dictionaries and are not tied to a
specific codebook version. There are also unresolved domain inconsistencies:

- `EducationEnum` defines `OTHER = 9`, `educ` maps code 9 to missing, but
  `college` maps it to zero. The latest file contains 62 code-9 responses.
- The latest raw file includes clearly implausible initial ages such as 0, 3, 4,
  and 511; they are propagated to every wave for those users.
- README says categorical enums are applied, but the enums are not imported by
  the processing code.

### Task

1. Obtain the official SCE questionnaire/codebook for the covered releases and
   cite it in code or project documentation.
2. Verify every recode used for `self_employed`, gender, Hispanic status,
   education, ownership, couple status, employment, and numerical-literacy
   correctness.
3. Replace anonymous mappings with named constants/enums or a versioned mapping
   table used by the transformation.
4. Define documented treatment for “Other/unknown/refused” category codes.
5. Define valid age bounds from the survey design; set out-of-domain responses
   to missing and log counts rather than propagating impossible values.

### Acceptance criteria

- No production recode is documented as an unverified assumption.
- Code 9 education has consistent `educ` and `college` semantics.
- Every mapping has explicit behavior for missing/other values.
- Out-of-domain age handling is documented and counted.
- Mapping fixtures cover every allowed source code.

---

## [ ] SCE-014 — Repair and actually use variable/value metadata

**Priority:** P2  
**Files:** `src/SCE/annotations.py`, `src/SCE/enums.py`, `src/main.py`,
`README.md`

### Problem

The annotation and enum modules are currently unused. Stata exports receive no
`variable_labels` or `value_labels`, despite README claims that the importer maps
labels and applies enums.

The metadata has already drifted from the extract schema. Current output fields
without labels include `hh_inc_change`, `credit_cond_past_12m`, `hh_inc_bin`,
`hh_inc_bin_rank`, all 1y/3y density summaries, and identifiers/date. Labels exist
for nonexistent `hh_income_change`, `credit_cond_past12m`, and `hh_income`.
The `hh_changed` label says “HH unchaged from last survey,” which is misspelled
and has the opposite meaning from the derived field.

### Task

1. Make label keys exactly match the declared full/extract schemas.
2. Add labels for identifiers, dates, income ranks, density summaries, and all
   fields introduced by other tasks.
3. Correct spelling and semantic direction, especially `hh_changed`.
4. Pass supported variable/value labels to `DataFrame.to_stata` and define where
   metadata lives for Pickle (for example `DataFrame.attrs`).
5. Either apply enum-derived value labels or remove the inaccurate README claim.
6. Add a metadata coverage check against each output schema.

### Acceptance criteria

- Every extract field has exactly one variable label.
- No label key refers to a nonexistent output field.
- Stata output exposes the intended variable/value labels on a small fixture.
- Labels agree with coding direction and units (`[0, 1]` versus `[0, 100]`).

---

## [ ] SCE-015 — Declare and audit the “full” and extract output schemas

**Priority:** P2  
**Files:** `src/SCE/importer.py`, a new schema module or data file,
`README.md`

### Problem

The importer builds both frames imperatively, with a mixture of hard-coded
columns and permissive regex/filter calls. There is no declared output schema or
list of intentionally omitted raw fields. The current raw file has 229 columns
while `df_full` has 157, so “full” does not mean all source variables. Upstream
additions can be silently discarded—the missing five-year summaries are a
current example—and broad regexes can silently capture unintended future fields.

### Task

1. Decide and document what “full” means: all raw fields plus normalized fields,
   or a curated comprehensive schema.
2. Declare ordered expected schemas for raw inputs, full output, and extract
   output, including units/dtypes and optional release-specific fields.
3. Anchor regexes such as `Q10_.*`, `Q35.*`, and `Q45new_.*` to the precise field
   patterns they intend to select.
4. At import time, report upstream columns that are new, missing, or
   intentionally ignored. Required columns should fail clearly; optional
   release-specific fields should be explicit.
5. Add a lightweight schema-audit command that reads workbook headers only and
   does not run the full importer.

### Acceptance criteria

- Every source column is classified as retained, transformed, or intentionally
  omitted.
- Every output column has a declared order, dtype, unit, and optionality.
- A newly added upstream header cannot disappear silently.
- The three current workbook headers pass the audit with only documented
  release differences.

---

## [ ] SCE-016 — Fix incorrect diagnostic histogram bins and outlier thresholds

**Priority:** P2  
**Files:** `src/main_plot_diag.py` (around lines 82–113 and 337–355),
`stata/main_ftotinc_IPUMS.do` (diagnostic graph block around lines 159–191)

### Problem

Python diagnostics contain two calculation errors:

1. `bins = np.arange(nmax + 1)` uses integer observations as bin edges. The final
   bin combines the `nmax - 1` and `nmax` discrete counts, while tick labels imply
   separate categories. Integer-count histograms need half-integer edges.
2. In outlier filtering, the 25th and 75th percentiles are assigned backwards:

   ```python
   p25 = df_qntl.xs(0.75, ...)
   p75 = df_qntl.xs(0.25, ...)
   ```

   The IQR happens to remain positive because the names are then subtracted in
   reverse, but upper/lower cutoffs use the wrong quartile and differ by one IQR
   at each bound from the documented rule.

The Stata diagnostic block also references the misspelled macro `byblb` instead
of `bylbl`, and exports both college-loop graphs to the same filename, so the
second overwrites the first.

### Task

1. Use histogram edges `np.arange(-0.5, nmax + 1.5)` (or equivalent) and align
   ticks/limits with integer counts.
2. Assign `q1`/`q3` correctly and implement the documented
   `q1 - 100*IQR`/`q3 + 100*IQR` cutoffs.
3. Fix the Stata legend macro and include college status in graph filenames, or
   produce one combined graph.
4. Add tiny deterministic diagnostic fixtures. Do not run Stata without
   approval.

### Acceptance criteria

- Every integer count from 0 through `nmax` has its own histogram bin.
- Outlier bounds use the correctly named quartiles.
- Stata diagnostic outputs cannot overwrite each other.
- Diagnostic fixes do not alter processed survey data.

---

## [ ] SCE-017 — Make expensive export formats selectable

**Priority:** P2  
**Files:** `src/main.py`, `src/env.py`, `README.md`

### Problem

Every import unconditionally writes two Pickles, two Stata files, Excel, and CSV.
The existing run log shows the Excel export alone taking about three minutes,
while all processing and rank merging completed in roughly two seconds. There is
no way to request only the format needed for a given workflow, making routine
iteration unnecessarily slow.

### Task

1. Add a CLI option such as `--formats pickle,stata,excel,csv`, with a documented
   backward-compatible default.
2. Split each exporter into a small function and execute only selected formats.
3. Log skipped and written outputs, including elapsed time and final size.
4. Ensure diagnostics can locate the configured canonical Pickle output.
5. Consider writing expensive outputs atomically so failed exports do not leave
   apparently complete partial files.

### Acceptance criteria

- A Pickle-only run does not invoke Stata/Excel/CSV writers.
- The default behavior is explicitly documented.
- Invalid format names fail during argument parsing.
- Export selection is verified with a tiny DataFrame; validating this task does
  not require running the full SCE import.

---

## [ ] SCE-018 — Emit a reproducibility manifest for every completed import

**Priority:** P2  
**Files:** `src/main.py`, optionally a new provenance module, `README.md`

### Problem

The current FRBNY workbook is silently replaced upstream, output filenames are
stable, and `final_date` defaults to unbounded. Although input MD5 hashes are used
as cache keys, they are not recorded alongside final outputs. A consumer cannot
reconstruct which workbook revisions, ACS mapping, processing parameters, or
code revision produced a given `sce_extract.*` file.

### Task

1. Write a machine-readable manifest (for example `sce_manifest.json`) containing:
   - input filenames, sizes, and strong content hashes;
   - ACS-rank filename/hash and available years;
   - row/date ranges for each input and output;
   - final-date and rounding settings;
   - selected export formats;
   - package/project version and git commit/dirty status when available;
   - output filenames, sizes, and hashes.
2. Write/finalize the manifest only after selected outputs complete, with clear
   status if atomic finalization is not feasible.
3. Include or link the manifest in Pickle `attrs` where practical.
4. Document how to reproduce a pinned run.

### Acceptance criteria

- Two runs with different latest workbooks or processing options have visibly
  different manifests.
- Every final output can be traced to exact raw and ACS inputs.
- Manifest generation can be tested with temporary tiny files and does not
  require running the full importer.

---

## [ ] SCE-019 — Add fast transformation regression tests

**Priority:** P2  
**Files:** new `tests/` files, `pyproject.toml`, and transformation helpers
factored from `src/SCE/importer.py`

### Problem

Ruff and ty both pass, but they cannot detect the data-corruption and recoding
issues above. There are currently no tests for panel propagation, missingness,
sign normalization, date-to-rank-year mapping, rank filling, or output schema.
Many transformations are embedded in one large function, which makes focused
verification difficult and encourages reliance on the very slow end-to-end
script.

### Task

1. Add small synthetic fixtures with the established `(userid, wid)` panel index
   and only the columns needed by the helper under test.
2. Factor pure helpers for household state propagation, nullable binary recodes,
   sign normalization, income reference year, and rank-table expansion.
3. Add regression tests for SCE-001, SCE-003, SCE-005, SCE-007, SCE-009, and
   SCE-010, plus schema/metadata coverage tests.
4. Keep raw FRBNY files and private data out of the test suite.
5. Ensure tests are deterministic and complete in seconds; no test should call
   `src/main.py`, write production outputs, or invoke Stata.

### Acceptance criteria

- The suite reproduces the pre-fix failure modes with synthetic data and passes
  after the corresponding fixes.
- Tests run without the raw SCE workbooks, existing caches, or Stata.
- Test runtime is short enough for routine agent use.
- `uv run ruff check` and `uv run ty check` continue to pass.
