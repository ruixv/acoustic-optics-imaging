#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, re, html

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

INDEX='''<!doctype html>
<html lang='en' data-page='index'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Acoustic–Optics Imaging Paper Tracker</title><link rel='stylesheet' href='style.css'></head>
<body data-page='index'><div class='shell'><header class='topbar'><a class='brand' href='index.html'><span class='mark'>AΩ</span><span>Acoustic–Optics Imaging</span></a><nav class='nav'><a href='index.html' data-i18n='navVerified'>Verified papers</a><a href='updates.html' data-i18n='navUpdates'>Auto-reviewed updates</a><a href='data/papers.json'>papers.json</a><a href='data/candidates.json'>candidates.json</a></nav><div class='lang'><button data-lang='en'>EN</button><button data-lang='zh'>中文</button></div></header><main><section class='hero'><div><p class='eyebrow' data-i18n='eyebrow'>Scheduled literature tracker</p><h1 data-i18n='heroTitle'>Top-tier papers on sound, light, and computational imaging.</h1><p class='lead' data-i18n='heroSubtitle'>A clean reading map for acoustic–optical fusion, acoustic coded imaging, sonar reconstruction, acoustic holography, photoacoustic imaging, and acousto-optic imaging.</p><div class='actions'><a class='primary' href='updates.html' data-i18n='viewUpdates'>View auto-reviewed updates</a><a class='secondary' href='data/papers.json' data-i18n='viewJson'>Open metadata JSON</a></div></div><aside class='metrics'><div><b id='m-papers'>—</b><span data-i18n='metricPapers'>verified papers</span></div><div><b id='m-candidates'>—</b><span data-i18n='metricCandidates'>auto-reviewed candidates</span></div><div><b id='m-latest'>—</b><span data-i18n='metricLatest'>latest update</span></div></aside></section><section class='audit'><strong data-i18n='auditTitle'>Automatic curation agent</strong><p data-i18n='auditText'>Every scheduled run searches public scholarly sources, audits venue/source/relevance/PDF signals, promotes high-confidence papers, and keeps borderline records as candidates.</p></section><section class='toolbar'><input id='q' type='search'><select id='venue'></select><select id='topic'></select><select id='rel'></select></section><section class='section-head'><div><h2 data-i18n='libraryTitle'>Verified library</h2><p data-i18n='librarySubtitle'>English is the default. Switch to Chinese for translated titles and Chinese highlights.</p></div><p id='count'>—</p></section><section id='grid' class='grid'></section></main><footer class='footer'><p data-i18n='footerPdf'>PDF links point only to open or legitimate sources.</p><p data-i18n='footerPrivacy'>Public metadata uses neutral project language.</p></footer></div><script src='script.js' defer></script></body></html>
'''
UPDATES='''<!doctype html>
<html lang='en' data-page='updates'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Auto-reviewed Updates · Acoustic–Optics Imaging</title><link rel='stylesheet' href='style.css'></head>
<body data-page='updates'><div class='shell'><header class='topbar'><a class='brand' href='index.html'><span class='mark'>AΩ</span><span>Acoustic–Optics Imaging</span></a><nav class='nav'><a href='index.html' data-i18n='navVerified'>Verified papers</a><a href='updates.html' data-i18n='navUpdates'>Auto-reviewed updates</a><a href='data/papers.json'>papers.json</a><a href='data/candidates.json'>candidates.json</a></nav><div class='lang'><button data-lang='en'>EN</button><button data-lang='zh'>中文</button></div></header><main><section class='hero compact'><div><p class='eyebrow' data-i18n='updatesEyebrow'>Automated discovery</p><h1 data-i18n='updatesTitle'>Auto-reviewed paper updates.</h1><p class='lead' data-i18n='updatesSubtitle'>The scheduled workflow searches public scholarly sources every 6 hours. A curation agent scores venue quality, source reliability, topical relevance, PDF availability, and duplicate status.</p></div><aside class='metrics'><div><b id='m-candidates'>—</b><span data-i18n='metricCandidates'>auto-reviewed candidates</span></div><div><b id='m-promoted'>—</b><span data-i18n='metricPromoted'>agent-promoted papers</span></div><div><b id='m-latest'>—</b><span data-i18n='metricLatest'>latest update</span></div></aside></section><section class='audit'><strong data-i18n='autoAuditTitle'>Agent audit policy</strong><p data-i18n='autoAuditText'>High-confidence papers can be promoted automatically. Borderline records remain visible here for transparency.</p></section><section class='toolbar one'><input id='q' type='search'></section><section class='section-head'><div><h2 data-i18n='candidateTitle'>Candidate stream</h2><p data-i18n='candidateSubtitle'>Each item keeps its audit status, score, and source.</p></div><p id='count'>—</p></section><section id='grid' class='grid'></section></main><footer class='footer'><p>Raw JSON: <a href='data/candidates.json'>data/candidates.json</a> · Run log: <a href='data/last_update.json'>data/last_update.json</a></p></footer></div><script src='script.js' defer></script></body></html>
'''
PAPER='''<!doctype html>
<html lang='en' data-page='paper'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Paper details · Acoustic–Optics Imaging</title><link rel='stylesheet' href='style.css'></head><body data-page='paper'><div class='shell'><header class='topbar'><a class='brand' href='index.html'><span class='mark'>AΩ</span><span>Acoustic–Optics Imaging</span></a><nav class='nav'><a href='index.html' data-i18n='navVerified'>Verified papers</a><a href='updates.html' data-i18n='navUpdates'>Auto-reviewed updates</a><a href='data/papers.json'>papers.json</a></nav><div class='lang'><button data-lang='en'>EN</button><button data-lang='zh'>中文</button></div></header><main><p class='back'><a href='index.html' data-i18n='backToIndex'>← Back to paper index</a></p><article id='detail' class='detail'></article></main><footer class='footer'><p data-i18n='footerPrivacy'>Public metadata uses neutral project language.</p></footer></div><script src='script.js' defer></script></body></html>
'''

def load(name,default):
    p=DATA/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def sanitize(txt):
    txt=str(txt or '')
    scope=chr(0x4E0E)+chr(0x4F60)+chr(0x7684)
    poss=chr(0x4F60)+chr(0x7684)
    txt=re.sub(re.escape(scope)+r'[“\"][^。]*[”\"][^。]*。?','该论文与公开追踪主题直接相关，并提供可核验来源。',txt)
    return txt.replace(poss,'该')

def redirect(pid,title):
    pid=html.escape(pid); title=html.escape(title or pid)
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta http-equiv='refresh' content='0; url=../paper.html?id={pid}'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{title} · Acoustic–Optics Imaging</title><link rel='canonical' href='../paper.html?id={pid}'><link rel='stylesheet' href='../style.css'></head><body><main class='shell'><p class='note'>This page has moved to <a href='../paper.html?id={pid}'>paper.html?id={pid}</a>.</p></main></body></html>"""

def main():
    papers=load('papers.json',[]); changed=False
    for p in papers:
        for k,v in list(p.items()):
            if isinstance(v,str):
                nv=sanitize(v)
                if nv!=v: p[k]=nv; changed=True
    if changed: write_json(DATA/'papers.json',papers)
    (ROOT/'index.html').write_text(INDEX,encoding='utf-8')
    (ROOT/'updates.html').write_text(UPDATES,encoding='utf-8')
    (ROOT/'paper.html').write_text(PAPER,encoding='utf-8')
    d=ROOT/'papers'; d.mkdir(exist_ok=True)
    for p in papers:
        if p.get('id'): (d/f"{p['id']}.html").write_text(redirect(p['id'],p.get('title','')),encoding='utf-8')
    print(f'Rebuilt bilingual data-driven site for {len(papers)} papers')
if __name__=='__main__': main()
