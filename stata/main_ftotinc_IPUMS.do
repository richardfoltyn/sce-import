/*

Script to map each SCE family income bin to the median rank in the family
income distribution using the ACS data for the same survey years.

*/


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

local LOGNAME = "ftotinc_IPUMS"
capture log close `LOGNAME'
log using "${LOGDIR}/`LOGNAME'.log", text replace name(`LOGNAME')


// Input data file
global DATAFILE = "`home'/data/IPUMS/ACS/ftotinc_2008-2024.dta"

// Family income bin edges used in SCE
global FAM_INC_CUTS = "0 10000 20000 30000 40000 50000 60000 75000 100000 150000 200000 1e20"


//------------------------------------------------------------------------------
// Pooled median income ranks

use "${DATAFILE}", clear

keep if age >= 18
// keep if age <= 80

// IPUMS codes 9,999,998 and 9,999,999 as missing total family income.
// Report the unweighted records excluded from the rank calculation by year.
generate byte ftotinc_sentinel = inrange(ftotinc, 9999998, 9999999)
display "Excluded FTOTINC sentinel records by year:"
tabulate year if ftotinc_sentinel

recode ftotinc (9999998/9999999 = .)
drop if missing(ftotinc)
drop ftotinc_sentinel

// Generate person-level family income ranks within each survey year using the
// ACS person weights.
by year, sort: cumul ftotinc [fw=perwt], generate(rank)

summarize ftotinc, detail
summarize ftotinc [fw=perwt], detail

// Force zero lower bound to fit into bins
replace ftotinc = max(0, ftotinc)

// Verify that no IPUMS missing-value sentinel reaches the SCE binning step.
assert !inrange(ftotinc, 9999998, 9999999)

// Discretize into bins which are the same as in the SCE
egen lbound = cut(ftotinc), at(${FAM_INC_CUTS})

// Compute the person-weighted median rank within each year and SCE income bin.
collapse (median) rank [fw=perwt], by(year lbound)

format %5.3f rank

drop if missing(lbound)
sort year lbound

// Create 1-based bin index without the lower bound label
by year (lbound): generate ibin = _n

// Store as CSV
order year ibin lbound rank 

describe

export delimited using `"${OUTDIR}/IPUMS_ftotinc_rank_by_year_sce_bins.csv"', ///
    replace datafmt

    
//------------------------------------------------------------------------------
// Median income ranks by college for initial age range

// Set whether family income rank should be computed by age or pooled
local by_age = 0

// Age range for "newborn" sample
local age_min = 18
local age_max = 27

use "${DATAFILE}", clear

label variable year "Year"
label variable age "Age"

// Recode variables
recode educ (0/9 = 0) (10/11 = 1), generate(college)
label variable college "College"

recode ftotinc (9999998/9999999 = .)

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

drop if missing(ftotinc)

// Generate person-level family income ranks within each survey year
by `cellvars', sort: cumul ftotinc [fw=perwt], generate(rank)

summarize ftotinc, detail
summarize ftotinc [fw=perwt], detail

// Force zero lower bound to fit into bins
replace ftotinc = max(0, ftotinc)

// Discretize into bins which are the same as in the SCE
egen lbound = cut(ftotinc), at(${FAM_INC_CUTS})

// Compute median rank (within the family income distribution of each year)
// for each bin.
// Generate nobs variable to be used with rawsum to get actual number of obs.
// even when fweights are used.
generate nobs = 1
collapse (min) rank_min=rank (median) rank (rawsum) nobs (rawsum) mass=perwt ///
    [fw=perwt], by(`cellvars' lbound)

by `cellvars': egen mass_total = total(mass)
replace mass = mass / mass_total
drop mass_total

// Create 1-based bin index without the lower bound label
by `cellvars' (lbound), sort: generate ibin = _n

label variable ibin "Family income bin"
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
            local legend_str `"`legend_str' label(`i' "`byblb' `value'") "'
            local ++i
        }

        quietly summarize ibin
        local imax = r(max)

        #delimit ;
        twoway 
            `graph_str',
            ytitle("Rank")
            xtitle("Family income bin")
            title("Family income rank (ages `age_min'-`age_max')")
            xlabel(1(1)`imax')
            legend(`legend_str' position(6) rows(2))
            ;
        #delimit cr

        graph export "${GRAPHDIR}/fam_inc_rank_by_year_college_ages`age_min'-`age_max'.pdf", replace
    }
}


// --- Store CSV ---

// Drop year/age/college cells with less than 1000 individuals since this is
// more noise than data.
by `cellvars', sort: egen nobs_cell = total(nobs)

keep if nobs_cell >= 1000
drop nobs_cell

format %5.3f rank rank_min mass

drop if missing(lbound)
sort `cellvars' lbound

// Store as CSV
order `cellvars' ibin lbound rank rank_min, first 

describe

local suffix = cond(`by_age' == 1, "_age", "")

export delimited using ///
    `"${OUTDIR}/IPUMS_ftotinc_rank_by_year_college`suffix'_ages`age_min'-`age_max'_sce_bins.csv"', ///
    replace datafmt

log close `LOGNAME'
