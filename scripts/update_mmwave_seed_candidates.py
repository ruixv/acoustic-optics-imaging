#!/usr/bin/env python3
"""Targeted discovery for the optional hidden mmWave side-track.

This script searches public scholarly sources with seed queries that are easy to
miss with generic keyword search, then appends the results to candidates.json.
It also records exact manual seed titles so future runs keep looking for them
until authoritative metadata is found.
"""
from __future__ import annotations
from pathlib import Path
import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CANDIDATES = DATA / "candidates.json"
PAPERS = DATA / "papers.json"
FOCUS = DATA / "focus_papers.json"
MMWAVE = DATA / "mmwave_papers.json"
LOG = DATA / "last_update.json"

SEED_QUERIES = [
    "high resolution handheld millimeter wave imaging phase error estimation compensation",
    "A high-resolution handheld millimeter-wave imaging system with phase error estimation and compensation",
    "Communications Engineering handheld millimeter-wave imaging phase error compensation",
    "IFNet deep imaging focusing handheld SAR millimeter wave signals",
    "TwinFocus autofocus handheld mmWave SAR imaging physical digital twin references",
    "High-Fidelity Through-Occlusion 3D Reconstruction Millimeter-Wave Surface Normal Estimation",
    "mmNorm millimeter-wave surface normal hidden object reconstruction",
    "Wave-Former through occlusion 3D reconstruction wireless shape completion",
    "RISE single static radar indoor scene understanding",
    "single static radar indoor scene understanding mmWave multipath",
    "handheld millimeter wave SAR autofocus MobiSys MobiCom SenSys",
    "millimeter wave radar indoor scene understanding MobiCom SenSys",
    "mmWave surface normal estimation 3D reconstruction CVPR ICCV",
    "Nature Portfolio millimeter wave radar imaging Communications Engineering",
]

MANUAL_SEEDS = [
    {
        "title": "TwinFocus: Autofocus for Handheld mmWave SAR Imaging via Physical and Digital Twin References",
        "matched_query": "TwinFocus autofocus handheld mmWave SAR imaging physical digital twin references",
    },
    {
        "title": "High-Fidelity Through-Occlusion 3D Reconstruction via Millimeter-Wave Surface Normal Estimation",
        "matched_query": "High-Fidelity Through-Occlusion 3D Reconstruction Millimeter-Wave Surface Normal Estimation",
    },
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "acoustic-optics-mmwave-seed-search/1.1 (https://github.com/ruixv/acoustic-optics-imaging; mailto:%s)" % os.getenv("CROSSREF_MAILTO", "example@example.com")})


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm(x: str) -> str:
    return re.sub(r"\s+", " ", (x or "").strip())


def slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")[:90] or "mmwave-seed"


def fp(item: Dict[str, Any]) -> str:
    key = (item.get("doi") or item.get("title") or item.get("primary_url") or "").lower().strip()
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def date_from_crossref(item: Dict[str, Any]) -> Tuple[Optional[int], str]:
    for k in ["published-print", "published-online", "published", "issued", "created"]:
        parts = (item.get(k) or {}).get("date-parts")
        if parts and parts[0]:
            arr = parts[0]
            y = int(arr[0]) if arr and arr[0] else None
            m = int(arr[1]) if len(arr) > 1 else 1
            d = int(arr[2]) if len(arr) > 2 else 1
            if y:
                return y, f"{y:04d}-{m:02d}-{d:02d}"
    return None, ""


def score(title: str, abstract: str, venue: str) -> int:
    text = f"{title} {abstract} {venue}".lower()
    s = 0
    if any(k in text for k in ["mmwave", "millimeter wave", "millimeter-wave", "millimetre wave", "radar", "fmcw", "mimo-sar", "wireless"]):
        s += 5
    if any(k in text for k in ["imaging", "reconstruction", "mapping", "scene understanding", "sar", "surface normal", "autofocus", "phase error", "phase compensation", "phase calibration", "through-occlusion", "shape completion", "multipath", "single static radar", "digital twin", "physical twin"]):
        s += 5
    if any(k in text for k in ["cvpr", "iccv", "eccv", "iclr", "icml", "iccp", "neurips", "mobisys", "mobicom", "sensys", "transactions on mobile computing", "nature", "communications engineering", "communications physics"]):
        s += 4
    return s


def crossref(query: str) -> List[Dict[str, Any]]:
    params = {"query.bibliographic": query, "rows": 10, "sort": "published", "order": "desc"}
    if os.getenv("CROSSREF_MAILTO"):
        params["mailto"] = os.getenv("CROSSREF_MAILTO")
    r = SESSION.get("https://api.crossref.org/works?" + urllib.parse.urlencode(params), timeout=45)
    r.raise_for_status()
    out = []
    for it in r.json().get("message", {}).get("items", []):
        title = norm(" ".join(it.get("title") or []))
        if not title:
            continue
        venue = norm(" ".join(it.get("container-title") or []))
        abstract = re.sub(r"<[^>]+>", " ", html.unescape(it.get("abstract") or ""))
        y, pub = date_from_crossref(it)
        doi = it.get("DOI") or ""
        url = it.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        authors = []
        for a in it.get("author") or []:
            name = norm(" ".join([a.get("given", ""), a.get("family", "")]))
            if name:
                authors.append(name)
        sc = score(title, abstract, venue)
        if sc < 7:
            continue
        out.append({"id": slugify(f"{y or 'yyyy'}-{title}") + "-" + fp({"title": title, "doi": doi, "primary_url": url}), "title": title, "authors": "; ".join(authors), "year": y, "publication_date": pub, "venue": venue, "doi": doi, "primary_url": url, "pdf_url": "", "source": "Crossref-mmwave-seed", "matched_query": query, "score": sc, "reasons": ["mmwave-seed-query"], "status": "candidate-pending-agent-audit"})
    return out


def arxiv(query: str) -> List[Dict[str, Any]]:
    params = {"search_query": " OR ".join([f'all:\"{w}\"' for w in query.split() if len(w) > 3]), "start": 0, "max_results": 10, "sortBy": "submittedDate", "sortOrder": "descending"}
    r = SESSION.get("http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params), timeout=45)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        title = norm(e.findtext("a:title", default="", namespaces=ns))
        summary = norm(e.findtext("a:summary", default="", namespaces=ns))
        pub = (e.findtext("a:published", default="", namespaces=ns) or "")[:10]
        y = int(pub[:4]) if pub[:4].isdigit() else None
        url = e.findtext("a:id", default="", namespaces=ns)
        pdf = ""
        for link in e.findall("a:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf = link.attrib.get("href", "")
        authors = "; ".join(norm(a.findtext("a:name", default="", namespaces=ns)) for a in e.findall("a:author", ns))
        sc = score(title, summary, "arXiv preprint")
        if sc < 7:
            continue
        out.append({"id": slugify(f"{y or 'yyyy'}-{title}") + "-" + fp({"title": title, "primary_url": url}), "title": title, "authors": authors, "year": y, "publication_date": pub, "venue": "arXiv preprint", "doi": "", "primary_url": url, "pdf_url": pdf, "source": "arXiv-mmwave-seed", "matched_query": query, "score": sc, "reasons": ["mmwave-seed-query", "requires-final-venue-verification"], "status": "candidate-pending-agent-audit"})
    return out


def manual_seed_items() -> List[Dict[str, Any]]:
    today = dt.date.today().isoformat()
    out = []
    for seed in MANUAL_SEEDS:
        title = seed["title"]
        out.append({
            "id": slugify(f"manual-{title}") + "-" + fp({"title": title}),
            "title": title,
            "authors": "Authors pending verification",
            "year": None,
            "publication_date": "",
            "venue": "Metadata pending",
            "doi": "",
            "primary_url": "",
            "pdf_url": "",
            "source": "Manual-mmwave-seed",
            "matched_query": seed.get("matched_query", title),
            "score": 12,
            "reasons": ["manual-mmwave-seed", "requires-authoritative-metadata"],
            "status": "candidate-pending-agent-audit",
            "first_seen": today,
            "last_seen": today,
            "times_seen": 1,
        })
    return out


verified = load(PAPERS, []) + load(FOCUS, []) + load(MMWAVE, [])
existing = load(CANDIDATES, [])
seen = {fp(x) for x in verified + existing}
new_items = []
errors = []
for q in SEED_QUERIES:
    for fn in [crossref, arxiv]:
        try:
            for item in fn(q):
                key = fp(item)
                if key not in seen:
                    item["first_seen"] = dt.date.today().isoformat()
                    item["last_seen"] = dt.date.today().isoformat()
                    item["times_seen"] = 1
                    new_items.append(item)
                    seen.add(key)
        except Exception as e:
            errors.append({"query": q, "source": fn.__name__, "error": str(e)})
        time.sleep(0.5)

for item in manual_seed_items():
    key = fp(item)
    if key not in seen:
        new_items.append(item)
        seen.add(key)

merged = existing + new_items
merged.sort(key=lambda x: (x.get("score", 0), str(x.get("publication_date", ""))), reverse=True)
dump(CANDIDATES, merged)
log = load(LOG, {})
log["mmwave_seed_queries"] = SEED_QUERIES
log["mmwave_manual_seed_titles"] = [s["title"] for s in MANUAL_SEEDS]
log["mmwave_seed_new_candidates"] = len(new_items)
if errors:
    log.setdefault("errors", []).extend(errors)
dump(LOG, log)
print(f"mmWave seed search added {len(new_items)} candidates")
