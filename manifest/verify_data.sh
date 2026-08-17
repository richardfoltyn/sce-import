#!/usr/bin/env bash

set -euo pipefail

# Default directories (can be overridden by environment variables or CLI options)
SCE_DIR="${SCE_DIR:-$HOME/data/SCE}"
ACS_DIR="${ACS_DIR:-$HOME/data/IPUMS/ACS}"
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    cat << EOF
Usage: $(basename "$0") [options]

Verify the MD5 checksums of the input data files.

Options:
  --sce-dir PATH      Path to the directory containing SCE data files.
                      Default: $SCE_DIR
  --acs-dir PATH      Path to the directory containing ACS data files.
                      Default: $ACS_DIR
  -h, --help          Show this help message.
EOF
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sce-dir)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --sce-dir requires a path argument." >&2
                exit 1
            fi
            SCE_DIR="$2"
            shift 2
            ;;
        --acs-dir)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --acs-dir requires a path argument." >&2
                exit 1
            fi
            ACS_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Error: Unknown option $1" >&2
            show_help >&2
            exit 1
            ;;
    esac
done

# Resolve to absolute paths
SCE_DIR="$(realpath "$SCE_DIR" 2>/dev/null || echo "$SCE_DIR")"
ACS_DIR="$(realpath "$ACS_DIR" 2>/dev/null || echo "$ACS_DIR")"

echo "=== Verifying SCE Data Files ==="
echo "SCE data directory: $SCE_DIR"
SCE_MANIFEST="$MANIFEST_DIR/FRBNY-SCE.md5"

if [[ ! -f "$SCE_MANIFEST" ]]; then
    echo "Error: SCE manifest not found at $SCE_MANIFEST" >&2
    exit 1
fi

if [[ ! -d "$SCE_DIR" ]]; then
    echo "Error: SCE data directory does not exist at $SCE_DIR" >&2
    exit 1
fi

# Verify SCE files
(
    cd "$SCE_DIR"
    md5sum -c "$SCE_MANIFEST"
)

echo ""
echo "=== Verifying ACS Data Files ==="
echo "ACS data directory: $ACS_DIR"
ACS_MANIFEST="$MANIFEST_DIR/ACS.md5"

if [[ ! -f "$ACS_MANIFEST" ]]; then
    echo "Error: ACS manifest not found at $ACS_MANIFEST" >&2
    exit 1
fi

if [[ ! -d "$ACS_DIR" ]]; then
    echo "Error: ACS data directory does not exist at $ACS_DIR" >&2
    exit 1
fi

# Verify ACS files
(
    cd "$ACS_DIR"
    md5sum -c "$ACS_MANIFEST"
)

echo ""
echo "All files verified successfully!"
