#!/usr/bin/env python3
from pathlib import Path
import json, requests
ROOT = Path(__file__).resolve().parents[1]
papers = json.loads((ROOT/'data'/'papers.json').read_text(encoding='utf-8'))
headers={'User-Agent':'Mozilla/5.0 (compatible; acoustic-optics-imaging-linkcheck/1.0)'}
for p in papers:
    for k in ['primary_url','pdf_url','project_url','code_url']:
        url=p.get(k)
        if not url: continue
        try:
            r=requests.head(url,headers=headers,timeout=20,allow_redirects=True)
            if r.status_code>=400 or r.status_code==405:
                r=requests.get(url,headers=headers,timeout=20,allow_redirects=True,stream=True)
            print(f"{r.status_code}\t{k}\t{p['id']}\t{url}")
        except Exception as e:
            print(f"ERR\t{k}\t{p['id']}\t{url}\t{e}")
