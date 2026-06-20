#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: 0 GB
# Estimated disk usage after extraction: 0 GB
#
# No external dataset or model download is required for the symbolic benchmark
# instances packaged in this workspace.

set -e

cd "$(dirname "$0")/.."

mkdir -p data/downloads
echo "Packaged symbolic benchmarks require no external datasets."
