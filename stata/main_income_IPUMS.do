/*
    Map each SCE household-income bin to the median rank in the person-weighted
    household-income distribution using ACS data.

    Notes:
    - HHINCOME includes income from all household members age 15 or older,
      including people unrelated to the household head; FTOTINC does not.
    - The reference population consists of person records age 18 or older.
*/

set more off
set varabbrev off


//------------------------------------------------------------------------------
// Configuration

if "${S_OS}" == "Unix" {
    local home: environment HOME
}
else {
    local home: environment USERPROFILE
}

global RUNDIR = "`home'/run/sce-import"
global OUTDIR = "${RUNDIR}/stata/output"
global LOGDIR = "${RUNDIR}/stata/logs"

capture mkdir `"${RUNDIR}"'
capture mkdir `"${RUNDIR}/stata"'
capture mkdir `"${OUTDIR}"'
capture mkdir `"${LOGDIR}"'

local logname = "income_IPUMS"
capture log close `logname'
log using "${LOGDIR}/`logname'.log", text replace name(`logname')


// Input data file
// The generic file name is scoped by its ACS/income directory.
global DATAFILE = "`home'/data/IPUMS/ACS/income/data.dta"

// Household-income bin edges used in SCE
global INCOME_CUTS = "0 10000 20000 30000 40000 50000 60000 75000 100000 150000 200000 1e20"


//------------------------------------------------------------------------------
// Pooled median income ranks

use year hhincome age perwt using "${DATAFILE}", clear

keep if age >= 18

// IPUMS uses 9,999,999 as N/A for total household income.
// Report the unweighted records excluded from the rank calculation by year.
generate byte hhincome_sentinel = hhincome == 9999999
display "Excluded HHINCOME sentinel records by year:"
tabulate year if hhincome_sentinel

replace hhincome = . if hhincome_sentinel
drop if missing(hhincome)
drop hhincome_sentinel

// Generate person-level household-income ranks within each survey year using
// the ACS person weights.
by year, sort: cumul hhincome [fw=perwt], generate(rank) equal

summarize hhincome, detail
summarize hhincome [fw=perwt], detail

// Force negative income into the first SCE bin without changing its CDF rank.
replace hhincome = max(0, hhincome)

// Verify that no IPUMS missing-value sentinel reaches the SCE binning step.
assert hhincome != 9999999

// Discretize using the SCE bins. Derive the bin code from the cut points so a
// missing observed bin cannot shift the codes assigned to higher-income bins.
egen lbound = cut(hhincome), at(${INCOME_CUTS})
egen ibin = cut(hhincome), at(${INCOME_CUTS}) icodes
replace ibin = ibin + 1 if !missing(ibin)

// Compute the person-weighted median rank within each year and SCE income bin.
collapse (median) rank [fw=perwt], by(year ibin lbound)

drop if missing(ibin, lbound)
format %5.3f rank

sort year ibin
isid year ibin
assert inrange(ibin, 1, 11)
by year: assert _N == 11

order year ibin lbound rank

describe

export delimited using `"${OUTDIR}/IPUMS_income_rank_by_year_sce_bins.csv"', ///
    replace datafmt

log close `logname'
