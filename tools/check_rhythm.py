#!/usr/bin/env python3
"""Check rhythm normalization results."""

import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    path = Path("data/00_input/Testidata nuottisivu/music/music.json")
else:
    path = Path(sys.argv[1])

d = json.load(open(path, encoding="utf-8"))
omr = d.get("omr", {})

print("=== Rhythm Normalization ===")
rn = omr.get("rhythm_normalization", {})
if rn:
    print(f"Total measures: {rn.get('total_measures')}")
    print(f"Corrected measures: {rn.get('corrected_measures')}")
    print(f"All valid: {rn.get('all_valid')}")
    print(f"Errors: {len(rn.get('errors', []))}")
    if rn.get("errors"):
        print("\nFirst 5 errors:")
        for err in rn["errors"][:5]:
            print(f"  - {err}")
else:
    print("No rhythm normalization data")

print("\n=== Preflight 2 ===")
pf2 = omr.get("preflight2", {})
if pf2:
    print(f"Time signature: {pf2.get('time_signature')}")
    print(f"Clef: {pf2.get('clef')}")
    print(f"Key signature: {pf2.get('key_signature')}")
else:
    print("No preflight2 data")

print("\n=== QA Status ===")
qa = d.get("qa", {})
print(f"Status: {qa.get('status')}")
for finding in qa.get("findings", []):
    severity = finding.get("severity", "info")
    message = finding.get("message", "")
    print(f"  [{severity}] {message}")
