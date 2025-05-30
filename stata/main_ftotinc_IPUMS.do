/*

Script to map each SCE family income bin to the median rank in the family
income distribution using the ACS data for the same survey years.

*/


//------------------------------------------------------------------------------
// Directories and paths

if "${S_OS}" == "Unix" {
	local home: environment HOME
}
else {
	local home: environment USERPROFILE
}

global RUNDIR = "`home'/run/sce-import"
global OUTDIR = "${RUNDIR}/stata/output"

capture mkdir `"${RUNDIR}"'
capture mkdir `"${RUNDIR}/stata"'
capture mkdir `"${OUTDIR}"'

// Input data file
global DATAFILE = "`home'/data/IPUMS/ACS/ftotinc_2008-2023.dta"

// Family income bin edges used in SCE
global FAM_INC_CUTS = "0 10000 20000 30000 40000 50000 60000 75000 100000 150000 200000 1e20"


//------------------------------------------------------------------------------
// Pooled median income ranks

use "${DATAFILE}", clear

keep if age >= 18
// keep if age <= 80

// Generate person-level family income ranks within each survey year
by year, sort: cumul ftotinc [fw=perwt], generate(rank)

// Discretize into bins which are the same as in the SCE
quietly summarize ftotinc

egen lbound = cut(ftotinc), at(${FAM_INC_CUTS})

// Compute median rank (within the family income distribution of each year)
// for each bin
collapse (median) rank, by(year lbound)

format %5.3f rank

drop if missing(lbound)
sort year lbound

// Create 1-based bin index without the lower bound label
by year (lbound): generate ibin = _n

// Store as CSV
order year ibin lbound rank 

export delimited using `"${OUTDIR}/IPUMS_ftotinc_rank_by_year.csv"', ///
    replace datafmt

    
//------------------------------------------------------------------------------
// Median income ranks by college for initial age range

// Age range for "newborn" sample
local age_min = 23
local age_max = 27

use "${DATAFILE}", clear

// Recode variables
recode educ (0/9 = 0) (10/11 = 1), generate(college)
recode ftotinc (9999998/9999999 = .)

tabulate educ [fw=perwt]

tabulate educ [fw=perwt] if age >= `age_min' & age <= `age_max'

// Fraction with at least bachelor degree
mean college [pw=perwt] if age >= `age_min' & age <= `age_max'

keep if age >= `age_min'
keep if age <= `age_max'

local cellvars "year college"

// Generate person-level family income ranks within each survey year
by `cellvars', sort: cumul ftotinc [fw=perwt], generate(rank)

// Discretize into bins which are the same as in the SCE
quietly summarize ftotinc

egen lbound = cut(ftotinc), at(${FAM_INC_CUTS})

// Compute median rank (within the family income distribution of each year)
// for each bin
collapse (median) rank, by(`cellvars' lbound)

format %5.3f rank

drop if missing(lbound)
sort `cellvars' lbound

// Create 1-based bin index without the lower bound label
by `cellvars' (lbound), sort: generate ibin = _n

// Store as CSV
order `cellvars' ibin lbound rank 

export delimited using ///
    `"${OUTDIR}/IPUMS_ftotinc_rank_by_year_college_age`age_min'-`age_max'.csv"', ///
    replace datafmt


