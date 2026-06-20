#!/bin/bash
# Full CPU reproduction job for the exact symbolic AI-Noether experiments.

set -e

cd /home/user

bash scripts/reproduce.sh
python validate.py --compare
