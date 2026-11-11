#!/usr/bin/env python3
"""No-abduction baseline: keep the incomplete theory and propose nothing.

Usage: no_abduction.py <instance.json> <output.json>
"""
import json
import sys
from pathlib import Path

instance = json.loads(Path(sys.argv[1]).read_text())
payload = {"method": "no_abduction_baseline", "candidate_sets": [], "instance": instance.get("id")}
Path(sys.argv[2]).write_text(json.dumps(payload))
