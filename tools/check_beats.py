#!/usr/bin/env python3
"""Check beat positions in music.json."""

import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    path = Path("data/00_input/Testidata nuottisivu/music/music.json")
else:
    path = Path(sys.argv[1])

d = json.load(open(path, encoding="utf-8"))
omr = d.get("omr", {})

print("=== Beat Positions Check ===")
measures = omr.get("measures", [])
if measures:
    for m in measures[:3]:
        print(f"\nMeasure {m['number']}:")
        notes = m.get("notes", [])
        for n in notes[:5]:
            beat = n.get("beat", "MISSING")
            print(f"  {n['pitch']} ({n['duration']}) beat={beat}")
    
    # Count notes with beat
    total_notes = sum(len(m.get("notes", [])) for m in measures)
    notes_with_beat = sum(
        1 for m in measures
        for n in m.get("notes", [])
        if n.get("beat") is not None and n.get("beat") != 0.0
    )
    print(f"\nTotal notes: {total_notes}")
    print(f"Notes with beat: {notes_with_beat} ({notes_with_beat/total_notes*100:.1f}%)")
