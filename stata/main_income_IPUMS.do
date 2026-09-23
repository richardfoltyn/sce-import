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

global DIAGNOSTICS = 1

global RUNDIR = "`home'/run/sce-import"
global OUTDIR = "${RUNDIR}/stata/output"
global LOGDIR = "${RUNDIR}/stata/logs"
global GRAPHDIR = "${RUNDIR}/stata/graphs"

capture mkdir `"${RUNDIR}"'
capture mkdir `"${RUNDIR}/stata"'
capture mkdir `"${OUTDIR}"'
capture mkdir `"${LOGDIR}"'
capture mkdir `"${GRAPHDIR}"'

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

use year hhincome age perwt educ using "${DATAFILE}", clear

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


//------------------------------------------------------------------------------
// Median income ranks by college for initial age range

// Set whether household-income rank should be computed by age or pooled
local by_age = 0

// Age range for "newborn" sample
local age_min = 18
local age_max = 27

use year hhincome age perwt educ using "${DATAFILE}", clear

label variable year "Year"
label variable age "Age"

// Recode variables
recode educ (0/9 = 0) (10/11 = 1), generate(college)
label variable college "College"

replace hhincome = . if hhincome == 9999999

tabulate educ [fw=perwt]

tabulate educ [fw=perwt] if age >= `age_min' & age <= `age_max'

// Fraction with at least bachelor degree
mean college [pw=perwt] if age >= `age_min' & age <= `age_max'

keep if age >= `age_min'
keep if age <= `age_max'

local cellvars "year college"
if `by_age' {
    local cellvars = "`cellvars' age"
}

drop if missing(hhincome)

// Generate person-level household-income ranks within each cell.
by `cellvars', sort: cumul hhincome [fw=perwt], generate(rank) equal

summarize hhincome, detail
summarize hhincome [fw=perwt], detail

// Force negative income into the first SCE bin without changing its CDF rank.
replace hhincome = max(0, hhincome)
assert hhincome != 9999999

// Discretize using the SCE bins and retain their fixed 1-based codes.
egen lbound = cut(hhincome), at(${INCOME_CUTS})
egen ibin = cut(hhincome), at(${INCOME_CUTS}) icodes
replace ibin = ibin + 1 if !missing(ibin)

// Generate nobs variable to count unweighted observations with rawsum under fweights
generate byte nobs = 1

// Compute summary statistics for each income bin within each cell.
// (rawsum) nobs is required because (count) with fweights sums the weights
collapse (min) rank_min=rank (median) rank (rawsum) nobs (rawsum) mass=perwt ///
    [fw=perwt], by(`cellvars' ibin lbound)

drop if missing(ibin, lbound)
assert inrange(ibin, 1, 11)

// Normalize mass within each cell so exact bins sum to 1.0
by `cellvars': egen mass_total = total(mass)
replace mass = mass / mass_total

label variable ibin "Household-income bin"
label variable mass "Frac of obs within `cellvars'"
label variable rank "Median rank within income bin"
label variable rank_min "Lowest rank within income bin"
label variable lbound "Bin lower bound (nominal USD)"
label variable nobs "N. obs within bin"

// --- Plot median rank by bin and year ---

if ${DIAGNOSTICS} {
    local byvar year
    local bylbl: variable label `byvar'

    forvalues college = 0/1 {

        quietly levelsof `byvar' if college == `college', local(byvalues)

        local graph_str = ""
        local legend_str = ""
        local i = 1
        foreach value of local byvalues {
            local graph_str `"`graph_str' (scatter rank ibin if `byvar' == `value' & college == `college', connect(l) msymbol(o) msize(medium))"'
            local legend_str `"`legend_str' label(`i' "`bylbl' `value'") "'
            local ++i
        }

        quietly summarize ibin
        local imax = r(max)

        #delimit ;
        twoway
            `graph_str',
            ytitle("Rank")
            xtitle("Household-income bin")
            title("Household-income rank (ages `age_min'-`age_max')")
            xlabel(1(1)`imax')
            legend(`legend_str' position(6) rows(2))
            ;
        #delimit cr

        graph export "${GRAPHDIR}/income_rank_by_year_college`college'_ages`age_min'-`age_max'.pdf", replace
    }
}


// --- Store CSV ---

// Drop year/age/college cells with less than 1000 individuals since this is
// more noise than data.
by `cellvars', sort: egen nobs_cell = total(nobs)

keep if nobs_cell >= 1000
drop nobs_cell

sort `cellvars' ibin
isid `cellvars' ibin

format %5.3f rank rank_min mass

local varlist `cellvars' ibin lbound rank rank_min nobs mass
keep `varlist'
order `varlist'

describe

local suffix = cond(`by_age' == 1, "_age", "")

export delimited using ///
    `"${OUTDIR}/IPUMS_income_rank_by_year_college`suffix'_ages`age_min'-`age_max'_sce_bins.csv"', ///
    replace datafmt

log close `logname'
