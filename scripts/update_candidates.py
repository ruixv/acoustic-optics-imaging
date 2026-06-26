#!/usr/bin/env python3
"""Scheduled discovery step for the acoustic-optics imaging tracker.

This script favors recall. It writes discovered records to data/candidates.json
with status `candidate-pending-agent-audit`. The next pipeline step,
scripts/agent_audit.py, performs curation and promotes high-confidence records.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
PAPERS_PATH = DATA_DIR / "papers.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
RUN_LOG_PATH = DATA_DIR / "last_update.json"

TOP_VENUE_HINTS = [
    "Nature", "Nature Electronics", "Nature Photonics", "Nature Communications",
    "Communications Physics", "Scientific Data", "Light: Science & Applications",
    "Science", "Science Advances", "Science Robotics", "Science Translational Medicine",
    "ACM Transactions on Graphics", "TOG", "SIGGRAPH", "SIGGRAPH Asia",
    "IEEE Transactions on Pattern Analysis and Machine Intelligence", "TPAMI",
    "IEEE Transactions on Image Processing", "TIP",
    "CVPR", "ICCV", "ECCV", "ICLR", "NeurIPS", "Neural Information Processing Systems",
]

QUERIES = [
    "acoustic optical imaging",
    "acoustic-optical imaging",
    "acoustic optical sensor fusion",
    "camera sonar fusion",
    "vision sonar fusion",
    "synthetic aperture sonar neural reconstruction",
    "synthetic aperture sonar 3D reconstruction",
    "acoustic non-line-of-sight imaging",
    "ultrasound synthetic aperture non-line-of-sight imaging",
    "acoustic holography imaging",
    "acoustic coded imaging",
    "computational ultrasound imaging",
    "acousto optic imaging",
    "acousto-optic imaging",
    "photoacoustic imaging temporal encoding",
    "photoacoustic computed tomography deep learning",
    "all optical ultrasound detection photoacoustic imaging",
]

CORE_TERMS = [
    "acoustic", "sonar", "ultrasound", "photoacoustic", "optoacoustic", "acousto-optic", "acousto optic",
]
IMAGING_TERMS = [
    "imaging", "reconstruction", "tomography", "holography", "nlos", "non-line-of-sight", "non line of sight",
    "synthetic aperture", "sensor fusion", "gaussian splatting", "neural rendering", "3d",
]
NEGATIVE_TERMS = [
    "speech recognition", "music", "audio caption", "radio galaxy", "black hole", "x-ray binary",
    "tidal disruption", "cell culture", "ball games", "raman data fusion",
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "acoustic-optics-imaging-updater/2.0 (https://github.com/ruixv/acoustic-optics-imaging; mailto:%s)" % os.getenv("CROSSREF_MAILTO", "example@example.com")
})


def norm_text(x: str) -> str:
    return re.sub(r"\s+", " ", (x or "").strip())


def slugify(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:max_len].strip("-") or "candidate"


def fingerprint(title: str, doi: str = "", url: str = "") -> str:
    key = (doi or title or url).lower().strip()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_year_date_crossref(item: Dict[str, Any]) -> Tuple[Optional[int], str]:
    for k in ["published-print", "published-online", "published", "created", "issued"]:
        parts = (item.get(k) or {}).get("date-parts")
        if parts and parts[0]:
            arr = parts[0]
            year = int(arr[0]) if arr and arr[0] else None
            month = int(arr[1]) if len(arr) > 1 else 1
            day = int(arr[2]) if len(arr) > 2 else 1
            if year:
                return year, f"{year:04d}-{month:02d}-{day:02d}"
    return None, ""


def score_candidate(title: str, abstract: str, venue: str, query: str, year: Optional[int]) -> Tuple[int, List[str]]:
    text = f"{title} {abstract}".lower()
    venue_text = venue.lower()
    reasons: List[str] = []
    score = 0
    if any(v.lower() in venue_text or v.lower() in text for v in TOP_VENUE_HINTS):
        score += 4
        reasons.append("top-venue-hint")
    if any(t in text for t in CORE_TERMS):
        score += 3
        reasons.append("acoustic/photoacoustic term")
    if any(t in text for t in IMAGING_TERMS):
        score += 3
        reasons.append("imaging/reconstruction term")
    if any(t in text for t in NEGATIVE_TERMS):
        score -= 4
        reasons.append("negative-topic-filter")
    q_terms = [w for w in re.split(r"\W+", query.lower()) if len(w) > 3]
    hits = sum(1 for w in q_terms if w in text)
    if q_terms and hits >= max(1, len(q_terms) // 2):
        score += 2
        reasons.append("query-title/abstract match")
    current_year = dt.date.today().year
    if year and year >= current_year - 2:
        score += 1
        reasons.append("recent")
    return score, reasons


def record_base(title: str, authors: str, year: Optional[int], pub_date: str, venue: str, doi: str, url: str, pdf: str, source: str, query: str, score: int, reasons: List[str]) -> Dict[str, Any]:
    return {
        "id": slugify(f"{year or 'yyyy'}-{title}") + "-" + fingerprint(title, doi, url),
        "title": title,
        "authors": authors,
        "year": year,
        "publication_date": pub_date,
        "venue": venue,
        "doi": doi,
        "primary_url": url,
        "pdf_url": pdf,
        "source": source,
        "matched_query": query,
        "score": score,
        "reasons": reasons,
        "status": "candidate-pending-agent-audit",
    }


def crossref_search(query: str, rows: int, from_date: str) -> List[Dict[str, Any]]:
    params = {
        "query.bibliographic": query,
        "rows": rows,
        "sort": "published",
        "order": "desc",
        "filter": f"from-pub-date:{from_date}",
        "select": "DOI,title,author,container-title,published-print,published-online,published,issued,created,URL,type,abstract",
    }
    if os.getenv("CROSSREF_MAILTO"):
        params["mailto"] = os.getenv("CROSSREF_MAILTO")
    r = SESSION.get("https://api.crossref.org/works?" + urllib.parse.urlencode(params), timeout=45)
    r.raise_for_status()
    out: List[Dict[str, Any]] = []
    for it in r.json().get("message", {}).get("items", []):
        title = norm_text(" ".join(it.get("title") or []))
        if not title:
            continue
        venue = norm_text(" ".join(it.get("container-title") or []))
        abstract = re.sub(r"<[^>]+>", " ", html.unescape(it.get("abstract") or ""))
        year, pub_date = get_year_date_crossref(it)
        authors = []
        for a in it.get("author") or []:
            name = norm_text(" ".join([a.get("given", ""), a.get("family", "")]))
            if name:
                authors.append(name)
        doi = it.get("DOI") or ""
        url = it.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        score, reasons = score_candidate(title, abstract, venue, query, year)
        out.append(record_base(title, "; ".join(authors[:8]) + ("; et al." if len(authors) > 8 else ""), year, pub_date, venue, doi, url, "", "Crossref", query, score, reasons))
    return out


def arxiv_search(query: str, rows: int, from_date: str) -> List[Dict[str, Any]]:
    search_query = " OR ".join([f'all:"{part}"' for part in query.split() if len(part) > 3]) or f'all:"{query}"'
    params = {"search_query": search_query, "start": 0, "max_results": rows, "sortBy": "submittedDate", "sortOrder": "descending"}
    r = SESSION.get("http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params), timeout=45)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    cutoff = dt.date.fromisoformat(from_date)
    out: List[Dict[str, Any]] = []
    for e in root.findall("a:entry", ns):
        title = norm_text(e.findtext("a:title", default="", namespaces=ns))
        summary = norm_text(e.findtext("a:summary", default="", namespaces=ns))
        published = e.findtext("a:published", default="", namespaces=ns)
        pub_date = published[:10] if published else ""
        if pub_date:
            try:
                if dt.date.fromisoformat(pub_date) < cutoff:
                    continue
            except ValueError:
                pass
        year = int(pub_date[:4]) if pub_date[:4].isdigit() else None
        authors = "; ".join(norm_text(a.findtext("a:name", default="", namespaces=ns)) for a in e.findall("a:author", ns))
        entry_id = e.findtext("a:id", default="", namespaces=ns)
        pdf_url = ""
        for link in e.findall("a:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
        score, reasons = score_candidate(title, summary, "arXiv", query, year)
        out.append(record_base(title, authors, year, pub_date, "arXiv preprint", "", entry_id, pdf_url, "arXiv", query, score, reasons))
    return out


def merge_candidates(new_items: Iterable[Dict[str, Any]], existing: List[Dict[str, Any]], verified: List[Dict[str, Any]], min_score: int) -> List[Dict[str, Any]]:
    verified_keys = {fingerprint(p.get("title", ""), p.get("doi", ""), p.get("primary_url", "")) for p in verified}
    by_key: Dict[str, Dict[str, Any]] = {}
    today = dt.date.today().isoformat()
    for item in existing:
        by_key[fingerprint(item.get("title", ""), item.get("doi", ""), item.get("primary_url", ""))] = item
    for item in new_items:
        if item.get("score", 0) < min_score:
            continue
        k = fingerprint(item.get("title", ""), item.get("doi", ""), item.get("primary_url", ""))
        if k in verified_keys:
            continue
        if k in by_key:
            prev = by_key[k]
            prev.update({kk: vv for kk, vv in item.items() if vv not in [None, "", []]})
            prev["last_seen"] = today
            prev["times_seen"] = int(prev.get("times_seen", 1)) + 1
        else:
            item["first_seen"] = today
            item["last_seen"] = today
            item["times_seen"] = 1
            by_key[k] = item
    merged = list(by_key.values())
    merged.sort(key=lambda x: (x.get("score", 0), x.get("publication_date", "")), reverse=True)
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=730)
    ap.add_argument("--rows", type=int, default=30)
    ap.add_argument("--min-score", type=int, default=6)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()
    today = dt.date.today()
    from_date = (today - dt.timedelta(days=args.since_days)).isoformat()
    verified = load_json(PAPERS_PATH, [])
    existing = load_json(CANDIDATES_PATH, [])
    all_new: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for q in QUERIES:
        for source_name, func in [("Crossref", crossref_search), ("arXiv", arxiv_search)]:
            try:
                items = func(q, args.rows, from_date)
                all_new.extend(items)
                print(f"{source_name}: {q!r}: {len(items)} raw candidates")
            except Exception as e:
                print(f"ERROR {source_name} {q!r}: {e}")
                errors.append({"source": source_name, "query": q, "error": str(e)})
            time.sleep(args.sleep)
    merged = merge_candidates(all_new, existing, verified, args.min_score)
    write_json(CANDIDATES_PATH, merged)
    write_json(RUN_LOG_PATH, {
        "last_run": dt.datetime.now(dt.timezone.utc).isoformat(),
        "since_date": from_date,
        "raw_candidates_seen": len(all_new),
        "saved_candidates_total": len(merged),
        "errors": errors,
        "note": "Candidates are ready for automatic curation-agent audit; high-confidence records may be promoted by scripts/agent_audit.py.",
    })
    print(f"saved {len(merged)} candidates to {CANDIDATES_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
