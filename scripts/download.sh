#!/bin/bash
# Fetch the public artifacts this gym uses.  Idempotent; safe to rerun.
#
# Estimated total download size: < 5 MB.  Estimated disk usage: < 10 MB.
#
# The train slice uses the twelve benchmark theories published with the paper
# (https://github.com/IBM/AI-Noether, folder systems_and_phenomena).  A copy is
# tracked in data/systems_and_phenomena; this script clones the upstream
# repository into data/downloads/ and restores that copy if it is missing.
# The held-out test theories are authored for this gym and live in eval/test/.
set -e
cd "$(dirname "$0")/.."
mkdir -p data/downloads
if [ ! -d data/downloads/AI-Noether/.git ]; then
  git clone --depth 1 https://github.com/IBM/AI-Noether.git data/downloads/AI-Noether
fi
if [ ! -f data/systems_and_phenomena/kepler/system.txt ]; then
  mkdir -p data/systems_and_phenomena
  cp -r data/downloads/AI-Noether/systems_and_phenomena/. data/systems_and_phenomena/
fi
echo "Benchmark theories available in data/systems_and_phenomena"
