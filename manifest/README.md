# Data Manifests

This folder contains the MD5 checksums for the input data files used in this project, ensuring version control and reproducibility.

## Manifest Files

- `FRBNY-SCE.md5`: MD5 checksums for the Federal Reserve Bank of New York (FRBNY) SCE Excel microdata files (`FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx`, `FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx`, `frbny-sce-public-microdata-20-24.xlsx`, `frbny-sce-public-microdata-latest.xlsx`).
- `ACS.md5`: MD5 checksum for the IPUMS ACS input data file (`ftotinc_2008-2024.dta`).

## Data Verification

A verification script is included to check that the input data files on the current machine match the expected MD5 checksums.

To run the verification:
```bash
./manifest/verify_data.sh
```

You can customize the directories to verify by passing options:
```bash
./manifest/verify_data.sh --sce-dir /path/to/sce/data --acs-dir /path/to/acs/data
```

## Recreating MD5 Sum Files

To recreate or update the MD5 checksum files from updated raw input data, run the `md5sum` command from within the respective data directory so that relative file paths match the manifest format:

```bash
# Recreate FRBNY SCE manifest
(cd ~/data/SCE && md5sum FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx frbny-sce-public-microdata-20-24.xlsx frbny-sce-public-microdata-latest.xlsx) > manifest/FRBNY-SCE.md5

# Recreate ACS manifest
(cd ~/data/IPUMS/ACS && md5sum ftotinc_2008-2024.dta) > manifest/ACS.md5
```
