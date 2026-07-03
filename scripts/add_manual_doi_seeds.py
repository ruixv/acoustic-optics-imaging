#!/usr/bin/env python3
"""Merge manually supplied DOI seeds into the candidate stream.

This is intentionally conservative: manual DOI seeds are not promoted directly.
They enter data/candidates.json with explicit metadata-pending status, then the
normal audit and future metadata-resolution passes can upgrade them once ACM,
Crossref, OpenAlex, DBLP, or other authoritative sources expose full metadata.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SEEDS = DATA / 'manual_doi_seeds.json'
CANDIDATES = DATA / 'candidates.json'
PAPERS = DATA / 'papers.json'
FOCUS = DATA / 'focus_papers.json'
MMWAVE = DATA / 'mmwave_papers.json'
LOG = DATA / 'last_update.json'


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fp(item: Dict[str, Any]) -> str:
    key = (item.get('doi') or item.get('title') or item.get('primary_url') or '').lower().strip()
    return hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]


def title_key(item: Dict[str, Any]) -> str:
    return ' '.join((item.get('title') or '').lower().split())


def normalize_seed(seed: Dict[str, Any]) -> Dict[str, Any]:
    today = dt.date.today().isoformat()
    out = dict(seed)
    out.setdefault('source', 'Manual-DOI-seed')
    out.setdefault('score', 11)
    out.setdefault('status', 'metadata-pending-manual-doi')
    out.setdefault('first_seen', today)
    out['last_seen'] = today
    out['times_seen'] = int(out.get('times_seen', 0) or 0) + 1
    out.setdefault('final_version_status', 'manual-doi-metadata-pending')
    out.setdefault('needs_metadata_verification', True)
    out.setdefault('reasons', ['manual-doi-seed'])
    if 'manual-doi-seed' not in out['reasons']:
        out['reasons'].append('manual-doi-seed')
    out.setdefault('agent_audit', {})
    return out


def main() -> int:
    seeds: List[Dict[str, Any]] = load(SEEDS, [])
    candidates: List[Dict[str, Any]] = load(CANDIDATES, [])
    verified = load(PAPERS, []) + load(FOCUS, []) + load(MMWAVE, [])

    verified_fps = {fp(x) for x in verified}
    verified_titles = {title_key(x) for x in verified}
    by_fp = {fp(x): x for x in candidates}

    added = 0
    updated = 0
    for seed in seeds:
        item = normalize_seed(seed)
        key = fp(item)
        if key in verified_fps or title_key(item) in verified_titles:
            continue
        if key in by_fp:
            prev = by_fp[key]
            prev.update({k: v for k, v in item.items() if v not in [None, '', []]})
            updated += 1
        else:
            by_fp[key] = item
            added += 1

    merged = list(by_fp.values())
    merged.sort(key=lambda x: (x.get('score', 0), str(x.get('publication_date', ''))), reverse=True)
    dump(CANDIDATES, merged)

    log = load(LOG, {})
    log.update({
        'manual_doi_seed_last_run': dt.datetime.now(dt.timezone.utc).isoformat(),
        'manual_doi_seed_count': len(seeds),
        'manual_doi_seed_added': added,
        'manual_doi_seed_updated': updated,
    })
    dump(LOG, log)
    print(f'manual DOI seeds merged: {added} added, {updated} updated, {len(seeds)} configured')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
