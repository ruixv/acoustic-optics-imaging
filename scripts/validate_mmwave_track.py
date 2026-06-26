#!/usr/bin/env python3
"""Enforce the public policy for the optional mmWave side track.

The mmWave side track is hidden/collapsed by default. It is allowed to contain:
1. final-venue papers from the explicit top-venue allow-list;
2. high-relevance mmWave arXiv/preprint records when no final venue is verified yet;
3. explicit manual tracking seeds requested by the maintainer, clearly marked as metadata-pending.
"""
from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MMWAVE = DATA / "mmwave_papers.json"
LOG = DATA / "last_update.json"

ALLOWED_FINAL_GROUPS = {
    "Nature", "Nature Portfolio", "Nature Communications", "Nature Electronics",
    "Nature Photonics", "Nature Machine Intelligence", "Nature Computational Science",
    "CVPR", "ICCV", "NeurIPS", "ECCV", "ICLR", "ICML", "ICCP",
    "MobiSys", "MobiCom", "SenSys", "IEEE TPAMI", "ACM TOG / SIGGRAPH",
    "IEEE TIP", "IEEE TMC", "SIGGRAPH"
}

MMWAVE_SCOPE_TERMS = [
    "mmwave", "millimeter-wave", "millimeter wave", "millimetre wave", "radar",
    "fmcw", "mimo-sar", "sar", "handheld", "autofocus", "phase error",
    "phase compensation", "phase calibration", "surface normal", "through-occlusion",
    "shape completion", "single static radar", "indoor scene understanding", "multipath"
]


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_of(p) -> str:
    return " ".join(str(p.get(k, "")) for k in ["title", "venue", "venue_group", "summary_en", "summary_cn", "why_include_en", "why_include_cn"] + ["topics"]).lower()


def is_mmwave_relevant(p) -> bool:
    txt = text_of(p)
    return any(term in txt for term in MMWAVE_SCOPE_TERMS)


def keep_reason(p):
    venue = str(p.get("venue", "")).lower()
    group = p.get("venue_group", "")
    origin = str(p.get("curation_origin", ""))
    verification = p.get("verification") or {}
    if group in ALLOWED_FINAL_GROUPS and venue != "arxiv preprint":
        return "allowed-final-venue"
    if origin.startswith("manual-user-request-mmwave") or verification.get("mode", "").startswith("manual-seed"):
        return "manual-mmwave-tracking-seed"
    if group == "arXiv" and venue == "arxiv preprint" and is_mmwave_relevant(p):
        return "high-relevance-mmwave-preprint"
    return "remove"


items = load(MMWAVE, [])
kept = []
removed = []
for p in items:
    reason = keep_reason(p)
    if reason != "remove":
        p.setdefault("verification", {})
        if isinstance(p["verification"], dict):
            p["verification"].setdefault("track", "mmwave")
            p["verification"]["mmwave_keep_reason"] = reason
        kept.append(p)
    else:
        removed.append({"id": p.get("id"), "title": p.get("title"), "venue": p.get("venue"), "venue_group": p.get("venue_group")})

kept.sort(key=lambda p: str(p.get("publication_date") or p.get("year") or ""), reverse=True)
dump(MMWAVE, kept)
log = load(LOG, {})
log["mmwave_allowlist_final_groups"] = sorted(ALLOWED_FINAL_GROUPS)
log["mmwave_track_total"] = len(kept)
log["mmwave_track_removed_non_policy"] = removed
log["mmwave_track_policy"] = "Hidden mmWave side track keeps final top-venue papers, high-relevance mmWave arXiv/preprints, and explicitly marked manual tracking seeds. Nature Portfolio includes Communications Engineering and other Nature-family journals through the curation group mapping."
dump(LOG, log)
print(f"mmWave side track: kept {len(kept)}, removed {len(removed)}")
