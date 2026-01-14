#!/usr/bin/env python3
"""Show OMR result summary from music.json."""

import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    path = Path("data/00_input/Testidata nuottisivu/music/music.json")
else:
    path = Path(sys.argv[1])

d = json.load(open(path, encoding="utf-8"))
omr = d.get("omr", {})

print("=== OMR Summary ===")
print(f"Success: {omr.get('success')}")
print(f"Engine: {omr.get('engine')}")
print(f"Measures: {omr.get('measure_count')}")
print(f"Notes: {omr.get('note_count')}")
print(f"Time Sig: {d.get('metadata', {}).get('time_signature')}")
print(f"Key Sig: {d.get('metadata', {}).get('key_signature')}")
print()

pf = omr.get("preflight", {})
if pf:
    print("=== Preflight ===")
    print(f"Interline: {pf.get('detected_interline_px')}px")
    print(f"Scale: {pf.get('scale_factor')}x")
    print(f"Upscaled: {pf.get('upscaled_size')}")
    print()

measures = omr.get("measures", [])
if measures:
    print(f"=== First 3 of {len(measures)} measures ===")
    for m in measures[:3]:
        notes = m.get("notes", [])
        print(f"  Measure {m['number']}: {len(notes)} notes")
        for n in notes[:4]:
            print(f"    {n['pitch']} ({n['duration']})")
        if len(notes) > 4:
            print(f"    ... and {len(notes)-4} more")
