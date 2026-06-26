#!/usr/bin/env python3
"""Enforce the strict public policy for the optional mmWave side track.

The mmWave side track may contain only papers whose final venue is in the
explicit top-venue allow-list. arXiv-only records are not allowed here.
"""
from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MMWAVE = DATA / "mmwave_papers.json"
LOG = DATA / "last_update.json"

ALLOWED = {
    "CVPR", "ICCV", "NeurIPS", "ECCV", "ICLR", "ICML", "ICCP",
    "MobiSys", "MobiCom", "SenSys", "IEEE TPAMI", "ACM TOG / SIGGRAPH",
    "IEEE TIP", "IEEE TMC", "SIGGRAPH"
}


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


items = load(MMWAVE, [])
kept = []
removed = []
for p in items:
    venue = str(p.get("venue", "")).lower()
    group = p.get("venue_group", "")
    if group in ALLOWED and venue != "arxiv preprint":
        kept.append(p)
    else:
        removed.append({"id": p.get("id"), "title": p.get("title"), "venue": p.get("venue"), "venue_group": group})

dump(MMWAVE, kept)
log = load(LOG, {})
log["mmwave_allowlist"] = sorted(ALLOWED)
log["mmwave_track_total"] = len(kept)
log["mmwave_track_removed_non_allowlist"] = removed
log["mmwave_track_policy"] = "Only final-venue papers from the explicit top-venue allow-list are allowed in data/mmwave_papers.json; arXiv-only records are excluded."
dump(LOG, log)
print(f"mmWave side track: kept {len(kept)}, removed {len(removed)}")
