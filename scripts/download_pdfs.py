#!/usr/bin/env python3
"""Download open-access PDFs listed in the public metadata.

This script intentionally downloads only URLs explicitly recorded in the metadata.
It does not bypass paywalls or use unofficial mirrors.
"""
from pathlib import Path
import json, re, sys, time
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
OUT = ROOT / 'pdfs'
OUT.mkdir(exist_ok=True)


def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s).strip('-')[:120]


def load(name):
    p = DATA_DIR / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else []


def download(url, out):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; acoustic-optics-imaging/1.1; +https://github.com/ruixv/acoustic-optics-imaging)'}
    with requests.get(url, headers=headers, stream=True, timeout=45, allow_redirects=True) as r:
        r.raise_for_status()
        ctype = r.headers.get('content-type', '').lower()
        if 'pdf' not in ctype and not url.lower().endswith('.pdf'):
            print(f'  warning: content-type is {ctype}; saving anyway')
        with out.open('wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)


seen = set()
papers = []
for item in load('focus_papers.json') + load('papers.json'):
    if item.get('id') and item['id'] not in seen:
        papers.append(item)
        seen.add(item['id'])

for p in papers:
    url = p.get('pdf_url')
    if not url:
        print(f"skip: {p['id']} (no pdf_url)")
        continue
    out = OUT / f"{safe_name(p['id'])}.pdf"
    if out.exists() and out.stat().st_size > 1024:
        print(f"exists: {out.name}")
        continue
    print(f"download: {p['id']}\n  {url}")
    try:
        download(url, out)
        print(f"  saved: {out} ({out.stat().st_size/1024:.1f} KiB)")
        time.sleep(1.0)
    except Exception as e:
        print(f"  failed: {e}", file=sys.stderr)
print('done')
