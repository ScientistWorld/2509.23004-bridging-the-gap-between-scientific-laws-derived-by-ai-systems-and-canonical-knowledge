#!/bin/bash
set -euo pipefail
cd /home/user
bash redteam/honest_broader/run.sh
bash redteam/honest_broader_weaker/run.sh
python redteam/summarize.py
